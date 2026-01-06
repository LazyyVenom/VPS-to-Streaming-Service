import asyncio
from torrentp import TorrentDownloader
import os

class TorrentVideosDownloader:
    def __init__(self, base_download_path):
        self.base_download_path = base_download_path

    def download(self, magnet_link, folder_path):
        download_path = os.path.join(self.base_download_path, folder_path)
        
        if os.path.exists(download_path):
            raise Exception("Folder Already Exisits!")
        
        os.makedirs(folder_path)

        torrent_file = TorrentDownloader(magnet_link, download_path, stop_after_download=True)
        asyncio.run(torrent_file.start_download())
        
        return download_path