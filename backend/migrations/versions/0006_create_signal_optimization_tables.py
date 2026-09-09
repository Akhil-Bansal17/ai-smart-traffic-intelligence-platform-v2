"""create signal optimization simulation runs table

Revision ID: 0006_create_signal_optimization_tables
Revises: 0005_harden_video_provenance_fields
Create Date: 2026-09-09 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0006_create_signal_optimization_tables'
down_revision: Union[str, None] = '0005_harden_video_provenance_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create signal_simulations table
    op.create_table(
        'signal_simulations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=True),
        sa.Column('intersection_name', sa.String(length=128), nullable=False),
        sa.Column('intersection_type', sa.String(length=32), nullable=False, server_default='four_way'),
        sa.Column('data_source', sa.String(length=64), nullable=False),
        sa.Column('algorithm_used', sa.String(length=64), nullable=False),
        sa.Column('baseline_cycle_length', sa.Float(), nullable=False),
        sa.Column('optimized_cycle_length', sa.Float(), nullable=False),
        sa.Column('baseline_delay_proxy', sa.Float(), nullable=False),
        sa.Column('optimized_delay_proxy', sa.Float(), nullable=False),
        sa.Column('delay_reduction_pct', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('baseline_queue_proxy', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('optimized_queue_proxy', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('queue_reduction_pct', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('baseline_throughput_proxy', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('optimized_throughput_proxy', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('throughput_increase_pct', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('objective_improvement_pct', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('execution_time_ms', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('intersection_config', sa.JSON(), nullable=False),
        sa.Column('demand_input', sa.JSON(), nullable=False),
        sa.Column('baseline_plan', sa.JSON(), nullable=False),
        sa.Column('optimized_plan', sa.JSON(), nullable=False),
        sa.Column('baseline_metrics', sa.JSON(), nullable=False),
        sa.Column('optimized_metrics', sa.JSON(), nullable=False),
        sa.Column('phase_comparisons', sa.JSON(), nullable=False),
        sa.Column('approach_comparisons', sa.JSON(), nullable=False),
        sa.Column('simulation_notes', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['analysis_sessions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_signal_simulations_id'), 'signal_simulations', ['id'], unique=False)
    op.create_index(op.f('ix_signal_simulations_session_id'), 'signal_simulations', ['session_id'], unique=False)
    op.create_index(op.f('ix_signal_simulations_data_source'), 'signal_simulations', ['data_source'], unique=False)
    op.create_index(op.f('ix_signal_simulations_created_at'), 'signal_simulations', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_signal_simulations_created_at'), table_name='signal_simulations')
    op.drop_index(op.f('ix_signal_simulations_data_source'), table_name='signal_simulations')
    op.drop_index(op.f('ix_signal_simulations_session_id'), table_name='signal_simulations')
    op.drop_index(op.f('ix_signal_simulations_id'), table_name='signal_simulations')
    op.drop_table('signal_simulations')
