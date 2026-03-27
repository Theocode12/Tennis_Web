import os
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_music_service, get_redis_client
from main import app

TEST_SECRET = "test-secret-123"


@pytest.fixture(autouse=True, scope="session")
def _set_api_secret():
    """Set API_SECRET for the entire test session."""
    with patch.dict(os.environ, {"API_SECRET": TEST_SECRET}):
        yield


@pytest.fixture(autouse=True)
def override_redis(redis_client):
    """Override the redis_client dependency for all API tests."""
    app.dependency_overrides[get_redis_client] = lambda: redis_client
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


def _secret_param() -> str:
    return f"?secret={TEST_SECRET}"


# ── Public routes (no secret needed) ────────────────────────────────────


@pytest.mark.redis
@pytest.mark.asyncio
async def test_list_playlists_empty(async_client, redis_client):
    """Test GET /api/v1/music/playlists when no playlists are registered."""
    response = await async_client.get("/api/v1/music/playlists")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.redis
@pytest.mark.asyncio
async def test_list_playlists_with_data(mock_media_env, async_client, redis_client):
    """Test GET /api/v1/music/playlists with registered data."""
    service = get_music_service()
    store_data = service.file_store.load_store()

    await service.register_all(songs=store_data.get("songs", []), playlists=store_data.get("playlists", []))

    response = await async_client.get("/api/v1/music/playlists")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == mock_media_env["playlist_id"]


@pytest.mark.redis
@pytest.mark.asyncio
async def test_get_playlist_details(mock_media_env, async_client, redis_client):
    """Test GET /api/v1/music/playlist/{id}."""
    service = get_music_service()
    store_data = service.file_store.load_store()

    await service.register_all(songs=store_data.get("songs", []), playlists=store_data.get("playlists", []))

    playlist_id = mock_media_env["playlist_id"]
    response = await async_client.get(f"/api/v1/music/playlist/{playlist_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == mock_media_env["song_id"]
    assert "stream_url" in data[0]


@pytest.mark.asyncio
async def test_get_playlist_not_found(async_client):
    """Test GET /api/v1/music/playlist/{id} for non-existent playlist."""
    response = await async_client.get("/api/v1/music/playlist/ghost_playlist")
    assert response.status_code == 404
    assert response.json() == {"detail": "Playlist not found"}


# ── Protected routes (secret required) ──────────────────────────────────


@pytest.mark.redis
@pytest.mark.asyncio
async def test_list_registered_songs(mock_media_env, async_client, redis_client):
    """Test GET /api/v1/music/songs."""
    service = get_music_service()
    store_data = service.file_store.load_store()

    await service.register_all(songs=store_data.get("songs", []), playlists=[])

    response = await async_client.get(f"/api/v1/music/songs{_secret_param()}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == mock_media_env["song_id"]


@pytest.mark.redis
@pytest.mark.asyncio
async def test_scan_media_folder(mock_media_env, async_client):
    """Test GET /api/v1/music/media-folder."""
    response = await async_client.get(f"/api/v1/music/media-folder{_secret_param()}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == mock_media_env["song_id"]
    assert data[0]["hls_available"] is True


@pytest.mark.redis
@pytest.mark.asyncio
async def test_ingest_song_endpoint(async_client, redis_client):
    """Test POST /api/v1/music/ingest."""
    with patch("app.api.v1.media.process_song_task.delay") as mock_delay:
        files = {"file": ("test.mp3", b"data", "audio/mpeg")}
        data = {"title": "New", "artist": "Artist"}

        response = await async_client.post(f"/api/v1/music/ingest{_secret_param()}", data=data, files=files)

        assert response.status_code == 200
        result = response.json()
        assert "job_id" in result
        assert mock_delay.called


@pytest.mark.redis
@pytest.mark.asyncio
async def test_get_ingest_status(async_client, redis_client):
    """Test GET /api/v1/music/ingest/{job_id}."""
    from app.infra.job_store_async import create_job

    job_id = "test_job"
    await create_job(redis_client, job_id)

    response = await async_client.get(f"/api/v1/music/ingest/{job_id}{_secret_param()}")
    assert response.status_code == 200
    assert response.json()["status"] == "processing"


@pytest.mark.redis
@pytest.mark.asyncio
async def test_register_song_endpoint(mock_media_env, async_client, redis_client):
    """Test POST /api/v1/music/register/{song_id}."""
    song_id = mock_media_env["song_id"]
    response = await async_client.post(f"/api/v1/music/register/{song_id}{_secret_param()}")
    assert response.status_code == 200
    assert response.json()["status"] == "registered"


@pytest.mark.redis
@pytest.mark.asyncio
async def test_make_playlist_endpoint(async_client, redis_client):
    """Test POST /api/v1/music/playlist."""
    response = await async_client.post(f"/api/v1/music/playlist{_secret_param()}", data={"name": "New P"})
    assert response.status_code == 200
    assert "playlist_id" in response.json()


@pytest.mark.redis
@pytest.mark.asyncio
async def test_insert_song_to_playlist_endpoint(mock_media_env, async_client, redis_client):
    """Test POST /api/v1/music/playlist/{pid}/add/{sid}."""
    pid = mock_media_env["playlist_id"]
    sid = mock_media_env["song_id"]

    # Register first
    await async_client.post(f"/api/v1/music/register/{sid}{_secret_param()}")

    response = await async_client.post(f"/api/v1/music/playlist/{pid}/add/{sid}{_secret_param()}")
    assert response.status_code == 200
    assert response.json()["status"] == "added"


# ── Secret validation ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_protected_route_without_secret_returns_404(async_client):
    """Calling a protected route without ?secret returns 404."""
    response = await async_client.get("/api/v1/music/songs")
    assert response.status_code == 404
    assert response.json()["detail"] == "Not found"


@pytest.mark.asyncio
async def test_protected_route_with_wrong_secret_returns_404(async_client):
    """Calling a protected route with wrong ?secret returns 404."""
    response = await async_client.get("/api/v1/music/songs?secret=wrong")
    assert response.status_code == 404
    assert response.json()["detail"] == "Not found"


@pytest.mark.asyncio
async def test_protected_route_with_correct_secret(async_client):
    """Calling a protected route with correct ?secret succeeds."""
    response = await async_client.get(f"/api/v1/music/songs{_secret_param()}")
    assert response.status_code == 200
