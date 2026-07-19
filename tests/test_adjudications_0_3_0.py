"""Committee decisions and administrative appeals (WI-P7).

The oversight question this package could not answer was "did the supervising
body actually act?" The statute was reachable and the court ruling was
reachable, but the disposition in between — a 개인정보보호위원회 의결, a 공정위
과징금 처분, a 조세심판원 재결 — was outside the surface entirely.

Seventeen bodies, one code path: the request shape is identical and only the
vocabulary differs. So most of what these tests protect is the normalization
(every body's spelling of the same concept lands in the same field) and the
authority labelling (none of these is precedent, and the two groups are not
interchangeable with each other either).
"""

import json

import pytest

from moleg_api import AdjudicationText, MolegApi, NoResultError
from moleg_api._laws.adjudication_registry import APPEAL_BODIES, COMMITTEES, appeal_spec, committee_spec
from moleg_api._normalization.adjudications import (
    _adjudication_date,
    _clean,
    _flatten,
    adjudication_detail,
    adjudication_rows,
    normalize_adjudication_identity,
)
from moleg_api.cli import main
from moleg_api.errors import UnsupportedFormatError

PPC_ROW = {
    "결정문일련번호": "9745",
    "안건명": "「산업기술의 유출방지 및 보호에 관한 법률 시행규칙」 일부개정안",
    "의결일": "2025.4.23.",
    "결정구분": "심의ㆍ의결",
}

PPC_DETAIL = {
    "PpcService": {
        "의결서": {
            "결정문일련번호": "9745",
            "안건명": "개인정보 침해요인 평가에 관한 건",
            "의결일자": "2025.4.23.",
            "주문": "원안 동의한다.",
            "결정요지": "요지 본문",
            "이유": "이유 본문",
            "기관명": "개인정보보호위원회",
        }
    }
}

DECC_DETAIL = {
    "PrecService": {
        "재결청": "국민권익위원회",
        "처분청": "○○시장",
        "행정심판례일련번호": "273321",
        "사건명": "정보공개 거부처분 취소청구",
        "의결일자": "2025-07-01",
        "주문": "청구인의 청구를 기각한다.",
        "재결요지": "재결 요지",
        "이유": "재결 이유",
        "청구취지": "거부처분을 취소한다.",
    }
}


class FakeSource:
    def __init__(self, *, search_payload=None, service_payload=None):
        self.search_payload = search_payload or {}
        self.service_payload = service_payload or {}
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


# --- registry -------------------------------------------------------------------


def test_every_committee_probed_live_is_registered():
    # All twelve answered list and detail on 2026-07-19 with the shared default OC.
    assert set(COMMITTEES) == {
        "ppc", "ftc", "fsc", "sfc", "kcc", "nhrck",
        "acr", "nlrc", "eiac", "iaciac", "oclt", "ecc",
    }


def test_special_tribunals_are_registered_alongside_the_general_docket():
    # Omitting them would make a 소청·조세·해양안전 question return nothing from
    # decc and read as absence rather than as "wrong docket".
    assert set(APPEAL_BODIES) == {"decc", "acr", "adap", "tt", "kmst"}
    assert APPEAL_BODIES["tt"]["target"] == "ttSpecialDecc"


def test_committee_and_appeal_authority_labels_are_distinct():
    committee = committee_spec("ppc")["authority"]
    appeal = appeal_spec("decc")["authority"]
    assert committee != appeal
    assert "판결이 아니다" in committee and "판결이 아니다" in appeal
    assert "행정소송" in committee and "행정소송" in appeal


def test_unknown_body_code_is_a_caller_mistake_not_an_empty_docket():
    # Mapping a typo to "no records" would let a misspelled agency read as an
    # agency that never acted — the exact wrong conclusion for oversight.
    with pytest.raises(UnsupportedFormatError):
        committee_spec("nope")
    with pytest.raises(UnsupportedFormatError):
        appeal_spec("nope")


# --- normalization --------------------------------------------------------------


def test_rows_are_found_by_shape_not_by_target_name():
    """The four special tribunals answer a request for `acrSpecialDecc` with rows
    keyed `decc`. Keying on the requested target returns nothing, which reads as
    "this tribunal has no records"."""
    payload = {"Decc": {"decc": [{"특별행정심판재결례일련번호": "1"}]}}
    assert adjudication_rows(payload, "acrSpecialDecc") == [{"특별행정심판재결례일련번호": "1"}]


def test_detail_unwraps_through_the_uigyeolseo_wrapper():
    # ppc and acr nest the document one level deeper than the other ten.
    body = adjudication_detail(PPC_DETAIL)
    assert body["주문"] == "원안 동의한다."


@pytest.mark.parametrize(
    "field, key",
    [("summary", "결정요지"), ("summary", "판단요지"), ("summary", "판정요지"), ("summary", "재결요지")],
)
def test_every_body_s_word_for_the_gist_lands_in_summary(field, key):
    from moleg_api._normalization.adjudications import normalize_adjudication_text

    identity = normalize_adjudication_identity({}, spec=committee_spec("ppc"))
    text = normalize_adjudication_text({key: "가치 있는 요지"}, identity)
    assert getattr(text, field) == "가치 있는 요지"


def test_dotted_unpadded_dates_are_normalized():
    """Committees emit `2020.6.8.`, which the shared compact_date passes through
    untouched. An un-normalized date sorts wrong, and in an oversight question the
    date is the finding: when the regulator knew, and how long it then took."""
    assert _adjudication_date("2020.6.8.") == "20200608"
    assert _adjudication_date("2025.4.23.") == "20250423"
    assert _adjudication_date("2017.07.31") == "20170731"
    assert _adjudication_date("2025-04-23") == "20250423"
    assert _adjudication_date(None) is None


def test_literal_null_strings_are_not_passed_off_as_content():
    # Several targets return the four-character string "null" for absent fields;
    # rendered as-is it becomes a plausible-looking case number in an answer.
    assert _clean("null") is None
    assert _clean("  ") is None
    assert _clean("2023서카2662") == "2023서카2662"


def test_nested_field_values_are_flattened_not_repr_d():
    assert _flatten(["가", ["나", "다"]]) == "가\n나\n다"
    assert _flatten({"피심정보명": "갑", "피심정보내용": "을"}) == "갑\n을"


def test_identity_carries_the_body_and_its_authority():
    identity = normalize_adjudication_identity(PPC_ROW, spec=committee_spec("ppc"))
    assert identity.decision_id == "9745"
    assert identity.body == "ppc" and identity.body_name == "개인정보보호위원회"
    assert identity.source_type == "committee_decision"
    assert identity.decided_on == "20250423"


# --- SDK ------------------------------------------------------------------------


def test_committee_search_returns_candidates_with_a_load_follow_up():
    source = FakeSource(search_payload={"Ppc": {"ppc": [PPC_ROW]}})
    hits = MolegApi(source).search_committee_decisions("유출", committee="ppc")
    assert len(hits) == 1
    assert hits[0].follow_up.interface == "get_committee_decision"
    assert hits[0].follow_up.filters == {"body": "ppc"}
    assert source.calls[0][1] == "ppc"


def test_rows_without_an_id_are_dropped_rather_than_returned_unloadable():
    source = FakeSource(search_payload={"Ppc": {"ppc": [{"안건명": "제목만 있는 행"}]}})
    assert MolegApi(source).search_committee_decisions(None, committee="ppc") == []


def test_committee_load_normalizes_across_the_wrapper():
    result = MolegApi(FakeSource(service_payload=PPC_DETAIL)).get_committee_decision("9745", committee="ppc")
    assert isinstance(result, AdjudicationText)
    assert result.disposition == "원안 동의한다."
    assert result.summary == "요지 본문" and result.reasoning == "이유 본문"
    assert "주문" in result.text and "이유" in result.text


def test_appeal_load_keeps_both_agencies_apart():
    # 재결청 (who reviewed) and 처분청 (who acted) answer different oversight
    # questions; collapsing them loses which agency is actually on the hook.
    result = MolegApi(FakeSource(service_payload=DECC_DETAIL)).get_administrative_appeal("273321")
    assert result.identity.review_agency == "국민권익위원회"
    assert result.identity.respondent_agency == "○○시장"
    assert result.claim == "거부처분을 취소한다."


def test_empty_detail_body_is_no_result_not_a_blank_document():
    source = FakeSource(service_payload={"PpcService": {"의결서": {"주문": "null", "이유": ""}}})
    with pytest.raises(NoResultError):
        MolegApi(source).get_committee_decision("999999", committee="ppc")


def test_missing_id_is_rejected_before_a_request_is_spent():
    source = FakeSource()
    with pytest.raises(NoResultError):
        MolegApi(source).get_committee_decision("  ", committee="ppc")
    assert source.calls == []


# --- envelope -------------------------------------------------------------------


def test_committee_envelope_refuses_to_be_read_as_precedent(capsys):
    code = main(["get-committee-decision", "--id", "9745", "--committee", "ppc"],
                api=MolegApi(FakeSource(service_payload=PPC_DETAIL)))
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["kind"] == "committee_decision_text"
    assert out["flags"]["source_type"] == "committee_decision"
    assert "판례" not in out["kind"]
    assert any("법원 판결이 아니다" in d for d in out["discipline"])


def test_appeal_envelope_gets_its_own_kind(capsys):
    # Sharing one kind with committee decisions is how a reviewable disposition
    # gets treated as a settled one.
    main(["get-administrative-appeal", "--id", "273321"],
         api=MolegApi(FakeSource(service_payload=DECC_DETAIL)))
    out = json.loads(capsys.readouterr().out)
    assert out["kind"] == "administrative_appeal_text"
    assert out["flags"]["source_type"] == "administrative_appeal"


def test_zero_hits_are_not_sold_as_the_agency_never_acting(capsys):
    code = main(["search-committee-decisions", "없는질의", "--committee", "ppc"],
                api=MolegApi(FakeSource(search_payload={"Ppc": {"ppc": []}})))
    out = json.loads(capsys.readouterr().out)
    assert code == 0 and out["ok"] is True and out["count"] == 0
    discipline = " ".join(out["discipline"])
    assert "처분한 적 없음" in discipline and "증명이 아님" in discipline


def test_appeal_search_points_at_the_special_dockets(capsys):
    main(["search-administrative-appeals", "소청"],
         api=MolegApi(FakeSource(search_payload={"Decc": {"decc": []}})))
    out = json.loads(capsys.readouterr().out)
    assert any("특별행정심판" in d for d in out["discipline"])


def test_brief_drops_the_reasoning_which_is_the_bulk(capsys):
    main(["get-committee-decision", "--id", "9745", "--committee", "ppc", "--brief"],
         api=MolegApi(FakeSource(service_payload=PPC_DETAIL)))
    out = json.loads(capsys.readouterr().out)
    assert out["data"]["reasoning"] is None
    assert out["data"]["summary"] == "요지 본문"
    assert "reasoning" in out["flags"]["brief"]["withheld"]
