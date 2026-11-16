from __future__ import annotations

from aiogram.types import CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📤 Upload File", callback_data="menu:upload")
    kb.button(text="👤 My Account", callback_data="menu:account")
    kb.button(text="💎 Buy Storage", callback_data="menu:buy")
    kb.button(text="❓ Help", callback_data="menu:help")
    kb.adjust(2, 2)
    return kb.as_markup()


def copy_button(label: str, text: str, key: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=label, copy_text=CopyTextButton(text=text))


def upload_success(link: str, file_uid: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(copy_button("📋 Copy Link", link, "copy_link"))
    kb.row(InlineKeyboardButton(text="👤 My Account", callback_data="menu:account"))
    return kb.as_markup()


def plan_buttons() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="💎 30 Days — ₹199", callback_data="plan:monthly"))
    kb.row(InlineKeyboardButton(text="♾️ Lifetime — ₹250", callback_data="plan:lifetime"))
    return kb.as_markup()


def payment_screen(order_id: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(
        text="📸 I've Paid — Submit Screenshot", callback_data=f"shot:{order_id}"
    ))
    kb.row(InlineKeyboardButton(text="❌ Cancel Order", callback_data=f"cancel:{order_id}"))
    return kb.as_markup()


def payment_review(order_id: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ COMPLETE / APPROVE", callback_data=f"pay:approve:{order_id}"),
        InlineKeyboardButton(text="❌ REJECT", callback_data=f"pay:reject:{order_id}"),
    )
    kb.row(InlineKeyboardButton(text="⏳ PAYMENT NOT RECEIVED",
                                callback_data=f"pay:nopay:{order_id}"))
    return kb.as_markup()


def redeem_button(key: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(copy_button("📋 Copy /redeem Command", f"/redeem {key}", "copy_redeem"))
    return kb.as_markup()


def help_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📤 How to Upload Files", callback_data="help:upload"))
    kb.row(InlineKeyboardButton(text="🔗 How to Share Files", callback_data="help:share"))
    kb.row(InlineKeyboardButton(text="💎 Buy Premium", callback_data="menu:buy"))
    kb.row(InlineKeyboardButton(text="👤 My Account", callback_data="menu:account"))
    kb.row(InlineKeyboardButton(text="📊 My Statistics", callback_data="help:stats"))
    kb.row(InlineKeyboardButton(text="💬 Contact Admin", url="https://t.me/"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="menu:home"))
    return kb.as_markup()


def back_home() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="menu:home"))
    return kb.as_markup()


def admin_panel() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📊 Dashboard", callback_data="adm:dash"))
    kb.row(
        InlineKeyboardButton(text="👥 Total Users", callback_data="adm:users"),
        InlineKeyboardButton(text="💎 Premium Users", callback_data="adm:premium"),
    )
    kb.row(InlineKeyboardButton(text="📦 Total Files", callback_data="adm:files"))
    kb.row(
        InlineKeyboardButton(text="💰 Payment Requests", callback_data="adm:pending"),
        InlineKeyboardButton(text="✅ Approved", callback_data="adm:approved"),
    )
    kb.row(InlineKeyboardButton(text="❌ Rejected", callback_data="adm:rejected"))
    kb.row(InlineKeyboardButton(text="🔑 Generate Premium Key", callback_data="adm:genkey"))
    kb.row(InlineKeyboardButton(text="📢 Broadcast", callback_data="adm:broadcast"))
    kb.row(InlineKeyboardButton(text="🔍 Search User", callback_data="adm:search"))
    kb.row(InlineKeyboardButton(text="📈 Download Analytics", callback_data="adm:analytics"))
    kb.row(InlineKeyboardButton(text="⚙️ Bot Settings", callback_data="adm:settings"))
    kb.adjust(1, 2, 1, 2, 1, 1, 1, 1, 1, 1)
    return kb.as_markup()


def admin_genkey_plans() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="30 Days Key", callback_data="adm:genkey:monthly"))
    kb.row(InlineKeyboardButton(text="Lifetime Key", callback_data="adm:genkey:lifetime"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="adm:home"))
    return kb.as_markup()


def admin_back() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 Admin Panel", callback_data="adm:home"))
    return kb.as_markup()


def broadcast_preview() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Confirm Broadcast", callback_data="bcast:confirm"),
        InlineKeyboardButton(text="❌ Cancel", callback_data="bcast:cancel"),
    )
    return kb.as_markup()
