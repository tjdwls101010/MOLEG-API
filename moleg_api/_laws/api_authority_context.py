from __future__ import annotations

from .authority_context_details import (
    append_authority_context_followups,
    current_authorities_from_state,
    load_authority_details,
)
from .authority_context_pipeline import (
    load_authority_target_articles,
    new_authority_context_state,
    search_authority_candidates,
)
from .support import *


class AuthorityContextMixin:
    def load_authority_context(
        self,
        law_identifier: LawIdentity | LawHit | str,
        *,
        articles: list[str | int],
        query: str | None = None,
        budget: BundleBudget = "standard",
        as_of: str | None = None,
    ) -> AuthorityContext:
        """Load article-scoped interpretations, cases, and decisions.

        Use when: the skill needs authority context for specific statute
        articles and should not treat mismatched, undated, or pre-amendment
        authority as current target-article support.
        Returns: `AuthorityContext` with target articles, loaded authority
        details, `current_authorities` filtered to dated structured article matches,
        candidates, gaps, deferred lookups, and source notes.
        Raises: `NoResultError` for empty article lists or blank supplied
        queries; source failures from target article loading are preserved as
        gaps when possible.
        Related: use `search_interpretations`, `search_cases`, and
        `search_constitutional_decisions` for candidate discovery only, or
        `load_legal_context_bundle` for a broader first pass.
        """
        if not articles:
            raise NoResultError("articles must contain at least one article")

        limits = authority_load_limits(budget)
        reference_date = compact_date(as_of) if as_of else None
        ranking_query = require_query(query) if query is not None else None
        identity = identity_from_identifier(law_identifier, basis="effective")
        requested_articles = list(articles)
        search_query = ranking_query or f"{identity.name} {' '.join(article_label_for_filter(item) for item in articles)}"
        request = BundleRequest(
            query=search_query,
            mode="statute_review",
            budget=budget,
            articles=requested_articles,
            law_identifier=law_identifier,
            as_of=reference_date,
        )

        state = new_authority_context_state()
        load_authority_target_articles(self, identity, requested_articles, reference_date, state)
        search_queries = article_target_search_queries(
            identity,
            requested_articles,
            state.target_articles,
            ranking_query=ranking_query,
        )
        authority_ranking_query = " ".join(search_queries)
        search_authority_candidates(self, search_queries, limits, state)
        load_authority_details(self, authority_ranking_query, limits, state)
        append_authority_context_followups(state, reference_date)

        return AuthorityContext(
            request=request,
            target_articles=state.target_articles,
            loaded=LoadedContext(
                articles=state.loaded_article_rows,
                interpretations=state.loaded_interpretations,
                cases=state.loaded_cases,
                constitutional_decisions=state.loaded_constitutional_decisions,
            ),
            current_authorities=current_authorities_from_state(state, reference_date),
            candidates=CandidateContext(
                interpretations=state.interpretation_candidates,
                cases=state.case_candidates,
                constitutional_decisions=state.constitutional_candidates,
            ),
            deferred=state.deferred,
            gaps=state.gaps,
            source_notes=state.source_notes,
        )


__all__ = [name for name in globals() if not name.startswith("__")]
