from conftest import register_user


async def _upload(client, name: str, color: tuple[int, int, int], png_bytes):
    response = await client.post(
        "/api/v1/media/upload",
        files={"file": (name, png_bytes(color), "image/png")},
        data={"title": name.replace(".png", "").title(), "category": "Teknologi"},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_favorites_are_idempotent(client, credentials, png_bytes):
    await register_user(client, credentials)
    media = await _upload(client, "favorite.png", (200, 30, 30), png_bytes)

    assert (await client.put(f"/api/v1/favorites/{media['id']}")).status_code == 200
    assert (await client.put(f"/api/v1/favorites/{media['id']}")).status_code == 200

    favorites = await client.get("/api/v1/favorites")
    assert favorites.status_code == 200
    assert [item["id"] for item in favorites.json()] == [media["id"]]

    assert (await client.delete(f"/api/v1/favorites/{media['id']}")).status_code == 200
    assert (await client.get("/api/v1/favorites")).json() == []


async def test_watch_history_and_continue_watching(client, credentials, png_bytes):
    await register_user(client, credentials)
    media = await _upload(client, "progress.png", (40, 90, 200), png_bytes)

    response = await client.post(
        "/api/v1/watch-history",
        json={"media_id": media["id"], "position_seconds": 10, "duration_seconds": 100},
    )
    assert response.status_code == 200
    assert response.json()["completed"] is False

    continue_watching = await client.get("/api/v1/library/continue")
    assert continue_watching.status_code == 200
    assert continue_watching.json()[0]["id"] == media["id"]
    assert continue_watching.json()[0]["progress"]["position_seconds"] == 10

    finished = await client.post(
        "/api/v1/watch-history",
        json={"media_id": media["id"], "position_seconds": 99, "duration_seconds": 100},
    )
    assert finished.json()["completed"] is True
    assert (await client.get("/api/v1/library/continue")).json() == []


async def test_collections_crud(client, credentials, png_bytes):
    await register_user(client, credentials)
    media = await _upload(client, "collect.png", (90, 200, 40), png_bytes)

    created = await client.post(
        "/api/v1/collections",
        json={"title": "Open Movies", "description": "Koleksi uji"},
    )
    assert created.status_code == 201, created.text
    collection = created.json()
    assert collection["slug"] == "open-movies"

    added = await client.post(
        f"/api/v1/collections/{collection['id']}/items",
        json={"media_id": media["id"]},
    )
    assert added.status_code == 201

    detail = await client.get(f"/api/v1/collections/{collection['id']}")
    assert detail.status_code == 200
    assert detail.json()["item_count"] == 1
    assert detail.json()["items"][0]["id"] == media["id"]

    filtered = await client.get(
        "/api/v1/media", params={"collection": collection["id"]}
    )
    assert filtered.json()["total"] == 1

    assert (
        await client.delete(
            f"/api/v1/collections/{collection['id']}/items/{media['id']}"
        )
    ).status_code == 200
    empty = await client.get(f"/api/v1/collections/{collection['id']}")
    assert empty.json()["item_count"] == 0


async def test_recommendations_skip_watched_and_explain(client, credentials, png_bytes):
    await register_user(client, credentials)
    first = await _upload(client, "watched.png", (120, 40, 160), png_bytes)
    second = await _upload(client, "next.png", (40, 160, 120), png_bytes)

    await client.post(
        "/api/v1/watch-history",
        json={"media_id": first["id"], "position_seconds": 5, "duration_seconds": 100},
    )
    response = await client.get("/api/v1/recommendations")
    assert response.status_code == 200
    items = response.json()
    assert items, items
    assert all(item["media_id"] != first["id"] for item in items)
    assert any(item["media_id"] == second["id"] for item in items)
    assert items[0]["reason"] in {"same_category", "recently_added"}
    assert items[0]["thumbnail_url"]
