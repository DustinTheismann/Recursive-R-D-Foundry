"""Self-contained HTML dashboard for a RunPack.

No external dependencies, no JS frameworks — everything is hand-rolled HTML + SVG
so the artifact opens anywhere. Shows the recursive loop's vital signs: champion
trajectory, HALF-LIFE state timeline, capability-vs-assurance, the QD archive
heatmap, the lineage DAG, gate outcomes, scientist reviews, and the meta-gate log.
"""
from __future__ import annotations

import html
from typing import Any

_CSS = """
body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#0d1117;color:#c9d1d9}
.wrap{max-width:1100px;margin:0 auto;padding:24px}
h1{font-size:22px;margin:0 0 4px} h2{font-size:15px;color:#58a6ff;margin:26px 0 8px;border-bottom:1px solid #21262d;padding-bottom:4px}
.sub{color:#8b949e;font-size:13px;margin-bottom:16px}
.cards{display:flex;flex-wrap:wrap;gap:12px}
.card{background:#161b22;border:1px solid #21262d;border-radius:8px;padding:12px 16px;min-width:150px}
.card .v{font-size:22px;font-weight:600} .card .l{color:#8b949e;font-size:12px}
table{border-collapse:collapse;width:100%;font-size:12px} td,th{border:1px solid #21262d;padding:4px 8px;text-align:left}
th{background:#161b22;color:#8b949e} .ok{color:#3fb950} .no{color:#f85149} .mono{font-family:ui-monospace,monospace;font-size:11px}
.state-GREEN{color:#3fb950}.state-AMBER{color:#d29922}.state-RED{color:#f85149}.state-BLACK{color:#f85149;font-weight:700}
.chip{display:inline-block;padding:1px 7px;border-radius:10px;font-size:11px;margin:1px}
svg{background:#0d1117}
.pill{background:#161b22;border:1px solid #21262d;border-radius:6px;padding:8px 10px;margin:6px 0;font-size:12px}
"""


def _esc(x: Any) -> str:
    return html.escape(str(x))


def _cards(rp: dict) -> str:
    reg = rp["successor_registry"]
    hl = rp["half_life"]["snapshot"]
    cells = [
        ("Champion fitness", round(reg.get("champion_fitness") or 0, 4)),
        ("Promotions", reg.get("n_promotions", 0)),
        ("Candidates", rp.get("n_candidates", 0)),
        ("HALF-LIFE", f'<span class="state-{hl["state"]}">{hl["state"]}</span>'),
        ("Assurance", hl.get("cumulative_assurance")),
        ("Assurance debt", hl.get("debt")),
        ("QD coverage", rp["qd_archive"].get("coverage")),
        ("QD score", rp["qd_archive"].get("qd_score")),
    ]
    return '<div class="cards">' + "".join(
        f'<div class="card"><div class="v">{v}</div><div class="l">{_esc(l)}</div></div>'
        for l, v in cells) + "</div>"


def _line_chart(rp: dict) -> str:
    cycles = rp["cycles"]
    if not cycles:
        return ""
    W, H, pad = 1040, 220, 36
    xs = [c["cycle"] for c in cycles]
    series = {
        "capability": ([c["capability_index"] for c in cycles], "#58a6ff"),
        "assurance": ([c["assurance_index"] for c in cycles], "#3fb950"),
        "entropy": ([c["population_entropy"] for c in cycles], "#d29922"),
    }
    vmax = max(1e-6, max(max(v) for v, _ in series.values()))
    def X(i): return pad + (W - 2 * pad) * (i / max(1, len(xs) - 1))
    def Y(v): return H - pad - (H - 2 * pad) * (v / vmax)
    parts = [f'<svg width="{W}" height="{H}">']
    parts.append(f'<line x1="{pad}" y1="{H-pad}" x2="{W-pad}" y2="{H-pad}" stroke="#30363d"/>')
    for name, (vals, color) in series.items():
        pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(vals))
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2"/>')
    legend = "  ".join(f'<span class="chip" style="background:{c}22;color:{c}">{n}</span>'
                       for n, (_, c) in series.items())
    parts.append("</svg>")
    return legend + "<br>" + "".join(parts)


def _halflife_timeline(rp: dict) -> str:
    colors = {"GREEN": "#3fb950", "AMBER": "#d29922", "RED": "#f85149", "BLACK": "#8b0000"}
    chips = "".join(
        f'<span class="chip" style="background:{colors.get(c["half_life_state"],"#444")}33;'
        f'color:{colors.get(c["half_life_state"],"#ccc")}">c{c["cycle"]}:{c["half_life_state"]}</span>'
        for c in rp["cycles"])
    return chips


def _qd_heatmap(rp: dict) -> str:
    qd = rp["qd_archive"]
    grid = qd.get("grid", 8)
    cells = qd.get("cells", {})
    cell = 26
    W = H = grid * cell + 2
    parts = [f'<svg width="{W}" height="{H}">']
    for key, e in cells.items():
        try:
            i, j = (int(x) for x in key.split(","))
        except Exception:
            continue
        f = e["fitness"]
        g = int(60 + 160 * min(1.0, f))
        parts.append(f'<rect x="{i*cell+1}" y="{(grid-1-j)*cell+1}" width="{cell-2}" '
                     f'height="{cell-2}" fill="rgb(40,{g},90)"><title>{_esc(key)} '
                     f'fit={f} {_esc(e["origin"])}</title></rect>')
    parts.append("</svg>")
    legend = '<div class="sub">x = packing tightness · y = openness · brighter = fitter elite</div>'
    return legend + "".join(parts)


def _lineage_dag(rp: dict) -> str:
    g = rp["lineage_graph"]
    nodes = g["nodes"]
    edges = g["edges"]
    # layer by generation
    layers: dict[int, list[str]] = {}
    for cid, a in nodes.items():
        layers.setdefault(int(a.get("gen", 0)), []).append(cid)
    if not layers:
        return ""
    maxlayer = max(layers)
    W = 1040
    rowh = 70
    H = (maxlayer + 1) * rowh + 30
    pos: dict[str, tuple[float, float]] = {}
    for gen, cids in layers.items():
        cids = sorted(cids)
        for idx, cid in enumerate(cids):
            x = 40 + (W - 80) * ((idx + 1) / (len(cids) + 1))
            y = 24 + gen * rowh
            pos[cid] = (x, y)
    parts = [f'<svg width="{W}" height="{H}">']
    for p, c in edges:
        if p in pos and c in pos:
            x1, y1 = pos[p]; x2, y2 = pos[c]
            parts.append(f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" '
                         f'stroke="#30363d" stroke-width="1"/>')
    for cid, (x, y) in pos.items():
        fit = nodes[cid].get("fitness", 0) or 0
        gcol = int(60 + 160 * min(1.0, fit))
        parts.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="5" fill="rgb(40,{gcol},90)">'
                     f'<title>{_esc(cid)} {_esc(nodes[cid].get("origin"))} fit={fit}</title></circle>')
    parts.append("</svg>")
    return '<div class="sub">rows = generations · brighter = fitter</div>' + "".join(parts)


def _promotions(rp: dict) -> str:
    rows = ["<tr><th>cid</th><th>kind</th><th>fitness</th><th>Δ</th><th>causal</th>"
            "<th>HALF-LIFE</th><th>novelty</th></tr>"]
    for p in rp["successor_registry"]["promotions"]:
        rep = p.get("report") or {}
        rows.append(
            f'<tr><td class="mono">{_esc(p["candidate"]["cid"][:14])}</td>'
            f'<td>{_esc(p["kind"])}</td>'
            f'<td>{_esc(p["result"]["fitness"])}</td>'
            f'<td>{_esc(rep.get("fitness_delta",""))}</td>'
            f'<td>{_esc(rep.get("causal_effect",""))}</td>'
            f'<td class="state-{rep.get("half_life_state","GREEN")}">{_esc(rep.get("half_life_state",""))}</td>'
            f'<td>{_esc(rep.get("novelty_score",""))}</td></tr>')
    return "<table>" + "".join(rows) + "</table>"


def _reviews(rp: dict) -> str:
    out = []
    for r in rp.get("scientist_reviews", []):
        out.append(f'<div class="pill"><b>gen {_esc(r.get("generation"))}</b> — '
                   f'{_esc(r.get("hypothesis"))}<br><i>{_esc(r.get("conclusion"))}</i></div>')
    return "".join(out) or '<div class="sub">no reviews</div>'


def _meta(rp: dict) -> str:
    out = []
    for m in rp.get("meta_gate_log", []):
        cls = "ok" if m.get("allowed") else "no"
        out.append(f'<div class="pill"><span class="{cls}">{_esc(m.get("action"))}</span> '
                   f'({_esc(m.get("trigger"))}) — allowed={_esc(m.get("allowed"))} '
                   f'{_esc(m.get("blocked_reason",""))}</div>')
    return "".join(out) or '<div class="sub">no gate adjustments</div>'


def _seal(rp: dict) -> str:
    priors = rp["seal_training"]["priors"]
    bars = []
    for g, v in priors.items():
        w = int(120 * v / 2.0)
        bars.append(f'<div style="margin:3px 0">{_esc(g)} '
                    f'<span style="display:inline-block;height:10px;width:{w}px;'
                    f'background:#58a6ff;border-radius:3px"></span> {v}</div>')
    return (f'<div class="sub">{rp["seal_training"]["n_examples"]} mined training examples · '
            f'per-gene exploration priors:</div>' + "".join(bars))


def render_html(rp: dict) -> str:
    reg = rp["successor_registry"]
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Recursive R&D Foundry — RunPack</title><style>{_CSS}</style></head>
<body><div class="wrap">
<h1>Recursive R&D Foundry — RunPack Dashboard</h1>
<div class="sub">lineage root <span class="mono">{_esc(rp.get('lineage_root',''))}</span>
 · seed {_esc(rp.get('root_seed'))} · champion <span class="mono">{_esc(reg.get('champion'))}</span></div>
{_cards(rp)}
<h2>Capability vs Assurance vs Diversity</h2>{_line_chart(rp)}
<h2>HALF-LIFE state timeline</h2>{_halflife_timeline(rp)}
<h2>Quality-Diversity archive (MAP-Elites)</h2>{_qd_heatmap(rp)}
<h2>Lineage DAG</h2>{_lineage_dag(rp)}
<h2>Promotions</h2>{_promotions(rp)}
<h2>AI-Scientist reviews</h2>{_reviews(rp)}
<h2>Meta-gate (recursive governance)</h2>{_meta(rp)}
<h2>SEAL failure-mined self-training</h2>{_seal(rp)}
</div></body></html>"""


def save_dashboard(rp: dict, path: str) -> str:
    import os
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write(render_html(rp))
    return path
