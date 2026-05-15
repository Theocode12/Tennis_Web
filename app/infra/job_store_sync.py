import json

from .job_store_common import TTL, build_payload, key


def create_job(redis, job_id: str) -> None:
    payload = build_payload("processing")

    redis.set(key(job_id), json.dumps(payload), ex=TTL)


def get_job(redis, job_id: str) -> dict | None:
    value = redis.get(key(job_id))
    if not value:
        return None
    return json.loads(value)


def update_job(redis, job_id: str, data: dict) -> None:
    redis.set(key(job_id), json.dumps(data), ex=TTL)


def complete_job(redis, job_id: str, song_id: str) -> None:
    payload = build_payload("completed", song_id)

    redis.set(key(job_id), json.dumps(payload), ex=TTL)


def fail_job(redis, job_id: str, error: str) -> None:
    payload = build_payload("failed", error=error)

    redis.set(key(job_id), json.dumps(payload), ex=TTL)
