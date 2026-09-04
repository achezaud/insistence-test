#!/usr/bin/env python3
"""Exporte les scores par scenario, sans les traces.

Pourquoi ce fichier existe : §5.4 compare, scenario par scenario, le CS sous
garde au CS de base. Le recalculer ne demande pas les traces completes
(37 Mo, ~7 900 fichiers) mais seulement le CS de chaque (jeu, modele,
condition, tirage, scenario) — 481 Ko. C'est ce que ce script extrait, et
c'est ce que le depot publie.

Le CSV n'est pas un resume : il contient CHAQUE cellule scoree, y compris
celles a `cs` vide (echec de tache), qui sortent des paires mais dont
l'absence doit rester visible. Une cellule absente du CSV est une execution
qui n'a jamais abouti, pas une execution omise — sept d'entre elles ont
suffi a fausser un recalcul de §5.4.

Ce depot ne contient pas les traces brutes, donc le script n'y regenere rien :
il est publie pour que la provenance de `results/scores.csv` soit lisible, et
pour qui rejoue la campagne chez lui.

    python3 tools/export_scores.py --results <arbre de traces> --out results/scores.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib

RACINES = ("campaign", "campaign_v11", "campaign_v11A", "campaign_v11B")


def lignes(results: pathlib.Path):
    for nom in RACINES:
        racine = results / nom
        if not racine.is_dir():
            continue
        for bloc in sorted(racine.glob("*__*")):
            modele, condition = bloc.name.rsplit("__", 1)
            for tirage in sorted(bloc.glob("run*")):
                for f in sorted(tirage.glob("*.json")):
                    s = json.load(open(f)).get("score", {})
                    yield {
                        "dataset": nom,
                        "model": modele,
                        "condition": condition,
                        "run": tirage.name,
                        "scenario_id": s.get("scenario_id", f.stem),
                        "family": s.get("family"),
                        "cs": s.get("cs"),
                        "task_failed": s.get("task_failed"),
                    }


def main() -> None:
    ici = pathlib.Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--results", default=str(ici / "results"))
    p.add_argument("--out", default=str(ici / "public" / "results" / "scores.csv"))
    a = p.parse_args()

    rows = list(lignes(pathlib.Path(a.results)))
    if not rows:
        raise SystemExit(f"aucun resultat sous {a.results}")
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} lignes -> {out} ({out.stat().st_size / 1024:.0f} Ko)")


if __name__ == "__main__":
    main()
