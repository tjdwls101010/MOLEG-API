from __future__ import annotations

from .support import *


@dataclass
class DelegatedCriteriaState:
    source_notes: list[str]
    gaps: list[ContextGap]
    deferred: list[DeferredLookup]
    administrative_candidates: list[AdministrativeRuleHit]
    annex_form_candidates: list[AnnexFormHit]
    loaded_administrative_rules: list[AdministrativeRuleText]
    loaded_annex_forms: list[AnnexFormText]
    loaded_candidate_keys: set[tuple[str | None, str]]
    delegated_scope: Any


def new_delegated_criteria_state(bundle: LegalContextBundle) -> DelegatedCriteriaState:
    return DelegatedCriteriaState(
        source_notes=list(bundle.source_notes),
        gaps=list(bundle.gaps),
        deferred=[
            item
            for item in bundle.deferred
            if item.interface
            not in {
                "get_administrative_rule",
                "load_administrative_rule_context",
                "get_annex_form_body",
            }
        ],
        administrative_candidates=list(bundle.candidates.administrative_rules),
        annex_form_candidates=list(bundle.candidates.annex_forms),
        loaded_administrative_rules=[],
        loaded_annex_forms=[],
        loaded_candidate_keys=set(),
        delegated_scope=delegated_criteria_target_scope(bundle),
    )


def refresh_delegated_criteria_candidates(
    api: Any,
    bundle: LegalContextBundle,
    explicit_query: str | None,
    explicit_queries: list[str],
    candidate_limits: dict[str, int],
    state: DelegatedCriteriaState,
) -> None:
    delegated_rule_names = (
        delegated_subordinate_rule_names(bundle, state.delegated_scope)
        if not explicit_query
        else []
    )
    if delegated_rule_names:
        subordinate_annex_limit = candidate_limits["annex_forms"]
        delegated_annex_candidates = dedupe_candidates(
            [
                hit
                for rule_name in delegated_rule_names
                for hit in safe_list(
                    lambda rule_name=rule_name: api.search_annex_forms(
                        rule_name,
                        source="law",
                        search_scope="source",
                        annex_type="별표",
                        display=subordinate_annex_limit,
                    ),
                    state.source_notes,
                    f"Delegated-criteria subordinate-rule annex/form search for {rule_name}",
                    gaps=state.gaps,
                    deferred=state.deferred,
                    query=rule_name,
                    recommended_interface="search_annex_forms",
                    source_type="annex_form",
                    filters={"source": "law", "search_scope": "source", "annex_type": "별표"},
                )
            ]
        )
        state.annex_form_candidates = dedupe_candidates(
            [*delegated_annex_candidates, *state.annex_form_candidates]
        )[:subordinate_annex_limit]

    if not explicit_query:
        return

    query_administrative_candidates = dedupe_candidates(
        [
            candidate
            for candidate_query in explicit_queries
            for candidate in safe_list(
                lambda candidate_query=candidate_query: api.search_administrative_rules(
                    candidate_query,
                    display=candidate_limits["administrative_rules"],
                ),
                state.source_notes,
                "Delegated-criteria administrative-rule query search",
                gaps=state.gaps,
                deferred=state.deferred,
                query=candidate_query,
                recommended_interface="search_administrative_rules",
                source_type="administrative_rule",
            )
        ]
    )
    state.administrative_candidates = dedupe_candidates(
        [*query_administrative_candidates, *state.administrative_candidates]
    )[: candidate_limits["administrative_rules"]]

    annex_form_limit = candidate_limits["annex_forms"]
    law_annex_limit = (annex_form_limit + 1) // 2
    admin_annex_limit = max(1, annex_form_limit - law_annex_limit)
    query_law_annex_candidates = search_delegated_annex_candidates(
        api,
        explicit_queries,
        law_annex_limit,
        state,
        source="law",
        source_label="Delegated-criteria law annex/form query search",
    )
    query_admin_annex_candidates = search_delegated_annex_candidates(
        api,
        explicit_queries,
        admin_annex_limit,
        state,
        source="administrative_rule",
        source_label="Delegated-criteria administrative-rule annex/form query search",
    )
    state.annex_form_candidates = dedupe_candidates(
        [
            *query_law_annex_candidates,
            *query_admin_annex_candidates,
            *state.annex_form_candidates,
        ]
    )[:annex_form_limit]


def search_delegated_annex_candidates(
    api: Any,
    queries: list[str],
    display: int,
    state: DelegatedCriteriaState,
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
