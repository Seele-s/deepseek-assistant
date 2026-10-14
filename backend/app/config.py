"""集中配置模块。

所有可调参数统一从环境变量（backend/.env）读取，杜绝硬编码。
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent  # -> backend/
load_dotenv(BASE_DIR / ".env")


def _split(value: str) -> list:
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings:
    """应用配置。部署时请务必用 .env 覆盖 SECRET_KEY / DEEPSEEK_API_KEY。"""

    def __init__(self) -> None:
        self.app_name = os.getenv("APP_NAME", "DeepSeek 智能问答助手")
        self.version = "2.0.0"
        self.api_prefix = "/api"
        self.debug = os.getenv("DEBUG", "true").lower() == "true"

        # ---- 数据库：默认 SQLite；改 MySQL 只需覆盖 DATABASE_URL ----
        default_db = "sqlite:///" + (BASE_DIR / "chat.db").as_posix()
        self.database_url = os.getenv("DATABASE_URL", default_db)

        # ---- 鉴权 ----
        self.secret_key = os.getenv("SECRET_KEY", "dev-only-secret-please-change")
        self.algorithm = os.getenv("ALGORITHM", "HS256")
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

        # ---- DeepSeek ----
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.chat_model = os.getenv("CHAT_MODEL", "deepseek-chat")
        self.reasoner_model = os.getenv("REASONER_MODEL", "deepseek-reasoner")
        self.temperature = float(os.getenv("TEMPERATURE", "1.0"))

        # ---- 上下文窗口 ----
        self.max_context_messages = int(os.getenv("MAX_CONTEXT_MESSAGES", "20"))
        self.max_context_chars = int(os.getenv("MAX_CONTEXT_CHARS", "24000"))
        self.max_inline_file_chars = int(os.getenv("MAX_INLINE_FILE_CHARS", "100000"))

        # ---- 上传 ----
        self.upload_dir = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads")))
        self.max_upload_mb = int(os.getenv("MAX_UPLOAD_MB", "20"))
        self.allowed_upload_exts = {
            ".txt", ".md", ".markdown", ".py", ".js", ".ts", ".json", ".csv", ".log",
            ".html", ".css", ".vue", ".java", ".c", ".h", ".cpp", ".go", ".sql",
            ".yaml", ".yml", ".xml", ".ini", ".conf", ".sh",
        }

        # ---- CORS ----
        self.cors_origins = _split(os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000",
        ))

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


settings = Settings()
