"""add foreign keys to loans

Revision ID: 4f9810568259
Revises: b1f9478cdf7b
Create Date: 2026-03-30 00:15:16.684611

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4f9810568259'
down_revision: Union[str, Sequence[str], None] = 'b1f9478cdf7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_loans_borrower",
        "loans", "users",
        ["borrower_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_loans_lender",
        "loans", "users",
        ["lender_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_loans_borrower", "loans", type_="foreignkey")
    op.drop_constraint("fk_loans_lender", "loans", type_="foreignkey")
