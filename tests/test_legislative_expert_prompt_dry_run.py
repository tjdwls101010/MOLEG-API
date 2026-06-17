from scripts.legislative_expert_prompt_dry_run import (
    RAW_MOLEG_TARGETS,
    run_legislative_expert_prompt_dry_run,
)


def test_prompt_dry_run_covers_representative_legislative_prompts():
    reports = run_legislative_expert_prompt_dry_run()

    assert [report.scenario for report in reports] == [
        "current_article_review",
        "nested_article_unit_review",
        "deleted_article_current_force_review",
        "moved_article_current_force_review",
        "query_expansion_candidate_authority_review",
        "law_search_candidate_detail_review",
        "empty_law_search_absence_review",
        "mixed_interpretation_authority_review",
        "interpretation_search_candidate_detail_review",
        "empty_interpretation_search_absence_review",
        "source_access_failure_absence_review",
        "case_search_candidate_detail_review",
        "empty_case_search_absence_review",
        "constitutional_search_candidate_detail_review",
        "empty_constitutional_search_absence_review",
        "authority_article_reference_match_review",
        "context_bundle_authority_article_mismatch_review",
        "context_bundle_authority_article_unverified_review",
        "context_bundle_authority_article_partial_match_review",
        "context_bundle_authority_temporal_mismatch_review",
        "law_structure_hierarchy_candidate_review",
        "empty_delegation_graph_absence_review",
        "administrative_rule_search_candidate_detail_review",
        "administrative_rule_issued_on_current_criteria_review",
        "administrative_rule_article_status_review",
        "administrative_rule_supplementary_transition_review",
        "empty_administrative_rule_search_absence_review",
        "administrative_rule_missing_source_reference_review",
        "comparable_mechanism_candidate_detail_review",
        "proposed_bill_current_law_check",
        "enacted_bill_change_trace",
        "historical_repealed_law_review",
        "supplementary_transition_review",
        "delegated_operational_criteria",
        "annex_search_candidate_detail_review",
        "empty_annex_form_search_absence_review",
        "annex_table_extraction_confidence",
        "comparative_sanction_design",
        "context_bundle_bounded_authority_review",
        "institutional_system_explicit_statute_set_review",
        "constitutional_risk_review",
        "latest_social_context_plus_current_law",
    ]
    assert all(report.prompt for report in reports)
    assert all(report.planned_steps for report in reports)


def test_prompt_dry_run_uses_skill_facing_interfaces_not_raw_targets():
    reports = run_legislative_expert_prompt_dry_run()

    planned_interfaces = {
        step.interface
        for report in reports
        for step in report.planned_steps
    }

    assert planned_interfaces.isdisjoint(RAW_MOLEG_TARGETS)
    assert "get_article" in planned_interfaces
    assert "find_delegated_rules" in planned_interfaces
    assert "find_comparable_mechanisms" in planned_interfaces
    assert "trace_law_history" in planned_interfaces
    assert "compare_law_versions" in planned_interfaces
    assert "latest_social_facts" in planned_interfaces


def test_prompt_dry_run_blocks_proposed_bill_until_congress_bridge_exists():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["proposed_bill_current_law_check"]

    assert report.status == "needs_congress_db_first"
    assert report.planned_steps[0].source == "congress-db"
    assert report.planned_steps[0].interface == "bill_final_outcomes"
    assert any(step.interface == "resolve_promulgated_law" for step in report.planned_steps)
    assert "A proposed bill title is not a current-law identity." in report.guardrails
    assert any("proposed bill" in action for action in report.forbidden_actions)


def test_prompt_dry_run_requires_nested_article_units_for_definition_review():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["nested_article_unit_review"]

    required_interfaces = {
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    }
    optional_interfaces = {
        step.interface
        for step in report.planned_steps
        if not step.required_before_answer
    }

    assert report.status == "moleg_ready"
    assert {"search_laws", "get_article"}.issubset(required_interfaces)
    assert "search_interpretations" in optional_interfaces
    assert any("항, 호, and 목" in guardrail for guardrail in report.guardrails)
    assert any("top-level 조문내용 alone" in action for action in report.forbidden_actions)


def test_prompt_dry_run_requires_article_status_for_deleted_article_review():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["deleted_article_current_force_review"]

    required_interfaces = {
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    }
    optional_interfaces = {
        step.interface
        for step in report.planned_steps
        if not step.required_before_answer
    }

    assert report.status == "moleg_ready"
    assert {"search_laws", "get_article"}.issubset(required_interfaces)
    assert "trace_law_history" in optional_interfaces
    assert any("marked deleted" in guardrail for guardrail in report.guardrails)
    assert any("current duty" in action for action in report.forbidden_actions)


def test_prompt_dry_run_requires_destination_loading_for_moved_article_review():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["moved_article_current_force_review"]

    required_interfaces = [
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    ]
    optional_interfaces = {
        step.interface
        for step in report.planned_steps
        if not step.required_before_answer
    }

    assert report.status == "needs_more_source_loading"
    assert "load_article_context" in required_interfaces
    assert "trace_law_history" in optional_interfaces
    assert any("current_article" in guardrail for guardrail in report.guardrails)
    assert any("current_article" in action for action in report.forbidden_actions)


def test_prompt_dry_run_requires_source_loading_after_query_expansion():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["query_expansion_candidate_authority_review"]

    required_interfaces = {
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    }

    assert report.status == "needs_more_source_loading"
    assert {"expand_legal_query", "search_laws", "get_article"}.issubset(required_interfaces)
    assert any("planning context" in guardrail for guardrail in report.guardrails)
    assert any("output alone" in action for action in report.forbidden_actions)


def test_prompt_dry_run_requires_law_or_article_loading_after_law_search():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["law_search_candidate_detail_review"]

    required_interfaces = {
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    }

    assert report.status == "needs_more_source_loading"
    assert {"search_laws", "get_article"}.issubset(required_interfaces)
    assert any("identity candidates" in guardrail for guardrail in report.guardrails)
    assert any("search_laws() output alone" in action for action in report.forbidden_actions)
    assert any("current duty" in action for action in report.forbidden_actions)


def test_prompt_dry_run_refuses_absence_claim_from_one_empty_law_search():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["empty_law_search_absence_review"]

    required_interfaces = [
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    ]

    assert report.status == "needs_more_source_loading"
    assert required_interfaces.count("search_laws") == 2
    assert "expand_legal_query" in required_interfaces
    assert any("one scoped law search" in guardrail for guardrail in report.guardrails)
    assert any("No current legal basis exists" in action for action in report.forbidden_actions)
    assert any("zero hits" in action for action in report.forbidden_actions)


def test_prompt_dry_run_requires_history_or_diff_before_amendment_delta_claims():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["enacted_bill_change_trace"]

    required_interfaces = {
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    }

    assert report.status == "needs_more_source_loading"
    assert report.planned_steps[0].source == "congress-db"
    assert {"resolve_promulgated_law", "get_law"}.issubset(required_interfaces)
    assert {"trace_law_history", "compare_law_versions"}.issubset(required_interfaces)
    assert any("not the amendment delta" in guardrail for guardrail in report.guardrails)
    assert any("current text alone" in action for action in report.forbidden_actions)
    assert any("bridge resolution" in action for action in report.forbidden_actions)


def test_prompt_dry_run_distinguishes_historical_repealed_law_from_current_law():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["historical_repealed_law_review"]

    required_interfaces = {
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    }
    optional_interfaces = {
        step.interface
        for step in report.planned_steps
        if not step.required_before_answer
    }

    assert report.status == "moleg_ready"
    assert {"search_laws", "trace_law_history", "get_article"}.issubset(required_interfaces)
    assert "search_laws" in optional_interfaces
    assert any("not a current-law prompt" in guardrail for guardrail in report.guardrails)
    assert any("current no-result" in action for action in report.forbidden_actions)
    assert any("currently in force" in action for action in report.forbidden_actions)


def test_prompt_dry_run_requires_full_law_text_for_supplementary_transition_review():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["supplementary_transition_review"]

    required_interfaces = {
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    }
    optional_interfaces = {
        step.interface
        for step in report.planned_steps
        if not step.required_before_answer
    }

    assert report.status == "moleg_ready"
    assert {"search_laws", "get_law"}.issubset(required_interfaces)
    assert "trace_law_history" in optional_interfaces
    assert any("Supplementary provisions" in guardrail for guardrail in report.guardrails)
    assert any("main article alone" in action for action in report.forbidden_actions)
    assert any("effective_date metadata" in action for action in report.forbidden_actions)


def test_prompt_dry_run_preserves_interpretation_authority_labels():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["mixed_interpretation_authority_review"]

    planned_interfaces = {step.interface for step in report.planned_steps}

    assert report.status == "moleg_ready"
    assert {"search_interpretations", "get_interpretation"}.issubset(planned_interfaces)
    assert any("distinct authority labels" in guardrail for guardrail in report.guardrails)
    assert any("all ministries" in action for action in report.forbidden_actions)


def test_prompt_dry_run_requires_interpretation_detail_before_substance_claims():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["interpretation_search_candidate_detail_review"]

    required_interfaces = {
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    }

    assert report.status == "needs_more_source_loading"
    assert {"search_interpretations", "get_interpretation"}.issubset(required_interfaces)
    assert any("candidate metadata" in guardrail for guardrail in report.guardrails)
    assert any("search_interpretations() output alone" in action for action in report.forbidden_actions)
    assert any("question, answer, reason" in action for action in report.forbidden_actions)


def test_prompt_dry_run_requires_case_detail_before_judicial_reasoning():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["case_search_candidate_detail_review"]

    required_interfaces = {
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    }

    assert report.status == "needs_more_source_loading"
    assert {"search_cases", "get_case"}.issubset(required_interfaces)
    assert any("candidate metadata" in guardrail for guardrail in report.guardrails)
    assert any("search_cases() output alone" in action for action in report.forbidden_actions)
    assert any("case full text" in action for action in report.forbidden_actions)


def test_prompt_dry_run_refuses_absence_claim_from_one_empty_case_search():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["empty_case_search_absence_review"]

    required_interfaces = [
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    ]

    assert report.status == "needs_more_source_loading"
    assert required_interfaces.count("search_cases") == 2
    assert "search_constitutional_decisions" in required_interfaces
    assert "search_interpretations" in required_interfaces
    assert any("one scoped case search" in guardrail for guardrail in report.guardrails)
    assert any("No relevant precedent exists" in action for action in report.forbidden_actions)
    assert any("zero hits" in action for action in report.forbidden_actions)


def test_prompt_dry_run_requires_constitutional_detail_before_reasoning():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["constitutional_search_candidate_detail_review"]

    required_interfaces = {
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    }

    assert report.status == "needs_more_source_loading"
    assert {"search_constitutional_decisions", "get_constitutional_decision"}.issubset(
        required_interfaces
    )
    assert any("candidate metadata" in guardrail for guardrail in report.guardrails)
    assert any(
        "search_constitutional_decisions() output alone" in action
        for action in report.forbidden_actions
    )
    assert any("decision summary" in action for action in report.forbidden_actions)


def test_prompt_dry_run_refuses_absence_claim_from_one_empty_constitutional_search():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["empty_constitutional_search_absence_review"]

    required_interfaces = [
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    ]

    assert report.status == "needs_more_source_loading"
    assert required_interfaces.count("search_constitutional_decisions") == 2
    assert "search_cases" in required_interfaces
    assert "search_interpretations" in required_interfaces
    assert any("one scoped Constitutional Court search" in guardrail for guardrail in report.guardrails)
    assert any("No constitutional decision exists" in action for action in report.forbidden_actions)
    assert any("no constitutional risk" in action for action in report.forbidden_actions)


def test_prompt_dry_run_requires_authority_article_reference_match_before_citation():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["authority_article_reference_match_review"]

    required_interfaces = {
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    }

    assert report.status == "needs_more_source_loading"
    assert {
        "get_interpretation",
        "get_case",
        "get_constitutional_decision",
        "search_interpretations",
        "search_cases",
        "search_constitutional_decisions",
    }.issubset(required_interfaces)
    assert any("referenced_articles" in guardrail for guardrail in report.guardrails)
    assert any("reviewed_articles" in guardrail for guardrail in report.guardrails)
    assert any("different article" in action for action in report.forbidden_actions)
    assert any("no relevant authority exists" in action for action in report.forbidden_actions)


def test_prompt_dry_run_requires_followup_when_context_bundle_authorities_mismatch_article():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["context_bundle_authority_article_mismatch_review"]

    required_interfaces = {
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    }

    assert report.status == "needs_more_source_loading"
    assert {
        "load_legal_context_bundle",
        "search_interpretations",
        "search_cases",
        "search_constitutional_decisions",
    }.issubset(required_interfaces)
    assert any("authority_article_mismatch" in guardrail for guardrail in report.guardrails)
    assert any("referenced_articles" in guardrail for guardrail in report.guardrails)
    assert any("eager-loaded" in action for action in report.forbidden_actions)
    assert any("target-article authority" in action for action in report.forbidden_actions)


def test_prompt_dry_run_requires_followup_when_context_bundle_authorities_lack_article_refs():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["context_bundle_authority_article_unverified_review"]

    required_interfaces = {
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    }

    assert report.status == "needs_more_source_loading"
    assert {
        "load_legal_context_bundle",
        "search_interpretations",
        "search_cases",
        "search_constitutional_decisions",
    }.issubset(required_interfaces)
    assert any("authority_article_unverified" in guardrail for guardrail in report.guardrails)
    assert any("referenced_articles" in guardrail for guardrail in report.guardrails)
    assert any("reviewed_articles" in guardrail for guardrail in report.guardrails)
    assert any("implicit match" in action for action in report.forbidden_actions)
    assert any("target-article authority" in action for action in report.forbidden_actions)


def test_prompt_dry_run_requires_followup_when_context_bundle_authorities_match_only_some_articles():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["context_bundle_authority_article_partial_match_review"]

    required_interfaces = {
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    }

    assert report.status == "needs_more_source_loading"
    assert {
        "load_legal_context_bundle",
        "search_interpretations",
        "search_cases",
        "search_constitutional_decisions",
    }.issubset(required_interfaces)
    assert any("authority_article_partial_match" in guardrail for guardrail in report.guardrails)
    assert any("some requested articles" in guardrail for guardrail in report.guardrails)
    assert any("referenced_articles" in guardrail for guardrail in report.guardrails)
    assert any("reviewed_articles" in guardrail for guardrail in report.guardrails)
    assert any("all requested articles" in action for action in report.forbidden_actions)
    assert any("broadcast" in action for action in report.forbidden_actions)


def test_prompt_dry_run_requires_history_when_context_bundle_authority_predates_current_article():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["context_bundle_authority_temporal_mismatch_review"]

    required_interfaces = {
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    }

    assert report.status == "needs_more_source_loading"
    assert {
        "load_legal_context_bundle",
        "trace_law_history",
        "get_article",
    }.issubset(required_interfaces)
    assert any("authority_temporal_mismatch" in guardrail for guardrail in report.guardrails)
    assert any("effective date" in guardrail for guardrail in report.guardrails)
    assert any("referenced_articles" in action for action in report.forbidden_actions)
    assert any("current wording" in action for action in report.forbidden_actions)


def test_prompt_dry_run_requires_delegation_and_detail_after_law_structure():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["law_structure_hierarchy_candidate_review"]

    required_interfaces = [
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    ]

    assert report.status == "needs_more_source_loading"
    assert required_interfaces[0] == "get_law_structure"
    assert "find_delegated_rules" in required_interfaces
    assert "get_article" in required_interfaces
    assert "get_administrative_rule" in required_interfaces
    assert any("hierarchy" in guardrail for guardrail in report.guardrails)
    assert any("article-level delegation" in action for action in report.forbidden_actions)
    assert any("operational criteria" in action for action in report.forbidden_actions)


def test_prompt_dry_run_refuses_absence_claim_from_one_empty_delegation_graph():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["empty_delegation_graph_absence_review"]

    required_interfaces = [
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    ]

    assert report.status == "needs_more_source_loading"
    assert required_interfaces.count("find_delegated_rules") == 2
    assert "get_law_structure" in required_interfaces
    assert "search_administrative_rules" in required_interfaces
    assert "search_annex_forms" in required_interfaces
    assert any("one scoped delegation graph" in guardrail for guardrail in report.guardrails)
    assert any("No delegated rule exists" in action for action in report.forbidden_actions)
    assert any("zero rules" in action for action in report.forbidden_actions)


def test_prompt_dry_run_requires_administrative_rule_detail_before_operational_claims():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["administrative_rule_search_candidate_detail_review"]

    required_interfaces = {
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    }

    assert report.status == "needs_more_source_loading"
    assert {"search_administrative_rules", "get_administrative_rule"}.issubset(
        required_interfaces
    )
    assert any("candidate metadata" in guardrail for guardrail in report.guardrails)
    assert any(
        "search_administrative_rules() output alone" in action
        for action in report.forbidden_actions
    )
    assert any("current operational criteria" in action for action in report.forbidden_actions)


def test_prompt_dry_run_keeps_administrative_rule_issued_on_separate_from_as_of():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["administrative_rule_issued_on_current_criteria_review"]

    required_interfaces = [
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    ]

    assert report.status == "needs_more_source_loading"
    assert required_interfaces.count("search_administrative_rules") == 2
    assert "get_administrative_rule" in required_interfaces
    assert any("발령일자" in guardrail for guardrail in report.guardrails)
    assert any("as-of" in guardrail for guardrail in report.guardrails)
    assert any("issued_on" in action for action in report.forbidden_actions)
    assert any("effective_date" in action for action in report.forbidden_actions)


def test_prompt_dry_run_requires_admin_rule_destination_loading_for_article_status():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["administrative_rule_article_status_review"]

    required_interfaces = [
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    ]
    optional_interfaces = {
        step.interface
        for step in report.planned_steps
        if not step.required_before_answer
    }

    assert report.status == "needs_more_source_loading"
    assert required_interfaces == ["load_administrative_rule_context"]
    assert "trace_law_history" in optional_interfaces
    assert any("deleted administrative-rule article" in guardrail for guardrail in report.guardrails)
    assert any("moved administrative-rule article marker" in action for action in report.forbidden_actions)


def test_prompt_dry_run_requires_admin_rule_detail_for_supplementary_transition_review():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["administrative_rule_supplementary_transition_review"]

    required_interfaces = {
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    }
    optional_interfaces = {
        step.interface
        for step in report.planned_steps
        if not step.required_before_answer
    }

    assert report.status == "moleg_ready"
    assert "get_administrative_rule" in required_interfaces
    assert "trace_law_history" in optional_interfaces
    assert any("Administrative-rule supplementary provisions" in guardrail for guardrail in report.guardrails)
    assert any("administrative-rule article alone" in action for action in report.forbidden_actions)
    assert any("effective_date metadata" in action for action in report.forbidden_actions)


def test_prompt_dry_run_refuses_absence_claim_from_one_empty_administrative_rule_search():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["empty_administrative_rule_search_absence_review"]

    required_interfaces = [
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    ]

    assert report.status == "needs_more_source_loading"
    assert required_interfaces.count("search_administrative_rules") == 2
    assert "find_delegated_rules" in required_interfaces
    assert any("one scoped administrative-rule search" in guardrail for guardrail in report.guardrails)
    assert any("No delegated operational criteria exist" in action for action in report.forbidden_actions)
    assert any("zero hits" in action for action in report.forbidden_actions)


def test_prompt_dry_run_requires_comparable_article_before_design_claims():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["comparable_mechanism_candidate_detail_review"]

    required_interfaces = {
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    }

    assert report.status == "needs_more_source_loading"
    assert {"find_comparable_mechanisms", "get_article"}.issubset(required_interfaces)
    assert any("planning candidates" in guardrail for guardrail in report.guardrails)
    assert any("find_comparable_mechanisms() output alone" in action for action in report.forbidden_actions)
    assert any("legally equivalent" in action for action in report.forbidden_actions)


def test_prompt_dry_run_refuses_no_authorization_claim_from_missing_admin_rule_reference():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["administrative_rule_missing_source_reference_review"]

    required_interfaces = {
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    }

    assert report.status == "needs_more_source_loading"
    assert {"get_administrative_rule", "find_delegated_rules"}.issubset(required_interfaces)
    assert any("unknown in this MOLEG payload" in guardrail for guardrail in report.guardrails)
    assert any("source_law_name=None" in action for action in report.forbidden_actions)
    assert any("invalid" in action for action in report.forbidden_actions)


def test_prompt_dry_run_refuses_absence_claim_from_one_empty_interpretation_search():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["empty_interpretation_search_absence_review"]

    required_interfaces = [
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    ]

    assert report.status == "needs_more_source_loading"
    assert required_interfaces.count("search_interpretations") == 2
    assert "expand_legal_query" in required_interfaces
    assert any("not proof" in guardrail for guardrail in report.guardrails)
    assert any("no relevant interpretation exists" in action for action in report.forbidden_actions)
    assert any("zero hits" in action for action in report.forbidden_actions)


def test_prompt_dry_run_refuses_absence_claim_from_source_access_failure():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["source_access_failure_absence_review"]

    required_interfaces = [
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    ]

    assert report.status == "needs_more_source_loading"
    assert required_interfaces == ["search_laws", "search_laws"]
    assert any("source-access problem" in guardrail for guardrail in report.guardrails)
    assert any("RateLimitError" in guardrail for guardrail in report.guardrails)
    assert any("no current legal basis" in action for action in report.forbidden_actions)
    assert any("rate limit" in action for action in report.forbidden_actions)


def test_prompt_dry_run_refuses_exhaustive_authority_claim_from_context_bundle():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["context_bundle_bounded_authority_review"]

    required_interfaces = {
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    }

    assert report.status == "needs_more_source_loading"
    assert "load_legal_context_bundle" in required_interfaces
    assert {
        "get_interpretation",
        "get_case",
        "get_constitutional_decision",
        "get_administrative_rule",
        "get_annex_form_body",
    }.issubset(required_interfaces)
    assert any("bounded first pass" in guardrail for guardrail in report.guardrails)
    assert any("exhaustive authority survey" in action for action in report.forbidden_actions)
    assert any("administrative-rule" in action for action in report.forbidden_actions)
    assert any("annex/form" in action for action in report.forbidden_actions)


def test_prompt_dry_run_limits_institutional_system_to_explicit_statute_set():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["institutional_system_explicit_statute_set_review"]

    required_interfaces = {
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    }
    optional_interfaces = {
        step.interface
        for step in report.planned_steps
        if not step.required_before_answer
    }

    assert report.status == "moleg_ready"
    assert required_interfaces == {"load_institutional_system"}
    assert {"expand_legal_query", "search_laws"}.issubset(optional_interfaces)
    assert any("already selected" in guardrail for guardrail in report.guardrails)
    assert any("exhaustive" in action for action in report.forbidden_actions)


def test_prompt_dry_run_requires_detail_loading_for_delegated_candidates():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["delegated_operational_criteria"]

    required_interfaces = {
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    }

    assert report.status == "needs_more_source_loading"
    assert required_interfaces == {"load_delegated_criteria"}
    assert any("bounded source loading" in guardrail for guardrail in report.guardrails)
    assert any("exhaustively inspected" in action for action in report.forbidden_actions)


def test_prompt_dry_run_requires_annex_body_before_attached_criteria_claims():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["annex_search_candidate_detail_review"]

    required_interfaces = {
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    }

    assert report.status == "needs_more_source_loading"
    assert {"search_annex_forms", "get_annex_form_body"}.issubset(required_interfaces)
    assert any("candidate metadata" in guardrail for guardrail in report.guardrails)
    assert any("search_annex_forms() output alone" in action for action in report.forbidden_actions)
    assert any("thresholds" in action for action in report.forbidden_actions)


def test_prompt_dry_run_refuses_absence_claim_from_one_empty_annex_form_search():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["empty_annex_form_search_absence_review"]

    required_interfaces = [
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    ]

    assert report.status == "needs_more_source_loading"
    assert required_interfaces.count("search_annex_forms") == 2
    assert "get_law" in required_interfaces
    assert "search_administrative_rules" in required_interfaces
    assert any("one scoped annex/form search" in guardrail for guardrail in report.guardrails)
    assert any("No attached criteria exist" in action for action in report.forbidden_actions)
    assert any("zero hits" in action for action in report.forbidden_actions)


def test_prompt_dry_run_requires_annex_parsing_confidence_before_structured_thresholds():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["annex_table_extraction_confidence"]

    required_interfaces = {
        step.interface
        for step in report.planned_steps
        if step.required_before_answer
    }

    assert report.status == "moleg_ready"
    assert {"search_annex_forms", "get_annex_form_body"}.issubset(required_interfaces)
    assert any("parsing_confidence is high" in guardrail for guardrail in report.guardrails)
    assert any("empty low-confidence structured rows" in action for action in report.forbidden_actions)
    assert any("no thresholds" in action for action in report.forbidden_actions)


def test_prompt_dry_run_routes_latest_social_facts_to_websearch():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["latest_social_context_plus_current_law"]

    assert report.status == "requires_websearch_handoff"
    assert any(step.source == "websearch" for step in report.planned_steps)
    assert any(step.source == "moleg-api" for step in report.planned_steps)
    assert any("WebSearch" in guardrail for guardrail in report.guardrails)


def test_prompt_dry_run_marks_constitutional_doctrine_search_as_free_text():
    report = {
        item.scenario: item
        for item in run_legislative_expert_prompt_dry_run()
    }["constitutional_risk_review"]

    planned_interfaces = {step.interface for step in report.planned_steps}

    assert report.status == "moleg_ready"
    assert {"search_constitutional_decisions", "get_constitutional_decision"}.issubset(
        planned_interfaces
    )
    assert any("free-text" in guardrail for guardrail in report.guardrails)
    assert any("exhaustive" in action for action in report.forbidden_actions)
