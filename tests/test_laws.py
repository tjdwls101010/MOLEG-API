import pytest

from moleg_api import AmbiguousLawError, MolegApi, NoResultError
from moleg_api.errors import UnsupportedFormatError
from moleg_api.models import JudicialDecisionIdentity, LawIdentity
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


def test_search_administrative_rules_normalizes_current_rule_hits():
    source = FakeSource(
        search_payloads=[
            {
                "AdmRulSearch": {
                    "admrul": [
                        {
                            "행정규칙 일련번호": "2100000248758",
                            "행정규칙ID": "012345",
                            "행정규칙명": "119항공대 운영 규정",
                            "행정규칙종류": "훈령",
                            "발령일자": "20250501",
                            "발령번호": "제2025-1호",
                            "소관부처명": "소방청",
                            "소관부처코드": "1661000",
                            "현행연혁구분": "현행",
                            "제개정구분명": "일부개정",
                            "시행일자": "20250501",
                        }
                    ]
                }
            }
        ]
    )

    hits = MolegApi(source).search_administrative_rules(
        "119항공대",
        ministry="1661000",
        rule_type="1",
        issued_on="2025-05-01",
        display=10,
    )

    assert len(hits) == 1
    identity = hits[0].identity
    assert identity.serial_id == "2100000248758"
    assert identity.rule_id == "012345"
    assert identity.name == "119항공대 운영 규정"
    assert identity.rule_type == "훈령"
    assert identity.issuing_date == "20250501"
    assert identity.effective_date == "20250501"
    assert identity.ministry == "소방청"
    assert identity.current_status == "현행"
    assert source.calls[0] == (
        "search",
        "admrul",
        {
            "query": "119항공대",
            "display": 10,
            "nw": 1,
            "org": "1661000",
            "knd": "1",
            "date": "20250501",
        },
    )


def test_search_annex_forms_normalizes_law_candidates_without_exposing_targets():
    source = FakeSource(
        search_payloads=[
            {
                "licbyl": [
                    {
                        "licbyl id": "220000001",
                        "별표일련번호": "300001",
                        "관련법령일련번호": "270001",
                        "관련법령ID": "001234",
                        "별표명": "자동차등록번호판의 기준",
                        "관련법령명": "자동차관리법",
                        "별표번호": "별표 1",
                        "별표종류": "별표",
                        "소관부처명": "국토교통부",
                        "공포일자": "20250101",
                        "공포번호": "제2025-1호",
                        "제개정구분명": "일부개정",
                        "법령종류": "법률",
                        "별표서식 파일링크": "https://example.test/annex.hwp",
                        "별표서식 PDF파일링크": "https://example.test/annex.pdf",
                        "별표법령 상세링크": "https://example.test/detail",
                    }
                ]
            }
        ]
    )

    hits = MolegApi(source).search_annex_forms(
        "자동차",
        source="law",
        search_scope="source",
        annex_type="annex",
        display=3,
    )

    assert len(hits) == 1
    identity = hits[0].identity
    assert identity.annex_id == "220000001"
    assert identity.title == "자동차등록번호판의 기준"
    assert identity.source_type == "law"
    assert identity.source_target == "licbyl"
    assert identity.related_name == "자동차관리법"
    assert identity.related_id == "001234"
    assert identity.related_serial_id == "270001"
    assert identity.annex_number == "별표 1"
    assert identity.annex_type == "별표"
    assert identity.ministry == "국토교통부"
    assert identity.promulgation_date == "20250101"
    assert identity.file_link == "https://example.test/annex.hwp"
    assert identity.pdf_link == "https://example.test/annex.pdf"
    assert identity.detail_link == "https://example.test/detail"
    assert source.calls[0] == (
        "search",
        "licbyl",
        {"query": "자동차", "display": 3, "search": 2, "knd": "1"},
    )


def test_search_annex_forms_normalizes_administrative_rule_candidates():
    source = FakeSource(
        search_payloads=[
            {
                "AdmRulBylSearch": {
                    "admbyl": [
                        {
                            "admrulbyl id": "330000001",
                            "별표일련번호": "400001",
                            "관련행정규칙 일련번호": "2100000248758",
                            "관련법령ID": "001234",
                            "별표명": "무단방치 자동차 처리 서식",
                            "관련행정규칙명": "무단방치 자동차 처리 규정",
                            "별표번호": "서식 2",
                            "별표종류": "서식",
                            "소관부처명": "국토교통부",
                            "발령일자": "20250203",
                            "발령번호": "제2025-2호",
                            "행정규칙종류": "고시",
                            "별표서식파일링크": "https://example.test/form.hwp",
                            "별표행정규칙 상세링크": "https://example.test/rule-detail",
                        }
                    ]
                }
            }
        ]
    )

    hits = MolegApi(source).search_annex_forms(
        "자동차",
        source="administrative_rule",
        search_scope="body",
        annex_type="form",
        ministry="국토교통부",
        display=5,
    )

    identity = hits[0].identity
    assert identity.annex_id == "330000001"
    assert identity.title == "무단방치 자동차 처리 서식"
    assert identity.source_type == "administrative_rule"
    assert identity.source_target == "admbyl"
    assert identity.related_name == "무단방치 자동차 처리 규정"
    assert identity.related_id == "001234"
    assert identity.related_serial_id == "2100000248758"
    assert identity.issued_on == "20250203"
    assert identity.issuing_number == "제2025-2호"
    assert identity.rule_type == "고시"
    assert identity.file_link == "https://example.test/form.hwp"
    assert identity.detail_link == "https://example.test/rule-detail"
    assert source.calls[0] == (
        "search",
        "admbyl",
        {
            "query": "자동차",
            "display": 5,
            "search": 3,
            "knd": "2",
            "org": "국토교통부",
        },
    )


def test_search_annex_forms_rejects_unsupported_source():
    source = FakeSource()

    with pytest.raises(UnsupportedFormatError):
        MolegApi(source).search_annex_forms("자동차", source="ordinance")


def test_get_administrative_rule_loads_structured_articles_and_filters():
    source = FakeSource(
        service_payloads=[
            {
                "admrul": {
                    "행정규칙 일련번호": "2100000248758",
                    "행정규칙ID": "012345",
                    "행정규칙명": "119항공대 운영 규정",
                    "행정규칙종류": "훈령",
                    "발령일자": "20250501",
                    "발령번호": "제2025-1호",
                    "소관부처명": "소방청",
                    "시행일자": "20250501",
                    "조문": {
                        "조문단위": [
                            {
                                "조문번호": "1",
                                "조문제목": "목적",
                                "조문내용": "이 훈령은 119항공대 운영에 필요한 사항을 정한다.",
                            },
                            {
                                "조문번호": "2",
                                "조문제목": "정의",
                                "조문내용": "이 훈령에서 사용하는 용어의 뜻은 다음과 같다.",
                            },
                        ]
                    },
                    "부칙": {"부칙내용": "이 훈령은 발령한 날부터 시행한다."},
                }
            }
        ]
    )

    text = MolegApi(source).get_administrative_rule(
        "2100000248758",
        articles=["제2조"],
    )

    assert text.identity.name == "119항공대 운영 규정"
    assert text.identity.serial_id == "2100000248758"
    assert text.articles[0].article == "제2조"
    assert text.articles[0].title == "정의"
    assert "용어의 뜻" in text.articles[0].text
    assert "정의" in text.text
    assert source.calls[0] == ("service", "admrul", {"ID": "2100000248758"})


def test_get_administrative_rule_can_use_exact_name_and_preserves_flat_text():
    source = FakeSource(
        service_payloads=[
            {
                "admrul": {
                    "행정규칙명": "데이터기반행정 활성화 규정",
                    "행정규칙종류": "고시",
                    "발령일자": "20240115",
                    "조문내용": "제1조(목적) 이 고시는 데이터기반행정 활성화에 필요한 사항을 정한다.",
                }
            }
        ]
    )

    text = MolegApi(source).get_administrative_rule("데이터기반행정 활성화 규정")

    assert text.identity.name == "데이터기반행정 활성화 규정"
    assert text.identity.rule_type == "고시"
    assert text.identity.issuing_date == "20240115"
    assert text.articles[0].article is None
    assert "데이터기반행정" in text.articles[0].text
    assert source.calls[0] == (
        "service",
        "admrul",
        {"LM": "데이터기반행정 활성화 규정"},
    )


def test_search_interpretations_defaults_to_official_moleg_source():
    source = FakeSource(
        search_payloads=[
            {
                "ExpcSearch": {
                    "expc": [
                        {
                            "법령해석례일련번호": "330471",
                            "안건명": "자동차관리법 관련 법령해석례",
                            "안건번호": "21-0001",
                            "질의기관명": "국토교통부",
                            "회신기관명": "법제처",
                            "회신일자": "20240115",
                            "법령해석례 상세링크": "/DRF/lawService.do?target=expc&ID=330471",
                        }
                    ]
                }
            }
        ]
    )

    hits = MolegApi(source).search_interpretations("자동차", display=5)

    assert len(hits) == 1
    identity = hits[0].identity
    assert identity.interpretation_id == "330471"
    assert identity.source_type == "moleg"
    assert identity.title == "자동차관리법 관련 법령해석례"
    assert identity.case_number == "21-0001"
    assert identity.reply_agency == "법제처"
    assert identity.interpretation_date == "20240115"
    assert source.calls[0] == (
        "search",
        "expc",
        {"query": "자동차", "display": 5, "search": 1},
    )


def test_search_interpretations_uses_ministry_registry():
    source = FakeSource(
        search_payloads=[
            {
                "CgmExpcSearch": {
                    "moeCgmExpc": [
                        {
                            "법령해석일련번호": "417984",
                            "안건명": "학교안전 관련 법령해석",
                            "안건번호": "교육-1",
                            "질의기관명": "교육청",
                            "해석기관명": "교육부",
                            "해석일자": "20240220",
                        }
                    ]
                }
            }
        ]
    )

    hits = MolegApi(source).search_interpretations(
        "학교안전",
        source="ministry",
        ministry="교육부",
        search_body=True,
    )

    assert hits[0].identity.source_type == "ministry"
    assert hits[0].identity.source_target == "moeCgmExpc"
    assert hits[0].identity.ministry == "교육부"
    assert hits[0].identity.reply_agency == "교육부"
    assert source.calls[0] == (
        "search",
        "moeCgmExpc",
        {"query": "학교안전", "display": 20, "search": 2},
    )


def test_get_interpretation_loads_full_text_by_identity():
    source = FakeSource(
        service_payloads=[
            {
                "expc": {
                    "법령해석례일련번호": "330471",
                    "안건명": "자동차관리법 관련 법령해석례",
                    "안건번호": "21-0001",
                    "해석일자": "20240115",
                    "해석기관명": "법제처",
                    "질의기관명": "국토교통부",
                    "질의요지": "자동차 등록 기준은 어떻게 적용되는가?",
                    "회답": "자동차관리법에 따라 등록 기준을 적용한다.",
                    "이유": "관련 조문과 입법 취지를 종합하면 그렇다.",
                    "관련법령": "자동차관리법 제1조",
                }
            }
        ]
    )

    text = MolegApi(source).get_interpretation("330471")

    assert text.identity.source_type == "moleg"
    assert text.identity.interpretation_id == "330471"
    assert "자동차 등록 기준" in text.question
    assert "등록 기준을 적용" in text.answer
    assert "입법 취지" in text.reason
    assert text.related_laws == "자동차관리법 제1조"
    assert "질의요지" in text.text
    assert source.calls[0] == ("service", "expc", {"ID": "330471"})


def test_get_interpretation_refuses_ministry_without_detail_target():
    with pytest.raises(UnsupportedFormatError):
        MolegApi(FakeSource()).get_interpretation(
            "123",
            source="ministry",
            ministry="국세청",
        )


def test_search_cases_normalizes_case_hits_and_court_filter():
    source = FakeSource(
        search_payloads=[
            {
                "PrecSearch": {
                    "prec": [
                        {
                            "판례일련번호": "228541",
                            "사건명": "손해배상",
                            "사건번호": "2020다12345",
                            "선고일자": "20240115",
                            "법원명": "대법원",
                            "법원종류코드": "400201",
                            "사건종류명": "민사",
                            "판결유형": "판결",
                            "데이터출처명": "대법원",
                        }
                    ]
                }
            }
        ]
    )

    hits = MolegApi(source).search_cases("손해배상", court="supreme", display=5)

    assert hits[0].identity.decision_id == "228541"
    assert hits[0].identity.source_type == "case"
    assert hits[0].identity.source_target == "prec"
    assert hits[0].identity.title == "손해배상"
    assert hits[0].identity.case_number == "2020다12345"
    assert hits[0].identity.decision_date == "20240115"
    assert hits[0].identity.court == "대법원"
    assert source.calls[0] == (
        "search",
        "prec",
        {"query": "손해배상", "display": 5, "search": 1, "org": "400201"},
    )


def test_get_case_loads_case_text_by_source_id():
    source = FakeSource(
        service_payloads=[
            {
                "prec": {
                    "판례정보일련번호": "228541",
                    "사건명": "손해배상",
                    "사건번호": "2020다12345",
                    "선고일자": "20240115",
                    "법원명": "대법원",
                    "판시사항": "불법행위 손해배상책임의 성립 요건",
                    "판결요지": "위법행위와 손해 사이의 인과관계가 인정되어야 한다.",
                    "참조조문": "민법 제750조",
                    "참조판례": "대법원 2019다0000 판결",
                    "판례내용": "주문 및 이유 전문",
                }
            }
        ]
    )

    text = MolegApi(source).get_case("228541")

    assert text.identity.source_type == "case"
    assert text.identity.decision_id == "228541"
    assert "손해배상책임" in text.holdings
    assert "인과관계" in text.summary
    assert text.referenced_statutes == "민법 제750조"
    assert "주문 및 이유" in text.full_text
    assert source.calls[0] == ("service", "prec", {"ID": "228541"})


def test_search_constitutional_decisions_normalizes_hits():
    source = FakeSource(
        search_payloads=[
            {
                "DetcSearch": {
                    "detc": [
                        {
                            "헌재결정례일련번호": "58400",
                            "사건명": "자동차관리법제26조등위헌확인",
                            "사건번호": "2020헌마1",
                            "종국일자": "20240229",
                            "헌재결정례 상세링크": "/DRF/lawService.do?target=detc&ID=58400",
                        }
                    ]
                }
            }
        ]
    )

    hits = MolegApi(source).search_constitutional_decisions(
        "자동차",
        decided_on="2024-02-29",
    )

    assert hits[0].identity.source_type == "constitutional"
    assert hits[0].identity.source_target == "detc"
    assert hits[0].identity.decision_id == "58400"
    assert hits[0].identity.decision_date == "20240229"
    assert source.calls[0] == (
        "search",
        "detc",
        {"query": "자동차", "display": 20, "search": 1, "date": "20240229"},
    )


def test_get_constitutional_decision_loads_decision_text_by_source_id():
    source = FakeSource(
        service_payloads=[
            {
                "detc": {
                    "헌재결정례일련번호": "58400",
                    "사건명": "자동차관리법제26조등위헌확인",
                    "사건번호": "2020헌마1",
                    "종국일자": "20240229",
                    "사건종류명": "헌법소원",
                    "판시사항": "자동차관리법 조항의 위헌 여부",
                    "결정요지": "해당 조항은 과잉금지원칙에 위반되지 않는다.",
                    "심판대상조문": "자동차관리법 제26조",
                    "참조조문": "헌법 제37조 제2항",
                    "참조판례": "헌재 2018헌마000 결정",
                    "전문": "결정 전문",
                }
            }
        ]
    )

    text = MolegApi(source).get_constitutional_decision("58400")

    assert text.identity.source_type == "constitutional"
    assert text.identity.title == "자동차관리법제26조등위헌확인"
    assert "위헌 여부" in text.holdings
    assert "과잉금지원칙" in text.summary
    assert "자동차관리법 제26조" in text.reviewed_statutes
    assert source.calls[0] == ("service", "detc", {"ID": "58400"})


def test_get_case_refuses_constitutional_identity():
    identity = JudicialDecisionIdentity(
        decision_id="58400",
        title="자동차관리법제26조등위헌확인",
        source_type="constitutional",
        source_target="detc",
    )

    with pytest.raises(UnsupportedFormatError):
        MolegApi(FakeSource()).get_case(identity)


def test_expand_legal_query_builds_planning_context_without_exposing_targets():
    source = FakeSource(
        search_payloads=[
            {
                "LawSearch": {
                    "law": [
                        {
                            "법령ID": "001234",
                            "법령명한글": "자동차관리법",
                            "법령일련번호": "270001",
                            "시행일자": "20250101",
                        }
                    ]
                }
            },
            {
                "lstrmAI": [
                    {
                        "법령용어 id": "100",
                        "법령용어명": "자동차",
                        "동음이의어 존재여부": "N",
                        "조문간관계 링크": "/DRF/lawService.do?target=lstrmRltJo&query=자동차",
                    }
                ]
            },
            {
                "dlytrm": [
                    {
                        "일상용어 id": "900",
                        "일상용어명": "차량",
                        "출처": "일상용어사전",
                    }
                ]
            },
            {
                "aiSearch": [
                    {
                        "법령ID": "001234",
                        "법령명": "자동차관리법",
                        "법령일련번호": "270001",
                        "조문번호": "26",
                        "조문제목": "자동차의 강제처리",
                        "조문내용": "자동차 소유자는...",
                    }
                ]
            },
            {
                "aiRltLs": [
                    {
                        "법령ID": "009999",
                        "법령명": "자동차손해배상 보장법",
                        "조문번호": "3",
                        "조문제목": "자동차손해배상책임",
                    }
                ]
            },
        ],
        service_payloads=[
            {
                "lstrmRlt": [
                    {
                        "법령용어명": "자동차",
                        "연계용어 id": "901",
                        "일상용어명": "차량",
                        "용어관계": "동의어",
                    }
                ]
            },
            {
                "dlytrmRlt": [
                    {
                        "일상용어명": "차량",
                        "연계용어 id": "101",
                        "법령용어명": "자동차",
                        "용어관계": "연관어",
                    }
                ]
            },
            {
                "lstrmRltJo": [
                    {
                        "법령용어명": "자동차",
                        "법령명": "자동차관리법",
                        "조번호": "26",
                        "조문내용": "자동차의 강제처리 관련 조문",
                        "용어구분": "정의",
                    }
                ]
            },
        ],
    )

    expansion = MolegApi(source).expand_legal_query("자동차 방치 문제")

    assert expansion.original_query == "자동차 방치 문제"
    assert expansion.law_candidates[0].name == "자동차관리법"
    assert expansion.term_candidates[0].term == "자동차"
    assert expansion.term_candidates[0].source_type == "legal_term"
    assert expansion.term_candidates[1].term == "차량"
    assert expansion.term_candidates[1].source_type == "everyday_term"
    assert expansion.related_terms[0].term == "차량"
    assert expansion.related_terms[0].relation == "동의어"
    assert expansion.related_articles[0].law_name == "자동차관리법"
    assert expansion.related_articles[0].article == "제26조"
    assert expansion.related_laws[0].name == "자동차관리법"
    assert expansion.related_laws[1].name == "자동차손해배상 보장법"
    assert any(search.interface == "websearch" for search in expansion.follow_up_searches)
    assert all("target" not in search.interface for search in expansion.follow_up_searches)
    assert source.calls == [
        ("search", "eflaw", {"query": "자동차 방치 문제", "display": 5}),
        ("search", "lstrmAI", {"query": "자동차 방치 문제", "display": 5}),
        ("search", "dlytrm", {"query": "자동차 방치 문제", "display": 5}),
        ("service", "lstrmRlt", {"query": "자동차 방치 문제"}),
        ("service", "dlytrmRlt", {"query": "자동차 방치 문제"}),
        ("service", "lstrmRltJo", {"query": "자동차 방치 문제"}),
        ("search", "aiSearch", {"query": "자동차 방치 문제", "display": 5, "search": 0}),
        ("search", "aiRltLs", {"query": "자동차 방치 문제", "search": 0}),
    ]


def test_expand_legal_query_records_empty_sources_without_failing():
    source = FakeSource(
        search_payloads=[
            {"LawSearch": {"law": []}},
            {"lstrmAI": []},
            {"dlytrm": []},
            {"aiSearch": []},
            {"aiRltLs": []},
        ],
        service_payloads=[
            {"lstrmRlt": []},
            {"dlytrmRlt": []},
            {"lstrmRltJo": []},
        ],
    )

    expansion = MolegApi(source).expand_legal_query("최신 배달 플랫폼 사고 통계")

    assert expansion.law_candidates == []
    assert "eflaw" in expansion.empty_sources
    assert "lstrmAI" in expansion.empty_sources
    assert "websearch" not in expansion.empty_sources
    assert expansion.follow_up_searches[-1].interface == "websearch"
    assert "최신" in expansion.follow_up_searches[-1].query


def test_load_legal_context_bundle_stages_question_context():
    source = FakeSource(
        search_payloads=[
            {
                "LawSearch": {
                    "law": [
                        {
                            "법령ID": "001234",
                            "법령명한글": "자동차관리법",
                            "법령일련번호": "270001",
                            "시행일자": "20250101",
                        }
                    ]
                }
            },
            {"lstrmAI": [{"법령용어 id": "100", "법령용어명": "자동차"}]},
            {"dlytrm": [{"일상용어 id": "900", "일상용어명": "차량"}]},
            {
                "aiSearch": [
                    {
                        "법령ID": "001234",
                        "법령명": "자동차관리법",
                        "법령일련번호": "270001",
                        "조문번호": "26",
                        "조문제목": "자동차의 강제처리",
                    }
                ]
            },
            {"aiRltLs": []},
            {
                "AdmRulSearch": {
                    "admrul": [
                        {
                            "행정규칙 일련번호": "2100000248758",
                            "행정규칙명": "무단방치 자동차 처리 규정",
                            "행정규칙종류": "고시",
                            "발령일자": "20250101",
                        }
                    ]
                }
            },
            {
                "ExpcSearch": {
                    "expc": [
                        {
                            "법령해석례일련번호": "330471",
                            "안건명": "자동차 방치 관련 법령해석례",
                            "안건번호": "21-0001",
                            "회신기관명": "법제처",
                        }
                    ]
                }
            },
            {
                "PrecSearch": {
                    "prec": [
                        {
                            "판례일련번호": "228541",
                            "사건명": "자동차 인도청구",
                            "사건번호": "2020다12345",
                            "법원명": "대법원",
                        }
                    ]
                }
            },
            {
                "DetcSearch": {
                    "detc": [
                        {
                            "헌재결정례일련번호": "58400",
                            "사건명": "자동차관리법제26조등위헌확인",
                            "사건번호": "2020헌마1",
                        }
                    ]
                }
            },
            {
                "licbyl": [
                    {
                        "licbyl id": "220000001",
                        "별표명": "무단방치 자동차 처리 기준",
                        "관련법령명": "자동차관리법",
                        "관련법령ID": "001234",
                        "별표종류": "별표",
                        "별표법령 상세링크": "https://example.test/annex-detail",
                    }
                ]
            },
            {
                "admbyl": [
                    {
                        "admrulbyl id": "330000001",
                        "별표명": "무단방치 자동차 처리 서식",
                        "관련행정규칙명": "무단방치 자동차 처리 규정",
                        "관련행정규칙 일련번호": "2100000248758",
                        "별표종류": "서식",
                        "별표서식파일링크": "https://example.test/rule-form.hwp",
                    }
                ]
            },
        ],
        service_payloads=[
            {
                "lstrmRlt": [
                    {
                        "법령용어명": "자동차",
                        "일상용어명": "차량",
                        "용어관계": "동의어",
                    }
                ]
            },
            {"dlytrmRlt": []},
            {
                "lstrmRltJo": [
                    {
                        "법령용어명": "자동차",
                        "법령명": "자동차관리법",
                        "조번호": "26",
                    }
                ]
            },
            {
                "eflaw": {
                    "기본정보": {
                        "법령ID": "001234",
                        "법령명_한글": "자동차관리법",
                        "법령일련번호": "270001",
                        "시행일자": "20250101",
                    },
                    "조문": {
                        "조문단위": [
                            {
                                "조문번호": "26",
                                "조문제목": "자동차의 강제처리",
                                "조문내용": "시장ㆍ군수ㆍ구청장은 무단방치 자동차를 처리할 수 있다.",
                            }
                        ]
                    },
                }
            },
            {
                "lsDelegated": {
                    "법령": {
                        "법령정보": {
                            "법령ID": "001234",
                            "법령명": "자동차관리법",
                            "법령일련번호": "270001",
                        },
                        "위임조문정보": [
                            {
                                "조정보": {"조문번호": "26", "조문제목": "자동차의 강제처리"},
                                "위임정보": {
                                    "위임구분": "시행령",
                                    "위임법령제목": "자동차관리법 시행령",
                                    "라인텍스트": "대통령령으로 정하는 바에 따라",
                                },
                            }
                        ],
                    }
                }
            },
        ],
    )

    bundle = MolegApi(source).load_legal_context_bundle("자동차 방치 문제")

    assert bundle.request.mode == "question"
    assert bundle.request.budget == "standard"
    assert bundle.loaded.laws[0].identity.name == "자동차관리법"
    assert bundle.loaded.delegations[0].rules[0].delegated_name == "자동차관리법 시행령"
    assert bundle.candidates.query_expansion.original_query == "자동차 방치 문제"
    assert bundle.candidates.administrative_rules[0].identity.name == "무단방치 자동차 처리 규정"
    assert bundle.candidates.interpretations[0].identity.title == "자동차 방치 관련 법령해석례"
    assert bundle.candidates.cases[0].identity.title == "자동차 인도청구"
    assert bundle.candidates.constitutional_decisions[0].identity.source_target == "detc"
    assert bundle.candidates.annex_forms[0].identity.title == "무단방치 자동차 처리 기준"
    assert bundle.candidates.annex_forms[0].identity.source_target == "licbyl"
    assert bundle.candidates.annex_forms[1].identity.source_target == "admbyl"
    assert any(item.interface == "get_interpretation" for item in bundle.deferred)
    assert any(item.interface == "get_case" for item in bundle.deferred)
    assert bundle.gaps[0].kind == "websearch_required"
    assert bundle.gaps[0].recommended_interface == "websearch"


def test_load_legal_context_bundle_resolves_promulgation_bridge_success_path():
    source = FakeSource(
        search_payloads=[
            {
                "LawSearch": {
                    "law": [
                        {
                            "법령ID": "111111",
                            "법령명한글": "데이터기본법",
                            "법령일련번호": "260001",
                            "공포번호": "20000",
                            "공포일자": "20250101",
                        }
                    ]
                }
            },
            {"AdmRulSearch": {"admrul": []}},
            {"ExpcSearch": {"expc": []}},
            {"PrecSearch": {"prec": []}},
            {"DetcSearch": {"detc": []}},
            {"licbyl": []},
            {"admbyl": []},
        ],
        service_payloads=[
            {
                "eflaw": {
                    "기본정보": {
                        "법령ID": "111111",
                        "법령명_한글": "데이터기본법",
                        "법령일련번호": "270001",
                        "시행일자": "20260101",
                    },
                    "조문": {
                        "조문단위": [
                            {
                                "조문번호": "1",
                                "조문제목": "목적",
                                "조문내용": "이 법은 데이터 경제 활성화에 이바지함을 목적으로 한다.",
                            }
                        ]
                    },
                }
            },
            {
                "lsDelegated": {
                    "법령": {
                        "법령정보": {
                            "법령ID": "111111",
                            "법령명": "데이터기본법",
                            "법령일련번호": "270001",
                        },
                        "위임조문정보": [
                            {
                                "조정보": {"조문번호": "10", "조문제목": "실태조사"},
                                "위임정보": {
                                    "위임구분": "시행령",
                                    "위임법령제목": "데이터기본법 시행령",
                                },
                            }
                        ],
                    }
                }
            },
        ],
    )

    bundle = MolegApi(source).load_legal_context_bundle(
        promulgation_bridge={
            "prom_law_nm": "데이터기본법",
            "prom_no": "20000",
            "promulgation_dt": "20250101",
        },
        mode="promulgated_bill",
    )

    assert bundle.loaded.laws[0].identity.name == "데이터기본법"
    assert bundle.loaded.laws[0].identity.basis == "effective"
    assert bundle.loaded.delegations[0].rules[0].delegated_name == "데이터기본법 시행령"
    assert any(item.interface == "trace_law_history" for item in bundle.deferred)
    assert any(item.interface == "compare_law_versions" for item in bundle.deferred)
    assert bundle.gaps[-1].kind == "websearch_required"
    assert source.calls[0] == ("search", "law", {"query": "데이터기본법", "display": 20})
    assert source.calls[1] == ("service", "eflaw", {"ID": "111111"})


def test_load_legal_context_bundle_statute_review_loads_requested_articles_first():
    identity = LawIdentity(law_id="001234", name="자동차관리법", basis="effective")
    source = FakeSource(
        search_payloads=[
            {"AdmRulSearch": {"admrul": []}},
            {"ExpcSearch": {"expc": []}},
            {"PrecSearch": {"prec": []}},
            {"DetcSearch": {"detc": []}},
            {"licbyl": []},
            {"admbyl": []},
        ],
        service_payloads=[
            {
                "eflawjosub": {
                    "조문": {
                        "조문번호": "26",
                        "조문제목": "자동차의 강제처리",
                        "조문내용": "시장ㆍ군수ㆍ구청장은 무단방치 자동차를 처리할 수 있다.",
                    }
                }
            },
            {
                "lsDelegated": {
                    "법령": {
                        "법령정보": {
                            "법령ID": "001234",
                            "법령명": "자동차관리법",
                        },
                        "위임조문정보": [
                            {
                                "조정보": {"조문번호": "26"},
                                "위임정보": {"위임법령제목": "자동차관리법 시행령"},
                            }
                        ],
                    }
                }
            },
        ],
    )

    bundle = MolegApi(source).load_legal_context_bundle(
        law_identifier=identity,
        articles=["제26조"],
        mode="statute_review",
        budget="minimal",
    )

    assert bundle.loaded.laws == []
    assert bundle.loaded.articles[0].article == "제26조"
    assert bundle.loaded.delegations[0].rules[0].source_article == "제26조"
    assert bundle.request.budget == "minimal"
    assert source.calls[0] == ("service", "eflawjosub", {"ID": "001234", "JO": "002600"})


def test_load_legal_context_bundle_preserves_promulgation_bridge_ambiguity():
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

    bundle = MolegApi(source).load_legal_context_bundle(
        promulgation_bridge={"prom_law_nm": "데이터기본법", "prom_no": "1"},
        mode="promulgated_bill",
    )

    assert bundle.loaded.laws == []
    assert bundle.ambiguities
    assert bundle.ambiguities[0].kind == "promulgation_bridge"
    assert "multiple laws" in bundle.ambiguities[0].message
    assert bundle.gaps[0].kind == "manual_review_required"
