"""Row traversal and article label formatting helpers."""

from __future__ import annotations

from typing import Any, Literal

import re

from moleg_api.errors import ParseFailureError

from .primitives import _digits, ensure_list, first_value

def collect_rows(obj: Any, *keys: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(obj, list):
        for item in obj:
            rows.extend(collect_rows(item, *keys))
    elif isinstance(obj, dict):
        for key in keys:
            value = obj.get(key)
            if isinstance(value, list):
                rows.extend([item for item in value if isinstance(item, dict)])
            elif isinstance(value, dict):
                if any(isinstance(value.get(k), (list, dict)) for k in keys):
                    rows.extend(collect_rows(value, *keys))
                else:
                    rows.append(value)
        if not rows:
            for value in obj.values():
                if isinstance(value, (list, dict)):
                    rows.extend(collect_rows(value, *keys))
    return rows


def article_rows_from_diff(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    container = payload.get(key)
    if isinstance(container, dict):
        return [row for row in ensure_list(container.get("조문")) if isinstance(row, dict)]
    return []


def article_key(row: dict[str, Any]) -> str:
    return article_label_from_parts(
        first_value(row, "no", "조문번호", "JO"),
        first_value(row, "조문가지번호", "조가지번호"),
    ) or ""


def article_label(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if text.startswith("제"):
        return text
    if re.fullmatch(r"\d{6}", text):
        main = int(text[:4])
        branch = int(text[4:])
        return f"제{main}조의{branch}" if branch else f"제{main}조"
    match = re.fullmatch(r"(\d+)\s*조(?:\s*의\s*(\d+))?", text)
    if match:
        main = int(match.group(1))
        branch = int(match.group(2) or 0)
        return f"제{main}조의{branch}" if branch else f"제{main}조"
    if text.isdigit():
        return f"제{int(text)}조"
    return text


def annex_number_from_parts(number: Any, branch: Any = None) -> str | None:
    if number in (None, ""):
        return None
    text = str(number).strip()
    branch_text = str(branch or "").strip()
    if not branch_text or not branch_text.isdigit() or int(branch_text) == 0:
        return text
    if re.search(r"의\s*\d+", text):
        return text
    return f"{text}의{int(branch_text)}"


def article_label_from_parts(number: Any, branch: Any = None) -> str | None:
    if number in (None, ""):
        return None
    text = str(number).strip()
    branch_text = str(branch or "").strip()
    branch_number = int(branch_text) if branch_text.isdigit() and int(branch_text) != 0 else None
    if branch_number is None and re.fullmatch(r"\d{6}", text):
        main = int(text[:4])
        source_branch = int(text[4:])
        return f"제{main}조의{source_branch}" if source_branch else f"제{main}조"
    if text.startswith("제"):
        if branch_number is not None:
            match = re.fullmatch(r"제\s*(\d+)\s*조", text)
            if match:
                return f"제{int(match.group(1))}조의{branch_number}"
        return text
    if not text.isdigit():
        return text
    main = int(text)
    if branch_number is not None:
        return f"제{main}조의{branch_number}"
    return f"제{main}조"


def format_article_jo(article: str | int) -> str:
    if isinstance(article, int):
        return f"{article:04d}00"
    text = str(article).strip()
    if re.fullmatch(r"\d{6}", text):
        return text
    match = re.search(r"제?\s*(\d+)\s*조(?:\s*의\s*(\d+))?", text)
    if match:
        main = int(match.group(1))
        branch = int(match.group(2) or 0)
        return f"{main:04d}{branch:02d}"
    if text.isdigit():
        return f"{int(text):04d}00"
    raise ParseFailureError(f"Unsupported article notation: {article}")
