import pytest

from moleg_api import LawGoKrClient, MolegApi, MolegApiError, NoResultError
from moleg_api.source import local_env_value


pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(not local_env_value("MOLEG_OC"), reason="MOLEG_OC is required"),
]


ARTICLE_SCENARIOS = [
    ("자동차 방치", "자동차관리법", "제1조"),
    ("자동차 운행정지", "자동차관리법", "제26조"),
    ("개인정보 수집 동의", "개인정보 보호법", "제15조"),
    ("근로시간 상한", "근로기준법", "제50조"),
    ("작업중지와 산업안전", "산업안전보건법", "제38조"),
    ("중대재해 사업주 의무", "중대재해 처벌 등에 관한 법률", "제4조"),
    ("건축 인허가", "건축법", "제11조"),
    ("감염병 방역조치", "감염병의 예방 및 관리에 관한 법률", "제49조"),
    ("아동학대 금지행위", "아동복지법", "제17조"),
    ("학교폭력 정의", "학교폭력예방 및 대책에 관한 법률", "제2조"),
    ("탄소중립 기본계획", "기후위기 대응을 위한 탄소중립ㆍ녹색성장 기본법", "제10조"),
    ("장애인 차별 금지", "장애인차별금지 및 권리구제 등에 관한 법률", "제4조"),
    ("불법정보 유통", "정보통신망 이용촉진 및 정보보호 등에 관한 법률", "제44조의7"),
]

DELEGATION_SCENARIOS = [
    ("자동차 하위규정", "자동차관리법"),
    ("식품위생 하위규정", "식품위생법"),
    ("의료법 하위규정", "의료법"),
]

LAW_HISTORY_SCENARIO = ("건축법 법령연혁", "건축법")

ADMINISTRATIVE_RULE_SCENARIOS = [
    ("자동차 행정규칙", "자동차"),
    ("감염병 행정규칙", "감염병"),
    ("산업안전 행정규칙", "산업안전"),
]

LAW_ANNEX_SCENARIOS = [
    ("자동차 별표/서식", "자동차", None),
    ("식품위생 별표", "식품위생법", "annex"),
]

LAW_ANNEX_BODY_SCENARIO = ("식품위생법 시행령 과태료 별표 본문", "식품위생법", "과태료의 부과기준")

INTERPRETATION_SCENARIOS = [
    ("자동차 법령해석", "자동차"),
    ("건축 법령해석", "건축"),
]

MINISTRY_INTERPRETATION_SCENARIO = (
    "방위사업청 법령해석",
    "방위사업청",
    "기술",
    "409840",
)

CASE_SCENARIOS = [
    ("손해배상 판례", "손해배상", False),
    ("근로기준법 판례", "근로기준법", True),
    ("개인정보 판례", "개인정보", True),
]

QUERY_EXPANSION_SCENARIOS = [
    "자동차 방치",
    "개인정보 가명처리",
    "탄소중립 기본계획",
    "전세사기 피해자 지원",
    "중대재해 사업주 의무",
]

COMPARABLE_MECHANISM_SCENARIOS = [
    "과징금",
]

BUNDLE_QUESTION_SCENARIOS = [
    "자동차 방치",
    "탄소중립 기본계획",
    "개인정보 가명처리",
    "전세사기 피해자 지원",
]

BUNDLE_STATUTE_SCENARIOS = [
    ("자동차관리법 제26조 검토", "자동차관리법", "제26조"),
    ("개인정보 보호법 제15조 검토", "개인정보 보호법", "제15조"),
]

INSTITUTIONAL_SYSTEM_SCENARIOS = [
    ("자동차관리 제도", ["자동차관리법", "자동차관리법 시행령"]),
]

CONSTITUTIONAL_DETAIL_SCENARIO = (
    "참전유공자예우에관한법률 제6조 제1항 위헌확인",
    "58400",
)


@pytest.fixture(scope="module")
def api() -> MolegApi:
    return MolegApi(LawGoKrClient())


def test_live_e2e_matrix_covers_dozens_of_legislative_scenarios():
    scenario_count = (
        len(ARTICLE_SCENARIOS)
        + len(DELEGATION_SCENARIOS)
        + 1  # Full law-level history through lsHistory HTML.
        + len(ADMINISTRATIVE_RULE_SCENARIOS)
        + len(LAW_ANNEX_SCENARIOS)
        + 1  # Law annex/form body text export.
        + len(INTERPRETATION_SCENARIOS)
        + 1  # Ministry first-instance interpretation search/detail/source labels.
        + len(CASE_SCENARIOS)
        + len(QUERY_EXPANSION_SCENARIOS)
        + len(COMPARABLE_MECHANISM_SCENARIOS)
        + len(BUNDLE_QUESTION_SCENARIOS)
        + len(BUNDLE_STATUTE_SCENARIOS)
        + len(INSTITUTIONAL_SYSTEM_SCENARIOS)
        + 1  # Constitutional detail source label.
        + 1  # congress-db bridge, credential-dependent.
    )

    assert scenario_count >= 30


@pytest.mark.parametrize("description, law_name, article", ARTICLE_SCENARIOS)
def test_live_e2e_loads_current_statute_articles(api: MolegApi, description: str, law_name: str, article: str):
    identity = exact_law_identity(api, law_name)
    text = api.get_article(identity, article)

    assert identity.basis == "effective"
    assert identity.law_id or identity.mst
    assert text.identity.name == law_name or text.identity.law_id == identity.law_id
    assert text.article.startswith(base_article_label(article))
    assert text.text.strip(), description


@pytest.mark.parametrize("description, law_name", DELEGATION_SCENARIOS)
def test_live_e2e_loads_delegated_rule_context(api: MolegApi, description: str, law_name: str):
    identity = exact_law_identity(api, law_name)
    graph = api.find_delegated_rules(identity)

    assert graph.identity.name or identity.name
    assert graph.rules, description
    assert any(rule.delegated_name or rule.delegated_type or rule.text for rule in graph.rules)


def test_live_e2e_loads_full_law_history_context(api: MolegApi):
    description, law_name = LAW_HISTORY_SCENARIO
    identity = exact_law_identity(api, law_name)
    history = api.trace_law_history(identity)

    assert history.events, description
    assert any(event.identity.name == law_name for event in history.events)
    assert any(event.revision_type for event in history.events)
    assert any(event.promulgation_date for event in history.events)
    assert any(event.effective_date for event in history.events)
    assert history.raw["source_target"] == "lsHistory"


@pytest.mark.parametrize("description, query", ADMINISTRATIVE_RULE_SCENARIOS)
def test_live_e2e_loads_administrative_rule_context(api: MolegApi, description: str, query: str):
    hits = api.search_administrative_rules(query, display=5)
    hit, text = first_detail_or_skip(
        hits,
        lambda candidate: api.get_administrative_rule(candidate.identity),
        description,
    )

    assert hit.identity.name
    assert hit.identity.serial_id or hit.identity.rule_id
    assert text.identity.name
    assert text.text.strip()


@pytest.mark.parametrize("description, query, annex_type", LAW_ANNEX_SCENARIOS)
def test_live_e2e_surfaces_law_annex_form_candidates(
    api: MolegApi,
    description: str,
    query: str,
    annex_type: str | None,
):
    kwargs = {"source": "law", "display": 5}
    if annex_type:
        kwargs["annex_type"] = annex_type
    hits = api.search_annex_forms(query, **kwargs)

    hit = first_hit_or_skip(hits, description)
    assert hit.identity.source_type == "law"
    assert hit.identity.source_target == "licbyl"
    assert hit.identity.title
    assert hit.identity.related_name or hit.identity.related_id or hit.identity.file_link or hit.identity.detail_link


def test_live_e2e_loads_law_annex_form_body(api: MolegApi):
    description, query, title_fragment = LAW_ANNEX_BODY_SCENARIO
    hits = api.search_annex_forms(query, source="law", annex_type="annex", display=10)
    matching_hit = next((hit for hit in hits if title_fragment in hit.identity.title), None)
    if matching_hit is None:
        titles = [hit.identity.title for hit in hits[:10]]
        pytest.fail(f"No live {description} candidate returned; titles={titles}")

    body = api.get_annex_form_body(matching_hit.identity)

    assert body.identity.source_type == "law"
    assert body.identity.source_target == "licbyl"
    assert body.identity.annex_id
    assert body.file_type == "text/plain"
    assert body.extraction_method == "lsBylTextDownLoad.do"
    assert body.extraction_confidence == "high"
    assert title_fragment in body.text
    assert "식품위생법 시행령" in body.text
    assert body.text.strip(), description


@pytest.mark.parametrize("description, query", INTERPRETATION_SCENARIOS)
def test_live_e2e_loads_official_interpretation_context(api: MolegApi, description: str, query: str):
    hit, text = first_detail_or_skip(
        api.search_interpretations(query, display=10),
        lambda candidate: api.get_interpretation(candidate.identity),
        description,
    )

    assert hit.identity.source_type == "moleg"
    assert hit.identity.source_target == "expc"
    assert text.identity.source_type == "moleg"
    assert text.text.strip()


def test_live_e2e_loads_ministry_first_instance_interpretation_context(api: MolegApi):
    description, ministry, query, detail_id = MINISTRY_INTERPRETATION_SCENARIO

    hits = api.search_interpretations(query, source="ministry", ministry=ministry, display=3)
    assert hits, description
    assert all(hit.identity.source_type == "ministry" for hit in hits)
    assert all(hit.identity.source_target == "dapaCgmExpc" for hit in hits)
    assert all(hit.identity.ministry == ministry for hit in hits)
    assert any(hit.identity.interpretation_id for hit in hits)

    text = api.get_interpretation(detail_id, source="ministry", ministry=ministry)
    assert text.identity.source_type == "ministry"
    assert text.identity.source_target == "dapaCgmExpc"
    assert text.identity.ministry == ministry
    assert text.identity.interpretation_id == detail_id
    assert text.text.strip()

    all_hits = api.search_interpretations(query, source="all", ministry=ministry, display=2)
    labels = {(hit.identity.source_type, hit.identity.source_target, hit.identity.ministry) for hit in all_hits}
    assert ("moleg", "expc", None) in labels
    assert ("ministry", "dapaCgmExpc", ministry) in labels


@pytest.mark.parametrize("description, query, search_body", CASE_SCENARIOS)
def test_live_e2e_loads_case_context(api: MolegApi, description: str, query: str, search_body: bool):
    hit, text = first_detail_or_skip(
        api.search_cases(query, court="supreme", search_body=search_body, display=10),
        lambda candidate: api.get_case(candidate.identity),
        description,
    )

    assert hit.identity.source_type == "case"
    assert hit.identity.source_target == "prec"
    assert text.identity.source_type == "case"
    assert text.identity.source_target == "prec"
    assert text.text.strip()


def test_live_e2e_loads_constitutional_decision_detail(api: MolegApi):
    title, decision_id = CONSTITUTIONAL_DETAIL_SCENARIO
    text = api.get_constitutional_decision(decision_id)

    assert text.identity.source_type == "constitutional"
    assert text.identity.source_target == "detc"
    assert text.identity.decision_id == decision_id
    assert text.identity.title == title
    assert text.text.strip()


@pytest.mark.parametrize("query", QUERY_EXPANSION_SCENARIOS)
def test_live_e2e_expands_queries_as_planning_context(api: MolegApi, query: str):
    expansion = api.expand_legal_query(query, display=3)

    assert expansion.original_query == query
    assert expansion.follow_up_searches
    assert any(search.interface == "websearch" for search in expansion.follow_up_searches)
    assert any(search.interface != "websearch" for search in expansion.follow_up_searches)


@pytest.mark.parametrize("concept", COMPARABLE_MECHANISM_SCENARIOS)
def test_live_e2e_finds_comparable_mechanism_candidates(api: MolegApi, concept: str):
    identities = api.find_comparable_mechanisms(concept, display=3)

    assert 1 <= len(identities) <= 3
    assert all(identity.basis == "effective" for identity in identities)
    assert all(identity.raw_keys.get("comparative_discovery") is True for identity in identities)
    assert all(identity.raw_keys.get("concept") == concept for identity in identities)
    assert any(identity.raw_keys.get("source_articles") for identity in identities)


@pytest.mark.parametrize("query", BUNDLE_QUESTION_SCENARIOS)
def test_live_e2e_loads_question_context_bundle(api: MolegApi, query: str):
    bundle = api.load_legal_context_bundle(query, mode="question", budget="minimal")

    assert bundle.request.mode == "question"
    assert bundle.request.query == query
    assert bundle.source_notes
    assert any(gap.recommended_interface == "websearch" for gap in bundle.gaps)
    assert bundle.candidates.query_expansion is not None
    assert bundle.candidates.laws or bundle.deferred or bundle.gaps


@pytest.mark.parametrize("description, law_name, article", BUNDLE_STATUTE_SCENARIOS)
def test_live_e2e_loads_statute_review_bundle(api: MolegApi, description: str, law_name: str, article: str):
    identity = exact_law_identity(api, law_name)
    bundle = api.load_legal_context_bundle(
        description,
        law_identifier=identity,
        articles=[article],
        mode="statute_review",
        budget="minimal",
    )

    assert bundle.request.mode == "statute_review"
    assert bundle.loaded.articles
    assert bundle.loaded.articles[0].article.startswith(base_article_label(article))
    assert bundle.loaded.articles[0].text.strip()
    assert any(gap.recommended_interface == "websearch" for gap in bundle.gaps)


@pytest.mark.parametrize("description, law_names", INSTITUTIONAL_SYSTEM_SCENARIOS)
def test_live_e2e_loads_institutional_system_bundle(api: MolegApi, description: str, law_names: list[str]):
    identities = [exact_loadable_law_identity(api, law_name) for law_name in law_names]
    bundle = api.load_institutional_system(identities, budget="minimal")

    assert bundle.request.mode == "institutional_system"
    assert bundle.request.statute_ids == law_names
    assert len(bundle.loaded.laws) == len(law_names)
    assert bundle.loaded.law_structures
    assert len(bundle.loaded.delegations) == len(law_names)
    assert bundle.candidates.administrative_rules or bundle.candidates.annex_forms or bundle.deferred
    assert any(gap.recommended_interface == "websearch" for gap in bundle.gaps)


def test_live_e2e_resolves_real_congress_db_promulgation_bridges(api: MolegApi):
    dsn = local_env_value("CONGRESS_DB_READONLY_URL")
    if not dsn:
        pytest.skip("CONGRESS_DB_READONLY_URL is required")

    psycopg = pytest.importorskip("psycopg")
    rows = congress_bridge_rows(psycopg, dsn)
    resolved = []
    no_results = []
    for row in rows:
        try:
            identity = api.resolve_promulgated_law(
                prom_law_nm=row["prom_law_nm"],
                prom_no=row["prom_no"],
                promulgation_dt=row["promulgation_dt"],
            )
        except NoResultError:
            no_results.append(row)
            continue
        resolved.append((row, identity))
        if len(resolved) >= 3:
            break

    assert len(resolved) >= 3, f"Only resolved {len(resolved)} congress bridge rows; no-results={len(no_results)}"
    for row, identity in resolved:
        assert identity.name == row["prom_law_nm"]
        assert identity.promulgation_number == row["prom_no"]
        assert identity.promulgation_date == row["promulgation_dt"].replace("-", "")


def exact_law_identity(api: MolegApi, law_name: str):
    hits = api.search_laws(law_name, display=20)
    for hit in hits:
        if hit.identity.name == law_name:
            return hit.identity
    names = [hit.identity.name for hit in hits[:5]]
    pytest.fail(f"No exact live law identity for {law_name}; candidates={names}")


def exact_loadable_law_identity(api: MolegApi, law_name: str):
    hits = api.search_laws(law_name, display=20)
    no_result_reasons = []
    for hit in hits:
        if hit.identity.name != law_name:
            continue
        try:
            api.get_law(hit.identity)
            return hit.identity
        except NoResultError as exc:
            no_result_reasons.append(str(exc))
    names = [hit.identity.name for hit in hits[:5]]
    pytest.fail(
        f"No exact loadable live law identity for {law_name}; "
        f"candidates={names}; no_results={no_result_reasons[:3]}"
    )


def first_hit_or_skip(hits, label: str):
    if not hits:
        pytest.skip(f"No live {label} sample returned")
    return hits[0]


def first_detail_or_skip(hits, load_detail, label: str):
    no_result_reasons = []
    source_errors = []
    for hit in hits:
        try:
            return hit, load_detail(hit)
        except NoResultError as exc:
            no_result_reasons.append(str(exc))
        except MolegApiError as exc:
            source_errors.append(f"{type(exc).__name__}: {exc}")
    if no_result_reasons or source_errors:
        pytest.skip(
            f"No loadable live {label} detail sample returned: "
            + " / ".join([*no_result_reasons[:3], *source_errors[:3]])
        )
    pytest.skip(f"No live {label} sample returned")


def base_article_label(article: str) -> str:
    return article.split("의", 1)[0]


def congress_bridge_rows(psycopg, dsn: str) -> list[dict[str, str]]:
    query = """
        SELECT
          bfo.prom_law_nm,
          bfo.prom_no,
          bfo.promulgation_dt::text AS promulgation_dt
        FROM public.bill_final_outcomes bfo
        JOIN public.bills b ON b.bill_no = bfo.bill_no
        WHERE bfo.prom_law_nm IS NOT NULL
          AND bfo.prom_no IS NOT NULL
          AND bfo.promulgation_dt IS NOT NULL
          AND bfo.prom_law_nm IN (
            '자동차관리법',
            '개인정보 보호법',
            '건축법',
            '아동복지법',
            '감염병의 예방 및 관리에 관한 법률',
            '기후위기 대응을 위한 탄소중립ㆍ녹색성장 기본법',
            '학교폭력예방 및 대책에 관한 법률',
            '근로기준법'
          )
        ORDER BY bfo.promulgation_dt DESC
        LIMIT 25
    """
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute("SET default_transaction_read_only = on")
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(query)
            rows = list(cur.fetchall())
    return rows
