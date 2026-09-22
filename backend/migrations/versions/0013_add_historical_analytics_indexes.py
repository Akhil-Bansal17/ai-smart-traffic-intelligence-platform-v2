"""add historical analytics indexes

Revision ID: 0013_add_historical_analytics_indexes
Revises: 0012_create_camera_sources_and_live_jobs
Create Date: 2026-09-22 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0013_add_historical_analytics_indexes'
down_revision: Union[str, None] = '0012_create_camera_sources_and_live_jobs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Index on traffic_metrics.created_at for temporal metrics filtering
    op.create_index(
        'ix_traffic_metrics_created_at',
        'traffic_metrics',
        ['created_at'],
        unique=False,
    )

    # 2. Compound index on analysis_sessions(started_at, status) for range + status queries
    op.create_index(
        'ix_analysis_sessions_started_status',
        'analysis_sessions',
        ['started_at', 'status'],
        unique=False,
    )

    # 3. Compound index on analysis_sessions(camera_source_id, started_at) for per-camera queries
    op.create_index(
        'ix_analysis_sessions_camera_source_started',
        'analysis_sessions',
        ['camera_source_id', 'started_at'],
        unique=False,
    )

    # 4. Compound index on lane_results(analysis_session_id, lane_id) for lane trends
    op.create_index(
        'ix_lane_results_session_lane',
        'lane_results',
        ['analysis_session_id', 'lane_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_lane_results_session_lane', table_name='lane_results')
    op.drop_index('ix_analysis_sessions_camera_source_started', table_name='analysis_sessions')
    op.drop_index('ix_analysis_sessions_started_status', table_name='analysis_sessions')
    op.drop_index('ix_traffic_metrics_created_at', table_name='traffic_metrics')
