import re
import asyncio
import time
import aiohttp
import yt_dlp

from urllib.parse import quote

from ShonaX.helpers import Track, utils


class YouTube:
    def __init__(self):

        # =========================
        # 🌐 API CONFIG
        # =========================

        self.API_URL = "https://pvtz.nexgenbots.xyz"

        self.VIDEO_API_URL = "https://api.video.nexgenbots.xyz"

        # 🔑 CHANGE ONLY THIS KEY AFTER 30 DAYS
        self.API_KEY = "30DxNexGenBotsb9296b"

        # =========================
        # BASE
        # =========================
        self.base = "https://www.youtube.com/watch?v="

        self.regex = re.compile(
            r"(https?://)?(www\.|m\.|music\.)?"
            r"(youtube\.com|youtu\.be)/"
        )

        # =========================
        # CACHE
        # =========================
        self.cache = {}
        self.cache_ttl = 3600

        # =========================
        # SESSION
        # =========================
        self.session = None

    # =========================
    # SESSION
    # =========================
    async def get_session(self):
        if not self.session or self.session.closed:

            timeout = aiohttp.ClientTimeout(total=20)

            self.session = aiohttp.ClientSession(
                timeout=timeout
            )

        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    # =========================
    # URL CHECK
    # =========================
    def is_url(self, text: str):
        return bool(re.match(self.regex, text))

    # =========================
    # CACHE
    # =========================
    def get_cache(self, query):

        data = self.cache.get(query)

        if not data:
            return None

        result, expiry = data

        if time.time() > expiry:
            del self.cache[query]
            return None

        return result

    def set_cache(self, query, result):

        self.cache[query] = (
            result,
            time.time() + self.cache_ttl
        )

    # =========================
    # API SEARCH
    # =========================
    async def api_search(self, query: str):

        try:
            session = await self.get_session()

            query = quote(query)

            url = (
                f"{self.API_URL}/search"
                f"?query={query}"
                f"&api_key={self.API_KEY}"
            )

            async with session.get(url) as resp:

                if resp.status != 200:
                    print("SEARCH API STATUS:", resp.status)
                    return None

                data = await resp.json()

            result = None

            if isinstance(data, list) and data:
                result = data[0]

            elif isinstance(data, dict):

                if data.get("result"):
                    result = data["result"][0]

                elif data.get("results"):
                    result = data["results"][0]

                else:
                    result = data

            if not result:
                return None

            video_id = (
                result.get("id")
                or result.get("videoId")
                or result.get("video_id")
            )

            if not video_id:
                return None

            return {
                "id": video_id,
                "title": result.get(
                    "title",
                    "Unknown"
                ),
                "channel": (
                    result.get("channel")
                    or result.get("channelTitle")
                    or result.get("uploader")
                    or "Unknown"
                ),
                "thumbnail": (
                    result.get("thumbnail")
                    or result.get("thumb")
                    or ""
                ),
                "duration": result.get(
                    "duration",
                    "Unknown"
                ),
                "duration_sec": int(
                    result.get("duration_sec", 0)
                ),
                "views": str(
                    result.get("views")
                    or result.get("view_count")
                    or ""
                ),
            }

        except Exception as e:
            print("API SEARCH ERROR:", e)
            return None

    # =========================
    # YTDLP FALLBACK
    # =========================
    async def ytdlp_search(self, query: str):

        def extract():

            try:
                opts = {
                    "quiet": True,
                    "no_warnings": True,
                }

                with yt_dlp.YoutubeDL(opts) as ydl:

                    data = ydl.extract_info(
                        f"ytsearch1:{query}",
                        download=False
                    )

                if not data:
                    return None

                entries = data.get("entries")

                if not entries:
                    return None

                return entries[0]

            except Exception as e:
                print("YTDLP SEARCH ERROR:", e)
                return None

        info = await asyncio.to_thread(extract)

        if not info:
            return None

        return {
            "id": info.get("id"),
            "title": info.get("title"),
            "channel": info.get(
                "uploader",
                "Unknown"
            ),
            "thumbnail": info.get(
                "thumbnail",
                ""
            ),
            "duration": utils.format_duration(
                info.get("duration", 0)
            ),
            "duration_sec": info.get(
                "duration",
                0
            ),
            "views": str(
                info.get("view_count", "")
            ),
        }

    # =========================
    # SEARCH
    # =========================
    async def search(
        self,
        query: str,
        m_id: int,
        video: bool = False
    ):

        try:
            cached = self.get_cache(query)

            if cached:
                return cached

            # =========================
            # URL SEARCH
            # =========================
            if self.is_url(query):

                return await self.get_track_from_url(
                    query,
                    m_id,
                    video
                )

            # =========================
            # API SEARCH
            # =========================
            data = await self.api_search(query)

            # =========================
            # FALLBACK
            # =========================
            if not data:
                data = await self.ytdlp_search(query)

            if not data:
                return None

            track = Track(
                id=data["id"],
                channel_name=data["channel"],
                duration=data["duration"],
                duration_sec=data["duration_sec"],
                message_id=m_id,
                title=(data["title"] or "")[:60],
                thumbnail=data["thumbnail"],
                url=self.base + data["id"],
                view_count=data["views"],
                video=video,
            )

            self.set_cache(query, track)

            return track

        except Exception as e:
            print("SEARCH ERROR:", e)
            return None

    # =========================
    # URL TRACK
    # =========================
    async def get_track_from_url(
        self,
        url: str,
        m_id: int,
        video: bool = False
    ):

        def extract():

            try:
                with yt_dlp.YoutubeDL(
                    self.ydl_opts()
                ) as ydl:

                    return ydl.extract_info(
                        url,
                        download=False
                    )

            except Exception as e:
                print("URL ERROR:", e)
                return None

        info = await asyncio.to_thread(extract)

        if not info:
            return None

        duration = info.get("duration", 0)

        return Track(
            id=info.get("id"),
            channel_name=info.get(
                "uploader",
                "Unknown"
            ),
            duration=utils.format_duration(duration),
            duration_sec=duration,
            message_id=m_id,
            title=(info.get("title") or "")[:60],
            thumbnail=info.get("thumbnail", ""),
            url=url,
            view_count=str(
                info.get("view_count", "")
            ),
            video=video,
        )

    # =========================
    # YTDLP OPTIONS
    # =========================
    def ydl_opts(self):

        return {
            "quiet": True,
            "no_warnings": True,
            "geo_bypass": True,
            "nocheckcertificate": True,
            "ignoreerrors": True,
            "retries": 10,
            "format": "bestaudio/best",
        }

    # =========================
    # STREAM
    # =========================
    async def stream(self, url_or_id: str):

        try:
            session = await self.get_session()

            video_id = (
                url_or_id.split("v=")[-1]
                if self.is_url(url_or_id)
                else url_or_id
            )

            api_url = (
                f"{self.VIDEO_API_URL}/stream"
                f"?id={video_id}"
                f"&api_key={self.API_KEY}"
            )

            async with session.get(api_url) as resp:

                if resp.status == 200:

                    data = await resp.json()

                    stream_url = (
                        data.get("url")
                        or data.get("stream")
                    )

                    if stream_url:
                        return stream_url

            # =========================
            # FALLBACK YTDLP
            # =========================
            url = (
                url_or_id
                if self.is_url(url_or_id)
                else self.base + url_or_id
            )

            def extract():

                try:
                    with yt_dlp.YoutubeDL(
                        self.ydl_opts()
                    ) as ydl:

                        info = ydl.extract_info(
                            url,
                            download=False
                        )

                        if info.get("url"):
                            return info["url"]

                        for fmt in reversed(
                            info.get("formats", [])
                        ):

                            if fmt.get("acodec") != "none":
                                return fmt["url"]

                except Exception as e:
                    print("STREAM ERROR:", e)
                    return None

            return await asyncio.to_thread(extract)

        except Exception as e:
            print("FINAL STREAM ERROR:", e)
            return None
