
from fastapi import Form
from pydantic import BaseModel, Field


class Song(BaseModel):
    id: str
    title: str
    artist: str
    hls_path: str  # /media/song_1/playlist.m3u8


class Playlist(BaseModel):
    id: str
    name: str
    song_ids: list[str] = Field(default_factory=list)


class SongIngestRequest(BaseModel):
    title: str = Field(..., min_length=1)
    artist: str = Field(..., min_length=1)

    @classmethod
    def as_form(cls, title: str = Form(...), artist: str = Form(...)):
        return cls(title=title, artist=artist)
