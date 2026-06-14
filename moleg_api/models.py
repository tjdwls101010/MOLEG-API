"""Public data models for the first MOLEG-API vertical slice."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


Basis = Literal["effective", "promulgated"]


@dataclass(frozen=True)
class LawIdentity:
    """Normalized law identity exposed to skill callers."""

    law_id: str | None
    name: str
    basis: Basis
    mst: str | None = None
    lid: str | None = None
    promulgation_date: str | None = None
    effective_date: str | None = None
    promulgation_number: str | None = None
    law_type: str | None = None
    ministry: str | None = None
    raw_keys: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LawHit:
    """Search result carrying a normalized identity and source row."""

    identity: LawIdentity
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ArticleText:
    """Normalized article text."""

    identity: LawIdentity
    article: str
    text: str
    title: str | None = None
    effective_date: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LawText:
    """Normalized law text with article list and raw source payload."""

    identity: LawIdentity
    articles: list[ArticleText]
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HistoryEvent:
    """Normalized law or article change event."""

    identity: LawIdentity
    changed_date: str | None = None
    effective_date: str | None = None
    promulgation_date: str | None = None
    promulgation_number: str | None = None
    revision_type: str | None = None
    article: str | None = None
    reason: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LawHistory:
    """Normalized history result."""

    identity: LawIdentity
    events: list[HistoryEvent]
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LawDiffChange:
    """One before/after article comparison row."""

    article: str
    before_text: str
    after_text: str
    title: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LawDiff:
    """Normalized before/after law comparison."""

    identity: LawIdentity
    before_identity: LawIdentity | None
    after_identity: LawIdentity | None
    changes: list[LawDiffChange]
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DelegatedRule:
    """One delegated rule or lower-law relationship."""

    source_article: str | None = None
    source_article_title: str | None = None
    delegated_type: str | None = None
    delegated_name: str | None = None
    delegated_law_id: str | None = None
    delegated_mst: str | None = None
    delegated_article: str | None = None
    text: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DelegationGraph:
    """Delegation graph rooted at one law identity."""

    identity: LawIdentity
    rules: list[DelegatedRule]
    raw: dict[str, Any] = field(default_factory=dict)
