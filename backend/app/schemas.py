"""请求/响应模型（Pydantic），负责入参校验与出参裁剪。"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SessionCreate(BaseModel):
    title: str = Field(default="新对话", max_length=255)


class SessionUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    created_at: Optional[datetime] = None


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    role: str
    content: str
    created_at: Optional[datetime] = None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: int
    is_reasoning: bool = False
    file_path: Optional[str] = None


class UploadOut(BaseModel):
    url: str
    filename: str
    local_path: str
    size: int
