from __future__ import annotations

from .foundation import *
from .._version import __version__
from .catalog import CATALOG
from .constants import (
    CliError,
    EXIT_AMBIGUOUS,
    EXIT_NO_RESULT,
    EXIT_OK,
    EXIT_SOURCE,
    EXIT_USAGE,
    SEARCH_COMMANDS,
)
from .data import _to_data
from .dispatch import _call
from .parser import build_parser
from .payload_size import large_payload_signals
from .signals import signals_for

def _emit(payload: dict[str, Any]) -> None:
    # Stamped here rather than at each call site so no envelope — success, error,
    # or catalog — can ship without it. A consumer that cannot tell which version
    # answered cannot tell whether a missing field means "not supported yet" or
    # "the call failed", which is how a stale install reads as a data gap.
    stamped: dict[str, Any] = {}
    for key, value in payload.items():
        stamped[key] = value
        if key == "command":
            stamped["version"] = __version__
    if "version" not in stamped:
        stamped["version"] = __version__
    print(json.dumps(stamped, ensure_ascii=False, indent=2))


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
    except AsOfBeforeCoverageError as exc:
        law_id = getattr(exc, "law_id", None) or getattr(args, "law", "")
        _emit({"ok": False, "command": args.command, "kind": "version_request_unfulfilled", "error": str(exc),
               "flags": {"as_of": getattr(args, "as_of", None), "earliest_available": getattr(exc, "earliest_available", None)},
               "discipline": ["요청 시점이 이 법령의 통합본 제공 최초 시행일보다 앞선다(일시적 실패 아님) — 그 이전 본문은 통합본으로 제공되지 않으니 연혁으로 확인하라."],
               "next": [{"why": "가용 최초 버전·개정 연혁 확인", "cmd": f"moleg trace-law-history --law {law_id}"}]})
        return EXIT_NO_RESULT
    except ParseFailureError as exc:
        _emit({"ok": False, "command": args.command, "kind": "parse_error", "error": str(exc),
               "discipline": ["소스가 인식 불가한 형태의 응답을 줌 — 같은 호출을 재시도해도 대개 그대로다(일시 장애와 다름).",
                              "식별자 오류 가능성을 먼저 배제하라(search-*로 신원 재확인). 그래도 같으면 다른 경로/커맨드로 확인하고, 부재로 단정하지 마라."]})
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
                   "discipline": ["이 식별자·조회로 소스 본문 없음 — 일시 장애가 아니니 재시도는 무의미하다. 식별자가 틀렸을 수 있으니 search-* 계열로 신원을 재확인하라.",
                                  "검색어·범위를 밝히고 대체 경로를 시도하기 전 부재로 단정 금지."]})
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
    # Measured on the serialized data, after every narrowing option has had its
    # effect — a guess from a row count would fire on 139 short articles and stay
    # quiet on 20 long ones, and would need updating for every command added later.
    size_flags, size_discipline = large_payload_signals(
        args.command,
        len(json.dumps(envelope["data"], ensure_ascii=False)),
        {"articles": len(result.articles)} if isinstance(getattr(result, "articles", None), list) else None,
    )
    sig["flags"].update(size_flags)
    sig["discipline"].extend(size_discipline)
    if sig["flags"]:
        envelope["flags"] = sig["flags"]
    if sig["discipline"]:
        envelope["discipline"] = sig["discipline"]
    if sig["next"]:
        envelope["next"] = sig["next"]
    _emit(envelope)
    return EXIT_OK

__all__ = [name for name in globals() if not name.startswith("__")]
