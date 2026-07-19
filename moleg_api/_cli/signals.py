from __future__ import annotations

from .foundation import *
from .signal_helpers import (
    _annex_next, _broaden_next, _comparable_next, _id_next,
    _law_list_signals, _searched_scope, _snake,
)
from .signals_meta import (
    SINGLE_META, _article_flags, _deferred_next, _gap_signals,
    _has_supplementary, _law_time_flags, _resolve_list_kind,
    _real_moved_to, _standing_list_discipline,
)
from .signal_helpers import _authority_counts

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
            query = getattr(args, "query", None)
            # 헌재·판례 검색 기본은 제목(사건명) — doctrine·법리 키워드는 --search-body(본문 전체)라야 매칭된다.
            if eff_command in ("search-constitutional-decisions", "search-cases") and not getattr(args, "search_body", False) and query:
                next_cmds.append({"why": "제목이 아닌 본문(판시·주문·이유) 전체 검색으로 재시도", "cmd": f"moleg {eff_command} {json.dumps(query, ensure_ascii=False)} --search-body"})
                discipline.append("헌재·판례 검색 기본은 제목 검색 — doctrine·본문 키워드로 0건이면 --search-body로 재시도하라.")
            # 별표 검색은 스코프(title=별표 제목 / source=소관 법령명)에 따라 결과가 갈린다 — 반대 스코프로 재시도.
            elif eff_command == "search-annex-forms" and query:
                scope = getattr(args, "search_scope", "title") or "title"
                other = "source" if scope == "title" else "title"
                next_cmds.append({"why": f"별표 검색 스코프 전환({scope}→{other})으로 재시도", "cmd": f"moleg search-annex-forms {json.dumps(query, ensure_ascii=False)} --search-scope {other}"})
                discipline.append("별표 검색 title=별표 제목 / source=소관 법령명 매칭(토큰 근접) — 0건이면 반대 스코프로 재시도하라.")
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
        if flags.get("not_effective_as_of"):
            source = "법제처 / 공포본(장래 시행 — 아직 미시행)"
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
        if flags.get("not_effective_as_of"):
            source = "법제처 / 공포본 조문(장래 시행 — 아직 미시행)"
        discipline.append("정의·예외·적용대상·요건은 text의 항·호·목 중첩에 있다 — 조문제목·상위 조문내용만으로 요약 금지.")
        moved = _real_moved_to(result)
        if moved:
            next_cmds.append({"why": "이동 목적지 로드", "cmd": f"moleg load-article-context --law {result.identity.law_id or ''} {moved}"})

    elif tname == "AdjudicationText":
        ident = result.identity
        # The kind carries the authority, not just the shape. An 행정심판 재결 and
        # a 위원회 처분 are both "an agency decided something" structurally, and
        # collapsing them into one kind is how a reader ends up treating a
        # reviewable disposition as a settled one.
        kind = ("administrative_appeal_text" if "appeal" in (ident.source_type or "")
                else "committee_decision_text")
        source = f"법제처 / {ident.body_name}"
        flags["source_type"] = ident.source_type
        flags["source_authority"] = ident.source_authority
        flags["body"] = {"code": ident.body, "name": ident.body_name}
        if ident.respondent_agency:
            flags["respondent_agency"] = ident.respondent_agency
        if ident.review_agency:
            flags["review_agency"] = ident.review_agency
        discipline.append(ident.source_authority)
        # 감독기관이 "확인했는가"를 묻는 것이 이 계열의 용도다. 처분이 있었다는 사실은
        # 그 기관이 그 사안을 인지·판단했다는 1차 증거이고, 없다는 것은 부재의 증명이
        # 아니라 이 검색 범위에서 못 찾았다는 뜻일 뿐이다.
        discipline.append(
            "이 결정의 존재는 해당 기관이 그 사안을 실제로 판단했다는 1차 기록 — "
            "다만 '이 기관에 기록이 없다'가 '문제가 없었다'는 뜻은 아니다(미접수·미조사·비공개 가능)."
        )
        if ident.decided_on:
            flags["decided_on"] = ident.decided_on

    elif tname == "LawToc":
        tf, tl = _law_time_flags(result.identity, as_of)
        flags.update(tf); discipline.extend(tl)
        flags["article_count"] = result.article_count
        gone = [e.article for e in result.entries if e.is_deleted or e.moved_to]
        if gone:
            flags["articles_deleted_or_moved"] = len(gone)
        # kind ends in _map, not _text — the naming convention already says this
        # is not citable, but a목차 is close enough to content to be misread as
        # having been read, so say it outright.
        discipline.append(
            "목차는 본문이 아님 — 조번호·조제목만으로 조문 내용을 단정하거나 인용하지 마라. "
            "인용은 get-article/get-law --article로 본문을 로드한 뒤에."
        )
        if result.identity.law_id:
            next_cmds.append({
                "why": "목차에서 고른 조문 본문 로드",
                "cmd": f"moleg get-article --law {result.identity.law_id} <제N조>",
            })

    elif tname == "RevisionReason":
        tf, tl = _law_time_flags(result.identity, as_of)
        flags.update(tf); discipline.extend(tl)
        if result.mst:
            flags["mst"] = result.mst
        flags["has_promulgation_text"] = bool(result.promulgation_text)
        # 개정이유는 입법자·정부가 스스로 밝힌 취지 서술이지 중립적 사실 확인이 아니다.
        # 이걸 "그 법이 왜 바뀌었는지"의 확정 답으로 평탄화하면 제안자의 주장을 근거로
        # 둔갑시키게 된다 — 실제 효과·부작용은 별도 확인이 필요하다.
        discipline.append(
            "개정이유는 제안자(정부·의원)가 밝힌 취지 서술이지 효과의 검증이 아님 — "
            "'왜 바뀌었나'의 자기 진술로 인용하고, 실제 효과·부작용은 별도 근거로 확인하라."
        )
        # 이 텍스트는 오직 이 한 버전의 것이다. 법 전체의 개정 서사로 일반화하면
        # 다른 개정들의 이유를 조용히 이 하나로 대체하게 된다.
        discipline.append(
            "이 개정이유는 이 버전(mst) 한 건의 것 — 법 전체의 개정 서사로 일반화 금지. "
            "다른 개정의 이유는 각 버전 mst로 따로 로드하라."
        )
        if result.identity.law_id:
            next_cmds.append({
                "why": "다른 개정 버전(mst) 목록 확인",
                "cmd": f"moleg trace-law-history --law {result.identity.law_id}",
            })

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
            disposition = getattr(result.identity, "decision_type", None)
            if disposition:
                flags["disposition"] = disposition
            elif not (getattr(result, "holdings", None) or getattr(result, "summary", None) or getattr(result, "reviewed_statutes", None)):
                discipline.append("주문·처분 결과가 구조화 필드에 없음 — full_text의 【주 문】을 직접 읽어 각하/기각/합헌/위헌을 판단하고, 각하·기각을 본안(merits) 판단으로 오인하지 마라.")
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

    if getattr(args, "brief", False):
        dropped = getattr(args, "brief_dropped", []) or []
        flags["brief"] = {"withheld": dropped}
        # The candidate-vs-body rule applies *within* a loaded document too: a
        # 요지 is the court's own précis, and quoting it as the ruling's wording
        # is the same error as quoting a search hit as text.
        discipline.append(
            "요지·판시사항만 로드됨(전문 미로드) — 판시 문구의 축자 인용은 --brief 없이 전문을 로드한 뒤에."
            + (f" 생략된 항목: {', '.join(dropped)}." if dropped else " 이 문서에는 생략할 전문 항목이 없었다.")
        )

    return {"kind": kind, "source": source, "flags": flags,
            "discipline": discipline, "next": next_cmds[:3]}

__all__ = [name for name in globals() if not name.startswith("__")]
