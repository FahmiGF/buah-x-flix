from conftest import register_user


async def test_analyze_page_extracts_metadata_and_thumbnail(
    client, credentials, allowed_source, media_server
):
    await register_user(client, credentials)
    response = await client.post(
        "/api/v1/analyze", json={"url": f"{media_server}/page"}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["title"] == "Demo Page"
    assert body["kind"] == "video"
    assert body["download"] == {
        "allowed": True,
        "reason": "source_download_allowed",
        "max_bytes": 10 * 1024 * 1024,
    }
    assert body["candidates"][0]["url"].endswith("/clip.mp4")
    assert body["thumbnail_url"]

    thumbnail = await client.get(body["thumbnail_url"])
    assert thumbnail.status_code == 200
    assert thumbnail.headers["content-type"].startswith("image/")


async def test_analyze_direct_image(client, credentials, allowed_source, media_server):
    await register_user(client, credentials)
    response = await client.post(
        "/api/v1/analyze", json={"url": f"{media_server}/image.png"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "image"
    assert body["download"]["allowed"] is True
    assert body["candidates"][0]["mime_type"] == "image/png"


async def test_analyze_blocks_redirect_to_private_network(
    client, credentials, allowed_source, media_server
):
    await register_user(client, credentials)
    response = await client.post(
        "/api/v1/analyze", json={"url": f"{media_server}/redirect-private"}
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "blocked_host"


async def test_analyze_blocks_private_ip_literal(client, credentials):
    await register_user(client, credentials)
    response = await client.post(
        "/api/v1/analyze", json={"url": "http://10.0.0.1/secret"}
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "blocked_host"


async def test_analyze_marks_drm_stream(client, credentials, allowed_source, media_server):
    await register_user(client, credentials)
    response = await client.post(
        "/api/v1/analyze", json={"url": f"{media_server}/stream.m3u8"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "stream"
    assert body["download"]["allowed"] is False
    assert body["download"]["reason"] == "drm_protected"


async def test_analyze_pending_source_cannot_download(
    client, credentials, media_server
):
    await register_user(client, credentials)
    response = await client.post(
        "/api/v1/analyze", json={"url": f"{media_server}/image.png"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["download"]["allowed"] is False
    assert body["download"]["reason"] == "source_pending_review"


async def test_analyze_requires_session(client, media_server):
    response = await client.post(
        "/api/v1/analyze", json={"url": f"{media_server}/page"}
    )
    assert response.status_code == 401
