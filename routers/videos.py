from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db import get_db
from models.users import User
from models.videos import Video, VideoStatus
from schemas.videos import VideoResponse
from utils.auth import get_current_user
from typing import List

route = APIRouter(prefix="/videos", tags=["Videos"])

@route.post("/", response_model=dict)
def add_torrent(
    current_user: User = Depends(get_current_user)
):
    """
    Will get link and use it for playlist making / Video editing
    """
    creator_username = current_user.username
    

@route.get("/", response_model=List[VideoResponse])
def get_videos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all videos for the authenticated user.
    """
    videos = db.query(Video).filter(Video.owner_id == current_user.id).all()
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
    
    return video