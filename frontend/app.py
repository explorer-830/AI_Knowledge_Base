import streamlit as st
import requests
import  os
BACKEND_URL=os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
st.set_page_config(
    page_title="AI 企业知识库",
    page_icon="📚",
    layout="wide"
)

st.title("AI 企业知识库")

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.header("📚 知识库")
    st.caption("上传PDF,构建你的专属知识库")

    st.divider()
    st.subheader("文档管理")

    if st.button("新建对话", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    uploaded_file = st.file_uploader(
        "上传 PDF 文件",
        type=["pdf"]
    )

    if uploaded_file is not None:
        if st.button("上传到知识库", use_container_width=True):
            files = {
                "file": (
                    uploaded_file.name,
                    uploaded_file.getvalue(),
                    "application/pdf"
                )
            }

            try:
                with st.spinner("📚 正在处理 PDF..."):
                    response = requests.post(
                        f"{BACKEND_URL}/upload",
                        files=files,
                        timeout=60
                    )

                if response.status_code == 200:
                    data = response.json()

                    st.success("上传成功")
                    st.write(f"文件：{data['filename']}")
                    st.write(f"文本块：{data['chunk_count']}")

                else:
                    st.error(
                        f"上传失败，状态码：{response.status_code}"
                    )

            except requests.exceptions.RequestException:
                st.error(
                    "无法连接后端服务，请确认 FastAPI 正在运行。"
                )

    st.divider()
    st.subheader("系统状态")
    st.success("API服务正常")
    st.caption("FastAPI")


st.divider()
st.subheader("知识库问答")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

        if message["role"] == "assistant" and "sources" in message:
            with st.expander("参考来源"):
                for source in message["sources"]:
                    st.write(f"{source['source']}")
                    st.write(source["content"])


if not st.session_state.messages:
    st.info("你好,我是知识库助手,pdf上传之后可以向我提问")


question = st.chat_input("请输入你的问题")

if question:
    st.session_state.messages.append({
        "role": "user",
        "content": question
    })

    try:
        with st.spinner("正在检索知识库并生成回答"):
            response = requests.post(
                f"{BACKEND_URL}/chat",
                json={"query": question},
                timeout=60
            )

        if response.status_code == 200:
            data = response.json()

            answer = data["answer"]
            sources = data.get("sources", [])

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
                "sources": sources
            })

            st.rerun()

        else:
            st.error(
                f"请求失败，状态码：{response.status_code}"
            )

    except requests.exceptions.RequestException:
        st.error(
            "无法连接后端服务，请检查 FastAPI 是否启动。"
        )