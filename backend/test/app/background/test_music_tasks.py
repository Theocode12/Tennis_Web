from unittest.mock import patch

import pytest

from app.background.tasks.music_tasks import process_song_task


@pytest.mark.redis
def test_process_song_task_success(redis_client_sync):
    """Test that the Celery task correctly coordinates ingestion and state updates."""
    job_id = "test_task_job"
    title = "Task Title"
    artist = "Task Artist"

    from app.infra.job_store_sync import create_job as create_job_sync

    create_job_sync(redis_client_sync, job_id)

    # Mock ingestion_service.process_song and get_redis_client locally
    with (
        patch("app.background.tasks.music_tasks.process_song", return_value="test_song_id") as mock_process,
        patch("app.background.tasks.music_tasks.get_redis_client", return_value=redis_client_sync),
    ):
        # We call the function directly (not .delay) to test the logic
        process_song_task(job_id, title, artist)

        mock_process.assert_called_once_with(job_id, title, artist)

        # Verify job status in Redis
        # Wait, job_store_sync vs async. music_tasks uses job_store_sync.
        from app.infra.job_store_sync import get_job as get_job_sync

        job = get_job_sync(redis_client_sync, job_id)
        assert job["status"] == "completed"
        assert job["song_id"] == "test_song_id"


@pytest.mark.redis
def test_process_song_task_failure(redis_client_sync):
    """Test that the Celery task handles failures correctly."""
    job_id = "fail_job"

    from app.infra.job_store_sync import create_job as create_job_sync

    create_job_sync(redis_client_sync, job_id)

    with (
        patch("app.background.tasks.music_tasks.process_song", side_effect=Exception("Failed!")),
        patch("app.background.tasks.music_tasks.get_redis_client", return_value=redis_client_sync),
    ):
        process_song_task(job_id, "T", "A")

        from app.infra.job_store_sync import get_job as get_job_sync

        job = get_job_sync(redis_client_sync, job_id)
        assert job["status"] == "failed"
        assert "Failed!" in job["error"]
