"""Serialization helpers shared by public dataclass models."""

from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from typing import Any

def _model_to_dict(self: Any, *, include_raw: bool = False) -> dict[str, Any]:
    return _serialize_dataclass(self, include_raw=include_raw)


def _model_to_json_string(self: Any, *, include_raw: bool = False) -> str:
    return json.dumps(
        self.to_dict(include_raw=include_raw),
        ensure_ascii=False,
        sort_keys=True,
    )


def _serialize_dataclass(value: Any, *, include_raw: bool) -> dict[str, Any]:
    # A model may declare `_omit_when_empty` to drop fields that carry nothing.
    # Normally the opposite is right — a present-but-null field tells a consumer
    # the concept exists and is unset. It stops being right when a model is a
    # long list of small rows: on a 139-entry statute map, the null and false
    # placeholders were most of the payload, and a table of contents that costs
    # what the full text costs is not a table of contents.
    omit = getattr(type(value), "_omit_when_empty", ())
    data: dict[str, Any] = {}
    for item in fields(value):
        if item.name == "raw" and not include_raw:
            continue
        current = getattr(value, item.name)
        if item.name in omit and current in (None, "", False, [], {}):
            continue
        data[item.name] = _serialize_value(current, include_raw=include_raw)
    return data


def _serialize_value(value: Any, *, include_raw: bool) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _serialize_dataclass(value, include_raw=include_raw)
    if isinstance(value, list):
        return [_serialize_value(item, include_raw=include_raw) for item in value]
    if isinstance(value, tuple):
        return [_serialize_value(item, include_raw=include_raw) for item in value]
    if isinstance(value, set):
        serialized_items = [_serialize_value(item, include_raw=include_raw) for item in value]
        return sorted(serialized_items, key=_json_sort_key)
    if isinstance(value, dict):
        return _serialize_dict(value, include_raw=include_raw)
    return value


def _json_sort_key(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _serialize_dict(value: dict[Any, Any], *, include_raw: bool) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    groups: dict[str, list[dict[str, Any]]] = {}
    for key, item in value.items():
        serialized_key = _serialize_key(key)
        entry = {
            "key": key,
            "item": item,
            "serialized_key": serialized_key,
            "disambiguated_key": _serialize_disambiguated_key(key),
            "output_key": serialized_key,
        }
        entries.append(entry)
        groups.setdefault(serialized_key, []).append(entry)

    for group in groups.values():
        if len(group) > 1:
            for entry in group:
                entry["output_key"] = entry["disambiguated_key"]

    while True:
        output_groups: dict[str, list[dict[str, Any]]] = {}
        for entry in entries:
            output_groups.setdefault(entry["output_key"], []).append(entry)
        conflicting_entries = [
            entry
            for group in output_groups.values()
            if len(group) > 1
            for entry in group
        ]
        promoted = False
        for entry in conflicting_entries:
            if entry["output_key"] != entry["disambiguated_key"]:
                entry["output_key"] = entry["disambiguated_key"]
                promoted = True
        if not promoted:
            break

    data: dict[str, Any] = {}
    for entry in sorted(entries, key=_serialized_entry_sort_key):
        output_key = _dedupe_key(entry["output_key"], data)
        data[output_key] = _serialize_value(entry["item"], include_raw=include_raw)
    return data


def _serialize_key(key: Any) -> str:
    if isinstance(key, str):
        return key
    return str(key)


def _serialize_disambiguated_key(key: Any) -> str:
    return f"{type(key).__name__}:{key!r}"


def _serialized_entry_sort_key(entry: dict[str, Any]) -> tuple[str, str]:
    key = entry["key"]
    return (entry["output_key"], f"{type(key).__module__}.{type(key).__qualname__}:{key!r}")


def _dedupe_key(key: str, data: dict[str, Any]) -> str:
    if key not in data:
        return key
    counter = 2
    while f"{key}#{counter}" in data:
        counter += 1
    return f"{key}#{counter}"


def install_serialization_methods(namespace: dict[str, Any], *, public_module: str) -> None:
    for value in list(namespace.values()):
        if isinstance(value, type) and is_dataclass(value):
            value.__module__ = public_module
            setattr(value, "to_dict", _model_to_dict)
            setattr(value, "to_json_string", _model_to_json_string)
