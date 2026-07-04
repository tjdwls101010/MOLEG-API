from __future__ import annotations

from .bundle_state import BundleState
from .support import *


def load_bundle_primary_context(
    api: Any,
    primary_identity: LawIdentity | None,
    request: BundleRequest,
    search_query: str | None,
    limits: dict[str, int],
    state: BundleState,
) -> LawIdentity | None:
    if primary_identity is None:
        return None

    current_identity = primary_identity
    if request.articles:
        current_identity = load_bundle_primary_articles(
            api,
            current_identity,
            request,
            search_query,
            limits,
            state,
        )
    else:
        current_identity = load_bundle_primary_law(api, current_identity, request, search_query, state)

    load_bundle_primary_delegations(api, current_identity, limits, state)
    append_promulgated_bill_followups(current_identity, request, state)
    return current_identity


def load_bundle_primary_articles(
    api: Any,
    identity: LawIdentity,
    request: BundleRequest,
    search_query: str | None,
    limits: dict[str, int],
    state: BundleState,
) -> LawIdentity:
    current_identity = identity
    for article in request.articles[: limits["articles"]]:
        try:
            article_context = api.load_article_context(
                current_identity,
                article,
                as_of=request.as_of,
                basis="effective",
            )
            state.loaded_articles.extend(article_context.loaded_articles)
            state.gaps.extend(article_context.gaps)
            state.deferred.extend(article_context.deferred)
            state.source_notes.extend(article_context.source_notes)
            if article_context.current_article is not None:
                state.authority_target_articles.append(article_context.current_article)
            for article_text in article_context.loaded_articles:
                current_identity = prefer_versioned_law_identity(
                    current_identity,
                    article_text.identity,
                )
                append_not_effective_as_of_gap(
                    article_text.identity,
                    request.as_of,
                    state.gaps,
                    state.source_notes,
                    query=search_query or current_identity.name,
                )
        except MolegApiError as exc:
            state.source_notes.append(f"Article load skipped for {article}: {exc}")
            append_requested_article_load_gap(
                exc,
                current_identity,
                article,
                state.gaps,
                state.deferred,
                as_of=request.as_of,
            )
    return current_identity


def load_bundle_primary_law(
    api: Any,
    identity: LawIdentity,
    request: BundleRequest,
    search_query: str | None,
    state: BundleState,
) -> LawIdentity:
    try:
        law_text = api.get_law(identity, as_of=request.as_of)
        state.loaded_laws.append(law_text)
        loaded_identity = law_text.identity
        append_not_effective_as_of_gap(
            loaded_identity,
            request.as_of,
            state.gaps,
            state.source_notes,
            query=search_query or loaded_identity.name,
        )
        append_whole_law_article_status_gaps(
            law_text,
            state.gaps,
            state.deferred,
            state.source_notes,
            as_of=request.as_of,
            basis="effective",
        )
        return loaded_identity
    except MolegApiError as exc:
        state.source_notes.append(f"Primary law load skipped: {exc}")
        append_requested_law_load_gap(
            exc,
            identity,
            state.gaps,
            state.deferred,
            as_of=request.as_of,
        )
        return identity


def load_bundle_primary_delegations(
    api: Any,
    identity: LawIdentity,
    limits: dict[str, int],
    state: BundleState,
) -> None:
    if not law_identity_has_source_identifier(identity):
        return
    try:
        graph = api.find_delegated_rules(identity)
        state.loaded_delegations.append(limit_delegation_graph(graph, limits["delegations"]))
    except NoResultError:
        state.loaded_delegations.append(DelegationGraph(identity=identity, rules=[], raw={}))
        append_empty_delegation_lookup_gap(identity, state.gaps, state.deferred)
    except MolegApiError as exc:
        state.source_notes.append(f"Delegation lookup skipped: {exc}")
        append_delegation_lookup_failure_gap(exc, identity, state.gaps, state.deferred)


def append_promulgated_bill_followups(
    identity: LawIdentity,
    request: BundleRequest,
    state: BundleState,
) -> None:
    if request.mode != "promulgated_bill" or not law_identity_has_source_identifier(identity):
        return
    state.deferred.append(
        DeferredLookup(
            interface="trace_law_history",
            query=identity.name,
            reason="Trace amendment history once the relevant article or date range is known.",
            source_type="law_history",
            filters=law_identity_followup_filters(identity),
        )
    )
    state.deferred.append(
        DeferredLookup(
            interface="compare_law_versions",
            query=identity.name,
            reason="Compare before/after text when the bill's affected articles are identified.",
            source_type="law_diff",
            filters=law_identity_followup_filters(identity),
        )
    )


__all__ = [name for name in globals() if not name.startswith("__")]
