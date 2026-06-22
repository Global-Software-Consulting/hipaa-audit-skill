#!/usr/bin/env python3
"""
Render audit.json → audit.html. Self-contained, no JS deps, dark+light friendly.
Shows verdict badge, score gauge, category bars, severity chart, vendor risks,
findings table with filters.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

VERDICT_COLOR = {
    "compliant": ("#0a7d36", "#dcf4e3", "COMPLIANT"),
    "partially_compliant": ("#a86700", "#fff4dc", "PARTIALLY COMPLIANT"),
    "not_compliant": ("#b3261e", "#fde7e5", "NOT COMPLIANT"),
}
STATUS_COLOR = {
    "pass": "#0a7d36",
    "fail": "#b3261e",
    "manual": "#1463cc",
    "skipped": "#6b7280",
}
SEVERITY_BADGE = {
    "must": ("#b3261e", "#fde7e5"),
    "should": ("#a86700", "#fff4dc"),
    "nice": ("#1463cc", "#e6f0ff"),
}


def esc(v) -> str:
    return html.escape(str(v if v is not None else ""))


def render(audit: dict) -> str:
    v = audit["verdict"]
    fg, bg, label = VERDICT_COLOR.get(v, ("#333", "#eee", v.upper()))
    score = audit["overall_score"]
    cats = sorted(audit["category_scores"].items(), key=lambda x: x[1])
    findings = audit["findings"]
    fails_must = [f for f in findings if f["status"] == "fail" and f["severity"] == "must"]
    fails_should = [f for f in findings if f["status"] == "fail" and f["severity"] == "should"]
    manuals = [f for f in findings if f["status"] == "manual"]
    passing = [f for f in findings if f["status"] == "pass"]
    vendors = audit.get("vendor_matches", [])
    blocked_v = [x for x in vendors if x["baa"] == "blocked"]
    ent_v = [x for x in vendors if x["baa"] == "enterprise_required"]
    sign_v = [x for x in vendors if x["baa"] == "signable"]

    cat_fail = Counter(f["category"] for f in findings if f["status"] == "fail")
    sev_counts = audit["summary"]

    # gauge: half-circle SVG
    gauge_color = "#b3261e" if score < 60 else "#a86700" if score < 85 else "#0a7d36"

    rows = []
    for f in findings:
        sev_fg, sev_bg = SEVERITY_BADGE[f["severity"]]
        st_color = STATUS_COLOR[f["status"]]
        ev = ""
        if f.get("evidence"):
            ev_lines = "".join(f"<div class=ev>{esc(e)}</div>" for e in f["evidence"])
            ev = f"<details><summary>evidence</summary>{ev_lines}</details>"
        is_interview = "yes" if f.get("_interview") else "no"
        src_label = "interview" if f.get("_interview") else "code"
        rows.append(
            f'<tr data-status="{f["status"]}" data-severity="{f["severity"]}" data-category="{f["category"]}" data-source="{src_label}">'
            f'<td><code>{esc(f["rule_id"])}</code></td>'
            f'<td>{esc(f["category"])}</td>'
            f'<td><span class="badge" style="color:{sev_fg};background:{sev_bg}">{f["severity"]}</span></td>'
            f'<td><span class="status" style="color:{st_color}">●</span> {f["status"]}</td>'
            f'<td><span class=srcbadge data-src="{src_label}">{src_label}</span></td>'
            f'<td>{esc(f["title"])}{ev}<div class=hint>{esc(f["fix_hint"])}</div>'
            f'<a class=src href="{esc(f["source_url"])}" target=_blank>source</a></td>'
            f"</tr>"
        )
    interview_count = sum(1 for f in findings if f.get("_interview"))
    interview_failed = sum(1 for f in findings if f.get("_interview") and f["status"] == "fail")

    cat_bars = "".join(
        f'<div class="catrow"><span class=catname>{esc(c)}</span>'
        f'<span class=catbar><span class=catfill style="width:{s}%;background:{("#b3261e" if s<60 else "#a86700" if s<85 else "#0a7d36")}"></span></span>'
        f'<span class=catscore>{s}</span></div>'
        for c, s in cats
    )

    vendor_html = ""
    if vendors:
        def vrow(x, badge_color):
            return (
                f"<tr><td><code>{esc(x['package'])}</code></td>"
                f"<td>{esc(x['vendor'])}</td>"
                f'<td><span class=badge style="color:#fff;background:{badge_color}">{esc(x["baa"])}</span></td></tr>'
            )
        v_rows = "".join(vrow(x, "#b3261e") for x in blocked_v) \
               + "".join(vrow(x, "#a86700") for x in ent_v) \
               + "".join(vrow(x, "#0a7d36") for x in sign_v)
        vendor_html = (
            "<h2>Vendor BAA Risk</h2>"
            f"<p><strong style=color:#b3261e>{len(blocked_v)} blocked</strong> · "
            f"<strong style=color:#a86700>{len(ent_v)} enterprise tier required</strong> · "
            f"<strong style=color:#0a7d36>{len(sign_v)} signable</strong></p>"
            "<table><thead><tr><th>Package</th><th>Vendor</th><th>BAA Status</th></tr></thead>"
            f"<tbody>{v_rows}</tbody></table>"
        )

    sev_chart = ""
    for sev in ("must", "should", "nice"):
        row = sev_counts.get(sev, {})
        total = sum(row.values()) or 1
        pass_pct = row.get("pass", 0) / total * 100
        fail_pct = row.get("fail", 0) / total * 100
        manual_pct = row.get("manual", 0) / total * 100
        skip_pct = row.get("skipped", 0) / total * 100
        sev_chart += (
            f'<div class=sevrow><span class=sevlabel>{sev}</span>'
            f'<span class=sevbar>'
            f'<span style="width:{pass_pct}%;background:#0a7d36" title="pass {row.get("pass",0)}"></span>'
            f'<span style="width:{fail_pct}%;background:#b3261e" title="fail {row.get("fail",0)}"></span>'
            f'<span style="width:{manual_pct}%;background:#1463cc" title="manual {row.get("manual",0)}"></span>'
            f'<span style="width:{skip_pct}%;background:#6b7280" title="skipped {row.get("skipped",0)}"></span>'
            f'</span>'
            f'<span class=sevcount>{row.get("pass",0)}/{row.get("fail",0)}/{row.get("manual",0)}/{row.get("skipped",0)}</span>'
            "</div>"
        )

    top_fail_cats = "".join(
        f"<li><code>{esc(c)}</code> — {n} failure(s)</li>"
        for c, n in cat_fail.most_common(5)
    )

    must_fix_html = "".join(
        f"<div class=card><h3>{esc(f['title'])} <code class=tag>{esc(f['rule_id'])}</code></h3>"
        f"<p class=meta><strong>{f['category']}</strong> · <span style='color:#b3261e'>MUST</span></p>"
        f"<p><strong>Why it matters:</strong> {esc(f['rationale'])}</p>"
        f"<p><strong>Fix:</strong> {esc(f['fix_hint'])}</p>"
        + (
            "<p><strong>Evidence:</strong></p><pre>"
            + "\n".join(esc(e) for e in f.get("evidence", []))
            + "</pre>" if f.get("evidence") else ""
        )
        + f'<p><a href="{esc(f["source_url"])}" target=_blank>{esc(f["source_url"])}</a></p></div>'
        for f in fails_must
    )

    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    project = esc(audit.get("project_path", "unknown"))

    return f"""<!doctype html>
<html lang=en>
<head>
<meta charset=utf-8>
<title>HIPAA Audit — {project}</title>
<meta name=viewport content="width=device-width,initial-scale=1">
<style>
:root {{
  --bg:#fafafa; --fg:#1a1a1a; --muted:#6b7280; --card:#fff; --border:#e5e7eb;
}}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#0f1115; --fg:#e8eaed; --muted:#9aa0a6; --card:#1a1d23; --border:#2a2e36; }}
}}
* {{ box-sizing:border-box }}
body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; margin:0; padding:0 24px 64px; background:var(--bg); color:var(--fg); line-height:1.5 }}
.container {{ max-width:1100px; margin:0 auto }}
header {{ padding:32px 0 16px; border-bottom:1px solid var(--border) }}
h1 {{ font-size:28px; margin:0 0 8px }}
h2 {{ margin:32px 0 12px; font-size:20px }}
h3 {{ margin:0 0 8px; font-size:16px }}
.meta {{ color:var(--muted); font-size:13px; margin:4px 0 }}
.verdict {{ display:inline-block; padding:6px 14px; border-radius:999px; font-weight:700; font-size:14px; color:{fg}; background:{bg}; border:1px solid {fg}33 }}
.scorebox {{ display:flex; gap:24px; align-items:center; margin:24px 0; flex-wrap:wrap }}
.gauge {{ width:160px; height:90px; position:relative }}
.gauge svg {{ width:100% }}
.gauge .num {{ position:absolute; bottom:0; left:0; right:0; text-align:center; font-size:32px; font-weight:700; color:{gauge_color} }}
.kpis {{ display:flex; gap:16px; flex-wrap:wrap; flex:1 }}
.kpi {{ background:var(--card); border:1px solid var(--border); border-radius:8px; padding:12px 16px; min-width:140px }}
.kpi .label {{ font-size:12px; color:var(--muted); text-transform:uppercase; letter-spacing:0.5px }}
.kpi .val {{ font-size:22px; font-weight:700; margin-top:4px }}
.catrow {{ display:flex; align-items:center; gap:12px; margin:6px 0; font-size:13px }}
.catname {{ width:200px; color:var(--muted) }}
.catbar {{ flex:1; height:8px; background:var(--border); border-radius:4px; overflow:hidden }}
.catfill {{ display:block; height:100%; transition:width .4s }}
.catscore {{ width:36px; text-align:right; font-weight:600 }}
.sevrow {{ display:flex; align-items:center; gap:12px; margin:8px 0; font-size:13px }}
.sevlabel {{ width:80px; text-transform:uppercase; font-weight:600; color:var(--muted) }}
.sevbar {{ flex:1; height:14px; display:flex; border-radius:4px; overflow:hidden; background:var(--border) }}
.sevbar > span {{ display:inline-block; height:100% }}
.sevcount {{ width:120px; text-align:right; color:var(--muted); font-family:monospace }}
table {{ width:100%; border-collapse:collapse; margin:12px 0; font-size:13px; background:var(--card); border:1px solid var(--border); border-radius:8px; overflow:hidden }}
th, td {{ padding:10px 12px; text-align:left; border-bottom:1px solid var(--border); vertical-align:top }}
th {{ background:var(--bg); font-weight:600; font-size:12px; text-transform:uppercase; letter-spacing:0.3px; color:var(--muted) }}
tbody tr:last-child td {{ border-bottom:none }}
code {{ background:var(--bg); padding:2px 6px; border-radius:3px; font-size:12px }}
.badge {{ display:inline-block; padding:2px 8px; border-radius:999px; font-size:11px; font-weight:600; text-transform:uppercase }}
.status {{ font-size:18px; line-height:1 }}
.hint {{ color:var(--muted); font-size:12px; margin-top:4px }}
.src {{ font-size:11px; color:var(--muted); text-decoration:none }}
.src:hover {{ text-decoration:underline }}
.ev {{ font-family:monospace; font-size:11px; color:var(--muted); padding:2px 0 }}
details summary {{ cursor:pointer; color:var(--muted); font-size:12px; margin-top:4px }}
.card {{ background:var(--card); border:1px solid var(--border); border-left:4px solid #b3261e; border-radius:8px; padding:16px; margin:12px 0 }}
.tag {{ font-size:11px; color:var(--muted) }}
pre {{ background:var(--bg); border:1px solid var(--border); padding:8px; border-radius:4px; overflow:auto; font-size:11px }}
.filters {{ display:flex; gap:8px; margin:12px 0; flex-wrap:wrap }}
.filters button {{ background:var(--card); border:1px solid var(--border); padding:6px 12px; border-radius:6px; cursor:pointer; font-size:12px; color:var(--fg) }}
.filters button.active {{ background:var(--fg); color:var(--bg) }}
footer {{ margin-top:48px; padding-top:16px; border-top:1px solid var(--border); color:var(--muted); font-size:12px }}
.warn {{ background:#fff4dc; color:#8a4a00; padding:10px 14px; border-radius:6px; font-size:13px; border:1px solid #e8c98c }}
.srcbadge {{ display:inline-block; padding:1px 6px; border-radius:3px; font-size:10px; text-transform:uppercase; letter-spacing:0.3px }}
.srcbadge[data-src=interview] {{ background:#1463cc22; color:#1463cc }}
.srcbadge[data-src=code] {{ background:#0a7d3622; color:#0a7d36 }}
@media (prefers-color-scheme: dark) {{
  .warn {{ background:#3a2c10; color:#f0c570; border-color:#7a5c20 }}
}}
</style>
</head>
<body>
<div class=container>
<header>
  <h1>HIPAA Compliance Audit</h1>
  <p class=meta><code>{project}</code> · generated {generated}</p>
  <p><span class=verdict>{label}</span></p>
</header>

<div class=warn>
  ⚠️ Static analysis only. Does not replace a HITRUST or SOC 2 + HIPAA audit by a qualified auditor. Treat findings as signal, not legal certification.
</div>

<div class=scorebox>
  <div class=gauge>
    <svg viewBox="0 0 200 110">
      <path d="M10,100 A90,90 0 0,1 190,100" fill=none stroke="#e5e7eb" stroke-width=14 />
      <path d="M10,100 A90,90 0 0,1 190,100" fill=none stroke="{gauge_color}" stroke-width=14
            stroke-dasharray="{score * 2.83} 283" />
    </svg>
    <div class=num>{score}</div>
  </div>
  <div class=kpis>
    <div class=kpi><div class=label>Rules evaluated</div><div class=val>{audit['rules_total']}</div></div>
    <div class=kpi><div class=label>MUST failures</div><div class=val style="color:#b3261e">{len(fails_must)}</div></div>
    <div class=kpi><div class=label>SHOULD failures</div><div class=val style="color:#a86700">{len(fails_should)}</div></div>
    <div class=kpi><div class=label>Manual verify</div><div class=val style="color:#1463cc">{len(manuals)}</div></div>
    <div class=kpi><div class=label>Passing</div><div class=val style="color:#0a7d36">{len(passing)}</div></div>
    <div class=kpi><div class=label>Interview gaps</div><div class=val>{interview_failed}/{interview_count}</div></div>
  </div>
</div>

<h2>Category Scores</h2>
{cat_bars}

<h2>Severity Breakdown</h2>
<p class=meta>pass / fail / manual / skipped</p>
{sev_chart}

{("<h2>Top Failing Categories</h2><ul>" + top_fail_cats + "</ul>") if top_fail_cats else ""}

{vendor_html}

{("<h2>🔴 Critical — MUST Fix</h2>" + must_fix_html) if must_fix_html else ""}

<h2>All Findings</h2>
<div class=filters>
  <button class=active data-filter=all>All ({len(findings)})</button>
  <button data-filter=fail>Fail ({len(fails_must)+len(fails_should)})</button>
  <button data-filter=manual>Manual ({len(manuals)})</button>
  <button data-filter=pass>Pass ({len(passing)})</button>
  <button data-filter=must>MUST severity</button>
  <button data-filter=interview>Interview ({interview_count})</button>
  <button data-filter=code>Code scan</button>
</div>
<table id=findings>
  <thead><tr><th>Rule</th><th>Category</th><th>Severity</th><th>Status</th><th>Source</th><th>Detail</th></tr></thead>
  <tbody>{"".join(rows)}</tbody>
</table>

<footer>
  Generated by <code>hipaa-audit</code> skill. Citations: HHS, NIST 800-66 Rev 2, OCR Audit Protocol, 45 CFR Part 164. <br>
  This automated report is one input among many; pair with policies, BAAs, training records, and a qualified auditor before claiming legal compliance.
</footer>
</div>

<script>
document.querySelectorAll('.filters button').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('.filters button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const f = btn.dataset.filter;
    document.querySelectorAll('#findings tbody tr').forEach(tr => {{
      if (f === 'all') tr.style.display = '';
      else if (f === 'must') tr.style.display = (tr.dataset.severity === 'must') ? '' : 'none';
      else if (f === 'interview') tr.style.display = (tr.dataset.source === 'interview') ? '' : 'none';
      else if (f === 'code') tr.style.display = (tr.dataset.source === 'code') ? '' : 'none';
      else tr.style.display = (tr.dataset.status === f) ? '' : 'none';
    }});
  }});
}});
</script>
</body></html>
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    audit = json.loads(args.audit.read_text())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(audit))
    print(f"render_html → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
