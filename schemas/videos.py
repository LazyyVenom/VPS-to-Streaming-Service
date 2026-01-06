from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from models.videos import VideoStatus


class TorrentRequest(BaseModel):
    magnet_link: str
    torrent_name: Optional[str] = None


class VideoCreate(BaseModel):
    title: str
    owner_id: str
    url: str
    thumbnail_url: Optional[str] = None
    status: VideoStatus


class VideoUpdate(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    status: Optional[VideoStatus] = None


class VideoResponse(BaseModel):
    id: str
    title: str
    owner_id: str
    storage_path: str
    thumbnail_url: Optional[str]
    status: VideoStatus
    created_at: datetime
    duration_seconds: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    size_bytes: Optional[int] = None

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


class PlaylistWithVideosResponse(BaseModel):
    id: str
    title: str
    owner_id: str
    created_at: datetime
    videos: List['VideoResponse'] = []

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
