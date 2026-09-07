"""add source_type to videos table

Revision ID: 0004_add_video_source_type
Revises: 0003_create_prediction_tables
Create Date: 2026-09-07 15:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0004_add_video_source_type'
down_revision: Union[str, None] = '0003_create_prediction_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('videos', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('source_type', sa.String(length=32), nullable=False, server_default='real_world')
        )
        batch_op.create_index(batch_op.f('ix_videos_source_type'), ['source_type'], unique=False)

    # Classify existing test/fixture videos as synthetic_test
    op.execute(
        "UPDATE videos SET source_type = 'synthetic_test' "
        "WHERE original_filename LIKE 'test_%' "
        "OR original_filename LIKE 'synthetic_%' "
        "OR original_filename LIKE 'fixture_%' "
        "OR original_filename LIKE 'traffic_clip_%' "
        "OR original_filename LIKE 'traffic_camera_stream_%' "
        "OR original_filename LIKE 'live_test_%'"
    )


def downgrade() -> None:
    with op.batch_alter_table('videos', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_videos_source_type'))
        batch_op.drop_column('source_type')
