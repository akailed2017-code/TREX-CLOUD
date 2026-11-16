from __future__ import annotations

from dataclasses import dataclass

from config import Config
from utils.helpers import now


@dataclass(frozen=True)
class Entitlements:
    effective_plan: str          # free | monthly | lifetime
    is_premium: bool
    storage_limit: int | None    # None = unlimited
    daily_uploads: int | None    # None = unlimited
    retention_days: int | None   # None = permanent
    premium_until: int | None    # None for lifetime / free


def entitlements(user, cfg: Config) -> Entitlements:
    plan = (user["plan"] or "free").lower() if user else "free"
    until = user["premium_until"] if user else None

    if plan == "lifetime":
        return Entitlements("lifetime", True, None, None, None, None)

    if plan == "monthly":
        if until and until > now():
            return Entitlements("monthly", True, None, None, None, int(until))
        plan = "free"

    return Entitlements(
        "free", False, cfg.free_storage_bytes, cfg.free_daily_uploads,
        cfg.free_retention_days, None,
    )
