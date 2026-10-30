"""Add autonomous creator tables and extend scheduled_posts.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f678
Create Date: 2026-10-30

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f678'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # 1. Create autonomous_configs
    if 'autonomous_configs' not in existing_tables:
        op.create_table(
            'autonomous_configs',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('workspace_id', UUID(as_uuid=True), sa.ForeignKey('workspaces.id'), unique=True, nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('approval_mode', sa.String(), nullable=False, server_default='manual_for_sensitive'),
            sa.Column('min_posts_per_day', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('max_posts_per_day', sa.Integer(), nullable=False, server_default='3'),
            sa.Column('quiet_hours_start', sa.Integer(), nullable=False, server_default='22'),
            sa.Column('quiet_hours_end', sa.Integer(), nullable=False, server_default='7'),
            sa.Column('restricted_keywords', sa.JSON(), nullable=True),
            sa.Column('target_topics', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
        )

    # 2. Create strategy_insights
    if 'strategy_insights' not in existing_tables:
        op.create_table(
            'strategy_insights',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('workspace_id', UUID(as_uuid=True), sa.ForeignKey('workspaces.id'), nullable=False),
            sa.Column('topic', sa.String(), nullable=False),
            sa.Column('hook_type', sa.String(), nullable=True),
            sa.Column('format_type', sa.String(), nullable=True),
            sa.Column('best_time_slot', sa.String(), nullable=True),
            sa.Column('performance_score', sa.Float(), nullable=True, server_default='0.0'),
            sa.Column('hypothesis', sa.Text(), nullable=False),
            sa.Column('recommendation', sa.Text(), nullable=False),
            sa.Column('confidence_score', sa.Float(), nullable=True, server_default='0.5'),
            sa.Column('is_mock', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('evidence_data', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
        )

    # 3. Create post_analytics_observations
    if 'post_analytics_observations' not in existing_tables:
        op.create_table(
            'post_analytics_observations',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('workspace_id', UUID(as_uuid=True), sa.ForeignKey('workspaces.id'), nullable=False),
            sa.Column('scheduled_post_id', UUID(as_uuid=True), sa.ForeignKey('scheduled_posts.id'), nullable=False),
            sa.Column('platform_post_id', sa.String(), nullable=True),
            sa.Column('post_age_hours', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('impressions', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('reach', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('likes', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('comments', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('shares', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('saves', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('engagement_rate', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('data_provenance', sa.String(), nullable=False, server_default='mock_simulation'),
            sa.Column('recorded_at', sa.DateTime(), nullable=False),
        )

    # 4. Create automation_audit_logs
    if 'automation_audit_logs' not in existing_tables:
        op.create_table(
            'automation_audit_logs',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('workspace_id', UUID(as_uuid=True), sa.ForeignKey('workspaces.id'), nullable=False),
            sa.Column('action', sa.String(), nullable=False),
            sa.Column('status', sa.String(), nullable=False, server_default='success'),
            sa.Column('summary', sa.String(), nullable=False),
            sa.Column('details', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
        )

    # 5. Extend scheduled_posts
    existing_post_cols = [c['name'] for c in inspector.get_columns('scheduled_posts')]
    with op.batch_alter_table('scheduled_posts') as batch_op:
        if 'workspace_id' not in existing_post_cols:
            batch_op.add_column(sa.Column('workspace_id', UUID(as_uuid=True), sa.ForeignKey('workspaces.id'), nullable=True))
        if 'user_id' not in existing_post_cols:
            batch_op.add_column(sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True))
        if 'caption' not in existing_post_cols:
            batch_op.add_column(sa.Column('caption', sa.Text(), nullable=True))
        if 'image_url' not in existing_post_cols:
            batch_op.add_column(sa.Column('image_url', sa.String(), nullable=True))
        if 'concept' not in existing_post_cols:
            batch_op.add_column(sa.Column('concept', sa.String(), nullable=True))
        if 'hook' not in existing_post_cols:
            batch_op.add_column(sa.Column('hook', sa.Text(), nullable=True))
        if 'script_or_body' not in existing_post_cols:
            batch_op.add_column(sa.Column('script_or_body', sa.Text(), nullable=True))
        if 'call_to_action' not in existing_post_cols:
            batch_op.add_column(sa.Column('call_to_action', sa.String(), nullable=True))
        if 'requires_approval' not in existing_post_cols:
            batch_op.add_column(sa.Column('requires_approval', sa.Boolean(), nullable=True, server_default=sa.false()))
        if 'approved_at' not in existing_post_cols:
            batch_op.add_column(sa.Column('approved_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('scheduled_posts') as batch_op:
        batch_op.drop_column('approved_at')
        batch_op.drop_column('requires_approval')
        batch_op.drop_column('call_to_action')
        batch_op.drop_column('script_or_body')
        batch_op.drop_column('hook')
        batch_op.drop_column('concept')

    op.drop_table('automation_audit_logs')
    op.drop_table('post_analytics_observations')
    op.drop_table('strategy_insights')
    op.drop_table('autonomous_configs')
