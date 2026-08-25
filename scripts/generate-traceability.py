#!/usr/bin/env python3
"""Build requirement traceability only from registered, evidenced test results."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


VALID_RESULTS = {"PASS", "FAIL", "ERROR", "BLOCKED_EXTERNAL", "NOT_RUN"}


def read_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def rows(value, key: str) -> list[dict]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict) and isinstance(value.get(key), list):
        return value[key]
    raise ValueError(f"{key} must be a list")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--results", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    try:
        requirements = rows(read_json(args.manifest), "requirements")
        registered = rows(read_json(args.registry), "tests")
        executed = rows(read_json(args.results), "tests")
        requirement_ids = {str(item.get("id", "")).strip() for item in requirements}
        test_by_id: dict[str, dict] = {}
        for test in registered:
            test_id = str(test.get("id", "")).strip()
            if not test_id or test_id in test_by_id:
                raise ValueError(f"duplicate or empty registered test id: {test_id!r}")
            mapped = [str(item).strip() for item in test.get("requirements", [])]
            unknown_requirements = sorted(set(mapped) - requirement_ids)
            if unknown_requirements:
                raise ValueError(f"test {test_id} maps unknown requirements: {unknown_requirements}")
            test_by_id[test_id] = {**test, "requirements": mapped}

        result_by_id: dict[str, dict] = {}
        for result in executed:
            test_id = str(result.get("id", "")).strip()
            if test_id not in test_by_id:
                raise ValueError(f"unknown test id in results: {test_id}")
            status = str(result.get("status", "")).strip().upper()
            if status not in VALID_RESULTS:
                raise ValueError(f"invalid result status for {test_id}: {status}")
            if status == "PASS" and not str(result.get("evidence", "")).strip():
                raise ValueError(f"PASS result for {test_id} has no evidence")
            result_by_id[test_id] = {**result, "status": status}

        output_rows = []
        unmapped: list[str] = []
        for requirement in requirements:
            requirement_id = str(requirement.get("id", "")).strip()
            mapped_tests = sorted(test_id for test_id, test in test_by_id.items() if requirement_id in test["requirements"])
            if not mapped_tests:
                latest = "NOT_RUN"
                if str(requirement.get("level", "")).upper() in {"MUST", "SHOULD"}:
                    unmapped.append(requirement_id)
            else:
                states = [result_by_id.get(test_id, {}).get("status", "NOT_RUN") for test_id in mapped_tests]
                if any(state in {"FAIL", "ERROR"} for state in states):
                    latest = "FAIL"
                elif states and all(state == "PASS" for state in states):
                    latest = "PASS"
                elif any(state == "BLOCKED_EXTERNAL" for state in states):
                    latest = "BLOCKED_EXTERNAL"
                else:
                    latest = "NOT_RUN"
            output_rows.append(
                {
                    **requirement,
                    "acceptance_test_ids": mapped_tests,
                    "latest_result": latest,
                    "production_acceptance": latest == "PASS",
                    "evidence": [result_by_id[test_id].get("evidence") for test_id in mapped_tests if test_id in result_by_id],
                }
            )

        payload = {
            "schema_version": 2,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "requirements": output_rows,
            "summary": {
                status: sum(row["latest_result"] == status for row in output_rows)
                for status in ("PASS", "FAIL", "BLOCKED_EXTERNAL", "NOT_RUN")
            },
            "unmapped_required": unmapped,
        }
        required_rows = [row for row in output_rows if str(row.get("level", "")).upper() in {"MUST", "SHOULD"}]
        payload["required_summary"] = {
            status: sum(row["latest_result"] == status for row in required_rows)
            for status in ("PASS", "FAIL", "BLOCKED_EXTERNAL", "NOT_RUN")
        }
        payload["production_ready"] = not unmapped and all(row["latest_result"] == "PASS" for row in required_rows)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if args.strict and (unmapped or payload["summary"]["FAIL"] or payload["required_summary"]["NOT_RUN"]):
            raise ValueError(
                f"strict traceability gate failed: unmapped={len(unmapped)} "
                f"fail={payload['summary']['FAIL']} required_not_run={payload['required_summary']['NOT_RUN']}"
            )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"traceability error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
