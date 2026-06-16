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
    raw_keys: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AdministrativeRuleHit:
    """Search result carrying a normalized administrative-rule identity."""

    identity: AdministrativeRuleIdentity
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AdministrativeRuleArticleText:
    """Normalized administrative-rule article or text section."""

    identity: AdministrativeRuleIdentity
    article: str | None
    text: str
    title: str | None = None
    effective_date: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AdministrativeRuleText:
    """Normalized administrative-rule text."""

    identity: AdministrativeRuleIdentity
    text: str
    articles: list[AdministrativeRuleArticleText]
    raw: dict[str, Any] = field(default_factory=dict)


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


@dataclass(frozen=True)
class AnnexFormText:
    """Extracted annex/form body text."""

    identity: AnnexFormIdentity
    text: str
    file_type: str
    extraction_method: str
    extraction_confidence: str
    raw: dict[str, Any] = field(default_factory=dict)


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


@dataclass(frozen=True)
class InterpretationText:
    """Normalized legal-interpretation full text."""

    identity: InterpretationIdentity
    question: str | None = None
    answer: str | None = None
    reason: str | None = None
    related_laws: str | None = None
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
    text: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


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
    source_type: str = "law"
    source_target: str | None = None
    relation: str | None = None
    article: str | None = None
    article_title: str | None = None
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
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BundleRequest:
    """Request metadata for a legal context bundle."""

    query: str | None
    mode: str
    budget: str
    articles: list[str | int] = field(default_factory=list)
    statute_ids: list[str] = field(default_factory=list)
    promulgation_bridge: dict[str, Any] = field(default_factory=dict)
    law_identifier: Any = None


@dataclass(frozen=True)
class LoadedContext:
    """Official context already loaded for Claude to inspect."""

    laws: list[LawText] = field(default_factory=list)
    articles: list[ArticleText] = field(default_factory=list)
    delegations: list[DelegationGraph] = field(default_factory=list)
    law_structures: list[LawStructure] = field(default_factory=list)
    administrative_rules: list[AdministrativeRuleText] = field(default_factory=list)
    interpretations: list[InterpretationText] = field(default_factory=list)
    cases: list[JudicialDecisionText] = field(default_factory=list)
    constitutional_decisions: list[JudicialDecisionText] = field(default_factory=list)
    histories: list[LawHistory] = field(default_factory=list)
    diffs: list[LawDiff] = field(default_factory=list)


@dataclass(frozen=True)
class CandidateContext:
    """Candidate context discovered but not necessarily loaded."""

    query_expansion: LegalQueryExpansion | None = None
    laws: list[LawIdentity] = field(default_factory=list)
    administrative_rules: list[AdministrativeRuleHit] = field(default_factory=list)
    annex_forms: list[AnnexFormHit] = field(default_factory=list)
    interpretations: list[InterpretationHit] = field(default_factory=list)
    cases: list[JudicialDecisionHit] = field(default_factory=list)
    constitutional_decisions: list[JudicialDecisionHit] = field(default_factory=list)


@dataclass(frozen=True)
class DeferredLookup:
    """A bounded follow-up lookup the skill may choose to run later."""

    interface: str
    query: str
    reason: str
    source_type: str | None = None
    filters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Ambiguity:
    """Ambiguity that must not be silently resolved."""

    kind: str
    message: str
    candidates: list[Any] = field(default_factory=list)


@dataclass(frozen=True)
class ContextGap:
    """Context that should be filled by another source or human review."""

    kind: str
    reason: str
    query: str | None = None
    recommended_interface: str | None = None


@dataclass(frozen=True)
class LegalContextBundle:
    """Staged legal context for the legislative-expert skill."""

    request: BundleRequest
    loaded: LoadedContext
    candidates: CandidateContext
    deferred: list[DeferredLookup] = field(default_factory=list)
    ambiguities: list[Ambiguity] = field(default_factory=list)
    gaps: list[ContextGap] = field(default_factory=list)
    source_notes: list[str] = field(default_factory=list)
