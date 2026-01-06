import os
import time
import libtorrent as lt

class TorrentVideosDownloader:
    def __init__(self, base_download_path: str):
        self.base_download_path = base_download_path
        self.session = lt.session()
        self.session.listen_on(6881, 6891)

    def download(self, magnet_link: str, folder_path: str) -> str:
        download_path = os.path.join(self.base_download_path, folder_path)

        if os.path.exists(download_path):
            raise Exception("Folder already exists")

        os.makedirs(download_path, exist_ok=False)

        params = lt.parse_magnet_uri(magnet_link)
        params.save_path = download_path

        handle = self.session.add_torrent(params)

        while not handle.has_metadata():
            time.sleep(1)

        while not handle.is_seed():
            status = handle.status()
            print(
                f"{status.progress * 100:.2f}% | "
                f"↓ {status.download_rate / 1024:.1f} KB/s | "
                f"Peers: {status.num_peers}"
            )
            time.sleep(1)

        handle.pause()
        return download_path

    def get_info(self, magnet_link: str) -> dict:
        """
        Fetch torrent metadata only (no download).
        """
        params = lt.parse_magnet_uri(magnet_link)
        params.save_path = self.base_download_path

        handle = self.session.add_torrent(params)

        while not handle.has_metadata():
            time.sleep(1)

        info = handle.get_torrent_info()
        files = info.files()

        file_list = []
        structure = {}

        for i in range(info.num_files()):
            path = files.file_path(i)
            size = files.file_size(i)

            file_list.append({
                "path": path,
                "size": size
            })

            parts = path.split(os.sep)
            current = structure
            for part in parts[:-1]:
                current = current.setdefault(part, {})
            current[parts[-1]] = size

        handle.pause()
        self.session.remove_torrent(handle)

        return {
            "name": info.name(),
            "info_hash": str(info.info_hash()),
            "total_size": info.total_size(),
            "file_count": info.num_files(),
            "files": file_list,
            "structure": structure
        }
