import asyncio
import os
import re
from typing import Union
import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from py_yt import VideosSearch, Playlist
import aiohttp

API_URL = os.environ.get("SHRUTI_API_URL", "https://api.shrutibots.site")
API_KEY = os.environ.get("SHRUTI_API_KEY", "ShrutiBotsq0pta5RkvDV1YH7lSaDU")

DOWNLOAD_DIR = "downloads"

# ✅ STRICT YouTube ID validation (11 chars typical)
YOUTUBE_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{6,15}$")


def sanitize_video_id(link: str) -> Union[str, None]:
    """Extract and validate video ID safely"""
    if "youtube.com" in link or "youtu.be" in link:
        if "v=" in link:
            vid = link.split("v=")[-1].split("&")[0]
        elif "youtu.be/" in link:
            vid = link.split("youtu.be/")[-1].split("?")[0]
        else:
            return None
    else:
        vid = link

    if YOUTUBE_ID_REGEX.match(vid):
        return vid
    return None


def safe_path(filename: str) -> str:
    """Prevent path traversal"""
    filename = os.path.basename(filename)
    return os.path.join(DOWNLOAD_DIR, filename)


def time_to_seconds(time):
    return sum(int(x) * 60 ** i for i, x in enumerate(reversed(str(time).split(":"))))


async def download_file(video_id: str, filetype: str) -> Union[str, None]:
    """Generic secure downloader"""
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    filename = f"{video_id}.{filetype}"
    file_path = safe_path(filename)

    # ✅ prevent overwrite abuse
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        return file_path

    try:
        timeout = aiohttp.ClientTimeout(total=300 if filetype == "mp3" else 600)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                f"{API_URL}/download",
                params={
                    "url": video_id,
                    "type": "audio" if filetype == "mp3" else "video",
                    "api_key": API_KEY,
                },
            ) as resp:

                if resp.status != 200:
                    return None

                with open(file_path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(1024 * 128):
                        f.write(chunk)

        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            return file_path

    except Exception:
        if os.path.exists(file_path):
            os.remove(file_path)

    return None


async def download_song(link: str) -> Union[str, None]:
    video_id = sanitize_video_id(link)
    if not video_id:
        return None
    return await download_file(video_id, "mp3")


async def download_video(link: str) -> Union[str, None]:
    video_id = sanitize_video_id(link)
    if not video_id:
        return None
    return await download_file(video_id, "mp4")



class Track:
    def __init__(
        self,
        id,
        title,
        duration,
        duration_sec,
        thumb,
        file_path=None,
        video=False,
        user="Unknown",
        message_id=0,
    ):
        self.id = id
        self.title = title
        self.duration = duration
        self.duration_sec = duration_sec

        # Thumbnail support
        self.thumb = thumb
        self.thumbnail = thumb

        self.file_path = file_path
        self.video = video
        self.user = user
        self.message_id = message_id
        self.time = 0

        # Thumbnail.py ke liye required
        self.channel_name = "YouTube"
        self.view_count = "0 Views"

        self.url = f"https://www.youtube.com/watch?v={id}"

class YouTubeAPI:

    async def search(self, query, message_id=None, video=False):
    try:
        results = VideosSearch(query, limit=1)
        data = (await results.next())["result"][0]

        track = Track(
            id=data["id"],
            title=data["title"],
            duration=data.get("duration", "0:00"),
            duration_sec=time_to_seconds(
                data.get("duration", "0:00")
            ),
            thumb=data["thumbnails"][0]["url"],
            video=video,
            message_id=message_id or 0,
        )

        try:
            track.channel_name = data.get(
                "channel", {}
            ).get("name", "YouTube")
        except:
            pass

        try:
            track.view_count = data.get(
                "viewCount", {}
            ).get("short", "0 Views")
        except:
            pass

        return track

    except Exception as e:
        print(f"Search Error: {e}")
        return None

    async def download(self, video_id, video=False):
        if video:
            return await download_video(video_id)
        return await download_song(video_id)

    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.listbase = "https://youtube.com/playlist?list="
        self.regex = r"(youtube\.com|youtu\.be)"

    async def exists(self, link: str) -> bool:
        return bool(re.search(self.regex, link))

    async def url(self, message: Message) -> Union[str, None]:
        messages = [message]
        if message.reply_to_message:
            messages.append(message.reply_to_message)

        for msg in messages:
            if msg.entities:
                for entity in msg.entities:
                    if entity.type == MessageEntityType.URL:
                        text = msg.text or msg.caption
                        return text[entity.offset: entity.offset + entity.length]
        return None

    async def details(self, link: str):
        video_id = sanitize_video_id(link)
        if not video_id:
            return None

        results = VideosSearch(video_id, limit=1)
        data = (await results.next())["result"][0]

        return (
            data["title"],
            data["duration"],
            time_to_seconds(data["duration"]) if data["duration"] else 0,
            data["thumbnails"][0]["url"],
            data["id"],
        )

    async def video(self, link: str):
        file = await download_video(link)
        if file:
            return 1, file
        return 0, "Download failed"

    async def playlist(self, link, limit=10):
        try:
            plist = await Playlist.get(link)
        except Exception:
            return []

        return [
            v.get("id")
            for v in (plist.get("videos") or [])[:limit]
            if v and v.get("id")
        ]

    async def formats(self, link: str):
        video_id = sanitize_video_id(link)
        if not video_id:
            return [], link

        ydl = yt_dlp.YoutubeDL({"quiet": True})

        with ydl:
            info = ydl.extract_info(self.base + video_id, download=False)

        formats = []
        for f in info.get("formats", []):
            if "dash" not in str(f.get("format", "")).lower():
                formats.append({
                    "format": f.get("format"),
                    "filesize": f.get("filesize"),
                    "format_id": f.get("format_id"),
                    "ext": f.get("ext"),
                })

        return formats, link


YouTube = YouTubeAPI()
