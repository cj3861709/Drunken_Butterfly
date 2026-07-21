"""
Drunken_Butterfly - 数据研究 Agent

功能：
- 多数据源支持：同时加载多个 Excel/CSV/MySQL 数据表
- 拖拽上传：支持数据文件 + 文档文件（.txt/.md/.pdf）拖拽进浏览器
- 本地缓存：保存上次的文件夹路径和记录，下次打开自动恢复
- 多表格分析：同时分析多个数据表
- 对话历史：类 ChatGPT 的多轮对话交互，历史保存本地，支持切换/新建/删除
"""

import streamlit as st
import pandas as pd
import os
import sys
import json
import uuid
from datetime import datetime
from agent_core import ask_question
from tool_functions import list_data_files, read_file, EXCEL_EXTENSIONS, CSV_EXTENSIONS
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, MYSQL_CONNECTION_STRING
from persistent_store import load_cache, save_cache
import conversation_store as conv_store

# ----- Streamlit 页面配置 -----
st.set_page_config(page_title="Drunken_Butterfly", layout="wide")

# ----- 加载 Airtable 设计系统 CSS -----
_css_path = os.path.join(os.path.dirname(__file__), "assets", "style.css")
if os.path.exists(_css_path):
    with open(_css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("🦋 Drunken_Butterfly - 数据研究 Agent")

# ----- 初始化 session 状态 -----
if "data_sources" not in st.session_state:
    st.session_state["data_sources"] = {}  # {name: {type, df, content, path, ...}}
if "last_folder" not in st.session_state:
    cache = load_cache()
    st.session_state["last_folder"] = cache.get("last_folder", "")
if "selected_file_path" not in st.session_state:
    st.session_state["selected_file_path"] = None
if "cache" not in st.session_state:
    st.session_state["cache"] = load_cache()
if "_chart_counter" not in st.session_state:
    st.session_state["_chart_counter"] = 0
if "_last_figures" not in st.session_state:
    st.session_state["_last_figures"] = None  # 最新助手响应的图表列表

# ----- 对话相关状态 -----
if "conversations" not in st.session_state:
    st.session_state["conversations"] = {}  # {conv_id: {...全量数据...}}
if "current_conv_id" not in st.session_state:
    st.session_state["current_conv_id"] = None
if "conv_list_cache" not in st.session_state:
    st.session_state["conv_list_cache"] = []


def _init_new_conversation():
    """创建新对话"""
    conv_id = uuid.uuid4().hex[:12]
    now = datetime.now().isoformat()
    conv = {
        "id": conv_id,
        "title": "新对话",
        "created_at": now,
        "updated_at": now,
        "messages": [],
    }
    st.session_state["conversations"][conv_id] = conv
    st.session_state["current_conv_id"] = conv_id
    return conv_id


def _switch_conversation(conv_id):
    """切换到指定对话"""
    if conv_id in st.session_state["conversations"]:
        st.session_state["current_conv_id"] = conv_id
    else:
        # 不在内存中则从本地加载
        data = conv_store.load_conversation(conv_id)
        if data:
            st.session_state["conversations"][conv_id] = data
            st.session_state["current_conv_id"] = conv_id
        else:
            _init_new_conversation()


def _get_current_conv():
    """获取当前对话对象"""
    conv_id = st.session_state.get("current_conv_id")
    if not conv_id or conv_id not in st.session_state["conversations"]:
        _init_new_conversation()
        conv_id = st.session_state["current_conv_id"]
    return st.session_state["conversations"][conv_id]


def _save_current_conversation():
    """保存当前对话到本地"""
    conv = _get_current_conv()
    conv["updated_at"] = datetime.now().isoformat()
    if conv["messages"]:
        conv["title"] = conv_store.generate_title(conv["messages"])
    conv_store.save_conversation(conv)


def _add_message(role: str, content: str, figures: list = None):
    """给当前对话添加一条消息"""
    conv = _get_current_conv()
    msg = {
        "role": role,
        "content": content,
        "time": datetime.now().isoformat(),
    }
    if figures:
        msg["chart_count"] = len(figures)
        # 将图表序列化为 JSON，重新打开后可还原
        msg["charts_json"] = [fig.to_json() for fig in figures]
    conv["messages"].append(msg)
    _save_current_conversation()


def _delete_conversation(conv_id):
    """删除对话"""
    conv_store.delete_conversation(conv_id)
    st.session_state["conversations"].pop(conv_id, None)
    if st.session_state.get("current_conv_id") == conv_id:
        # 切换到其他对话
        all_ids = list(st.session_state["conversations"].keys())
        if all_ids:
            st.session_state["current_conv_id"] = all_ids[0]
        else:
            _init_new_conversation()


# ----- 启动时自动恢复上次对话 -----
if not st.session_state["conversations"]:
    # 从本地加载最近对话列表
    conv_list = conv_store.list_conversations()
    if conv_list:
        # 加载最近的对话
        latest = conv_list[0]
        data = conv_store.load_conversation(latest["id"])
        if data:
            st.session_state["conversations"][data["id"]] = data
            st.session_state["current_conv_id"] = data["id"]
    if not st.session_state.get("current_conv_id"):
        _init_new_conversation()

# ----- 启动时自动恢复上次的数据源 -----
cache = st.session_state["cache"]
if cache.get("data_source_paths"):
    for name, fp in list(cache["data_source_paths"].items()):
        if os.path.exists(fp) and name not in st.session_state["data_sources"]:
            try:
                df = read_file(fp)
                _add_data_source(name, df=df, file_path=fp, src_type="dataframe")
            except Exception:
                pass  # 文件可能已被移动或删除，静默跳过


# ----- 辅助函数 -----
SUPPORTED_DATA_EXTENSIONS = {e.lstrip(".") for e in EXCEL_EXTENSIONS | CSV_EXTENSIONS}
SUPPORTED_DOC_EXTENSIONS = {"txt", "md", "pdf"}
ALL_ACCEPTED_TYPES = sorted(SUPPORTED_DATA_EXTENSIONS | SUPPORTED_DOC_EXTENSIONS)


def _extract_text_from_file(uploaded_file) -> str:
    """从上传的文档文件中提取文本"""
    fname = uploaded_file.name.lower()
    content = uploaded_file.read()
    if fname.endswith(".txt") or fname.endswith(".md"):
        return content.decode("utf-8", errors="replace")
    elif fname.endswith(".pdf"):
        try:
            import io
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(content))
            texts = []
            for page in reader.pages:
                texts.append(page.extract_text())
            return "\n".join(texts)
        except ImportError:
            return "[PDF解析需要安装 PyPDF2: pip install PyPDF2]"
    return ""


def _add_data_source(name: str, df: pd.DataFrame = None, content: str = None,
                     file_path: str = None, src_type: str = "dataframe"):
    """添加一个数据源到 session_state"""
    st.session_state["data_sources"][name] = {
        "type": src_type,
        "df": df,
        "content": content,
        "path": file_path,
        "rows": len(df) if df is not None else 0,
        "cols": list(df.columns) if df is not None else [],
    }
    # 持久化摘要信息
    cache = st.session_state["cache"]
    info_list = [n for n in cache.get("data_sources_info", []) if n != name]
    info_list.insert(0, name)
    cache["data_sources_info"] = info_list[:20]
    # 持久化文件路径（用于下次启动自动恢复）
    if file_path:
        paths = cache.get("data_source_paths", {})
        paths[name] = file_path
        cache["data_source_paths"] = paths
    save_cache(cache)


def _remove_data_source(name: str):
    """删除一个数据源"""
    if name in st.session_state["data_sources"]:
        del st.session_state["data_sources"][name]
    # 清理缓存路径
    cache = st.session_state["cache"]
    if "data_source_paths" in cache and name in cache["data_source_paths"]:
        del cache["data_source_paths"][name]
        save_cache(cache)


# 文件夹加载辅助
def _load_folder_files(file_names, file_path_map):
    """批量加载文件夹中的文件"""
    for name in file_names:
        fp = file_path_map[name]
        try:
            df = read_file(fp)
            _add_data_source(name, df=df, file_path=fp, src_type="dataframe")
            st.success(f"✅ 已加载 {name}")
        except Exception as e:
            st.error(f"❌ {name} 加载失败: {e}")


# ===================================================================
# 侧边栏：数据源管理 + 对话历史
# ===================================================================
with st.sidebar:
    st.header("📂 数据源管理")

    # 缓存恢复
    cache = st.session_state["cache"]
    if cache.get("last_folder") and not st.session_state["last_folder"]:
        st.session_state["last_folder"] = cache["last_folder"]

    # ========= 方式1：拖拽上传（支持数据文件 + 文档） =========
    st.subheader("📤 拖拽上传文件")
    uploaded_files = st.file_uploader(
        "将文件拖拽到此处",
        type=ALL_ACCEPTED_TYPES,
        accept_multiple_files=True,
        key="drag_uploader"
    )

    if uploaded_files:
        for upf in uploaded_files:
            base_name = upf.name
            if base_name in st.session_state["data_sources"]:
                continue

            fname_lower = base_name.lower()
            ext = fname_lower.split(".")[-1]

            try:
                if ext in SUPPORTED_DATA_EXTENSIONS:
                    if ext == "csv":
                        df = pd.read_csv(upf)
                    else:
                        df = pd.read_excel(upf)
                    _add_data_source(base_name, df=df, src_type="dataframe")
                    st.success(f"✅ 数据表 {base_name} ({len(df)}行)")

                elif ext in SUPPORTED_DOC_EXTENSIONS:
                    text = _extract_text_from_file(upf)
                    _add_data_source(base_name, content=text, src_type="document")
                    st.success(f"✅ 文档 {base_name} ({len(text)}字)")

            except Exception as e:
                st.error(f"❌ {base_name} 加载失败: {e}")

    # ========= 方式2：本地文件夹 =========
    st.subheader("💻 本地文件夹")
    folder_input = st.text_input(
        "文件夹路径",
        value=st.session_state["last_folder"],
        placeholder="例如: D:/data/ 或 /home/user/data",
        key="folder_input"
    )

    if folder_input and os.path.isdir(folder_input):
        st.session_state["last_folder"] = folder_input
        cache["last_folder"] = folder_input
        save_cache(cache)

        all_files = list_data_files(folder_input)
        if all_files:
            # 区分已加载与未加载
            loaded_names = set()
            for fp in all_files:
                bn = os.path.basename(fp)
                if bn in st.session_state["data_sources"]:
                    loaded_names.add(bn)
                    ds = st.session_state["data_sources"][bn]
                    if ds.get("path") is None:
                        ds["path"] = fp

            file_options = []
            file_path_map = {}
            for fp in all_files:
                bn = os.path.basename(fp)
                if bn not in loaded_names:
                    file_options.append(bn)
                    file_path_map[bn] = fp

            if file_options:
                selected_names = st.multiselect(
                    "📄 选择要加载的文件（可多选）",
                    options=file_options,
                    key="folder_multiselect"
                )

                # 预览功能：勾选文件后可以先看内容再决定加载
                if selected_names:
                    with st.expander("👁️ 预览选中文件内容", expanded=False):
                        preview_cols = st.columns(min(len(selected_names), 3))
                        for idx, name in enumerate(selected_names):
                            col = preview_cols[idx % len(preview_cols)]
                            with col:
                                fp = file_path_map[name]
                                try:
                                    ext = name.lower().split(".")[-1]
                                    if ext == "csv":
                                        preview_df = pd.read_csv(fp, nrows=5)
                                    else:
                                        preview_df = pd.read_excel(fp, nrows=5)
                                    st.caption(f"**{name}** ({len(preview_df)}行预览)")
                                    st.dataframe(preview_df, height=150, use_container_width=True)
                                except Exception as e:
                                    st.warning(f"{name} 预览失败: {e}")

                if st.button("📥 加载选中文件", key="load_folder_btn") and selected_names:
                    _load_folder_files(selected_names, file_path_map)
                    st.rerun()
            else:
                st.info("✅ 文件夹中所有数据文件已加载")

            if loaded_names:
                st.caption(f"📌 已加载: {', '.join(sorted(loaded_names))}")
        else:
            fmt_list = ", ".join(sorted(SUPPORTED_DATA_EXTENSIONS))
            st.warning(f"⚠️ 未找到支持的数据文件 ({fmt_list})")
    elif folder_input and not os.path.isdir(folder_input):
        st.error("❌ 路径无效")

    # ========= 已加载数据源一览 =========
    st.divider()
    st.subheader("📋 已加载的数据源")

    if st.session_state["data_sources"]:
        for name, ds in list(st.session_state["data_sources"].items()):
            col_a, col_b = st.columns([4, 1])
            with col_a:
                if ds["type"] == "document":
                    content_len = len(ds["content"]) if ds.get("content") else 0
                    st.caption(f"📄 **{name}** ({content_len}字 文档)")
                else:
                    rows = ds.get("rows", 0)
                    cols = ds.get("cols", [])
                    st.caption(f"📊 **{name}** ({rows}行 × {len(cols)}列)")
            with col_b:
                if st.button("🗑️", key=f"del_{name}"):
                    _remove_data_source(name)
                    st.rerun()

        st.caption(f"共 {len(st.session_state['data_sources'])} 个数据源")
        if st.button("🧹 清除所有数据源", key="clear_all"):
            st.session_state["data_sources"] = {}
            # 同时清除缓存的路径
            cache_clear = st.session_state["cache"]
            cache_clear["data_source_paths"] = {}
            save_cache(cache_clear)
            st.rerun()
    else:
        st.caption("暂无数据源，请通过上方上传或选择文件")

    # ----- MySQL / API 状态 -----
    st.divider()
    st.subheader("🗄️ MySQL")
    if MYSQL_CONNECTION_STRING:
        st.success("已配置")
    else:
        st.info("未配置（.env 中设置 MYSQL_CONNECTION_STRING）")

    st.divider()
    st.subheader("🔑 API")
    if DEEPSEEK_API_KEY:
        st.success("DeepSeek 已配置")
    else:
        st.error("❌ 未配置 DeepSeek API Key")

    # ========= 对话历史侧边栏 =========
    st.divider()
    st.subheader("💬 对话历史")

    # 刷新对话列表
    conv_list = conv_store.list_conversations()
    # 合并内存中的对话（可能有未保存的新对话）
    mem_ids = set(st.session_state["conversations"].keys())
    existing_ids = {c["id"] for c in conv_list}
    for mem_id in mem_ids:
        if mem_id not in existing_ids:
            conv_list.append(st.session_state["conversations"][mem_id])
    conv_list.sort(key=lambda x: x.get("updated_at", ""), reverse=True)

    if conv_list:
        for c in conv_list:
            cid = c["id"]
            is_current = (cid == st.session_state.get("current_conv_id"))
            prefix = "▶ " if is_current else "  "
            title = c.get("title", "未命名")
            label = f"{prefix}{title} ({c.get('msg_count', 0)}条)"

            col_a, col_b = st.columns([5, 1])
            with col_a:
                if st.button(label, key=f"switch_{cid}", use_container_width=True):
                    if not is_current:
                        _switch_conversation(cid)
                        st.rerun()
            with col_b:
                if st.button("🗑️", key=f"del_conv_{cid}"):
                    _delete_conversation(cid)
                    st.rerun()

    if st.button("➕ 新建对话", key="new_conv_btn", use_container_width=True):
        _init_new_conversation()
        st.rerun()


# ===================================================================
# 主区域：数据预览 + 对话聊天界面
# ===================================================================

# ========= 数据预览（Tabs 多表格） =========
if st.session_state["data_sources"]:
    st.header("📊 数据预览")
    tab_names = list(st.session_state["data_sources"].keys())
    tabs = st.tabs(tab_names)

    for idx, (name, ds) in enumerate(st.session_state["data_sources"].items()):
        with tabs[idx]:
            if ds["type"] == "document":
                content_preview = ds.get("content", "")
                st.text_area(
                    "📄 文档内容预览",
                    value=content_preview[:2000] + ("..." if len(content_preview) > 2000 else ""),
                    height=300,
                    disabled=True
                )
            else:
                df = ds.get("df")
                if df is not None:
                    col1, col2, col3 = st.columns(3)
                    col1.metric("行数", ds["rows"])
                    col2.metric("列数", len(ds["cols"]))
                    col3.metric("列名", ", ".join(ds["cols"][:5]) + ("..." if len(ds["cols"]) > 5 else ""))
                    st.dataframe(df, width='stretch')
                else:
                    st.info("数据无预览")


# ========= 对话聊天界面 =========
st.header("💬 对话")

# 显示当前对话标题
current_conv = _get_current_conv()
conv_title = current_conv.get("title", "新对话")
st.caption(f"当前对话: {conv_title}")

# 显示消息历史（类似 ChatGPT）
chat_container = st.container()
with chat_container:
    messages = current_conv.get("messages", [])
    for idx, msg in enumerate(messages):
        role = msg.get("role", "user")
        content = msg.get("content", "")
        chart_count = msg.get("chart_count", 0)
        msg_time = msg.get("time", "")[11:19] if msg.get("time") else ""

        if role == "user":
            with st.chat_message("user"):
                st.markdown(content)
                st.caption(f"🕐 {msg_time}")
        elif role == "assistant":
            with st.chat_message("assistant", avatar="🦋"):
                st.markdown(content)
                # 从保存的 charts_json 还原图表（支持历史消息）
                charts_json = msg.get("charts_json")
                if charts_json:
                    import plotly.io as pio
                    for i, chart_json in enumerate(charts_json):
                        fig = pio.from_json(chart_json)
                        st.plotly_chart(
                            fig,
                            width='stretch',
                            key=f"hist_chart_{st.session_state['_chart_counter']}_{i}"
                        )
                    st.session_state["_chart_counter"] += len(charts_json)
                elif chart_count and chart_count > 0:
                    # 旧格式消息：只有计数，没有图表数据
                    st.caption(f"📊 包含 {chart_count} 张图表（历史消息，图表数据已过期）")
                st.caption(f"🕐 {msg_time}")
        elif role == "system":
            with st.chat_message("assistant", avatar="⚙️"):
                st.info(content)

# 输入区
if st.session_state["data_sources"]:
    src_summary = ", ".join(st.session_state["data_sources"].keys())
    input_placeholder = f"📎 [{src_summary}] 输入你的数据分析需求..."
else:
    input_placeholder = "💡 输入需求（历史对话可直接追问，无需重新加载数据）"

user_question = st.chat_input(input_placeholder)

if user_question:
    # 添加用户消息
    _add_message("user", user_question)

    with st.chat_message("user"):
        st.markdown(user_question)

    with st.chat_message("assistant", avatar="🦋"):
        with st.spinner("🦋 Drunken_Butterfly 正在思考并调用工具..."):
            try:
                text_answer, figures = ask_question(
                    user_question,
                    file_path=st.session_state.get("selected_file_path"),
                    data_sources=st.session_state["data_sources"],
                    history_messages=_get_current_conv().get("messages", [])
                )

                st.markdown(text_answer)

                # 保存图表到 session_state，以便 st.rerun() 后能恢复
                st.session_state["_last_figures"] = figures

                # 显示图表
                for i, fig in enumerate(figures):
                    with st.container():
                        st.plotly_chart(
                            fig,
                            width='stretch',
                            key=f"chart_{st.session_state['_chart_counter']}_{i}"
                        )
                st.session_state["_chart_counter"] += 1

                # 保存助理回复到对话历史
                _add_message("assistant", text_answer, figures=figures)

            except Exception as e:
                error_msg = f"⚠️ 执行出错: {e}"
                st.error(error_msg)
                st.exception(e)
                _add_message("assistant", f"错误: {str(e)}")

        st.rerun()


# ----- 调试信息 -----
with st.expander("🔍 调试信息"):
    st.write("**data_sources 键:**", list(st.session_state["data_sources"].keys()))
    st.write("**current_conv_id:**", st.session_state.get("current_conv_id"))
    conv = _get_current_conv()
    st.write("**当前对话标题:**", conv.get("title"))
    st.write("**消息数:**", len(conv.get("messages", [])))
    st.write("**cache:**", st.session_state.get("cache", {}))
    st.write("**last_folder:**", st.session_state.get("last_folder", ""))
    st.write("**_chart_counter:**", st.session_state.get("_chart_counter", 0))

# ----- 启动保护 -----
if __name__ == "__main__":
    print("=" * 60)
    print("[错误] 请使用 'streamlit run app.py' 启动本项目")
    print("")
    print("    正确的启动命令:  streamlit run app.py")
    print("")
    print("=" * 60)