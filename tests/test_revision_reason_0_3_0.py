"""Tests for get-revision-reason (WI-P3).

The package could say *what* a statute now reads and *what changed between two
versions*, but nothing reached *why it changed*. `HistoryEvent.reason` sounded
like it should — it is a bare change-type label (본조신설, or None on all 13
events of 개인정보 보호법). Meanwhile law.go.kr was shipping the full
「개정이유 및 주요내용」 inside every version detail response and normalization
was discarding it. The download was already paid for; only the parse was missing.
"""

import json

import pytest

from moleg_api import MolegApi, NoResultError, RevisionReason
from moleg_api._laws.api_revision_reason import _flatten_strings, _revision_block_text
from moleg_api.cli import main

REASON_PAYLOAD = {
    "법령": {
        "기본정보": {
            "법령ID": "011357",
            "법령명_한글": "개인정보 보호법",
            "시행일자": "20260911",
            "공포일자": "20260310",
            "공포번호": "21445",
        },
        "제개정이유": {
            "제개정이유내용": [["[일부개정]", "◇ 개정이유", "  대규모 개인정보 유출사고가 …", ""]]
        },
        "개정문": {"개정문내용": [["국회에서 의결된 …", "⊙법률 제21445호"]]},
    }
}

VERSION_ROWS = {
    "LawSearch": {
        "law": [
            {"법령일련번호": "283839", "시행일자": "20260911", "공포번호": "21445", "법령명한글": "개인정보 보호법"},
            {"법령일련번호": "248613", "시행일자": "20230915", "공포번호": "19234", "법령명한글": "개인정보 보호법"},
        ]
    }
}


class ReasonSource:
    """Fake law.go.kr: `search` lists versions, `service` returns one version."""

    def __init__(self, *, service_payload=None, search_payload=None):
        self.service_payload = service_payload if service_payload is not None else REASON_PAYLOAD
        self.search_payload = search_payload if search_payload is not None else VERSION_ROWS
        self.calls = []

    def search(self, target, params):
        self.calls.append(("search", target, params))
        return self.search_payload

    def service(self, target, params):
        self.calls.append(("service", target, params))
        return self.service_payload

    def search_html(self, target, params):
        return ""

    def post_text(self, path, params):
        return ""


# --- text extraction ---------------------------------------------------------


def test_flattens_the_two_level_string_arrays():
    # law.go.kr nests paragraphs a list deep; a naive join yields "[['…']]".
    assert _flatten_strings([["가", "나"], ["다"]]) == ["가", "나", "다"]


def test_blank_entries_are_dropped_not_joined():
    # Otherwise an empty block renders as a run of newlines and reads as present.
    assert _flatten_strings([["", "  ", "내용"]]) == ["내용"]
    assert _revision_block_text({"제개정이유": {"제개정이유내용": [["", "  "]]}}, "제개정이유", "제개정이유내용") is None


def test_missing_block_is_none_not_an_exception():
    assert _revision_block_text({}, "제개정이유", "제개정이유내용") is None
    assert _revision_block_text({"제개정이유": "문자열"}, "제개정이유", "제개정이유내용") is None


# --- version selection -------------------------------------------------------


def test_explicit_mst_is_loaded_verbatim():
    source = ReasonSource()
    result = MolegApi(source).get_revision_reason("011357", mst="283839")
    assert isinstance(result, RevisionReason)
    assert result.mst == "283839"
    assert "대규모 개인정보 유출사고" in result.reason
    assert result.promulgation_text.startswith("국회에서 의결된")
    # an explicit mst must not spend a call listing versions
    assert not [c for c in source.calls if c[0] == "search"]


def test_no_selector_takes_the_newest_version():
    """The newest amendment is usually the one a "왜 바뀌었나" question means, even
    when its effective date has not arrived — the temporal flag handles the rest."""
    result = MolegApi(ReasonSource()).get_revision_reason("011357")
    assert result.mst == "283839"


def test_as_of_takes_the_version_in_force_then():
    result = MolegApi(ReasonSource()).get_revision_reason("011357", as_of="2024-01-01")
    assert result.mst == "248613"


def test_version_without_either_block_is_no_result():
    # A real older version: identity parses fine, law.go.kr just has no reason on file.
    source = ReasonSource(
        service_payload={"법령": {"기본정보": {"법령ID": "011357", "법령명_한글": "개인정보 보호법", "시행일자": "20110930"}}}
    )
    with pytest.raises(NoResultError):
        MolegApi(source).get_revision_reason("011357", mst="195062")


def test_unlistable_versions_steer_to_history_instead_of_guessing():
    source = ReasonSource(search_payload={"LawSearch": {"law": []}})
    with pytest.raises(NoResultError) as exc:
        MolegApi(source).get_revision_reason("011357")
    assert "trace-law-history" in str(exc.value)


# --- envelope ----------------------------------------------------------------


def test_envelope_labels_the_reason_as_the_proposer_s_own_account(capsys):
    code = main(["get-revision-reason", "--law", "011357", "--mst", "283839"],
                api=MolegApi(ReasonSource()))
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["kind"] == "revision_reason_text"
    discipline = " ".join(out["discipline"])
    # citing a proposal's stated intent as verified effect is the trap here
    assert "효과의 검증이 아님" in discipline
    # and one version's reason is not the statute's whole amendment story
    assert "일반화 금지" in discipline


def test_envelope_flags_a_future_effective_version(capsys):
    main(["get-revision-reason", "--law", "011357", "--mst", "283839"], api=MolegApi(ReasonSource()))
    out = json.loads(capsys.readouterr().out)
    assert out["flags"]["not_effective_as_of"] is True
    assert out["flags"]["mst"] == "283839"
    assert any("미시행" in d for d in out["discipline"])


def test_envelope_points_at_the_version_list(capsys):
    main(["get-revision-reason", "--law", "011357", "--mst", "283839"], api=MolegApi(ReasonSource()))
    out = json.loads(capsys.readouterr().out)
    assert any("trace-law-history" in n["cmd"] for n in out["next"])
