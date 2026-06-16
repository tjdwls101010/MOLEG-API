"""Deep law interfaces for the first MOLEG-API vertical slice."""

from __future__ import annotations

from dataclasses import dataclass, replace
import re
from typing import Any

from .errors import AmbiguousLawError, MolegApiError, NoResultError, ParseFailureError, UnsupportedFormatError
from .models import (
    AdministrativeRuleHit,
    AdministrativeRuleIdentity,
    AdministrativeRuleText,
    Ambiguity,
    AnnexFormSource,
    AnnexFormHit,
    AnnexFormIdentity,
    AnnexFormText,
    AnnexSearchScope,
    AnnexType,
    ArticleText,
    Basis,
    BundleBudget,
    BundleMode,
    BundleRequest,
    CandidateContext,
    CaseCourt,
    ContextGap,
    DeferredLookup,
    DelegationGraph,
    FollowUpSearch,
    HistoryEvent,
    InterpretationHit,
    InterpretationIdentity,
    InterpretationSearchSource,
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
    LawStructure,
    LawText,
    StructuredTableData,
)
from .normalization import (
    compact_date,
    compact_promulgation_number,
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
    normalize_law_structure,
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

BUNDLE_EAGER_DETAIL_LIMITS: dict[str, dict[str, int]] = {
    "minimal": {
        "interpretations": 0,
        "cases": 0,
        "constitutional_decisions": 0,
    },
    "standard": {
        "interpretations": 1,
        "cases": 1,
        "constitutional_decisions": 1,
    },
    "broad": {
        "interpretations": 2,
        "cases": 2,
        "constitutional_decisions": 2,
    },
}

BUNDLE_EAGER_TEXT_CHAR_LIMITS = {
    "minimal": 0,
    "standard": 30_000,
    "broad": 80_000,
}

BUNDLE_LEGAL_MEANING_KEYWORDS = (
    "의미",
    "뜻",
    "해석",
    "법령해석",
    "어떻게 보아야",
)

BUNDLE_APPLICATION_KEYWORDS = (
    "적용",
    "요건",
    "조건",
    "판례",
    "사례",
    "분쟁",
    "책임",
)

BUNDLE_CONSTITUTIONAL_KEYWORDS = (
    "위헌",
    "헌법",
    "기본권",
    "평등",
    "과잉금지원칙",
    "비례",
    "표현의 자유",
    "적법",
    "정당성",
)

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

BASIS_VALUES = ("effective", "promulgated")
ANNEX_SOURCE_VALUES = ("law", "administrative_rule")
ANNEX_SEARCH_SCOPE_VALUES = ("title", "source", "body")
INTERPRETATION_SOURCE_VALUES = ("moleg", "ministry", "all", "all_ministries")
COURT_VALUES = ("all", "supreme", "lower")
BUNDLE_MODE_VALUES = ("question", "promulgated_bill", "statute_review")
BUNDLE_BUDGET_VALUES = ("minimal", "standard", "broad")


@dataclass(frozen=True)
class InterpretationSourceSpec:
    source_type: str
    target: str
    ministry: str | None = None
    can_get: bool = True


@dataclass(frozen=True)
class InstitutionalStatuteResolution:
    identifier: str
    identity: LawIdentity | None
    candidates: list[LawIdentity]
    error_kind: str | None = None
    message: str | None = None


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
    """Task-level MOLEG-API facade for legislative-expert callers.

    MOLEG source targets, identifier quirks, article-number formatting, and
    authority labels stay inside this module. Callers choose legal tasks.

    Method selection:
    - Start with `search_laws` for free-text statute candidates; use
      `resolve_promulgated_law` only when congress-db provides promulgation
      bridge fields such as `prom_law_nm`, `prom_no`, and `promulgation_dt`.
    - Use `get_law` for statute text and `get_article` for one precise
      article. Prefer effective basis for current-force questions.
    - Use `trace_law_history` for amendment chronology and
      `compare_law_versions` for the MOLEG before/after text surface; current
      arbitrary two-date comparison is not modeled here.
    - Use `find_delegated_rules`, `search_administrative_rules`, and
      annex/form loaders when statute text may omit delegated criteria,
      notices, attached tables, thresholds, amounts, or forms.
    - Use `search_interpretations` for MOLEG/ministry interpretations,
      `search_cases` for ordinary judicial decisions, and
      `search_constitutional_decisions` for Constitutional Court decisions;
      these are separate authority types, not flags on one search.
    - Use `expand_legal_query` for search planning and
      `load_legal_context_bundle` for a staged first pass over a broad
      question. Both return source-loading context, not legal conclusions.
    """

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
        """Search law.go.kr for statute identity candidates.

        Use when: the skill has a law name, keyword, or expanded search term
        and needs candidate current or promulgated statute identities.
        Returns: a list of `LawHit` values carrying normalized `LawIdentity`
        objects plus the source row; an empty list means no source rows.
        Raises: source adapter errors or parse errors if a returned row cannot
        be normalized; no-result is represented as an empty list.
        Related: use `resolve_promulgated_law` for congress-db bridge fields
        and `expand_legal_query` when the query itself needs planning.
        """
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
        """Resolve a congress-db promulgation bridge to one law identity.

        Use when: a National Assembly bill row has reached the promulgation
        side and provides bridge fields such as law name, promulgation number,
        or promulgation date.
        Returns: one normalized `LawIdentity` on the promulgated basis.
        Raises: `NoResultError` when required bridge fields are missing or no
        source row matches; `AmbiguousLawError` when several identities remain.
        Related: `search_laws(basis="promulgated")` is free-text discovery;
        this method is the stricter bridge resolver for enacted bill facts.
        """
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
        """Load normalized statute text for one law identity.

        Use when: the skill already has a plausible statute identity and needs
        the effective or promulgated text behind it. Pass a `LawIdentity` or
        `LawHit` when possible; a bare string should be a source identifier.
        Returns: `LawText` with a normalized identity and extracted articles,
        optionally preserving raw metadata for audit.
        Raises: `NoResultError` for unusable identifiers and source/parse
        errors when law.go.kr cannot provide normalizable statute text.
        Related: use `get_article` for precise article lookup and
        `search_laws` first when the identity is still uncertain.
        """
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
        """Load one article by human article notation.

        Use when: the skill needs a specific provision such as `제10조의2`
        without formatting MOLEG's six-digit `JO` value itself.
        Returns: `ArticleText` with the article label, title, text, effective
        date when available, and normalized source identity.
        Raises: `NoResultError` when the article text is absent, plus source or
        parse errors for invalid source payloads.
        Related: use `get_law` for whole-statute context and
        `trace_law_history(article=...)` for article-level history events.
        """
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
        promulgation_bridge: dict[tuple[Any, Any, Any], Any] | None = None,
    ) -> LawHistory:
        """Load amendment-history events for a statute or article.

        Use when: the skill needs chronology, amendment reasons, promulgation
        numbers, or effective dates rather than the current text itself.
        Returns: `LawHistory` with normalized `HistoryEvent` records; full-law
        history uses the HTML-only `lsHistory` list parser.
        Raises: `NoResultError` when no matching events exist; parse/source
        errors surface when the source shape is unusable.
        Related: use `compare_law_versions` for before/after text rows and
        `resolve_promulgated_law` before history when starting from a bill.
        """
        identity = identity_from_identifier(law_identifier, basis="effective")
        bill_id_map = normalize_history_bill_id_map(promulgation_bridge)
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

        events = normalize_history_events(payload, identity, bill_id_map=bill_id_map)
        if article is not None:
            events = self._populate_article_history_text(identity, article, events)
        if not events:
            raise NoResultError("No law history events found")
        return LawHistory(identity=identity, events=events, raw=payload)

    def _populate_article_history_text(
        self,
        identity: LawIdentity,
        article: str | int,
        events: list[HistoryEvent],
    ) -> list[HistoryEvent]:
        article_texts_by_lookup: dict[tuple[str, str], str | None] = {}
        populated: list[HistoryEvent] = []
        for event in events:
            if event.article_text:
                populated.append(event)
                continue
            as_of = event.effective_date or event.changed_date
            if not as_of:
                populated.append(event)
                continue
            event_article = article_label_for_filter(article)
            lookup_key = (str(event_article), as_of)
            if lookup_key not in article_texts_by_lookup:
                try:
                    article_snapshot = self.get_article(identity, event_article, as_of=as_of)
                    article_texts_by_lookup[lookup_key] = article_snapshot.text
                except MolegApiError:
                    article_texts_by_lookup[lookup_key] = None
            populated.append(replace(event, article_text=article_texts_by_lookup[lookup_key]))
        return populated

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
        """Load MOLEG before/after text rows for one statute.

        Use when: the skill needs the source `oldAndNew` comparison surface for
        a candidate law or article. The current implementation rejects arbitrary
        before/after dates because the source does not support that window.
        Returns: `LawDiff` with before and after identities when the source
        exposes them and normalized changed article text.
        Raises: `UnsupportedFormatError` for arbitrary date-window arguments;
        `NoResultError` when the source returns no comparable changes, plus
        source/parse errors for unusable payloads.
        Related: use `trace_law_history` to choose dates or amendment events;
        use `get_law`/`get_article` for current text.
        """
        if before is not None or after is not None:
            raise UnsupportedFormatError(
                "Arbitrary two-date comparison is not supported by law.go.kr oldAndNew; "
                "call compare_law_versions() without before/after to load the source-supplied "
                "before/after pair."
            )

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
            raw=raw_diff,
        )

    def find_delegated_rules(
        self,
        law_identifier: LawIdentity | LawHit | str,
        *,
        article: str | int | None = None,
    ) -> DelegationGraph:
        """Find delegated lower-rule context for a statute.

        Use when: statute text may delegate details to enforcement decrees,
        enforcement rules, notices, or administrative rules.
        Returns: a `DelegationGraph` rooted at the law identity with normalized
        delegated-rule rows, optionally filtered by source article.
        Raises: `NoResultError` when no delegated rows remain after filtering,
        plus source/parse errors for unusable source data.
        Related: use `search_administrative_rules` and
        `get_administrative_rule` to search or load the lower rules themselves.
        """
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

    def get_law_structure(
        self,
        law_identifier: LawIdentity | LawHit | str,
        *,
        depth: int = 0,
    ) -> LawStructure:
        """Load the MOLEG `lsStmd` structural hierarchy for one law.

        Use when: the skill needs the broader 법률 -> 시행령 / 시행규칙 /
        행정규칙 hierarchy around a statute, not article-level delegation text.
        Returns: `LawStructure` with normalized law and administrative-rule
        nodes, preserving nested children up to the requested depth.
        Raises: `UnsupportedFormatError` for negative depth, `NoResultError`
        for an empty hierarchy, and parse/source errors for unusable payloads.
        Related: use `find_delegated_rules` for article-level delegation
        relationships; `lsStmd` does not provide source-article links.
        """
        if depth < 0:
            raise UnsupportedFormatError("Law structure depth must be 0 or greater")
        identity = identity_from_identifier(law_identifier, basis="effective")
        params = identity_params(identity, as_of=None, basis="effective")
        payload = self.source.service("lsStmd", params)
        raw_structure = unwrap_service_payload(payload, "lsStmd")
        structure = normalize_law_structure(raw_structure, max_depth=depth)
        if not structure.instruments:
            raise NoResultError("No law structure instruments found")
        return structure

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
        """Search notices, directives, established rules, and other admin rules.

        Use when: delegated or practical execution criteria may live outside
        statute text, especially in ministry-level administrative rules.
        Returns: a list of `AdministrativeRuleHit` values with normalized
        serial ID, rule ID, issuing/effective dates, ministry, and status.
        Raises: source adapter or parse errors; no-result is an empty list.
        Related: use `find_delegated_rules` from a known statute and
        `get_administrative_rule` to load a selected rule body.
        """
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
        source: AnnexFormSource = "law",
        search_scope: AnnexSearchScope = "source",
        annex_type: AnnexType | None = None,
        ministry: str | None = None,
        display: int = 20,
    ) -> list[AnnexFormHit]:
        """Search statute or administrative-rule annex/form candidates.

        Use when: operative content may be in 별표ㆍ서식 material such as
        tables, thresholds, criteria, amounts, or required forms.
        Returns: a list of `AnnexFormHit` values with source law/rule identity,
        annex title/number/type, dates, ministry, and file/detail links.
        Raises: `UnsupportedFormatError` for unsupported source, scope, or
        annex type values; source/parse errors may also propagate.
        Related: call `get_annex_form_body` for a selected candidate before
        treating attached material as inspected.
        """
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
        source: AnnexFormSource = "law",
        title: str | None = None,
        include_metadata: bool = True,
        attempt_structuring: bool = True,
    ) -> AnnexFormText:
        """Load text for one selected law or administrative-rule annex/form.

        Use when: an annex/form candidate may carry operative criteria and the
        skill needs the body text before citing or reasoning from it.
        Returns: `AnnexFormText` with text/plain content, source identity,
        extraction method, confidence, and optional metadata.
        Raises: `NoResultError` when the identity lacks a source ID or returns
        empty text; `UnsupportedFormatError` for unsupported source targets.
        Related: call `search_annex_forms` first; direct HWP/PDF parsing is
        outside this interface.
        """
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
        structured_data = (
            structure_annex_form_text(text, identity)
            if attempt_structuring and annex_form_is_table_like(identity)
            else None
        )
        return AnnexFormText(
            identity=identity,
            text=text,
            file_type="text/plain",
            extraction_method=endpoint,
            extraction_confidence="high",
            structured_data=structured_data,
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
        """Load one administrative-rule body by identity, ID, or exact name.

        Use when: the skill selected a notice, directive, established rule, or
        similar administrative rule and needs inspectable text.
        Returns: `AdministrativeRuleText` with normalized identity, full joined
        text, structured articles when available, and optional raw metadata.
        Raises: `NoResultError` when the identity cannot locate text or article
        filtering removes all rows; source/parse errors may also propagate.
        Related: use `search_administrative_rules` for discovery and
        `find_delegated_rules` when starting from a statute.
        """
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
        source: InterpretationSearchSource = "moleg",
        ministry: str | None = None,
        search_body: bool = False,
        interpreted_on: str | None = None,
        display: int = 20,
    ) -> list[InterpretationHit]:
        """Search MOLEG and ministry first-instance legal interpretations.

        Use when: the skill needs official or ministry interpretation context
        about how a statute is applied, distinct from court decisions. Use
        `source="all"` for MOLEG plus one specified ministry; use
        `source="all_ministries"` only for deep institutional analysis that
        justifies registry-wide fan-out.
        Returns: `InterpretationHit` rows with normalized source authority
        labels, ministry where relevant, case number, title, and date.
        Raises: `NoResultError` when ministry search lacks a ministry;
        `UnsupportedFormatError` for unsupported source/ministry values.
        Related: use `search_cases` for ordinary judicial decisions and
        `search_constitutional_decisions` for Constitutional Court decisions.
        """
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
        source: InterpretationSearchSource | None = None,
        ministry: str | None = None,
        include_metadata: bool = True,
    ) -> InterpretationText:
        """Load one MOLEG or ministry interpretation detail.

        Use when: a selected interpretation needs question, answer, reason, and
        related-law text before the skill cites or reasons from it.
        Returns: `InterpretationText` with preserved source authority labels,
        agencies, case number, interpretation date, and optional raw metadata.
        Raises: `NoResultError` for missing source IDs and
        `UnsupportedFormatError` for sources without cataloged detail support.
        Related: call `search_interpretations` first; use judicial loaders for
        cases or constitutional decisions, not this method.
        """
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
                referenced_articles=text.referenced_articles,
                text=text.text,
                raw={},
            )
        return text

    def search_cases(
        self,
        query: str,
        *,
        court: CaseCourt = "all",
        court_name: str | None = None,
        search_body: bool = False,
        decided_on: str | None = None,
        case_number: str | None = None,
        display: int = 20,
    ) -> list[JudicialDecisionHit]:
        """Search ordinary court cases through the MOLEG case source.

        Use when: the skill needs Supreme Court or lower-court precedent,
        holdings, or judicial limits for a statute or issue.
        Returns: `JudicialDecisionHit` rows labeled as `case` with decision ID,
        title, court, case number, decision date, and summary metadata.
        Raises: `UnsupportedFormatError` for unsupported court filters; source
        or parse errors may also propagate. Empty search results return [].
        Related: use `get_case` for detail and
        `search_constitutional_decisions` for Constitutional Court authority.
        """
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
        """Load one ordinary court case detail.

        Use when: a selected case must be inspected for holdings, summary, full
        text, referenced statutes, or referenced cases.
        Returns: `JudicialDecisionText` labeled as `case`, optionally without
        raw metadata when the caller is budgeting context.
        Raises: `NoResultError` for missing/non-numeric source IDs and
        `UnsupportedFormatError` if a non-case identity is passed here.
        Related: call `search_cases` first; use constitutional loaders for
        `detc` Constitutional Court decisions.
        """
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
            referenced_articles=text.referenced_articles,
            reviewed_articles=text.reviewed_articles,
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
        """Search Constitutional Court decisions.

        Use when: the skill needs constitutional-risk context, reviewed
        statutes, holdings, or constitutional reasoning distinct from ordinary
        court precedent.
        Returns: `JudicialDecisionHit` rows labeled as `constitutional` with
        decision ID, case number, decision date, title, and summary metadata.
        Raises: source adapter or parse errors; no-result is an empty list.
        Related: use `get_constitutional_decision` for detail and
        `search_cases` for ordinary Supreme Court/lower-court cases.
        """
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
        """Load one Constitutional Court decision detail.

        Use when: a selected constitutional decision needs holdings, summary,
        full text, reviewed statutes, or referenced authority.
        Returns: `JudicialDecisionText` labeled as `constitutional`, optionally
        without raw metadata for context budgeting.
        Raises: `NoResultError` for missing/non-numeric source IDs and
        `UnsupportedFormatError` if an ordinary case identity is passed here.
        Related: call `search_constitutional_decisions` first; use `get_case`
        for ordinary judicial decisions.
        """
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
            referenced_articles=text.referenced_articles,
            reviewed_articles=text.reviewed_articles,
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
        """Build legal search-planning context for a broad query.

        Use when: the user's wording may need legal terms, everyday terms,
        related articles/laws, AI-search hints, or WebSearch handoff guidance
        before loading primary source text.
        Returns: `LegalQueryExpansion` with candidate laws, terms, related
        articles/laws, follow-up search recommendations, and empty-source notes.
        Raises: `NoResultError` for blank queries; source or parse errors may
        propagate from the planning sources.
        Related: this is not legal authority. Use returned follow-ups with
        `get_law`, `get_article`, interpretation, case, or annex loaders.
        """
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

    def find_comparable_mechanisms(
        self,
        concept: str,
        *,
        display: int = 5,
    ) -> list[LawIdentity]:
        """Find source-backed law candidates with similar legal mechanisms.

        Use when: the skill is doing legislative design or comparative 제도
        planning for a concept such as 과징금, 인허가, authorization, or 신고제.
        Returns: bounded `LawIdentity` candidates with source endpoints and
        article anchors preserved in `raw_keys` for later selective loading.
        Raises: `NoResultError` for blank concepts or when no comparable source
        candidates are found; source/parse errors may also propagate.
        Related: use `expand_legal_query` for broader search planning and
        `get_law`/`get_article` before citing or concluding mechanisms match.
        """
        concept = concept.strip()
        if not concept:
            raise NoResultError("concept is required for comparable mechanism discovery")

        ai_search_payload = self.source.search(
            "aiSearch",
            {"query": concept, "display": display, "search": 0},
        )
        ai_related_payload = self.source.search(
            "aiRltLs",
            {"query": concept, "search": 0},
        )
        term_article_payload = self.source.service("lstrmRltJo", {"query": concept})

        candidates = comparable_mechanism_identities(
            concept,
            [
                *laws_from_rows(unwrap_target_rows(ai_search_payload, "aiSearch"), source_target="aiSearch"),
                *laws_from_rows(unwrap_target_rows(ai_related_payload, "aiRltLs"), source_target="aiRltLs"),
                *laws_from_rows(unwrap_target_rows(term_article_payload, "lstrmRltJo"), source_target="lstrmRltJo"),
            ],
            display=display,
        )
        if not candidates:
            raise NoResultError(f"No comparable mechanisms found for concept: {concept}")
        return candidates

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

    def load_institutional_system(
        self,
        statute_identifiers: list[str | LawIdentity | LawHit],
        *,
        articles: list[str | int] | None = None,
        budget: str = "standard",
    ) -> LegalContextBundle:
        """Load one explicit multi-statute institutional system.

        Use when: the skill has already selected the statute set for a 제도 and
        needs one staged source bundle across those statutes.
        Returns: `LegalContextBundle` with `request.mode="institutional_system"`,
        `request.statute_ids`, loaded law/article text, law structures,
        delegation graphs, candidates, deferred lookups, ambiguities, and gaps.
        Raises: `NoResultError` for an empty statute set and budget validation
        errors from the normal bundle limits; per-statute failures are recorded
        in the returned bundle instead of aborting the whole load.
        Related: use `search_laws` or `expand_legal_query` before this method
        when the statute set itself is uncertain.
        """
        if not statute_identifiers:
            raise NoResultError("statute_identifiers is required for institutional-system bundles")

        limits = bundle_limits(budget)
        request = BundleRequest(
            query=None,
            mode="institutional_system",
            budget=budget,
            articles=list(articles or []),
            statute_ids=[statute_identifier_label(identifier) for identifier in statute_identifiers],
        )
        source_notes: list[str] = [
            "Institutional-system bundle is staged source context, not a legal conclusion."
        ]
        ambiguities: list[Ambiguity] = []
        gaps: list[ContextGap] = []
        deferred: list[DeferredLookup] = []
        loaded_laws: list[LawText] = []
        loaded_articles: list[ArticleText] = []
        loaded_delegations: list[DelegationGraph] = []
        law_structures: list[LawStructure] = []
        law_candidates: list[LawIdentity] = []
        administrative_candidates: list[AdministrativeRuleHit] = []
        annex_form_candidates: list[AnnexFormHit] = []
        interpretation_candidates: list[InterpretationHit] = []
        case_candidates: list[JudicialDecisionHit] = []
        constitutional_candidates: list[JudicialDecisionHit] = []

        for statute_identifier in statute_identifiers:
            resolution = self._resolve_institutional_statute(
                statute_identifier,
                display=max(2, limits["law_candidates"]),
            )
            law_candidates.extend(resolution.candidates)
            if resolution.identity is None:
                if resolution.error_kind == "ambiguous":
                    ambiguities.append(
                        Ambiguity(
                            kind="statute_identity",
                            message=resolution.message
                            or f"Statute identifier is ambiguous: {resolution.identifier}",
                            candidates=resolution.candidates,
                        )
                    )
                else:
                    source_notes.append(
                        resolution.message or f"Statute '{resolution.identifier}' was not found"
                    )
                gaps.append(
                    ContextGap(
                        kind="manual_review_required",
                        reason="A statute identifier could not be resolved to one MOLEG law identity.",
                        query=resolution.identifier,
                        recommended_interface="search_laws",
                    )
                )
                deferred.append(
                    DeferredLookup(
                        interface="search_laws",
                        query=resolution.identifier,
                        reason="Resolve the statute identity before loading this part of the institutional system.",
                        source_type="law",
                    )
                )
                continue

            identity = resolution.identity
            if articles:
                for article in articles[: limits["articles"]]:
                    try:
                        loaded_articles.append(self.get_article(identity, article))
                    except MolegApiError as exc:
                        source_notes.append(f"Article load skipped for {identity.name} {article}: {exc}")
            else:
                try:
                    law_text = self.get_law(identity)
                    loaded_laws.append(law_text)
                    identity = law_text.identity
                    law_candidates.append(identity)
                except MolegApiError as exc:
                    source_notes.append(f"Law load skipped for {identity.name}: {exc}")

            try:
                law_structures.append(self.get_law_structure(identity, depth=1))
            except MolegApiError as exc:
                source_notes.append(f"Law-structure lookup skipped for {identity.name}: {exc}")

            try:
                graph = self.find_delegated_rules(identity)
                loaded_delegations.append(limit_delegation_graph(graph, limits["delegations"]))
            except NoResultError:
                loaded_delegations.append(DelegationGraph(identity=identity, rules=[], raw={}))
            except MolegApiError as exc:
                source_notes.append(f"Delegation lookup skipped for {identity.name}: {exc}")

            administrative_candidates.extend(
                safe_list(
                    lambda identity=identity: self.search_administrative_rules(
                        identity.name,
                        display=limits["administrative_rules"],
                    ),
                    source_notes,
                    f"Administrative-rule search for {identity.name}",
                )
            )
            interpretation_candidates.extend(
                safe_list(
                    lambda identity=identity: self.search_interpretations(
                        identity.name,
                        display=limits["interpretations"],
                    ),
                    source_notes,
                    f"Interpretation search for {identity.name}",
                )
            )
            case_candidates.extend(
                safe_list(
                    lambda identity=identity: self.search_cases(
                        identity.name,
                        display=limits["cases"],
                    ),
                    source_notes,
                    f"Case search for {identity.name}",
                )
            )
            constitutional_candidates.extend(
                safe_list(
                    lambda identity=identity: self.search_constitutional_decisions(
                        identity.name,
                        display=limits["constitutional_decisions"],
                    ),
                    source_notes,
                    f"Constitutional decision search for {identity.name}",
                )
            )

            annex_form_limit = limits["annex_forms"]
            law_annex_limit = (annex_form_limit + 1) // 2
            admin_annex_limit = max(1, annex_form_limit - law_annex_limit)
            annex_form_candidates.extend(
                [
                    *safe_list(
                        lambda identity=identity: self.search_annex_forms(
                            identity.name,
                            source="law",
                            search_scope="source",
                            display=law_annex_limit,
                        ),
                        source_notes,
                        f"Law annex/form search for {identity.name}",
                    ),
                    *safe_list(
                        lambda identity=identity: self.search_annex_forms(
                            identity.name,
                            source="administrative_rule",
                            search_scope="source",
                            display=admin_annex_limit,
                        ),
                        source_notes,
                        f"Administrative-rule annex/form search for {identity.name}",
                    ),
                ]
            )
            gaps.append(
                ContextGap(
                    kind="websearch_required",
                    reason="Use WebSearch for latest social facts, statistics, policy announcements, news, or non-MOLEG background.",
                    query=identity.name,
                    recommended_interface="websearch",
                )
            )

        deferred.extend(
            deferred_from_candidates(administrative_candidates, "get_administrative_rule", "administrative_rule")
        )
        deferred.extend(deferred_from_candidates(interpretation_candidates, "get_interpretation", "interpretation"))
        deferred.extend(deferred_from_candidates(case_candidates, "get_case", "case"))
        deferred.extend(
            deferred_from_candidates(
                constitutional_candidates,
                "get_constitutional_decision",
                "constitutional",
            )
        )

        return LegalContextBundle(
            request=request,
            loaded=LoadedContext(
                laws=loaded_laws,
                articles=loaded_articles,
                delegations=loaded_delegations,
                law_structures=law_structures,
            ),
            candidates=CandidateContext(
                laws=dedupe_identities(law_candidates),
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

    def _resolve_institutional_statute(
        self,
        identifier: str | LawIdentity | LawHit,
        *,
        display: int,
    ) -> InstitutionalStatuteResolution:
        label = statute_identifier_label(identifier)
        if isinstance(identifier, LawHit):
            return InstitutionalStatuteResolution(label, identifier.identity, [identifier.identity])
        if isinstance(identifier, LawIdentity):
            return InstitutionalStatuteResolution(label, identifier, [identifier])
        text = label.strip()
        if not text:
            return InstitutionalStatuteResolution(
                label,
                None,
                [],
                error_kind="no_result",
                message="Blank statute identifier cannot be resolved",
            )
        if text.isdigit():
            identity = LawIdentity(law_id=text, name=text, basis="effective")
            return InstitutionalStatuteResolution(label, identity, [identity])

        hits = self.search_laws(text, display=display)
        identities = dedupe_identities([hit.identity for hit in hits])
        if not identities:
            return InstitutionalStatuteResolution(
                label,
                None,
                [],
                error_kind="no_result",
                message=f"Statute '{text}' was not found",
            )
        exact = [identity for identity in identities if identity.name == text]
        if len(exact) == 1:
            return InstitutionalStatuteResolution(label, exact[0], identities)
        if len(exact) > 1:
            return InstitutionalStatuteResolution(
                label,
                None,
                exact,
                error_kind="ambiguous",
                message=f"Statute identifier '{text}' matched multiple exact law identities",
            )
        if len(identities) == 1:
            return InstitutionalStatuteResolution(label, identities[0], identities)
        return InstitutionalStatuteResolution(
            label,
            None,
            identities,
            error_kind="ambiguous",
            message=f"Statute identifier '{text}' matched multiple law identities",
        )

    def load_legal_context_bundle(
        self,
        query: str | None = None,
        *,
        promulgation_bridge: dict[str, Any] | None = None,
        law_identifier: LawIdentity | LawHit | str | None = None,
        articles: list[str | int] | None = None,
        mode: BundleMode = "question",
        budget: BundleBudget = "standard",
    ) -> LegalContextBundle:
        """Load a staged legal context bundle for Claude inspection.

        Use when: the question is broad, under-specified, or begins from a
        statute/bill anchor and the skill needs one bounded first pass over
        likely MOLEG sources.
        Returns: `LegalContextBundle` with loaded primary law/article/delegation
        context, bounded candidates, deferred lookups, ambiguities, gaps, and
        source notes.
        Raises: `NoResultError` for missing required mode inputs and
        `UnsupportedFormatError` for unsupported mode or budget values; many
        source failures are recorded as `source_notes` instead of aborting.
        Related: the bundle loads sources, not conclusions. Use explicit
        loaders for selected candidates and WebSearch for non-MOLEG facts.
        """
        validate_choice("mode", mode, BUNDLE_MODE_VALUES)
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
        loaded_interpretations: list[InterpretationText] = []
        loaded_cases: list[JudicialDecisionText] = []
        loaded_constitutional_decisions: list[JudicialDecisionText] = []
        query_expansion: LegalQueryExpansion | None = None
        law_candidates: list[LawIdentity] = []
        administrative_candidates: list[AdministrativeRuleHit] = []
        annex_form_candidates: list[AnnexFormHit] = []
        interpretation_candidates: list[InterpretationHit] = []
        case_candidates: list[JudicialDecisionHit] = []
        constitutional_candidates: list[JudicialDecisionHit] = []
        loaded_detail_keys: set[tuple[str | None, str]] = set()

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

        eager_detail_limits = bundle_eager_detail_limits(search_query, mode=mode, budget=budget)
        eager_text_budget = BUNDLE_EAGER_TEXT_CHAR_LIMITS[budget]
        eager_text_used = 0
        if any(eager_detail_limits.values()):
            source_notes.append(
                "Eager detail loading triggered for "
                + ", ".join(key for key, value in eager_detail_limits.items() if value)
                + "."
            )

        for candidate in ranked_candidates(
            interpretation_candidates,
            search_query,
            limit=eager_detail_limits["interpretations"],
        ):
            key = candidate_identity_key(candidate)
            try:
                text = self.get_interpretation(candidate.identity, include_metadata=False)
            except MolegApiError as exc:
                source_notes.append(f"Eager interpretation detail load skipped: {exc}")
                continue
            text_length = len(text.text)
            if eager_text_used + text_length > eager_text_budget:
                source_notes.append("Eager interpretation detail load skipped: text budget exceeded")
                continue
            eager_text_used += text_length
            loaded_interpretations.append(text)
            loaded_detail_keys.add(key)

        for candidate in ranked_candidates(
            case_candidates,
            search_query,
            limit=eager_detail_limits["cases"],
        ):
            key = candidate_identity_key(candidate)
            try:
                text = self.get_case(candidate.identity, include_metadata=False)
            except MolegApiError as exc:
                source_notes.append(f"Eager case detail load skipped: {exc}")
                continue
            text_length = len(text.text)
            if eager_text_used + text_length > eager_text_budget:
                source_notes.append("Eager case detail load skipped: text budget exceeded")
                continue
            eager_text_used += text_length
            loaded_cases.append(text)
            loaded_detail_keys.add(key)

        for candidate in ranked_candidates(
            constitutional_candidates,
            search_query,
            limit=eager_detail_limits["constitutional_decisions"],
        ):
            key = candidate_identity_key(candidate)
            try:
                text = self.get_constitutional_decision(candidate.identity, include_metadata=False)
            except MolegApiError as exc:
                source_notes.append(f"Eager constitutional detail load skipped: {exc}")
                continue
            text_length = len(text.text)
            if eager_text_used + text_length > eager_text_budget:
                source_notes.append("Eager constitutional detail load skipped: text budget exceeded")
                continue
            eager_text_used += text_length
            loaded_constitutional_decisions.append(text)
            loaded_detail_keys.add(key)

        deferred.extend(
            deferred_from_candidates(
                unloaded_candidates(interpretation_candidates, loaded_detail_keys),
                "get_interpretation",
                "interpretation",
            )
        )
        deferred.extend(
            deferred_from_candidates(
                unloaded_candidates(case_candidates, loaded_detail_keys),
                "get_case",
                "case",
            )
        )
        deferred.extend(
            deferred_from_candidates(
                unloaded_candidates(constitutional_candidates, loaded_detail_keys),
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
                interpretations=loaded_interpretations,
                cases=loaded_cases,
                constitutional_decisions=loaded_constitutional_decisions,
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


def validate_choice(
    param: str,
    value: str,
    valid_values: tuple[str, ...],
    *,
    context: str | None = None,
) -> None:
    if value in valid_values:
        return
    label = f"{param} for {context}" if context else param
    valid = ", ".join(repr(item) for item in valid_values)
    raise UnsupportedFormatError(f"Invalid {label}: {value!r}. Valid values: {valid}.")


def target_for(basis: Basis, kind: str) -> str:
    validate_choice("basis", basis, BASIS_VALUES)
    return TARGETS[basis][kind]


def annex_source_type(source: str) -> str:
    validate_choice("source", source, ANNEX_SOURCE_VALUES)
    if source == "law":
        return "law"
    if source == "administrative_rule":
        return "administrative_rule"
    raise AssertionError("validated annex/form source should be reachable")


def annex_target_for(source_type: str) -> str:
    validate_choice("source", source_type, ANNEX_SOURCE_VALUES)
    return ANNEX_FORM_TARGETS[source_type]


def annex_search_scope(search_scope: str) -> int:
    validate_choice("search_scope", search_scope, ANNEX_SEARCH_SCOPE_VALUES)
    return ANNEX_SEARCH_SCOPES[search_scope]


def annex_type_code(source_type: str, annex_type: str) -> str:
    valid_values = tuple(ANNEX_TYPE_CODES[annex_source_type(source_type)])
    validate_choice("annex_type", annex_type, valid_values, context=source_type)
    return ANNEX_TYPE_CODES[source_type][annex_type]


def annex_form_is_table_like(identity: AnnexFormIdentity) -> bool:
    signals = " ".join(
        value
        for value in (identity.annex_type, identity.annex_number, identity.title)
        if value
    )
    if any(token in signals for token in ("서식", "별지")):
        return False
    return any(token in signals for token in ("별표", "기준표", "표", "기준", "부과기준"))


def structure_annex_form_text(text: str, identity: AnnexFormIdentity) -> StructuredTableData:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    pipe_table = parse_pipe_table(lines, identity)
    if pipe_table:
        return pipe_table
    spaced_table = parse_spaced_table(lines, identity)
    if spaced_table:
        return spaced_table
    return low_confidence_table(identity)


def parse_pipe_table(lines: list[str], identity: AnnexFormIdentity) -> StructuredTableData | None:
    table_rows: list[list[str]] = []
    for line in lines:
        if "|" not in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if is_markdown_separator(cells):
            continue
        if len(cells) >= 2 and all(cells):
            table_rows.append(cells)
    return structured_table_from_rows(table_rows, identity)


def parse_spaced_table(lines: list[str], identity: AnnexFormIdentity) -> StructuredTableData | None:
    table_rows: list[list[str]] = []
    expected_columns: int | None = None
    for line in lines:
        cells = [cell.strip() for cell in re.split(r"\s{2,}", line.strip()) if cell.strip()]
        if len(cells) < 2:
            if table_rows:
                break
            continue
        if expected_columns is None:
            expected_columns = len(cells)
        if len(cells) != expected_columns:
            break
        table_rows.append(cells)
    return structured_table_from_rows(table_rows, identity)


def structured_table_from_rows(
    table_rows: list[list[str]],
    identity: AnnexFormIdentity,
) -> StructuredTableData | None:
    if len(table_rows) < 2:
        return None
    headers = table_rows[0]
    body_rows = table_rows[1:]
    if not body_rows or any(len(row) != len(headers) for row in body_rows):
        return None
    keys = normalized_table_keys(headers)
    rows = [dict(zip(keys, row, strict=True)) for row in body_rows]
    return StructuredTableData(
        title=identity.title,
        headers=headers,
        rows=rows,
        units=table_units(rows),
        parsing_confidence="high",
        notes=[],
    )


def normalized_table_keys(headers: list[str]) -> list[str]:
    keys: list[str] = []
    seen: dict[str, int] = {}
    for index, header in enumerate(headers, start=1):
        key = re.sub(r"\s+", "_", header.strip().lower())
        key = re.sub(r"[^\w가-힣]+", "_", key).strip("_")
        if not key:
            key = f"column_{index}"
        count = seen.get(key, 0)
        seen[key] = count + 1
        keys.append(key if count == 0 else f"{key}_{count + 1}")
    return keys


def table_units(rows: list[dict[str, str]]) -> list[str]:
    units: list[str] = []
    seen: set[str] = set()
    unit_pattern = re.compile(r"\d+(?:\.\d+)?\s*(만원|천원|억원|원|%|퍼센트|명|개|건|일|개월|년)")
    for row in rows:
        for value in row.values():
            for match in unit_pattern.findall(value):
                if match not in seen:
                    seen.add(match)
                    units.append(match)
    return units


def is_markdown_separator(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def low_confidence_table(identity: AnnexFormIdentity) -> StructuredTableData:
    return StructuredTableData(
        title=identity.title,
        headers=[],
        rows=[],
        units=[],
        parsing_confidence="low",
        notes=["plain text retained; table structure was irregular or ambiguous"],
    )


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
    validate_choice("source", source, INTERPRETATION_SOURCE_VALUES)
    if source == "moleg":
        return [OFFICIAL_INTERPRETATION_SOURCE]
    if source == "ministry":
        return [ministry_interpretation_source(ministry)]
    if source == "all":
        if not ministry:
            raise NoResultError(
                "ministry is required for source='all'; use source='moleg' or source='all_ministries'"
            )
        specs = [OFFICIAL_INTERPRETATION_SOURCE]
        specs.append(ministry_interpretation_source(ministry))
        return specs
    if source == "all_ministries":
        return [OFFICIAL_INTERPRETATION_SOURCE, *MINISTRY_INTERPRETATION_SOURCES.values()]
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
    validate_choice("court", court, COURT_VALUES)
    if court == "all":
        return None
    if court == "supreme":
        return "400201"
    if court == "lower":
        return "400202"
    raise AssertionError("validated court filter should be reachable")


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


def comparable_mechanism_identities(
    concept: str,
    laws: list[LegalLawCandidate],
    *,
    display: int,
) -> list[LawIdentity]:
    identities: dict[str, LawIdentity] = {}
    endpoints: dict[str, list[str]] = {}
    articles: dict[str, list[dict[str, str | None]]] = {}

    for law in laws:
        if law.source_type != "law":
            continue
        key = law.name
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
        elif not identities[key].law_id and law.law_id:
            current = identities[key]
            identities[key] = LawIdentity(
                law_id=law.law_id,
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
        }
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
    validate_choice("budget", budget, BUNDLE_BUDGET_VALUES)
    return BUNDLE_BUDGETS[budget]


def bundle_eager_detail_limits(
    query: str | None,
    *,
    mode: str,
    budget: str,
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


def bundle_query_intents(query: str | None, *, mode: str) -> set[str]:
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


def string_value(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def statute_identifier_label(identifier: str | LawIdentity | LawHit) -> str:
    if isinstance(identifier, LawHit):
        return identifier.identity.name
    if isinstance(identifier, LawIdentity):
        return identifier.name
    return str(identifier)


def normalize_history_bill_id_map(
    promulgation_bridge: dict[tuple[Any, Any, Any], Any] | None,
) -> dict[tuple[str, str, str], str] | None:
    if not promulgation_bridge:
        return None
    bill_id_map: dict[tuple[str, str, str], str] = {}
    for key, bill_id in promulgation_bridge.items():
        if not isinstance(key, tuple) or len(key) != 3:
            raise UnsupportedFormatError(
                "promulgation_bridge keys must be (prom_law_nm, prom_no, promulgation_dt)"
            )
        law_name, prom_no, promulgation_dt = key
        normalized_law_name = string_value(law_name)
        normalized_prom_no = compact_promulgation_number(prom_no)
        normalized_dt = compact_date(promulgation_dt)
        normalized_bill_id = string_value(bill_id)
        if (
            not normalized_law_name
            or not normalized_prom_no
            or not normalized_dt
            or not normalized_bill_id
        ):
            continue
        bill_id_map[(normalized_law_name, normalized_prom_no, normalized_dt)] = normalized_bill_id
    return bill_id_map or None


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


def significant_query_terms(query: str | None) -> list[str]:
    text = str(query or "")
    return [term for term in text.split() if len(term) >= 2]


def candidate_rank_score(candidate: Any, terms: list[str]) -> int:
    identity = getattr(candidate, "identity", None)
    haystack = " ".join(
        str(value or "")
        for value in (
            getattr(identity, "title", None),
            getattr(identity, "case_number", None),
            getattr(identity, "source_type", None),
            getattr(identity, "ministry", None),
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
        or getattr(identity, "title", None)
        or getattr(identity, "name", None)
    )
    return (source_target, str(source_id or ""))
