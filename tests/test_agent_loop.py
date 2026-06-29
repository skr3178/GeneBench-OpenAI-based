"""Agent-loop + sandbox tests using a scripted mock model (no API calls)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from genebench.agent import AgentConfig, run_agent
from genebench.models.base import ModelResponse, ToolCall
from genebench.problem import Problem
from genebench.runner import run_problem
from genebench.sandbox.local import LocalSandbox

PROBLEM_DIR = Path(__file__).resolve().parents[1] / "problems" / "ldl_gwas_followup"


class MockModel:
    """Replays a fixed list of (tool_calls, stop_reason) steps."""
    name = "mock"

    def __init__(self, steps):
        self._steps = steps
        self._i = 0

    def create(self, system, messages, tools, max_tokens=16000):
        calls, stop = self._steps[min(self._i, len(self._steps) - 1)]
        self._i += 1
        return ModelResponse(text="", tool_calls=calls, stop_reason=stop,
                             assistant_content="(mock)", input_tokens=10, output_tokens=50)

    def tool_result_message(self, results):
        return {"role": "user", "content": [r["content"] for r in results]}


def _writer_step(answer: dict):
    code = ("import json\n"
            f"json.dump({json.dumps(answer)}, open('eval_answer.json','w'))\n"
            "print('wrote answer')")
    return ([ToolCall(id="t1", name="run_python", input={"code": code})], "tool_use")


def test_sandbox_executes_against_staged_files(tmp_path):
    problem = Problem.load(PROBLEM_DIR)
    problem.generate(seed=7, outdir=tmp_path)
    sb = LocalSandbox()
    try:
        sb.setup([(tmp_path / n, n) for n in problem.staged_files])
        res = sb.run_python(
            "import pandas as pd; "
            "print(pd.read_csv('cohort.tsv.gz', sep='\\t').shape[0])")
        assert res.returncode == 0
        assert res.stdout.strip() == "520"
    finally:
        sb.cleanup()


@pytest.fixture(scope="module")
def prepared(tmp_path_factory):
    data_dir = tmp_path_factory.mktemp("ldl_agent")
    problem = Problem.load(PROBLEM_DIR)
    problem.generate(seed=7, outdir=data_dir)
    truth = problem.graded_truth(data_dir)
    return problem, data_dir, truth


def test_agent_writes_correct_answer_passes(prepared):
    problem, data_dir, truth = prepared
    model = MockModel([_writer_step(truth), ([], "end_turn")])
    res = run_agent(problem, data_dir, model, config=AgentConfig(max_steps=5))
    assert res.status == "answered"
    assert res.answer == truth
    assert res.output_tokens == 50  # one model turn before the answer was detected


def test_agent_wrong_answer_is_gradeable(prepared):
    problem, data_dir, truth = prepared
    wrong = dict(truth, lead_variant_index=19)  # skip-HWE style wrong variant
    model = MockModel([_writer_step(wrong), ([], "end_turn")])
    res = run_agent(problem, data_dir, model, config=AgentConfig(max_steps=5))
    assert res.status == "answered"
    assert res.answer["lead_variant_index"] == 19


def test_agent_no_answer_when_model_stops(prepared):
    problem, data_dir, _ = prepared
    model = MockModel([([], "end_turn")])
    res = run_agent(problem, data_dir, model, config=AgentConfig(max_steps=5))
    assert res.status == "no_answer"
    assert res.answer is None


def test_runner_grades_replicates(monkeypatch):
    problem = Problem.load(PROBLEM_DIR)

    # a model that, each rep, writes the rep's own computed truth (always passes)
    class TruthModel:
        name = "truth-mock"

        def create(self, system, messages, tools, max_tokens=16000):
            # recover the truth from the staged files via the reference pipeline,
            # then emit a run_python step that writes exactly that answer.
            # (the data dir is the sandbox cwd; reference_solution is importable
            #  from the problem dir.)
            code = (
                "import sys, json\n"
                f"sys.path.insert(0, {str(problem.directory)!r})\n"
                "from reference_solution import reference_solution\n"
                "ans = reference_solution('.')\n"
                "json.dump({k: ans[k] for k in "
                "['lead_variant_index','lead_beta_mgdl','source_mean_untreated_ldl_mgdl']}, "
                "open('eval_answer.json','w'))\n"
            )
            return ModelResponse(text="", tool_calls=[ToolCall("t", "run_python", {"code": code})],
                                 stop_reason="tool_use", assistant_content="m",
                                 input_tokens=5, output_tokens=20)

        def tool_result_message(self, results):
            return {"role": "user", "content": [r["content"] for r in results]}

    result = run_problem(problem, TruthModel(), reps=2, base_seed=200,
                         config=AgentConfig(max_steps=3), progress=False)
    assert result.n == 2
    assert result.pass_rate == 1.0  # reference pipeline recovers each rep's truth
