"""create analysis sessions, traffic metrics, lane results, and crossing events tables

Revision ID: 0002_create_analysis_tables
Revises: 0001_create_videos_table
Create Date: 2026-09-06 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002_create_analysis_tables'
down_revision: Union[str, None] = '0001_create_videos_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create analysis_sessions table
    op.create_table(
        'analysis_sessions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('video_id', sa.String(length=36), nullable=False),
        sa.Column('analysis_type', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processing_time_ms', sa.Float(), nullable=True),
        sa.Column('total_frames_processed', sa.Integer(), nullable=False),
        sa.Column('total_vehicles_detected', sa.Integer(), nullable=False),
        sa.Column('total_vehicles_counted', sa.Integer(), nullable=False),
        sa.Column('config_snapshot', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.String(length=1024), nullable=True),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_analysis_sessions_id'), 'analysis_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_analysis_sessions_video_id'), 'analysis_sessions', ['video_id'], unique=False)
    op.create_index(op.f('ix_analysis_sessions_analysis_type'), 'analysis_sessions', ['analysis_type'], unique=False)
    op.create_index(op.f('ix_analysis_sessions_status'), 'analysis_sessions', ['status'], unique=False)
    op.create_index(op.f('ix_analysis_sessions_started_at'), 'analysis_sessions', ['started_at'], unique=False)

    # 2. Create traffic_metrics table
    op.create_table(
        'traffic_metrics',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('analysis_session_id', sa.String(length=36), nullable=False),
        sa.Column('observation_duration_seconds', sa.Float(), nullable=False),
        sa.Column('total_volume', sa.Integer(), nullable=False),
        sa.Column('flow_rate_per_minute', sa.Float(), nullable=False),
        sa.Column('flow_rate_per_hour', sa.Float(), nullable=False),
        sa.Column('is_extrapolated', sa.Boolean(), nullable=False),
        sa.Column('class_distribution', sa.JSON(), nullable=True),
        sa.Column('direction_distribution', sa.JSON(), nullable=True),
        sa.Column('time_series_buckets', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['analysis_session_id'], ['analysis_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_traffic_metrics_id'), 'traffic_metrics', ['id'], unique=False)
    op.create_index(op.f('ix_traffic_metrics_analysis_session_id'), 'traffic_metrics', ['analysis_session_id'], unique=False)

    # 3. Create lane_results table
    op.create_table(
        'lane_results',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('analysis_session_id', sa.String(length=36), nullable=False),
        sa.Column('lane_id', sa.String(length=64), nullable=False),
        sa.Column('lane_name', sa.String(length=128), nullable=False),
        sa.Column('direction_hint', sa.String(length=64), nullable=True),
        sa.Column('polygon_json', sa.JSON(), nullable=True),
        sa.Column('polygon_area_px2', sa.Float(), nullable=False),
        sa.Column('unique_vehicles_count', sa.Integer(), nullable=False),
        sa.Column('peak_occupancy', sa.Integer(), nullable=False),
        sa.Column('average_occupancy', sa.Float(), nullable=False),
        sa.Column('image_space_density', sa.Float(), nullable=False),
        sa.Column('normalized_density_score', sa.Float(), nullable=False),
        sa.Column('vehicle_class_counts', sa.JSON(), nullable=True),
        sa.Column('density_unit', sa.String(length=32), nullable=False),
        sa.Column('density_calibration_warning', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['analysis_session_id'], ['analysis_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lane_results_id'), 'lane_results', ['id'], unique=False)
    op.create_index(op.f('ix_lane_results_analysis_session_id'), 'lane_results', ['analysis_session_id'], unique=False)
    op.create_index(op.f('ix_lane_results_lane_id'), 'lane_results', ['lane_id'], unique=False)

    # 4. Create crossing_events table
    op.create_table(
        'crossing_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('analysis_session_id', sa.String(length=36), nullable=False),
        sa.Column('track_id', sa.Integer(), nullable=False),
        sa.Column('class_name', sa.String(length=32), nullable=False),
        sa.Column('direction', sa.String(length=32), nullable=False),
        sa.Column('frame_index', sa.Integer(), nullable=False),
        sa.Column('timestamp_seconds', sa.Float(), nullable=False),
        sa.Column('centroid_x', sa.Float(), nullable=False),
        sa.Column('centroid_y', sa.Float(), nullable=False),
        sa.Column('line_label', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['analysis_session_id'], ['analysis_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('analysis_session_id', 'track_id', 'line_label', name='uq_crossing_event_session_track_line')
    )
    op.create_index(op.f('ix_crossing_events_id'), 'crossing_events', ['id'], unique=False)
    op.create_index(op.f('ix_crossing_events_analysis_session_id'), 'crossing_events', ['analysis_session_id'], unique=False)
    op.create_index(op.f('ix_crossing_events_track_id'), 'crossing_events', ['track_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_crossing_events_track_id'), table_name='crossing_events')
    op.drop_index(op.f('ix_crossing_events_analysis_session_id'), table_name='crossing_events')
    op.drop_index(op.f('ix_crossing_events_id'), table_name='crossing_events')
    op.drop_table('crossing_events')

    op.drop_index(op.f('ix_lane_results_lane_id'), table_name='lane_results')
    op.drop_index(op.f('ix_lane_results_analysis_session_id'), table_name='lane_results')
    op.drop_index(op.f('ix_lane_results_id'), table_name='lane_results')
    op.drop_table('lane_results')

    op.drop_index(op.f('ix_traffic_metrics_analysis_session_id'), table_name='traffic_metrics')
    op.drop_index(op.f('ix_traffic_metrics_id'), table_name='traffic_metrics')
    op.drop_table('traffic_metrics')

    op.drop_index(op.f('ix_analysis_sessions_started_at'), table_name='analysis_sessions')
    op.drop_index(op.f('ix_analysis_sessions_status'), table_name='analysis_sessions')
    op.drop_index(op.f('ix_analysis_sessions_analysis_type'), table_name='analysis_sessions')
    op.drop_index(op.f('ix_analysis_sessions_video_id'), table_name='analysis_sessions')
    op.drop_index(op.f('ix_analysis_sessions_id'), table_name='analysis_sessions')
    op.drop_table('analysis_sessions')
