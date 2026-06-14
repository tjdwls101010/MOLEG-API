"""Deep law interfaces for the first MOLEG-API vertical slice."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .errors import AmbiguousLawError, NoResultError, UnsupportedFormatError
from .models import (
    AdministrativeRuleHit,
    AdministrativeRuleIdentity,
    AdministrativeRuleText,
    ArticleText,
    Basis,
    DelegationGraph,
    InterpretationHit,
    InterpretationIdentity,
    InterpretationText,
    JudicialDecisionHit,
    JudicialDecisionIdentity,
    JudicialDecisionText,
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
    normalize_article,
    normalize_delegated_rules,
    normalize_diff_changes,
    normalize_history_events,
    normalize_interpretation_identity,
    normalize_interpretation_text,
    normalize_judicial_decision_identity,
    normalize_judicial_decision_text,
    normalize_law_identity,
    unwrap_search_administrative_rules,
    unwrap_search_interpretations,
    unwrap_search_judicial_decisions,
    unwrap_search_laws,
    unwrap_service_payload,
)
from .source import LawGoKrClient, MolegSource


TARGETS: dict[Basis, dict[str, str]] = {
    "effective": {"list": "eflaw", "detail": "eflaw", "article": "eflawjosub"},
    "promulgated": {"list": "law", "detail": "law", "article": "lawjosub"},
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
            raise AmbiguousLawError(f"Promulgation bridge matched multiple laws: {names}")
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
        identity_hint = identity_from_identifier(identifier, basis=basis)
        target = target_for(basis, "detail")
        params = identity_params(identity_hint, as_of=as_of, basis=basis)
        if articles:
            params["JO"] = format_article_jo(articles[0])

        payload = self.source.service(target, params)
        raw_law = unwrap_service_payload(payload, target)
        identity = normalize_law_identity(raw_law, basis=basis)
        law_articles = extract_articles(raw_law, identity)
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
            raise UnsupportedFormatError(
                "Full law history uses the HTML-only lsHistory source; pass article or date_range for JSON change history"
            )

        events = normalize_history_events(payload, identity)
        if not events:
            raise NoResultError("No law history events found")
        return LawHistory(identity=identity, events=events, raw=payload)

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


def target_for(basis: Basis, kind: str) -> str:
    return TARGETS[basis][kind]


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
