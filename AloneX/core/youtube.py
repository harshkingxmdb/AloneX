# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic

import os
import re
import yt_dlp
import random
import asyncio
import aiohttp
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

    def get_cookies(self):
        if not self.checked:

            if os.path.exists(self.cookie_dir):

                for file in os.listdir(self.cookie_dir):

                    if file.endswith(".txt"):

                        self.cookies.append(
                            f"{self.cookie_dir}/{file}"
                        )

            self.checked = True

        if not self.cookies:

            if not self.warned:

                self.warned = True

                logger.warning(
                    "Cookies are missing; downloads might fail."
                )

            return None

        return random.choice(self.cookies)

    async def save_cookies(
        self,
        urls: list[str]
    ) -> None:

        logger.info("Saving cookies from urls...")

        os.makedirs(self.cookie_dir, exist_ok=True)

        async with aiohttp.ClientSession() as session:

            for url in urls:

                name = url.split("/")[-1]

                link = "https://batbin.me/raw/" + name

                async with session.get(link) as resp:

                    resp.raise_for_status()

                    with open(
                        f"{self.cookie_dir}/{name}.txt",
                        "wb"
                    ) as fw:

                        fw.write(await resp.read())

        logger.info(
            f"Cookies saved in {self.cookie_dir}."
        )

    def valid(self, url: str) -> bool:

        return bool(
            re.match(self.regex, url)
        )

    def invalid(self, url: str) -> bool:

        return bool(
            re.match(self.iregex, url)
        )

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

        except Exception as ex:

            logger.warning(
                "Playlist error: %s",
                ex
            )

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

            if response.status_code != 200:

                logger.warning(
                    "API status code: %s",
                    response.status_code
                )

                return None

            data = response.json()

            if data.get("status") != "success":

                logger.warning(
                    "API failed response."
                )

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

            os.makedirs("downloads", exist_ok=True)

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

        # TRY API DOWNLOAD FIRST
        api_file = await self.api_download(
            video_id,
            video
        )

        if api_file:

            return api_file

        url = self.base + video_id

        os.makedirs("downloads", exist_ok=True)

        base_opts = {
            "outtmpl": "downloads/%(id)s.%(ext)s",
            "quiet": True,
            "noplaylist": True,
            "geo_bypass": True,
            "no_warnings": True,
            "overwrites": False,
            "nocheckcertificate": True,

            # HEROKU FIX
            "source_address": "0.0.0.0",

            # YOUTUBE FIX 2026
            "extractor_args": {
                "youtube": {
                    "player_client": [
                        "android",
                        "web"
                    ]
                }
            },

            # MOBILE HEADERS
            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Linux; Android 14)"
                )
            },
        }

        cookie_file = self.get_cookies()

        if cookie_file:

            base_opts["cookiefile"] = cookie_file

        if video:

            ydl_opts = {
                **base_opts,

                "format": (
                    "(bestvideo[height<=?720]"
                    "[ext=mp4])"
                    "+(bestaudio)"
                ),

                "merge_output_format": "mp4",
            }

        else:

            ydl_opts = {
                **base_opts,
                "format": "bestaudio/best",
            }

        def _download():

            try:

                with yt_dlp.YoutubeDL(
                    ydl_opts
                ) as ydl:

                    info = ydl.extract_info(
                        url,
                        download=True
                    )

                    file_path = ydl.prepare_filename(
                        info
                    )

                    # AUDIO FORMAT FIX
                    if not video:

                        possible_exts = [
                            ".webm",
                            ".m4a",
                            ".mp3",
                            ".opus"
                        ]

                        base = os.path.splitext(
                            file_path
                        )[0]

                        for ext in possible_exts:

                            p = base + ext

                            if os.path.exists(p):

                                return p

                    # VIDEO OUTPUT
                    if os.path.exists(file_path):

                        return file_path

                    # MP4 MERGE FIX
                    merged = (
                        os.path.splitext(
                            file_path
                        )[0] + ".mp4"
                    )

                    if os.path.exists(merged):

                        return merged

                    return None

            except (
                yt_dlp.utils.DownloadError,
                yt_dlp.utils.ExtractorError
            ) as ex:

                logger.warning(
                    "YT-DLP Error: %s",
                    ex
                )

                return None

            except Exception as ex:

                logger.warning(
                    "Download failed: %s",
                    ex
                )

                return None

        await asyncio.sleep(1)

        return await asyncio.to_thread(
            _download
              )
