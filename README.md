# hipaa-audit-skill

> A Claude Code skill for HIPAA compliance gap assessment. Three-phase audit (auto-scan → guided interview → merged report) with scored verdict, severity-tagged findings, and citations to HHS / NIST 800-66 / OCR.

**Verdict:** Not Compliant / Partially Compliant / Compliant
**Score:** 0–100 per category + overall
**Stdlib only** — no Python dependencies
**Output:** JSON + Markdown + interactive HTML dashboard

---

## What this is (and is not)

**Is:** a pre-audit gap assessment tool for engineering teams. Catches obvious technical mistakes (encryption off, hardcoded secrets, vendors without BAA, PHI in logs) and surfaces process gaps (missing policies, no risk analysis, no incident runbook) via a guided interview.

**Is not:** a HIPAA certification. Static checks + self-reported answers cover ~62% of HIPAA obligations. **Always pair with a qualified third-party auditor** (HITRUST, SOC 2 + HIPAA) before clinical go-live.

Realistic confidence:
- Catch obvious mistakes before they ship: **~90%**
- Surface real gaps before paid auditor finds them: **~75%**
- Replace a HIPAA auditor: **0%**

---

## Install (one-time)

```bash
git clone git@github.com:Global-Software-Consulting/hipaa-audit-skill.git ~/hipaa-audit-skill
bash ~/hipaa-audit-skill/install.sh
```

Creates a symlink at `~/.claude/skills/hipaa-audit`. Edits in the cloned repo apply live.

Restart Claude Code → skill auto-loads. Verify:

```bash
ls -la ~/.claude/skills/hipaa-audit
```

### Uninstall

```bash
bash ~/hipaa-audit-skill/uninstall.sh
```

---

## Usage

### Inside Claude Code (preferred)

```
/hipaa-audit /path/to/project
```

Or any trigger phrase:
- "hipaa audit `/path/to/project`"
- "is `/path/to/project` hipaa compliant?"
- "phi leak check on `/path/to/project`"
- "baa audit on `/path/to/project`"

Claude follows the 3-phase flow:

1. **Phase 1 (auto-scan, ~30 sec):** scans code/infra/deps, prints findings + initial score, drops `hipaa-audit-report.html` in project root.
2. **Phase 2 (interview, ~30–45 min, pausable):** Claude asks 3–5 questions per turn, MUST severity first. Skip / unknown accepted. Resumable across sessions.
3. **Phase 3 (merge):** combined scored report. Walks you through top must-fix items, offers to generate tickets.

### Direct script (no Claude, Phase 1 only)

```bash
bash ~/hipaa-audit-skill/skills/hipaa-audit/scripts/run_audit.sh /path/to/project
```

Output:
```
/tmp/hipaa-audit-<timestamp>/
├── facts.json
├── audit.json
├── audit.md
└── audit.html

# also copied into the project root:
your-project/hipaa-audit-report.html
your-project/hipaa-audit-report.md
```

### Flags

| Flag | Effect |
|------|--------|
| `--out DIR` | override output directory |
| `--no-deps` | skip vendor BAA scan |
| `--no-infra` | skip Dockerfile / TF / yaml / env scan |
| `--no-html-in-project` | don't drop report inside audited project |

---

## What it checks (12 categories)

| Category | Examples |
|----------|----------|
| `encryption-at-rest` | DB / object storage / backup encryption |
| `encryption-in-transit` | TLS 1.2+, HSTS, no plaintext HTTP, no disabled TLS verify |
| `access-control` | auth framework, MFA, wildcard CORS, RBAC |
| `audit-logging` | who-accessed-what, immutable, retention ≥ 6yr |
| `phi-in-logs` | PHI patterns in log statements, scrubber present |
| `phi-in-urls` | identifiers in query strings or path params |
| `secrets-mgmt` | hardcoded keys, committed `.env`, exposed tokens |
| `input-validation` | injection prevention, body validation |
| `session-mgmt` | timeout, auto-logoff |
| `dep-baa` | vendor BAA: signable / enterprise / blocked |
| `de-identification` | Safe Harbor 18 identifiers, dev/test fixtures |
| `breach-readiness` | risk analysis, incident runbook, DR, NPP, patient rights |

Each rule cites HHS / NIST 800-66 / OCR / 45 CFR Part 164.

---

## Project type compatibility

| Type | Works | Notes |
|------|-------|-------|
| Single web app (React, Next.js, Vue, Svelte) | ✅ | All categories |
| Single mobile app (React Native, Flutter, native) | ✅ | Mobile interview section auto-included |
| Single backend (Node, Python, Go, Java, Rails) | ✅ | All categories |
| Monorepo (FE + BE + shared) | ✅ | Single run = combined report. For per-app reports, run per package path. |

---

## Output sample

HTML dashboard includes:
- Verdict badge + gauge
- KPI grid (rules, MUST/SHOULD failures, manual verify, passing, interview gaps)
- Category bars with color-coded scores
- Severity distribution chart
- Vendor BAA risk table (blocked / enterprise / signable)
- Filterable findings table (filter by status, severity, code vs interview source)
- Dark-mode aware

Markdown report includes:
- Executive summary
- Severity summary table
- Analytics breakdown
- Top failing categories
- MUST-fix detail cards
- Remediation roadmap (Week 1 / Sprint 1 / Manual)

---

## Verdict thresholds

| Verdict | Condition |
|---------|-----------|
| **Not Compliant** | any `must` failed OR overall < 60 |
| **Partially Compliant** | no `must` failed AND overall 60–84 |
| **Compliant** | no `must` failed AND overall ≥ 85 AND no critical category < 70 |

`compliant` = automated checks passed. Not a legal certification.

---

## Limits (read this)

- **Static analysis only.** Cannot verify runtime behavior, signed BAAs, training logs, policies.
- **False positives expected.** Regex catches namespace URLs (`http://www.w3.org/2000/svg`), route constants (`PASSWORD: '/auth/forgot-password'`), env files already in `.gitignore`. Review each finding.
- **Interview = self-reported.** "Yes, we have a risk analysis" is not verified against actual document content or freshness.
- **BAA vendor list is a snapshot.** Confirm current BAA status on each vendor's HIPAA page before signing.
- **Doesn't replace:** HITRUST cert, SOC 2 + HIPAA audit, penetration test, code review, runtime cloud-config audit.

---

## Repository layout

```
hipaa-audit-skill/
├── install.sh                          ← global install script
├── uninstall.sh
├── README.md
├── LICENSE                             ← MIT
├── requirements.txt                    ← stdlib only
├── .claude-plugin/plugin.json
└── skills/hipaa-audit/
    ├── SKILL.md                        ← skill definition (Claude reads this)
    ├── docs/
    │   ├── HIPAA_RULES_SIMPLE.md       ← plain-English HIPAA explainer
    │   ├── 18_IDENTIFIERS.md           ← Safe Harbor identifier list
    │   ├── BAA_VENDORS.md              ← vendor BAA status map
    │   ├── INTERVIEW.md                ← Phase 2 interview guide
    │   ├── interview.json              ← interview schema
    │   ├── rules.yaml                  ← human-readable rule source
    │   └── rules.json                  ← runtime rule format
    └── scripts/
        ├── run_audit.sh                ← Phase 1 orchestrator
        ├── scan_code.py                ← source scan
        ├── scan_infra.py               ← infra/config scan
        ├── scan_deps.py                ← dependency BAA classifier
        ├── rules_engine.py             ← rule evaluator
        ├── merge_interview.py          ← Phase 3 merge
        ├── render_report.py            ← markdown renderer
        └── render_html.py              ← HTML dashboard renderer
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Three common contributions:

1. **Add a rule** — append to `skills/hipaa-audit/docs/rules.yaml`, re-export to `rules.json` (see CONTRIBUTING). Cite an authoritative source.
2. **Update vendor BAA status** — edit `skills/hipaa-audit/docs/BAA_VENDORS.md` and `scripts/scan_deps.py:VENDOR_MAP`. Include vendor page URL as evidence.
3. **Add interview question** — append to `skills/hipaa-audit/docs/interview.json`. Match an existing category.

Open an issue first for new rule categories.

---

## License

MIT. See [LICENSE](LICENSE).

---

## References

- HHS Security Rule: https://www.hhs.gov/hipaa/for-professionals/security/laws-regulations/index.html
- HHS Privacy Rule: https://www.hhs.gov/hipaa/for-professionals/privacy/laws-regulations/index.html
- HHS Breach Notification: https://www.hhs.gov/hipaa/for-professionals/breach-notification/index.html
- NIST 800-66 Rev 2: https://csrc.nist.gov/publications/detail/sp/800-66/rev-2/final
- OCR Audit Protocol: https://www.hhs.gov/hipaa/for-professionals/compliance-enforcement/audit/protocol/index.html
- Safe Harbor 18 identifiers: 45 CFR § 164.514(b)(2)
- HHS Tracking Technologies bulletin (GA4 / Meta Pixel): https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/hipaa-online-tracking/index.html
