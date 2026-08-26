# Copyright (c) 2025 @THECDERQUEEN
# Licensed under the MIT License.
# This file is part of @SHONA_BOTS
#SHONA-DECODER

from pyrogram import filters, types

from AloneX import app, db


def _format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds or 0))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h:{minutes}m:{secs}s"
    if minutes:
        return f"{minutes}m:{secs}s"
    return f"{secs}s"


@app.on_message(filters.video_chat_members_invited & filters.group & ~app.bl_users)
async def _vc_invited(_, message: types.Message):
    invited = []

    for user in message.video_chat_members_invited.users:
        try:
            invited.append(f'<a href="tg://user?id={user.id}">{user.first_name}</a>')
        except Exception:
            pass

    if not invited:
        return

    text = (
        f"<blockquote>{message.from_user.mention} Iɴᴠɪᴛᴇᴅ "
        f"{', '.join(invited)} Tᴏ Tʜᴇ Vɪᴅᴇᴏ Cʜᴀᴛ.</blockquote>"
    )

    try:
        await message.reply(text)
    except Exception:
        pass


@app.on_message(filters.video_chat_started & filters.group & ~app.bl_users)
async def _vc_started(_, message: types.Message):
    if not await db.get_vc_logger(message.chat.id):
        return

    text = "<blockquote>♻️ Video Chat Started!</blockquote>"
    try:
        await message.reply(text)
    except Exception:
        pass


@app.on_message(filters.video_chat_ended & filters.group & ~app.bl_users)
async def _vc_ended(_, message: types.Message):
    if not await db.get_vc_logger(message.chat.id):
        return

    duration = _format_duration(getattr(message.video_chat_ended, "duration", None))
    text = (
        "<blockquote>⚠️ Video Chat Ended!\n\n"
        f"⏰ Duration : {duration}</blockquote>"
    )
    try:
        await message.reply(text)
    except Exception:
        pass
