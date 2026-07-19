from dataclasses import is_dataclass

import moleg_api
import moleg_api.models as models
from moleg_api import LawGoKrClient, MolegApi
from moleg_api.cli import CATALOG, build_parser, main, signals_for
from moleg_api.laws import (
    MINISTRY_INTERPRETATION_SOURCES,
    delegated_criteria_target_scope,
    delegated_subordinate_rule_names,
    enrich_annex_identity_from_body,
    structured_table_from_rows,
)
from moleg_api.normalization import (
    format_article_jo,
    mask_oc_param,
    normalize_delegated_rules,
    parse_law_history_html,
    unwrap_search_judicial_decisions,
)
from moleg_api.source import DEFAULT_OC


def test_legacy_public_imports_survive_refactor():
    assert MolegApi is moleg_api.MolegApi
    assert LawGoKrClient is moleg_api.LawGoKrClient
    assert callable(build_parser)
    assert callable(main)
    assert callable(signals_for)
    assert "경찰청" in MINISTRY_INTERPRETATION_SOURCES
    assert callable(delegated_criteria_target_scope)
    assert callable(delegated_subordinate_rule_names)
    assert callable(enrich_annex_identity_from_body)
    assert callable(structured_table_from_rows)
    assert format_article_jo("제10조의2") == "001002"
    assert callable(mask_oc_param)
    assert callable(normalize_delegated_rules)
    assert callable(parse_law_history_html)
    assert callable(unwrap_search_judicial_decisions)


def test_model_dataclasses_keep_public_module_identity():
    model_classes = [
        value
        for value in vars(models).values()
        if isinstance(value, type) and is_dataclass(value)
    ]

    assert model_classes
    assert all(model_class.__module__ == "moleg_api.models" for model_class in model_classes)


def test_cli_parser_and_catalog_command_surfaces_match():
    parser = build_parser()
    subparsers = [
        action for action in parser._actions if getattr(action, "choices", None)
    ]
    parser_commands = set(subparsers[0].choices)
    catalog_commands = {cmd for group in CATALOG["commands"].values() for cmd in group}

    assert parser_commands - {"catalog"} == catalog_commands
    assert "catalog" in parser_commands
    # A lower bound, not an exact count: the invariant worth holding is the set
    # equality above. Pinning the number only guarantees that whoever adds a
    # command also edits this line, which teaches them to edit the line.
    assert len(parser_commands - {"catalog"}) >= 27


def test_shared_oc_default_remains_registered_for_zero_config_use():
    assert DEFAULT_OC == "chunghun1"
    assert LawGoKrClient().oc == "chunghun1"
