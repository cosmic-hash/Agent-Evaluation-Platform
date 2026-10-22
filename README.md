# AI Agent Evaluation Platform

A locally runnable MVP for answering: **does an agent configuration improve reliability, and at what latency/cost?** It has a FastAPI REST API, PostgreSQL persistence, a database-backed asynchronous worker, versioned datasets, deterministic assertions, traces, comparison summaries, migrations, and tests.

## What is implemented

- Agent configurations (model, prompt, declared tools, parameters) with a deterministic `mock` adapter.
- Immutable dataset versions; every experiment pins one version.
- Queued → running → completed/failed experiment run lifecycle.
- A separate worker claims queued runs and invokes every test case in a fresh Python subprocess, with a timeout and minimal inherited environment.
- Exact answer and normalized tool-call assertions, per-case pass/fail explanations, traces, latency, and transparent local token-cost estimates.
- REST endpoints plus a tiny browser page at `/` for creating a demo run.
- Alembic schema migration, demo seed fixture, pytest/HTTPX integration coverage, and Docker Compose.

## Quick start (Docker)

```bash
cd ai-agent-evaluation-platform
docker compose up --build
# Open http://localhost:8000/docs or http://localhost:8000
```

The `migrate` container completes once; `api` and `worker` stay running. Stop with `docker compose down`. Add `-v` only when you intentionally want to remove the database volume.

## Local start

```bash
cd ai-agent-evaluation-platform
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=sqlite:///./agent_eval.db
alembic upgrade head
python scripts/seed_demo.py
python -m app.worker                 # terminal 1
uvicorn app.main:app --reload         # terminal 2
```

## End-to-end API example

```bash
curl -sX POST localhost:8000/api/agents -H 'content-type: application/json' -d '{"name":"demo-agent","adapter_type":"mock","tools":["lookup"]}'

curl -sX POST localhost:8000/api/datasets -H 'content-type: application/json' -d '{"name":"cities-v1","cases":[{"name":"capital","input":{"answer":"Paris"},"expected_answer":"Paris"},{"name":"lookup","input":{"answer":"found","tool_calls":[{"name":"lookup","arguments":{"city":"Paris"}}]},"expected_answer":"found","expected_tool_calls":[{"name":"lookup","arguments":{"city":"Paris"}}]}]}'
```

Use the returned agent id and first dataset-version id:

```bash
curl -sX POST localhost:8000/api/experiments -H 'content-type: application/json' -d '{"name":"baseline","agent_config_id":"AGENT_ID","dataset_version_id":"VERSION_ID"}'
curl -sX POST localhost:8000/api/experiments/EXPERIMENT_ID/runs -H 'content-type: application/json' -d '{}'
curl -s localhost:8000/api/runs/RUN_ID/results
curl -s 'localhost:8000/api/runs/compare?left=RUN_A&right=RUN_B'
```

## API map

| Method | Path | Purpose |
| --- | --- | --- |
| `POST/GET` | `/api/agents` | Create/list agent configurations |
| `POST/GET` | `/api/datasets` | Create/list initial dataset versions |
| `POST` | `/api/datasets/{id}/versions` | Add an immutable dataset version |
| `POST` | `/api/experiments` | Bind agent configuration to dataset version |
| `POST` | `/api/experiments/{id}/runs` | Queue an asynchronous run |
| `GET` | `/api/runs/{id}`, `/api/runs/{id}/results` | Inspect run and case-level evidence |
| `GET` | `/api/runs/compare?left=&right=` | Compare reliability, latency, and cost |

## Tests

```bash
pytest -q
```

## Security and MVP boundaries

The supplied mock adapter is intentionally deterministic and performs no network calls. Invocations use a short-lived subprocess and timeout to model isolation, but this **is not a hostile-code sandbox**: a production adapter must run in a locked-down container or microVM with resource limits, no host mounts, egress allowlists, tenant authentication/authorization, encrypted secrets, audit logging, and a real queue.

Cost is a documented local estimate based on mock token counts—not billing data. The MVP deliberately does not include user accounts, provider SDK adapters, distributed queue/retries, streaming traces, dataset imports, or statistical significance testing. These are the natural next enhancements.
