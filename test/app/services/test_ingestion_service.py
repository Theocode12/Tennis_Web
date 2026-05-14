import json
from configparser import ConfigParser
from unittest.mock import patch

import pytest

from app.services.ingestion_service import process_song


def _make_config(tmp_path, *, upload_dir, media_root) -> ConfigParser:
    """Build a minimal ConfigParser directing path lookups to tmp_path."""
    cfg = ConfigParser()
    cfg["media"] = {
        "upload_dir": str(upload_dir),
        "root_dir": str(media_root),
        "music_store_path": str(tmp_path / "music.json"),
    }
    return cfg


def test_process_song_success(tmp_path):
    """Test the full ingestion process by mocking FFmpeg."""
    media_root = tmp_path / "media"
    upload_dir = tmp_path / "tmp_uploads"
    upload_dir.mkdir()

    song_id = "test_job"
    input_path = upload_dir / f"{song_id}.mp3"
    input_path.write_text("fake mp3 data")

    cfg = _make_config(tmp_path, upload_dir=upload_dir, media_root=media_root)

    with (
        patch("app.services.ingestion_service.load_config", return_value=cfg),
        patch("app.services.ingestion_service.ffmpeg") as mock_ffmpeg,
    ):
        # Configure mock chain: ffmpeg.input().output().run()
        mock_input = mock_ffmpeg.input.return_value
        mock_output = mock_input.output.return_value

        result_id = process_song(song_id, "Test Title", "Test Artist")

        # Verify FFmpeg was called via fluent API
        mock_ffmpeg.input.assert_called_with(str(input_path))
        assert mock_output.run.called

        # Verify metadata was written
        meta_path = media_root / song_id / "meta.json"
        assert meta_path.exists()
        meta = json.loads(meta_path.read_text())
        assert meta["title"] == "Test Title"
        assert meta["artist"] == "Test Artist"

        # Verify temp file cleanup
        assert not input_path.exists()
        assert result_id == song_id


def test_process_song_missing_file(tmp_path):
    """Test behavior when the input file is missing."""
    media_root = tmp_path / "media"
    upload_dir = tmp_path / "tmp_uploads"
    upload_dir.mkdir()

    cfg = _make_config(tmp_path, upload_dir=upload_dir, media_root=media_root)

    with patch("app.services.ingestion_service.load_config", return_value=cfg):
        with pytest.raises(FileNotFoundError):
            process_song("missing", "T", "A")
