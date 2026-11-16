"""SQLite persistence layer. Designed so the SQL stays portable to PostgreSQL."""
from __future__ import annotations

import secrets
import string
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import aiosqlite

from utils.helpers import now as _now

_ALPHABET = string.ascii_uppercase + string.digits

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS users (
    user_id         INTEGER PRIMARY KEY,
    username        TEXT,
    first_name      TEXT,
    unique_uid      TEXT NOT NULL UNIQUE,
    plan            TEXT NOT NULL DEFAULT 'free',
    premium_until   INTEGER,
    created_at      INTEGER NOT NULL,
    last_seen       INTEGER,
    is_blocked      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS files (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    token               TEXT NOT NULL UNIQUE,
    file_uid            TEXT NOT NULL UNIQUE,
    user_id             INTEGER NOT NULL,
    file_unique_id      TEXT,
    file_name           TEXT,
    file_size           INTEGER NOT NULL DEFAULT 0,
    mime_type           TEXT,
    file_type           TEXT,
    storage_chat_id     INTEGER NOT NULL,
    storage_message_id  INTEGER NOT NULL,
    created_at          INTEGER NOT NULL,
    expires_at          INTEGER,
    deleted             INTEGER NOT NULL DEFAULT 0,
    downloads           INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
CREATE INDEX IF NOT EXISTS idx_files_user ON files(user_id);
CREATE INDEX IF NOT EXISTS idx_files_unique ON files(user_id, file_unique_id);

CREATE TABLE IF NOT EXISTS daily_uploads (
    user_id  INTEGER NOT NULL,
    day      TEXT NOT NULL,
    count    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, day)
);

CREATE TABLE IF NOT EXISTS orders (
    order_id            TEXT PRIMARY KEY,
    user_id             INTEGER NOT NULL,
    plan                TEXT NOT NULL,
    amount              INTEGER NOT NULL,
    status              TEXT NOT NULL DEFAULT 'pending',
    created_at          INTEGER NOT NULL,
    updated_at          INTEGER,
    reviewed_by         INTEGER,
    payment_message_id  INTEGER
);
CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id, status);

CREATE TABLE IF NOT EXISTS payments (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id                TEXT NOT NULL,
    user_id                 INTEGER NOT NULL,
    screenshot_chat_id      INTEGER,
    screenshot_message_id   INTEGER,
    evidence_chat_id        INTEGER,
    evidence_message_id     INTEGER,
    file_unique_id          TEXT,
    created_at              INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS premium_keys (
    key          TEXT PRIMARY KEY,
    plan         TEXT NOT NULL,
    user_id      INTEGER,
    order_id     TEXT,
    status       TEXT NOT NULL DEFAULT 'unused',
    created_at   INTEGER NOT NULL,
    redeemed_at  INTEGER,
    redeemed_by  INTEGER
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    plan        TEXT NOT NULL,
    started_at  INTEGER NOT NULL,
    expires_at  INTEGER,
    key         TEXT,
    order_id    TEXT
);

CREATE TABLE IF NOT EXISTS downloads (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id     INTEGER NOT NULL,
    user_id     INTEGER NOT NULL,
    status      TEXT NOT NULL,
    created_at  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_downloads_file ON downloads(file_id);

CREATE TABLE IF NOT EXISTS broadcasts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id     INTEGER NOT NULL,
    kind         TEXT,
    sent         INTEGER NOT NULL DEFAULT 0,
    failed       INTEGER NOT NULL DEFAULT 0,
    created_at   INTEGER NOT NULL,
    finished_at  INTEGER
);

CREATE TABLE IF NOT EXISTS admin_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id    INTEGER NOT NULL,
    action      TEXT NOT NULL,
    target      TEXT,
    meta        TEXT,
    created_at  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key    TEXT PRIMARY KEY,
    value  TEXT
);
"""


def _rand(n: int = 8) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(n))


class Database:
    def __init__(self, path: str):
        self.path = path
        self.conn: aiosqlite.Connection | None = None

    # ---------- lifecycle ----------

    async def connect(self) -> None:
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA foreign_keys=ON")
        await self.conn.commit()

    async def close(self) -> None:
        if self.conn is not None:
            await self.conn.close()
            self.conn = None

    async def init_schema(self) -> None:
        assert self.conn is not None
        await self.conn.executescript(SCHEMA)
        await self.conn.commit()

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator["Database"]:
        assert self.conn is not None
        await self.conn.execute("BEGIN IMMEDIATE")
        try:
            yield self
        except BaseException:
            await self.conn.rollback()
            raise
        else:
            await self.conn.commit()

    # ---------- primitives ----------

    async def execute(self, sql: str, params: tuple = ()) -> None:
        assert self.conn is not None
        await self.conn.execute(sql, params)

    async def fetchone(self, sql: str, params: tuple = ()) -> aiosqlite.Row | None:
        assert self.conn is not None
        cur = await self.conn.execute(sql, params)
        row = await cur.fetchone()
        await cur.close()
        return row

    async def fetchall(self, sql: str, params: tuple = ()) -> list[aiosqlite.Row]:
        assert self.conn is not None
        cur = await self.conn.execute(sql, params)
        rows = await cur.fetchall()
        await cur.close()
        return rows

    async def scalar(self, sql: str, params: tuple = (), default: Any = 0) -> Any:
        row = await self.fetchone(sql, params)
        if row is None:
            return default
        v = row[0]
        return default if v is None else v

    # ---------- users ----------

    async def ensure_user(self, user_id: int, username: str | None, first_name: str | None):
        ts = _now()
        row = await self.fetchone("SELECT * FROM users WHERE user_id=?", (user_id,))
        if row:
            await self.execute(
                "UPDATE users SET username=?, first_name=?, last_seen=? WHERE user_id=?",
                (username, first_name, ts, user_id),
            )
            assert self.conn is not None
            await self.conn.commit()
            return await self.fetchone("SELECT * FROM users WHERE user_id=?", (user_id,))

        for _ in range(6):
            uid = f"TCU-{_rand(8)}"
            try:
                await self.execute(
                    "INSERT INTO users (user_id, username, first_name, unique_uid, plan, created_at, last_seen)"
                    " VALUES (?,?,?,?, 'free', ?, ?)",
                    (user_id, username, first_name, uid, ts, ts),
                )
                assert self.conn is not None
                await self.conn.commit()
                return await self.fetchone("SELECT * FROM users WHERE user_id=?", (user_id,))
            except aiosqlite.IntegrityError:
                continue
        raise RuntimeError("could not allocate a unique user id")

    async def get_user(self, user_id: int):
        return await self.fetchone("SELECT * FROM users WHERE user_id=?", (user_id,))

    async def get_user_by_username(self, username: str):
        return await self.fetchone(
            "SELECT * FROM users WHERE lower(username)=lower(?)", (username.lstrip("@"),)
        )

    async def get_user_by_unique(self, uid: str):
        return await self.fetchone("SELECT * FROM users WHERE unique_uid=?", (uid,))

    # ---------- quota ----------

    async def storage_used(self, user_id: int) -> int:
        return int(
            await self.scalar(
                "SELECT COALESCE(SUM(file_size),0) FROM files WHERE user_id=? AND deleted=0",
                (user_id,),
            )
        )

    async def uploads_today(self, user_id: int) -> int:
        day = _day_key()
        return int(
            await self.scalar(
                "SELECT count FROM daily_uploads WHERE user_id=? AND day=?", (user_id, day)
            )
        )

    async def bump_daily_upload(self, user_id: int) -> None:
        day = _day_key()
        await self.execute(
            "INSERT INTO daily_uploads (user_id, day, count) VALUES (?,?,1)"
            " ON CONFLICT(user_id, day) DO UPDATE SET count = count + 1",
            (user_id, day),
        )

    # ---------- files ----------

    async def new_token(self) -> str:
        for _ in range(8):
            token = _rand(10).lower()
            exists = await self.fetchone("SELECT 1 FROM files WHERE token=?", (token,))
            if not exists:
                return token
        raise RuntimeError("token space exhausted")

    async def new_file_uid(self) -> str:
        for _ in range(8):
            uid = f"TC-{_rand(8)}"
            exists = await self.fetchone("SELECT 1 FROM files WHERE file_uid=?", (uid,))
            if not exists:
                return uid
        raise RuntimeError("file uid space exhausted")

    async def find_duplicate(self, user_id: int, file_unique_id: str | None):
        if not file_unique_id:
            return None
        return await self.fetchone(
            "SELECT * FROM files WHERE user_id=? AND file_unique_id=? AND deleted=0 LIMIT 1",
            (user_id, file_unique_id),
        )

    async def add_file(self, **kw) -> int:
        assert self.conn is not None
        cur = await self.conn.execute(
            "INSERT INTO files (token, file_uid, user_id, file_unique_id, file_name,"
            " file_size, mime_type, file_type, storage_chat_id, storage_message_id,"
            " created_at, expires_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                kw["token"], kw["file_uid"], kw["user_id"], kw.get("file_unique_id"),
                kw.get("file_name"), kw.get("file_size", 0), kw.get("mime_type"),
                kw.get("file_type"), kw["storage_chat_id"], kw["storage_message_id"],
                kw["created_at"], kw.get("expires_at"),
            ),
        )
        await self.conn.commit()
        return int(cur.lastrowid)

    async def get_file_by_token(self, token: str):
        return await self.fetchone("SELECT * FROM files WHERE token=?", (token,))

    async def get_file_by_uid(self, uid: str):
        return await self.fetchone("SELECT * FROM files WHERE file_uid=?", (uid,))

    async def mark_file_deleted(self, file_id: int) -> None:
        await self.execute("UPDATE files SET deleted=1 WHERE id=?", (file_id,))
        assert self.conn is not None
        await self.conn.commit()

    async def inc_downloads(self, file_id: int) -> None:
        await self.execute("UPDATE files SET downloads = downloads + 1 WHERE id=?", (file_id,))
        assert self.conn is not None
        await self.conn.commit()

    async def user_files(self, user_id: int, limit: int = 10):
        return await self.fetchall(
            "SELECT * FROM files WHERE user_id=? AND deleted=0 ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        )

    # ---------- downloads ----------

    async def record_download(self, file_id: int, user_id: int, status: str) -> None:
        await self.execute(
            "INSERT INTO downloads (file_id, user_id, status, created_at) VALUES (?,?,?,?)",
            (file_id, user_id, status, _now()),
        )
        assert self.conn is not None
        await self.conn.commit()

    # ---------- orders ----------

    async def create_order(self, user_id: int, plan: str, amount: int) -> str:
        for _ in range(8):
            oid = f"TC-ORDER-{_rand(8)}"
            exists = await self.fetchone("SELECT 1 FROM orders WHERE order_id=?", (oid,))
            if exists:
                continue
            ts = _now()
            await self.execute(
                "UPDATE orders SET status='cancelled', updated_at=? WHERE user_id=? AND status='pending'",
                (ts, user_id),
            )
            await self.execute(
                "INSERT INTO orders (order_id, user_id, plan, amount, status, created_at)"
                " VALUES (?,?,?,?, 'pending', ?)",
                (oid, user_id, plan, amount, ts),
            )
            assert self.conn is not None
            await self.conn.commit()
            return oid
        raise RuntimeError("could not allocate an order id")

    async def get_order(self, order_id: str):
        return await self.fetchone("SELECT * FROM orders WHERE order_id=?", (order_id,))

    async def pending_order(self, user_id: int):
        return await self.fetchone(
            "SELECT * FROM orders WHERE user_id=? AND status='pending' ORDER BY created_at DESC LIMIT 1",
            (user_id,),
        )

    async def set_order_status(self, order_id: str, status: str, admin_id: int | None = None) -> None:
        await self.execute(
            "UPDATE orders SET status=?, updated_at=?, reviewed_by=? WHERE order_id=?",
            (status, _now(), admin_id, order_id),
        )
        assert self.conn is not None
        await self.conn.commit()

    # ---------- payments ----------

    async def add_payment(self, order_id: str, user_id: int, chat_id: int, msg_id: int,
                          evidence_chat_id: int, evidence_msg_id: int, unique_id: str | None) -> None:
        await self.execute(
            "INSERT INTO payments (order_id, user_id, screenshot_chat_id, screenshot_message_id,"
            " evidence_chat_id, evidence_message_id, file_unique_id, created_at)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (order_id, user_id, chat_id, msg_id, evidence_chat_id, evidence_msg_id, unique_id, _now()),
        )
        assert self.conn is not None
        await self.conn.commit()

    # ---------- premium keys ----------

    async def add_key(self, key: str, plan: str, user_id: int, order_id: str) -> None:
        await self.execute(
            "INSERT INTO premium_keys (key, plan, user_id, order_id, status, created_at)"
            " VALUES (?,?,?,?, 'unused', ?)",
            (key, plan, user_id, order_id, _now()),
        )

    async def get_key(self, key: str):
        return await self.fetchone("SELECT * FROM premium_keys WHERE key=?", (key,))

    async def mark_key_redeemed(self, key: str, user_id: int) -> None:
        await self.execute(
            "UPDATE premium_keys SET status='redeemed', redeemed_at=?, redeemed_by=? WHERE key=?",
            (_now(), user_id, key),
        )

    # ---------- subscriptions ----------

    async def add_subscription(self, user_id: int, plan: str, expires_at: int | None,
                               key: str | None, order_id: str | None) -> None:
        await self.execute(
            "INSERT INTO subscriptions (user_id, plan, started_at, expires_at, key, order_id)"
            " VALUES (?,?,?,?,?,?)",
            (user_id, plan, _now(), expires_at, key, order_id),
        )

    # ---------- admin logs ----------

    async def log_admin(self, admin_id: int, action: str, target: str | None = None,
                        meta: str | None = None) -> None:
        await self.execute(
            "INSERT INTO admin_logs (admin_id, action, target, meta, created_at) VALUES (?,?,?,?,?)",
            (admin_id, action, target, meta, _now()),
        )
        assert self.conn is not None
        await self.conn.commit()

    # ---------- broadcasts ----------

    async def create_broadcast(self, admin_id: int, kind: str) -> int:
        assert self.conn is not None
        cur = await self.conn.execute(
            "INSERT INTO broadcasts (admin_id, kind, created_at) VALUES (?,?,?)",
            (admin_id, kind, _now()),
        )
        await self.conn.commit()
        return int(cur.lastrowid)

    async def finish_broadcast(self, bid: int, sent: int, failed: int) -> None:
        await self.execute(
            "UPDATE broadcasts SET sent=?, failed=?, finished_at=? WHERE id=?",
            (sent, failed, _now(), bid),
        )
        assert self.conn is not None
        await self.conn.commit()

    async def broadcast_recipients(self) -> list[int]:
        rows = await self.fetchall("SELECT user_id FROM users WHERE is_blocked=0")
        return [int(r["user_id"]) for r in rows]

    # ---------- settings ----------

    async def get_setting(self, key: str, default: str | None = None) -> str | None:
        row = await self.fetchone("SELECT value FROM settings WHERE key=?", (key,))
        return row["value"] if row else default

    async def set_setting(self, key: str, value: str) -> None:
        await self.execute(
            "INSERT INTO settings (key, value) VALUES (?,?)"
            " ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        assert self.conn is not None
        await self.conn.commit()


def _day_key() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
