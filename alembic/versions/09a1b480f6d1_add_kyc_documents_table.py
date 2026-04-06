"""add_kyc_documents_table

Revision ID: 09a1b480f6d1
Revises: abf83a58077b
Create Date: 2026-03-26 10:56:21.939285

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '09a1b480f6d1'
down_revision: Union[str, Sequence[str], None] = 'abf83a58077b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum first (if not exists)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE kycdocumenttype AS ENUM ('PAN', 'AADHAAR', 'SALARY_SLIP');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
    """)
    
    # Create table only if it doesn't exist
    op.execute("""
        CREATE TABLE IF NOT EXISTS kyc_documents (
            id UUID PRIMARY KEY,
            request_id UUID NOT NULL,
            doc_type kycdocumenttype NOT NULL,
            file_url TEXT NOT NULL UNIQUE,
            uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            CONSTRAINT fk_kyc_documents_request_id FOREIGN KEY(request_id) REFERENCES kyc_req(id) ON DELETE CASCADE
        );
    """)
    
    # Create indexes (IF NOT EXISTS)
    op.execute("CREATE INDEX IF NOT EXISTS ix_kyc_documents_request_id ON kyc_documents(request_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_kyc_documents_doc_type ON kyc_documents(doc_type)")


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_kyc_documents_doc_type', table_name='kyc_documents')
    op.drop_index('ix_kyc_documents_request_id', table_name='kyc_documents')
    
    # Drop table
    op.drop_table('kyc_documents')
    
    # Drop enum type
    op.execute("DROP TYPE IF EXISTS kycdocumenttype")