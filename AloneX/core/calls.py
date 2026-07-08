# Copyright (c) 2025 TheHamkerAlone
# Licensed under the MIT License.
# This file is part of AloneXMusic
# ALONE-CODER

from collections import defaultdict

from ntgcalls import (ConnectionNotFound, TelegramServerError,
                      RTMPStreamingUnsupported)
from pyrogram.errors import MessageIdInvalid
from pyrogram.types import InputMediaPhoto, Message
from pytgcalls import PyTgCalls, exceptions, types
from pytgcalls.pytgcalls_session import PyTgCallsSession

from AloneX import app, config, db, lang, logger, queue, userbot, yt
from AloneX.helpers import Media, Track, buttons, thumb, vclogger


class TgCall(PyTgCalls):
    def __init__(self):
        self.clients = []
        self.history: dict[int, list[str]] = defaultdict(list)
        self.pending_autoplay: dict[int, Track] = {}
        self.autoplay_prefetching: set[int] = set()

    async def pause(self, chat_id: int) -> bool:
        client = await db.get_assistant(chat_id)
        await db.playing(chat_id, paused=True)
        return await client.pause(chat_id)

    async def resume(self, chat_id: int) -> bool:
        client = await db.get_assistant(chat_id)
        await db.playing(chat_id, paused=False)
        return await client.resume(chat_id)

    async def stop(self, chat_id: int) -> None:
        client = await db.get_assistant(chat_id)
        try:
            queue.clear(chat_id)
            await db.remove_call(chat_id)
        except:
            pass

        self.history.pop(chat_id, None)
        self.pending_autoplay.pop(chat_id, None)
        self.autoplay_prefetching.discard(chat_id)
        vclogger.clear_chat(chat_id)

        try:
            await client.leave_call(chat_id, close=False)
        except:
            pass


    async def play_media(
        self,
        chat_id: int,
        message: Message,
        media: Media | Track,
        seek_time: int = 0,
    ) -> None:
        client = await db.get_assistant(chat_id)
        _lang = await lang.get_lang(chat_id)
        _thumb = (
            await thumb.generate(media)
            if isinstance(media, Track)
            else config.DEFAULT_THUMB
        )

        if not media.file_path:
            await message.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
            return await self.play_next(chat_id)

        stream = types.MediaStream(
            media_path=media.file_path,
            audio_parameters=types.AudioQuality.HIGH,
            video_parameters=types.VideoQuality.HD_720p,
            audio_flags=types.MediaStream.Flags.REQUIRED,
            video_flags=(
                types.MediaStream.Flags.AUTO_DETECT
                if media.video
                else types.MediaStream.Flags.IGNORE
            ),
            ffmpeg_parameters=f"-ss {seek_time}" if seek_time > 1 else None,
        )
        try:
            await client.play(
                chat_id=chat_id,
                stream=stream,
                config=types.GroupCallConfig(auto_start=False),
            )
            if not seek_time:
                media.time = 1
                await db.add_call(chat_id)
                text = _lang["play_media"].format(
                    media.url,
                    media.title,
                    media.duration,
                    media.user,
                )
                keyboard = buttons.controls(chat_id)
                try:
                    await message.edit_media(
                        media=InputMediaPhoto(
                            media=_thumb,
                            caption=text,
                        ),
                        reply_markup=keyboard,
                    )
                except MessageIdInvalid:
                    media.message_id = (await app.send_photo(
                        chat_id=chat_id,
                        photo=_thumb,
                        caption=text,
                        reply_markup=keyboard,
                    )).id
        except FileNotFoundError:
            await message.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
            await self.play_next(chat_id)
        except exceptions.NoActiveGroupCall:
            await self.stop(chat_id)
            await message.edit_text(_lang["error_no_call"])
        except exceptions.NoAudioSourceFound:
            await message.edit_text(_lang["error_no_audio"])
            await self.play_next(chat_id)
        except (ConnectionNotFound, TelegramServerError):
            await self.stop(chat_id)
            await message.edit_text(_lang["error_tg_server"])
        except RTMPStreamingUnsupported:
            await self.stop(chat_id)
            await message.edit_text(_lang["error_rtmp"])


    async def replay(self, chat_id: int) -> None:
        if not await db.get_call(chat_id):
            return

        media = queue.get_current(chat_id)
        _lang = await lang.get_lang(chat_id)
        msg = await app.send_message(chat_id=chat_id, text=_lang["play_again"])
        await self.play_media(chat_id, msg, media)


    async def play_next(self, chat_id: int) -> None:
        current = queue.get_current(chat_id)
        if current:
            history = self.history[chat_id]
            history.append(current.id)
            del history[:-20]

        # reset the prefetch guard now that this song's lifecycle has ended
        self.autoplay_prefetching.discard(chat_id)

        media = queue.get_next(chat_id)
        try:
            if media.message_id:
                await app.delete_messages(
                    chat_id=chat_id,
                    message_ids=media.message_id,
                    revoke=True,
                )
                media.message_id = 0
        except:
            pass

        if not media:
            if current and isinstance(current, Track) and await db.get_autoplay(chat_id):
                _lang = await lang.get_lang(chat_id)

                # fast path: a track was already searched & downloaded in the
                # background (~30s before this song ended) — instant, no lag
                related = self.pending_autoplay.pop(chat_id, None)

                if not related:
                    notice = await app.send_message(
                        chat_id=chat_id,
                        text=_lang.get(
                            "autoplay_searching",
                            "🔎 Queue is empty — Autoplay is searching for a related song...",
                        ),
                    )
                    try:
                        related = await yt.get_related(current, self.history[chat_id])
                    except Exception as e:
                        logger.error(f"[Autoplay] Unexpected error for chat {chat_id}: {e}")
                        related = None

                    try:
                        await notice.delete()
                    except:
                        pass

                if related:
                    related.user = "Autoplay"
                    queue.add(chat_id, related)
                    media = queue.get_current(chat_id)
                else:
                    await app.send_message(
                        chat_id=chat_id,
                        text=_lang.get(
                            "autoplay_failed",
                            "⚠️ Autoplay couldn't find a related song to play next, so the stream has ended.",
                        ),
                    )

            if not media:
                return await self.stop(chat_id)

        _lang = await lang.get_lang(chat_id)
        msg = await app.send_message(chat_id=chat_id, text=_lang["play_next"])
        if not media.file_path:
            media.file_path = await yt.download(media.id, video=media.video)
            if not media.file_path:
                await self.stop(chat_id)
                return await msg.edit_text(
                    _lang["error_no_file"].format(config.SUPPORT_CHAT)
                )

        media.message_id = msg.id
        await self.play_media(chat_id, msg, media)


    async def ping(self) -> float:
        pings = [client.ping for client in self.clients]
        return round(sum(pings) / len(pings), 2)


    async def decorators(self, client: PyTgCalls) -> None:
        participant_update = getattr(types, "UpdatedGroupCallParticipant", None)

        @client.on_update()
        async def update_handler(_, update: types.Update) -> None:
            if isinstance(update, types.StreamEnded):
                if update.stream_type == types.StreamEnded.Type.AUDIO:
                    await self.play_next(update.chat_id)
            elif isinstance(update, types.ChatUpdate):
                if update.status in [
                    types.ChatUpdate.Status.KICKED,
                    types.ChatUpdate.Status.LEFT_GROUP,
                    types.ChatUpdate.Status.CLOSED_VOICE_CHAT,
                ]:
                    await self.stop(update.chat_id)
            elif participant_update and isinstance(update, participant_update):
                try:
                    if not await db.get_vc_logger(update.chat_id):
                        return

                    # `action` lives on the update itself; `user_id` lives on
                    # update.participant. Fall back defensively in case this
                    # differs across pytgcalls versions.
                    action = getattr(update, "action", None)
                    if action is None:
                        action = getattr(update.participant, "action", None)

                    user_id = getattr(update.participant, "user_id", None)
                    if user_id is None:
                        user_id = getattr(update, "user_id", None)

                    if action == types.GroupCallParticipant.Action.JOINED:
                        await vclogger.notify_join(update.chat_id, user_id)
                    elif action == types.GroupCallParticipant.Action.LEFT:
                        await vclogger.notify_leave(update.chat_id, user_id)
                except Exception as e:
                    logger.error(f"[VCLogger] Update handling error: {e}")


    async def boot(self) -> None:
        PyTgCallsSession.notice_displayed = True
        for ub in userbot.clients:
            client = PyTgCalls(ub, cache_duration=100)
            await client.start()
            self.clients.append(client)
            await self.decorators(client)
        logger.info("PyTgCalls client(s) started.")
