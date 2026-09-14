"""create traffic insights table

Revision ID: 0010_create_traffic_insights_table
Revises: 0009_create_analysis_jobs_table
Create Date: 2026-09-14 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0010_create_traffic_insights_table'
down_revision: Union[str, None] = '0009_create_analysis_jobs_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'traffic_insights',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=True),
        sa.Column('job_id', sa.String(length=36), nullable=True),
        sa.Column('insight_type', sa.String(length=64), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=False, server_default='CONGESTION'),
        sa.Column('severity', sa.String(length=32), nullable=False, server_default='INFO'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='NEW'),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('start_timestamp_seconds', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('end_timestamp_seconds', sa.Float(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('affected_lane_id', sa.String(length=64), nullable=True),
        sa.Column('affected_lane_name', sa.String(length=128), nullable=True),
        sa.Column('root_cause_observed', sa.JSON(), nullable=True),
        sa.Column('root_cause_inferred', sa.JSON(), nullable=True),
        sa.Column('recommendation', sa.Text(), nullable=True),
        sa.Column('recommendation_rationale', sa.Text(), nullable=True),
        sa.Column('recommendation_type', sa.String(length=64), nullable=True, server_default='none'),
        sa.Column('evidence_package', sa.JSON(), nullable=True),
        sa.Column('limitations', sa.JSON(), nullable=True),
        sa.Column('provenance_category', sa.String(length=64), nullable=False, server_default='real_database_metrics'),
        sa.Column('is_synthetic', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('dedup_signature', sa.String(length=128), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['analysis_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_id'], ['analysis_jobs.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_traffic_insights_id'), 'traffic_insights', ['id'], unique=False)
    op.create_index(op.f('ix_traffic_insights_session_id'), 'traffic_insights', ['session_id'], unique=False)
    op.create_index(op.f('ix_traffic_insights_job_id'), 'traffic_insights', ['job_id'], unique=False)
    op.create_index(op.f('ix_traffic_insights_insight_type'), 'traffic_insights', ['insight_type'], unique=False)
    op.create_index(op.f('ix_traffic_insights_category'), 'traffic_insights', ['category'], unique=False)
    op.create_index(op.f('ix_traffic_insights_severity'), 'traffic_insights', ['severity'], unique=False)
    op.create_index(op.f('ix_traffic_insights_status'), 'traffic_insights', ['status'], unique=False)
    op.create_index(op.f('ix_traffic_insights_affected_lane_id'), 'traffic_insights', ['affected_lane_id'], unique=False)
    op.create_index(op.f('ix_traffic_insights_provenance_category'), 'traffic_insights', ['provenance_category'], unique=False)
    op.create_index(op.f('ix_traffic_insights_is_synthetic'), 'traffic_insights', ['is_synthetic'], unique=False)
    op.create_index(op.f('ix_traffic_insights_dedup_signature'), 'traffic_insights', ['dedup_signature'], unique=False)
    op.create_index(op.f('ix_traffic_insights_created_at'), 'traffic_insights', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_traffic_insights_created_at'), table_name='traffic_insights')
    op.drop_index(op.f('ix_traffic_insights_dedup_signature'), table_name='traffic_insights')
    op.drop_index(op.f('ix_traffic_insights_is_synthetic'), table_name='traffic_insights')
    op.drop_index(op.f('ix_traffic_insights_provenance_category'), table_name='traffic_insights')
    op.drop_index(op.f('ix_traffic_insights_affected_lane_id'), table_name='traffic_insights')
    op.drop_index(op.f('ix_traffic_insights_status'), table_name='traffic_insights')
    op.drop_index(op.f('ix_traffic_insights_severity'), table_name='traffic_insights')
    op.drop_index(op.f('ix_traffic_insights_category'), table_name='traffic_insights')
    op.drop_index(op.f('ix_traffic_insights_insight_type'), table_name='traffic_insights')
    op.drop_index(op.f('ix_traffic_insights_job_id'), table_name='traffic_insights')
    op.drop_index(op.f('ix_traffic_insights_session_id'), table_name='traffic_insights')
    op.drop_index(op.f('ix_traffic_insights_id'), table_name='traffic_insights')
    op.drop_table('traffic_insights')
