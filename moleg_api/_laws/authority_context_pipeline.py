from __future__ import annotations

from .support import *


@dataclass
class AuthorityContextState:
    source_notes: list[str]
    gaps: list[ContextGap]
    deferred: list[DeferredLookup]
    target_articles: list[ArticleText]
    loaded_article_rows: list[ArticleText]
    interpretation_candidates: list[InterpretationHit]
    case_candidates: list[JudicialDecisionHit]
    constitutional_candidates: list[JudicialDecisionHit]
    loaded_interpretations: list[InterpretationText]
    loaded_cases: list[JudicialDecisionText]
    loaded_constitutional_decisions: list[JudicialDecisionText]
    loaded_detail_keys: set[tuple[str | None, str]]


def new_authority_context_state() -> AuthorityContextState:
    return AuthorityContextState(
        source_notes=["AuthorityContext is scoped source context for Claude inspection, not a legal conclusion."],
        gaps=[],
        deferred=[],
        target_articles=[],
        loaded_article_rows=[],
        interpretation_candidates=[],
        case_candidates=[],
        constitutional_candidates=[],
        loaded_interpretations=[],
        loaded_cases=[],
        loaded_constitutional_decisions=[],
        loaded_detail_keys=set(),
    )


def load_authority_target_articles(
    api: Any,
    identity: LawIdentity,
    requested_articles: list[str | int],
    reference_date: str | None,
    state: AuthorityContextState,
) -> None:
    for article in requested_articles:
        try:
            article_context = api.load_article_context(
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
                state.gaps,
                state.deferred,
                as_of=reference_date,
            )
            continue
        state.loaded_article_rows.extend(article_context.loaded_articles)
        state.gaps.extend(article_context.gaps)
        state.deferred.extend(article_context.deferred)
        state.source_notes.extend(article_context.source_notes)
        if article_context.current_article is not None:
            state.target_articles.append(article_context.current_article)


def search_authority_candidates(
    api: Any,
    search_queries: list[str],
    limits: dict[str, int],
    state: AuthorityContextState,
) -> None:
    state.interpretation_candidates = dedupe_candidates(
        [
            candidate
            for candidate_query in search_queries
            for candidate in safe_list(
                lambda candidate_query=candidate_query: api.search_interpretations(
                    candidate_query,
                    display=limits["interpretations"],
                ),
                state.source_notes,
                "Authority interpretation search",
                gaps=state.gaps,
                deferred=state.deferred,
                query=candidate_query,
                recommended_interface="search_interpretations",
                source_type="interpretation",
            )
        ]
    )
    state.case_candidates = dedupe_candidates(
        [
            candidate
            for candidate_query in search_queries
            for candidate in safe_list(
                lambda candidate_query=candidate_query: api.search_cases(
                    candidate_query,
                    display=limits["cases"],
                ),
                state.source_notes,
                "Authority case search",
                gaps=state.gaps,
                deferred=state.deferred,
                query=candidate_query,
                recommended_interface="search_cases",
                source_type="case",
            )
        ]
    )
    state.constitutional_candidates = dedupe_candidates(
        [
            candidate
            for candidate_query in search_queries
            for candidate in safe_list(
                lambda candidate_query=candidate_query: api.search_constitutional_decisions(
                    candidate_query,
                    display=limits["constitutional_decisions"],
                ),
                state.source_notes,
                "Authority Constitutional Court search",
                gaps=state.gaps,
                deferred=state.deferred,
                query=candidate_query,
                recommended_interface="search_constitutional_decisions",
                source_type="constitutional",
            )
        ]
    )


__all__ = [name for name in globals() if not name.startswith("__")]
