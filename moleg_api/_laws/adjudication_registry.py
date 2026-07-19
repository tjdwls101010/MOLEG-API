from __future__ import annotations

from .foundation import *

# Probed live on 2026-07-19 with the shared default OC: every target below
# answers both list and detail with no 활용신청 required.
#
# The authority sentence travels with the body rather than being written once for
# the family, because the two groups settle genuinely different things and a
# reader who conflates them draws a wrong conclusion about what is final.

_COMMITTEE_AUTHORITY = (
    "행정기관(위원회)의 처분·의결 — 법원 판결이 아니다. 해당 기관의 법 집행 기준·처분 사례를 보여줄 뿐, "
    "판례처럼 법 해석을 확정하지 않으며 행정소송으로 뒤집힐 수 있다."
)
_APPEAL_AUTHORITY = (
    "행정심판 재결 — 행정기관 내부의 쟁송 판단이지 법원 판결이 아니다. 처분청의 처분을 심사한 결과이며, "
    "재결에 불복하면 행정소송으로 다툴 수 있다. 판례로 인용 금지."
)

COMMITTEES: dict[str, dict[str, str]] = {
    "ppc": {"target": "ppc", "name": "개인정보보호위원회"},
    "ftc": {"target": "ftc", "name": "공정거래위원회"},
    "fsc": {"target": "fsc", "name": "금융위원회"},
    "sfc": {"target": "sfc", "name": "증권선물위원회"},
    "kcc": {"target": "kcc", "name": "방송통신위원회"},
    "nhrck": {"target": "nhrck", "name": "국가인권위원회"},
    "acr": {"target": "acr", "name": "국민권익위원회"},
    "nlrc": {"target": "nlrc", "name": "노동위원회"},
    "eiac": {"target": "eiac", "name": "고용보험심사위원회"},
    "iaciac": {"target": "iaciac", "name": "산업재해보상보험재심사위원회"},
    "oclt": {"target": "oclt", "name": "중앙토지수용위원회"},
    "ecc": {"target": "ecc", "name": "중앙환경분쟁조정위원회"},
}

# The four special tribunals cost almost nothing beyond the general 행정심판례:
# same request shape, same field vocabulary, a handful of extra keys each. Left
# out, a 소청·조세·해양안전 question would silently return nothing from decc and
# read as absence.
APPEAL_BODIES: dict[str, dict[str, str]] = {
    "decc": {"target": "decc", "name": "행정심판위원회(일반)", "kind": "administrative_appeal"},
    "acr": {"target": "acrSpecialDecc", "name": "국민권익위원회 특별행정심판", "kind": "special_administrative_appeal"},
    "adap": {"target": "adapSpecialDecc", "name": "소청심사위원회", "kind": "special_administrative_appeal"},
    "tt": {"target": "ttSpecialDecc", "name": "조세심판원", "kind": "special_administrative_appeal"},
    "kmst": {"target": "kmstSpecialDecc", "name": "해양안전심판원", "kind": "special_administrative_appeal"},
}


def committee_spec(code: str) -> dict[str, str]:
    spec = COMMITTEES.get(str(code).strip().lower())
    if not spec:
        raise CliOrUsageError(
            f"알 수 없는 위원회 코드 {code!r} — 가능한 값: {', '.join(sorted(COMMITTEES))}"
        )
    return {**spec, "code": str(code).strip().lower(),
            "source_type": "committee_decision", "authority": _COMMITTEE_AUTHORITY}


def appeal_spec(code: str) -> dict[str, str]:
    spec = APPEAL_BODIES.get(str(code).strip().lower())
    if not spec:
        raise CliOrUsageError(
            f"알 수 없는 심판기관 코드 {code!r} — 가능한 값: {', '.join(sorted(APPEAL_BODIES))}"
        )
    return {**spec, "code": str(code).strip().lower(),
            "source_type": spec["kind"], "authority": _APPEAL_AUTHORITY}


class CliOrUsageError(UnsupportedFormatError):
    """An unknown body code — a caller mistake, not a source failure.

    Raised as UnsupportedFormatError so the CLI maps it to a usage exit rather
    than letting a typo look like the agency has no records.
    """

__all__ = [name for name in globals() if not name.startswith("__")]
