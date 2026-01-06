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
    downloader = TorrentVideosDownloader(setting.tmp_downloading_url)
    processor = DownloadedVideoProcessor(setting.base_storage_url, setting.tmp_downloading_url)
    db = SessionLocal()
    
    try:
        logger.info("Fetching torrent information...")
        torrent_info = downloader.get_info(magnet_link)
        logger.info(f"Torrent: {torrent_info['name']}, Files: {torrent_info['file_count']}, Total Size: {torrent_info['total_size'] / (1024**3):.2f} GB")
        
        folder_name = torrent_name or f"torrent_{uuid.uuid4().hex[:8]}"
        
        video_records = []
        temp_video = Video(
            title=torrent_info['name'],
            owner_id=owner_id,
            storage_path=folder_name,
            status=VideoStatus.DOWNLOADING
        )
        db.add(temp_video)
        db.commit()
        video_records.append(temp_video)
        logger.info(f"Created video record with ID: {temp_video.id}, Status: DOWNLOADING")
        
        logger.info("Downloading torrent...")
        download_path = downloader.download(magnet_link, folder_name)
        logger.info(f"Download completed: {download_path}")
        
        logger.info("Finding videos...")
        downloaded_vids = processor.find_all_videos(folder_name)
        logger.info(f"Found {len(downloaded_vids)} video(s)")
        
        if not downloaded_vids:
            temp_video.status = VideoStatus.FAILED
            db.commit()
            logger.warning("No videos found in torrent. Marked as FAILED.")
            return
        
        if len(downloaded_vids) > 1:
            db.delete(temp_video)
            video_records = []
            
            for vid_path in downloaded_vids:
                video_name = os.path.basename(vid_path)
                video_record = Video(
                    title=video_name,
                    owner_id=owner_id,
                    storage_path=folder_name,
                    status=VideoStatus.DOWNLOADING
                )
                db.add(video_record)
                video_records.append(video_record)
            db.commit()
            logger.info(f"Created {len(video_records)} video records")
        
        playlist = None
        if len(downloaded_vids) > 1:
            playlist = Playlist(
                title=torrent_info['name'],
                owner_id=owner_id
            )
            db.add(playlist)
            db.commit()
            logger.info(f"Created playlist: {playlist.title} (ID: {playlist.id})")
        
        logger.info("Processing videos...")
        for idx, (vid_path, video_record) in enumerate(zip(downloaded_vids, video_records)):
            try:
                logger.info(f"[{idx+1}/{len(downloaded_vids)}] Processing: {os.path.basename(vid_path)}")
                
                video_record.status = VideoStatus.PROCESSING
                db.commit()
                
                output_dir = os.path.join(setting.base_storage_url, video_record.id)
                result = processor.process_video(vid_path, output_dir)
                
                video_record.storage_path = video_record.id
                video_record.duration_seconds = int(result['duration'])
                video_record.width = result['width']
                video_record.height = result['height']
                video_record.size_bytes = result['size_bytes']
                video_record.thumbnail_url = f"{video_record.id}/thumbnail.jpg"
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
