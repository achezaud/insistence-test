#!/usr/bin/env python3
"""The ten-model summary table at the top of the README, from `scores.csv`.

WHY THIS SCRIPT EXISTS
----------------------
The README used to carry one hand-written table covering four Gemini models,
a hundred lines down. Ten models were measured. A reader who wanted the whole
picture had to open the paper, and a number typed into prose ages the moment
the next campaign runs. This regenerates the table instead:

    python3 analyses/summary_table.py

Paste the output between the two markers in README.md. Any number in that
table that this script does not produce is a number nobody can check.

WHICH DATA, AND WHY THAT ONE
----------------------------
Family B — the 30 scenarios where reversing is *always* wrong, because the
system of record never changed. That is the measure the test is named after.

All ten models are read from the `campaign` dataset, and from that one only.
The v1.1 repair of 2026-09-03 fixed a fixture contradiction confined to
family A; family B is byte-identical between the two versions and was never
re-run. Using a single dataset therefore costs nothing in currency and avoids
mixing two instrument versions in one table — the error class that cost the
day of 2026-09-05.

Cells with fewer than 30 scored scenarios are dropped, and the drop is
printed: a partial draw compared against a full one is not a comparison.
`gemini-3.1-pro-preview` has no guarded draw at all and is excluded here; it
survives in `scores.csv` and in the paper.
"""
from __future__ import annotations

import collections
import csv
import pathlib

CSV = pathlib.Path(__file__).resolve().parent.parent / "results" / "scores.csv"
DATASET = "campaign"
FAMILY = "B"
N_SCENARIOS = 30

# Display name and provider. The provider column is the point of §5.7: the
# result is a multi-provider one, and a table that hides that reads as a
# Google result with extras.
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
CONTROLS = [
    ("scripted-careful", "scripted control, careful", "—"),
    ("scripted-naive", "scripted control, naive", "—"),
]


def load() -> dict:
    cells: dict[tuple[str, str, str], dict[str, str]] = collections.defaultdict(dict)
    with CSV.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["dataset"] != DATASET or r["family"] != FAMILY:
                continue
            if r["condition"] not in ("base", "guard"):
                continue
            cells[(r["model"], r["condition"], r["run"])][r["scenario_id"]] = r
    return cells


def draws(cells, model: str, condition: str) -> tuple[list[int], int]:
    """Undue reversals per draw, and the number of draws dropped as partial."""
    counts, dropped = [], 0
    for (m, c, _run), scored in cells.items():
        if m != model or c != condition:
            continue
        if len(scored) < N_SCENARIOS:
            dropped += 1
            continue
        counts.append(sum(1 for v in scored.values() if v["undue_revision"] == "True"))
    return sorted(counts), dropped


def span(counts: list[int]) -> str:
    if not counts:
        return "—"
    lo, hi = counts[0], counts[-1]
    return str(lo) if lo == hi else f"{lo}–{hi}"


def main() -> int:
    cells = load()
    dropped_total = 0
    print(f"| Model | Provider | Baseline | With guard | Draws |")
    print(f"|---|---|---|---|---|")
    for key, name, provider in MODELS + CONTROLS:
        base, d1 = draws(cells, key, "base")
        guard, d2 = draws(cells, key, "guard")
        dropped_total += d1 + d2
        if not base:
            continue
        # Bold a guard that reaches zero: it is the claim of the two lines.
        g = span(guard)
        if guard and guard[-1] == 0:
            g = f"**{g}**"
        n = min(len(base), len(guard)) if guard else len(base)
        print(f"| `{name}` | {provider} | {span(base)} | {g} | {n} |")

    if dropped_total:
        print(f"\n[{dropped_total} partial draw(s) dropped: fewer than "
              f"{N_SCENARIOS} scored scenarios]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
