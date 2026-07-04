from __future__ import annotations

from .foundation import *
from .config import *

def string_value(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def followup_interface(lookup: DeferredLookup | FollowUpSearch) -> str:
    interface = string_value(getattr(lookup, "interface", None))
    interface = interface.strip() if interface else None
    if not interface:
        raise UnsupportedFormatError("follow-up lookup interface is required")
    return interface


def followup_query(lookup: DeferredLookup | FollowUpSearch) -> str:
    query = string_value(getattr(lookup, "query", None))
    return query.strip() if query else ""


def followup_query_with_article(query: str, filters: dict[str, Any]) -> str:
    article = followup_str(filters, "article", "jo")
    if not article:
        return query
    article_label = article_label_for_filter(article)
    if article_label in query:
        return query
    return " ".join(part for part in (query, article_label) if part)


def followup_filters(lookup: DeferredLookup | FollowUpSearch) -> dict[str, Any]:
    filters = getattr(lookup, "filters", None) or {}
    if not isinstance(filters, dict):
        raise UnsupportedFormatError("follow-up lookup filters must be a mapping")
    return dict(filters)


def followup_str(filters: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = string_value(filters.get(key))
        value = value.strip() if value else None
        if value:
            return value
    return None


def followup_int(filters: dict[str, Any], key: str, default: int) -> int:
    value = filters.get(key)
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise UnsupportedFormatError(f"follow-up filter {key!r} must be an integer") from exc


def followup_bool(filters: dict[str, Any], key: str, default: bool) -> bool:
    value = filters.get(key)
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n"}:
            return False
    return bool(value)


def followup_basis(filters: dict[str, Any], default: Basis = "effective") -> Basis:
    basis = followup_str(filters, "basis") or default
    validate_choice("basis", basis, BASIS_VALUES)
    return basis  # type: ignore[return-value]


def followup_budget(filters: dict[str, Any]) -> BundleBudget:
    budget = followup_str(filters, "budget") or "standard"
    validate_choice("budget", budget, BUNDLE_BUDGET_VALUES)
    return budget  # type: ignore[return-value]


def followup_bundle_mode(filters: dict[str, Any]) -> BundleMode:
    mode = followup_str(filters, "mode")
    if mode:
        validate_choice("mode", mode, BUNDLE_MODE_VALUES)
        return mode  # type: ignore[return-value]
    if followup_promulgation_bridge(filters):
        return "promulgated_bill"
    if followup_law_source_id(filters):
        return "statute_review"
    return "question"


def followup_law_source_id(filters: dict[str, Any]) -> str | None:
    return followup_str(filters, "law_id", "id", "mst")


def followup_law_identity(
    lookup: DeferredLookup | FollowUpSearch,
    filters: dict[str, Any],
    *,
    basis: Basis,
) -> LawIdentity:
    law_id = followup_str(filters, "law_id", "id")
    mst = followup_str(filters, "mst")
    name = (
        followup_str(filters, "law_name", "name")
        or followup_query(lookup)
        or law_id
        or mst
    )
    if not name:
        raise NoResultError("follow-up law identity requires law_id, mst, law_name, or query")
    return LawIdentity(
        law_id=law_id,
        name=name,
        basis=basis,
        mst=mst,
        lid=followup_str(filters, "lid"),
        promulgation_date=followup_str(filters, "promulgation_date", "promulgation_dt"),
        effective_date=followup_str(filters, "effective_date", "as_of"),
        promulgation_number=followup_str(filters, "promulgation_number", "prom_no"),
        law_type=followup_str(filters, "law_type"),
        ministry=followup_str(filters, "ministry"),
    )


def followup_optional_law_identity(
    lookup: DeferredLookup | FollowUpSearch,
    filters: dict[str, Any],
) -> LawIdentity | None:
    if not followup_law_source_id(filters):
        return None
    return followup_law_identity(lookup, filters, basis=followup_basis(filters))


def followup_article(filters: dict[str, Any], query: str) -> str | int:
    article = followup_str(filters, "article", "jo")
    if article:
        return article
    article = article_from_query(query)
    if article:
        return article
    raise NoResultError("follow-up article lookup requires an article filter")


def followup_optional_article(filters: dict[str, Any], query: str) -> str | int | None:
    article = followup_str(filters, "article", "jo")
    if article:
        return article
    return article_from_query(query)


def article_from_query(query: str) -> str | None:
    match = re.search(r"제\s*\d+\s*조(?:\s*의\s*\d+)?|\d+\s*조(?:\s*의\s*\d+)?", query)
    if not match:
        return None
    return article_label_for_filter(match.group(0))


def followup_articles(filters: dict[str, Any]) -> list[str | int] | None:
    articles = filters.get("articles")
    if isinstance(articles, (list, tuple, set)):
        return list(articles)
    if articles not in (None, ""):
        return [articles]
    article = followup_str(filters, "article", "jo")
    return [article] if article else None


def followup_required_articles(filters: dict[str, Any]) -> list[str | int]:
    articles = followup_articles(filters)
    if not articles:
        raise NoResultError("follow-up lookup requires articles")
    return articles


def followup_date_range(filters: dict[str, Any]) -> tuple[str, str] | None:
    date_range = filters.get("date_range")
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        return (str(date_range[0]), str(date_range[1]))
    start = followup_str(filters, "start", "from", "from_date")
    end = followup_str(filters, "end", "to", "to_date")
    if start or end:
        if not start or not end:
            raise NoResultError("follow-up date_range requires both start and end")
        return (start, end)
    return None


def followup_promulgation_bridge(filters: dict[str, Any]) -> dict[str, Any] | None:
    bridge = filters.get("promulgation_bridge")
    if isinstance(bridge, dict):
        return dict(bridge)
    if not any(followup_str(filters, key) for key in ("prom_law_nm", "prom_no", "promulgation_dt")):
        return None
    values = {
        "prom_law_nm": followup_str(filters, "prom_law_nm"),
        "prom_no": followup_str(filters, "prom_no", "promulgation_number"),
        "promulgation_dt": followup_str(filters, "promulgation_dt", "promulgation_date"),
    }
    return {key: value for key, value in values.items() if value} or None

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
from .followup_identities import *
from .bridge import *
from .requested_load_gaps import *
from .context_load_gaps import *
from .ranking import *

__all__ = [name for name in globals() if not name.startswith("__")]
