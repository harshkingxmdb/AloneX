# Copyright (c) 2025 TheHamkerAlone
# Licensed under the MIT License.
# This file is part of AloneXMusic


import re
import asyncio

from pyrogram import filters, types

from AloneX import anon, app, db, lang, queue, tg, yt
from AloneX.helpers import admin_check, buttons, can_manage_vc


@app.on_callback_query(filters.regex("cancel_dl") & ~app.bl_users)
@lang.language()
async def cancel_dl(_, query: types.CallbackQuery):
    await query.answer()
    await tg.cancel(query)


@app.on_callback_query(filters.regex("controls") & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _controls(_, query: types.CallbackQuery):
    args = query.data.split()
    action, chat_id = args[1], int(args[2])
    qaction = len(args) == 4
    user = query.from_user.mention

    if not await db.get_call(chat_id):
        return await query.answer(query.lang["not_playing"], show_alert=True)

    if action == "status":
        return await query.answer()
    await query.answer(query.lang["processing"], show_alert=True)

    if action == "pause":
        if not await db.playing(chat_id):
            return await query.answer(
                query.lang["play_already_paused"], show_alert=True
            )
        await anon.pause(chat_id)
        if qaction:
            return await query.edit_message_reply_markup(
                reply_markup=buttons.queue_markup(chat_id, query.lang["paused"], False)
            )
        status = query.lang["paused"]
        reply = query.lang["play_paused"].format(user)

    elif action == "resume":
        if await db.playing(chat_id):
            return await query.answer(query.lang["play_not_paused"], show_alert=True)
        await anon.resume(chat_id)
        if qaction:
            return await query.edit_message_reply_markup(
                reply_markup=buttons.queue_markup(chat_id, query.lang["playing"], True)
            )
        reply = query.lang["play_resumed"].format(user)

    elif action == "skip":
        await anon.play_next(chat_id)
        status = query.lang["skipped"]
        reply = query.lang["play_skipped"].format(user)

    elif action == "force":
        pos, media = queue.check_item(chat_id, args[3])
        if not media or pos == -1:
            return await query.edit_message_text(query.lang["play_expired"])

        m_id = queue.get_current(chat_id).message_id
        queue.force_add(chat_id, media, remove=pos)
        try:
            await app.delete_messages(
                chat_id=chat_id, message_ids=[m_id, media.message_id], revoke=True
            )
            media.message_id = None
        except:
            pass

        msg = await app.send_message(chat_id=chat_id, text=query.lang["play_next"])
        if not media.file_path:
            media.file_path = await yt.download(media.id, video=media.video)
        media.message_id = msg.id
        return await anon.play_media(chat_id, msg, media)

    elif action == "replay":
        media = queue.get_current(chat_id)
        media.user = user
        await anon.replay(chat_id)
        status = query.lang["replayed"]
        reply = query.lang["play_replayed"].format(user)

    elif action in ("seek_fwd", "seek_back"):
        media = queue.get_current(chat_id)
        if not media or not media.duration_sec:
            return await query.answer(query.lang["play_seek_no_dur"], show_alert=True)

        to_seek = 20
        if action == "seek_back":
            start_from = media.time - to_seek
            if start_from < 1:
                start_from = 1
            stype = query.lang["backward"]
        else:
            start_from = media.time + to_seek
            if start_from + 10 > media.duration_sec:
                start_from = media.duration_sec - 5
            stype = query.lang["forward"]

        sent = await app.send_message(chat_id=chat_id, text=query.lang["play_seeking"])
        await anon.play_media(chat_id, sent, media, start_from)
        media.time = start_from
        return await sent.edit_text(
            query.lang["play_seeked"].format(stype, start_from, user)
        )

    elif action == "stop":
        await anon.stop(chat_id)
        status = query.lang["stopped"]
        reply = query.lang["play_stopped"].format(user)

    try:
        if action in ["skip", "replay", "stop"]:
            await query.message.reply_text(reply, quote=False)
            await query.message.delete()
        else:
            mtext = re.sub(
                r"\n\n<blockquote>.*?</blockquote>",
                "",
                query.message.caption.html or query.message.text.html,
                flags=re.DOTALL,
            )
            keyboard = buttons.controls(
                chat_id, status=status if action != "resume" else None
            )
        await query.edit_message_text(
            f"{mtext}\n\n<blockquote>{reply}</blockquote>", reply_markup=keyboard
        )
    except:
        pass


@app.on_callback_query(filters.regex("help") & ~app.bl_users)
@lang.language()
async def _help(_, query: types.CallbackQuery):
    data = query.data.split()
    if len(data) == 1:
        return await query.answer(url=f"https://t.me/{app.username}?start=help")

    if data[1] == "back":
        return await query.edit_message_text(
            text=query.lang["help_menu"], reply_markup=buttons.help_markup(query.lang)
        )
    elif data[1] == "home":
        return await query.answer(url=f"https://t.me/{app.username}?start=home")
    elif data[1] == "close":
        try:
            await query.message.delete()
            return await query.message.reply_to_message.delete()
        except:
            pass

    await query.edit_message_text(
        text=query.lang[f"help_{data[1]}"],
        reply_markup=buttons.help_markup(query.lang, True),
    )


@app.on_callback_query(filters.regex("settings") & ~app.bl_users)
@lang.language()
@admin_check
async def _settings_cb(_, query: types.CallbackQuery):
    cmd = query.data.split()
    if len(cmd) == 1:
        return await query.answer()
    await query.answer(query.lang["processing"], show_alert=True)

    chat_id = query.message.chat.id
    _admin = await db.get_play_mode(chat_id)
    _delete = await db.get_cmd_delete(chat_id)
    _language = await db.get_lang(chat_id)

    if cmd[1] == "delete":
        _delete = not _delete
        await db.set_cmd_delete(chat_id, _delete)
    elif cmd[1] == "play":
        await db.set_play_mode(chat_id, _admin)
        _admin = not _admin
    await query.edit_message_reply_markup(
        reply_markup=buttons.settings_markup(
            query.lang,
            _admin,
            _delete,
            _language,
            chat_id,
        )
    )


async def _delete_later(message: types.Message) -> None:
    try:
        await asyncio.sleep(7)
        await message.delete()
    except Exception:
        pass


@app.on_callback_query(filters.regex("^autoplay_panel") & ~app.bl_users)
@lang.language()
async def _autoplay_panel(_, query: types.CallbackQuery):
    data = query.data.split()
    action = data[1] if len(data) > 1 else None
    chat_id = query.message.chat.id

    if action == "info":
        await query.answer()
        return await query.edit_message_text(
            text=query.lang.get(
                "autoplay_info_title",
                "ℹ️ <b>How Autoplay works?</b>\n\n"
                "• Automatically continues music playback.\n"
                "• Follows current audio or video mode.\n"
                "• Designed for seamless listening.\n\n"
                "🎶 Sit back & enjoy the music.",
            ),
            reply_markup=buttons.autoplay_info_markup(query.lang),
        )

    elif action == "back":
        await query.answer()
        return await query.edit_message_text(
            text=query.lang.get(
                "autoplay_panel_title",
                "🎶 <b>Autoplay:</b>\n\n"
                "• Keeps music playing automatically.\n"
                "• Ensures smooth and uninterrupted listening.\n"
                "• Designed for a seamless music experience.",
            ),
            reply_markup=buttons.autoplay_markup(query.lang),
        )

    elif action == "close":
        await query.answer()
        try:
            await query.message.delete()
        except:
            pass
        return

    elif action == "enable":
        await db.set_autoplay(chat_id, True)
        await query.answer(query.lang.get("autoplay_on", "Enabled"))

        try:
            await query.message.delete()
        except:
            pass

        msg = await app.send_message(
            chat_id=chat_id,
            text=query.lang.get("autoplay_enabled_short", "✅ Autoplay Enabled"),
        )
        asyncio.create_task(_delete_later(msg))
        return
