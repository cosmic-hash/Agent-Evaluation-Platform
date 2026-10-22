"""initial schema

Revision ID: 0001_initial
Revises: 
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("agent_configs", sa.Column("id", sa.String(36), primary_key=True), sa.Column("name", sa.String(120), nullable=False), sa.Column("adapter_type", sa.String(60), nullable=False), sa.Column("model", sa.String(120), nullable=False), sa.Column("prompt", sa.Text(), nullable=False), sa.Column("tools", sa.JSON(), nullable=False), sa.Column("parameters", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.UniqueConstraint("name"))
    op.create_index("ix_agent_configs_name", "agent_configs", ["name"])
    op.create_table("datasets", sa.Column("id", sa.String(36), primary_key=True), sa.Column("name", sa.String(120), nullable=False), sa.Column("description", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.UniqueConstraint("name"))
    op.create_index("ix_datasets_name", "datasets", ["name"])
    op.create_table("dataset_versions", sa.Column("id", sa.String(36), primary_key=True), sa.Column("dataset_id", sa.String(36), sa.ForeignKey("datasets.id"), nullable=False), sa.Column("version", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False))
    op.create_index("ix_dataset_versions_dataset_id", "dataset_versions", ["dataset_id"])
    op.create_table("test_cases", sa.Column("id", sa.String(36), primary_key=True), sa.Column("dataset_version_id", sa.String(36), sa.ForeignKey("dataset_versions.id"), nullable=False), sa.Column("name", sa.String(160), nullable=False), sa.Column("input", sa.JSON(), nullable=False), sa.Column("expected_answer", sa.Text()), sa.Column("expected_tool_calls", sa.JSON(), nullable=False), sa.Column("metadata", sa.JSON(), nullable=False))
    op.create_index("ix_test_cases_dataset_version_id", "test_cases", ["dataset_version_id"])
    op.create_table("experiments", sa.Column("id", sa.String(36), primary_key=True), sa.Column("name", sa.String(160), nullable=False), sa.Column("agent_config_id", sa.String(36), sa.ForeignKey("agent_configs.id"), nullable=False), sa.Column("dataset_version_id", sa.String(36), sa.ForeignKey("dataset_versions.id"), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False))
    op.create_index("ix_experiments_name", "experiments", ["name"])
    op.create_table("experiment_runs", sa.Column("id", sa.String(36), primary_key=True), sa.Column("experiment_id", sa.String(36), sa.ForeignKey("experiments.id"), nullable=False), sa.Column("status", sa.Enum("queued", "running", "completed", "failed", name="runstatus"), nullable=False), sa.Column("started_at", sa.DateTime(timezone=True)), sa.Column("finished_at", sa.DateTime(timezone=True)), sa.Column("error", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False))
    op.create_index("ix_experiment_runs_experiment_id", "experiment_runs", ["experiment_id"]); op.create_index("ix_experiment_runs_status", "experiment_runs", ["status"])
    op.create_table("evaluation_results", sa.Column("id", sa.String(36), primary_key=True), sa.Column("run_id", sa.String(36), sa.ForeignKey("experiment_runs.id"), nullable=False), sa.Column("test_case_id", sa.String(36), sa.ForeignKey("test_cases.id"), nullable=False), sa.Column("passed", sa.Boolean(), nullable=False), sa.Column("answer_correct", sa.Boolean(), nullable=False), sa.Column("tool_calls_correct", sa.Boolean(), nullable=False), sa.Column("answer", sa.Text(), nullable=False), sa.Column("tool_calls", sa.JSON(), nullable=False), sa.Column("latency_ms", sa.Float(), nullable=False), sa.Column("estimated_cost_usd", sa.Float(), nullable=False), sa.Column("trace", sa.JSON(), nullable=False), sa.Column("failure_explanation", sa.Text()))
    op.create_index("ix_evaluation_results_run_id", "evaluation_results", ["run_id"])


def downgrade() -> None:
    op.drop_table("evaluation_results"); op.drop_table("experiment_runs"); op.drop_table("experiments"); op.drop_table("test_cases"); op.drop_table("dataset_versions"); op.drop_table("datasets"); op.drop_table("agent_configs")
