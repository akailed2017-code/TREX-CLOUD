from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import Message

from config import Config
from database import Database
from utils.helpers import human_size, now

log = logging.getLogger(__name__)


class FileTooLarge(RuntimeError):
    pass


class StorageError(RuntimeError):
    pass


def extract_file_meta(message: Message) -> dict | None:
    """Return normalized file metadata for a supported Telegram attachment."""
    m = message
    if m.document:
        d = m.document
        return {"type": "document", "name": d.file_name or "document",
                "size": d.file_size or 0, "mime": d.mime_type,
                "unique": d.file_unique_id}
    if m.video:
        v = m.video
        return {"type": "video", "name": v.file_name or "video.mp4",
                "size": v.file_size or 0, "mime": v.mime_type,
                "unique": v.file_unique_id}
    if m.audio:
        a = m.audio
        return {"type": "audio", "name": a.file_name or "audio.mp3",
                "size": a.file_size or 0, "mime": a.mime_type,
                "unique": a.file_unique_id}
    if m.animation:
        a = m.animation
        return {"type": "animation", "name": a.file_name or "animation",
                "size": a.file_size or 0, "mime": a.mime_type,
                "unique": a.file_unique_id}
    if m.voice:
        v = m.voice
        return {"type": "voice", "name": "voice.ogg",
                "size": v.file_size or 0, "mime": v.mime_type,
                "unique": v.file_unique_id}
    if m.video_note:
        v = m.video_note
        return {"type": "video_note", "name": "video_note.mp4",
                "size": v.file_size or 0, "mime": "video/mp4",
                "unique": v.file_unique_id}
    if m.photo:
        p = m.photo[-1]
        return {"type": "photo", "name": "photo.jpg",
                "size": p.file_size or 0, "mime": "image/jpeg",
                "unique": p.file_unique_id}
    return None


async def store_in_channel(bot: Bot, cfg: Config, message: Message) -> int:
    """Copy the received message into the private storage channel."""
    try:
        copied = await bot.copy_message(
            chat_id=cfg.storage_channel_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        log.exception("storage copy failed")
        raise StorageError(
            "Storage channel copy failed. Bot must be an admin in the storage channel "
            f"with post rights. ({e})"
        ) from e
    return copied.message_id


async def deliver_file(bot: Bot, db: Database, message: Message, token: str) -> None:
    f = await db.get_file_by_token(token)
    if f is None:
        await message.answer("❌ <b>File not found.</b>\nThis link does not exist.")
        return

    if f["deleted"]:
        await message.answer(
            "❌ <b>File unavailable.</b>\nThe stored copy has been removed from Telegram."
        )
        return

    if f["expires_at"] and f["expires_at"] < now():
        await message.answer(
            "❌ <b>Link expired.</b>\nThis free-plan link passed its retention window."
        )
        return

    await db.record_download(f["id"], message.from_user.id, "requested")

    try:
        await bot.copy_message(
            chat_id=message.chat.id,
            from_chat_id=f["storage_chat_id"],
            message_id=f["storage_message_id"],
        )
    except TelegramBadRequest as e:
        msg = str(e).lower()
        await db.record_download(f["id"], message.from_user.id, "failed")
        if "not found" in msg or "message_id_invalid" in msg or "message to copy" in msg:
            await db.mark_file_deleted(f["id"])
            await message.answer(
                "❌ <b>File unavailable.</b>\nThe stored copy is no longer accessible on Telegram."
            )
        else:
            log.warning("delivery failed for file %s: %s", f["id"], e)
            await message.answer("❌ Could not deliver this file right now. Try again later.")
        return
    except (TelegramForbiddenError, Exception) as e:  # noqa: BLE001
        await db.record_download(f["id"], message.from_user.id, "failed")
        log.exception("delivery error for file %s", f["id"])
        await message.answer("❌ Delivery failed. Please try again later.")
        return

    await db.record_download(f["id"], message.from_user.id, "delivered")
    await db.inc_downloads(f["id"])
    await message.answer(
        "✅ <b>File delivered</b>\n\n"
        f"📁 {f['file_name']}\n"
        f"📦 {human_size(f['file_size'])}"
    )
