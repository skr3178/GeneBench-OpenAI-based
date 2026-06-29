"""Replicate runner: run an agent on a problem N times and grade each attempt."""
from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from genebench.agent import AgentConfig, run_agent
from genebench.grader import grade
from genebench.models.base import ModelClient
from genebench.problem import Problem


@dataclass
class RunRecord:
    rep: int
    seed: int
    status: str
    passed: bool
    answer: dict | None
    truth: dict
    input_tokens: int
    output_tokens: int
    steps: int
    error: str | None = None


@dataclass
class ProblemResult:
    problem_id: str
    model: str
    records: list[RunRecord] = field(default_factory=list)

    @property
    def n(self) -> int:
        return len(self.records)

    @property
    def pass_rate(self) -> float:
        if not self.records:
            return 0.0
        return sum(r.passed for r in self.records) / len(self.records)

    @property
    def mean_output_tokens(self) -> float:
        if not self.records:
            return 0.0
        return sum(r.output_tokens for r in self.records) / len(self.records)


def run_problem(problem: Problem, model: ModelClient, reps: int = 5,
                base_seed: int = 1000, config: AgentConfig | None = None,
                progress: bool = True) -> ProblemResult:
    config = config or AgentConfig()
    result = ProblemResult(problem_id=problem.id, model=getattr(model, "name", "model"))

    for rep in range(reps):
        seed = base_seed + rep
        with tempfile.TemporaryDirectory(prefix=f"gb_{problem.id}_") as data_dir:
            problem.generate(seed=seed, outdir=data_dir)
            truth = problem.graded_truth(data_dir)
            agent_res = run_agent(problem, data_dir, model, config=config)
            graded = grade(agent_res.answer or {}, truth, problem.graded_fields)
            rec = RunRecord(
                rep=rep, seed=seed, status=agent_res.status,
                passed=bool(agent_res.answer is not None and graded.passed),
                answer=agent_res.answer, truth=truth,
                input_tokens=agent_res.input_tokens, output_tokens=agent_res.output_tokens,
                steps=agent_res.steps, error=agent_res.error,
            )
            result.records.append(rec)
            if progress:
                mark = "PASS" if rec.passed else rec.status
                print(f"  [{problem.id}] rep {rep+1}/{reps} (seed {seed}): {mark} "
                      f"({rec.output_tokens} out-tok, {rec.steps} steps)")
    return result
