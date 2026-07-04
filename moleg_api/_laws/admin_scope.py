from __future__ import annotations

from .foundation import *
from .config import *

def administrative_rule_text_from_articles(articles: list[AdministrativeRuleArticleText]) -> str:
    return "\n\n".join(
        f"{article.article or ''} {article.title or ''}\n{article.text}".strip()
        for article in articles
    )


def administrative_rule_text_from_current_articles(
    context: AdministrativeRuleContext,
) -> AdministrativeRuleText:
    current_articles = list(context.current_articles)
    return replace(
        context.rule,
        text=administrative_rule_text_from_articles(current_articles),
        articles=current_articles,
    )


def filter_administrative_rule_text_to_delegated_scope(
    rule: AdministrativeRuleText,
    scope: dict[str, set[str]],
    gaps: list[ContextGap],
    source_notes: list[str],
) -> AdministrativeRuleText:
    if not rule.articles or (not scope["law_names"] and not scope["law_ids"]):
        return rule

    article_states = [
        (article, administrative_rule_article_source_match_state(article, scope))
        for article in rule.articles
    ]
    matching_articles = [
        article
        for article, (match_state, _) in article_states
        if match_state == "matched"
    ]
    if not matching_articles:
        return rule

    query = delegated_criteria_scope_label(scope)
    for article, (match_state, source_label) in article_states:
        if match_state == "matched":
            continue
        article_label = article.article or "unlabeled article"
        if match_state == "unverified":
            reason = (
                f"{rule.identity.name} {article_label} was excluded from target delegated criteria "
                f"because its source-law or source-article reference is missing for {query}."
            )
            kind = "delegated_criteria_source_unverified"
        else:
            reason = (
                f"{rule.identity.name} {article_label} was excluded from target delegated criteria "
                f"because its explicit source reference ({source_label}) does not match {query}."
            )
            kind = "delegated_criteria_source_mismatch"
        gaps.append(
            ContextGap(
                kind=kind,
                reason=reason,
                query=query,
                recommended_interface="find_delegated_rules",
            )
        )
        source_notes.append(reason)

    return replace(
        rule,
        text=administrative_rule_text_from_articles(matching_articles),
        articles=matching_articles,
    )


def administrative_rule_article_source_match_state(
    article: AdministrativeRuleArticleText,
    scope: dict[str, set[str]],
) -> tuple[str, str]:
    reference = {
        "law_id": article.source_law_id,
        "law_name": article.source_law_name,
        "article": comparable_article_label(article.source_article),
    }
    if not any(reference.values()):
        return ("unverified", "missing source reference")
    source_label = " ".join(
        part
        for part in (
            reference["law_name"] or reference["law_id"] or "unknown law",
            reference["article"],
        )
        if part
    )
    if not source_law_matches_scope(reference, scope):
        return ("mismatch", source_label)
    if not scope["articles"]:
        return ("matched", source_label)
    if not reference["article"]:
        return ("unverified", source_label)
    if any(articles_overlap(reference["article"], target_article) for target_article in scope["articles"]):
        return ("matched", source_label)
    return ("mismatch", source_label)

from .validation import *
from .annex_tables import *
from .identity_params import *
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
from .ranking import *

__all__ = [name for name in globals() if not name.startswith("__")]
