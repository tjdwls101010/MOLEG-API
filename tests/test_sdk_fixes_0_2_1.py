"""Regression tests for the 0.2.1 defect fixes.

Each group locks one consumer-facing defect surfaced by the published-package
end-to-end pass:

* #1  load-delegated-criteria reached 별표 in the delegated 시행령·시행규칙
* #2  find-delegated-rules recall, resolved identity name, populated signals
* #3  get-annex-form-body recovers the authoritative label from the body
* #4  헌재 search parses capitalized row keys; detail accepts a 사건번호
* #5  CLI: no dead --before/--after, a top-level --version
"""

import argparse

import pytest

from moleg_api import MolegApi
from moleg_api.cli import build_parser, signals_for
from moleg_api.laws import (
    _CONSTITUTIONAL_CASE_NUMBER_RE,
    delegated_criteria_target_scope,
    delegated_subordinate_rule_names,
    enrich_annex_identity_from_body,
)
from moleg_api.models import (
    AnnexFormIdentity,
    BundleRequest,
    CandidateContext,
    DelegatedRule,
    DelegationGraph,
    LawIdentity,
    LawStructure,
    LawStructureNode,
    LegalContextBundle,
    LoadedContext,
)
from moleg_api.normalization import (
    normalize_delegated_rules,
    unwrap_search_judicial_decisions,
)


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

    def search_html(self, target, params):  # pragma: no cover - unused here
        raise AssertionError("search_html not expected")

    def post_text(self, path, params):  # pragma: no cover - unused here
        raise AssertionError("post_text not expected")


def _args(**kw):
    ns = argparse.Namespace(as_of=None)
    for key, value in kw.items():
        setattr(ns, key, value)
    return ns


# --------------------------------------------------------------------------- #
# #4A — 헌재 search row-key casing (Detc vs prec)
# --------------------------------------------------------------------------- #

def test_unwrap_detc_capitalized_row_key_returns_rows():
    payload = {
        "DetcSearch": {
            "totalCnt": 29,
            "target": "detc",
            "Detc": [
                {"헌재결정례일련번호": "48654", "사건번호": "2015헌마1140"},
                {"헌재결정례일련번호": "50600", "사건번호": "2016헌마492"},
            ],
        }
    }
    rows = unwrap_search_judicial_decisions(payload, "detc")
    assert [row["헌재결정례일련번호"] for row in rows] == ["48654", "50600"]


def test_unwrap_prec_lowercase_row_key_unchanged():
    payload = {"PrecSearch": {"prec": [{"판례일련번호": "1"}]}}
    assert len(unwrap_search_judicial_decisions(payload, "prec")) == 1


def test_unwrap_detc_single_object_is_wrapped():
    payload = {"DetcSearch": {"Detc": {"헌재결정례일련번호": "137475"}}}
    rows = unwrap_search_judicial_decisions(payload, "detc")
    assert len(rows) == 1 and rows[0]["헌재결정례일련번호"] == "137475"


def test_unwrap_detc_scalar_target_echo_not_treated_as_rows():
    payload = {"DetcSearch": {"target": "detc", "Detc": [{"헌재결정례일련번호": "1"}]}}
    rows = unwrap_search_judicial_decisions(payload, "detc")
    assert len(rows) == 1


# --------------------------------------------------------------------------- #
# #4B — get-constitutional-decision accepts a 사건번호
# --------------------------------------------------------------------------- #

def test_constitutional_case_number_regex():
    assert _CONSTITUTIONAL_CASE_NUMBER_RE.match("2005헌마1139")
    assert _CONSTITUTIONAL_CASE_NUMBER_RE.match("2015헌바9")
    assert not _CONSTITUTIONAL_CASE_NUMBER_RE.match("48654")  # a bare serial
    assert not _CONSTITUTIONAL_CASE_NUMBER_RE.match("개인정보")  # free text


def test_get_constitutional_decision_resolves_case_number_via_search():
    source = FakeSource(
        search_payloads=[
            {
                "DetcSearch": {
                    "Detc": [
                        {
                            "헌재결정례일련번호": "137475",
                            "사건명": "공직자병역사항 위헌확인",
                            "사건번호": "2005헌마1139",
                            "종국일자": "20070101",
                        }
                    ]
                }
            }
        ],
        service_payloads=[
            {
                "detc": {
                    "헌재결정례일련번호": "137475",
                    "사건명": "공직자병역사항 위헌확인",
                    "사건번호": "2005헌마1139",
                    "종국일자": "20070101",
                    "전문": "결정 전문",
                }
            }
        ],
    )

    text = MolegApi(source).get_constitutional_decision("2005헌마1139")

    assert text.identity.decision_id == "137475"
    assert source.calls[0][:2] == ("search", "detc")
    assert source.calls[1] == ("service", "detc", {"ID": "137475"})


def test_get_constitutional_decision_numeric_serial_skips_search():
    source = FakeSource(
        service_payloads=[
            {
                "detc": {
                    "헌재결정례일련번호": "58400",
                    "사건명": "X",
                    "사건번호": "2020헌마1",
                    "종국일자": "20240229",
                    "전문": "전문",
                }
            }
        ]
    )

    MolegApi(source).get_constitutional_decision("58400")

    assert source.calls[0] == ("service", "detc", {"ID": "58400"})


# --------------------------------------------------------------------------- #
# #2a — normalize_delegated_rules keeps multi-target (list-valued) delegations
# --------------------------------------------------------------------------- #

def test_normalize_delegated_rules_splits_list_valued_info():
    payload = {
        "위임조문정보": [
            {
                "조정보": {"조문번호": "160", "조문제목": "과태료"},
                "위임정보": [
                    {"위임구분": "위임규칙", "위임행정규칙제목": "도로교통법 시행규칙"},
                    {"위임구분": "위임법령", "위임법령제목": "도로교통법 시행령"},
                ],
            }
        ]
    }
    rules = normalize_delegated_rules(payload)
    assert len(rules) == 2
    assert {rule.delegated_name for rule in rules} == {"도로교통법 시행규칙", "도로교통법 시행령"}
    assert all(rule.source_article == "제160조" for rule in rules)


def test_normalize_delegated_rules_dict_valued_single_target_unchanged():
    payload = {
        "위임조문정보": [
            {"조정보": {"조문번호": "163"}, "위임정보": {"위임법령제목": "도로교통법"}}
        ]
    }
    rules = normalize_delegated_rules(payload)
    assert len(rules) == 1 and rules[0].delegated_name == "도로교통법"


def test_normalize_delegated_rules_flat_row_shape_preserved():
    payload = {"위임법령": [{"위임법령제목": "어떤 시행령", "조문번호": "5"}]}
    rules = normalize_delegated_rules(payload)
    assert len(rules) == 1 and rules[0].delegated_name == "어떤 시행령"


# --------------------------------------------------------------------------- #
# #2b / #5c — resolved statute name replaces a bare law_id
# --------------------------------------------------------------------------- #

class _NamedApi(MolegApi):
    def _law_name_for(self, identity):
        return "주택임대차보호법" if str(identity.name).isdigit() else identity.name


def test_resolve_identity_name_backfills_digit_name():
    api = _NamedApi(source=object())
    out = api._resolve_identity_name(LawIdentity(law_id="001248", name="001248", basis="effective"))
    assert out.name == "주택임대차보호법"


def test_resolve_identity_name_keeps_real_name():
    api = _NamedApi(source=object())
    ident = LawIdentity(law_id="001248", name="주택임대차보호법", basis="effective")
    assert api._resolve_identity_name(ident) is ident


# --------------------------------------------------------------------------- #
# #2c — DelegationGraph signals are populated for a non-empty result
# --------------------------------------------------------------------------- #

def test_delegation_graph_signals_populated_when_rules_present():
    graph = DelegationGraph(
        identity=LawIdentity(law_id="001638", name="도로교통법", basis="effective"),
        rules=[DelegatedRule(source_article="제160조", delegated_name="도로교통법 시행령")],
    )
    sig = signals_for("find-delegated-rules", graph, _args())
    assert sig["flags"]["count"] == 1
    assert any("별표" in line for line in sig["discipline"])
    assert any("search-annex-forms" in cmd["cmd"] for cmd in sig["next"])


def test_delegation_graph_signals_empty_keeps_absence_discipline():
    graph = DelegationGraph(
        identity=LawIdentity(law_id="x", name="x", basis="effective"), rules=[]
    )
    sig = signals_for("find-delegated-rules", graph, _args())
    assert sig["flags"]["count"] == 0
    assert sig["discipline"]


# --------------------------------------------------------------------------- #
# #3 — enrich_annex_identity_from_body recovers the authoritative label
# --------------------------------------------------------------------------- #

def _bare_annex(annex_id="18177371"):
    return AnnexFormIdentity(
        annex_id=annex_id, title=annex_id, source_type="law", source_target="licbyl"
    )


def test_enrich_annex_byeolpyo_recovers_title_and_metadata():
    text = (
        "■ 도로교통법 시행령 [별표 8] <개정 2025. 6. 2.>\n"
        "\n"
        "범칙행위 및 범칙금액(운전자)(제93조제1항 관련)\n"
        "┏━━━┓"
    )
    out = enrich_annex_identity_from_body(_bare_annex(), text)
    assert out.related_name == "도로교통법 시행령"
    assert out.annex_type == "별표"
    assert out.annex_number == "8"
    assert "범칙행위 및 범칙금액(운전자)" in out.title
    assert out.title != out.annex_id


def test_enrich_annex_form_uses_bracket_label():
    text = "■ 도로교통법 시행규칙 [별지 제159호의2서식] <개정 2024. 7. 31.>\n서식 본문"
    out = enrich_annex_identity_from_body(_bare_annex("18148709"), text)
    assert out.related_name == "도로교통법 시행규칙"
    assert out.annex_type == "별지"
    assert out.title == "도로교통법 시행규칙 [별지 제159호의2서식]"


def test_enrich_annex_does_not_clobber_rich_identity():
    ident = AnnexFormIdentity(
        annex_id="1",
        title="진짜 제목",
        source_type="law",
        source_target="licbyl",
        related_name="식품위생법 시행령",
        annex_type="별표",
    )
    out = enrich_annex_identity_from_body(ident, "■ 다른법 시행령 [별표 3]\n다른 이름")
    assert out.title == "진짜 제목"
    assert out.related_name == "식품위생법 시행령"
    assert out.annex_type == "별표"


def test_enrich_annex_without_header_leaves_identity():
    out = enrich_annex_identity_from_body(_bare_annex("9"), "헤더 없는 그냥 본문")
    assert out.title == "9"


def test_enrich_annex_non_legislation_source_not_adopted_as_reference():
    # A header that is not a statute/rule name must not become a citable
    # related_name (it feeds delegated-criteria source verification).
    out = enrich_annex_identity_from_body(
        AnnexFormIdentity(annex_id="44", title="무단방치 기준", source_type="law", source_target="licbyl"),
        "■ 출처 미상 [별표]\n표 내용",
    )
    assert out.related_name is None


# --------------------------------------------------------------------------- #
# #1 — delegated_subordinate_rule_names resolves the 시행령·시행규칙 to search
# --------------------------------------------------------------------------- #

def test_delegated_subordinate_rule_names_scopes_and_includes_structures():
    ident = LawIdentity(law_id="001638", name="도로교통법", basis="effective")
    delegation = DelegationGraph(
        identity=ident,
        rules=[
            DelegatedRule(source_article="제160조", delegated_name="도로교통법 시행규칙"),
            DelegatedRule(source_article="제999조", delegated_name="무관 시행령"),
        ],
    )
    structure = LawStructure(
        identity=ident,
        instruments=[
            LawStructureNode(name="도로교통법 시행령", source_type="law", instrument_type="enforcement_decree"),
            LawStructureNode(name="도로교통법 시행규칙", source_type="law", instrument_type="enforcement_rule"),
            LawStructureNode(name="상위 법률", source_type="law", instrument_type="related_law"),
        ],
    )
    bundle = LegalContextBundle(
        request=BundleRequest(query=None, mode="institutional_system", budget="standard", articles=["제160조"]),
        loaded=LoadedContext(delegations=[delegation], law_structures=[structure]),
        candidates=CandidateContext(),
    )
    names = delegated_subordinate_rule_names(bundle, delegated_criteria_target_scope(bundle))
    assert "도로교통법 시행령" in names
    assert "도로교통법 시행규칙" in names
    assert "무관 시행령" not in names  # source article out of requested scope
    assert "상위 법률" not in names  # related_law instrument excluded


# --------------------------------------------------------------------------- #
# #5a / #5b — CLI: dead flags removed, --version added
# --------------------------------------------------------------------------- #

def test_compare_law_versions_rejects_removed_before_after():
    with pytest.raises(SystemExit):
        build_parser().parse_args(
            ["compare-law-versions", "--law", "001248", "--before", "2020-01-01"]
        )


def test_compare_law_versions_accepts_law_and_article():
    ns = build_parser().parse_args(
        ["compare-law-versions", "--law", "001248", "--article", "제3조"]
    )
    assert ns.law == "001248" and ns.article == "제3조"


def test_top_level_version_flag_prints_and_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--version"])
    assert exc.value.code == 0
    assert "moleg-api" in capsys.readouterr().out
