import os
from dotenv import load_dotenv

load_dotenv()  # 加载 .env 文件中的变量

# DeepSeek / LLM API（兼容两种变量名）
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY") or os.getenv("API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL") or os.getenv("API_BASE_URL", "https://api.deepseek.com/v1")

# MySQL：优先使用完整连接字符串，否则从各个字段拼接
MYSQL_CONNECTION_STRING = os.getenv("MYSQL_CONNECTION_STRING", "")
if not MYSQL_CONNECTION_STRING:
    host = os.getenv("MYSQL_HOST", "localhost")
    port = os.getenv("MYSQL_PORT", "3306")
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "")
    database = os.getenv("MYSQL_DATABASE", "")
    if host and database:
        MYSQL_CONNECTION_STRING = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"