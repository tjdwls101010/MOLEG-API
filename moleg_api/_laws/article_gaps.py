from __future__ import annotations

from .foundation import *
from .config import *

def append_deleted_article_gap(
    article: ArticleText,
    gaps: list[ContextGap],
    source_notes: list[str],
) -> None:
    gaps.append(
        ContextGap(
            kind="deleted_article",
            reason=(
                f"{article.identity.name} {article.article} is marked deleted; "
                "do not treat the deletion marker as current article substance."
            ),
            query=f"{article.identity.name} {article.article}",
            recommended_interface="trace_law_history",
        )
    )
    source_notes.append(
        f"{article.identity.name} {article.article} is a deleted article source state, not operative text."
    )


def append_moved_destination_lookup_gap(
    exc: MolegApiError,
    identity: LawIdentity,
    article: str,
    gaps: list[ContextGap],
    deferred: list[DeferredLookup],
    *,
    as_of: str | None,
    basis: Basis,
) -> None:
    query = f"{identity.name} {article}"
    append_source_failure_gap(
        exc,
        gaps,
        query=query,
        recommended_interface="get_article",
        source_label=f"Moved-article destination lookup for {query}",
    )
    append_moved_destination_deferred(
        identity,
        article,
        deferred,
        as_of=as_of,
        basis=basis,
    )


def append_moved_destination_deferred(
    identity: LawIdentity,
    article: str,
    deferred: list[DeferredLookup],
    *,
    as_of: str | None,
    basis: Basis,
) -> None:
    query = f"{identity.name} {article}"
    deferred.append(
        DeferredLookup(
            interface="get_article",
            query=query,
            reason="Load the moved article destination before making a current article-substance claim.",
            source_type="law_article",
            filters=article_lookup_filters(identity, article, as_of=as_of, basis=basis),
        )
    )


def append_whole_law_article_status_gaps(
    law_text: LawText,
    gaps: list[ContextGap],
    deferred: list[DeferredLookup],
    source_notes: list[str],
    *,
    as_of: str | None,
    basis: Basis,
) -> None:
    for article in law_text.articles:
        if article.is_deleted:
            append_deleted_article_gap(article, gaps, source_notes)
            continue
        if not article.moved_to:
            continue

        query = f"{article.identity.name} {article.article}".strip()
        gaps.append(
            ContextGap(
                kind="moved_article",
                reason=(
                    f"{query} is marked moved to {article.moved_to}; "
                    "do not treat the movement marker as current article substance."
                ),
                query=query,
                recommended_interface="load_article_context",
            )
        )
        filters = article_lookup_filters(article.identity, article.article, as_of=as_of, basis=basis)
        filters["moved_to"] = article.moved_to
        deferred.append(
            DeferredLookup(
                interface="load_article_context",
                query=query,
                reason=(
                    "Load moved-article context so the destination article is established "
                    "before making a current article-substance claim."
                ),
                source_type="law_article",
                filters=filters,
            )
        )
        source_notes.append(
            f"{query} is a moved article source state to {article.moved_to}, not operative text."
        )


def append_deleted_administrative_rule_article_gap(
    article: AdministrativeRuleArticleText,
    gaps: list[ContextGap],
    source_notes: list[str],
) -> None:
    gaps.append(
        ContextGap(
            kind="deleted_administrative_rule_article",
            reason=(
                f"{article.identity.name} {article.article} is marked deleted; "
                "do not treat the deletion marker as current operational criteria."
            ),
            query=f"{article.identity.name} {article.article}",
            recommended_interface="load_administrative_rule_context",
        )
    )
    source_notes.append(
        f"{article.identity.name} {article.article} is a deleted administrative-rule article "
        "source state, not current operational criteria."
    )


def append_moved_administrative_rule_destination_lookup_gap(
    exc: MolegApiError,
    identity: AdministrativeRuleIdentity,
    article: str,
    gaps: list[ContextGap],
    deferred: list[DeferredLookup],
) -> None:
    query = f"{identity.name} {article}"
    append_source_failure_gap(
        exc,
        gaps,
        query=query,
        recommended_interface="load_administrative_rule_context",
        source_label=f"Moved administrative-rule article destination lookup for {query}",
    )
    append_moved_administrative_rule_destination_deferred(identity, article, deferred)


def append_moved_administrative_rule_destination_deferred(
    identity: AdministrativeRuleIdentity,
    article: str,
    deferred: list[DeferredLookup],
) -> None:
    query = f"{identity.name} {article}"
    deferred.append(
        DeferredLookup(
            interface="load_administrative_rule_context",
            query=query,
            reason=(
                "Retry the moved administrative-rule article destination before making a "
                "current operational-criteria claim."
            ),
            source_type="administrative_rule_article",
            filters=administrative_rule_article_lookup_filters(identity, article),
        )
    )


def administrative_rule_article_lookup_filters(
    identity: AdministrativeRuleIdentity,
    article: str,
) -> dict[str, Any]:
    filters: dict[str, Any] = {"article": article}
    if identity.serial_id:
        filters["serial_id"] = identity.serial_id
    elif identity.rule_id:
        filters["rule_id"] = identity.rule_id
    else:
        filters["name"] = identity.name
    return filters


def article_lookup_filters(
    identity: LawIdentity,
    article: str,
    *,
    as_of: str | None,
    basis: Basis,
) -> dict[str, Any]:
    filters: dict[str, Any] = {
        "article": article,
        "basis": basis,
    }
    reference_date = compact_date(as_of) if as_of else None
    if reference_date:
        filters["as_of"] = reference_date
    if identity.law_id:
        filters["law_id"] = identity.law_id
    elif identity.mst:
        filters["mst"] = identity.mst
    else:
        filters["law_name"] = identity.name
    return filters


def is_compact_ymd(value: str | None) -> bool:
    return bool(value and len(value) == 8 and value.isdigit())

from .validation import *
from .annex_tables import *
from .identity_params import *
from .admin_scope import *
from .temporal_gaps import *
from .delegated_scope import *
from .source_matching import *
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
from .ranking import *

__all__ = [name for name in globals() if not name.startswith("__")]
