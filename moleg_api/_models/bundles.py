"""Context bundle and authority aggregate models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .admin import AdministrativeRuleHit, AdministrativeRuleText
from .annex import AnnexFormHit, AnnexFormText
from .authority import InterpretationHit, InterpretationText, JudicialDecisionHit, JudicialDecisionText
from .followups import Ambiguity, ContextGap, DeferredLookup
from .laws import ArticleText, DelegationGraph, LawIdentity, LawStructure, LawText
from .query import LegalQueryExpansion
from .types import BundleBudget, BundleRequestMode

@dataclass(frozen=True)
class BundleRequest:
    """Request metadata for a legal context bundle."""

    query: str | None
    mode: BundleRequestMode
    budget: BundleBudget
    articles: list[str | int] = field(default_factory=list)
    statute_ids: list[str] = field(default_factory=list)
    promulgation_bridge: dict[str, Any] = field(default_factory=dict)
    law_identifier: Any = None
    as_of: str | None = None


@dataclass(frozen=True)
class LoadedContext:
    """Official context already loaded for Claude to inspect."""

    laws: list[LawText] = field(default_factory=list)
    articles: list[ArticleText] = field(default_factory=list)
    delegations: list[DelegationGraph] = field(default_factory=list)
    law_structures: list[LawStructure] = field(default_factory=list)
    administrative_rules: list[AdministrativeRuleText] = field(default_factory=list)
    annex_forms: list[AnnexFormText] = field(default_factory=list)
    interpretations: list[InterpretationText] = field(default_factory=list)
    cases: list[JudicialDecisionText] = field(default_factory=list)
    constitutional_decisions: list[JudicialDecisionText] = field(default_factory=list)


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


@dataclass(frozen=True)
class AuthorityContext:
    """Authority lookup context scoped to loaded target articles."""

    request: BundleRequest
    target_articles: list[ArticleText] = field(default_factory=list)
    loaded: LoadedContext = field(default_factory=LoadedContext)
    current_authorities: LoadedContext = field(default_factory=LoadedContext)
    candidates: CandidateContext = field(default_factory=CandidateContext)
    deferred: list[DeferredLookup] = field(default_factory=list)
    gaps: list[ContextGap] = field(default_factory=list)
    source_notes: list[str] = field(default_factory=list)
