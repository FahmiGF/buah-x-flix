from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = "development"
    database_url: str = "postgresql+asyncpg://uvh:uvh@localhost:55432/uvh"
    redis_url: str = "redis://localhost:6379/0"
    cache_url: str = "redis://localhost:6379/1"

    session_secret: str = "dev-only-secret-change-me-32-bytes-min"
    session_cookie: str = "uvh_session"
    session_ttl_days: int = 30
    cookie_secure: bool = False
    cookie_domain: str = ""

    allowed_origins: str = "http://localhost:3000,http://localhost:3001"
    media_root: str = "./media-library"
    user_quota_bytes: int = 20 * 1024**3

    login_rate_limit: int = 10
    login_email_rate_limit: int = 5
    rate_limit_backend: str = "memory"
    log_level: str = "INFO"

    allow_http: bool = True
    max_download_bytes: int = 2 * 1024**3
    analyzer_timeout_seconds: float = 8.0
    analyzer_max_html_bytes: int = 512 * 1024
    analyzer_max_image_bytes: int = 2 * 1024**2
    allow_test_hosts: str = ""

    @property
    def origins(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins.split(",") if item.strip()]

    @property
    def test_hosts(self) -> set[str]:
        return {item.strip() for item in self.allow_test_hosts.split(",") if item.strip()}

    @property
    def media_path(self) -> Path:
        path = Path(self.media_root).expanduser()
        if path.is_absolute():
            return path.resolve()
        # Keep media at the monorepo root regardless of the process cwd.
        return (REPO_ROOT / path).resolve()

    @property
    def cookie_domain_value(self) -> str | None:
        return self.cookie_domain.strip() or None


@lru_cache
def get_settings() -> Settings:
    return Settings()
