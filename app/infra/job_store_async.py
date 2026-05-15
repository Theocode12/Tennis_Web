import json

from .job_store_common import TTL, build_payload, key


async def create_job(redis, job_id: str) -> None:
    payload = build_payload("processing")

    await redis.set(key(job_id), json.dumps(payload), ex=TTL)


async def get_job(redis, job_id: str) -> dict | None:
    value = await redis.get(key(job_id))
    if not value:
        return None
    return json.loads(value)


async def update_job(redis, job_id: str, data: dict) -> None:
    await redis.set(key(job_id), json.dumps(data), ex=TTL)


async def complete_job(redis, job_id: str, song_id: str) -> None:
    payload = build_payload("completed", song_id)

    await redis.set(key(job_id), json.dumps(payload), ex=TTL)


async def fail_job(redis, job_id: str, error: str) -> None:
    payload = build_payload("failed", error=error)

    await redis.set(key(job_id), json.dumps(payload), ex=TTL)
