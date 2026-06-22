#!/usr/bin/env python3
"""
Merge auto-scan audit.json with interview.json (off-code answers) into a final
unified audit. Adds interview findings as additional "findings" with severity,
status, and category — they participate in the same scoring + report.

Status mapping for interview answers:
  yes              → pass
  no               → fail
  partial          → fail (low confidence) — counted as fail, flagged in report
  unknown / skip   → manual
  enum values:
    never / none   → fail
    on_incident    → fail (insufficient cadence)
    annually       → pass (default acceptable)
    quarterly / monthly / daily / weekly / realtime_alerts → pass
  date answer:
    within last 12mo → pass
    older            → fail (stale)
    missing          → manual
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path


PASS_ENUMS = {"annually", "quarterly", "monthly", "daily", "weekly", "realtime_alerts",
              "safe_harbor", "expert_determination", "limited_data_set"}
FAIL_ENUMS = {"never", "none", "on_incident"}


def parse_date(s: str):
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d-%m-%Y", "%Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


def map_status(q: dict, ans: dict) -> str:
    a = (ans.get("answer") or "").strip().lower()
    if a in ("skip", "unknown", "n/a", ""):
        return "manual"

    accept = q.get("accept", "")
    if accept in ("yes_no", "yes_no_partial"):
        if a == "yes":
            return "pass"
        if a == "partial":
            return "fail"  # partial = not adequate
        return "fail"

    if accept.startswith("enum:"):
        if a in PASS_ENUMS:
            return "pass"
        if a in FAIL_ENUMS:
            return "fail"
        return "manual"

    if accept == "date":
        d = parse_date(a)
        if not d:
            return "manual"
        if (date.today() - d) <= timedelta(days=400):
            return "pass"
        return "fail"

    return "manual"


def make_finding(q: dict, ans: dict) -> dict:
    status = map_status(q, ans)
    fix = ans.get("note") or ""
    title = q.get("title") or q.get("prompt") or q["id"]
    return {
        "rule_id": f"interview.{q['id']}",
        "category": q["category"],
        "severity": q["severity"],
        "title": title,
        "status": status,
        "observed": ans.get("answer", ""),
        "evidence": [ans.get("evidence")] if ans.get("evidence") else [],
        "source_url": q.get("source_url", "https://www.hhs.gov/hipaa/for-professionals/security/laws-regulations/index.html"),
        "fix_hint": fix or f"Document and produce evidence for: {q['prompt']}",
        "rationale": "Off-code HIPAA obligation captured by interview (not detectable by static scan).",
        "_interview": True,
    }


SEVERITY_WEIGHT = {"must": 3.0, "should": 1.5, "nice": 0.5}
CRITICAL_CATEGORIES = {
    "encryption-at-rest", "encryption-in-transit", "access-control",
    "audit-logging", "phi-in-logs", "secrets-mgmt",
}


def rescore(audit: dict) -> None:
    findings = audit["findings"]
    summary = {s: {"pass": 0, "fail": 0, "manual": 0, "skipped": 0} for s in SEVERITY_WEIGHT}
    any_must_failed = False
    by_cat: dict[str, list[dict]] = {}
    for f in findings:
        sev = f["severity"]
        st = f["status"]
        summary[sev][st] = summary[sev].get(st, 0) + 1
        if sev == "must" and st == "fail":
            any_must_failed = True
        by_cat.setdefault(f["category"], []).append(f)

    cat_scores: dict[str, int] = {}
    for cat, fs in by_cat.items():
        total_w = 0.0
        earned_w = 0.0
        for f in fs:
            w = SEVERITY_WEIGHT[f["severity"]]
            total_w += w
            if f["status"] == "pass":
                earned_w += w
            elif f["status"] == "manual":
                earned_w += w * 0.5
        cat_scores[cat] = round((earned_w / total_w) * 100) if total_w else 100

    overall = round(sum(cat_scores.values()) / max(len(cat_scores), 1))
    crit_low = any(cat_scores.get(c, 100) < 70 for c in CRITICAL_CATEGORIES if c in cat_scores)
    if any_must_failed or overall < 60:
        verdict = "not_compliant"
    elif overall >= 85 and not crit_low:
        verdict = "compliant"
    else:
        verdict = "partially_compliant"

    audit["summary"] = summary
    audit["any_must_failed"] = any_must_failed
    audit["category_scores"] = cat_scores
    audit["overall_score"] = overall
    audit["verdict"] = verdict
    audit["rules_total"] = len(findings)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, required=True, help="audit.json from rules_engine")
    parser.add_argument("--interview-answers", type=Path, required=True, help="interview answers JSON")
    parser.add_argument("--interview-schema", type=Path, required=True, help="interview.json schema (questions definition)")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    audit = json.loads(args.audit.read_text())
    schema = json.loads(args.interview_schema.read_text())
    answers = json.loads(args.interview_answers.read_text())

    qmap: dict[str, dict] = {}
    for section in schema["sections"]:
        for q in section["questions"]:
            qmap[q["id"]] = q

    ans_block = answers.get("answers", {})
    added = 0
    for qid, ans in ans_block.items():
        q = qmap.get(qid)
        if not q:
            continue
        audit["findings"].append(make_finding(q, ans))
        added += 1

    rescore(audit)
    audit["interview_questions_answered"] = added

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(audit, indent=2))
    print(f"merge_interview: +{added} interview findings → verdict={audit['verdict']} score={audit['overall_score']} → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
