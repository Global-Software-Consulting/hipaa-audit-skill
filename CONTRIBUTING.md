# Contributing

Welcome. Keep changes small + cited.

## Local setup

```bash
git clone git@github.com:Global-Software-Consulting/hipaa-audit-skill.git
cd hipaa-audit-skill
bash install.sh
```

No Python dependencies (stdlib only). Verified on Python 3.10+.

## Test a change

```bash
bash skills/hipaa-audit/scripts/run_audit.sh /path/to/any/test/project --out /tmp/test-audit
```

Inspect `/tmp/test-audit/audit.html` in browser, verify finding evidence matches reality.

## Adding a rule

1. Append to `skills/hipaa-audit/docs/rules.yaml`:

```yaml
- id: <category>.<short-name>
  category: encryption-in-transit   # one of 12 documented
  severity: must                    # must | should | nice
  title: "Short human title"
  check:
    fact: code.<fact_name>           # produced by scan_code/scan_infra/scan_deps
    op: truthy                       # truthy|falsy|equals|gte|lte|...
  source_url: "https://..."          # HHS / NIST / OWASP / vendor doc URL
  fix_hint: "What to do."
  rationale: "Why it matters. Cite 45 CFR § or NIST §."
```

2. Re-generate `rules.json`:

```bash
python3 - <<'PY'
import json, pathlib
# regen logic — see scripts/run_audit.sh
PY
```

(Until a `regen-rules.py` script lands, manual JSON edit is OK.)

3. If new fact needed, add to scanner:
   - source patterns → `scan_code.py`
   - infra config → `scan_infra.py`
   - dependency match → `scan_deps.py`

4. Test on a known-failing project + known-passing project. Verify the rule fires correctly in both directions.

## Adding an interview question

Append to `skills/hipaa-audit/docs/interview.json`:

```json
{
  "id": "section.short_name",
  "severity": "must",
  "category": "audit-logging",
  "prompt": "Plain question (≤120 chars).",
  "accept": "yes_no|yes_no_partial|date|enum:a|b|c|text|number"
}
```

Also document the rationale in `docs/INTERVIEW.md`.

## Updating vendor BAA status

Vendors update their HIPAA pages quarterly. To update:

1. Confirm status on vendor's HIPAA page (link is canonical evidence)
2. Edit `skills/hipaa-audit/docs/BAA_VENDORS.md` with new tier + evidence URL
3. Edit `skills/hipaa-audit/scripts/scan_deps.py` `VENDOR_MAP`:

```python
("vendor-name", ["package-pattern", "alt-package"], "signable"|"enterprise_required"|"blocked"),
```

PR description must cite the vendor page URL and date checked.

## Commit conventions

- Conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
- Atomic commits — one logical change per commit
- No Claude / AI attribution in commit messages

## False positive reports

Open an issue with:
- Project type + framework
- Exact finding (`rule_id` + evidence line)
- Why it's a false positive
- Proposed fix (regex tweak, allowlist, project-type filter)

## Out of scope

This skill is HIPAA-specific. Don't add:
- General security audits (use the `security` skill instead)
- Code-quality / linting rules
- Penetration testing
- Policy-drafting features

## License

By contributing you agree your changes are MIT-licensed.
