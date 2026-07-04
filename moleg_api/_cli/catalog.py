from __future__ import annotations

from .foundation import *

CATALOG = {
    "convention": [
        "kind 접미사가 후보≠본문을 구조로 표시: *_hit/*_candidate/*_planning = 검색 후보(인용 불가), *_text/*_context/*_identity = 로드된 본문.",
        "인용은 항상 로드된 본문에서만 — search/expand/find-comparable 결과는 '다음에 무엇을 로드할지의 메뉴'일 뿐.",
        "출처 권위 보존: 법제처 법령 > 법제처 해석 > 부처 해석 ≠ 판례 ≠ 헌재. flags.source_type/라벨을 답에 반영.",
        "0건·호출 실패 ≠ 부재. 종료코드로 구분: 0 ok(0건 포함) · 2 모호 · 3 소스접근실패 · 4 no-result · 5 usage/순서위반.",
        "load 계열에 법령명을 주면 needs_search_first(exit 5) — 먼저 search-laws로 law_id를 얻어라.",
        "deferred는 data.deferred[i]를 load-followup --json -로 파이프(손타이핑 금지).",
        "로더(get-law/get-article)는 기본이 현행 통합본, --as-of <날짜>(YYYY-MM-DD/YYYYMMDD만)면 그 시점 시행 버전을 로드한다. 반환 effective_date를 오늘과 대조해 현행/미시행을 판정하라 — flags.not_effective_as_of=공포됐으나 미시행(미래 시행일, 현행 인용 금지), version_mismatch={requested,loaded}=요청 시점과 반환 버전 시행일 불일치, version_request_unfulfilled=요청보다 이후 버전이 반환됨. 요청 시점이 통합본 커버리지보다 이르면 kind:version_request_unfulfilled+earliest_available(→trace-law-history).",
        "검색 스코프 뉘앙스: 헌재·판례는 기본이 제목(사건명) 검색이라 doctrine·본문 키워드는 --search-body(본문 전체)라야 매칭(0건이면 next가 재시도 제시). 별표는 --search-scope title(별표 제목)/source(소관 법령명, 토큰 근접)이라 0건이면 반대 스코프로. 부처 해석은 --source all_ministries(법제처+부처 혼합)로만 나오고, 부처 본문 로드는 --source ministry --ministry <기관> 필수(검색 hit의 follow_up.filters를 그대로 로더 인자로).",
        "개정 전후 델타=compare-law-versions는 소스가 주는 최근 두 버전만 비교하고 changes[].article은 본문에서 파싱한 실제 조문번호(매핑 불가 시 null). 임의 두 시점 델타는 get-article --as-of를 전후 날짜로 두 번 로드해 대조.",
    ],
    "routing_rules": [
        "본문 로드: 살아있는 조문=get-article / 이동·삭제 가능성 있는 조문=load-article-context(기본이 이동추적).",
        "개정: 무엇이 바뀌었나(전후 문구 델타)=compare-law-versions / 어떤 개정들이 있었나(연혁)=trace-law-history.",
        "이 법 아래 무엇이 있나: 계층 조망=get-law-structure(위임 증명 아님) / 조문 단위 위임 규정=find-delegated-rules.",
        "넓은 탐색: 넓은 질의의 용어·관련법 조사계획=expand-legal-query / 유사 제도(비슷한 기제)를 가진 법 후보(설계용)=find-comparable-mechanisms.",
        "묶음 로더 — authority=특정 조문의 해석/판례/헌재 권위 / bundle=진입점 모를 때 단일법·넓은 질문(--mode) / institutional=명시된 다법령 집합(--statute 반복) / delegated=단일법의 하위규칙·별표 집행기준 본문.",
        "별표 금액·기준표: 위임된 시행령·시행규칙의 별표를 search-annex-forms --search-scope source <법령명> → get-annex-form-body --id(=--annex-id)로 로드. 표 파싱이 무너지면 structured_data.parsing_confidence=low — 금액은 text를 1차로 인용하라. bare id 로드는 소관법령ID·pdf_link 등 링크 메타를 복구하지 못하니 현행성은 모법 버전으로 확인.",
    ],
    "commands": {
        "검색·계획(후보)": [
            "search-laws", "resolve-promulgated-law", "search-administrative-rules", "search-annex-forms",
            "search-interpretations", "search-cases", "search-constitutional-decisions",
            "expand-legal-query", "find-comparable-mechanisms",
        ],
        "본문 로드": [
            "get-law", "get-article", "load-article-context", "get-administrative-rule",
            "load-administrative-rule-context", "get-annex-form-body", "get-interpretation",
            "get-case", "get-constitutional-decision",
        ],
        "연혁·체계·위임": ["trace-law-history", "compare-law-versions", "find-delegated-rules", "get-law-structure"],
        "권위·묶음": ["load-authority-context", "load-legal-context-bundle", "load-institutional-system", "load-delegated-criteria", "load-followup"],
    },
    "kinds": [
        "law_hit_list", "admin_rule_hit_list", "annex_form_hit_list", "interpretation_hit_list",
        "case_hit_list", "constitutional_hit_list", "comparable_planning_list", "query_expansion_planning",
        "law_text", "article_text", "article_context", "admin_rule_text", "admin_rule_context",
        "annex_form_text", "interpretation_text", "case_text", "constitutional_text", "law_identity",
        "law_history", "law_diff", "delegation_graph", "law_structure_hierarchy_only",
        "legal_context_bundle", "authority_context",
        "ambiguous", "source_access_error", "parse_error", "no_result",
        "needs_search_first", "usage_error", "unsupported", "error",
    ],
}

__all__ = [name for name in globals() if not name.startswith("__")]
