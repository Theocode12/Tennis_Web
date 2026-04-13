PREFIX = "music:job:"
TTL = 60 * 60 * 2


def build_payload(status, song_id=None, error=None):
    return {
        "status": status,
        "song_id": song_id,
        "error": error,
    }


def key(job_id: str):
    return f"{PREFIX}{job_id}"
