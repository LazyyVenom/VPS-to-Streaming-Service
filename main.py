from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)

app.include_router(auth.route)
app.include_router(videos.route)
app.include_router(playlists.route)