from __future__ import annotations

from .foundation import *
from .signals_meta import _compact_digits, _law_time_flags, _today_compact

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
    today = _today_compact()
    by_name: dict[str, list[Any]] = {}
    for h in hits:
        by_name.setdefault(getattr(h.identity, "name", ""), []).append(h)
    ambiguous = any(len(v) > 1 for v in by_name.values())
    # The current in-force version is the LATEST 시행일 that is ≤ today; every
    # other candidate (older OR future) is not currently in force. bare
    # `get-law --law` returns that current version, so only it gets the bare
    # steer; the rest get an --as-of targeting their own effective_date.
    effs_all = [_compact_digits(getattr(h.identity, "effective_date", None)) for h in hits]
    in_force_effs = [e for e in effs_all if len(e) == 8 and e <= today]
    current_eff = max(in_force_effs) if in_force_effs else None
    first_eff = effs_all[0] if effs_all else ""
    future_top = len(first_eff) == 8 and first_eff > today
    if future_top:
        flags["top_candidate_not_yet_effective"] = True
    if ambiguous:
        flags["ambiguous_versions"] = True
        discipline.append(
            "동명 후보가 시행일 다름 — 현행본은 그냥 get-law --law(로더가 현행 시행본 해결), 특정 시점 버전은 --as-of <시행일>. "
            "목록은 최신 공포순이라 상단이 미시행(장래 시행)일 수 있으니 effective_date를 오늘과 대조하라."
        )
    elif future_top:
        discipline.append(
            "최신 후보가 아직 미시행(장래 시행)이다 — get-law --law는 현행 시행본을 반환한다. effective_date를 오늘과 대조해 인용하라."
        )
    for h in hits[:3]:
        ident = h.identity
        law_id = getattr(ident, "law_id", "") or ""
        eff = getattr(ident, "effective_date", None)
        e = _compact_digits(eff)
        is_current = bool(current_eff) and e == current_eff
        status = "현행" if is_current else ("미시행" if (len(e) == 8 and e > today) else "과거")
        cmd = f"moleg get-law --law {law_id}"
        if not is_current and e:
            cmd += f" --as-of {e}"
        why = f"후보 로드: {getattr(ident, 'name', '')}" + (f" (시행 {eff}, {status})" if eff else "")
        next_cmds.append({"why": why, "cmd": cmd})
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
            cmd = f"moleg {command} --id {val}"
            # 부처 해석 본문 로드는 --id만으론 안 되고 --source ministry --ministry <기관>이 필수다.
            if command == "get-interpretation" and getattr(h.identity, "source_type", None) == "ministry":
                ministry = getattr(h.identity, "ministry", None)
                if ministry:
                    cmd += f" --source ministry --ministry {ministry}"
            out.append({"why": f"본문 로드: {getattr(h.identity, 'title', getattr(h.identity, 'name', val))}", "cmd": cmd})
    return out


def _searched_scope(command: str, args: argparse.Namespace) -> dict[str, Any]:
    scope: dict[str, Any] = {}
    for key in ("query", "concept", "basis", "ministry", "law_type", "court", "source", "search_scope", "annex_type", "rule_type", "search_body", "as_of"):
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

__all__ = [name for name in globals() if not name.startswith("__")]
