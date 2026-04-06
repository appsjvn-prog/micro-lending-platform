# tests/test_integration.py - Simplified version

import pytest
from decimal import Decimal
import uuid
from app.core.security import create_access_token
from app.models.user import User, UserRole, UserStatus
from app.services.otp_service import OTPService
from app.models.lender_profile import LenderProfile, LenderStatus


@pytest.fixture
def admin_headers(db):
    """Get admin authentication headers"""
    admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
    if not admin:
        admin = User(
            id=uuid.uuid4(),
            email=f"admin_{uuid.uuid4().hex[:8]}@example.com",
            country_code="+91",
            national_number="9876543212",
            password_hash="hashed_password",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
    
    token = create_access_token(data={"sub": str(admin.id)})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def test_borrower(client, db):
    """Create a fresh borrower for each test"""
    email = f"borrower_{uuid.uuid4().hex[:8]}@example.com"
    phone = "9876543210"
    
    # Register
    reg_response = client.post("/register", json={
        "email": email,
        "phone": {"country_code": "+91", "national_number": phone},
        "role": "BORROWER"
    })
    assert reg_response.status_code == 201
    user_id = reg_response.json()["id"]
    
    # Setup OTP and password
    otp_service = OTPService(db)
    phone_full = f"+91{phone}"
    
    from app.models.otp import OTPVerification
    otp_record = db.query(OTPVerification).filter(
        OTPVerification.phone == phone_full
    ).order_by(OTPVerification.created_at.desc()).first()
    
    if otp_record:
        otp_record.is_used = True
        db.commit()
    
    new_otp = otp_service.create_otp(
        email=email, phone=phone_full, purpose="REGISTRATION", user_id=str(user_id)
    )
    
    verify = client.post("/otp/verify", json={"user_id": user_id, "otp_code": new_otp.otp_code})
    assert verify.status_code == 200
    temp_token = verify.json()["temp_token"]
    
    pwd_response = client.post("/auth/set-password", json={
        "token": temp_token, "password": "Test@123", "confirm_password": "Test@123"
    })
    assert pwd_response.status_code == 200
    
    access_token = pwd_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    return {"id": user_id, "email": email, "phone": phone, "headers": headers}


@pytest.fixture
def test_lender(client, db):
    """Create a fresh lender for each test"""
    email = f"lender_{uuid.uuid4().hex[:8]}@example.com"
    phone = "9876543211"
    
    # Register
    reg_response = client.post("/register", json={
        "email": email,
        "phone": {"country_code": "+91", "national_number": phone},
        "role": "LENDER"
    })
    assert reg_response.status_code == 201
    user_id = reg_response.json()["id"]
    
    # Setup OTP and password
    otp_service = OTPService(db)
    phone_full = f"+91{phone}"
    
    from app.models.otp import OTPVerification
    otp_record = db.query(OTPVerification).filter(
        OTPVerification.phone == phone_full
    ).order_by(OTPVerification.created_at.desc()).first()
    
    if otp_record:
        otp_record.is_used = True
        db.commit()
    
    new_otp = otp_service.create_otp(
        email=email, phone=phone_full, purpose="REGISTRATION", user_id=str(user_id)
    )
    
    verify = client.post("/otp/verify", json={"user_id": user_id, "otp_code": new_otp.otp_code})
    assert verify.status_code == 200
    temp_token = verify.json()["temp_token"]
    
    pwd_response = client.post("/auth/set-password", json={
        "token": temp_token, "password": "Test@123", "confirm_password": "Test@123"
    })
    assert pwd_response.status_code == 200
    
    access_token = pwd_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    return {"id": user_id, "email": email, "phone": phone, "headers": headers}

def create_borrower_with_bank_account(client, db):
    """Helper to create a borrower with bank account"""
    borrower_email = f"borrower_{uuid.uuid4().hex[:8]}@example.com"
    borrower_phone = "9876543210"
    
    # Register
    reg_response = client.post("/register", json={
        "email": borrower_email,
        "phone": {"country_code": "+91", "national_number": borrower_phone},
        "role": "BORROWER"
    })
    assert reg_response.status_code == 201
    borrower_id = reg_response.json()["id"]
    
    # Setup password
    from app.models.otp import OTPVerification
    otp_service = OTPService(db)
    phone_full = f"+91{borrower_phone}"
    
    otp_record = db.query(OTPVerification).filter(
        OTPVerification.phone == phone_full
    ).order_by(OTPVerification.created_at.desc()).first()
    
    if otp_record:
        otp_record.is_used = True
        db.commit()
    
    new_otp = otp_service.create_otp(
        email=borrower_email, phone=phone_full, purpose="REGISTRATION", user_id=str(borrower_id)
    )
    
    verify = client.post("/otp/verify", json={"user_id": borrower_id, "otp_code": new_otp.otp_code})
    assert verify.status_code == 200
    temp_token = verify.json()["temp_token"]
    
    pwd_response = client.post("/auth/set-password", json={
        "token": temp_token, "password": "Test@123", "confirm_password": "Test@123"
    })
    assert pwd_response.status_code == 200
    access_token = pwd_response.json()["access_token"]
    borrower_headers = {"Authorization": f"Bearer {access_token}"}
    
    # Create user profile
    client.post("/user/profile", json={
        "first_name": "Test",
        "last_name": "Borrower",
        "dob": "1990-01-01",
        "gender": "MALE",
        "email": borrower_email,
        "mobile": {"country_code": "+91", "national_number": borrower_phone}
    }, headers=borrower_headers)
    
    # Create borrower profile
    client.post("/borrower/profile", json={
        "employment_type": "SALARIED",
        "monthly_income": 50000,
        "employer_name": "Tech Corp",
        "current_job_tenure_months": 24,
        "total_work_experience_years": 5
    }, headers=borrower_headers)
    
    # Add bank account
    client.post("/bank-accounts", json={
        "bank_name": "SBI",
        "account_holder_name": "Test Borrower",
        "account_type": "SAVINGS",
        "account_number": "123456789012",
        "ifsc_code": "SBIN0001234",
        "is_primary": True
    }, headers=borrower_headers)
    
    return {"id": borrower_id, "headers": borrower_headers}

# ============== INDIVIDUAL TEST CASES ==============

class TestUserProfile:
    """Test user profile creation"""
    
    def test_borrower_profile(self, client, test_borrower):
        """Test creating user profile for borrower"""
        response = client.post("/user/profile", json={
            "first_name": "Test",
            "last_name": "Borrower",
            "dob": "1990-01-01",
            "gender": "MALE",
            "email": test_borrower["email"],
            "mobile": {"country_code": "+91", "national_number": test_borrower["phone"]}
        }, headers=test_borrower["headers"])
        
        print(f"\nUser profile response: {response.status_code}")
        if response.status_code != 201:
            print(f"Error: {response.text}")
        
        assert response.status_code == 201
    
    def test_borrower_employment_profile(self, client, test_borrower):
        """Test creating borrower employment profile"""
        # First create user profile
        user_profile = client.post("/user/profile", json={
            "first_name": "Test",
            "last_name": "Borrower",
            "dob": "1990-01-01",
            "gender": "MALE",
            "email": test_borrower["email"],
            "mobile": {"country_code": "+91", "national_number": test_borrower["phone"]}
        }, headers=test_borrower["headers"])
        assert user_profile.status_code == 201
        
        # Now create borrower profile
        response = client.post("/borrower/profile", json={
            "employment_type": "SALARIED",
            "monthly_income": 50000,
            "employer_name": "Tech Corp",
            "current_job_tenure_months": 24,
            "total_work_experience_years": 5
        }, headers=test_borrower["headers"])
        
        print(f"\nBorrower profile response: {response.status_code}")
        if response.status_code != 201:
            print(f"Error: {response.text}")
        
        assert response.status_code == 201


class TestBankAccounts:
    """Test bank account creation"""
    
    def test_borrower_bank_account(self, client, test_borrower):
        """Test adding bank account for borrower"""
        # Create user profile first
        client.post("/user/profile", json={
            "first_name": "Test",
            "last_name": "Borrower",
            "dob": "1990-01-01",
            "gender": "MALE",
            "email": test_borrower["email"],
            "mobile": {"country_code": "+91", "national_number": test_borrower["phone"]}
        }, headers=test_borrower["headers"])
        
        # Create bank account
        response = client.post("/bank-accounts", json={
            "bank_name": "SBI",
            "account_holder_name": "Test Borrower",
            "account_type": "SAVINGS",
            "account_number": "123456789012",
            "ifsc_code": "SBIN0001234",
            "is_primary": True
        }, headers=test_borrower["headers"])
        
        print(f"\nBank account response: {response.status_code}")
        if response.status_code != 201:
            print(f"Error: {response.text}")
        
        assert response.status_code == 201

class TestLoanProduct:
    """Test loan product creation (admin only)"""
    
    def test_create_loan_product(self, client, admin_headers):
        """Test creating a loan product as admin with correct enum values"""
        
        # Use correct enum values from your model
        product_data = {
            "name": f"Test Product {uuid.uuid4().hex[:4]}",
            "min_amount": 10000,
            "max_amount": 500000,
            "min_tenure_months": 6,
            "max_tenure_months": 36,
            "interest_type": "FLAT",  # Changed from SIMPLE to FLAT
            "min_interest_rate": 10.5,
            "max_interest_rate": 18.0,
            "repayment_frequency": "MONTHLY",
            "repayment_day_source": "DISBURSEMENT_DATE",
            "grace_period_days": 3,
            "late_fee_percentage": 2.0,
            "status": "ACTIVE"
        }
        
        print(f"\nSending product data: {product_data}")
        
        response = client.post("/loan-products", json=product_data, headers=admin_headers)
        
        print(f"\nResponse status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 422:
            error_data = response.json()
            print(f"\nValidation errors: {error_data}")
            for error in error_data.get("detail", []):
                print(f"Field: {error.get('loc', [])} - Error: {error.get('msg', '')}")
        
        assert response.status_code == 201
        assert "id" in response.json()
        print(f"\n✅ Loan product created with ID: {response.json()['id']}")


class TestLoanOffer:
    """Test loan offer creation"""
    
    def test_create_loan_offer(self, client, admin_headers, db):
        """Test creating a loan offer"""
        
        # First create a loan product
        product_response = client.post("/loan-products", json={
            "name": f"Product {uuid.uuid4().hex[:4]}",
            "min_amount": 10000,
            "max_amount": 500000,
            "min_tenure_months": 6,
            "max_tenure_months": 36,
            "interest_type": "FLAT",
            "min_interest_rate": 10.5,
            "max_interest_rate": 18.0,
            "repayment_frequency": "MONTHLY",
            "repayment_day_source": "DISBURSEMENT_DATE",
            "grace_period_days": 3,
            "late_fee_percentage": 2.0,
            "status": "ACTIVE"
        }, headers=admin_headers)
        
        assert product_response.status_code == 201
        product_id = product_response.json()["id"]
        print(f"✅ Loan product created: {product_id}")
        
        # Create a lender user
        lender_email = f"lender_{uuid.uuid4().hex[:8]}@example.com"
        lender_phone = "9876543211"
        
        # Register lender
        reg_response = client.post("/register", json={
            "email": lender_email,
            "phone": {"country_code": "+91", "national_number": lender_phone},
            "role": "LENDER"
        })
        assert reg_response.status_code == 201
        lender_id = reg_response.json()["id"]
        print(f"✅ Lender registered: {lender_id}")
        
        # Setup OTP and password for lender
        from app.models.otp import OTPVerification
        otp_service = OTPService(db)
        phone_full = f"+91{lender_phone}"
        
        otp_record = db.query(OTPVerification).filter(
            OTPVerification.phone == phone_full
        ).order_by(OTPVerification.created_at.desc()).first()
        
        if otp_record:
            otp_record.is_used = True
            db.commit()
        
        new_otp = otp_service.create_otp(
            email=lender_email, phone=phone_full, purpose="REGISTRATION", user_id=str(lender_id)
        )
        
        verify = client.post("/otp/verify", json={"user_id": lender_id, "otp_code": new_otp.otp_code})
        assert verify.status_code == 200
        temp_token = verify.json()["temp_token"]
        
        pwd_response = client.post("/auth/set-password", json={
            "token": temp_token, "password": "Test@123", "confirm_password": "Test@123"
        })
        assert pwd_response.status_code == 200
        access_token = pwd_response.json()["access_token"]
        lender_headers = {"Authorization": f"Bearer {access_token}"}
        print(f"✅ Lender authenticated")
        
        # Create user profile for lender
        profile_response = client.post("/user/profile", json={
            "first_name": "Test",
            "last_name": "Lender",
            "dob": "1985-01-01",
            "gender": "MALE",
            "email": lender_email,
            "mobile": {"country_code": "+91", "national_number": lender_phone}
        }, headers=lender_headers)
        
        if profile_response.status_code == 400:
            print("User profile already exists")
        else:
            assert profile_response.status_code == 201
        print(f"✅ User profile created")
        
        # Create lender profile
        lender_profile_response = client.post("/lender/profile", json={
            "profile_name": "Test Lender",
            "business_type": "INDIVIDUAL",
            "risk_appetite": "MEDIUM"
        }, headers=lender_headers)
        
        if lender_profile_response.status_code == 400:
            print("Lender profile already exists")
        else:
            assert lender_profile_response.status_code == 201
        
        # Get the lender profile from database and verify it
        lender_profile = db.query(LenderProfile).filter(
            LenderProfile.user_id == lender_id
        ).first()
        
        if lender_profile:
            # Mark as verified (normally admin would do this)
            lender_profile.is_verified = True
            lender_profile.status = LenderStatus.ACTIVE
            db.commit()
            print(f"✅ Lender profile verified")
        
        # Create loan offer
        offer_data = {
            "loan_product_id": str(product_id),
            "offer_name": f"Offer {uuid.uuid4().hex[:4]}",
            "description": "Test offer for personal loans",
            "min_amount": 50000,
            "max_amount": 200000,
            "min_tenure_months": 12,
            "max_tenure_months": 24,
            "interest_rate": 12.5,
            "preferred_credit_score": 650,
            "preferred_employment_types": "SALARIED"
        }
        
        print(f"\nSending offer data: {offer_data}")
        
        response = client.post("/loan-offers", json=offer_data, headers=lender_headers)
        
        print(f"\nLoan offer response status: {response.status_code}")
        
        if response.status_code == 403:
            print(f"Forbidden - Lender may not be verified")
            print(f"Response: {response.text}")
        elif response.status_code == 422:
            error_data = response.json()
            print(f"Validation errors: {error_data}")
            for error in error_data.get("detail", []):
                print(f"  Field: {error.get('loc', [])} - Error: {error.get('msg', '')}")
        
        if response.status_code != 201:
            print(f"Error response body: {response.text}")
        
        assert response.status_code == 201
        assert "id" in response.json()
        print(f"\n✅ Loan offer created with ID: {response.json()['id']}")

class TestLoanApplication:
    """Test loan application creation"""
    
    def test_create_loan_application(self, client, admin_headers, db):
        """Test creating a loan application"""
        
        # First create a loan product
        product_response = client.post("/loan-products", json={
            "name": f"Product {uuid.uuid4().hex[:4]}",
            "min_amount": 10000,
            "max_amount": 500000,
            "min_tenure_months": 6,
            "max_tenure_months": 36,
            "interest_type": "FLAT",
            "min_interest_rate": 10.5,
            "max_interest_rate": 18.0,
            "repayment_frequency": "MONTHLY",
            "repayment_day_source": "DISBURSEMENT_DATE",
            "grace_period_days": 3,
            "late_fee_percentage": 2.0,
            "status": "ACTIVE"
        }, headers=admin_headers)
        assert product_response.status_code == 201
        product_id = product_response.json()["id"]
        
        # Create verified lender
        lender_id = create_verified_lender(client, db)
        lender_headers = lender_id["headers"]
        
        # Create loan offer
        offer_response = client.post("/loan-offers", json={
            "loan_product_id": str(product_id),
            "offer_name": f"Offer {uuid.uuid4().hex[:4]}",
            "description": "Test offer",
            "min_amount": 50000,
            "max_amount": 200000,
            "min_tenure_months": 12,
            "max_tenure_months": 24,
            "interest_rate": 12.5,
            "preferred_credit_score": 650,
            "preferred_employment_types": "SALARIED"
        }, headers=lender_headers)
        assert offer_response.status_code == 201
        offer_id = offer_response.json()["id"]
        
        # Create borrower
        borrower = create_borrower(client, db)
        
        # Create loan application
        response = client.post("/loan-applications", json={
            "loan_offer_id": offer_id,
            "requested_amount": 100000,
            "requested_tenure": 12,
            "purpose": "Home renovation",
            "notes": "Test application"
        }, headers=borrower["headers"])
        
        print(f"\nApplication response: {response.status_code}")
        if response.status_code != 201:
            print(f"Error: {response.text}")
        
        assert response.status_code == 201
        print(f"✅ Loan application created")


def create_verified_lender(client, db):
    """Helper to create a verified lender (simplified - no extra params)"""
    lender_email = f"lender_{uuid.uuid4().hex[:8]}@example.com"
    lender_phone = "9876543211"
    
    # Register
    reg_response = client.post("/register", json={
        "email": lender_email,
        "phone": {"country_code": "+91", "national_number": lender_phone},
        "role": "LENDER"
    })
    assert reg_response.status_code == 201
    lender_id = reg_response.json()["id"]
    
    # Setup password
    from app.models.otp import OTPVerification
    otp_service = OTPService(db)
    phone_full = f"+91{lender_phone}"
    
    otp_record = db.query(OTPVerification).filter(
        OTPVerification.phone == phone_full
    ).order_by(OTPVerification.created_at.desc()).first()
    
    if otp_record:
        otp_record.is_used = True
        db.commit()
    
    new_otp = otp_service.create_otp(
        email=lender_email, phone=phone_full, purpose="REGISTRATION", user_id=str(lender_id)
    )
    
    verify = client.post("/otp/verify", json={"user_id": lender_id, "otp_code": new_otp.otp_code})
    assert verify.status_code == 200
    temp_token = verify.json()["temp_token"]
    
    pwd_response = client.post("/auth/set-password", json={
        "token": temp_token, "password": "Test@123", "confirm_password": "Test@123"
    })
    assert pwd_response.status_code == 200
    access_token = pwd_response.json()["access_token"]
    lender_headers = {"Authorization": f"Bearer {access_token}"}
    
    # Create profiles
    client.post("/user/profile", json={
        "first_name": "Test",
        "last_name": "Lender",
        "dob": "1985-01-01",
        "gender": "MALE",
        "email": lender_email,
        "mobile": {"country_code": "+91", "national_number": lender_phone}
    }, headers=lender_headers)
    
    client.post("/lender/profile", json={
        "profile_name": "Test Lender",
        "business_type": "INDIVIDUAL",
        "risk_appetite": "MEDIUM"
    }, headers=lender_headers)
    
    # Add bank account
    client.post("/bank-accounts", json={
        "bank_name": "HDFC",
        "account_holder_name": "Test Lender",
        "account_type": "SAVINGS",
        "account_number": "098765432109",
        "ifsc_code": "HDFC0005678",
        "is_primary": True
    }, headers=lender_headers)
    
    # Verify lender profile
    lender_profile = db.query(LenderProfile).filter(
        LenderProfile.user_id == lender_id
    ).first()
    if lender_profile:
        lender_profile.is_verified = True
        lender_profile.status = LenderStatus.ACTIVE
        db.commit()
    
    return {"id": lender_id, "headers": lender_headers}


def create_borrower(client, db):
    """Helper to create a borrower"""
    borrower_email = f"borrower_{uuid.uuid4().hex[:8]}@example.com"
    borrower_phone = "9876543210"
    
    # Register
    reg_response = client.post("/register", json={
        "email": borrower_email,
        "phone": {"country_code": "+91", "national_number": borrower_phone},
        "role": "BORROWER"
    })
    assert reg_response.status_code == 201
    borrower_id = reg_response.json()["id"]
    
    # Setup password
    from app.models.otp import OTPVerification
    otp_service = OTPService(db)
    phone_full = f"+91{borrower_phone}"
    
    otp_record = db.query(OTPVerification).filter(
        OTPVerification.phone == phone_full
    ).order_by(OTPVerification.created_at.desc()).first()
    
    if otp_record:
        otp_record.is_used = True
        db.commit()
    
    new_otp = otp_service.create_otp(
        email=borrower_email, phone=phone_full, purpose="REGISTRATION", user_id=str(borrower_id)
    )
    
    verify = client.post("/otp/verify", json={"user_id": borrower_id, "otp_code": new_otp.otp_code})
    assert verify.status_code == 200
    temp_token = verify.json()["temp_token"]
    
    pwd_response = client.post("/auth/set-password", json={
        "token": temp_token, "password": "Test@123", "confirm_password": "Test@123"
    })
    assert pwd_response.status_code == 200
    access_token = pwd_response.json()["access_token"]
    borrower_headers = {"Authorization": f"Bearer {access_token}"}
    
    # Create profiles
    client.post("/user/profile", json={
        "first_name": "Test",
        "last_name": "Borrower",
        "dob": "1990-01-01",
        "gender": "MALE",
        "email": borrower_email,
        "mobile": {"country_code": "+91", "national_number": borrower_phone}
    }, headers=borrower_headers)
    
    client.post("/borrower/profile", json={
        "employment_type": "SALARIED",
        "monthly_income": 50000,
        "employer_name": "Tech Corp",
        "current_job_tenure_months": 24,
        "total_work_experience_years": 5
    }, headers=borrower_headers)
    
    # Add bank account
    client.post("/bank-accounts", json={
        "bank_name": "SBI",
        "account_holder_name": "Test Borrower",
        "account_type": "SAVINGS",
        "account_number": "123456789012",
        "ifsc_code": "SBIN0001234",
        "is_primary": True
    }, headers=borrower_headers)
    
    return {"id": borrower_id, "headers": borrower_headers}

class TestLoanAcceptance:
    """Test loan acceptance and disbursement"""
    
    def test_accept_loan_application(self, client, admin_headers, db):
        """Test lender accepting a loan application"""
        
        # Create loan product
        product_response = client.post("/loan-products", json={
            "name": f"Product {uuid.uuid4().hex[:4]}",
            "min_amount": 10000,
            "max_amount": 500000,
            "min_tenure_months": 6,
            "max_tenure_months": 36,
            "interest_type": "FLAT",
            "min_interest_rate": 10.5,
            "max_interest_rate": 18.0,
            "repayment_frequency": "MONTHLY",
            "repayment_day_source": "DISBURSEMENT_DATE",
            "grace_period_days": 3,
            "late_fee_percentage": 2.0,
            "status": "ACTIVE"
        }, headers=admin_headers)
        assert product_response.status_code == 201
        product_id = product_response.json()["id"]
        print(f"✅ Loan product created: {product_id}")
        
        # Create verified lender
        lender = create_verified_lender(client, db)
        lender_headers = lender["headers"]
        
        # Create loan offer
        offer_response = client.post("/loan-offers", json={
            "loan_product_id": str(product_id),
            "offer_name": f"Offer {uuid.uuid4().hex[:4]}",
            "description": "Test offer",
            "min_amount": 50000,
            "max_amount": 200000,
            "min_tenure_months": 12,
            "max_tenure_months": 24,
            "interest_rate": 12.5,
            "preferred_credit_score": 650,
            "preferred_employment_types": "SALARIED"
        }, headers=lender_headers)
        assert offer_response.status_code == 201
        offer_id = offer_response.json()["id"]
        print(f"✅ Loan offer created: {offer_id}")
        
        # Create borrower with bank account
        borrower = create_borrower_with_bank_account(client, db)
        borrower_headers = borrower["headers"]
        
        # Create loan application
        app_response = client.post("/loan-applications", json={
            "loan_offer_id": offer_id,
            "requested_amount": 100000,
            "requested_tenure": 12,
            "purpose": "Home renovation",
            "notes": "Test application"
        }, headers=borrower_headers)
        assert app_response.status_code == 201
        application_id = app_response.json()["id"]
        print(f"✅ Loan application created: {application_id}")
        
        # Accept the application
        accept_response = client.post(f"/loan-applications/{application_id}/review", json={
            "status": "ACCEPTED",
            "lender_notes": "Approved based on good profile"
        }, headers=lender_headers)
        
        print(f"\nAcceptance response status: {accept_response.status_code}")
        if accept_response.status_code != 200:
            print(f"Error: {accept_response.text}")
        
        assert accept_response.status_code == 200
        print(f"✅ Loan application accepted")
        
        # Verify loan was created
        loans_response = client.get("/loans", headers=borrower_headers)
        assert loans_response.status_code == 200
        loans = loans_response.json()
        assert len(loans) >= 1
        
        loan_id = loans[0]["id"]
        print(f"✅ Loan created: {loan_id}")
        
        # Verify repayment schedule was generated
        schedule_response = client.get(f"/loans/{loan_id}/schedule", headers=borrower_headers)
        assert schedule_response.status_code == 200
        schedule_data = schedule_response.json()
        assert len(schedule_data["schedules"]) == 12
        print(f"✅ Repayment schedule generated with 12 installments")
        
        return loan_id
    
class TestRepayment:
    """Test loan repayment"""
    
    def test_make_repayment(self, client, admin_headers, db):
        # Create loan product
        product_response = client.post("/loan-products", json={
            "name": f"Product {uuid.uuid4().hex[:4]}",
            "min_amount": 10000,
            "max_amount": 500000,
            "min_tenure_months": 6,
            "max_tenure_months": 36,
            "interest_type": "FLAT",
            "min_interest_rate": 10.5,
            "max_interest_rate": 18.0,
            "repayment_frequency": "MONTHLY",
            "repayment_day_source": "DISBURSEMENT_DATE",
            "grace_period_days": 3,
            "late_fee_percentage": 2.0,
            "status": "ACTIVE"
        }, headers=admin_headers)
        assert product_response.status_code == 201
        product_id = product_response.json()["id"]
        
        # Create lender
        lender = create_verified_lender(client, db)
        lender_headers = lender["headers"]
        
        # Create loan offer
        offer_response = client.post("/loan-offers", json={
            "loan_product_id": str(product_id),
            "offer_name": f"Offer {uuid.uuid4().hex[:4]}",
            "description": "Test offer",
            "min_amount": 50000,
            "max_amount": 200000,
            "min_tenure_months": 12,
            "max_tenure_months": 24,
            "interest_rate": 12.5,
            "preferred_credit_score": 650,
            "preferred_employment_types": "SALARIED"
        }, headers=lender_headers)
        assert offer_response.status_code == 201
        offer_id = offer_response.json()["id"]
        
        # Create borrower
        borrower = create_borrower_with_bank_account(client, db)
        borrower_headers = borrower["headers"]
        
        # Create loan application
        app_response = client.post("/loan-applications", json={
            "loan_offer_id": offer_id,
            "requested_amount": 100000,
            "requested_tenure": 12,
            "purpose": "Home renovation",
            "notes": "Test application"
        }, headers=borrower_headers)
        assert app_response.status_code == 201
        application_id = app_response.json()["id"]
        
        # Accept the application
        accept_response = client.post(f"/loan-applications/{application_id}/review", json={
            "status": "ACCEPTED",
            "lender_notes": "Approved"
        }, headers=lender_headers)
        assert accept_response.status_code == 200
        
        # Get the loan
        loans_response = client.get("/loans", headers=borrower_headers)
        assert loans_response.status_code == 200
        loans = loans_response.json()
        assert len(loans) >= 1
        loan_id = loans[0]["id"]
        
        # Get the loan schedule
        schedule_response = client.get(f"/loans/{loan_id}/schedule", headers=borrower_headers)
        assert schedule_response.status_code == 200
        schedule_data = schedule_response.json()
        
        # Get EMI amount
        emi_amount = float(schedule_data["schedules"][0]["amount_due"])
        
        # Make repayment
        repayment_response = client.post("/transactions/repayments", json={
            "loan_id": loan_id,
            "amount": emi_amount
        }, headers=borrower_headers)
        
        assert repayment_response.status_code == 201
        print(f"\n✅ Repayment successful")

# tests/test_integration.py - Add this complete integration test

class TestCompleteLoanLifecycle:
    """Complete integration test for the entire loan lifecycle"""
    
    def test_complete_loan_lifecycle(self, client, admin_headers, db):
        """
        INTEGRATION TEST: Complete loan lifecycle
        """
        
        print("\n" + "="*70)
        print("INTEGRATION TEST: COMPLETE LOAN LIFECYCLE")
        print("="*70)
        
        # ========== PHASE 1-8: Same as before until loan creation ==========
        print("\n📌 PHASE 1: Creating loan product (admin)")
        product_response = client.post("/loan-products", json={
            "name": f"Integration Test Product",
            "min_amount": 10000,
            "max_amount": 500000,
            "min_tenure_months": 6,
            "max_tenure_months": 36,
            "interest_type": "FLAT",
            "min_interest_rate": 10.5,
            "max_interest_rate": 18.0,
            "repayment_frequency": "MONTHLY",
            "repayment_day_source": "DISBURSEMENT_DATE",
            "grace_period_days": 3,
            "late_fee_percentage": 2.0,
            "status": "ACTIVE"
        }, headers=admin_headers)
        assert product_response.status_code == 201
        product_id = product_response.json()["id"]
        print(f"   ✅ Loan product created: {product_id}")
        
        print("\n📌 PHASE 2: Creating lender")
        lender = create_verified_lender(client, db)
        lender_headers = lender["headers"]
        print(f"   ✅ Lender created: {lender['id']}")
        
        print("\n📌 PHASE 3: Creating loan offer")
        offer_response = client.post("/loan-offers", json={
            "loan_product_id": str(product_id),
            "offer_name": f"Integration Test Offer",
            "description": "Loan offer for integration testing",
            "min_amount": 50000,
            "max_amount": 200000,
            "min_tenure_months": 12,
            "max_tenure_months": 24,
            "interest_rate": 12.5,
            "preferred_credit_score": 650,
            "preferred_employment_types": "SALARIED"
        }, headers=lender_headers)
        assert offer_response.status_code == 201
        offer_id = offer_response.json()["id"]
        print(f"   ✅ Loan offer created: {offer_id}")
        
        print("\n📌 PHASE 4: Creating borrower")
        borrower = create_borrower_with_bank_account(client, db)
        borrower_headers = borrower["headers"]
        print(f"   ✅ Borrower created: {borrower['id']}")
        
        print("\n📌 PHASE 5: Creating loan application")
        app_response = client.post("/loan-applications", json={
            "loan_offer_id": offer_id,
            "requested_amount": 100000,
            "requested_tenure": 12,
            "purpose": "Home renovation",
            "notes": "Integration test application"
        }, headers=borrower_headers)
        assert app_response.status_code == 201
        application_id = app_response.json()["id"]
        print(f"   ✅ Loan application created: {application_id}")
        
        print("\n📌 PHASE 6: Accepting application")
        accept_response = client.post(f"/loan-applications/{application_id}/review", json={
            "status": "ACCEPTED",
            "lender_notes": "Approved"
        }, headers=lender_headers)
        assert accept_response.status_code == 200
        print(f"   ✅ Application accepted")
        
        print("\n📌 PHASE 7: Getting loan")
        loans_response = client.get("/loans", headers=borrower_headers)
        assert loans_response.status_code == 200
        loans = loans_response.json()
        assert len(loans) >= 1
        loan_id = loans[0]["id"]
        print(f"   ✅ Loan created: {loan_id}")
        
        print("\n📌 PHASE 8: Getting repayment schedule")
        schedule_response = client.get(f"/loans/{loan_id}/schedule", headers=borrower_headers)
        assert schedule_response.status_code == 200
        schedule_data = schedule_response.json()
        assert len(schedule_data["schedules"]) == 12
        print(f"   ✅ Repayment schedule generated")
        
        # ========== PHASE 9: Make all repayments ==========
        print("\n📌 PHASE 9: Making repayments")
        
        total_repayment = float(schedule_data["total_repayment"])
        print(f"   Total loan amount to repay: ₹{total_repayment}")
        
        total_paid = 0
        for i, schedule in enumerate(schedule_data["schedules"], 1):
            amount_due = float(schedule["amount_due"])
            print(f"\n   Payment {i}/{len(schedule_data['schedules'])}: ₹{amount_due}")
            
            repayment_response = client.post("/transactions/repayments", json={
                "loan_id": loan_id,
                "amount": amount_due
            }, headers=borrower_headers)
            
            print(f"      Status: {repayment_response.status_code}")
            
            if repayment_response.status_code != 201:
                print(f"      Error: {repayment_response.text}")
                assert False, f"Repayment {i} failed with status {repayment_response.status_code}"
            
            repayment_data = repayment_response.json()
            total_paid += amount_due
            
            print(f"      Success: {repayment_data['success']}")
            print(f"      Is fully paid: {repayment_data['is_loan_fully_paid']}")
            print(f"      Remaining balance: ₹{repayment_data['remaining_balance']}")
            
            if i < len(schedule_data['schedules']):
                assert repayment_data["is_loan_fully_paid"] == False, f"Payment {i} incorrectly marked as fully paid"
            else:
                # Last payment should mark loan as fully paid
                assert repayment_data["is_loan_fully_paid"] == True, f"Last payment did not mark loan as fully paid"
        
        # ========== PHASE 10: Verify final loan status ==========
        print("\n📌 PHASE 10: Verifying final loan status")
        
        final_loan = client.get(f"/loans/{loan_id}", headers=borrower_headers)
        final_loan_data = final_loan.json()
        
        print(f"   Final loan status: {final_loan_data['status']}")
        print(f"   Remaining balance: ₹{final_loan_data['remaining_balance']}")
        
        assert final_loan_data["status"] == "CLOSED", f"Expected CLOSED, got {final_loan_data['status']}"
        assert float(final_loan_data["remaining_balance"]) <= 0, f"Remaining balance should be 0, got {final_loan_data['remaining_balance']}"
        
        # ========== SUMMARY ==========
        print("\n" + "="*70)
        print("🎉 INTEGRATION TEST PASSED!")
        print("="*70)
        print("✅ Complete loan lifecycle tested successfully")
        print(f"✅ Total paid: ₹{total_paid}")
        print(f"✅ Final status: {final_loan_data['status']}")
        print("="*70)
# Run tests
if __name__ == "__main__":
    # Run specific test to isolate failure
    pytest.main([__file__, "-v", "-s", "--disable-warnings", "-k", "test_borrower_employment_profile"])