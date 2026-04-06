"""add_transactions_table

Revision ID: 30c2760b5779
Revises: 09a1b480f6d1
Create Date: 2026-03-26 11:19:18.631230

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '30c2760b5779'
down_revision: Union[str, Sequence[str], None] = '09a1b480f6d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    
    # Create transactions table
    op.create_table('transactions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('loan_id', sa.UUID(), nullable=False),
        sa.Column('from_account_id', sa.UUID(), nullable=False),
        sa.Column('to_account_id', sa.UUID(), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('type', 
                  sa.Enum('DISBURSEMENT', 'REPAYMENT', 'REFUND', name='transactiontype'),
                  nullable=False),
        sa.Column('status', 
                  sa.Enum('INITIATED', 'SUCCESS', 'PENDING', 'FAILED', name='transactionstatus'),
                  nullable=False,
                  server_default='INITIATED'),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('reference_number', sa.String(100), nullable=True, unique=True),
        sa.Column('created_at', sa.DateTime(timezone=True), 
                  server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), 
                  server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=True),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['loan_id'], ['loans.id'], 
                                name='fk_transactions_loan_id',
                                ondelete='RESTRICT'),
        
        # Primary key
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for performance
    op.create_index('ix_transactions_loan_id', 'transactions', ['loan_id'])
    op.create_index('ix_transactions_status', 'transactions', ['status'])
    op.create_index('ix_transactions_type', 'transactions', ['type'])
    op.create_index('ix_transactions_reference_number', 'transactions', ['reference_number'])
    op.create_index('ix_transactions_created_at', 'transactions', ['created_at'])
    
    # Add check constraint for positive amount
    op.create_check_constraint(
        'ck_transactions_amount_positive',
        'transactions',
        'amount > 0'
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_transactions_created_at', table_name='transactions')
    op.drop_index('ix_transactions_reference_number', table_name='transactions')
    op.drop_index('ix_transactions_type', table_name='transactions')
    op.drop_index('ix_transactions_status', table_name='transactions')
    op.drop_index('ix_transactions_loan_id', table_name='transactions')
    
    # Drop table
    op.drop_table('transactions')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS transactionstatus")
    op.execute("DROP TYPE IF EXISTS transactiontype")
