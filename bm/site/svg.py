"""Hand-built SVG charts. Colors are CSS variables so light/dark themes swap in
one place; every chart carries a hover layer (see TOOLTIP_JS in build.py) and
a caption with its source line."""
from __future__ import annotations

import html
import json

W, H = 720, 300
M = {"l": 52, "r": 20, "t": 16, "b": 34}


def esc(s) -> str:
    return html.escape(str(s), quote=True)


class Scale:
    def __init__(self, d0, d1, r0, r1):
        self.d0, self.d1, self.r0, self.r1 = d0, d1, r0, r1

    def __call__(self, v):
        if self.d1 == self.d0:
            return self.r0
        return self.r0 + (v - self.d0) * (self.r1 - self.r0) / (self.d1 - self.d0)


def _path(pts, sx, sy):
    return "M" + " L".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in pts)


def line_chart(cid: str, *, series=(), bands=(), x_domain, y_domain, x_ticks, y_ticks,
               y_fmt="{:.0f}", x_fmt=None, hrefs=(), vrefs=(), labels=(), height=H,
               aria="") -> str:
    """series: [{name, points:[(x,y)], color, dash?, width?, tt_fmt?}]
    bands: [{lower:[(x,y)], upper:[(x,y)], color, name}]
    hrefs/vrefs: [{at, label, color?}]  labels: [{x, y, text, anchor?, color?}]"""
    w, h = W, height
    sx = Scale(*x_domain, M["l"], w - M["r"])
    sy = Scale(*y_domain, h - M["b"], M["t"])
    out = [f'<svg class="chart" id="{esc(cid)}" viewBox="0 0 {w} {h}" role="img" '
           f'aria-label="{esc(aria)}" preserveAspectRatio="xMidYMid meet">']
    # grid + y ticks
    for v in y_ticks:
        y = sy(v)
        out.append(f'<line class="grid" x1="{M["l"]}" x2="{w - M["r"]}" y1="{y:.1f}" y2="{y:.1f}"/>')
        out.append(f'<text class="tick" x="{M["l"] - 8}" y="{y + 4:.1f}" text-anchor="end">{esc(y_fmt.format(v))}</text>')
    for v, lab in x_ticks:
        x = sx(v)
        out.append(f'<line class="axis" x1="{x:.1f}" x2="{x:.1f}" y1="{h - M["b"]}" y2="{h - M["b"] + 5}"/>')
        out.append(f'<text class="tick" x="{x:.1f}" y="{h - M["b"] + 19}" text-anchor="middle">{esc(lab)}</text>')
    out.append(f'<line class="axis" x1="{M["l"]}" x2="{w - M["r"]}" y1="{h - M["b"]}" y2="{h - M["b"]}"/>')
    for b in bands:
        pts = [(x, y) for x, y in b["upper"]] + [(x, y) for x, y in reversed(b["lower"])]
        d = _path(pts, sx, sy) + " Z"
        out.append(f'<path class="band" d="{d}" style="fill:var({b["color"]})"><title>{esc(b.get("name",""))}</title></path>')
    for r in vrefs:
        x = sx(r["at"])
        out.append(f'<line class="ref" x1="{x:.1f}" x2="{x:.1f}" y1="{M["t"]}" y2="{h - M["b"]}"/>')
        if r.get("label"):
            out.append(f'<text class="reflabel" x="{x + 5:.1f}" y="{M["t"] + 11}">{esc(r["label"])}</text>')
    for r in hrefs:
        y = sy(r["at"])
        out.append(f'<line class="ref" x1="{M["l"]}" x2="{w - M["r"]}" y1="{y:.1f}" y2="{y:.1f}"/>')
        if r.get("label"):
            out.append(f'<text class="reflabel" x="{w - M["r"] - 4}" y="{y - 6:.1f}" text-anchor="end">{esc(r["label"])}</text>')
    tt = {"series": []}
    for s in series:
        if not s["points"]:
            continue
        dash = ' stroke-dasharray="5 4"' if s.get("dash") else ""
        out.append(f'<path class="line" d="{_path(s["points"], sx, sy)}" '
                   f'style="stroke:var({s["color"]});stroke-width:{s.get("width", 2)}"{dash}/>')
        lx, ly = s["points"][-1]
        out.append(f'<circle class="end" cx="{sx(lx):.1f}" cy="{sy(ly):.1f}" r="4" style="fill:var({s["color"]})"/>')
        fmt = s.get("tt_fmt", y_fmt)
        tt["series"].append({
            "name": s["name"], "color": s["color"],
            "px": [round(sx(x), 1) for x, _ in s["points"]],
            "py": [round(sy(y), 1) for _, y in s["points"]],
            "xl": [x_fmt(x) if x_fmt else str(x) for x, _ in s["points"]],
            "yl": [fmt.format(y) for _, y in s["points"]],
        })
    for lab in labels:
        anchor = lab.get("anchor", "start")
        out.append(f'<text class="dlabel" x="{sx(lab["x"]):.1f}" y="{sy(lab["y"]):.1f}" '
                   f'text-anchor="{anchor}" style="fill:var({lab.get("color", "--ink-2")})">{esc(lab["text"])}</text>')
    out.append(f'<rect class="hit" x="{M["l"]}" y="{M["t"]}" width="{w - M["l"] - M["r"]}" height="{h - M["t"] - M["b"]}"/>')
    out.append(f'<g class="hover" visibility="hidden"><line class="xhair" y1="{M["t"]}" y2="{h - M["b"]}"/></g>')
    out.append("</svg>")
    out.append(f'<script type="application/json" class="tt-data" data-for="{esc(cid)}">{json.dumps(tt)}</script>')
    return "".join(out)


def stacked_bar(rows: list[dict], order: list[tuple[str, str]], width=W) -> str:
    """rows: [{label, counts:{cat:n}}]; order: [(cat, css var)]. Horizontal,
    direct-labelled segments with 2px gaps."""
    bar_h, gap_y, left, right = 30, 22, 70, 16
    h = len(rows) * (bar_h + gap_y) + 30
    out = [f'<svg class="chart stack" viewBox="0 0 {width} {h}" role="img" aria-label="Generational makeup of Congress">']
    for i, r in enumerate(rows):
        total = sum(r["counts"].values())
        y = 10 + i * (bar_h + gap_y)
        out.append(f'<text class="rowlabel" x="0" y="{y + bar_h / 2 + 5}">{esc(r["label"])}</text>')
        x = left
        span = width - left - right
        for cat, var in order:
            n = r["counts"].get(cat, 0)
            if not n:
                continue
            wseg = span * n / total
            pct = 100 * n / total
            out.append(f'<rect x="{x:.1f}" y="{y}" width="{max(wseg - 2, 1):.1f}" height="{bar_h}" rx="3" '
                       f'style="fill:var({var})"><title>{esc(cat)}: {n} of {total} ({pct:.0f}%)</title></rect>')
            if wseg > 34:
                out.append(f'<text class="seglabel" x="{x + wseg / 2 - 1:.1f}" y="{y + bar_h / 2 + 5}" text-anchor="middle">{n}</text>')
            x += wseg
    out.append("</svg>")
    return "".join(out)
