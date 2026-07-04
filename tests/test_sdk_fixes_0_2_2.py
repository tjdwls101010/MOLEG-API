"""Regression tests for the 0.2.2 defect fixes (Tier 1+2).

Each fix was reproduced live against law.go.kr, then locked here with a
deterministic unit. Date-dependent logic uses far-future (2999) / far-past
(2010-2020) dates so the assertions are not brittle against `date.today()`.
"""

import argparse

import pytest

from moleg_api import AsOfBeforeCoverageError, MolegApi, UnsupportedFormatError
from moleg_api.cli import (
    _id_next,
    _law_list_signals,
    _law_time_flags,
    build_parser,
    main,
    parse_as_of,
    signals_for,
)
from moleg_api.laws import structured_table_from_rows
from moleg_api.models import (
    AnnexFormIdentity,
    LawHit,
    LawIdentity,
)
from moleg_api.normalization import (
    law_name_before_article,
    mask_oc_param,
    normalize_delegated_rules,
    normalize_diff_changes,
    normalize_history_events,
    parse_article_references,
    parse_constitutional_disposition,
)


def _ns(**kw):
    kw.setdefault("as_of", None)
    return argparse.Namespace(**kw)


def _law(**kw):
    kw.setdefault("law_id", "001638")
    kw.setdefault("name", "도로교통법")
    kw.setdefault("basis", "effective")
    return LawIdentity(**kw)


# --------------------------------------------------------------------------- #
# T1-A / T2-D — future-effective (미시행) and current-version signalling
# --------------------------------------------------------------------------- #

def test_law_time_flags_future_version_marks_not_effective():
    flags, lines = _law_time_flags(_law(effective_date="29991231"), None)
    assert flags["not_effective_as_of"] is True
    assert any("미시행" in line for line in lines)


def test_law_time_flags_current_version_has_no_future_flag():
    flags, _ = _law_time_flags(_law(effective_date="20200101"), None)
    assert "not_effective_as_of" not in flags


def test_law_time_flags_as_of_mismatch_emits_version_mismatch():
    flags, lines = _law_time_flags(_law(effective_date="20200101"), "2018-01-01")
    assert flags["version_mismatch"] == {"requested": "20180101", "loaded": "20200101"}
    assert flags["version_request_unfulfilled"] is True
    assert any("trace-law-history" in line for line in lines)


def test_lawtext_future_version_relabels_source():
    from moleg_api.models import LawText

    result = LawText(identity=_law(effective_date="29991231"), articles=[], raw={})
    sig = signals_for("get-law", result, _ns(as_of="29991231"))
    assert sig["flags"]["not_effective_as_of"] is True
    assert "현행 법령 본문" not in sig["source"]


def test_law_list_signals_currency_and_steer_labels():
    hits = [
        LawHit(identity=_law(effective_date="29991231", mst="a")),  # future
        LawHit(identity=_law(effective_date="20200101", mst="b")),  # current (max <= today)
        LawHit(identity=_law(effective_date="20100101", mst="c")),  # superseded past
    ]
    sig = _law_list_signals(hits)
    assert sig["flags"]["top_candidate_not_yet_effective"] is True
    cmds = {n["cmd"]: n["why"] for n in sig["next"]}
    # only the current version gets a bare command; others target their own eff
    assert "moleg get-law --law 001638" in cmds
    assert "현행" in cmds["moleg get-law --law 001638"]
    assert any(c.endswith("--as-of 29991231") for c in cmds)
    assert any(c.endswith("--as-of 20100101") for c in cmds)


# --------------------------------------------------------------------------- #
# T2-J — strict --as-of validation
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("raw,expected", [("2019-06-01", "20190601"), ("20190601", "20190601"), (" 2020-1-2 ", None)])
def test_parse_as_of_accepts_valid_formats(raw, expected):
    if expected is None:
        # zero-padded only via strptime; "2020-1-2" is actually valid for %Y-%m-%d
        assert parse_as_of(raw) == "20200102"
    else:
        assert parse_as_of(raw) == expected


@pytest.mark.parametrize("bad", ["garbage", "2019-13-99", "2019-02-30", "19", "99999999"])
def test_parse_as_of_rejects_bad_dates(bad):
    with pytest.raises(Exception) as exc:
        parse_as_of(bad)
    assert getattr(exc.value, "exit_code", None) == 5


# --------------------------------------------------------------------------- #
# T2-K — as-of before coverage maps to a non-transient envelope
# --------------------------------------------------------------------------- #

class _CoverageFloorApi:
    def get_law(self, *a, **k):
        raise AsOfBeforeCoverageError("before coverage", law_id="001823", earliest_available="20090301")


def test_as_of_before_coverage_envelope(capsys):
    code = main(["get-law", "--law", "001823", "--as-of", "2000-01-01"], api=_CoverageFloorApi())
    import json

    out = json.loads(capsys.readouterr().out)
    assert code == 4
    assert out["kind"] == "version_request_unfulfilled"
    assert out["flags"]["earliest_available"] == "20090301"
    assert any("trace-law-history" in n["cmd"] for n in out["next"])


# --------------------------------------------------------------------------- #
# G2 — compare-law-versions article labels from content, not the row index
# --------------------------------------------------------------------------- #

def test_normalize_diff_changes_labels_from_content_header():
    payload = {
        "구조문목록": {"조문": [
            {"no": "1", "content": "제8조의2(주택임대차위원회) ① 종전"},
            {"no": "2", "content": "④ 종전 항"},
        ]},
        "신조문목록": {"조문": [
            {"no": "1", "content": "제8조의2(주택임대차위원회) ① 개정"},
            {"no": "2", "content": "④ 개정 항"},
        ]},
    }
    changes = normalize_diff_changes(payload)
    assert [c.article for c in changes] == ["제8조의2", "제8조의2"]  # not 제1조/제2조


def test_normalize_diff_changes_null_when_no_header_or_real_no():
    payload = {
        "구조문목록": {"조문": [{"no": "1", "content": "머리말 없는 조각"}]},
        "신조문목록": {"조문": [{"no": "1", "content": "머리말 없는 조각"}]},
    }
    changes = normalize_diff_changes(payload)
    assert changes[0].article is None  # never the sequential index 제1조


# --------------------------------------------------------------------------- #
# G3 — trace-law-history nested serialization + OC masking
# --------------------------------------------------------------------------- #

def test_mask_oc_param():
    assert mask_oc_param("/DRF/x?OC=test&target=eflaw&JO=1") == "/DRF/x?OC=***&target=eflaw&JO=1"
    assert mask_oc_param(None) is None


def test_normalize_history_events_flattens_nested_article_payload():
    payload = {"조문변경이력": [
        {
            "조문정보": {"조문번호": "000700", "조문링크": "/DRF/x?OC=test&JO=000700", "변경사유": "제정", "조문변경일": "19810305"},
            "법령정보": {"제개정구분명": "제정", "시행일자": "19810305", "공포번호": "03379"},
        }
    ]}
    events = normalize_history_events(payload, _law(law_id="001248", name="주택임대차보호법"))
    ev = events[0]
    assert ev.article == "제7조"  # not a dict-repr string
    assert ev.revision_type == "제정"
    assert ev.effective_date == "19810305"
    assert ev.reason == "제정"
    assert "OC=test" not in (ev.article_link or "")
    assert "OC=***" in (ev.article_link or "")


# --------------------------------------------------------------------------- #
# T2-E — interpretation source usage errors + ministry next steer
# --------------------------------------------------------------------------- #

def test_search_interpretations_ministry_without_ministry_is_usage_error():
    with pytest.raises(UnsupportedFormatError):
        MolegApi(source=object()).search_interpretations("x", source="ministry")


class _InterpretationHitStub:
    def __init__(self, **kw):
        self.identity = argparse.Namespace(title=None, name=None, **kw)


def test_id_next_ministry_hit_carries_source_and_ministry():
    interp = _InterpretationHitStub(interpretation_id="415980", source_type="ministry", ministry="식품의약품안전처")
    out = _id_next([interp], "get-interpretation")
    assert out[0]["cmd"] == "moleg get-interpretation --id 415980 --source ministry --ministry 식품의약품안전처"


# --------------------------------------------------------------------------- #
# T2-F — annex search default scope + --annex-id alias
# --------------------------------------------------------------------------- #

def test_search_annex_forms_default_scope_is_title():
    ns = build_parser().parse_args(["search-annex-forms", "과태료의 부과기준"])
    assert ns.search_scope == "title"


def test_get_annex_form_body_accepts_annex_id_alias():
    a = build_parser().parse_args(["get-annex-form-body", "--annex-id", "18177371"])
    b = build_parser().parse_args(["get-annex-form-body", "--id", "18177371"])
    assert a.identifier == b.identifier == "18177371"


def test_zero_hit_annex_steers_to_other_scope():
    sig = signals_for("search-annex-forms", [], _ns(query="과태료", search_scope="title"))
    assert any("--search-scope source" in n["cmd"] for n in sig["next"])


# --------------------------------------------------------------------------- #
# T2-G — delegated multi-target (parallel-array) transpose
# --------------------------------------------------------------------------- #

def test_normalize_delegated_rules_transposes_parallel_arrays():
    payload = {"위임조문정보": [{
        "조정보": {"조문번호": "3"},
        "위임정보": {
            "위임구분": ["인용법령", "인용법령"],
            "위임법령제목": ["도로교통법", "자동차관리법"],
            "위임법령일련번호": ["259491", "259585"],
        },
    }]}
    rules = normalize_delegated_rules(payload)
    assert len(rules) == 2
    assert {r.delegated_name for r in rules} == {"도로교통법", "자동차관리법"}
    assert {r.delegated_mst for r in rules} == {"259491", "259585"}
    assert all(not str(r.delegated_type).startswith("[") for r in rules)


# --------------------------------------------------------------------------- #
# T2-I — collapsed box-drawing table is not high confidence
# --------------------------------------------------------------------------- #

def test_structured_table_rejects_box_char_junk():
    rows = [["┃범칙행위", "│금액", "┃"], ["┃", "│13만원", "┃"]]
    data = structured_table_from_rows(rows, AnnexFormIdentity(annex_id="1", title="t", source_type="law", source_target="licbyl"))
    assert data.parsing_confidence == "low"


def test_structured_table_clean_rows_stay_high():
    rows = [["구분", "금액"], ["범칙", "13만원"]]
    data = structured_table_from_rows(rows, AnnexFormIdentity(annex_id="1", title="t", source_type="law", source_target="licbyl"))
    assert data.parsing_confidence == "high"


# --------------------------------------------------------------------------- #
# G7-1 — doctrine 0-count steers to --search-body
# --------------------------------------------------------------------------- #

def test_zero_hit_constitutional_steers_to_search_body():
    sig = signals_for("search-constitutional-decisions", [], _ns(query="과잉금지원칙", search_body=False))
    assert any(n["cmd"].endswith("--search-body") for n in sig["next"])


def test_search_body_flag_has_help_text():
    parser = build_parser()
    for action in parser._subparsers._group_actions[0].choices["search-constitutional-decisions"]._actions:
        if action.dest == "search_body":
            assert action.help
            break
    else:
        raise AssertionError("--search-body not found")


# --------------------------------------------------------------------------- #
# G7-2 — statute-name back-references keep their full name
# --------------------------------------------------------------------------- #

def test_law_name_before_article_keeps_internal_and():
    # ' 및 ' internal to the name must survive; promulgation clause stripped.
    name = law_name_before_article("부정청탁 및 금품등 수수의 금지에 관한 법률(2015. 3. 27. 법률 제13278호로 제정된 것) ")
    assert name == "부정청탁 및 금품등 수수의 금지에 관한 법률"


def test_parse_article_references_splits_and_separator():
    refs = parse_article_references("개인정보 보호법 제8조, 제15조 및 데이터기본법 제5조")
    assert (refs[-1].law_name, refs[-1].article) == ("데이터기본법", "제5조")


# --------------------------------------------------------------------------- #
# G7-3 — disposition parsed from the 주문 only
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("text,expected", [
    ("【주 문】이 사건 심판청구를 각하한다.[이 유] 위반된다 위반된다", "각하"),
    ("【주 문】형법 제241조는 헌법에 위반되지 아니한다.[이 유]", "합헌"),
    ("[주 문] 위 조항은 헌법에 위반된다.[이 유]", "위헌"),
    ("주문 표지 없음 위반된다", None),
])
def test_parse_constitutional_disposition(text, expected):
    assert parse_constitutional_disposition(text) == expected


# --------------------------------------------------------------------------- #
# G8 — promulgated search includes future-effective rows (nw=1)
# --------------------------------------------------------------------------- #

class _ParamCapture:
    def __init__(self):
        self.params = None

    def search(self, target, params):
        self.params = params
        return {"LawSearch": {"law": []}}

    def service(self, *a, **k):  # pragma: no cover
        raise AssertionError

    def search_html(self, *a, **k):  # pragma: no cover
        raise AssertionError

    def post_text(self, *a, **k):  # pragma: no cover
        raise AssertionError


def test_promulgated_search_sends_nw_but_effective_does_not():
    src = _ParamCapture()
    MolegApi(src).search_laws("도로교통법", basis="promulgated")
    assert src.params.get("nw") == 1
    src2 = _ParamCapture()
    MolegApi(src2).search_laws("도로교통법", basis="effective")
    assert "nw" not in src2.params
