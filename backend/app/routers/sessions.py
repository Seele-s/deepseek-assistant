"""会话与消息路由。所有查询都带 user_id 过滤，防止越权访问他人数据。"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_current_user, get_db

router = APIRouter(prefix="/sessions", tags=["会话"])


def get_owned_session(session_id: int, user: models.User, db: Session) -> models.ChatSession:
    """取得会话并校验归属，找不到或不属于当前用户都返回 404。"""
    session = (
        db.query(models.ChatSession)
        .filter(models.ChatSession.id == session_id, models.ChatSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "会话不存在")
    return session


@router.get("", response_model=list[schemas.SessionOut])
def list_sessions(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(models.ChatSession)
        .filter(models.ChatSession.user_id == user.id)
        .order_by(models.ChatSession.id.desc())
        .all()
    )


@router.post("", response_model=schemas.SessionOut, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: schemas.SessionCreate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = models.ChatSession(user_id=user.id, title=payload.title or "新对话")
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.patch("/{session_id}", response_model=schemas.SessionOut)
def rename_session(
    session_id: int,
    payload: schemas.SessionUpdate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = get_owned_session(session_id, user, db)
    session.title = payload.title
    db.commit()
    db.refresh(session)
    return session


@router.delete("/{session_id}")
def delete_session(
    session_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = get_owned_session(session_id, user, db)
    db.delete(session)
    db.commit()
    return {"msg": "会话已删除"}


@router.get("/{session_id}/messages", response_model=list[schemas.MessageOut])
def list_messages(
    session_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_owned_session(session_id, user, db)
    return (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id == session_id)
        .order_by(models.ChatMessage.id)
        .all()
    )
