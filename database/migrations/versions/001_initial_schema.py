"""Initial schema for Smart Notes

Revision ID: 001
Revises: 
Create Date: 2025-08-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create research_threads table
    op.create_table('research_threads',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('emoji', sa.String(length=10), nullable=True),
        sa.Column('domain', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('progress_score', sa.Float(), nullable=True),
        sa.Column('capture_count', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_active', sa.DateTime(timezone=True), nullable=True),
        sa.Column('topics', sa.JSON(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.CheckConstraint("status IN ('active', 'paused', 'completed', 'archived')", name='valid_status'),
        sa.CheckConstraint('progress_score >= 0.0 AND progress_score <= 1.0', name='valid_progress'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_research_threads_user_status', 'research_threads', ['user_id', 'status'])
    op.create_index('ix_research_threads_last_active', 'research_threads', ['last_active'])

    # Create reading_sessions table
    op.create_table('reading_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('thread_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('session_type', sa.String(length=100), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('context_data', sa.JSON(), nullable=True),
        sa.Column('capture_count', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['thread_id'], ['research_threads.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_reading_sessions_user_thread', 'reading_sessions', ['user_id', 'thread_id'])
    op.create_index('ix_reading_sessions_time_range', 'reading_sessions', ['start_time', 'end_time'])
    op.create_index('ix_reading_sessions_active', 'reading_sessions', ['is_active'])

    # Create captures table
    op.create_table('captures',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('thread_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reading_session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('title', sa.String(length=1000), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('capture_type', sa.String(length=100), nullable=True),
        sa.Column('intent', sa.String(length=100), nullable=True),
        sa.Column('user_note', sa.Text(), nullable=True),
        sa.Column('captured_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processing_status', sa.String(length=100), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('content_metadata', sa.JSON(), nullable=True),
        sa.Column('processed_metadata', sa.JSON(), nullable=True),
        sa.Column('resume_context', sa.JSON(), nullable=True),
        sa.Column('domain', sa.String(length=255), nullable=True),
        sa.Column('word_count', sa.Integer(), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(['reading_session_id'], ['reading_sessions.id'], ),
        sa.ForeignKeyConstraint(['thread_id'], ['research_threads.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('content_hash', 'user_id', name='uq_captures_content_user')
    )
    op.create_index('ix_captures_user_thread', 'captures', ['user_id', 'thread_id'])
    op.create_index('ix_captures_type_intent', 'captures', ['capture_type', 'intent'])
    op.create_index('ix_captures_captured_at', 'captures', ['captured_at'])
    op.create_index('ix_captures_content_hash', 'captures', ['content_hash'])
    op.create_index('ix_captures_processing_status', 'captures', ['processing_status'])

    # Create timeline_entries table
    op.create_table('timeline_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('thread_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('capture_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('entry_type', sa.String(length=100), nullable=True),
        sa.Column('resume_context', sa.JSON(), nullable=True),
        sa.Column('quick_actions', sa.JSON(), nullable=True),
        sa.Column('session_context', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['capture_id'], ['captures.id'], ),
        sa.ForeignKeyConstraint(['thread_id'], ['research_threads.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_timeline_entries_thread_time', 'timeline_entries', ['thread_id', 'timestamp'])
    op.create_index('ix_timeline_entries_user_time', 'timeline_entries', ['user_id', 'timestamp'])
    op.create_index('ix_timeline_entries_type', 'timeline_entries', ['entry_type'])

    # Create user_preferences table
    op.create_table('user_preferences',
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('default_thread_emoji', sa.String(length=10), nullable=True),
        sa.Column('session_gap_hours', sa.Integer(), nullable=True),
        sa.Column('auto_thread_assignment', sa.Boolean(), nullable=True),
        sa.Column('resume_reminders', sa.Boolean(), nullable=True),
        sa.Column('timeline_items_per_page', sa.Integer(), nullable=True),
        sa.Column('analytics_enabled', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('settings', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('user_id')
    )

def downgrade() -> None:
    op.drop_table('user_preferences')
    op.drop_table('timeline_entries')
    op.drop_table('captures')
    op.drop_table('reading_sessions')
    op.drop_table('research_threads')