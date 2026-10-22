"""Adapters normalize agent outputs. Only the deterministic mock adapter ships in this MVP."""
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class AgentResponse:
    answer: str
    tool_calls: list[dict[str, Any]]
    input_tokens: int
    output_tokens: int
    trace: list[dict[str, Any]]


class AgentAdapter(Protocol):
    def run(self, payload: dict[str, Any], config: dict[str, Any]) -> AgentResponse: ...


class MockAdapter:
    """Predictable test adapter.

    `input.answer` specifies its answer. `input.tool_calls` supplies declared calls.
    `parameters.force_answer` lets two configurations be deliberately compared.
    """
    def run(self, payload: dict[str, Any], config: dict[str, Any]) -> AgentResponse:
        answer = config.get("parameters", {}).get("force_answer", payload.get("answer", ""))
        calls = payload.get("tool_calls", [])
        return AgentResponse(
            answer=str(answer), tool_calls=calls,
            input_tokens=len(str(payload)) // 4, output_tokens=len(str(answer)) // 4,
            trace=[
                {"event": "adapter_started", "adapter": "mock"},
                {"event": "response_created", "answer": str(answer), "tool_call_count": len(calls)},
            ],
        )


def get_adapter(adapter_type: str) -> AgentAdapter:
    if adapter_type == "mock":
        return MockAdapter()
    raise ValueError(f"Unsupported adapter_type '{adapter_type}'. Only 'mock' is enabled in this MVP.")
