import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AgentConfig, EvaluationResult, Experiment, ExperimentRun, RunStatus, TestCase


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalized_calls(calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"name": c.get("name"), "arguments": c.get("arguments", {})} for c in calls]


def invoke_isolated(agent: AgentConfig, payload: dict[str, Any]) -> dict[str, Any]:
    """Run an adapter in a clean subprocess with a timeout and minimal inherited environment."""
    started = time.perf_counter()
    request = {"adapter_type": agent.adapter_type, "config": {
        "model": agent.model, "prompt": agent.prompt, "tools": agent.tools, "parameters": agent.parameters,
    }, "input": payload}
    safe_env = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": os.getcwd(), "PYTHONDONTWRITEBYTECODE": "1"}
    completed = subprocess.run(
        [sys.executable, "-m", "app.isolation_runner"], input=json.dumps(request), text=True,
        capture_output=True, timeout=get_settings().execution_timeout_seconds, env=safe_env, check=False,
    )
    latency_ms = round((time.perf_counter() - started) * 1000, 3)
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or "isolated adapter failed")
    response = json.loads(completed.stdout)
    response["latency_ms"] = latency_ms
    return response


def explain_failure(answer_ok: bool, tools_ok: bool, expected_answer: str | None,
                    actual_answer: str, expected_tools: list, actual_tools: list) -> str | None:
    reasons = []
    if not answer_ok:
        reasons.append(f"Answer mismatch: expected {expected_answer!r}, got {actual_answer!r}.")
    if not tools_ok:
        reasons.append(f"Tool calls mismatch: expected {expected_tools!r}, got {actual_tools!r}.")
    return " ".join(reasons) if reasons else None


def claim_next_run(db: Session) -> ExperimentRun | None:
    # PostgreSQL uses SKIP LOCKED; SQLite test mode serializes safely in one worker.
    stmt = select(ExperimentRun).where(ExperimentRun.status == RunStatus.queued).order_by(ExperimentRun.created_at).limit(1)
    if db.bind and db.bind.dialect.name == "postgresql":
        stmt = stmt.with_for_update(skip_locked=True)
    run = db.execute(stmt).scalar_one_or_none()
    if run:
        run.status, run.started_at = RunStatus.running, utcnow()
        db.commit()
        db.refresh(run)
    return run


def execute_run(db: Session, run: ExperimentRun) -> ExperimentRun:
    experiment = db.get(Experiment, run.experiment_id)
    if not experiment:
        raise RuntimeError("experiment no longer exists")
    agent = db.get(AgentConfig, experiment.agent_config_id)
    cases = db.scalars(select(TestCase).where(TestCase.dataset_version_id == experiment.dataset_version_id)).all()
    try:
        for case in cases:
            response = invoke_isolated(agent, case.input)
            answer_ok = case.expected_answer is None or response["answer"] == case.expected_answer
            actual_tools = normalized_calls(response["tool_calls"])
            expected_tools = normalized_calls(case.expected_tool_calls)
            tools_ok = actual_tools == expected_tools
            # Deterministic, transparent local estimate (not a provider invoice).
            cost = round((response["input_tokens"] * 0.000001) + (response["output_tokens"] * 0.000002), 8)
            db.add(EvaluationResult(
                run_id=run.id, test_case_id=case.id, passed=answer_ok and tools_ok,
                answer_correct=answer_ok, tool_calls_correct=tools_ok, answer=response["answer"],
                tool_calls=response["tool_calls"], latency_ms=response["latency_ms"], estimated_cost_usd=cost,
                trace=response["trace"], failure_explanation=explain_failure(
                    answer_ok, tools_ok, case.expected_answer, response["answer"], expected_tools, actual_tools),
            ))
        run.status, run.finished_at = RunStatus.completed, utcnow()
    except Exception as exc:
        run.status, run.finished_at, run.error = RunStatus.failed, utcnow(), str(exc)
    db.commit()
    db.refresh(run)
    return run


def run_summary(db: Session, run: ExperimentRun) -> dict[str, Any]:
    results = list(run.results)
    return {
        "id": run.id, "experiment_id": run.experiment_id, "status": run.status.value,
        "started_at": run.started_at, "finished_at": run.finished_at, "error": run.error,
        "created_at": run.created_at, "result_count": len(results),
    }


def compare_runs(db: Session, left_id: str, right_id: str) -> dict[str, Any]:
    left, right = db.get(ExperimentRun, left_id), db.get(ExperimentRun, right_id)
    if not left or not right:
        raise LookupError("run not found")
    def aggregate(run: ExperimentRun):
        results = run.results
        return {"run_id": run.id, "cases": len(results),
                "pass_rate": (sum(r.passed for r in results) / len(results)) if results else 0,
                "mean_latency_ms": (sum(r.latency_ms for r in results) / len(results)) if results else 0,
                "estimated_cost_usd": sum(r.estimated_cost_usd for r in results)}
    left_a, right_a = aggregate(left), aggregate(right)
    return {"left": left_a, "right": right_a, "delta": {
        "pass_rate": right_a["pass_rate"] - left_a["pass_rate"],
        "mean_latency_ms": right_a["mean_latency_ms"] - left_a["mean_latency_ms"],
        "estimated_cost_usd": right_a["estimated_cost_usd"] - left_a["estimated_cost_usd"],
    }}
