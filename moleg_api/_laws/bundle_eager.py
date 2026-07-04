from __future__ import annotations

from .bundle_state import BundleState
from .support import *


def load_bundle_eager_details(
    api: Any,
    request: BundleRequest,
    search_query: str | None,
    article_target_queries: list[str],
    state: BundleState,
) -> None:
    eager_detail_limits = bundle_eager_detail_limits(search_query, mode=request.mode, budget=request.budget)
    if any(item.kind == "statute_identity" for item in state.ambiguities):
        eager_detail_limits = {key: 0 for key in eager_detail_limits}
        state.source_notes.append(
            "Eager authority detail loading skipped until statute identity ambiguity is resolved."
        )

    authority_ranking_query = " ".join(article_target_queries) if search_query else search_query
    eager_text_budget = BUNDLE_EAGER_TEXT_CHAR_LIMITS[request.budget]
    eager_text_used = 0
    if any(eager_detail_limits.values()):
        state.source_notes.append(
            "Eager detail loading triggered for "
            + ", ".join(key for key, value in eager_detail_limits.items() if value)
            + "."
        )

    eager_text_used = load_bundle_eager_detail_group(
        api.get_interpretation,
        state.interpretation_candidates,
        authority_ranking_query,
        eager_detail_limits["interpretations"],
        eager_text_budget,
        eager_text_used,
        state.loaded_interpretations,
        state,
        recommended_interface="get_interpretation",
        source_label="Eager interpretation detail load",
    )
    eager_text_used = load_bundle_eager_detail_group(
        api.get_case,
        state.case_candidates,
        authority_ranking_query,
        eager_detail_limits["cases"],
        eager_text_budget,
        eager_text_used,
        state.loaded_cases,
        state,
        recommended_interface="get_case",
        source_label="Eager case detail load",
    )
    load_bundle_eager_detail_group(
        api.get_constitutional_decision,
        state.constitutional_candidates,
        authority_ranking_query,
        eager_detail_limits["constitutional_decisions"],
        eager_text_budget,
        eager_text_used,
        state.loaded_constitutional_decisions,
        state,
        recommended_interface="get_constitutional_decision",
        source_label="Eager constitutional detail load",
    )
    append_bundle_authority_gaps(state, request.as_of)


def load_bundle_eager_detail_group(
    loader: Any,
    candidates: list[Any],
    ranking_query: str | None,
    limit: int,
    eager_text_budget: int,
    eager_text_used: int,
    loaded: list[Any],
    state: BundleState,
    *,
    recommended_interface: str,
    source_label: str,
) -> int:
    for candidate in ranked_candidates(candidates, ranking_query, limit=limit):
        key = candidate_identity_key(candidate)
        try:
            text = loader(candidate.identity, include_metadata=False)
        except MolegApiError as exc:
            state.source_notes.append(f"{source_label} skipped: {exc}")
            append_eager_detail_failure_gap(
                exc,
                state.gaps,
                candidate=candidate,
                recommended_interface=recommended_interface,
                source_label=source_label,
            )
            continue
        text_length = len(text.text)
        if eager_text_used + text_length > eager_text_budget:
            state.source_notes.append(f"{source_label} skipped: text budget exceeded")
            continue
        eager_text_used += text_length
        loaded.append(text)
        state.loaded_detail_keys.add(key)
    return eager_text_used


def append_bundle_authority_gaps(
    state: BundleState,
    reference_date: str | None,
) -> None:
    append_authority_article_mismatch_gaps(
        target_article_refs_from_loaded_articles(state.authority_target_articles),
        interpretations=state.loaded_interpretations,
        cases=state.loaded_cases,
        constitutional_decisions=state.loaded_constitutional_decisions,
        gaps=state.gaps,
    )
    append_authority_temporal_mismatch_gaps(
        state.authority_target_articles,
        interpretations=state.loaded_interpretations,
        cases=state.loaded_cases,
        constitutional_decisions=state.loaded_constitutional_decisions,
        gaps=state.gaps,
        deferred=state.deferred,
        reference_date=reference_date,
    )


__all__ = [name for name in globals() if not name.startswith("__")]
