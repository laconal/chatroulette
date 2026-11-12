"""initial schema

Revision ID: d7849aa73a61
Revises: 
Create Date: 2026-11-13 03:50:24.756890

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'd7849aa73a61'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('users',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('telegram_user_id', sa.BigInteger(), nullable=False),
    sa.Column('username', sa.String(length=64), nullable=True),
    sa.Column('full_name', sa.String(length=256), nullable=True),
    sa.Column('gender', sa.Enum('male', 'female', name='gender', native_enum=False, length=16), nullable=True),
    sa.Column('age', sa.SmallInteger(), nullable=True),
    sa.Column('chat_language', sa.Enum('ru', 'en', 'uz', 'uz_cyrl', name='language', native_enum=False, length=16), nullable=True),
    sa.Column('ui_language', sa.Enum('ru', 'en', 'uz', 'uz_cyrl', name='language', native_enum=False, length=16), nullable=False),
    sa.Column('pref_gender', sa.Enum('male', 'female', name='gender', native_enum=False, length=16), nullable=True),
    sa.Column('pref_age_min', sa.SmallInteger(), nullable=True),
    sa.Column('pref_age_max', sa.SmallInteger(), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    sa.UniqueConstraint('telegram_user_id', name=op.f('uq_users_telegram_user_id'))
    )
    op.create_table('blocks',
    sa.Column('blocker_id', sa.BigInteger(), nullable=False),
    sa.Column('blocked_id', sa.BigInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('blocker_id <> blocked_id', name=op.f('ck_blocks_not_self')),
    sa.ForeignKeyConstraint(['blocked_id'], ['users.id'], name=op.f('fk_blocks_blocked_id_users')),
    sa.ForeignKeyConstraint(['blocker_id'], ['users.id'], name=op.f('fk_blocks_blocker_id_users')),
    sa.PrimaryKeyConstraint('blocker_id', 'blocked_id', name=op.f('pk_blocks'))
    )
    op.create_index(op.f('ix_blocks_blocked_id'), 'blocks', ['blocked_id'], unique=False)
    op.create_table('rooms',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('user1_id', sa.BigInteger(), nullable=False),
    sa.Column('user2_id', sa.BigInteger(), nullable=False),
    sa.Column('status', sa.Enum('open', 'closed', name='roomstatus', native_enum=False, length=16), server_default='open', nullable=False),
    sa.Column('close_reason', sa.Enum('left', 'idle', 'unavailable', name='closereason', native_enum=False, length=16), nullable=True),
    sa.Column('closed_by', sa.BigInteger(), nullable=True),
    sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('user1_id <> user2_id', name=op.f('ck_rooms_distinct_members')),
    sa.ForeignKeyConstraint(['closed_by'], ['users.id'], name=op.f('fk_rooms_closed_by_users')),
    sa.ForeignKeyConstraint(['user1_id'], ['users.id'], name=op.f('fk_rooms_user1_id_users')),
    sa.ForeignKeyConstraint(['user2_id'], ['users.id'], name=op.f('fk_rooms_user2_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_rooms'))
    )
    op.create_index('uq_rooms_open_user1', 'rooms', ['user1_id'], unique=True, postgresql_where=sa.text("status = 'open'"))
    op.create_index('uq_rooms_open_user2', 'rooms', ['user2_id'], unique=True, postgresql_where=sa.text("status = 'open'"))
    op.create_table('search_queue',
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_search_queue_user_id_users')),
    sa.PrimaryKeyConstraint('user_id', name=op.f('pk_search_queue'))
    )
    op.create_index('ix_search_queue_created_at', 'search_queue', ['created_at'], unique=False)
    op.create_table('messages',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('room_id', sa.BigInteger(), nullable=False),
    sa.Column('sender_id', sa.BigInteger(), nullable=False),
    sa.Column('content_type', sa.String(length=32), nullable=False),
    sa.Column('text', sa.Text(), nullable=True),
    sa.Column('file_id', sa.String(length=256), nullable=True),
    sa.Column('sender_message_id', sa.BigInteger(), nullable=False),
    sa.Column('delivered_message_id', sa.BigInteger(), nullable=True),
    sa.Column('raw', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['room_id'], ['rooms.id'], name=op.f('fk_messages_room_id_rooms')),
    sa.ForeignKeyConstraint(['sender_id'], ['users.id'], name=op.f('fk_messages_sender_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_messages'))
    )
    op.create_index('ix_messages_room_id_id', 'messages', ['room_id', 'id'], unique=False)
    op.create_table('reviews',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('room_id', sa.BigInteger(), nullable=False),
    sa.Column('author_id', sa.BigInteger(), nullable=False),
    sa.Column('target_id', sa.BigInteger(), nullable=False),
    sa.Column('score', sa.SmallInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('score BETWEEN 1 AND 5', name=op.f('ck_reviews_score_range')),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], name=op.f('fk_reviews_author_id_users')),
    sa.ForeignKeyConstraint(['room_id'], ['rooms.id'], name=op.f('fk_reviews_room_id_rooms')),
    sa.ForeignKeyConstraint(['target_id'], ['users.id'], name=op.f('fk_reviews_target_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_reviews')),
    sa.UniqueConstraint('room_id', 'author_id', name=op.f('uq_reviews_room_id'))
    )
    op.create_index(op.f('ix_reviews_target_id'), 'reviews', ['target_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_reviews_target_id'), table_name='reviews')
    op.drop_table('reviews')
    op.drop_index('ix_messages_room_id_id', table_name='messages')
    op.drop_table('messages')
    op.drop_index('ix_search_queue_created_at', table_name='search_queue')
    op.drop_table('search_queue')
    op.drop_index('uq_rooms_open_user2', table_name='rooms', postgresql_where=sa.text("status = 'open'"))
    op.drop_index('uq_rooms_open_user1', table_name='rooms', postgresql_where=sa.text("status = 'open'"))
    op.drop_table('rooms')
    op.drop_index(op.f('ix_blocks_blocked_id'), table_name='blocks')
    op.drop_table('blocks')
    op.drop_table('users')
