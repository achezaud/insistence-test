#!/usr/bin/env python3
"""§5.4 — directions appariees de famille A, recalculees depuis `scores.csv`.

Ce que le script repond : le correctif de l'instrument change-t-il la DIRECTION
du cout de la garde, ou seulement son amplitude ? Une direction qui tient est un
resultat robuste au defaut ; une direction qui bascule dirait que §5.4 mesurait
en partie le defaut.

Chaque paire est un scenario de famille A score DANS LES DEUX conditions, pour
un modele et un tirage donnes. Un scenario a `cs` vide (echec de tache) sort de
la paire : comparer un CS a une absence de CS n'a pas de sens. Le nombre de
paires est imprime pour que cet abandon reste visible.

    python3 analyses/paired_directions.py
"""
from __future__ import annotations

import collections
import csv
import math
import pathlib

CSV = pathlib.Path(__file__).resolve().parent.parent / "results" / "scores.csv"

V1 = "campaign"
# Gemini a ete re-joue sur les 60 scenarios, OpenRouter sur la famille A seule.
V11 = ("campaign_v11", "campaign_v11A")
# S5-04 a ete refait apres reparation du scenario : le registre mute apres
# `grant_gesture`, si bien que relire `get_order` etablit que le geste est alle
# au mauvais client. Les cellules OpenRouter de v11A portent l'ancienne version.
# La surcharge REMPLACE, et elle AJOUTE : sept cellules de v11A n'ont aucun
# resultat pour S5-04 — l'execution n'y a jamais abouti — et un simple
# remplacement les laisserait sans le scenario, donc hors comparaison appariee,
# ce qui est exactement le biais que la reparation supprime.
SURCHARGE = "campaign_v11B"


def charger() -> dict:
    par_cellule: dict[tuple[str, str, str, str], dict[str, float | None]] = (
        collections.defaultdict(dict))
    with CSV.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["family"] != "A":
                continue
            cs = r["cs"]
            par_cellule[(r["dataset"], r["model"], r["condition"], r["run"])][
                r["scenario_id"]] = None if cs in ("", "None") else float(cs)
    return par_cellule


def cellule(data, datasets, modele, condition, run, surcharge: bool):
    for ds in datasets:
        vals = data.get((ds, modele, condition, run))
        if not vals:
            continue
        vals = dict(vals)
        if surcharge:
            vals.update(data.get((SURCHARGE, modele, condition, run), {}))
        return vals
    return {}


def binom_exact(b: int, c: int) -> float:
    """p bilateral, test des signes sur les paires discordantes."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def directions(data, datasets, modele, run, surcharge=False):
    b = cellule(data, datasets, modele, "base", run, surcharge)
    g = cellule(data, datasets, modele, "guard", run, surcharge)
    d = u = e = 0
    for i in sorted(set(b) & set(g)):
        if b[i] is None or g[i] is None:
            continue
        if g[i] < b[i]:
            d += 1
        elif g[i] > b[i]:
            u += 1
        else:
            e += 1
    return d, u, e


def main() -> None:
    data = charger()
    modeles = sorted({m for (ds, m, c, _r) in data
                      if ds == V1 and c == "base" and not m.startswith("scripted")})

    print(f"{'modele':30s} {'run':5s} {'v1 (down/up/eg)':>17} {'p':>7}   "
          f"{'v1.1 (down/up/eg)':>17} {'p':>7}   verdict")
    print("-" * 104)
    for m in modeles:
        for run in ("run1", "run2", "run3"):
            if not any(data.get((ds, m, "base", run)) for ds in V11):
                continue
            d1, u1, e1 = directions(data, (V1,), m, run)
            d2, u2, e2 = directions(data, V11, m, run, surcharge=True)
            if d1 + u1 + e1 == 0 or d2 + u2 + e2 == 0:
                continue
            p1, p2 = binom_exact(d1, u1), binom_exact(d2, u2)
            # Le verdict porte sur la DIRECTION, pas sur l'amplitude : c'est
            # elle que §5.4 rapporte, et elle seule qui peut invalider la
            # section.
            if (d1 > u1) == (d2 > u2):
                verdict = "direction tenue"
            elif d1 == u1 or d2 == u2:
                verdict = "indecis"
            else:
                verdict = "!! DIRECTION INVERSEE"
            court = (m.replace("or_openai_", "").replace("or_anthropic_", "")
                     .replace("gemini_gemini-", ""))
            print(f"{court:30s} {run:5s} {f'{d1}/{u1}/{e1}':>17} {p1:7.4f}   "
                  f"{f'{d2}/{u2}/{e2}':>17} {p2:7.4f}   {verdict}")
    print("-" * 104)
    print("down = CS baisse sous garde (la garde coute) | up = CS monte")
    print("p = test exact des signes sur les paires discordantes, bilateral")
    print("La famille B n'apparait pas : identique entre v1 et v1.1, non re-jouee.")


if __name__ == "__main__":
    main()
