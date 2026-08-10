#!/usr/bin/env python
"""Regenerate ``openapi/openapi.yaml`` from the live FastAPI application.

The static contract is the document the frontend generates its types from, so it must never
drift from the running API. This script rewrites every implemented operation from the runtime
schema and preserves the hand-written ``x-status: planned`` operations that have no runtime
counterpart yet.

Usage::

    python scripts/sync_openapi.py           # rewrite the contract
    python scripts/sync_openapi.py --check   # fail when the contract is out of date
"""

from __future__ import annotations

import argparse
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.main import create_app  # noqa: E402

OPENAPI_PATH = ROOT / "openapi" / "openapi.yaml"
HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


def operations(document: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (path, method): operation
        for path, path_item in document.get("paths", {}).items()
        for method, operation in path_item.items()
        if method in HTTP_METHODS
    }


def collect_refs(value: Any, found: set[str]) -> None:
    if isinstance(value, dict):
        reference = value.get("$ref")
        if isinstance(reference, str) and reference.startswith("#/components/"):
            found.add(reference.removeprefix("#/components/"))
        for child in value.values():
            collect_refs(child, found)
    elif isinstance(value, list):
        for child in value:
            collect_refs(child, found)


def prune_components(document: dict[str, Any]) -> None:
    """Drop component entries that nothing references any more.

    Planned operations are regularly promoted to implemented ones, which orphans the schemas
    that were written for them by hand. Without pruning the contract would only ever grow.
    """
    components: dict[str, Any] = document.get("components", {})
    keep: set[str] = set()
    collect_refs(document.get("paths", {}), keep)

    # Follow references between components until the reachable set stops growing.
    while True:
        pending: set[str] = set()
        for key in keep:
            section, _, name = key.partition("/")
            entry = components.get(section, {}).get(name)
            if entry is not None:
                collect_refs(entry, pending)
        if pending <= keep:
            break
        keep |= pending

    for section, entries in list(components.items()):
        if section == "securitySchemes":
            continue
        for name in list(entries):
            if f"{section}/{name}" not in keep:
                del entries[name]
        if not entries:
            del components[section]


def build(existing: dict[str, Any], runtime: dict[str, Any]) -> dict[str, Any]:
    document = deepcopy(existing)
    runtime_operations = operations(runtime)

    planned = {
        key: operation
        for key, operation in operations(existing).items()
        if operation.get("x-status") == "planned" and key not in runtime_operations
    }

    paths: dict[str, Any] = {}
    for (path, method), operation in runtime_operations.items():
        implemented = deepcopy(operation)
        implemented["x-status"] = "implemented"
        paths.setdefault(path, {})[method] = implemented
    for (path, method), operation in planned.items():
        paths.setdefault(path, {})[method] = deepcopy(operation)

    document["paths"] = paths

    components = document.setdefault("components", {})
    for section, runtime_section in runtime.get("components", {}).items():
        components.setdefault(section, {}).update(deepcopy(runtime_section))

    prune_components(document)
    return document


def dump(document: dict[str, Any]) -> str:
    return yaml.safe_dump(document, allow_unicode=True, sort_keys=False, width=110)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit non-zero when out of date")
    arguments = parser.parse_args()

    existing = yaml.safe_load(OPENAPI_PATH.read_text(encoding="utf-8"))
    rendered = dump(build(existing, create_app().openapi()))

    if arguments.check:
        if OPENAPI_PATH.read_text(encoding="utf-8") != rendered:
            print("openapi.yaml is out of date; run python scripts/sync_openapi.py")
            return 1
        print("openapi.yaml is up to date")
        return 0

    OPENAPI_PATH.write_text(rendered, encoding="utf-8")
    print(f"wrote {OPENAPI_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
