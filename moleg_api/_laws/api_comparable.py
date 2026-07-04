from __future__ import annotations

from .support import *

class ComparableMechanismsMixin:
    def find_comparable_mechanisms(
        self,
        concept: str,
        *,
        display: int = 5,
    ) -> list[LawIdentity]:
        """Find source-backed law candidates with similar legal mechanisms.

        Use when: the skill is doing legislative design or comparative 제도
        planning for a concept such as 과징금, 인허가, authorization, or 신고제.
        Returns: bounded `LawIdentity` candidates with source endpoints and
        article anchors preserved in `raw_keys` for later selective loading.
        Raises: `NoResultError` for blank concepts or when no comparable source
        candidates are found; source/parse errors may also propagate.
        Related: use `expand_legal_query` for broader search planning and
        `get_law`/`get_article` before citing or concluding mechanisms match.
        """
        concept = concept.strip()
        if not concept:
            raise NoResultError("concept is required for comparable mechanism discovery")

        source_failures: list[ContextGap] = []
        first_failure: MolegApiError | None = None

        def remember_failure(exc: MolegApiError) -> None:
            nonlocal first_failure
            if first_failure is None:
                first_failure = exc

        try:
            ai_search_payload = self.source.search(
                "aiSearch",
                {"query": concept, "display": display, "search": 0},
            )
            ai_search_rows = unwrap_target_rows(ai_search_payload, "aiSearch")
        except MolegApiError as exc:
            remember_failure(exc)
            append_source_failure_gap(
                exc,
                source_failures,
                query=concept,
                recommended_interface="find_comparable_mechanisms",
                source_label="Comparable-mechanism AI search",
            )
            ai_search_rows = []

        try:
            ai_related_payload = self.source.search(
                "aiRltLs",
                {"query": concept, "search": 0},
            )
            ai_related_rows = unwrap_target_rows(ai_related_payload, "aiRltLs")
        except MolegApiError as exc:
            remember_failure(exc)
            append_source_failure_gap(
                exc,
                source_failures,
                query=concept,
                recommended_interface="find_comparable_mechanisms",
                source_label="Comparable-mechanism related-law search",
            )
            ai_related_rows = []

        try:
            term_article_payload = self.source.service("lstrmRltJo", {"query": concept})
            term_article_rows = unwrap_target_rows(term_article_payload, "lstrmRltJo")
        except MolegApiError as exc:
            remember_failure(exc)
            append_source_failure_gap(
                exc,
                source_failures,
                query=concept,
                recommended_interface="find_comparable_mechanisms",
                source_label="Comparable-mechanism term-article lookup",
            )
            term_article_rows = []

        candidates = comparable_mechanism_identities(
            concept,
            [
                *laws_from_rows(ai_search_rows, source_target="aiSearch"),
                *laws_from_rows(ai_related_rows, source_target="aiRltLs"),
                *laws_from_rows(term_article_rows, source_target="lstrmRltJo"),
            ],
            display=display,
            source_failures=source_failures,
        )
        if not candidates:
            if first_failure is not None:
                raise first_failure
            raise NoResultError(f"No comparable mechanisms found for concept: {concept}")
        return candidates

    def _search_rows(
        self,
        target: str,
        params: dict[str, Any],
        raw: dict[str, Any],
        empty_sources: list[str],
        *,
        source_failures: list[ContextGap] | None = None,
        source_label: str | None = None,
    ) -> list[dict[str, Any]]:
        try:
            payload = self.source.search(target, params)
        except MolegApiError as exc:
            if source_failures is not None:
                append_source_failure_gap(
                    exc,
                    source_failures,
                    query=string_value(params.get("query")),
                    recommended_interface="expand_legal_query",
                    source_label=source_label or f"Query-expansion {target} search",
                )
            return []
        raw[target] = payload
        rows = unwrap_target_rows(payload, target)
        if not rows:
            empty_sources.append(target)
        return rows

__all__ = [name for name in globals() if not name.startswith("__")]
