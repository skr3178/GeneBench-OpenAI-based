"""ReAct-style agent loop for GeneBench problems.

The agent receives, in order: a system message describing the execution
environment, the problem prompt, the required output schema, and a manifest of
the mounted data files. It can execute Python or bash in the sandbox, and must
write its final answer to ``eval_answer.json`` in the workspace. The loop runs
until the answer file is present and valid, the model ends its turn, or a step /
token budget is hit.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from genebench.models.base import ModelClient
from genebench.sandbox.local import LocalSandbox

SYSTEM_PROMPT = """\
You are a quantitative scientist working in an isolated Linux sandbox. You have a \
Python 3 environment with numpy, pandas, scipy, scikit-learn, statsmodels, \
lifelines, matplotlib, and seaborn installed. There is NO internet access and no \
domain-specific bioinformatics packages.

You solve the task by exploring the staged data files and running analyses with the \
run_python and run_bash tools. Files you write persist in the working directory \
across tool calls. Think carefully about data-quality issues, ascertainment/selection \
biases, confounding, and method choice — the data are realistically messy and a naive \
analysis will usually give the wrong answer.

When you are confident in your result, write your final answer to a file named \
'eval_answer.json' in the working directory, matching the schema given in the task. \
Then stop.\
"""

TOOLS = [
    {
        "name": "run_python",
        "description": "Execute a Python 3 snippet in the sandbox working directory. "
                       "Returns stdout/stderr. Files persist across calls.",
        "input_schema": {
            "type": "object",
            "properties": {"code": {"type": "string", "description": "Python source to execute."}},
            "required": ["code"],
        },
    },
    {
        "name": "run_bash",
        "description": "Execute a bash command in the sandbox working directory. "
                       "Returns stdout/stderr.",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string", "description": "Bash command to run."}},
            "required": ["command"],
        },
    },
]


@dataclass
class AgentResult:
    status: str                       # "answered" | "no_answer" | "budget_exhausted" | "error"
    answer: dict | None
    steps: int
    input_tokens: int
    output_tokens: int
    error: str | None = None
    transcript: list[dict] = field(default_factory=list)


@dataclass
class AgentConfig:
    max_steps: int = 30
    max_output_tokens: int | None = None   # cumulative output-token budget; None = unbounded
    step_timeout: float = 180.0
    max_tool_output_chars: int = 12000


def _initial_user_message(prompt: str, answer_file: str, file_names: list[str],
                          schema: Any) -> str:
    manifest = "\n".join(f"  - {n}" for n in file_names)
    schema_str = json.dumps(schema, indent=2) if schema else "(see task prompt)"
    return (
        f"{prompt}\n\n"
        f"Files available in your working directory:\n{manifest}\n\n"
        f"Write your final answer to '{answer_file}' as JSON. Required schema:\n"
        f"{schema_str}\n"
    )


def run_agent(problem, data_dir, model: ModelClient, sandbox: LocalSandbox | None = None,
              config: AgentConfig | None = None) -> AgentResult:
    """Run one agent attempt on ``problem`` with data generated in ``data_dir``."""
    from pathlib import Path

    config = config or AgentConfig()
    data_dir = Path(data_dir)
    owns_sandbox = sandbox is None
    sandbox = sandbox or LocalSandbox()

    staged = [(data_dir / name, name) for name in problem.staged_files]
    sandbox.setup(staged)

    user_msg = _initial_user_message(
        problem.prompt, problem.answer_file, problem.staged_files,
        problem.meta.get("schema"))
    messages: list[dict] = [{"role": "user", "content": user_msg}]

    in_tok = out_tok = steps = 0
    try:
        while steps < config.max_steps:
            steps += 1
            resp = model.create(SYSTEM_PROMPT, messages, TOOLS)
            in_tok += resp.input_tokens
            out_tok += resp.output_tokens
            messages.append({"role": "assistant", "content": resp.assistant_content})

            if resp.stop_reason == "pause_turn":
                # server-side tool pause: resend to resume
                continue

            if resp.tool_calls:
                results = []
                for call in resp.tool_calls:
                    if call.name == "run_python":
                        ex = sandbox.run_python(call.input.get("code", ""), config.step_timeout)
                    elif call.name == "run_bash":
                        ex = sandbox.run_bash(call.input.get("command", ""), config.step_timeout)
                    else:
                        results.append({"tool_use_id": call.id,
                                        "content": f"Unknown tool: {call.name}", "is_error": True})
                        continue
                    results.append({"tool_use_id": call.id,
                                    "content": ex.format(config.max_tool_output_chars),
                                    "is_error": ex.returncode != 0})
                messages.append(model.tool_result_message(results))

            # check for a completed answer after any tool execution
            answer = _read_answer(sandbox, problem.answer_file)
            if answer is not None:
                return AgentResult("answered", answer, steps, in_tok, out_tok, transcript=messages)

            if config.max_output_tokens and out_tok >= config.max_output_tokens:
                return AgentResult("budget_exhausted", None, steps, in_tok, out_tok, transcript=messages)

            if resp.stop_reason == "end_turn" and not resp.tool_calls:
                # model stopped without producing an answer file
                answer = _read_answer(sandbox, problem.answer_file)
                status = "answered" if answer is not None else "no_answer"
                return AgentResult(status, answer, steps, in_tok, out_tok, transcript=messages)

        return AgentResult("budget_exhausted", _read_answer(sandbox, problem.answer_file),
                           steps, in_tok, out_tok, transcript=messages)
    except Exception as e:  # pragma: no cover - surfaced as a failed run
        return AgentResult("error", None, steps, in_tok, out_tok, error=repr(e), transcript=messages)
    finally:
        if owns_sandbox:
            sandbox.cleanup()


def _read_answer(sandbox, answer_file: str) -> dict | None:
    raw = sandbox.read_file(answer_file)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None
