import asyncio

from conftest import register_user


async def wait_for_job(client, job_id: str, max_wait: float = 15.0) -> dict:
    deadline = asyncio.get_running_loop().time() + max_wait
    last = {}
    while asyncio.get_running_loop().time() < deadline:
        response = await client.get(f"/api/v1/downloads/{job_id}")
        assert response.status_code == 200
        last = response.json()
        if last["state"] in {"completed", "failed", "cancelled", "blocked"}:
            return last
        await asyncio.sleep(0.1)
    raise AssertionError(f"job tidak selesai: {last}")


async def test_download_appears_in_library_with_range_stream(
    client, credentials, allowed_source, media_server
):
    await register_user(client, credentials)
    response = await client.post(
        "/api/v1/downloads", json={"url": f"{media_server}/image.png"}
    )
    assert response.status_code == 202, response.text
    job = await wait_for_job(client, response.json()["id"])
    assert job["state"] == "completed", job
    assert job["progress"] == 100

    media_id = job["media_id"]
    detail = await client.get(f"/api/v1/media/{media_id}")
    assert detail.status_code == 200
    media = detail.json()
    assert media["kind"] == "image"
    assert media["width"] == 32
    assert media["thumbnail_url"]
    assert (await client.get(media["thumbnail_url"])).status_code == 200

    ranged = await client.get(
        f"/api/v1/media/{media_id}/stream", headers={"Range": "bytes=0-3"}
    )
    assert ranged.status_code == 206
    assert ranged.headers["content-range"].startswith("bytes 0-3/")
    assert ranged.content[:4] == b"\x89PNG"

    duplicate = await client.post(
        "/api/v1/downloads", json={"url": f"{media_server}/image.png"}
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "conflict_duplicate"


async def test_download_rejects_unapproved_source(client, credentials, media_server):
    await register_user(client, credentials)
    response = await client.post(
        "/api/v1/downloads", json={"url": f"{media_server}/image.png"}
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "source_pending_review"


async def test_upload_image_creates_thumbnail(client, credentials, png_bytes):
    await register_user(client, credentials)
    response = await client.post(
        "/api/v1/media/upload",
        files={"file": ("sample.png", png_bytes(), "image/png")},
        data={"title": "Sample Upload", "category": "Teknologi"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["title"] == "Sample Upload"
    assert body["kind"] == "image"
    assert body["thumbnail_url"]
    assert (await client.get(body["thumbnail_url"])).status_code == 200

    duplicate = await client.post(
        "/api/v1/media/upload",
        files={"file": ("sample.png", png_bytes(), "image/png")},
    )
    assert duplicate.status_code == 409


async def test_upload_rejects_unknown_format(client, credentials):
    await register_user(client, credentials)
    response = await client.post(
        "/api/v1/media/upload",
        files={"file": ("malware.exe", b"MZ\x90\x00payload", "application/octet-stream")},
    )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_media"


async def test_media_is_scoped_to_owner(client, credentials, png_bytes):
    await register_user(client, credentials)
    upload = await client.post(
        "/api/v1/media/upload",
        files={"file": ("mine.png", png_bytes(), "image/png")},
    )
    media_id = upload.json()["id"]

    await client.post("/api/v1/auth/logout")
    other = {
        "email": "other@example.com",
        "password": "password-lain-2026",
        "display_name": "Other",
    }
    assert (await register_user(client, other)).status_code == 201

    assert (await client.get(f"/api/v1/media/{media_id}")).status_code == 404
    assert (await client.get(f"/api/v1/media/{media_id}/stream")).status_code == 404
    assert (
        await client.get(f"/api/v1/media/{media_id}/thumbnail")
    ).status_code == 404
    assert (
        await client.put(f"/api/v1/favorites/{media_id}")
    ).status_code == 404


async def test_media_filters_and_patch(client, credentials, png_bytes):
    await register_user(client, credentials)
    upload = await client.post(
        "/api/v1/media/upload",
        files={"file": ("filter.png", png_bytes((10, 200, 90)), "image/png")},
    )
    media_id = upload.json()["id"]

    search = await client.get("/api/v1/media", params={"q": "filter"})
    assert search.status_code == 200
    assert search.json()["total"] >= 1

    missing = await client.get("/api/v1/media", params={"q": "tidak-ada"})
    assert missing.json()["total"] == 0

    patched = await client.patch(
        f"/api/v1/media/{media_id}", json={"title": "Judul Baru", "category": "Travel"}
    )
    assert patched.status_code == 200
    assert patched.json()["title"] == "Judul Baru"
    assert patched.json()["category"] == "Travel"

    deleted = await client.delete(f"/api/v1/media/{media_id}")
    assert deleted.status_code == 200
    assert (await client.get(f"/api/v1/media/{media_id}")).status_code == 404
