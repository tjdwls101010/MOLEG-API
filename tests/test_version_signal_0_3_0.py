"""Tests for the version signal added in 0.3.0 (WI-P2).

Before this, nothing in the package identified itself: no `__version__`, no field
on the envelope. A consumer holding a response could not tell whether an absent
field meant "this release doesn't support it" or "the call went wrong", and a
checkout on sys.path silently answered in place of the installed release with no
way to notice. The version has to ride on the envelope, because that is the only
artifact a consumer actually sees.
"""

import json
import tomllib
from pathlib import Path

import moleg_api
from moleg_api._version import __version__
from moleg_api.cli import main


class StubApi:
    def __init__(self, *, exc=None, result=None):
        self.exc = exc
        self.result = result

    def __getattr__(self, _name):
        def call(*_args, **_kwargs):
            if self.exc is not None:
                raise self.exc
            return self.result

        return call


def test_package_exposes_version():
    assert moleg_api.__version__ == __version__
    assert "__version__" in moleg_api.__all__


def test_version_is_a_release_string():
    parts = __version__.split(".")
    assert len(parts) == 3 and all(part.isdigit() for part in parts), __version__


def test_pyproject_reads_the_version_from_the_package():
    """Guards the single source of truth.

    A literal duplicated in pyproject.toml drifts the moment one side is bumped
    and the other is forgotten — and the resulting wheel reports a version its own
    code disagrees with.
    """
    pyproject = tomllib.loads(Path(__file__).resolve().parents[1].joinpath("pyproject.toml").read_text())
    assert "version" in pyproject["project"].get("dynamic", []), "version must stay dynamic"
    assert pyproject["project"].get("version") is None, "a static version would shadow the package literal"
    assert pyproject["tool"]["setuptools"]["dynamic"]["version"] == {"attr": "moleg_api._version.__version__"}


def test_catalog_envelope_carries_version(capsys):
    code = main(["catalog"], api=StubApi())
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["version"] == __version__


def test_error_envelope_carries_version(capsys):
    from moleg_api.errors import NoResultError

    code = main(["get-law", "--law", "999999"], api=StubApi(exc=NoResultError("no law text")))
    out = json.loads(capsys.readouterr().out)
    assert code == 4
    assert out["version"] == __version__


def test_success_envelope_carries_version(capsys):
    from moleg_api.models import LawIdentity, LawText

    law = LawText(identity=LawIdentity(law_id="011357", name="개인정보 보호법", basis="effective"), articles=[])
    code = main(["get-law", "--law", "011357"], api=StubApi(result=law))
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["version"] == __version__


def test_version_sits_next_to_command_for_readability(capsys):
    main(["catalog"], api=StubApi())
    out = json.loads(capsys.readouterr().out)
    keys = list(out)
    assert keys.index("version") == keys.index("command") + 1


def test_usage_error_before_a_command_is_parsed_still_carries_version(capsys):
    # command is None here, so the "after command" insertion point does not exist —
    # the fallback has to cover it or the earliest failures ship unidentified.
    code = main(["search-laws", "x", "--nope"], api=StubApi())
    out = json.loads(capsys.readouterr().out)
    assert code == 5
    assert out["version"] == __version__
