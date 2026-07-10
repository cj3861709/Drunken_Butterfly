"""
本地持久化存储模块

将用户配置、最近文件等数据保存到本地 cache.json，
确保下次打开应用时能恢复上次状态。
"""

import json
import os

CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache.json")


def load_cache() -> dict:
    """加载本地缓存"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "last_folder": "",
        "recent_files": [],        # 最近使用的文件路径列表
        "data_sources_info": [],   # 数据源摘要 [{name, type, cols, rows}]
    }


def save_cache(data: dict):
    """保存本地缓存"""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass