from __future__ import annotations

from .bundle_state import BundleState
from .support import *


def finalize_bundle(
    request: BundleRequest,
    search_query: str | None,
    state: BundleState,
) -> LegalContextBundle:
    append_bundle_deferred_from_candidates(state)
    if search_query:
        state.gaps.append(
            ContextGap(
                kind="websearch_required",
                reason="Use WebSearch for latest social facts, statistics, policy announcements, news, or non-MOLEG background.",
                query=search_query,
                recommended_interface="websearch",
            )
        )

    return LegalContextBundle(
        request=request,
        loaded=LoadedContext(
            laws=state.loaded_laws,
            articles=state.loaded_articles,
            delegations=state.loaded_delegations,
            interpretations=state.loaded_interpretations,
            cases=state.loaded_cases,
            constitutional_decisions=state.loaded_constitutional_decisions,
        ),
        candidates=CandidateContext(
            query_expansion=state.query_expansion,
            laws=state.law_candidates,
            administrative_rules=state.administrative_candidates,
            annex_forms=state.annex_form_candidates,
            interpretations=state.interpretation_candidates,
            cases=state.case_candidates,
            constitutional_decisions=state.constitutional_candidates,
        ),
        deferred=state.deferred,
        ambiguities=state.ambiguities,
        gaps=state.gaps,
        source_notes=state.source_notes,
    )


def append_bundle_deferred_from_candidates(state: BundleState) -> None:
    state.deferred.extend(
        deferred_from_candidates(
            state.administrative_candidates,
            "get_administrative_rule",
            "administrative_rule",
        )
    )
    state.deferred.extend(
        deferred_from_candidates(
            state.annex_form_candidates,
            "get_annex_form_body",
            "annex_form",
        )
    )
    state.deferred.extend(
        deferred_from_candidates(
            unloaded_candidates(state.interpretation_candidates, state.loaded_detail_keys),
            "get_interpretation",
            "interpretation",
        )
    )
    state.deferred.extend(
        deferred_from_candidates(
            unloaded_candidates(state.case_candidates, state.loaded_detail_keys),
            "get_case",
            "case",
        )
    )
    state.deferred.extend(
        deferred_from_candidates(
            unloaded_candidates(state.constitutional_candidates, state.loaded_detail_keys),
            "get_constitutional_decision",
            "constitutional",
        )
    )


__all__ = [name for name in globals() if not name.startswith("__")]
