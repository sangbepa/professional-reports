"""Shared contracts, validated without domain-specific planning templates."""
from pathlib import Path
from .util import ContractError, read_json


def validate(root, name, value):
    try:
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError as exc:
        raise ContractError("Install pinned requirements before using contracts") from exc
    schema = read_json(Path(root) / "schemas" / f"{name}.schema.json")
    errors = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value),
                    key=lambda e: str(list(e.path)))
    if errors:
        raise ContractError("; ".join(f"{name}.{'.'.join(map(str,e.path))}: {e.message}" for e in errors[:8]))
    return value
