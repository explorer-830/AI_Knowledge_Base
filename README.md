# AI Knowledge Base

基于 RAG 的企业知识库项目，使用 **Vue 3 + FastAPI + LangChain + Chroma + 本地 BGE Embedding + DeepSeek API**。

上传文档后，后端提取文本、切分、向量化并写入 Chroma；提问时检索相关片段，结合 DeepSeek 生成回答并展示参考来源。Vue 已替换原来的 Streamlit 前端。

## 功能

- 上传 PDF、Word `.docx`、Excel `.xlsx`、TXT，单文件最大 20 MB。
- Word 提取正文段落与表格；Excel 提取多工作表内容及行列位置，保留零值、布尔值和公式字符串。
- TXT 支持 UTF-8（含 BOM）、带 BOM 的 UTF-16、GB18030。
- LangChain 文本切分：`chunk_size=500`、`chunk_overlap=50`。
- 本地 BGE 向量化、Chroma 持久化、BM25 与向量混合检索、RRF 排序。
- 中文分词使用 jieba，LangChain BM25Retriever 与 EnsembleRetriever 组合混合检索；使用原始向量距离和关键词覆盖率筛选候选片段。
- 回答前使用 DeepSeek 判断候选是否提供足够证据，回答与来源使用相同的已验证片段；证据不足时返回无相关内容提示。
- 同文件名、同文本分块生成稳定 ID，重复上传时复用 ID。
- Vue 聊天界面、页面内聊天记录、新建对话、来源展示、上传状态和后端健康检查。
- 文件类型、空文件、空文本、大小及解析异常校验；日志与异常处理。

当前不支持 Markdown、CSV、旧版 DOC/XLS 或扫描图片 OCR。Excel 公式不会重新计算。聊天记录只用于页面展示，当前后端每次根据本次问题独立检索，不包含跨轮记忆。向量距离阈值和关键词覆盖率是实验参数；RRF 分数只用于排序，不能当作原始距离。证据判断增加一次模型调用，仍需持续评估误召回和拒答。

## 技术栈

| 技术 | 用途 |
| --- | --- |
| Vue 3 | 页面、状态管理与交互（本地全局构建版本） |
| FastAPI / Uvicorn | HTTP API |
| pypdf / pdfplumber / python-docx / openpyxl | 文档解析 |
| LangChain | 文本切分、Embedding、向量库及混合检索组件 |
| BAAI/bge-small-zh-v1.5 | 本地中文 Embedding 模型 |
| Chroma | 向量存储与相似度检索 |
| DeepSeek API | 基于检索上下文生成答案 |
| Docker Compose / Nginx | 后端容器与 Vue 静态页面服务 |

## 项目结构

```text
backend/
  main.py                 FastAPI 路由、上传和问答
  file_utils.py           按扩展名分发的文档解析入口
  pdf_utils.py            PDF 文本解析
  text_splitter.py        文本切分
  vector_store.py         Embedding、Chroma、去重和检索
frontend-web/
  index.html              Vue 页面、样式与业务方法
  vue.global.prod.js      本地 Vue 运行库
  LICENSE.vue             Vue MIT 许可
Dockerfile
docker-compose.yml
requirements.txt
.env.example
```

```text
文档 → Vue → /upload → 解析 → 分块 → BGE → Chroma
问题 → Vue → /chat → 检索与过滤 → DeepSeek → 答案及来源
```

## 本地启动（Windows PowerShell）

### 1. 安装依赖

```powershell
git clone https://github.com/explorer-830/AI_Kowledge_Base.git AI_Knowledge_Base
cd AI_Knowledge_Base
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

### 2. 配置模型与密钥

编辑 `.env`：

```dotenv
DeepSeek_API_key=your_api_key_here
EMBEDDING_MODEL_PATH=D:/models/bge-small-zh-v1.5
EMBEDDING_MODEL_HOST_PATH=D:/models/bge-small-zh-v1.5
```

`EMBEDDING_MODEL_PATH` 是本地 Python 运行时使用的完整模型目录，需要事先准备好 BGE 模型权重、配置和 tokenizer 文件。项目使用离线加载，不会在启动时自动下载模型。

`EMBEDDING_MODEL_HOST_PATH` 仅用于 Docker，将主机上的完整模型目录挂载到容器。默认目录为 `./models/bge-small-zh-v1.5`。

### 3. 启动后端

在项目根目录运行：

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

API 文档：<http://127.0.0.1:8000/docs>。

### 4. 启动 Vue 前端

另开终端，在项目根目录运行：

```powershell
python -m http.server 4000 --bind 127.0.0.1 --directory frontend-web
```

打开 <http://127.0.0.1:4000>。前端使用本地 Vue 文件，无需 Node.js、npm 或 CDN。不要直接双击 HTML 文件启动。

前端 API 地址在 `frontend-web/index.html` 的 `API_BASE` 中，默认是 `http://127.0.0.1:8000`；后端 CORS 允许 `localhost:4000` 与 `127.0.0.1:4000`。修改地址或端口时需同步调整。当前配置面向本机运行，远程部署时需要使用客户端可访问的 API 地址并调整 CORS。

## Docker Compose

准备好 `.env` 和完整模型目录后，在项目根目录运行：

```powershell
docker compose up --build
```

- Vue 页面：<http://127.0.0.1:4000>，由 Nginx 提供静态文件。
- 后端：<http://127.0.0.1:8000>。
- `chroma_db/` 与 `uploads/` 挂载持久化；模型目录只读挂载。
- `.env`、虚拟环境、模型、上传文件和向量数据不提交 Git，也不打包进镜像。

Compose 配置已做静态校验；当前没有完成容器启动和真实模型的端到端部署验证。

## API

| 方法 | 路径 | 功能 |
| --- | --- | --- |
| GET | `/` | 后端健康检查 |
| POST | `/upload` | multipart 上传文档，返回文件名、文本长度、分块数量 |
| POST | `/search` | 接收 `{"query":"问题"}`，返回内容、来源、RRF 分数、原始向量距离和关键词覆盖率 |
| POST | `/chat` | 接收 `{"query":"问题"}`，返回答案及来源 |

上传失败：不支持的格式、空文件、无文本或损坏文件返回 400；超过 20 MB 返回 413；内部处理失败返回 500。

上传路由使用同步函数，由 FastAPI 线程池执行解析、切分和 Embedding，避免在异步路由中直接运行同步工作。

## 验证与当前边界

- 17 项后端自测通过：真实文件解析与上传、编码、表格内容、非法输入、路径安全及存储异常。向量入库使用替身，不写入正式知识库。
- 25 个 Vue 上传方法场景通过：格式与大小校验、正常响应、异常响应、网络错误及重复上传保护。不是浏览器端到端测试。
- 语法与 Git diff 格式检查通过。
- 已进行本地 BGE 混合检索评估、DeepSeek 证据判断和部分问答验证，测试不能代表所有真实文档均检索准确。
- PDF 否定符号恢复、计数及页数不匹配降级、无目标符号快速路径已做回归；该功能不是 OCR，也不保证所有公式均正确解析。

项目当前覆盖基础 RAG 流程；权限管理、多知识库隔离、文档删除、OCR、跨轮记忆、Rerank 和更全面的检索效果评估仍可继续完善。
