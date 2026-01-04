from fastapi import FastAPI
from routers import auth, videos, playlists
from db import engine, Base
from models.users import User, UserUsage
from models.videos import Video, Playlist, PlaylistVideoMapping

# Create all database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Streamer API",
    description="A FastAPI application for video streaming platform",
    version="1.0.0"
)

app.include_router(auth.route)
app.include_router(videos.route)
app.include_router(playlists.route)