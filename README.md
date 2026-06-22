# hipaa-audit-skill

> HIPAA compliance audit skill for Claude Code. Scans a project (codebase + infra config + dependencies) against HIPAA Security/Privacy/Breach Notification rules and Safe Harbor de-identification. Emits a scored report with severity-tagged findings, evidence, and citations.

**Verdict:** Not Compliant / Partially Compliant / Compliant
**Score:** 0–100 per category + overall
**Citations:** every rule traces to HHS / NIST 800-66 / OCR audit protocol

---

## Quick start

```bash
# from anywhere
bash skills/hipaa-audit/scripts/run_audit.sh /path/to/your/project
# default output: /tmp/hipaa-audit-<timestamp>/
#   ├── facts.json    (raw scan facts)
#   ├── audit.json    (rule evaluations)
#   ├── audit.md      (human report w/ score + analytics)
#   └── audit.html    (interactive dashboard — open in browser)
#
# also dropped inside the audited project:
#   ├── hipaa-audit-report.html   (the dashboard)
#   └── hipaa-audit-report.md
```

No Python dependencies — uses stdlib only.

Flags:
- `--out DIR` — override output directory
- `--no-deps` — skip dependency BAA scan
- `--no-infra` — skip Dockerfile/yaml/env scan
- `--no-html-in-project` — skip dropping reports inside the audited project

## Trigger phrases (skill auto-loads)

"hipaa audit", "hipaa compliance check", "is my app hipaa compliant",
"phi leak check", "scan for phi", "baa audit", "safe harbor check",
"healthcare security audit", "ocr audit prep"

## What it checks (12 categories)

| Category | Examples |
|----------|----------|
| **encryption-at-rest** | DB/storage encryption, KMS, backup encryption |
| **encryption-in-transit** | TLS 1.2+, HSTS, no plaintext HTTP |
| **access-control** | RBAC, MFA, unique user IDs, auto-logoff |
| **audit-logging** | who-accessed-what, retention ≥6yr, immutable |
| **phi-in-logs** | PHI patterns leaking into log statements |
| **phi-in-urls** | identifiers in query strings or path params |
| **secrets-mgmt** | hardcoded keys, .env in repo, exposed tokens |
| **input-validation** | injection prevention, body validation |
| **session-mgmt** | timeout, secure cookies, CSRF |
| **dep-baa** | third-party vendors require Business Associate Agreement |
| **de-identification** | 18 Safe Harbor identifiers handling |
| **breach-readiness** | incident response, backup, DR, audit log integrity |

## Limits

- Static analysis. Does NOT replace a HITRUST / SOC 2 + HIPAA audit by qualified auditor.
- Vendor BAA list is heuristic from `package.json` / `requirements.txt` / Terraform. Confirm BAA status with each vendor.
- Cannot evaluate non-technical safeguards (workforce training, policies, signed BAAs) — those are flagged as "manual verification required".

## Docs

- [skills/hipaa-audit/docs/HIPAA_RULES_SIMPLE.md](skills/hipaa-audit/docs/HIPAA_RULES_SIMPLE.md) — plain-English explainer
- [skills/hipaa-audit/docs/18_IDENTIFIERS.md](skills/hipaa-audit/docs/18_IDENTIFIERS.md) — Safe Harbor list
- [skills/hipaa-audit/docs/BAA_VENDORS.md](skills/hipaa-audit/docs/BAA_VENDORS.md) — common vendor BAA status
- [skills/hipaa-audit/docs/rules.yaml](skills/hipaa-audit/docs/rules.yaml) — rule definitions

## License

MIT
