"""Fix trend_opportunities schema: add columns present in the model but missing from the initial migration.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-11-09

Missing columns (all were in the TrendOpportunity SQLAlchemy model but NOT created by
revision 07a099f53417):
  - source_name        VARCHAR  NULL
  - publication_date   TIMESTAMP NULL
  - retrieved_at       TIMESTAMP NULL (default NOW())
  - is_evergreen       BOOLEAN  NOT NULL (server_default FALSE)
  - trend_metadata     JSON     NULL

All ADDs are idempotent: they check the current column list and skip if already present,
so this migration is safe to re-run via `alembic upgrade head` even if partially applied.
Existing rows are preserved; no INSERT changes.

downgrade() is a no-op to protect existing production data.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    existing_cols = {c['name'] for c in inspector.get_columns('trend_opportunities')}

    with op.batch_alter_table('trend_opportunities') as batch_op:
        if 'source_name' not in existing_cols:
            batch_op.add_column(sa.Column('source_name', sa.String(), nullable=True))

        if 'publication_date' not in existing_cols:
            batch_op.add_column(sa.Column('publication_date', sa.DateTime(), nullable=True))

        if 'retrieved_at' not in existing_cols:
            # server_default so existing NULL rows get a timestamp on next UPDATE;
            # CURRENT_TIMESTAMP is supported by both SQLite (tests) and PostgreSQL (prod).
            # The Python default=datetime.utcnow fires on new inserts anyway.
            batch_op.add_column(
                sa.Column(
                    'retrieved_at',
                    sa.DateTime(),
                    nullable=True,
                    server_default=sa.text('CURRENT_TIMESTAMP'),
                )
            )

        if 'is_evergreen' not in existing_cols:
            # NOT NULL with server_default FALSE so existing rows are valid immediately.
            batch_op.add_column(
                sa.Column(
                    'is_evergreen',
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                )
            )

        if 'trend_metadata' not in existing_cols:
            batch_op.add_column(sa.Column('trend_metadata', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Intentional no-op: dropping these columns on a live Neon database could
    # permanently destroy data. The owner must perform any rollback manually
    # after a full backup.
    pass
