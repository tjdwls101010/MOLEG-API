from scripts.fake_skill_tracer_bullet import run_fake_skill_tracer_bullet


def test_fake_skill_tracer_bullet_covers_all_consumer_readiness_archetypes():
    results = run_fake_skill_tracer_bullet()

    assert [result.archetype for result in results] == [
        "sanction_design",
        "delegated_criteria_tracing",
        "statute_evolution",
        "congress_bill_to_current_law",
        "constitutional_risk_scan",
        "multi_law_concept_assembly",
        "comparative_design",
    ]
    assert all(result.public_interfaces for result in results)
    assert all(result.loaded or result.candidates or result.deferred for result in results)


def test_fake_skill_tracer_bullet_preserves_consumer_critical_context():
    by_archetype = {
        result.archetype: result
        for result in run_fake_skill_tracer_bullet()
    }

    sanction = by_archetype["sanction_design"]
    assert sanction.evidence["structured_annex_rows"] == 2
    assert sanction.evidence["referenced_articles"] == ["제75조"]
    assert "websearch" in sanction.gaps

    delegated = by_archetype["delegated_criteria_tracing"]
    assert delegated.evidence["law_structures"] == 1
    assert delegated.evidence["delegated_rules"] == 1
    assert delegated.evidence["admin_rule_candidates"] == 1

    evolution = by_archetype["statute_evolution"]
    assert evolution.evidence["article_text_present"] is True
    assert evolution.evidence["bill_id"] == "BILL-20001"
    assert evolution.evidence["promulgation_number"] == "20001"

    bridge = by_archetype["congress_bill_to_current_law"]
    assert bridge.evidence["resolved_law"] == "데이터기본법"
    assert bridge.evidence["basis"] == "effective"
    assert bridge.evidence["has_history_followup"] is True

    constitutional = by_archetype["constitutional_risk_scan"]
    assert constitutional.evidence["loaded_constitutional_decisions"] == 2
    assert constitutional.evidence["deferred_constitutional_decisions"] == 1
    assert constitutional.evidence["reviewed_articles"] == ["제37조"]

    multi_law = by_archetype["multi_law_concept_assembly"]
    assert multi_law.evidence["loaded_laws"] == 2
    assert multi_law.evidence["law_structures"] == 2
    assert multi_law.evidence["delegation_graphs"] == 2
    assert multi_law.evidence["request_statute_ids"] == [
        "전자금융거래법",
        "전자금융거래법 시행령",
    ]

    comparative = by_archetype["comparative_design"]
    assert comparative.evidence["candidate_count"] == 3
    assert "aiSearch" in comparative.evidence["discovery_endpoints"]
    assert comparative.evidence["loaded_article"] == "제50조"
