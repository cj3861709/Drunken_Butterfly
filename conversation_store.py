"""
对话历史管理模块

将每次分析对话持久化到本地 JSON 文件，
支持历史对话列表、新建、切换、删除，
下次打开应用自动恢复上次对话。
"""

import json
import os
from datetime import datetime

CONVERSATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "conversations")


def _ensure_dir():
    """确保对话目录存在"""
    if not os.path.exists(CONVERSATIONS_DIR):
        os.makedirs(CONVERSATIONS_DIR)


def list_conversations():
    """列出所有历史对话（按更新时间倒序）"""
    _ensure_dir()
    convs = []
    for fname in os.listdir(CONVERSATIONS_DIR):
        if fname.startswith("conv_") and fname.endswith(".json"):
            fpath = os.path.join(CONVERSATIONS_DIR, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                convs.append({
                    "id": data.get("id", fname),
                    "title": data.get("title", "未命名对话"),
                    "created_at": data.get("created_at", ""),
                    "updated_at": data.get("updated_at", ""),
                    "msg_count": len(data.get("messages", [])),
                })
            except (json.JSONDecodeError, OSError):
                pass
    convs.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return convs


def load_conversation(conv_id):
    """加载指定对话的完整内容（含 messages）"""
    _ensure_dir()
    for fname in os.listdir(CONVERSATIONS_DIR):
        if fname.startswith("conv_") and fname.endswith(".json"):
            fpath = os.path.join(CONVERSATIONS_DIR, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("id") == conv_id:
                    return data
            except (json.JSONDecodeError, OSError):
                pass
    return None


def save_conversation(data):
    """保存对话到本地文件"""
    _ensure_dir()
    conv_id = data.get("id", "unknown")
    fname = f"conv_{conv_id}.json"
    fpath = os.path.join(CONVERSATIONS_DIR, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return fpath


def delete_conversation(conv_id):
    """删除指定对话"""
    _ensure_dir()
    for fname in os.listdir(CONVERSATIONS_DIR):
        if fname.startswith("conv_") and fname.endswith(".json"):
            fpath = os.path.join(CONVERSATIONS_DIR, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("id") == conv_id:
                    os.remove(fpath)
                    return True
            except (json.JSONDecodeError, OSError):
                pass
    return False


def generate_title(messages):
    """从对话消息中自动生成标题（取第一条用户消息的前30字）"""
    for msg in messages:
        if msg.get("role") == "user":
            text = msg.get("content", "").strip()
            if text:
                return text[:30] + ("..." if len(text) > 30 else "")
    return "新对话"