# Copyright (c) 2025 TheHamkerAlone
# Licensed under the MIT License.
# This file is part of AloneXMusic


from pyrogram import filters, types

from AloneX import app


@app.on_message(filters.command(["getid"]) & ~app.bl_users)
async def _get_sticker_id(_, m: types.Message):
    target = m.reply_to_message if m.reply_to_message else m

    if target.sticker:
        return await m.reply_text(
            f"<b>Sticker file_id:</b>\n<code>{target.sticker.file_id}</code>"
        )

    if target.photo:
        return await m.reply_text(
            f"<b>Photo file_id:</b>\n<code>{target.photo.file_id}</code>"
        )

    await m.reply_text(
        "Send a sticker directly with /getid, or reply to a sticker/photo with /getid."
      )
