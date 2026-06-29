"""Anthropic / Claude adapter for the agent loop.

Uses the Messages API with adaptive thinking and the effort parameter. Token
accounting reports output tokens (the model's reasoning trace + final response),
matching the paper's "average tokens used" definition. Requires the ``anthropic``
package and an ANTHROPIC_API_KEY in the environment.
"""
from __future__ import annotations

from genebench.models.base import ModelResponse, ToolCall

DEFAULT_MODEL = "claude-opus-4-8"


class AnthropicClient:
    def __init__(self, model: str = DEFAULT_MODEL, effort: str = "high",
                 thinking: bool = True, max_tokens: int = 16000):
        try:
            import anthropic
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                "The 'anthropic' package is required for the Claude adapter. "
                "Install it with: pip install anthropic"
            ) from e
        self._anthropic = anthropic
        self.client = anthropic.Anthropic()
        self.model = model
        self.effort = effort
        self.thinking = thinking
        self.max_tokens = max_tokens
        self.name = f"anthropic:{model}:{effort}"

    def create(self, system: str, messages: list[dict], tools: list[dict],
               max_tokens: int | None = None) -> ModelResponse:
        kwargs = dict(
            model=self.model,
            max_tokens=max_tokens or self.max_tokens,
            system=system,
            messages=messages,
            tools=tools,
            output_config={"effort": self.effort},
        )
        if self.thinking:
            kwargs["thinking"] = {"type": "adaptive"}
        resp = self.client.messages.create(**kwargs)

        text = "".join(b.text for b in resp.content if b.type == "text")
        tool_calls = [ToolCall(id=b.id, name=b.name, input=dict(b.input))
                      for b in resp.content if b.type == "tool_use"]
        usage = resp.usage
        return ModelResponse(
            text=text,
            tool_calls=tool_calls,
            stop_reason=resp.stop_reason,
            assistant_content=resp.content,
            input_tokens=getattr(usage, "input_tokens", 0) or 0,
            output_tokens=getattr(usage, "output_tokens", 0) or 0,
            raw=resp,
        )

    def tool_result_message(self, results: list[dict]) -> dict:
        content = [
            {"type": "tool_result", "tool_use_id": r["tool_use_id"],
             "content": r["content"], "is_error": r.get("is_error", False)}
            for r in results
        ]
        return {"role": "user", "content": content}
