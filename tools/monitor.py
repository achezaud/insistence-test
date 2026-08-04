#!/usr/bin/env python3
"""Daily launch watch: what changed on the repo since the last check.

    python3 tools/monitor.py --repo owner/name

Prints a short report and remembers the state in tools/monitor_state.json, so
each run tells you the delta rather than the total. Needs the `gh` CLI. Nothing
else — stdlib only.

Add --collect to also regenerate the README results table when new results
land, so a contributed run shows up in the table without you doing anything.

This file is gitignored state, not published output.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

STATE = pathlib.Path(__file__).with_name("monitor_state.json")


def gh(args: list[str]) -> object:
    out = subprocess.run(["gh", *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"gh failed: {' '.join(args)}\n{out.stderr.strip()}")
    return json.loads(out.stdout or "null")


def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", required=True, help="owner/name")
    ap.add_argument("--collect", action="store_true",
                    help="regenerate the README table if new results arrived")
    ap.add_argument("--readme", default="README.md")
    args = ap.parse_args()

    repo = gh(["repo", "view", args.repo, "--json", "stargazerCount,forkCount"])
    issues = gh(["issue", "list", "--repo", args.repo, "--state", "all",
                 "--limit", "300", "--json", "number,title,labels,author,createdAt"])

    prev = load_state()
    now = {
        "stars": repo["stargazerCount"],
        "forks": repo["forkCount"],
        "issues": [i["number"] for i in issues],
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    def delta(key: str) -> str:
        if key not in prev:
            return ""
        d = now[key] - prev[key]
        return f"  ({d:+d})" if d else "  (=)"

    print(f"\n{args.repo} — {now['checked_at']}")
    if prev.get("checked_at"):
        print(f"since {prev['checked_at']}")
    print()
    print(f"  stars   {now['stars']}{delta('stars')}")
    print(f"  forks   {now['forks']}{delta('forks')}")

    first_run = prev.get("issues") is None
    # On the first run everything looks new. Record the baseline, don't dump it.
    new = [] if first_run else [
        i for i in issues if i["number"] not in set(prev.get("issues", []))
    ]
    results = [i for i in new if any(l["name"] == "result" for l in i.get("labels", []))]
    other = [i for i in new if i not in results]

    if first_run:
        print(f"  issues  {len(issues)}  (first run — baseline recorded, nothing to diff)")
    else:
        print(f"  issues  {len(issues)}  ({len(new)} new)")

    if results:
        print(f"\n  NEW RESULTS ({len(results)}) — someone ran it on their model:")
        for i in results:
            print(f"    #{i['number']} {i['title']}  @{i['author']['login']}")
    if other:
        print(f"\n  other new issues ({len(other)}):")
        for i in other:
            print(f"    #{i['number']} {i['title']}  @{i['author']['login']}")

    if not new and prev.get("checked_at"):
        print("\n  nothing new.")

    STATE.write_text(json.dumps(now, indent=1), encoding="utf-8")

    if args.collect and results:
        print("\n  regenerating the results table…")
        subprocess.run([sys.executable,
                        str(pathlib.Path(__file__).with_name("collect_results.py")),
                        "--repo", args.repo, "--readme", args.readme], check=False)


if __name__ == "__main__":
    main()
