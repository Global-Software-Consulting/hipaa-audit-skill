# /hipaa-audit

Run a HIPAA compliance gap assessment on a project. Usage: `/hipaa-audit <project-path>`.

Follow the 3-phase workflow:

1. **Auto-scan** — run `bash skills/hipaa-audit/scripts/run_audit.sh <project-path>`.
   Report the number of technical issues found and where the HTML report was dropped.
2. **Interview** — load `skills/hipaa-audit/docs/interview.json`, ask 3–5 questions per turn
   (`must` first), record answers to `<out>/interview.json`, accept skip/unknown.
3. **Merge + report** — run `merge_interview.py`, `render_report.py`, `render_html.py`, then
   walk me through the top 5 must-fix items.

See `.cursor/rules/hipaa-audit.mdc` for full command details and verdict thresholds.
Static analysis only — not a legal certification; review every finding.
