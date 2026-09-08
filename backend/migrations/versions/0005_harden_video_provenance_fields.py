"""Harden video provenance fields and trust boundary

Revision ID: 0005_harden_video_provenance_fields
Revises: 0004_add_video_source_type
Create Date: 2026-09-08 10:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0005_harden_video_provenance_fields'
down_revision: Union[str, None] = '0004_add_video_source_type'
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add provenance fields with safe defaults
    with op.batch_alter_table('videos', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('source_reference', sa.String(length=255), nullable=True)
        )
        batch_op.add_column(
            sa.Column('license_reference', sa.String(length=255), nullable=True)
        )
        batch_op.add_column(
            sa.Column('provenance_note', sa.String(length=512), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                'provenance_verified',
                sa.Boolean(),
                nullable=False,
                server_default=sa.text('0'),
            )
        )
        batch_op.add_column(
            sa.Column('captured_at', sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.create_index(
            'ix_videos_provenance_verified', ['provenance_verified'], unique=False
        )

    # 2. Backfill existing synthetic test videos with truthful provenance metadata
    op.execute(
        sa.text(
            "UPDATE videos SET "
            "source_type = 'synthetic_test', "
            "source_reference = 'internal://test_fixtures', "
            "license_reference = 'Proprietary Test Fixture', "
            "provenance_note = 'Phase 11 synthetic pipeline fixture clip', "
            "provenance_verified = 1 "
            "WHERE source_type = 'synthetic_test' OR source_type = 'real_world' OR source_type IS NULL"
        )
    )


def downgrade() -> None:
    with op.batch_alter_table('videos', schema=None) as batch_op:
        batch_op.drop_index('ix_videos_provenance_verified')
        batch_op.drop_column('captured_at')
        batch_op.drop_column('provenance_verified')
        batch_op.drop_column('provenance_note')
        batch_op.drop_column('license_reference')
        batch_op.drop_column('source_reference')
