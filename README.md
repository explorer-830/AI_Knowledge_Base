AI Knowledge Base

一个基于 RAG（Retrieval-Augmented Generation，检索增强生成） 架构实现的 AI 企业知识库项目。

项目支持上传 PDF 文档，对文档进行解析、文本切分、向量化并存储到 Chroma 向量数据库。用户提问后，系统通过向量相似度检索知识库中的相关内容，并结合 DeepSeek 大语言模型生成回答。

项目采用 FastAPI + Streamlit + LangChain + Chroma + HuggingFace Embedding + DeepSeek API等框架 构建。

项目功能

-  PDF 文档上传
-  PDF 文本解析
-  基于 LangChain 的文本切分
-  HuggingFace Embedding 向量化
   Chroma 向量数据库存储
-  向量相似度检索
-  基于距离值的相关性阈值判断
-  DeepSeek 大语言模型问答
   FastAPI 后端 API
-  Streamlit Web 前端
-  多轮对话
-  新建对话
-  回答参考来源展示
-  日志记录与异常处理
-  Docker / Docker Compose 配置

«Docker 配置文件已经加入项目，但目前尚未完成完整的 Docker 部署验证。»

---

技术栈

技术| 用途
Python| 项目主要开发语言
FastAPI| 后端 API 服务
Uvicorn| FastAPI 服务运行
Streamlit| Web 前端界面
LangChain| 文本切分、Embedding 与向量检索相关组件
Chroma| 向量数据库
HuggingFace| Embedding 模型
BAAI/bge-small-zh-v1.5| 中文文本向量化模型
DeepSeek API| 大语言模型
pypdf| PDF 文档解析
Docker| 容器化配置
Docker Compose| 容器编排配置

---

系统架构

                    用户
                     │
                     ▼
             ┌───────────────┐
             │   Streamlit   │
             │    前端界面    │
             └───────┬───────┘
                     │ HTTP
                     ▼
             ┌───────────────┐
             │    FastAPI    │
             │    后端 API    │
             └───────┬───────┘
                     │
          ┌──────────┴──────────┐
          │                     │
          ▼                     ▼
    PDF 文档处理             用户问题
          │                     │
          ▼                     ▼
      文本切分             向量相似度检索
          │                     │
          ▼                     ▼
  BGE Embedding             Chroma
          │                向量数据库
          ▼                     │
        Chroma ◄────────────────┘
                                │
                                ▼
                         相关内容 / Context
                                │
                                ▼
                         DeepSeek LLM
                                │
                                ▼
                             AI 回答

---

RAG 工作流程

1. 文档入库

用户通过 Streamlit 上传 PDF：

PDF
 ↓
FastAPI /upload
 ↓
pypdf 解析文本
 ↓
LangChain RecursiveCharacterTextSplitter
 ↓
文本 Chunk
 ↓
BGE Embedding
 ↓
Chroma

项目当前文本切分配置：

chunk_size = 500
chunk_overlap = 50

---

2. 用户提问

用户在 Streamlit 中输入问题：

用户问题
   ↓
FastAPI /chat
   ↓
Embedding
   ↓
Chroma 相似度检索
   ↓
获取 Top-K 相关文本
   ↓
距离值阈值判断
   ↓
构建知识库 Context
   ↓
DeepSeek
   ↓
生成回答

---

向量检索与阈值判断

项目使用 Chroma 的：

similarity_search_with_score()

获取相关文档及对应距离值。

当前检索默认返回 Top 3 结果：

search_documents(query, k=3)

项目对检索结果进行距离值判断：

best_score = min(score for doc, score in results)

if best_score > 1:
    return {
        "answer": "知识库当中没有相关内容"
    }

同时仅将满足当前阈值条件的内容作为上下文提供给大语言模型。

这样可以在用户提出与知识库无关的问题时，减少无关内容被直接交给 LLM 的情况。

«当前阈值属于项目现阶段的实验参数，后续会根据实际数据进一步优化。»

---

大语言模型

项目使用 DeepSeek API 进行最终回答生成。

当前使用模型：

deepseek-chat

系统 Prompt 要求模型：

- 根据知识库内容回答问题
- 不随意编造知识库不存在的信息
- 如果知识库中没有相关内容，明确告知用户

---

项目结构

AI_Knowledge_Base/
│
├── backend/
│   ├── main.py              # FastAPI 后端入口
│   ├── pdf_utils.py         # PDF 文本解析
│   ├── text_splitter.py     # 文本切分
│   └── vector_store.py      # Embedding、Chroma 与向量检索
│
├── frontend/
│   └── app.py               # Streamlit 前端
│
├── .dockerignore            # Docker 忽略文件
├── .env.example             # 环境变量配置示例
├── .gitignore               # Git 忽略文件
├── Dockerfile               # Docker 镜像配置
├── docker-compose.yml       # Docker Compose 配置
├── requirements.txt         # Python 项目依赖
└── README.md                # 项目说明

---

API 接口

GET "/"

检查后端服务是否正常运行。

GET /

返回：

{
  "message": "企业知识库启动成功"
}

---

POST "/upload"

上传 PDF 文档并将其加入知识库。

POST /upload

主要处理流程：

上传 PDF
 ↓
保存文件
 ↓
解析 PDF
 ↓
文本切分
 ↓
Embedding
 ↓
写入 Chroma

---

POST "/search"

根据用户问题进行知识库检索。

POST /search

返回：

- 查询内容
- 检索结果
- 文档来源
- 距离值

---

POST "/chat"

基于知识库内容进行 AI 问答。

POST /chat

主要流程：

用户问题
 ↓
知识库检索
 ↓
阈值判断
 ↓
构建 Context
 ↓
DeepSeek
 ↓
返回回答

---

环境配置

项目使用 ".env" 保存 API Key 和模型路径等环境变量。

首先复制：

.env.example

创建：

.env

根据自己的环境配置：

DeepSeek_API_key=your_api_key

EMBEDDING_MODEL_PATH=your_local_model_path

BACKEND_URL=http://127.0.0.1:8000

其中：

- "DeepSeek_API_key"：DeepSeek API Key
- "EMBEDDING_MODEL_PATH"：本地 HuggingFace Embedding 模型路径
- "BACKEND_URL"：Streamlit 访问 FastAPI 的地址

---

本地运行

1. 克隆项目

git clone https://github.com/explorer-830/AI_Knowledge_Base.git

进入项目目录：

cd AI_Knowledge_Base

---

2. 创建虚拟环境

python -m venv .venv

Windows：

.venv\Scripts\activate

---

3. 安装依赖

pip install -r requirements.txt

---

4. 配置环境变量

创建 ".env" 文件：

DeepSeek_API_key=your_api_key
EMBEDDING_MODEL_PATH=your_local_model_path
BACKEND_URL=http://127.0.0.1:8000

---

5. 启动 FastAPI

在项目根目录执行：

uvicorn backend.main:app --reload

默认地址：

http://127.0.0.1:8000

FastAPI 接口文档：

http://127.0.0.1:8000/docs

---

6. 启动 Streamlit

重新打开一个终端并激活虚拟环境：

.venv\Scripts\activate

运行：

streamlit run frontend/app.py

然后通过 Streamlit 提供的本地地址访问前端。

---

Embedding 模型

项目使用：

BAAI/bge-small-zh-v1.5

作为中文文本 Embedding 模型。

Embedding 模型负责将文本转换为向量，使系统能够通过向量距离判断用户问题与知识库文本之间的相关程度。

项目支持本地模型路径，并配置了 HuggingFace / Transformers 离线加载：

HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1

可以减少运行过程中对 HuggingFace 网络连接的依赖。

---

Streamlit 前端

当前前端主要包含：

知识库管理

- PDF 文件上传
- 上传至知识库
- 显示文件名
- 显示文本块数量

AI 问答

- 用户问题输入
- AI 回答展示
- 多轮聊天记录
- 新建对话
- 参考来源展示

前端通过 HTTP 请求调用 FastAPI 后端：

Streamlit
    │
    │ requests
    ▼
FastAPI

---

Docker

项目目前已经提供 Docker 相关配置：

Dockerfile
docker-compose.yml
.dockerignore

用于后续容器化部署。

当前状态：

- Dockerfile：已编写
- docker-compose.yml：已编写
- Docker 实际部署：尚未完成验证

后续将继续完成 Docker 容器运行、数据持久化以及多服务部署测试。

---

项目特点

1. 完整的 RAG 基础流程

项目实现了从：

文档上传
 → 文本解析
 → 文本切分
 → Embedding
 → 向量存储
 → 相似度检索
 → 阈值判断
 → LLM 生成

的完整基础 RAG 流程。

2. 前后端分离

使用 FastAPI 提供后端 API，Streamlit 负责前端交互。

Streamlit
    ↓
FastAPI
    ↓
Chroma / DeepSeek

3. 本地 Embedding

使用本地 BGE 模型完成文本向量化，减少对第三方 Embedding API 的依赖。

4. 检索相关性控制

通过 Chroma 返回的距离值进行阈值判断，在检索结果相关性较低时减少无关内容进入 LLM 上下文。

5. 基础工程化实践

项目中加入：

- ".env" 环境变量管理
- ".gitignore"
- 日志记录
- FastAPI 异常处理
- Docker 配置
- Git / GitHub 版本管理

---

后续计划

- 优化文本切分策略
- 优化 Chunk Size 与 Chunk Overlap
-  优化向量检索效果
-  增加 Rerank
-  优化检索阈值
-  优化 Prompt
-  完善日志与异常处理
-  完善 Docker 部署
-  优化 Streamlit 前端 UI
-  增加知识库与文档管理功能
---

项目状态

当前项目已经完成：

-PDF 文档上传
-  PDF 文本解析
-  文本切分
-  HuggingFace BGE Embedding
-  Chroma 向量数据库
-  相似度检索
-  检索距离阈值判断
-  DeepSeek AI 问答
-  FastAPI 后端
-  Streamlit 前端
-  多轮对话
-  参考来源展示
-  日志与异常处理
-  Git 版本管理
   GitHub 项目托管
-  Docker 配置文件

Docker 实际部署以及进一步的 RAG 检索优化将在后续开发中完成。
