import os
import ffmpeg

class DownloadedVideoProcessor:
    def __init__(self, base_storage_path, tmp_downloaded_path):
        self.tmp_downloaded_path = tmp_downloaded_path
        self.base_storage_path = base_storage_path
        self.presets = {
            "360p": (640, 360, 800_000),
            "720p": (1280, 720, 2_500_000),
            "1080p": (1920, 1080, 5_000_000),
        }

    def find_all_videos(self, folder_path):
        VIDEO_EXTENSIONS = {
            ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv",
            ".webm", ".mpeg", ".mpg", ".m4v", ".3gp",
            ".3g2", ".ts", ".vob", ".ogv"
        }

        base_path = os.path.join(self.tmp_downloaded_path, folder_path)

        if not os.path.isdir(base_path):
            return []

        videos = []

        for root, _, files in os.walk(base_path):
            for filename in files:
                ext = os.path.splitext(filename)[1].lower()
                if ext in VIDEO_EXTENSIONS:
                    videos.append(os.path.join(root, filename))

        videos.sort(key=lambda p: os.path.basename(p).lower())
        return videos

    def probe_video(self, input_path):
        probe = ffmpeg.probe(input_path)
        video_stream = next(
            s for s in probe["streams"] if s["codec_type"] == "video"
        )

        return {
            "width": int(video_stream["width"]),
            "height": int(video_stream["height"]),
            "duration": float(probe["format"]["duration"]),
            "size_bytes": int(probe["format"]["size"]),
        }

    def select_variants(self, width, height):
        variants = []
        for name, (w, h, _) in self.presets.items():
            if width >= w and height >= h:
                variants.append(name)
        return variants

    def generate_hls(self, input_path, output_dir, variants):
        os.makedirs(output_dir, exist_ok=True)

        for variant in variants:
            w, h, bitrate = self.presets[variant]

            variant_dir = os.path.join(output_dir, variant)
            os.makedirs(variant_dir, exist_ok=True)

            (
                ffmpeg
                .input(input_path)
                .filter("scale", w, h)
                .output(
                    os.path.join(variant_dir, "index.m3u8"),
                    format="hls",
                    hls_time=6,
                    hls_playlist_type="vod",
                    hls_segment_filename=os.path.join(
                        variant_dir, "seg_%03d.ts"
                    ),
                    vcodec="libx264",
                    acodec="aac",
                    video_bitrate=bitrate,
                    maxrate=bitrate,
                    bufsize=bitrate * 2,
                )
                .overwrite_output()
                .run(quiet=True)
            )

    def generate_adaptive_master_streamer(self, output_dir, variants):
        lines = ["#EXTM3U"]

        for variant in variants:
            w, h, bitrate = self.presets[variant]
            lines.append(
                f"#EXT-X-STREAM-INF:BANDWIDTH={bitrate},RESOLUTION={w}x{h}"
            )
            lines.append(f"{variant}/index.m3u8")

        master_path = os.path.join(output_dir, "master.m3u8")
        with open(master_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def generate_thumbnail(self, input_path, output_dir):
        os.makedirs(output_dir, exist_ok=True)

        (
            ffmpeg
            .input(input_path, ss=1)
            .output(
                os.path.join(output_dir, "thumbnail.jpg"),
                vframes=1,
                format="image2"
            )
            .overwrite_output()
            .run(quiet=True)
        )

    def process_video(self, input_path, output_dir):
        meta = self.probe_video(input_path)
        variants = self.select_variants(meta["width"], meta["height"])

        self.generate_hls(input_path, output_dir, variants)
        self.generate_adaptive_master_streamer(output_dir, variants)
        self.generate_thumbnail(input_path, output_dir)

        return {
            "variants": variants,
            "duration": meta["duration"],
            "width": meta["width"],
            "height": meta["height"],
            "size_bytes": meta["size_bytes"],
        }