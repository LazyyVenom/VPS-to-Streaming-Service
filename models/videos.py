from sqlalchemy import Column, Integer, String,DateTime, ForeignKey, func, UniqueConstraint
from enum import Enum
from sqlalchemy import Enum as SAEnum
import uuid

# Importing Base
from db import Base

class VideoStatus(Enum):
  DOWNLOADING = 'DOWNLOADING'
  PROCESSING = 'PROCESSING'
  PROCESSED = 'PROCESSED'
  FAILED = 'FAILED'

class Video(Base):
    __tablename__ = "videos" 

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    storage_path = Column(String, nullable=False)
    thumbnail_url = Column(String)
    status = Column(SAEnum(VideoStatus, native_enum=False), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    duration_seconds = Column(Integer)
    width = Column(Integer)
    height = Column(Integer)
    size_bytes = Column(Integer)

class Playlist(Base):
    __tablename__ = "playlists" 

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class PlaylistVideoMapping(Base):
    __tablename__ = "playlists_videos_mappings"
    playlist_id = Column(
        String(36),
        ForeignKey("playlists.id", ondelete="CASCADE"),
        primary_key=True
    )
    video_id = Column(
        String(36),
        ForeignKey("videos.id", ondelete="CASCADE"),
        primary_key=True
    )
    position = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("playlist_id", "position", name="uq_playlist_position"),
    )