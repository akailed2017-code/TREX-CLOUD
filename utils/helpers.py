from __future__ import annotations

import re
import time
from datetime import datetime, timezone

_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{6,64}$")


def now() -> int:
    return int(time.time())


def human_size(n) -> str:
    n = float(n or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{int(n)} B" if unit == "B" else f"{n:.2f} {unit}"
        n /= 1024
    return f"{n:.2f} TB"


def human_time(ts) -> str:
    if not ts:
        return "—"
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%d %b %Y, %H:%M UTC")


def human_date(ts) -> str:
    if not ts:
        return "—"
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%d %b %Y")


def valid_token(t: str) -> bool:
    return bool(_TOKEN_RE.match(t or ""))


def share_link(bot_username: str, token: str) -> str:
    return f"https://t.me/{bot_username}?start=file_{token}"


def esc(text) -> str:
    if text is None:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
