import asyncio
import threading
from queue import Queue
from utils.downloader import TorrentVideosDownloader
from utils.downloads_processor import DownloadedVideoProcessor
from config import setting
from utils.torrent_processor import download_and_process_torrent

downloader = TorrentVideosDownloader(setting.tmp_downloading_url)
downloads_processor = DownloadedVideoProcessor(setting.base_storage_url, setting.tmp_downloading_url)

# Queue for torrent processing
torrent_queue = Queue()

def process_torrent_queue():
    """Background worker that processes torrents from the queue."""
    while True:
        try:
            task = torrent_queue.get()
            if task is None:
                break
            
            magnet_link = task['magnet_link']
            owner_id = task['owner_id']
            torrent_name = task.get('torrent_name')
            
            download_and_process_torrent(magnet_link, owner_id, torrent_name)
            
            torrent_queue.task_done()
        except Exception as e:
            pass

# Start background worker thread
worker_thread = threading.Thread(target=process_torrent_queue, daemon=True)
worker_thread.start()