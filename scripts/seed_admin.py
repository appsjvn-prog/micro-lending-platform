#!/usr/bin/env python
"""Seed script to create first admin user"""
import sys
import os
from pathlib import Path

# Add project root to path so we can import app modules
sys.path.append(str(Path(__file__).parent.parent))

import getpass
from app.core.database import SessionLocal
from app.models.user import User, UserRole, UserStatus
from app.core.security import get_password_hash

def create_admin():
    """Create the first admin user"""
    db = SessionLocal()
    
    try:
        # Check if admin already exists
        existing_admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
        if existing_admin:
            print(f"❌ Admin already exists: {existing_admin.email}")
            print("Use the admin promotion endpoint to create more admins.")
            return
        
        print("\n Create First Admin User")
        print("-" * 30)
        
        email = input("Email: ").strip()
        if not email:
            print("❌ Email is required")
            return
        
        # Ask for country code and national number separately
        country_code = input("Country Code (e.g., +91): ").strip()
        if not country_code:
            country_code = "+91"  # Default to India
            print(f"Using default country code: {country_code}")
        
        national_number = input("Phone Number (without country code): ").strip()
        if not national_number:
            print("❌ Phone number is required")
            return
        
        password = getpass.getpass("Password: ")
        if not password:
            print("❌ Password is required")
            return
        
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("❌ Passwords do not match")
            return
        
        # Create admin with new phone structure
        admin = User(
            email=email,
            country_code=country_code,
            national_number=national_number,
            password_hash=get_password_hash(password),
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE
        )
        
        db.add(admin)
        db.commit()
        print(f"\n✅ Admin created successfully!")
        print(f"Email: {email}")
        print(f"Phone: {country_code} {national_number}")
        print("You can now log in with this account.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()