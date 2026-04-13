import logging
import shutil
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from app.background.tasks.music_tasks import process_song_task
from app.dependencies import get_app_logger, get_music_service, require_secret
from app.infra.job_store_async import create_job, get_job
from app.models.music import SongIngestRequest
from app.services.music_service import MusicService

router = APIRouter(prefix="/music", tags=["music"])

UPLOAD_DIR = Path("tmp_uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@router.get("/playlists")
async def list_playlists(music_service: Annotated[MusicService, Depends(get_music_service)]):
    playlists = await music_service.get_all_playlists()
    return [{"id": p.id, "name": p.name} for p in playlists]


@router.get("/playlist/{playlist_id}")
async def get_playlist_details(
    playlist_id: str, request: Request, music_service: Annotated[MusicService, Depends(get_music_service)]
):
    songs = await music_service.get_playlist_details(playlist_id)

    if songs is None:
        raise HTTPException(status_code=404, detail="Playlist not found")

    base_url = str(request.base_url).rstrip("/")

    return [
        {
            "id": s.id,
            "title": s.title,
            "artist": s.artist,
            "stream_url": f"{base_url}{s.hls_path}" if s.hls_path else None,
        }
        for s in songs
    ]


@router.get("/songs")
async def get_registered_songs(
    music_service: Annotated[MusicService, Depends(get_music_service)],
    _secret: None = Depends(require_secret),
):
    return await music_service.get_all_songs()


@router.get("/media-folder")
def get_unregistered_media(
    music_service: Annotated[MusicService, Depends(get_music_service)],
    _secret: None = Depends(require_secret),
):
    """Scan the media folder for all processed songs, even if not registered."""
    return music_service.file_store.scan_media_folder()


@router.post("/register/{song_id}")
async def register_song_metadata(
    song_id: str,
    music_service: Annotated[MusicService, Depends(get_music_service)],
    logger: Annotated[logging.Logger, Depends(get_app_logger)] = None,
    _secret: None = Depends(require_secret),
):
    try:
        await music_service.store_and_register_song(song_id)
        logger.info(f"Registered song {song_id}")
        return {"song_id": song_id, "status": "registered"}
    except Exception as e:
        logger.error(f"Failed to register song {song_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/playlist")
async def create_new_playlist(
    name: str = Form(...),
    music_service: Annotated[MusicService, Depends(get_music_service)] = None,
    logger: Annotated[logging.Logger, Depends(get_app_logger)] = None,
    _secret: None = Depends(require_secret),
):
    playlist_id = str(uuid.uuid4())
    try:
        await music_service.create_playlist(playlist_id, name)
        logger.info(f"Created playlist {playlist_id} with name '{name}'")
        return {"playlist_id": playlist_id, "status": "created"}
    except Exception as e:
        logger.error(f"Failed to create playlist {playlist_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/playlist/{playlist_id}/add/{song_id}")
async def add_song_to_playlist(
    playlist_id: str,
    song_id: str,
    music_service: Annotated[MusicService, Depends(get_music_service)],
    logger: Annotated[logging.Logger, Depends(get_app_logger)] = None,
    _secret: None = Depends(require_secret),
):
    try:
        await music_service.add_song_to_playlist(playlist_id, song_id)
        logger.info(f"Added song {song_id} to playlist {playlist_id}")
        return {"playlist_id": playlist_id, "song_id": song_id, "status": "added"}
    except Exception as e:
        logger.error(f"Failed to add song {song_id} to playlist {playlist_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/ingest")
async def ingest_music_file(
    file: UploadFile = File(...),
    request: SongIngestRequest = Depends(SongIngestRequest.as_form),
    music_service: Annotated[MusicService, Depends(get_music_service)] = None,
    logger: Annotated[logging.Logger, Depends(get_app_logger)] = None,
    _secret: None = Depends(require_secret),
):
    if not file.filename or not file.filename.lower().endswith(".mp3"):
        raise HTTPException(status_code=400, detail="Only MP3 files supported")

    # --- 2. Generate IDs ---
    job_id = str(uuid.uuid4())
    song_id = job_id

    # --- 3. Persist temp file ---
    temp_path = UPLOAD_DIR / f"{song_id}.mp3"

    try:
        with temp_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to save upload: {e}")
        raise HTTPException(status_code=500, detail="Failed to save file") from e

    # --- 4. Create job in Redis ---
    await create_job(music_service.redis_store.redis_client, job_id)

    # --- 5. Enqueue background job ---
    try:
        process_song_task.delay(job_id, request.title, request.artist)
    except Exception as e:
        logger.error(f"Failed to enqueue job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to enqueue job") from e

    logger.info(f"Created ingestion job {job_id} for song '{request.title}'")

    return {"job_id": job_id, "status": "processing"}


@router.get("/ingest/{job_id}")
async def get_ingestion_status(
    job_id: str,
    music_service: Annotated[MusicService, Depends(get_music_service)],
    _secret: None = Depends(require_secret),
):
    job = await get_job(music_service.redis_store.redis_client, job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    status = job.get("status")

    if status == "processing":
        return {"job_id": job_id, "status": "processing"}

    if status == "completed":
        song_id = job.get("song_id")
        return {
            "job_id": job_id,
            "status": "completed",
            "song_id": song_id,
            "stream_url": f"/media/{song_id}/playlist.m3u8",
        }

    if status == "failed":
        return {"job_id": job_id, "status": "failed", "error": job.get("error")}

    return {"job_id": job_id, "status": "unknown"}
