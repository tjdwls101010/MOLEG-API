"""Core law, article, history, and hierarchy models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from .followups import ContextGap, DeferredLookup
from .types import Basis

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
    follow_up: DeferredLookup | None = None


@dataclass(frozen=True)
class ArticleText:
    """Normalized article text."""

    identity: LawIdentity
    article: str
    text: str
    title: str | None = None
    effective_date: str | None = None
    article_kind: str | None = None
    revision_type: str | None = None
    moved_from: str | None = None
    moved_to: str | None = None
    has_changes: bool | None = None
    is_deleted: bool = False
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ArticleContext:
    """Article lookup context with movement/deletion guardrails."""

    requested_article: ArticleText
    current_article: ArticleText | None
    loaded_articles: list[ArticleText] = field(default_factory=list)
    deferred: list[DeferredLookup] = field(default_factory=list)
    gaps: list[ContextGap] = field(default_factory=list)
    source_notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SupplementaryProvision:
    """Normalized supplementary provision/addendum text."""

    source_type: Literal["law", "administrative_rule"]
    text: str
    promulgation_date: str | None = None
    promulgation_number: str | None = None
    title: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LawText:
    """Normalized law text with article list and raw source payload."""

    identity: LawIdentity
    articles: list[ArticleText]
    supplementary_provisions: list[SupplementaryProvision] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HistoryEvent:
    """Normalized law or article change event."""

    identity: LawIdentity
    changed_date: str | None = None
    effective_date: str | None = None
    promulgation_law_name: str | None = None
    promulgation_date: str | None = None
    promulgation_number: str | None = None
    bill_id: str | None = None
    revision_type: str | None = None
    article: str | None = None
    article_text: str | None = None
    article_link: str | None = None
    reason: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LawHistory:
    """Normalized history result."""

    identity: LawIdentity
    events: list[HistoryEvent]
    source_failures: list[ContextGap] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LawTocEntry:
    """One line of a statute's table of contents — a heading or an article stub.

    Empty fields are omitted on serialization: with 139 entries, the null and
    false placeholders outweighed the content they surrounded, and `is_deleted`
    absent reads the same as `is_deleted: false` while `is_deleted: true` still
    stands out — which is the only case a reader has to notice.
    """

    _omit_when_empty = ("article", "title", "heading", "is_deleted", "moved_to")

    article: str | None = None
    title: str | None = None
    heading: str | None = None
    entry_kind: str = "article"
    is_deleted: bool = False
    moved_to: str | None = None


@dataclass(frozen=True)
class LawToc:
    """A statute's article map without any article text.

    Exists because the alternative was loading everything: a full 개인정보 보호법
    is 139 articles and ~174,000 characters, and the only narrowing tool was
    `--article`, which presumes you already know which article you want. Reading
    the whole statute to find that out is the expensive way to ask a cheap
    question. The table of contents answers "what is in here" in a few KB and
    turns the follow-up into a targeted load.
    """

    identity: LawIdentity
    entries: list[LawTocEntry]
    article_count: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RevisionReason:
    """The 「개정이유 및 주요내용」 block for one statute version.

    Distinct from `HistoryEvent.revision_type`, which only carries a change-type
    label such as 일부개정 or 본조신설. This is the drafter's stated *why* — the
    problem the amendment claims to answer — which is what a policy reading
    actually needs and which no other command reaches.

    Scoped to one version by design: law.go.kr embeds each version's reason in
    that version's own detail response, so `mst` is what pins which amendment
    this text explains.
    """

    identity: LawIdentity
    mst: str | None = None
    reason: str | None = None
    promulgation_text: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LawDiffChange:
    """One before/after article comparison row."""

    article: str | None
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


@dataclass(frozen=True)
class LawStructureNode:
    """One law-structure node from the MOLEG structural hierarchy."""

    name: str
    source_type: str
    instrument_type: str
    law_id: str | None = None
    mst: str | None = None
    serial_id: str | None = None
    rule_id: str | None = None
    law_type: str | None = None
    effective_date: str | None = None
    promulgation_date: str | None = None
    promulgation_number: str | None = None
    issuing_date: str | None = None
    issuing_number: str | None = None
    ministry: str | None = None
    detail_link: str | None = None
    children: list[LawStructureNode] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LawStructure:
    """Normalized law hierarchy from the MOLEG law-structure view."""

    identity: LawIdentity
    instruments: list[LawStructureNode]
    raw: dict[str, Any] = field(default_factory=dict)
