# Copyright (c) 2025 AnonymousX1025
# Modified: Stable version (cookies optional + async safe)

import os
import re
import yt_dlp
import random
import asyncio
import aiohttp

from pathlib import Path
from py_yt import Playlist, VideosSearch

from AloneX import logger
from AloneX.helpers import Track, utils
from config import Config

config = Config()

YT_API_KEY = config.YT_API_KEY
YTPROXY = config.YTPROXY_URL


class YouTube:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.cookies = []
        self.checked = False
        self.cookie_dir = "anony/cookies"

        self.regex = re.compile(
            r"(https?://)?(www\.|m\.|music\.)?"
            r"(youtube\.com/(watch\?v=|shorts/|playlist\?list=)|youtu\.be/)"
            r"([A-Za-z0-9_-]{11}|PL[A-Za-z0-9_-]+)"
        )

    # ✅ Cookies optional
    def get_cookies(self):
        if not self.checked:
            if os.path.exists(self.cookie_dir):
                for file in os.listdir(self.cookie_dir):
                    if file.endswith(".txt"):
                        self.cookies.append(
                            f"{self.cookie_dir}/{file}"
                        )
            self.checked = True

        return random.choice(self.cookies) if self.cookies else None

    def valid(self, url: str) -> bool:
        return bool(re.match(self.regex, url))

    # ✅ SEARCH
    async def search(self, query: str, m_id: int, video: bool = False):
        try:
            search = VideosSearch(query, limit=1)
            results = await search.next()
        except Exception:
            return None

        if results and results["result"]:
            data = results["result"][0]

            return Track(
                id=data.get("id"),
                title=data.get("title")[:25],
                url=data.get("link"),
                duration=data.get("duration"),
                duration_sec=utils.to_seconds(data.get("duration")),
                thumbnail=data.get("thumbnails", [{}])[-1].get("url"),
                channel_name=data.get("channel", {}).get("name"),
                view_count=data.get("viewCount", {}).get("short"),
                message_id=m_id,
                video=video,
            )

        return None

    # ✅ PLAYLIST
    async def playlist(self, limit, user, url, video):
        tracks = []

        try:
            plist = await Playlist.get(url)

            for data in plist["videos"][:limit]:
                tracks.append(
                    Track(
                        id=data.get("id"),
                        title=data.get("title")[:25],
                        url=data.get("link").split("&list=")[0],
                        duration=data.get("duration"),
                        duration_sec=utils.to_seconds(data.get("duration")),
                        thumbnail=data.get("thumbnails")[-1].get("url"),
                        channel_name=data.get("channel", {}).get("name", ""),
                        user=user,
                        video=video,
                    )
                )

        except Exception as e:
            logger.warning(f"Playlist error: {e}")

        return tracks

    # ✅ API DOWNLOAD (ASYNC FIXED)
    async def api_download(self, video_id: str, video=False):
        try:
            endpoint = f"{YTPROXY}/info/{video_id}"
            headers = {
                "x-api-key": YT_API_KEY,
                "User-Agent": "Mozilla/5.0"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint, headers=headers) as res:

                    if res.status != 200:
                        return None

                    data = await res.json()

                if data.get("status") != "success":
                    return None

                file_url = data.get("video_url") if video else data.get("audio_url")
                if not file_url:
                    return None

                ext = "mp4" if video else "webm"
                filename = f"downloads/{video_id}.{ext}"

                os.makedirs("downloads", exist_ok=True)

                if Path(filename).exists():
                    return filename

                async with session.get(file_url) as r:
                    if r.status != 200:
                        return None

                    with open(filename, "wb") as f:
                        async for chunk in r.content.iter_chunked(1024 * 1024):
                            f.write(chunk)

                return filename

        except Exception as e:
            logger.warning(f"API Download failed: {e}")
            return None

    # ✅ MAIN DOWNLOAD
    async def download(self, video_id: str, video=False):

        # TRY API FIRST
        file = await self.api_download(video_id, video)
        if file:
            return file

        url = self.base + video_id
        os.makedirs("downloads", exist_ok=True)

        base_opts = {
            "outtmpl": "downloads/%(id)s.%(ext)s",
            "quiet": True,
            "noplaylist": True,
            "geo_bypass": True,
            "nocheckcertificate": True,

            "source_address": "0.0.0.0",

            # ✅ 2026 stable fix
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "web"]
                }
            },

            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Linux; Android 14)"
            },
        }

        cookie = self.get_cookies()
        if cookie:
            base_opts["cookiefile"] = cookie

        if video:
            base_opts.update({
                "format": "(bestvideo[height<=?720][ext=mp4])+bestaudio",
                "merge_output_format": "mp4",
            })
        else:
            base_opts.update({
                "format": "bestaudio/best"
            })

        def run():
            try:
                with yt_dlp.YoutubeDL(base_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    file_path = ydl.prepare_filename(info)

                    base = os.path.splitext(file_path)[0]

                    for ext in [".mp4", ".webm", ".m4a", ".mp3", ".opus"]:
                        f = base + ext
                        if os.path.exists(f):
                            return f

                    return None

            except Exception as e:
                logger.warning(f"YT-DLP Error: {e}")
                return None

        return await asyncio.to_thread(run)
