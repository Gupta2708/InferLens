"""gateway resilience and observability fields

Revision ID: 0003_gateway_observability
Revises: 0002_stabilization_indexes_seed
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_gateway_observability"
down_revision = "0002_stabilization_indexes_seed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("inference_traces") as batch:
        batch.add_column(sa.Column("otel_trace_id", sa.String(64)))
        batch.add_column(sa.Column("otel_root_span_id", sa.String(32)))
        batch.add_column(sa.Column("otel_instrumented_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("original_trace_id", sa.String(64)))
        batch.add_column(sa.Column("completed_at", sa.DateTime(timezone=True)))
    op.create_index("ix_inference_traces_otel_trace_id", "inference_traces", ["otel_trace_id"])
    op.create_index("ix_inference_traces_original_trace_id", "inference_traces", ["original_trace_id"])
    with op.batch_alter_table("inference_logs") as batch:
        batch.add_column(sa.Column("error_category", sa.String(64)))
        batch.add_column(sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("fallback_provider", sa.String(64)))
        batch.add_column(sa.Column("routing_strategy", sa.String(64)))
        batch.add_column(sa.Column("routing_history_json", sa.JSON(), nullable=False, server_default="[]"))
        batch.add_column(sa.Column("finish_reason", sa.String(64)))
        batch.add_column(sa.Column("first_token_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("completed_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("content_captured", sa.Boolean(), nullable=False, server_default=sa.false()))
    for name, cols in [("ix_inference_logs_error_category", ["error_category"]), ("ix_inference_logs_fallback_provider", ["fallback_provider"]), ("ix_inference_logs_finish_reason", ["finish_reason"])]:
        op.create_index(name, "inference_logs", cols)
    with op.batch_alter_table("ingestion_events") as batch:
        batch.add_column(sa.Column("dead_lettered_at", sa.DateTime(timezone=True)))
    with op.batch_alter_table("dead_letter_events") as batch:
        batch.add_column(sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("error_category", sa.String(64)))
        batch.add_column(sa.Column("failed_at", sa.DateTime(timezone=True)))
    op.create_index("ix_dead_letter_events_error_category", "dead_letter_events", ["error_category"])
    with op.batch_alter_table("comparison_results") as batch:
        batch.add_column(sa.Column("error_category", sa.String(64)))
        batch.add_column(sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("finish_reason", sa.String(64)))
        batch.add_column(sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("fallback_provider", sa.String(64)))
        batch.add_column(sa.Column("completed_at", sa.DateTime(timezone=True)))
    op.create_index("ix_comparison_results_error_category", "comparison_results", ["error_category"])
    op.create_index("ix_comparison_results_finish_reason", "comparison_results", ["finish_reason"])


def downgrade() -> None:
    for name, table in [("ix_comparison_results_finish_reason", "comparison_results"), ("ix_comparison_results_error_category", "comparison_results"), ("ix_dead_letter_events_error_category", "dead_letter_events"), ("ix_inference_logs_finish_reason", "inference_logs"), ("ix_inference_logs_fallback_provider", "inference_logs"), ("ix_inference_logs_error_category", "inference_logs"), ("ix_inference_traces_original_trace_id", "inference_traces"), ("ix_inference_traces_otel_trace_id", "inference_traces")]:
        op.drop_index(name, table_name=table)
    with op.batch_alter_table("comparison_results") as batch:
        for col in ["completed_at", "fallback_provider", "retry_count", "finish_reason", "output_tokens", "input_tokens", "error_category"]: batch.drop_column(col)
    with op.batch_alter_table("dead_letter_events") as batch:
        for col in ["failed_at", "error_category", "retry_count"]: batch.drop_column(col)
    with op.batch_alter_table("ingestion_events") as batch: batch.drop_column("dead_lettered_at")
    with op.batch_alter_table("inference_logs") as batch:
        for col in ["content_captured", "completed_at", "first_token_at", "finish_reason", "routing_history_json", "routing_strategy", "fallback_provider", "retry_count", "error_category"]: batch.drop_column(col)
    with op.batch_alter_table("inference_traces") as batch:
        for col in ["completed_at", "original_trace_id", "otel_instrumented_at", "otel_root_span_id", "otel_trace_id"]: batch.drop_column(col)
