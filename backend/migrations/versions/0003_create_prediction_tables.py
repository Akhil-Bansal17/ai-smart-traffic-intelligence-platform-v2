"""create prediction runs and prediction items tables

Revision ID: 0003_create_prediction_tables
Revises: 0002_create_analysis_tables
Create Date: 2026-09-06 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003_create_prediction_tables'
down_revision: Union[str, None] = '0002_create_analysis_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create prediction_runs table
    op.create_table(
        'prediction_runs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('model_name', sa.String(length=64), nullable=False),
        sa.Column('model_type', sa.String(length=64), nullable=False),
        sa.Column('target_variable', sa.String(length=64), nullable=False),
        sa.Column('horizon_minutes', sa.Integer(), nullable=False),
        sa.Column('data_source', sa.String(length=64), nullable=False),
        sa.Column('training_sample_count', sa.Integer(), nullable=False),
        sa.Column('test_sample_count', sa.Integer(), nullable=False),
        sa.Column('training_time_ms', sa.Float(), nullable=False),
        sa.Column('mae', sa.Float(), nullable=False),
        sa.Column('rmse', sa.Float(), nullable=False),
        sa.Column('r2_score', sa.Float(), nullable=True),
        sa.Column('baseline_mae', sa.Float(), nullable=False),
        sa.Column('baseline_rmse', sa.Float(), nullable=False),
        sa.Column('feature_names', sa.JSON(), nullable=True),
        sa.Column('feature_importances', sa.JSON(), nullable=True),
        sa.Column('model_params', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_prediction_runs_id'), 'prediction_runs', ['id'], unique=False)
    op.create_index(op.f('ix_prediction_runs_created_at'), 'prediction_runs', ['created_at'], unique=False)

    # 2. Create prediction_items table
    op.create_table(
        'prediction_items',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('prediction_run_id', sa.String(length=36), nullable=False),
        sa.Column('step_index', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('predicted_value', sa.Float(), nullable=False),
        sa.Column('lower_bound', sa.Float(), nullable=True),
        sa.Column('upper_bound', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['prediction_run_id'], ['prediction_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_prediction_items_id'), 'prediction_items', ['id'], unique=False)
    op.create_index(op.f('ix_prediction_items_prediction_run_id'), 'prediction_items', ['prediction_run_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_prediction_items_prediction_run_id'), table_name='prediction_items')
    op.drop_index(op.f('ix_prediction_items_id'), table_name='prediction_items')
    op.drop_table('prediction_items')

    op.drop_index(op.f('ix_prediction_runs_created_at'), table_name='prediction_runs')
    op.drop_index(op.f('ix_prediction_runs_id'), table_name='prediction_runs')
    op.drop_table('prediction_runs')
