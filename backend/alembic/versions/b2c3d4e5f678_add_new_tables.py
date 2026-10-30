"""Add comments, meta_tokens tables; extend scheduled_posts with direct fields.

Revision ID: b2c3d4e5f678
Revises: 07a099f53417
Create Date: 2026-10-30

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b2c3d4e5f678'
down_revision: Union[str, Sequence[str], None] = '07a099f53417'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add direct fields to scheduled_posts
    with op.batch_alter_table('scheduled_posts') as batch_op:
        batch_op.alter_column('draft_id', nullable=True)
        batch_op.add_column(sa.Column('workspace_id', sa.UUID(), nullable=True))
        batch_op.add_column(sa.Column('user_id', sa.UUID(), nullable=True))
        batch_op.add_column(sa.Column('caption', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('image_url', sa.String(), nullable=True))

    # Create comments table
    op.create_table(
        'comments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('post_id', sa.String(), nullable=True),
        sa.Column('author', sa.String(), nullable=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('platform_comment_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create meta_tokens table
    op.create_table(
        'meta_tokens',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('ig_user_id', sa.String(), nullable=True),
        sa.Column('encrypted_token', sa.Text(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )


def downgrade() -> None:
    op.drop_table('meta_tokens')
    op.drop_table('comments')
    with op.batch_alter_table('scheduled_posts') as batch_op:
        batch_op.drop_column('image_url')
        batch_op.drop_column('caption')
        batch_op.drop_column('user_id')
        batch_op.drop_column('workspace_id')
        batch_op.alter_column('draft_id', nullable=False)
