# Copyright (c) 2025 @THECDERQUEEN
# Licensed under the MIT License.
# This file is part of @SHONA_BOTS
#SHONA-DECODER

import asyncio
import time

from pyrogram import enums, types

from AloneX import app, logger

DELETE_DELAY = 7


class VCLogger:
    def __init__(self):
        self.join_count: dict[tuple, int] = {}
        self.user_cache: dict[tuple, tuple] = {}
        self.vc_start_time: dict[int, float] = {}

    async def _get_user_info(self, chat_id: int, user_id: int) -> tuple:
        """Returns (name, username, role) for a participant, cached per chat."""
        key = (chat_id, user_id)
        if key in self.user_cache:
            return self.user_cache[key]

        name = "User"
        username = "Ignored"
        role = "Member"

        try:
            member = await app.get_chat_member(chat_id, user_id)
            if member:
                if member.user:
                    user = member.user
                    name = user.first_name or "User"
                    if user.last_name:
                        name += f" {user.last_name}"
                    username = f"@{user.username}" if user.username else "Ignored"

                if member.status == enums.ChatMemberStatus.OWNER:
                    role = "Owner"
                elif member.status == enums.ChatMemberStatus.ADMINISTRATOR:
                    role = "Admin"
        except Exception:
            pass

        self.user_cache[key] = (name, username, role)
        return name, username, role

    async def _get_vc_link(self, chat_id: int) -> str | None:
        try:
            chat = await app.get_chat(chat_id)
            if chat.username:
                return f"https://t.me/{chat.username}?videochat"
            if chat.invite_link:
                return f"{chat.invite_link}?videochat"
            link = await app.export_chat_invite_link(chat_id)
            return f"{link}?videochat" if link else None
        except Exception:
            return None

    async def _delete_later(self, chat_id: int, message_id: int) -> None:
        try:
            await asyncio.sleep(DELETE_DELAY)
            await app.delete_messages(chat_id, message_id)
        except Exception:
            pass

    async def _send(self, chat_id: int, user_id: int, joined: bool) -> None:
        name, username, role = await self._get_user_info(chat_id, user_id)
        mention = f'<a href="tg://user?id={user_id}">{name}</a>'
        tag = "#JoinVideoChat" if joined else "#LeaveVideoChat"
        action = f"Joined [{role}]" if joined else f"Left [{role}]"

        text = (
            f"<b>{tag}</b>\n\n"
            f"<blockquote>Name ➜ {mention}\n"
            f"Id ➜ <code>{user_id}</code>\n"
            f"Username ➜ {username}\n"
            f"Action ➜ {action}</blockquote>"
        )

        if joined:
            key = (chat_id, user_id)
            self.join_count[key] = self.join_count.get(key, 0) + 1
            text += f"\n🔄 <b>Join Count</b> ➜ <code>{self.join_count[key]}</code>"

        reply_markup = None
        vc_link = await self._get_vc_link(chat_id)
        if vc_link:
            reply_markup = types.InlineKeyboardMarkup(
                [[types.InlineKeyboardButton(text="Join Live Vc 📶", url=vc_link)]]
            )

        try:
            msg = await app.send_message(chat_id, text, reply_markup=reply_markup)
            asyncio.create_task(self._delete_later(chat_id, msg.id))
        except Exception as e:
            logger.error(f"[VCLogger] Failed to send notice for {chat_id}: {e}")

    async def notify_join(self, chat_id: int, user_id: int) -> None:
        await self._send(chat_id, user_id, joined=True)

    async def notify_leave(self, chat_id: int, user_id: int) -> None:
        await self._send(chat_id, user_id, joined=False)

    def clear_chat(self, chat_id: int) -> None:
        for key in [k for k in self.join_count if k[0] == chat_id]:
            del self.join_count[key]
        for key in [k for k in self.user_cache if k[0] == chat_id]:
            del self.user_cache[key]
        self.vc_start_time.pop(chat_id, None)

    def _format_duration(self, seconds: float) -> str:
        seconds = max(0, int(seconds))
        hours, rem = divmod(seconds, 3600)
        minutes, secs = divmod(rem, 60)
        if hours:
            return f"{hours}h:{minutes}m:{secs}s"
        if minutes:
            return f"{minutes}m:{secs}s"
        return f"{secs}s"

    async def notify_vc_started(self, chat_id: int) -> None:
        self.vc_start_time[chat_id] = time.time()
        text = "<blockquote>♻️ Video Chat Started!</blockquote>"

        try:
            await app.send_message(chat_id, text)
        except Exception as e:
            logger.error(f"[VCLogger] Failed to send VC start notice for {chat_id}: {e}")

    async def notify_vc_ended(self, chat_id: int) -> None:
        started = self.vc_start_time.pop(chat_id, None)
        duration = self._format_duration(time.time() - started) if started else None

        text = "<blockquote>⚠️ Video Chat Ended!"
        if duration:
            text += f"\n\n⏰ Duration : {duration}"
        text += "</blockquote>"

        try:
            await app.send_message(chat_id, text)
        except Exception as e:
            logger.error(f"[VCLogger] Failed to send VC end notice for {chat_id}: {e}")
