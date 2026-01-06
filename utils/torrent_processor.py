import os
import uuid
import logging
from utils.downloader import TorrentVideosDownloader
from utils.downloads_processor import DownloadedVideoProcessor
from models.videos import Video, VideoStatus, Playlist, PlaylistVideoMapping
from db import SessionLocal
from config import setting

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_and_process_torrent(magnet_link: str, owner_id: str, torrent_name: str = None):
    """
    Download and process videos from a torrent, creating database records and playlist if needed.
    
    Args:
        magnet_link: The magnet link to download
        owner_id: The user ID who owns these videos
        torrent_name: Optional name for the torrent (used as folder name)
    """
    downloader = TorrentVideosDownloader(setting.tmp_downloading_path)
    processor = DownloadedVideoProcessor(setting.base_storage_path, setting.tmp_downloading_path)
    db = SessionLocal()
    
    try:
        logger.info("Fetching torrent information...")
        torrent_info = downloader.get_info(magnet_link)
        logger.info(f"Torrent: {torrent_info['name']}, Files: {torrent_info['file_count']}, Total Size: {torrent_info['total_size'] / (1024**3):.2f} GB")
        
        folder_name = torrent_name or f"torrent_{uuid.uuid4().hex[:8]}"
        
        # Identify all video files from torrent metadata
        VIDEO_EXTENSIONS = {
            ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv",
            ".webm", ".mpeg", ".mpg", ".m4v", ".3gp",
            ".3g2", ".ts", ".vob", ".ogv"
        }
        
        video_files = []
        for file_info in torrent_info['files']:
            file_path = file_info['path']
            ext = os.path.splitext(file_path)[1].lower()
            if ext in VIDEO_EXTENSIONS:
                video_files.append(file_path)
        
        logger.info(f"Identified {len(video_files)} video file(s) in torrent")
        
        if not video_files:
            logger.warning("No video files found in torrent metadata. Skipping download.")
            return
        
        # Create video records for each identified video file BEFORE downloading
        video_records = []
        for video_file in video_files:
            video_name = os.path.basename(video_file)
            video_record = Video(
                title=video_name,
                owner_id=owner_id,
                storage_path=folder_name,
                status=VideoStatus.DOWNLOADING
            )
            db.add(video_record)
            video_records.append(video_record)
        
        db.commit()
        logger.info(f"Created {len(video_records)} video record(s) with DOWNLOADING status")
        
        # Create a playlist if multiple videos
        playlist = None
        if len(video_files) > 1:
            playlist = Playlist(
                title=torrent_info['name'],
                owner_id=owner_id
            )
            db.add(playlist)
            db.commit()
            logger.info(f"Created playlist: {playlist.title} (ID: {playlist.id})")
        
        logger.info("Downloading torrent...")
        download_path = downloader.download(magnet_link, folder_name)
        logger.info(f"Download completed: {download_path}")
        
        logger.info("Finding downloaded videos...")
        downloaded_vids = processor.find_all_videos(folder_name)
        logger.info(f"Found {len(downloaded_vids)} downloaded video(s)")
        
        logger.info(f"Found {len(downloaded_vids)} downloaded video(s)")
        
        if not downloaded_vids:
            # No videos found after download, mark all as failed
            for video_record in video_records:
                video_record.status = VideoStatus.FAILED
            db.commit()
            logger.warning("No videos found after download. Marked all as FAILED.")
            return
        
        # Match downloaded videos with database records by filename
        downloaded_video_map = {os.path.basename(vid_path): vid_path for vid_path in downloaded_vids}
        
        logger.info("Processing videos...")
        for idx, video_record in enumerate(video_records):
            try:
                video_filename = video_record.title
                
                if video_filename not in downloaded_video_map:
                    logger.warning(f"Video file not found for: {video_filename}")
                    video_record.status = VideoStatus.FAILED
                    db.commit()
                    continue
                
                vid_path = downloaded_video_map[video_filename]
                logger.info(f"[{idx+1}/{len(video_records)}] Processing: {video_filename}")
                
                video_record.status = VideoStatus.PROCESSING
                db.commit()
                
                # Create storage path: users/{user_id}/videos/{video_id}
                output_dir = os.path.join(
                    setting.base_storage_path, 
                    "users", 
                    owner_id, 
                    "videos", 
                    video_record.id
                )
                result = processor.process_video(vid_path, output_dir)
                
                # Store relative path from base_storage_path
                video_record.storage_path = f"users/{owner_id}/videos/{video_record.id}"
                video_record.duration_seconds = int(result['duration'])
                video_record.width = result['width']
                video_record.height = result['height']
                video_record.size_bytes = result['size_bytes']
                video_record.thumbnail_url = f"users/{owner_id}/videos/{video_record.id}/thumbnail.jpg"
                video_record.status = VideoStatus.PROCESSED
                db.commit()
                
                logger.info(f"Video processed: {result['width']}x{result['height']}, Variants: {', '.join(result['variants'])}")
                
                if playlist:
                    mapping = PlaylistVideoMapping(
                        playlist_id=playlist.id,
                        video_id=video_record.id,
                        position=idx
                    )
                    db.add(mapping)
                    db.commit()
                    logger.info(f"Added to playlist at position {idx}")
                    
            except Exception as e:
                logger.error(f"Error processing video: {str(e)}")
                video_record.status = VideoStatus.FAILED
                db.commit()
        
        successful = sum(1 for v in video_records if v.status == VideoStatus.PROCESSED)
        failed = sum(1 for v in video_records if v.status == VideoStatus.FAILED)
        logger.info(f"Summary - Total: {len(video_records)}, Successful: {successful}, Failed: {failed}")
        if playlist:
            logger.info(f"Playlist created: {playlist.title}")
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        for video_record in video_records:
            if video_record.status != VideoStatus.PROCESSED:
                video_record.status = VideoStatus.FAILED
        db.commit()
        
    finally:
        db.close()
