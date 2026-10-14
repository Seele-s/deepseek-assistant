"""上下文窗口管理：把历史消息裁剪到可控长度，避免超出模型 Token 上限。"""
from ..config import settings

SYSTEM_PROMPT = (
    "You are a helpful assistant. "
    "回答使用 Markdown 格式，代码请使用带语言标注的代码块，数学公式请使用 LaTeX。"
)


def build_context(history: list, user_message: str) -> list:
    """构造发给模型的消息列表。

    history: 已按时间升序排列的历史消息 [{"role": ..., "content": ...}]（不含本轮）
    策略：
      1. 只保留最近 MAX_CONTEXT_MESSAGES 条历史；
      2. 再按字符预算 MAX_CONTEXT_CHARS 从新到旧累计，超出即停止；
      3. system 提示词与本轮用户消息一定保留。
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    budget = settings.max_context_chars - len(user_message)
    kept = []
    for item in reversed(history[-settings.max_context_messages:]):
        content = item.get("content") or ""
        if len(content) > budget:
            break
        budget -= len(content)
        kept.append({"role": item.get("role", "user"), "content": content})
    kept.reverse()

    messages.extend(kept)
    messages.append({"role": "user", "content": user_message})
    return messages
