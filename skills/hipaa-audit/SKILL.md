---
name: hipaa-audit
description: HIPAA compliance audit for any project (web, mobile, backend). Scans codebase, infra config, env files, dependencies, and vendor list against the HIPAA Security Rule (administrative/physical/technical safeguards), Privacy Rule, Breach Notification Rule, and Safe Harbor 18-identifier de-identification. Emits a scored report (Not Compliant / Partially Compliant / Compliant) with severity-tagged findings, evidence, citations to HHS / NIST 800-66 / OCR audit protocol, and remediation hints. Use when the user asks "hipaa audit", "hipaa compliance check", "is my app hipaa compliant", "phi leak check", "scan for phi", "baa audit", "safe harbor check", "healthcare security audit", "ocr audit prep", or provides a project path to evaluate against HIPAA. Do NOT use for non-healthcare security audits (use the security skill) — this skill audits HIPAA-specific obligations only.
user-invokable: true
argument-hint: <project-path> [--out DIR] [--no-deps] [--no-infra]
license: MIT
metadata:
  version: 0.1.0
  category: security
  keywords:
    - hipaa
    - compliance
    - phi
    - phi-leak
    - safe-harbor
    - de-identification
    - baa
    - encryption
    - audit-logs
    - healthcare
    - security-rule
    - privacy-rule
    - breach-notification
    - ocr
    - nist-800-66
    - hitrust
    - audit
---

# hipaa-audit

Three-phase HIPAA compliance audit:

1. **Phase 1 — Auto-scan** of the codebase, infra, deps (the cheap, deterministic stuff)
2. **Phase 2 — Off-code interview** that Claude walks the user through (BAAs, policies, training, risk analysis, runtime evidence)
3. **Phase 3 — Merge + final report** combining both into a single scored verdict with remediation roadmap

Every rule cites HHS / NIST 800-66 / OCR. Verdict: **Not Compliant** / **Partially Compliant** / **Compliant** with per-category + overall scores 0–100. Code scan alone catches ~30–40% of HIPAA obligations — Phase 2 is required to reach a meaningful verdict.

## When to use

Trigger on any of:
- "hipaa audit", "hipaa compliance check"
- "is my app hipaa compliant"
- "scan for phi", "phi leak check"
- "baa audit", "vendor baa check"
- "safe harbor check", "de-identification audit"
- "healthcare security audit", "ocr audit prep"

Do NOT use for: general security audits unrelated to PHI (use the `security` skill), penetration testing, code-quality review, or policy drafting.

## How Claude should drive this skill

When triggered:

### Step A — run Phase 1 (auto-scan)

Run `run_audit.sh` on the target path. Produces `audit.json`, `audit.md`, `audit.html` in the audit output dir, and drops a copy of the HTML + MD reports inside the audited project root.

Tell the user:
> "Phase 1 complete. Auto-scan caught **N** technical issues. Static analysis covers ~30–40% of HIPAA obligations. The remaining 60% lives in policies, BAAs, training records, and runtime evidence — let's walk through that now. ~30–45 min, can pause anytime."

### Step B — run Phase 2 (interview)

Load `docs/interview.json`. Walk the user through each section IN ORDER, asking **3–5 questions per turn** (never the full list at once). Rules:

1. Start with `must` severity questions first
2. For each `no` / `partial` answer, ask the question's evidence prompt
3. Accept "skip" / "unknown" — record as `manual` with a note
4. After each batch, write the answers so far to `<out>/interview.json` (resumable across sessions)
5. Skip the `mobile` section if the project is web/backend only
6. When all `must` done, ask the user whether to continue with `should` / `nice` or stop

Answers file format:

```json
{
  "completed_at": "ISO-8601",
  "sections_completed": ["baa", "risk"],
  "answers": {
    "baa.with_covered_entity": { "answer": "yes", "evidence": "Notion/Compliance/BAA.md", "note": "" },
    "risk.analysis_doc": { "answer": "no", "evidence": "", "note": "scheduled Q3 2026" }
  }
}
```

### Step C — run Phase 3 (merge + final report)

```bash
python "$SKILL_DIR/scripts/merge_interview.py" \
  --audit "$OUT/audit.json" \
  --interview-answers "$OUT/interview.json" \
  --interview-schema "$SKILL_DIR/docs/interview.json" \
  --out "$OUT/audit_final.json"

python "$SKILL_DIR/scripts/render_report.py" --audit "$OUT/audit_final.json" --out "$OUT/audit_final.md"
python "$SKILL_DIR/scripts/render_html.py"   --audit "$OUT/audit_final.json" --out "$OUT/audit_final.html"

cp "$OUT/audit_final.html" "$PROJECT/hipaa-audit-report.html"
cp "$OUT/audit_final.md"   "$PROJECT/hipaa-audit-report.md"
```

After Phase 3, **walk the user through the top 5 must-fix items**, propose owners and deadlines, and offer to:
- Generate skeleton policy docs they're missing
- Create issues/tickets for each remediation
- Schedule a follow-up audit after fixes

## How it runs

**Preferred — one-shot orchestration of Phase 1 only:**

```bash
SKILL_DIR="${CLAUDE_SKILL_DIR:-$(dirname "$(readlink -f "${BASH_SOURCE[0]:-$0}")")}"
pip install -q -r "$SKILL_DIR/../../requirements.txt" 2>/dev/null || true
bash "$SKILL_DIR/scripts/run_audit.sh" "$PROJECT_PATH"
```

`run_audit.sh` runs all steps and writes `facts.json`, `audit.json`, `audit.md`, and `audit.html` to `/tmp/hipaa-audit-<timestamp>/`. It also copies the HTML + MD reports into the audited project as `hipaa-audit-report.html` / `hipaa-audit-report.md` so the team can open the dashboard in a browser immediately.

No Python dependencies — uses stdlib only.

Flags:
- `--out DIR` — output directory
- `--no-deps` — skip vendor BAA scan
- `--no-infra` — skip Dockerfile/yaml/env scan
- `--no-html-in-project` — skip dropping reports inside the audited project

### Manual step breakdown

#### 1. Scan codebase for PHI risk

```bash
python "$SKILL_DIR/scripts/scan_code.py" "$PROJECT_PATH" --out "$OUT/code.json"
```

Searches source files for:
- PHI identifier patterns (SSN, MRN, email, phone, DOB) inside log statements, URLs, console output
- Hardcoded secrets / API keys / tokens
- Plaintext HTTP URLs
- Disabled TLS verification (`verify=False`, `rejectUnauthorized: false`)
- Wildcard CORS on PHI endpoints
- Missing input validation decorators

#### 2. Scan infrastructure

```bash
python "$SKILL_DIR/scripts/scan_infra.py" "$PROJECT_PATH" --out "$OUT/infra.json"
```

Inspects:
- `Dockerfile`, `docker-compose.yml`, `*.tf`, `*.yaml`, `*.yml`, `serverless.yml`
- TLS / HSTS / HTTPS-only flags
- Database encryption at rest (`storage_encrypted`, `encryption: AES256`)
- S3 / Blob public-access settings
- Logging config (CloudWatch, Sentry, Datadog) — flags PHI risk if no scrubber
- `.env`, `.env.example` — checks for committed secrets and unencrypted PHI

#### 3. Scan dependencies for BAA needs

```bash
python "$SKILL_DIR/scripts/scan_deps.py" "$PROJECT_PATH" --out "$OUT/deps.json"
```

Reads `package.json`, `requirements.txt`, `Pipfile`, `go.mod`, `Gemfile`, `pom.xml`, `composer.json` and matches against `docs/BAA_VENDORS.md` to flag vendors that:
- Touch PHI in transit/at rest
- Require a signed BAA
- Have NO BAA option (must replace)

#### 4. Evaluate rules

```bash
python "$SKILL_DIR/scripts/rules_engine.py" \
  --facts "$OUT/facts.json" \
  --rules "$SKILL_DIR/docs/rules.json" \
  --out "$OUT/audit.json"
```

Output schema:
```json
{
  "project_path": "...",
  "rules_total": N,
  "verdict": "not_compliant | partially_compliant | compliant",
  "overall_score": 0-100,
  "category_scores": {
    "encryption-at-rest": 0-100,
    "encryption-in-transit": 0-100,
    "access-control": 0-100,
    ...
  },
  "summary": {
    "must":   {"pass": x, "fail": y, "manual": m, "skipped": s},
    "should": {...},
    "nice":   {...}
  },
  "findings": [
    {
      "rule_id": "encryption.tls12-min",
      "category": "encryption-in-transit",
      "severity": "must",
      "status": "pass|fail|manual|skipped",
      "title": "...",
      "evidence": "file.py:42 — `verify=False`",
      "source_url": "https://www.hhs.gov/hipaa/...",
      "fix_hint": "...",
      "rationale": "..."
    }
  ]
}
```

#### 5. Render reports

```bash
python "$SKILL_DIR/scripts/render_report.py" --audit "$OUT/audit.json" --out "$OUT/audit.md"
python "$SKILL_DIR/scripts/render_html.py"   --audit "$OUT/audit.json" --out "$OUT/audit.html"
```

Produces:
- **`audit.md`** — markdown report (verdict + score + category bars + remediation roadmap)
- **`audit.html`** — interactive dashboard (gauge, category radar, severity chart, vendor BAA risk table, filterable findings table, dark-mode aware)
- A copy of both is also dropped inside the audited project root as `hipaa-audit-report.{html,md}` for the team to open immediately.

## Verdict thresholds

| Verdict | Condition |
|---------|-----------|
| **Not Compliant** | any `must` failed OR overall < 60 |
| **Partially Compliant** | no `must` failed AND overall 60–84 |
| **Compliant** | no `must` failed AND overall ≥ 85 AND no critical category < 70 |

`compliant` does NOT mean legally compliant — it means automated checks passed. Always pair with a qualified HIPAA auditor.

## Limits

- Static analysis only. Cannot verify runtime behavior, signed BAAs, training logs, or policies.
- BAA vendor list is a heuristic; confirm with each vendor's HIPAA page.
- False positives possible on PHI pattern detection — review each finding before acting.

## References

- HHS Security Rule: https://www.hhs.gov/hipaa/for-professionals/security/laws-regulations/index.html
- HHS Privacy Rule: https://www.hhs.gov/hipaa/for-professionals/privacy/laws-regulations/index.html
- HHS Breach Notification: https://www.hhs.gov/hipaa/for-professionals/breach-notification/index.html
- NIST 800-66 Rev 2: https://csrc.nist.gov/publications/detail/sp/800-66/rev-2/final
- OCR Audit Protocol: https://www.hhs.gov/hipaa/for-professionals/compliance-enforcement/audit/protocol/index.html
- Safe Harbor 18 identifiers: 45 CFR § 164.514(b)(2)
