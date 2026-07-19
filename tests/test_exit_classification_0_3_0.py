"""Regression tests for the 0.3.0 exit-code reclassification (WI-P1).

Two defects motivated these:

1. `unwrap.py` raised `ParseFailureError` without importing it — a leftover of the
   0.2.3 file-split refactor that shipped in 0.2.4. Every unwrap failure became a
   `NameError` traceback instead of a JSON envelope, so the CLI's error contract
   silently stopped holding on that path.
2. A nonexistent identifier came back as exit 3 with "일시적 … 재시도" discipline.
   law.go.kr answers a detail lookup for a bad identifier with an *empty* body, a
   permanent fact — telling the caller to retry sent it into a loop that can never
   succeed, and the "부재 아님" wording actively misled it.
"""

import json

import pytest

from moleg_api.cli import main
from moleg_api.errors import NoResultError, ParseFailureError, RateLimitError
from moleg_api._normalization.unwrap import is_empty_payload, unwrap_service_payload


class StubApi:
    """Minimal MolegApi stand-in: every call raises `exc` or returns `result`."""

    def __init__(self, *, exc=None, result=None):
        self.exc = exc
        self.result = result

    def __getattr__(self, _name):
        def call(*_args, **_kwargs):
            if self.exc is not None:
                raise self.exc
            return self.result

        return call


# --- unwrap-level classification -------------------------------------------------


def test_empty_service_payload_is_no_result_not_parse_failure():
    # law.go.kr's real answer for get-article --law 999999 on target eflawjosub
    with pytest.raises(NoResultError):
        unwrap_service_payload({}, "eflawjosub")


def test_unrecognized_nonempty_payload_still_raises_parse_failure():
    # Guards the import-loss regression: this line used to NameError. It also keeps
    # the empty-payload branch from swallowing shapes we merely failed to recognize.
    with pytest.raises(ParseFailureError):
        unwrap_service_payload({"어떤키": "내용이 있는 값", "다른키": "또 다른 값"}, "prec")


def test_is_empty_payload_is_conservative():
    assert is_empty_payload({})
    assert is_empty_payload({"법령": ""})
    assert is_empty_payload({"법령": None, "부가": []})
    # anything carrying real content must not be mistaken for a missing record
    assert not is_empty_payload({"법령": "내용"})
    assert not is_empty_payload({"법령": 0})
    assert not is_empty_payload({"법령": {"조문": "x"}})


def test_no_result_sentence_payload_still_maps_to_no_result():
    with pytest.raises(NoResultError):
        unwrap_service_payload({"Law": "일치하는 법령이 없습니다.  법령명을 확인하여 주십시오."}, "law")


# --- CLI-level envelope contract -------------------------------------------------


def test_bad_identifier_exits_4_and_does_not_claim_transience(capsys):
    code = main(
        ["get-article", "--law", "999999", "제3조"],
        api=StubApi(exc=NoResultError("Source returned an empty body for target eflawjosub")),
    )
    out = json.loads(capsys.readouterr().out)
    assert code == 4
    assert out["kind"] == "no_result"
    discipline = " ".join(out["discipline"])
    assert "재시도는 무의미" in discipline
    assert "search-*" in discipline
    # the old exit-3 wording promised a retry would fix it
    assert "잠시 후 재시도" not in discipline


def test_real_transient_failure_still_exits_3_as_source_access_error(capsys):
    code = main(["get-law", "--law", "011357"], api=StubApi(exc=RateLimitError("429 Too Many Requests")))
    out = json.loads(capsys.readouterr().out)
    assert code == 3
    assert out["kind"] == "source_access_error"
    assert any("재시도" in d for d in out["discipline"])


def test_parse_error_keeps_exit_3_but_drops_the_transient_story(capsys):
    code = main(
        ["get-case", "--id", "193332"],
        api=StubApi(exc=ParseFailureError("Could not unwrap service payload for target prec")),
    )
    out = json.loads(capsys.readouterr().out)
    assert code == 3
    assert out["kind"] == "parse_error"
    discipline = " ".join(out["discipline"])
    assert "재시도해도" in discipline
    assert "식별자 오류 가능성" in discipline


def test_catalog_exit_table_distinguishes_the_two_exit_3_kinds(capsys):
    code = main(["catalog"], api=StubApi())
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    convention = " ".join(out["data"]["convention"])
    assert "source_access_error" in convention and "parse_error" in convention
    assert "no_result(exit 4)" in convention
