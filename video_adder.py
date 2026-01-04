"""
Script to add videos to the database for a specific user.
The videos should be stored in the VPS structure:
BASE_URL/users/{user_id}/videos/{video_id}/
"""

import warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", message=".*trapped.*")

import os
import uuid
from pathlib import Path
from db import SessionLocal, Base, engine
from models.users import User
from models.videos import Video, VideoStatus
from config import setting


def get_video_url(user_id: str, video_id: str) -> str:
    """Generate the master.m3u8 URL for a video."""
    return f"{setting.base_storage_url}/users/{user_id}/videos/{video_id}/master.m3u8"


def get_thumbnail_url(user_id: str, video_id: str) -> str:
    """Generate the thumbnail URL for a video."""
    return f"{setting.base_storage_url}/users/{user_id}/videos/{video_id}/thumbnail.jpg"


def verify_video_files_exist(user_id: str, video_id: str) -> bool:
    """Check if video files exist in the expected directory structure."""
    video_dir = Path(setting.base_storage_url) / "users" / user_id / "videos" / video_id
    
    master_file = video_dir / "master.m3u8"
    thumbnail_file = video_dir / "thumbnail.jpg"
    video_file = video_dir / "360p.mp4"
    
    return master_file.exists() and thumbnail_file.exists() and video_file.exists()


def add_video(username: str, title: str, check_files: bool = False):
    """
    Add a video for a user to the database.
    
    Args:
        username: Username of the video owner
        title: Title of the video
        check_files: If True, verify files exist before adding (default: False for flexibility)
    """
    # Create database session
    db = SessionLocal()
    
    try:
        # Find user by username
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            print(f"❌ Error: User '{username}' not found!")
            print("Available users:")
            users = db.query(User).all()
            for u in users:
                print(f"  - {u.username}")
            return None
        
        # Generate video ID
        video_id = str(uuid.uuid4())
        
        # Generate URLs
        video_url = get_video_url(user.id, video_id)
        thumbnail_url = get_thumbnail_url(user.id, video_id)
        
        # Check if files exist (optional)
        if check_files:
            if not verify_video_files_exist(user.id, video_id):
                print(f"❌ Error: Video files not found in expected directory structure:")
                print(f"   Expected path: {setting.base_storage_url}/users/{user.id}/videos/{video_id}/")
                print(f"   Required files: master.m3u8, 360p.mp4, thumbnail.jpg")
                return None
        
        # Create video entry
        new_video = Video(
            id=video_id,
            title=title,
            owner_id=user.id,
            url=video_url,
            thumbnail_url=thumbnail_url,
            status=VideoStatus.PROCESSED
        )
        
        db.add(new_video)
        db.commit()
        db.refresh(new_video)
        
        print(f"✅ Video added successfully!")
        print(f"   Video ID: {new_video.id}")
        print(f"   Title: {new_video.title}")
        print(f"   Owner: {username} ({user.id})")
        print(f"   Video URL: {video_url}")
        print(f"   Thumbnail URL: {thumbnail_url}")
        print(f"   Status: {new_video.status.value}")
        print(f"\n📁 Expected file structure:")
        print(f"   {setting.base_storage_url}/users/{user.id}/videos/{video_id}/")
        print(f"   ├── master.m3u8")
        print(f"   ├── 360p.mp4")
        print(f"   └── thumbnail.jpg")
        
        return new_video
        
    except Exception as e:
        print(f"❌ Error occurred: {str(e)}")
        db.rollback()
        return None
    finally:
        db.close()


def add_multiple_videos(username: str, video_titles: list, check_files: bool = False):
    """
    Add multiple videos for a user.
    
    Args:
        username: Username of the video owner
        video_titles: List of video titles to add
        check_files: If True, verify files exist before adding
    """
    print(f"Adding {len(video_titles)} videos for user '{username}'...")
    print("="*70)
    
    added_count = 0
    failed_count = 0
    
    for title in video_titles:
        result = add_video(username, title, check_files)
        if result:
            added_count += 1
        else:
            failed_count += 1
        print()
    
    print("="*70)
    print(f"Summary: {added_count} videos added, {failed_count} failed")
    print("="*70)


def list_user_videos(username: str):
    """List all videos for a specific user."""
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            print(f"❌ Error: User '{username}' not found!")
            return
        
        videos = db.query(Video).filter(Video.owner_id == user.id).all()
        
        if not videos:
            print(f"No videos found for user '{username}'")
            return
        
        print(f"\n📹 Videos for user '{username}' ({len(videos)} total):")
        print("="*70)
        
        for idx, video in enumerate(videos, 1):
            print(f"\n{idx}. {video.title}")
            print(f"   ID: {video.id}")
            print(f"   URL: {video.url}")
            print(f"   Thumbnail: {video.thumbnail_url}")
            print(f"   Status: {video.status.value}")
            print(f"   Created: {video.created_at}")
        
        print("="*70)
        
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    
    print("Video Adder Script")
    print("="*70)
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python video_adder.py <username> <title> [--check-files]")
        print("  python video_adder.py list <username>")
        print("\nExamples:")
        print("  python video_adder.py Anubhav 'My Awesome Video'")
        print("  python video_adder.py Anubhav 'Tutorial' --check-files")
        print("  python video_adder.py list Anubhav")
        sys.exit(1)
    
    if sys.argv[1] == "list":
        if len(sys.argv) < 3:
            print("❌ Error: Username required for list command")
            sys.exit(1)
        list_user_videos(sys.argv[2])
    else:
        username = sys.argv[1]
        title = sys.argv[2] if len(sys.argv) > 2 else "Untitled Video"
        check_files = "--check-files" in sys.argv
        
        add_video(username, title, check_files)
