# Copyright (c) 2025 TheHamkerAlone
# Licensed under the MIT License.
# This file is part of AloneXMusic
#ALONE-CODER

import asyncio
import random
from pyrogram import enums, filters, types

from AloneX import app, config, db, lang, logger
from AloneX.helpers import buttons, utils

REACT_EMOJIS = ["🥰", "🔥", "💖", "😁", "😎", "🌚", "❤️‍🔥", "♥️", "🎉", "🙈"]

PURVI_STKR = [
    "CAACAgUAAxkBAAIPNGpruZ9_f9uU1fDT8NH8_Y0khHzgAAIpFQACvTqpVWqbFSKOnWYxHgQ",
    "CAACAgUAAxkBAAIPN2pruiFB2-n9WchfMu_XhVud1CASAAI4FwACDDexVVp91U_1BZKFHgQ",
    "CAACAgUAAxkBAAIPOmprujVwFDuRESgRAdHYqrIKu1MzAAKDGgACZSupVbmJpWW9LmXJHgQ",
    "CAACAgUAAxkBAAIPO2prujYWaRAGsER9KWAs4rX0Zss_AAIsHwACdd6xVd2HOWQPA_qtHgQ",
    "CAACAgUAAxkBAAIPPGprujjZmdaEeRs2uVC1RMxamfl9AAJZHQACCa-pVfefqZZtTHEdHgQ",
    "CAACAgUAAxkBAAIPPWprujnZdJc-uGh9Ij8BHsZhTuFVAAJ9GAACXB-pVds_sm8brMEqHgQ",
    "CAACAgUAAxkBAAIPPmprujogyg_RWL6jgoRS0c0dxRC4AAIlGAACKI6wVVNEvN-6z3Z7HgQ",
]

EFFECT_IDS = [
    5046509860389126442,
    5107584321108051014,
    5104841245755180586,
    5159385139981059251,
]


@app.on_message(filters.command(["help"]) & filters.private & ~app.bl_users)
@lang.language()
async def _help(_, m: types.Message):
    await m.reply_text(
        text=m.lang["help_menu"],
        reply_markup=buttons.help_markup(m.lang),
        quote=True,
    )


@app.on_message(filters.command(["start"]))
@lang.language()
async def start(_, message: types.Message):
    if message.from_user.id in app.bl_users and message.from_user.id not in db.notified:
        return await message.reply_text(message.lang["bl_user_notify"])

    if len(message.command) > 1 and message.command[1] == "help":
        return await _help(_, message)

    try:
        await message.react(random.choice(REACT_EMOJIS))
    except Exception as e:
        logger.error(f"[Start] Reaction failed: {e}")

    try:
        sticker = await message.reply_sticker(random.choice(PURVI_STKR))
        await asyncio.sleep(1)
        await sticker.delete()
    except Exception as e:
        logger.error(f"[Start] Sticker failed: {e}")

    private = message.chat.type == enums.ChatType.PRIVATE

    if private:
        try:
            purvi = await message.reply_text(f"**ʜєʟʟᴏ ᴅєᴧʀ {message.from_user.mention}**")
            await asyncio.sleep(0.4)
            await purvi.edit_text("**ɪ ᴧϻ ʏσᴜʀ ϻᴜsɪᴄ ʙσᴛ..🦋**")
            await asyncio.sleep(0.4)
            await purvi.edit_text("**ʜσᴡ ᴧʀє ʏσᴜ ᴛσᴅᴧʏ.....??**")
            await asyncio.sleep(0.4)
            await purvi.delete()
        except Exception:
            pass

    _text = (
        message.lang["start_pm"].format(message.from_user.first_name, app.name)
        if private
        else message.lang["start_gp"].format(app.name)
    )

    key = buttons.start_key(message.lang, private)
    try:
        await message.reply_photo(
            photo=config.START_IMG,
            caption=_text,
            reply_markup=key,
            quote=not private,
            message_effect_id=random.choice(EFFECT_IDS),
        )
    except Exception as e:
        logger.error(f"[Start] message_effect_id failed, falling back: {e}")
        await message.reply_photo(
            photo=config.START_IMG,
            caption=_text,
            reply_markup=key,
            quote=not private,
        )

    if private:
        if await db.is_user(message.from_user.id):
            return
        await utils.send_log(message)
        await db.add_user(message.from_user.id)
    else:
        if await db.is_chat(message.chat.id):
            return
        await utils.send_log(message, True)
        await db.add_chat(message.chat.id)


@app.on_message(filters.command(["playmode", "settings"]) & filters.group & ~app.bl_users)
@lang.language()
async def settings(_, message: types.Message):
    admin_only = await db.get_play_mode(message.chat.id)
    cmd_delete = await db.get_cmd_delete(message.chat.id)
    _language = await db.get_lang(message.chat.id)
    await message.reply_text(
        text=message.lang["start_settings"].format(message.chat.title),
        reply_markup=buttons.settings_markup(
            message.lang, admin_only, cmd_delete, _language, message.chat.id
        ),
        quote=True,
    )


@app.on_message(filters.new_chat_members, group=7)
@lang.language()
async def _new_member(_, message: types.Message):
    if message.chat.type != enums.ChatType.SUPERGROUP:
        return await message.chat.leave()

    bot_joined = any(member.id == app.id for member in message.new_chat_members)

    if bot_joined:
        if message.chat.id in await db.get_blacklisted(True):
            try:
                await message.reply_text(
                    message.lang.get(
                        "bl_chat_notify",
                        "This group is blacklisted from using this bot.",
                    )
                )
            except Exception:
                pass
            return await message.chat.leave()

        await asyncio.sleep(3)
        if await db.is_chat(message.chat.id):
            return
        await utils.send_log(message, True)
        await db.add_chat(message.chat.id)
        return

    banned_users = await db.get_blacklisted()
    for member in message.new_chat_members:
        if member.id in banned_users:
            try:
                await message.chat.ban_member(member.id)
            except Exception:
                pass
