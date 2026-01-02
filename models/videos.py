from sqlalchemy import Column, Integer, String,DateTime, ForeignKey
from enum import Enum
from sqlalchemy import Enum as SAEnum

# Importing Base
from db import Base

class VideoStatus(Enum):
  UPLOADING = 'UPLOADING'
  PROCESSING = 'PROCESSING'
  PROCESSED = 'PROCESSED'

class Video(Base):
    __tablename__ = "videos" 

    id = Column(String(36), primary_key=True)
    title = Column(String, nullable=False)
    owner_id = Column(String(36), ForeignKey("users.id"))
    url = Column(String, nullable=False)
    status = Column(SAEnum(VideoStatus), nullable=False)

class Playlist(Base):
    __tablename__ = "playlists" 

    id = Column(String(36), primary_key=True)
    title = Column(String, nullable=False)
    owner_id = Column(String(36), ForeignKey("users.id"))

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