import pytest

from moleg_api import AmbiguousLawError, MolegApi, NoResultError
from moleg_api.errors import UnsupportedFormatError
from moleg_api.models import LawIdentity
from moleg_api.normalization import format_article_jo


class FakeSource:
    def __init__(self, *, search_payloads=None, service_payloads=None):
        self.search_payloads = list(search_payloads or [])
        self.service_payloads = list(service_payloads or [])
        self.calls = []

    def search(self, target, params):
        self.calls.append(("search", target, params))
        return self.search_payloads.pop(0)

    def service(self, target, params):
        self.calls.append(("service", target, params))
        return self.service_payloads.pop(0)


def test_search_laws_defaults_to_effective_basis_and_normalizes_hits():
    source = FakeSource(
        search_payloads=[
            {
                "LawSearch": {
                    "law": [
                        {
                            "법령ID": "014152",
                            "법령명한글": "기후위기 대응을 위한 탄소중립ㆍ녹색성장 기본법",
                            "법령일련번호": "261457",
                            "공포번호": "21527",
                            "공포일자": "20260407",
                            "시행일자": "20260407",
                            "법령구분명": "법률",
                            "소관부처명": "기후에너지환경부",
                        }
                    ]
                }
            }
        ]
    )

    hits = MolegApi(source).search_laws("기후위기")

    assert len(hits) == 1
    identity = hits[0].identity
    assert identity.law_id == "014152"
    assert identity.mst == "261457"
    assert identity.basis == "effective"
    assert identity.promulgation_number == "21527"
    assert identity.effective_date == "20260407"
    assert identity.ministry == "기후에너지환경부"
    assert source.calls[0][1] == "eflaw"


def test_resolve_promulgated_law_uses_congress_bridge_fields():
    source = FakeSource(
        search_payloads=[
            {
                "LawSearch": {
                    "law": [
                        {
                            "법령ID": "111111",
                            "법령명한글": "데이터기본법",
                            "공포번호": "20000",
                            "공포일자": "20250101",
                        },
                        {
                            "법령ID": "222222",
                            "법령명한글": "데이터기본법",
                            "공포번호": "20100",
                            "공포일자": "20250315",
                        },
                    ]
                }
            }
        ]
    )

    identity = MolegApi(source).resolve_promulgated_law(
        prom_law_nm="데이터기본법",
        prom_no="20100",
        promulgation_dt="2025-03-15",
    )

    assert identity.law_id == "222222"
    assert identity.basis == "promulgated"
    assert source.calls[0][1] == "law"


def test_resolve_promulgated_law_raises_on_ambiguous_bridge():
    source = FakeSource(
        search_payloads=[
            {
                "LawSearch": {
                    "law": [
                        {"법령ID": "1", "법령명한글": "데이터기본법", "공포번호": "1"},
                        {"법령ID": "2", "법령명한글": "데이터기본법", "공포번호": "1"},
                    ]
                }
            }
        ]
    )

    with pytest.raises(AmbiguousLawError):
        MolegApi(source).resolve_promulgated_law(
            prom_law_nm="데이터기본법",
            prom_no="1",
        )


def test_resolve_promulgated_law_raises_on_no_result():
    source = FakeSource(search_payloads=[{"LawSearch": {"law": []}}])

    with pytest.raises(NoResultError):
        MolegApi(source).resolve_promulgated_law(prom_law_nm="없는법")


def test_get_law_returns_identity_and_articles_from_effective_text():
    source = FakeSource(
        service_payloads=[
            {
                "eflaw": {
                    "기본정보": {
                        "법령ID": "014152",
                        "법령명_한글": "기후위기 대응을 위한 탄소중립ㆍ녹색성장 기본법",
                        "공포번호": "21527",
                        "공포일자": "20260407",
                        "시행일자": "20260407",
                    },
                    "조문": {
                        "조문단위": [
                            {
                                "조문번호": "1",
                                "조문제목": "목적",
                                "조문내용": "이 법은 기후위기의 심각한 영향을 예방하기 위하여...",
                                "조문시행일자": "20260407",
                            }
                        ]
                    },
                }
            }
        ]
    )

    result = MolegApi(source).get_law("014152")

    assert result.identity.name == "기후위기 대응을 위한 탄소중립ㆍ녹색성장 기본법"
    assert result.identity.basis == "effective"
    assert result.articles[0].article == "제1조"
    assert result.articles[0].title == "목적"
    assert "기후위기" in result.articles[0].text
    assert source.calls[0] == ("service", "eflaw", {"ID": "014152"})


def test_get_article_formats_human_article_notation_and_returns_text():
    identity = LawIdentity(
        law_id="014152",
        mst="261457",
        name="기후위기 대응을 위한 탄소중립ㆍ녹색성장 기본법",
        basis="effective",
    )
    source = FakeSource(
        service_payloads=[
            {
                "eflawjosub": {
                    "조문": {
                        "조문번호": "10",
                        "조문제목": "국가 탄소중립 녹색성장 기본계획의 수립ㆍ시행",
                        "조문내용": "정부는 국가비전 및 중장기감축목표등의 달성을 위하여...",
                    }
                }
            }
        ]
    )

    article = MolegApi(source).get_article(identity, "제10조의2")

    assert article.article == "제10조"
    assert article.title == "국가 탄소중립 녹색성장 기본계획의 수립ㆍ시행"
    assert "정부는" in article.text
    assert source.calls[0] == (
        "service",
        "eflawjosub",
        {"ID": "014152", "JO": "001002"},
    )


def test_article_jo_format_hides_source_six_digit_rule():
    assert format_article_jo("제2조") == "000200"
    assert format_article_jo("제10조의2") == "001002"
    assert format_article_jo(7) == "000700"
    assert format_article_jo("000300") == "000300"


def test_trace_law_history_uses_article_change_history_json_surface():
    identity = LawIdentity(
        law_id="001971",
        name="건축법",
        basis="effective",
    )
    source = FakeSource(
        service_payloads=[
            {
                "lsJoHstInf": {
                    "law": [
                        {
                            "법령ID": "001971",
                            "법령명한글": "건축법",
                            "조문번호": "5",
                            "변경사유": "일부개정",
                            "조문변경일": "20250101",
                            "조문시행일": "20250401",
                            "공포번호": "20001",
                        }
                    ]
                }
            }
        ]
    )

    history = MolegApi(source).trace_law_history(identity, article="제5조")

    assert history.events[0].identity.name == "건축법"
    assert history.events[0].article == "제5조"
    assert history.events[0].changed_date == "20250101"
    assert history.events[0].effective_date == "20250401"
    assert history.events[0].reason == "일부개정"
    assert source.calls[0] == (
        "service",
        "lsJoHstInf",
        {"ID": "001971", "JO": "000500"},
    )


def test_trace_law_history_requires_json_reachable_scope():
    with pytest.raises(UnsupportedFormatError):
        MolegApi(FakeSource()).trace_law_history("001971")


def test_compare_law_versions_normalizes_old_and_new_articles():
    identity = LawIdentity(law_id="000182", name="가정폭력방지법", basis="effective")
    source = FakeSource(
        service_payloads=[
            {
                "oldAndNew": {
                    "구조문_기본정보": {
                        "법령ID": "000182",
                        "법령명": "가정폭력방지법",
                        "법령일련번호": "270885",
                        "공포일자": "20240101",
                        "시행일자": "20240101",
                    },
                    "신조문_기본정보": {
                        "법령ID": "000182",
                        "법령명": "가정폭력방지법",
                        "법령일련번호": "276865",
                        "공포일자": "20250101",
                        "시행일자": "20250101",
                    },
                    "구조문목록": {
                        "조문": [{"no": "제1조", "content": "종전 목적"}]
                    },
                    "신조문목록": {
                        "조문": [{"no": "제1조", "content": "개정 목적"}]
                    },
                }
            }
        ]
    )

    diff = MolegApi(source).compare_law_versions(
        identity,
        before="2024-01-01",
        after="2025-01-01",
        article="제1조",
    )

    assert diff.before_identity.mst == "270885"
    assert diff.after_identity.mst == "276865"
    assert diff.changes[0].article == "제1조"
    assert diff.changes[0].before_text == "종전 목적"
    assert diff.changes[0].after_text == "개정 목적"
    assert source.calls[0] == ("service", "oldAndNew", {"ID": "000182"})


def test_find_delegated_rules_normalizes_lower_rule_relationships():
    identity = LawIdentity(law_id="000182", name="가정폭력방지법", basis="effective")
    source = FakeSource(
        service_payloads=[
            {
                "lsDelegated": {
                    "법령": {
                        "법령정보": {
                            "법령ID": "000182",
                            "법령명": "가정폭력방지법",
                            "법령일련번호": "276865",
                        },
                        "위임조문정보": [
                            {
                                "조정보": {
                                    "조문번호": "4",
                                    "조문제목": "국가 등의 책무",
                                },
                                "위임정보": {
                                    "위임구분": "시행령",
                                    "위임법령제목": "가정폭력방지법 시행령",
                                    "위임법령일련번호": "123456",
                                    "위임법령조문번호": "2",
                                    "라인텍스트": "대통령령으로 정하는 바에 따라",
                                },
                            }
                        ],
                    }
                }
            }
        ]
    )

    graph = MolegApi(source).find_delegated_rules(identity, article="제4조")

    assert graph.identity.name == "가정폭력방지법"
    assert graph.rules[0].source_article == "제4조"
    assert graph.rules[0].source_article_title == "국가 등의 책무"
    assert graph.rules[0].delegated_type == "시행령"
    assert graph.rules[0].delegated_name == "가정폭력방지법 시행령"
    assert graph.rules[0].delegated_mst == "123456"
    assert graph.rules[0].delegated_article == "제2조"
    assert "대통령령" in graph.rules[0].text
    assert source.calls[0] == ("service", "lsDelegated", {"ID": "000182"})
