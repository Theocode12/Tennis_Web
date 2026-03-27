import json
from typing import Any

import redis.asyncio as redis

from .music_redis_store_common import PLAYLISTS_KEY, SONGS_KEY


class MusicRedisStore:
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client

    async def save_song(self, song_id: str, data: dict[str, Any]) -> None:
        await self.redis_client.hset(SONGS_KEY, song_id, json.dumps(data))

    async def get_song(self, song_id: str) -> dict[str, Any] | None:
        data = await self.redis_client.hget(SONGS_KEY, song_id)
        return json.loads(data) if data else None

    async def get_all_songs(self) -> dict[str, dict[str, Any]]:
        data = await self.redis_client.hgetall(SONGS_KEY)
        return {k: json.loads(v) for k, v in data.items()}

    async def save_playlist(self, playlist_id: str, data: dict[str, Any]) -> None:
        await self.redis_client.hset(PLAYLISTS_KEY, playlist_id, json.dumps(data))

    async def get_playlist(self, playlist_id: str) -> dict[str, Any] | None:
        data = await self.redis_client.hget(PLAYLISTS_KEY, playlist_id)
        return json.loads(data) if data else None

    async def get_all_playlists(self) -> dict[str, dict[str, Any]]:
        data = await self.redis_client.hgetall(PLAYLISTS_KEY)
        return {k: json.loads(v) for k, v in data.items()}

    async def sync_from_store(self, store_data: dict[str, Any]) -> None:
        """Bulk sync from file store data to Redis."""
        songs = store_data.get("songs", {})
        playlists = store_data.get("playlists", {})

        if songs:
            serialized_songs = {k: json.dumps(v) for k, v in songs.items()}
            await self.redis_client.hset(SONGS_KEY, mapping=serialized_songs)

        if playlists:
            serialized_playlists = {k: json.dumps(v) for k, v in playlists.items()}
            await self.redis_client.hset(PLAYLISTS_KEY, mapping=serialized_playlists)

    async def clear_all(self):
        """Clear the music hashes."""
        await self.redis_client.delete(SONGS_KEY, PLAYLISTS_KEY)
