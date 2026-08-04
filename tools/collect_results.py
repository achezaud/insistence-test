#!/usr/bin/env python3
"""Regenerate the community results table in README.md from GitHub issues.

Reads issues labelled `result`, parses the reported numbers, and rewrites the
table between the two marker comments in README.md. Idempotent: run it as often
as you like, it always rebuilds the table from scratch.

    python3 tools/collect_results.py --repo owner/name          # live
    python3 tools/collect_results.py --from-json fixtures.json   # offline

Needs the `gh` CLI authenticated for live mode. Nothing else — stdlib only.

Issue body format (anything else is skipped and reported):

    model: gpt-5
    prompt: SYSTEM_BASE
    baseline: 3/4
    guard: 1/4
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys

START = "<!-- results:start -->"
END = "<!-- results:end -->"

SEED_ROW = "| `gemini-3.6-flash` | `SYSTEM_BASE` | 3/4 | 0–1/4 | this repo |"

KEYS = "model|prompt|baseline|guard"
# Free-form body: `model: gpt-5`
INLINE = re.compile(rf"^\s*({KEYS})\s*:\s*(.+?)\s*$", re.I | re.M)
# GitHub issue *form* body: `### model` then the value on a later line.
# The two formats are different and both turn up in practice, so accept both.
HEADING = re.compile(rf"^#{{1,6}}\s*({KEYS})\s*$\n+(.+?)\s*$", re.I | re.M)
SCORE = re.compile(r"^\d+\s*/\s*\d+$")


def parse_issue(issue: dict) -> dict | None:
    """Pull the four fields out of an issue body. None if it doesn't parse."""
    body = issue.get("body") or ""
    found = {k.lower(): v for k, v in INLINE.findall(body)}
    # Headings win: if someone used the form, that's the authoritative answer.
    found.update({k.lower(): v for k, v in HEADING.findall(body)})
    # A form field left empty renders as "_No response_".
    found = {k: v for k, v in found.items() if v.strip().lower() != "_no response_"}
    model, baseline, guard = found.get("model"), found.get("baseline"), found.get("guard")
    if not (model and baseline and guard):
        return None
    if not (SCORE.match(baseline) and SCORE.match(guard)):
        return None
    author = (issue.get("author") or {}).get("login") or "unknown"
    return {
        "model": model,
        "prompt": found.get("prompt") or "SYSTEM_BASE",
        "baseline": baseline,
        "guard": guard,
        "author": author,
        "number": issue.get("number"),
    }


def fetch_issues(repo: str) -> list[dict]:
    out = subprocess.run(
        ["gh", "issue", "list", "--repo", repo, "--label", "result",
         "--state", "all", "--limit", "300",
         "--json", "number,body,author"],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        raise SystemExit(f"gh failed: {out.stderr.strip()}")
    return json.loads(out.stdout or "[]")


def render(rows: list[dict], repo: str | None) -> str:
    lines = [
        "| Model | prompt | baseline | with guard | contributed by |",
        "|---|---|---|---|---|",
        SEED_ROW,
    ]
    for r in sorted(rows, key=lambda r: r["model"]):
        who = f"[@{r['author']}]" + (
            f"(https://github.com/{repo}/issues/{r['number']})" if repo and r["number"] else ""
        )
        prompt = r["prompt"]
        prompt_cell = f"`{prompt}`" if prompt.upper() == "SYSTEM_BASE" else prompt
        lines.append(
            f"| `{r['model']}` | {prompt_cell} | {r['baseline']} | {r['guard']} | {who} |"
        )
    return "\n".join(lines)


def splice(readme: str, table: str) -> str:
    if START not in readme or END not in readme:
        raise SystemExit(f"markers {START} / {END} not found in README.md")
    head, rest = readme.split(START, 1)
    _, tail = rest.split(END, 1)
    return f"{head}{START}\n{table}\n{END}{tail}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--repo", help="owner/name — fetches via the gh CLI")
    src.add_argument("--from-json", help="path to a JSON array of issues (offline/testing)")
    ap.add_argument("--readme", default="README.md")
    ap.add_argument("--dry-run", action="store_true", help="print, don't write")
    args = ap.parse_args()

    issues = (
        json.loads(pathlib.Path(args.from_json).read_text(encoding="utf-8"))
        if args.from_json else fetch_issues(args.repo)
    )

    rows, skipped = [], []
    for issue in issues:
        parsed = parse_issue(issue)
        (rows.append(parsed) if parsed else skipped.append(issue.get("number")))

    table = render(rows, args.repo)
    if args.dry_run:
        print(table)
    else:
        path = pathlib.Path(args.readme)
        path.write_text(splice(path.read_text(encoding="utf-8"), table), encoding="utf-8")
        print(f"{path}: {len(rows)} result(s) written")

    if skipped:
        print(f"skipped (unparseable): {skipped}", file=sys.stderr)


if __name__ == "__main__":
    main()
