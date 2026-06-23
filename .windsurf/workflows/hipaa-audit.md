---
description: HIPAA compliance audit — 3-phase gap assessment (auto-scan, guided interview, scored report).
---

# /hipaa-audit (Windsurf workflow)

Run a HIPAA compliance gap assessment. Invoke with `/hipaa-audit` and provide a project path
(ask the user if missing). Scanner is plain Python 3.10+ (stdlib only). Mirrors
`skills/hipaa-audit/SKILL.md`.

## Step 1 — Auto-scan

Run:

```bash
bash skills/hipaa-audit/scripts/run_audit.sh <TARGET_PROJECT_PATH>
```

Flags: `--out DIR`, `--no-deps`, `--no-infra`, `--no-html-in-project`. Outputs `audit.{json,md,html}`
to `/tmp/hipaa-audit-<timestamp>/` and drops `hipaa-audit-report.{html,md}` into the audited project.
Report the issue count; note static analysis covers ~30–40% of HIPAA, the interview covers the rest.

## Step 2 — Interview

Load `skills/hipaa-audit/docs/interview.json` (12 sections). Ask the user **3–5 questions per turn**,
`must`-severity first. For each `no`/`partial`, ask the evidence prompt. Accept skip/unknown (record as
`manual`). Persist answers to `<out>/interview.json` after each batch (resumable). Skip the `mobile`
section for web/backend-only projects. When all `must` are done, ask whether to continue with
`should`/`nice` or stop.

## Step 3 — Merge + report

```bash
python skills/hipaa-audit/scripts/merge_interview.py \
  --audit "$OUT/audit.json" --interview-answers "$OUT/interview.json" \
  --interview-schema skills/hipaa-audit/docs/interview.json --out "$OUT/audit_final.json"
python skills/hipaa-audit/scripts/render_report.py --audit "$OUT/audit_final.json" --out "$OUT/audit_final.md"
python skills/hipaa-audit/scripts/render_html.py   --audit "$OUT/audit_final.json" --out "$OUT/audit_final.html"
```

Then walk the user through the top 5 must-fix items and offer tickets / policy skeletons / follow-up.

## Verdict

- any `must` failed OR overall < 60 → **Not Compliant**
- no `must` failed AND overall 60–84 → **Partially Compliant**
- no `must` failed AND overall ≥ 85 AND no critical category < 70 → **Compliant**

`compliant` = automated checks passed, NOT a legal certification. Static analysis only — review every
finding; false positives expected.
