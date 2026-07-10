<img width="1265" height="642" alt="image" src="https://github.com/user-attachments/assets/eb92177e-8b36-419c-8b69-98b93c6e404a" /># 🦋 Drunken Butterfly

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Streamlit-1.28%2B-red?logo=streamlit&logoColor=white" alt="Streamlit">
  <img src="https://img.shields.io/badge/LLM-DeepSeek-brightgreen" alt="DeepSeek">
  <img src="https://img.shields.io/badge/Database-MySQL-4479A1?logo=mysql&logoColor=white" alt="MySQL">
  <img src="https://img.shields.io/badge/Charts-Plotly-3F4F75?logo=plotly&logoColor=white" alt="Plotly">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
</p>

一个基于 LLM 的 AI Agent 助手，支持通过自然语言调用工具完成**数据分析和可视化**任务。

## ✨ 功能

- **📊 读取 Excel/CSV** — 解析 `.xlsx` / `.xls` / `.xlsm` / `.xlsb` / `.xltx` / `.xltm` / `.csv` 文件并返回结构化摘要
- **🗄️ 查询 MySQL** — 执行 SELECT 查询，结果自动存入内存数据源，可直接用于后续分析和绘图
- **📈 绘制图表** — 支持柱状图、折线图、饼图、散点图、直方图、箱线图、热力图等 17 种图表类型
- **📋 数据概览 (data_profile)** — 缺失值、列类型、唯一值、描述性统计的完整数据画像
- **🔗 相关性分析 (correlation_analysis)** — Pearson / Spearman / Kendall 相关系数矩阵 + 高相关对自动提取
- **📊 详细统计摘要 (statistical_summary)** — 分位数、偏度、峰度、变异系数、频率分布等
- **⚠️ 异常值检测 (detect_outliers)** — IQR / Z-Score 方法检测异常值
- **📉 分布分析 (distribution_analysis)** — 数值列分箱统计 / 类别列频率分布
- **📑 分组聚合分析 (group_analysis)** — 按分组列 + 聚合函数计算（mean/sum/count/max/min/std/median）
- **💬 对话式交互** — 基于 Streamlit 聊天界面，多轮 Tool Calling 自动迭代，支持系统消息提示
- **📂 多数据源** — 支持同时加载多个 Excel/CSV 文件 + MySQL 查询结果 + **文本文档**（.txt / .md / .pdf）
- **🔄 拖拽上传** — 浏览器直接拖拽上传数据文件或文本文档
- **👁️ 文件预览** — 加载前可预览文件夹中选中文件的前 5 行内容
- **📑 多表格预览** — 已加载的数据源以 Tabs 标签页展示，支持行数 / 列数指标
- **💾 数据自动恢复** — 重启应用后自动加载上次的数据表，无需手动重新选择
- **💬 对话历史管理** — 对话自动保存到本地，支持**切换 / 新建 / 删除**，对话标题自动生成
- **🖼️ 图表持久化** — 历史对话中的图表以 JSON 格式保存，重新打开后可正常显示
- **🎨 Airtable 设计系统** — 基于 Airtable 设计规范的前端 UI 风格（白色画布、深色墨色、干净编辑风）

## 📸 效果预览

> （建议在这里放一张应用运行截图或 GIF，例如 `assets/demo.png`）

<p align="center">
  <img src="assets/demo.png" alt="Drunken Butterfly 界面预览" width="80%" />
</p>

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/cj3861709/Drunken_Butterfly.git
cd Drunken_Butterfly
```

### 2. 创建虚拟环境（推荐）

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

将 `.env.example` 复制为 `.env`，并填入你的配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```ini
# LLM API 配置（二选一）
DEEPSEEK_API_KEY=sk-your-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com

# MySQL 数据库配置（按需修改）
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your-password
MYSQL_DATABASE=your-database
```

>
> 💡 环境变量同时兼容旧版变量名 `API_KEY` / `API_BASE_URL` / `MODEL_NAME`。

### 5. 运行应用

Windows 可直接双击 `start.bat`，或执行：

```bash
streamlit run app.py
```

浏览器会自动打开 `http://localhost:8501`。

## 🧩 项目结构

```
Drunken_Butterfly/
├── app.py                 # Streamlit 主界面（对话、数据源管理、自动恢复）
├── agent_core.py          # Agent 核心逻辑（多轮 Tool Calling 循环，5 大工具接口）
├── analysis_script.py     # 数据分析脚本（画像/相关性/异常检测等 6 种分析，支持独立运行）
├── tool_functions.py      # 工具函数（读 Excel / 查 MySQL / 17 种图表绘制）
├── config.py              # 读取环境变量（兼容新旧变量名）
├── conversation_store.py  # 对话历史持久化（本地 JSON 文件，支持切换/新建/删除）
├── persistent_store.py    # 缓存管理（数据源路径、最近文件夹等）
├── assets/
│   └── style.css          # Airtable 设计系统 CSS 样式
├── .streamlit/
│   └── config.toml        # Streamlit 主题配置
├── conversations/         # 对话历史 JSON 文件（自动生成）
├── cache.json             # 本地缓存文件（数据源路径、最近文件夹等，自动生成）
├── requirements.txt       # 依赖列表
├── .env                   # 存放 API Key（已忽略，不提交）
├── .env.example           # 环境变量模板
├── .gitignore             # 忽略规则
├── start.bat              # Windows 一键启动脚本
└── README.md              # 项目说明文档
```

## 🛠️ 使用的技术

| 技术 | 用途 |
|------|------|
| [Streamlit](https://streamlit.io) | Web 交互界面 |
| [OpenAI Python SDK](https://github.com/openai/openai-python) | LLM Function Calling（兼容 DeepSeek API） |
| [Pandas](https://pandas.pydata.org) | 数据处理与分析 |
| [Plotly](https://plotly.com/python/) | 交互式图表绘制（17 种图表类型） |
| [NumPy](https://numpy.org) | 数值计算 |
| [SQLAlchemy](https://www.sqlalchemy.org) | MySQL 数据库连接 |
| [PyMySQL](https://github.com/PyMySQL/PyMySQL) | MySQL 驱动 |
| [python-dotenv](https://pypi.org/project/python-dotenv/) | 环境变量加载 |
| [openpyxl](https://openpyxl.readthedocs.io) | Excel 文件读写 |
| [Tabulate](https://github.com/astanin/python-tabulate) | 表格格式化输出 |

## 🤖 Agent 工具

Drunken Butterfly 内置 5 个 LLM 工具，通过 Function Calling 自动编排调用：

| 工具 | 用途 |
|------|------|
| `read_file` | 读取数据文件（Excel / CSV），返回数据摘要 |
| `query_mysql` | 执行 MySQL 查询，结果自动存入内存数据源 |
| `get_data_full` | 获取内存中数据源的完整数据（支持按列筛选） |
| `run_analysis` | **统一分析入口**：data_profile / correlation_analysis / statistical_summary / detect_outliers / distribution_analysis / group_analysis |
| `create_chart` | 通用图表绘制，支持 17 种图表类型 |

> 分析流程：用户提问 → Agent 自动选择工具 → 获取数据 → 分析/绘图 → 返回结果，全程无需手动切换。

## 📝 使用示例

| 问题 | 预期行为 |
|------|----------|
| "读取销售数据.xlsx 文件" | Agent 调用 `read_file` 返回数据摘要 |
| "查询 users 表的前 10 条记录" | Agent 调用 `query_mysql`，结果自动存入内存 |
| "为销量画一张柱状图" | Agent 调用 `get_data_full` + `create_chart` 生成图表 |
| "大类有多少商品，各占比多少" | Agent 直接调用 `run_analysis` 分组聚合 + 饼图 |
| "有哪些异常数据" | Agent 直接调用 `run_analysis` 进行异常值检测 |
| "分析销量和利润的相关性" | Agent 调用 `run_analysis` 进行相关性分析 |

## 🔄 数据持久化说明

- **数据表自动恢复**：从文件夹加载的数据表，重启后自动重新加载（需文件路径不变）
- **对话历史**：所有对话自动保存到 `conversations/` 目录，支持侧边栏切换 / 新建 / 删除，标题自动从首条用户消息生成
- **图表保存**：生成的图表以 JSON 格式序列化存入对话记录，重新打开后仍可正常查看
- **缓存文件**：`cache.json` 保存最近文件夹路径、数据源文件路径等信息

## 🎨 界面设计

前端 UI 采用 **Airtable 设计规范**，核心风格：

- **白色画布** + **深色墨色** (#181d26) 主色调
- **近黑色主按钮** (12px 圆角) + **白色次按钮** (hairline 边框)
- **系统原生字体栈**（-apple-system, BlinkMacSystemFont, Segoe UI 等）
- **干净留白**，无渐变或装饰性背景，强调内容本身
- **对话气泡卡片** 风格，用户 / 助手 / 系统消息各自区分
- **侧边栏数据源管理** + **对话历史** 分层布局


## 📄 许可证

[MIT](LICENSE)
