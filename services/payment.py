from __future__ import annotations

from dataclasses import dataclass

from database import Database
from services.keys import make_premium_key
from utils.helpers import now


@dataclass
class ApproveResult:
    ok: bool
    reason: str
    key: str | None = None
    user_id: int | None = None
    plan: str | None = None


async def approve_order(db: Database, order_id: str, admin_id: int) -> ApproveResult:
    async with db.transaction():
        order = await db.fetchone("SELECT * FROM orders WHERE order_id=?", (order_id,))
        if order is None:
            return ApproveResult(False, "missing")

        if order["status"] != "pending":
            return ApproveResult(False, f"already_{order['status']}")

        key = make_premium_key(order["plan"])
        ts = now()
        await db.execute(
            "UPDATE orders SET status='approved', updated_at=?, reviewed_by=? WHERE order_id=?",
            (ts, admin_id, order_id),
        )
        await db.add_key(key, order["plan"], order["user_id"], order_id)
        return ApproveResult(True, "approved", key, int(order["user_id"]), order["plan"])


async def reject_order(db: Database, order_id: str, admin_id: int, status: str) -> ApproveResult:
    async with db.transaction():
        order = await db.fetchone("SELECT * FROM orders WHERE order_id=?", (order_id,))
        if order is None:
            return ApproveResult(False, "missing")
        if order["status"] != "pending":
            return ApproveResult(False, f"already_{order['status']}")
        await db.execute(
            "UPDATE orders SET status=?, updated_at=?, reviewed_by=? WHERE order_id=?",
            (status, now(), admin_id, order_id),
        )
        return ApproveResult(True, status, None, int(order["user_id"]), order["plan"])


async def redeem_key(db: Database, user_id: int, key_str: str) -> tuple[str, dict | None]:
    key_str = key_str.strip().upper()
    async with db.transaction():
        key = await db.fetchone("SELECT * FROM premium_keys WHERE key=?", (key_str,))
        if key is None:
            return "invalid", None
        if key["status"] == "redeemed":
            return "used", None
        if key["status"] == "revoked":
            return "revoked", None
        if key["user_id"] and int(key["user_id"]) != int(user_id):
            return "not_yours", None

        ts = now()
        if key["plan"] == "lifetime":
            await db.execute(
                "UPDATE users SET plan='lifetime', premium_until=NULL WHERE user_id=?",
                (user_id,),
            )
            expires = None
        else:
            user = await db.fetchone("SELECT * FROM users WHERE user_id=?", (user_id,))
            base = ts
            if user and user["plan"] == "monthly" and user["premium_until"] \
                    and int(user["premium_until"]) > ts:
                base = int(user["premium_until"])
            expires = base + 30 * 86400
            await db.execute(
                "UPDATE users SET plan='monthly', premium_until=? WHERE user_id=?",
                (expires, user_id),
            )

        await db.mark_key_redeemed(key_str, user_id)
        await db.add_subscription(user_id, key["plan"], expires, key_str, key["order_id"])
        return "ok", {"plan": key["plan"], "expires": expires}
