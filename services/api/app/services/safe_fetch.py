import asyncio
import hashlib
import ipaddress
import mimetypes
import socket
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import httpx

from app.config import get_settings
from app.errors import ApiError

settings = get_settings()
USER_AGENT = "UniversalVideoHub/0.1 (+https://localhost/bot)"
TRACKING_PREFIXES = ("utm_", "fbclid", "gclid", "mc_", "ref_")
MAX_URL_LENGTH = 2048

VIDEO_EXTENSIONS = {".mp4", ".webm", ".mkv", ".mov", ".ogv", ".m4v", ".avi"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif"}
EXTENSION_BY_TYPE = {
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
    "video/ogg": ".ogv",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/avif": ".avif",
    "image/gif": ".gif",
}


class DownloadCancelled(Exception):
    pass


@dataclass
class Fetched:
    url: str
    status_code: int
    headers: dict[str, str]
    content: bytes
    content_type: str


@dataclass
class ProbeResult:
    final_url: str
    content_type: str
    total_bytes: int | None


@dataclass
class DownloadResult:
    final_url: str
    content_type: str
    total_bytes: int
    checksum_sha256: str
    temp_path: Path
    extension: str


def _test_host_allowed(host: str) -> bool:
    return settings.env == "test" and host in settings.test_hosts


def normalize_url(raw: str) -> str:
    value = raw.strip()
    if not value or len(value) > MAX_URL_LENGTH:
        raise ApiError(400, "invalid_url", "URL kosong atau terlalu panjang.")
    if "://" not in value:
        value = f"https://{value}"

    parts = urlsplit(value)
    if parts.scheme not in {"http", "https"}:
        raise ApiError(400, "unsupported_scheme", "Hanya URL http atau https yang didukung.")
    if parts.scheme == "http" and not settings.allow_http:
        raise ApiError(400, "unsupported_scheme", "URL harus memakai https.")
    if parts.username or parts.password:
        raise ApiError(400, "invalid_url", "URL tidak boleh memuat kredensial.")
    if not parts.hostname:
        raise ApiError(400, "invalid_url", "URL tidak memiliki host.")

    try:
        port = parts.port
    except ValueError as exc:
        raise ApiError(400, "invalid_url", "Port pada URL tidak valid.") from exc

    host = parts.hostname.lower().rstrip(".")
    if host in {"localhost", "metadata.google.internal"} and not _test_host_allowed(host):
        raise ApiError(403, "blocked_host", "Host internal tidak diizinkan.")
    if port and port not in {80, 443} and not _test_host_allowed(host):
        raise ApiError(403, "blocked_host", "Hanya port 80 dan 443 yang diizinkan.")

    query = urlencode(
        [
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if not key.lower().startswith(TRACKING_PREFIXES)
        ]
    )
    netloc = parts.netloc.rsplit("@", 1)[-1].lower()
    return urlunsplit((parts.scheme, netloc, parts.path or "/", query, ""))


def _is_public_ip(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


async def resolve_public_ips(host: str) -> list[str]:
    if _test_host_allowed(host):
        return ["127.0.0.1"]

    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None

    if literal is not None:
        if not _is_public_ip(str(literal)):
            raise ApiError(403, "blocked_host", "Alamat IP privat tidak diizinkan.")
        return [str(literal)]

    try:
        infos = await asyncio.to_thread(
            socket.getaddrinfo, host, None, 0, socket.SOCK_STREAM
        )
    except socket.gaierror as exc:
        raise ApiError(422, "fetch_failed", "Host tidak bisa di-resolve.") from exc

    addresses = sorted({info[4][0] for info in infos})
    if not addresses:
        raise ApiError(422, "fetch_failed", "Host tidak memiliki alamat IP.")
    for address in addresses:
        if not _is_public_ip(address):
            raise ApiError(403, "blocked_host", "Host mengarah ke jaringan privat.")
    return addresses


def _content_type(headers: httpx.Headers) -> str:
    return headers.get("content-type", "").split(";")[0].strip().lower()


def extension_for(content_type: str, url: str) -> str:
    if content_type in EXTENSION_BY_TYPE:
        return EXTENSION_BY_TYPE[content_type]
    guessed = mimetypes.guess_extension(content_type or "") or ""
    if guessed in EXTENSION_BY_TYPE.values():
        return guessed
    suffix = Path(urlsplit(url).path).suffix.lower()
    if suffix in VIDEO_EXTENSIONS | IMAGE_EXTENSIONS:
        return suffix
    return ".bin"


async def _open_stream(
    client: httpx.AsyncClient,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    max_redirects: int = 3,
) -> tuple[httpx.Response, httpx.AsyncClient, str]:
    current = normalize_url(url)
    for _ in range(max_redirects + 1):
        host = urlsplit(current).hostname or ""
        await resolve_public_ips(host)
        request = client.build_request("GET", current, headers=headers)
        response = await client.send(request, stream=True)
        if response.is_redirect:
            location = response.headers.get("location")
            await response.aclose()
            if not location:
                raise ApiError(422, "fetch_failed", "Sumber mengirim redirect tanpa lokasi.")
            current = normalize_url(urljoin(current, location))
            continue
        return response, client, current
    raise ApiError(422, "too_many_redirects", "Terlalu banyak redirect.")


async def fetch_limited(url: str, max_bytes: int | None = None) -> Fetched:
    limit = max_bytes or settings.analyzer_max_html_bytes
    timeout_value = settings.analyzer_timeout_seconds
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(timeout_value, connect=4.0),
        follow_redirects=False,
        headers=headers,
        trust_env=False,
    ) as client:
        while True:
            response, _, current = await _open_stream(client, url)
            try:
                if response.status_code >= 400:
                    raise ApiError(
                        422,
                        "fetch_failed",
                        f"Sumber membalas HTTP {response.status_code}.",
                    )
                data = bytearray()
                async for chunk in response.aiter_bytes():
                    data.extend(chunk)
                    if len(data) > limit:
                        raise ApiError(413, "too_large", "Konten melebihi batas analisis.")
                return Fetched(
                    url=str(response.url),
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    content=bytes(data),
                    content_type=_content_type(response.headers),
                )
            finally:
                await response.aclose()


async def probe_media(url: str) -> ProbeResult:
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(settings.analyzer_timeout_seconds, connect=4.0),
        follow_redirects=False,
        headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
        trust_env=False,
    ) as client:
        while True:
            response, _, current = await _open_stream(
                client, url, headers={"User-Agent": USER_AGENT, "Range": "bytes=0-0"}
            )
            try:
                if response.status_code >= 400:
                    raise ApiError(
                        422,
                        "fetch_failed",
                        f"Sumber membalas HTTP {response.status_code}.",
                    )
                total: int | None = None
                content_range = response.headers.get("content-range", "")
                if "/" in content_range:
                    try:
                        total = int(content_range.rsplit("/", 1)[1])
                    except ValueError:
                        total = None
                if total is None:
                    length = response.headers.get("content-length")
                    if length and length.isdigit():
                        total = int(length)
                return ProbeResult(
                    final_url=str(response.url),
                    content_type=_content_type(response.headers),
                    total_bytes=total,
                )
            finally:
                await response.aclose()


async def _hash_file(path: Path) -> str:
    def _hash() -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    return await asyncio.to_thread(_hash)


async def download_to_temp(
    url: str,
    dest: Path,
    *,
    max_bytes: int,
    on_progress: Callable[[int, int | None], Awaitable[None]] | None = None,
    should_cancel: Callable[[], bool] | None = None,
    retries: int = 2,
) -> DownloadResult:
    dest.parent.mkdir(parents=True, exist_ok=True)
    attempt = 0
    last_error: Exception | None = None

    while attempt <= retries:
        try:
            return await _download_attempt(
                url,
                dest,
                max_bytes=max_bytes,
                on_progress=on_progress,
                should_cancel=should_cancel,
            )
        except DownloadCancelled:
            raise
        except (httpx.HTTPError, OSError) as exc:
            last_error = exc
            attempt += 1
            if attempt > retries:
                break
            await asyncio.sleep(attempt)

    raise ApiError(502, "download_failed", f"Unduhan gagal: {last_error}")


async def _download_attempt(
    url: str,
    dest: Path,
    *,
    max_bytes: int,
    on_progress: Callable[[int, int | None], Awaitable[None]] | None,
    should_cancel: Callable[[], bool] | None,
) -> DownloadResult:
    headers = {"User-Agent": USER_AGENT}
    def _existing_size() -> int:
        return dest.stat().st_size if dest.exists() else 0

    resume_at = await asyncio.to_thread(_existing_size)
    if resume_at:
        headers["Range"] = f"bytes={resume_at}-"

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(30.0, connect=5.0),
        follow_redirects=False,
        headers=headers,
        trust_env=False,
    ) as client:
        response, _, current = await _open_stream(client, url, headers=headers)
        try:
            if response.status_code >= 400:
                raise ApiError(
                    422,
                    "fetch_failed",
                    f"Sumber membalas HTTP {response.status_code}.",
                )

            if response.status_code == 200:
                resume_at = 0

            length_header = response.headers.get("content-length")
            remaining = int(length_header) if length_header and length_header.isdigit() else None
            total = (resume_at + remaining) if remaining is not None else None
            if total is not None and total > max_bytes:
                raise ApiError(413, "too_large", "File melebihi batas unduhan.")

            digest = hashlib.sha256()
            if resume_at:
                existing_digest = await _hash_file(dest)
                digest = hashlib.sha256()
                with dest.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
                _ = existing_digest

            done = resume_at
            last_report = 0.0
            mode = "ab" if resume_at else "wb"
            with dest.open(mode) as handle:
                async for chunk in response.aiter_bytes(chunk_size=256 * 1024):
                    if should_cancel and should_cancel():
                        raise DownloadCancelled()
                    handle.write(chunk)
                    digest.update(chunk)
                    done += len(chunk)
                    if done > max_bytes:
                        raise ApiError(413, "too_large", "File melebihi batas unduhan.")
                    now = time.monotonic()
                    if on_progress and (now - last_report >= 1.0 or done == total):
                        await on_progress(done, total)
                        last_report = now

            if on_progress:
                await on_progress(done, total)

            content_type = _content_type(response.headers)
            return DownloadResult(
                final_url=str(response.url),
                content_type=content_type,
                total_bytes=done,
                checksum_sha256=digest.hexdigest(),
                temp_path=dest,
                extension=extension_for(content_type, current),
            )
        finally:
            await response.aclose()
