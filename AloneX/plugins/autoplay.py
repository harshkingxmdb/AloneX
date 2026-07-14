# Copyright (c) 2025 TheHamkerAlone
# Licensed under the MIT License.
# This file is part of AloneXMusic


import asyncio

from pyrogram import filters, types

from AloneX import app, db, lang
from AloneX.helpers import buttons

DELETE_DELAY = 7


async def _delete_later(message: types.Message) -> None:
    try:
        await asyncio.sleep(DELETE_DELAY)
        await message.delete()
    except Exception:
        pass


@app.on_message(filters.command(["autoplay"]) & filters.group & ~app.bl_users)
@lang.language()
async def _autoplay(_, m: types.Message):
    mode = m.command[1].lower() if len(m.command) > 1 else None

    if mode in ("off", "disable"):
        await db.set_autoplay(m.chat.id, False)
        msg = await m.reply_text(
            m.lang.get(
                "autoplay_disabled",
                "🚫 Autoplay has been disabled.\n\nPlayback will stop once the queue is empty.",
            )
        )
        asyncio.create_task(_delete_later(msg))
        return

    if mode is not None and mode not in ("on", "enable"):
        msg = await m.reply_text(
            m.lang.get("autoplay_usage", "Usage: /autoplay [on|off]")
        )
        asyncio.create_task(_delete_later(msg))
        return

    # bare /autoplay or /autoplay on -> show the panel
    await m.reply_text(
        m.lang.get(
            "autoplay_panel_title",
            "🎶 <b>Autoplay:</b>\n\n"
            "• Keeps music playing automatically.\n"
            "• Ensures smooth and uninterrupted listening.\n"
            "• Designed for a seamless music experience.",
        ),
        reply_markup=buttons.autoplay_markup(m.lang),
    )
