# =========================================
# SECURE YT.PY MADE BY ANONYMOUS 💗
# Anti-Leak + Secure Logger + Safe Cookies
# Shell Injection Fixed Version
# =========================================

import os
import re
import glob
import shutil
import random
import asyncio
import tempfile
import logging

from pathlib import Path
from typing import Union

import requests
import yt_dlp

from pyrogram.types import Message
from pyrogram.enums import MessageEntityType

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from py_yt import VideosSearch

from AloneX.utils.formatters import time_to_seconds

# =========================================
# LOGGER
# =========================================

LOGGER = logging.getLogger
logger = LOGGER(__name__)

# =========================================
# CONFIG IMPORT
# =========================================

from config import Config

config = Config()

YT_API_KEY = config.YT_API_KEY
YTPROXY = config.YTPROXY_URL

# =========================================
# SAFE LOGGER
# =========================================

SENSITIVE_PATTERNS = [
    r"(?i)api[_-]?key\s*[:=]\s*['\"]?.+?['\"]?",
    r"(?i)token\s*[:=]\s*['\"]?.+?['\"]?",
    r"(?i)session\s*[:=]\s*['\"]?.+?['\"]?",
    r"(?i)cookie\s*[:=]\s*['\"]?.+?['\"]?",
]


def safe_log(message: str):

    try:

        clean = str(message)

        for pattern in SENSITIVE_PATTERNS:

            clean = re.sub(
                pattern,
                "[REDACTED]",
                clean
            )

        logger.info(clean[:300])

    except Exception:

        logger.info("Secure log error")


# =========================================
# CONSTANTS
# =========================================

BASE_URL = "https://www.youtube.com/watch?v="
PLAYLIST_URL = "https://youtube.com/playlist?list="
YT_REGEX = r"(?:youtube\.com|youtu\.be)"

DOWNLOADS_DIR = "downloads"
COOKIES_DIR = "cookies"

Path(DOWNLOADS_DIR).mkdir(exist_ok=True)
Path(COOKIES_DIR).mkdir(exist_ok=True)

# =========================================
# COOKIE MANAGER
# =========================================


class SecureCookieManager:

    @staticmethod
    def get_cookie():

        try:

            files = glob.glob(
                os.path.join(
                    COOKIES_DIR,
                    "*.txt"
                )
            )

            valid = []

            for file in files:

                try:

                    size = os.path.getsize(file)

                    if size < 10:
                        continue

                    if size > 10 * 1024 * 1024:
                        continue

                    valid.append(file)

                except Exception:
                    continue

            if not valid:
                return None

            cookie = random.choice(valid)

            temp_cookie = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".txt"
            )

            shutil.copy(
                cookie,
                temp_cookie.name
            )

            return temp_cookie.name

        except Exception:
            return None

    @staticmethod
    def cleanup(cookie_path):

        try:

            if (
                cookie_path
                and os.path.exists(cookie_path)
            ):
                os.remove(cookie_path)

        except Exception:
            pass


# =========================================
# CLEAN LINK
# =========================================

def clean_link(link: str):

    if not link:
        return ""

    link = link.strip()

    if "&" in link:
        link = link.split("&")[0]

    if "?si=" in link:
        link = link.split("?si=")[0]

    elif "&si=" in link:
        link = link.split("&si=")[0]

    return link


# =========================================
# SECURE SESSION
# =========================================

def create_secure_session():

    session = requests.Session()

    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[
            429,
            500,
            502,
            503,
            504,
        ],
    )

    adapter = HTTPAdapter(
        max_retries=retries
    )

    session.mount(
        "http://",
        adapter
    )

    session.mount(
        "https://",
        adapter
    )

    session.headers.update({
        "User-Agent":
        "Mozilla/5.0"
    })

    return session


# =========================================
# YOUTUBE API
# =========================================

class YouTubeAPI:

    def __init__(self):

        self.base = BASE_URL
        self.regex = YT_REGEX
        self.listbase = PLAYLIST_URL

    async def exists(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            link = self.base + link

        return bool(
            re.search(
                self.regex,
                link
            )
        )

    async def url(
        self,
        message_1: Message
    ):

        messages = [message_1]

        if message_1.reply_to_message:
            messages.append(
                message_1.reply_to_message
            )

        for message in messages:

            if message.entities:

                for entity in message.entities:

                    if (
                        entity.type
                        == MessageEntityType.URL
                    ):

                        text = (
                            message.text
                            or message.caption
                        )

                        return text[
                            entity.offset:
                            entity.offset + entity.length
                        ]

            if message.caption_entities:

                for entity in message.caption_entities:

                    if (
                        entity.type
                        == MessageEntityType.TEXT_LINK
                    ):
                        return entity.url

        return None

    async def details(
        self,
        link: str,
        videoid=False
    ):

        if videoid:
            link = self.base + link

        link = clean_link(link)

        search = VideosSearch(
            link,
            limit=1
        )

        result = (
            await search.next()
        )["result"][0]

        duration = result.get(
            "duration"
        )

        duration_sec = (
            int(time_to_seconds(duration))
            if duration
            else 0
        )

        return (
            result["title"],
            duration,
            duration_sec,
            result["thumbnails"][0]["url"].split("?")[0],
            result["id"],
        )

    async def safe_exec(
        self,
        args: list
    ):

        try:

            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:

                safe_log(stderr.decode())

                return None

            return stdout.decode().strip()

        except Exception as e:

            safe_log(str(e))

            return None

    async def video(
        self,
        link: str,
        videoid=False
    ):

        if videoid:
            link = self.base + link

        link = clean_link(link)

        cookie = SecureCookieManager.get_cookie()

        try:

            cmd = [
                "yt-dlp",
                "-g",
                "-f",
                "best[height<=?720][width<=?1280]",
                link,
            ]

            if cookie:
                cmd.insert(1, "--cookies")
                cmd.insert(2, cookie)

            result = await self.safe_exec(cmd)

            if result:

                return (
                    1,
                    result.split("\n")[0]
                )

            return (
                0,
                "Failed"
            )

        finally:

            SecureCookieManager.cleanup(cookie)

    async def playlist(
        self,
        link,
        limit,
        user_id,
        videoid=False
    ):

        if videoid:
            link = self.listbase + link

        link = clean_link(link)

        cookie = SecureCookieManager.get_cookie()

        try:

            cmd = [
                "yt-dlp",
                "-i",
                "--flat-playlist",
                "--get-id",
                "--playlist-end",
                str(limit),
                "--skip-download",
                link,
            ]

            if cookie:
                cmd.insert(1, "--cookies")
                cmd.insert(2, cookie)

            result = await self.safe_exec(cmd)

            if not result:
                return []

            return [
                x.strip()
                for x in result.splitlines()
                if x.strip()
            ]

        finally:

            SecureCookieManager.cleanup(cookie)

    async def formats(
        self,
        link: str,
        videoid=False
    ):

        if videoid:
            link = self.base + link

        link = clean_link(link)

        cookie = SecureCookieManager.get_cookie()

        ytdl_opts = {
            "quiet": True,
            "nocheckcertificate": True,
        }

        if cookie:
            ytdl_opts["cookiefile"] = cookie

        formats_available = []

        try:

            with yt_dlp.YoutubeDL(
                ytdl_opts
            ) as ydl:

                info = ydl.extract_info(
                    link,
                    download=False
                )

                for fmt in info.get(
                    "formats",
                    []
                ):

                    filesize = fmt.get("filesize")

                    if not filesize:
                        continue

                    formats_available.append({

                        "format":
                        fmt.get("format"),

                        "filesize":
                        filesize,

                        "format_id":
                        fmt.get("format_id"),

                        "ext":
                        fmt.get("ext"),

                        "yturl":
                        link,
                    })

        except Exception as e:

            safe_log(str(e))

            return [], link

        finally:

            SecureCookieManager.cleanup(cookie)

        return (
            formats_available,
            link
)
        async def secure_download(
        self,
        url,
        filepath,
        headers
    ):

        session = create_secure_session()

        try:

            response = session.get(
                url,
                headers=headers,
                stream=True,
                timeout=60,
                allow_redirects=True,
            )

            response.raise_for_status()

            with open(
                filepath,
                "wb"
            ) as file:

                for chunk in response.iter_content(
                    1024 * 1024
                ):

                    if chunk:
                        file.write(chunk)

            return filepath

        except Exception:

            if os.path.exists(filepath):
                os.remove(filepath)

            return None

        finally:

            session.close()

    async def download(
        self,
        link: str,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
    ):

        try:

            if videoid:

                vid_id = link
                link = self.base + link

            else:

                (
                    _,
                    _,
                    _,
                    _,
                    vid_id
                ) = await self.details(link)

            headers = {

                "x-api-key":
                YT_API_KEY,

                "User-Agent":
                "Mozilla/5.0"
            }

            session = create_secure_session()

            async def audio_dl():

                try:

                    filepath = os.path.join(
                        DOWNLOADS_DIR,
                        f"{vid_id}.mp3"
                    )

                    if os.path.exists(filepath):
                        return filepath

                    response = session.get(
                        f"{YTPROXY}/info/{vid_id}",
                        headers=headers,
                        timeout=60,
                    )

                    data = response.json()

                    if (
                        data.get("status")
                        != "success"
                    ):
                        return None

                    audio_url = data.get(
                        "audio_url"
                    )

                    if not audio_url:
                        return None

                    return await self.secure_download(
                        audio_url,
                        filepath,
                        headers,
                    )

                except Exception as e:

                    safe_log(
                        f"Audio Error: {str(e)}"
                    )

                    return None

            async def video_dl():

                try:

                    filepath = os.path.join(
                        DOWNLOADS_DIR,
                        f"{vid_id}.mp4"
                    )

                    if os.path.exists(filepath):
                        return filepath

                    response = session.get(
                        f"{YTPROXY}/info/{vid_id}",
                        headers=headers,
                        timeout=60,
                    )

                    data = response.json()

                    if (
                        data.get("status")
                        != "success"
                    ):
                        return None

                    video_url = data.get(
                        "video_url"
                    )

                    if not video_url:
                        return None

                    return await self.secure_download(
                        video_url,
                        filepath,
                        headers,
                    )

                except Exception as e:

                    safe_log(
                        f"Video Error: {str(e)}"
                    )

                    return None

            if songvideo or video:

                downloaded_file = await video_dl()

            else:

                downloaded_file = await audio_dl()

            return (
                downloaded_file,
                True
            )

        except Exception as e:

            safe_log(
                f"Main Download Error: {str(e)}"
            )

            return (
                None,
                False
                    )
