import json

from scripts.legislative_expert_answer_discipline import run_legislative_expert_answer_discipline


def test_answer_discipline_reports_cover_high_risk_answer_states():
    reports = run_legislative_expert_answer_discipline()

    assert [report.scenario for report in reports] == [
        "proposed_bill_current_law_answer_discipline",
        "enacted_bill_change_trace_answer_discipline",
        "loaded_before_after_amendment_delta_answer_discipline",
        "historical_repealed_law_answer_discipline",
        "nested_article_unit_answer_discipline",
        "deleted_article_answer_discipline",
        "moved_article_answer_discipline",
        "query_expansion_candidate_answer_discipline",
        "law_search_candidate_answer_discipline",
        "empty_law_search_absence_answer_discipline",
        "interpretation_authority_answer_discipline",
        "interpretation_search_candidate_answer_discipline",
        "empty_interpretation_search_absence_answer_discipline",
        "source_access_failure_answer_discipline",
        "case_search_candidate_answer_discipline",
        "empty_case_search_absence_answer_discipline",
        "constitutional_search_candidate_answer_discipline",
        "empty_constitutional_search_absence_answer_discipline",
        "authority_article_reference_mismatch_answer_discipline",
        "context_bundle_authority_article_mismatch_answer_discipline",
        "context_bundle_authority_article_unverified_answer_discipline",
        "context_bundle_authority_article_partial_match_answer_discipline",
        "context_bundle_authority_temporal_mismatch_answer_discipline",
        "law_structure_hierarchy_candidate_answer_discipline",
        "empty_delegation_graph_absence_answer_discipline",
        "administrative_rule_search_candidate_answer_discipline",
        "administrative_rule_issued_on_not_effective_as_of_answer_discipline",
        "administrative_rule_article_status_answer_discipline",
        "administrative_rule_supplementary_transition_answer_discipline",
        "empty_administrative_rule_search_absence_answer_discipline",
        "administrative_rule_missing_source_reference_answer_discipline",
        "comparable_mechanism_candidate_answer_discipline",
        "annex_form_search_candidate_answer_discipline",
        "empty_annex_form_search_absence_answer_discipline",
        "delegated_criteria_answer_discipline",
        "delegated_criteria_after_followups_answer_discipline",
        "low_confidence_annex_body_answer_discipline",
        "future_effective_administrative_rule_answer_discipline",
        "future_effective_promulgated_law_answer_discipline",
        "constitutional_risk_answer_discipline",
        "comparative_design_answer_discipline",
        "context_bundle_authority_answer_discipline",
        "institutional_system_answer_discipline",
        "latest_social_context_answer_discipline",
        "supplementary_transition_answer_discipline",
    ]
    assert all(report.allowed_claims for report in reports)
    assert all(report.forbidden_claims for report in reports)
    assert json.loads(json.dumps([report.to_dict() for report in reports], ensure_ascii=False))


def test_answer_discipline_refuses_proposed_bill_current_law_claim():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["proposed_bill_current_law_answer_discipline"]

    assert report.status == "must_not_answer_as_current_law"
    assert "congress-db.bill_final_outcomes" in report.required_followups
    assert report.evidence["moleg_source_calls"] == []
    assert any("not current law" in disclosure for disclosure in report.required_disclosures)
    assert any("current law" in claim for claim in report.forbidden_claims)


def test_answer_discipline_refuses_amendment_delta_claim_before_history_or_diff():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["enacted_bill_change_trace_answer_discipline"]

    assert report.status == "must_load_more_sources"
    assert {"trace_law_history", "compare_law_versions"}.issubset(report.required_followups)
    assert report.evidence["resolved_law"] == "데이터기본법"
    assert report.evidence["basis"] == "effective"
    assert report.evidence["has_history_followup"] is True
    assert "history_not_loaded_until_article_or_date_known" in report.evidence["risk_flags"]
    assert any("Current text alone" in claim for claim in report.forbidden_claims)
    assert any("bridge resolution" in claim for claim in report.forbidden_claims)
    assert any("amendment-delta" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_allows_loaded_before_after_wording_delta_only():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["loaded_before_after_amendment_delta_answer_discipline"]

    assert report.status == "can_answer_with_loaded_sources"
    assert report.evidence["changes"] == [
        {
            "article": "제1조",
            "before_text": "종전 목적",
            "after_text": "개정 목적",
        }
    ]
    assert report.evidence["before_mst"] == "270885"
    assert report.evidence["after_mst"] == "276865"
    assert "before_after_comparison_supports_wording_delta_only" in report.evidence["risk_flags"]
    assert "trace_law_history" in report.required_followups
    assert {citation.source_type for citation in report.citations} == {"law_diff"}
    assert any("before/after wording" in claim for claim in report.allowed_claims)
    assert any("legislative intent" in claim for claim in report.forbidden_claims)
    assert any("selected article" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_allows_historical_article_only_with_as_of_and_repeal_disclosure():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["historical_repealed_law_answer_discipline"]

    assert report.status == "can_answer_with_loaded_sources"
    assert report.evidence["as_of"] == "20121230"
    assert report.evidence["article_effective_date"] == "20120101"
    assert "폐지" in report.evidence["history_statuses"]
    assert "historical_article_not_current_law" in report.evidence["risk_flags"]
    assert any("historical article text" in claim for claim in report.allowed_claims)
    assert any("currently in force" in claim for claim in report.forbidden_claims)
    assert any("as-of date" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_requires_nested_article_units_for_definition_claims():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["nested_article_unit_answer_discipline"]

    assert report.status == "can_answer_with_loaded_sources"
    assert report.evidence["line_count"] >= 4
    assert report.evidence["contains_terms"] == {
        "자동차": True,
        "승용자동차": True,
        "일반형 승용자동차": True,
        "자동차사용자": True,
    }
    assert "nested_article_units_required_for_complete_article_text" in report.evidence["risk_flags"]
    assert "search_interpretations" in report.required_followups
    assert any("full ArticleText.text" in claim for claim in report.allowed_claims)
    assert any("top-level 조문내용 alone" in claim for claim in report.forbidden_claims)
    assert any("Nested 호 or 목" in claim for claim in report.forbidden_claims)
    assert any("nested 항, 호, or 목 labels" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_refuses_operational_claim_from_deleted_article():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["deleted_article_answer_discipline"]

    assert report.status == "can_answer_with_loaded_sources"
    assert report.evidence["is_deleted"] is True
    assert report.evidence["revision_type"] == "삭제"
    assert report.evidence["effective_date"] == "20250101"
    assert report.evidence["moved_from"] == "제7조"
    assert report.evidence["moved_to"] == "제9조"
    assert "deleted_article_is_not_current_operational_text" in report.evidence["risk_flags"]
    assert "trace_law_history" in report.required_followups
    assert any("marked deleted" in claim for claim in report.allowed_claims)
    assert any("current duty" in claim for claim in report.forbidden_claims)
    assert any("prior wording" in claim for claim in report.forbidden_claims)
    assert any("marked deleted" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_requires_destination_loading_for_moved_article():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["moved_article_answer_discipline"]

    assert report.status == "can_answer_with_loaded_sources"
    assert report.evidence["is_deleted"] is False
    assert report.evidence["revision_type"] == "이동"
    assert report.evidence["moved_from"] == "제8조"
    assert report.evidence["moved_to"] == "제12조"
    assert report.evidence["current_article"] == "제12조"
    assert report.evidence["loaded_articles"] == ["제8조", "제12조"]
    assert "moved_article_destination_loaded_before_current_substance" in report.evidence["risk_flags"]
    assert {citation.article for citation in report.citations} == {"제8조", "제12조"}
    assert "get_article" not in report.required_followups
    assert "trace_law_history" in report.required_followups
    assert any("moved to 제12조" in claim for claim in report.allowed_claims)
    assert any("loaded destination article" in claim for claim in report.allowed_claims)
    assert any("moved article marker" in claim for claim in report.forbidden_claims)
    assert any("moved article" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_refuses_legal_claim_from_query_expansion_candidates():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["query_expansion_candidate_answer_discipline"]

    assert report.status == "must_load_more_sources"
    assert report.evidence["citations_loaded"] == 0
    assert {"search_laws", "get_article"}.issubset(report.required_followups)
    assert "query_expansion_is_not_final_authority" in report.evidence["risk_flags"]
    assert any("planning" in claim for claim in report.allowed_claims)
    assert any("inspected legal authority" in claim for claim in report.forbidden_claims)
    assert any("output alone" in claim for claim in report.forbidden_claims)
    assert any("planning context" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_refuses_current_law_claim_from_law_search_hits():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["law_search_candidate_answer_discipline"]

    assert report.status == "must_load_more_sources"
    assert "get_article" in report.required_followups
    assert report.evidence["citations_loaded"] == 0
    assert report.evidence["service_call_targets"] == []
    assert (
        "law_search_hit_requires_selected_law_or_article_loading"
        in report.evidence["risk_flags"]
    )
    assert any("identity candidate" in claim for claim in report.allowed_claims)
    assert any("current duty" in claim for claim in report.forbidden_claims)
    assert any("get_law() or get_article()" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_refuses_absence_claim_from_one_empty_law_search():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["empty_law_search_absence_answer_discipline"]

    assert report.status == "must_load_more_sources"
    assert report.citations == []
    assert report.evidence["hit_count"] == 0
    assert report.evidence["search_call_targets"] == ["eflaw"]
    assert "expand_legal_query" in report.required_followups
    assert "search_laws" in report.required_followups
    assert any("zero hits" in claim for claim in report.allowed_claims)
    assert any("No current legal basis exists" in claim for claim in report.forbidden_claims)
    assert any("one scoped law search" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_preserves_moleg_and_ministry_interpretation_authority():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["interpretation_authority_answer_discipline"]

    assert report.status == "can_answer_with_loaded_sources"
    assert report.evidence["labels"] == [
        ["moleg", "expc", None],
        ["ministry", "dapaCgmExpc", "방위사업청"],
    ]
    assert {citation.authority for citation in report.citations} == {
        "MOLEG official interpretation",
        "ministry first-instance interpretation",
    }
    assert any("ministry first-instance" in claim for claim in report.forbidden_claims)
    assert any("all ministry" in claim for claim in report.forbidden_claims)
    assert "get_interpretation" in report.required_followups


def test_answer_discipline_refuses_interpretation_substance_from_search_hits():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["interpretation_search_candidate_answer_discipline"]

    assert report.status == "must_load_more_sources"
    assert "get_interpretation" in report.required_followups
    assert report.evidence["citations_loaded"] == 0
    assert report.evidence["service_call_targets"] == []
    assert "interpretation_search_hit_requires_get_interpretation_detail" in report.evidence["risk_flags"]
    assert any("candidate" in claim for claim in report.allowed_claims)
    assert any("question, answer, or reason" in claim for claim in report.forbidden_claims)
    assert any("get_interpretation" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_refuses_case_rule_from_search_hits():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["case_search_candidate_answer_discipline"]

    assert report.status == "must_load_more_sources"
    assert "get_case" in report.required_followups
    assert report.evidence["citations_loaded"] == 0
    assert report.evidence["service_call_targets"] == []
    assert "case_search_hit_requires_get_case_detail" in report.evidence["risk_flags"]
    assert any("candidate" in claim for claim in report.allowed_claims)
    assert any("judicial holding" in claim for claim in report.forbidden_claims)
    assert any("get_case" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_refuses_absence_claim_from_one_empty_case_search():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["empty_case_search_absence_answer_discipline"]

    assert report.status == "must_load_more_sources"
    assert report.citations == []
    assert report.evidence["hit_count"] == 0
    assert report.evidence["search_call_targets"] == ["prec"]
    assert "search_cases" in report.required_followups
    assert "search_constitutional_decisions" in report.required_followups
    assert "search_interpretations" in report.required_followups
    assert any("zero hits" in claim for claim in report.allowed_claims)
    assert any("No relevant precedent exists" in claim for claim in report.forbidden_claims)
    assert any("one scoped case search" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_refuses_constitutional_reasoning_from_search_hits():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["constitutional_search_candidate_answer_discipline"]

    assert report.status == "must_load_more_sources"
    assert "get_constitutional_decision" in report.required_followups
    assert report.evidence["citations_loaded"] == 0
    assert report.evidence["service_call_targets"] == []
    assert (
        "constitutional_search_hit_requires_get_constitutional_decision_detail"
        in report.evidence["risk_flags"]
    )
    assert any("candidate" in claim for claim in report.allowed_claims)
    assert any("constitutional holding" in claim for claim in report.forbidden_claims)
    assert any("get_constitutional_decision" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_refuses_absence_claim_from_one_empty_constitutional_search():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["empty_constitutional_search_absence_answer_discipline"]

    assert report.status == "must_load_more_sources"
    assert report.citations == []
    assert report.evidence["hit_count"] == 0
    assert report.evidence["search_call_targets"] == ["detc"]
    assert "search_constitutional_decisions" in report.required_followups
    assert "search_cases" in report.required_followups
    assert "search_interpretations" in report.required_followups
    assert any("zero hits" in claim for claim in report.allowed_claims)
    assert any("No constitutional decision exists" in claim for claim in report.forbidden_claims)
    assert any("one scoped Constitutional Court search" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_refuses_mismatched_loaded_authority_as_target_authority():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["authority_article_reference_mismatch_answer_discipline"]

    assert report.status == "must_load_more_sources"
    assert report.citations == []
    assert {
        "search_interpretations",
        "search_cases",
        "search_constitutional_decisions",
    }.issubset(report.required_followups)
    assert report.evidence["target_article"] == {
        "law_name": "개인정보 보호법",
        "article": "제15조",
    }
    assert report.evidence["authority_article_matches"] == {
        "interpretation": False,
        "case": False,
        "constitutional": False,
    }
    assert (
        "loaded_authority_reference_mismatch_not_target_article_authority"
        in report.evidence["risk_flags"]
    )
    assert any("target article" in claim for claim in report.forbidden_claims)
    assert any("no relevant authority exists" in claim.lower() for claim in report.forbidden_claims)
    assert any("structured article references do not match" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_refuses_context_bundle_mismatched_authority_as_target_authority():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["context_bundle_authority_article_mismatch_answer_discipline"]

    assert report.status == "must_load_more_sources"
    assert [citation.source_type for citation in report.citations] == ["law"]
    assert {
        "search_interpretations",
        "search_cases",
        "search_constitutional_decisions",
    }.issubset(report.required_followups)
    assert report.evidence["authority_gap_interfaces"] == [
        "search_interpretations",
        "search_cases",
        "search_constitutional_decisions",
    ]
    assert report.evidence["authority_article_matches"] == {
        "interpretation": False,
        "case": False,
        "constitutional": False,
    }
    assert (
        "context_bundle_eager_authority_reference_mismatch_not_target_article_citation"
        in report.evidence["risk_flags"]
    )
    assert any("target article" in claim for claim in report.forbidden_claims)
    assert any("context bundle" in claim for claim in report.forbidden_claims)
    assert any("authority_article_mismatch" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_refuses_context_bundle_unverified_authority_as_target_authority():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["context_bundle_authority_article_unverified_answer_discipline"]

    assert report.status == "must_load_more_sources"
    assert [citation.source_type for citation in report.citations] == ["law"]
    assert {
        "search_interpretations",
        "search_cases",
        "search_constitutional_decisions",
    }.issubset(report.required_followups)
    assert report.evidence["authority_gap_interfaces"] == [
        "search_interpretations",
        "search_cases",
        "search_constitutional_decisions",
    ]
    assert report.evidence["authority_reference_counts"] == {
        "interpretation": 0,
        "case": 0,
        "constitutional": 0,
    }
    assert (
        "context_bundle_eager_authority_without_structured_refs_not_target_article_citation"
        in report.evidence["risk_flags"]
    )
    assert any("implicit match" in claim for claim in report.forbidden_claims)
    assert any("context bundle" in claim for claim in report.forbidden_claims)
    assert any("authority_article_unverified" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_refuses_context_bundle_partial_authority_as_all_target_authority():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["context_bundle_authority_article_partial_match_answer_discipline"]

    assert report.status == "must_load_more_sources"
    assert [citation.source_type for citation in report.citations] == ["law", "law"]
    assert {
        "search_interpretations",
        "search_cases",
        "search_constitutional_decisions",
    }.issubset(report.required_followups)
    assert report.evidence["target_articles"] == [
        {"law_name": "개인정보 보호법", "article": "제15조"},
        {"law_name": "개인정보 보호법", "article": "제17조"},
    ]
    assert report.evidence["authority_matched_articles"] == {
        "interpretation": ["제17조"],
        "case": ["제17조"],
        "constitutional": ["제17조"],
    }
    assert report.evidence["missing_authority_article"] == "제15조"
    assert (
        "context_bundle_eager_authority_partial_match_not_all_target_articles"
        in report.evidence["risk_flags"]
    )
    assert any("제15조" in claim for claim in report.forbidden_claims)
    assert any("every requested article" in claim for claim in report.forbidden_claims)
    assert any("authority_article_partial_match" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_refuses_context_bundle_older_authority_as_current_authority():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["context_bundle_authority_temporal_mismatch_answer_discipline"]

    assert report.status == "must_load_more_sources"
    assert [citation.source_type for citation in report.citations] == ["law"]
    assert {"trace_law_history", "get_article"}.issubset(report.required_followups)
    assert report.evidence["target_article"] == {
        "law_name": "개인정보 보호법",
        "article": "제15조",
        "effective_date": "20250101",
    }
    assert report.evidence["authority_dates"] == {
        "interpretation": "20210115",
        "case": "20210215",
        "constitutional": "20210315",
    }
    assert report.evidence["authority_article_matches"] == {
        "interpretation": True,
        "case": True,
        "constitutional": True,
    }
    assert report.evidence["authority_gap_interfaces"] == [
        "trace_law_history",
        "trace_law_history",
        "trace_law_history",
    ]
    assert (
        "context_bundle_authority_temporal_mismatch_gap_requires_history_check"
        in report.evidence["risk_flags"]
    )
    assert any("current target-article authority" in claim for claim in report.forbidden_claims)
    assert any("currently effective wording" in claim for claim in report.forbidden_claims)
    assert any("authority_temporal_mismatch" in disclosure for disclosure in report.required_disclosures)
    assert any("effective date" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_refuses_administrative_rule_criteria_from_search_hits():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["administrative_rule_search_candidate_answer_discipline"]

    assert report.status == "must_load_more_sources"
    assert "get_administrative_rule" in report.required_followups
    assert report.evidence["citations_loaded"] == 0
    assert report.evidence["service_call_targets"] == []
    assert (
        "administrative_rule_search_hit_requires_get_administrative_rule_detail"
        in report.evidence["risk_flags"]
    )
    assert any("candidate" in claim for claim in report.allowed_claims)
    assert any("operational criteria" in claim for claim in report.forbidden_claims)
    assert any("get_administrative_rule" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_refuses_issued_on_as_administrative_rule_as_of_proof():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["administrative_rule_issued_on_not_effective_as_of_answer_discipline"]

    assert report.status == "must_load_more_sources"
    assert report.citations == []
    assert "get_administrative_rule" in report.required_followups
    assert "search_administrative_rules" in report.required_followups
    assert report.evidence["reference_date"] == "20250101"
    assert report.evidence["candidate"] == {
        "name": "전기자동차 충전시설 운영 규정",
        "issuing_date": "20250101",
        "effective_date": "20250301",
        "current_status": "현행",
    }
    assert (
        "administrative_rule_issued_on_filter_is_not_effective_as_of"
        in report.evidence["risk_flags"]
    )
    assert any("issued_on" in claim for claim in report.forbidden_claims)
    assert any("current_status" in claim for claim in report.forbidden_claims)
    assert any("발령일자" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_refuses_delegation_detail_from_law_structure_only():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["law_structure_hierarchy_candidate_answer_discipline"]

    assert report.status == "must_load_more_sources"
    assert "find_delegated_rules" in report.required_followups
    assert "get_article" in report.required_followups
    assert "get_administrative_rule" in report.required_followups
    assert {citation.source_type for citation in report.citations} == {"law_structure"}
    assert report.evidence["service_call_targets"] == ["lsStmd"]
    assert report.evidence["article_level_delegation_targets"] == []
    assert "law_structure_is_not_article_level_delegation" in report.evidence["risk_flags"]
    assert any("hierarchy" in claim for claim in report.allowed_claims)
    assert any("article-level delegation" in claim for claim in report.forbidden_claims)
    assert any("operational criteria" in claim for claim in report.forbidden_claims)


def test_answer_discipline_refuses_absence_claim_from_one_empty_delegation_graph():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["empty_delegation_graph_absence_answer_discipline"]

    assert report.status == "must_load_more_sources"
    assert report.citations == []
    assert report.evidence["rule_count"] == 0
    assert report.evidence["service_call_targets"] == ["lsDelegated"]
    assert "find_delegated_rules" in report.required_followups
    assert "get_law_structure" in report.required_followups
    assert "search_administrative_rules" in report.required_followups
    assert "search_annex_forms" in report.required_followups
    assert any("zero rules" in claim for claim in report.allowed_claims)
    assert any("No delegated rule exists" in claim for claim in report.forbidden_claims)
    assert any("one scoped delegation graph" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_requires_admin_rule_destination_loading_for_article_status():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["administrative_rule_article_status_answer_discipline"]

    assert report.status == "must_load_more_sources"
    assert report.citations == []
    assert report.evidence["deleted_article"] == "제3조"
    assert report.evidence["moved_article"] == "제4조"
    assert report.evidence["moved_to"] == "제6조"
    assert (
        "administrative_rule_deleted_article_is_not_current_operational_criteria"
        in report.evidence["risk_flags"]
    )
    assert "get_administrative_rule" in report.required_followups
    assert "trace_law_history" in report.required_followups
    assert any("deleted administrative-rule article" in claim for claim in report.allowed_claims)
    assert any("destination administrative-rule article" in claim for claim in report.forbidden_claims)
    assert any("administrative-rule article status" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_requires_admin_rule_supplementary_provisions_for_transition_claims():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["administrative_rule_supplementary_transition_answer_discipline"]

    assert report.status == "can_answer_with_loaded_sources"
    assert report.evidence["supplementary_provision_count"] == 2
    assert report.evidence["supplementary_text_contains_transition"] is True
    assert (
        "administrative_rule_supplementary_provision_required_for_transition_application"
        in report.evidence["risk_flags"]
    )
    assert "trace_law_history" in report.required_followups
    assert {"administrative_rule", "supplementary_provision"} == {
        citation.source_type for citation in report.citations
    }
    assert any("administrative-rule supplementary provisions" in claim for claim in report.allowed_claims)
    assert any("administrative-rule article alone" in claim for claim in report.forbidden_claims)
    assert any("effective_date metadata" in claim for claim in report.forbidden_claims)
    assert any(
        "Cite administrative-rule supplementary provisions separately" in disclosure
        for disclosure in report.required_disclosures
    )


def test_answer_discipline_refuses_absence_claim_from_one_empty_administrative_rule_search():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["empty_administrative_rule_search_absence_answer_discipline"]

    assert report.status == "must_load_more_sources"
    assert report.citations == []
    assert report.evidence["hit_count"] == 0
    assert report.evidence["search_call_targets"] == ["admrul"]
    assert "find_delegated_rules" in report.required_followups
    assert "search_administrative_rules" in report.required_followups
    assert any("zero hits" in claim for claim in report.allowed_claims)
    assert any("No delegated operational criteria exist" in claim for claim in report.forbidden_claims)
    assert any("one scoped administrative-rule search" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_refuses_comparative_claims_from_candidates_only():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["comparable_mechanism_candidate_answer_discipline"]

    assert report.status == "must_load_more_sources"
    assert "get_article" in report.required_followups
    assert report.evidence["citations_loaded"] == 0
    assert report.evidence["article_service_targets"] == []
    assert (
        "comparable_mechanism_candidate_requires_selected_article_loading"
        in report.evidence["risk_flags"]
    )
    assert any("candidate" in claim for claim in report.allowed_claims)
    assert any("legally equivalent" in claim for claim in report.forbidden_claims)
    assert any("get_article" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_refuses_annex_criteria_from_search_hits():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["annex_form_search_candidate_answer_discipline"]

    assert report.status == "must_load_more_sources"
    assert "get_annex_form_body" in report.required_followups
    assert report.evidence["citations_loaded"] == 0
    assert report.evidence["text_call_targets"] == []
    assert "annex_form_search_hit_requires_get_annex_form_body" in report.evidence["risk_flags"]
    assert any("candidate" in claim for claim in report.allowed_claims)
    assert any("attached criteria" in claim for claim in report.forbidden_claims)
    assert any("get_annex_form_body" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_refuses_absence_claim_from_one_empty_annex_form_search():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["empty_annex_form_search_absence_answer_discipline"]

    assert report.status == "must_load_more_sources"
    assert report.citations == []
    assert report.evidence["hit_count"] == 0
    assert report.evidence["search_call_targets"] == ["licbyl"]
    assert "search_annex_forms" in report.required_followups
    assert "get_law" in report.required_followups
    assert "search_administrative_rules" in report.required_followups
    assert any("zero hits" in claim for claim in report.allowed_claims)
    assert any("No attached criteria exist" in claim for claim in report.forbidden_claims)
    assert any("one scoped annex/form search" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_requires_loading_delegated_candidate_bodies():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["delegated_criteria_answer_discipline"]

    assert report.status == "must_load_more_sources"
    assert {"get_administrative_rule", "get_annex_form_body"}.issubset(report.required_followups)
    assert all(citation.source_type != "administrative_rule" for citation in report.citations)
    assert any("candidates" in claim for claim in report.allowed_claims)
    assert any("inspected" in claim for claim in report.forbidden_claims)


def test_answer_discipline_allows_delegated_criteria_after_followups_only_with_scope_limit():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["delegated_criteria_after_followups_answer_discipline"]

    assert report.status == "can_answer_with_loaded_sources"
    assert {"administrative_rule", "annex"}.issubset(
        {citation.source_type for citation in report.citations}
    )
    assert report.evidence["structured_annex_rows"] == 2
    assert any("selected" in disclosure for disclosure in report.required_disclosures)
    assert any("exhaustively inspected" in claim for claim in report.forbidden_claims)


def test_answer_discipline_refuses_threshold_claims_from_low_confidence_annex_rows():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["low_confidence_annex_body_answer_discipline"]

    assert report.status == "can_answer_with_loaded_sources"
    assert report.evidence["extraction_confidence"] == "high"
    assert report.evidence["parsing_confidence"] == "low"
    assert report.evidence["structured_rows"] == 0
    assert "annex_structured_rows_low_confidence" in report.evidence["risk_flags"]
    assert any("plain text" in claim for claim in report.allowed_claims)
    assert any("empty structured rows" in claim for claim in report.forbidden_claims)
    assert any("low parsing confidence" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_refuses_current_force_claim_for_future_effective_law():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["future_effective_promulgated_law_answer_discipline"]

    assert report.status == "can_answer_with_loaded_sources"
    assert report.evidence["as_of"] == "20260617"
    assert report.evidence["effective_date"] == "20270101"
    assert any("not effective" in claim for claim in report.allowed_claims)
    assert any("currently in force" in claim for claim in report.forbidden_claims)
    assert any("future effective date" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_refuses_current_operational_claim_for_future_effective_admin_rule():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["future_effective_administrative_rule_answer_discipline"]

    assert report.status == "can_answer_with_loaded_sources"
    assert report.evidence["as_of"] == "20260617"
    assert report.evidence["administrative_rule_effective_date"] == "20270101"
    assert any("not effective" in claim for claim in report.allowed_claims)
    assert any("current operational criteria" in claim for claim in report.forbidden_claims)
    assert any("administrative-rule future effective date" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_refuses_exhaustive_constitutional_doctrine_claim():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["constitutional_risk_answer_discipline"]

    assert report.status == "can_answer_with_loaded_sources"
    assert report.evidence["loaded_constitutional_decisions"] == 2
    assert report.evidence["deferred_constitutional_decisions"] == 1
    assert report.evidence["reviewed_articles"] == ["제37조"]
    assert any(citation.source_type == "constitutional" for citation in report.citations)
    assert any("exhaustive" in claim for claim in report.forbidden_claims)
    assert any("free-text search terms" in disclosure for disclosure in report.required_disclosures)
    assert "get_constitutional_decision" in report.required_followups


def test_answer_discipline_allows_comparative_design_only_with_caveat():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["comparative_design_answer_discipline"]

    assert report.status == "can_answer_with_loaded_sources"
    assert any(citation.article == "제50조" for citation in report.citations)
    assert "search_interpretations" in report.required_followups
    assert "search_cases" in report.required_followups
    assert "search_constitutional_decisions" in report.required_followups
    assert any("legally equivalent" in claim for claim in report.forbidden_claims)


def test_answer_discipline_refuses_exhaustive_authority_claim_from_context_bundle():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["context_bundle_authority_answer_discipline"]

    assert report.status == "must_load_more_sources"
    assert {
        "get_interpretation",
        "get_case",
        "get_constitutional_decision",
        "get_administrative_rule",
        "get_annex_form_body",
    }.issubset(report.required_followups)
    assert report.evidence["loaded_authority_detail_types"] == [
        "interpretation_detail",
        "case_detail",
        "constitutional_detail",
    ]
    assert {"administrative_rule", "annex_form"}.issubset(report.evidence["candidate_types"])
    assert (
        "context_bundle_is_bounded_first_pass_not_exhaustive_authority_survey"
        in report.evidence["risk_flags"]
    )
    assert any("Loaded authority details" in claim for claim in report.allowed_claims)
    assert any("exhaustive authority survey" in claim for claim in report.forbidden_claims)
    assert any("administrative-rule" in claim for claim in report.forbidden_claims)
    assert any("annex/form" in claim for claim in report.forbidden_claims)
    assert any("bounded first pass" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_refuses_no_authorization_claim_from_missing_admin_rule_reference():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["administrative_rule_missing_source_reference_answer_discipline"]

    assert report.status == "must_load_more_sources"
    assert "find_delegated_rules" in report.required_followups
    assert report.evidence["source_law_name"] is None
    assert report.evidence["source_article"] is None
    assert report.evidence["service_call_targets"] == ["admrul"]
    assert (
        "missing_administrative_rule_source_reference_is_unknown_not_no_authorization"
        in report.evidence["risk_flags"]
    )
    assert any("unknown source state" in claim for claim in report.allowed_claims)
    assert any("no legal basis" in claim for claim in report.forbidden_claims)
    assert any("invalid" in claim for claim in report.forbidden_claims)
    assert any("not exposed" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_refuses_absence_claim_from_one_empty_interpretation_search():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["empty_interpretation_search_absence_answer_discipline"]

    assert report.status == "must_load_more_sources"
    assert report.evidence["hit_count"] == 0
    assert report.evidence["search_call_targets"] == ["expc"]
    assert report.evidence["citations_loaded"] == 0
    assert "expand_legal_query" in report.required_followups
    assert "search_interpretations" in report.required_followups
    assert any("zero hits" in claim for claim in report.allowed_claims)
    assert any("No relevant interpretation exists" in claim for claim in report.forbidden_claims)
    assert any("absence of authority" in claim for claim in report.forbidden_claims)
    assert any("not an exhaustive interpretation survey" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_refuses_absence_claim_from_source_access_failure():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["source_access_failure_answer_discipline"]

    assert report.status == "must_load_more_sources"
    assert report.citations == []
    assert report.evidence["error_type"] == "RateLimitError"
    assert report.evidence["hit_count"] is None
    assert "search_laws" in report.required_followups
    assert any("source access failed" in claim for claim in report.allowed_claims)
    assert any("No current legal basis exists" in claim for claim in report.forbidden_claims)
    assert any("rate limit" in claim for claim in report.forbidden_claims)
    assert any("source-access failure" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_limits_institutional_system_claims_to_explicit_set():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["institutional_system_answer_discipline"]

    assert report.status == "can_answer_with_loaded_sources"
    assert report.evidence["request_statute_ids"] == [
        "전자금융거래법",
        "전자금융거래법 시행령",
    ]
    assert report.evidence["loaded_laws"] == 2
    assert "institutional_system_does_not_discover_statute_set" in report.evidence["risk_flags"]
    assert {"expand_legal_query", "search_laws"}.issubset(report.required_followups)
    assert any("explicitly selected statute set" in claim for claim in report.allowed_claims)
    assert any("exhaustive list" in claim for claim in report.forbidden_claims)
    assert any("explicit statute set" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_requires_websearch_before_latest_social_fact_claims():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["latest_social_context_answer_discipline"]

    assert report.status == "must_load_more_sources"
    assert report.required_followups == ["websearch.latest_social_facts"]
    assert report.evidence["social_fact_sources_loaded"] == []
    assert report.evidence["follow_up_interfaces"][-1] == "websearch"
    assert "latest_social_facts_require_websearch" in report.evidence["risk_flags"]
    assert {citation.source_type for citation in report.citations} == {"law"}
    assert any("legal text" in claim for claim in report.allowed_claims)
    assert any("latest statistics" in claim for claim in report.forbidden_claims)
    assert any("separate WebSearch citations" in claim for claim in report.forbidden_claims)
    assert any("MOLEG legal-source citations" in disclosure for disclosure in report.required_disclosures)


def test_answer_discipline_requires_supplementary_provisions_for_transition_claims():
    report = {
        item.scenario: item
        for item in run_legislative_expert_answer_discipline()
    }["supplementary_transition_answer_discipline"]

    assert report.status == "can_answer_with_loaded_sources"
    assert report.evidence["supplementary_provision_count"] == 2
    assert report.evidence["supplementary_text_contains_transition"] is True
    assert "supplementary_provision_required_for_transition_application" in report.evidence["risk_flags"]
    assert "trace_law_history" in report.required_followups
    assert {"law", "supplementary_provision"} == {
        citation.source_type for citation in report.citations
    }
    assert any("supplementary provisions" in claim for claim in report.allowed_claims)
    assert any("main article alone" in claim for claim in report.forbidden_claims)
    assert any("effective_date metadata" in claim for claim in report.forbidden_claims)
    assert any("Cite supplementary provisions separately" in disclosure for disclosure in report.required_disclosures)
