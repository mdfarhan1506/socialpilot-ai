"""Add unique constraint on (workspace_id, topic) for strategy_insights to prevent
duplicate Audience Baseline Learning rows, and deduplicate existing rows.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-11-09
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # 1. Deduplicate existing rows: keep the most recently created row per (workspace_id, topic).
    #    Safe for both SQLite (tests) and PostgreSQL (production).
    dialect = conn.dialect.name
    if dialect == 'sqlite':
        # SQLite: use a subquery with MIN(rowid) to identify and delete duplicates.
        conn.execute(sa.text("""
            DELETE FROM strategy_insights
            WHERE rowid NOT IN (
                SELECT MIN(rowid)
                FROM strategy_insights
                GROUP BY workspace_id, topic
            )
        """))
    else:
        # PostgreSQL: use ctid (physical row identity).
        conn.execute(sa.text("""
            DELETE FROM strategy_insights
            WHERE ctid NOT IN (
                SELECT MIN(ctid)
                FROM strategy_insights
                GROUP BY workspace_id, topic
            )
        """))

    # 2. Add the unique constraint (batch_alter_table handles SQLite's lack of ALTER COLUMN).
    existing_constraints = {c.get('name') for c in inspector.get_unique_constraints('strategy_insights')}
    if 'uq_strategy_insights_workspace_topic' not in existing_constraints:
        with op.batch_alter_table('strategy_insights') as batch_op:
            batch_op.create_unique_constraint(
                'uq_strategy_insights_workspace_topic',
                ['workspace_id', 'topic'],
            )


def downgrade() -> None:
    with op.batch_alter_table('strategy_insights') as batch_op:
        batch_op.drop_constraint('uq_strategy_insights_workspace_topic', type_='unique')
