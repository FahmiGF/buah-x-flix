import os
import subprocess
import sys
from pathlib import Path

os.environ["ENV"] = "test"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://uvh:uvh@localhost:55432/uvh_test"
os.environ["MEDIA_ROOT"] = str(Path(__file__).parent / ".media")
os.environ["RATE_LIMIT_BACKEND"] = "memory"
os.environ["COOKIE_SECURE"] = "false"
os.environ["ALLOW_HTTP"] = "true"
os.environ["ALLOW_TEST_HOSTS"] = "127.0.0.1"
os.environ.pop("COOKIE_DOMAIN", None)

import shutil  # noqa: E402
import threading  # noqa: E402
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # noqa: E402
from io import BytesIO  # noqa: E402

import httpx  # noqa: E402
import psycopg  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from PIL import Image  # noqa: E402
from sqlalchemy import text  # noqa: E402

API_DIR = Path(__file__).resolve().parents[1]
ADMIN_DSN = "postgresql://uvh:uvh@localhost:55432/postgres"
MEDIA_DIR = Path(os.environ["MEDIA_ROOT"])
shutil.rmtree(MEDIA_DIR, ignore_errors=True)

with psycopg.connect(ADMIN_DSN, autocommit=True) as admin:
    admin.execute("drop database if exists uvh_test with (force)")
    admin.execute("create database uvh_test")

subprocess.run(
    [sys.executable, "-m", "alembic", "upgrade", "head"],
    cwd=API_DIR,
    check=True,
    env=os.environ.copy(),
)

from app.db import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Source, SourcePolicy  # noqa: E402
from app.services.auth import login_email_limiter, login_ip_limiter  # noqa: E402

TRUNCATE = """
truncate table audit_log, recommendations, media_item_tags, tags, favorites,
watch_history, collection_items, collections, download_jobs, media_files,
media_items, sources, sessions, users restart identity cascade
"""


@pytest_asyncio.fixture(autouse=True)
async def clean_state():
    login_ip_limiter.reset()
    login_email_limiter.reset()
    async with engine.begin() as conn:
        await conn.execute(text(TRUNCATE))
    yield


@pytest_asyncio.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client


@pytest.fixture
def credentials():
    return {
        "email": "fahmi@example.com",
        "password": "rahasia-sekali-2026",
        "display_name": "Fahmi",
    }


async def register_user(client: httpx.AsyncClient, credentials: dict[str, str]) -> httpx.Response:
    return await client.post("/api/v1/auth/register", json=credentials)


async def login_user(client: httpx.AsyncClient, credentials: dict[str, str]) -> httpx.Response:
    return await client.post(
        "/api/v1/auth/login",
        json={"email": credentials["email"], "password": credentials["password"]},
    )


@pytest.fixture
def png_bytes():
    def make(color: tuple[int, int, int] = (230, 80, 60), size=(32, 24)) -> bytes:
        buffer = BytesIO()
        Image.new("RGB", size, color).save(buffer, "PNG")
        return buffer.getvalue()

    return make


@pytest.fixture
def media_server(png_bytes):
    image = png_bytes()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            return

        def _send(self, status, body: bytes, content_type: str, extra=None):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            for key, value in (extra or {}).items():
                self.send_header(key, value)
            self.end_headers()
            if body and self.command != "HEAD":
                self.wfile.write(body)

        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            port = self.server.server_port
            if self.path == "/page":
                html = f"""<!doctype html><html><head>
                <title>Fallback title</title>
                <meta property="og:title" content="Demo Page">
                <meta property="og:description" content="A tech documentary about code">
                <meta property="og:image" content="http://127.0.0.1:{port}/image.png">
                <meta property="og:video" content="http://127.0.0.1:{port}/clip.mp4">
                </head><body><video src="/clip.mp4"></video></body></html>"""
                self._send(200, html.encode(), "text/html; charset=utf-8")
            elif self.path == "/image.png":
                self._send(200, image, "image/png")
            elif self.path == "/clip.mp4":
                self._send(200, b"\x00\x00\x00\x18ftypmp42" + b"0" * 1024, "video/mp4")
            elif self.path == "/stream.m3u8":
                body = (
                    "#EXTM3U\n#EXT-X-KEY:METHOD=SAMPLE-AES,URI=\"key.bin\"\n"
                    "#EXT-X-TARGETDURATION:4\n#EXTINF:4,\nsegment.ts\n"
                )
                self._send(200, body.encode(), "application/vnd.apple.mpegurl")
            elif self.path == "/redirect-private":
                self.send_response(302)
                self.send_header("Location", "http://169.254.169.254/latest/meta-data/")
                self.end_headers()
            else:
                self._send(404, b"not found", "text/plain")

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    thread.join(timeout=2)


@pytest_asyncio.fixture
async def allowed_source():
    async with SessionLocal() as db:
        db.add(
            Source(
                host="127.0.0.1",
                display_name="Local test source",
                policy=SourcePolicy.download_allowed,
                include_subdomains=False,
                max_file_bytes=10 * 1024 * 1024,
            )
        )
        await db.commit()
