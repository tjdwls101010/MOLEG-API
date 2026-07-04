from __future__ import annotations

from .support import *

SIZE_OK = "load_delegated_criteria is preserved as one method to avoid changing staged bundle semantics"
class DelegatedCriteriaMixin:
    def load_delegated_criteria(
        self,
        law_identifier: str | LawIdentity | LawHit,
        *,
        articles: list[str | int] | None = None,
        query: str | None = None,
        budget: BundleBudget = "standard",
        as_of: str | None = None,
    ) -> LegalContextBundle:
        """Load delegated operational criteria from a known statute anchor.

        Use when: the skill has a statute or article and needs subordinate
        administrative-rule and annex/form bodies before discussing concrete
        operational criteria.
        Returns: a `LegalContextBundle` with the same staged context as
        `load_institutional_system`, plus bounded loaded administrative-rule
        and annex/form bodies in `loaded`.
        Raises: the same validation errors as `load_institutional_system`; a
        blank `query` is rejected when supplied, while per-candidate detail-load
        failures become gaps and deferred lookups.
        Related: use `load_institutional_system` when candidate discovery is
        enough and detail bodies should remain deferred.
        """
        if articles is not None and not articles:
            raise NoResultError("articles must contain at least one article when provided")
        explicit_query = require_query(query) if query is not None else None

        bundle = self.load_institutional_system(
            [law_identifier],
            articles=articles,
            budget=budget,
            as_of=as_of,
        )
        limits = dict(delegated_criteria_load_limits(budget))
        candidate_limits = bundle_limits(budget)
        explicit_queries = (
            delegated_criteria_query_search_queries(bundle, explicit_query)
            if explicit_query
            else []
        )
        ranking_query = " ".join(explicit_queries) if explicit_queries else delegated_criteria_ranking_query(bundle)

        source_notes = list(bundle.source_notes)
        gaps = list(bundle.gaps)
        deferred = [
            item
            for item in bundle.deferred
            if item.interface
            not in {
                "get_administrative_rule",
                "load_administrative_rule_context",
                "get_annex_form_body",
            }
        ]
        loaded_administrative_rules: list[AdministrativeRuleText] = []
        loaded_annex_forms: list[AnnexFormText] = []
        loaded_candidate_keys: set[tuple[str | None, str]] = set()
        administrative_candidates = list(bundle.candidates.administrative_rules)
        annex_form_candidates = list(bundle.candidates.annex_forms)
        delegated_scope = delegated_criteria_target_scope(bundle)

        # Criteria/amount 별표 live inside the delegated 시행령·시행규칙, not the
        # parent Act, and law.go.kr's lsDelegated never surfaces 별표 pointers. On
        # the bare-anchor path (no --query) the inherited discovery searches only
        # the parent law's own name and finds nothing, so reach the subordinate
        # legislation's annexes directly by their resolved names. With an explicit
        # query the block below already drives annex discovery by that query.
        delegated_rule_names = (
            delegated_subordinate_rule_names(bundle, delegated_scope)
            if not explicit_query
            else []
        )
        if delegated_rule_names:
            subordinate_annex_limit = candidate_limits["annex_forms"]
            # Restrict to 별표 (criteria/amount tables); 서식·별지 forms are not
            # operational criteria and would otherwise crowd out the penalty/fine
            # tables the anchor articles delegate.
            delegated_annex_candidates = dedupe_candidates(
                [
                    hit
                    for rule_name in delegated_rule_names
                    for hit in safe_list(
                        lambda rule_name=rule_name: self.search_annex_forms(
                            rule_name,
                            source="law",
                            search_scope="source",
                            annex_type="별표",
                            display=subordinate_annex_limit,
                        ),
                        source_notes,
                        f"Delegated-criteria subordinate-rule annex/form search for {rule_name}",
                        gaps=gaps,
                        deferred=deferred,
                        query=rule_name,
                        recommended_interface="search_annex_forms",
                        source_type="annex_form",
                        filters={"source": "law", "search_scope": "source", "annex_type": "별표"},
                    )
                ]
            )
            annex_form_candidates = dedupe_candidates(
                [*delegated_annex_candidates, *annex_form_candidates]
            )[:subordinate_annex_limit]

        if explicit_query:
            query_administrative_candidates = dedupe_candidates(
                [
                    candidate
                    for candidate_query in explicit_queries
                    for candidate in safe_list(
                        lambda candidate_query=candidate_query: self.search_administrative_rules(
                            candidate_query,
                            display=candidate_limits["administrative_rules"],
                        ),
                        source_notes,
                        "Delegated-criteria administrative-rule query search",
                        gaps=gaps,
                        deferred=deferred,
                        query=candidate_query,
                        recommended_interface="search_administrative_rules",
                        source_type="administrative_rule",
                    )
                ]
            )
            administrative_candidates = dedupe_candidates(
                [
                    *query_administrative_candidates,
                    *administrative_candidates,
                ]
            )[: candidate_limits["administrative_rules"]]
            annex_form_limit = candidate_limits["annex_forms"]
            law_annex_limit = (annex_form_limit + 1) // 2
            admin_annex_limit = max(1, annex_form_limit - law_annex_limit)
            query_law_annex_candidates = dedupe_candidates(
                [
                    candidate
                    for candidate_query in explicit_queries
                    for candidate in safe_list(
                        lambda candidate_query=candidate_query: self.search_annex_forms(
                            candidate_query,
                            source="law",
                            search_scope="source",
                            display=law_annex_limit,
                        ),
                        source_notes,
                        "Delegated-criteria law annex/form query search",
                        gaps=gaps,
                        deferred=deferred,
                        query=candidate_query,
                        recommended_interface="search_annex_forms",
                        source_type="annex_form",
                        filters={"source": "law", "search_scope": "source"},
                    )
                ]
            )
            query_admin_annex_candidates = dedupe_candidates(
                [
                    candidate
                    for candidate_query in explicit_queries
                    for candidate in safe_list(
                        lambda candidate_query=candidate_query: self.search_annex_forms(
                            candidate_query,
                            source="administrative_rule",
                            search_scope="source",
                            display=admin_annex_limit,
                        ),
                        source_notes,
                        "Delegated-criteria administrative-rule annex/form query search",
                        gaps=gaps,
                        deferred=deferred,
                        query=candidate_query,
                        recommended_interface="search_annex_forms",
                        source_type="annex_form",
                        filters={"source": "administrative_rule", "search_scope": "source"},
                    )
                ]
            )
            annex_form_candidates = dedupe_candidates(
                [
                    *query_law_annex_candidates,
                    *query_admin_annex_candidates,
                    *annex_form_candidates,
                ]
            )[:annex_form_limit]

        if any(item.kind == "statute_identity" for item in bundle.ambiguities):
            limits = {key: 0 for key in limits}
            source_notes.append(
                "Delegated-criteria detail loading skipped until statute identity ambiguity is resolved."
            )

        for candidate in ranked_candidates(
            administrative_candidates,
            ranking_query,
            limit=limits["administrative_rules"],
        ):
            try:
                rule_context = self.load_administrative_rule_context(candidate.identity)
                gaps.extend(rule_context.gaps)
                deferred.extend(rule_context.deferred)
                source_notes.extend(rule_context.source_notes)
                rule_text = administrative_rule_text_from_current_articles(rule_context)
                rule_text = filter_administrative_rule_text_to_delegated_scope(
                    rule_text,
                    delegated_scope,
                    gaps,
                    source_notes,
                )
                if rule_text.articles:
                    loaded_administrative_rules.append(rule_text)
                loaded_candidate_keys.add(candidate_identity_key(candidate))
                append_administrative_rule_not_effective_as_of_gap(
                    rule_context.rule.identity,
                    as_of,
                    gaps,
                    source_notes,
                    query=ranking_query,
                )
            except MolegApiError as exc:
                source_notes.append(f"Administrative-rule detail load skipped: {exc}")
                append_eager_detail_failure_gap(
                    exc,
                    gaps,
                    candidate=candidate,
                    recommended_interface="load_administrative_rule_context",
                    source_label="Delegated-criteria administrative-rule detail",
                )

        for candidate in ranked_candidates(
            annex_form_candidates,
            ranking_query,
            limit=limits["annex_forms"],
        ):
            try:
                annex_text = self.get_annex_form_body(candidate.identity)
                loaded_annex_forms.append(annex_text)
                loaded_candidate_keys.add(candidate_identity_key(candidate))
            except MolegApiError as exc:
                source_notes.append(f"Annex/form body load skipped: {exc}")
                append_eager_detail_failure_gap(
                    exc,
                    gaps,
                    candidate=candidate,
                    recommended_interface="get_annex_form_body",
                    source_label="Delegated-criteria annex/form body",
                )

        append_delegated_criteria_source_gaps(
            bundle,
            loaded_administrative_rules,
            gaps,
            source_notes,
        )
        append_delegated_criteria_annex_source_gaps(
            bundle,
            loaded_administrative_rules,
            loaded_annex_forms,
            gaps,
            source_notes,
        )

        deferred.extend(
            deferred_from_candidates(
                unloaded_candidates(administrative_candidates, loaded_candidate_keys),
                "get_administrative_rule",
                "administrative_rule",
            )
        )
        deferred.extend(
            deferred_from_candidates(
                unloaded_candidates(annex_form_candidates, loaded_candidate_keys),
                "get_annex_form_body",
                "annex_form",
            )
        )

        # websearch_required is a generic "no first-party path succeeded" prompt
        # inherited from load_institutional_system. When the delegated annex
        # search did surface first-party 별표, that prompt is misleading — drop it.
        if loaded_annex_forms or annex_form_candidates:
            gaps = [gap for gap in gaps if getattr(gap, "kind", None) != "websearch_required"]

        return replace(
            bundle,
            request=replace(bundle.request, query=explicit_query, mode="delegated_criteria"),
            loaded=replace(
                bundle.loaded,
                administrative_rules=loaded_administrative_rules,
                annex_forms=loaded_annex_forms,
            ),
            candidates=replace(
                bundle.candidates,
                administrative_rules=administrative_candidates,
                annex_forms=annex_form_candidates,
            ),
            deferred=deferred,
            gaps=gaps,
            source_notes=source_notes,
        )

__all__ = [name for name in globals() if not name.startswith("__")]
