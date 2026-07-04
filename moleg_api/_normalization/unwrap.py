"""Payload unwrapping helpers for MOLEG search/service responses."""

from __future__ import annotations

from typing import Any, Literal

from moleg_api.errors import NoResultError

from .primitives import AI_ROW_KEYS, LAW_SEARCH_ENVELOPES, ensure_list
from .row_format import collect_rows

def unwrap_search_laws(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for envelope in LAW_SEARCH_ENVELOPES:
        if isinstance(payload.get(envelope), dict):
            rows = payload[envelope].get("law")
            return [row for row in ensure_list(rows) if isinstance(row, dict)]
    rows = payload.get("law")
    return [row for row in ensure_list(rows) if isinstance(row, dict)]


def unwrap_search_administrative_rules(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for envelope in ("AdmRulSearch", "admrulSearch", "AdmrulSearch", "AdmRulSearchService"):
        if isinstance(payload.get(envelope), dict):
            rows = payload[envelope].get("admrul")
            return [row for row in ensure_list(rows) if isinstance(row, dict)]
    rows = payload.get("admrul")
    if rows is not None:
        return [row for row in ensure_list(rows) if isinstance(row, dict)]
    return collect_rows(payload, "admrul")


def unwrap_search_interpretations(payload: dict[str, Any], target: str) -> list[dict[str, Any]]:
    row_keys = tuple(dict.fromkeys((target, "expc", "cgmExpc")))
    for envelope in (
        "ExpcSearch",
        "expcSearch",
        "Expc",
        "expc",
        "CgmExpcSearch",
        "cgmExpcSearch",
        "CgmExpc",
        "cgmExpc",
    ):
        if isinstance(payload.get(envelope), dict):
            rows = next((payload[envelope].get(key) for key in row_keys if key in payload[envelope]), None)
            return [row for row in ensure_list(rows) if isinstance(row, dict)]
    rows = next((payload.get(key) for key in row_keys if key in payload), None)
    if rows is not None:
        return [row for row in ensure_list(rows) if isinstance(row, dict)]
    return collect_rows(payload, *row_keys)


def unwrap_search_judicial_decisions(payload: dict[str, Any], target: str) -> list[dict[str, Any]]:
    for envelope in ("PrecSearch", "precSearch", "DetcSearch", "detcSearch"):
        if isinstance(payload.get(envelope), dict):
            env = payload[envelope]
            # law.go.kr names the row-element key by its own casing, not the
            # request target: "prec" (lowercase) for cases but "Detc"
            # (capitalized) for constitutional decisions. Match it
            # case-insensitively, excluding the scalar "target" echo field.
            rows = env.get(target)
            if rows is None:
                rows = next(
                    (
                        env[key]
                        for key in env
                        if isinstance(key, str)
                        and key.lower() == target.lower()
                        and key != "target"
                    ),
                    None,
                )
            return [row for row in ensure_list(rows) if isinstance(row, dict)]
    rows = payload.get(target)
    if rows is not None:
        return [row for row in ensure_list(rows) if isinstance(row, dict)]
    return collect_rows(payload, target)


def unwrap_target_rows(payload: dict[str, Any], target: str) -> list[dict[str, Any]]:
    if target in ("aiSearch", "aiRltLs"):
        rows = collect_rows(payload, *AI_ROW_KEYS)
        if rows or isinstance(payload.get(target), dict):
            return rows
    rows = payload.get(target)
    if rows is not None:
        return [row for row in ensure_list(rows) if isinstance(row, dict)]
    for value in payload.values():
        if isinstance(value, dict):
            nested = value.get(target)
            if nested is not None:
                return [row for row in ensure_list(nested) if isinstance(row, dict)]
    return collect_rows(payload, target)


def unwrap_service_payload(payload: dict[str, Any], target: str) -> dict[str, Any]:
    if isinstance(payload.get(target), dict):
        return payload[target]
    if len(payload) == 1:
        only = next(iter(payload.values()))
        if isinstance(only, dict):
            return only
        if is_no_result_message(only):
            raise NoResultError(str(only))
    if "기본정보" in payload or "조문" in payload:
        return payload
    raise ParseFailureError(f"Could not unwrap service payload for target {target}")


def is_no_result_message(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return "일치하는" in value and "없습니다" in value
