# Copyright (c) 2025 TheHamkerAlone
# Licensed under the MIT License.
# This file is part of AloneXMusic


import asyncio

from pyrogram import filters, types

from AloneX import app, db, lang
from AloneX.helpers import can_manage_vc

DELETE_DELAY = 7


async def _delete_later(message: types.Message) -> None:
    try:
        await asyncio.sleep(DELETE_DELAY)
        await message.delete()
    except Exception:
        pass


@app.on_message(filters.command(["autoplay"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _autoplay(_, m: types.Message):
    if len(m.command) < 2:
        status = await db.get_autoplay(m.chat.id)
        state = m.lang.get("autoplay_on", "Enabled") if status else m.lang.get(
            "autoplay_off", "Disabled"
        )
        msg = await m.reply_text(
            m.lang.get("autoplay_status", "Autoplay is currently: {0}").format(state)
        )
        asyncio.create_task(_delete_later(msg))
        return

    mode = m.command[1].lower()
    if mode in ("on", "enable"):
        await db.set_autoplay(m.chat.id, True)
        msg = await m.reply_text(
            m.lang.get(
                "autoplay_enabled",
                "🎶 Autoplay enabled.",
            )
        )
        asyncio.create_task(_delete_later(msg))
        return
    elif mode in ("off", "disable"):
        await db.set_autoplay(m.chat.id, False)
        msg = await m.reply_text(
            m.lang.get(
                "autoplay_disabled",
                "🚫 Autoplay disabled.",
            )
        )
        asyncio.create_task(_delete_later(msg))
        return
    else:
        msg = await m.reply_text(
            m.lang.get("autoplay_usage", "Usage: /autoplay [on|off]")
        )
        asyncio.create_task(_delete_later(msg))
        return
