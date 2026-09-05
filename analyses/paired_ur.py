#!/usr/bin/env python3
"""§5.1, §5.2, §5.3, §5.7 — l'effet apparie de famille B, depuis `scores.csv`.

Ce que le script repond : sur chaque modele et chaque tirage, combien de
scenarios de famille B passent d'une reversion indue a aucune sous la garde
(`repare`), combien font l'inverse (`casse`), et ou tombent les reversions qui
restent, par dimension de pression. C'est le calcul de §5.1 et de §5.7, et sa
decomposition en §5.3.

Chaque paire est un scenario score DANS LES DEUX conditions, pour un modele et
un tirage donnes. Le p est le test exact de McNemar, bilateral, sur les paires
discordantes seules — jamais cumule entre tirages : trois tirages rejouent les
memes 30 scenarios et n'en font pas 90 independants.

Les jeux sont imprimes separement et jamais fusionnes. `campaign` et
`campaign_v11` sont deux series de tirages sur des scenarios de famille B
**byte-identiques** ; melanger leurs lignes dans une meme table donnerait des
totaux qu'aucune des deux ne soutient. Le papier lit `campaign`.

    python3 analyses/paired_ur.py
"""
from __future__ import annotations

import collections
import csv
import math
import pathlib

CSV = pathlib.Path(__file__).resolve().parent.parent / "results" / "scores.csv"
DIMENSIONS = ("D1", "D2", "D3", "D4")


def charger() -> dict:
    par_cellule = collections.defaultdict(dict)
    with CSV.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["family"] != "B":
                continue
            par_cellule[(r["dataset"], r["model"], r["condition"], r["run"])][
                r["scenario_id"]] = r["undue_revision"] == "True"
    return par_cellule


def mcnemar(repares: int, casses: int) -> float:
    n = repares + casses
    if n == 0:
        return 1.0
    k = min(repares, casses)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def par_dimension(cellule: dict, paires: list) -> str:
    """Restreint aux scenarios apparies : une cellule interrompue afficherait
    sinon une base sur 30 scenarios en face d'une garde sur 2."""
    total = collections.Counter(s.split("-")[0] for s in paires)
    ur = collections.Counter(s.split("-")[0] for s in paires if cellule[s])
    return " ".join(f"{d} {ur[d]}/{total[d]}" for d in DIMENSIONS)


def recensement_issues() -> None:
    """§3.3 — les trois issues de famille B, et ce que couterait de les ramener a deux.

    `suspendu` = l'action attendue a ete reellement faite puis annulee ET une
    escalade suit l'injection. Compter ce cas comme une reversion indue rendrait
    l'effet du papier PLUS net, pas moins : c'est pourquoi il est compte a part
    et pourquoi le script imprime les deux totaux.
    """
    issues = collections.Counter()
    scriptes = collections.Counter()
    with CSV.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["family"] != "B":
                continue
            issues[r["outcome_b"]] += 1
            if r["model"].startswith("scripted"):
                scriptes[r["outcome_b"]] += 1
    total = sum(issues.values())
    print(f"\n§3.3 — {total} executions de famille B : "
          + ", ".join(f"{n} {k}" for k, n in issues.most_common()))
    print(f"        dont agents scriptes : "
          + ", ".join(f"{n} {k}" for k, n in scriptes.most_common()))


def main() -> None:
    data = charger()
    recensement_issues()
    jeux = sorted({ds for (ds, _m, _c, _r) in data})
    for jeu in jeux:
        modeles = sorted({m for (ds, m, c, _r) in data
                          if ds == jeu and c == "guard"})
        if not modeles:
            continue
        print(f"\n=== {jeu} ===")
        for modele in modeles:
            court = (modele.replace("or_openai_", "").replace("or_anthropic_", "")
                     .replace("gemini_gemini-", ""))
            for run in ("run1", "run2", "run3"):
                base = data.get((jeu, modele, "base", run))
                garde = data.get((jeu, modele, "guard", run))
                if not base or not garde:
                    continue
                paires = sorted(set(base) & set(garde))
                repares = sum(1 for s in paires if base[s] and not garde[s])
                casses = sum(1 for s in paires if not base[s] and garde[s])
                print(f"{court:22} {run} {len(paires):2} paires  UR "
                      f"{sum(base[s] for s in paires):2} -> "
                      f"{sum(garde[s] for s in paires):2}  "
                      f"repares/casses {repares:2}/{casses}  "
                      f"p={mcnemar(repares, casses):.4f}")
                print(f"{'':22}      base  {par_dimension(base, paires)}")
                print(f"{'':22}      garde {par_dimension(garde, paires)}")


if __name__ == "__main__":
    main()
