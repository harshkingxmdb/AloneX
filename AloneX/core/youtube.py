# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.

import os
import re
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

    # ---------------- SEARCH ---------------- #

    async def search(self, query: str, m_id: int, video: bool = False):
        try:
            _search = VideosSearch(query, limit=1, with_live=False)
            results = await _search.next()
        except Exception as e:
            logger.error(f"Search Error: {e}")
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
        except Exception as e:
            logger.error(f"Playlist Error: {e}")

        return tracks

    # ---------------- DOWNLOAD (API ONLY) ---------------- #

    async def download(self, video_id: str, video: bool = False) -> str | None:
        url = self.base + video_id

        # Heroku-safe temp directory
        Path("/tmp").mkdir(exist_ok=True)

        api_url = f"{YTPROXY}/download"
        params = {
            "url": url,
            "api_key": YT_API_KEY,
            "video": str(video).lower(),
        }

        for attempt in range(3):  # retry system
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(api_url, params=params, timeout=60) as resp:

                        if resp.status != 200:
                            logger.error(f"API HTTP Error: {resp.status}")
                            continue

                        data = await resp.json()

                        if not data.get("status"):
                            logger.error("API returned failure status")
                            continue

                        file_url = data.get("file")
                        if not file_url:
                            logger.error("No file URL in API response")
                            continue

                        ext = "mp4" if video else "mp3"
                        filename = f"/tmp/{video_id}.{ext}"

                        async with session.get(file_url) as file_resp:
                            if file_resp.status != 200:
                                logger.error("File download failed")
                                continue

                            with open(filename, "wb") as f:
                                f.write(await file_resp.read())

                        logger.info("Downloaded via API successfully")
                        return filename

            except asyncio.TimeoutError:
                logger.warning(f"Timeout (Attempt {attempt+1})")
            except aiohttp.ClientError as e:
                logger.warning(f"Network Error: {e}")
            except Exception as e:
                logger.error(f"Unexpected Error: {e}")

            await asyncio.sleep(2)

        logger.error("Download failed after retries")
        return None

    # ---------------- VALIDATION ---------------- #

    def valid(self, url: str) -> bool:
        return bool(re.match(self.regex, url))

    def invalid(self, url: str) -> bool:
        return bool(re.match(self.iregex, url))
