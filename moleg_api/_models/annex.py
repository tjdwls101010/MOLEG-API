"""Annex and form model group."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .followups import DeferredLookup

@dataclass(frozen=True)
class AnnexFormIdentity:
    """Normalized law or administrative-rule annex/form identity."""

    annex_id: str | None
    title: str
    source_type: str
    source_target: str
    related_name: str | None = None
    related_id: str | None = None
    related_serial_id: str | None = None
    annex_number: str | None = None
    annex_type: str | None = None
    ministry: str | None = None
    promulgation_date: str | None = None
    promulgation_number: str | None = None
    issued_on: str | None = None
    issuing_number: str | None = None
    revision_type: str | None = None
    law_type: str | None = None
    rule_type: str | None = None
    file_link: str | None = None
    pdf_link: str | None = None
    detail_link: str | None = None
    raw_keys: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AnnexFormHit:
    """Search result carrying a normalized annex/form identity."""

    identity: AnnexFormIdentity
    raw: dict[str, Any] = field(default_factory=dict)
    follow_up: DeferredLookup | None = None


@dataclass(frozen=True)
class StructuredTableData:
    """Best-effort structured rows extracted from a text-export annex/form body."""

    title: str | None
    headers: list[str]
    rows: list[dict[str, str]]
    units: list[str] = field(default_factory=list)
    parsing_confidence: str = "low"
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AnnexFormText:
    """Extracted annex/form body text."""

    identity: AnnexFormIdentity
    text: str
    file_type: str
    extraction_method: str
    extraction_confidence: str
    structured_data: StructuredTableData | None = None
    raw: dict[str, Any] = field(default_factory=dict)
