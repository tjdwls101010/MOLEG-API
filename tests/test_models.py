import json
import re
from dataclasses import is_dataclass
from pathlib import Path
from typing import get_args, get_type_hints

import moleg_api
import moleg_api.models as models
from moleg_api import (
    Ambiguity,
    ArticleText,
    BundleRequest,
    CandidateContext,
    ContextGap,
    DeferredLookup,
    LawHit,
    LawIdentity,
    LawText,
    LegalContextBundle,
    LoadedContext,
)


def test_public_model_types_are_exported_from_package_root():
    public_model_names = {
        name
        for name in vars(models)
        if name[:1].isupper() and name not in {"Any", "Literal"}
    }

    assert "Basis" in public_model_names
    missing_exports = sorted(name for name in public_model_names if name not in moleg_api.__all__)

    assert missing_exports == []


def test_package_root_all_names_are_bound():
    missing_names = sorted(name for name in moleg_api.__all__ if not hasattr(moleg_api, name))

    assert missing_names == []


def test_pyproject_dev_extra_covers_requirements_dev():
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    requirements = {
        line.strip()
        for line in Path("requirements-dev.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    dev_section = re.search(r"^dev = \[(.*?)^\]", pyproject, re.MULTILINE | re.DOTALL)

    assert dev_section is not None
    dev_dependencies = set(re.findall(r'"([^"]+)"', dev_section.group(1)))
    assert requirements <= dev_dependencies


def test_bundle_request_mode_covers_returned_bundle_modes_without_widening_call_mode():
    assert set(get_args(models.BundleMode)) == {
        "question",
        "promulgated_bill",
        "statute_review",
    }
    assert set(get_args(models.BundleRequestMode)) == {
        "question",
        "promulgated_bill",
        "statute_review",
        "institutional_system",
    }
    assert get_type_hints(models.BundleRequest)["budget"] == models.BundleBudget


def test_all_public_dataclasses_have_serialization_methods():
    model_classes = [
        value
        for value in vars(models).values()
        if isinstance(value, type) and value.__module__ == models.__name__ and is_dataclass(value)
    ]

    assert model_classes
    assert all(callable(getattr(model_class, "to_dict", None)) for model_class in model_classes)
    assert all(callable(getattr(model_class, "to_json_string", None)) for model_class in model_classes)


def test_to_dict_serializes_nested_dataclasses_without_raw_by_default():
    identity = LawIdentity(
        law_id="014152",
        name="기후위기 대응을 위한 탄소중립ㆍ녹색성장 기본법",
        basis="effective",
        mst="261457",
        raw_keys={"법령ID": "014152"},
    )
    article = ArticleText(
        identity=identity,
        article="제1조",
        title="목적",
        text="탄소중립 목적",
        raw={"source": "article-payload"},
    )
    law = LawText(identity=identity, articles=[article], raw={"source": "law-payload"})

    data = law.to_dict()

    assert data == {
        "identity": {
            "law_id": "014152",
            "name": "기후위기 대응을 위한 탄소중립ㆍ녹색성장 기본법",
            "basis": "effective",
            "mst": "261457",
            "lid": None,
            "promulgation_date": None,
            "effective_date": None,
            "promulgation_number": None,
            "law_type": None,
            "ministry": None,
            "raw_keys": {"법령ID": "014152"},
        },
        "articles": [
            {
                "identity": {
                    "law_id": "014152",
                    "name": "기후위기 대응을 위한 탄소중립ㆍ녹색성장 기본법",
                    "basis": "effective",
                    "mst": "261457",
                    "lid": None,
                    "promulgation_date": None,
                    "effective_date": None,
                    "promulgation_number": None,
                    "law_type": None,
                    "ministry": None,
                    "raw_keys": {"법령ID": "014152"},
                },
                "article": "제1조",
                "text": "탄소중립 목적",
                "title": "목적",
                "effective_date": None,
            }
        ],
    }


def test_to_dict_can_include_raw_recursively():
    identity = LawIdentity(law_id="014152", name="탄소중립법", basis="effective")
    article = ArticleText(
        identity=identity,
        article="제1조",
        text="목적",
        raw={"조문번호": "1"},
    )
    law = LawText(identity=identity, articles=[article], raw={"법령ID": "014152"})

    data = law.to_dict(include_raw=True)

    assert data["raw"] == {"법령ID": "014152"}
    assert data["articles"][0]["raw"] == {"조문번호": "1"}


def test_to_dict_serializes_full_context_bundle_graph():
    identity = LawIdentity(law_id="014152", name="탄소중립법", basis="effective")
    hit = LawHit(identity=identity, raw={"source": "candidate"})
    law = LawText(
        identity=identity,
        articles=[ArticleText(identity=identity, article="제1조", text="목적")],
        raw={"source": "loaded"},
    )
    bundle = LegalContextBundle(
        request=BundleRequest(
            query="탄소중립",
            mode="question",
            budget="minimal",
            promulgation_bridge={"prom_no": "1"},
        ),
        loaded=LoadedContext(laws=[law]),
        candidates=CandidateContext(laws=[identity]),
        deferred=[
            DeferredLookup(
                interface="get_law",
                query="탄소중립법",
                reason="Load full text",
                filters={"basis": "effective"},
            )
        ],
        ambiguities=[Ambiguity(kind="law_name", message="ambiguous", candidates=[hit])],
        gaps=[
            ContextGap(
                kind="websearch_required",
                reason="Latest statistics are outside MOLEG.",
                query="탄소중립 통계",
                recommended_interface="websearch",
            )
        ],
        source_notes=["candidate only"],
    )

    data = bundle.to_dict()

    assert data["request"]["promulgation_bridge"] == {"prom_no": "1"}
    assert data["loaded"]["laws"][0]["articles"][0]["article"] == "제1조"
    assert data["candidates"]["laws"][0]["name"] == "탄소중립법"
    assert data["deferred"][0]["filters"] == {"basis": "effective"}
    assert data["ambiguities"][0]["candidates"][0]["identity"]["law_id"] == "014152"
    assert "raw" not in data["loaded"]["laws"][0]
    assert "raw" not in data["ambiguities"][0]["candidates"][0]


def test_to_json_string_returns_deterministic_json_without_escaping_korean():
    identity = LawIdentity(law_id="014152", name="탄소중립법", basis="effective")
    payload = identity.to_json_string()

    assert json.loads(payload) == identity.to_dict()
    assert "탄소중립법" in payload
    assert payload == identity.to_json_string()
