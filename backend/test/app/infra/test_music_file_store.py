import json

from app.infra.music_file_store import MusicFileStore


def test_music_file_store_ensures_json(tmp_path):
    """Test that MusicFileStore creates music.json if it doesn't exist."""
    media_root = tmp_path / "media"
    store_path = tmp_path / "music.json"

    MusicFileStore(media_root, store_path)

    assert store_path.exists()
    data = json.loads(store_path.read_text())
    assert data["songs"] == []
    assert data["playlists"] == []


def test_music_file_store_load_save(tmp_path):
    """Test loading and saving to the file store."""
    media_root = tmp_path / "media"
    store_path = tmp_path / "music.json"
    store = MusicFileStore(media_root, store_path)

    test_data = {"songs": [{"id": "s1", "title": "T1"}], "playlists": []}
    store.save_store(test_data)

    loaded = store.load_store()
    assert loaded == test_data


def test_music_file_store_metadata(tmp_path):
    """Test reading song metadata from disk."""
    media_root = tmp_path / "media"
    store_path = tmp_path / "music.json"
    store = MusicFileStore(media_root, store_path)

    song_id = "test_song"
    song_dir = media_root / song_id
    song_dir.mkdir(parents=True)

    meta = {"title": "Test Song", "artist": "Artist"}
    (song_dir / "meta.json").write_text(json.dumps(meta))

    # Test get_metadata
    read_meta = store.get_metadata(song_id)
    assert read_meta == meta

    # Test song_exists (requires playlist.m3u8)
    assert store.song_exists(song_id) is False
    (song_dir / "playlist.m3u8").write_text("#EXTM3U")
    assert store.song_exists(song_id) is True


def test_scan_media_folder(tmp_path):
    """Test scanning the media folder for all songs."""
    media_root = tmp_path / "media"
    store_path = tmp_path / "music.json"
    store = MusicFileStore(media_root, store_path)

    # Create one valid song and one invalid
    (media_root / "s1").mkdir(parents=True)
    (media_root / "s1" / "meta.json").write_text(json.dumps({"title": "S1"}))
    (media_root / "s1" / "playlist.m3u8").write_text("...")

    (media_root / "s2").mkdir(parents=True)  # No meta, no hls

    results = store.scan_media_folder()
    assert len(results) == 2

    s1 = next(r for r in results if r["id"] == "s1")
    assert s1["metadata"]["title"] == "S1"
    assert s1["hls_available"] is True

    s2 = next(r for r in results if r["id"] == "s2")
    assert s2["metadata"] is None
    assert s2["hls_available"] is False
