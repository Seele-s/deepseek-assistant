"""公共依赖：数据库会话与当前登录用户。

注意：网关（Nginx Basic Auth）占用了标准的 Authorization 请求头，
因此应用的 JWT 走自定义请求头 X-Auth-Token，两者互不干扰。
为了兼容 Swagger 调试，也同时接受标准的 Authorization: Bearer。
"""
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from . import models
from .config import settings
from .database import SessionLocal
from .security import decode_access_token

# auto_error=False：没有 Authorization 头时不直接报错，交给下面的逻辑统一处理
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=settings.api_prefix + "/token", auto_error=False
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _strip_bearer(raw: str) -> str:
    raw = raw.strip()
    if raw.lower().startswith("bearer "):
        return raw[7:].strip()
    return raw


def get_current_user(
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
    bearer_token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    raw = x_auth_token or bearer_token
    if not raw:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "未登录",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = decode_access_token(_strip_bearer(raw))
    if not username:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "登录状态已失效，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户不存在")
    return user
