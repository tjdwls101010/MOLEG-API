from __future__ import annotations

from .bundle_state import BundleState
from .support import *


def discover_bundle_candidates(
    api: Any,
    primary_identity: LawIdentity | None,
    request: BundleRequest,
    search_query: str | None,
    limits: dict[str, int],
    state: BundleState,
) -> list[str]:
    article_target_queries = [search_query] if search_query else []
    if not search_query:
        return article_target_queries

    if primary_identity is not None:
        article_target_queries = article_target_search_queries(
            primary_identity,
            list(request.articles),
            state.authority_target_articles,
            ranking_query=search_query,
        )

    state.administrative_candidates = search_bundle_administrative_candidates(
        api,
        article_target_queries,
        limits,
        state,
    )
    state.interpretation_candidates = search_bundle_authority_candidates(
        api.search_interpretations,
        article_target_queries,
        limits["interpretations"],
        state,
        source_label="Interpretation search",
        recommended_interface="search_interpretations",
        source_type="interpretation",
    )
    state.case_candidates = search_bundle_authority_candidates(
        api.search_cases,
        article_target_queries,
        limits["cases"],
        state,
        source_label="Case search",
        recommended_interface="search_cases",
        source_type="case",
    )
    state.constitutional_candidates = search_bundle_authority_candidates(
        api.search_constitutional_decisions,
        article_target_queries,
        limits["constitutional_decisions"],
        state,
        source_label="Constitutional decision search",
        recommended_interface="search_constitutional_decisions",
        source_type="constitutional",
    )
    state.annex_form_candidates = search_bundle_annex_candidates(
        api,
        article_target_queries,
        limits,
        state,
    )
    return article_target_queries


def search_bundle_administrative_candidates(
    api: Any,
    queries: list[str],
    limits: dict[str, int],
    state: BundleState,
) -> list[AdministrativeRuleHit]:
    return dedupe_candidates(
        [
            candidate
            for candidate_query in queries
            for candidate in safe_list(
                lambda candidate_query=candidate_query: api.search_administrative_rules(
                    candidate_query,
                    display=limits["administrative_rules"],
                ),
                state.source_notes,
                "Administrative-rule search",
                gaps=state.gaps,
                deferred=state.deferred,
                query=candidate_query,
                recommended_interface="search_administrative_rules",
                source_type="administrative_rule",
            )
        ]
    )[: limits["administrative_rules"]]


def search_bundle_authority_candidates(
    search: Any,
    queries: list[str],
    display: int,
    state: BundleState,
    *,
    source_label: str,
    recommended_interface: str,
    source_type: str,
) -> list[Any]:
    return dedupe_candidates(
        [
            candidate
            for candidate_query in queries
            for candidate in safe_list(
                lambda candidate_query=candidate_query: search(
                    candidate_query,
                    display=display,
                ),
                state.source_notes,
                source_label,
                gaps=state.gaps,
                deferred=state.deferred,
                query=candidate_query,
                recommended_interface=recommended_interface,
                source_type=source_type,
            )
        ]
    )


def search_bundle_annex_candidates(
    api: Any,
    queries: list[str],
    limits: dict[str, int],
    state: BundleState,
) -> list[AnnexFormHit]:
    annex_form_limit = limits["annex_forms"]
    law_annex_limit = (annex_form_limit + 1) // 2
    admin_annex_limit = max(1, annex_form_limit - law_annex_limit)
    return [
        *search_bundle_annex_source_candidates(
            api,
            queries,
            law_annex_limit,
            state,
            source="law",
            source_label="Law annex/form search",
        )[:law_annex_limit],
        *search_bundle_annex_source_candidates(
            api,
            queries,
            admin_annex_limit,
            state,
            source="administrative_rule",
            source_label="Administrative-rule annex/form search",
        )[:admin_annex_limit],
    ][:annex_form_limit]


def search_bundle_annex_source_candidates(
    api: Any,
    queries: list[str],
    display: int,
    state: BundleState,
    *,
    source: AnnexFormSource,
    source_label: str,
) -> list[AnnexFormHit]:
    return dedupe_candidates(
        [
            candidate
            for candidate_query in queries
            for candidate in safe_list(
                lambda candidate_query=candidate_query: api.search_annex_forms(
                    candidate_query,
                    source=source,
                    search_scope="source",
                    display=display,
                ),
                state.source_notes,
                source_label,
                gaps=state.gaps,
                deferred=state.deferred,
                query=candidate_query,
                recommended_interface="search_annex_forms",
                source_type="annex_form",
                filters={"source": source, "search_scope": "source"},
            )
        ]
    )


__all__ = [name for name in globals() if not name.startswith("__")]
