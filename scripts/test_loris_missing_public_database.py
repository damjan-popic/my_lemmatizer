#!/usr/bin/env python3
"""
Smoke-test candidate missing LORIS rules against a running my_lemmatizer/LingHub endpoint.

Usage:
  python3 test_loris_missing_public_database.py \
    loris_missing_public_database_import_candidates.json \
    http://127.0.0.1:8001/loris/check

or through LingHub:
  python3 test_loris_missing_public_database.py \
    loris_missing_public_database_import_candidates.json \
    http://127.0.0.1:8010/nlp/loris-check
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path


def post_json(url: str, payload: dict, timeout: int = 60) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    if len(sys.argv) != 3:
        print(__doc__.strip(), file=sys.stderr)
        raise SystemExit(2)

    candidates_path = Path(sys.argv[1])
    endpoint = sys.argv[2]
    data = json.loads(candidates_path.read_text(encoding="utf-8"))
    rules = data["rules"]

    failures = []
    for rule in rules:
        rid = rule["id"]
        trig = rule["trigger"]
        values = trig.get("lemmas", []) if trig.get("type") == "lemma" else trig.get("forms", [])
        value = values[0]
        text = f"To je testni primer: {value}."
        try:
            out = post_json(endpoint, {"lang": "sl", "text": text})
        except Exception as e:
            failures.append((rid, value, f"request failed: {e}"))
            continue
        found = {x.get("rule_id") for x in out.get("spans", [])} | {x.get("rule_id") for x in out.get("issues", [])}
        if rid not in found:
            failures.append((rid, value, sorted(x for x in found if x)))

    print(f"rules tested: {len(rules)}")
    print(f"failures: {len(failures)}")
    if failures:
        for rid, value, info in failures[:50]:
            print(f"FAIL {rid} / {value!r}: {info}")
        raise SystemExit(1)
    print("OK: all candidate rules were found")


if __name__ == "__main__":
    main()
