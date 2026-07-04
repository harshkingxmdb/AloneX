# Copyright (c) 2025 TheHamkerAlone
# Licensed under the MIT License.
# This file is part of AloneXMusic


from pyrogram import filters, types

from AloneX import app, db, lang
from AloneX.helpers import can_manage_vc


@app.on_message(filters.command(["autoplay"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _autoplay(_, m: types.Message):
    if len(m.command) < 2:
        status = await db.get_autoplay(m.chat.id)
        state = m.lang.get("autoplay_on", "Enabled") if status else m.lang.get(
            "autoplay_off", "Disabled"
        )
        return await m.reply_text(
            m.lang.get("autoplay_status", "Autoplay is currently: {0}").format(state)
        )

    mode = m.command[1].lower()
    if mode in ("on", "enable"):
        await db.set_autoplay(m.chat.id, True)
        return await m.reply_text(
            m.lang.get(
                "autoplay_enabled",
                "🎶 Autoplay has been enabled.\n\nWhen the queue runs out, I'll automatically keep playing related songs.",
            )
        )
    elif mode in ("off", "disable"):
        await db.set_autoplay(m.chat.id, False)
        return await m.reply_text(
            m.lang.get(
                "autoplay_disabled",
                "🚫 Autoplay has been disabled.\n\nPlayback will stop once the queue is empty.",
            )
        )
    else:
        return await m.reply_text(
            m.lang.get("autoplay_usage", "Usage: /autoplay [on|off]")
        )