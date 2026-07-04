from __future__ import annotations

from .foundation import *
from .config import *

def terms_from_rows(
    rows: list[dict[str, Any]],
    *,
    source_type: str,
    source_target: str,
) -> list[LegalTermCandidate]:
    terms: list[LegalTermCandidate] = []
    for row in rows:
        term = normalize_term_candidate(row, source_type=source_type, source_target=source_target)
        if term:
            terms.append(term)
    return terms


def articles_from_rows(
    rows: list[dict[str, Any]],
    *,
    source_target: str,
) -> list[LegalArticleCandidate]:
    articles: list[LegalArticleCandidate] = []
    for row in rows:
        article = normalize_related_article_candidate(row, source_target=source_target)
        if article:
            articles.append(article)
    return articles


def laws_from_rows(
    rows: list[dict[str, Any]],
    *,
    source_target: str,
) -> list[LegalLawCandidate]:
    laws: list[LegalLawCandidate] = []
    for row in rows:
        law = normalize_related_law_candidate(row, source_target=source_target)
        if law:
            laws.append(law)
    return laws


def compact_terms(terms: list[LegalTermCandidate]) -> list[LegalTermCandidate]:
    seen: set[tuple[str, str, str | None]] = set()
    compacted: list[LegalTermCandidate] = []
    for term in terms:
        key = (term.term, term.source_type, term.relation)
        if key in seen:
            continue
        seen.add(key)
        compacted.append(term)
    return compacted


def compact_articles(articles: list[LegalArticleCandidate]) -> list[LegalArticleCandidate]:
    seen: set[tuple[str | None, str | None, str | None]] = set()
    compacted: list[LegalArticleCandidate] = []
    for article in articles:
        key = (article.law_id, article.law_name, article.article)
        if key in seen:
            continue
        seen.add(key)
        compacted.append(article)
    return compacted


def compact_laws(laws: list[LegalLawCandidate]) -> list[LegalLawCandidate]:
    seen: set[tuple[str | None, str, str | None]] = set()
    compacted: list[LegalLawCandidate] = []
    for law in laws:
        key = (law.law_id, law.name, law.article)
        if key in seen:
            continue
        seen.add(key)
        compacted.append(law)
    return compacted


def comparable_mechanism_identities(
    concept: str,
    laws: list[LegalLawCandidate],
    *,
    display: int,
    source_failures: list[ContextGap] | None = None,
) -> list[LawIdentity]:
    identities: dict[str, LawIdentity] = {}
    endpoints: dict[str, list[str]] = {}
    articles: dict[str, list[dict[str, str | None]]] = {}
    primary_key_by_name: dict[str, str] = {}

    for law in laws:
        if law.source_type != "law":
            continue

        if law.law_id:
            key = f"id:{law.law_id}"
            fallback_key = f"name:{law.name}"
            if key not in identities and fallback_key in identities:
                identities[key] = identities.pop(fallback_key)
                endpoints[key] = endpoints.pop(fallback_key)
                articles[key] = articles.pop(fallback_key)
                if primary_key_by_name.get(law.name) == fallback_key:
                    primary_key_by_name[law.name] = key
        else:
            key = primary_key_by_name.get(law.name, f"name:{law.name}")

        if key not in identities:
            identities[key] = LawIdentity(
                law_id=law.law_id,
                name=law.name,
                basis="effective",
                mst=law.mst,
                promulgation_date=law.promulgation_date,
                effective_date=law.effective_date,
                promulgation_number=law.promulgation_number,
                law_type=law.law_type,
                ministry=law.ministry,
                raw_keys={
                    "comparative_discovery": True,
                    "concept": concept,
                    "source_type": law.source_type,
                },
            )
            endpoints[key] = []
            articles[key] = []
            primary_key_by_name.setdefault(law.name, key)
        elif law.law_id and (
            not identities[key].law_id
            or not identities[key].mst
            or not identities[key].effective_date
        ):
            current = identities[key]
            identities[key] = LawIdentity(
                law_id=law.law_id or current.law_id,
                name=current.name,
                basis=current.basis,
                mst=law.mst or current.mst,
                lid=current.lid,
                promulgation_date=law.promulgation_date or current.promulgation_date,
                effective_date=law.effective_date or current.effective_date,
                promulgation_number=law.promulgation_number or current.promulgation_number,
                law_type=law.law_type or current.law_type,
                ministry=law.ministry or current.ministry,
                raw_keys=current.raw_keys,
            )
        if law.source_target and law.source_target not in endpoints[key]:
            endpoints[key].append(law.source_target)
        if law.article:
            anchor = {
                "article": law.article,
                "title": law.article_title,
                "source_target": law.source_target,
            }
            if not any(
                item["article"] == anchor["article"] and item["title"] == anchor["title"]
                for item in articles[key]
            ):
                articles[key].append(anchor)

    results: list[LawIdentity] = []
    for key, identity in identities.items():
        raw_keys = {
            **identity.raw_keys,
            "discovery_endpoints": endpoints[key],
            "source_articles": articles[key],
            "source_law_followups": comparable_source_law_followups(identity),
            "source_article_followups": comparable_source_article_followups(
                identity,
                articles[key],
            ),
        }
        if source_failures:
            raw_keys["source_failures"] = source_failure_payloads(source_failures)
        results.append(
            LawIdentity(
                law_id=identity.law_id,
                name=identity.name,
                basis=identity.basis,
                mst=identity.mst,
                lid=identity.lid,
                promulgation_date=identity.promulgation_date,
                effective_date=identity.effective_date,
                promulgation_number=identity.promulgation_number,
                law_type=identity.law_type,
                ministry=identity.ministry,
                raw_keys=raw_keys,
            )
        )
        if len(results) >= display:
            break
    return results


def comparable_source_law_followups(identity: LawIdentity) -> list[DeferredLookup]:
    if not law_identity_has_source_identifier(identity):
        return []
    return [
        DeferredLookup(
            interface="get_law",
            query=identity.name,
            reason="Load selected comparable law text before citing or comparing legal structure.",
            source_type="law",
            filters=law_identity_followup_filters(identity, include_basis=True),
        )
    ]


def comparable_source_article_followups(
    identity: LawIdentity,
    source_articles: list[dict[str, str | None]],
) -> list[DeferredLookup]:
    if not law_identity_has_source_identifier(identity):
        return []
    followups: list[DeferredLookup] = []
    for source_article in source_articles:
        article = source_article.get("article")
        if not article:
            continue
        filters: dict[str, Any] = {
            "article": article,
            "basis": identity.basis,
        }
        if identity.law_id:
            filters["law_id"] = identity.law_id
        if identity.mst:
            filters["mst"] = identity.mst
        followups.append(
            DeferredLookup(
                interface="get_article",
                query=f"{identity.name} {article}",
                reason="Load selected comparable mechanism article before citing or comparing legal structure.",
                source_type="law_article",
                filters=filters,
            )
        )
    return followups

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
