"""remove unused columns from lender_profiles

Revision ID: b26ec8e8e360
Revises: 4f9810568259
Create Date: 2026-03-30 11:55:30.148833

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b26ec8e8e360'
down_revision: Union[str, Sequence[str], None] = '4f9810568259'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove unused columns from lender_profiles"""
    
    # Only remove the columns you don't need
    with op.batch_alter_table('lender_profiles') as batch_op:
        # Drop columns if they exist
        batch_op.drop_column('available_balance')
        batch_op.drop_column('total_lent')
        batch_op.drop_column('default_min_amount')
        batch_op.drop_column('default_max_amount')
        batch_op.drop_column('default_min_tenure')
        batch_op.drop_column('default_max_tenure')
        batch_op.drop_column('default_interest_rate')
    
    # If you also need to make other columns nullable or change defaults:
    with op.batch_alter_table('lender_profiles') as batch_op:
        batch_op.alter_column('risk_appetite',
               existing_type=sa.Enum('LOW', 'MEDIUM', 'HIGH', name='riskappetite'),
               nullable=True)
        batch_op.alter_column('status',
               existing_type=sa.Enum('ACTIVE', 'INACTIVE', name='lenderstatus'),
               nullable=True)


def downgrade() -> None:
    """Re-add the columns (but they will be empty)"""
    
    with op.batch_alter_table('lender_profiles') as batch_op:
        # Add back the columns (nullable since we don't have original data)
        batch_op.add_column(sa.Column('available_balance', sa.Numeric(10, 2), nullable=True))
        batch_op.add_column(sa.Column('total_lent', sa.Numeric(10, 2), nullable=True))
        batch_op.add_column(sa.Column('default_min_amount', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('default_max_amount', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('default_min_tenure', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('default_max_tenure', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('default_interest_rate', sa.Float(), nullable=True))