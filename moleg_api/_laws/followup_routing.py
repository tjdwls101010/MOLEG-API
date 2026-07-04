from __future__ import annotations

from .support import *

NO_FOLLOWUP_RESULT = object()


def route_planning_followup(api: Any, interface: str, filters: dict[str, Any], query: str) -> Any:
    if interface == "expand_legal_query":
        return api.expand_legal_query(
            query,
            display=followup_int(filters, "display", 5),
            include_websearch_hint=followup_bool(filters, "include_websearch_hint", True),
        )
    if interface == "find_comparable_mechanisms":
        return api.find_comparable_mechanisms(query, display=followup_int(filters, "display", 5))
    if interface == "resolve_promulgated_law":
        return api.resolve_promulgated_law(
            prom_law_nm=followup_str(filters, "prom_law_nm", "law_name") or query,
            prom_no=followup_str(filters, "prom_no", "promulgation_number"),
            promulgation_dt=followup_str(filters, "promulgation_dt", "promulgation_date"),
        )
    return NO_FOLLOWUP_RESULT


def route_law_followup(
    api: Any,
    lookup: DeferredLookup | FollowUpSearch,
    interface: str,
    filters: dict[str, Any],
    query: str,
) -> Any:
    if interface == "search_laws":
        return api.search_laws(
            query,
            as_of=followup_str(filters, "as_of"),
            basis=followup_basis(filters),
            law_type=followup_str(filters, "law_type"),
            ministry=followup_str(filters, "ministry"),
            display=followup_int(filters, "display", 20),
        )
    if interface == "get_law":
        basis = followup_basis(filters)
        return api.get_law(
            followup_law_identity(lookup, filters, basis=basis),
            as_of=followup_str(filters, "as_of"),
            basis=basis,
            articles=followup_articles(filters),
            include_metadata=followup_bool(filters, "include_metadata", True),
        )
    if interface == "get_article":
        basis = followup_basis(filters)
        return api.get_article(
            followup_law_identity(lookup, filters, basis=basis),
            followup_article(filters, query),
            as_of=followup_str(filters, "as_of"),
            basis=basis,
        )
    if interface == "load_article_context":
        return load_followup_article_context(api, lookup, filters, query)
    if interface == "trace_law_history":
        return api.trace_law_history(
            followup_law_identity(lookup, filters, basis="effective"),
            date_range=followup_date_range(filters),
            article=followup_optional_article(filters, query),
            promulgation_bridge=followup_promulgation_bridge(filters),
        )
    if interface == "compare_law_versions":
        return api.compare_law_versions(
            followup_law_identity(lookup, filters, basis="effective"),
            before=followup_str(filters, "before"),
            after=followup_str(filters, "after"),
            article=followup_optional_article(filters, query),
        )
    if interface == "find_delegated_rules":
        return api.find_delegated_rules(
            followup_law_identity(lookup, filters, basis="effective"),
            article=followup_optional_article(filters, query),
        )
    if interface == "get_law_structure":
        return api.get_law_structure(
            followup_law_identity(lookup, filters, basis="effective"),
            depth=followup_int(filters, "depth", 0),
        )
    return NO_FOLLOWUP_RESULT


def load_followup_article_context(
    api: Any,
    lookup: DeferredLookup | FollowUpSearch,
    filters: dict[str, Any],
    query: str,
) -> ArticleContext:
    basis = followup_basis(filters)
    as_of = followup_str(filters, "as_of")
    article = followup_article(filters, query)
    follow_moved = followup_bool(filters, "follow_moved", True)
    context = api.load_article_context(
        followup_law_identity(lookup, filters, basis=basis),
        article,
        as_of=as_of,
        basis=basis,
        follow_moved=follow_moved,
    )
    moved_to = followup_str(filters, "moved_to")
    if not moved_to or not follow_moved or context.requested_article.moved_to or context.current_article is None:
        return context

    destination = article_label_for_filter(moved_to)
    requested = replace(context.requested_article, moved_to=destination)
    try:
        destination_article = api.get_article(
            requested.identity,
            destination,
            as_of=as_of,
            basis=basis,
        )
    except MolegApiError as exc:
        gaps = list(context.gaps)
        deferred = list(context.deferred)
        append_moved_destination_lookup_gap(
            exc,
            requested.identity,
            destination,
            gaps,
            deferred,
            as_of=as_of,
            basis=basis,
        )
        return replace(
            context,
            requested_article=requested,
            current_article=None,
            gaps=gaps,
            deferred=deferred,
        )
    return replace(
        context,
        requested_article=requested,
        current_article=destination_article,
        loaded_articles=[*context.loaded_articles, destination_article],
    )


def route_administrative_followup(
    api: Any,
    lookup: DeferredLookup | FollowUpSearch,
    interface: str,
    filters: dict[str, Any],
    query: str,
) -> Any:
    if interface == "search_administrative_rules":
        return api.search_administrative_rules(
            followup_query_with_article(query, filters),
            ministry=followup_str(filters, "ministry"),
            rule_type=followup_str(filters, "rule_type"),
            issued_on=followup_str(filters, "issued_on"),
            include_history=followup_bool(filters, "include_history", False),
            display=followup_int(filters, "display", 20),
        )
    if interface == "get_administrative_rule":
        return api.get_administrative_rule(
            followup_administrative_rule_identity(lookup, filters),
            articles=followup_articles(filters),
            include_metadata=followup_bool(filters, "include_metadata", True),
        )
    if interface == "load_administrative_rule_context":
        return api.load_administrative_rule_context(
            followup_administrative_rule_identity(lookup, filters),
            articles=followup_articles(filters),
            include_metadata=followup_bool(filters, "include_metadata", True),
            follow_moved=followup_bool(filters, "follow_moved", True),
        )
    return NO_FOLLOWUP_RESULT


def route_annex_followup(
    api: Any,
    lookup: DeferredLookup | FollowUpSearch,
    interface: str,
    filters: dict[str, Any],
    query: str,
) -> Any:
    if interface == "search_annex_forms":
        hits: list[AnnexFormHit] = []
        for source in followup_annex_sources(filters):
            hits.extend(
                api.search_annex_forms(
                    followup_query_with_article(query, filters),
                    source=source,
                    search_scope=followup_annex_search_scope(filters),
                    annex_type=followup_str(filters, "annex_type"),
                    ministry=followup_str(filters, "ministry"),
                    display=followup_int(filters, "display", 20),
                )
            )
        return hits
    if interface == "get_annex_form_body":
        source = followup_annex_source(filters)
        return api.get_annex_form_body(
            followup_annex_form_identity(lookup, filters, source=source),
            source=source,
            title=followup_str(filters, "title"),
            include_metadata=followup_bool(filters, "include_metadata", True),
            attempt_structuring=followup_bool(filters, "attempt_structuring", True),
        )
    return NO_FOLLOWUP_RESULT


__all__ = [name for name in globals() if not name.startswith("__")]
