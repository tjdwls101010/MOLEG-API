from __future__ import annotations

from .foundation import *
from .constants import CliError, EXIT_USAGE

LIST_META: dict[str, tuple[str, str]] = {
    "search-laws": ("law_hit", "법제처 / 법령검색"),
    "search-administrative-rules": ("admin_rule_hit", "법제처 / 행정규칙 검색"),
    "search-annex-forms": ("annex_form_hit", "법제처 / 별표·서식 검색"),
    "search-interpretations": ("interpretation_hit", "법제처 / 법령해석례 검색"),
    "search-cases": ("case_hit", "법제처 / 판례 검색"),
    "search-constitutional-decisions": ("constitutional_hit", "법제처 / 헌재결정 검색"),
    "find-comparable-mechanisms": ("comparable_planning", "법제처 / 유사제도 탐색"),
}

# element dataclass name -> (canonical command, element kind, source). Keys
# signal derivation on the *result type*, not the invoking subcommand, so a list
# reached through load-followup gets the right kind and disciplines.
# JudicialDecisionHit is split by source_type in _resolve_list_kind (prec/detc).
ELEM_KIND: dict[str, tuple[str, str, str]] = {
    "LawHit": ("search-laws", "law_hit", "법제처 / 법령검색"),
    "AdministrativeRuleHit": ("search-administrative-rules", "admin_rule_hit", "법제처 / 행정규칙 검색"),
    "AnnexFormHit": ("search-annex-forms", "annex_form_hit", "법제처 / 별표·서식 검색"),
    "InterpretationHit": ("search-interpretations", "interpretation_hit", "법제처 / 법령해석례 검색"),
    "LawIdentity": ("find-comparable-mechanisms", "comparable_planning", "법제처 / 유사제도 탐색"),
}


def _resolve_list_kind(command: str, result: list[Any]) -> tuple[str, str, str]:
    """Return (canonical command, element kind, source) from the result type.

    Falls back to the invoking command for empty/unknown lists so a zero-hit
    search still reports the right kind.
    """
    if result:
        et = type(result[0]).__name__
        if et == "JudicialDecisionHit":
            st = getattr(result[0].identity, "source_type", "") or ""
            if "detc" in str(st) or command == "search-constitutional-decisions":
                return "search-constitutional-decisions", "constitutional_hit", "법제처 / 헌재결정 검색"
            return "search-cases", "case_hit", "법제처 / 판례 검색"
        meta = ELEM_KIND.get(et)
        if meta:
            return meta
    elem_kind, source = LIST_META.get(command, ("hit", "법제처"))
    return command, elem_kind, source


def _standing_list_discipline(eff_command: str, flags: dict[str, Any]) -> list[str]:
    """Command-level notes that hold for the result type regardless of hit count.

    These fire on zero hits too — a zero-hit Constitutional search is exactly
    when "no hits ≠ no constitutional risk" matters most.
    """
    lines: list[str] = []
    if eff_command == "search-constitutional-decisions":
        lines.append("doctrine(과잉금지원칙 등)는 색인 아닌 자유텍스트 검색어 — '위헌 소지 없음'·doctrine 망라 단정 금지. get-constitutional-decision으로 로드.")
    elif eff_command == "find-comparable-mechanisms":
        lines.append("설계 후보일 뿐 — 법적 동등·신법 적합성·순위 판단 아님. 선택 조문을 get-article로 로드한 뒤에야 구조 비교.")
    elif eff_command == "search-annex-forms":
        lines.append("검색 결과는 후보 — 임계값·금액·기준은 get-annex-form-body로 본문 로드 후에만 인용.")
    elif eff_command == "search-interpretations":
        flags["source_authority"] = "법제처 해석 ≠ 부처 1차 해석 — 답에서 출처 유형 보존"
    elif eff_command == "search-administrative-rules":
        flags["issued_on_is"] = "발령일자 필터(시행일 아님)"
    return lines

SINGLE_META: dict[str, tuple[str, str]] = {
    "LawText": ("law_text", "법제처 / 현행 법령 본문"),
    "ArticleText": ("article_text", "법제처 / 법령 조문"),
    "ArticleContext": ("article_context", "법제처 / 법령 조문(이동·삭제 확인)"),
    "AdministrativeRuleText": ("admin_rule_text", "법제처 / 행정규칙 본문"),
    "AdministrativeRuleContext": ("admin_rule_context", "법제처 / 행정규칙 본문(이동·삭제 확인)"),
    "AnnexFormText": ("annex_form_text", "법제처 / 별표·서식 본문"),
    "InterpretationText": ("interpretation_text", "법제처 / 법령해석례 본문"),
    "JudicialDecisionText": ("judicial_text", "법제처 / 판결·결정 본문"),
    "LawIdentity": ("law_identity", "법제처 / 공포 bridge 신원 확정"),
    "LawHistory": ("law_history", "법제처 / 개정 연혁"),
    "RevisionReason": ("revision_reason_text", "법제처 / 개정이유·공포문 원문"),
    "LawDiff": ("law_diff", "법제처 / 개정 전후 비교"),
    "DelegationGraph": ("delegation_graph", "법제처 / 위임 규정"),
    "LawStructure": ("law_structure_hierarchy_only", "법제처 / 법령 체계도"),
    "LegalQueryExpansion": ("query_expansion_planning", "법제처 / 질의 확장(조사 계획)"),
    "LegalContextBundle": ("legal_context_bundle", "법제처 / staged 법적 컨텍스트"),
    "AuthorityContext": ("authority_context", "법제처 / 조문 권위(해석·판례·헌재)"),
}


def _gap_signals(gaps: list[Any]) -> tuple[dict[str, Any], list[str]]:
    """Group ContextGap.kind values into flags + the discipline they trigger."""
    kinds = [getattr(g, "kind", "") or "" for g in (gaps or [])]
    flags: dict[str, Any] = {}
    lines: list[str] = []

    authority = sorted({k for k in kinds if k.startswith("authority_")})
    if authority:
        flags["authority_gaps"] = authority
        if any(k in ("authority_article_mismatch", "authority_article_unverified", "authority_article_partial_match") for k in authority):
            lines.append(
                "eager-load된 해석·판례·헌재 본문이 대상 조문과 구조적으로 일치하지 않음 — "
                "대상 조문의 권위로 인용 금지. current_authorities에 든 것만 인용하고, 나머지는 조문 범위로 후속검색."
            )
        if "authority_temporal_mismatch" in authority:
            lines.append(
                "조문은 맞으나 시점 미검증/기준일 이후 — 현행·기준일 권위로 단정 금지, 시점 확인 후 인용."
            )

    delegated = sorted({k for k in kinds if k.startswith("delegated_criteria_")})
    if delegated:
        flags["delegated_criteria_gaps"] = delegated
        lines.append(
            "로드된 고시·별표의 명시 source 법령·조문이 대상과 불일치/미검증 — 이 조문의 위임 집행기준으로 인용 금지, 근거 확인 필요."
        )

    if any(k == "not_effective_as_of" for k in kinds):
        flags["not_effective_as_of"] = True
        lines.append("공포됐으나 기준일 미시행 — '현재 시행 중'으로 단정 금지.")
    if any("source_lag" in k or "manual_review" in k for k in kinds):
        flags["bridge_source_lag"] = True
        lines.append("공포 bridge 불일치이나 후보 있음 — '제정 안 됨'이 아니라 소스 지연/수동검토 상태로 설명.")

    other = sorted({k for k in kinds if k and k not in authority and k not in delegated and k not in ("not_effective_as_of",) and "source_lag" not in k and "manual_review" not in k})
    if other:
        flags["gaps"] = other
    return flags, lines


def _deferred_next(deferred: list[Any], *, cap: int = 3) -> tuple[list[dict[str, str]], int]:
    """Render up to ``cap`` deferred lookups as ready-to-run load-followup cmds."""
    items: list[dict[str, str]] = []
    for lookup in (deferred or []):
        if len(items) >= cap:
            break
        payload = lookup.to_dict() if hasattr(lookup, "to_dict") else None
        if payload is None:
            continue
        why = getattr(lookup, "reason", None) or getattr(lookup, "interface", "follow-up")
        items.append({"why": why, "cmd": "moleg load-followup --json " + json.dumps(json.dumps(payload, ensure_ascii=False), ensure_ascii=False)})
    overflow = max(0, len(deferred or []) - len(items))
    return items, overflow


def _today_compact() -> str:
    return date.today().strftime("%Y%m%d")


def _compact_digits(value: Any) -> str:
    return "".join(ch for ch in str(value) if ch.isdigit()) if value else ""


def parse_as_of(raw: str) -> str:
    """Strictly parse an --as-of value to canonical YYYYMMDD.

    Accepts YYYY-MM-DD or YYYYMMDD only, with real calendar validation (rejects
    month 13, Feb 30, day 99, and non-dates). A malformed date is a usage error,
    not a silent fallback to the current version.
    """
    text = raw.strip()
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y%m%d")
        except ValueError:
            continue
    raise CliError(
        f"--as-of 값 {raw!r}을(를) 날짜로 해석할 수 없다 — YYYY-MM-DD 또는 YYYYMMDD 형식만 허용(월 1~12·일 유효 범위).",
        kind="usage_error",
        exit_code=EXIT_USAGE,
    )


def _law_time_flags(identity: Any, as_of: str | None) -> tuple[dict[str, Any], list[str]]:
    flags: dict[str, Any] = {}
    lines: list[str] = []
    basis = getattr(identity, "basis", None)
    if basis:
        flags["basis"] = basis
    eff = getattr(identity, "effective_date", None)
    if eff:
        flags["effective_date"] = eff
    e = _compact_digits(eff)
    # 공포됐어도 시행일이 미래면 아직 효력이 없다. 반환 버전의 시행일을 오늘과 직접
    # 대조해 '미시행'을 신호한다 — as_of 유무와 무관(미래 버전은 어느 경로로도 올 수 있다).
    if len(e) == 8 and e > _today_compact():
        flags["not_effective_as_of"] = True
        lines.append(
            "이 버전은 시행일이 미래 — 공포됐으나 아직 미시행이다. 현행 시행 문구로 인용 금지; "
            "현재 시행 중 본문은 --as-of 없이(현행) 로드하라."
        )
    # --as-of는 그 시점에 시행 중이던 버전을 로드한다(로더가 역사 버전을 해결). 반환
    # effective_date를 확인하라 — 요청 시점과 다르면 인접 버전이 반환된 것이다.
    if as_of:
        flags["as_of"] = as_of
        a = _compact_digits(as_of)
        if a and e and e != a:
            flags["version_mismatch"] = {"requested": a, "loaded": e}
            if e > a:
                # 하위호환: SKILL.md·catalog가 참조하는 기존 플래그 유지.
                flags["version_request_unfulfilled"] = True
            lines.append(
                "요청한 시점(as_of)과 반환된 버전의 시행일이 다르다 — 반환 effective_date 기준으로 해석하라. "
                "그 시점의 정확한 시행 버전 이력은 trace-law-history로 확인."
            )
    return flags, lines


# law.go.kr emits "제0조" (and blank) as a sentinel on rows that were not
# actually moved — treat it as parse noise, not a real destination.
_SENTINEL_ARTICLES = {"제0조", "0", ""}


def _real_moved_to(article: Any) -> str | None:
    mt = getattr(article, "moved_to", None)
    return mt if mt and mt not in _SENTINEL_ARTICLES else None


def _article_flags(article: Any) -> tuple[dict[str, Any], list[str]]:
    flags: dict[str, Any] = {}
    lines: list[str] = []
    if getattr(article, "is_deleted", False) or getattr(article, "revision_type", None) == "삭제":
        flags["is_deleted"] = True
        lines.append("삭제 상태 조문 — 현행 의무·제재·절차 아님. '제N조 삭제'를 현행 규율로 인용 금지.")
    moved_to = _real_moved_to(article)
    if moved_to:
        flags["moved_to"] = moved_to
        lines.append(f"이동 조문 — 실체는 {moved_to}에. load-article-context로 목적지를 로드한 뒤 인용.")
    return flags, lines


def _has_supplementary(result: Any) -> bool:
    return bool(getattr(result, "supplementary_provisions", None))

__all__ = [name for name in globals() if not name.startswith("__")]
