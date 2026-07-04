from __future__ import annotations

from .foundation import *
from .config import *

def deferred_from_candidates(
    candidates: list[Any],
    interface: str,
    source_type: str,
) -> list[DeferredLookup]:
    deferred: list[DeferredLookup] = []
    for candidate in candidates:
        identity = getattr(candidate, "identity", None)
        title = getattr(identity, "title", None) or getattr(identity, "name", None)
        source_id = (
            getattr(identity, "interpretation_id", None)
            or getattr(identity, "decision_id", None)
            or getattr(identity, "serial_id", None)
            or getattr(identity, "law_id", None)
            or getattr(identity, "annex_id", None)
        )
        if not title and not source_id:
            continue
        lookup_source_type = source_type
        if isinstance(identity, AnnexFormIdentity):
            lookup_source_type = "annex_form"
        elif identity is not None:
            lookup_source_type = getattr(identity, "source_type", source_type)
        lookup_interface = interface
        if interface == "get_administrative_rule" and isinstance(identity, AdministrativeRuleIdentity):
            lookup_interface = "load_administrative_rule_context"
        deferred.append(
            DeferredLookup(
                interface=lookup_interface,
                query=str(title or source_id),
                reason="Load full text only if Claude needs this candidate after ranking the bundle.",
                source_type=lookup_source_type,
                filters=deferred_lookup_filters(identity, source_id),
            )
        )
    return deferred


def deferred_lookup_filters(identity: Any, source_id: Any) -> dict[str, Any]:
    filters: dict[str, Any] = {}
    if source_id:
        filters["id"] = str(source_id)
    if isinstance(identity, AnnexFormIdentity):
        if identity.annex_id:
            filters["annex_id"] = identity.annex_id
        filters["source"] = identity.source_type
        if identity.related_name:
            filters["related_name"] = identity.related_name
    elif isinstance(identity, InterpretationIdentity):
        filters["source"] = identity.source_type
        if identity.ministry:
            filters["ministry"] = identity.ministry
    elif isinstance(identity, JudicialDecisionIdentity):
        filters["source"] = identity.source_type
    elif isinstance(identity, AdministrativeRuleIdentity):
        if identity.rule_id:
            filters["rule_id"] = identity.rule_id
    return filters


def delegated_criteria_ranking_query(bundle: LegalContextBundle) -> str:
    parts: list[str] = []
    parts.extend(bundle.request.statute_ids)
    parts.extend(str(article) for article in bundle.request.articles)
    parts.extend(identity.name for identity in bundle.candidates.laws[:1])
    return " ".join(part for part in parts if part).strip()


def delegated_criteria_query_search_queries(bundle: LegalContextBundle, query: str) -> list[str]:
    identity = delegated_criteria_query_identity(bundle)
    if identity is None or not bundle.request.articles or not bundle.loaded.articles:
        return [query]
    return article_target_search_queries(
        identity,
        list(bundle.request.articles),
        bundle.loaded.articles,
        ranking_query=query,
    )


def delegated_criteria_query_identity(bundle: LegalContextBundle) -> LawIdentity | None:
    for article in bundle.loaded.articles:
        if article.identity.law_id or article.identity.mst or article.identity.name:
            return article.identity
    for law in bundle.loaded.laws:
        if law.identity.law_id or law.identity.mst or law.identity.name:
            return law.identity
    for graph in bundle.loaded.delegations:
        if graph.identity.law_id or graph.identity.mst or graph.identity.name:
            return graph.identity
    for identity in bundle.candidates.laws:
        if identity.law_id or identity.mst or identity.name:
            return identity
    return None


def ranked_candidates(candidates: list[Any], query: str | None, *, limit: int) -> list[Any]:
    if limit <= 0:
        return []
    terms = significant_query_terms(query)
    scored = [
        (candidate_rank_score(candidate, terms), index, candidate)
        for index, candidate in enumerate(candidates)
    ]
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [candidate for _, _, candidate in scored[:limit]]


def dedupe_candidates(candidates: list[Any]) -> list[Any]:
    seen: set[tuple[str | None, str]] = set()
    unique: list[Any] = []
    for candidate in candidates:
        key = candidate_identity_key(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def article_target_search_queries(
    identity: LawIdentity,
    requested_articles: list[str | int],
    target_articles: list[ArticleText],
    *,
    ranking_query: str | None,
) -> list[str]:
    requested_labels = [article_label_for_filter(item) for item in requested_articles]
    base_query = ranking_query or f"{identity.name} {' '.join(requested_labels)}"
    queries = [base_query.strip()]
    requested_set = set(requested_labels)

    for article in target_articles:
        if not article.article or article.article in requested_set:
            continue
        queries.append(
            article_target_destination_query(
                identity,
                article.article,
                ranking_query=ranking_query,
                requested_labels=requested_labels,
            )
        )

    deduped_queries: list[str] = []
    for query in queries:
        if query and query not in deduped_queries:
            deduped_queries.append(query)
    return deduped_queries


def article_target_destination_query(
    identity: LawIdentity,
    destination_article: str,
    *,
    ranking_query: str | None,
    requested_labels: list[str],
) -> str:
    if ranking_query:
        query = ranking_query
        replaced = False
        for requested_label in requested_labels:
            if requested_label and requested_label in query:
                query = query.replace(requested_label, destination_article)
                replaced = True
        if replaced or destination_article in query:
            return query.strip()
        return f"{query} {destination_article}".strip()
    return f"{identity.name} {destination_article}".strip()


def significant_query_terms(query: str | None) -> list[str]:
    text = str(query or "")
    return [term for term in text.split() if len(term) >= 2]


def candidate_rank_score(candidate: Any, terms: list[str]) -> int:
    identity = getattr(candidate, "identity", None)
    haystack = " ".join(
        str(value or "")
        for value in (
            getattr(identity, "title", None),
            getattr(identity, "name", None),
            getattr(identity, "case_number", None),
            getattr(identity, "source_type", None),
            getattr(identity, "ministry", None),
            getattr(identity, "source_law_name", None),
            getattr(identity, "source_article", None),
            getattr(identity, "related_name", None),
            getattr(identity, "annex_number", None),
        )
    )
    return sum(1 for term in terms if term in haystack)


def unloaded_candidates(candidates: list[Any], loaded_keys: set[tuple[str | None, str]]) -> list[Any]:
    return [candidate for candidate in candidates if candidate_identity_key(candidate) not in loaded_keys]


def candidate_identity_key(candidate: Any) -> tuple[str | None, str]:
    identity = getattr(candidate, "identity", None)
    source_target = getattr(identity, "source_target", None)
    source_id = (
        getattr(identity, "interpretation_id", None)
        or getattr(identity, "decision_id", None)
        or getattr(identity, "serial_id", None)
        or getattr(identity, "law_id", None)
        or getattr(identity, "annex_id", None)
        or getattr(identity, "title", None)
        or getattr(identity, "name", None)
    )
    return (source_target, str(source_id or ""))

from .validation import *
from .annex_tables import *
from .identity_params import *
from .admin_scope import *
from .temporal_gaps import *
from .delegated_scope import *
from .source_matching import *
from .article_gaps import *
from .history_identity import *
from .authority_sources import *
from .candidates import *
from .followup_searches import *
from .followup_hits import *
from .limits_intents import *
from .authority_article_gaps import *
from .authority_temporal_gaps import *
from .authority_temporal_filters import *
from .followup_basic import *
from .followup_identities import *
from .bridge import *
from .requested_load_gaps import *
from .context_load_gaps import *

__all__ = [name for name in globals() if not name.startswith("__")]
