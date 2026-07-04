"""Deterministic tests for the moleg CLI wrapper.

These test the envelope + signal derivation (kind, flags, discipline, next) and
error mapping, keyed on the *result dataclass type* rather than live law.go.kr.
Signal logic is type-driven, so it survives command renames/consolidation.
"""

import argparse
import json

import pytest

from moleg_api.cli import (
    CliError,
    _read_followup,
    build_parser,
    main,
    signals_for,
)
from moleg_api.errors import AmbiguousLawError, NoResultError, RateLimitError
from moleg_api.models import (
    AdministrativeRuleIdentity,
    AdministrativeRuleText,
    AnnexFormText,
    AuthorityContext,
    BundleRequest,
    ContextGap,
    DelegationGraph,
    JudicialDecisionHit,
    JudicialDecisionIdentity,
    LawHit,
    LawIdentity,
    LawStructure,
    LawText,
    LoadedContext,
    StructuredTableData,
)


def ns(**kw):
    kw.setdefault("as_of", None)
    return argparse.Namespace(**kw)


def law_ident(**kw):
    kw.setdefault("law_id", "001248")
    kw.setdefault("name", "주택임대차보호법")
    kw.setdefault("basis", "effective")
    return LawIdentity(**kw)


# --------------------------------------------------------------------------- #
# candidate vs loaded: kind suffix + candidate discipline is structural
# --------------------------------------------------------------------------- #

def test_search_law_list_flags_same_name_different_effective_dates():
    hits = [
        LawHit(identity=law_ident(effective_date="20260102", mst="276291")),
        LawHit(identity=law_ident(effective_date="20240101", mst="200000")),
    ]
    sig = signals_for("search-laws", hits, ns())
    assert sig["kind"] == "law_hit_list"
    assert sig["flags"]["ambiguous_versions"] is True
    assert any("--as-of" in d for d in sig["discipline"])
    # next loads an older version by its effective date via --as-of
    assert any("--as-of 20240101" in n["cmd"] for n in sig["next"])


def test_zero_hit_search_is_scoped_not_absence():
    sig = signals_for("search-cases", [], ns(query="없는질의", court="all", court_name=None))
    assert sig["kind"] == "case_hit_list"
    assert sig["count"] == 0
    assert sig["flags"]["searched"]["query"] == "없는질의"
    assert any("0건" in d for d in sig["discipline"])


def test_constitutional_doctrine_discipline_fires_even_on_zero_hits():
    # zero hits is exactly when "no hits != no constitutional risk" matters most
    sig = signals_for("search-constitutional-decisions", [], ns(query="과잉금지원칙"))
    assert sig["kind"] == "constitutional_hit_list"
    assert any("doctrine" in d for d in sig["discipline"])
    assert any("0건" in d for d in sig["discipline"])


# --------------------------------------------------------------------------- #
# loaded article status guardrails (fire only when live)
# --------------------------------------------------------------------------- #

def test_article_deleted_flag_and_discipline():
    from moleg_api.models import ArticleText

    art = ArticleText(identity=law_ident(), article="제3조", text="제3조 삭제", is_deleted=True)
    sig = signals_for("get-article", art, ns())
    assert sig["kind"] == "article_text"
    assert sig["flags"]["is_deleted"] is True
    assert any("삭제" in d for d in sig["discipline"])


def test_article_moved_adds_destination_next():
    from moleg_api.models import ArticleText

    art = ArticleText(identity=law_ident(mst="276291"), article="제3조", text="", moved_to="제3조의2")
    sig = signals_for("get-article", art, ns())
    assert sig["flags"]["moved_to"] == "제3조의2"
    assert any("load-article-context" in n["cmd"] for n in sig["next"])


def test_clean_article_has_no_deleted_or_moved_flags():
    from moleg_api.models import ArticleText

    art = ArticleText(identity=law_ident(), article="제3조", text="본문")
    sig = signals_for("get-article", art, ns())
    assert "is_deleted" not in sig["flags"]
    assert "moved_to" not in sig["flags"]
    # the nested 항·호·목 note is a standing article discipline
    assert any("항" in d for d in sig["discipline"])


def test_law_text_supplementary_provision_discipline():
    from moleg_api.models import ArticleText, SupplementaryProvision

    law = LawText(
        identity=law_ident(effective_date="20260102"),
        articles=[ArticleText(identity=law_ident(), article="제1조", text="본문")],
        supplementary_provisions=[SupplementaryProvision(source_type="law", text="부칙 시행일...")],
    )
    sig = signals_for("get-law", law, ns())
    assert sig["kind"] == "law_text"
    assert sig["flags"]["has_supplementary"] is True
    assert any("부칙" in d or "supplementary" in d for d in sig["discipline"])


def test_law_text_not_effective_as_of_when_future_effective_date():
    from moleg_api.models import ArticleText

    law = LawText(identity=law_ident(effective_date="20990101"), articles=[])
    # as_of historical path only checks <20240101; effective-in-future needs bundle gap,
    # so here we just confirm effective_date/basis surface as flags.
    sig = signals_for("get-law", law, ns(as_of="20250101"))
    assert sig["flags"]["effective_date"] == "20990101"
    assert sig["flags"]["basis"] == "effective"


def test_as_of_mismatch_flags_unfulfilled_version_request():
    # loader served a version effective AFTER the requested date → not historical text
    from moleg_api.models import ArticleText

    art = ArticleText(identity=law_ident(effective_date="20260102"), article="제3조", text="본문")
    sig = signals_for("get-article", art, ns(as_of="2018-01-01"))
    assert sig["flags"]["version_request_unfulfilled"] is True
    assert any("시행 이력" in d or "찾지 못" in d for d in sig["discipline"])
    # and never a false "historical" claim from the request alone
    assert "as_of_basis" not in sig["flags"]


def test_current_as_of_does_not_flag_unfulfilled():
    from moleg_api.models import ArticleText

    art = ArticleText(identity=law_ident(effective_date="20230418"), article="제3조", text="본문")
    sig = signals_for("get-article", art, ns(as_of="2026-07-03"))
    assert "version_request_unfulfilled" not in sig["flags"]


def test_moved_sentinel_je0jo_is_not_treated_as_move():
    from moleg_api.models import ArticleText

    art = ArticleText(identity=law_ident(), article="제8조의2", text="본문", moved_to="제0조", moved_from="제0조")
    sig = signals_for("get-article", art, ns())
    assert "moved_to" not in sig["flags"]
    assert not any("이동" in d for d in sig["discipline"])
    assert not sig["next"]


# --------------------------------------------------------------------------- #
# administrative rule: source back-ref None != absent authority
# --------------------------------------------------------------------------- #

def test_admin_rule_missing_source_backref_is_not_absence():
    rule = AdministrativeRuleText(
        identity=AdministrativeRuleIdentity(serial_id="123", name="어떤고시", effective_date="20250101"),
        text="본문",
        articles=[],
    )
    sig = signals_for("get-administrative-rule", rule, ns())
    assert sig["kind"] == "admin_rule_text"
    assert sig["flags"]["source_backref_present"] is False
    assert any("근거" in d for d in sig["discipline"])


# --------------------------------------------------------------------------- #
# annex/form low-confidence structured rows
# --------------------------------------------------------------------------- #

def test_annex_low_confidence_rows_fallback_discipline():
    from moleg_api.models import AnnexFormIdentity

    annex = AnnexFormText(
        identity=AnnexFormIdentity(annex_id="9", title="별표2", source_type="law", source_target="licbyl"),
        text="table text",
        file_type="txt",
        extraction_method="text_export",
        extraction_confidence="low",
        structured_data=StructuredTableData(title=None, headers=[], rows=[], parsing_confidence="low"),
    )
    sig = signals_for("get-annex-form-body", annex, ns())
    assert sig["kind"] == "annex_form_text"
    assert any("폴백" in d or "plain text" in d for d in sig["discipline"])


# --------------------------------------------------------------------------- #
# authority context: strong gate (loaded vs current) + gap discipline
# --------------------------------------------------------------------------- #

def test_authority_context_mismatch_gap_gates_citation():
    ac = AuthorityContext(
        request=BundleRequest(query="x", mode="question", budget="standard"),
        loaded=LoadedContext(constitutional_decisions=[]),
        current_authorities=LoadedContext(),
        gaps=[ContextGap(kind="authority_article_mismatch", reason="r")],
    )
    sig = signals_for("load-authority-context", ac, ns())
    assert sig["kind"] == "authority_context"
    assert sig["flags"]["authority_gaps"] == ["authority_article_mismatch"]
    assert "loaded_vs_current" in sig["flags"]
    assert any("current_authorities" in d for d in sig["discipline"])


# --------------------------------------------------------------------------- #
# hierarchy-only + empty delegation
# --------------------------------------------------------------------------- #

def test_law_structure_is_hierarchy_only():
    ls = LawStructure(identity=law_ident(), instruments=[])
    sig = signals_for("get-law-structure", ls, ns())
    assert sig["kind"] == "law_structure_hierarchy_only"
    assert any("계층" in d for d in sig["discipline"])


def test_empty_delegation_is_scoped_not_absence():
    dg = DelegationGraph(identity=law_ident(), rules=[])
    sig = signals_for("find-delegated-rules", dg, ns())
    assert sig["kind"] == "delegation_graph"
    assert any("위임" in d for d in sig["discipline"])


# --------------------------------------------------------------------------- #
# load-followup: kind is derived from the executed result type, not the command
# --------------------------------------------------------------------------- #

def test_load_followup_result_kind_follows_result_type():
    hits = [LawHit(identity=law_ident())]
    sig = signals_for("load-followup", hits, ns())
    assert sig["kind"] == "law_hit_list"  # not a generic hit_list


def test_judicial_hit_list_splits_case_vs_constitutional_by_source_type():
    detc = [JudicialDecisionHit(identity=JudicialDecisionIdentity(decision_id="1", title="t", source_type="detc", source_target="detc"))]
    sig = signals_for("load-followup", detc, ns())
    assert sig["kind"] == "constitutional_hit_list"
    prec = [JudicialDecisionHit(identity=JudicialDecisionIdentity(decision_id="1", title="t", source_type="prec", source_target="prec"))]
    sig = signals_for("load-followup", prec, ns())
    assert sig["kind"] == "case_hit_list"


# --------------------------------------------------------------------------- #
# _read_followup validation
# --------------------------------------------------------------------------- #

def test_read_followup_accepts_known_interface():
    lookup = _read_followup('{"interface":"search_laws","query":"주택임대차보호법","filters":{"basis":"effective"}}')
    assert lookup.interface == "search_laws"
    assert lookup.filters["basis"] == "effective"


def test_read_followup_rejects_unknown_interface():
    with pytest.raises(CliError) as exc:
        _read_followup('{"interface":"rm_rf","query":"x"}')
    assert exc.value.exit_code == 5


def test_read_followup_rejects_list():
    with pytest.raises(CliError):
        _read_followup('[{"interface":"search_laws"}]')


# --------------------------------------------------------------------------- #
# main(): error mapping through a stub api
# --------------------------------------------------------------------------- #

class StubApi:
    def __init__(self, exc=None, result=None):
        self._exc = exc
        self._result = result

    def __getattr__(self, name):
        def method(*args, **kwargs):
            if self._exc is not None:
                raise self._exc
            return self._result
        return method


def _run(argv, api):
    return main(argv, api=api)


def test_main_ambiguous_exits_2(capsys):
    code = _run(["resolve-promulgated-law", "--prom-no", "123"],
                StubApi(exc=AmbiguousLawError("multi", kind="promulgation_bridge", candidates=[law_ident()])))
    out = json.loads(capsys.readouterr().out)
    assert code == 2
    assert out["ok"] is False and out["kind"] == "ambiguous"
    assert out["flags"]["candidates"]


def test_main_rate_limit_exits_3_and_is_not_absence(capsys):
    code = _run(["search-laws", "주택임대차보호법"], StubApi(exc=RateLimitError("429")))
    out = json.loads(capsys.readouterr().out)
    assert code == 3
    assert out["kind"] == "source_access_error"
    assert any("부재" in d for d in out["discipline"])


def test_main_law_name_to_loader_is_needs_search_first(capsys):
    # resolve_law_arg passes a non-digit name through; the SDK's name-guard fires.
    code = _run(["get-article", "--law", "주택임대차보호법", "제3조"],
                StubApi(exc=NoResultError("Identifier 'x' looks like a law name, not a law ID. Call search_laws(...)")))
    out = json.loads(capsys.readouterr().out)
    assert code == 5
    assert out["kind"] == "needs_search_first"
    assert out["next"] and "search-laws" in out["next"][0]["cmd"]


def test_main_no_result_exits_4(capsys):
    code = _run(["get-law", "--law", "999999"], StubApi(exc=NoResultError("No law text found")))
    out = json.loads(capsys.readouterr().out)
    assert code == 4
    assert out["kind"] == "no_result"


def test_search_zero_hit_from_noresult_is_ok_true(capsys):
    # some SDK searches raise NoResultError on empty; a search finding nothing is
    # a scoped ok:true result, never an error (matches the other search commands)
    code = _run(["search-interpretations", "없는질의"], StubApi(exc=NoResultError("no interpretation found")))
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["ok"] is True and out["kind"] == "interpretation_hit_list" and out["count"] == 0


def test_unknown_flag_is_usage_error_not_ambiguous(capsys):
    # argparse would exit 2, which collides with EXIT_AMBIGUOUS; remap to 5
    code = main(["search-laws", "x", "--nope"], api=StubApi())
    out = json.loads(capsys.readouterr().out)
    assert code == 5
    assert out["kind"] == "usage_error"


def test_main_success_envelope_shape(capsys):
    law = LawText(identity=law_ident(effective_date="20260102"), articles=[])
    code = _run(["get-law", "--law", "001248"], StubApi(result=law))
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["ok"] is True and out["command"] == "get-law" and out["kind"] == "law_text"
    assert out["source"].startswith("법제처")
    assert "data" in out


def test_catalog_lists_conventions_and_kinds(capsys):
    code = _run(["catalog"], StubApi())
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["kind"] == "catalog"
    assert "convention" in out["data"] and "kinds" in out["data"]


def test_parser_exposes_all_expected_subcommands():
    parser = build_parser()
    # argparse stores subparsers; pull their names
    sub = [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)][0]
    names = set(sub.choices.keys())
    expected = {
        "search-laws", "resolve-promulgated-law", "search-administrative-rules",
        "search-annex-forms", "search-interpretations", "search-cases",
        "search-constitutional-decisions", "expand-legal-query", "find-comparable-mechanisms",
        "get-law", "get-article", "load-article-context", "get-administrative-rule",
        "load-administrative-rule-context", "get-annex-form-body", "get-interpretation",
        "get-case", "get-constitutional-decision", "trace-law-history", "compare-law-versions",
        "find-delegated-rules", "get-law-structure", "load-authority-context",
        "load-legal-context-bundle", "load-institutional-system", "load-delegated-criteria",
        "load-followup", "catalog",
    }
    assert expected <= names, expected - names
