import os
from backend.pdf_utils import read_pdf
from fastapi import FastAPI, UploadFile, File,HTTPException
from backend.text_splitter import split_text
from backend.vector_store import add_documents, search_documents
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI
import logging
load_dotenv()
logging.basicConfig(level=logging.INFO,format='%(asctime)s - %(name)s '
                                              '- %(levelname)s - %(message)s')
logger=logging.getLogger(__name__)

client = OpenAI(
    api_key=os.getenv("DeepSeek_API_key"),
    base_url="https://api.deepseek.com"
)


class SearchRequest(BaseModel):
    query: str


class ChatRequest(BaseModel):
    query: str


app = FastAPI(
    title="AI Knowledge Base API",
    description="企业知识库接口",
    version="1.0.0"
)


@app.get("/")
def home():
    return {"message": "企业知识库启动成功"}

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        logger.info("开始处理文件：%s", file.filename)

        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)

        file_path = os.path.join(upload_dir, file.filename)

        with open(file_path, "wb") as f:
            f.write(await file.read())

        text = read_pdf(file_path)

        chunks = split_text(text)

        chunk_count = add_documents(chunks, file.filename)

        logger.info(
            "文件处理完成：%s，共 %s 个文本块",
            file.filename,
            chunk_count
        )

        return {
            "message": "上传成功",
            "filename": file.filename,
            "length": len(text),
            "chunk_count": chunk_count
        }

    except Exception:
        logger.exception("处理文件失败：%s", file.filename)
        raise HTTPException(
            status_code=500,
            detail="PDF处理失败"
        )



@app.post("/search")
def search(request: SearchRequest):
    try:
        logger.info("收到检索请求：%s", request.query)

        results = search_documents(request.query, k=3)

        logger.info("检索完成：%s", request.query)

        return {
            "query": request.query,
            "results": [
                {
                    "content": result.page_content,
                    "source": result.metadata["source"],
                    "score": score
                }
                for result, score in results
            ]
        }

    except Exception:
        logger.exception("知识库检索失败：%s", request.query)

        raise HTTPException(
            status_code=500,
            detail="知识库检索失败"
        )


@app.post("/chat")
def chat(request: ChatRequest):
    try:
        logger.info("收到用户的问题: %s", request.query)
        results = search_documents(request.query, k=3)

        best_score=min(score for doc,score in results)
        if best_score>1:
            return {"answer":"知识库当中没有相关内容"
            }
      
        context = "\n\n".join(
            doc.page_content
            for doc,score in results
            if score<=1
        )

    
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是企业知识库助手。"
                        "请严格根据提供的知识库内容回答问题。"
                        "如果知识库中没有相关信息，请明确告诉用户，"
                        "不要自己编造答案。"
                    )
                },
                {
                    "role": "user",
                    "content": f"""
    知识库内容：
    {context}
    
    用户问题：
    {request.query}
    """
                }
            ]
        )

        answer = response.choices[0].message.content
        logger.info("问题处理完成:%s",request.query)
        return {
            "question": request.query,
            "answer": answer,
            "sources": [
                {
                    "content": doc.page_content,
                    "source": doc.metadata["source"]
                }
                for doc,score in results
            ]
        }
    except Exception :
        logger.exception("知识库回答失败: %s", request.query)
        raise HTTPException(status_code=500,detail="知识库回答异常")
