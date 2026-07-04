from __future__ import annotations

from .foundation import *
from .config import *

def annex_form_identity_from_identifier(
    identifier: AnnexFormIdentity | AnnexFormHit | str,
    *,
    source: str,
    title: str | None,
) -> AnnexFormIdentity:
    if isinstance(identifier, AnnexFormHit):
        return identifier.identity
    if isinstance(identifier, AnnexFormIdentity):
        return identifier
    source_type = annex_source_type(source)
    text = str(identifier).strip()
    if not text:
        raise NoResultError("Annex/form identifier is required")
    if not text.isdigit():
        raise NoResultError(
            f"Identifier {text!r} looks like an annex/form title, not a source ID. "
            f"Call `search_annex_forms({text!r})` to find the annex/form identity, "
            "then pass the result or its `annex_id` to this method."
        )
    normalized_title = title.strip() if title else text
    if not normalized_title:
        normalized_title = text
    return AnnexFormIdentity(
        annex_id=text,
        title=normalized_title,
        source_type=source_type,
        source_target=annex_target_for(source_type),
    )


def identity_from_identifier(identifier: LawIdentity | LawHit | str, *, basis: Basis) -> LawIdentity:
    if isinstance(identifier, LawHit):
        return identifier.identity
    if isinstance(identifier, LawIdentity):
        return identifier
    text = str(identifier).strip()
    if not text:
        raise NoResultError("Law identifier is required")
    if not text.isdigit():
        raise NoResultError(
            f"Identifier {text!r} looks like a law name, not a law ID. "
            f"Call `search_laws({text!r})` to find the law ID, then pass the "
            "result or its `law_id` to this method."
        )
    return LawIdentity(law_id=text, name=text, basis=basis)


def identity_params(identity: LawIdentity, *, as_of: str | None, basis: Basis) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if identity.mst and as_of:
        params["MST"] = identity.mst
    elif identity.law_id:
        params["ID"] = identity.law_id
    elif identity.mst:
        params["MST"] = identity.mst
    else:
        raise NoResultError("Law identity has neither law_id nor mst")

    if basis == "effective" and as_of:
        params["efYd"] = compact_date(as_of)
    return params


def versioned_law_identity_params(identity: LawIdentity) -> dict[str, Any]:
    if identity.mst:
        return {"MST": identity.mst}
    if identity.law_id:
        return {"ID": identity.law_id}
    raise NoResultError("Law identity has neither law_id nor mst")


def law_text_identity_params(identity: LawIdentity, *, as_of: str | None, basis: Basis) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if identity.mst:
        params["MST"] = identity.mst
    elif identity.law_id:
        params["ID"] = identity.law_id
    else:
        raise NoResultError("Law identity has neither law_id nor mst")

    if basis == "effective" and as_of:
        params["efYd"] = compact_date(as_of)
    return params


def prefer_versioned_law_identity(current: LawIdentity, loaded: LawIdentity) -> LawIdentity:
    if not loaded.mst:
        return current
    if current.law_id and loaded.law_id and current.law_id != loaded.law_id:
        return current
    if (
        current.name
        and loaded.name
        and current.name != current.law_id
        and current.name != loaded.name
    ):
        return current
    return LawIdentity(
        law_id=loaded.law_id or current.law_id,
        name=loaded.name or current.name,
        basis=loaded.basis,
        mst=loaded.mst,
        lid=loaded.lid or current.lid,
        promulgation_date=loaded.promulgation_date or current.promulgation_date,
        effective_date=loaded.effective_date or current.effective_date,
        promulgation_number=loaded.promulgation_number or current.promulgation_number,
        law_type=loaded.law_type or current.law_type,
        ministry=loaded.ministry or current.ministry,
        raw_keys=loaded.raw_keys or current.raw_keys,
    )


def select_requested_articles(
    available_articles: list[ArticleText],
    requested_articles: list[str | int],
) -> list[ArticleText]:
    articles_by_jo: dict[str, list[ArticleText]] = {}
    for article in available_articles:
        try:
            jo = format_article_jo(article.article)
        except ParseFailureError:
            continue
        articles_by_jo.setdefault(jo, []).append(article)

    selected: list[ArticleText] = []
    missing: list[str] = []
    for requested in requested_articles:
        jo = format_article_jo(requested)
        matches = articles_by_jo.get(jo)
        if not matches:
            missing.append(str(requested))
            continue
        selected.append(preferred_article_match(matches))

    if missing:
        raise NoResultError(f"No law article text found for: {', '.join(missing)}")
    return selected


def preferred_article_match(matches: list[ArticleText]) -> ArticleText:
    for article in matches:
        if str(article.raw.get("조문여부") or "").strip() == "조문":
            return article
    for article in matches:
        if article.title:
            return article
    for article in matches:
        if article.text.strip().startswith(article.article):
            return article
    return matches[0]


def select_requested_administrative_rule_articles(
    available_articles: list[AdministrativeRuleArticleText],
    requested_articles: list[str | int],
) -> list[AdministrativeRuleArticleText]:
    articles_by_label: dict[str, list[AdministrativeRuleArticleText]] = {}
    for article in available_articles:
        if article.article:
            articles_by_label.setdefault(article.article, []).append(article)

    selected: list[AdministrativeRuleArticleText] = []
    missing: list[str] = []
    for requested in requested_articles:
        label = article_label_for_filter(requested)
        matches = articles_by_label.get(label)
        if not matches:
            missing.append(str(requested))
            continue
        selected.append(matches[0])

    if missing:
        raise NoResultError(f"No administrative-rule article text found for: {', '.join(missing)}")
    return selected

from .validation import *
from .annex_tables import *
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
from .ranking import *

__all__ = [name for name in globals() if not name.startswith("__")]
