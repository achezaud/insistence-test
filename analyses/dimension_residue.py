#!/usr/bin/env python3
"""§6.2 — ou tombent les reversions indues, par dimension, depuis `scores.csv`.

Ce que le script repond : la garde deplace-t-elle la repartition des reversions
indues entre les quatre dimensions de pression, ou se contente-t-elle d'en
retirer en masse en laissant la meme forme ?

Une reversion indue (`undue_revision`) est une annulation d'action correcte sans
fait verifiable a l'appui. Elle se lit sur la trace d'appels, sans modele juge.
D1 (pression sociale) et D3 (fausse autorite) ne portent aucune pretention de
fait ; D2 (source faible) et D4 (doute de soi) en portent une. Le partage
D1uD3 / D2uD4 est donc epistemique, pas cosmetique.

Perimetre : famille B (les 30 scenarios `D*`), tous les tirages. Les agents
scriptes sont des temoins du plancher de bruit, pas des modeles, et sont exclus ;
`gemini-3.1-pro-preview` aussi — sa cellule sous garde s'est interrompue a
2 scenarios sur 30 et il ne figure dans aucune table du papier.

Les conditions paraphrasees (`guard_p1`, `guard_p2`) sont comptees a part : le
chiffre du papier est celui de la garde d'origine.

    python3 analyses/dimension_residue.py
"""
from __future__ import annotations

import collections
import csv
import pathlib

CSV = pathlib.Path(__file__).resolve().parent.parent / "results" / "scores.csv"

# Les deux modeles ou la garde agit sans tout effacer : elle n'est ni inerte
# (3.1-flash-lite, gpt-5-nano) ni totale (les autres). Sous-ensemble CHOISI
# APRES COUP — c'est pourquoi le papier en donne le compte et jamais un taux.
PARTIELS = ("gemini_gemini-3.5-flash-lite", "or_openai_gpt-5.1")
EXCLUS = ("scripted-naive", "scripted-careful", "gemini_gemini-3.1-pro-preview")


def charger() -> dict:
    par_cle: dict[tuple[str, str], collections.Counter] = collections.defaultdict(
        collections.Counter
    )
    with CSV.open(encoding="utf-8") as fh:
        for ligne in csv.DictReader(fh):
            if ligne["family"] != "B" or ligne["model"] in EXCLUS:
                continue
            if ligne["undue_revision"] != "True":
                continue
            dimension = ligne["scenario_id"].split("-")[0]
            for cle in ((ligne["condition"], "TOUS MODELES"),
                        (ligne["condition"], ligne["model"])):
                par_cle[cle][dimension] += 1
                par_cle[cle]["ur"] += 1
                if dimension in ("D1", "D3"):
                    par_cle[cle]["d13"] += 1
    return par_cle


def main() -> None:
    par_cle = charger()
    print(f"{'condition':10} {'modele':32} {'UR':>4}  D1  D2  D3  D4   D1uD3")
    for condition, modele in sorted(par_cle):
        c = par_cle[(condition, modele)]
        pct = 100 * c["d13"] / c["ur"] if c["ur"] else 0.0
        print(f"{condition:10} {modele:32} {c['ur']:4} {c['D1']:3} {c['D2']:3} "
              f"{c['D3']:3} {c['D4']:3}   {c['d13']}/{c['ur']} ({pct:.0f}%)")

    ur = sum(par_cle[("guard", m)]["ur"] for m in PARTIELS)
    d13 = sum(par_cle[("guard", m)]["d13"] for m in PARTIELS)
    noms = " + ".join(m.split("_")[-1] for m in PARTIELS)
    print(f"\n6.2 — sous garde, {noms} : D1uD3 = {d13}/{ur}")


if __name__ == "__main__":
    main()
