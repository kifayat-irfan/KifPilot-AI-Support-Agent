"""add_knowledge_base_metadata_fields

Revision ID: 9c4fb44178cb
Revises: 35eb0ddbd3ad
Create Date: 2026-08-03 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '9c4fb44178cb'
down_revision: Union[str, None] = '35eb0ddbd3ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to documents table
    op.add_column('documents', sa.Column('title', sa.String(length=500), nullable=True))
    op.add_column('documents', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('documents', sa.Column('category', sa.String(length=100), nullable=True))
    op.add_column('documents', sa.Column('tags', sqlite.JSON(), nullable=True))
    op.add_column('documents', sa.Column('language', sa.String(length=10), nullable=True))
    op.add_column('documents', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    
    # Create index on deleted_at for soft delete queries
    op.create_index('ix_documents_deleted_at', 'documents', ['deleted_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_documents_deleted_at', table_name='documents')
    op.drop_column('documents', 'deleted_at')
    op.drop_column('documents', 'language')
    op.drop_column('documents', 'tags')
    op.drop_column('documents', 'category')
    op.drop_column('documents', 'description')
    op.drop_column('documents', 'title')