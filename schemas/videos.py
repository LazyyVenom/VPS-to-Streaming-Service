from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from models.videos import VideoStatus


class VideoCreate(BaseModel):
    title: str
    owner_id: str
    url: str
    status: VideoStatus


class VideoUpdate(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    status: Optional[VideoStatus] = None


class VideoResponse(BaseModel):
    id: str
    title: str
    owner_id: str
    url: str
    status: VideoStatus
    created_at: datetime

    class Config:
        from_attributes = True


class PlaylistCreate(BaseModel):
    title: str
    owner_id: str


class PlaylistResponse(BaseModel):
    id: str
    title: str
    owner_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class PlaylistVideoMappingCreate(BaseModel):
    playlist_id: str
    video_id: str
    position: int


class PlaylistVideoMappingResponse(BaseModel):
    playlist_id: str
    video_id: str
    position: int

    class Config:
        from_attributes = True
