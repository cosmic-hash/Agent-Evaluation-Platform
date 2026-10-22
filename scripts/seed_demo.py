"""Seed one agent, dataset, experiment, and queued run for local exploration."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.database import SessionLocal
from app.models import AgentConfig, Dataset, DatasetVersion, Experiment, ExperimentRun, TestCase


def main():
    with SessionLocal() as db:
        agent = AgentConfig(name="demo-agent", adapter_type="mock", model="demo-v1", tools=["lookup"])
        dataset = Dataset(name="demo-cases", description="Deterministic answer and tool-call checks")
        version = DatasetVersion(version=1, cases=[
            TestCase(name="simple answer", input={"answer": "Paris"}, expected_answer="Paris"),
            TestCase(name="tool use", input={"answer": "Found", "tool_calls": [{"name": "lookup", "arguments": {"city": "Paris"}}]}, expected_answer="Found", expected_tool_calls=[{"name": "lookup", "arguments": {"city": "Paris"}}]),
        ])
        dataset.versions.append(version); db.add_all([agent, dataset]); db.flush()
        experiment = Experiment(name="demo experiment", agent_config_id=agent.id, dataset_version_id=version.id)
        db.add(experiment); db.flush(); run = ExperimentRun(experiment_id=experiment.id); db.add(run); db.commit()
        print(f"Seeded queued run: {run.id}")


if __name__ == "__main__": main()
