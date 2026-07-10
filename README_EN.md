# 🦋 Drunken Butterfly

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Streamlit-1.28%2B-red?logo=streamlit&logoColor=white" alt="Streamlit">
  <img src="https://img.shields.io/badge/LLM-DeepSeek-brightgreen" alt="DeepSeek">
  <img src="https://img.shields.io/badge/Database-MySQL-4479A1?logo=mysql&logoColor=white" alt="MySQL">
  <img src="https://img.shields.io/badge/Charts-Plotly-3F4F75?logo=plotly&logoColor=white" alt="Plotly">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
</p>

An LLM-powered AI Agent assistant that enables **data analysis and visualization** through natural language, leveraging Tool Calling (Function Calling) for automatic task orchestration.

## ✨ Features

- **📊 Read Excel/CSV** — Parse `.xlsx` / `.xls` / `.xlsm` / `.xlsb` / `.xltx` / `.xltm` / `.csv` files and return structured summaries
- **🗄️ Query MySQL** — Execute SELECT queries; results are automatically stored in-memory for further analysis and charting
- **📈 Charting** — 17+ chart types including bar, line, pie, scatter, histogram, box plot, heatmap, etc.
- **📋 Data Profile** — Missing values, column types, unique values, descriptive statistics
- **🔗 Correlation Analysis** — Pearson / Spearman / Kendall matrix + automatic high-correlation pair extraction
- **📊 Statistical Summary** — Quantiles, skewness, kurtosis, CV, frequency distribution
- **⚠️ Outlier Detection** — IQR / Z-Score methods
- **📉 Distribution Analysis** — Numeric binning / categorical frequency
- **📑 Group Analysis** — Group by + aggregation (mean/sum/count/max/min/std/median)
- **💬 Conversational UI** — Streamlit chat interface with multi-turn Tool Calling, supporting system messages
- **📂 Multi-source Data** — Load multiple Excel/CSV files + MySQL query results + text documents (.txt / .md / .pdf) simultaneously
- **🔄 Drag & Drop Upload** — Upload data files or documents directly in the browser
- **👁️ File Preview** — Preview the first 5 rows of a selected file before loading
- **📑 Multi-table Preview** — Display loaded data sources in Tabs with row/column count metrics
- **💾 Auto-restore on Restart** — Automatically reload previously loaded data tables without manual re-selection
- **💬 Conversation History** — Auto-saved locally, supports switch / new / delete, auto-generates titles
- **🖼️ Chart Persistence** — Charts serialized as JSON in conversation history, viewable after reopening
- **🎨 Airtable Design System** — White canvas, dark ink (#181d26), clean editorial style

## 🚀 Quick Start

### 1. Clone

```bash
git clone https://github.com/cj3861709/Drunken_Butterfly.git
cd Drunken_Butterfly
```

### 2. Virtual Environment (recommended)

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Copy `.env.example` to `.env` and fill in your configuration:

```bash
cp .env.example .env
```

Edit `.env`:

```ini
# LLM API config (choose one)
DEEPSEEK_API_KEY=sk-your-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1

# MySQL config (adjust as needed)
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your-password
MYSQL_DATABASE=your-database
```

> ⚠️ **Note**: `.env` contains sensitive info and is excluded by `.gitignore`. Never commit it.

### 5. Run

Windows: double-click `start.bat`, or:

```bash
streamlit run app.py
```

The browser will open at `http://localhost:8501`.

## 🧩 Project Structure

```
Drunken_Butterfly/
├── app.py                 # Streamlit main UI (chat, data source management, auto-restore)
├── agent_core.py          # Agent core (multi-turn Tool Calling, 5 tool interfaces)
├── analysis_script.py     # Analysis scripts (profile/correlation/outlier detection, 6 methods)
├── tool_functions.py      # Tool functions (read files, query MySQL, 17 chart types)
├── config.py              # Environment variable loader
├── conversation_store.py  # Conversation persistence (local JSON, switch/new/delete)
├── persistent_store.py    # Cache management (data source paths, recent folders)
├── assets/
│   └── style.css          # Airtable design system CSS
├── .streamlit/
│   └── config.toml        # Streamlit theme config
├── conversations/         # Conversation history JSON files (auto-generated)
├── cache.json             # Cache file (auto-generated)
├── requirements.txt       # Dependencies
├── .env                   # API keys (gitignored)
├── .env.example           # Environment template
├── .gitignore
├── start.bat              # Windows one-click launcher
└── README.md              # Documentation
```

## 🛠️ Tech Stack

| Technology | Purpose |
|------------|---------|
| [Streamlit](https://streamlit.io) | Web UI framework |
| [OpenAI Python SDK](https://github.com/openai/openai-python) | LLM Function Calling (compatible with DeepSeek API) |
| [Pandas](https://pandas.pydata.org) | Data processing & analysis |
| [Plotly](https://plotly.com/python/) | Interactive charts (17 types) |
| [NumPy](https://numpy.org) | Numerical computation |
| [SQLAlchemy](https://www.sqlalchemy.org) | MySQL connection |
| [PyMySQL](https://github.com/PyMySQL/PyMySQL) | MySQL driver |
| [python-dotenv](https://pypi.org/project/python-dotenv/) | Environment variable loading |
| [openpyxl](https://openpyxl.readthedocs.io) | Excel file I/O |
| [Tabulate](https://github.com/astanin/python-tabulate) | Table formatting |

## 🤖 Agent Tools

Drunken Butterfly has 5 built-in LLM tools, orchestrated via Function Calling:

| Tool | Purpose |
|------|---------|
| `read_file` | Read data files (Excel / CSV), return summary |
| `query_mysql` | Execute MySQL queries, results auto-stored in memory |
| `get_data_full` | Get full data from in-memory source (column filtering supported) |
| `run_analysis` | **Unified analysis entry**: data_profile / correlation_analysis / statistical_summary / detect_outliers / distribution_analysis / group_analysis |
| `create_chart` | Generic charting, 17 chart types |

> Workflow: User asks → Agent selects tool → Gets data → Analyzes/Charts → Returns result. No manual switching needed.

## 📝 Usage Examples

| Question | Expected Behavior |
|----------|-----------------|
| "Read sales_data.xlsx" | Agent calls `read_file`, returns summary |
| "Show top 10 from users table" | Agent calls `query_mysql`, result auto-stored |
| "Draw a bar chart for sales" | Agent calls `get_data_full` + `create_chart` |
| "How many products per category?" | Agent calls `run_analysis` for group aggregation + pie chart |
| "Any outliers in the data?" | Agent calls `run_analysis` for outlier detection |
| "Correlation between sales and profit" | Agent calls `run_analysis` for correlation analysis |

## 📄 License

[MIT](LICENSE)
