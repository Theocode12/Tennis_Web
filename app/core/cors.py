from fastapi.middleware.cors import CORSMiddleware

from os import getenv

frontend_url = getenv("SIM_FRONTEND_URL")

def setup_cors(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
