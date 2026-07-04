from __future__ import annotations

from .foundation import *

def _to_data(result: Any, *, include_raw: bool) -> Any:
    if isinstance(result, list):
        return [_to_data(item, include_raw=include_raw) for item in result]
    if hasattr(result, "to_dict"):
        return result.to_dict(include_raw=include_raw)
    return result


def _statute_args(values: list[str]) -> list[str]:
    if not values:
        raise CliError(
            "load-institutional-system needs at least one --statute law_id",
            kind="usage",
            exit_code=EXIT_USAGE,
        )
    return values

__all__ = [name for name in globals() if not name.startswith("__")]
