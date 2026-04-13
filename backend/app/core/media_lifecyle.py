from contextlib import asynccontextmanager

from app.dependencies import get_music_service
from utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def media_lifespan(app) -> None:
    music_service = get_music_service()

    # Load data from file store
    data = music_service.file_store.load_store()

    # Sync and register everything in Redis
    # register_all handles both songs and playlists
    await music_service.register_all(songs=data.get("songs", []), playlists=data.get("playlists", []))

    logger.info("Music bootstrap completed (MusicService class synced)")

    yield
