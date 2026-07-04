from __future__ import annotations

from .support import *


@dataclass
class BundleState:
    source_notes: list[str]
    ambiguities: list[Ambiguity]
    gaps: list[ContextGap]
    deferred: list[DeferredLookup]
    loaded_laws: list[LawText]
    loaded_articles: list[ArticleText]
    authority_target_articles: list[ArticleText]
    loaded_delegations: list[DelegationGraph]
    loaded_interpretations: list[InterpretationText]
    loaded_cases: list[JudicialDecisionText]
    loaded_constitutional_decisions: list[JudicialDecisionText]
    query_expansion: LegalQueryExpansion | None
    law_candidates: list[LawIdentity]
    administrative_candidates: list[AdministrativeRuleHit]
    annex_form_candidates: list[AnnexFormHit]
    interpretation_candidates: list[InterpretationHit]
    case_candidates: list[JudicialDecisionHit]
    constitutional_candidates: list[JudicialDecisionHit]
    loaded_detail_keys: set[tuple[str | None, str]]


@dataclass
class BundleSeed:
    primary_identity: LawIdentity | None
    search_query: str | None


def new_bundle_state() -> BundleState:
    return BundleState(
        source_notes=["LegalContextBundle is staged context for Claude inspection, not a legal conclusion."],
        ambiguities=[],
        gaps=[],
        deferred=[],
        loaded_laws=[],
        loaded_articles=[],
        authority_target_articles=[],
        loaded_delegations=[],
        loaded_interpretations=[],
        loaded_cases=[],
        loaded_constitutional_decisions=[],
        query_expansion=None,
        law_candidates=[],
        administrative_candidates=[],
        annex_form_candidates=[],
        interpretation_candidates=[],
        case_candidates=[],
        constitutional_candidates=[],
        loaded_detail_keys=set(),
    )


__all__ = [name for name in globals() if not name.startswith("__")]
