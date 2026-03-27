from celery import shared_task

from app.infra.job_store_sync import complete_job, fail_job
from app.infra.sync_redis import get_redis_client
from app.services.ingestion_service import process_song
from utils.logger import get_logger

logger = get_logger(__name__)


@shared_task(name="process_song_task")
def process_song_task(job_id: str, title: str, artist: str):
    redis = get_redis_client()

    try:
        song_id = process_song(job_id, title, artist)
        complete_job(redis, job_id, song_id)
        logger.info(f"Job {job_id} completed")

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        fail_job(redis, job_id, str(e))
