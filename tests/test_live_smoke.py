import os

import pytest

from moleg_api import LawGoKrClient, MolegApi


pytestmark = pytest.mark.live


@pytest.mark.skipif(not os.environ.get("MOLEG_OC"), reason="MOLEG_OC is required")
def test_live_search_and_get_law_smoke():
    api = MolegApi(LawGoKrClient())

    hits = api.search_laws("자동차관리법", display=3)

    assert hits
    law = api.get_law(hits[0].identity)
    assert law.identity.law_id
    assert law.identity.name
    assert law.articles


@pytest.mark.skipif(not os.environ.get("MOLEG_OC"), reason="MOLEG_OC is required")
def test_live_search_administrative_rules_smoke():
    api = MolegApi(LawGoKrClient())

    hits = api.search_administrative_rules("학교", display=3)

    assert hits
    assert hits[0].identity.name


@pytest.mark.skipif(not os.environ.get("MOLEG_OC"), reason="MOLEG_OC is required")
def test_live_search_interpretations_smoke():
    api = MolegApi(LawGoKrClient())

    hits = api.search_interpretations("자동차", display=3)

    assert hits
    assert hits[0].identity.title


@pytest.mark.skipif(not os.environ.get("MOLEG_OC"), reason="MOLEG_OC is required")
def test_live_search_cases_smoke():
    api = MolegApi(LawGoKrClient())

    hits = api.search_cases("자동차", display=3)

    assert hits
    assert hits[0].identity.title


@pytest.mark.skipif(not os.environ.get("MOLEG_OC"), reason="MOLEG_OC is required")
def test_live_search_constitutional_decisions_smoke():
    api = MolegApi(LawGoKrClient())

    hits = api.search_constitutional_decisions("자동차", display=3)

    assert hits
    assert hits[0].identity.title


@pytest.mark.skipif(not os.environ.get("MOLEG_OC"), reason="MOLEG_OC is required")
def test_live_expand_legal_query_smoke():
    api = MolegApi(LawGoKrClient())

    expansion = api.expand_legal_query("자동차 방치", display=2)

    assert expansion.original_query == "자동차 방치"
    assert expansion.follow_up_searches
