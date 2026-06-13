# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic

import re
import yt_dlp
import asyncio
import requests

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

    def valid(self, url: str) -> bool:
        return bool(re.match(self.regex, url))

    def invalid(self, url: str) -> bool:
        return bool(re.match(self.iregex, url))

    async def search(
        self,
        query: str,
        m_id: int,
        video: bool = False
    ) -> Track | None:

        try:
            _search = VideosSearch(
                query,
                limit=1,
                with_live=False
            )

            results = await _search.next()

        except Exception:
            return None

        if results and results["result"]:

            data = results["result"][0]

            return Track(
                id=data.get("id"),
                channel_name=data.get(
                    "channel",
                    {}
                ).get("name"),
                duration=data.get("duration"),
                duration_sec=utils.to_seconds(
                    data.get("duration")
                ),
                message_id=m_id,
                title=data.get("title")[:25],
                thumbnail=data.get(
                    "thumbnails",
                    [{}]
                )[-1].get("url").split("?")[0],
                url=data.get("link"),
                view_count=data.get(
                    "viewCount",
                    {}
                ).get("short"),
                video=video,
            )

        return None

    async def playlist(
        self,
        limit: int,
        user: str,
        url: str,
        video: bool
    ) -> list[Track | None]:

        tracks = []

        try:
            plist = await Playlist.get(url)

            for data in plist["videos"][:limit]:

                track = Track(
                    id=data.get("id"),
                    channel_name=data.get(
                        "channel",
                        {}
                    ).get("name", ""),
                    duration=data.get("duration"),
                    duration_sec=utils.to_seconds(
                        data.get("duration")
                    ),
                    title=data.get("title")[:25],
                    thumbnail=data.get(
                        "thumbnails"
                    )[-1].get("url").split("?")[0],
                    url=data.get("link").split("&list=")[0],
                    user=user,
                    view_count="",
                    video=video,
                )

                tracks.append(track)

        except Exception:
            pass

        return tracks

    async def api_download(
        self,
        video_id: str,
        video: bool = False
    ) -> str | None:

        try:
            endpoint = f"{YTPROXY}/info/{video_id}"

            headers = {
                "x-api-key": YT_API_KEY,
                "User-Agent": "Mozilla/5.0"
            }

            response = requests.get(
                endpoint,
                headers=headers,
                timeout=30
            )

            data = response.json()

            if data.get("status") != "success":
                return None

            file_url = (
                data.get("video_url")
                if video
                else data.get("audio_url")
            )

            if not file_url:
                return None

            ext = "mp4" if video else "webm"
            filename = f"downloads/{video_id}.{ext}"

            if Path(filename).exists():
                return filename

            r = requests.get(
                file_url,
                stream=True,
                timeout=60
            )

            with open(filename, "wb") as f:
                for chunk in r.iter_content(1024 * 1024):
                    if chunk:
                        f.write(chunk)

            return filename

        except Exception as ex:
            logger.warning(
                "API Download failed: %s",
                ex
            )
            return None

    async def download(
        self,
        video_id: str,
        video: bool = False
    ) -> str | None:

        # API FIRST
        api_file = await self.api_download(
            video_id,
            video
        )

        if api_file:
            return api_file

        # YT-DLP FALLBACK
        url = self.base + video_id

        ext = "mp4" if video else "webm"
        filename = f"downloads/{video_id}.{ext}"

        if Path(filename).exists():
            return filename

        base_opts = {
            "outtmpl": "downloads/%(id)s.%(ext)s",
            "quiet": True,
            "noplaylist": True,
            "geo_bypass": True,
            "no_warnings": True,
            "overwrites": False,
            "nocheckcertificate": True,
        }

        if video:
            ydl_opts = {
                **base_opts,
                "format": "(bestvideo[height<=?720][width<=?1280][ext=mp4])+(bestaudio)",
                "merge_output_format": "mp4",
            }
        else:
            ydl_opts = {
                **base_opts,
                "format": "bestaudio[ext=webm][acodec=opus]",
            }

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    ydl.download([url])

                except (
                    yt_dlp.utils.DownloadError,
                    yt_dlp.utils.ExtractorError
                ):
                    return None

                except Exception as ex:
                    logger.warning(
                        "Download failed: %s",
                        ex
                    )
                    return None

            return filename

        return await asyncio.to_thread(_download)
