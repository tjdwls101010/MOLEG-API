from __future__ import annotations

from .authority_context_pipeline import AuthorityContextState
from .support import *


def load_authority_details(
    api: Any,
    authority_ranking_query: str,
    limits: dict[str, int],
    state: AuthorityContextState,
) -> None:
    load_authority_detail_group(
        api.get_interpretation,
        state.interpretation_candidates,
        authority_ranking_query,
        limits["interpretations"],
        state.loaded_interpretations,
        state,
        recommended_interface="get_interpretation",
        source_label="Authority interpretation detail load",
    )
    load_authority_detail_group(
        api.get_case,
        state.case_candidates,
        authority_ranking_query,
        limits["cases"],
        state.loaded_cases,
        state,
        recommended_interface="get_case",
        source_label="Authority case detail load",
    )
    load_authority_detail_group(
        api.get_constitutional_decision,
        state.constitutional_candidates,
        authority_ranking_query,
        limits["constitutional_decisions"],
        state.loaded_constitutional_decisions,
        state,
        recommended_interface="get_constitutional_decision",
        source_label="Authority constitutional detail load",
    )


def load_authority_detail_group(
    loader: Any,
    candidates: list[Any],
    ranking_query: str,
    limit: int,
    loaded: list[Any],
    state: AuthorityContextState,
    *,
    recommended_interface: str,
    source_label: str,
) -> None:
    for candidate in ranked_candidates(candidates, ranking_query, limit=limit):
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
        loaded.append(text)
        state.loaded_detail_keys.add(candidate_identity_key(candidate))


def append_authority_context_followups(
    state: AuthorityContextState,
    reference_date: str | None,
) -> None:
    append_authority_article_mismatch_gaps(
        target_article_refs_from_loaded_articles(state.target_articles),
        interpretations=state.loaded_interpretations,
        cases=state.loaded_cases,
        constitutional_decisions=state.loaded_constitutional_decisions,
        gaps=state.gaps,
    )
    append_authority_temporal_mismatch_gaps(
        state.target_articles,
        interpretations=state.loaded_interpretations,
        cases=state.loaded_cases,
        constitutional_decisions=state.loaded_constitutional_decisions,
        gaps=state.gaps,
        deferred=state.deferred,
        reference_date=reference_date,
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


def current_authorities_from_state(
    state: AuthorityContextState,
    reference_date: str | None,
) -> LoadedContext:
    return LoadedContext(
        interpretations=[
            item
            for item in state.loaded_interpretations
            if authority_references_current_targets(
                item.referenced_articles,
                item.identity.interpretation_date,
                state.target_articles,
                reference_date=reference_date,
            )
        ],
        cases=[
            item
            for item in state.loaded_cases
            if authority_references_current_targets(
                item.referenced_articles,
                item.identity.decision_date,
                state.target_articles,
                reference_date=reference_date,
            )
        ],
        constitutional_decisions=[
            item
            for item in state.loaded_constitutional_decisions
            if authority_references_current_targets(
                item.reviewed_articles,
                item.identity.decision_date,
                state.target_articles,
                reference_date=reference_date,
            )
        ],
    )


__all__ = [name for name in globals() if not name.startswith("__")]
