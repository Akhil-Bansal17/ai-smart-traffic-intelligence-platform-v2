"""create anomaly events table

Revision ID: 0008_create_anomaly_events_tables
Revises: 0007_create_emergency_corridor_tables
Create Date: 2026-09-12 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0008_create_anomaly_events_tables'
down_revision: Union[str, None] = '0007_create_emergency_corridor_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create anomaly_events table
    op.create_table(
        'anomaly_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('anomaly_type', sa.String(length=64), nullable=False),
        sa.Column('severity', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='open'),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('start_timestamp_seconds', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('end_timestamp_seconds', sa.Float(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('metric_name', sa.String(length=64), nullable=False),
        sa.Column('trigger_value', sa.Float(), nullable=False),
        sa.Column('baseline_value', sa.Float(), nullable=True),
        sa.Column('threshold_value', sa.Float(), nullable=False),
        sa.Column('deviation_pct', sa.Float(), nullable=True),
        sa.Column('lane_id', sa.String(length=64), nullable=True),
        sa.Column('provenance_category', sa.String(length=64), nullable=False, server_default='real_database_metrics'),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('details_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['analysis_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_anomaly_events_id'), 'anomaly_events', ['id'], unique=False)
    op.create_index(op.f('ix_anomaly_events_session_id'), 'anomaly_events', ['session_id'], unique=False)
    op.create_index(op.f('ix_anomaly_events_anomaly_type'), 'anomaly_events', ['anomaly_type'], unique=False)
    op.create_index(op.f('ix_anomaly_events_severity'), 'anomaly_events', ['severity'], unique=False)
    op.create_index(op.f('ix_anomaly_events_status'), 'anomaly_events', ['status'], unique=False)
    op.create_index(op.f('ix_anomaly_events_lane_id'), 'anomaly_events', ['lane_id'], unique=False)
    op.create_index(op.f('ix_anomaly_events_provenance_category'), 'anomaly_events', ['provenance_category'], unique=False)
    op.create_index(op.f('ix_anomaly_events_is_synthetic'), 'anomaly_events', ['is_synthetic'], unique=False)
    op.create_index(op.f('ix_anomaly_events_created_at'), 'anomaly_events', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_anomaly_events_created_at'), table_name='anomaly_events')
    op.drop_index(op.f('ix_anomaly_events_is_synthetic'), table_name='anomaly_events')
    op.drop_index(op.f('ix_anomaly_events_provenance_category'), table_name='anomaly_events')
    op.drop_index(op.f('ix_anomaly_events_lane_id'), table_name='anomaly_events')
    op.drop_index(op.f('ix_anomaly_events_status'), table_name='anomaly_events')
    op.drop_index(op.f('ix_anomaly_events_severity'), table_name='anomaly_events')
    op.drop_index(op.f('ix_anomaly_events_anomaly_type'), table_name='anomaly_events')
    op.drop_index(op.f('ix_anomaly_events_session_id'), table_name='anomaly_events')
    op.drop_index(op.f('ix_anomaly_events_id'), table_name='anomaly_events')
    op.drop_table('anomaly_events')
