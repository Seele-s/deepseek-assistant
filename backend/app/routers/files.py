"""文件上传路由：带类型白名单与大小限制。"""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from .. import models
from ..config import settings
from ..deps import get_current_user

router = APIRouter(tags=["文件"])


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    user: models.User = Depends(get_current_user),
):
    original_name = file.filename or "unnamed"
    ext = Path(original_name).suffix.lower()
    if ext not in settings.allowed_upload_exts:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "不支持的文件类型：" + (ext or "无扩展名") + "（仅支持文本/代码类文件）",
        )

    content = await file.read()
    limit = settings.max_upload_mb * 1024 * 1024
    if len(content) > limit:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "文件超过 " + str(settings.max_upload_mb) + "MB 限制",
        )

    # 用 UUID 重命名，避免中文名/重名/路径注入问题
    stored_name = uuid.uuid4().hex + ext
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    (settings.upload_dir / stored_name).write_bytes(content)

    return {
        "url": settings.api_prefix + "/files/" + stored_name,
        "filename": original_name,
        "local_path": stored_name,
        "size": len(content),
    }
