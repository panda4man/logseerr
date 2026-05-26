import aiosqlite
from pathlib import Path

DB_PATH = Path("state.db")

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS checkpoints (
    service TEXT PRIMARY KEY,
    last_ns  INTEGER NOT NULL
)
"""


async def get_last_ingested(service: str) -> int | None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(_CREATE_TABLE)
        async with db.execute(
            "SELECT last_ns FROM checkpoints WHERE service = ?", (service,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def set_last_ingested(service: str, last_ns: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(_CREATE_TABLE)
        await db.execute(
            "INSERT OR REPLACE INTO checkpoints (service, last_ns) VALUES (?, ?)",
            (service, last_ns),
        )
        await db.commit()
