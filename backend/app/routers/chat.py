"""对话路由：SSE 流式输出，区分「思考过程」与「最终回答」。"""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import settings
from ..database import SessionLocal
from ..deps import get_current_user, get_db
from ..services import llm
from ..services.context import build_context

router = APIRouter(tags=["对话"])

DEFAULT_TITLES = (None, "", "新对话", "New Chat")


def read_attachment(local_path: str) -> str:
    """读取已上传附件的内容。只允许 uploads 目录内的白名单文件，防路径穿越。"""
    name = Path(local_path).name  # 丢掉任何目录部分，杜绝 ../ 穿越
    target = settings.upload_dir / name
    if target.suffix.lower() not in settings.allowed_upload_exts or not target.is_file():
        return "[系统提示] 附件不存在或类型不支持"
    text = target.read_text(encoding="utf-8", errors="ignore")
    if len(text) > settings.max_inline_file_chars:
        return text[: settings.max_inline_file_chars] + "\n\n[系统提示] 文件过大，已截断"
    return text


def maybe_auto_title(db: Session, session: models.ChatSession, first_message: str) -> None:
    """会话还是默认标题时，用第一条消息自动命名（避免每次都要手动输入标题）。"""
    if session.title in DEFAULT_TITLES:
        session.title = (first_message.strip()[:30] or "新对话")
        db.commit()


@router.post("/chat")
async def chat(
    request: schemas.ChatRequest,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = (
        db.query(models.ChatSession)
        .filter(
            models.ChatSession.id == request.session_id,
            models.ChatSession.user_id == user.id,
        )
        .first()
    )
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "会话不存在")

    # 发给模型的 prompt（含附件正文），与落库内容分开，避免库里存大段文件
    prompt = request.message
    if request.file_path:
        prompt += "\n\n--- 附件内容 ---\n" + read_attachment(request.file_path) + "\n--- 附件结束 ---"

    db.add(models.ChatMessage(session_id=session.id, role="user", content=request.message))
    db.commit()
    maybe_auto_title(db, session, request.message)

    history = [
        {"role": m.role, "content": m.content}
        for m in db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id == session.id)
        .order_by(models.ChatMessage.id)
        .all()
    ][:-1]  # 去掉刚写入的这条，本轮内容由 prompt 提供
    messages = build_context(history, prompt)

    session_id = session.id
    is_reasoning = request.is_reasoning

    async def event_stream():
        full_response = ""
        try:
            async for event in llm.stream_chat(messages, is_reasoning):
                if event["type"] == "c":
                    full_response += event["text"]
                yield llm.encode_event(event)
        except Exception as exc:
            yield llm.encode_event({"type": "c", "text": "\n[服务异常] " + str(exc)})
        finally:
            if full_response:
                # 流式响应期间单独开一个会话写库，避免依赖注入的生命周期问题
                with SessionLocal() as write_db:
                    write_db.add(models.ChatMessage(
                        session_id=session_id, role="assistant", content=full_response))
                    write_db.commit()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲，否则流式会变成一次性返回
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
