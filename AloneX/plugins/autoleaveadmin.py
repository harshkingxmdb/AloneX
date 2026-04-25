# Copyright (c) 2025 TheHamkerAlone
# Licensed under the MIT License.
# This file is part of AloneXMusic
# ALONE-CODER

from pyrogram import enums, filters
from pyrogram.types import ChatMemberUpdated
from AloneX import app, logger

@app.on_chat_member_updated(filters.group)
async def autoleaveadmin(_, update: ChatMemberUpdated):
    if not update.new_chat_member:
        return

    # Check if the bot itself is the one updated
    if update.new_chat_member.user.id != app.id:
        return

    # Check if the new status is Administrator
    if update.new_chat_member.status == enums.ChatMemberStatus.ADMINISTRATOR:
        try:
            logger.info(f"Bot became admin in {update.chat.title} ({update.chat.id}). Leaving...")
            await app.send_message(
                update.chat.id,
                "Babe, I don't like being an admin in groups. I prefer being a guest. Leaving now! Bye-bye!"
            )
            await app.leave_chat(update.chat.id)
        except Exception as e:
            logger.error(f"Error while leaving chat {update.chat.id}: {e}")
