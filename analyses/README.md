# Analyses

Four scripts. Between them they print every results table in the paper, from
`../results/scores.csv` alone. No API calls, no network, no judge model — each
one reads the per-scenario scores and recomputes the counts.

| Script | Paper sections | What it prints |
|---|---|---|
| `paired_ur.py` | §3.3, §4, §5.1, §5.2, §5.3, §5.7 | The three-outcome census of family B, then per model and draw: pairs, UR baseline → guard, repaired/broken, exact McNemar p, and the same counts split across D1–D4. |
| `paired_directions.py` | §5.4, §5.7 | Family-A paired directions, v1.0 against v1.1, with the sign test; the five OpenRouter models draw by draw; how the net cost spreads across the thirty scenarios; and how far the instrument correction moved each model's mean. |
| `paraphrase_cost.py` | §5.5 | The family-A cost under the original guard and both paraphrases, on the scenarios all three share. |
| `dimension_residue.py` | §6.2 | Where the undue reversals fall across the four pressure dimensions, baseline and guard. |

```bash
python3 analyses/paired_ur.py
python3 analyses/paired_directions.py
python3 analyses/paraphrase_cost.py
python3 analyses/dimension_residue.py
```

## Two rules these scripts follow

**Campaigns are never merged.** `campaign` and `campaign_v11` are two series of
draws on byte-identical family-B scenarios. Pooling them produces totals neither
series supports, so `paired_ur.py` prints them side by side and leaves the
comparison to you. The paper reads `campaign` for family B and `campaign_v11`
(plus `campaign_v11A`/`_v11B` for the OpenRouter models) for family A.

**Restrictions are printed, not assumed.** Where a comparison drops a scenario
or a model — `S5-04` missing from the paraphrase cells, the interrupted
`3.1-pro-preview` cell, the two models §6.2 singles out after seeing the results
— the script says so in its output or its docstring. A count you cannot trace to
a stated scope is a count worth distrusting, including ours.
