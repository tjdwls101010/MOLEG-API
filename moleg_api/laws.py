"""Deep law interfaces for the first MOLEG-API vertical slice."""

from __future__ import annotations

from dataclasses import dataclass, replace
import re
from typing import Any

from .errors import (
    AmbiguousLawError,
    MolegApiError,
    NoResultError,
    ParseFailureError,
    SourceApiError,
    UnsupportedFormatError,
)
from .models import (
    AdministrativeRuleHit,
    AdministrativeRuleArticleText,
    AdministrativeRuleContext,
    AdministrativeRuleIdentity,
    AdministrativeRuleText,
    Ambiguity,
    AnnexFormSource,
    AnnexFormHit,
    AnnexFormIdentity,
    AnnexFormText,
    AnnexSearchScope,
    AnnexType,
    ArticleContext,
    ArticleText,
    AuthorityContext,
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
    extract_supplementary_provisions,
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

DELEGATED_CRITERIA_LOAD_LIMITS: dict[str, dict[str, int]] = {
    "minimal": {"administrative_rules": 1, "annex_forms": 1},
    "standard": {"administrative_rules": 2, "annex_forms": 2},
    "broad": {"administrative_rules": 3, "annex_forms": 3},
}

AUTHORITY_LOAD_LIMITS: dict[str, dict[str, int]] = {
    "minimal": {"interpretations": 1, "cases": 1, "constitutional_decisions": 1},
    "standard": {"interpretations": 2, "cases": 2, "constitutional_decisions": 2},
    "broad": {"interpretations": 5, "cases": 5, "constitutional_decisions": 5},
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
        query = require_query(query)
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
        law_name = string_value(prom_law_nm)
        law_name = law_name.strip() if law_name else None
        if not law_name:
            raise NoResultError(
                "prom_law_nm is required to resolve a promulgated law without unbounded source search"
            )

        hits = self.search_laws(law_name, basis="promulgated")
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
        Returns: `LawText` with a normalized identity, extracted articles,
        supplementary provisions when present, and optionally preserved raw
        metadata for audit.
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
        supplementary_provisions = extract_supplementary_provisions(raw_law, "law")
        if articles is not None:
            law_articles = select_requested_articles(law_articles, articles)
        return LawText(
            identity=identity,
            articles=law_articles,
            supplementary_provisions=supplementary_provisions,
            raw=raw_law if include_metadata else {},
        )

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
        requested_article = article_label_for_filter(article)
        if requested_article.startswith(f"{normalized.article}의"):
            normalized = replace(normalized, article=requested_article)
        return normalized

    def load_article_context(
        self,
        law_identifier: LawIdentity | LawHit | str,
        article: str | int,
        *,
        as_of: str | None = None,
        basis: Basis = "effective",
        follow_moved: bool = True,
    ) -> ArticleContext:
        """Load an article and resolve moved-article source state.

        Use when: the skill needs current/as-of article substance and should
        not mistake a moved or deleted article marker for operative text.
        Returns: `ArticleContext` with the requested article, the current
        destination article when one is safely loaded, all loaded article rows,
        and any gaps/deferred lookups needed before a substance claim.
        Raises: source and parse errors from the initial requested article load;
        destination-load failures are preserved as context gaps instead.
        Related: use `get_article` for a single source row and
        `trace_law_history` when the movement event or prior wording matters.
        """
        requested = self.get_article(law_identifier, article, as_of=as_of, basis=basis)
        loaded_articles = [requested]
        gaps: list[ContextGap] = []
        deferred: list[DeferredLookup] = []
        source_notes: list[str] = []

        if requested.is_deleted:
            append_deleted_article_gap(requested, gaps, source_notes)
            return ArticleContext(
                requested_article=requested,
                current_article=None,
                loaded_articles=loaded_articles,
                deferred=deferred,
                gaps=gaps,
                source_notes=source_notes,
            )

        current_article: ArticleText | None = requested
        seen_articles = {requested.article}
        followups_remaining = 5
        while follow_moved and current_article and current_article.moved_to:
            destination = current_article.moved_to
            if destination in seen_articles:
                gaps.append(
                    ContextGap(
                        kind="article_movement_cycle",
                        reason=(
                            f"{current_article.identity.name} movement chain loops at {destination}; "
                            "manual review is required before making a current-substance claim."
                        ),
                        query=f"{current_article.identity.name} {destination}",
                        recommended_interface="get_article",
                    )
                )
                current_article = None
                break
            if followups_remaining <= 0:
                append_moved_destination_lookup_gap(
                    NoResultError("Moved-article chain exceeded follow-up limit"),
                    current_article.identity,
                    destination,
                    gaps,
                    deferred,
                    as_of=as_of,
                    basis=basis,
                )
                current_article = None
                break
            followups_remaining -= 1
            try:
                destination_article = self.get_article(
                    current_article.identity,
                    destination,
                    as_of=as_of,
                    basis=basis,
                )
            except MolegApiError as exc:
                append_moved_destination_lookup_gap(
                    exc,
                    current_article.identity,
                    destination,
                    gaps,
                    deferred,
                    as_of=as_of,
                    basis=basis,
                )
                current_article = None
                break

            loaded_articles.append(destination_article)
            seen_articles.add(destination_article.article)
            current_article = destination_article
            if current_article.is_deleted:
                append_deleted_article_gap(current_article, gaps, source_notes)
                current_article = None
                break

        if current_article and current_article.moved_to:
            current_article = None

        if requested.moved_to and not follow_moved:
            append_moved_destination_deferred(
                requested.identity,
                requested.moved_to,
                deferred,
                as_of=as_of,
                basis=basis,
            )
            current_article = None

        return ArticleContext(
            requested_article=requested,
            current_article=current_article,
            loaded_articles=loaded_articles,
            deferred=deferred,
            gaps=gaps,
            source_notes=source_notes,
        )

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
        source_failures: list[ContextGap] = []
        if article is not None:
            events = self._populate_article_history_text(
                identity,
                article,
                events,
                source_failures,
            )
        if not events:
            raise NoResultError("No law history events found")
        return LawHistory(identity=identity, events=events, source_failures=source_failures, raw=payload)

    def _populate_article_history_text(
        self,
        identity: LawIdentity,
        article: str | int,
        events: list[HistoryEvent],
        source_failures: list[ContextGap],
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
                except MolegApiError as exc:
                    append_source_failure_gap(
                        exc,
                        source_failures,
                        query=f"{identity.name} {event_article} {as_of}",
                        recommended_interface="get_article",
                        source_label="Article-history snapshot lookup",
                    )
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
        params = versioned_law_identity_params(identity)
        payload = self.source.service("lsDelegated", params)
        raw_delegation = unwrap_service_payload(payload, "lsDelegated")
        root_identity = maybe_identity(raw_delegation.get("법령정보"), basis="effective") or identity
        rules = normalize_delegated_rules(raw_delegation)
        if article is not None:
            wanted = article_label_for_filter(article)
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
        params = versioned_law_identity_params(identity)
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
        query = require_query(query)
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
        query = require_query(query)
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
        text, structured articles when available, supplementary provisions when
        present, and optional raw metadata.
        Raises: `NoResultError` when the identity cannot locate text or article
        filtering removes all rows; source/parse errors may also propagate.
        Related: use `search_administrative_rules` for discovery and
        `find_delegated_rules` when starting from a statute.
        """
        if articles is not None and not articles:
            raise NoResultError("articles must contain at least one article when provided")

        identity_hint = self._resolve_administrative_rule_identifier(identifier)
        params = administrative_rule_identity_params(identity_hint)
        payload = self.source.service("admrul", params)
        raw_rule = unwrap_service_payload(payload, "admrul")
        identity = normalize_administrative_rule_identity(raw_rule)
        rule_articles = extract_administrative_rule_articles(raw_rule, identity)
        supplementary_provisions = extract_supplementary_provisions(raw_rule, "administrative_rule")
        if articles is not None:
            rule_articles = select_requested_administrative_rule_articles(rule_articles, articles)
        if not rule_articles:
            raise NoResultError("No administrative-rule text found")
        text = administrative_rule_text_from_articles(rule_articles)
        return AdministrativeRuleText(
            identity=identity,
            text=text,
            articles=rule_articles,
            supplementary_provisions=supplementary_provisions,
            raw=raw_rule if include_metadata else {},
        )

    def _resolve_administrative_rule_identifier(
        self,
        identifier: AdministrativeRuleIdentity | AdministrativeRuleHit | str,
    ) -> AdministrativeRuleIdentity:
        identity = administrative_rule_identity_from_identifier(identifier)
        if identity.serial_id or identity.rule_id:
            return identity
        if not identity.name:
            raise NoResultError("Administrative-rule identity has neither ID, LID, nor exact name")

        hits = self.search_administrative_rules(identity.name)
        exact = [
            hit.identity
            for hit in hits
            if hit.identity.name == identity.name
        ]
        unique: list[AdministrativeRuleIdentity] = []
        seen: set[tuple[str | None, str | None, str]] = set()
        for item in exact:
            key = (item.serial_id, item.rule_id, item.name)
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)

        if len(unique) == 1:
            return unique[0]
        if len(unique) > 1:
            raise AmbiguousLawError(
                f"Administrative-rule name {identity.name!r} matched multiple identities",
                kind="administrative_rule_identity",
                candidates=unique,
            )
        raise NoResultError(f"No administrative-rule identity matched exact name: {identity.name}")

    def load_administrative_rule_context(
        self,
        identifier: AdministrativeRuleIdentity | AdministrativeRuleHit | str,
        *,
        articles: list[str | int] | None = None,
        include_metadata: bool = True,
        follow_moved: bool = True,
    ) -> AdministrativeRuleContext:
        """Load administrative-rule text and resolve moved/deleted articles.

        Use when: the skill needs current operational criteria from a selected
        notice, directive, established rule, or similar administrative rule and
        should not mistake deleted/moved article markers for operative text.
        Returns: `AdministrativeRuleContext` with requested articles,
        current-citable articles, all loaded article rows, and any
        gaps/deferred lookups needed before a criteria claim.
        Raises: source and parse errors from the initial selected rule load;
        moved-destination failures are preserved as context gaps instead.
        Related: use `search_administrative_rules` for discovery and
        `get_administrative_rule` when the caller only needs source text rows.
        """
        rule = self.get_administrative_rule(
            identifier,
            articles=articles,
            include_metadata=include_metadata,
        )
        requested_articles = list(rule.articles)
        loaded_articles = list(requested_articles)
        current_articles: list[AdministrativeRuleArticleText] = []
        deferred: list[DeferredLookup] = []
        gaps: list[ContextGap] = []
        source_notes: list[str] = []

        for requested in requested_articles:
            if requested.is_deleted:
                append_deleted_administrative_rule_article_gap(requested, gaps, source_notes)
                continue

            current_article: AdministrativeRuleArticleText | None = requested
            seen_articles = {requested.article} if requested.article else set()
            followups_remaining = 5
            while follow_moved and current_article and current_article.moved_to:
                destination = current_article.moved_to
                source_notes.append(
                    f"{current_article.identity.name} {current_article.article} is moved to "
                    f"{destination}; current operational criteria must come from the destination article."
                )
                if destination in seen_articles:
                    gaps.append(
                        ContextGap(
                            kind="administrative_rule_article_movement_cycle",
                            reason=(
                                f"{current_article.identity.name} movement chain loops at {destination}; "
                                "manual review is required before making a current operational-criteria claim."
                            ),
                            query=f"{current_article.identity.name} {destination}",
                            recommended_interface="load_administrative_rule_context",
                        )
                    )
                    current_article = None
                    break
                if followups_remaining <= 0:
                    append_moved_administrative_rule_destination_lookup_gap(
                        NoResultError("Moved administrative-rule article chain exceeded follow-up limit"),
                        current_article.identity,
                        destination,
                        gaps,
                        deferred,
                    )
                    current_article = None
                    break
                followups_remaining -= 1
                try:
                    destination_rule = self.get_administrative_rule(
                        current_article.identity,
                        articles=[destination],
                        include_metadata=include_metadata,
                    )
                except MolegApiError as exc:
                    append_moved_administrative_rule_destination_lookup_gap(
                        exc,
                        current_article.identity,
                        destination,
                        gaps,
                        deferred,
                    )
                    current_article = None
                    break

                destination_article = destination_rule.articles[0]
                loaded_articles.append(destination_article)
                if destination_article.article:
                    seen_articles.add(destination_article.article)
                current_article = destination_article
                if current_article.is_deleted:
                    append_deleted_administrative_rule_article_gap(
                        current_article,
                        gaps,
                        source_notes,
                    )
                    current_article = None
                    break

            if current_article and current_article.moved_to:
                current_article = None

            if requested.moved_to and not follow_moved:
                append_moved_administrative_rule_destination_deferred(
                    requested.identity,
                    requested.moved_to,
                    deferred,
                )
                current_article = None

            if current_article is not None:
                current_articles.append(current_article)

        return AdministrativeRuleContext(
            rule=rule,
            requested_articles=requested_articles,
            current_articles=current_articles,
            loaded_articles=loaded_articles,
            deferred=deferred,
            gaps=gaps,
            source_notes=source_notes,
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
        query = require_query(query)
        specs = interpretation_sources_for(source, ministry)
        aggregate_search = len(specs) > 1
        hits: list[InterpretationHit] = []
        source_failures: list[ContextGap] = []
        first_failure: MolegApiError | None = None
        for spec in specs:
            params: dict[str, Any] = {
                "query": query,
                "display": display,
                "search": 2 if search_body else 1,
            }
            if interpreted_on:
                params["explYd"] = compact_date(interpreted_on)
            try:
                payload = self.source.search(spec.target, params)
            except MolegApiError as exc:
                if not aggregate_search:
                    raise
                if first_failure is None:
                    first_failure = exc
                append_source_failure_gap(
                    exc,
                    source_failures,
                    query=query,
                    recommended_interface="search_interpretations",
                    source_label=f"Interpretation search for {spec.ministry or spec.target}",
                )
                continue
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
        if not hits and first_failure is not None:
            raise first_failure
        if source_failures:
            hits = attach_interpretation_source_failures(hits, source_failures)
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
        query = require_query(query)
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
        query = require_query(query)
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

    def load_authority_context(
        self,
        law_identifier: LawIdentity | LawHit | str,
        *,
        articles: list[str | int],
        query: str | None = None,
        budget: BundleBudget = "standard",
        as_of: str | None = None,
    ) -> AuthorityContext:
        """Load article-scoped interpretations, cases, and decisions.

        Use when: the skill needs authority context for specific statute
        articles and should not treat mismatched, undated, or pre-amendment
        authority as current target-article support.
        Returns: `AuthorityContext` with target articles, loaded authority
        details, `current_authorities` filtered to dated structured article matches,
        candidates, gaps, deferred lookups, and source notes.
        Raises: `NoResultError` for empty article lists or blank supplied
        queries; source failures from target article loading are preserved as
        gaps when possible.
        Related: use `search_interpretations`, `search_cases`, and
        `search_constitutional_decisions` for candidate discovery only, or
        `load_legal_context_bundle` for a broader first pass.
        """
        if not articles:
            raise NoResultError("articles must contain at least one article")
        limits = authority_load_limits(budget)
        reference_date = compact_date(as_of) if as_of else None
        ranking_query = require_query(query) if query is not None else None
        identity = identity_from_identifier(law_identifier, basis="effective")
        requested_articles = list(articles)
        search_query = ranking_query or f"{identity.name} {' '.join(article_label_for_filter(item) for item in articles)}"
        request = BundleRequest(
            query=search_query,
            mode="statute_review",
            budget=budget,
            articles=requested_articles,
            law_identifier=law_identifier,
            as_of=reference_date,
        )
        source_notes: list[str] = [
            "AuthorityContext is scoped source context for Claude inspection, not a legal conclusion."
        ]
        gaps: list[ContextGap] = []
        deferred: list[DeferredLookup] = []
        target_articles: list[ArticleText] = []
        loaded_article_rows: list[ArticleText] = []

        for article in requested_articles:
            try:
                article_context = self.load_article_context(
                    identity,
                    article,
                    as_of=reference_date,
                    basis="effective",
                )
            except MolegApiError as exc:
                append_requested_article_load_gap(
                    exc,
                    identity,
                    article,
                    gaps,
                    deferred,
                    as_of=reference_date,
                )
                continue
            loaded_article_rows.extend(article_context.loaded_articles)
            gaps.extend(article_context.gaps)
            deferred.extend(article_context.deferred)
            source_notes.extend(article_context.source_notes)
            if article_context.current_article is not None:
                target_articles.append(article_context.current_article)

        search_queries = article_target_search_queries(
            identity,
            requested_articles,
            target_articles,
            ranking_query=ranking_query,
        )
        authority_ranking_query = " ".join(search_queries)

        interpretation_candidates = dedupe_candidates(
            [
                candidate
                for candidate_query in search_queries
                for candidate in safe_list(
                    lambda candidate_query=candidate_query: self.search_interpretations(
                        candidate_query,
                        display=limits["interpretations"],
                    ),
                    source_notes,
                    "Authority interpretation search",
                    gaps=gaps,
                    deferred=deferred,
                    query=candidate_query,
                    recommended_interface="search_interpretations",
                    source_type="interpretation",
                )
            ]
        )
        case_candidates = dedupe_candidates(
            [
                candidate
                for candidate_query in search_queries
                for candidate in safe_list(
                    lambda candidate_query=candidate_query: self.search_cases(
                        candidate_query,
                        display=limits["cases"],
                    ),
                    source_notes,
                    "Authority case search",
                    gaps=gaps,
                    deferred=deferred,
                    query=candidate_query,
                    recommended_interface="search_cases",
                    source_type="case",
                )
            ]
        )
        constitutional_candidates = dedupe_candidates(
            [
                candidate
                for candidate_query in search_queries
                for candidate in safe_list(
                    lambda candidate_query=candidate_query: self.search_constitutional_decisions(
                        candidate_query,
                        display=limits["constitutional_decisions"],
                    ),
                    source_notes,
                    "Authority Constitutional Court search",
                    gaps=gaps,
                    deferred=deferred,
                    query=candidate_query,
                    recommended_interface="search_constitutional_decisions",
                    source_type="constitutional",
                )
            ]
        )

        loaded_interpretations: list[InterpretationText] = []
        loaded_cases: list[JudicialDecisionText] = []
        loaded_constitutional_decisions: list[JudicialDecisionText] = []
        loaded_detail_keys: set[tuple[str | None, str]] = set()

        for candidate in ranked_candidates(
            interpretation_candidates,
            authority_ranking_query,
            limit=limits["interpretations"],
        ):
            try:
                text = self.get_interpretation(candidate.identity, include_metadata=False)
            except MolegApiError as exc:
                source_notes.append(f"Authority interpretation detail load skipped: {exc}")
                append_eager_detail_failure_gap(
                    exc,
                    gaps,
                    candidate=candidate,
                    recommended_interface="get_interpretation",
                    source_label="Authority interpretation detail load",
                )
                continue
            loaded_interpretations.append(text)
            loaded_detail_keys.add(candidate_identity_key(candidate))

        for candidate in ranked_candidates(
            case_candidates,
            authority_ranking_query,
            limit=limits["cases"],
        ):
            try:
                text = self.get_case(candidate.identity, include_metadata=False)
            except MolegApiError as exc:
                source_notes.append(f"Authority case detail load skipped: {exc}")
                append_eager_detail_failure_gap(
                    exc,
                    gaps,
                    candidate=candidate,
                    recommended_interface="get_case",
                    source_label="Authority case detail load",
                )
                continue
            loaded_cases.append(text)
            loaded_detail_keys.add(candidate_identity_key(candidate))

        for candidate in ranked_candidates(
            constitutional_candidates,
            authority_ranking_query,
            limit=limits["constitutional_decisions"],
        ):
            try:
                text = self.get_constitutional_decision(candidate.identity, include_metadata=False)
            except MolegApiError as exc:
                source_notes.append(f"Authority constitutional detail load skipped: {exc}")
                append_eager_detail_failure_gap(
                    exc,
                    gaps,
                    candidate=candidate,
                    recommended_interface="get_constitutional_decision",
                    source_label="Authority constitutional detail load",
                )
                continue
            loaded_constitutional_decisions.append(text)
            loaded_detail_keys.add(candidate_identity_key(candidate))

        append_authority_article_mismatch_gaps(
            target_article_refs_from_loaded_articles(target_articles),
            interpretations=loaded_interpretations,
            cases=loaded_cases,
            constitutional_decisions=loaded_constitutional_decisions,
            gaps=gaps,
        )
        append_authority_temporal_mismatch_gaps(
            target_articles,
            interpretations=loaded_interpretations,
            cases=loaded_cases,
            constitutional_decisions=loaded_constitutional_decisions,
            gaps=gaps,
            deferred=deferred,
            reference_date=reference_date,
        )

        current_interpretations = [
            item
            for item in loaded_interpretations
            if authority_references_current_targets(
                item.referenced_articles,
                item.identity.interpretation_date,
                target_articles,
                reference_date=reference_date,
            )
        ]
        current_cases = [
            item
            for item in loaded_cases
            if authority_references_current_targets(
                item.referenced_articles,
                item.identity.decision_date,
                target_articles,
                reference_date=reference_date,
            )
        ]
        current_constitutional_decisions = [
            item
            for item in loaded_constitutional_decisions
            if authority_references_current_targets(
                item.reviewed_articles,
                item.identity.decision_date,
                target_articles,
                reference_date=reference_date,
            )
        ]

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

        return AuthorityContext(
            request=request,
            target_articles=target_articles,
            loaded=LoadedContext(
                articles=loaded_article_rows,
                interpretations=loaded_interpretations,
                cases=loaded_cases,
                constitutional_decisions=loaded_constitutional_decisions,
            ),
            current_authorities=LoadedContext(
                interpretations=current_interpretations,
                cases=current_cases,
                constitutional_decisions=current_constitutional_decisions,
            ),
            candidates=CandidateContext(
                interpretations=interpretation_candidates,
                cases=case_candidates,
                constitutional_decisions=constitutional_candidates,
            ),
            deferred=deferred,
            gaps=gaps,
            source_notes=source_notes,
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
        articles/laws, follow-up search recommendations, empty-source notes,
        and source-failure gaps when optional planning sources fail.
        Raises: `NoResultError` for blank queries.
        Related: this is not legal authority. Use returned follow-ups with
        `get_law`, `get_article`, interpretation, case, or annex loaders.
        """
        query = require_query(query)

        raw: dict[str, Any] = {}
        empty_sources: list[str] = []
        source_failures: list[ContextGap] = []

        try:
            law_payload = self.source.search("eflaw", {"query": query, "display": display})
            raw["eflaw"] = law_payload
            law_rows = unwrap_search_laws(law_payload)
            if not law_rows:
                empty_sources.append("eflaw")
        except MolegApiError as exc:
            append_source_failure_gap(
                exc,
                source_failures,
                query=query,
                recommended_interface="expand_legal_query",
                source_label="Query-expansion law candidate search",
            )
            law_rows = []
        law_candidates: list[LawIdentity] = []
        for row in law_rows:
            try:
                law_candidates.append(normalize_law_identity(row, basis="effective"))
            except ParseFailureError:
                continue

        legal_term_rows = self._search_rows(
            "lstrmAI",
            {"query": query, "display": display},
            raw,
            empty_sources,
            source_failures=source_failures,
            source_label="Query-expansion legal-term search",
        )
        everyday_term_rows = self._search_rows(
            "dlytrm",
            {"query": query, "display": display},
            raw,
            empty_sources,
            source_failures=source_failures,
            source_label="Query-expansion everyday-term search",
        )
        legal_to_everyday_rows = self._service_rows(
            "lstrmRlt",
            {"query": query},
            raw,
            empty_sources,
            source_failures=source_failures,
            source_label="Query-expansion legal-to-everyday term relation lookup",
        )
        everyday_to_legal_rows = self._service_rows(
            "dlytrmRlt",
            {"query": query},
            raw,
            empty_sources,
            source_failures=source_failures,
            source_label="Query-expansion everyday-to-legal term relation lookup",
        )
        term_article_rows = self._service_rows(
            "lstrmRltJo",
            {"query": query},
            raw,
            empty_sources,
            source_failures=source_failures,
            source_label="Query-expansion term-article relation lookup",
        )
        ai_search_rows = self._search_rows(
            "aiSearch",
            {"query": query, "display": display, "search": 0},
            raw,
            empty_sources,
            source_failures=source_failures,
            source_label="Query-expansion AI search",
        )
        ai_related_rows = self._search_rows(
            "aiRltLs",
            {"query": query, "search": 0},
            raw,
            empty_sources,
            source_failures=source_failures,
            source_label="Query-expansion AI related-law search",
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
            source_failures=source_failures,
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

        source_failures: list[ContextGap] = []
        first_failure: MolegApiError | None = None

        def remember_failure(exc: MolegApiError) -> None:
            nonlocal first_failure
            if first_failure is None:
                first_failure = exc

        try:
            ai_search_payload = self.source.search(
                "aiSearch",
                {"query": concept, "display": display, "search": 0},
            )
            ai_search_rows = unwrap_target_rows(ai_search_payload, "aiSearch")
        except MolegApiError as exc:
            remember_failure(exc)
            append_source_failure_gap(
                exc,
                source_failures,
                query=concept,
                recommended_interface="find_comparable_mechanisms",
                source_label="Comparable-mechanism AI search",
            )
            ai_search_rows = []

        try:
            ai_related_payload = self.source.search(
                "aiRltLs",
                {"query": concept, "search": 0},
            )
            ai_related_rows = unwrap_target_rows(ai_related_payload, "aiRltLs")
        except MolegApiError as exc:
            remember_failure(exc)
            append_source_failure_gap(
                exc,
                source_failures,
                query=concept,
                recommended_interface="find_comparable_mechanisms",
                source_label="Comparable-mechanism related-law search",
            )
            ai_related_rows = []

        try:
            term_article_payload = self.source.service("lstrmRltJo", {"query": concept})
            term_article_rows = unwrap_target_rows(term_article_payload, "lstrmRltJo")
        except MolegApiError as exc:
            remember_failure(exc)
            append_source_failure_gap(
                exc,
                source_failures,
                query=concept,
                recommended_interface="find_comparable_mechanisms",
                source_label="Comparable-mechanism term-article lookup",
            )
            term_article_rows = []

        candidates = comparable_mechanism_identities(
            concept,
            [
                *laws_from_rows(ai_search_rows, source_target="aiSearch"),
                *laws_from_rows(ai_related_rows, source_target="aiRltLs"),
                *laws_from_rows(term_article_rows, source_target="lstrmRltJo"),
            ],
            display=display,
            source_failures=source_failures,
        )
        if not candidates:
            if first_failure is not None:
                raise first_failure
            raise NoResultError(f"No comparable mechanisms found for concept: {concept}")
        return candidates

    def _search_rows(
        self,
        target: str,
        params: dict[str, Any],
        raw: dict[str, Any],
        empty_sources: list[str],
        *,
        source_failures: list[ContextGap] | None = None,
        source_label: str | None = None,
    ) -> list[dict[str, Any]]:
        try:
            payload = self.source.search(target, params)
        except MolegApiError as exc:
            if source_failures is not None:
                append_source_failure_gap(
                    exc,
                    source_failures,
                    query=string_value(params.get("query")),
                    recommended_interface="expand_legal_query",
                    source_label=source_label or f"Query-expansion {target} search",
                )
            return []
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
        budget: BundleBudget = "standard",
        as_of: str | None = None,
    ) -> LegalContextBundle:
        """Load one explicit multi-statute institutional system.

        Use when: the skill has already selected the statute set for a 제도 and
        needs one staged source bundle across those statutes.
        Returns: `LegalContextBundle` with `request.mode="institutional_system"`,
        `request.statute_ids`, loaded law/article text, law structures,
        delegation graphs, candidates, deferred lookups, ambiguities, and gaps.
        Pass `as_of` when the statute set is being reviewed for current force
        on a specific reference date.
        Raises: `NoResultError` for an empty statute set and budget validation
        errors from the normal bundle limits; per-statute failures are recorded
        in the returned bundle instead of aborting the whole load.
        Related: use `search_laws` or `expand_legal_query` before this method
        when the statute set itself is uncertain.
        """
        if not statute_identifiers:
            raise NoResultError("statute_identifiers is required for institutional-system bundles")
        if articles is not None and not articles:
            raise NoResultError("articles must contain at least one article when provided")

        limits = bundle_limits(budget)
        reference_date = compact_date(as_of) if as_of else None
        request = BundleRequest(
            query=None,
            mode="institutional_system",
            budget=budget,
            articles=list(articles or []),
            statute_ids=[statute_identifier_label(identifier) for identifier in statute_identifiers],
            as_of=reference_date,
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
            try:
                resolution = self._resolve_institutional_statute(
                    statute_identifier,
                    display=max(2, limits["law_candidates"]),
                )
            except MolegApiError as exc:
                label = statute_identifier_label(statute_identifier)
                source_notes.append(f"Statute resolution skipped for {label}: {exc}")
                append_institutional_statute_resolution_failure_gap(
                    exc,
                    label,
                    gaps,
                    deferred,
                )
                continue
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
                        article_context = self.load_article_context(
                            identity,
                            article,
                            as_of=reference_date,
                            basis="effective",
                        )
                        loaded_articles.extend(article_context.loaded_articles)
                        gaps.extend(article_context.gaps)
                        deferred.extend(article_context.deferred)
                        source_notes.extend(article_context.source_notes)
                        for article_text in article_context.loaded_articles:
                            identity = prefer_versioned_law_identity(identity, article_text.identity)
                            append_not_effective_as_of_gap(
                                article_text.identity,
                                reference_date,
                                gaps,
                                source_notes,
                                query=identity.name,
                            )
                    except MolegApiError as exc:
                        source_notes.append(f"Article load skipped for {identity.name} {article}: {exc}")
                        append_requested_article_load_gap(
                            exc,
                            identity,
                            article,
                            gaps,
                            deferred,
                            as_of=reference_date,
                        )
            else:
                try:
                    law_text = self.get_law(identity, as_of=reference_date)
                    loaded_laws.append(law_text)
                    identity = law_text.identity
                    law_candidates.append(identity)
                    append_not_effective_as_of_gap(
                        identity,
                        reference_date,
                        gaps,
                        source_notes,
                        query=identity.name,
                    )
                    append_whole_law_article_status_gaps(
                        law_text,
                        gaps,
                        deferred,
                        source_notes,
                        as_of=reference_date,
                        basis="effective",
                    )
                except MolegApiError as exc:
                    source_notes.append(f"Law load skipped for {identity.name}: {exc}")
                    append_requested_law_load_gap(
                        exc,
                        identity,
                        gaps,
                        deferred,
                        as_of=reference_date,
                    )

            try:
                law_structures.append(self.get_law_structure(identity, depth=1))
            except MolegApiError as exc:
                source_notes.append(f"Law-structure lookup skipped for {identity.name}: {exc}")
                append_law_structure_load_gap(
                    exc,
                    identity,
                    gaps,
                    deferred,
                )

            try:
                graph = self.find_delegated_rules(identity)
                loaded_delegations.append(limit_delegation_graph(graph, limits["delegations"]))
            except NoResultError:
                loaded_delegations.append(DelegationGraph(identity=identity, rules=[], raw={}))
                append_empty_delegation_lookup_gap(
                    identity,
                    gaps,
                    deferred,
                    recommended_interface="search_administrative_rules",
                    deferred_interface=None,
                )
            except MolegApiError as exc:
                source_notes.append(f"Delegation lookup skipped for {identity.name}: {exc}")
                append_delegation_lookup_failure_gap(
                    exc,
                    identity,
                    gaps,
                    deferred,
                )

            administrative_candidates.extend(
                safe_list(
                    lambda identity=identity: self.search_administrative_rules(
                        identity.name,
                        display=limits["administrative_rules"],
                    ),
                    source_notes,
                    f"Administrative-rule search for {identity.name}",
                    gaps=gaps,
                    deferred=deferred,
                    query=identity.name,
                    recommended_interface="search_administrative_rules",
                    source_type="administrative_rule",
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
                    gaps=gaps,
                    deferred=deferred,
                    query=identity.name,
                    recommended_interface="search_interpretations",
                    source_type="interpretation",
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
                    gaps=gaps,
                    deferred=deferred,
                    query=identity.name,
                    recommended_interface="search_cases",
                    source_type="case",
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
                    gaps=gaps,
                    deferred=deferred,
                    query=identity.name,
                    recommended_interface="search_constitutional_decisions",
                    source_type="constitutional",
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
                        gaps=gaps,
                        deferred=deferred,
                        query=identity.name,
                        recommended_interface="search_annex_forms",
                        source_type="annex_form",
                        filters={"source": "law", "search_scope": "source"},
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
                        gaps=gaps,
                        deferred=deferred,
                        query=identity.name,
                        recommended_interface="search_annex_forms",
                        source_type="annex_form",
                        filters={"source": "administrative_rule", "search_scope": "source"},
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
            deferred_from_candidates(
                administrative_candidates,
                "get_administrative_rule",
                "administrative_rule",
            )
        )
        deferred.extend(
            deferred_from_candidates(
                annex_form_candidates,
                "get_annex_form_body",
                "annex_form",
            )
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

    def load_delegated_criteria(
        self,
        law_identifier: str | LawIdentity | LawHit,
        *,
        articles: list[str | int] | None = None,
        query: str | None = None,
        budget: BundleBudget = "standard",
        as_of: str | None = None,
    ) -> LegalContextBundle:
        """Load delegated operational criteria from a known statute anchor.

        Use when: the skill has a statute or article and needs subordinate
        administrative-rule and annex/form bodies before discussing concrete
        operational criteria.
        Returns: a `LegalContextBundle` with the same staged context as
        `load_institutional_system`, plus bounded loaded administrative-rule
        and annex/form bodies in `loaded`.
        Raises: the same validation errors as `load_institutional_system`; a
        blank `query` is rejected when supplied, while per-candidate detail-load
        failures become gaps and deferred lookups.
        Related: use `load_institutional_system` when candidate discovery is
        enough and detail bodies should remain deferred.
        """
        if articles is not None and not articles:
            raise NoResultError("articles must contain at least one article when provided")
        explicit_query = require_query(query) if query is not None else None

        bundle = self.load_institutional_system(
            [law_identifier],
            articles=articles,
            budget=budget,
            as_of=as_of,
        )
        limits = dict(delegated_criteria_load_limits(budget))
        candidate_limits = bundle_limits(budget)
        explicit_queries = (
            delegated_criteria_query_search_queries(bundle, explicit_query)
            if explicit_query
            else []
        )
        ranking_query = " ".join(explicit_queries) if explicit_queries else delegated_criteria_ranking_query(bundle)

        source_notes = list(bundle.source_notes)
        gaps = list(bundle.gaps)
        deferred = [
            item
            for item in bundle.deferred
            if item.interface not in {"get_administrative_rule", "get_annex_form_body"}
        ]
        loaded_administrative_rules: list[AdministrativeRuleText] = []
        loaded_annex_forms: list[AnnexFormText] = []
        loaded_candidate_keys: set[tuple[str | None, str]] = set()
        administrative_candidates = list(bundle.candidates.administrative_rules)
        annex_form_candidates = list(bundle.candidates.annex_forms)
        delegated_scope = delegated_criteria_target_scope(bundle)

        if explicit_query:
            query_administrative_candidates = dedupe_candidates(
                [
                    candidate
                    for candidate_query in explicit_queries
                    for candidate in safe_list(
                        lambda candidate_query=candidate_query: self.search_administrative_rules(
                            candidate_query,
                            display=candidate_limits["administrative_rules"],
                        ),
                        source_notes,
                        "Delegated-criteria administrative-rule query search",
                        gaps=gaps,
                        deferred=deferred,
                        query=candidate_query,
                        recommended_interface="search_administrative_rules",
                        source_type="administrative_rule",
                    )
                ]
            )
            administrative_candidates = dedupe_candidates(
                [
                    *query_administrative_candidates,
                    *administrative_candidates,
                ]
            )[: candidate_limits["administrative_rules"]]
            annex_form_limit = candidate_limits["annex_forms"]
            law_annex_limit = (annex_form_limit + 1) // 2
            admin_annex_limit = max(1, annex_form_limit - law_annex_limit)
            query_law_annex_candidates = dedupe_candidates(
                [
                    candidate
                    for candidate_query in explicit_queries
                    for candidate in safe_list(
                        lambda candidate_query=candidate_query: self.search_annex_forms(
                            candidate_query,
                            source="law",
                            search_scope="source",
                            display=law_annex_limit,
                        ),
                        source_notes,
                        "Delegated-criteria law annex/form query search",
                        gaps=gaps,
                        deferred=deferred,
                        query=candidate_query,
                        recommended_interface="search_annex_forms",
                        source_type="annex_form",
                        filters={"source": "law", "search_scope": "source"},
                    )
                ]
            )
            query_admin_annex_candidates = dedupe_candidates(
                [
                    candidate
                    for candidate_query in explicit_queries
                    for candidate in safe_list(
                        lambda candidate_query=candidate_query: self.search_annex_forms(
                            candidate_query,
                            source="administrative_rule",
                            search_scope="source",
                            display=admin_annex_limit,
                        ),
                        source_notes,
                        "Delegated-criteria administrative-rule annex/form query search",
                        gaps=gaps,
                        deferred=deferred,
                        query=candidate_query,
                        recommended_interface="search_annex_forms",
                        source_type="annex_form",
                        filters={"source": "administrative_rule", "search_scope": "source"},
                    )
                ]
            )
            annex_form_candidates = dedupe_candidates(
                [
                    *query_law_annex_candidates,
                    *query_admin_annex_candidates,
                    *annex_form_candidates,
                ]
            )[:annex_form_limit]

        if any(item.kind == "statute_identity" for item in bundle.ambiguities):
            limits = {key: 0 for key in limits}
            source_notes.append(
                "Delegated-criteria detail loading skipped until statute identity ambiguity is resolved."
            )

        for candidate in ranked_candidates(
            administrative_candidates,
            ranking_query,
            limit=limits["administrative_rules"],
        ):
            try:
                rule_context = self.load_administrative_rule_context(candidate.identity)
                gaps.extend(rule_context.gaps)
                deferred.extend(rule_context.deferred)
                source_notes.extend(rule_context.source_notes)
                rule_text = administrative_rule_text_from_current_articles(rule_context)
                rule_text = filter_administrative_rule_text_to_delegated_scope(
                    rule_text,
                    delegated_scope,
                    gaps,
                    source_notes,
                )
                if rule_text.articles:
                    loaded_administrative_rules.append(rule_text)
                loaded_candidate_keys.add(candidate_identity_key(candidate))
                append_administrative_rule_not_effective_as_of_gap(
                    rule_context.rule.identity,
                    as_of,
                    gaps,
                    source_notes,
                    query=ranking_query,
                )
            except MolegApiError as exc:
                source_notes.append(f"Administrative-rule detail load skipped: {exc}")
                append_eager_detail_failure_gap(
                    exc,
                    gaps,
                    candidate=candidate,
                    recommended_interface="get_administrative_rule",
                    source_label="Delegated-criteria administrative-rule detail",
                )

        for candidate in ranked_candidates(
            annex_form_candidates,
            ranking_query,
            limit=limits["annex_forms"],
        ):
            try:
                annex_text = self.get_annex_form_body(candidate.identity)
                loaded_annex_forms.append(annex_text)
                loaded_candidate_keys.add(candidate_identity_key(candidate))
            except MolegApiError as exc:
                source_notes.append(f"Annex/form body load skipped: {exc}")
                append_eager_detail_failure_gap(
                    exc,
                    gaps,
                    candidate=candidate,
                    recommended_interface="get_annex_form_body",
                    source_label="Delegated-criteria annex/form body",
                )

        append_delegated_criteria_source_gaps(
            bundle,
            loaded_administrative_rules,
            gaps,
            source_notes,
        )
        append_delegated_criteria_annex_source_gaps(
            bundle,
            loaded_administrative_rules,
            loaded_annex_forms,
            gaps,
            source_notes,
        )

        deferred.extend(
            deferred_from_candidates(
                unloaded_candidates(administrative_candidates, loaded_candidate_keys),
                "get_administrative_rule",
                "administrative_rule",
            )
        )
        deferred.extend(
            deferred_from_candidates(
                unloaded_candidates(annex_form_candidates, loaded_candidate_keys),
                "get_annex_form_body",
                "annex_form",
            )
        )

        return replace(
            bundle,
            loaded=replace(
                bundle.loaded,
                administrative_rules=loaded_administrative_rules,
                annex_forms=loaded_annex_forms,
            ),
            candidates=replace(
                bundle.candidates,
                administrative_rules=administrative_candidates,
                annex_forms=annex_form_candidates,
            ),
            deferred=deferred,
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
        as_of: str | None = None,
    ) -> LegalContextBundle:
        """Load a staged legal context bundle for Claude inspection.

        Use when: the question is broad, under-specified, or begins from a
        statute/bill anchor and the skill needs one bounded first pass over
        likely MOLEG sources.
        Returns: `LegalContextBundle` with loaded primary law/article/delegation
        context, bounded candidates, deferred lookups, ambiguities, gaps, and
        source notes. Pass `as_of` for current-force questions that need an
        explicit reference date.
        Raises: `NoResultError` for missing required mode inputs and
        `UnsupportedFormatError` for unsupported mode or budget values; many
        source failures are recorded as `source_notes` instead of aborting.
        Related: the bundle loads sources, not conclusions. Use explicit
        loaders for selected candidates and WebSearch for non-MOLEG facts.
        """
        if articles is not None and not articles:
            raise NoResultError("articles must contain at least one article when provided")

        validate_choice("mode", mode, BUNDLE_MODE_VALUES)
        limits = bundle_limits(budget)
        reference_date = compact_date(as_of) if as_of else None
        request = BundleRequest(
            query=query,
            mode=mode,
            budget=budget,
            articles=list(articles or []),
            promulgation_bridge=dict(promulgation_bridge or {}),
            law_identifier=law_identifier,
            as_of=reference_date,
        )

        source_notes: list[str] = [
            "LegalContextBundle is staged context for Claude inspection, not a legal conclusion."
        ]
        ambiguities: list[Ambiguity] = []
        gaps: list[ContextGap] = []
        deferred: list[DeferredLookup] = []
        loaded_laws: list[LawText] = []
        loaded_articles: list[ArticleText] = []
        authority_target_articles: list[ArticleText] = []
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
            query = require_query(query)
            search_query = query
            try:
                query_expansion = self.expand_legal_query(query, display=limits["law_candidates"])
                gaps.extend(query_expansion.source_failures)
                if query_expansion.source_failures:
                    deferred.append(
                        DeferredLookup(
                            interface="expand_legal_query",
                            query=query,
                            reason="Retry query expansion after source-access recovery before treating missing planning candidates as legal absence.",
                            source_type="query_expansion",
                        )
                    )
                law_candidates = query_expansion.law_candidates[: limits["law_candidates"]]
                if len(law_candidates) == 1:
                    primary_identity = law_candidates[0]
                elif len(law_candidates) > 1:
                    ambiguities.append(
                        Ambiguity(
                            kind="statute_identity",
                            message=(
                                "Question query matched multiple MOLEG law identities; "
                                "select one LawIdentity or use statute_review before loading statute text."
                            ),
                            candidates=law_candidates,
                        )
                    )
                    gaps.append(
                        ContextGap(
                            kind="manual_review_required",
                            reason="The question matched multiple MOLEG law identities, so no statute text was auto-loaded.",
                            query=query,
                            recommended_interface="search_laws",
                        )
                    )
                    deferred.append(
                        DeferredLookup(
                            interface="search_laws",
                            query=query,
                            reason="Resolve one LawIdentity before loading current statute text.",
                            source_type="law",
                            filters={"basis": "effective"},
                        )
                    )
            except MolegApiError as exc:
                source_notes.append(f"Query expansion skipped: {exc}")
                append_query_expansion_failure_gap(
                    exc,
                    query,
                    gaps,
                    deferred,
                )
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
                        gaps=gaps,
                        deferred=deferred,
                        query=prom_law_nm,
                        recommended_interface="search_laws",
                        source_type="law",
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
            except MolegApiError as exc:
                source_notes.append(f"Promulgation bridge resolution skipped: {exc}")
                append_promulgation_bridge_resolution_failure_gap(
                    exc,
                    prom_law_nm=prom_law_nm,
                    prom_no=prom_no,
                    promulgation_dt=promulgation_dt,
                    gaps=gaps,
                    deferred=deferred,
                )
                search_query = prom_law_nm
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
                        article_context = self.load_article_context(
                            primary_identity,
                            article,
                            as_of=reference_date,
                            basis="effective",
                        )
                        loaded_articles.extend(article_context.loaded_articles)
                        gaps.extend(article_context.gaps)
                        deferred.extend(article_context.deferred)
                        source_notes.extend(article_context.source_notes)
                        if article_context.current_article is not None:
                            authority_target_articles.append(article_context.current_article)
                        for article_text in article_context.loaded_articles:
                            primary_identity = prefer_versioned_law_identity(
                                primary_identity,
                                article_text.identity,
                            )
                            append_not_effective_as_of_gap(
                                article_text.identity,
                                reference_date,
                                gaps,
                                source_notes,
                                query=search_query or primary_identity.name,
                            )
                    except MolegApiError as exc:
                        source_notes.append(f"Article load skipped for {article}: {exc}")
                        append_requested_article_load_gap(
                            exc,
                            primary_identity,
                            article,
                            gaps,
                            deferred,
                            as_of=reference_date,
                        )
            else:
                try:
                    law_text = self.get_law(primary_identity, as_of=reference_date)
                    loaded_laws.append(law_text)
                    primary_identity = law_text.identity
                    append_not_effective_as_of_gap(
                        primary_identity,
                        reference_date,
                        gaps,
                        source_notes,
                        query=search_query or primary_identity.name,
                    )
                    append_whole_law_article_status_gaps(
                        law_text,
                        gaps,
                        deferred,
                        source_notes,
                        as_of=reference_date,
                        basis="effective",
                    )
                except MolegApiError as exc:
                    source_notes.append(f"Primary law load skipped: {exc}")
                    append_requested_law_load_gap(
                        exc,
                        primary_identity,
                        gaps,
                        deferred,
                        as_of=reference_date,
                    )

            try:
                graph = self.find_delegated_rules(primary_identity)
                loaded_delegations.append(limit_delegation_graph(graph, limits["delegations"]))
            except NoResultError:
                loaded_delegations.append(DelegationGraph(identity=primary_identity, rules=[], raw={}))
                append_empty_delegation_lookup_gap(
                    primary_identity,
                    gaps,
                    deferred,
                )
            except MolegApiError as exc:
                source_notes.append(f"Delegation lookup skipped: {exc}")
                append_delegation_lookup_failure_gap(
                    exc,
                    primary_identity,
                    gaps,
                    deferred,
                )

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

        article_target_queries = [search_query] if search_query else []
        if search_query:
            if primary_identity is not None:
                article_target_queries = article_target_search_queries(
                    primary_identity,
                    list(articles or []),
                    authority_target_articles,
                    ranking_query=search_query,
                )
            administrative_candidates = dedupe_candidates(
                [
                    candidate
                    for candidate_query in article_target_queries
                    for candidate in safe_list(
                        lambda candidate_query=candidate_query: self.search_administrative_rules(
                            candidate_query,
                            display=limits["administrative_rules"],
                        ),
                        source_notes,
                        "Administrative-rule search",
                        gaps=gaps,
                        deferred=deferred,
                        query=candidate_query,
                        recommended_interface="search_administrative_rules",
                        source_type="administrative_rule",
                    )
                ]
            )[: limits["administrative_rules"]]
            interpretation_candidates = dedupe_candidates(
                [
                    candidate
                    for candidate_query in article_target_queries
                    for candidate in safe_list(
                        lambda candidate_query=candidate_query: self.search_interpretations(
                            candidate_query,
                            display=limits["interpretations"],
                        ),
                        source_notes,
                        "Interpretation search",
                        gaps=gaps,
                        deferred=deferred,
                        query=candidate_query,
                        recommended_interface="search_interpretations",
                        source_type="interpretation",
                    )
                ]
            )
            case_candidates = dedupe_candidates(
                [
                    candidate
                    for candidate_query in article_target_queries
                    for candidate in safe_list(
                        lambda candidate_query=candidate_query: self.search_cases(
                            candidate_query,
                            display=limits["cases"],
                        ),
                        source_notes,
                        "Case search",
                        gaps=gaps,
                        deferred=deferred,
                        query=candidate_query,
                        recommended_interface="search_cases",
                        source_type="case",
                    )
                ]
            )
            constitutional_candidates = dedupe_candidates(
                [
                    candidate
                    for candidate_query in article_target_queries
                    for candidate in safe_list(
                        lambda candidate_query=candidate_query: self.search_constitutional_decisions(
                            candidate_query,
                            display=limits["constitutional_decisions"],
                        ),
                        source_notes,
                        "Constitutional decision search",
                        gaps=gaps,
                        deferred=deferred,
                        query=candidate_query,
                        recommended_interface="search_constitutional_decisions",
                        source_type="constitutional",
                    )
                ]
            )
            annex_form_limit = limits["annex_forms"]
            law_annex_limit = (annex_form_limit + 1) // 2
            admin_annex_limit = max(1, annex_form_limit - law_annex_limit)
            annex_form_candidates = [
                *dedupe_candidates(
                    [
                        candidate
                        for candidate_query in article_target_queries
                        for candidate in safe_list(
                            lambda candidate_query=candidate_query: self.search_annex_forms(
                                candidate_query,
                                source="law",
                                search_scope="source",
                                display=law_annex_limit,
                            ),
                            source_notes,
                            "Law annex/form search",
                            gaps=gaps,
                            deferred=deferred,
                            query=candidate_query,
                            recommended_interface="search_annex_forms",
                            source_type="annex_form",
                            filters={"source": "law", "search_scope": "source"},
                        )
                    ]
                )[:law_annex_limit],
                *dedupe_candidates(
                    [
                        candidate
                        for candidate_query in article_target_queries
                        for candidate in safe_list(
                            lambda candidate_query=candidate_query: self.search_annex_forms(
                                candidate_query,
                                source="administrative_rule",
                                search_scope="source",
                                display=admin_annex_limit,
                            ),
                            source_notes,
                            "Administrative-rule annex/form search",
                            gaps=gaps,
                            deferred=deferred,
                            query=candidate_query,
                            recommended_interface="search_annex_forms",
                            source_type="annex_form",
                            filters={"source": "administrative_rule", "search_scope": "source"},
                        )
                    ]
                )[:admin_annex_limit],
            ][:annex_form_limit]

        eager_detail_limits = bundle_eager_detail_limits(search_query, mode=mode, budget=budget)
        if any(item.kind == "statute_identity" for item in ambiguities):
            eager_detail_limits = {key: 0 for key in eager_detail_limits}
            source_notes.append(
                "Eager authority detail loading skipped until statute identity ambiguity is resolved."
            )
        authority_ranking_query = " ".join(article_target_queries) if search_query else search_query
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
            authority_ranking_query,
            limit=eager_detail_limits["interpretations"],
        ):
            key = candidate_identity_key(candidate)
            try:
                text = self.get_interpretation(candidate.identity, include_metadata=False)
            except MolegApiError as exc:
                source_notes.append(f"Eager interpretation detail load skipped: {exc}")
                append_eager_detail_failure_gap(
                    exc,
                    gaps,
                    candidate=candidate,
                    recommended_interface="get_interpretation",
                    source_label="Eager interpretation detail load",
                )
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
            authority_ranking_query,
            limit=eager_detail_limits["cases"],
        ):
            key = candidate_identity_key(candidate)
            try:
                text = self.get_case(candidate.identity, include_metadata=False)
            except MolegApiError as exc:
                source_notes.append(f"Eager case detail load skipped: {exc}")
                append_eager_detail_failure_gap(
                    exc,
                    gaps,
                    candidate=candidate,
                    recommended_interface="get_case",
                    source_label="Eager case detail load",
                )
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
            authority_ranking_query,
            limit=eager_detail_limits["constitutional_decisions"],
        ):
            key = candidate_identity_key(candidate)
            try:
                text = self.get_constitutional_decision(candidate.identity, include_metadata=False)
            except MolegApiError as exc:
                source_notes.append(f"Eager constitutional detail load skipped: {exc}")
                append_eager_detail_failure_gap(
                    exc,
                    gaps,
                    candidate=candidate,
                    recommended_interface="get_constitutional_decision",
                    source_label="Eager constitutional detail load",
                )
                continue
            text_length = len(text.text)
            if eager_text_used + text_length > eager_text_budget:
                source_notes.append("Eager constitutional detail load skipped: text budget exceeded")
                continue
            eager_text_used += text_length
            loaded_constitutional_decisions.append(text)
            loaded_detail_keys.add(key)

        append_authority_article_mismatch_gaps(
            target_article_refs_from_loaded_articles(authority_target_articles),
            interpretations=loaded_interpretations,
            cases=loaded_cases,
            constitutional_decisions=loaded_constitutional_decisions,
            gaps=gaps,
        )
        append_authority_temporal_mismatch_gaps(
            authority_target_articles,
            interpretations=loaded_interpretations,
            cases=loaded_cases,
            constitutional_decisions=loaded_constitutional_decisions,
            gaps=gaps,
            deferred=deferred,
            reference_date=reference_date,
        )

        deferred.extend(
            deferred_from_candidates(
                administrative_candidates,
                "get_administrative_rule",
                "administrative_rule",
            )
        )
        deferred.extend(
            deferred_from_candidates(
                annex_form_candidates,
                "get_annex_form_body",
                "annex_form",
            )
        )
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
        *,
        source_failures: list[ContextGap] | None = None,
        source_label: str | None = None,
    ) -> list[dict[str, Any]]:
        try:
            payload = self.source.service(target, params)
        except MolegApiError as exc:
            if source_failures is not None:
                append_source_failure_gap(
                    exc,
                    source_failures,
                    query=string_value(params.get("query")),
                    recommended_interface="expand_legal_query",
                    source_label=source_label or f"Query-expansion {target} lookup",
                )
            return []
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


def require_query(query: Any) -> str:
    normalized = string_value(query)
    normalized = normalized.strip() if normalized else None
    if not normalized:
        raise NoResultError("query is required")
    return normalized


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


def matches_bridge(
    identity: LawIdentity,
    *,
    prom_no: str | None,
    promulgation_dt: str | None,
) -> bool:
    if prom_no and (
        compact_promulgation_number(identity.promulgation_number) != compact_promulgation_number(prom_no)
    ):
        return False
    if promulgation_dt and compact_date(identity.promulgation_date) != compact_date(promulgation_dt):
        return False
    return True


def append_not_effective_as_of_gap(
    identity: LawIdentity,
    as_of: str | None,
    gaps: list[ContextGap],
    source_notes: list[str],
    *,
    query: str | None,
) -> None:
    effective_date = compact_date(identity.effective_date)
    reference_date = compact_date(as_of)
    if not is_compact_ymd(effective_date) or not is_compact_ymd(reference_date):
        return
    if effective_date <= reference_date:
        return
    gaps.append(
        ContextGap(
            kind="not_effective_as_of",
            reason=(
                f"{identity.name} has effective date {effective_date}, "
                f"so it is not effective as of {reference_date}."
            ),
            query=query or identity.name,
            recommended_interface="load_legal_context_bundle",
        )
    )
    source_notes.append(
        f"{identity.name} is promulgated/source-loadable but not effective as of {reference_date}; "
        f"effective date is {effective_date}."
    )


def append_administrative_rule_not_effective_as_of_gap(
    identity: AdministrativeRuleIdentity,
    as_of: str | None,
    gaps: list[ContextGap],
    source_notes: list[str],
    *,
    query: str | None,
) -> None:
    effective_date = compact_date(identity.effective_date)
    reference_date = compact_date(as_of)
    if not is_compact_ymd(effective_date) or not is_compact_ymd(reference_date):
        return
    if effective_date <= reference_date:
        return
    gaps.append(
        ContextGap(
            kind="not_effective_as_of",
            reason=(
                f"{identity.name} has administrative-rule effective date {effective_date}, "
                f"so it is not effective as of {reference_date}."
            ),
            query=query or identity.name,
            recommended_interface="load_delegated_criteria",
        )
    )
    source_notes.append(
        f"{identity.name} is loaded but not effective as of {reference_date}; "
        f"administrative-rule effective date is {effective_date}."
    )


def append_delegated_criteria_source_gaps(
    bundle: LegalContextBundle,
    administrative_rules: list[AdministrativeRuleText],
    gaps: list[ContextGap],
    source_notes: list[str],
) -> None:
    scope = delegated_criteria_target_scope(bundle)
    if not administrative_rules or (not scope["law_names"] and not scope["law_ids"]):
        return
    for rule in administrative_rules:
        match_state, source_label = delegated_criteria_source_match_state(rule, scope)
        if match_state == "matched":
            continue
        query = delegated_criteria_scope_label(scope)
        if match_state == "unverified":
            reason = (
                f"{rule.identity.name} was loaded as delegated criteria, but its source-law "
                f"or source-article reference is missing for {query}; inspect delegation "
                "metadata before treating it as target operational criteria."
            )
            kind = "delegated_criteria_source_unverified"
        else:
            reason = (
                f"{rule.identity.name} was loaded as delegated criteria, but its explicit "
                f"source reference ({source_label}) does not match {query}; do not cite it "
                "as target operational criteria without another delegation source."
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


def append_delegated_criteria_annex_source_gaps(
    bundle: LegalContextBundle,
    administrative_rules: list[AdministrativeRuleText],
    annex_forms: list[AnnexFormText],
    gaps: list[ContextGap],
    source_notes: list[str],
) -> None:
    scope = delegated_criteria_annex_target_scope(bundle, administrative_rules)
    if not annex_forms or (not scope["law_names"] and not scope["law_ids"]):
        return
    for annex in annex_forms:
        match_state, source_label = delegated_criteria_annex_source_match_state(annex, scope)
        if match_state == "matched":
            continue
        query = delegated_criteria_scope_label(scope)
        if match_state == "unverified":
            reason = (
                f"{annex.identity.title} was loaded as delegated criteria, but its "
                f"source-law or source-rule reference is missing for {query}; inspect "
                "attached-material metadata before treating it as target operational criteria."
            )
            kind = "delegated_criteria_annex_source_unverified"
        else:
            reason = (
                f"{annex.identity.title} was loaded as delegated criteria, but its explicit "
                f"attached-material source reference ({source_label}) does not match {query}; "
                "do not cite it as target operational criteria without another source."
            )
            kind = "delegated_criteria_annex_source_mismatch"
        gaps.append(
            ContextGap(
                kind=kind,
                reason=reason,
                query=query,
                recommended_interface="search_annex_forms",
            )
        )
        source_notes.append(reason)


def delegated_criteria_annex_target_scope(
    bundle: LegalContextBundle,
    administrative_rules: list[AdministrativeRuleText],
) -> dict[str, set[str]]:
    scope = delegated_criteria_target_scope(bundle)
    scope["administrative_rule_names"] = set()
    scope["administrative_rule_ids"] = set()
    scope["administrative_rule_serial_ids"] = set()
    for rule in administrative_rules:
        match_state, _ = delegated_criteria_source_match_state(rule, scope)
        if match_state != "matched":
            continue
        if rule.identity.name:
            scope["administrative_rule_names"].add(rule.identity.name)
        if rule.identity.rule_id:
            scope["administrative_rule_ids"].add(rule.identity.rule_id)
        if rule.identity.serial_id:
            scope["administrative_rule_serial_ids"].add(rule.identity.serial_id)
    return scope


def delegated_criteria_target_scope(bundle: LegalContextBundle) -> dict[str, set[str]]:
    law_ids: set[str] = set()
    law_msts: set[str] = set()
    law_names: set[str] = set()
    articles: set[str] = {
        comparable_article_label(article)
        for article in bundle.request.articles
        if comparable_article_label(article)
    }
    for law in bundle.loaded.laws:
        if law.identity.law_id:
            law_ids.add(law.identity.law_id)
        if law.identity.mst:
            law_msts.add(law.identity.mst)
        if law.identity.name:
            law_names.add(law.identity.name)
    for article in bundle.loaded.articles:
        if article.identity.law_id:
            law_ids.add(article.identity.law_id)
        if article.identity.mst:
            law_msts.add(article.identity.mst)
        if article.identity.name:
            law_names.add(article.identity.name)
        if article.article:
            articles.add(comparable_article_label(article.article))
    for graph in bundle.loaded.delegations:
        if graph.identity.law_id:
            law_ids.add(graph.identity.law_id)
        if graph.identity.mst:
            law_msts.add(graph.identity.mst)
        if graph.identity.name:
            law_names.add(graph.identity.name)
    return {"law_ids": law_ids, "law_msts": law_msts, "law_names": law_names, "articles": articles}


def delegated_criteria_scope_label(scope: dict[str, set[str]]) -> str:
    law_label = ", ".join(sorted(scope["law_names"] or scope["law_ids"]))
    article_label = ", ".join(sorted(scope["articles"]))
    return f"{law_label} {article_label}".strip()


def delegated_criteria_source_match_state(
    rule: AdministrativeRuleText,
    scope: dict[str, set[str]],
) -> tuple[str, str]:
    references = administrative_rule_source_references(rule)
    if not references:
        return ("unverified", "missing source reference")
    matching_law_refs = [
        reference
        for reference in references
        if source_law_matches_scope(reference, scope)
    ]
    if not matching_law_refs:
        return ("mismatch", administrative_rule_source_reference_label(references))
    if not scope["articles"]:
        return ("matched", administrative_rule_source_reference_label(matching_law_refs))
    article_refs = [
        reference
        for reference in matching_law_refs
        if reference["article"]
    ]
    if not article_refs:
        return ("unverified", administrative_rule_source_reference_label(matching_law_refs))
    if any(
        articles_overlap(reference["article"], target_article)
        for reference in article_refs
        for target_article in scope["articles"]
    ):
        return ("matched", administrative_rule_source_reference_label(article_refs))
    return ("mismatch", administrative_rule_source_reference_label(article_refs))


def delegated_criteria_annex_source_match_state(
    annex: AnnexFormText,
    scope: dict[str, set[str]],
) -> tuple[str, str]:
    reference = annex_form_source_reference(annex.identity)
    if not annex_form_has_related_source_reference(reference):
        return ("unverified", "missing attached-material source reference")
    source_label = annex_form_source_reference_label(reference)
    if annex.identity.source_type == "law":
        if annex_law_reference_matches_scope(reference, scope):
            return ("matched", source_label)
        return ("mismatch", source_label)
    if annex.identity.source_type == "administrative_rule":
        if not (
            scope["administrative_rule_names"]
            or scope["administrative_rule_ids"]
            or scope["administrative_rule_serial_ids"]
        ):
            return ("unverified", source_label)
        if annex_administrative_rule_reference_matches_scope(reference, scope):
            return ("matched", source_label)
        return ("mismatch", source_label)
    return ("unverified", source_label)


def annex_form_source_reference(identity: AnnexFormIdentity) -> dict[str, str | None]:
    return {
        "source_type": identity.source_type,
        "related_name": identity.related_name,
        "related_id": identity.related_id,
        "related_serial_id": identity.related_serial_id,
    }


def annex_form_has_related_source_reference(reference: dict[str, str | None]) -> bool:
    return bool(
        reference["related_name"]
        or reference["related_id"]
        or reference["related_serial_id"]
    )


def annex_law_reference_matches_scope(
    reference: dict[str, str | None],
    scope: dict[str, set[str]],
) -> bool:
    return bool(
        (reference["related_id"] and reference["related_id"] in scope["law_ids"])
        or (
            reference["related_serial_id"]
            and reference["related_serial_id"] in scope["law_msts"]
        )
        or (reference["related_name"] and reference["related_name"] in scope["law_names"])
    )


def annex_administrative_rule_reference_matches_scope(
    reference: dict[str, str | None],
    scope: dict[str, set[str]],
) -> bool:
    return bool(
        (
            reference["related_id"]
            and reference["related_id"] in scope["administrative_rule_ids"]
        )
        or (
            reference["related_serial_id"]
            and reference["related_serial_id"] in scope["administrative_rule_serial_ids"]
        )
        or (
            reference["related_name"]
            and reference["related_name"] in scope["administrative_rule_names"]
        )
    )


def annex_form_source_reference_label(reference: dict[str, str | None]) -> str:
    parts = [
        value
        for value in (
            reference["source_type"],
            reference["related_name"],
            reference["related_id"],
            reference["related_serial_id"],
        )
        if value
    ]
    return " ".join(parts) if parts else "missing source reference"


def administrative_rule_source_references(rule: AdministrativeRuleText) -> list[dict[str, str | None]]:
    references: list[dict[str, str | None]] = []
    raw_references = [
        {
            "law_id": rule.identity.source_law_id,
            "law_name": rule.identity.source_law_name,
            "article": rule.identity.source_article,
        },
        *[
            {
                "law_id": article.source_law_id,
                "law_name": article.source_law_name,
                "article": article.source_article,
            }
            for article in rule.articles
        ],
    ]
    seen: set[tuple[str | None, str | None, str | None]] = set()
    for reference in raw_references:
        if not any(reference.values()):
            continue
        normalized = {
            "law_id": reference["law_id"],
            "law_name": reference["law_name"],
            "article": comparable_article_label(reference["article"]),
        }
        key = (normalized["law_id"], normalized["law_name"], normalized["article"])
        if key in seen:
            continue
        seen.add(key)
        references.append(normalized)
    return references


def source_law_matches_scope(
    reference: dict[str, str | None],
    scope: dict[str, set[str]],
) -> bool:
    return bool(
        (reference["law_id"] and reference["law_id"] in scope["law_ids"])
        or (reference["law_name"] and reference["law_name"] in scope["law_names"])
    )


def administrative_rule_source_reference_label(
    references: list[dict[str, str | None]],
) -> str:
    return ", ".join(
        " ".join(
            part
            for part in (
                reference["law_name"] or reference["law_id"] or "unknown law",
                reference["article"],
            )
            if part
        )
        for reference in references
    )


def comparable_article_label(value: Any) -> str:
    if value in (None, ""):
        return ""
    return re.sub(r"\s+", "", article_label_for_filter(value))


def articles_overlap(first: str | None, second: str | None) -> bool:
    left = comparable_article_label(first)
    right = comparable_article_label(second)
    if not left or not right:
        return False
    return (
        left == right
        or (left.startswith(right) and left[len(right):].startswith("제"))
        or (right.startswith(left) and right[len(left):].startswith("제"))
    )


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
    text = str(identifier).strip()
    if not text:
        raise NoResultError("Administrative-rule identifier is required")
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
    text = str(article).strip()
    if text.startswith("제"):
        return text
    if re.fullmatch(r"\d{6}", text):
        main = int(text[:4])
        branch = int(text[4:])
        return f"제{main}조의{branch}" if branch else f"제{main}조"
    match = re.fullmatch(r"(\d+)\s*조(?:\s*의\s*(\d+))?", text)
    if match:
        main = int(match.group(1))
        branch = int(match.group(2) or 0)
        return f"제{main}조의{branch}" if branch else f"제{main}조"
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


def attach_interpretation_source_failures(
    hits: list[InterpretationHit],
    source_failures: list[ContextGap],
) -> list[InterpretationHit]:
    failures = source_failure_payloads(source_failures)
    return [
        InterpretationHit(
            identity=replace(
                hit.identity,
                raw_keys={**hit.identity.raw_keys, "source_failures": failures},
            ),
            raw=hit.raw,
        )
        for hit in hits
    ]


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
    text = str(identifier).strip()
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
    text = str(identifier).strip()
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


def append_authority_article_mismatch_gaps(
    targets: set[tuple[str, str]],
    *,
    interpretations: list[InterpretationText],
    cases: list[JudicialDecisionText],
    constitutional_decisions: list[JudicialDecisionText],
    gaps: list[ContextGap],
) -> None:
    if not targets:
        return

    target_label = article_ref_label(targets)
    authority_groups: list[tuple[str, str, str, str, list[list[Any]]]] = [
        (
            "interpretation",
            "search_interpretations",
            "Eager-loaded interpretation detail references articles outside",
            "Eager-loaded interpretation detail has no structured article references for",
            [item.referenced_articles for item in interpretations],
        ),
        (
            "case",
            "search_cases",
            "Eager-loaded court-case detail references articles outside",
            "Eager-loaded court-case detail has no structured article references for",
            [item.referenced_articles for item in cases],
        ),
        (
            "constitutional",
            "search_constitutional_decisions",
            "Eager-loaded Constitutional Court detail reviews articles outside",
            "Eager-loaded Constitutional Court detail has no structured reviewed articles for",
            [item.reviewed_articles for item in constitutional_decisions],
        ),
    ]
    for source_type, interface, mismatch_reason_prefix, unverified_reason_prefix, reference_sets in authority_groups:
        if not reference_sets:
            continue
        has_unverified = any(not references for references in reference_sets)
        structured_reference_sets = [references for references in reference_sets if references]
        if has_unverified:
            gaps.append(
                ContextGap(
                    kind="authority_article_unverified",
                    reason=(
                        f"{unverified_reason_prefix} {target_label}; run {interface} or inspect "
                        "source article references before making target-article "
                        f"{source_type} authority claims."
                    ),
                    query=target_label,
                    recommended_interface=interface,
                )
            )
        if not structured_reference_sets:
            continue

        has_mismatch = False
        missing_targets: set[tuple[str, str]] = set()
        for references in structured_reference_sets:
            matched_targets = article_refs_matching_targets([references], targets)
            if not matched_targets:
                has_mismatch = True
                continue
            if matched_targets != targets:
                missing_targets.update(targets - matched_targets)

        if missing_targets:
            missing_target_label = article_ref_label(missing_targets)
            gaps.append(
                ContextGap(
                    kind="authority_article_partial_match",
                    reason=(
                        f"Eager-loaded {source_type} detail matches only some requested articles; "
                        f"run {interface} before making target-article {source_type} authority claims "
                        f"for {missing_target_label}."
                    ),
                    query=missing_target_label,
                    recommended_interface=interface,
                )
            )
        if not has_mismatch:
            continue
        gaps.append(
            ContextGap(
                kind="authority_article_mismatch",
                reason=(
                    f"{mismatch_reason_prefix} {target_label}; run {interface} before making "
                    f"target-article {source_type} authority claims."
                ),
                query=target_label,
                recommended_interface=interface,
            )
        )


def append_authority_temporal_mismatch_gaps(
    target_articles: list[ArticleText],
    *,
    interpretations: list[InterpretationText],
    cases: list[JudicialDecisionText],
    constitutional_decisions: list[JudicialDecisionText],
    gaps: list[ContextGap],
    deferred: list[DeferredLookup],
    reference_date: str | None = None,
) -> None:
    reference_date = compact_date(reference_date)
    raw_target_effective_dates = {
        (article.identity.name, article.article): compact_date(
            article.effective_date or article.identity.effective_date
        )
        for article in target_articles
        if article.identity.name and article.article
    }
    target_refs = set(raw_target_effective_dates)
    target_effective_dates = {
        target: effective_date
        for target, effective_date in raw_target_effective_dates.items()
        if is_compact_ymd(effective_date)
    }
    if not target_refs:
        return

    authority_groups: list[tuple[str, list[tuple[str | None, list[Any]]]]] = [
        (
            "interpretation",
            [(item.identity.interpretation_date, item.referenced_articles) for item in interpretations],
        ),
        (
            "case",
            [(item.identity.decision_date, item.referenced_articles) for item in cases],
        ),
        (
            "constitutional",
            [(item.identity.decision_date, item.reviewed_articles) for item in constitutional_decisions],
        ),
    ]
    emitted: set[tuple[str, tuple[str, str], str]] = set()
    for source_type, authority_items in authority_groups:
        for authority_date_value, references in authority_items:
            authority_date = compact_date(authority_date_value)
            for reference in references:
                target = (reference.law_name, reference.article)
                if target not in target_refs:
                    continue
                effective_date = target_effective_dates.get(target)
                target_label = article_ref_label({target})
                if not is_compact_ymd(authority_date):
                    if not effective_date and not is_compact_ymd(reference_date):
                        continue
                    key = (source_type, target, "unverified")
                    if key in emitted:
                        continue
                    emitted.add(key)
                    gaps.append(
                        ContextGap(
                            kind="authority_temporal_mismatch",
                            reason=(
                                f"Eager-loaded {source_type} detail for {target_label} has a missing "
                                f"or unparseable authority date, while the loaded article effective date is "
                                f"{effective_date or 'unknown'}"
                                f"{authority_reference_date_phrase(reference_date)}; run trace_law_history "
                                "or inspect the authority-date source before treating it as current "
                                "target-article authority."
                            ),
                            query=target_label,
                            recommended_interface="trace_law_history",
                        )
                    )
                    deferred.append(
                        DeferredLookup(
                            interface="trace_law_history",
                            query=target_label,
                            reason=(
                                f"Check whether {target_label} changed before citing undated {source_type} "
                                f"authority against current effective date {effective_date}."
                            ),
                            source_type="authority_temporal_mismatch",
                            filters={
                                "law_name": target[0],
                                "article": target[1],
                                "authority_source_type": source_type,
                                "authority_date": None,
                                **authority_temporal_filter_dates(effective_date, reference_date),
                            },
                        )
                    )
                    continue
                if is_compact_ymd(reference_date) and authority_date > reference_date:
                    key = (source_type, target, f"after-reference:{authority_date}")
                    if key in emitted:
                        continue
                    emitted.add(key)
                    followup_interface = authority_search_interface(source_type)
                    gaps.append(
                        ContextGap(
                            kind="authority_temporal_mismatch",
                            reason=(
                                f"Eager-loaded {source_type} detail for {target_label} is dated "
                                f"{authority_date}, after the reference date {reference_date}; "
                                "search for authority available on or before the reference date before treating "
                                "it as as-of target-article authority."
                            ),
                            query=target_label,
                            recommended_interface=followup_interface,
                        )
                    )
                    deferred.append(
                        DeferredLookup(
                            interface=followup_interface,
                            query=target_label,
                            reason=(
                                f"Find {source_type} authority for {target_label} that existed on or before "
                                f"reference date {reference_date}; loaded authority date {authority_date} is later."
                            ),
                            source_type="authority_temporal_mismatch",
                            filters={
                                "law_name": target[0],
                                "article": target[1],
                                "authority_source_type": source_type,
                                "authority_date": authority_date,
                                **authority_temporal_filter_dates(effective_date, reference_date),
                            },
                        )
                    )
                    continue
                if not effective_date:
                    continue
                if authority_date >= effective_date:
                    continue
                key = (source_type, target, authority_date)
                if key in emitted:
                    continue
                emitted.add(key)
                gaps.append(
                    ContextGap(
                        kind="authority_temporal_mismatch",
                        reason=(
                            f"Eager-loaded {source_type} detail for {target_label} is dated "
                            f"{authority_date}, before the loaded article's effective date {effective_date}; "
                            "run trace_law_history or load the article as of the authority date before treating "
                            "it as current target-article authority."
                        ),
                        query=target_label,
                        recommended_interface="trace_law_history",
                    )
                )
                deferred.append(
                    DeferredLookup(
                        interface="trace_law_history",
                        query=target_label,
                        reason=(
                            f"Check whether {target_label} changed between {source_type} authority date "
                            f"{authority_date} and current effective date {effective_date}."
                        ),
                        source_type="authority_temporal_mismatch",
                        filters={
                            "law_name": target[0],
                            "article": target[1],
                            "authority_source_type": source_type,
                            "authority_date": authority_date,
                            **authority_temporal_filter_dates(effective_date, reference_date),
                        },
                    )
                )


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


def safe_list(
    fn: Any,
    source_notes: list[str],
    label: str,
    *,
    gaps: list[ContextGap] | None = None,
    deferred: list[DeferredLookup] | None = None,
    query: str | None = None,
    recommended_interface: str | None = None,
    source_type: str | None = None,
    filters: dict[str, Any] | None = None,
    reason: str | None = None,
) -> list[Any]:
    try:
        return fn()
    except MolegApiError as exc:
        source_notes.append(f"{label} skipped: {exc}")
        if gaps is not None and recommended_interface is not None:
            append_source_failure_gap(
                exc,
                gaps,
                query=query,
                recommended_interface=recommended_interface,
                source_label=label,
            )
        if deferred is not None and recommended_interface is not None:
            deferred.append(
                DeferredLookup(
                    interface=recommended_interface,
                    query=str(query or ""),
                    reason=reason
                    or f"Retry {label} after source-access recovery before treating missing candidates as absence.",
                    source_type=source_type,
                    filters=dict(filters or {}),
                )
            )
        return []


def append_source_failure_gap(
    exc: MolegApiError,
    gaps: list[ContextGap],
    *,
    query: str | None,
    recommended_interface: str,
    source_label: str,
) -> None:
    gap_kind = "source_access_failure" if isinstance(exc, SourceApiError) else "source_loading_failed"
    gaps.append(
        ContextGap(
            kind=gap_kind,
            reason=f"{source_label} failed with {type(exc).__name__}: {exc}",
            query=query,
            recommended_interface=recommended_interface,
        )
    )


def source_failure_payloads(source_failures: list[ContextGap]) -> list[dict[str, str | None]]:
    return [
        {
            "kind": gap.kind,
            "reason": gap.reason,
            "query": gap.query,
            "recommended_interface": gap.recommended_interface,
        }
        for gap in source_failures
    ]


def append_eager_detail_failure_gap(
    exc: MolegApiError,
    gaps: list[ContextGap],
    *,
    candidate: Any,
    recommended_interface: str,
    source_label: str,
) -> None:
    identity = getattr(candidate, "identity", None)
    query_value = (
        getattr(identity, "title", None)
        or getattr(identity, "name", None)
        or getattr(identity, "interpretation_id", None)
        or getattr(identity, "decision_id", None)
        or getattr(identity, "serial_id", None)
    )
    append_source_failure_gap(
        exc,
        gaps,
        query=str(query_value) if query_value else None,
        recommended_interface=recommended_interface,
        source_label=source_label,
    )


def append_query_expansion_failure_gap(
    exc: MolegApiError,
    query: str,
    gaps: list[ContextGap],
    deferred: list[DeferredLookup],
) -> None:
    append_source_failure_gap(
        exc,
        gaps,
        query=query,
        recommended_interface="expand_legal_query",
        source_label="Query expansion",
    )
    deferred.append(
        DeferredLookup(
            interface="expand_legal_query",
            query=query,
            reason="Retry query expansion before treating missing planning candidates as a legal absence.",
            source_type="query_expansion",
        )
    )


def append_institutional_statute_resolution_failure_gap(
    exc: MolegApiError,
    query: str,
    gaps: list[ContextGap],
    deferred: list[DeferredLookup],
) -> None:
    append_source_failure_gap(
        exc,
        gaps,
        query=query,
        recommended_interface="search_laws",
        source_label=f"Institutional statute resolution for {query}",
    )
    deferred.append(
        DeferredLookup(
            interface="search_laws",
            query=query,
            reason="Retry statute identity resolution before treating this institutional-system member as unavailable.",
            source_type="law",
        )
    )


def append_promulgation_bridge_resolution_failure_gap(
    exc: MolegApiError,
    *,
    prom_law_nm: str | None,
    prom_no: str | None,
    promulgation_dt: str | None,
    gaps: list[ContextGap],
    deferred: list[DeferredLookup],
) -> None:
    query = prom_law_nm or prom_no
    append_source_failure_gap(
        exc,
        gaps,
        query=query,
        recommended_interface="resolve_promulgated_law",
        source_label="Promulgation bridge resolution",
    )
    filters = {
        key: value
        for key, value in {
            "prom_law_nm": prom_law_nm,
            "prom_no": prom_no,
            "promulgation_dt": promulgation_dt,
        }.items()
        if value
    }
    deferred.append(
        DeferredLookup(
            interface="resolve_promulgated_law",
            query=str(query or ""),
            reason="Retry the strict congress-db promulgation bridge before treating the bill as not enacted or unavailable in MOLEG.",
            source_type="law",
            filters=filters,
        )
    )


def append_requested_article_load_gap(
    exc: MolegApiError,
    identity: LawIdentity,
    article: str | int,
    gaps: list[ContextGap],
    deferred: list[DeferredLookup],
    *,
    as_of: str | None,
) -> None:
    article_label = article_label_for_filter(article)
    query = f"{identity.name} {article_label}"
    gap_kind = "source_access_failure" if isinstance(exc, SourceApiError) else "requested_article_not_loaded"
    gaps.append(
        ContextGap(
            kind=gap_kind,
            reason=f"Requested article load failed with {type(exc).__name__}: {exc}",
            query=query,
            recommended_interface="get_article",
        )
    )
    filters = {"article": article_label}
    if identity.law_id:
        filters["law_id"] = identity.law_id
    elif identity.mst:
        filters["mst"] = identity.mst
    else:
        filters["law_name"] = identity.name
    if as_of:
        filters["as_of"] = as_of
    deferred.append(
        DeferredLookup(
            interface="get_article",
            query=query,
            reason="Load the requested article before relying on current target-article text.",
            source_type="law_article",
            filters=filters,
        )
    )


def append_requested_law_load_gap(
    exc: MolegApiError,
    identity: LawIdentity,
    gaps: list[ContextGap],
    deferred: list[DeferredLookup],
    *,
    as_of: str | None,
) -> None:
    gap_kind = "source_access_failure" if isinstance(exc, SourceApiError) else "requested_law_not_loaded"
    gaps.append(
        ContextGap(
            kind=gap_kind,
            reason=f"Requested law load failed with {type(exc).__name__}: {exc}",
            query=identity.name,
            recommended_interface="get_law",
        )
    )
    filters: dict[str, Any] = {"basis": identity.basis}
    if identity.law_id:
        filters["law_id"] = identity.law_id
    elif identity.mst:
        filters["mst"] = identity.mst
    else:
        filters["law_name"] = identity.name
    if as_of:
        filters["as_of"] = as_of
    deferred.append(
        DeferredLookup(
            interface="get_law",
            query=identity.name,
            reason="Load the law text before relying on whole-statute current-law context.",
            source_type="law",
            filters=filters,
        )
    )


def append_delegation_lookup_failure_gap(
    exc: MolegApiError,
    identity: LawIdentity,
    gaps: list[ContextGap],
    deferred: list[DeferredLookup],
) -> None:
    append_source_failure_gap(
        exc,
        gaps,
        query=identity.name,
        recommended_interface="find_delegated_rules",
        source_label=f"Delegation lookup for {identity.name}",
    )
    filters: dict[str, Any] = {}
    if identity.law_id:
        filters["law_id"] = identity.law_id
    elif identity.mst:
        filters["mst"] = identity.mst
    else:
        filters["law_name"] = identity.name
    deferred.append(
        DeferredLookup(
            interface="find_delegated_rules",
            query=identity.name,
            reason="Retry delegation lookup before assuming lower-rule context is unavailable.",
            source_type="delegation",
            filters=filters,
        )
    )


def append_empty_delegation_lookup_gap(
    identity: LawIdentity,
    gaps: list[ContextGap],
    deferred: list[DeferredLookup],
    *,
    recommended_interface: str = "get_law_structure",
    deferred_interface: str | None = "get_law_structure",
    deferred_source_type: str | None = "law_structure",
    deferred_reason: str | None = None,
) -> None:
    gaps.append(
        ContextGap(
            kind="empty_delegation_graph",
            reason=(
                "find_delegated_rules returned no delegated rows for this scoped lookup. "
                "Do not treat one empty delegation graph as proof that no lower-rule, "
                "subordinate source, notice, annex, or delegated criteria exists."
            ),
            query=identity.name,
            recommended_interface=recommended_interface,
        )
    )
    if deferred_interface is None:
        return
    filters: dict[str, Any] = {}
    if identity.law_id:
        filters["law_id"] = identity.law_id
    elif identity.mst:
        filters["mst"] = identity.mst
    else:
        filters["law_name"] = identity.name
    deferred.append(
        DeferredLookup(
            interface=deferred_interface,
            query=identity.name,
            reason=deferred_reason or (
                "Load law hierarchy or alternate lower-rule paths before making "
                "any no-delegated-rule or no-delegated-criteria claim."
            ),
            source_type=deferred_source_type,
            filters=filters,
        )
    )


def append_law_structure_load_gap(
    exc: MolegApiError,
    identity: LawIdentity,
    gaps: list[ContextGap],
    deferred: list[DeferredLookup],
) -> None:
    gap_kind = "source_access_failure" if isinstance(exc, SourceApiError) else "law_structure_not_loaded"
    gaps.append(
        ContextGap(
            kind=gap_kind,
            reason=f"Law-structure lookup failed with {type(exc).__name__}: {exc}",
            query=identity.name,
            recommended_interface="get_law_structure",
        )
    )
    filters: dict[str, Any] = {"depth": 1}
    if identity.law_id:
        filters["law_id"] = identity.law_id
    elif identity.mst:
        filters["mst"] = identity.mst
    else:
        filters["law_name"] = identity.name
    deferred.append(
        DeferredLookup(
            interface="get_law_structure",
            query=identity.name,
            reason="Load hierarchy context before claiming lower instruments are unavailable.",
            source_type="law_structure",
            filters=filters,
        )
    )


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
            or getattr(identity, "annex_id", None)
        )
        if not title and not source_id:
            continue
        lookup_source_type = source_type
        if isinstance(identity, AnnexFormIdentity):
            lookup_source_type = "annex_form"
        elif identity is not None:
            lookup_source_type = getattr(identity, "source_type", source_type)
        deferred.append(
            DeferredLookup(
                interface=interface,
                query=str(title or source_id),
                reason="Load full text only if Claude needs this candidate after ranking the bundle.",
                source_type=lookup_source_type,
                filters=deferred_lookup_filters(identity, source_id),
            )
        )
    return deferred


def deferred_lookup_filters(identity: Any, source_id: Any) -> dict[str, Any]:
    filters: dict[str, Any] = {}
    if source_id:
        filters["id"] = str(source_id)
    if isinstance(identity, AnnexFormIdentity):
        if identity.annex_id:
            filters["annex_id"] = identity.annex_id
        filters["source"] = identity.source_type
        filters["source_target"] = identity.source_target
        if identity.related_name:
            filters["related_name"] = identity.related_name
    return filters


def delegated_criteria_ranking_query(bundle: LegalContextBundle) -> str:
    parts: list[str] = []
    parts.extend(bundle.request.statute_ids)
    parts.extend(str(article) for article in bundle.request.articles)
    parts.extend(identity.name for identity in bundle.candidates.laws[:1])
    return " ".join(part for part in parts if part).strip()


def delegated_criteria_query_search_queries(bundle: LegalContextBundle, query: str) -> list[str]:
    identity = delegated_criteria_query_identity(bundle)
    if identity is None or not bundle.request.articles or not bundle.loaded.articles:
        return [query]
    return article_target_search_queries(
        identity,
        list(bundle.request.articles),
        bundle.loaded.articles,
        ranking_query=query,
    )


def delegated_criteria_query_identity(bundle: LegalContextBundle) -> LawIdentity | None:
    for article in bundle.loaded.articles:
        if article.identity.law_id or article.identity.mst or article.identity.name:
            return article.identity
    for law in bundle.loaded.laws:
        if law.identity.law_id or law.identity.mst or law.identity.name:
            return law.identity
    for graph in bundle.loaded.delegations:
        if graph.identity.law_id or graph.identity.mst or graph.identity.name:
            return graph.identity
    for identity in bundle.candidates.laws:
        if identity.law_id or identity.mst or identity.name:
            return identity
    return None


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


def dedupe_candidates(candidates: list[Any]) -> list[Any]:
    seen: set[tuple[str | None, str]] = set()
    unique: list[Any] = []
    for candidate in candidates:
        key = candidate_identity_key(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def article_target_search_queries(
    identity: LawIdentity,
    requested_articles: list[str | int],
    target_articles: list[ArticleText],
    *,
    ranking_query: str | None,
) -> list[str]:
    requested_labels = [article_label_for_filter(item) for item in requested_articles]
    base_query = ranking_query or f"{identity.name} {' '.join(requested_labels)}"
    queries = [base_query.strip()]
    requested_set = set(requested_labels)

    for article in target_articles:
        if not article.article or article.article in requested_set:
            continue
        queries.append(
            article_target_destination_query(
                identity,
                article.article,
                ranking_query=ranking_query,
                requested_labels=requested_labels,
            )
        )

    deduped_queries: list[str] = []
    for query in queries:
        if query and query not in deduped_queries:
            deduped_queries.append(query)
    return deduped_queries


def article_target_destination_query(
    identity: LawIdentity,
    destination_article: str,
    *,
    ranking_query: str | None,
    requested_labels: list[str],
) -> str:
    if ranking_query:
        query = ranking_query
        replaced = False
        for requested_label in requested_labels:
            if requested_label and requested_label in query:
                query = query.replace(requested_label, destination_article)
                replaced = True
        if replaced or destination_article in query:
            return query.strip()
        return f"{query} {destination_article}".strip()
    return f"{identity.name} {destination_article}".strip()


def significant_query_terms(query: str | None) -> list[str]:
    text = str(query or "")
    return [term for term in text.split() if len(term) >= 2]


def candidate_rank_score(candidate: Any, terms: list[str]) -> int:
    identity = getattr(candidate, "identity", None)
    haystack = " ".join(
        str(value or "")
        for value in (
            getattr(identity, "title", None),
            getattr(identity, "name", None),
            getattr(identity, "case_number", None),
            getattr(identity, "source_type", None),
            getattr(identity, "ministry", None),
            getattr(identity, "source_law_name", None),
            getattr(identity, "source_article", None),
            getattr(identity, "related_name", None),
            getattr(identity, "annex_number", None),
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
        or getattr(identity, "annex_id", None)
        or getattr(identity, "title", None)
        or getattr(identity, "name", None)
    )
    return (source_target, str(source_id or ""))
