# Installation

MOLEG-API is a task-level Python interface for loading Korean legal sources from [law.go.kr](https://www.law.go.kr/). This page covers installing the package, the OC credential it uses to call law.go.kr, and the editable install used for development.

## Requirements

- Python **3.10 or newer**.
- No third-party runtime dependencies. The package uses only the Python standard library, so a plain `pip install` pulls in nothing else.

## Install with pip

```bash
pip install moleg-api
```

The distribution name is `moleg-api`; the import name is `moleg_api`:

```python
import moleg_api
from moleg_api import MolegApi

api = MolegApi()
```

Installing the package also registers a `moleg` console command, so every method is available from a shell without writing Python:

```bash
moleg catalog                          # self-documenting entry point
moleg search-laws "주택임대차보호법"     # → candidates with law_id, mst
```

You can also invoke the CLI as a module, which is convenient from a checkout:

```bash
python -m moleg_api catalog
```

## The OC credential

Live law.go.kr calls use an OpenAPI credential called the **OC** — a law.go.kr account's email id. It is **free** and **not a secret** (it travels as a plain query parameter on every request).

The package ships with a shared default OC, so calls work **out of the box with no registration and no configuration**:

```bash
moleg search-laws "자동차관리법" --display 2
```

The shared default funnels all traffic through one credential and can hit law.go.kr rate limits. If you call the API heavily, register your own OC at law.go.kr and set it.

### Setting your own OC

Export it as an environment variable:

```bash
export MOLEG_OC="your-law-go-kr-oc"
```

`MOLEG_OC` is also read from a local `.env.local` or `.env` file in the current working directory (a plain `MOLEG_OC=your-oc` line). This lets the CLI pick up your OC without exporting it in every shell.

From Python, pass your OC explicitly by constructing a client and handing it to `MolegApi`:

```python
from moleg_api import MolegApi, LawGoKrClient

api = MolegApi(source=LawGoKrClient(oc="your-law-go-kr-oc"))
```

The CLI has no `--oc` flag; it takes the OC from `MOLEG_OC` (environment or a local `.env`/`.env.local`), falling back to the bundled default.

### Resolution order

When a client resolves the OC to use, it takes the **first** of these that is set:

1. The `oc=` argument to `LawGoKrClient` (Python only).
2. `MOLEG_OC`, read from the environment, then from `.env.local`, then from `.env` in the current working directory.
3. The bundled shared default.

So an explicit `oc=` always wins over the environment, and any `MOLEG_OC` value wins over the default.

## Development install

To work on the package from a checkout, install it in editable mode with the test extras:

```bash
pip install -e ".[test]"
```

The `test` extra adds `pytest`. Run the suite from the repository root:

```bash
pytest
```

Tests that call live law.go.kr endpoints are marked `live` and are skipped by default; a `dev` extra is also available for the fuller development toolchain.

## Next steps

- [Quickstart](Quickstart.md) — first search-then-load calls in Python and the CLI.
- [CLI](CLI-Reference.md) — the JSON envelope contract, exit codes, and the search→load discipline.
