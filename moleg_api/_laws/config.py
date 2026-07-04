from __future__ import annotations

from .foundation import *

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
# 헌재 사건번호 shape, e.g. 2005헌마1139 / 2015헌바9 (digits + 헌 + class letter(s)
# + digits) — distinct from the pure-digit 헌재결정례일련번호 detail id.
_CONSTITUTIONAL_CASE_NUMBER_RE = re.compile(r"^\d+헌[가-힣]+\d+$")


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

__all__ = [name for name in globals() if not name.startswith("__")]
