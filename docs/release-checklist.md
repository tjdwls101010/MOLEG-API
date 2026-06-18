# Release Checklist

Use this checklist before publishing MOLEG-API to TestPyPI or PyPI.

## Local Verification

```bash
python -m pytest -m "not live" -q
python -m compileall moleg_api scripts tests -q
git diff --check
```

If `MOLEG_OC` is available:

```bash
python -m pytest -m live -q
```

Run the deterministic scenario audit:

```bash
python scripts/legislative_expert_e2e_audit.py
```

## Build Verification

Install build tools in an isolated environment:

```bash
python -m pip install --upgrade build twine
```

Build and check metadata:

```bash
rm -rf dist
python -m build
python -m twine check dist/*
```

Verify import from the built wheel outside the repository:

```bash
target="$(mktemp -d)"
python -m pip install dist/*.whl --no-deps --target "$target"
cd /tmp
PYTHONPATH="$target" python - <<'PY'
from moleg_api import DeferredLookup, LawIdentity, MolegApi

identity = LawIdentity(law_id="001234", name="테스트법", basis="effective")
assert identity.to_dict()["law_id"] == "001234"
assert DeferredLookup(interface="get_law", query="테스트법", reason="test").to_dict()
assert MolegApi
PY
```

## Publication Order

1. Publish to TestPyPI.
2. Install from TestPyPI in a clean environment.
3. Run the import smoke test.
4. Publish the same version to PyPI.
5. Create a GitHub release and tag.

Do not publish credentials, `.env` files, live payload dumps with secrets, build
artifacts, or local database files.
