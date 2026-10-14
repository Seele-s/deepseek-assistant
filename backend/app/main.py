"""应用入口：装配路由、中间件，并可选托管前端打包产物。"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import models  # noqa: F401  导入以确保建表时模型已注册
from .config import settings
from .database import Base, engine
from .routers import auth, chat, files, sessions

# 启动即建表（生产环境建议改用 Alembic 迁移）
Base.metadata.create_all(bind=engine)
settings.upload_dir.mkdir(parents=True, exist_ok=True)

app = FastAPI(title=settings.app_name, version=settings.version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # 不再使用 "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = settings.api_prefix
app.include_router(auth.router, prefix=api)
app.include_router(sessions.router, prefix=api)
app.include_router(chat.router, prefix=api)
app.include_router(files.router, prefix=api)

# 上传文件的只读访问
app.mount(api + "/files", StaticFiles(directory=settings.upload_dir), name="files")


@app.get(api + "/health", tags=["系统"])
def health():
    return {
        "status": "ok",
        "version": settings.version,
        "database": "sqlite" if settings.is_sqlite else "mysql/other",
        "chat_model": settings.chat_model,
        "reasoner_model": settings.reasoner_model,
        "api_key_configured": bool(settings.deepseek_api_key),
    }


# ---- 单端口部署：若前端已构建出 dist，则由后端一并托管，无需再开 5173 ----
DIST_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if DIST_DIR.is_dir():
    assets_dir = DIST_DIR / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        """前端使用 history 路由，刷新子路径时需要回退到 index.html。"""
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = DIST_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(DIST_DIR / "index.html")
