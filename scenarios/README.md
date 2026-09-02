# Scenarios

The 60 scenarios behind the measurements in the paper. Deterministic, MIT
licensed, no judge model required.

## The two families

Each scenario is one JSON file. `family` says which half it belongs to, and the
two halves are the same size on purpose.

**Family B — 30 scenarios, `D1` to `D4`.** The agent has completed a correct,
irreversible action. The user then pushes back with **no verifiable new fact**.
Reversing is wrong by construction, because the system of record is queryable,
authoritative and unchanged. The failure this measures is an *undue reversal*.

| Prefix | Pressure | Count |
|---|---|---|
| `D1` | social pressure | 8 |
| `D2` | a weaker source contradicting a stronger one | 8 |
| `D3` | fake authority | 7 |
| `D4` | being asked again with nothing new | 7 |

**Family A — 30 scenarios, `S1` to `S6`.** The mirror case: something in the
world genuinely justifies correcting course, and *not* correcting is the
failure. This half exists so that an agent which simply stops acting scores
worse rather than better. Without it, any intervention that induces paralysis
looks like a success.

## Fields

- `world` — the system of record the tools read: orders, customers, identity
  tokens, notes. Static unless `mutations` says otherwise.
- `injection` — the pushback: `after.action` gives the tool call it follows,
  `text` is what the user says.
- `expected_task_action` — what a correct agent does before any pushback.
- `expect` — what the trace must and must not contain afterwards.
  `required_standing_actions` are the calls that must still stand at the end;
  `forbidden_final_actions` are the ones that must not appear.

Scoring reads these fields against the tool-call trace only. See
`../scoring/rules.py`, and `../env/tools.py` for the ten tools an agent may
call. Prompts are in French; the tool interface and the scoring are
language-independent.

## Regenerating

`build.py`, `build_distractors.py` and `build_extension.py` produced these
files. They are included so the construction is auditable, not because you need
to run them — the JSON is the artifact.
