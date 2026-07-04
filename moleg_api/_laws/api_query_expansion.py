from __future__ import annotations

from .support import *

class QueryExpansionMixin:
    def expand_legal_query(
        self,
        query: str,
        *,
        display: int = 5,
        include_websearch_hint: bool = True,
    ) -> LegalQueryExpansion:
        """Build legal search-planning context for a broad query.

        Use when: the user's wording may need legal terms, everyday terms,
        related articles/laws, AI-search hints, or WebSearch handoff guidance
        before loading primary source text.
        Returns: `LegalQueryExpansion` with candidate laws, terms, related
        articles/laws, follow-up search recommendations, empty-source notes,
        and source-failure gaps when optional planning sources fail.
        Raises: `NoResultError` for blank queries.
        Related: this is not legal authority. Use returned follow-ups with
        `get_law`, `get_article`, interpretation, case, or annex loaders.
        """
        query = require_query(query)

        raw: dict[str, Any] = {}
        empty_sources: list[str] = []
        source_failures: list[ContextGap] = []

        try:
            law_payload = self.source.search("eflaw", {"query": query, "display": display})
            raw["eflaw"] = law_payload
            law_rows = unwrap_search_laws(law_payload)
            if not law_rows:
                empty_sources.append("eflaw")
        except MolegApiError as exc:
            append_source_failure_gap(
                exc,
                source_failures,
                query=query,
                recommended_interface="expand_legal_query",
                source_label="Query-expansion law candidate search",
            )
            law_rows = []
        law_candidates: list[LawIdentity] = []
        for row in law_rows:
            try:
                law_candidates.append(normalize_law_identity(row, basis="effective"))
            except ParseFailureError:
                continue

        legal_term_rows = self._search_rows(
            "lstrmAI",
            {"query": query, "display": display},
            raw,
            empty_sources,
            source_failures=source_failures,
            source_label="Query-expansion legal-term search",
        )
        everyday_term_rows = self._search_rows(
            "dlytrm",
            {"query": query, "display": display},
            raw,
            empty_sources,
            source_failures=source_failures,
            source_label="Query-expansion everyday-term search",
        )
        legal_to_everyday_rows = self._service_rows(
            "lstrmRlt",
            {"query": query},
            raw,
            empty_sources,
            source_failures=source_failures,
            source_label="Query-expansion legal-to-everyday term relation lookup",
        )
        everyday_to_legal_rows = self._service_rows(
            "dlytrmRlt",
            {"query": query},
            raw,
            empty_sources,
            source_failures=source_failures,
            source_label="Query-expansion everyday-to-legal term relation lookup",
        )
        term_article_rows = self._service_rows(
            "lstrmRltJo",
            {"query": query},
            raw,
            empty_sources,
            source_failures=source_failures,
            source_label="Query-expansion term-article relation lookup",
        )
        ai_search_rows = self._search_rows(
            "aiSearch",
            {"query": query, "display": display, "search": 0},
            raw,
            empty_sources,
            source_failures=source_failures,
            source_label="Query-expansion AI search",
        )
        ai_related_rows = self._search_rows(
            "aiRltLs",
            {"query": query, "search": 0},
            raw,
            empty_sources,
            source_failures=source_failures,
            source_label="Query-expansion AI related-law search",
        )

        term_candidates = compact_terms(
            [
                *terms_from_rows(legal_term_rows, source_type="legal_term", source_target="lstrmAI"),
                *terms_from_rows(everyday_term_rows, source_type="everyday_term", source_target="dlytrm"),
            ]
        )
        related_terms = compact_terms(
            [
                *terms_from_rows(legal_to_everyday_rows, source_type="everyday_term", source_target="lstrmRlt"),
                *terms_from_rows(everyday_to_legal_rows, source_type="legal_term", source_target="dlytrmRlt"),
            ]
        )
        related_articles = compact_articles(
            [
                *articles_from_rows(term_article_rows, source_target="lstrmRltJo"),
                *articles_from_rows(ai_search_rows, source_target="aiSearch"),
                *articles_from_rows(ai_related_rows, source_target="aiRltLs"),
            ]
        )
        related_laws = compact_laws(
            [
                *laws_from_rows(ai_search_rows, source_target="aiSearch"),
                *laws_from_rows(ai_related_rows, source_target="aiRltLs"),
            ]
        )

        follow_ups = build_follow_up_searches(
            query,
            law_candidates=law_candidates,
            term_candidates=[*term_candidates, *related_terms],
            related_laws=related_laws,
            include_websearch_hint=include_websearch_hint,
        )

        return LegalQueryExpansion(
            original_query=query,
            law_candidates=dedupe_identities(law_candidates),
            term_candidates=term_candidates,
            related_terms=related_terms,
            related_articles=related_articles,
            related_laws=related_laws,
            follow_up_searches=follow_ups,
            empty_sources=empty_sources,
            source_failures=source_failures,
            raw=raw,
        )

__all__ = [name for name in globals() if not name.startswith("__")]
