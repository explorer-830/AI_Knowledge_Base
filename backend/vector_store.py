import hashlib
import json
import logging
import os
import re
from pathlib import Path
from threading import RLock

import jieba
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_huggingface import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)
load_dotenv()
os.environ["HF_HUB_OFFLINE"]="1"
os.environ["TRANSFORMERS_OFFLINE"]="1"
BASE_DIR = Path(__file__).resolve().parent.parent
CHROMA_DIR = BASE_DIR / "chroma_db"

MODEL_PATH = os.getenv("EMBEDDING_MODEL_PATH")

embeddings = HuggingFaceEmbeddings(
    model_name=MODEL_PATH
)

vector_store = Chroma(
    collection_name="knowledge_base",
    embedding_function=embeddings,
    persist_directory=str(CHROMA_DIR)
)


def add_documents(chunks,filename):
    metadatas=[{"source":filename}
               for _ in chunks]
    document_key = hashlib.sha256(
        json.dumps([filename, chunks], ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    ids = [f"{document_key}:{index}" for index in range(len(chunks))]
    global _bm25_index
    with _index_lock:
        try:
            vector_store.add_texts(texts=chunks, metadatas=metadatas, ids=ids)
        finally:
            _bm25_index = None
    return len(chunks)


def search_documents(query: str, k: int = 3):
    results=vector_store.similarity_search_with_score(query,k=k)
    for doc,score in results:
        logger.debug("距离: %s", score)
        logger.debug("来源: %s", doc.metadata.get("source", ""))
    return results


_index_lock = RLock()
_bm25_index = None
_stop_words = set("的 了 是 在 有 和 与 或 请 问 如何 怎么 什么 哪个 哪些 为什么 可以 需要 我 我们 你 一个 一下 这个 那个 吗 呢 吧".split())


def tokenize(text):
    tokens = []
    for part in re.findall(r"[a-zA-Z0-9_]+(?:[.-][a-zA-Z0-9_]+)*|[\u4e00-\u9fff]+", text.lower()):
        words = jieba.lcut(part) if re.search(r"[\u4e00-\u9fff]", part) else [part]
        tokens.extend(word for word in words if word not in _stop_words)
    return tokens


class CandidateRetriever(BaseRetriever):
    documents: list[Document]

    def _get_relevant_documents(self, query, *, run_manager):
        return self.documents


def get_bm25_index():
    global _bm25_index
    if _bm25_index is None:
        stored = vector_store.get(include=["documents", "metadatas"])
        documents = []
        for chunk_id, text, metadata in zip(stored["ids"], stored["documents"], stored["metadatas"]):
            if text and tokenize(text):
                documents.append(Document(
                    page_content=text,
                    metadata={**(metadata or {}), "chunk_id": chunk_id},
                    id=chunk_id
                ))
        if documents:
            _bm25_index = BM25Retriever.from_documents(documents, preprocess_func=tokenize)
            logger.info("BM25 index restored: %s chunks", len(documents))
    return _bm25_index


def hybrid_search(query: str, k: int = 3):
    query_tokens = set(tokenize(query))
    if not query_tokens or k <= 0:
        return []
    with _index_lock:
        bm25 = get_bm25_index()
        if bm25 is None:
            return []
        candidate_k = max(k * 3, 10)
        bm25.k = candidate_k
        lexical = [doc for doc in bm25.invoke(query)
                   if query_tokens.intersection(tokenize(doc.page_content))]
        dense_results = search_documents(query, k=candidate_k)
        dense = []
        distances = {}
        for doc, distance in dense_results:
            chunk_id = doc.id or doc.metadata.get("chunk_id")
            if chunk_id is None:
                raise ValueError("Vector result is missing its chunk ID")
            doc.metadata["chunk_id"] = chunk_id
            dense.append(doc)
            distances[chunk_id] = float(distance)
        ensemble = EnsembleRetriever(
            retrievers=[CandidateRetriever(documents=lexical),
                        CandidateRetriever(documents=dense)],
            weights=[0.5, 0.5], id_key="chunk_id", c=60
        )
        ranked = ensemble.invoke(query)
        scores = {}
        for documents in (lexical, dense):
            for rank, doc in enumerate(documents, 1):
                chunk_id = doc.metadata["chunk_id"]
                scores[chunk_id] = scores.get(chunk_id, 0.0) + 0.5 / (60 + rank)
        identifiers = {token for token in query_tokens
                       if re.search(r"[a-z]", token) and re.search(r"[0-9_]", token)}
        results = []
        for doc in ranked:
            chunk_id = doc.metadata["chunk_id"]
            doc_tokens = set(tokenize(doc.page_content))
            matched = query_tokens.intersection(doc_tokens)
            coverage = len(matched) / len(query_tokens)
            distance = distances.get(chunk_id)
            keyword_match = (len(matched) >= 2 and coverage >= 0.6) or query_tokens <= doc_tokens
            relevant = (distance is not None and distance <= 1.0) or keyword_match
            if identifiers:
                relevant = relevant and identifiers <= doc_tokens
            doc.metadata = {**doc.metadata, "vector_distance": distance,
                            "keyword_coverage": coverage, "relevant": relevant}
            if relevant:
                results.append((doc, scores[chunk_id]))
            if len(results) == k:
                break
        logger.info("Hybrid retrieval: %s keyword, %s vector, %s accepted",
                    len(lexical), len(dense), len(results))
        return results
