"""接口自动化测试：健康检查、鉴权、会话隔离、越权防护。"""
import os
import tempfile
import uuid
from pathlib import Path

# 必须在导入 app 之前设置环境变量，让应用指向独立的测试数据库
TEST_DB = Path(tempfile.gettempdir()) / ("test_chat_" + uuid.uuid4().hex + ".db")
os.environ["DATABASE_URL"] = "sqlite:///" + TEST_DB.as_posix()
os.environ.setdefault("DEEPSEEK_API_KEY", "test-key-not-used")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _register_and_login(username: str):
    client.post("/api/register", json={"username": username, "password": "test123456"})
    res = client.post("/api/token", data={"username": username, "password": "test123456"})
    assert res.status_code == 200, res.text
    return {"Authorization": "Bearer " + res.json()["access_token"]}


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_register_and_login():
    username = "u_" + uuid.uuid4().hex[:8]
    headers = _register_and_login(username)
    res = client.get("/api/me", headers=headers)
    assert res.status_code == 200
    assert res.json()["username"] == username


def test_duplicate_username_rejected():
    username = "dup_" + uuid.uuid4().hex[:8]
    _register_and_login(username)
    res = client.post("/api/register", json={"username": username, "password": "test123456"})
    assert res.status_code == 409


def test_weak_password_rejected():
    res = client.post("/api/register", json={"username": "short_" + uuid.uuid4().hex[:6], "password": "123"})
    assert res.status_code == 422


def test_requires_auth():
    assert client.get("/api/sessions").status_code == 401
    assert client.get("/api/sessions", headers={"Authorization": "Bearer bad.token.here"}).status_code == 401


def test_session_crud():
    headers = _register_and_login("sess_" + uuid.uuid4().hex[:8])
    created = client.post("/api/sessions", json={"title": "测试会话"}, headers=headers)
    assert created.status_code == 201
    sid = created.json()["id"]

    listing = client.get("/api/sessions", headers=headers)
    assert any(s["id"] == sid for s in listing.json())

    renamed = client.patch("/api/sessions/" + str(sid), json={"title": "改个名"}, headers=headers)
    assert renamed.json()["title"] == "改个名"

    assert client.delete("/api/sessions/" + str(sid), headers=headers).status_code == 200
    assert client.get("/api/sessions/" + str(sid) + "/messages", headers=headers).status_code == 404


def test_user_cannot_access_others_session():
    """越权防护：A 不能读/删 B 的会话。"""
    headers_a = _register_and_login("a_" + uuid.uuid4().hex[:8])
    headers_b = _register_and_login("b_" + uuid.uuid4().hex[:8])

    sid = client.post("/api/sessions", json={"title": "B的会话"}, headers=headers_b).json()["id"]

    assert client.get("/api/sessions/" + str(sid) + "/messages", headers=headers_a).status_code == 404
    assert client.delete("/api/sessions/" + str(sid), headers=headers_a).status_code == 404


def test_upload_rejects_unsupported_type():
    headers = _register_and_login("up_" + uuid.uuid4().hex[:8])
    res = client.post(
        "/api/upload",
        files={"file": ("evil.exe", b"MZ...", "application/octet-stream")},
        headers=headers,
    )
    assert res.status_code == 400


def test_upload_accepts_text_file():
    headers = _register_and_login("upt_" + uuid.uuid4().hex[:8])
    res = client.post(
        "/api/upload",
        files={"file": ("hello.py", b"print(1)", "text/x-python")},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["local_path"].endswith(".py")


def test_context_builder_limits_history():
    """上下文裁剪：不应超过配置的消息条数。"""
    from app.services.context import build_context

    history = [{"role": "user", "content": "x" * 100} for _ in range(100)]
    messages = build_context(history, "本轮问题")
    assert messages[0]["role"] == "system"
    assert messages[-1]["content"] == "本轮问题"
    assert len(messages) <= 22
