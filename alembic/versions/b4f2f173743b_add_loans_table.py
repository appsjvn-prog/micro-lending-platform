"""add_loans_table

Revision ID: b4f2f173743b
Revises: ac171b455c35
Create Date: 2026-03-26 10:54:47.543500

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4f2f173743b'
down_revision: Union[str, Sequence[str], None] = 'ac171b455c35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    
    op.create_table('loans',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('loan_application_id', sa.UUID(), nullable=True),
        sa.Column('borrower_id', sa.UUID(), nullable=False),
        sa.Column('lender_id', sa.UUID(), nullable=False),
        sa.Column('principal_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('tenure_months', sa.Numeric(), nullable=False),
        sa.Column('interest_rate', sa.Numeric(5, 2), nullable=False),
        sa.Column('emi_amount', sa.Numeric(10, 2), nullable=True),
        sa.Column('total_interest', sa.Numeric(10, 2), nullable=True),
        sa.Column('total_repayment', sa.Numeric(10, 2), nullable=True),
        sa.Column('status', 
                  sa.Enum('APPROVED', 'DISBURSED', 'ACTIVE', 'CLOSED', 'DEFAULTED', 
                         name='loanstatus'), 
                  nullable=False, 
                  server_default='APPROVED'),
        sa.Column('disbursed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), 
                  server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), 
                  server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=True),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['borrower_id'], ['users.id'], name='fk_loans_borrower_id'),
        sa.ForeignKeyConstraint(['lender_id'], ['users.id'], name='fk_loans_lender_id'),
        sa.ForeignKeyConstraint(['loan_application_id'], ['loan_applications.id'], 
                                name='fk_loans_application_id'),
        
        # Primary key
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for performance
    op.create_index('ix_loans_borrower_id', 'loans', ['borrower_id'])
    op.create_index('ix_loans_lender_id', 'loans', ['lender_id'])
    op.create_index('ix_loans_status', 'loans', ['status'])
    op.create_index('ix_loans_loan_application_id', 'loans', ['loan_application_id'])
    op.create_index('ix_loans_created_at', 'loans', ['created_at'])


def downgrade() -> None:
    
    op.drop_index('ix_loans_created_at', table_name='loans')
    op.drop_index('ix_loans_loan_application_id', table_name='loans')
    op.drop_index('ix_loans_status', table_name='loans')
    op.drop_index('ix_loans_lender_id', table_name='loans')
    op.drop_index('ix_loans_borrower_id', table_name='loans')
    
    # Drop table
    op.drop_table('loans')
    
    # Drop enum type
    op.execute("DROP TYPE IF EXISTS loanstatus")