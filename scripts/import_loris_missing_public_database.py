#!/usr/bin/env python3
"""
Import the broader/public Kaj zna Loris missing entries into loris_rules_final.json.

Usage:
  python3 import_loris_missing_public_database.py \
    /path/to/loris_rules_final.json \
    /path/to/loris_missing_public_database_import_candidates.json

Behavior:
- Creates a timestamped backup of loris_rules_final.json.
- Upserts by rule id: existing IDs are updated, new IDs are appended.
- Strips internal _import metadata before writing the runtime JSON.
- Writes an audit report next to loris_rules_final.json.
- Fails if the resulting JSON has duplicate rule IDs.
"""

from __future__ import annotations

import copy
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def die(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(code)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        die(f"File not found: {path}")
    except json.JSONDecodeError as e:
        die(f"Invalid JSON in {path}: {e}")


def norm(s: str) -> str:
    return " ".join((s or "").strip().split()).casefold()


def runtime_rule(rule: dict[str, Any]) -> dict[str, Any]:
    """Remove importer-only metadata before writing loris_rules_final.json."""
    r = copy.deepcopy(rule)
    r.pop("_import", None)
    return r


def trigger_values(rule: dict[str, Any]) -> list[str]:
    trig = rule.get("trigger", {})
    if trig.get("type") == "lemma":
        return list(trig.get("lemmas", []) or [])
    return list(trig.get("forms", []) or [])


def main() -> None:
    if len(sys.argv) != 3:
        die(__doc__.strip(), 2)

    rules_path = Path(sys.argv[1]).resolve()
    candidates_path = Path(sys.argv[2]).resolve()

    data = load_json(rules_path)
    if not isinstance(data, dict) or not isinstance(data.get("rules"), list):
        die(f"Expected {rules_path} to be a dict with a 'rules' list")

    cand_data = load_json(candidates_path)
    candidates = cand_data.get("rules") if isinstance(cand_data, dict) else cand_data
    if not isinstance(candidates, list):
        die(f"Expected {candidates_path} to contain a 'rules' list")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = rules_path.with_name(f"{rules_path.stem}.before_missing_public_import_{ts}{rules_path.suffix}")
    shutil.copy2(rules_path, backup_path)

    rules: list[dict[str, Any]] = data["rules"]
    before_count = len(rules)
    by_id = {r.get("id"): i for i, r in enumerate(rules)}
    before_ids = [r.get("id") for r in rules]
    if len(before_ids) != len(set(before_ids)):
        die("Target JSON already contains duplicate rule IDs; aborting before import")

    # Existing trigger index for warnings only.
    existing_trigger_index: dict[tuple[str, str], list[str]] = {}
    for r in rules:
        trig = r.get("trigger", {})
        ttype = trig.get("type")
        for value in trigger_values(r):
            existing_trigger_index.setdefault((ttype, norm(value)), []).append(r.get("id", ""))

    added: list[str] = []
    updated: list[str] = []
    warnings: list[str] = []

    for candidate in candidates:
        if not isinstance(candidate, dict):
            die(f"Candidate is not an object: {candidate!r}")
        rid = candidate.get("id")
        if not rid:
            die(f"Candidate without id: {candidate!r}")

        clean = runtime_rule(candidate)
        trig = clean.get("trigger", {})
        ttype = trig.get("type")
        if ttype not in {"lemma", "surface", "surface_name"}:
            die(f"Unsupported trigger type for {rid}: {ttype!r}")

        values = trigger_values(clean)
        if not values:
            die(f"No trigger values for {rid}")

        # Warn about trigger collisions with other existing IDs.
        for value in values:
            for existing_id in existing_trigger_index.get((ttype, norm(value)), []):
                if existing_id != rid:
                    warnings.append(
                        f"Trigger collision: candidate {rid} uses {ttype}:{value!r}, already used by {existing_id}"
                    )

        if rid in by_id:
            rules[by_id[rid]] = clean
            updated.append(rid)
        else:
            by_id[rid] = len(rules)
            rules.append(clean)
            added.append(rid)
            for value in values:
                existing_trigger_index.setdefault((ttype, norm(value)), []).append(rid)

    after_ids = [r.get("id") for r in rules]
    duplicate_count = len(after_ids) - len(set(after_ids))
    if duplicate_count:
        # Restore backup before failing.
        shutil.copy2(backup_path, rules_path)
        die(f"Import produced {duplicate_count} duplicate rule IDs; restored backup")

    rules_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "timestamp": ts,
        "target": str(rules_path),
        "candidate_file": str(candidates_path),
        "backup": str(backup_path),
        "before_count": before_count,
        "candidate_count": len(candidates),
        "added_count": len(added),
        "updated_count": len(updated),
        "after_count": len(rules),
        "duplicate_rule_ids": duplicate_count,
        "added": added,
        "updated": updated,
        "warnings": warnings,
    }
    report_path = rules_path.with_name(f"loris_missing_public_import_report_{ts}.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("OK: import complete")
    print(f"Target: {rules_path}")
    print(f"Backup: {backup_path}")
    print(f"Report: {report_path}")
    print(f"Before: {before_count}")
    print(f"Candidates: {len(candidates)}")
    print(f"Added: {len(added)}")
    print(f"Updated: {len(updated)}")
    print(f"After: {len(rules)}")
    if warnings:
        print(f"Warnings: {len(warnings)}")
        for w in warnings[:20]:
            print(f"- {w}")
        if len(warnings) > 20:
            print(f"... {len(warnings) - 20} more warnings in report")


if __name__ == "__main__":
    main()
