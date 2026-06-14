import os

import pytest

from moleg_api import LawGoKrClient, MolegApi, NoResultError


pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(not os.environ.get("MOLEG_OC"), reason="MOLEG_OC is required"),
]


def live_api() -> MolegApi:
    return MolegApi(LawGoKrClient())


def first_hit_or_skip(hits, label: str):
    if not hits:
        pytest.skip(f"No live {label} sample returned")
    return hits[0]


def test_live_search_law_detail_and_article_smoke():
    api = live_api()

    hits = api.search_laws("자동차관리법", display=3)
    hit = first_hit_or_skip(hits, "law")
    law = api.get_law(hit.identity)
    article = api.get_article(law.identity, "제1조")

    assert law.identity.law_id
    assert law.identity.name
    assert law.articles
    assert article.article == "제1조"
    assert article.text


def test_live_delegation_and_context_bundle_smoke():
    api = live_api()

    hit = first_hit_or_skip(api.search_laws("자동차관리법", display=3), "law")
    graph = api.find_delegated_rules(hit.identity)
    bundle = api.load_legal_context_bundle("자동차 방치", budget="minimal")

    assert graph.identity.name
    assert graph.rules
    assert bundle.request.mode == "question"
    assert bundle.candidates.query_expansion is not None
    assert any(gap.recommended_interface == "websearch" for gap in bundle.gaps)


def test_live_administrative_rule_search_and_detail_smoke():
    api = live_api()

    hit = first_hit_or_skip(api.search_administrative_rules("자동차", display=3), "administrative-rule")
    text = api.get_administrative_rule(hit.identity)

    assert hit.identity.name
    assert text.identity.name
    assert text.text


def test_live_annex_form_search_smoke():
    api = live_api()

    hit = first_hit_or_skip(
        api.search_annex_forms("자동차", source="law", display=3),
        "law annex/form",
    )
    admin_hits = api.search_annex_forms("자동차", source="administrative_rule", display=3)

    assert hit.identity.title
    assert hit.identity.source_target == "licbyl"
    assert hit.identity.related_name or hit.identity.related_id
    if admin_hits:
        assert admin_hits[0].identity.source_target == "admbyl"
        assert admin_hits[0].identity.title


def test_live_interpretation_search_and_detail_smoke():
    api = live_api()

    hit = first_hit_or_skip(api.search_interpretations("자동차", display=3), "interpretation")
    text = api.get_interpretation(hit.identity)

    assert hit.identity.title
    assert text.identity.title
    assert text.text


def test_live_case_search_and_detail_smoke():
    api = live_api()

    hit = first_hit_or_skip(api.search_cases("자동차", display=3), "case")
    text = api.get_case(hit.identity)

    assert hit.identity.title
    assert text.identity.title
    assert text.text


def test_live_constitutional_decision_search_and_detail_smoke():
    api = live_api()

    hit = first_hit_or_skip(
        api.search_constitutional_decisions("자동차", display=3),
        "constitutional decision",
    )
    text = api.get_constitutional_decision(hit.identity)

    assert hit.identity.title
    assert text.identity.title
    assert text.text


def test_live_history_or_comparison_smoke():
    api = live_api()

    hit = first_hit_or_skip(api.search_laws("건축법", display=3), "law")
    outcomes = []
    no_result_reasons = []

    try:
        history = api.trace_law_history(hit.identity, article=5)
        outcomes.append(history.events)
    except NoResultError as exc:
        no_result_reasons.append(str(exc))

    try:
        diff = api.compare_law_versions(hit.identity)
        outcomes.append(diff.changes)
    except NoResultError as exc:
        no_result_reasons.append(str(exc))

    if not outcomes:
        pytest.skip("No live history/comparison sample returned: " + " / ".join(no_result_reasons))

    assert any(outcome for outcome in outcomes)


def test_live_expand_legal_query_smoke():
    api = live_api()

    expansion = api.expand_legal_query("자동차 방치", display=2)

    assert expansion.original_query == "자동차 방치"
    assert expansion.follow_up_searches
