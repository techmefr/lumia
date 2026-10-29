from typing import Any, cast

from sqlalchemy import CursorResult, Result


def affected_rows(result: Result[Any]) -> int:
    return cast(CursorResult[Any], result).rowcount
