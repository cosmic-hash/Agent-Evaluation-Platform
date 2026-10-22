import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def new_id() -> str:
    return str(uuid.uuid4())


class RunStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class AgentConfig(Base):
    __tablename__ = "agent_configs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    adapter_type: Mapped[str] = mapped_column(String(60), default="mock")
    model: Mapped[str] = mapped_column(String(120), default="demo-v1")
    prompt: Mapped[str] = mapped_column(Text, default="")
    tools: Mapped[list] = mapped_column(JSON, default=list)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Dataset(Base):
    __tablename__ = "datasets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    versions: Mapped[list["DatasetVersion"]] = relationship(back_populates="dataset", cascade="all, delete-orphan")


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    dataset: Mapped[Dataset] = relationship(back_populates="versions")
    cases: Mapped[list["TestCase"]] = relationship(back_populates="dataset_version", cascade="all, delete-orphan")


class TestCase(Base):
    __tablename__ = "test_cases"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    input: Mapped[dict] = mapped_column(JSON)
    expected_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_tool_calls: Mapped[list] = mapped_column(JSON, default=list)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    dataset_version: Mapped[DatasetVersion] = relationship(back_populates="cases")


class Experiment(Base):
    __tablename__ = "experiments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160), index=True)
    agent_config_id: Mapped[str] = mapped_column(ForeignKey("agent_configs.id"))
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExperimentRun(Base):
    __tablename__ = "experiment_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id"), index=True)
    status: Mapped[RunStatus] = mapped_column(Enum(RunStatus), default=RunStatus.queued, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    results: Mapped[list["EvaluationResult"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("experiment_runs.id"), index=True)
    test_case_id: Mapped[str] = mapped_column(ForeignKey("test_cases.id"))
    passed: Mapped[bool] = mapped_column(Boolean)
    answer_correct: Mapped[bool] = mapped_column(Boolean)
    tool_calls_correct: Mapped[bool] = mapped_column(Boolean)
    answer: Mapped[str] = mapped_column(Text)
    tool_calls: Mapped[list] = mapped_column(JSON, default=list)
    latency_ms: Mapped[float] = mapped_column(Float)
    estimated_cost_usd: Mapped[float] = mapped_column(Float)
    trace: Mapped[list] = mapped_column(JSON, default=list)
    failure_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    run: Mapped[ExperimentRun] = relationship(back_populates="results")
