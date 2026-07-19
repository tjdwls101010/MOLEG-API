"""Whole-surface dispatch smoke + catalog/parser/dispatch agreement (WI-P8).

The 0.2.3 file-split refactor dropped three imports that were only referenced
inside command paths — institutional dispatch (50169cf), constitutional
disposition (41bcd43), and the unwrap failure path (fixed in 0.3.0, which had
been shipping a NameError traceback since 0.2.4). Every one of them passed CI:
the suite imported the modules and exercised the SDK, but nothing ran each
subcommand end to end, and a name that is only looked up when a branch executes
is invisible until that branch executes.

So this file walks the whole command surface. It asserts almost nothing about the
*answers* — the point is that every command survives its own dispatch path and
produces a well-formed envelope instead of an interpreter traceback. Argv is
derived from the parser rather than hand-listed, so a command added later is
covered the day it is added, not the day someone remembers to add it here.
"""

import argparse
import inspect
import json
import re
import sys

import pytest

from moleg_api import MolegApi
from moleg_api._cli.catalog import CATALOG
from moleg_api._cli.dispatch import _call
from moleg_api._cli.parser import build_parser
from moleg_api.cli import main

VALID_EXIT_CODES = {0, 2, 3, 4, 5}

# Placeholders keyed by the parser's own dest/flag names. Values only need to be
# well formed — the fake source decides what comes back.
PLACEHOLDERS = {
    "query": "개인정보",
    "concept": "과징금",
    "article": "제3조",
    "--law": "011357",
    "--id": "123456",
    "--article": "제3조",
    "--json": json.dumps(
        {"interface": "get_law", "query": "개인정보 보호법", "reason": "smoke", "filters": {}},
        ensure_ascii=False,
    ),
}

# Commands whose interesting dispatch branch only runs when an optional argument
# is present. load-institutional-system is the 50169cf regression itself: without
# --statute it short-circuits before reaching the code that lost its import.
EXTRA_ARGS = {
    "load-institutional-system": ["--statute", "001638", "--article", "제3조"],
    "load-legal-context-bundle": ["--query", "개인정보 유출", "--law", "011357"],
    "load-delegated-criteria": ["--article", "제3조"],
    "trace-law-history": ["--article", "제3조"],
    "compare-law-versions": ["--article", "제3조"],
    "find-delegated-rules": ["--article", "제3조"],
    # narrowing modes are separate dispatch branches, not just formatting
    "get-law": ["--toc"],
    "get-case": ["--brief"],
    "get-constitutional-decision": ["--brief"],
    "get-interpretation": ["--brief"],
}


class SmokeSource:
    """Fake law.go.kr that answers every call with the same shape.

    Three modes, because the failures hide at different depths and each mode
    reaches a branch the others skip:

    - ``empty`` — ``{}``, what law.go.kr actually returns for a bad identifier;
      drives the no-result path.
    - ``shallow`` — ``{target: {}}``; unwraps successfully and pushes execution one
      layer further into normalization.
    - ``unrecognized`` — a populated payload matching no known shape; the only mode
      that reaches the ParseFailureError branch. Added after the first two were
      found to sail past a missing ``ParseFailureError`` import — the exact defect
      this file exists to catch. A smoke that never enters the error branch is
      green for the same reason the old suite was.
    """

    def __init__(self, mode: str):
        self.mode = mode

    def _payload(self, target: str):
        if self.mode == "empty":
            return {}
        if self.mode == "unrecognized":
            return {"알수없는키": "내용이 있는 값", "또다른키": "값"}
        return {target: {}}

    def search(self, target, params):
        return self._payload(target)

    def service(self, target, params):
        return self._payload(target)

    def search_html(self, target, params):
        return self._payload(target)

    def post_text(self, path, params):
        return ""


def _subcommands() -> dict[str, argparse.ArgumentParser]:
    parser = build_parser()
    action = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    return dict(action.choices)


def _argv_for(name: str, sub: argparse.ArgumentParser) -> list[str]:
    argv = [name]
    for action in sub._actions:
        if isinstance(action, argparse._HelpAction):
            continue
        if not action.option_strings:
            argv.append(PLACEHOLDERS.get(action.dest, "x"))
        elif action.required:
            flag = action.option_strings[0]
            argv.extend([flag, PLACEHOLDERS.get(flag, "x")])
    return argv + EXTRA_ARGS.get(name, [])


ALL_COMMANDS = sorted(_subcommands())


@pytest.mark.parametrize("mode", ["empty", "shallow", "unrecognized"])
@pytest.mark.parametrize("command", ALL_COMMANDS)
def test_every_command_dispatches_to_an_envelope(command, mode, capsys):
    sub = _subcommands()[command]
    argv = _argv_for(command, sub)

    # No try/except on purpose. A NameError, AttributeError or TypeError from a
    # half-wired module must fail the test loudly — that is the entire point.
    code = main(argv, api=MolegApi(SmokeSource(mode)))

    out = capsys.readouterr().out
    assert code in VALID_EXIT_CODES, f"{command} ({mode}) returned exit {code}"
    envelope = json.loads(out)  # exactly one JSON document, always
    # A usage error means argparse rejected the argv *this file* built, so
    # dispatch never ran and the case proved nothing. It once passed silently for
    # load-legal-context-bundle, whose query is --query and not positional — the
    # smoke was green while covering nothing.
    assert envelope["kind"] != "usage_error", f"{command} ({mode}): smoke argv is malformed, dispatch never ran"
    assert envelope["command"] in (command, None)
    assert "version" in envelope
    assert isinstance(envelope["ok"], bool)
    if envelope["ok"] is False:
        assert envelope["kind"] in set(CATALOG["kinds"]), f"{command} ({mode}) → unlisted kind {envelope['kind']}"


def test_smoke_covers_every_command_the_parser_offers():
    """Guards the guard: a fixture that silently stops covering things is worse
    than no fixture, because the green suite now asserts something false."""
    assert len(ALL_COMMANDS) >= 28, ALL_COMMANDS
    assert "catalog" in ALL_COMMANDS


# --- catalog / parser / dispatch agreement ---------------------------------------


def _catalog_commands() -> set[str]:
    return {name for group in CATALOG["commands"].values() for name in group}


def _dispatch_commands() -> set[str]:
    # Read the whole module rather than one function: dispatch is a flat
    # `if c == "name"` ladder, but which function holds it is an implementation
    # detail that has already moved once. Pinning the function name made this
    # test fail on a refactor that changed nothing it was meant to protect.
    return set(re.findall(r'c == "([a-z0-9-]+)"', inspect.getsource(sys.modules[_call.__module__])))


def test_catalog_advertises_nothing_the_parser_lacks():
    missing = _catalog_commands() - set(ALL_COMMANDS)
    assert not missing, f"catalog advertises commands the CLI cannot parse: {sorted(missing)}"


def test_parser_offers_nothing_the_catalog_hides():
    # The catalog is how a consumer discovers the surface; an unlisted command is
    # one nobody will ever call.
    undocumented = set(ALL_COMMANDS) - _catalog_commands() - {"catalog"}
    assert not undocumented, f"commands missing from the catalog: {sorted(undocumented)}"


def test_every_parsed_command_has_a_dispatch_branch():
    unreachable = set(ALL_COMMANDS) - _dispatch_commands() - {"catalog"}
    assert not unreachable, f"parsable but never dispatched: {sorted(unreachable)}"


def test_every_dispatch_branch_is_reachable_from_the_parser():
    orphaned = _dispatch_commands() - set(ALL_COMMANDS)
    assert not orphaned, f"dispatch handles commands the parser cannot produce: {sorted(orphaned)}"
