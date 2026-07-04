from __future__ import annotations

from .delegated_criteria_details import (
    finalize_delegated_criteria_bundle,
    load_delegated_criteria_details,
)
from .delegated_criteria_pipeline import (
    new_delegated_criteria_state,
    refresh_delegated_criteria_candidates,
)
from .support import *


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
        state = new_delegated_criteria_state(bundle)
        refresh_delegated_criteria_candidates(
            self,
            bundle,
            explicit_query,
            explicit_queries,
            candidate_limits,
            state,
        )

        if any(item.kind == "statute_identity" for item in bundle.ambiguities):
            limits = {key: 0 for key in limits}
            state.source_notes.append(
                "Delegated-criteria detail loading skipped until statute identity ambiguity is resolved."
            )

        load_delegated_criteria_details(self, ranking_query, limits, as_of, state)
        return finalize_delegated_criteria_bundle(bundle, explicit_query, state)


__all__ = [name for name in globals() if not name.startswith("__")]
