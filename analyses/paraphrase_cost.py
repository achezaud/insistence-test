#!/usr/bin/env python3
"""§5.5 — le cout de la garde tient-il sous les deux paraphrases ?

Les cellules paraphrasees (`guard_p1`, `guard_p2`) ont ete jouees sans `S5-04`,
qui a ete repare apres elles. Comparer la garde d'origine sur 30 scenarios aux
paraphrases sur 29 melangerait l'effet de la formulation et l'effet du scenario
manquant, donc les trois formulations sont comparees ici sur les **29 scenarios
communs**, et le script imprime ce nombre pour que la restriction reste visible.

Famille A seulement : le versant famille B de §5.5 se lit dans les colonnes UR,
qui ne dependent pas du CS.

    python3 analyses/paraphrase_cost.py
"""
from __future__ import annotations

import collections
import csv
import math
import pathlib

CSV = pathlib.Path(__file__).resolve().parent.parent / "results" / "scores.csv"
JEU = "campaign_v11"
FORMULATIONS = ("guard", "guard_p1", "guard_p2")
TIRAGES = ("run1", "run2")


def charger() -> dict:
    par_cellule = collections.defaultdict(dict)
    with CSV.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["family"] != "A" or r["dataset"] != JEU:
                continue
            cs = r["cs"]
            par_cellule[(r["model"], r["condition"], r["run"])][r["scenario_id"]] = (
                None if cs in ("", "None") else float(cs))
    return par_cellule


def signes(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)


def main() -> None:
    data = charger()
    modeles = sorted({m for (m, c, _r) in data if c == "guard_p1"})
    for modele in modeles:
        communs = None
        for cond in FORMULATIONS:
            for run in TIRAGES:
                cle = set(data.get((modele, cond, run), {}))
                communs = cle if communs is None else communs & cle
        if not communs:
            continue
        court = modele.replace("gemini_gemini-", "")
        print(f"\n{court} — {len(communs)} scenarios communs aux trois "
              f"formulations ({'avec' if 'S5-04' in communs else 'sans'} S5-04)")
        for cond in FORMULATIONS:
            bas = hauts = 0
            detail = []
            for run in TIRAGES:
                b = data.get((modele, "base", run), {})
                g = data.get((modele, cond, run), {})
                ks = [k for k in sorted(communs)
                      if b.get(k) is not None and g.get(k) is not None]
                d = sum(1 for k in ks if g[k] < b[k])
                u = sum(1 for k in ks if g[k] > b[k])
                bas += d
                hauts += u
                detail.append(f"{run} {d}/{u} p={signes(d, u):.4f} "
                              f"CS {sum(b[k] for k in ks) / len(ks):.3f}"
                              f"->{sum(g[k] for k in ks) / len(ks):.3f}")
            print(f"   {cond:9} total {bas}/{hauts}   " + " | ".join(detail))


if __name__ == "__main__":
    main()
