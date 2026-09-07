"""Derive an OpenAI Structured Outputs json_schema from Pydantic models."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from pydantic import BaseModel


def openai_json_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Pydantic schema rewritten for Responses API `strict: true`.

    Every object gets `additionalProperties: false` and every property is
    listed in `required`. Fields that were optional become anyOf + null.
    """
    raw = model.model_json_schema()
    defs = raw.pop("$defs", {})
    inlined = _inline_refs(raw, defs)
    return _strictify(inlined)


def _inline_refs(node: Any, defs: dict[str, Any]) -> Any:
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/$defs/"):
            name = ref.split("/")[-1]
            return _inline_refs(deepcopy(defs[name]), defs)
        return {key: _inline_refs(value, defs) for key, value in node.items()}
    if isinstance(node, list):
        return [_inline_refs(item, defs) for item in node]
    return node


def _already_nullable(spec: Any) -> bool:
    if not isinstance(spec, dict):
        return False
    if spec.get("type") == "null":
        return True
    variants = spec.get("anyOf") or spec.get("oneOf") or []
    return any(
        isinstance(item, dict) and item.get("type") == "null" for item in variants
    )


def _as_nullable(spec: Any) -> dict[str, Any]:
    if _already_nullable(spec):
        return spec if isinstance(spec, dict) else {"anyOf": [spec, {"type": "null"}]}
    return {"anyOf": [spec, {"type": "null"}]}


def _strictify(node: Any) -> Any:
    if isinstance(node, list):
        return [_strictify(item) for item in node]
    if not isinstance(node, dict):
        return node

    cleaned = {
        key: value
        for key, value in node.items()
        if key not in {"title", "description", "default", "examples"}
    }

    if "anyOf" in cleaned:
        cleaned["anyOf"] = [_strictify(item) for item in cleaned["anyOf"]]
    if "oneOf" in cleaned:
        cleaned["oneOf"] = [_strictify(item) for item in cleaned["oneOf"]]
    if "items" in cleaned:
        cleaned["items"] = _strictify(cleaned["items"])

    if cleaned.get("type") == "object" or "properties" in cleaned:
        original_required = set(cleaned.get("required") or [])
        props = {
            name: _strictify(spec)
            for name, spec in (cleaned.get("properties") or {}).items()
        }
        for name, spec in list(props.items()):
            if name not in original_required:
                props[name] = _as_nullable(spec)
        cleaned["properties"] = props
        cleaned["type"] = "object"
        cleaned["additionalProperties"] = False
        cleaned["required"] = list(props.keys())

    return cleaned
