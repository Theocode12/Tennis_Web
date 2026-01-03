from fastapi import APIRouter

from app.api.v1 import live_games

router = APIRouter(prefix="/api/v1")

router.include_router(live_games.router, tags=["Live Games"])
