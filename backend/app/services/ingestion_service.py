import json
from pathlib import Path

import ffmpeg

from utils.logger import get_logger

logger = get_logger(__name__)

MEDIA_ROOT = Path("media")
UPLOAD_DIR = Path("tmp_uploads")


def process_song(job_id: str, title: str, artist: str):
    song_id = job_id

    input_path = UPLOAD_DIR / f"{song_id}.mp3"
    output_dir = MEDIA_ROOT / song_id

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Run FFmpeg using ffmpeg-python
    logger.info(f"Running FFmpeg for job {job_id}")

    try:
        (
            ffmpeg.input(str(input_path))
            .output(
                str(output_dir / "playlist.m3u8"),
                acodec="aac",
                audio_bitrate="128k",
                f="hls",
                hls_time=5,
                hls_list_size=0,
                hls_segment_filename=str(output_dir / "segment%03d.ts"),
            )
            .run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as e:
        stderr = e.stderr.decode() if e.stderr else "Unknown error"
        logger.error(f"FFmpeg error: {stderr}")
        raise RuntimeError(f"FFmpeg processing failed: {stderr}") from e

    # Write metadata
    meta = {"id": song_id, "title": title, "artist": artist, "status": "ready"}

    meta_path = output_dir / "meta.json"
    meta_path.write_text(json.dumps(meta, indent=2))

    # Cleanup temp file
    try:
        input_path.unlink()
    except Exception:
        logger.warning(f"Failed to delete temp file {input_path}")

    return song_id
