# Copyright (c) 2025 TheHamkerAlone
# Licensed under the MIT License.
# This file is part of AloneXMusic
#ALONE-CODER

import time
import logging
import static_ffmpeg
static_ffmpeg.add_paths()
from logging.handlers import RotatingFileHandler

logging.basicConfig(
    format="[%(asctime)s - %(levelname)s] - %(name)s: %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    handlers=[
        RotatingFileHandler("log.txt", maxBytes=10485760, backupCount=5),
        logging.StreamHandler(),
    ],
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("ntgcalls").setLevel(logging.CRITICAL)
logging.getLogger("pymongo").setLevel(logging.ERROR)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("pytgcalls").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)


__version__ = "3.0.1"

from config import Config

config = Config()
config.check()
tasks = []
boot = time.time()

from AloneX.core.bot import Bot
app = Bot()

from AloneX.core.dir import ensure_dirs
ensure_dirs()

from AloneX.core.userbot import Userbot
userbot = Userbot()

from AloneX.core.mongo import MongoDB
db = MongoDB()

from AloneX.core.lang import Language
lang = Language()

from AloneX.core.telegram import Telegram
from AloneX.core.youtube import YouTube
tg = Telegram()
yt = YouTube()

from AloneX.helpers import Queue
queue = Queue()

from AloneX.core.calls import TgCall
anon = TgCall()


async def stop() -> None:
    logger.info("Stopping...")
    for task in tasks:
        task.cancel()
        try:
            await task
        except:
            pass

    await app.exit()
    await userbot.exit()
    await db.close()

    logger.info("Stopped.\n")
