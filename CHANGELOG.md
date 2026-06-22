# Changelog

## [0.1.0] — 2026-06-22

Initial release.

### Added
- Three-phase audit workflow (auto-scan → guided interview → merged report)
- Phase 1 scanners: `scan_code.py`, `scan_infra.py`, `scan_deps.py`
- Phase 2 interview schema: 12 sections, 45+ questions covering BAAs, risk analysis, workforce, audit logs, encryption, incident response, physical safeguards, DR, de-identification, patient rights, mobile-specific
- Phase 3 merger: `merge_interview.py` combines static scan + interview answers into final scored verdict
- 24 baseline rules in `docs/rules.yaml` / `rules.json`, each citing HHS / NIST 800-66 / OCR / 45 CFR
- Rules engine with category + overall scoring (0–100), verdict thresholds
- Renderers: markdown report (`render_report.py`), interactive HTML dashboard (`render_html.py`)
- HTML dashboard features: verdict gauge, KPI grid, category bars, severity chart, vendor BAA risk table, filterable findings (by status / severity / code vs interview source), dark-mode aware
- Vendor BAA classifier: signable / enterprise-required / blocked, mapping for AWS, GCP, Azure, Stripe, Twilio, Sentry, Datadog, Vercel, Mailchimp, GA4, Meta Pixel, Crashlytics, etc.
- Docs: `HIPAA_RULES_SIMPLE.md` (plain-English explainer), `18_IDENTIFIERS.md` (Safe Harbor), `BAA_VENDORS.md` (vendor map), `INTERVIEW.md` (Phase 2 guide)
- Install / uninstall scripts (symlink-based, edits in repo apply live)
- Reports auto-dropped into audited project root (`hipaa-audit-report.{html,md}`)

### Known limits
- Static analysis only — no runtime verification
- Interview answers self-reported, not evidence-verified
- False positives on namespace URLs (`http://www.w3.org/*`), route constants (`PASSWORD: '/auth/...'`), env files already in `.gitignore`
- No project-type classifier — backend rules currently apply to frontend-only projects
- BAA vendor list is a 2026-06 snapshot
