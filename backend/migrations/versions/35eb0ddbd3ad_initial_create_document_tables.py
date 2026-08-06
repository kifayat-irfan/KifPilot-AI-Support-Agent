"""initial_create_document_tables

Revision ID: 35eb0ddbd3ad
Revises: 
Create Date: 2026-08-03 16:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '35eb0ddbd3ad'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', sqlite.CHAR(length=36), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('file_type', sa.String(length=50), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('uploading', 'parsing', 'chunking', 'embedding', 'storing', 'completed', 'failed', name='documentstatus'), nullable=False),
        sa.Column('page_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('chunk_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('embeddings_created', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('company', sa.String(length=255), nullable=False, server_default='default'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id', name='uq_documents_id')
    )
    op.create_index('ix_documents_id', 'documents', ['id'], unique=False)
    op.create_index('ix_documents_company', 'documents', ['company'], unique=False)
    op.create_index('ix_documents_status', 'documents', ['status'], unique=False)

    # Create document_chunks table
    op.create_table(
        'document_chunks',
        sa.Column('id', sqlite.CHAR(length=36), nullable=False),
        sa.Column('document_id', sqlite.CHAR(length=36), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('chunk_id', sqlite.CHAR(length=36), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('page', sa.Integer(), nullable=True),
        sa.Column('section', sa.String(length=500), nullable=True),
        sa.Column('heading', sa.String(length=500), nullable=True),
        sa.Column('token_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('vector_id', sqlite.CHAR(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('chunk_id', name='uq_document_chunks_chunk_id')
    )
    op.create_index('ix_document_chunks_id', 'document_chunks', ['id'], unique=False)
    op.create_index('ix_document_chunks_document_id', 'document_chunks', ['document_id'], unique=False)
    op.create_index('ix_document_chunks_chunk_id', 'document_chunks', ['chunk_id'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_document_chunks_chunk_id', table_name='document_chunks')
    op.drop_index('ix_document_chunks_document_id', table_name='document_chunks')
    op.drop_index('ix_document_chunks_id', table_name='document_chunks')
    op.drop_table('document_chunks')
    op.drop_index('ix_documents_status', table_name='documents')
    op.drop_index('ix_documents_company', table_name='documents')
    op.drop_index('ix_documents_id', table_name='documents')
    op.drop_table('documents')