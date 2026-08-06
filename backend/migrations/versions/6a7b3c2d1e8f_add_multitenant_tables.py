"""add_multitenant_tables

Revision ID: 6a7b3c2d1e8f
Revises: 5e8f2b1a4c9d
Create Date: 2026-08-04 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '6a7b3c2d1e8f'
down_revision: Union[str, None] = '5e8f2b1a4c9d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create organizations table
    op.create_table(
        'organizations',
        sa.Column('id', sqlite.CHAR(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id', name='uq_organizations_id')
    )
    op.create_index('ix_organizations_id', 'organizations', ['id'], unique=False)
    op.create_index('ix_organizations_slug', 'organizations', ['slug'], unique=True)
    op.create_index('ix_organizations_is_active', 'organizations', ['is_active'], unique=False)

    # Create organization_settings table
    op.create_table(
        'organization_settings',
        sa.Column('id', sqlite.CHAR(length=36), nullable=False),
        sa.Column('organization_id', sqlite.CHAR(length=36), nullable=False),
        sa.Column('default_top_k', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('default_min_score', sa.Float(), nullable=False, server_default='0.65'),
        sa.Column('default_max_context', sa.Integer(), nullable=False, server_default='8000'),
        sa.Column('max_message_history', sa.Integer(), nullable=False, server_default='20'),
        sa.Column('max_tokens_context', sa.Integer(), nullable=False, server_default='8000'),
        sa.Column('embedding_model', sa.String(length=100), nullable=False, server_default='nomic-embed-text'),
        sa.Column('enable_streaming', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('enable_citations', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('enable_conversation_memory', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id', name='uq_organization_settings_id'),
        sa.UniqueConstraint('organization_id', name='uq_organization_settings_org_id')
    )
    op.create_index('ix_organization_settings_id', 'organization_settings', ['id'], unique=False)
    op.create_index('ix_organization_settings_organization_id', 'organization_settings', ['organization_id'], unique=True)

    # Create organization_members association table
    op.create_table(
        'organization_members',
        sa.Column('organization_id', sqlite.CHAR(length=36), nullable=False),
        sa.Column('user_id', sqlite.CHAR(length=36), nullable=False),
        sa.Column('role', sa.Enum('owner', 'admin', 'member', name='organizationrole'), nullable=False, server_default='member'),
        sa.Column('joined_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('organization_id', 'user_id')
    )
    op.create_index('ix_organization_members_organization_id', 'organization_members', ['organization_id'], unique=False)
    op.create_index('ix_organization_members_user_id', 'organization_members', ['user_id'], unique=False)

    # Add organization_id to documents table
    op.add_column('documents', sa.Column('organization_id', sqlite.CHAR(length=36), nullable=True))
    op.create_index('ix_documents_organization_id', 'documents', ['organization_id'], unique=False)
    op.create_foreign_key('fk_documents_organization_id', 'documents', 'organizations', ['organization_id'], ['id'], ondelete='CASCADE')

    # Add organization_id to chat_sessions table
    op.add_column('chat_sessions', sa.Column('organization_id', sqlite.CHAR(length=36), nullable=True))
    op.create_index('ix_chat_sessions_organization_id', 'chat_sessions', ['organization_id'], unique=False)
    op.create_foreign_key('fk_chat_sessions_organization_id', 'chat_sessions', 'organizations', ['organization_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    # Remove foreign keys and columns from chat_sessions
    op.drop_constraint('fk_chat_sessions_organization_id', 'chat_sessions', type_='foreignkey')
    op.drop_index('ix_chat_sessions_organization_id', table_name='chat_sessions')
    op.drop_column('chat_sessions', 'organization_id')

    # Remove foreign keys and columns from documents
    op.drop_constraint('fk_documents_organization_id', 'documents', type_='foreignkey')
    op.drop_index('ix_documents_organization_id', table_name='documents')
    op.drop_column('documents', 'organization_id')

    # Drop organization_members
    op.drop_index('ix_organization_members_user_id', table_name='organization_members')
    op.drop_index('ix_organization_members_organization_id', table_name='organization_members')
    op.drop_table('organization_members')

    # Drop organization_settings
    op.drop_index('ix_organization_settings_organization_id', table_name='organization_settings')
    op.drop_index('ix_organization_settings_id', table_name='organization_settings')
    op.drop_table('organization_settings')

    # Drop organizations
    op.drop_index('ix_organizations_is_active', table_name='organizations')
    op.drop_index('ix_organizations_slug', table_name='organizations')
    op.drop_index('ix_organizations_id', table_name='organizations')
    op.drop_table('organizations')