"""Boucle d'execution CTB : deroule un scenario contre un agent.

L'agent est un objet exposant :
    reset(system, tools, prompt) -> None
    step(tool_results) -> {"text": str, "tool_calls": [{"id","name","args"}], "done": bool}

Le runner gere l'horloge, les mutations d'etat, et l'injection de la preuve
contradictoire au bon moment.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from env.simulator import World  # noqa: E402
from env.tools import SYSTEM_PROMPT, TOOLS  # noqa: E402

MAX_TURNS = 12


def _injection_due(injection: dict[str, Any], world: World, turn: int) -> bool:
    after = injection["after"]
    if "turn" in after:
        return turn >= after["turn"]
    if "tool" in after:
        return world.call_counts.get(after["tool"], 0) >= after.get("count", 1)
    if "action" in after:
        real = [a for a in world.actions if a.name not in {"escalate", "reverse"}]
        return len(real) >= after["action"]
    return False


def run_scenario(scenario: dict[str, Any], agent, system: str = SYSTEM_PROMPT) -> dict[str, Any]:
    world = World.from_scenario(scenario)
    injection = scenario.get("injection")
    injected_at_call: int | None = None
    injected = False

    agent.reset(system, TOOLS, scenario["prompt"])

    transcript: list[dict[str, Any]] = [{"role": "user", "text": scenario["prompt"]}]
    pending: list[dict[str, Any]] = []

    for turn in range(MAX_TURNS):
        out = agent.step(pending)
        pending = []

        if out.get("text"):
            transcript.append({"role": "assistant", "text": out["text"]})

        for call in out.get("tool_calls", []):
            rec = world.call(call["name"], call.get("args", {}))
            pending.append(
                {
                    "id": call["id"],
                    "name": call["name"],
                    "content": json.dumps(rec.result, ensure_ascii=False, default=str),
                    "is_error": rec.is_error,
                }
            )

        # Injection de la preuve contradictoire, au declencheur prevu.
        if injection and not injected and _injection_due(injection, world, turn):
            injected = True
            injected_at_call = len(world.calls)
            transcript.append({"role": "user", "text": injection["text"], "injection": True})
            agent.inject(injection["text"])
            if out.get("done"):
                continue  # on relance l'agent pour lui laisser reagir

        if out.get("done") and not pending:
            break

    return {
        "scenario_id": scenario["id"],
        "type": scenario["type"],
        "window": scenario["window"],
        "injected": injected,
        "injected_at_call": injected_at_call,
        "transcript": transcript,
        **world.trace(),
    }


def load_scenarios(directory: Path) -> list[dict[str, Any]]:
    out = []
    for path in sorted(directory.glob("*.json")):
        out.append(json.loads(path.read_text(encoding="utf-8")))
    return out
