from __future__ import annotations

from .support import *

SIZE_OK = "load_authority_context is preserved as one method until behavior-neutral extraction can split the staged authority pipeline"
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
        source_notes: list[str] = [
            "AuthorityContext is scoped source context for Claude inspection, not a legal conclusion."
        ]
        gaps: list[ContextGap] = []
        deferred: list[DeferredLookup] = []
        target_articles: list[ArticleText] = []
        loaded_article_rows: list[ArticleText] = []

        for article in requested_articles:
            try:
                article_context = self.load_article_context(
                    identity,
                    article,
                    as_of=reference_date,
                    basis="effective",
                )
            except MolegApiError as exc:
                append_requested_article_load_gap(
                    exc,
                    identity,
                    article,
                    gaps,
                    deferred,
                    as_of=reference_date,
                )
                continue
            loaded_article_rows.extend(article_context.loaded_articles)
            gaps.extend(article_context.gaps)
            deferred.extend(article_context.deferred)
            source_notes.extend(article_context.source_notes)
            if article_context.current_article is not None:
                target_articles.append(article_context.current_article)

        search_queries = article_target_search_queries(
            identity,
            requested_articles,
            target_articles,
            ranking_query=ranking_query,
        )
        authority_ranking_query = " ".join(search_queries)

        interpretation_candidates = dedupe_candidates(
            [
                candidate
                for candidate_query in search_queries
                for candidate in safe_list(
                    lambda candidate_query=candidate_query: self.search_interpretations(
                        candidate_query,
                        display=limits["interpretations"],
                    ),
                    source_notes,
                    "Authority interpretation search",
                    gaps=gaps,
                    deferred=deferred,
                    query=candidate_query,
                    recommended_interface="search_interpretations",
                    source_type="interpretation",
                )
            ]
        )
        case_candidates = dedupe_candidates(
            [
                candidate
                for candidate_query in search_queries
                for candidate in safe_list(
                    lambda candidate_query=candidate_query: self.search_cases(
                        candidate_query,
                        display=limits["cases"],
                    ),
                    source_notes,
                    "Authority case search",
                    gaps=gaps,
                    deferred=deferred,
                    query=candidate_query,
                    recommended_interface="search_cases",
                    source_type="case",
                )
            ]
        )
        constitutional_candidates = dedupe_candidates(
            [
                candidate
                for candidate_query in search_queries
                for candidate in safe_list(
                    lambda candidate_query=candidate_query: self.search_constitutional_decisions(
                        candidate_query,
                        display=limits["constitutional_decisions"],
                    ),
                    source_notes,
                    "Authority Constitutional Court search",
                    gaps=gaps,
                    deferred=deferred,
                    query=candidate_query,
                    recommended_interface="search_constitutional_decisions",
                    source_type="constitutional",
                )
            ]
        )

        loaded_interpretations: list[InterpretationText] = []
        loaded_cases: list[JudicialDecisionText] = []
        loaded_constitutional_decisions: list[JudicialDecisionText] = []
        loaded_detail_keys: set[tuple[str | None, str]] = set()

        for candidate in ranked_candidates(
            interpretation_candidates,
            authority_ranking_query,
            limit=limits["interpretations"],
        ):
            try:
                text = self.get_interpretation(candidate.identity, include_metadata=False)
            except MolegApiError as exc:
                source_notes.append(f"Authority interpretation detail load skipped: {exc}")
                append_eager_detail_failure_gap(
                    exc,
                    gaps,
                    candidate=candidate,
                    recommended_interface="get_interpretation",
                    source_label="Authority interpretation detail load",
                )
                continue
            loaded_interpretations.append(text)
            loaded_detail_keys.add(candidate_identity_key(candidate))

        for candidate in ranked_candidates(
            case_candidates,
            authority_ranking_query,
            limit=limits["cases"],
        ):
            try:
                text = self.get_case(candidate.identity, include_metadata=False)
            except MolegApiError as exc:
                source_notes.append(f"Authority case detail load skipped: {exc}")
                append_eager_detail_failure_gap(
                    exc,
                    gaps,
                    candidate=candidate,
                    recommended_interface="get_case",
                    source_label="Authority case detail load",
                )
                continue
            loaded_cases.append(text)
            loaded_detail_keys.add(candidate_identity_key(candidate))

        for candidate in ranked_candidates(
            constitutional_candidates,
            authority_ranking_query,
            limit=limits["constitutional_decisions"],
        ):
            try:
                text = self.get_constitutional_decision(candidate.identity, include_metadata=False)
            except MolegApiError as exc:
                source_notes.append(f"Authority constitutional detail load skipped: {exc}")
                append_eager_detail_failure_gap(
                    exc,
                    gaps,
                    candidate=candidate,
                    recommended_interface="get_constitutional_decision",
                    source_label="Authority constitutional detail load",
                )
                continue
            loaded_constitutional_decisions.append(text)
            loaded_detail_keys.add(candidate_identity_key(candidate))

        append_authority_article_mismatch_gaps(
            target_article_refs_from_loaded_articles(target_articles),
            interpretations=loaded_interpretations,
            cases=loaded_cases,
            constitutional_decisions=loaded_constitutional_decisions,
            gaps=gaps,
        )
        append_authority_temporal_mismatch_gaps(
            target_articles,
            interpretations=loaded_interpretations,
            cases=loaded_cases,
            constitutional_decisions=loaded_constitutional_decisions,
            gaps=gaps,
            deferred=deferred,
            reference_date=reference_date,
        )

        current_interpretations = [
            item
            for item in loaded_interpretations
            if authority_references_current_targets(
                item.referenced_articles,
                item.identity.interpretation_date,
                target_articles,
                reference_date=reference_date,
            )
        ]
        current_cases = [
            item
            for item in loaded_cases
            if authority_references_current_targets(
                item.referenced_articles,
                item.identity.decision_date,
                target_articles,
                reference_date=reference_date,
            )
        ]
        current_constitutional_decisions = [
            item
            for item in loaded_constitutional_decisions
            if authority_references_current_targets(
                item.reviewed_articles,
                item.identity.decision_date,
                target_articles,
                reference_date=reference_date,
            )
        ]

        deferred.extend(
            deferred_from_candidates(
                unloaded_candidates(interpretation_candidates, loaded_detail_keys),
                "get_interpretation",
                "interpretation",
            )
        )
        deferred.extend(
            deferred_from_candidates(
                unloaded_candidates(case_candidates, loaded_detail_keys),
                "get_case",
                "case",
            )
        )
        deferred.extend(
            deferred_from_candidates(
                unloaded_candidates(constitutional_candidates, loaded_detail_keys),
                "get_constitutional_decision",
                "constitutional",
            )
        )

        return AuthorityContext(
            request=request,
            target_articles=target_articles,
            loaded=LoadedContext(
                articles=loaded_article_rows,
                interpretations=loaded_interpretations,
                cases=loaded_cases,
                constitutional_decisions=loaded_constitutional_decisions,
            ),
            current_authorities=LoadedContext(
                interpretations=current_interpretations,
                cases=current_cases,
                constitutional_decisions=current_constitutional_decisions,
            ),
            candidates=CandidateContext(
                interpretations=interpretation_candidates,
                cases=case_candidates,
                constitutional_decisions=constitutional_candidates,
            ),
            deferred=deferred,
            gaps=gaps,
            source_notes=source_notes,
        )

__all__ = [name for name in globals() if not name.startswith("__")]
