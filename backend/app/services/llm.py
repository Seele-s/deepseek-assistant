"""DeepSeek 调用封装：异步流式，区分 reasoning_content 与 content。"""
import json
from typing import AsyncIterator

from openai import AsyncOpenAI

from ..config import settings

_client = None


def get_client() -> AsyncOpenAI:
    """懒加载单例客户端，避免每次请求都新建连接。"""
    global _client
    if _client is None:
        if not settings.deepseek_api_key:
            raise RuntimeError("未配置 DEEPSEEK_API_KEY，请在 backend/.env 中填写")
        _client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
    return _client


def pick_model(is_reasoning: bool) -> str:
    return settings.reasoner_model if is_reasoning else settings.chat_model


async def stream_chat(messages: list, is_reasoning: bool) -> AsyncIterator[dict]:
    """产出 {"type": "r"|"c", "text": ...}
    r = reasoning_content（深度思考过程）
    c = content（最终回答）
    """
    client = get_client()
    response = await client.chat.completions.create(
        model=pick_model(is_reasoning),
        messages=messages,
        stream=True,
        temperature=settings.temperature,
    )
    async for chunk in response:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        reasoning = getattr(delta, "reasoning_content", None)
        if reasoning:
            yield {"type": "r", "text": reasoning}
        if delta.content:
            yield {"type": "c", "text": delta.content}


def encode_event(event: dict) -> str:
    return json.dumps(event, ensure_ascii=False) + "\n"
