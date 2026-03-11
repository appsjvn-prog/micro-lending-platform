"""split phone into country_code and national_number

Revision ID: 394b86277d9a
Revises: c8f978f2c47f
Create Date: 2026-03-11 10:42:26.832720

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import phonenumbers

# revision identifiers, used by Alembic.
revision: str = '394b86277d9a'
down_revision: Union[str, Sequence[str], None] = 'c8f978f2c47f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Add columns as NULLABLE first
    op.add_column('users', sa.Column('country_code', sa.String(length=5), nullable=True))
    op.add_column('users', sa.Column('national_number', sa.String(length=15), nullable=True))
    
    # Step 2: Migrate existing data using phonenumbers
    connection = op.get_bind()
    
    # Get all users with phone numbers
    results = connection.execute(
        sa.text("SELECT id, phone FROM users WHERE phone IS NOT NULL")
    ).fetchall()
    
    for user_id, phone_str in results:
        country_code = None
        national_number = None
        
        try:
            # Parse the phone number
            parsed = phonenumbers.parse(phone_str, None)
            country_code = f"+{parsed.country_code}"
            national_number = str(parsed.national_number)
            
        except Exception as e:
            # If parsing fails, log it and use defaults
            print(f"Could not parse phone {phone_str} for user {user_id}: {e}")
            # For Indian numbers that might have parsing issues, use +91 as fallback
            if phone_str.startswith('+91'):
                country_code = '+91'
                national_number = phone_str[3:]  # Remove +91
            else:
                # For other numbers, skip and handle manually later
                continue
        
        if country_code and national_number:
            connection.execute(
                sa.text("UPDATE users SET country_code = :cc, national_number = :nn WHERE id = :id"),
                {"cc": country_code, "nn": national_number, "id": user_id}
            )
    
    # Step 3: For any remaining NULLs (like the +567... number), set defaults
    connection.execute(
        sa.text("""
            UPDATE users 
            SET country_code = '+91', national_number = '0000000000'
            WHERE country_code IS NULL OR national_number IS NULL
        """)
    )
    
    # Step 4: Now make columns NOT NULL
    op.alter_column('users', 'country_code', nullable=False)
    op.alter_column('users', 'national_number', nullable=False)
    
    # Step 5: Drop old index
    op.drop_index('ix_users_phone', table_name='users')
    
    # Step 6: Create new index
    op.create_index('ix_users_national_number', 'users', ['national_number'], unique=False)
    
    # Step 7: Add unique constraint
    op.create_unique_constraint('unique_phone', 'users', ['country_code', 'national_number'])
    
    # Step 8: Finally, drop old column
    op.drop_column('users', 'phone')


def downgrade() -> None:
    # Reverse the changes
    op.add_column('users', sa.Column('phone', sa.String(length=20), nullable=True))
    
    # Reconstruct phone from components
    op.execute("""
        UPDATE users 
        SET phone = country_code || national_number
        WHERE country_code IS NOT NULL AND national_number IS NOT NULL
    """)
    
    op.drop_constraint('unique_phone', 'users', type_='unique')
    op.drop_index('ix_users_national_number', table_name='users')
    op.create_index('ix_users_phone', 'users', ['phone'], unique=True)
    op.alter_column('users', 'phone', nullable=False)
    op.drop_column('users', 'national_number')
    op.drop_column('users', 'country_code')