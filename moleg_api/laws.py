"""Deep law interfaces for the first MOLEG-API vertical slice."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .errors import AmbiguousLawError, MolegApiError, NoResultError, ParseFailureError, UnsupportedFormatError
from .models import (
    AdministrativeRuleHit,
    AdministrativeRuleIdentity,
    AdministrativeRuleText,
    Ambiguity,
    AnnexFormHit,
    AnnexFormIdentity,
    AnnexFormText,
    ArticleText,
    Basis,
    BundleRequest,
    CandidateContext,
    ContextGap,
    DeferredLookup,
    DelegationGraph,
    FollowUpSearch,
    InterpretationHit,
    InterpretationIdentity,
    InterpretationText,
    JudicialDecisionHit,
    JudicialDecisionIdentity,
    JudicialDecisionText,
    LegalArticleCandidate,
    LegalContextBundle,
    LegalLawCandidate,
    LegalQueryExpansion,
    LegalTermCandidate,
    LoadedContext,
    LawDiff,
    LawHit,
    LawHistory,
    LawIdentity,
    LawText,
)
from .normalization import (
    compact_date,
    extract_administrative_rule_articles,
    extract_articles,
    format_article_jo,
    normalize_administrative_rule_identity,
    normalize_annex_form_identity,
    normalize_article,
    normalize_delegated_rules,
    normalize_diff_changes,
    normalize_history_events,
    normalize_interpretation_identity,
    normalize_interpretation_text,
    normalize_judicial_decision_identity,
    normalize_judicial_decision_text,
    normalize_law_identity,
    normalize_related_article_candidate,
    normalize_related_law_candidate,
    normalize_term_candidate,
    parse_law_history_html,
    parse_law_history_total_count,
    unwrap_search_administrative_rules,
    unwrap_search_interpretations,
    unwrap_search_judicial_decisions,
    unwrap_search_laws,
    unwrap_service_payload,
    unwrap_target_rows,
)
from .source import LawGoKrClient, MolegSource


TARGETS: dict[Basis, dict[str, str]] = {
    "effective": {"list": "eflaw", "detail": "eflaw", "article": "eflawjosub"},
    "promulgated": {"list": "law", "detail": "law", "article": "lawjosub"},
}

LAW_HISTORY_HTML_DISPLAY = 100
LAW_HISTORY_HTML_MAX_PAGES = 20

BUNDLE_BUDGETS: dict[str, dict[str, int]] = {
    "minimal": {
        "law_candidates": 1,
        "articles": 3,
        "delegations": 3,
        "administrative_rules": 3,
        "annex_forms": 3,
        "interpretations": 3,
        "cases": 3,
        "constitutional_decisions": 2,
    },
    "standard": {
        "law_candidates": 3,
        "articles": 5,
        "delegations": 5,
        "administrative_rules": 5,
        "annex_forms": 5,
        "interpretations": 5,
        "cases": 5,
        "constitutional_decisions": 3,
    },
    "broad": {
        "law_candidates": 5,
        "articles": 10,
        "delegations": 10,
        "administrative_rules": 10,
        "annex_forms": 10,
        "interpretations": 10,
        "cases": 10,
        "constitutional_decisions": 10,
    },
}

ANNEX_FORM_TARGETS = {
    "law": "licbyl",
    "administrative_rule": "admbyl",
}

ANNEX_FORM_TEXT_ENDPOINTS = {
    "licbyl": "lsBylTextDownLoad.do",
    "admbyl": "admRulBylTextDownLoad.do",
}

ANNEX_SEARCH_SCOPES = {
    "title": 1,
    "source": 2,
    "body": 3,
}

ANNEX_TYPE_CODES = {
    "law": {
        "annex": "1",
        "별표": "1",
        "form": "2",
        "서식": "2",
        "attached_form": "3",
        "별지": "3",
        "separate": "4",
        "별도": "4",
        "appendix": "5",
        "부록": "5",
    },
    "administrative_rule": {
        "annex": "1",
        "별표": "1",
        "form": "2",
        "서식": "2",
        "attached_form": "3",
        "별지": "3",
    },
}


@dataclass(frozen=True)
class InterpretationSourceSpec:
    source_type: str
    target: str
    ministry: str | None = None
    can_get: bool = True


OFFICIAL_INTERPRETATION_SOURCE = InterpretationSourceSpec(
    source_type="moleg",
    target="expc",
)


MINISTRY_INTERPRETATION_SOURCES: dict[str, InterpretationSourceSpec] = {
    "경찰청": InterpretationSourceSpec("ministry", "npaCgmExpc", "경찰청"),
    "고용노동부": InterpretationSourceSpec("ministry", "moelCgmExpc", "고용노동부"),
    "과학기술정보통신부": InterpretationSourceSpec("ministry", "msitCgmExpc", "과학기술정보통신부"),
    "관세청": InterpretationSourceSpec("ministry", "kcsCgmExpc", "관세청"),
    "교육부": InterpretationSourceSpec("ministry", "moeCgmExpc", "교육부"),
    "국가데이터처": InterpretationSourceSpec("ministry", "kostatCgmExpc", "국가데이터처"),
    "국가보훈부": InterpretationSourceSpec("ministry", "mpvaCgmExpc", "국가보훈부"),
    "국가유산청": InterpretationSourceSpec("ministry", "khsCgmExpc", "국가유산청"),
    "국방부": InterpretationSourceSpec("ministry", "mndCgmExpc", "국방부"),
    "국세청": InterpretationSourceSpec("ministry", "ntsCgmExpc", "국세청", can_get=False),
    "국토교통부": InterpretationSourceSpec("ministry", "molitCgmExpc", "국토교통부"),
    "기상청": InterpretationSourceSpec("ministry", "kmaCgmExpc", "기상청"),
    "기후에너지환경부": InterpretationSourceSpec("ministry", "meCgmExpc", "기후에너지환경부"),
    "농림축산식품부": InterpretationSourceSpec("ministry", "mafraCgmExpc", "농림축산식품부"),
    "농촌진흥청": InterpretationSourceSpec("ministry", "rdaCgmExpc", "농촌진흥청"),
    "문화체육관광부": InterpretationSourceSpec("ministry", "mcstCgmExpc", "문화체육관광부"),
    "방위사업청": InterpretationSourceSpec("ministry", "dapaCgmExpc", "방위사업청"),
    "법무부": InterpretationSourceSpec("ministry", "mojCgmExpc", "법무부"),
    "법제처": InterpretationSourceSpec("ministry", "molegCgmExpc", "법제처"),
    "병무청": InterpretationSourceSpec("ministry", "mmaCgmExpc", "병무청"),
    "보건복지부": InterpretationSourceSpec("ministry", "mohwCgmExpc", "보건복지부"),
    "산림청": InterpretationSourceSpec("ministry", "kfsCgmExpc", "산림청"),
    "산업통상부": InterpretationSourceSpec("ministry", "motieCgmExpc", "산업통상부"),
    "성평등가족부": InterpretationSourceSpec("ministry", "mogefCgmExpc", "성평등가족부"),
    "소방청": InterpretationSourceSpec("ministry", "nfaCgmExpc", "소방청"),
    "식품의약품안전처": InterpretationSourceSpec("ministry", "mfdsCgmExpc", "식품의약품안전처"),
    "외교부": InterpretationSourceSpec("ministry", "mofaCgmExpc", "외교부"),
    "인사혁신처": InterpretationSourceSpec("ministry", "mpmCgmExpc", "인사혁신처"),
    "재외동포청": InterpretationSourceSpec("ministry", "okaCgmExpc", "재외동포청"),
    "재정경제부": InterpretationSourceSpec("ministry", "moefCgmExpc", "재정경제부", can_get=False),
    "조달청": InterpretationSourceSpec("ministry", "ppsCgmExpc", "조달청"),
    "중소벤처기업부": InterpretationSourceSpec("ministry", "mssCgmExpc", "중소벤처기업부"),
    "지식재산처": InterpretationSourceSpec("ministry", "kipoCgmExpc", "지식재산처"),
    "질병관리청": InterpretationSourceSpec("ministry", "kdcaCgmExpc", "질병관리청"),
    "통일부": InterpretationSourceSpec("ministry", "mouCgmExpc", "통일부"),
    "해양경찰청": InterpretationSourceSpec("ministry", "kcgCgmExpc", "해양경찰청"),
    "해양수산부": InterpretationSourceSpec("ministry", "mofCgmExpc", "해양수산부"),
    "행정안전부": InterpretationSourceSpec("ministry", "moisCgmExpc", "행정안전부"),
    "행정중심복합도시건설청": InterpretationSourceSpec("ministry", "naaccCgmExpc", "행정중심복합도시건설청"),
}


class MolegApi:
    """Task-level MOLEG-API facade for legislative-expert callers."""

    def __init__(self, source: MolegSource | None = None) -> None:
        self.source = source or LawGoKrClient()

    def search_laws(
        self,
        query: str,
        *,
        as_of: str | None = None,
        basis: Basis = "effective",
        law_type: str | None = None,
        ministry: str | None = None,
        display: int = 20,
    ) -> list[LawHit]:
        target = target_for(basis, "list")
        params: dict[str, Any] = {"query": query, "display": display}
        if as_of:
            params["efYd" if basis == "effective" else "date"] = compact_date(as_of)
        if law_type:
            params["knd"] = law_type
        if ministry:
            params["org"] = ministry

        payload = self.source.search(target, params)
        return [
            LawHit(identity=normalize_law_identity(row, basis=basis), raw=row)
            for row in unwrap_search_laws(payload)
        ]

    def resolve_promulgated_law(
        self,
        *,
        prom_law_nm: str | None = None,
        prom_no: str | None = None,
        promulgation_dt: str | None = None,
    ) -> LawIdentity:
        if not prom_law_nm and not prom_no:
            raise NoResultError("prom_law_nm or prom_no is required to resolve a promulgated law")

        hits = self.search_laws(prom_law_nm or "", basis="promulgated")
        filtered = [
            hit
            for hit in hits
            if matches_bridge(hit.identity, prom_no=prom_no, promulgation_dt=promulgation_dt)
        ]
        if not filtered:
            raise NoResultError("No law identity matched the promulgation bridge")
        identities = dedupe_identities([hit.identity for hit in filtered])
        if len(identities) > 1:
            names = ", ".join(identity.name for identity in identities[:5])
            raise AmbiguousLawError(
                f"Promulgation bridge matched multiple laws: {names}",
                kind="promulgation_bridge",
                candidates=identities,
            )
        return identities[0]

    def get_law(
        self,
        identifier: LawIdentity | LawHit | str,
        *,
        as_of: str | None = None,
        basis: Basis = "effective",
        articles: list[str | int] | None = None,
        include_metadata: bool = True,
    ) -> LawText:
        if articles is not None and not articles:
            raise NoResultError("articles must contain at least one article when provided")

        identity_hint = identity_from_identifier(identifier, basis=basis)
        target = target_for(basis, "detail")
        params = law_text_identity_params(identity_hint, as_of=as_of, basis=basis)

        payload = self.source.service(target, params)
        raw_law = unwrap_service_payload(payload, target)
        identity = normalize_law_identity(raw_law, basis=basis)
        law_articles = extract_articles(raw_law, identity)
        if articles is not None:
            law_articles = select_requested_articles(law_articles, articles)
        return LawText(identity=identity, articles=law_articles, raw=raw_law if include_metadata else {})

    def get_article(
        self,
        law_identifier: LawIdentity | LawHit | str,
        article: str | int,
        *,
        as_of: str | None = None,
        basis: Basis = "effective",
    ) -> ArticleText:
        identity = identity_from_identifier(law_identifier, basis=basis)
        target = target_for(basis, "article")
        params = identity_params(identity, as_of=as_of, basis=basis)
        params["JO"] = format_article_jo(article)

        payload = self.source.service(target, params)
        raw_article = unwrap_service_payload(payload, target)
        if "기본정보" in raw_article:
            article_identity = normalize_law_identity(raw_article, basis=basis)
        else:
            article_identity = identity
        article_row = article_payload_row(raw_article)
        normalized = normalize_article(article_row, article_identity)
        if normalized is None:
            raise NoResultError(f"No article text found for {article}")
        return normalized

    def trace_law_history(
        self,
        law_identifier: LawIdentity | LawHit | str,
        *,
        date_range: tuple[str, str] | None = None,
        article: str | int | None = None,
    ) -> LawHistory:
        identity = identity_from_identifier(law_identifier, basis="effective")
        if article is not None:
            params = identity_params(identity, as_of=None, basis="effective")
            params["JO"] = format_article_jo(article)
            payload = self.source.service("lsJoHstInf", params)
        elif date_range is not None:
            start, end = date_range
            params = {"fromRegDt": compact_date(start), "toRegDt": compact_date(end)}
            if identity.law_id:
                params["ID"] = identity.law_id
            payload = self.source.search("lsJoHstInf", params)
        else:
            payload = self._search_full_law_history(identity)

        events = normalize_history_events(payload, identity)
        if not events:
            raise NoResultError("No law history events found")
        return LawHistory(identity=identity, events=events, raw=payload)

    def _search_full_law_history(self, identity: LawIdentity) -> dict[str, Any]:
        rows: list[dict[str, Any]] = []
        page = 1
        pages_seen = 0
        total_count: int | None = None
        while page <= LAW_HISTORY_HTML_MAX_PAGES:
            params = {
                "query": identity.name,
                "display": LAW_HISTORY_HTML_DISPLAY,
                "page": page,
            }
            html = self.source.search_html("lsHistory", params)
            pages_seen += 1
            page_rows = parse_law_history_html(html)
            if total_count is None:
                total_count = parse_law_history_total_count(html)
            rows.extend(page_rows)
            if not page_rows:
                break
            if total_count is not None and len(rows) >= total_count:
                break
            page += 1

        matched_rows = [row for row in rows if history_row_matches_identity(row, identity)]
        if not matched_rows and rows:
            raise NoResultError(
                "No full law history rows matched the requested law identity; "
                "try an article/date_range history query or inspect lsHistory candidates manually"
            )
        return {
            "lsHistory": matched_rows,
            "source_target": "lsHistory",
            "source_total_count": total_count,
            "source_rows_seen": len(rows),
            "source_pages_seen": pages_seen,
        }

    def compare_law_versions(
        self,
        law_identifier: LawIdentity | LawHit | str,
        *,
        before: str | None = None,
        after: str | None = None,
        article: str | int | None = None,
    ) -> LawDiff:
        identity = identity_from_identifier(law_identifier, basis="effective")
        params = identity_params(identity, as_of=None, basis="effective")
        payload = self.source.service("oldAndNew", params)
        raw_diff = unwrap_service_payload(payload, "oldAndNew")
        before_identity = maybe_identity(raw_diff.get("구조문_기본정보"), basis="promulgated")
        after_identity = maybe_identity(raw_diff.get("신조문_기본정보"), basis="effective")
        changes = normalize_diff_changes(raw_diff, article=article)
        if not changes:
            raise NoResultError("No before/after law changes found")
        return LawDiff(
            identity=after_identity or before_identity or identity,
            before_identity=before_identity,
            after_identity=after_identity,
            changes=changes,
            raw={**raw_diff, "requested_before": before, "requested_after": after},
        )

    def find_delegated_rules(
        self,
        law_identifier: LawIdentity | LawHit | str,
        *,
        article: str | int | None = None,
    ) -> DelegationGraph:
        identity = identity_from_identifier(law_identifier, basis="effective")
        params = identity_params(identity, as_of=None, basis="effective")
        payload = self.source.service("lsDelegated", params)
        raw_delegation = unwrap_service_payload(payload, "lsDelegated")
        root_identity = maybe_identity(raw_delegation.get("법령정보"), basis="effective") or identity
        rules = normalize_delegated_rules(raw_delegation)
        if article is not None:
            wanted = f"제{int(article)}조" if isinstance(article, int) else str(article)
            rules = [rule for rule in rules if rule.source_article == wanted]
        if not rules:
            raise NoResultError("No delegated rules found")
        return DelegationGraph(identity=root_identity, rules=rules, raw=raw_delegation)

    def search_administrative_rules(
        self,
        query: str,
        *,
        ministry: str | None = None,
        rule_type: str | None = None,
        issued_on: str | None = None,
        include_history: bool = False,
        display: int = 20,
    ) -> list[AdministrativeRuleHit]:
        params: dict[str, Any] = {
            "query": query,
            "display": display,
            "nw": 2 if include_history else 1,
        }
        if ministry:
            params["org"] = ministry
        if rule_type:
            params["knd"] = rule_type
        if issued_on:
            params["date"] = compact_date(issued_on)

        payload = self.source.search("admrul", params)
        return [
            AdministrativeRuleHit(
                identity=normalize_administrative_rule_identity(row),
                raw=row,
            )
            for row in unwrap_search_administrative_rules(payload)
        ]

    def search_annex_forms(
        self,
        query: str,
        *,
        source: str = "law",
        search_scope: str = "source",
        annex_type: str | None = None,
        ministry: str | None = None,
        display: int = 20,
    ) -> list[AnnexFormHit]:
        source_type = annex_source_type(source)
        target = annex_target_for(source_type)
        params: dict[str, Any] = {
            "query": query,
            "display": display,
            "search": annex_search_scope(search_scope),
        }
        if annex_type:
            params["knd"] = annex_type_code(source_type, annex_type)
        if ministry:
            params["org"] = ministry

        payload = self.source.search(target, params)
        return [
            AnnexFormHit(
                identity=normalize_annex_form_identity(
                    row,
                    source_type=source_type,
                    source_target=target,
                ),
                raw=row,
            )
            for row in unwrap_target_rows(payload, target)
        ]

    def get_annex_form_body(
        self,
        identifier: AnnexFormIdentity | AnnexFormHit | str,
        *,
        source: str = "law",
        title: str | None = None,
        include_metadata: bool = True,
    ) -> AnnexFormText:
        identity = annex_form_identity_from_identifier(identifier, source=source, title=title)
        if not identity.annex_id:
            raise NoResultError("Annex/form identity has no source ID")
        try:
            endpoint = ANNEX_FORM_TEXT_ENDPOINTS[identity.source_target]
        except KeyError as exc:
            raise UnsupportedFormatError(
                f"{identity.source_target} annex/form body loading is not supported"
            ) from exc

        text = self.source.post_text(
            endpoint,
            {
                "bylSeq": identity.annex_id,
                "title": identity.title,
                "mode": "0",
            },
        )
        if not text.strip():
            raise NoResultError("No annex/form body text returned")
        return AnnexFormText(
            identity=identity,
            text=text,
            file_type="text/plain",
            extraction_method=endpoint,
            extraction_confidence="high",
            raw={
                "endpoint": endpoint,
                "source_target": identity.source_target,
                "annex_id": identity.annex_id,
            }
            if include_metadata
            else {},
        )

    def get_administrative_rule(
        self,
        identifier: AdministrativeRuleIdentity | AdministrativeRuleHit | str,
        *,
        articles: list[str | int] | None = None,
        include_metadata: bool = True,
    ) -> AdministrativeRuleText:
        identity_hint = administrative_rule_identity_from_identifier(identifier)
        params = administrative_rule_identity_params(identity_hint)
        payload = self.source.service("admrul", params)
        raw_rule = unwrap_service_payload(payload, "admrul")
        identity = normalize_administrative_rule_identity(raw_rule)
        rule_articles = extract_administrative_rule_articles(raw_rule, identity)
        if articles:
            wanted = {article_label_for_filter(article) for article in articles}
            rule_articles = [article for article in rule_articles if article.article in wanted]
        if not rule_articles:
            raise NoResultError("No administrative-rule text found")
        text = "\n\n".join(
            f"{article.article or ''} {article.title or ''}\n{article.text}".strip()
            for article in rule_articles
        )
        return AdministrativeRuleText(
            identity=identity,
            text=text,
            articles=rule_articles,
            raw=raw_rule if include_metadata else {},
        )

    def search_interpretations(
        self,
        query: str,
        *,
        source: str = "moleg",
        ministry: str | None = None,
        search_body: bool = False,
        interpreted_on: str | None = None,
        display: int = 20,
    ) -> list[InterpretationHit]:
        specs = interpretation_sources_for(source, ministry)
        hits: list[InterpretationHit] = []
        for spec in specs:
            params: dict[str, Any] = {
                "query": query,
                "display": display,
                "search": 2 if search_body else 1,
            }
            if interpreted_on:
                params["explYd"] = compact_date(interpreted_on)
            payload = self.source.search(spec.target, params)
            hits.extend(
                InterpretationHit(
                    identity=normalize_interpretation_identity(
                        row,
                        source_type=spec.source_type,
                        source_target=spec.target,
                        ministry=spec.ministry,
                    ),
                    raw=row,
                )
                for row in unwrap_search_interpretations(payload, spec.target)
            )
        return hits

    def get_interpretation(
        self,
        identifier: InterpretationIdentity | InterpretationHit | str,
        *,
        source: str | None = None,
        ministry: str | None = None,
        include_metadata: bool = True,
    ) -> InterpretationText:
        spec = interpretation_source_for_identifier(identifier, source=source, ministry=ministry)
        if not spec.can_get:
            raise UnsupportedFormatError(
                f"{spec.ministry or spec.target} interpretation source has no cataloged detail endpoint"
            )
        identity_hint = interpretation_identity_from_identifier(identifier, spec)
        params = interpretation_identity_params(identity_hint)
        payload = self.source.service(spec.target, params)
        raw_interpretation = unwrap_service_payload(payload, spec.target)
        text = normalize_interpretation_text(
            raw_interpretation,
            source_type=spec.source_type,
            source_target=spec.target,
            ministry=spec.ministry,
        )
        if not include_metadata:
            return InterpretationText(
                identity=text.identity,
                question=text.question,
                answer=text.answer,
                reason=text.reason,
                related_laws=text.related_laws,
                text=text.text,
                raw={},
            )
        return text

    def search_cases(
        self,
        query: str,
        *,
        court: str = "all",
        court_name: str | None = None,
        search_body: bool = False,
        decided_on: str | None = None,
        case_number: str | None = None,
        display: int = 20,
    ) -> list[JudicialDecisionHit]:
        params: dict[str, Any] = {
            "query": query,
            "display": display,
            "search": 2 if search_body else 1,
        }
        court_code = court_filter_code(court)
        if court_code:
            params["org"] = court_code
        if court_name:
            params["curt"] = court_name
        if decided_on:
            params["date"] = compact_date(decided_on)
        if case_number:
            params["nb"] = case_number

        payload = self.source.search("prec", params)
        return [
            JudicialDecisionHit(
                identity=normalize_judicial_decision_identity(
                    row,
                    source_type="case",
                    source_target="prec",
                ),
                raw=row,
            )
            for row in unwrap_search_judicial_decisions(payload, "prec")
        ]

    def get_case(
        self,
        identifier: JudicialDecisionIdentity | JudicialDecisionHit | str,
        *,
        include_metadata: bool = True,
    ) -> JudicialDecisionText:
        identity_hint = judicial_decision_identity_from_identifier(
            identifier,
            source_type="case",
            source_target="prec",
        )
        params = judicial_decision_identity_params(identity_hint)
        payload = self.source.service("prec", params)
        raw_case = unwrap_service_payload(payload, "prec")
        text = normalize_judicial_decision_text(
            raw_case,
            source_type="case",
            source_target="prec",
        )
        if include_metadata:
            return text
        return JudicialDecisionText(
            identity=text.identity,
            holdings=text.holdings,
            summary=text.summary,
            full_text=text.full_text,
            referenced_statutes=text.referenced_statutes,
            reviewed_statutes=text.reviewed_statutes,
            referenced_cases=text.referenced_cases,
            text=text.text,
            raw={},
        )

    def search_constitutional_decisions(
        self,
        query: str,
        *,
        search_body: bool = False,
        decided_on: str | None = None,
        case_number: str | None = None,
        display: int = 20,
    ) -> list[JudicialDecisionHit]:
        params: dict[str, Any] = {
            "query": query,
            "display": display,
            "search": 2 if search_body else 1,
        }
        if decided_on:
            params["date"] = compact_date(decided_on)
        if case_number:
            params["nb"] = case_number

        payload = self.source.search("detc", params)
        return [
            JudicialDecisionHit(
                identity=normalize_judicial_decision_identity(
                    row,
                    source_type="constitutional",
                    source_target="detc",
                ),
                raw=row,
            )
            for row in unwrap_search_judicial_decisions(payload, "detc")
        ]

    def get_constitutional_decision(
        self,
        identifier: JudicialDecisionIdentity | JudicialDecisionHit | str,
        *,
        include_metadata: bool = True,
    ) -> JudicialDecisionText:
        identity_hint = judicial_decision_identity_from_identifier(
            identifier,
            source_type="constitutional",
            source_target="detc",
        )
        params = judicial_decision_identity_params(identity_hint)
        payload = self.source.service("detc", params)
        raw_decision = unwrap_service_payload(payload, "detc")
        text = normalize_judicial_decision_text(
            raw_decision,
            source_type="constitutional",
            source_target="detc",
        )
        if include_metadata:
            return text
        return JudicialDecisionText(
            identity=text.identity,
            holdings=text.holdings,
            summary=text.summary,
            full_text=text.full_text,
            referenced_statutes=text.referenced_statutes,
            reviewed_statutes=text.reviewed_statutes,
            referenced_cases=text.referenced_cases,
            text=text.text,
            raw={},
        )

    def expand_legal_query(
        self,
        query: str,
        *,
        display: int = 5,
        include_websearch_hint: bool = True,
    ) -> LegalQueryExpansion:
        if not query.strip():
            raise NoResultError("query is required for legal query expansion")

        raw: dict[str, Any] = {}
        empty_sources: list[str] = []

        law_payload = self.source.search("eflaw", {"query": query, "display": display})
        raw["eflaw"] = law_payload
        law_rows = unwrap_search_laws(law_payload)
        if not law_rows:
            empty_sources.append("eflaw")
        law_candidates: list[LawIdentity] = []
        for row in law_rows:
            try:
                law_candidates.append(normalize_law_identity(row, basis="effective"))
            except ParseFailureError:
                continue

        legal_term_rows = self._search_rows("lstrmAI", {"query": query, "display": display}, raw, empty_sources)
        everyday_term_rows = self._search_rows("dlytrm", {"query": query, "display": display}, raw, empty_sources)
        legal_to_everyday_rows = self._service_rows("lstrmRlt", {"query": query}, raw, empty_sources)
        everyday_to_legal_rows = self._service_rows("dlytrmRlt", {"query": query}, raw, empty_sources)
        term_article_rows = self._service_rows("lstrmRltJo", {"query": query}, raw, empty_sources)
        ai_search_rows = self._search_rows(
            "aiSearch",
            {"query": query, "display": display, "search": 0},
            raw,
            empty_sources,
        )
        ai_related_rows = self._search_rows(
            "aiRltLs",
            {"query": query, "search": 0},
            raw,
            empty_sources,
        )

        term_candidates = compact_terms(
            [
                *terms_from_rows(legal_term_rows, source_type="legal_term", source_target="lstrmAI"),
                *terms_from_rows(everyday_term_rows, source_type="everyday_term", source_target="dlytrm"),
            ]
        )
        related_terms = compact_terms(
            [
                *terms_from_rows(legal_to_everyday_rows, source_type="everyday_term", source_target="lstrmRlt"),
                *terms_from_rows(everyday_to_legal_rows, source_type="legal_term", source_target="dlytrmRlt"),
            ]
        )
        related_articles = compact_articles(
            [
                *articles_from_rows(term_article_rows, source_target="lstrmRltJo"),
                *articles_from_rows(ai_search_rows, source_target="aiSearch"),
                *articles_from_rows(ai_related_rows, source_target="aiRltLs"),
            ]
        )
        related_laws = compact_laws(
            [
                *laws_from_rows(ai_search_rows, source_target="aiSearch"),
                *laws_from_rows(ai_related_rows, source_target="aiRltLs"),
            ]
        )

        follow_ups = build_follow_up_searches(
            query,
            law_candidates=law_candidates,
            term_candidates=[*term_candidates, *related_terms],
            related_laws=related_laws,
            include_websearch_hint=include_websearch_hint,
        )

        return LegalQueryExpansion(
            original_query=query,
            law_candidates=dedupe_identities(law_candidates),
            term_candidates=term_candidates,
            related_terms=related_terms,
            related_articles=related_articles,
            related_laws=related_laws,
            follow_up_searches=follow_ups,
            empty_sources=empty_sources,
            raw=raw,
        )

    def _search_rows(
        self,
        target: str,
        params: dict[str, Any],
        raw: dict[str, Any],
        empty_sources: list[str],
    ) -> list[dict[str, Any]]:
        payload = self.source.search(target, params)
        raw[target] = payload
        rows = unwrap_target_rows(payload, target)
        if not rows:
            empty_sources.append(target)
        return rows

    def load_legal_context_bundle(
        self,
        query: str | None = None,
        *,
        promulgation_bridge: dict[str, Any] | None = None,
        law_identifier: LawIdentity | LawHit | str | None = None,
        articles: list[str | int] | None = None,
        mode: str = "question",
        budget: str = "standard",
    ) -> LegalContextBundle:
        limits = bundle_limits(budget)
        request = BundleRequest(
            query=query,
            mode=mode,
            budget=budget,
            articles=list(articles or []),
            promulgation_bridge=dict(promulgation_bridge or {}),
            law_identifier=law_identifier,
        )

        source_notes: list[str] = [
            "LegalContextBundle is staged context for Claude inspection, not a legal conclusion."
        ]
        ambiguities: list[Ambiguity] = []
        gaps: list[ContextGap] = []
        deferred: list[DeferredLookup] = []
        loaded_laws: list[LawText] = []
        loaded_articles: list[ArticleText] = []
        loaded_delegations: list[DelegationGraph] = []
        admin_texts: list[AdministrativeRuleText] = []
        interpretation_texts: list[InterpretationText] = []
        case_texts: list[JudicialDecisionText] = []
        constitutional_texts: list[JudicialDecisionText] = []
        histories: list[LawHistory] = []
        diffs: list[LawDiff] = []
        query_expansion: LegalQueryExpansion | None = None
        law_candidates: list[LawIdentity] = []
        administrative_candidates: list[AdministrativeRuleHit] = []
        annex_form_candidates: list[AnnexFormHit] = []
        interpretation_candidates: list[InterpretationHit] = []
        case_candidates: list[JudicialDecisionHit] = []
        constitutional_candidates: list[JudicialDecisionHit] = []

        primary_identity: LawIdentity | None = None
        search_query = query

        if mode == "question":
            if not query:
                raise NoResultError("query is required for question bundles")
            query_expansion = self.expand_legal_query(query, display=limits["law_candidates"])
            law_candidates = query_expansion.law_candidates[: limits["law_candidates"]]
            primary_identity = law_candidates[0] if law_candidates else None
        elif mode == "promulgated_bill":
            if not promulgation_bridge:
                raise NoResultError("promulgation_bridge is required for promulgated_bill bundles")
            prom_law_nm = string_value(promulgation_bridge.get("prom_law_nm"))
            prom_no = string_value(promulgation_bridge.get("prom_no"))
            promulgation_dt = string_value(promulgation_bridge.get("promulgation_dt"))
            try:
                primary_identity = self.resolve_promulgated_law(
                    prom_law_nm=prom_law_nm,
                    prom_no=prom_no,
                    promulgation_dt=promulgation_dt,
                )
                law_candidates = [primary_identity]
                search_query = primary_identity.name
            except AmbiguousLawError as exc:
                ambiguities.append(
                    Ambiguity(
                        kind=exc.kind or "promulgation_bridge",
                        message=str(exc),
                        candidates=exc.candidates,
                    )
                )
                gaps.append(
                    ContextGap(
                        kind="manual_review_required",
                        reason="The congress-db promulgation bridge matched multiple MOLEG law identities.",
                        query=prom_law_nm,
                        recommended_interface="resolve_promulgated_law",
                    )
                )
            except NoResultError as exc:
                candidate_hits: list[LawHit] = []
                if prom_law_nm:
                    candidate_hits = safe_list(
                        lambda: self.search_laws(
                            prom_law_nm,
                            basis="promulgated",
                            display=max(2, limits["law_candidates"]),
                        ),
                        source_notes,
                        "Promulgation bridge candidate search",
                    )
                law_candidates = dedupe_identities([hit.identity for hit in candidate_hits])
                search_query = prom_law_nm
                if law_candidates:
                    ambiguities.append(
                        Ambiguity(
                            kind="promulgation_bridge_lag",
                            message=(
                                f"{exc}. Law-name candidates exist, but none matched "
                                "`prom_no` and `promulgation_dt` exactly."
                            ),
                            candidates=law_candidates,
                        )
                    )
                    gaps.append(
                        ContextGap(
                            kind="source_lag_or_manual_review_required",
                            reason=(
                                "The congress-db bridge did not exactly resolve in MOLEG. "
                                "This may be source lag or a bridge-field mismatch; do not treat it as proof "
                                "that the bill was not enacted."
                            ),
                            query=prom_law_nm,
                            recommended_interface="resolve_promulgated_law",
                        )
                    )
                else:
                    ambiguities.append(Ambiguity(kind="promulgation_bridge", message=str(exc)))
                    gaps.append(
                        ContextGap(
                            kind="manual_review_required",
                            reason="The congress-db promulgation bridge did not resolve to a MOLEG law identity.",
                            query=prom_law_nm,
                            recommended_interface="congress-db",
                        )
                    )
        elif mode == "statute_review":
            if law_identifier is None:
                raise NoResultError("law_identifier is required for statute_review bundles")
            primary_identity = identity_from_identifier(law_identifier, basis="effective")
            law_candidates = [primary_identity]
            search_query = query or primary_identity.name
        else:
            raise UnsupportedFormatError(f"Unsupported legal context bundle mode: {mode}")

        if primary_identity:
            if articles:
                for article in articles[: limits["articles"]]:
                    try:
                        loaded_articles.append(self.get_article(primary_identity, article))
                    except MolegApiError as exc:
                        source_notes.append(f"Article load skipped for {article}: {exc}")
            else:
                try:
                    law_text = self.get_law(primary_identity)
                    loaded_laws.append(law_text)
                    primary_identity = law_text.identity
                except MolegApiError as exc:
                    source_notes.append(f"Primary law load skipped: {exc}")

            try:
                graph = self.find_delegated_rules(primary_identity)
                loaded_delegations.append(limit_delegation_graph(graph, limits["delegations"]))
            except MolegApiError as exc:
                source_notes.append(f"Delegation lookup skipped: {exc}")

            if mode == "promulgated_bill":
                deferred.append(
                    DeferredLookup(
                        interface="trace_law_history",
                        query=primary_identity.name,
                        reason="Trace amendment history once the relevant article or date range is known.",
                        source_type="law_history",
                        filters={"law_id": primary_identity.law_id},
                    )
                )
                deferred.append(
                    DeferredLookup(
                        interface="compare_law_versions",
                        query=primary_identity.name,
                        reason="Compare before/after text when the bill's affected articles are identified.",
                        source_type="law_diff",
                        filters={"law_id": primary_identity.law_id},
                    )
                )

        if search_query:
            administrative_candidates = safe_list(
                lambda: self.search_administrative_rules(
                    search_query,
                    display=limits["administrative_rules"],
                ),
                source_notes,
                "Administrative-rule search",
            )
            interpretation_candidates = safe_list(
                lambda: self.search_interpretations(
                    search_query,
                    display=limits["interpretations"],
                ),
                source_notes,
                "Interpretation search",
            )
            case_candidates = safe_list(
                lambda: self.search_cases(
                    search_query,
                    display=limits["cases"],
                ),
                source_notes,
                "Case search",
            )
            constitutional_candidates = safe_list(
                lambda: self.search_constitutional_decisions(
                    search_query,
                    display=limits["constitutional_decisions"],
                ),
                source_notes,
                "Constitutional decision search",
            )
            annex_form_limit = limits["annex_forms"]
            law_annex_limit = (annex_form_limit + 1) // 2
            admin_annex_limit = max(1, annex_form_limit - law_annex_limit)
            annex_form_candidates = [
                *safe_list(
                    lambda: self.search_annex_forms(
                        search_query,
                        source="law",
                        search_scope="source",
                        display=law_annex_limit,
                    ),
                    source_notes,
                    "Law annex/form search",
                ),
                *safe_list(
                    lambda: self.search_annex_forms(
                        search_query,
                        source="administrative_rule",
                        search_scope="source",
                        display=admin_annex_limit,
                    ),
                    source_notes,
                    "Administrative-rule annex/form search",
                ),
            ][:annex_form_limit]

        deferred.extend(deferred_from_candidates(interpretation_candidates, "get_interpretation", "interpretation"))
        deferred.extend(deferred_from_candidates(case_candidates, "get_case", "case"))
        deferred.extend(
            deferred_from_candidates(
                constitutional_candidates,
                "get_constitutional_decision",
                "constitutional",
            )
        )

        if search_query:
            gaps.append(
                ContextGap(
                    kind="websearch_required",
                    reason="Use WebSearch for latest social facts, statistics, policy announcements, news, or non-MOLEG background.",
                    query=search_query,
                    recommended_interface="websearch",
                )
            )

        return LegalContextBundle(
            request=request,
            loaded=LoadedContext(
                laws=loaded_laws,
                articles=loaded_articles,
                delegations=loaded_delegations,
                administrative_rules=admin_texts,
                interpretations=interpretation_texts,
                cases=case_texts,
                constitutional_decisions=constitutional_texts,
                histories=histories,
                diffs=diffs,
            ),
            candidates=CandidateContext(
                query_expansion=query_expansion,
                laws=law_candidates,
                administrative_rules=administrative_candidates,
                annex_forms=annex_form_candidates,
                interpretations=interpretation_candidates,
                cases=case_candidates,
                constitutional_decisions=constitutional_candidates,
            ),
            deferred=deferred,
            ambiguities=ambiguities,
            gaps=gaps,
            source_notes=source_notes,
        )

    def _service_rows(
        self,
        target: str,
        params: dict[str, Any],
        raw: dict[str, Any],
        empty_sources: list[str],
    ) -> list[dict[str, Any]]:
        payload = self.source.service(target, params)
        raw[target] = payload
        rows = unwrap_target_rows(payload, target)
        if not rows:
            empty_sources.append(target)
        return rows


def target_for(basis: Basis, kind: str) -> str:
    return TARGETS[basis][kind]


def annex_source_type(source: str) -> str:
    if source in ("law", "statute"):
        return "law"
    if source in ("administrative_rule", "admin_rule"):
        return "administrative_rule"
    raise UnsupportedFormatError(f"Unsupported annex/form source: {source}")


def annex_target_for(source_type: str) -> str:
    try:
        return ANNEX_FORM_TARGETS[source_type]
    except KeyError as exc:
        raise UnsupportedFormatError(f"Unsupported annex/form source: {source_type}") from exc


def annex_search_scope(search_scope: str) -> int:
    try:
        return ANNEX_SEARCH_SCOPES[search_scope]
    except KeyError as exc:
        raise UnsupportedFormatError(f"Unsupported annex/form search scope: {search_scope}") from exc


def annex_type_code(source_type: str, annex_type: str) -> str:
    try:
        return ANNEX_TYPE_CODES[source_type][annex_type]
    except KeyError as exc:
        raise UnsupportedFormatError(
            f"Unsupported annex/form type for {source_type}: {annex_type}"
        ) from exc


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
    return AnnexFormIdentity(
        annex_id=str(identifier),
        title=title or str(identifier),
        source_type=source_type,
        source_target=annex_target_for(source_type),
    )


def identity_from_identifier(identifier: LawIdentity | LawHit | str, *, basis: Basis) -> LawIdentity:
    if isinstance(identifier, LawHit):
        return identifier.identity
    if isinstance(identifier, LawIdentity):
        return identifier
    return LawIdentity(law_id=str(identifier), name=str(identifier), basis=basis)


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


def matches_bridge(
    identity: LawIdentity,
    *,
    prom_no: str | None,
    promulgation_dt: str | None,
) -> bool:
    if prom_no and str(identity.promulgation_number or "") != str(prom_no):
        return False
    if promulgation_dt and compact_date(identity.promulgation_date) != compact_date(promulgation_dt):
        return False
    return True


def history_row_matches_identity(row: dict[str, Any], identity: LawIdentity) -> bool:
    row_name = str(row.get("법령명한글") or row.get("법령명") or "")
    if row_name == identity.name:
        return True

    row_ministry = str(row.get("소관부처명") or row.get("소관부처") or "")
    row_law_type = str(row.get("법령구분명") or row.get("법령종류") or "")
    return bool(
        identity.ministry
        and identity.law_type
        and row_ministry == identity.ministry
        and row_law_type == identity.law_type
    )


def dedupe_identities(identities: list[LawIdentity]) -> list[LawIdentity]:
    seen: set[tuple[str | None, str | None, str, str | None, str | None]] = set()
    unique: list[LawIdentity] = []
    for identity in identities:
        key = (
            identity.law_id,
            identity.mst,
            identity.name,
            identity.promulgation_number,
            identity.promulgation_date,
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(identity)
    return unique


def article_payload_row(raw_article: dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw_article.get("조문"), dict):
        article = raw_article["조문"]
        article_units = article.get("조문단위")
        if isinstance(article_units, list):
            for row in article_units:
                if isinstance(row, dict) and row.get("조문내용"):
                    return row
            for row in article_units:
                if isinstance(row, dict):
                    return row
        if isinstance(article.get("조문단위"), dict):
            return article["조문단위"]
        return article
    if isinstance(raw_article.get("조문단위"), dict):
        return raw_article["조문단위"]
    return raw_article


def maybe_identity(row: Any, *, basis: Basis) -> LawIdentity | None:
    if not isinstance(row, dict):
        return None
    try:
        return normalize_law_identity(row, basis=basis)
    except Exception:
        return None


def administrative_rule_identity_from_identifier(
    identifier: AdministrativeRuleIdentity | AdministrativeRuleHit | str,
) -> AdministrativeRuleIdentity:
    if isinstance(identifier, AdministrativeRuleHit):
        return identifier.identity
    if isinstance(identifier, AdministrativeRuleIdentity):
        return identifier
    text = str(identifier)
    if text.isdigit():
        return AdministrativeRuleIdentity(serial_id=text, name=text)
    return AdministrativeRuleIdentity(serial_id=None, name=text)


def administrative_rule_identity_params(identity: AdministrativeRuleIdentity) -> dict[str, Any]:
    if identity.serial_id:
        return {"ID": identity.serial_id}
    if identity.rule_id:
        return {"LID": identity.rule_id}
    if identity.name:
        return {"LM": identity.name}
    raise NoResultError("Administrative-rule identity has neither ID, LID, nor exact name")


def article_label_for_filter(article: str | int) -> str:
    if isinstance(article, int):
        return f"제{article}조"
    text = str(article)
    if text.startswith("제"):
        return text
    if text.isdigit():
        return f"제{int(text)}조"
    return text


def interpretation_sources_for(source: str, ministry: str | None) -> list[InterpretationSourceSpec]:
    if source == "moleg":
        return [OFFICIAL_INTERPRETATION_SOURCE]
    if source == "ministry":
        return [ministry_interpretation_source(ministry)]
    if source == "all":
        specs = [OFFICIAL_INTERPRETATION_SOURCE]
        if ministry:
            specs.append(ministry_interpretation_source(ministry))
        return specs
    raise UnsupportedFormatError(f"Unsupported interpretation source: {source}")


def ministry_interpretation_source(ministry: str | None) -> InterpretationSourceSpec:
    if not ministry:
        raise NoResultError("ministry is required for ministry interpretation search")
    if ministry in MINISTRY_INTERPRETATION_SOURCES:
        return MINISTRY_INTERPRETATION_SOURCES[ministry]
    for spec in MINISTRY_INTERPRETATION_SOURCES.values():
        if ministry == spec.target:
            return spec
    raise UnsupportedFormatError(f"Unsupported ministry interpretation source: {ministry}")


def interpretation_source_for_identifier(
    identifier: InterpretationIdentity | InterpretationHit | str,
    *,
    source: str | None,
    ministry: str | None,
) -> InterpretationSourceSpec:
    if isinstance(identifier, InterpretationHit):
        return interpretation_source_for_identifier(identifier.identity, source=source, ministry=ministry)
    if isinstance(identifier, InterpretationIdentity):
        if identifier.source_target == OFFICIAL_INTERPRETATION_SOURCE.target:
            return OFFICIAL_INTERPRETATION_SOURCE
        for spec in MINISTRY_INTERPRETATION_SOURCES.values():
            if spec.target == identifier.source_target:
                return spec
        return InterpretationSourceSpec(
            source_type=identifier.source_type,
            target=identifier.source_target,
            ministry=identifier.ministry,
        )
    return interpretation_sources_for(source or "moleg", ministry)[0]


def interpretation_identity_from_identifier(
    identifier: InterpretationIdentity | InterpretationHit | str,
    spec: InterpretationSourceSpec,
) -> InterpretationIdentity:
    if isinstance(identifier, InterpretationHit):
        return identifier.identity
    if isinstance(identifier, InterpretationIdentity):
        return identifier
    text = str(identifier)
    if not text.isdigit():
        raise NoResultError("Interpretation detail lookup requires a source interpretation ID")
    return InterpretationIdentity(
        interpretation_id=text,
        title=text,
        source_type=spec.source_type,
        source_target=spec.target,
        ministry=spec.ministry,
    )


def interpretation_identity_params(identity: InterpretationIdentity) -> dict[str, Any]:
    if identity.interpretation_id:
        return {"ID": identity.interpretation_id}
    raise NoResultError("Interpretation identity has no source interpretation ID")


def court_filter_code(court: str) -> str | None:
    if court == "all":
        return None
    if court == "supreme":
        return "400201"
    if court == "lower":
        return "400202"
    raise UnsupportedFormatError(f"Unsupported court filter: {court}")


def judicial_decision_identity_from_identifier(
    identifier: JudicialDecisionIdentity | JudicialDecisionHit | str,
    *,
    source_type: str,
    source_target: str,
) -> JudicialDecisionIdentity:
    if isinstance(identifier, JudicialDecisionHit):
        return identifier.identity
    if isinstance(identifier, JudicialDecisionIdentity):
        if identifier.source_target != source_target:
            raise UnsupportedFormatError(
                f"{identifier.source_target} identity cannot be loaded through {source_target}"
            )
        return identifier
    text = str(identifier)
    if not text.isdigit():
        raise NoResultError("Judicial decision detail lookup requires a source decision ID")
    return JudicialDecisionIdentity(
        decision_id=text,
        title=text,
        source_type=source_type,
        source_target=source_target,
    )


def judicial_decision_identity_params(identity: JudicialDecisionIdentity) -> dict[str, Any]:
    if identity.decision_id:
        return {"ID": identity.decision_id}
    raise NoResultError("Judicial decision identity has no source decision ID")


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


def build_follow_up_searches(
    query: str,
    *,
    law_candidates: list[LawIdentity],
    term_candidates: list[LegalTermCandidate],
    related_laws: list[LegalLawCandidate],
    include_websearch_hint: bool,
) -> list[FollowUpSearch]:
    searches: list[FollowUpSearch] = [
        FollowUpSearch(
            interface="search_laws",
            query=query,
            reason="Find current-law candidates before loading legal text.",
            source_type="law",
        ),
        FollowUpSearch(
            interface="search_administrative_rules",
            query=query,
            reason="Check practical execution criteria in notices, directives, and established rules.",
            source_type="administrative_rule",
        ),
        FollowUpSearch(
            interface="search_annex_forms",
            query=query,
            reason="Check attached tables, thresholds, amounts, criteria, and forms that may carry operative details.",
            source_type="annex_form",
            filters={"sources": ["law", "administrative_rule"], "search_scope": "source"},
        ),
        FollowUpSearch(
            interface="search_interpretations",
            query=query,
            reason="Check MOLEG and ministry interpretation constraints.",
            source_type="interpretation",
        ),
        FollowUpSearch(
            interface="search_cases",
            query=query,
            reason="Check judicial interpretation and limits.",
            source_type="case",
        ),
        FollowUpSearch(
            interface="search_constitutional_decisions",
            query=query,
            reason="Check constitutional-risk context.",
            source_type="constitutional",
        ),
    ]

    for identity in law_candidates[:3]:
        searches.append(
            FollowUpSearch(
                interface="get_law",
                query=identity.name,
                reason="Load the current effective text for a candidate law.",
                source_type="law",
                filters={"law_id": identity.law_id, "basis": "effective"},
            )
        )
    for term in term_candidates[:5]:
        searches.append(
            FollowUpSearch(
                interface="search_laws",
                query=term.term,
                reason="Use an expanded legal or everyday term as a law-search candidate.",
                source_type=term.source_type,
            )
        )
    for law in related_laws[:5]:
        searches.append(
            FollowUpSearch(
                interface="search_laws" if law.source_type == "law" else "search_administrative_rules",
                query=law.name,
                reason="Follow a related law candidate discovered by query expansion.",
                source_type=law.source_type,
                filters={"article": law.article} if law.article else {},
            )
        )
    if include_websearch_hint:
        searches.append(
            FollowUpSearch(
                interface="websearch",
                query=query,
                reason="Use for latest social facts, statistics, news, policy announcements, and non-MOLEG background.",
                source_type="web",
            )
        )
    return searches


def bundle_limits(budget: str) -> dict[str, int]:
    try:
        return BUNDLE_BUDGETS[budget]
    except KeyError as exc:
        raise UnsupportedFormatError(f"Unsupported legal context bundle budget: {budget}") from exc


def string_value(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def safe_list(fn: Any, source_notes: list[str], label: str) -> list[Any]:
    try:
        return fn()
    except MolegApiError as exc:
        source_notes.append(f"{label} skipped: {exc}")
        return []


def limit_delegation_graph(graph: DelegationGraph, limit: int) -> DelegationGraph:
    return DelegationGraph(identity=graph.identity, rules=graph.rules[:limit], raw=graph.raw)


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
        )
        if not title and not source_id:
            continue
        deferred.append(
            DeferredLookup(
                interface=interface,
                query=str(title or source_id),
                reason="Load full text only if Claude needs this candidate after ranking the bundle.",
                source_type=getattr(identity, "source_type", source_type),
                filters={"id": source_id} if source_id else {},
            )
        )
    return deferred
