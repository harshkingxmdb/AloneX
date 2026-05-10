# ALONE CODER

from os import getenv
from dotenv import load_dotenv

load_dotenv()


class Config:
    def __init__(self):

        self.API_ID = int(getenv("API_ID", "17596251"))

        self.API_HASH = getenv(
            "API_HASH",
            "e58343b4c0193e293e391daf97603fcd"
        )

        self.BOT_TOKEN = getenv(
            "BOT_TOKEN",
            "Apna Bot Token"
        )

        self.MONGO_URL = getenv(
            "MONGO_URL",
            "Apna Mongo Db Dalo"
        )

        self.LOGGER_ID = int(
            getenv("LOGGER_ID", "123456789")
        )

        self.OWNER_ID = int(
            getenv("OWNER_ID", "123456789")
        )

        self.SESSION1 = getenv(
            "SESSION",
            "Apna String Dalo"
        )

        self.SESSION2 = getenv("SESSION2", None)
        self.SESSION3 = getenv("SESSION3", None)

        self.SUPPORT_CHANNEL = getenv(
            "SUPPORT_CHANNEL",
            "https://t.me/shona_bots"
        )

        self.SUPPORT_CHAT = getenv(
            "SUPPORT_CHAT",
            "https://t.me/SHONA_SUPPORT"
        )

        # Boolean Settings
        self.AUTO_END = getenv(
            "AUTO_END",
            "False"
        ).lower() == "true"

        self.AUTO_LEAVE = getenv(
            "AUTO_LEAVE",
            "False"
        ).lower() == "true"

        self.VIDEO_PLAY = getenv(
            "VIDEO_PLAY",
            "True"
        ).lower() == "true"

        # Limits
        self.QUEUE_LIMIT = int(
            getenv("QUEUE_LIMIT", "200")
        )

        self.DURATION_LIMIT = int(
            getenv("DURATION_LIMIT", "17000")
        )

        self.PLAYLIST_LIMIT = int(
            getenv("PLAYLIST_LIMIT", "200")
        )

        # Cookies
        self.COOKIES_URL = [
            url
            for url in getenv(
                "COOKIES_URL",
                ""
            ).split(" ")
            if url and "batbin.me" in url
        ]

        # Images
        self.DEFAULT_THUMB = getenv(
            "DEFAULT_THUMB",
            "https://files.catbox.moe/s5orbf.jpg"
        )

        self.PING_IMG = getenv(
            "PING_IMG",
            "https://files.catbox.moe/s5orbf.jpg"
        )

        self.START_IMG = getenv(
            "START_IMG",
            "https://files.catbox.moe/s5orbf.jpg"
        )

        # API End Point
        self.YTPROXY_URL = getenv(
            "YTPROXY_URL",
            "https://tgapi.xbitcode.com"
        )

        self.YT_API_KEY = getenv(
            "YT_API_KEY",
            "xbit_93S-NHYcLZr7FzCnWl0i2JnDqhL8xd9H"
        )

    def check(self):

        missing = [
            var
            for var in [
                "API_ID",
                "API_HASH",
                "BOT_TOKEN",
                "MONGO_URL",
                "LOGGER_ID",
                "OWNER_ID",
                "SESSION1"
            ]
            if not getattr(self, var)
        ]

        if missing:
            raise SystemExit(
                f"Missing required environment variables: {', '.join(missing)}"
    )
