from __future__ import annotations

from .foundation import *

# Measured on 2026-07-19 against live law.go.kr (bytes of the emitted envelope):
#
#   load-delegated-criteria --budget standard   513,570
#   load-institutional-system --budget standard 396,609
#   get-law (139 articles, no --article)        276,748
#   get-case (one decision)                      82,700
#   load-legal-context-bundle --budget broad      37,822
#   load-authority-context                         6,889
#   get-article                                    2,280
#
# The threshold is in *characters*, not bytes, because characters track token
# cost and Korean text is three bytes each — measuring bytes would make the same
# amount of reading look three times worse in Korean than in English. 20,000
# characters is roughly 10–13k tokens: enough that a caller who could have
# narrowed the request should be told they didn't.
LARGE_PAYLOAD_CHARS = 20_000

# Searches are exempt. They return candidate identities by design — that breadth
# is what resolves ambiguity, and 20 hits costs ~18,000 characters, close enough
# to the line that including them would make the signal fire on the one command
# where the size is the intended behaviour.
_EXEMPT_PREFIXES = ("search-", "resolve-", "expand-", "find-comparable")

_ADVICE = {
    "get-law": "전체 로드 대신 --toc로 조문 지도를 먼저 받고, 필요한 조문만 --article로 표적 로드하라.",
    "get-case": "--brief로 요지(판시사항·결정요지)만 먼저 받고, 전문은 인용이 필요할 때만 로드하라.",
    "get-constitutional-decision": "--brief로 요지만 먼저 받고, 전문은 인용이 필요할 때만 로드하라.",
    "get-interpretation": "--brief로 질의·회답만 먼저 받고, 전문은 인용이 필요할 때만 로드하라.",
    "load-delegated-criteria": "--budget minimal로 좁히거나, 기준이 걸린 조문만 --article로 지정하라.",
    "load-institutional-system": "--budget minimal로 좁히거나, 실제로 볼 법령만 --statute으로 지정하라.",
    "load-legal-context-bundle": "--budget minimal로 좁히거나, 진입 조문을 --article로 지정하라.",
}

_DEFAULT_ADVICE = "이 응답은 컨텍스트를 크게 차지한다 — 범위를 좁힐 인자(--article·--budget·--brief 등)가 있는지 확인하라."


def large_payload_signals(command: str, data_chars: int, extra: dict[str, Any] | None = None) -> tuple[dict[str, Any], list[str]]:
    """Flag a response big enough that the caller should have narrowed it.

    Conditional like every other signal here: a small statute loads silently, so
    the flag firing means something. Measured on the serialized data rather than
    guessed from a row count, because the same number of articles can differ by
    an order of magnitude in length — and because a size check written against
    the actual output keeps working for commands added later.
    """
    if data_chars < LARGE_PAYLOAD_CHARS or any(command.startswith(p) for p in _EXEMPT_PREFIXES):
        return {}, []
    flags: dict[str, Any] = {"large_payload": {"chars": data_chars}}
    if extra:
        flags["large_payload"].update(extra)
    return flags, [_ADVICE.get(command, _DEFAULT_ADVICE)]

__all__ = [name for name in globals() if not name.startswith("__")]
