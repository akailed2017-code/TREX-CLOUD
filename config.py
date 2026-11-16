"""Environment-driven configuration. No secrets in source."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

GB = 1024 ** 3


class ConfigError(RuntimeError):
    pass


def _require(name: str) -> str:
    v = os.getenv(name, "").strip()
    if not v:
        raise ConfigError(f"missing required env var: {name}")
    return v


def _int(name: str, default: int | None = None, required: bool = False) -> int | None:
    raw = os.getenv(name, "").strip()
    if not raw:
        if required:
            raise ConfigError(f"missing required env var: {name}")
        return default
    try:
        return int(raw)
    except ValueError as e:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from e


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: frozenset[int]
    storage_channel_id: int
    payments_channel_id: int
    upi_id: str
    qr_image_url: str
    db_path: str

    free_storage_bytes: int
    free_daily_uploads: int
    free_retention_days: int

    plan_monthly_price: int
    plan_lifetime_price: int
    plan_monthly_days: int

    broadcast_batch: int
    broadcast_delay: float


def load_config() -> Config:
    token = _require("BOT_TOKEN")
    if ":" not in token:
        raise ConfigError("BOT_TOKEN does not look like a Telegram bot token")

    raw_admins = os.getenv("ADMIN_IDS", "6921606403,9132426280")
    admin_ids = frozenset(
        int(x) for x in (p.strip() for p in raw_admins.split(",")) if x
    )
    if not admin_ids:
        raise ConfigError("ADMIN_IDS resolved to an empty set")

    return Config(
        bot_token=token,
        admin_ids=admin_ids,
        storage_channel_id=_int("STORAGE_CHANNEL_ID", required=True),
        payments_channel_id=_int("PAYMENTS_CHANNEL_ID", required=True),
        upi_id=os.getenv("UPI_ID", "amanmanna198-4@okicici").strip(),
        qr_image_url=os.getenv(
            "QR_IMAGE_URL", "https://i.ibb.co/x9L6q34/Amit-pal-qr-code.png"
        ).strip(),
        db_path=os.getenv("DB_PATH", str(BASE_DIR / "trex_cloud.db")),
        free_storage_bytes=50 * GB,
        free_daily_uploads=10,
        free_retention_days=90,
        plan_monthly_price=199,
        plan_lifetime_price=250,
        plan_monthly_days=30,
        broadcast_batch=20,
        broadcast_delay=1.0,
    )
