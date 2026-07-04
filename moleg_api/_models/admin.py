"""Administrative-rule model group."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .followups import ContextGap, DeferredLookup
from .laws import SupplementaryProvision

@dataclass(frozen=True)
class AdministrativeRuleIdentity:
    """Normalized administrative-rule identity."""

    serial_id: str | None
    name: str
    rule_id: str | None = None
    rule_type: str | None = None
    issuing_date: str | None = None
    issuing_number: str | None = None
    effective_date: str | None = None
    ministry: str | None = None
    ministry_code: str | None = None
    current_status: str | None = None
    revision_type: str | None = None
    source_law_id: str | None = None
    source_law_name: str | None = None
    source_article: str | None = None
    source_article_title: str | None = None
    raw_keys: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AdministrativeRuleHit:
    """Search result carrying a normalized administrative-rule identity."""

    identity: AdministrativeRuleIdentity
    raw: dict[str, Any] = field(default_factory=dict)
    follow_up: DeferredLookup | None = None


@dataclass(frozen=True)
class AdministrativeRuleArticleText:
    """Normalized administrative-rule article or text section."""

    identity: AdministrativeRuleIdentity
    article: str | None
    text: str
    title: str | None = None
    effective_date: str | None = None
    article_kind: str | None = None
    revision_type: str | None = None
    moved_from: str | None = None
    moved_to: str | None = None
    has_changes: bool | None = None
    is_deleted: bool = False
    source_law_id: str | None = None
    source_law_name: str | None = None
    source_article: str | None = None
    source_article_title: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AdministrativeRuleText:
    """Normalized administrative-rule text."""

    identity: AdministrativeRuleIdentity
    text: str
    articles: list[AdministrativeRuleArticleText]
    supplementary_provisions: list[SupplementaryProvision] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AdministrativeRuleContext:
    """Administrative-rule lookup context with article-status guardrails."""

    rule: AdministrativeRuleText
    requested_articles: list[AdministrativeRuleArticleText] = field(default_factory=list)
    current_articles: list[AdministrativeRuleArticleText] = field(default_factory=list)
    loaded_articles: list[AdministrativeRuleArticleText] = field(default_factory=list)
    deferred: list[DeferredLookup] = field(default_factory=list)
    gaps: list[ContextGap] = field(default_factory=list)
    source_notes: list[str] = field(default_factory=list)
