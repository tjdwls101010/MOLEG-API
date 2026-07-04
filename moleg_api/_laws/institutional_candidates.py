from __future__ import annotations

from .support import *


def discover_institutional_candidates(
    api: Any,
    identity: LawIdentity,
    limits: dict[str, int],
    source_notes: list[str],
    gaps: list[ContextGap],
    deferred: list[DeferredLookup],
) -> tuple[
    list[AdministrativeRuleHit],
    list[AnnexFormHit],
    list[InterpretationHit],
    list[JudicialDecisionHit],
    list[JudicialDecisionHit],
]:
    administrative_candidates = safe_list(
        lambda: api.search_administrative_rules(
            identity.name,
            display=limits["administrative_rules"],
        ),
        source_notes,
        f"Administrative-rule search for {identity.name}",
        gaps=gaps,
        deferred=deferred,
        query=identity.name,
        recommended_interface="search_administrative_rules",
        source_type="administrative_rule",
    )
    interpretation_candidates = safe_list(
        lambda: api.search_interpretations(
            identity.name,
            display=limits["interpretations"],
        ),
        source_notes,
        f"Interpretation search for {identity.name}",
        gaps=gaps,
        deferred=deferred,
        query=identity.name,
        recommended_interface="search_interpretations",
        source_type="interpretation",
    )
    case_candidates = safe_list(
        lambda: api.search_cases(
            identity.name,
            display=limits["cases"],
        ),
        source_notes,
        f"Case search for {identity.name}",
        gaps=gaps,
        deferred=deferred,
        query=identity.name,
        recommended_interface="search_cases",
        source_type="case",
    )
    constitutional_candidates = safe_list(
        lambda: api.search_constitutional_decisions(
            identity.name,
            display=limits["constitutional_decisions"],
        ),
        source_notes,
        f"Constitutional decision search for {identity.name}",
        gaps=gaps,
        deferred=deferred,
        query=identity.name,
        recommended_interface="search_constitutional_decisions",
        source_type="constitutional",
    )
    annex_candidates = discover_institutional_annex_candidates(
        api,
        identity,
        limits,
        source_notes,
        gaps,
        deferred,
    )
    return (
        administrative_candidates,
        annex_candidates,
        interpretation_candidates,
        case_candidates,
        constitutional_candidates,
    )


def discover_institutional_annex_candidates(
    api: Any,
    identity: LawIdentity,
    limits: dict[str, int],
    source_notes: list[str],
    gaps: list[ContextGap],
    deferred: list[DeferredLookup],
) -> list[AnnexFormHit]:
    annex_form_limit = limits["annex_forms"]
    law_annex_limit = (annex_form_limit + 1) // 2
    admin_annex_limit = max(1, annex_form_limit - law_annex_limit)
    return [
        *safe_list(
            lambda: api.search_annex_forms(
                identity.name,
                source="law",
                search_scope="source",
                display=law_annex_limit,
            ),
            source_notes,
            f"Law annex/form search for {identity.name}",
            gaps=gaps,
            deferred=deferred,
            query=identity.name,
            recommended_interface="search_annex_forms",
            source_type="annex_form",
            filters={"source": "law", "search_scope": "source"},
        ),
        *safe_list(
            lambda: api.search_annex_forms(
                identity.name,
                source="administrative_rule",
                search_scope="source",
                display=admin_annex_limit,
            ),
            source_notes,
            f"Administrative-rule annex/form search for {identity.name}",
            gaps=gaps,
            deferred=deferred,
            query=identity.name,
            recommended_interface="search_annex_forms",
            source_type="annex_form",
            filters={"source": "administrative_rule", "search_scope": "source"},
        ),
    ]


def append_institutional_deferred(
    state: Any,
) -> None:
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
    state.deferred.extend(deferred_from_candidates(state.interpretation_candidates, "get_interpretation", "interpretation"))
    state.deferred.extend(deferred_from_candidates(state.case_candidates, "get_case", "case"))
    state.deferred.extend(
        deferred_from_candidates(
            state.constitutional_candidates,
            "get_constitutional_decision",
            "constitutional",
        )
    )


__all__ = [name for name in globals() if not name.startswith("__")]
