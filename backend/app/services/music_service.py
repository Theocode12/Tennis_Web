
from app.infra.music_file_store import MusicFileStore
from app.infra.music_redis_store import MusicRedisStore
from app.models.music import Playlist, Song
from utils.logger import get_logger

logger = get_logger(__name__)


class MusicService:
    def __init__(self, file_store: MusicFileStore, redis_store: MusicRedisStore):
        self.file_store = file_store
        self.redis_store = redis_store

    async def register_song(self, song_id: str) -> Song:
        """Register a song by scanning its metadata and saving it to Redis."""
        if not self.file_store.song_exists(song_id):
            raise ValueError(f"Song '{song_id}' does not exist on disk")

        meta = self.file_store.get_metadata(song_id)
        if not meta:
            raise ValueError(f"Metadata missing for song '{song_id}'")

        song_data = {
            "id": song_id,
            "title": meta.get("title", "Unknown Title"),
            "artist": meta.get("artist", "Unknown Artist"),
            "hls_path": f"/media/{song_id}/playlist.m3u8",
        }

        await self.redis_store.save_song(song_id, song_data)

        return Song(id=song_id, title=song_data["title"], artist=song_data["artist"], hls_path=song_data["hls_path"])

    async def register_all(self, songs: list[dict], playlists: list[dict]) -> None:
        """Register multiple songs and playlists into Redis."""
        # 1. Register all songs (this ensures they have hls_path in Redis)
        for s in songs:
            song_id = s.get("id")
            if song_id:
                try:
                    await self.register_song(song_id)
                except Exception as e:
                    logger.warning(f"Failed to register song {song_id} during bulk sync: {e}")

        # 2. Get registered songs to filter playlists
        registered_songs = await self.redis_store.get_all_songs()

        # 3. Register all playlists
        for p in playlists:
            playlist_id = p.get("id")
            if not playlist_id:
                continue

            # Map 'songs' (from file store) to 'song_ids' (for Redis/API)
            source_song_ids = p.get("songs", [])
            valid_song_ids = [sid for sid in source_song_ids if sid in registered_songs]

            playlist_data = {"id": playlist_id, "name": p.get("name", "Untitled"), "song_ids": valid_song_ids}
            await self.redis_store.save_playlist(playlist_id, playlist_data)

    async def store_and_register_song(self, song_id: str) -> Song:
        """Save song metadata to file and register in Redis."""
        meta = self.file_store.get_metadata(song_id)

        if not meta:
            raise FileNotFoundError(f"Song {song_id} metadata not found on disk")

        # Ensure 'id' is in meta
        meta["id"] = song_id

        # Update File Store
        store = self.file_store.load_store()
        if not isinstance(store.get("songs"), list):
            store["songs"] = []

        # Check if exists and update or append
        existing_idx = next((i for i, s in enumerate(store["songs"]) if s.get("id") == song_id), None)
        if existing_idx is not None:
            store["songs"][existing_idx] = meta
        else:
            store["songs"].append(meta)

        self.file_store.save_store(store)

        # Register in Redis (this will add hls_path and save to Redis)
        return await self.register_song(song_id)

    async def create_playlist(self, playlist_id: str, name: str) -> None:
        """Create a new playlist in both file store and Redis."""
        store = self.file_store.load_store()
        if not isinstance(store.get("playlists"), list):
            store["playlists"] = []

        if any(p.get("id") == playlist_id for p in store["playlists"]):
            logger.warning(f"Playlist {playlist_id} already exists")
            return

        new_p = {"id": playlist_id, "name": name, "songs": []}
        store["playlists"].append(new_p)
        self.file_store.save_store(store)

        # Redis expects a dict with 'song_ids' for the model
        await self.redis_store.save_playlist(playlist_id, {"id": playlist_id, "name": name, "song_ids": []})

    async def add_song_to_playlist(self, playlist_id: str, song_id: str) -> None:
        """Add a song to a playlist in both file store and Redis."""
        store = self.file_store.load_store()
        # Update File Store
        playlists = store.get("playlists", [])
        playlist_in_store = next((p for p in playlists if p.get("id") == playlist_id), None)
        if playlist_in_store:
            if "songs" not in playlist_in_store:
                playlist_in_store["songs"] = []
            if song_id not in playlist_in_store["songs"]:
                playlist_in_store["songs"].append(song_id)
                self.file_store.save_store(store)

        # Update Redis
        playlist = await self.redis_store.get_playlist(playlist_id)
        if playlist:
            if "song_ids" not in playlist:
                playlist["song_ids"] = []
            if song_id not in playlist["song_ids"]:
                playlist["song_ids"].append(song_id)
                await self.redis_store.save_playlist(playlist_id, playlist)

    async def get_all_songs(self) -> list[Song]:
        data = await self.redis_store.get_all_songs()
        return [
            Song(
                id=v.get("id", "unknown"),
                title=v.get("title", "Unknown Title"),
                artist=v.get("artist", "Unknown Artist"),
                hls_path=v.get("hls_path", ""),
            )
            for v in data.values()
        ]

    async def get_all_playlists(self) -> list[Playlist]:
        data = await self.redis_store.get_all_playlists()
        return [Playlist(**v) for v in data.values()]

    async def get_playlist_details(self, playlist_id: str) -> list[Song] | None:
        playlist = await self.redis_store.get_playlist(playlist_id)
        if not playlist:
            return None

        songs = []
        for song_id in playlist.get("song_ids", []):
            song_data = await self.redis_store.get_song(song_id)
            if song_data:
                songs.append(
                    Song(
                        id=song_data.get("id", song_id),
                        title=song_data.get("title", "Unknown Title"),
                        artist=song_data.get("artist", "Unknown Artist"),
                        hls_path=song_data.get("hls_path", ""),
                    )
                )
        return songs

    async def get_song_details(self, song_id: str) -> Song | None:
        data = await self.redis_store.get_song(song_id)
        if not data:
            return None
        return Song(
            id=data.get("id", song_id),
            title=data.get("title", "Unknown Title"),
            artist=data.get("artist", "Unknown Artist"),
            hls_path=data.get("hls_path", ""),
        )
