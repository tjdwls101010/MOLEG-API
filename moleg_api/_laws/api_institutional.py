from __future__ import annotations

from .institutional_candidates import append_institutional_deferred
from .institutional_pipeline import new_institutional_state, process_institutional_statute
from .support import *


class InstitutionalSystemMixin:
    def load_institutional_system(
        self,
        statute_identifiers: list[str | LawIdentity | LawHit],
        *,
        articles: list[str | int] | None = None,
        budget: BundleBudget = "standard",
        as_of: str | None = None,
    ) -> LegalContextBundle:
        """Load one explicit multi-statute institutional system.

        Use when: the skill has already selected the statute set for a 제도 and
        needs one staged source bundle across those statutes.
        Returns: `LegalContextBundle` with `request.mode="institutional_system"`,
        `request.statute_ids`, loaded law/article text, law structures,
        delegation graphs, candidates, deferred lookups, ambiguities, and gaps.
        Pass `as_of` when the statute set is being reviewed for current force
        on a specific reference date.
        Raises: `NoResultError` for an empty statute set and budget validation
        errors from the normal bundle limits; per-statute failures are recorded
        in the returned bundle instead of aborting the whole load.
        Related: use `search_laws` or `expand_legal_query` before this method
        when the statute set itself is uncertain.
        """
        if not statute_identifiers:
            raise NoResultError("statute_identifiers is required for institutional-system bundles")
        if articles is not None and not articles:
            raise NoResultError("articles must contain at least one article when provided")

        limits = bundle_limits(budget)
        reference_date = compact_date(as_of) if as_of else None
        request = BundleRequest(
            query=None,
            mode="institutional_system",
            budget=budget,
            articles=list(articles or []),
            statute_ids=[statute_identifier_label(identifier) for identifier in statute_identifiers],
            as_of=reference_date,
        )
        state = new_institutional_state()
        for statute_identifier in statute_identifiers:
            process_institutional_statute(
                self,
                statute_identifier,
                articles,
                limits,
                reference_date,
                state,
            )
        append_institutional_deferred(state)

        return LegalContextBundle(
            request=request,
            loaded=LoadedContext(
                laws=state.loaded_laws,
                articles=state.loaded_articles,
                delegations=state.loaded_delegations,
                law_structures=state.law_structures,
            ),
            candidates=CandidateContext(
                laws=dedupe_identities(state.law_candidates),
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


__all__ = [name for name in globals() if not name.startswith("__")]
