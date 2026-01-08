"""
Script to add videos or playlists to the Streamer application from a local folder.
- If folder contains 1 video: adds it as a single video
- If folder contains multiple videos: creates a playlist with all videos
"""

import warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", message=".*trapped.*")

import os
import sys
import uuid
from pathlib import Path

from db import SessionLocal, engine, Base
from models.users import User
from models.videos import Video, VideoStatus, Playlist, PlaylistVideoMapping
from utils.downloads_processor import DownloadedVideoProcessor
from config import setting


def add_videos_from_folder(username: str, folder_path: str):
    """
    Process videos from a folder and add them to the database for the specified user.
    
    Args:
        username: Username of the owner
        folder_path: Absolute path to the folder containing video(s)
    """
    
    # Create all tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Create a database session
    db = SessionLocal()
    
    try:
        # Find the user
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            print(f"❌ User '{username}' not found in database.")
            print("   Please create the user first.")
            return
        
        print(f"✅ Found user: {username} (ID: {user.id})")
        
        # Validate folder path
        if not os.path.isdir(folder_path):
            print(f"❌ Error: '{folder_path}' is not a valid directory.")
            return
        
        # Initialize video processor
        processor = DownloadedVideoProcessor(
            base_storage_path=setting.base_storage_path,
            tmp_downloaded_path=os.path.dirname(folder_path)
        )
        
        # Find all videos in the folder
        folder_name = os.path.basename(folder_path)
        videos_found = processor.find_all_videos(folder_name)
        
        if not videos_found:
            print(f"❌ No video files found in '{folder_path}'")
            return
        
        print(f"\n📹 Found {len(videos_found)} video(s) in folder")
        for i, video_path in enumerate(videos_found, 1):
            print(f"   {i}. {os.path.basename(video_path)}")
        
        # Determine if single video or playlist
        if len(videos_found) == 1:
            print("\n🎬 Processing as single video...")
            _process_single_video(db, processor, videos_found[0], user.id, folder_name)
        else:
            print("\n📚 Processing as playlist...")
            _process_playlist(db, processor, videos_found, user.id, folder_name)
        
        print("\n" + "="*60)
        print("✅ All videos processed successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


def _process_single_video(db, processor, video_path, owner_id, folder_name):
    """Process and add a single video to the database."""
    
    video_filename = os.path.basename(video_path)
    video_title = os.path.splitext(video_filename)[0]
    
    print(f"\n   Processing: {video_filename}")
    print(f"   - Video path: {video_path}")
    
    # Verify file exists
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    # Create unique storage path for this video
    video_id = str(uuid.uuid4())
    storage_path = os.path.join(owner_id, video_id)
    output_dir = os.path.join(setting.base_storage_path, storage_path)
    
    # Process the video (generate HLS, thumbnail, etc.)
    print("   - Generating HLS streams...")
    try:
        metadata = processor.process_video(video_path, output_dir)
    except Exception as e:
        print(f"   ❌ Failed to process video: {str(e)}")
        raise
    
    # Create video record
    video = Video(
        id=video_id,
        title=video_title,
        owner_id=owner_id,
        storage_path=storage_path,
        thumbnail_url=f"{storage_path}/thumbnail.jpg",
        status=VideoStatus.PROCESSED,
        duration_seconds=int(metadata["duration"]),
        width=metadata["width"],
        height=metadata["height"],
        size_bytes=metadata["size_bytes"]
    )
    
    db.add(video)
    db.commit()
    
    print(f"   ✅ Video added: '{video_title}' (ID: {video_id})")
    print(f"      Duration: {int(metadata['duration'])}s | Resolution: {metadata['width']}x{metadata['height']}")
    print(f"      Size: {metadata['size_bytes'] / (1024*1024):.2f} MB")
    print(f"      Variants: {', '.join(metadata['variants'])}")


def _process_playlist(db, processor, video_paths, owner_id, folder_name):
    """Process multiple videos and create a playlist."""
    
    # Create playlist
    playlist_id = str(uuid.uuid4())
    playlist_title = folder_name
    
    playlist = Playlist(
        id=playlist_id,
        title=playlist_title,
        owner_id=owner_id
    )
    
    db.add(playlist)
    db.commit()
    
    print(f"   ✅ Created playlist: '{playlist_title}' (ID: {playlist_id})")
    
    # Process each video
    for position, video_path in enumerate(video_paths, start=1):
        video_filename = os.path.basename(video_path)
        video_title = os.path.splitext(video_filename)[0]
        
        print(f"\n   [{position}/{len(video_paths)}] Processing: {video_filename}")
        print(f"       - Video path: {video_path}")
        
        # Verify file exists
        if not os.path.isfile(video_path):
            print(f"       ❌ Video file not found, skipping...")
            continue
        
        # Create unique storage path for this video
        video_id = str(uuid.uuid4())
        storage_path = os.path.join(owner_id, video_id)
        output_dir = os.path.join(setting.base_storage_path, storage_path)
        
        # Process the video
        print("       - Generating HLS streams...")
        try:
            metadata = processor.process_video(video_path, output_dir)
        except Exception as e:
            print(f"       ❌ Failed to process video: {str(e)}")
            continue
        
        # Create video record
        video = Video(
            id=video_id,
            title=video_title,
            owner_id=owner_id,
            storage_path=storage_path,
            thumbnail_url=f"{storage_path}/thumbnail.jpg",
            status=VideoStatus.PROCESSED,
            duration_seconds=int(metadata["duration"]),
            width=metadata["width"],
            height=metadata["height"],
            size_bytes=metadata["size_bytes"]
        )
        
        db.add(video)
        db.flush()  # Get the video ID
        
        # Create playlist mapping
        mapping = PlaylistVideoMapping(
            playlist_id=playlist_id,
            video_id=video_id,
            position=position
        )
        
        db.add(mapping)
        db.commit()
        
        print(f"       ✅ Added to playlist at position {position}")
        print(f"          Duration: {int(metadata['duration'])}s | Resolution: {metadata['width']}x{metadata['height']}")
        print(f"          Size: {metadata['size_bytes'] / (1024*1024):.2f} MB")
    
    print(f"\n   ✅ Playlist complete with {len(video_paths)} videos")


def main():
    """Main entry point with user input prompts."""
    
    print("="*60)
    print("  Video/Playlist Importer for Streamer")
    print("="*60)
    
    # Get username
    username = input("\nEnter username: ").strip()
    
    if not username:
        print("❌ Username cannot be empty")
        return
    
    # Get folder path
    folder_path = input("Enter full path to video folder: ").strip()
    
    # Remove quotes if user wrapped path in quotes
    folder_path = folder_path.strip("'\"")
    
    if not folder_path:
        print("❌ Folder path cannot be empty")
        return
    
    # Expand user path (handles ~)
    folder_path = os.path.expanduser(folder_path)
    folder_path = os.path.abspath(folder_path)
    
    print(f"\n📂 Using folder: {folder_path}")
    
    # Confirm before processing
    confirm = input("\nProceed with processing? (y/n): ").strip().lower()
    
    if confirm != 'y':
        print("❌ Operation cancelled")
        return
    
    print("\n" + "="*60)
    print("Starting video processing...")
    print("="*60)
    
    # Process videos
    add_videos_from_folder(username, folder_path)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
