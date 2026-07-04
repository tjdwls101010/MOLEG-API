from __future__ import annotations

from .foundation import *
from .config import *

def authority_temporal_trace_filters(
    identity: LawIdentity | None,
    target: tuple[str | None, str | None],
    *,
    source_type: str,
    authority_date: str | None,
    effective_date: str | None,
    reference_date: str | None,
) -> dict[str, Any]:
    filters: dict[str, Any] = {}
    if identity and identity.law_id:
        filters["law_id"] = identity.law_id
    elif identity and identity.mst:
        filters["mst"] = identity.mst
    elif target[0]:
        filters["law_name"] = target[0]
    filters["article"] = target[1]
    filters["authority_source_type"] = source_type
    filters["authority_date"] = authority_date
    filters.update(authority_temporal_filter_dates(effective_date, reference_date))
    return filters


def authority_reference_date_phrase(reference_date: str | None) -> str:
    if is_compact_ymd(reference_date):
        return f" and reference date is {reference_date}"
    return ""


def authority_temporal_filter_dates(
    effective_date: str | None,
    reference_date: str | None,
) -> dict[str, str]:
    filters: dict[str, str] = {}
    if effective_date:
        filters["current_article_effective_date"] = effective_date
    if is_compact_ymd(reference_date):
        filters["reference_date"] = str(reference_date)
    return filters


def authority_search_interface(source_type: str) -> str:
    if source_type == "interpretation":
        return "search_interpretations"
    if source_type == "case":
        return "search_cases"
    if source_type == "constitutional":
        return "search_constitutional_decisions"
    return "load_authority_context"


def authority_references_current_targets(
    references: list[Any],
    authority_date_value: str | None,
    target_articles: list[ArticleText],
    *,
    reference_date: str | None = None,
) -> bool:
    if not references or not target_articles:
        return False
    target_effective_dates = {
        (article.identity.name, article.article): compact_date(
            article.effective_date or article.identity.effective_date
        )
        for article in target_articles
        if article.identity.name and article.article
    }
    target_refs = set(target_effective_dates)
    authority_date = compact_date(authority_date_value)
    matched_targets = {
        (reference.law_name, reference.article)
        for reference in references
        if (reference.law_name, reference.article) in target_refs
    }
    if not matched_targets:
        return False
    if matched_targets != target_refs:
        return False
    if not is_compact_ymd(authority_date):
        if is_compact_ymd(reference_date):
            return False
        return not any(is_compact_ymd(target_effective_dates[target]) for target in matched_targets)
    reference_date = compact_date(reference_date)
    if is_compact_ymd(reference_date) and authority_date > reference_date:
        return False
    return all(
        not is_compact_ymd(target_effective_dates[target]) or authority_date >= target_effective_dates[target]
        for target in matched_targets
    )

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
from .followup_basic import *
from .followup_identities import *
from .bridge import *
from .requested_load_gaps import *
from .context_load_gaps import *
from .ranking import *

__all__ = [name for name in globals() if not name.startswith("__")]
