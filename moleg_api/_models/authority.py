"""Interpretation and judicial authority models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .followups import DeferredLookup

@dataclass(frozen=True)
class InterpretationIdentity:
    """Normalized legal-interpretation identity."""

    interpretation_id: str | None
    title: str
    source_type: str
    source_target: str
    case_number: str | None = None
    interpretation_date: str | None = None
    reply_agency: str | None = None
    reply_agency_code: str | None = None
    inquiry_agency: str | None = None
    inquiry_agency_code: str | None = None
    ministry: str | None = None
    data_timestamp: str | None = None
    raw_keys: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InterpretationHit:
    """Search result carrying a normalized interpretation identity."""

    identity: InterpretationIdentity
    raw: dict[str, Any] = field(default_factory=dict)
    follow_up: DeferredLookup | None = None


@dataclass(frozen=True)
class ArticleReference:
    """Structured reference to a statute article parsed from source text."""

    law_name: str
    article: str
    law_id: str | None = None


@dataclass(frozen=True)
class InterpretationText:
    """Normalized legal-interpretation full text."""

    identity: InterpretationIdentity
    question: str | None = None
    answer: str | None = None
    reason: str | None = None
    related_laws: str | None = None
    referenced_articles: list[ArticleReference] = field(default_factory=list)
    text: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class JudicialDecisionIdentity:
    """Normalized court case or Constitutional Court decision identity."""

    decision_id: str | None
    title: str
    source_type: str
    source_target: str
    case_number: str | None = None
    decision_date: str | None = None
    court: str | None = None
    court_type_code: str | None = None
    case_type: str | None = None
    decision_type: str | None = None
    data_source: str | None = None
    raw_keys: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class JudicialDecisionHit:
    """Search result carrying normalized judicial decision identity."""

    identity: JudicialDecisionIdentity
    raw: dict[str, Any] = field(default_factory=dict)
    follow_up: DeferredLookup | None = None


@dataclass(frozen=True)
class JudicialDecisionText:
    """Normalized court case or Constitutional Court decision text."""

    identity: JudicialDecisionIdentity
    holdings: str | None = None
    summary: str | None = None
    full_text: str | None = None
    referenced_statutes: str | None = None
    reviewed_statutes: str | None = None
    referenced_cases: str | None = None
    referenced_articles: list[ArticleReference] = field(default_factory=list)
    reviewed_articles: list[ArticleReference] = field(default_factory=list)
    text: str = ""
    raw: dict[str, Any] = field(default_factory=dict)
