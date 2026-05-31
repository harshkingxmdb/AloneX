# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.

import os
import re
import yt_dlp
import random
import asyncio
import aiohttp
from pathlib import Path

from py_yt import Playlist, VideosSearch

from config import Config
from AloneX import logger
from AloneX.helpers import Track, utils

config = Config()

YT_API_KEY = config.YT_API_KEY
YTPROXY = config.YTPROXY_URL


class YouTube:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.cookies = []
        self.checked = False
        self.cookie_dir = "anony/cookies"
        self.warned = False

        self.regex = re.compile(
            r"(https?://)?(www\.|m\.|music\.)?"
            r"(youtube\.com/(watch\?v=|shorts/|playlist\?list=)|youtu\.be/)"
            r"([A-Za-z0-9_-]{11}|PL[A-Za-z0-9_-]+)([&?][^\s]*)?"
        )

        self.iregex = re.compile(
            r"https?://(?:www\.|m\.|music\.)?(?:youtube\.com|youtu\.be)"
            r"(?!/(watch\?v=[A-Za-z0-9_-]{11}|shorts/[A-Za-z0-9_-]{11}"
            r"|playlist\?list=PL[A-Za-z0-9_-]+|[A-Za-z0-9_-]{11}))\S*"
        )

    # ---------------- COOKIES ---------------- #

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
                logger.warning("Cookies missing, may fail downloads")
            return None

        return random.choice(self.cookies)

    # ---------------- SEARCH ---------------- #

    async def search(self, query: str, m_id: int, video: bool = False):
        try:
            _search = VideosSearch(query, limit=1, with_live=False)
            results = await _search.next()
        except Exception:
            return None

        if results and results["result"]:
            data = results["result"][0]
            return Track(
                id=data.get("id"),
                channel_name=data.get("channel", {}).get("name"),
                duration=data.get("duration"),
                duration_sec=utils.to_seconds(data.get("duration")),
                message_id=m_id,
                title=data.get("title")[:25],
                thumbnail=data.get("thumbnails", [{}])[-1].get("url").split("?")[0],
                url=data.get("link"),
                view_count=data.get("viewCount", {}).get("short"),
                video=video,
            )
        return None

    # ---------------- PLAYLIST ---------------- #

    async def playlist(self, limit: int, user: str, url: str, video: bool):
        tracks = []
        try:
            plist = await Playlist.get(url)
            for data in plist["videos"][:limit]:
                tracks.append(
                    Track(
                        id=data.get("id"),
                        channel_name=data.get("channel", {}).get("name", ""),
                        duration=data.get("duration"),
                        duration_sec=utils.to_seconds(data.get("duration")),
                        title=data.get("title")[:25],
                        thumbnail=data.get("thumbnails")[-1].get("url").split("?")[0],
                        url=data.get("link").split("&list=")[0],
                        user=user,
                        view_count="",
                        video=video,
                    )
                )
        except Exception:
            pass

        return tracks

    # ---------------- DOWNLOAD ---------------- #

    async def download(self, video_id: str, video: bool = False) -> str | None:
        url = self.base + video_id

        Path("downloads").mkdir(exist_ok=True)

        # 🔥 TRY YTPROXY API
        try:
            api_url = f"{YTPROXY}/download"
            params = {
                "url": url,
                "api_key": YT_API_KEY,
                "video": str(video).lower(),
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()

                        if data.get("status") and data.get("file"):
                            file_url = data["file"]
                            ext = "mp4" if video else "mp3"
                            filename = f"downloads/{video_id}.{ext}"

                            async with session.get(file_url) as file_resp:
                                with open(filename, "wb") as f:
                                    f.write(await file_resp.read())

                            logger.info("Downloaded via API")
                            return filename

        except Exception as e:
            logger.warning(f"API failed: {e}")

        # 🔁 FALLBACK yt-dlp
        cookie = self.get_cookies()

        ydl_opts = {
            "outtmpl": "downloads/%(id)s.%(ext)s",
            "quiet": True,
            "noplaylist": True,
        }

        if cookie:
            ydl_opts["cookiefile"] = cookie

        if video:
            ydl_opts["format"] = "best[ext=mp4]"
        else:
            ydl_opts["format"] = "bestaudio/best"

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=True)
                    return ydl.prepare_filename(info)
                except Exception as ex:
                    logger.warning(f"yt-dlp failed: {ex}")
                    return None

        return await asyncio.to_thread(_download)

    # ---------------- VALIDATION ---------------- #

    def valid(self, url: str) -> bool:
        return bool(re.match(self.regex, url))

    def invalid(self, url: str) -> bool:
        return bool(re.match(self.iregex, url))
