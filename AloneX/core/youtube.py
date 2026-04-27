import os
import random
import asyncio
import yt_dlp
from pathlib import Path

from py_yt import VideosSearch

from AloneX import config, logger
from AloneX.helpers import Track, utils

# Safe import
try:
    from AloneX.helpers.NexGenApi import NexGenApi
except ImportError:
    NexGenApi = None


class YouTube:
    def __init__(self):
        self.api = None
        self.base = "https://www.youtube.com/watch?v="
        self.cookies = []
        self.checked = False
        self.cookie_dir = "AloneX/cookies"
        self.warned = False

        # NexGen API init
        if NexGenApi and config.API_URL and config.VIDEO_API_URL and config.API_KEY:
            try:
                self.api = NexGenApi(
                    config.API_URL,
                    config.VIDEO_API_URL,
                    config.API_KEY
                )
                logger.info("Using NexGenApi for downloads")
            except Exception as e:
                logger.warning(f"NexGenApi init failed: {e}")
                self.api = None

    def get_cookies(self):
        if not self.checked:
            if os.path.exists(self.cookie_dir):
                for file in os.listdir(self.cookie_dir):
                    if file.endswith(".txt"):
                        self.cookies.append(f"{self.cookie_dir}/{file}")
            self.checked = True

        if not self.cookies:
            if not self.warned:
                self.warned = True
                logger.warning("Cookies missing, downloads may fail")
            return None

        return random.choice(self.cookies)

    async def search(self, query: str, m_id: int, video: bool = False):
        try:
            search = VideosSearch(query, limit=1)
            results = await search.next()
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return None

        if not results or not results.get("result"):
            return None

        data = results["result"][0]

        thumbnail = None
        if data.get("thumbnails"):
            try:
                thumbnail = data["thumbnails"][0].get("url")
            except Exception:
                thumbnail = None

        return Track(
            id=data.get("id"),
            title=data.get("title"),
            duration=data.get("duration"),
            duration_sec=utils.to_seconds(data.get("duration")),
            url=data.get("link"),
            thumbnail=thumbnail,
            video=video,
            message_id=m_id,
            channel_name=data.get("channel") or data.get("channelName") or "Unknown"
        )

    async def download(self, video_id: str, video: bool = False):
        if self.api:
            try:
                file_path = await self.api.download(video_id, video)
                if file_path:
                    return file_path
            except Exception as e:
                logger.warning(f"NexGenApi failed: {e}")

        url = self.base + video_id
        ext = "mp4" if video else "webm"
        filename = f"downloads/{video_id}.{ext}"

        if Path(filename).exists():
            return filename

        ydl_opts = {
            "outtmpl": "downloads/%(id)s.%(ext)s",
            "quiet": True,
            "format": "bestaudio/best",
            "cookiefile": self.get_cookies(),
        }

        def _download():
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                return filename
            except Exception as e:
                logger.error(f"yt-dlp download failed: {e}")
                return None

        return await asyncio.to_thread(_download)
