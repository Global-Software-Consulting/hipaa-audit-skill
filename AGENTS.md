# AGENTS.md — hipaa-audit

> Universal agent instructions. Read by Cursor, GitHub Copilot, Windsurf, and other
> tools that support the `AGENTS.md` convention. The canonical definition lives in
> `skills/hipaa-audit/SKILL.md` (Claude Code format) — this file mirrors it for other editors.

## What this repo is

A HIPAA compliance gap-assessment tool. The core engine is **plain Python 3.10+ (stdlib only)**
and runs anywhere — no AI tool required. The AI layer just drives a 3-phase workflow on top of it.

## When to run a HIPAA audit

Trigger when the user asks any of:
- "hipaa audit", "hipaa compliance check", "is my app hipaa compliant"
- "scan for phi", "phi leak check"
- "baa audit", "vendor baa check"
- "safe harbor check", "de-identification audit"
- "healthcare security audit", "ocr audit prep"

Do NOT use for general (non-PHI) security audits, pen-testing, or policy drafting.

## The 3-phase workflow

### Phase 1 — Auto-scan (deterministic, ~30 sec)

Run the standalone scanner against the target project:

```bash
bash skills/hipaa-audit/scripts/run_audit.sh <TARGET_PROJECT_PATH>
```

Flags: `--out DIR`, `--no-deps`, `--no-infra`, `--no-html-in-project`.

This writes `facts.json`, `audit.json`, `audit.md`, `audit.html` to `/tmp/hipaa-audit-<timestamp>/`
and drops `hipaa-audit-report.{html,md}` into the audited project root.

Then tell the user:
> "Phase 1 complete. Auto-scan caught **N** technical issues. Static analysis covers ~30–40% of
> HIPAA obligations. The rest lives in policies, BAAs, training, and runtime evidence — let's walk
> through that now (~30–45 min, pausable)."

### Phase 2 — Interview (guided, self-reported)

Load `skills/hipaa-audit/docs/interview.json` (12 sections). Walk the user through each section IN ORDER:

1. Ask **3–5 questions per turn** — never the whole list at once.
2. Start with `must`-severity questions first.
3. For each `no` / `partial` answer, ask the question's evidence prompt.
4. Accept "skip" / "unknown" — record as `manual` with a note.
5. After each batch, write answers so far to `<out>/interview.json` (resumable across sessions).
6. Skip the `mobile` section for web/backend-only projects.
7. When all `must` questions are done, ask whether to continue with `should` / `nice` or stop.

Answers file format:

```json
{
  "completed_at": "ISO-8601",
  "sections_completed": ["baa", "risk"],
  "answers": {
    "baa.with_covered_entity": { "answer": "yes", "evidence": "Notion/Compliance/BAA.md", "note": "" }
  }
}
```

### Phase 3 — Merge + final report

```bash
python skills/hipaa-audit/scripts/merge_interview.py \
  --audit "$OUT/audit.json" \
  --interview-answers "$OUT/interview.json" \
  --interview-schema skills/hipaa-audit/docs/interview.json \
  --out "$OUT/audit_final.json"

python skills/hipaa-audit/scripts/render_report.py --audit "$OUT/audit_final.json" --out "$OUT/audit_final.md"
python skills/hipaa-audit/scripts/render_html.py   --audit "$OUT/audit_final.json" --out "$OUT/audit_final.html"

cp "$OUT/audit_final.html" "<TARGET_PROJECT_PATH>/hipaa-audit-report.html"
cp "$OUT/audit_final.md"   "<TARGET_PROJECT_PATH>/hipaa-audit-report.md"
```

After Phase 3, walk the user through the **top 5 must-fix items**, propose owners/deadlines, and offer to
generate missing policy skeletons, create tickets, and schedule a follow-up audit.

## Verdict thresholds

| Verdict | Condition |
|---------|-----------|
| **Not Compliant** | any `must` failed OR overall < 60 |
| **Partially Compliant** | no `must` failed AND overall 60–84 |
| **Compliant** | no `must` failed AND overall ≥ 85 AND no critical category < 70 |

`compliant` = automated checks passed. **Not a legal certification.** Always pair with a qualified
HIPAA auditor. Static analysis only — false positives expected; review every finding.

## Editor-specific adapters

- **Claude Code:** `skills/hipaa-audit/SKILL.md` (canonical)
- **Cursor:** `.cursor/rules/hipaa-audit.mdc` + `.cursor/commands/hipaa-audit.md`
- **GitHub Copilot:** `.github/prompts/hipaa-audit.prompt.md`
- **Windsurf:** `.windsurf/workflows/hipaa-audit.md`
