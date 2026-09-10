"""create emergency corridor simulation runs table

Revision ID: 0007_create_emergency_corridor_tables
Revises: 0006_create_signal_optimization_tables
Create Date: 2026-09-10 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0007_create_emergency_corridor_tables'
down_revision: Union[str, None] = '0006_create_signal_optimization_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create emergency_corridor_simulations table
    op.create_table(
        'emergency_corridor_simulations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=True),
        sa.Column('corridor_name', sa.String(length=128), nullable=False),
        sa.Column('corridor_nodes_count', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('total_distance_meters', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('vehicle_type', sa.String(length=32), nullable=False, server_default='ambulance'),
        sa.Column('priority_strategy', sa.String(length=64), nullable=False, server_default='green_extension_early_green'),
        sa.Column('recovery_strategy', sa.String(length=64), nullable=False, server_default='smooth_compensation'),
        sa.Column('data_source', sa.String(length=64), nullable=False),
        sa.Column('baseline_travel_time_seconds', sa.Float(), nullable=False),
        sa.Column('priority_travel_time_seconds', sa.Float(), nullable=False),
        sa.Column('travel_time_savings_seconds', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('travel_time_savings_pct', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('baseline_emergency_delay_seconds', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('priority_emergency_delay_seconds', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('emergency_delay_reduction_pct', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('baseline_cross_street_delay_avg', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('priority_cross_street_delay_avg', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('cross_street_delay_impact_pct', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_recovery_duration_seconds', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_interventions_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('execution_time_ms', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('corridor_config', sa.JSON(), nullable=False),
        sa.Column('vehicle_scenario', sa.JSON(), nullable=False),
        sa.Column('node_timelines', sa.JSON(), nullable=False),
        sa.Column('metrics_summary', sa.JSON(), nullable=False),
        sa.Column('simulation_notes', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['analysis_sessions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_emergency_corridor_simulations_id'), 'emergency_corridor_simulations', ['id'], unique=False)
    op.create_index(op.f('ix_emergency_corridor_simulations_session_id'), 'emergency_corridor_simulations', ['session_id'], unique=False)
    op.create_index(op.f('ix_emergency_corridor_simulations_data_source'), 'emergency_corridor_simulations', ['data_source'], unique=False)
    op.create_index(op.f('ix_emergency_corridor_simulations_created_at'), 'emergency_corridor_simulations', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_emergency_corridor_simulations_created_at'), table_name='emergency_corridor_simulations')
    op.drop_index(op.f('ix_emergency_corridor_simulations_data_source'), table_name='emergency_corridor_simulations')
    op.drop_index(op.f('ix_emergency_corridor_simulations_session_id'), table_name='emergency_corridor_simulations')
    op.drop_index(op.f('ix_emergency_corridor_simulations_id'), table_name='emergency_corridor_simulations')
    op.drop_table('emergency_corridor_simulations')
