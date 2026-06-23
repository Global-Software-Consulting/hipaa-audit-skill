---
mode: agent
description: HIPAA compliance audit — 3-phase gap assessment (auto-scan, guided interview, scored report).
---

# HIPAA Audit (GitHub Copilot prompt)

Run a HIPAA compliance gap assessment on the project path I provide (ask me for it if missing).
The scanner is plain Python 3.10+ (stdlib only). Mirrors `skills/hipaa-audit/SKILL.md`.

## Phase 1 — Auto-scan

Run in the terminal:

```bash
bash skills/hipaa-audit/scripts/run_audit.sh <TARGET_PROJECT_PATH>
```

Flags: `--out DIR`, `--no-deps`, `--no-infra`, `--no-html-in-project`. Outputs `audit.{json,md,html}`
to `/tmp/hipaa-audit-<timestamp>/` and drops `hipaa-audit-report.{html,md}` into the audited project.
Tell me how many issues were found and note static analysis only covers ~30–40% of HIPAA.

## Phase 2 — Interview

Load `skills/hipaa-audit/docs/interview.json` (12 sections). Ask me **3–5 questions per turn**,
`must`-severity first. For each `no`/`partial` answer, ask the evidence prompt. Accept skip/unknown
(record as `manual`). Persist answers to `<out>/interview.json` after each batch. Skip the `mobile`
section for web/backend-only projects.

## Phase 3 — Merge + report

```bash
python skills/hipaa-audit/scripts/merge_interview.py \
  --audit "$OUT/audit.json" --interview-answers "$OUT/interview.json" \
  --interview-schema skills/hipaa-audit/docs/interview.json --out "$OUT/audit_final.json"
python skills/hipaa-audit/scripts/render_report.py --audit "$OUT/audit_final.json" --out "$OUT/audit_final.md"
python skills/hipaa-audit/scripts/render_html.py   --audit "$OUT/audit_final.json" --out "$OUT/audit_final.html"
```

Then walk me through the top 5 must-fix items and offer to create issues/policy skeletons.

**Verdict:** any `must` fail OR overall <60 → Not Compliant; 60–84 → Partially Compliant;
≥85 and no critical category <70 → Compliant. `compliant` = automated checks passed, NOT a legal
certification. Review every finding — false positives are expected.
