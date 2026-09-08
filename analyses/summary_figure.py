#!/usr/bin/env python3
"""The README figure, written as SVG from `scores.csv`. Standard library only.

WHY SVG, AND WHY BY HAND
------------------------
A table does not travel. It cannot go into a slide, a thread, or a post, and a
benchmark that nobody can show is a benchmark nobody repeats. The figure is the
object that travels.

It is emitted as raw SVG rather than drawn with a plotting library because this
repository promises that `insistence_test.py` runs with nothing installed, and
adding matplotlib to regenerate a picture would put a 30 MB dependency behind a
claim about the data. Everything here is stdlib.

    python3 analyses/summary_figure.py > figure.svg

TWO RENDERING CONSTRAINTS THAT SHAPED THE OUTPUT
------------------------------------------------
1. GitHub strips `<style>` blocks and scripts from SVG shown in a README. Every
   colour, font and weight below is therefore a presentation attribute on the
   element itself, never CSS. Do not "tidy" these into a stylesheet: it renders
   locally and silently loses all styling on GitHub.
2. GitHub serves READMEs in both light and dark themes, and a figure with no
   background is transparent — dark text on a dark page is invisible. Hence the
   explicit white plate. It looks slightly inset in dark mode; that is the
   deliberate trade against being unreadable for half the readers.

WHAT IS PLOTTED
---------------
Family B, the 30 scenarios where the record never changed so reversing is
always wrong — the same data as the README table, from the same single dataset,
for the reasons given in `summary_table.py`.

Each row is one model. The bar runs from its baseline mean to its guarded mean;
individual draws are drawn as ticks so the reader sees the spread rather than
trusting an average. A row that barely moves is meant to be as visible as a row
that collapses to zero: `gpt-5-nano` not moving is a result, not a blemish.
"""
from __future__ import annotations

import collections
import csv
import pathlib
import sys

CSV = pathlib.Path(__file__).resolve().parent.parent / "results" / "scores.csv"
DATASET, FAMILY, N = "campaign", "B", 30

MODELS = [
    ("or_anthropic_claude-sonnet-5", "claude-sonnet-5", "Anthropic"),
    ("or_anthropic_claude-haiku-4.5", "claude-haiku-4.5", "Anthropic"),
    ("gemini_gemini-3.8-flash", "gemini-3.8-flash", "Google"),
    ("gemini_gemini-3.7-flash", "gemini-3.7-flash", "Google"),
    ("gemini_gemini-3.6-flash", "gemini-3.6-flash", "Google"),
    ("gemini_gemini-3.5-flash-lite", "gemini-3.5-flash-lite", "Google"),
    ("gemini_gemini-3.1-flash-lite", "gemini-3.1-flash-lite", "Google"),
    ("or_openai_gpt-5.1", "gpt-5.1", "OpenAI"),
    ("or_openai_gpt-5-mini", "gpt-5-mini", "OpenAI"),
    ("or_openai_gpt-5-nano", "gpt-5-nano", "OpenAI"),
]

INK = "#1F2328"        # text, on the white plate
MUTED = "#6E7781"      # axis, ticks, secondary text
BASE = "#BC4C00"       # baseline: the failure being measured
GUARD = "#1A7F37"      # guarded: the two lines doing their job
INERT = "#82071E"      # a guard that does not move the number
PLATE = "#FFFFFF"
GRID = "#E4E8EC"

W = 900                 # wide enough for the subtitle to fit on one line
L, R = 205, 76          # left: longest model name; right: the "guard inert" tag
TOP, BOT = 92, 80   # BOT holds the axis label and the provenance line
ROW_H = 31
GROUP_GAP = 24          # a provider label lives in this gap, not on a data row
XMAX = 20               # no model exceeds 18 of 30


def load() -> dict:
    cells: dict[tuple[str, str, str], dict[str, str]] = collections.defaultdict(dict)
    with CSV.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["dataset"] != DATASET or r["family"] != FAMILY:
                continue
            if r["condition"] in ("base", "guard"):
                cells[(r["model"], r["condition"], r["run"])][r["scenario_id"]] = r
    return cells


def draws(cells, model: str, cond: str) -> list[int]:
    out = []
    for (m, c, _run), scored in cells.items():
        if m == model and c == cond and len(scored) >= N:
            out.append(sum(1 for v in scored.values() if v["undue_revision"] == "True"))
    return sorted(out)


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main() -> int:
    cells = load()
    rows = []
    for key, name, provider in MODELS:
        b, g = draws(cells, key, "base"), draws(cells, key, "guard")
        if b and g:
            rows.append((name, provider, b, g))

    # Lay out first, then size the canvas to the result. Provider labels sit in
    # a gap of their own: drawn in the left margin beside a data row, they
    # collide with the longer model names.
    ys: list[float] = []
    labels: list[tuple[str, float]] = []
    y = TOP
    last = None
    for _name, provider, _b, _g in rows:
        if provider != last:
            if last is not None:
                y += GROUP_GAP
            labels.append((provider, y - 8))
            last = provider
        ys.append(y + ROW_H / 2)
        y += ROW_H
    H = int(y + BOT)
    plot_w = W - L - R

    def x(v: float) -> float:
        return L + plot_w * v / XMAX

    o: list[str] = []
    a = o.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
      f'width="{W}" height="{H}" font-family="-apple-system,BlinkMacSystemFont,'
      f'Segoe UI,Helvetica,Arial,sans-serif" role="img" '
      f'aria-label="Undue reversals out of 30 scenarios, baseline versus guarded, '
      f'ten models across three providers.">')
    a(f'<rect width="{W}" height="{H}" fill="{PLATE}"/>')

    a(f'<text x="{L}" y="34" font-size="17" font-weight="600" fill="{INK}">'
      f'Does the agent undo a correct decision when pushed?</text>')
    a(f'<text x="{L}" y="56" font-size="12.5" fill="{MUTED}">'
      f'Undue reversals out of 30 scenarios where the record never changed, so '
      f'reversing is always wrong.</text>')

    # Legend, placed before the plot so the reader has the key on first pass.
    lx = L
    a(f'<circle cx="{lx+5}" cy="72" r="5" fill="{BASE}"/>')
    a(f'<text x="{lx+17}" y="76" font-size="12" fill="{INK}">baseline</text>')
    a(f'<circle cx="{lx+92}" cy="72" r="5" fill="{GUARD}"/>')
    a(f'<text x="{lx+104}" y="76" font-size="12" fill="{INK}">with the two-line '
      f'guard</text>')
    a(f'<text x="{lx+250}" y="76" font-size="12" fill="{MUTED}">'
      f'ticks are individual draws</text>')

    # Vertical grid + axis labels.
    for v in range(0, XMAX + 1, 5):
        a(f'<line x1="{x(v):.1f}" y1="{TOP-8}" x2="{x(v):.1f}" y2="{H-BOT+6}" '
          f'stroke="{GRID}" stroke-width="1"/>')
        a(f'<text x="{x(v):.1f}" y="{H-BOT+24}" font-size="11.5" fill="{MUTED}" '
          f'text-anchor="middle">{v}</text>')
    a(f'<text x="{x(XMAX/2):.1f}" y="{H-BOT+46}" font-size="11.5" fill="{MUTED}" '
      f'text-anchor="middle">undue reversals (of 30)</text>')

    for provider, ly in labels:
        a(f'<text x="14" y="{ly:.1f}" font-size="10.5" font-weight="600" '
          f'fill="{MUTED}" letter-spacing="0.6">{esc(provider.upper())}</text>')

    for i, (name, provider, b, g) in enumerate(rows):
        cy = ys[i]
        mb, mg = sum(b) / len(b), sum(g) / len(g)
        moved = mb - mg
        # A guard that moves the number by less than one scenario out of 30 has
        # not moved it. Saying so in colour is the honest reading.
        colour = GUARD if moved >= 1 else INERT

        a(f'<text x="{L-14}" y="{cy+4:.1f}" font-size="12.5" fill="{INK}" '
          f'text-anchor="end" font-family="ui-monospace,SFMono-Regular,Menlo,'
          f'monospace">{esc(name)}</text>')

        a(f'<line x1="{x(mg):.1f}" y1="{cy:.1f}" x2="{x(mb):.1f}" y2="{cy:.1f}" '
          f'stroke="{colour}" stroke-width="2.5" opacity="0.35" '
          f'stroke-linecap="round"/>')
        for v in b:
            a(f'<line x1="{x(v):.1f}" y1="{cy-6:.1f}" x2="{x(v):.1f}" '
              f'y2="{cy+6:.1f}" stroke="{BASE}" stroke-width="1" opacity="0.55"/>')
        for v in g:
            a(f'<line x1="{x(v):.1f}" y1="{cy-6:.1f}" x2="{x(v):.1f}" '
              f'y2="{cy+6:.1f}" stroke="{colour}" stroke-width="1" opacity="0.55"/>')
        a(f'<circle cx="{x(mb):.1f}" cy="{cy:.1f}" r="5.5" fill="{BASE}"/>')
        a(f'<circle cx="{x(mg):.1f}" cy="{cy:.1f}" r="5.5" fill="{colour}"/>')

        if moved < 1:
            a(f'<text x="{x(max(mb, mg))+14:.1f}" y="{cy+4:.1f}" font-size="11.5" '
              f'font-weight="600" fill="{INERT}">guard inert</text>')
        elif mg == 0:
            a(f'<text x="{x(0)-0:.1f}" y="{cy-11:.1f}" font-size="11" '
              f'fill="{GUARD}" font-weight="600">0</text>')

    a(f'<text x="{L}" y="{H-12}" font-size="10.5" fill="{MUTED}">'
      f'Dots are means across draws; ticks are the draws. '
      f'analyses/summary_figure.py, from results/scores.csv.</text>')
    a('</svg>')
    sys.stdout.write("\n".join(o) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
