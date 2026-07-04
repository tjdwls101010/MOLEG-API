"""Law hierarchy normalization."""

from __future__ import annotations

from typing import Any, Literal

from moleg_api.errors import ParseFailureError
from moleg_api.models import LawIdentity, LawStructure, LawStructureNode

from .identities import normalize_administrative_rule_identity, normalize_law_identity
from .primitives import first_value, string_or_none

def normalize_law_structure(raw_structure: dict[str, Any], *, max_depth: int = 0) -> LawStructure:
    if not isinstance(raw_structure, dict):
        raise ParseFailureError("Law structure payload must be an object")
    root_info = raw_structure.get("기본정보")
    if not isinstance(root_info, dict):
        raise ParseFailureError("Law structure payload is missing 기본정보")
    hierarchy = raw_structure.get("상하위법")
    if hierarchy in (None, ""):
        hierarchy = {}
    if not isinstance(hierarchy, dict):
        raise ParseFailureError("Law structure 상하위법 must be an object")

    root_identity = normalize_law_identity(root_info, basis="effective")
    root_node = structure_root_node(hierarchy, root_identity)
    instruments = law_structure_children(root_node, depth_remaining=max_depth)
    return LawStructure(identity=root_identity, instruments=instruments, raw=raw_structure)


def structure_root_node(hierarchy: dict[str, Any], root_identity: LawIdentity) -> dict[str, Any]:
    for value in hierarchy.values():
        for node in structure_node_values(value):
            info = node.get("기본정보") if isinstance(node, dict) else None
            if isinstance(info, dict):
                identity = normalize_law_identity(info, basis="effective")
                if (
                    identity.law_id == root_identity.law_id
                    or identity.mst == root_identity.mst
                    or identity.name == root_identity.name
                ):
                    return node
    for value in hierarchy.values():
        for node in structure_node_values(value):
            if isinstance(node, dict) and isinstance(node.get("기본정보"), dict):
                return node
    return {}


def law_structure_children(container: dict[str, Any], *, depth_remaining: int) -> list[LawStructureNode]:
    if not isinstance(container, dict):
        raise ParseFailureError("Law structure node must be an object")
    children: list[LawStructureNode] = []
    for key, value in container.items():
        if key in {"기본정보", "자치법규"}:
            continue
        if key in {"시행령", "시행규칙", "법률"}:
            children.extend(law_structure_law_nodes(value, key, depth_remaining=depth_remaining))
        elif key == "행정규칙":
            children.extend(law_structure_administrative_nodes(value))
    return children


def law_structure_law_nodes(value: Any, key: str, *, depth_remaining: int) -> list[LawStructureNode]:
    nodes: list[LawStructureNode] = []
    for node in structure_node_values(value):
        info = node.get("기본정보")
        if not isinstance(info, dict):
            raise ParseFailureError(f"Law structure {key} node is missing 기본정보")
        identity = normalize_law_identity(info, basis="effective")
        children = law_structure_children(node, depth_remaining=depth_remaining - 1) if depth_remaining > 0 else []
        nodes.append(
            LawStructureNode(
                name=identity.name,
                source_type="law",
                instrument_type=instrument_type_for_law_node(key, identity.law_type),
                law_id=identity.law_id,
                mst=identity.mst,
                law_type=identity.law_type,
                effective_date=identity.effective_date,
                promulgation_date=identity.promulgation_date,
                promulgation_number=identity.promulgation_number,
                ministry=identity.ministry,
                detail_link=string_or_none(first_value(info, "본문상세링크", "법령상세링크")),
                children=children,
                raw=node,
            )
        )
    return nodes


def law_structure_administrative_nodes(value: Any) -> list[LawStructureNode]:
    if value in (None, ""):
        return []
    if not isinstance(value, dict):
        raise ParseFailureError("Law structure 행정규칙 must be an object")
    nodes: list[LawStructureNode] = []
    for rule_type, rule_value in value.items():
        for node in structure_node_values(rule_value):
            info = node.get("기본정보")
            if not isinstance(info, dict):
                raise ParseFailureError(f"Law structure {rule_type} node is missing 기본정보")
            identity = normalize_administrative_rule_identity(info)
            nodes.append(
                LawStructureNode(
                    name=identity.name,
                    source_type="administrative_rule",
                    instrument_type=instrument_type_for_admin_rule(rule_type),
                    serial_id=identity.serial_id,
                    rule_id=identity.rule_id,
                    law_type=identity.rule_type,
                    effective_date=identity.effective_date,
                    issuing_date=identity.issuing_date,
                    issuing_number=identity.issuing_number,
                    ministry=identity.ministry,
                    detail_link=string_or_none(first_value(info, "본문상세링크", "행정규칙 상세링크")),
                    raw=node,
                )
            )
    return nodes


def structure_node_values(value: Any) -> list[dict[str, Any]]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        if not all(isinstance(item, dict) for item in value):
            raise ParseFailureError("Law structure node list contains non-object entries")
        return value
    if isinstance(value, dict):
        if "기본정보" in value:
            return [value]
        nodes: list[dict[str, Any]] = []
        for child in value.values():
            nodes.extend(structure_node_values(child))
        return nodes
    raise ParseFailureError("Law structure node must be an object or list")


def instrument_type_for_law_node(key: str, law_type: str | None) -> str:
    if key == "시행령":
        return "enforcement_decree"
    if key == "시행규칙":
        return "enforcement_rule"
    if key == "법률":
        return "related_law"
    if law_type:
        return law_type
    return key


def instrument_type_for_admin_rule(rule_type: str) -> str:
    return {
        "고시": "notice",
        "훈령": "directive",
        "예규": "established_rule",
    }.get(rule_type, rule_type)
