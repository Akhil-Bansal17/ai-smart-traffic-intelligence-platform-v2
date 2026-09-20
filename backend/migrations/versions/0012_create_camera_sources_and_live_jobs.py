"""create camera sources and live jobs

Revision ID: 0012_create_camera_sources_and_live_jobs
Revises: 0011_create_reports_table
Create Date: 2026-09-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0012_create_camera_sources_and_live_jobs'
down_revision: Union[str, None] = '0011_create_reports_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create camera_sources table
    op.create_table(
        'camera_sources',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.String(length=512), nullable=True),
        sa.Column('source_type', sa.String(length=32), nullable=False, server_default='test_fixture'),
        sa.Column('connection_uri', sa.String(length=512), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='disconnected'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('location_name', sa.String(length=255), nullable=True),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('fps', sa.Float(), nullable=True),
        sa.Column('last_connected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_frame_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.String(length=1024), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_camera_sources_id'), 'camera_sources', ['id'], unique=False)
    op.create_index(op.f('ix_camera_sources_source_type'), 'camera_sources', ['source_type'], unique=False)
    op.create_index(op.f('ix_camera_sources_status'), 'camera_sources', ['status'], unique=False)
    op.create_index(op.f('ix_camera_sources_enabled'), 'camera_sources', ['enabled'], unique=False)
    op.create_index(op.f('ix_camera_sources_created_at'), 'camera_sources', ['created_at'], unique=False)

    # 2. Alter analysis_jobs to support live jobs
    with op.batch_alter_table('analysis_jobs', schema=None) as batch_op:
        batch_op.alter_column('video_id', existing_type=sa.String(length=36), nullable=True)
        batch_op.add_column(sa.Column('camera_source_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('job_mode', sa.String(length=32), nullable=False, server_default='file_analysis'))
        batch_op.create_foreign_key(
            'fk_analysis_jobs_camera_source_id',
            'camera_sources',
            ['camera_source_id'],
            ['id'],
            ondelete='CASCADE',
        )
        batch_op.create_index('ix_analysis_jobs_camera_source_id', ['camera_source_id'], unique=False)
        batch_op.create_index('ix_analysis_jobs_job_mode', ['job_mode'], unique=False)

    # 3. Alter analysis_sessions to support live sessions
    with op.batch_alter_table('analysis_sessions', schema=None) as batch_op:
        batch_op.alter_column('video_id', existing_type=sa.String(length=36), nullable=True)
        batch_op.add_column(sa.Column('camera_source_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('session_mode', sa.String(length=32), nullable=False, server_default='file_analysis'))
        batch_op.create_foreign_key(
            'fk_analysis_sessions_camera_source_id',
            'camera_sources',
            ['camera_source_id'],
            ['id'],
            ondelete='SET NULL',
        )
        batch_op.create_index('ix_analysis_sessions_camera_source_id', ['camera_source_id'], unique=False)
        batch_op.create_index('ix_analysis_sessions_session_mode', ['session_mode'], unique=False)


def downgrade() -> None:
    # Revert analysis_sessions
    with op.batch_alter_table('analysis_sessions', schema=None) as batch_op:
        batch_op.drop_index('ix_analysis_sessions_session_mode')
        batch_op.drop_index('ix_analysis_sessions_camera_source_id')
        batch_op.drop_constraint('fk_analysis_sessions_camera_source_id', type_='foreignkey')
        batch_op.drop_column('session_mode')
        batch_op.drop_column('camera_source_id')
        batch_op.alter_column('video_id', existing_type=sa.String(length=36), nullable=False)

    # Revert analysis_jobs
    with op.batch_alter_table('analysis_jobs', schema=None) as batch_op:
        batch_op.drop_index('ix_analysis_jobs_job_mode')
        batch_op.drop_index('ix_analysis_jobs_camera_source_id')
        batch_op.drop_constraint('fk_analysis_jobs_camera_source_id', type_='foreignkey')
        batch_op.drop_column('job_mode')
        batch_op.drop_column('camera_source_id')
        batch_op.alter_column('video_id', existing_type=sa.String(length=36), nullable=False)

    # Drop camera_sources table
    op.drop_index(op.f('ix_camera_sources_created_at'), table_name='camera_sources')
    op.drop_index(op.f('ix_camera_sources_enabled'), table_name='camera_sources')
    op.drop_index(op.f('ix_camera_sources_status'), table_name='camera_sources')
    op.drop_index(op.f('ix_camera_sources_source_type'), table_name='camera_sources')
    op.drop_index(op.f('ix_camera_sources_id'), table_name='camera_sources')
    op.drop_table('camera_sources')
