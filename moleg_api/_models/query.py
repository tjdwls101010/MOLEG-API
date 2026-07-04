"""Query-expansion candidate models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .followups import ContextGap, FollowUpSearch
from .laws import LawIdentity

@dataclass(frozen=True)
class LegalTermCandidate:
    """Legal or everyday term candidate for query planning."""

    term: str
    source_type: str
    source_target: str
    term_id: str | None = None
    relation: str | None = None
    note: str | None = None
    definition: str | None = None
    source_title: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LegalArticleCandidate:
    """Article candidate discovered during query expansion."""

    law_name: str | None
    law_id: str | None = None
    article: str | None = None
    title: str | None = None
    text: str | None = None
    source_target: str | None = None
    term: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LegalLawCandidate:
    """Law or administrative-rule candidate discovered during query expansion."""

    name: str
    law_id: str | None = None
    mst: str | None = None
    source_type: str = "law"
    source_target: str | None = None
    relation: str | None = None
    article: str | None = None
    article_title: str | None = None
    promulgation_date: str | None = None
    effective_date: str | None = None
    promulgation_number: str | None = None
    law_type: str | None = None
    ministry: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FollowUpSearch:
    """Recommended next search for the legislative-expert skill."""

    interface: str
    query: str
    reason: str
    source_type: str | None = None
    filters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LegalQueryExpansion:
    """Query-planning result; not final legal authority."""

    original_query: str
    law_candidates: list[LawIdentity]
    term_candidates: list[LegalTermCandidate]
    related_terms: list[LegalTermCandidate]
    related_articles: list[LegalArticleCandidate]
    related_laws: list[LegalLawCandidate]
    follow_up_searches: list[FollowUpSearch]
    empty_sources: list[str] = field(default_factory=list)
    source_failures: list[ContextGap] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
