"""add_repayment_schedules_table

Revision ID: 464b43b3e131
Revises: b4f2f173743b
Create Date: 2026-03-26 10:55:09.951805

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '464b43b3e131'
down_revision: Union[str, Sequence[str], None] = 'b4f2f173743b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    
    op.create_table('repayment_schedules',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('loan_id', sa.UUID(), nullable=False),
        sa.Column('installment_number', sa.Integer(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('amount_due', sa.Numeric(10, 2), nullable=False),
        sa.Column('principal_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('interest_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('status', 
                  sa.Enum('PENDING', 'PAID', 'OVERDUE', name='repaymentstatus'),
                  nullable=False,
                  server_default='PENDING'),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), 
                  server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), 
                  server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=True),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['loan_id'], ['loans.id'], 
                                name='fk_repayment_schedules_loan_id',
                                ondelete='CASCADE'),
        
        # Primary key
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for performance
    op.create_index('ix_repayment_schedules_loan_id', 'repayment_schedules', ['loan_id'])
    op.create_index('ix_repayment_schedules_status', 'repayment_schedules', ['status'])
    op.create_index('ix_repayment_schedules_due_date', 'repayment_schedules', ['due_date'])
    op.create_index('ix_repayment_schedules_loan_status', 'repayment_schedules', 
                    ['loan_id', 'status'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_repayment_schedules_loan_status', table_name='repayment_schedules')
    op.drop_index('ix_repayment_schedules_due_date', table_name='repayment_schedules')
    op.drop_index('ix_repayment_schedules_status', table_name='repayment_schedules')
    op.drop_index('ix_repayment_schedules_loan_id', table_name='repayment_schedules')
    
    # Drop table
    op.drop_table('repayment_schedules')
    
    # Drop enum type
    op.execute("DROP TYPE IF EXISTS repaymentstatus")



