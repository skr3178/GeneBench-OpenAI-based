"""Model-client interface for the agent loop.

A ModelClient wraps a provider's chat+tool-use API behind a small, normalized
surface so the agent loop is provider-agnostic. The Anthropic/Claude adapter is
the first implementation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict


@dataclass
class ModelResponse:
    text: str
    tool_calls: list[ToolCall]
    stop_reason: str
    # provider-native assistant content to append verbatim to the transcript
    assistant_content: Any
    # token accounting for this single turn
    input_tokens: int = 0
    output_tokens: int = 0
    raw: Any = field(default=None, repr=False)


class ModelClient(Protocol):
    name: str

    def create(self, system: str, messages: list[dict], tools: list[dict],
               max_tokens: int = 16000) -> ModelResponse: ...

    def tool_result_message(self, results: list[dict]) -> dict:
        """Build the provider-native user message carrying tool results.

        Each entry of ``results`` is ``{"tool_use_id", "content", "is_error"}``.
        """
        ...
