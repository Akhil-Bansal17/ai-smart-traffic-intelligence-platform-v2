"""create analysis jobs table

Revision ID: 0009_create_analysis_jobs_table
Revises: 0008_create_anomaly_events_tables
Create Date: 2026-09-13 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0009_create_analysis_jobs_table'
down_revision: Union[str, None] = '0008_create_anomaly_events_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'analysis_jobs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('video_id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='queued'),
        sa.Column('analysis_type', sa.String(length=64), nullable=False, server_default='full_pipeline'),
        sa.Column('progress', sa.Float(), nullable=True),
        sa.Column('frames_processed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_frames', sa.Integer(), nullable=True),
        sa.Column('processing_fps', sa.Float(), nullable=True),
        sa.Column('config_snapshot', sa.JSON(), nullable=True),
        sa.Column('cancellation_requested', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('error_code', sa.String(length=64), nullable=True),
        sa.Column('error_message', sa.String(length=1024), nullable=True),
        sa.Column('provenance_category', sa.String(length=64), nullable=False, server_default='real_analysis_job'),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['analysis_sessions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_analysis_jobs_id'), 'analysis_jobs', ['id'], unique=False)
    op.create_index(op.f('ix_analysis_jobs_video_id'), 'analysis_jobs', ['video_id'], unique=False)
    op.create_index(op.f('ix_analysis_jobs_session_id'), 'analysis_jobs', ['session_id'], unique=False)
    op.create_index(op.f('ix_analysis_jobs_status'), 'analysis_jobs', ['status'], unique=False)
    op.create_index(op.f('ix_analysis_jobs_analysis_type'), 'analysis_jobs', ['analysis_type'], unique=False)
    op.create_index(op.f('ix_analysis_jobs_cancellation_requested'), 'analysis_jobs', ['cancellation_requested'], unique=False)
    op.create_index(op.f('ix_analysis_jobs_provenance_category'), 'analysis_jobs', ['provenance_category'], unique=False)
    op.create_index(op.f('ix_analysis_jobs_is_synthetic'), 'analysis_jobs', ['is_synthetic'], unique=False)
    op.create_index(op.f('ix_analysis_jobs_created_at'), 'analysis_jobs', ['created_at'], unique=False)
    op.create_index(op.f('ix_analysis_jobs_updated_at'), 'analysis_jobs', ['updated_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_analysis_jobs_updated_at'), table_name='analysis_jobs')
    op.drop_index(op.f('ix_analysis_jobs_created_at'), table_name='analysis_jobs')
    op.drop_index(op.f('ix_analysis_jobs_is_synthetic'), table_name='analysis_jobs')
    op.drop_index(op.f('ix_analysis_jobs_provenance_category'), table_name='analysis_jobs')
    op.drop_index(op.f('ix_analysis_jobs_cancellation_requested'), table_name='analysis_jobs')
    op.drop_index(op.f('ix_analysis_jobs_analysis_type'), table_name='analysis_jobs')
    op.drop_index(op.f('ix_analysis_jobs_status'), table_name='analysis_jobs')
    op.drop_index(op.f('ix_analysis_jobs_session_id'), table_name='analysis_jobs')
    op.drop_index(op.f('ix_analysis_jobs_video_id'), table_name='analysis_jobs')
    op.drop_index(op.f('ix_analysis_jobs_id'), table_name='analysis_jobs')
    op.drop_table('analysis_jobs')
