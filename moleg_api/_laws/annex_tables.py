from __future__ import annotations

from .foundation import *
from .config import *

_ANNEX_HEADER_RE = re.compile(
    r"^\s*■\s*(?P<law>.+?)\s*\[\s*(?P<label>(?:별표|별지)[^\]]*?)\s*\]"
)
_ANNEX_BOX_CHARS = "┏┓┗┛┃┠┨┯┷━│─┌┐└┘├┤┼╋┣┫┳┻╂┿"
# Adopt a header's source-law as related_name only when it reads like a statute
# or subordinate/administrative rule, so junk header text is not treated as a
# citable source reference (which feeds delegated-criteria source verification).
_LEGISLATION_SUFFIXES = ("법", "법률", "령", "규칙", "조례", "규정", "고시", "훈령", "예규", "지침", "준칙")


def _looks_like_legislation_name(name: str) -> bool:
    return name.endswith(_LEGISLATION_SUFFIXES)


def enrich_annex_identity_from_body(
    identity: AnnexFormIdentity, text: str
) -> AnnexFormIdentity:
    """Recover the authoritative annex/form label from the loaded body header.

    The text-download endpoint returns plain text with no title field, so a
    bare-id identity (loaded via ``--id`` with no title) keeps the numeric id as
    its title, which also silences table structuring. Parse the
    ``■ <법령> [별표 N] ...`` header to backfill title/related_name/annex_type,
    filling only fields currently missing so a rich search-hit identity is never
    overwritten.
    """
    lines = text.splitlines()
    header_idx: int | None = None
    match: re.Match[str] | None = None
    for idx, line in enumerate(lines[:6]):
        m = _ANNEX_HEADER_RE.match(line)
        if m:
            header_idx = idx
            match = m
            break
    if match is None or header_idx is None:
        return identity

    law = match.group("law").strip()
    label = match.group("label").strip()
    annex_type = "별표" if label.startswith("별표") else "별지"

    updates: dict[str, Any] = {}
    if not identity.related_name and _looks_like_legislation_name(law):
        updates["related_name"] = law
    if not identity.annex_type:
        updates["annex_type"] = annex_type
    if not identity.annex_number:
        number = re.search(r"\d+", label)
        if number:
            updates["annex_number"] = number.group(0)

    if not identity.title or identity.title == identity.annex_id:
        # 별표 bodies place the annex name on its own line after the header;
        # forms carry it inside the bracket. Prefer the name line, fall back to
        # the bracketed "<법령> [별표 N]" label.
        name_line: str | None = None
        for line in lines[header_idx + 1 : header_idx + 8]:
            stripped = line.strip()
            if not stripped or stripped in ("(앞쪽)", "(뒤쪽)"):
                continue
            if stripped[0] in _ANNEX_BOX_CHARS or stripped.startswith("■"):
                break
            if any("가" <= ch <= "힣" for ch in stripped):
                name_line = stripped
            break
        if name_line and annex_type == "별표":
            updates["title"] = f"{law} [{label}] {name_line}"
        else:
            updates["title"] = f"{law} [{label}]"

    if not updates:
        return identity
    return replace(identity, **updates)


def structure_annex_form_text(text: str, identity: AnnexFormIdentity) -> StructuredTableData:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    pipe_table = parse_pipe_table(lines, identity)
    if pipe_table:
        return pipe_table
    spaced_table = parse_spaced_table(lines, identity)
    if spaced_table:
        return spaced_table
    return low_confidence_table(identity)


def parse_pipe_table(lines: list[str], identity: AnnexFormIdentity) -> StructuredTableData | None:
    table_rows: list[list[str]] = []
    for line in lines:
        if "|" not in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if is_markdown_separator(cells):
            continue
        if len(cells) >= 2 and all(cells):
            table_rows.append(cells)
    return structured_table_from_rows(table_rows, identity)


def parse_spaced_table(lines: list[str], identity: AnnexFormIdentity) -> StructuredTableData | None:
    table_rows: list[list[str]] = []
    expected_columns: int | None = None
    for line in lines:
        cells = [cell.strip() for cell in re.split(r"\s{2,}", line.strip()) if cell.strip()]
        if len(cells) < 2:
            if table_rows:
                break
            continue
        if expected_columns is None:
            expected_columns = len(cells)
        if len(cells) != expected_columns:
            break
        table_rows.append(cells)
    return structured_table_from_rows(table_rows, identity)


def structured_table_from_rows(
    table_rows: list[list[str]],
    identity: AnnexFormIdentity,
) -> StructuredTableData | None:
    if len(table_rows) < 2:
        return None
    headers = table_rows[0]
    body_rows = table_rows[1:]
    if not body_rows or any(len(row) != len(headers) for row in body_rows):
        return None
    # A cleanly delimited table has its separators stripped. Residual box-drawing
    # glyphs (┃│┏…) inside cells mean the splitter matched the wrong delimiter and
    # produced a junk table (the real amount rows get dropped). Never report that
    # as high confidence — fall back to plain text so amounts are read from .text.
    if any(ch in _ANNEX_BOX_CHARS for row in table_rows for cell in row for ch in cell):
        return low_confidence_table(identity)
    keys = normalized_table_keys(headers)
    rows = [dict(zip(keys, row, strict=True)) for row in body_rows]
    return StructuredTableData(
        title=identity.title,
        headers=headers,
        rows=rows,
        units=table_units(rows),
        parsing_confidence="high",
        notes=[],
    )


def normalized_table_keys(headers: list[str]) -> list[str]:
    keys: list[str] = []
    seen: dict[str, int] = {}
    for index, header in enumerate(headers, start=1):
        key = re.sub(r"\s+", "_", header.strip().lower())
        key = re.sub(r"[^\w가-힣]+", "_", key).strip("_")
        if not key:
            key = f"column_{index}"
        count = seen.get(key, 0)
        seen[key] = count + 1
        keys.append(key if count == 0 else f"{key}_{count + 1}")
    return keys


def table_units(rows: list[dict[str, str]]) -> list[str]:
    units: list[str] = []
    seen: set[str] = set()
    unit_pattern = re.compile(r"\d+(?:\.\d+)?\s*(만원|천원|억원|원|%|퍼센트|명|개|건|일|개월|년)")
    for row in rows:
        for value in row.values():
            for match in unit_pattern.findall(value):
                if match not in seen:
                    seen.add(match)
                    units.append(match)
    return units


def is_markdown_separator(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def low_confidence_table(identity: AnnexFormIdentity) -> StructuredTableData:
    return StructuredTableData(
        title=identity.title,
        headers=[],
        rows=[],
        units=[],
        parsing_confidence="low",
        notes=["plain text retained; table structure was irregular or ambiguous"],
    )

from .validation import *
from .identity_params import *
from .admin_scope import *
from .temporal_gaps import *
from .delegated_scope import *
from .source_matching import *
from .article_gaps import *
from .history_identity import *
from .authority_sources import *
from .candidates import *
from .followup_searches import *
from .followup_hits import *
from .limits_intents import *
from .authority_article_gaps import *
from .authority_temporal_gaps import *
from .authority_temporal_filters import *
from .followup_basic import *
from .followup_identities import *
from .bridge import *
from .requested_load_gaps import *
from .context_load_gaps import *
from .ranking import *

__all__ = [name for name in globals() if not name.startswith("__")]
