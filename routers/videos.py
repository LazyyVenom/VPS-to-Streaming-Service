from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db import get_db
from models.users import User
from models.videos import Video, VideoStatus
from schemas.videos import VideoResponse, TorrentRequest
from utils.auth import get_current_user
from typing import List
from index import torrent_queue
from config import setting

route = APIRouter(prefix="/videos", tags=["Videos"])

@route.post("/", response_model=dict)
def add_torrent(
    request: TorrentRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Add a torrent to the processing queue. Videos will be downloaded and processed in the background.
    """
    task = {
        'magnet_link': request.magnet_link,
        'owner_id': current_user.id,
        'torrent_name': request.torrent_name
    }
    
    torrent_queue.put(task)
    
    return {
        'status': 'queued',
        'message': 'Torrent added to processing queue',
        'queue_size': torrent_queue.qsize()
    }
    

@route.get("/", response_model=List[VideoResponse])
def get_videos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all videos for the authenticated user.
    """
    videos = db.query(Video).filter(Video.owner_id == current_user.id).all()
    
    # Prepend base_storage_url to relative paths
    for video in videos:
        video.storage_path = f"{setting.base_storage_url}/{video.storage_path}"
        if video.thumbnail_url:
            video.thumbnail_url = f"{setting.base_storage_url}/{video.thumbnail_url}"
    
    return videos


@route.get("/{video_id}", response_model=VideoResponse)
def get_video(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific video by ID. Only the owner can access it.
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    if video.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this video"
        )
    
    # Prepend base_storage_url to relative paths
    video.storage_path = f"{setting.base_storage_url}/{video.storage_path}"
    if video.thumbnail_url:
        video.thumbnail_url = f"{setting.base_storage_url}/{video.thumbnail_url}"
    
    return video