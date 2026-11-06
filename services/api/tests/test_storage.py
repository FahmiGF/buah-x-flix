import pytest

from app.services.quota import QuotaExceeded, ensure_quota
from app.services.storage import InvalidStorageKey, LocalStorage


@pytest.fixture
def storage(tmp_path):
    return LocalStorage(tmp_path / "library")


def test_roundtrip_and_delete(storage):
    storage.save_bytes("u_demo/videos/2026/11/item/original.mp4", b"hello")
    assert storage.exists("u_demo/videos/2026/11/item/original.mp4")
    assert storage.read_bytes("u_demo/videos/2026/11/item/original.mp4") == b"hello"
    assert storage.size("u_demo/videos/2026/11/item/original.mp4") == 5
    storage.delete("u_demo/videos/2026/11/item/original.mp4")
    assert not storage.exists("u_demo/videos/2026/11/item/original.mp4")
    storage.delete("u_demo/videos/2026/11/item/original.mp4")


@pytest.mark.parametrize(
    "key",
    [
        "../outside.txt",
        "a/../../outside.txt",
        "/etc/passwd",
        "C:/Windows/win.ini",
        "a\\..\\b.txt",
        "",
        ".",
        "a/\x00b",
    ],
)
def test_keys_cannot_escape_root(storage, key):
    with pytest.raises(InvalidStorageKey):
        storage.save_bytes(key, b"nope")


def test_ready_creates_root(storage):
    assert storage.ready()
    assert storage.root.is_dir()


def test_quota_boundary():
    ensure_quota(used=9, incoming=1, limit=10)
    with pytest.raises(QuotaExceeded):
        ensure_quota(used=9, incoming=2, limit=10)
    with pytest.raises(ValueError):
        ensure_quota(used=0, incoming=-1, limit=10)
