"""Command-line interface for the GeneBench harness.

Subcommands:
  generate   build a problem's staged data files + hidden truth.json
  solve      run a problem's reference solution and print the answer
  ablations  run a problem's wrong-but-plausible paths
  grade      grade an eval_answer.json against a generated truth.json
  verify     generate + check that the reference passes and ablations fail
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from genebench.grader import grade
from genebench.problem import Problem


def _resolve_problem(name_or_path: str) -> Problem:
    p = Path(name_or_path)
    if not (p / "meta.yaml").exists():
        p = Path("problems") / name_or_path
    return Problem.load(p)


def cmd_generate(args):
    prob = _resolve_problem(args.problem)
    res = prob.generate(seed=args.seed, outdir=args.outdir)
    print(json.dumps(res, indent=2, default=str))


def cmd_solve(args):
    prob = _resolve_problem(args.problem)
    print(json.dumps(prob.reference_solution(args.data_dir), indent=2))


def cmd_ablations(args):
    prob = _resolve_problem(args.problem)
    print(json.dumps(prob.run_ablations(args.data_dir), indent=2))


def cmd_grade(args):
    prob = _resolve_problem(args.problem)
    answer = json.loads(Path(args.answer).read_text())
    truth = prob.graded_truth(args.data_dir)
    result = grade(answer, truth, prob.graded_fields)
    print(json.dumps(result.to_dict(), indent=2))
    raise SystemExit(0 if result.passed else 1)


def cmd_run(args):
    from genebench.agent import AgentConfig
    from genebench.models.anthropic_client import AnthropicClient
    from genebench.runner import run_problem

    prob = _resolve_problem(args.problem)
    model = AnthropicClient(model=args.model, effort=args.effort)
    config = AgentConfig(max_steps=args.max_steps)
    print(f"Running {prob.id} with {model.name} ({args.reps} reps)...")
    result = run_problem(prob, model, reps=args.reps, base_seed=args.seed, config=config)
    print(f"\npass rate: {result.pass_rate:.1%}  "
          f"({sum(r.passed for r in result.records)}/{result.n})  "
          f"mean out-tokens: {result.mean_output_tokens:.0f}")
    for r in result.records:
        print(json.dumps({"rep": r.rep, "passed": r.passed, "status": r.status,
                          "answer": r.answer, "truth": r.truth}, default=str))


def cmd_verify(args):
    prob = _resolve_problem(args.problem)
    outdir = Path(args.outdir)
    prob.generate(seed=args.seed, outdir=outdir)
    truth = prob.graded_truth(outdir)
    ref = {"answer": prob.reference_solution(outdir)}
    ref_res = grade(ref, truth, prob.graded_fields)
    print(f"truth: {json.dumps(truth)}")
    print(f"reference passes: {ref_res.passed}")
    ok = ref_res.passed
    try:
        for name, ans in prob.run_ablations(outdir).items():
            res = grade({"answer": ans}, truth, prob.graded_fields)
            print(f"ablation {name:12s} passes: {res.passed} (must be False)")
            ok = ok and (not res.passed)
    except FileNotFoundError:
        print("(no ablations.py)")
    print("VERIFY OK" if ok else "VERIFY FAILED")
    raise SystemExit(0 if ok else 1)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="genebench")
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="generate staged data + truth")
    g.add_argument("problem")
    g.add_argument("--seed", type=int, default=7)
    g.add_argument("--outdir", default="_data")
    g.set_defaults(func=cmd_generate)

    s = sub.add_parser("solve", help="run the reference solution")
    s.add_argument("problem")
    s.add_argument("data_dir")
    s.set_defaults(func=cmd_solve)

    a = sub.add_parser("ablations", help="run wrong-but-plausible paths")
    a.add_argument("problem")
    a.add_argument("data_dir")
    a.set_defaults(func=cmd_ablations)

    gr = sub.add_parser("grade", help="grade an eval_answer.json")
    gr.add_argument("problem")
    gr.add_argument("data_dir")
    gr.add_argument("answer")
    gr.set_defaults(func=cmd_grade)

    r = sub.add_parser("run", help="run an LLM agent on a problem and grade it")
    r.add_argument("problem")
    r.add_argument("--model", default="claude-opus-4-8")
    r.add_argument("--effort", default="high", choices=["low", "medium", "high", "xhigh", "max"])
    r.add_argument("--reps", type=int, default=5)
    r.add_argument("--seed", type=int, default=1000)
    r.add_argument("--max-steps", type=int, default=30)
    r.set_defaults(func=cmd_run)

    v = sub.add_parser("verify", help="reference passes + ablations fail")
    v.add_argument("problem")
    v.add_argument("--seed", type=int, default=7)
    v.add_argument("--outdir", default="_data")
    v.set_defaults(func=cmd_verify)

    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
