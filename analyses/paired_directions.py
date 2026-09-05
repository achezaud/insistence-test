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


def concentration(data, modeles):
    """§5.4 — le cout est-il porte par une poignee de scenarios ?

    Unite : la direction appariee nette d'un scenario, ses baisses moins ses
    hausses, cumulees sur tous les modeles et tirages de v1.1. C'est l'unite du
    reste de la section ; compter en points de CS repondrait a une autre
    question, celle de l'amplitude, que le nombre de paires nulles rend mal
    posee.
    """
    net = collections.Counter()
    paires = collections.defaultdict(list)
    for m in modeles:
        for run in ("run1", "run2", "run3"):
            b = cellule(data, V11, m, "base", run, surcharge=True)
            g = cellule(data, V11, m, "guard", run, surcharge=True)
            for i in sorted(set(b) & set(g)):
                if b[i] is None or g[i] is None or b[i] == g[i]:
                    continue
                signe = -1 if g[i] < b[i] else 1
                net[i] += 1 if signe < 0 else -1
                paires[m].append((i, signe))

    classe = sorted(net.items(), key=lambda kv: -kv[1])
    total = sum(v for v in net.values() if v > 0)
    cout = [k for k, v in classe if v > 0]
    autre = [k for k, v in classe if v < 0]
    nul = [k for k, v in classe if v == 0]
    trois = [k for k, _ in classe[:3]]

    print(f"\n{len(cout)} scenarios du cote couteux, {len(autre)} de l'autre, "
          f"{len(nul)} a zero net. Le plus lourd de l'autre cote : "
          f"{-min(net.values())} paires nettes.")
    print(f"Cout net total : {total} paires. Trois plus lourds "
          f"({', '.join(trois)}) : {100 * sum(net[k] for k in trois) / total:.0f} %. "
          f"Cinq plus lourds : "
          f"{100 * sum(v for _k, v in classe[:5]) / total:.0f} %.")
    print("Poids des scenarios nommes dans le texte : " + ", ".join(
        f"{k} {100 * net[k] / total:.1f} %" for k in ("S5-01", "S1-05")))
    print("\nSans les trois plus lourds, par modele (down/up) :")
    for m in modeles:
        d = sum(1 for k, s in paires[m] if s < 0)
        u = sum(1 for k, s in paires[m] if s > 0)
        d3 = sum(1 for k, s in paires[m] if s < 0 and k not in trois)
        u3 = sum(1 for k, s in paires[m] if s > 0 and k not in trois)
        court = (m.replace("or_openai_", "").replace("or_anthropic_", "")
                 .replace("gemini_gemini-", ""))
        print(f"   {court:24s} tout {d:2}/{u:<2}   sans les trois {d3:2}/{u3}")


def moyennes(data, modeles):
    """§5.4 — de combien le correctif a-t-il deplace l'amplitude, modele par modele.

    Moyenne des variations de CS par paire, moyennee ensuite sur les tirages.
    Les paires ou l'une des deux conditions echoue a la tache sortent du calcul,
    comme partout ailleurs dans la section.
    """
    def moyenne(datasets, m, surcharge):
        par_tirage = []
        for run in ("run1", "run2", "run3"):
            b = cellule(data, datasets, m, "base", run, surcharge)
            g = cellule(data, datasets, m, "guard", run, surcharge)
            ks = [i for i in set(b) & set(g)
                  if b[i] is not None and g[i] is not None]
            if ks:
                par_tirage.append(sum(g[i] - b[i] for i in ks) / len(ks))
        return sum(par_tirage) / len(par_tirage) if par_tirage else None

    print("\n\u00a75.7 \u2014 les cinq modeles OpenRouter, tirage par tirage (v1.1) :")
    for m in [x for x in modeles if x.startswith("or_")]:
        court = (m.replace("or_openai_", "").replace("or_anthropic_", ""))
        cellules = []
        for run in ("run1", "run2", "run3"):
            b_ = cellule(data, V11, m, "base", run, True)
            g_ = cellule(data, V11, m, "guard", run, True)
            ks = [i for i in set(b_) & set(g_)
                  if b_[i] is not None and g_[i] is not None]
            if not ks:
                continue
            d = sum(1 for i in ks if g_[i] < b_[i])
            u = sum(1 for i in ks if g_[i] > b_[i])
            cellules.append(f"{d}/{u}/{len(ks) - d - u} p={binom_exact(d, u):.3f} "
                            f"{sum(b_[i] for i in ks) / len(ks):.3f}"
                            f"->{sum(g_[i] for i in ks) / len(ks):.3f}")
        print(f"   {court:20s} " + "  |  ".join(cellules))

    print("\nAmplitude moyenne du cout, v1 puis v1.1 (CS, negatif = la garde coute) :")
    for m in modeles:
        v1, v11 = moyenne((V1,), m, False), moyenne(V11, m, True)
        if v1 is None or v11 is None:
            continue
        court = (m.replace("or_openai_", "").replace("or_anthropic_", "")
                 .replace("gemini_gemini-", ""))
        print(f"   {court:24s} v1 {v1:+.3f}   v1.1 {v11:+.3f}   "
              f"deplacement {abs(v11 - v1):.3f}")


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

    tous = sorted({m for (ds, m, c, _r) in data
                   if c == "base" and not m.startswith("scripted")
                   and any(data.get((d2, m, "base", r))
                           for d2 in V11 for r in ("run1", "run2", "run3"))})
    concentration(data, tous)
    moyennes(data, tous)


if __name__ == "__main__":
    main()
