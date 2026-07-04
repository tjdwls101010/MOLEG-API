from __future__ import annotations

from .foundation import *
from .config import *

def bundle_limits(budget: BundleBudget) -> dict[str, int]:
    validate_choice("budget", budget, BUNDLE_BUDGET_VALUES)
    return BUNDLE_BUDGETS[budget]


def delegated_criteria_load_limits(budget: BundleBudget) -> dict[str, int]:
    validate_choice("budget", budget, BUNDLE_BUDGET_VALUES)
    return DELEGATED_CRITERIA_LOAD_LIMITS[budget]


def authority_load_limits(budget: BundleBudget) -> dict[str, int]:
    validate_choice("budget", budget, BUNDLE_BUDGET_VALUES)
    return AUTHORITY_LOAD_LIMITS[budget]


def bundle_eager_detail_limits(
    query: str | None,
    *,
    mode: BundleMode,
    budget: BundleBudget,
) -> dict[str, int]:
    try:
        budget_limits = BUNDLE_EAGER_DETAIL_LIMITS[budget]
    except KeyError as exc:
        raise UnsupportedFormatError(f"Unsupported legal context bundle budget: {budget}") from exc
    limits = {key: 0 for key in budget_limits}
    intents = bundle_query_intents(query, mode=mode)
    if "legal_meaning" in intents:
        limits["interpretations"] = budget_limits["interpretations"]
        limits["cases"] = budget_limits["cases"]
        limits["constitutional_decisions"] = budget_limits["constitutional_decisions"]
    if "application" in intents:
        limits["interpretations"] = max(limits["interpretations"], budget_limits["interpretations"])
        limits["cases"] = max(limits["cases"], budget_limits["cases"])
    if "constitutional" in intents:
        limits["constitutional_decisions"] = max(
            limits["constitutional_decisions"],
            budget_limits["constitutional_decisions"],
        )
    return limits


def bundle_query_intents(query: str | None, *, mode: BundleMode) -> set[str]:
    if mode not in ("question", "statute_review"):
        return set()
    text = str(query or "")
    intents: set[str] = set()
    if any(keyword in text for keyword in BUNDLE_LEGAL_MEANING_KEYWORDS):
        intents.add("legal_meaning")
    if any(keyword in text for keyword in BUNDLE_APPLICATION_KEYWORDS):
        intents.add("application")
    if any(keyword in text for keyword in BUNDLE_CONSTITUTIONAL_KEYWORDS):
        intents.add("constitutional")
    return intents


def target_article_refs_from_loaded_articles(articles: list[ArticleText]) -> set[tuple[str, str]]:
    return {
        (article.identity.name, article.article)
        for article in articles
        if article.identity.name and article.article
    }


def article_refs_matching_targets(
    reference_sets: list[list[Any]],
    targets: set[tuple[str, str]],
) -> set[tuple[str, str]]:
    return {
        (item.law_name, item.article)
        for references in reference_sets
        for item in references
        if (item.law_name, item.article) in targets
    }


def article_ref_label(references: set[tuple[str, str]]) -> str:
    return ", ".join(f"{law_name} {article}" for law_name, article in sorted(references))

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
