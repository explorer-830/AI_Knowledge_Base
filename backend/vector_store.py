from pathlib import Path
import  os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv
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
    vector_store.add_texts(texts=chunks,metadatas=metadatas)
    return len(chunks)


def search_documents(query: str, k: int = 3):
    results=vector_store.similarity_search_with_score(query,k=k)
    for doc,score in results:
        print("距离:",score)
        print("内容:",doc.page_content[:100])
        return results