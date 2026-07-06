from __future__ import annotations

import json
from typing import Any

from database.connection import db_session


def rows(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    with db_session() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def row(sql: str, params: tuple = ()) -> dict[str, Any] | None:
    result = rows(sql, params)
    return result[0] if result else None


def execute(sql: str, params: tuple = ()) -> None:
    with db_session() as conn:
        conn.execute(sql, params)


def execute_many(sql: str, params: list[tuple]) -> None:
    with db_session() as conn:
        conn.executemany(sql, params)


def jdump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def jload(value: str | None, default: Any = None) -> Any:
    if value is None:
        return default
    return json.loads(value)
