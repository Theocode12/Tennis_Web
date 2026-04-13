import json
from pathlib import Path
from typing import Any

from utils.logger import get_logger

logger = get_logger(__name__)


class MusicFileStore:
    def __init__(self, media_root: Path, store_path: Path):
        self.media_root = media_root
        self.store_path = store_path
        self._ensure_store()

    def _ensure_store(self):
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.store_path.exists():
            self.store_path.write_text(json.dumps({"songs": [], "playlists": []}, indent=2))

    def load_store(self) -> dict[str, Any]:
        return json.loads(self.store_path.read_text())

    def save_store(self, data: dict[str, Any]) -> None:
        self.store_path.write_text(json.dumps(data, indent=2))

    def get_song_dir(self, song_id: str) -> Path:
        return self.media_root / song_id

    def get_hls_path(self, song_id: str) -> Path:
        return self.get_song_dir(song_id) / "playlist.m3u8"

    def get_metadata(self, song_id: str) -> dict[str, Any] | None:
        meta_file = self.get_song_dir(song_id) / "meta.json"
        if not meta_file.exists():
            return None
        try:
            return json.loads(meta_file.read_text())
        except Exception as e:
            logger.error(f"Failed to read metadata for {song_id}: {e}")
            return None

    def song_exists(self, song_id: str) -> bool:
        return self.get_hls_path(song_id).exists()

    def scan_media_folder(self) -> list[dict[str, Any]]:
        results = []
        if not self.media_root.exists():
            return results

        for song_dir in self.media_root.iterdir():
            if not song_dir.is_dir():
                continue

            song_id = song_dir.name
            meta = self.get_metadata(song_id)
            results.append({"id": song_id, "metadata": meta, "hls_available": self.song_exists(song_id)})
        return results
