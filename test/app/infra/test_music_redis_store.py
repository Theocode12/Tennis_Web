import pytest

from app.infra.music_redis_store import MusicRedisStore


@pytest.mark.redis
@pytest.mark.asyncio
async def test_music_redis_store_song_ops(redis_client):
    """Test saving and getting songs from Redis."""
    store = MusicRedisStore(redis_client)
    song_id = "s1"
    song_data = {"id": song_id, "title": "T1"}

    await store.save_song(song_id, song_data)

    loaded = await store.get_song(song_id)
    assert loaded == song_data

    all_songs = await store.get_all_songs()
    assert all_songs[song_id] == song_data


@pytest.mark.redis
@pytest.mark.asyncio
async def test_music_redis_store_playlist_ops(redis_client):
    """Test saving and getting playlists from Redis."""
    store = MusicRedisStore(redis_client)
    p_id = "p1"
    p_data = {"id": p_id, "name": "P1", "song_ids": ["s1"]}

    await store.save_playlist(p_id, p_data)

    loaded = await store.get_playlist(p_id)
    assert loaded == p_data

    all_p = await store.get_all_playlists()
    assert all_p[p_id] == p_data


@pytest.mark.redis
@pytest.mark.asyncio
async def test_sync_from_store(redis_client):
    """Test bulk syncing from file store data."""
    store = MusicRedisStore(redis_client)
    store_data = {
        "songs": {"s1": {"id": "s1", "title": "T1"}},
        "playlists": {"p1": {"id": "p1", "name": "P1", "songs": ["s1"]}},
    }

    await store.sync_from_store(store_data)

    songs = await store.get_all_songs()
    assert "s1" in songs

    playlists = await store.get_all_playlists()
    assert "p1" in playlists


@pytest.mark.redis
@pytest.mark.asyncio
async def test_clear_all(redis_client):
    """Test clearing the hashes."""
    store = MusicRedisStore(redis_client)
    await store.save_song("s1", {"id": "s1"})

    assert await store.get_song("s1") is not None

    await store.clear_all()

    assert await store.get_song("s1") is None
    assert await store.get_all_songs() == {}
