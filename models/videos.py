from sqlalchemy import Column, Integer, String,DateTime, ForeignKey, func
from enum import Enum
from sqlalchemy import Enum as SAEnum
import uuid

# Importing Base
from db import Base

class VideoStatus(Enum):
  UPLOADING = 'UPLOADING'
  PROCESSING = 'PROCESSING'
  PROCESSED = 'PROCESSED'

class Video(Base):
    __tablename__ = "videos" 

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    url = Column(String, nullable=False)
    status = Column(SAEnum(VideoStatus, native_enum=False), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

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
        ForeignKey("playlists.id"),
        primary_key=True
    )
    video_id = Column(
        String(36),
        ForeignKey("videos.id"),
        primary_key=True
    )
    position = Column(Integer, nullable=False)