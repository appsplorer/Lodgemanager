#!/usr/bin/env python3
"""Execute dependency-free QA test functions and emit machine-readable evidence."""

from __future__ import annotations

import argparse
import importlib.util
import inspect
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path


def test_files(inputs: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in inputs:
        path = Path(raw).resolve()
        if path.is_dir():
            files.extend(sorted(path.glob("test_*.py")))
        elif path.is_file():
            files.append(path)
        else:
            raise FileNotFoundError(raw)
    return list(dict.fromkeys(files))


def load_module(path: Path, index: int):
    name = f"lodgeflow_source_test_{index}_{path.stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_function(function, path: Path) -> dict[str, object]:
    test_id = getattr(function, "requirement_test_id", function.__name__)
    base = {
        "id": test_id,
        "name": function.__name__,
        "file": str(path),
        "requirements": list(getattr(function, "requirement_ids", ())),
        "kind": getattr(function, "evidence_kind", "source-runtime"),
        "evidence": str(path),
    }
    try:
        function()
    except AssertionError as exc:
        return {**base, "status": "FAIL", "detail": str(exc) or "assertion failed"}
    except Exception as exc:  # dependency/import errors are distinct from assertion failures
        return {
            **base,
            "status": "ERROR",
            "detail": f"{type(exc).__name__}: {exc}",
            "traceback": "".join(traceback.format_exception(exc))[-4000:],
        }
    return {**base, "status": "PASS", "detail": ""}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", help="Test file(s) or directories")
    parser.add_argument("--output", default="qa/latest-test-results.json")
    args = parser.parse_args()

    results: list[dict[str, object]] = []
    try:
        files = test_files(args.inputs)
        for index, path in enumerate(files):
            module = load_module(path, index)
            functions = [
                value
                for name, value in inspect.getmembers(module, inspect.isfunction)
                if name.startswith("test_") and value.__module__ == module.__name__
            ]
            for function in functions:
                if inspect.signature(function).parameters:
                    results.append(
                        {
                            "id": getattr(function, "requirement_test_id", function.__name__),
                            "name": function.__name__,
                            "file": str(path),
                            "status": "ERROR",
                            "detail": "source test functions must not require fixtures",
                            "requirements": list(getattr(function, "requirement_ids", ())),
                            "kind": getattr(function, "evidence_kind", "source-runtime"),
                            "evidence": str(path),
                        }
                    )
                else:
                    results.append(run_function(function, path))
    except Exception as exc:
        print(f"source test runner error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    summary = {
        "passed": sum(row["status"] == "PASS" for row in results),
        "failed": sum(row["status"] == "FAIL" for row in results),
        "errors": sum(row["status"] == "ERROR" for row in results),
        "total": len(results),
    }
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "tests": results,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for row in results:
        print(f"{row['status']:5} {row['name']}")
    print(f"passed={summary['passed']} failed={summary['failed']} errors={summary['errors']} total={summary['total']}")
    return 0 if summary["failed"] == 0 and summary["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
