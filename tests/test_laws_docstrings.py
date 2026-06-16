import ast
import inspect
import re
from pathlib import Path
from typing import get_type_hints

import moleg_api
import moleg_api.errors as error_model
from moleg_api.laws import MolegApi
from moleg_api.models import BundleBudget


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


def _format_prd_default(value):
    if isinstance(value, str):
        return f'"{value}"'
    return repr(value)


def _format_prd_signature(method):
    params = []
    keyword_marker_added = False
    for param in inspect.signature(method).parameters.values():
        if param.name == "self":
            continue
        if (
            param.kind is inspect.Parameter.KEYWORD_ONLY
            and not keyword_marker_added
        ):
            params.append("*")
            keyword_marker_added = True
        rendered = param.name
        if param.default is not inspect.Parameter.empty:
            rendered = f"{rendered}={_format_prd_default(param.default)}"
        params.append(rendered)
    return f"{method.__name__}({', '.join(params)})"


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


def test_bundle_loader_budget_signatures_use_public_literal_vocabulary():
    institutional_hints = get_type_hints(MolegApi.load_institutional_system)
    context_hints = get_type_hints(MolegApi.load_legal_context_bundle)

    assert institutional_hints["budget"] == BundleBudget
    assert context_hints["budget"] == BundleBudget


def test_prd_public_interface_list_matches_public_methods():
    prd = Path("docs/design/PRD.md").read_text(encoding="utf-8")
    section = prd.split("## Public Interface", 1)[1].split("## Testing Decisions", 1)[0]
    documented_methods = {
        match.group(1)
        for match in re.finditer(r"^- `([a-zA-Z_][a-zA-Z0-9_]*)\(", section, re.MULTILINE)
    }
    public_methods = {
        name
        for name, member in inspect.getmembers(MolegApi, predicate=inspect.isfunction)
        if not name.startswith("_")
    }

    assert documented_methods == public_methods
    assert "search_body=False" in section
    assert "include_history=False" in section
    assert "include_websearch_hint=True" in section


def test_prd_public_interface_signatures_match_public_methods():
    prd = Path("docs/design/PRD.md").read_text(encoding="utf-8")
    section = prd.split("## Public Interface", 1)[1].split("## Testing Decisions", 1)[0]
    documented_signatures = {
        signature.split("(", 1)[0]: signature
        for signature in re.findall(
            r"^- `([a-zA-Z_][a-zA-Z0-9_]*\([^`]+\))`",
            section,
            re.MULTILINE,
        )
    }
    public_signatures = {
        name: _format_prd_signature(member)
        for name, member in inspect.getmembers(MolegApi, predicate=inspect.isfunction)
        if not name.startswith("_")
    }

    assert documented_signatures == public_signatures


def test_skill_integration_interface_list_matches_public_methods():
    skill_integration = Path("docs/SKILL-INTEGRATION.md").read_text(encoding="utf-8")
    section = skill_integration.split("## Expected Public Interfaces", 1)[1].split(
        "## Answering Discipline",
        1,
    )[0]
    documented_methods = {
        match.group(1)
        for match in re.finditer(
            r"^- `MolegApi\.([a-zA-Z_][a-zA-Z0-9_]*)\(\)`",
            section,
            re.MULTILINE,
        )
    }
    public_methods = {
        name
        for name, member in inspect.getmembers(MolegApi, predicate=inspect.isfunction)
        if not name.startswith("_")
    }

    assert documented_methods == public_methods
    assert "These interfaces are implemented as the skill-facing contract" in section


def test_skill_author_cookbook_distinguishes_pre_publication_install_paths():
    cookbook = Path("docs/SKILL-AUTHOR-COOKBOOK.md").read_text(encoding="utf-8")
    installation = cookbook.split("## Installation And Setup", 1)[1].split(
        "## Serialization",
        1,
    )[0]

    assert "After the human release step publishes the package" in installation
    assert "Before PyPI publication" in installation
    assert "python -m pip install ." in installation
    assert "python -m pip wheel . --no-deps -w dist" in installation
    assert "python -m pip install dist/moleg_api-*.whl --no-deps" in installation


def test_skill_author_cookbook_import_examples_are_package_root_exports():
    cookbook = Path("docs/SKILL-AUTHOR-COOKBOOK.md").read_text(encoding="utf-8")
    imported_names = {
        name.strip()
        for import_line in re.findall(
            r"^from moleg_api import ([^\n]+)$",
            cookbook,
            re.MULTILINE,
        )
        for name in import_line.split(",")
    }

    assert imported_names
    assert {
        name for name in imported_names if not hasattr(moleg_api, name)
    } == set()


def test_skill_author_cookbook_method_examples_are_public_moleg_api_methods():
    cookbook = Path("docs/SKILL-AUTHOR-COOKBOOK.md").read_text(encoding="utf-8")
    documented_methods = {
        match.group(1)
        for match in re.finditer(
            r"\bapi\.([a-zA-Z_][a-zA-Z0-9_]*)\(",
            cookbook,
        )
    }
    public_methods = {
        name
        for name, member in inspect.getmembers(MolegApi, predicate=inspect.isfunction)
        if not name.startswith("_")
    }

    assert documented_methods
    assert documented_methods <= public_methods


def test_skill_author_cookbook_python_examples_are_syntax_valid():
    cookbook = Path("docs/SKILL-AUTHOR-COOKBOOK.md").read_text(encoding="utf-8")
    python_blocks = re.findall(r"```python\n(.*?)\n```", cookbook, re.DOTALL)

    assert python_blocks
    for index, block in enumerate(python_blocks, start=1):
        ast.parse(block, filename=f"docs/SKILL-AUTHOR-COOKBOOK.md python block {index}")


def test_skill_author_cookbook_vendored_fallback_lists_package_files():
    cookbook = Path("docs/SKILL-AUTHOR-COOKBOOK.md").read_text(encoding="utf-8")
    section = cookbook.split("## Vendored Fallback", 1)[1].split(
        "## Error Handling",
        1,
    )[0]
    documented_files = {
        match.group(1)
        for match in re.finditer(
            r"^      ([a-zA-Z_][a-zA-Z0-9_]*(?:\.py)?|py\.typed)$",
            section,
            re.MULTILINE,
        )
    }
    package_files = {
        path.name
        for path in Path("moleg_api").iterdir()
        if path.is_file() and (path.suffix == ".py" or path.name == "py.typed")
    }

    assert documented_files == package_files


def test_skill_author_cookbook_error_handling_covers_public_error_exports():
    cookbook = Path("docs/SKILL-AUTHOR-COOKBOOK.md").read_text(encoding="utf-8")
    section = cookbook.split("## Error Handling", 1)[1].split(
        "## Source Boundaries",
        1,
    )[0]
    public_error_names = {
        name
        for name, value in vars(error_model).items()
        if (
            isinstance(value, type)
            and issubclass(value, Exception)
            and value.__module__ == error_model.__name__
            and name in moleg_api.__all__
        )
    }

    assert public_error_names
    assert public_error_names <= set(re.findall(r"`([A-Za-z][A-Za-z0-9_]+)`", section))
