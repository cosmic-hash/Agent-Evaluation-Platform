from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    adapter_type: str = "mock"
    model: str = "demo-v1"
    prompt: str = ""
    tools: list[str] = []
    parameters: dict[str, Any] = {}


class AgentOut(AgentCreate):
    id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TestCaseIn(BaseModel):
    name: str
    input: dict[str, Any]
    expected_answer: str | None = None
    expected_tool_calls: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {}


class DatasetCreate(BaseModel):
    name: str
    description: str = ""
    cases: list[TestCaseIn] = Field(min_length=1)


class DatasetVersionOut(BaseModel):
    id: str
    version: int
    created_at: datetime
    case_count: int


class DatasetOut(BaseModel):
    id: str
    name: str
    description: str
    created_at: datetime
    versions: list[DatasetVersionOut] = []


class ExperimentCreate(BaseModel):
    name: str
    agent_config_id: str
    dataset_version_id: str


class RunOut(BaseModel):
    id: str
    experiment_id: str
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None
    created_at: datetime
    result_count: int = 0


class ResultOut(BaseModel):
    id: str
    test_case_id: str
    passed: bool
    answer_correct: bool
    tool_calls_correct: bool
    answer: str
    tool_calls: list[Any]
    latency_ms: float
    estimated_cost_usd: float
    trace: list[Any]
    failure_explanation: str | None
