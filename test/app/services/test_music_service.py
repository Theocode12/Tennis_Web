import pytest

from app.dependencies import get_music_service


@pytest.mark.redis
@pytest.mark.asyncio
async def test_register_songs_success(mock_media_env, redis_client):
    """Test that songs are registered correctly when HLS files exist."""
    service = get_music_service()
    store_data = service.file_store.load_store()
    songs_list = store_data.get("songs", [])

    await service.register_all(songs=songs_list, playlists=[])

    registered = await service.get_all_songs()
    assert len(registered) == 1
    assert registered[0].id == mock_media_env["song_id"]
    assert registered[0].title == "Test Song Title"


@pytest.mark.redis
@pytest.mark.asyncio
async def test_register_playlists_success(mock_media_env, redis_client):
    """Test that playlists are registered with valid songs."""
    service = get_music_service()
    store_data = service.file_store.load_store()
    songs_list = store_data.get("songs", [])
    playlists_list = store_data.get("playlists", [])

    await service.register_all(songs=songs_list, playlists=playlists_list)

    registered_p = await service.get_all_playlists()
    assert len(registered_p) == 1
    assert registered_p[0].id == "test_playlist"
    assert registered_p[0].song_ids == [mock_media_env["song_id"]]


@pytest.mark.redis
@pytest.mark.asyncio
async def test_playlist_skips_missing_songs(mock_media_env, redis_client):
    """Test that playlists skip songs that aren't registered."""
    service = get_music_service()
    playlists = [{"id": "p1", "name": "P1", "songs": ["non_existent"]}]

    await service.register_all(songs=[], playlists=playlists)

    registered = await service.get_all_playlists()
    assert len(registered) == 1
    assert registered[0].song_ids == []


@pytest.mark.redis
@pytest.mark.asyncio
async def test_store_and_register_song(mock_media_env, redis_client):
    """Test persisting to json and then registering in Redis."""
    service = get_music_service()
    song_id = mock_media_env["song_id"]

    # We need to make sure the song exists on disk (conftest does this)
    song = await service.store_and_register_song(song_id)

    assert song.id == song_id
    assert (await service.redis_store.get_song(song_id)) is not None

    store = service.file_store.load_store()
    assert any(s["id"] == song_id for s in store["songs"])


@pytest.mark.redis
@pytest.mark.asyncio
async def test_create_playlist(mock_media_env, redis_client):
    """Test creating a new playlist."""
    service = get_music_service()
    p_id = "new_p"
    p_name = "New Playlist"

    await service.create_playlist(p_id, p_name)

    # Check Redis
    p = await service.redis_store.get_playlist(p_id)
    assert p["name"] == p_name

    # Check File Store
    store = service.file_store.load_store()
    playlist_in_store = next((p for p in store["playlists"] if p["id"] == p_id), None)
    assert playlist_in_store is not None
    assert playlist_in_store["name"] == p_name


@pytest.mark.redis
@pytest.mark.asyncio
async def test_add_song_to_playlist(mock_media_env, redis_client):
    """Test adding a song to a playlist."""
    service = get_music_service()
    song_id = mock_media_env["song_id"]
    p_id = mock_media_env["playlist_id"]

    # We need to register EVERYTHING first to ensure the playlist exists in Redis
    store_data = service.file_store.load_store()
    await service.register_all(songs=store_data.get("songs", []), playlists=store_data.get("playlists", []))

    await service.add_song_to_playlist(p_id, song_id)

    # Check Redis
    p = await service.redis_store.get_playlist(p_id)
    assert song_id in p["song_ids"]

    # Check File Store
    store = service.file_store.load_store()
    playlist_in_store = next((p for p in store["playlists"] if p["id"] == p_id), None)
    assert song_id in playlist_in_store["songs"]
