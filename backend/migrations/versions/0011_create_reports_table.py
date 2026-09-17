"""create reports table

Revision ID: 0011_create_reports_table
Revises: 0010_create_traffic_insights_table
Create Date: 2026-09-17 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0011_create_reports_table'
down_revision: Union[str, None] = '0010_create_traffic_insights_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'reports',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('report_type', sa.String(length=64), nullable=False, server_default='traffic_analysis'),
        sa.Column('scope_type', sa.String(length=32), nullable=False, server_default='session'),
        sa.Column('session_id', sa.String(length=36), nullable=True),
        sa.Column('time_range_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('time_range_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False, server_default='Traffic Analysis Report'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='pending'),
        sa.Column('format', sa.String(length=32), nullable=False, server_default='pdf'),
        sa.Column('file_path', sa.String(length=512), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('report_data_json', sa.JSON(), nullable=True),
        sa.Column('provenance_summary', sa.JSON(), nullable=True),
        sa.Column('artifact_metadata', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.String(length=1024), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processing_time_ms', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['analysis_sessions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reports_id'), 'reports', ['id'], unique=False)
    op.create_index(op.f('ix_reports_report_type'), 'reports', ['report_type'], unique=False)
    op.create_index(op.f('ix_reports_scope_type'), 'reports', ['scope_type'], unique=False)
    op.create_index(op.f('ix_reports_session_id'), 'reports', ['session_id'], unique=False)
    op.create_index(op.f('ix_reports_status'), 'reports', ['status'], unique=False)
    op.create_index(op.f('ix_reports_format'), 'reports', ['format'], unique=False)
    op.create_index(op.f('ix_reports_created_at'), 'reports', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_reports_created_at'), table_name='reports')
    op.drop_index(op.f('ix_reports_format'), table_name='reports')
    op.drop_index(op.f('ix_reports_status'), table_name='reports')
    op.drop_index(op.f('ix_reports_session_id'), table_name='reports')
    op.drop_index(op.f('ix_reports_scope_type'), table_name='reports')
    op.drop_index(op.f('ix_reports_report_type'), table_name='reports')
    op.drop_index(op.f('ix_reports_id'), table_name='reports')
    op.drop_table('reports')
