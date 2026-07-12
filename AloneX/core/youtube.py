import os
import re
import asyncio
import aiohttp
import yt_dlp
from py_yt import VideosSearch, Playlist
from AloneX import logger, config
from AloneX.helpers import Track, utils

API_URL = "https://teaminflex.xyz"
DOWNLOAD_DIR = "downloads"


class YouTube:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = re.compile(
            r"(https?://)?(www\.|m\.|music\.)?"
            r"(youtube\.com/(watch\?v=|shorts/|playlist\?list=)|youtu\.be/)"
            r"([A-Za-z0-9_-]{11}|PL[A-Za-z0-9_-]+)([&?][^\s]*)?"
        )

    # ---------------- basic helpers ----------------

    def valid(self, url: str) -> bool:
        return bool(re.match(self.regex, url))

    async def search(self, query: str, m_id: int, video: bool = False) -> Track | None:
        try:
            _search = VideosSearch(query, limit=1)
            results = await _search.next()
            if results and results["result"]:
                data = results["result"][0]
                return Track(
                    id=data.get("id"),
                    channel_name=data.get("channel", {}).get("name"),
                    duration=data.get("duration"),
                    duration_sec=utils.to_seconds(data.get("duration")) if data.get("duration") else 0,
                    message_id=m_id,
                    title=data.get("title")[:25],
                    thumbnail=data.get("thumbnails", [{}])[-1].get("url").split("?")[0],
                    url=data.get("link"),
                    view_count=data.get("viewCount", {}).get("short"),
                    video=video,
                )
        except Exception as e:
            logger.error(f"Search error: {e}")
        return None

    async def playlist(self, limit: int, user: str, url: str, video: bool) -> list[Track]:
        tracks = []
        try:
            plist = await Playlist.get(url)
            for data in plist.get("videos", [])[:limit]:
                track = Track(
                    id=data.get("id"),
                    channel_name=data.get("channel", {}).get("name", ""),
                    duration=data.get("duration"),
                    duration_sec=utils.to_seconds(data.get("duration")) if data.get("duration") else 0,
                    title=data.get("title")[:25],
                    thumbnail=data.get("thumbnails", [{}])[-1].get("url").split("?")[0],
                    url=data.get("link").split("&list=")[0],
                    user=user,
                    view_count="",
                    video=video,
                )
                tracks.append(track)
        except Exception as e:
            logger.error(f"Playlist error: {e}")
        return tracks

    # ---------------- download (teaminflex.xyz API) ----------------

    async def download(self, video_id: str, video: bool = False) -> str | None:
        if not video_id or len(video_id) < 3:
            return None

        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        ext = "mkv" if video else "webm"
        file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.{ext}")

        if os.path.exists(file_path):
            return file_path

        max_retries = 3
        retry_delay = 1  # seconds, flat delay — keep response fast
        transient_statuses = {502, 503, 504}

        for attempt in range(1, max_retries + 1):
            try:
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as session:
                    payload = {"url": video_id, "type": "video" if video else "audio"}
                    headers = {
                        "Content-Type": "application/json",
                        "X-API-KEY": config.YOUTUBE_API_KEY
                    }

                    # Step 1: Trigger API
                    async with session.post(f"{API_URL}/download", json=payload, headers=headers) as response:
                        if response.status == 401:
                            logger.error("[API] Invalid API key")
                            return None

                        if response.status in transient_statuses:
                            logger.warning(
                                f"[API] returned {response.status} (attempt {attempt}/{max_retries}) for {video_id}"
                            )
                            if attempt < max_retries:
                                await asyncio.sleep(retry_delay)
                                continue
                            logger.error(f"[API] gave up after {max_retries} attempts for {video_id}")
                            return None

                        if response.status != 200:
                            logger.error(f"[API] returned {response.status}")
                            return None

                        try:
                            data = await response.json()
                        except Exception as e:
                            logger.warning(
                                f"[API] invalid JSON response (attempt {attempt}/{max_retries}) for {video_id}: {e}"
                            )
                            if attempt < max_retries:
                                await asyncio.sleep(retry_delay)
                                continue
                            logger.error(f"[API] gave up after {max_retries} attempts for {video_id}")
                            return None

                        if data.get("status") != "success" or not data.get("download_url"):
                            logger.error(f"[API] response error: {data}")
                            if attempt < max_retries:
                                await asyncio.sleep(retry_delay)
                                continue
                            return None

                        download_link = f"{API_URL}{data['download_url']}"

                    # Step 2: Download file
                    async with session.get(download_link) as file_response:
                        if file_response.status in transient_statuses:
                            logger.warning(
                                f"[API] file download returned {file_response.status} (attempt {attempt}/{max_retries}) for {video_id}"
                            )
                            if attempt < max_retries:
                                await asyncio.sleep(retry_delay)
                                continue
                            logger.error(f"[API] gave up after {max_retries} attempts for {video_id}")
                            return None

                        if file_response.status != 200:
                            logger.error(f"[API] Download failed ({file_response.status})")
                            if attempt < max_retries:
                                await asyncio.sleep(retry_delay)
                                continue
                            return None

                        with open(file_path, "wb") as f:
                            async for chunk in file_response.content.iter_chunked(8192):
                                f.write(chunk)

                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    return file_path

                # File ended up missing/empty despite a "successful" response —
                # retry instead of silently giving up so transient glitches
                # (connection reset mid-download, truncated body, etc.) don't
                # cause a false "download failed" on the first blip.
                logger.warning(
                    f"[API] downloaded file was empty/missing (attempt {attempt}/{max_retries}) for {video_id}"
                )
                if os.path.exists(file_path):
                    try: os.remove(file_path)
                    except: pass
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)
                    continue
                logger.error(f"[API] gave up after {max_retries} attempts for {video_id}: file kept coming back empty")
                return None

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning(
                    f"[API] network error (attempt {attempt}/{max_retries}) for {video_id}: {e}"
                )
                if os.path.exists(file_path):
                    try: os.remove(file_path)
                    except: pass
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)
                    continue
                logger.error(f"[API] gave up after {max_retries} attempts for {video_id}: {e}")
                return None

            except Exception as e:
                logger.error(f"Download exception for ID {video_id} (attempt {attempt}/{max_retries}): {e}")
                if os.path.exists(file_path):
                    try: os.remove(file_path)
                    except: pass
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)
                    continue
                return None

        return None

    # ---------------- autoplay helpers ----------------

    def _format_duration(self, seconds: int) -> str:
        seconds = max(int(seconds or 0), 0)
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

    def _format_views(self, count) -> str:
        if not count:
            return ""
        count = int(count)
        if count >= 1_000_000:
            return f"{count / 1_000_000:.1f}M views"
        if count >= 1_000:
            return f"{count / 1_000:.1f}K views"
        return f"{count} views"

    def _extract_related(self, video_id: str) -> dict | None:
        opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
            "skip_download": True,
            "ignoreerrors": True,
            "geo_bypass": True,
            "socket_timeout": 10,
            "retries": 1,
            "extractor_retries": 1,
            "extractor_args": {"youtube": {"player_client": ["android"]}},
        }
        url = f"https://www.youtube.com/watch?v={video_id}&list=RD{video_id}"
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    async def _related_from_mix(
        self, video_id: str, played: set[str]
    ) -> Track | None:
        loop = asyncio.get_event_loop()
        try:
            info = await asyncio.wait_for(
                loop.run_in_executor(None, self._extract_related, video_id),
                timeout=20,
            )
        except asyncio.TimeoutError:
            logger.warning(f"[Autoplay] Mix fetch timed out for {video_id}.")
            return None
        except Exception as e:
            logger.error(f"[Autoplay] Mix fetch failed for {video_id}: {e}")
            return None

        entries = (info or {}).get("entries") or []
        for entry in entries:
            if not entry:
                continue

            eid = entry.get("id")
            if not eid or eid in played:
                continue

            title = entry.get("title") or "Unknown"
            if title.lower() in ("[deleted video]", "[private video]"):
                continue

            duration = int(entry.get("duration") or 0)
            if duration <= 0 or duration > config.DURATION_LIMIT:
                continue

            thumbs = entry.get("thumbnails") or []
            thumbnail = thumbs[-1]["url"].split("?")[0] if thumbs else None

            return Track(
                id=eid,
                channel_name=entry.get("channel") or entry.get("uploader") or "YouTube",
                duration=self._format_duration(duration),
                duration_sec=duration,
                title=title[:25],
                thumbnail=thumbnail,
                url=f"https://www.youtube.com/watch?v={eid}",
                view_count=self._format_views(entry.get("view_count")),
                video=False,
            )

        return None

    async def _related_from_search(
        self, current: Track, played: set[str]
    ) -> Track | None:
        """Fallback used when YouTube blocks the mix-playlist scrape (common on
        server/cloud IPs). Reuses the same search backend that
        already powers /play, so it works wherever normal search works."""
        queries = []
        if current.channel_name:
            queries.append(f"{current.channel_name}")
        if current.title:
            queries.append(f"{current.title}")

        for query in queries:
            try:
                _search = VideosSearch(query, limit=8)
                results = await _search.next()
            except Exception as e:
                logger.error(f"[Autoplay] Search fallback failed for {query!r}: {e}")
                continue

            for data in (results or {}).get("result", []):
                eid = data.get("id")
                if not eid or eid in played:
                    continue

                duration_str = data.get("duration")
                duration_sec = utils.to_seconds(duration_str) if duration_str else 0
                if not duration_sec or duration_sec > config.DURATION_LIMIT:
                    continue

                return Track(
                    id=eid,
                    channel_name=data.get("channel", {}).get("name") or "YouTube",
                    duration=duration_str,
                    duration_sec=duration_sec,
                    title=(data.get("title") or "Unknown")[:25],
                    thumbnail=(data.get("thumbnails", [{}])[-1].get("url") or "").split("?")[0] or None,
                    url=data.get("link"),
                    view_count=data.get("viewCount", {}).get("short"),
                    video=False,
                )

        return None

    async def get_related(
        self, current: Track, played: list[str] | None = None
    ) -> Track | None:
        """Fetch the next autoplay track, skipping anything already played in
        this session. Tries YouTube's related mix first, falling back to a
        text search (same backend as /play) if the mix is blocked or empty —
        this is common on server/cloud IPs."""
        if not current or not current.id:
            return None

        played = set(played or [])
        played.add(current.id)

        related = await self._related_from_mix(current.id, played)
        if related:
            return related

        logger.info(
            f"[Autoplay] Mix returned nothing for {current.id}, trying search fallback."
        )
        related = await self._related_from_search(current, played)
        if related:
            return related

        logger.warning(f"[Autoplay] No related track found for {current.id}.")
        return None
