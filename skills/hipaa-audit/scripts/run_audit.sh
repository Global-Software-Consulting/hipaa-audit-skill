#!/usr/bin/env bash
# Orchestrate a full HIPAA audit on a project path.
# Usage: run_audit.sh <project-path> [--out DIR] [--no-deps] [--no-infra]

set -euo pipefail

PROJECT="${1:-}"
if [[ -z "$PROJECT" ]]; then
  echo "usage: run_audit.sh <project-path> [--out DIR] [--no-deps] [--no-infra]" >&2
  exit 2
fi
shift || true

OUT=""
DO_DEPS=1
DO_INFRA=1
DROP_HTML_IN_PROJECT=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out) OUT="$2"; shift 2 ;;
    --no-deps) DO_DEPS=0; shift ;;
    --no-infra) DO_INFRA=0; shift ;;
    --no-html-in-project) DROP_HTML_IN_PROJECT=0; shift ;;
    *) echo "unknown flag: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$OUT" ]]; then
  OUT="/tmp/hipaa-audit-$(date +%s)"
fi
mkdir -p "$OUT"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
PY="${PYTHON:-python3}"

echo "→ project: $PROJECT"
echo "→ output:  $OUT"
echo

"$PY" "$SCRIPT_DIR/scan_code.py" "$PROJECT" --out "$OUT/code.json"

if [[ "$DO_INFRA" -eq 1 ]]; then
  "$PY" "$SCRIPT_DIR/scan_infra.py" "$PROJECT" --out "$OUT/infra.json"
else
  echo '{"infra": {}}' > "$OUT/infra.json"
fi

if [[ "$DO_DEPS" -eq 1 ]]; then
  "$PY" "$SCRIPT_DIR/scan_deps.py" "$PROJECT" --out "$OUT/deps.json"
else
  echo '{"deps": {}}' > "$OUT/deps.json"
fi

"$PY" - <<PYEOF
import json, pathlib
out = pathlib.Path("$OUT")
merged = {}
for name in ("code", "infra", "deps"):
    f = out / f"{name}.json"
    if f.exists():
        merged.update(json.loads(f.read_text()))
(out / "facts.json").write_text(json.dumps(merged, indent=2))
print(f"merged → {out / 'facts.json'}")
PYEOF

"$PY" "$SCRIPT_DIR/rules_engine.py" \
  --facts "$OUT/facts.json" \
  --rules "$SKILL_DIR/docs/rules.json" \
  --out "$OUT/audit.json"

"$PY" "$SCRIPT_DIR/render_report.py" \
  --audit "$OUT/audit.json" \
  --out "$OUT/audit.md"

"$PY" "$SCRIPT_DIR/render_html.py" \
  --audit "$OUT/audit.json" \
  --out "$OUT/audit.html"

if [[ "$DROP_HTML_IN_PROJECT" -eq 1 ]]; then
  PROJECT_ABS="$(cd "$PROJECT" && pwd)"
  cp "$OUT/audit.html" "$PROJECT_ABS/hipaa-audit-report.html"
  cp "$OUT/audit.md"   "$PROJECT_ABS/hipaa-audit-report.md"
  echo "✓ also dropped: $PROJECT_ABS/hipaa-audit-report.html"
  echo "✓ also dropped: $PROJECT_ABS/hipaa-audit-report.md"
fi

echo
echo "✓ done."
echo "  JSON: $OUT/audit.json"
echo "  MD:   $OUT/audit.md"
echo "  HTML: $OUT/audit.html"
