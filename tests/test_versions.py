"""Regression tests for historical-version loading and law-history parsing.

law.go.kr's ID+efYd detail lookups cannot select a past version — they return
current text (or nothing). The version-specific master sequence (MST) is the
only key that pins a version. These tests lock the resolve-and-reload path and
the lsHistory parser's tolerance of "no results" pages.
"""

import pytest

from moleg_api import MolegApi
from moleg_api.errors import NoResultError, ParseFailureError
from moleg_api.models import LawIdentity
from moleg_api.normalization import parse_law_history_html


def ident(law_id="001248", name="주택임대차보호법"):
    return LawIdentity(law_id=law_id, name=name, basis="effective")


VERSION_ROWS = [
    {"법령ID": "001248", "법령일련번호": "276291", "시행일자": "20260102", "공포번호": "21065", "법령명한글": "주택임대차보호법"},
    {"법령ID": "001248", "법령일련번호": "218963", "시행일자": "20201210", "공포번호": "17363", "법령명한글": "주택임대차보호법"},
    {"법령ID": "001248", "법령일련번호": "220619", "시행일자": "20201101", "공포번호": "17470", "법령명한글": "주택임대차보호법"},
]


class ListSource:
    """Serves the eflaw version list only."""

    def __init__(self, rows=VERSION_ROWS):
        self.rows = rows
        self.calls = []

    def search(self, target, params):
        self.calls.append(("search", target, dict(params)))
        return {"LawSearch": {"law": self.rows}}

    def service(self, target, params):  # pragma: no cover - should not be called
        raise AssertionError(f"unexpected service({target})")

    def search_html(self, target, params):  # pragma: no cover
        raise AssertionError("unexpected search_html")

    def post_text(self, path, params):  # pragma: no cover
        raise AssertionError("unexpected post_text")


# --------------------------------------------------------------------------- #
# version resolution helpers
# --------------------------------------------------------------------------- #

def test_resolve_version_mst_picks_latest_effective_on_or_before_as_of():
    api = MolegApi(ListSource())
    assert api._resolve_version_mst(ident(), "2021-01-01") == "218963"  # 20201210 latest ≤ 2021
    assert api._resolve_version_mst(ident(), "2026-07-03") == "276291"  # current
    assert api._resolve_version_mst(ident(), "2019-01-01") is None      # before earliest version


def test_law_name_for_recovers_real_name_from_bare_law_id():
    api = MolegApi(ListSource())
    assert api._law_name_for(ident(name="001248")) == "주택임대차보호법"


def test_law_version_rows_drops_foreign_law_ids():
    rows = VERSION_ROWS + [{"법령ID": "999999", "법령일련번호": "111", "시행일자": "20200101", "법령명한글": "다른법"}]
    api = MolegApi(ListSource(rows))
    got = api._law_version_rows(ident())
    assert got and all(r["법령ID"] == "001248" for r in got)


# --------------------------------------------------------------------------- #
# get_law / get_article: historical reload by version MST
# --------------------------------------------------------------------------- #

class HistoricalLawSource:
    """ID+efYd detail fails (as law.go.kr does for a past date); the version
    list resolves the MST; the MST-keyed promulgated payload is the history."""

    def __init__(self):
        self.calls = []

    def search(self, target, params):
        self.calls.append(("search", target, dict(params)))
        return {"LawSearch": {"law": VERSION_ROWS}}

    def service(self, target, params):
        self.calls.append(("service", target, dict(params)))
        if target == "eflaw":
            raise NoResultError("ID+efYd returns nothing for a past date")
        if target == "law":
            assert params.get("MST") == "218963"
            return {"law": {
                "기본정보": {"법령ID": "001248", "법령명_한글": "주택임대차보호법",
                             "공포번호": "17363", "공포일자": "20200609", "시행일자": "20201210"},
                "조문": {"조문단위": [{"조문번호": "1", "조문제목": "목적",
                                       "조문내용": "역사 본문", "조문시행일자": "20201210"}]},
            }}
        raise AssertionError(f"unexpected service({target})")

    def search_html(self, *a):  # pragma: no cover
        raise AssertionError

    def post_text(self, *a):  # pragma: no cover
        raise AssertionError


def test_get_law_historical_reloads_the_version_in_force_at_as_of():
    api = MolegApi(HistoricalLawSource())
    law = api.get_law("001248", as_of="2021-01-01")
    assert law.identity.effective_date == "20201210"      # not current 20260102
    assert law.identity.promulgation_number == "17363"    # not current 21065
    # it fell back to a version load by MST after the ID+efYd path failed
    assert ("service", "law", {"MST": "218963"}) in api.source.calls


class HistoricalArticleSource:
    """eflawjosub silently returns the current article; the correction reloads
    the historical article by MST via lawjosub."""

    def __init__(self):
        self.calls = []

    def search(self, target, params):
        self.calls.append(("search", target, dict(params)))
        return {"LawSearch": {"law": VERSION_ROWS}}

    def service(self, target, params):
        self.calls.append(("service", target, dict(params)))
        if target == "eflawjosub":
            return {"eflawjosub": {"조문": {"조문번호": "7", "조문제목": "우선변제",
                                            "조문내용": "현행 본문", "조문시행일자": "20260102"}}}
        if target == "lawjosub":
            assert params.get("MST") == "218963"
            return {"lawjosub": {"조문": {"조문번호": "7", "조문제목": "우선변제",
                                          "조문내용": "역사 본문", "조문시행일자": "20201210"}}}
        raise AssertionError(f"unexpected service({target})")

    def search_html(self, *a):  # pragma: no cover
        raise AssertionError

    def post_text(self, *a):  # pragma: no cover
        raise AssertionError


def test_get_article_historical_corrects_a_silently_current_result():
    api = MolegApi(HistoricalArticleSource())
    art = api.get_article("001248", "제7조", as_of="2021-01-01")
    assert art.effective_date == "20201210"   # corrected away from the silent current 20260102
    assert "역사" in art.text


def test_get_article_current_as_of_does_not_trigger_a_reload():
    api = MolegApi(HistoricalArticleSource())
    art = api.get_article("001248", "제7조", as_of="2026-07-03")
    assert art.effective_date == "20260102"
    # no version list lookup, no MST reload for a current-in-force date
    assert not any(c[1] == "lawjosub" for c in api.source.calls)


# --------------------------------------------------------------------------- #
# trace_law_history: recover the real name; parser tolerates "no results"
# --------------------------------------------------------------------------- #

_HISTORY_HTML = """
<html><div class="num">총<strong>1</strong>건</div>
<table summary="법령 연혁정보 목록"><tbody>
  <tr>
    <td class="ce">1</td>
    <td><a href="/DRF/lawService.do?target=lsHistory&amp;MST=218963&amp;type=HTML&amp;efYd=20201210">주택임대차보호법</a></td>
    <td class="ce">법무부</td>
    <td class="ce">일부개정</td>
    <td class="ce">법률</td>
    <td class="ce">제 17363호</td>
    <td class="ce">2020.6.9</td>
    <td class="ce">2020.12.10</td>
    <td class="ce">연혁</td>
  </tr>
</tbody></table></html>
"""


class TraceSource:
    def __init__(self, html):
        self.html = html
        self.calls = []

    def search(self, target, params):
        self.calls.append(("search", target, dict(params)))
        return {"LawSearch": {"law": VERSION_ROWS}}

    def search_html(self, target, params):
        self.calls.append(("search_html", target, dict(params)))
        return self.html

    def service(self, *a):  # pragma: no cover
        raise AssertionError

    def post_text(self, *a):  # pragma: no cover
        raise AssertionError


def test_trace_law_history_resolves_real_name_from_bare_law_id():
    api = MolegApi(TraceSource(_HISTORY_HTML))
    history = api.trace_law_history("001248")
    assert history.events
    html_calls = [c for c in api.source.calls if c[0] == "search_html"]
    # queried lsHistory by the resolved statute name, not the numeric law_id
    assert html_calls and html_calls[0][2]["query"] == "주택임대차보호법"


def test_history_parser_treats_no_results_message_as_empty():
    html = '<table summary="법령 연혁정보 목록"><tbody><tr><td>검색된 데이터가 없습니다.</td></tr></tbody></table>'
    assert parse_law_history_html(html) == []


def test_history_parser_raises_on_genuinely_malformed_rows():
    html = '<table summary="법령 연혁정보 목록"><tbody><tr><td>1</td><td>a</td><td>b</td></tr></tbody></table>'
    with pytest.raises(ParseFailureError):
        parse_law_history_html(html)
