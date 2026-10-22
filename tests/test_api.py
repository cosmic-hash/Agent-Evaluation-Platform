from app.models import ExperimentRun, RunStatus
from app.services import compare_runs, execute_run


def make_experiment(client, name="demo", force_answer=None):
    params = {"force_answer": force_answer} if force_answer is not None else {}
    agent = client.post("/api/agents", json={"name": f"agent-{name}", "parameters": params}).json()
    dataset = client.post("/api/datasets", json={"name": f"dataset-{name}", "cases": [
        {"name": "answer", "input": {"answer": "correct"}, "expected_answer": "correct"},
        {"name": "tool", "input": {"answer": "done", "tool_calls": [{"name": "search", "arguments": {"q": "x"}}]}, "expected_answer": "done", "expected_tool_calls": [{"name": "search", "arguments": {"q": "x"}}]},
    ]}).json()
    return client.post("/api/experiments", json={"name": name, "agent_config_id": agent["id"], "dataset_version_id": dataset["versions"][0]["id"]}).json()


def test_api_creates_immutable_dataset_version_and_queues_run(client):
    experiment = make_experiment(client)
    response = client.post(f"/api/experiments/{experiment['id']}/runs")
    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    datasets = client.get("/api/datasets").json()
    assert datasets[0]["versions"][0]["case_count"] == 2


def test_worker_records_assertions_metrics_trace_and_failure_explanation(client, db):
    experiment = make_experiment(client, "bad", force_answer="wrong")
    run_id = client.post(f"/api/experiments/{experiment['id']}/runs").json()["id"]
    run = db.get(ExperimentRun, run_id)
    run.status = RunStatus.running; db.commit()
    execute_run(db, run)
    results = client.get(f"/api/runs/{run_id}/results").json()
    assert len(results) == 2
    assert not results[0]["passed"]
    assert "Answer mismatch" in results[0]["failure_explanation"]
    assert results[0]["latency_ms"] >= 0
    assert results[0]["trace"][0]["event"] == "adapter_started"


def test_comparison_exposes_pass_latency_and_cost_deltas(client, db):
    good = make_experiment(client, "good")
    bad = make_experiment(client, "bad2", force_answer="wrong")
    ids = []
    for experiment in (good, bad):
        run_id = client.post(f"/api/experiments/{experiment['id']}/runs").json()["id"]
        run = db.get(ExperimentRun, run_id); run.status = RunStatus.running; db.commit(); execute_run(db, run)
        ids.append(run_id)
    comparison = compare_runs(db, *ids)
    assert comparison["left"]["pass_rate"] == 1
    assert comparison["right"]["pass_rate"] == 0
    assert comparison["delta"]["pass_rate"] == -1
