from __future__ import annotations

from .delegated_criteria_pipeline import DelegatedCriteriaState
from .support import *


def load_delegated_criteria_details(
    api: Any,
    ranking_query: str,
    limits: dict[str, int],
    as_of: str | None,
    state: DelegatedCriteriaState,
) -> None:
    for candidate in ranked_candidates(
        state.administrative_candidates,
        ranking_query,
        limit=limits["administrative_rules"],
    ):
        try:
            rule_context = api.load_administrative_rule_context(candidate.identity)
            state.gaps.extend(rule_context.gaps)
            state.deferred.extend(rule_context.deferred)
            state.source_notes.extend(rule_context.source_notes)
            rule_text = administrative_rule_text_from_current_articles(rule_context)
            rule_text = filter_administrative_rule_text_to_delegated_scope(
                rule_text,
                state.delegated_scope,
                state.gaps,
                state.source_notes,
            )
            if rule_text.articles:
                state.loaded_administrative_rules.append(rule_text)
            state.loaded_candidate_keys.add(candidate_identity_key(candidate))
            append_administrative_rule_not_effective_as_of_gap(
                rule_context.rule.identity,
                as_of,
                state.gaps,
                state.source_notes,
                query=ranking_query,
            )
        except MolegApiError as exc:
            state.source_notes.append(f"Administrative-rule detail load skipped: {exc}")
            append_eager_detail_failure_gap(
                exc,
                state.gaps,
                candidate=candidate,
                recommended_interface="load_administrative_rule_context",
                source_label="Delegated-criteria administrative-rule detail",
            )

    for candidate in ranked_candidates(
        state.annex_form_candidates,
        ranking_query,
        limit=limits["annex_forms"],
    ):
        try:
            annex_text = api.get_annex_form_body(candidate.identity)
            state.loaded_annex_forms.append(annex_text)
            state.loaded_candidate_keys.add(candidate_identity_key(candidate))
        except MolegApiError as exc:
            state.source_notes.append(f"Annex/form body load skipped: {exc}")
            append_eager_detail_failure_gap(
                exc,
                state.gaps,
                candidate=candidate,
                recommended_interface="get_annex_form_body",
                source_label="Delegated-criteria annex/form body",
            )


def finalize_delegated_criteria_bundle(
    bundle: LegalContextBundle,
    explicit_query: str | None,
    state: DelegatedCriteriaState,
) -> LegalContextBundle:
    append_delegated_criteria_source_gaps(
        bundle,
        state.loaded_administrative_rules,
        state.gaps,
        state.source_notes,
    )
    append_delegated_criteria_annex_source_gaps(
        bundle,
        state.loaded_administrative_rules,
        state.loaded_annex_forms,
        state.gaps,
        state.source_notes,
    )
    state.deferred.extend(
        deferred_from_candidates(
            unloaded_candidates(state.administrative_candidates, state.loaded_candidate_keys),
            "get_administrative_rule",
            "administrative_rule",
        )
    )
    state.deferred.extend(
        deferred_from_candidates(
            unloaded_candidates(state.annex_form_candidates, state.loaded_candidate_keys),
            "get_annex_form_body",
            "annex_form",
        )
    )
    if state.loaded_annex_forms or state.annex_form_candidates:
        state.gaps = [gap for gap in state.gaps if getattr(gap, "kind", None) != "websearch_required"]

    return replace(
        bundle,
        request=replace(bundle.request, query=explicit_query, mode="delegated_criteria"),
        loaded=replace(
            bundle.loaded,
            administrative_rules=state.loaded_administrative_rules,
            annex_forms=state.loaded_annex_forms,
        ),
        candidates=replace(
            bundle.candidates,
            administrative_rules=state.administrative_candidates,
            annex_forms=state.annex_form_candidates,
        ),
        deferred=state.deferred,
        gaps=state.gaps,
        source_notes=state.source_notes,
    )


__all__ = [name for name in globals() if not name.startswith("__")]
