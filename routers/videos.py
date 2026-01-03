from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db import get_db
from models.users import User
from models.videos import Video, VideoStatus
from schemas.videos import VideoCreate, VideoResponse
from utils.auth import get_current_user
from typing import List

route = APIRouter(prefix="/videos", tags=["Videos"])


@route.post("/", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
def create_video(
    payload: VideoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new video. Requires authentication.
    """
    # Ensure the owner_id matches the authenticated user
    if payload.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create videos for yourself"
        )
    
    new_video = Video(
        title=payload.title,
        owner_id=payload.owner_id,
        url=payload.url,
        status=payload.status
    )
    
    db.add(new_video)
    db.commit()
    db.refresh(new_video)
    
    return new_video


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