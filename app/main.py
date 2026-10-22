from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.database import Base, engine, get_db
from app.models import AgentConfig, Dataset, DatasetVersion, EvaluationResult, Experiment, ExperimentRun, TestCase
from app.schemas import AgentCreate, AgentOut, DatasetCreate, DatasetOut, DatasetVersionOut, ExperimentCreate, ResultOut, RunOut, TestCaseIn
from app.services import compare_runs, run_summary


@asynccontextmanager
async def lifespan(_: FastAPI):
    if get_settings().auto_create_tables:
        Base.metadata.create_all(engine)
    yield


app = FastAPI(title="AI Agent Evaluation Platform", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def ui():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.post("/api/agents", response_model=AgentOut, status_code=201)
def create_agent(body: AgentCreate, db: Session = Depends(get_db)):
    if db.scalar(select(AgentConfig).where(AgentConfig.name == body.name)):
        raise HTTPException(409, "Agent name already exists")
    agent = AgentConfig(**body.model_dump())
    db.add(agent); db.commit(); db.refresh(agent)
    return agent


@app.get("/api/agents", response_model=list[AgentOut])
def list_agents(db: Session = Depends(get_db)):
    return db.scalars(select(AgentConfig).order_by(AgentConfig.created_at.desc())).all()


@app.post("/api/datasets", response_model=DatasetOut, status_code=201)
def create_dataset(body: DatasetCreate, db: Session = Depends(get_db)):
    if db.scalar(select(Dataset).where(Dataset.name == body.name)):
        raise HTTPException(409, "Dataset name already exists")
    dataset = Dataset(name=body.name, description=body.description)
    version = DatasetVersion(version=1)
    for item in body.cases:
        payload = item.model_dump()
        version.cases.append(TestCase(name=payload["name"], input=payload["input"], expected_answer=payload["expected_answer"],
                                      expected_tool_calls=payload["expected_tool_calls"], metadata_=payload["metadata"]))
    dataset.versions.append(version)
    db.add(dataset); db.commit(); db.refresh(dataset)
    return dataset_out(dataset)


@app.post("/api/datasets/{dataset_id}/versions", response_model=DatasetVersionOut, status_code=201)
def version_dataset(dataset_id: str, cases: list[TestCaseIn], db: Session = Depends(get_db)):
    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(404, "Dataset not found")
    latest = db.scalar(select(DatasetVersion.version).where(DatasetVersion.dataset_id == dataset_id).order_by(DatasetVersion.version.desc())) or 0
    version = DatasetVersion(dataset_id=dataset_id, version=latest + 1)
    for item in cases:
        payload = item.model_dump()
        version.cases.append(TestCase(name=payload["name"], input=payload["input"], expected_answer=payload["expected_answer"], expected_tool_calls=payload["expected_tool_calls"], metadata_=payload["metadata"]))
    db.add(version); db.commit(); db.refresh(version)
    return DatasetVersionOut(id=version.id, version=version.version, created_at=version.created_at, case_count=len(version.cases))


def dataset_out(dataset: Dataset) -> DatasetOut:
    return DatasetOut(id=dataset.id, name=dataset.name, description=dataset.description, created_at=dataset.created_at,
                      versions=[DatasetVersionOut(id=v.id, version=v.version, created_at=v.created_at, case_count=len(v.cases)) for v in dataset.versions])


@app.get("/api/datasets", response_model=list[DatasetOut])
def list_datasets(db: Session = Depends(get_db)):
    datasets = db.scalars(select(Dataset).options(selectinload(Dataset.versions).selectinload(DatasetVersion.cases))).all()
    return [dataset_out(x) for x in datasets]


@app.post("/api/experiments", status_code=201)
def create_experiment(body: ExperimentCreate, db: Session = Depends(get_db)):
    if not db.get(AgentConfig, body.agent_config_id) or not db.get(DatasetVersion, body.dataset_version_id):
        raise HTTPException(404, "Agent or dataset version not found")
    experiment = Experiment(**body.model_dump())
    db.add(experiment); db.commit(); db.refresh(experiment)
    return {"id": experiment.id, "name": experiment.name, "agent_config_id": experiment.agent_config_id, "dataset_version_id": experiment.dataset_version_id}


@app.post("/api/experiments/{experiment_id}/runs", response_model=RunOut, status_code=202)
def enqueue_run(experiment_id: str, db: Session = Depends(get_db)):
    if not db.get(Experiment, experiment_id):
        raise HTTPException(404, "Experiment not found")
    run = ExperimentRun(experiment_id=experiment_id)
    db.add(run); db.commit(); db.refresh(run)
    return run_summary(db, run)


@app.get("/api/runs/{run_id}", response_model=RunOut)
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(ExperimentRun, run_id)
    if not run: raise HTTPException(404, "Run not found")
    return run_summary(db, run)


@app.get("/api/runs/{run_id}/results", response_model=list[ResultOut])
def get_results(run_id: str, db: Session = Depends(get_db)):
    if not db.get(ExperimentRun, run_id): raise HTTPException(404, "Run not found")
    return db.scalars(select(EvaluationResult).where(EvaluationResult.run_id == run_id)).all()


@app.get("/api/runs/compare")
def compare(left: str, right: str, db: Session = Depends(get_db)):
    try: return compare_runs(db, left, right)
    except LookupError as exc: raise HTTPException(404, str(exc))
