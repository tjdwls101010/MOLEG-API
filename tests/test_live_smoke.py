import pytest

from moleg_api import LawGoKrClient, MolegApi, NoResultError
from moleg_api.source import local_env_value


pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(not local_env_value("MOLEG_OC"), reason="MOLEG_OC is required"),
]


def live_api() -> MolegApi:
    return MolegApi(LawGoKrClient())


def first_hit_or_skip(hits, label: str):
    if not hits:
        pytest.skip(f"No live {label} sample returned")
    return hits[0]


def exact_law_hit_or_skip(api: MolegApi, query: str, exact_name: str):
    hits = api.search_laws(query, display=20)
    for hit in hits:
        if hit.identity.name == exact_name:
            return hit
    pytest.skip(f"No exact live law sample returned for {exact_name}")


def exact_law_detail_or_skip(api: MolegApi, query: str, exact_name: str):
    no_result_reasons = []
    hits = api.search_laws(query, display=20)
    for hit in hits:
        if hit.identity.name != exact_name:
            continue
        try:
            return hit, api.get_law(hit.identity)
        except NoResultError as exc:
            no_result_reasons.append(str(exc))
    if no_result_reasons:
        pytest.skip(f"No live law detail sample returned for {exact_name}: " + " / ".join(no_result_reasons[:3]))
    pytest.skip(f"No exact live law sample returned for {exact_name}")


def first_detail_or_skip(hits, load_detail, label: str):
    no_result_reasons = []
    for hit in hits:
        try:
            return hit, load_detail(hit)
        except NoResultError as exc:
            no_result_reasons.append(str(exc))
    if no_result_reasons:
        pytest.skip(f"No live {label} detail sample returned: " + " / ".join(no_result_reasons[:3]))
    pytest.skip(f"No live {label} sample returned")


def test_live_search_law_detail_and_article_smoke():
    api = live_api()

    hit, law = exact_law_detail_or_skip(api, "자동차관리법", "자동차관리법")
    article = api.get_article(law.identity, "제1조")

    assert law.identity.law_id
    assert law.identity.name
    assert law.articles
    assert article.article == "제1조"
    assert article.text


def test_live_delegation_and_context_bundle_smoke():
    api = live_api()

    hit = exact_law_hit_or_skip(api, "자동차관리법", "자동차관리법")
    graph = api.find_delegated_rules(hit.identity)
    structure = api.get_law_structure(hit.identity)
    bundle = api.load_legal_context_bundle("자동차 방치", budget="minimal")

    assert graph.identity.name
    assert graph.rules
    assert structure.identity.name == hit.identity.name
    assert structure.instruments
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

    hit, text = first_detail_or_skip(
        api.search_cases("자동차", display=10),
        lambda case_hit: api.get_case(case_hit.identity),
        "case",
    )

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

    hit = exact_law_hit_or_skip(api, "건축법", "건축법")
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


def test_live_constitutional_search_high_frequency_term_smoke():
    # 0.2.1 #4A: capitalized 'Detc' row key was dropping all hits to 0.
    api = live_api()

    hits = api.search_constitutional_decisions("개인정보", display=20)

    assert hits, "high-frequency 헌재 term should return hits after the row-key fix"
    assert hits[0].identity.decision_id


def test_live_constitutional_detail_by_case_number_smoke():
    # 0.2.1 #4B: get_constitutional_decision resolves a 사건번호 to its serial.
    api = live_api()

    hits = api.search_constitutional_decisions("개인정보", display=5)
    hit = first_hit_or_skip(hits, "constitutional decision")
    case_number = hit.identity.case_number
    if not case_number:
        pytest.skip("No 사건번호 on the sampled hit")

    text = api.get_constitutional_decision(case_number)

    assert text.identity.decision_id
    assert text.text


def test_live_find_delegated_rules_name_and_recall_smoke():
    # 0.2.1 #2: resolved statute name + multi-target recall.
    api = live_api()

    graph = api.find_delegated_rules("001638")  # 도로교통법

    assert graph.identity.name and not graph.identity.name.isdigit()
    articles = {rule.source_article for rule in graph.rules}
    assert "제160조" in articles and "제162조" in articles


def test_live_load_delegated_criteria_reaches_subordinate_annex_smoke():
    # 0.2.1 #1: 별표 in the delegated 시행령·시행규칙 are surfaced first-party,
    # not pushed to websearch.
    api = live_api()

    bundle = api.load_delegated_criteria("001638", articles=["제160조", "제162조"])

    annex_titles = [annex.identity.title for annex in bundle.loaded.annex_forms]
    candidate_titles = [c.identity.title for c in bundle.candidates.annex_forms]
    all_titles = " ".join(annex_titles + candidate_titles)
    assert bundle.candidates.annex_forms or bundle.loaded.annex_forms
    assert "과태료" in all_titles or "범칙" in all_titles
    gap_kinds = [gap.kind for gap in bundle.gaps]
    assert gap_kinds != ["websearch_required"]


def test_live_annex_form_body_recovers_label_smoke():
    # 0.2.1 #3: a bare-id annex body load recovers its authoritative label.
    api = live_api()

    hits = api.search_annex_forms("도로교통법 시행령", source="law", annex_type="별표", display=5)
    hit = first_hit_or_skip(hits, "law annex")
    body = api.get_annex_form_body(hit.identity.annex_id)  # bare id, no title

    assert body.identity.title and body.identity.title != body.identity.annex_id
    assert body.identity.related_name
