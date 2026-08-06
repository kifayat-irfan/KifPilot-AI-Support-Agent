"""add_content_hash_duplicate_detection

Revision ID: a1b2c3d4e5f6
Revises: 9c4fb44178cb
Create Date: 2026-08-04 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '9c4fb44178cb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add content_hash column to documents table
    op.add_column('documents', sa.Column('content_hash', sa.String(length=64), nullable=True))
    
    # Create unique index on content_hash
    op.create_index('ix_documents_content_hash', 'documents', ['content_hash'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_documents_content_hash', table_name='documents')
    op.drop_column('documents', 'content_hash')