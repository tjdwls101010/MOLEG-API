import inspect

from moleg_api.laws import MolegApi


CORE_METHODS = [
    "search_laws",
    "resolve_promulgated_law",
    "get_law",
    "get_article",
    "trace_law_history",
    "compare_law_versions",
    "find_delegated_rules",
    "get_law_structure",
    "search_administrative_rules",
    "search_annex_forms",
    "get_annex_form_body",
    "get_administrative_rule",
    "search_interpretations",
    "get_interpretation",
    "search_cases",
    "get_case",
    "search_constitutional_decisions",
    "get_constitutional_decision",
    "expand_legal_query",
    "find_comparable_mechanisms",
    "load_institutional_system",
    "load_legal_context_bundle",
]


def test_moleg_api_class_docstring_contains_method_selection_tree():
    doc = inspect.getdoc(MolegApi)

    assert doc is not None
    assert "Method selection" in doc
    for method_name in [
        "resolve_promulgated_law",
        "search_laws",
        "expand_legal_query",
        "search_interpretations",
        "search_cases",
        "search_constitutional_decisions",
    ]:
        assert method_name in doc


def test_all_public_methods_have_skill_author_contract_docstrings():
    public_names = [
        name
        for name, member in inspect.getmembers(MolegApi, predicate=inspect.isfunction)
        if not name.startswith("_")
    ]

    assert set(CORE_METHODS).issubset(public_names)
    for method_name in public_names:
        doc = inspect.getdoc(getattr(MolegApi, method_name))
        assert doc is not None, method_name
        for required_section in ["Use when:", "Returns:", "Raises:", "Related:"]:
            assert required_section in doc, method_name
