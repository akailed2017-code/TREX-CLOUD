from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import CallbackQuery, Message

from config import Config
from database import Database
from keyboards.inline import back_home, help_menu, main_menu
from services.storage import deliver_file
from utils.helpers import esc

router = Router(name="start")

WELCOME = (
    "☁️ <b>WELCOME TO TREX CLOUD</b>\n"
    "\n"
    "Your personal cloud storage, powered by speed and simplicity.\n"
    "\n"
    "Upload any supported file and get a unique sharing link instantly.\n"
    "Free and Premium storage plans available.\n"
    "\n"
    "Use the buttons below to get started."
)

HELP_TEXT = (
    "❓ <b>TREX CLOUD — HELP</b>\n"
    "\n"
    "📤 <b>Upload</b> — send any file directly to this chat. You get a permanent "
    "sharing link instantly.\n"
    "🔗 <b>Share</b> — forward your link. Anyone who opens it receives the file.\n"
    "💎 <b>Premium</b> — /buystorage for unlimited storage and permanent retention.\n"
    "👤 <b>Account</b> — /account to see usage and limits.\n"
    "📊 <b>Stats</b> — /mystats for your upload and download history.\n"
    "🔑 <b>Redeem</b> — /redeem &lt;key&gt; to activate a purchased plan.\n"
)


@router.message(CommandStart())
async def on_start(message: Message, command: CommandObject, bot, db: Database, cfg: Config):
    await db.ensure_user(message.from_user.id, message.from_user.username, message.from_user.first_name)

    args = (command.args or "").strip()
    if args.startswith("file_"):
        token = args[5:]
        await deliver_file(bot, db, message, token)
        return

    await message.answer(WELCOME, reply_markup=main_menu())


@router.message(Command("help"))
async def on_help(message: Message, db: Database):
    await db.ensure_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    await message.answer(HELP_TEXT, reply_markup=help_menu())


@router.callback_query(F.data == "menu:home")
async def cb_home(cq: CallbackQuery):
    await cq.message.edit_text(WELCOME, reply_markup=main_menu())
    await cq.answer()


@router.callback_query(F.data == "menu:upload")
async def cb_upload(cq: CallbackQuery):
    await cq.message.edit_text(
        "📤 <b>UPLOAD A FILE</b>\n\n"
        "Send any document, video, audio, APK, ZIP, PDF or image directly to this chat.\n"
        "The bot stores it and returns a permanent sharing link.",
        reply_markup=back_home(),
    )
    await cq.answer()


@router.callback_query(F.data == "menu:help")
async def cb_help(cq: CallbackQuery):
    await cq.message.edit_text(HELP_TEXT, reply_markup=help_menu())
    await cq.answer()


@router.callback_query(F.data.startswith("help:"))
async def cb_help_section(cq: CallbackQuery):
    section = cq.data.split(":", 1)[1]
    texts = {
        "upload": (
            "📤 <b>HOW TO UPLOAD</b>\n\n"
            "1. Open this chat.\n2. Attach a file.\n3. Send it.\n\n"
            "The bot replies with your unique TREX CLOUD link."
        ),
        "share": (
            "🔗 <b>HOW TO SHARE</b>\n\n"
            "Every upload gets a link like:\n"
            "<code>https://t.me/YourBot?start=file_xxxxxxxxxx</code>\n\n"
            "Anyone opening it receives the file directly from the bot."
        ),
        "stats": (
            "📊 <b>MY STATISTICS</b>\n\nUse /mystats to see your uploads, storage used "
            "and download activity."
        ),
    }
    if section == "stats":
        await cq.message.edit_text(texts["stats"], reply_markup=back_home())
    elif section in texts:
        await cq.message.edit_text(texts[section], reply_markup=back_home())
    else:
        await cq.message.edit_text(HELP_TEXT, reply_markup=help_menu())
    await cq.answer()
