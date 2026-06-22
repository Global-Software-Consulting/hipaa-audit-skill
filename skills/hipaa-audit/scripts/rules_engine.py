#!/usr/bin/env python3
"""
Evaluate rules.yaml against a merged facts.json. Emit audit.json with
per-category scores, overall score, and verdict.

Verdict thresholds:
  not_compliant       — any must failed OR overall < 60
  partially_compliant — no must failed AND 60 <= overall < 85
  compliant           — no must failed AND overall >= 85
                        AND no critical category < 70
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SEVERITY_WEIGHT = {"must": 3.0, "should": 1.5, "nice": 0.5}
CRITICAL_CATEGORIES = {
    "encryption-at-rest",
    "encryption-in-transit",
    "access-control",
    "audit-logging",
    "phi-in-logs",
    "secrets-mgmt",
}


class Skip(Exception):
    pass


def get_fact(facts: dict, path: str) -> Any:
    parts = path.split(".")
    cur: Any = facts
    for p in parts:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            raise Skip(f"fact {path} missing")
    return cur


def evaluate(check: dict, facts: dict) -> tuple[str, Any]:
    op = check["op"]
    fact_path = check["fact"]
    manual = bool(check.get("manual", False))
    expected = check.get("value")
    try:
        observed = get_fact(facts, fact_path)
    except Skip:
        return ("manual" if manual else "skipped", None)

    if op == "truthy":
        ok = bool(observed)
    elif op == "falsy":
        ok = not bool(observed)
    elif op == "equals":
        ok = observed == expected
    elif op == "not_equals":
        ok = observed != expected
    elif op == "gte":
        ok = (observed or 0) >= expected
    elif op == "lte":
        ok = (observed or 0) <= expected
    elif op == "exists":
        ok = observed is not None
    elif op == "not_exists":
        ok = observed is None
    elif op == "contains":
        ok = expected in (observed or "")
    elif op == "not_contains":
        ok = expected not in (observed or "")
    elif op == "length_eq":
        ok = len(observed or []) == expected
    elif op == "length_at_most":
        ok = len(observed or []) <= expected
    elif op == "any_match":
        ok = any(v in (observed or []) for v in expected)
    elif op == "none_match":
        ok = not any(v in (observed or []) for v in expected)
    else:
        return ("skipped", observed)

    if manual and not ok:
        return ("manual", observed)
    return ("pass" if ok else "fail", observed)


def category_score(cat_findings: list[dict]) -> int:
    total_w = 0.0
    earned_w = 0.0
    for f in cat_findings:
        w = SEVERITY_WEIGHT[f["severity"]]
        total_w += w
        if f["status"] == "pass":
            earned_w += w
        elif f["status"] == "manual":
            earned_w += w * 0.5
    if total_w == 0:
        return 100
    return round((earned_w / total_w) * 100)


def overall_verdict(category_scores: dict[str, int], any_must_failed: bool) -> tuple[str, int]:
    overall = round(sum(category_scores.values()) / max(len(category_scores), 1))
    if any_must_failed or overall < 60:
        return "not_compliant", overall
    crit_low = any(category_scores.get(c, 100) < 70 for c in CRITICAL_CATEGORIES if c in category_scores)
    if overall >= 85 and not crit_low:
        return "compliant", overall
    return "partially_compliant", overall


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--facts", type=Path, required=True)
    parser.add_argument("--rules", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    facts = json.loads(args.facts.read_text())
    rules_path = args.rules
    if rules_path.suffix in (".yaml", ".yml") and not rules_path.exists():
        rules_path = rules_path.with_suffix(".json")
    if rules_path.suffix == ".json":
        rules = json.loads(rules_path.read_text())
    else:
        # try sibling .json
        alt = rules_path.with_suffix(".json")
        if alt.exists():
            rules = json.loads(alt.read_text())
        else:
            print(f"error: only .json rules supported (no pyyaml). Provide {alt}", file=sys.stderr)
            sys.exit(2)

    findings: list[dict] = []
    any_must_failed = False
    summary = {s: {"pass": 0, "fail": 0, "manual": 0, "skipped": 0} for s in SEVERITY_WEIGHT}

    for rule in rules:
        status, observed = evaluate(rule["check"], facts)
        summary[rule["severity"]][status] = summary[rule["severity"]].get(status, 0) + 1
        if rule["severity"] == "must" and status == "fail":
            any_must_failed = True
        ev_samples = []
        cat_samples = facts.get("code", {}).get("samples", {})
        infra_samples = facts.get("infra", {}).get("samples", {})
        for key, val in {**cat_samples, **infra_samples}.items():
            if key in rule["check"].get("fact", ""):
                ev_samples = val[:3]
                break
        findings.append({
            "rule_id": rule["id"],
            "category": rule["category"],
            "severity": rule["severity"],
            "title": rule["title"],
            "status": status,
            "observed": observed,
            "evidence": ev_samples,
            "source_url": rule["source_url"],
            "fix_hint": rule["fix_hint"],
            "rationale": rule["rationale"],
        })

    by_cat: dict[str, list[dict]] = {}
    for f in findings:
        by_cat.setdefault(f["category"], []).append(f)
    cat_scores = {c: category_score(fs) for c, fs in by_cat.items()}

    verdict, overall = overall_verdict(cat_scores, any_must_failed)

    out = {
        "project_path": facts.get("project_path", ""),
        "rules_total": len(rules),
        "verdict": verdict,
        "overall_score": overall,
        "category_scores": cat_scores,
        "summary": summary,
        "any_must_failed": any_must_failed,
        "findings": findings,
        "vendor_matches": facts.get("deps", {}).get("matches", []),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2))
    print(f"rules_engine: {len(rules)} rules → verdict={verdict} score={overall} → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
