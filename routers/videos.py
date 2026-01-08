from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from db import get_db
from models.users import User
from models.videos import Video, VideoStatus, PlaylistVideoMapping
from schemas.videos import VideoResponse, TorrentRequest, VideoUpdate
from utils.auth import get_current_user
from typing import List
from index import torrent_queue
from config import setting
import os
import shutil

route = APIRouter(prefix="/videos", tags=["Videos"])

@route.post("/", response_model=dict)
def add_torrent(
    request: TorrentRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Add a torrent to the processing queue. Videos will be downloaded and processed in the background.
    """
    # I know shouldn't Have done this but I am lazy and no way of creating new user only through DB will change this later if I will feel like it
    if "guest" in current_user.username.lower():
        return Response({"body":"Sorry Can't Allow That You will fill my server"}, status_code=400)

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
    videos = (
        db.query(Video)
        .filter(Video.owner_id == current_user.id)
        .all()
    )

    for video in videos:
        video.storage_path = (
            f"{setting.api_base_url}/videos/{video.id}/play"
        )

        if video.thumbnail_url:
            video.thumbnail_url = (
                f"{setting.api_base_url}/videos/{video.id}/thumbnail"
            )

    return videos

@route.get("/{video_id}", response_model=VideoResponse)
def get_video(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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

    video.storage_path = (
        f"{setting.api_base_url}/videos/{video.id}/play"
    )

    if video.thumbnail_url:
        video.thumbnail_url = (
            f"{setting.api_base_url}/videos/{video.id}/thumbnail"
        )

    return video

@route.patch("/{video_id}", response_model=VideoResponse)
def update_video(
    video_id: str,
    payload: VideoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update video details (currently supports title update). Only the owner can update.
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
            detail="You don't have permission to update this video"
        )
    
    # Update only provided fields
    if payload.title is not None:
        video.title = payload.title
    
    db.commit()
    db.refresh(video)
    return video


@route.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a video, its HLS data, and all playlist associations. Only the owner can delete.
    """
    if "guest" in current_user.username.lower():
        return Response({"body":"Sorry Can't Allow That What will other watch"}, status_code=400)
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    if video.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this video"
        )
    
    # Delete HLS data from storage
    video_storage_path = os.path.join(setting.base_storage_path, video.storage_path)
    if os.path.exists(video_storage_path):
        try:
            shutil.rmtree(video_storage_path)
        except Exception as e:
            # Log but don't fail if file deletion fails
            pass
    
    # Delete playlist mappings
    db.query(PlaylistVideoMapping).filter(
        PlaylistVideoMapping.video_id == video_id
    ).delete()
    
    # Delete video record
    db.delete(video)
    db.commit()
    
    return None


# FILE PROTECTION USER WISE FILES ACCESS
@route.get("/{video_id}/play/{file_path:path}")
def play_video(
    video_id: str,
    file_path: str = "",  # Default to empty for master.m3u8
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    video = db.query(Video).filter(Video.id == video_id).first()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if video.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Default to master.m3u8 if no path specified
    if not file_path:
        file_path = "master.m3u8"
    
    # Determine content type
    if file_path.endswith('.m3u8'):
        content_type = "application/vnd.apple.mpegurl"
    elif file_path.endswith('.ts'):
        content_type = "video/mp2t"
    else:
        content_type = "application/octet-stream"

    return Response(
        headers={
            "X-Accel-Redirect": f"/_protected_hls/{video.storage_path}/{file_path}",
            "Content-Type": content_type,
        }
    )

@route.get("/{video_id}/thumbnail")
def get_thumbnail(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    video = db.query(Video).filter(Video.id == video_id).first()

    if not video or video.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    return Response(
        headers={
            "X-Accel-Redirect": f"/_protected_hls/{video.storage_path}/thumbnail.jpg",
            "Content-Type": "image/jpeg",
        }
    )
