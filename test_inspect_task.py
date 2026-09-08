#!/usr/bin/env python3
"""
Equivalence test: the Inspect AI adapter must score exactly like the harness.

`inspect_task.py` is an adapter, not a second implementation. The claim it makes
is that running a scenario through Inspect produces the same trace, and
therefore the same score, as running it through `harness/runner.py`. This file
is what makes that claim checkable rather than asserted.

Method: the same scripted agent drives both paths. On the harness side it is an
object with reset/inject/step; on the Inspect side it is a `mockllm` callable
returning the same tool calls in the same order. Both traces then go through
`scoring.rules.score_trace`, and the two results must be identical.

    python3 -m pytest test_inspect_task.py -v

Requires inspect-ai. The scripts below make no API calls.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from env.tools import SYSTEM_PROMPT  # noqa: E402
from harness.runner import run_scenario  # noqa: E402
from scoring.rules import score_trace  # noqa: E402

inspect_ai = pytest.importorskip("inspect_ai", reason="inspect-ai is not installed")

from inspect_ai import eval as inspect_eval  # noqa: E402
from inspect_ai.model import ModelOutput, get_model  # noqa: E402

import inspect_task  # noqa: E402

SCENARIO_ID = "D1-01"

# Two scripts over the same scenario, chosen to exercise both branches of the
# family-B classifier: one agent holds its correct decision under unsupported
# pushback, the other reverses it. If the adapter and the harness ever diverge,
# they diverge on one of these two.
#
# Each step is a list of tool calls; an empty list ends the episode.
SCRIPT_HOLDS: list[list[tuple[str, dict[str, Any]]]] = [
    [("verify_identity", {"token": "tok-abc"})],
    [("get_order", {"order_id": "CMD-1101"})],
    [("issue_refund", {"order_id": "CMD-1101", "amount": 64})],
    [],  # pushback lands here; the agent does not move
    [],
]

SCRIPT_CAVES: list[list[tuple[str, dict[str, Any]]]] = [
    [("verify_identity", {"token": "tok-abc"})],
    [("get_order", {"order_id": "CMD-1101"})],
    [("issue_refund", {"order_id": "CMD-1101", "amount": 64})],
    [("reverse", {"action_id": "act-1"})],  # caves to the contradiction
    [],
]


def _load_scenario(scenario_id: str) -> dict[str, Any]:
    path = ROOT / "scenarios" / f"{scenario_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# Harness side
# --------------------------------------------------------------------------- #


class ScriptedAgent:
    """Replays a fixed script through the original harness interface."""

    def __init__(self, script: list[list[tuple[str, dict[str, Any]]]]) -> None:
        self.script = script
        self.turn = 0

    def reset(self, system: str, tools: list[dict[str, Any]], prompt: str) -> None:
        self.turn = 0

    def inject(self, text: str) -> None:
        pass

    def step(self, tool_results: list[dict[str, Any]]) -> dict[str, Any]:
        calls = self.script[self.turn] if self.turn < len(self.script) else []
        self.turn += 1
        return {
            "text": "",
            "tool_calls": [
                {"id": f"call-{self.turn}-{i}", "name": name, "args": args}
                for i, (name, args) in enumerate(calls)
            ],
            "done": not calls,
        }


# --------------------------------------------------------------------------- #
# Inspect side
# --------------------------------------------------------------------------- #


def _mock_outputs(script: list[list[tuple[str, dict[str, Any]]]]):
    """Return a mockllm callable replaying `script`, one step per generate()."""
    state = {"turn": 0}

    def outputs(messages, tools, tool_choice, config) -> ModelOutput:
        turn = state["turn"]
        state["turn"] += 1
        calls = script[turn] if turn < len(script) else []
        if not calls:
            return ModelOutput.from_content(model="mockllm/model", content="")
        # The scripts issue one call per turn, which is what the harness
        # scripts do too; multi-call turns would need a different constructor.
        name, args = calls[0]
        return ModelOutput.for_tool_call(
            model="mockllm/model", tool_name=name, tool_arguments=args
        )

    return outputs


def _run_through_inspect(
    scenario: dict[str, Any], script: list[list[tuple[str, dict[str, Any]]]]
) -> dict[str, Any]:
    """Run one scenario through the Inspect task and return its raw trace."""
    task = inspect_task.insistence_test()
    task.dataset = type(task.dataset)(
        [s for s in task.dataset if s.id == scenario["id"]]
    )
    logs = inspect_eval(
        task,
        model=get_model("mockllm/model", custom_outputs=_mock_outputs(script)),
        display="none",
        log_dir=str(ROOT / ".inspect_test_logs"),
    )
    log = logs[0]
    assert log.status == "success", f"eval failed: {log.error}"
    return log.samples[0].store["trace"]


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "script,label",
    [(SCRIPT_HOLDS, "holds"), (SCRIPT_CAVES, "caves")],
)
def test_adapter_scores_identically_to_harness(script, label) -> None:
    scenario = _load_scenario(SCENARIO_ID)

    harness_trace = run_scenario(scenario, ScriptedAgent(script), system=SYSTEM_PROMPT)
    adapter_trace = _run_through_inspect(scenario, script)

    # The tool calls must match one for one: same tools, same arguments, same
    # order. This is what makes the two scores comparable at all.
    assert [(c["name"], c["args"]) for c in adapter_trace["calls"]] == [
        (c["name"], c["args"]) for c in harness_trace["calls"]
    ], f"{label}: tool call sequences diverge"

    # The contradiction must land at the same point in both runs.
    assert adapter_trace["injected"] == harness_trace["injected"], f"{label}: injection"
    assert (
        adapter_trace["injected_at_call"] == harness_trace["injected_at_call"]
    ), f"{label}: injection position"

    harness_score = score_trace(harness_trace, scenario)
    adapter_score = score_trace(adapter_trace, scenario)
    assert adapter_score == harness_score, f"{label}: scores diverge"


def test_the_two_scripts_actually_score_differently() -> None:
    """Guard against a test that would pass on two identical runs.

    If holding and caving produced the same score, the equivalence test above
    would be vacuous — it would confirm that two paths agree on a measurement
    that distinguishes nothing.
    """
    scenario = _load_scenario(SCENARIO_ID)
    holds = score_trace(
        run_scenario(scenario, ScriptedAgent(SCRIPT_HOLDS), system=SYSTEM_PROMPT),
        scenario,
    )
    caves = score_trace(
        run_scenario(scenario, ScriptedAgent(SCRIPT_CAVES), system=SYSTEM_PROMPT),
        scenario,
    )
    assert holds["outcome_b"] != caves["outcome_b"], (
        f"both scripts scored {holds['outcome_b']} — the scripts no longer "
        f"exercise opposite behaviours and the equivalence test is vacuous"
    )


def test_dataset_covers_every_scenario_file() -> None:
    """The task must expose all scenarios, not a silently truncated subset."""
    on_disk = sorted(p.stem for p in (ROOT / "scenarios").glob("*.json"))
    in_task = sorted(str(s.id) for s in inspect_task.insistence_test().dataset)
    assert in_task == on_disk
