"""Contadores de comandos en memoria con volcado periódico (spec 7.4).

Los puntos de pole NUNCA pasan por aquí: van a SQL en la transacción de la victoria.
"""

from __future__ import annotations

from collections import Counter

from nekita.core.db import Database

UPSERT = (
    "INSERT INTO stats(key, count) VALUES(?, ?) "
    "ON CONFLICT(key) DO UPDATE SET count = count + excluded.count"
)


class Stats:
    def __init__(self) -> None:
        self._pending: Counter[str] = Counter()

    def incr(self, key: str, n: int = 1) -> None:
        self._pending[key] += n

    def command(self, name: str) -> None:
        self.incr(f"cmd:{name}")

    @property
    def pending(self) -> int:
        return sum(self._pending.values())

    async def flush(self, db: Database) -> None:
        """Vuelca a SQLite. Si falla, los contadores se conservan para el próximo intento."""
        if not self._pending:
            return
        lote, self._pending = self._pending, Counter()
        try:
            async with db.transaction() as conn:
                await conn.executemany(UPSERT, list(lote.items()))
        except BaseException:
            self._pending.update(lote)
            raise

    async def top_commands(self, db: Database, limit: int = 10) -> list[tuple[str, int]]:
        """Top de comandos (BD + lo pendiente en memoria)."""
        total: Counter[str] = Counter(self._pending)
        for key, count in await db.fetchall("SELECT key, count FROM stats WHERE key LIKE 'cmd:%'"):
            total[key] += count
        cmds = [(k.removeprefix("cmd:"), v) for k, v in total.items() if k.startswith("cmd:")]
        return sorted(cmds, key=lambda kv: (-kv[1], kv[0]))[:limit]
