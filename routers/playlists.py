from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from db import get_db
from models.users import User
from models.videos import Playlist, PlaylistVideoMapping, Video
from schemas.videos import (PlaylistCreate, PlaylistResponse, PlaylistVideoMappingCreate, 
                            PlaylistVideoMappingResponse, PlaylistWithVideosResponse, VideoResponse)
from utils.auth import get_current_user
from typing import List
from config import setting

route = APIRouter(prefix="/playlists", tags=["Playlists"])


@route.post("/", response_model=PlaylistResponse, status_code=status.HTTP_201_CREATED)
def create_playlist(
    payload: PlaylistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new playlist. Requires authentication.
    """
    # Ensure the owner_id matches the authenticated user
    if payload.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create playlists for yourself"
        )
    
    new_playlist = Playlist(
        title=payload.title,
        owner_id=payload.owner_id
    )
    
    db.add(new_playlist)
    db.commit()
    db.refresh(new_playlist)
    
    return new_playlist


@route.get("/", response_model=List[PlaylistWithVideosResponse])
def get_playlists(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all playlists for the authenticated user with their videos.
    """
    playlists = db.query(Playlist).filter(Playlist.owner_id == current_user.id).all()
    
    result = []
    for playlist in playlists:
        # Get all videos in this playlist
        mappings = db.query(PlaylistVideoMapping).filter(
            PlaylistVideoMapping.playlist_id == playlist.id
        ).order_by(PlaylistVideoMapping.position).all()
        
        videos = []
        for mapping in mappings:
            video = db.query(Video).filter(Video.id == mapping.video_id).first()
            if video:
                # Use protected routes via API
                video.storage_path = f"{setting.api_base_url}/videos/{video.id}/play"
                if video.thumbnail_url:
                    video.thumbnail_url = f"{setting.api_base_url}/videos/{video.id}/thumbnail"
                videos.append(video)
        
        result.append({
            "id": playlist.id,
            "title": playlist.title,
            "owner_id": playlist.owner_id,
            "created_at": playlist.created_at,
            "videos": videos
        })
    
    return result


@route.get("/{playlist_id}", response_model=PlaylistWithVideosResponse)
def get_playlist(
    playlist_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific playlist by ID with its videos. Only the owner can access it.
    """
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    
    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found"
        )
    
    if playlist.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this playlist"
        )
    
    # Get all videos in this playlist
    mappings = db.query(PlaylistVideoMapping).filter(
        PlaylistVideoMapping.playlist_id == playlist_id
    ).order_by(PlaylistVideoMapping.position).all()
    
    videos = []
    for mapping in mappings:
        video = db.query(Video).filter(Video.id == mapping.video_id).first()
        if video:
            # Use protected routes via API
            video.storage_path = f"{setting.api_base_url}/videos/{video.id}/play"
            if video.thumbnail_url:
                video.thumbnail_url = f"{setting.api_base_url}/videos/{video.id}/thumbnail"
            videos.append(video)
    
    return {
        "id": playlist.id,
        "title": playlist.title,
        "owner_id": playlist.owner_id,
        "created_at": playlist.created_at,
        "videos": videos
    }


@route.post("/{playlist_id}/videos", response_model=PlaylistVideoMappingResponse, status_code=status.HTTP_201_CREATED)
def add_video_to_playlist(
    playlist_id: str,
    payload: PlaylistVideoMappingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a video to a playlist. Requires authentication and ownership of both playlist and video.
    """
    # Verify playlist exists and user owns it
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found"
        )
    
    if playlist.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to modify this playlist"
        )
    
    # Verify video exists and user owns it
    video = db.query(Video).filter(Video.id == payload.video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    if video.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only add your own videos to playlists"
        )
    
    # Check if video is already in the playlist
    existing_mapping = db.query(PlaylistVideoMapping).filter(
        PlaylistVideoMapping.playlist_id == playlist_id,
        PlaylistVideoMapping.video_id == payload.video_id
    ).first()
    
    if existing_mapping:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video is already in this playlist"
        )
    
    # Determine the position
    if payload.position is not None:
        position = payload.position
        # Check if this position is already taken
        position_exists = db.query(PlaylistVideoMapping).filter(
            PlaylistVideoMapping.playlist_id == playlist_id,
            PlaylistVideoMapping.position == position
        ).first()
        
        if position_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Position {position} is already occupied in this playlist"
            )
    else:
        # Get the maximum position and add 1
        max_position = db.query(func.max(PlaylistVideoMapping.position)).filter(
            PlaylistVideoMapping.playlist_id == playlist_id
        ).scalar()
        position = int(max_position or 0) + 1
    
    # Create the mapping
    new_mapping = PlaylistVideoMapping(
        playlist_id=playlist_id,
        video_id=payload.video_id,
        position=position
    )
    
    try:
        db.add(new_mapping)
        db.commit()
        db.refresh(new_mapping)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add video to playlist: {str(e)}"
        )
    
    return new_mapping


@route.delete("/{playlist_id}/videos/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_video_from_playlist(
    playlist_id: str,
    video_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove a video from a playlist. Requires authentication and playlist ownership.
    """
    # Verify playlist exists and user owns it
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found"
        )
    
    if playlist.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to modify this playlist"
        )
    
    # Find and delete the mapping
    mapping = db.query(PlaylistVideoMapping).filter(
        PlaylistVideoMapping.playlist_id == playlist_id,
        PlaylistVideoMapping.video_id == video_id
    ).first()
    
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found in this playlist"
        )
    
    db.delete(mapping)
    db.commit()
    
    return None


@route.delete("/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_playlist(
    playlist_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a playlist. Requires authentication and playlist ownership.
    """
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    
    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found"
        )
    
    if playlist.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this playlist"
        )
    
    # Delete all video mappings first
    db.query(PlaylistVideoMapping).filter(
        PlaylistVideoMapping.playlist_id == playlist_id
    ).delete()
    
    # Delete the playlist
    db.delete(playlist)
    db.commit()
    
    return None
