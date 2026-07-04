"""Command-line interface for :mod:`moleg_api`.

Wraps the 27 task-level :class:`~moleg_api.MolegApi` methods as subcommands so an
agent can call law.go.kr sources straight from a shell — no Python, no heredoc,
no introspection ritual. Every command prints exactly one JSON envelope to
stdout::

    {"ok": true, "command": ..., "kind": ..., "source": ...,
     "data": ..., "flags": {...}, "discipline": [...], "next": [...]}

Design contract:

* ``kind`` suffix carries the candidate/loaded distinction structurally —
  ``*_hit`` / ``*_candidate`` / ``*_planning`` are search candidates (not
  citable), ``*_text`` / ``*_context`` / ``*_identity`` are loaded source text.
* ``discipline`` lines appear **only when the trap is live** in this result
  (a deleted article, an authority-article mismatch, a future effective date),
  so the frequent-path calls stay quiet and the rare dangerous ones speak up.
* ``next`` mirrors the highest-leverage follow-up as a ready-to-run command,
  capped at three; the full follow-up set stays in ``data``.

The standing conventions that apply to every call live in ``moleg catalog``,
not on each response.
"""

from __future__ import annotations

import argparse
import json
import sys
from importlib.metadata import PackageNotFoundError, version as _dist_version
from typing import Any

from .errors import (
    AmbiguousLawError,
    MolegApiError,
    NoResultError,
    ParseFailureError,
    RateLimitError,
    RetryExhaustedError,
    UnsupportedFormatError,
)
from .laws import MolegApi
from .models import DeferredLookup


def _pkg_version() -> str:
    try:
        return _dist_version("moleg-api")
    except PackageNotFoundError:
        return "unknown"


# Exit codes distinguish outcomes a shell/agent must branch on.
EXIT_OK = 0            # includes a zero-hit search (ok:true, count:0)
EXIT_AMBIGUOUS = 2     # multiple plausible identities — surface, don't pick
EXIT_SOURCE = 3        # transient source access failure (rate limit / retry / source)
EXIT_NO_RESULT = 4     # a load found no source text for a valid identifier
EXIT_USAGE = 5         # bad arguments, or a loader was handed a law name (search first)

# Public MolegApi methods reachable through load-followup rehydration. Guards the
# candidate->body discipline: an arbitrary interface string cannot smuggle a
# candidate in as if it were loaded text.
FOLLOWUP_INTERFACES = frozenset(
    {
        "expand_legal_query",
        "find_comparable_mechanisms",
        "resolve_promulgated_law",
        "search_laws",
        "get_law",
        "get_article",
        "load_article_context",
        "search_administrative_rules",
        "get_administrative_rule",
        "load_administrative_rule_context",
        "search_annex_forms",
        "get_annex_form_body",
        "search_interpretations",
        "get_interpretation",
        "search_cases",
        "get_case",
        "search_constitutional_decisions",
        "get_constitutional_decision",
        "load_authority_context",
        "find_delegated_rules",
        "get_law_structure",
        "trace_law_history",
        "compare_law_versions",
        "load_legal_context_bundle",
        "load_institutional_system",
        "load_delegated_criteria",
    }
)
# Handoffs that are valid follow-up interfaces but belong to other sources.
FOLLOWUP_HANDOFFS = frozenset({"websearch", "congress-db"})

# Searches return a list; a zero-hit search is a scoped ok:true result (count 0),
# never an error — even when the SDK signals "nothing found" by raising.
SEARCH_COMMANDS = frozenset(
    {
        "search-laws",
        "search-administrative-rules",
        "search-annex-forms",
        "search-interpretations",
        "search-cases",
        "search-constitutional-decisions",
    }
)


class CliError(Exception):
    """A CLI-level failure carrying the envelope kind and exit code to emit."""

    def __init__(self, message: str, *, kind: str, exit_code: int, extra: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.kind = kind
        self.exit_code = exit_code
        self.extra = extra or {}


# --------------------------------------------------------------------------- #
# Serialization + identity helpers
# --------------------------------------------------------------------------- #

def _to_data(result: Any, *, include_raw: bool) -> Any:
    if isinstance(result, list):
        return [_to_data(item, include_raw=include_raw) for item in result]
    if hasattr(result, "to_dict"):
        return result.to_dict(include_raw=include_raw)
    return result


def _statute_args(values: list[str]) -> list[str]:
    if not values:
        raise CliError(
            "load-institutional-system needs at least one --statute law_id",
            kind="usage",
            exit_code=EXIT_USAGE,
        )
    return values


# --------------------------------------------------------------------------- #
# Signal derivation — kind / source / flags / discipline / next
#
# Signals are derived from the *result dataclass fields*, dispatched on the
# result type, not hardcoded per command. Twenty-seven methods collapse onto
# ~14 result shapes.
# --------------------------------------------------------------------------- #

# command -> (element kind, source label) for list-returning searches, so an
# empty list still reports the right kind and a candidate-discipline anchor.
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


def _law_time_flags(identity: Any, as_of: str | None) -> tuple[dict[str, Any], list[str]]:
    flags: dict[str, Any] = {}
    lines: list[str] = []
    basis = getattr(identity, "basis", None)
    if basis:
        flags["basis"] = basis
    eff = getattr(identity, "effective_date", None)
    if eff:
        flags["effective_date"] = eff
    # --as-of loads the version in force at that date (the loader resolves the
    # historical version). Verify the returned effective_date; a returned version
    # newer than the requested date means no version was in force then.
    if as_of:
        flags["as_of"] = as_of
        a = "".join(ch for ch in as_of if ch.isdigit())
        e = "".join(ch for ch in str(eff) if ch.isdigit()) if eff else ""
        if a and e and e > a:
            flags["version_request_unfulfilled"] = True
            lines.append(
                "요청 시점에 시행 중이던 버전을 찾지 못해 이후 버전이 반환됨 — 그 시점 이전엔 시행 이력이 없을 수 있다. "
                "조회 기준일을 답에 명기하라."
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


def signals_for(command: str, result: Any, args: argparse.Namespace) -> dict[str, Any]:
    """Return {kind, source, count?, flags, discipline, next} for a result."""
    flags: dict[str, Any] = {}
    discipline: list[str] = []
    next_cmds: list[dict[str, str]] = []

    # ---- list results (searches) --------------------------------------- #
    if isinstance(result, list):
        eff_command, elem_kind, source = _resolve_list_kind(command, result)
        kind = elem_kind + "_list"
        count = len(result)
        flags["count"] = count
        # standing, command-level disciplines fire regardless of count.
        discipline.extend(_standing_list_discipline(eff_command, flags))
        if count == 0:
            flags["searched"] = _searched_scope(command, args)
            discipline.append("0건 — 이 검색어·범위로 못 찾음일 뿐, 부재의 증명 아님.")
            # mechanical alternate: drop a narrowing filter if one was set.
            broaden = _broaden_next(command, args)
            if broaden:
                next_cmds.append(broaden)
        elif eff_command == "search-laws":
            sig = _law_list_signals(result)
            flags.update(sig["flags"])
            discipline.extend(sig["discipline"])
            next_cmds.extend(sig["next"])
        elif eff_command == "find-comparable-mechanisms":
            next_cmds.extend(_comparable_next(result))
        elif eff_command == "search-annex-forms":
            next_cmds.extend(_annex_next(result))
        elif eff_command == "search-constitutional-decisions":
            next_cmds.extend(_id_next(result, "get-constitutional-decision"))
        elif eff_command == "search-interpretations":
            next_cmds.extend(_id_next(result, "get-interpretation"))
        elif eff_command == "search-cases":
            next_cmds.extend(_id_next(result, "get-case"))
        elif eff_command == "search-administrative-rules":
            next_cmds.extend(_id_next(result, "get-administrative-rule"))
        return {"kind": kind, "source": source, "count": count,
                "flags": flags, "discipline": discipline, "next": next_cmds[:3]}

    # ---- single results -------------------------------------------------- #
    tname = type(result).__name__
    kind, source = SINGLE_META.get(tname, (_snake(tname), "법제처"))
    as_of = getattr(args, "as_of", None)

    if tname == "LawText":
        tf, tl = _law_time_flags(result.identity, as_of)
        flags.update(tf); discipline.extend(tl)
        if _has_supplementary(result):
            flags["has_supplementary"] = True
            discipline.append("시행일·적용례·경과조치는 supplementary_provisions에 별도 — 조문 본문·법령 effective_date만으로 전환 범위 답 금지.")
        bad = [a for a in result.articles if getattr(a, "is_deleted", False) or getattr(a, "moved_to", None)]
        if bad:
            flags["articles_deleted_or_moved"] = len(bad)
            discipline.append("일부 조문이 삭제/이동 상태 — 해당 조문은 load-article-context로 상태 확인 후 인용.")

    elif tname == "ArticleText":
        af, al = _article_flags(result)
        flags.update(af); discipline.extend(al)
        tf, tl = _law_time_flags(result.identity, as_of)
        flags.update(tf); discipline.extend(tl)
        discipline.append("정의·예외·적용대상·요건은 text의 항·호·목 중첩에 있다 — 조문제목·상위 조문내용만으로 요약 금지.")
        moved = _real_moved_to(result)
        if moved:
            next_cmds.append({"why": "이동 목적지 로드", "cmd": f"moleg load-article-context --law {result.identity.law_id or ''} {moved}"})

    elif tname == "ArticleContext":
        gf, gl = _gap_signals(getattr(result, "gaps", []))
        flags.update(gf); discipline.extend(gl)
        req = getattr(result, "requested_article", None)
        if req is not None:
            af, al = _article_flags(req)
            flags.update(af); discipline.extend(al)
        if getattr(result, "current_article", None) is None and req is not None and (_real_moved_to(req) or req.is_deleted):
            discipline.append("현행 실체 조문 미로드 — 목적지·대체 조문을 확인하기 전 현행 의무로 인용 금지.")
        nx, ov = _deferred_next(getattr(result, "deferred", []))
        next_cmds.extend(nx)

    elif tname in ("AdministrativeRuleText", "AdministrativeRuleContext"):
        rule = result if tname == "AdministrativeRuleText" else getattr(result, "rule", None)
        if rule is not None:
            ident = rule.identity
            eff = getattr(ident, "effective_date", None)
            if eff:
                flags["effective_date"] = eff
            if not getattr(ident, "source_law_name", None) and not getattr(ident, "source_article", None):
                flags["source_backref_present"] = False
                discipline.append("위임 근거 필드 미노출 — 근거 부재·무효의 증명 아님. 위임 근거는 상위법 find-delegated-rules로 역추적.")
            status = getattr(ident, "current_status", None)
            if status and any(s in str(status) for s in ("폐지", "실효")):
                flags["current_status"] = status
                discipline.append("폐지·실효 상태 행정규칙 — 현행 운영기준 아님.")
            if _has_supplementary(rule):
                flags["has_supplementary"] = True
                discipline.append("행정규칙 시행일·적용례·경과조치는 부칙(supplementary_provisions)에 별도 — 규칙 effective_date·조문 본문만으로 답 금지.")
        flags.setdefault("issued_on_note", "행정규칙 검색 date는 발령일자 — 로드된 effective_date를 기준일과 비교한 뒤 '현행 운영기준'.")
        gf, gl = _gap_signals(getattr(result, "gaps", []))
        flags.update(gf); discipline.extend(gl)
        if "not_effective_as_of" in gf:
            flags["rule_not_effective_as_of"] = True

    elif tname == "AnnexFormText":
        conf = getattr(result, "extraction_confidence", None)
        sd = getattr(result, "structured_data", None)
        flags["extraction_confidence"] = conf
        if sd is not None:
            flags["parsing_confidence"] = getattr(sd, "parsing_confidence", None)
            if not getattr(sd, "rows", None) or getattr(sd, "parsing_confidence", "low") == "low":
                discipline.append("구조화 rows가 비거나 신뢰도 낮음 — '기준 없음'이 아니라 plain text를 폴백으로 사용.")

    elif tname == "InterpretationText":
        flags["source_type"] = getattr(result.identity, "source_type", None)
        discipline.append("출처 유형(법제처 해석 / 부처 1차 해석) 보존 — 판례·헌재와 권위가 다르다.")

    elif tname == "JudicialDecisionText":
        st = getattr(result.identity, "source_type", None)
        flags["source_type"] = st
        if command == "get-constitutional-decision" or (st and "detc" in str(st)):
            kind, source = "constitutional_text", "법제처 / 헌재결정 본문"
            discipline.append("헌재 결정 — 판시사항·심판대상조문을 로드된 본문에서만 인용, doctrine 망라 단정 금지.")
        else:
            kind, source = "case_text", "법제처 / 판례 본문"

    elif tname == "LawIdentity":
        tf, tl = _law_time_flags(result, as_of)
        flags.update(tf); discipline.extend(tl)
        discipline.append("공포 bridge 신원 확정일 뿐 — 현행 시행 문구는 get-law --basis effective로, not_effective 여부 확인.")
        next_cmds.append({"why": "현행 시행 본문 로드", "cmd": f"moleg get-law --law {result.law_id or ''} --basis effective"})

    elif tname == "LawDiff":
        discipline.append("선택 조문의 전후 문구 델타만 — 개정이유·입법의도·전체 변경 조문 망라 아님. trace-law-history·국회 법안자료로 보강.")

    elif tname == "DelegationGraph":
        rules = getattr(result, "rules", None) or []
        flags["count"] = len(rules)
        if not rules:
            discipline.append("이 조회로 위임규정 못 찾음 ≠ 위임 없음 — 법령 체계도·다른 조문 범위·행정규칙·별표 경로를 더 확인.")
        else:
            discipline.append("위임 목록은 하위법령·인용법령 위임만 — 별표(과태료·범칙금액·기준표 등) 자체는 여기 없다. 금액·기준표는 위임된 시행령·시행규칙의 별표를 search-annex-forms(또는 load-delegated-criteria)로 확인.")
            ident = getattr(result, "identity", None)
            name = (getattr(ident, "name", None) or getattr(ident, "law_id", None) or "") if ident else ""
            if name:
                next_cmds.append({
                    "why": "위임된 별표·금액·기준표 확인",
                    "cmd": f"moleg search-annex-forms {json.dumps(name, ensure_ascii=False)} --source law",
                })

    elif tname == "LawStructure":
        discipline.append("체계도는 계층 컨텍스트일 뿐 — 시행령·규칙·행정규칙이 이 법 아래 있음은 보이나, 조문 단위 위임·하위규칙 본문·운영기준 증명 아님. find-delegated-rules로 확인.")

    elif tname == "LegalQueryExpansion":
        discipline.append("질의 확장은 조사 계획 — 법령용어·관련법·AI검색 후보를 로드 전엔 법적 권위로 인용 금지.")
        ef = getattr(result, "empty_sources", None)
        if ef:
            flags["empty_sources"] = ef
        if getattr(result, "source_failures", None):
            flags["source_failures"] = len(result.source_failures)
        nx, ov = _deferred_next(getattr(result, "follow_up_searches", []))
        next_cmds.extend(nx)
        if ov:
            flags["more_followups"] = ov

    elif tname in ("LegalContextBundle", "AuthorityContext"):
        gf, gl = _gap_signals(getattr(result, "gaps", []))
        flags.update(gf); discipline.extend(gl)
        if getattr(result, "ambiguities", None):
            flags["ambiguities"] = [getattr(a, "kind", "") for a in result.ambiguities]
            discipline.append("모호성 존재 — 조용히 첫 후보로 확정 금지, 후보를 사용자에게.")
        if tname == "AuthorityContext":
            loaded = getattr(result, "loaded", None)
            cur = getattr(result, "current_authorities", None)
            flags["loaded_vs_current"] = {
                "loaded": _authority_counts(loaded),
                "current_authorities": _authority_counts(cur),
            }
            discipline.append("대상 조문의 권위 인용은 current_authorities에 든 것만 — loaded는 1차 로드분(조문·시점 미검증 포함).")
        nx, ov = _deferred_next(getattr(result, "deferred", []))
        next_cmds.extend(nx)
        if ov:
            flags["more_followups"] = ov

    return {"kind": kind, "source": source, "flags": flags,
            "discipline": discipline, "next": next_cmds[:3]}


def _authority_counts(loaded: Any) -> dict[str, int]:
    if loaded is None:
        return {}
    out = {}
    for name in ("interpretations", "cases", "constitutional_decisions"):
        vals = getattr(loaded, name, None)
        if vals:
            out[name] = len(vals)
    return out


def _law_list_signals(hits: list[Any]) -> dict[str, Any]:
    flags: dict[str, Any] = {}
    discipline: list[str] = []
    next_cmds: list[dict[str, str]] = []
    by_name: dict[str, list[Any]] = {}
    for h in hits:
        by_name.setdefault(getattr(h.identity, "name", ""), []).append(h)
    ambiguous = any(len(v) > 1 for v in by_name.values())
    if ambiguous:
        flags["ambiguous_versions"] = True
        discipline.append("동명 후보가 시행일 다름 — 현행본은 그냥 get-law --law, 특정 시점 버전은 --as-of <시행일>로 로드.")
    for i, h in enumerate(hits[:3]):
        ident = h.identity
        law_id = getattr(ident, "law_id", "") or ""
        eff = getattr(ident, "effective_date", None)
        cmd = f"moleg get-law --law {law_id}"
        # first (latest) candidate is current; older candidates load by --as-of
        if ambiguous and i > 0 and eff:
            cmd += f" --as-of {eff}"
        next_cmds.append({"why": f"후보 로드: {getattr(ident, 'name', '')}" + (f" (시행 {eff})" if eff else ""), "cmd": cmd})
    return {"flags": flags, "discipline": discipline, "next": next_cmds}


def _comparable_next(items: list[Any]) -> list[dict[str, str]]:
    out = []
    for it in items[:3]:
        lid = getattr(it, "law_id", None)
        if lid:
            out.append({"why": f"후보 조문 로드: {getattr(it, 'name', lid)}", "cmd": f"moleg get-law --law {lid}"})
    return out


def _annex_next(hits: list[Any]) -> list[dict[str, str]]:
    out = []
    for h in hits[:2]:
        aid = getattr(h.identity, "annex_id", None)
        src = getattr(h.identity, "source_type", "law")
        if aid:
            out.append({"why": f"별표/서식 본문 로드: {getattr(h.identity, 'title', aid)}", "cmd": f"moleg get-annex-form-body --id {aid} --source {src}"})
    return out


def _id_next(hits: list[Any], command: str) -> list[dict[str, str]]:
    id_field = {
        "get-interpretation": "interpretation_id",
        "get-case": "decision_id",
        "get-constitutional-decision": "decision_id",
        "get-administrative-rule": "serial_id",
    }[command]
    out = []
    for h in hits[:2]:
        val = getattr(h.identity, id_field, None)
        if val:
            out.append({"why": f"본문 로드: {getattr(h.identity, 'title', getattr(h.identity, 'name', val))}", "cmd": f"moleg {command} --id {val}"})
    return out


def _searched_scope(command: str, args: argparse.Namespace) -> dict[str, Any]:
    scope: dict[str, Any] = {}
    for key in ("query", "concept", "basis", "ministry", "law_type", "court", "source", "annex_type", "rule_type", "as_of"):
        val = getattr(args, key, None)
        if val:
            scope[key] = val
    return scope


def _broaden_next(command: str, args: argparse.Namespace) -> dict[str, str] | None:
    query = getattr(args, "query", None) or getattr(args, "concept", None)
    if not query:
        return None
    for narrowing in ("ministry", "law_type", "court_name", "rule_type"):
        if getattr(args, narrowing, None):
            return {"why": f"필터(--{narrowing.replace('_', '-')}) 제거해 넓혀 재검색", "cmd": f"moleg {command} {json.dumps(query, ensure_ascii=False)}"}
    return None


def _snake(name: str) -> str:
    out = []
    for i, ch in enumerate(name):
        if ch.isupper() and i:
            out.append("_")
        out.append(ch.lower())
    return "".join(out)


# --------------------------------------------------------------------------- #
# Argument wiring
# --------------------------------------------------------------------------- #

def _add_law(p: argparse.ArgumentParser, required: bool = True) -> None:
    p.add_argument("--law", required=required, help="law_id (search-laws가 준 값). 법령명을 주면 needs_search_first로 막힘.")


def _add_basis(p: argparse.ArgumentParser) -> None:
    p.add_argument("--basis", choices=["effective", "promulgated"], default="effective")


def _add_as_of(p: argparse.ArgumentParser) -> None:
    p.add_argument("--as-of", dest="as_of", default=None, metavar="YYYY-MM-DD", help="기준일(현재 시행 여부·역사적 시점 조회).")


def _add_articles(p: argparse.ArgumentParser, required: bool = False) -> None:
    p.add_argument("--article", dest="article", action="append", default=[], required=required, help="조문(예: 제3조). 반복 지정 가능.")


def _add_budget(p: argparse.ArgumentParser) -> None:
    p.add_argument("--budget", choices=["minimal", "standard", "broad"], default="standard")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="moleg",
        description="법제처 law.go.kr 법령 자료 조회 CLI. 항상 JSON 엔벨로프 1개를 stdout으로 출력.",
    )
    parser.add_argument("--raw", action="store_true", help="원본 소스 payload(raw)까지 직렬화(디버그).")
    parser.add_argument(
        "--version",
        action="version",
        version=f"moleg-api {_pkg_version()}",
        help="설치된 moleg-api 버전을 출력하고 종료.",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    sub.add_parser("catalog", help="27개 서브커맨드·규약·kind 목록을 한 번에.")

    # ---- searches / planning ------------------------------------------- #
    p = sub.add_parser("search-laws", help="현행/공포 법령 신원 후보 검색.")
    p.add_argument("query"); _add_as_of(p); _add_basis(p)
    p.add_argument("--law-type", dest="law_type", default=None)
    p.add_argument("--ministry", default=None); p.add_argument("--display", type=int, default=20)

    p = sub.add_parser("resolve-promulgated-law", help="공포 bridge(법명·공포번호·공포일)로 법령 신원 확정.")
    p.add_argument("--prom-law-nm", dest="prom_law_nm", default=None)
    p.add_argument("--prom-no", dest="prom_no", default=None)
    p.add_argument("--promulgation-dt", dest="promulgation_dt", default=None)

    p = sub.add_parser("search-administrative-rules", help="고시·훈령·예규 등 행정규칙 검색.")
    p.add_argument("query"); p.add_argument("--ministry", default=None)
    p.add_argument("--rule-type", dest="rule_type", default=None)
    p.add_argument("--issued-on", dest="issued_on", default=None, help="발령일자 필터(시행일 아님).")
    p.add_argument("--include-history", dest="include_history", action="store_true")
    p.add_argument("--display", type=int, default=20)

    p = sub.add_parser("search-annex-forms", help="별표·서식 후보 검색.")
    p.add_argument("query")
    p.add_argument("--source", choices=["law", "administrative_rule"], default="law")
    p.add_argument("--search-scope", dest="search_scope", choices=["title", "source", "body"], default="source")
    p.add_argument("--annex-type", dest="annex_type", default=None)
    p.add_argument("--ministry", default=None); p.add_argument("--display", type=int, default=20)

    p = sub.add_parser("search-interpretations", help="법령해석례(법제처·부처) 검색.")
    p.add_argument("query")
    p.add_argument("--source", choices=["moleg", "ministry", "all", "all_ministries"], default="moleg")
    p.add_argument("--ministry", default=None)
    p.add_argument("--search-body", dest="search_body", action="store_true")
    p.add_argument("--interpreted-on", dest="interpreted_on", default=None)
    p.add_argument("--display", type=int, default=20)

    p = sub.add_parser("search-cases", help="대법원·각급 판례 검색.")
    p.add_argument("query")
    p.add_argument("--court", choices=["all", "supreme", "lower"], default="all")
    p.add_argument("--court-name", dest="court_name", default=None)
    p.add_argument("--search-body", dest="search_body", action="store_true")
    p.add_argument("--decided-on", dest="decided_on", default=None)
    p.add_argument("--case-number", dest="case_number", default=None)
    p.add_argument("--display", type=int, default=20)

    p = sub.add_parser("search-constitutional-decisions", help="헌재 결정 검색.")
    p.add_argument("query")
    p.add_argument("--search-body", dest="search_body", action="store_true")
    p.add_argument("--decided-on", dest="decided_on", default=None)
    p.add_argument("--case-number", dest="case_number", default=None)
    p.add_argument("--display", type=int, default=20)

    p = sub.add_parser("expand-legal-query", help="질의 확장·관련법/용어/조문 조사 계획.")
    p.add_argument("query"); p.add_argument("--display", type=int, default=5)
    p.add_argument("--no-websearch-hint", dest="no_websearch_hint", action="store_true")

    p = sub.add_parser("find-comparable-mechanisms", help="유사 법적 기제(제도) 탐색.")
    p.add_argument("concept"); p.add_argument("--display", type=int, default=5)

    # ---- loaders -------------------------------------------------------- #
    p = sub.add_parser("get-law", help="법령 본문 로드.")
    _add_law(p); _add_as_of(p); _add_basis(p); _add_articles(p)
    p.add_argument("--no-metadata", dest="no_metadata", action="store_true")

    p = sub.add_parser("get-article", help="조문 하나 로드.")
    _add_law(p); p.add_argument("article"); _add_as_of(p); _add_basis(p)

    p = sub.add_parser("load-article-context", help="조문 로드 + 이동/삭제 상태 해소.")
    _add_law(p); p.add_argument("article"); _add_as_of(p); _add_basis(p)
    p.add_argument("--no-follow-moved", dest="no_follow_moved", action="store_true")

    p = sub.add_parser("get-administrative-rule", help="행정규칙 본문 로드.")
    p.add_argument("--id", dest="identifier", required=True, help="serial_id(검색이 준 값).")
    _add_articles(p); p.add_argument("--no-metadata", dest="no_metadata", action="store_true")

    p = sub.add_parser("load-administrative-rule-context", help="행정규칙 로드 + 이동/삭제 해소.")
    p.add_argument("--id", dest="identifier", required=True)
    _add_articles(p); p.add_argument("--no-metadata", dest="no_metadata", action="store_true")
    p.add_argument("--no-follow-moved", dest="no_follow_moved", action="store_true")

    p = sub.add_parser("get-annex-form-body", help="별표·서식 본문 로드.")
    p.add_argument("--id", dest="identifier", required=True, help="annex_id(검색이 준 값).")
    p.add_argument("--source", choices=["law", "administrative_rule"], default="law")
    p.add_argument("--title", default=None)
    p.add_argument("--no-metadata", dest="no_metadata", action="store_true")
    p.add_argument("--no-structuring", dest="no_structuring", action="store_true")

    p = sub.add_parser("get-interpretation", help="법령해석례 본문 로드.")
    p.add_argument("--id", dest="identifier", required=True)
    p.add_argument("--source", choices=["moleg", "ministry", "all", "all_ministries"], default=None)
    p.add_argument("--ministry", default=None)
    p.add_argument("--no-metadata", dest="no_metadata", action="store_true")

    p = sub.add_parser("get-case", help="판례 본문 로드.")
    p.add_argument("--id", dest="identifier", required=True)
    p.add_argument("--no-metadata", dest="no_metadata", action="store_true")

    p = sub.add_parser("get-constitutional-decision", help="헌재 결정 본문 로드.")
    p.add_argument("--id", dest="identifier", required=True)
    p.add_argument("--no-metadata", dest="no_metadata", action="store_true")

    # ---- history / structure / delegation ------------------------------ #
    p = sub.add_parser("trace-law-history", help="개정 연혁 이벤트.")
    _add_law(p); p.add_argument("--article", default=None)
    p.add_argument("--date-from", dest="date_from", default=None)
    p.add_argument("--date-to", dest="date_to", default=None)

    p = sub.add_parser("compare-law-versions", help="개정 전후 조문 문구 비교(소스 제공 전후 쌍).")
    _add_law(p); p.add_argument("--article", default=None)

    p = sub.add_parser("find-delegated-rules", help="위임 규정·하위 법령.")
    _add_law(p); p.add_argument("--article", default=None)

    p = sub.add_parser("get-law-structure", help="법령 체계도(lsStmd 계층).")
    _add_law(p); p.add_argument("--depth", type=int, default=0)

    # ---- authority / bundles ------------------------------------------- #
    p = sub.add_parser("load-authority-context", help="조문 범위 해석·판례·헌재 권위.")
    _add_law(p); _add_articles(p, required=True); p.add_argument("--query", default=None)
    _add_budget(p); _add_as_of(p)

    p = sub.add_parser("load-legal-context-bundle", help="넓은 질문의 staged 1차 로딩.")
    p.add_argument("--query", default=None)
    _add_law(p, required=False); _add_articles(p)
    p.add_argument("--mode", choices=["question", "promulgated_bill", "statute_review"], default="question")
    _add_budget(p); _add_as_of(p)
    p.add_argument("--prom-law-nm", dest="prom_law_nm", default=None)
    p.add_argument("--prom-no", dest="prom_no", default=None)
    p.add_argument("--promulgation-dt", dest="promulgation_dt", default=None)

    p = sub.add_parser("load-institutional-system", help="명시적 다법령 제도 묶음 로딩.")
    p.add_argument("--statute", dest="statute", action="append", default=[], help="law_id. 반복 지정. (예: --statute 001248 --statute 001250)")
    _add_articles(p); _add_budget(p); _add_as_of(p)

    p = sub.add_parser("load-delegated-criteria", help="법령 앵커에서 위임 집행기준 로딩.")
    _add_law(p); _add_articles(p); p.add_argument("--query", default=None)
    _add_budget(p); _add_as_of(p)

    p = sub.add_parser("load-followup", help="bundle/expand가 준 deferred를 본문으로 실행. --json '<객체>' 또는 --json - (stdin/파이프).")
    p.add_argument("--json", dest="json_arg", required=True, help="deferred 객체 JSON, 또는 '-'로 stdin. 손타이핑 대신 data.deferred[i]를 파이프하라.")

    return parser


# --------------------------------------------------------------------------- #
# Dispatch
# --------------------------------------------------------------------------- #

def _call(api: MolegApi, args: argparse.Namespace) -> Any:
    c = args.command
    if c == "search-laws":
        return api.search_laws(args.query, as_of=args.as_of, basis=args.basis,
                               law_type=args.law_type, ministry=args.ministry, display=args.display)
    if c == "resolve-promulgated-law":
        return api.resolve_promulgated_law(prom_law_nm=args.prom_law_nm, prom_no=args.prom_no, promulgation_dt=args.promulgation_dt)
    if c == "search-administrative-rules":
        return api.search_administrative_rules(args.query, ministry=args.ministry, rule_type=args.rule_type,
                                               issued_on=args.issued_on, include_history=args.include_history, display=args.display)
    if c == "search-annex-forms":
        return api.search_annex_forms(args.query, source=args.source, search_scope=args.search_scope,
                                      annex_type=args.annex_type, ministry=args.ministry, display=args.display)
    if c == "search-interpretations":
        return api.search_interpretations(args.query, source=args.source, ministry=args.ministry,
                                          search_body=args.search_body, interpreted_on=args.interpreted_on, display=args.display)
    if c == "search-cases":
        return api.search_cases(args.query, court=args.court, court_name=args.court_name, search_body=args.search_body,
                                decided_on=args.decided_on, case_number=args.case_number, display=args.display)
    if c == "search-constitutional-decisions":
        return api.search_constitutional_decisions(args.query, search_body=args.search_body,
                                                    decided_on=args.decided_on, case_number=args.case_number, display=args.display)
    if c == "expand-legal-query":
        return api.expand_legal_query(args.query, display=args.display, include_websearch_hint=not args.no_websearch_hint)
    if c == "find-comparable-mechanisms":
        return api.find_comparable_mechanisms(args.concept, display=args.display)
    if c == "get-law":
        return api.get_law(args.law, as_of=args.as_of, basis=args.basis,
                           articles=args.article or None, include_metadata=not args.no_metadata)
    if c == "get-article":
        return api.get_article(args.law, args.article, as_of=args.as_of, basis=args.basis)
    if c == "load-article-context":
        return api.load_article_context(args.law, args.article,
                                        as_of=args.as_of, basis=args.basis, follow_moved=not args.no_follow_moved)
    if c == "get-administrative-rule":
        return api.get_administrative_rule(args.identifier, articles=args.article or None, include_metadata=not args.no_metadata)
    if c == "load-administrative-rule-context":
        return api.load_administrative_rule_context(args.identifier, articles=args.article or None,
                                                    include_metadata=not args.no_metadata, follow_moved=not args.no_follow_moved)
    if c == "get-annex-form-body":
        return api.get_annex_form_body(args.identifier, source=args.source, title=args.title,
                                       include_metadata=not args.no_metadata, attempt_structuring=not args.no_structuring)
    if c == "get-interpretation":
        return api.get_interpretation(args.identifier, source=args.source, ministry=args.ministry, include_metadata=not args.no_metadata)
    if c == "get-case":
        return api.get_case(args.identifier, include_metadata=not args.no_metadata)
    if c == "get-constitutional-decision":
        return api.get_constitutional_decision(args.identifier, include_metadata=not args.no_metadata)
    if c == "trace-law-history":
        date_range = (args.date_from, args.date_to) if (args.date_from and args.date_to) else None
        return api.trace_law_history(args.law, date_range=date_range, article=args.article)
    if c == "compare-law-versions":
        return api.compare_law_versions(args.law, article=args.article)
    if c == "find-delegated-rules":
        return api.find_delegated_rules(args.law, article=args.article)
    if c == "get-law-structure":
        return api.get_law_structure(args.law, depth=args.depth)
    if c == "load-authority-context":
        return api.load_authority_context(args.law, articles=args.article,
                                          query=args.query, budget=args.budget, as_of=args.as_of)
    if c == "load-legal-context-bundle":
        bridge = _bridge(args)
        law = args.law or None
        return api.load_legal_context_bundle(args.query, promulgation_bridge=bridge, law_identifier=law,
                                             articles=args.article or None, mode=args.mode, budget=args.budget, as_of=args.as_of)
    if c == "load-institutional-system":
        return api.load_institutional_system(_statute_args(args.statute), articles=args.article or None, budget=args.budget, as_of=args.as_of)
    if c == "load-delegated-criteria":
        return api.load_delegated_criteria(args.law, articles=args.article or None,
                                           query=args.query, budget=args.budget, as_of=args.as_of)
    if c == "load-followup":
        return api.load_followup(_read_followup(args.json_arg))
    raise CliError(f"unknown command: {c}", kind="usage", exit_code=EXIT_USAGE)


def _bridge(args: argparse.Namespace) -> dict[str, Any] | None:
    keys = {"prom_law_nm": args.prom_law_nm, "prom_no": args.prom_no, "promulgation_dt": args.promulgation_dt}
    keys = {k: v for k, v in keys.items() if v}
    return keys or None


def _read_followup(json_arg: str) -> DeferredLookup:
    text = sys.stdin.read() if json_arg == "-" else json_arg
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CliError(f"--json is not valid JSON: {exc}", kind="usage", exit_code=EXIT_USAGE) from exc
    if isinstance(obj, list):
        raise CliError("--json expects one deferred object (data.deferred[i]), not a list", kind="usage", exit_code=EXIT_USAGE)
    interface = obj.get("interface")
    if interface not in FOLLOWUP_INTERFACES and interface not in FOLLOWUP_HANDOFFS and not any(str(interface).startswith(h) for h in FOLLOWUP_HANDOFFS):
        raise CliError(
            f"unknown follow-up interface {interface!r} — pass a deferred object from a prior bundle/expand response, not a hand-written one",
            kind="usage", exit_code=EXIT_USAGE,
        )
    return DeferredLookup(
        interface=str(interface),
        query=str(obj.get("query", "")),
        reason=str(obj.get("reason", "")),
        source_type=obj.get("source_type"),
        filters=obj.get("filters") or {},
    )


# --------------------------------------------------------------------------- #
# Catalog + envelope emission
# --------------------------------------------------------------------------- #

CATALOG = {
    "convention": [
        "kind 접미사가 후보≠본문을 구조로 표시: *_hit/*_candidate/*_planning = 검색 후보(인용 불가), *_text/*_context/*_identity = 로드된 본문.",
        "인용은 항상 로드된 본문에서만 — search/expand/find-comparable 결과는 '다음에 무엇을 로드할지의 메뉴'일 뿐.",
        "출처 권위 보존: 법제처 법령 > 법제처 해석 > 부처 해석 ≠ 판례 ≠ 헌재. flags.source_type/라벨을 답에 반영.",
        "0건·호출 실패 ≠ 부재. 종료코드로 구분: 0 ok(0건 포함) · 2 모호 · 3 소스접근실패 · 4 no-result · 5 usage/순서위반.",
        "load 계열에 법령명을 주면 needs_search_first(exit 5) — 먼저 search-laws로 law_id를 얻어라.",
        "deferred는 data.deferred[i]를 load-followup --json -로 파이프(손타이핑 금지).",
        "로더(get-law/get-article)는 기본이 현행 통합본, --as-of <날짜>면 그 시점에 시행 중이던 역사 버전 본문을 로드한다(버전 자동 해결). 반환 effective_date를 확인하라 — flags.version_request_unfulfilled가 뜨면 그 시점 이전엔 시행 이력이 없다는 뜻. 개정 전후 델타는 compare-law-versions로.",
    ],
    "routing_rules": [
        "본문 로드: 살아있는 조문=get-article / 이동·삭제 가능성 있는 조문=load-article-context(기본이 이동추적).",
        "개정: 무엇이 바뀌었나(전후 문구 델타)=compare-law-versions / 어떤 개정들이 있었나(연혁)=trace-law-history.",
        "이 법 아래 무엇이 있나: 계층 조망=get-law-structure(위임 증명 아님) / 조문 단위 위임 규정=find-delegated-rules.",
        "넓은 탐색: 넓은 질의의 용어·관련법 조사계획=expand-legal-query / 유사 제도(비슷한 기제)를 가진 법 후보(설계용)=find-comparable-mechanisms.",
        "묶음 로더 — authority=특정 조문의 해석/판례/헌재 권위 / bundle=진입점 모를 때 단일법·넓은 질문(--mode) / institutional=명시된 다법령 집합(--statute 반복) / delegated=단일법의 하위규칙·별표 집행기준 본문.",
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


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None, *, api: MolegApi | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # argparse exits 0 after printing --help; anything else is a usage error.
        # Remap to EXIT_USAGE so it never collides with EXIT_AMBIGUOUS (2).
        if exc.code in (0, None):
            return EXIT_OK
        _emit({"ok": False, "command": None, "kind": "usage_error",
               "error": "잘못된 인자 — `moleg <command> --help` 또는 `moleg catalog` 참고."})
        return EXIT_USAGE

    if not args.command:
        _emit({"ok": False, "command": None, "kind": "usage_error",
               "error": "서브커맨드가 필요합니다 — `moleg catalog`로 목록을 보라."})
        return EXIT_USAGE
    if args.command == "catalog":
        _emit({"ok": True, "command": "catalog", "kind": "catalog", "source": "moleg CLI", "data": CATALOG})
        return EXIT_OK

    client = api or MolegApi()
    try:
        result = _call(client, args)
    except CliError as exc:
        _emit({"ok": False, "command": args.command, "kind": exc.kind, "error": exc.message, **exc.extra})
        return exc.exit_code
    except AmbiguousLawError as exc:
        candidates = _to_data(getattr(exc, "candidates", []), include_raw=False)
        _emit({"ok": False, "command": args.command, "kind": "ambiguous", "error": str(exc),
               "flags": {"candidates": candidates},
               "discipline": ["모호성이지 첫 후보를 고를 허가가 아님 — 후보를 사용자에게 제시."]})
        return EXIT_AMBIGUOUS
    except (RateLimitError, RetryExhaustedError) as exc:
        _emit({"ok": False, "command": args.command, "kind": "source_access_error", "error": str(exc),
               "discipline": ["일시적 소스 접근 실패이지 법령 부재 아님 — 잠시 후 재시도. 시행일 등은 폴백 규율로 채우되 위헌·판례류는 '1차 확인 필요'로 남겨라."]})
        return EXIT_SOURCE
    except ParseFailureError as exc:
        _emit({"ok": False, "command": args.command, "kind": "parse_error", "error": str(exc),
               "discipline": ["소스 응답을 정규화하지 못함(소스접근 실패·법령 부재 아님) — 다른 경로/커맨드로 확인하라."]})
        return EXIT_SOURCE
    except NoResultError as exc:
        msg = str(exc)
        if args.command in SEARCH_COMMANDS:
            # A search that finds nothing is a scoped ok:true result, not an error.
            result = []
        elif "law name" in msg or "search_laws" in msg:
            search_cmd = None
            law = getattr(args, "law", None)
            if law:
                search_cmd = [{"why": "먼저 신원 검색", "cmd": f"moleg search-laws {json.dumps(law, ensure_ascii=False)}"}]
            _emit({"ok": False, "command": args.command, "kind": "needs_search_first", "error": msg,
                   "discipline": ["로더에 법령명이 들어옴 — search-laws로 law_id를 먼저 얻어 --law에 넘겨라."],
                   "next": search_cmd or []})
            return EXIT_USAGE
        else:
            _emit({"ok": False, "command": args.command, "kind": "no_result", "error": msg,
                   "discipline": ["이 식별자·조회로 소스 본문 없음 — 검색어·범위를 밝히고 대체 경로를 시도하기 전 부재로 단정 금지."]})
            return EXIT_NO_RESULT
    except UnsupportedFormatError as exc:
        _emit({"ok": False, "command": args.command, "kind": "unsupported", "error": str(exc),
               "discipline": ["이 소스는 이 형식/경로로 제공 안 됨 — websearch·congress 등 다른 출처로 넘겨라."]})
        return EXIT_USAGE
    except MolegApiError as exc:
        _emit({"ok": False, "command": args.command, "kind": "error", "error": str(exc)})
        return EXIT_SOURCE

    include_raw = getattr(args, "raw", False)
    sig = signals_for(args.command, result, args)
    envelope = {
        "ok": True,
        "command": args.command,
        "kind": sig["kind"],
        "source": sig["source"],
    }
    if "count" in sig:
        envelope["count"] = sig["count"]
    envelope["data"] = _to_data(result, include_raw=include_raw)
    if sig["flags"]:
        envelope["flags"] = sig["flags"]
    if sig["discipline"]:
        envelope["discipline"] = sig["discipline"]
    if sig["next"]:
        envelope["next"] = sig["next"]
    _emit(envelope)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
