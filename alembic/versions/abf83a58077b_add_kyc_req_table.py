"""add_kyc_req_table

Revision ID: abf83a58077b
Revises: 464b43b3e131
Create Date: 2026-03-26 10:56:12.855390

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'abf83a58077b'
down_revision: Union[str, Sequence[str], None] = '464b43b3e131'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Create enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE kycstatus AS ENUM ('PENDING', 'VERIFIED', 'REJECTED');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
    """)
    
    # Create table
    op.execute("""
        CREATE TABLE IF NOT EXISTS kyc_req (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL UNIQUE,
            status kycstatus DEFAULT 'PENDING' NOT NULL,
            rejection_reason TEXT,
            verified_at TIMESTAMP WITH TIME ZONE,
            verified_by UUID,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            CONSTRAINT fk_kyc_req_user_id FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            CONSTRAINT fk_kyc_req_verified_by FOREIGN KEY(verified_by) REFERENCES users(id)
        );
    """)
    
    # Create indexes
    op.execute("CREATE INDEX IF NOT EXISTS ix_kyc_req_user_id ON kyc_req(user_id)")