"""create videos table

Revision ID: 0001_create_videos_table
Revises: 
Create Date: 2026-09-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001_create_videos_table'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'videos',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('uploaded_by', sa.String(length=36), nullable=True),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('storage_path', sa.String(length=512), nullable=False),
        sa.Column('duration_seconds', sa.Float(), nullable=False),
        sa.Column('fps', sa.Float(), nullable=False),
        sa.Column('resolution', sa.String(length=32), nullable=False),
        sa.Column('frame_count', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_videos_id'), 'videos', ['id'], unique=False)
    op.create_index(op.f('ix_videos_status'), 'videos', ['status'], unique=False)
    op.create_index(op.f('ix_videos_uploaded_at'), 'videos', ['uploaded_at'], unique=False)
    op.create_index(op.f('ix_videos_uploaded_by'), 'videos', ['uploaded_by'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_videos_uploaded_by'), table_name='videos')
    op.drop_index(op.f('ix_videos_uploaded_at'), table_name='videos')
    op.drop_index(op.f('ix_videos_status'), table_name='videos')
    op.drop_index(op.f('ix_videos_id'), table_name='videos')
    op.drop_table('videos')
