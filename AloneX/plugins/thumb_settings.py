# This file added by kingxmdb
# @shona_bots
#ANONY PAPA KA FILE CHURAA LO 

from pyrogram import filters, types

from AloneX import app, db, lang
from AloneX.helpers import buttons, can_manage_vc


@app.on_message(filters.command(["thumb", "thumbnail"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _thumb(_, m: types.Message):
    enabled = await db.get_thumb(m.chat.id)
    status = "Enabled" if enabled else "Disabled"

    await m.reply_text(
        f"<b>{m.from_user.mention}</b>\n\n"
        f"Thumbnail Settings\n\n"
        f"Current Status: {status}\n\n"
        f"Click the button below to toggle the status:",
        reply_markup=buttons.thumb_markup(m.chat.id, enabled),
    )
