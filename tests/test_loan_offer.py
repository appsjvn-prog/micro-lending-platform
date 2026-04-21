import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from app.models.user import User, UserRole, UserStatus
from app.models.user_profile import UserProfile
from app.models.lender_profile import LenderProfile, RiskAppetite, LenderStatus
from app.models.loan_offer import LoanOffer, LoanOfferStatus
from app.core.security import get_password_hash, create_access_token
from app.core.timezone import utc_now


#  FIXTURES 

@pytest.fixture
def test_lender(db):
    """Create a test lender user"""
    user = User(
        id=uuid.uuid4(),
        email=f"lender_{uuid.uuid4().hex[:8]}@example.com",
        country_code="+91",
        national_number="9876543210",
        password_hash=get_password_hash("TestPass123"),
        role=UserRole.LENDER,
        status=UserStatus.ACTIVE
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_admin(db):
    """Create a test admin user"""
    admin = User(
        id=uuid.uuid4(),
        email=f"admin_{uuid.uuid4().hex[:8]}@example.com",
        country_code="+91",
        national_number="9876543211",
        password_hash=get_password_hash("AdminPass123"),
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@pytest.fixture
def test_borrower(db):
    """Create a test borrower user"""
    borrower = User(
        id=uuid.uuid4(),
        email=f"borrower_{uuid.uuid4().hex[:8]}@example.com",
        country_code="+91",
        national_number="9876543212",
        password_hash=get_password_hash("TestPass123"),
        role=UserRole.BORROWER,
        status=UserStatus.ACTIVE
    )
    db.add(borrower)
    db.commit()
    db.refresh(borrower)
    return borrower


@pytest.fixture
def test_user_profile(db, test_lender):
    """Create a user profile for the test lender"""
    profile = UserProfile(
        user_id=test_lender.id,
        first_name="Test",
        last_name="Lender",
        dob=datetime.now().date() - relativedelta(years=30),
        gender="MALE",
        email=test_lender.email,
        country_code="+91",
        national_number="9876543210"
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@pytest.fixture
def test_lender_profile(db, test_lender):
    """Create a lender profile"""
    profile = LenderProfile(
        user_id=test_lender.id,
        profile_name="Test Lender",
        business_type="INDIVIDUAL",
        risk_appetite=RiskAppetite.MEDIUM,
        status=LenderStatus.ACTIVE,
        is_verified=True
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@pytest.fixture
def auth_headers(test_lender):
    """Get auth headers for test lender"""
    access_token = create_access_token(data={"sub": str(test_lender.id)})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def admin_auth_headers(test_admin):
    """Get auth headers for admin user"""
    access_token = create_access_token(data={"sub": str(test_admin.id)})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def borrower_auth_headers(test_borrower):
    """Get auth headers for borrower user"""
    access_token = create_access_token(data={"sub": str(test_borrower.id)})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def sample_loan_offer_data():
    """Sample loan offer data"""
    return {
        "offer_name": "Personal Loan Offer",
        "description": "Competitive interest rates for personal loans",
        "min_amount": 10000.00,
        "max_amount": 500000.00,
        "min_tenure_months": 6,
        "max_tenure_months": 36,
        "interest_rate": 12.5,
        "preferred_credit_score": 700,
        "preferred_employment_types": "SALARIED,SELF_EMPLOYED"
    }


@pytest.fixture
def test_loan_offer(db, test_lender, sample_loan_offer_data):
    """Create a test loan offer"""
    offer = LoanOffer(
        lender_id=test_lender.id,
        offer_name=sample_loan_offer_data["offer_name"],
        description=sample_loan_offer_data["description"],
        min_amount=Decimal(str(sample_loan_offer_data["min_amount"])),
        max_amount=Decimal(str(sample_loan_offer_data["max_amount"])),
        min_tenure_months=sample_loan_offer_data["min_tenure_months"],
        max_tenure_months=sample_loan_offer_data["max_tenure_months"],
        interest_rate=Decimal(str(sample_loan_offer_data["interest_rate"])),
        preferred_credit_score=sample_loan_offer_data["preferred_credit_score"],
        preferred_employment_types=sample_loan_offer_data["preferred_employment_types"],
        expires_at=utc_now() + timedelta(days=30),
        status=LoanOfferStatus.ACTIVE,
        created_at=utc_now(),
        updated_at=utc_now()
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer

@pytest.fixture
def test_user(db):
    """Create a test user (regular user)"""
    from app.models.user import User, UserRole, UserStatus
    
    user = User(
        id=uuid.uuid4(),
        email=f"user_{uuid.uuid4().hex[:8]}@example.com",
        country_code="+91",
        national_number="9876543213",
        password_hash=get_password_hash("TestPass123"),
        role=UserRole.BORROWER,  # Regular user as borrower
        status=UserStatus.ACTIVE
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


#  TEST CREATE LOAN OFFER 

def test_create_loan_offer_success(client, test_user_profile, test_lender_profile, auth_headers, sample_loan_offer_data):
    """Test successful loan offer creation"""
    response = client.post(
        "/loan-offers",
        headers=auth_headers,
        json=sample_loan_offer_data
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["offer_name"] == "Personal Loan Offer"
    assert data["status"] == "ACTIVE"
    assert "created successfully" in data["message"]


def test_create_loan_offer_duplicate_name(client, test_user_profile, test_lender_profile, auth_headers, sample_loan_offer_data, test_loan_offer):
    """Test creating duplicate loan offer name should fail"""
    response = client.post(
        "/loan-offers",
        headers=auth_headers,
        json=sample_loan_offer_data
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "already exists" in str(data).lower()


def test_create_loan_offer_invalid_amount_range(client, test_user_profile, test_lender_profile, auth_headers):
    """Test creating loan offer with invalid amount range"""
    response = client.post(
        "/loan-offers",
        headers=auth_headers,
        json={
            "offer_name": "Invalid Offer",
            "min_amount": 50000.00,
            "max_amount": 10000.00,
            "min_tenure_months": 6,
            "max_tenure_months": 36,
            "interest_rate": 12.5
        }
    )
    
    assert response.status_code == 422


def test_create_loan_offer_invalid_tenure_range(client, test_user_profile, test_lender_profile, auth_headers):
    """Test creating loan offer with invalid tenure range"""
    response = client.post(
        "/loan-offers",
        headers=auth_headers,
        json={
            "offer_name": "Invalid Tenure",
            "min_amount": 10000.00,
            "max_amount": 50000.00,
            "min_tenure_months": 36,
            "max_tenure_months": 6,
            "interest_rate": 12.5
        }
    )
    
    assert response.status_code == 422


def test_create_loan_offer_missing_required_fields(client, test_user_profile, test_lender_profile, auth_headers):
    """Test creating loan offer with missing required fields"""
    response = client.post(
        "/loan-offers",
        headers=auth_headers,
        json={
            "offer_name": "Incomplete Offer"
        }
    )
    
    assert response.status_code == 422


def test_create_loan_offer_without_lender_profile(client, test_borrower, db):
    """Test regular user (borrower) cannot create loan offer"""
    from app.models.user_profile import UserProfile
    from datetime import date
    from app.core.security import create_access_token
    
    # Create user profile for the borrower
    user_profile = UserProfile(
        user_id=test_borrower.id,
        first_name="Test",
        last_name="Borrower",
        dob=date(1990, 1, 1),
        gender="MALE",
        email=test_borrower.email,
        country_code="+91",
        national_number="9876543210"
    )
    db.add(user_profile)
    db.commit()
    
    # Create auth headers for borrower
    borrower_token = create_access_token(data={"sub": str(test_borrower.id)})
    borrower_headers = {"Authorization": f"Bearer {borrower_token}"}
    
    # Try to create loan offer (should fail because user is not a lender)
    response = client.post(
        "/loan-offers",
        headers=borrower_headers,
        json={
            "offer_name": "Test Offer",
            "min_amount": 10000.00,
            "max_amount": 50000.00,
            "min_tenure_months": 6,
            "max_tenure_months": 36,
            "interest_rate": 12.5
        }
    )
    
    # Should fail with 403 because user is not authorized to create loan offers
    assert response.status_code == 403
    data = response.json()
    assert "not authorized" in str(data).lower() or "create loan offers" in str(data).lower()

def test_create_loan_offer_as_borrower(client, test_user_profile, borrower_auth_headers):
    """Test borrower cannot create loan offer"""
    response = client.post(
        "/loan-offers",
        headers=borrower_auth_headers,
        json={
            "offer_name": "Test Offer",
            "min_amount": 10000.00,
            "max_amount": 50000.00,
            "min_tenure_months": 6,
            "max_tenure_months": 36,
            "interest_rate": 12.5
        }
    )
    
    assert response.status_code == 403


def test_create_loan_offer_unverified_lender(client, test_user_profile, db):
    """Test unverified lender cannot create loan offer"""
    # Create unverified lender
    unverified_lender = User(
        id=uuid.uuid4(),
        email="unverified@example.com",
        country_code="+91",
        national_number="9876543213",
        password_hash=get_password_hash("TestPass123"),
        role=UserRole.LENDER,
        status=UserStatus.ACTIVE
    )
    db.add(unverified_lender)
    
    # Create lender profile but not verified
    lender_profile = LenderProfile(
        user_id=unverified_lender.id,
        profile_name="Unverified Lender",
        business_type="INDIVIDUAL",
        risk_appetite=RiskAppetite.MEDIUM,
        status=LenderStatus.ACTIVE,
        is_verified=False
    )
    db.add(lender_profile)
    db.commit()
    
    unverified_token = create_access_token(data={"sub": str(unverified_lender.id)})
    unverified_headers = {"Authorization": f"Bearer {unverified_token}"}
    
    response = client.post(
        "/loan-offers",
        headers=unverified_headers,
        json={
            "offer_name": "Test Offer",
            "min_amount": 10000.00,
            "max_amount": 50000.00,
            "min_tenure_months": 6,
            "max_tenure_months": 36,
            "interest_rate": 12.5
        }
    )
    
    assert response.status_code == 403


#  TEST GET LOAN OFFERS 

def test_get_all_loan_offers_public(client, test_loan_offer):
    """Test getting all loan offers (public - no auth)"""
    response = client.get("/loan-offers")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["offer_name"] == "Personal Loan Offer"


def test_get_lender_own_offers(client, test_loan_offer, auth_headers):
    """Test lender getting their own offers"""
    response = client.get("/loan-offers", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["offer_name"] == "Personal Loan Offer"


def test_get_admin_all_offers(client, test_loan_offer, admin_auth_headers):
    """Test admin getting all offers"""
    response = client.get("/loan-offers", headers=admin_auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


def test_get_loan_offer_by_id(client, test_loan_offer):
    """Test getting loan offer by ID"""
    response = client.get(f"/loan-offers/{test_loan_offer.id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_loan_offer.id)
    assert data["offer_name"] == "Personal Loan Offer"


def test_get_loan_offer_not_found(client):
    """Test getting non-existent loan offer"""
    fake_id = uuid.uuid4()
    response = client.get(f"/loan-offers/{fake_id}")
    
    assert response.status_code == 404
    data = response.json()
    assert "not found" in str(data).lower()


def test_get_expired_loan_offer(client, test_loan_offer, db):
    """Test getting expired loan offer"""
    # Manually expire the offer
    test_loan_offer.expires_at = utc_now() - timedelta(days=1)
    db.commit()
    
    response = client.get(f"/loan-offers/{test_loan_offer.id}")
    
    assert response.status_code == 400
    data = response.json()
    assert "expired" in str(data).lower()


#  TEST UPDATE LOAN OFFER 

def test_update_loan_offer_success(client, test_loan_offer, auth_headers):
    """Test successfully updating loan offer"""
    response = client.put(
        f"/loan-offers/{test_loan_offer.id}",
        headers=auth_headers,
        json={
            "offer_name": "Updated Loan Offer",
            "interest_rate": 13.5
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["offer_name"] == "Updated Loan Offer"
    assert float(data["interest_rate"]) == 13.5


def test_update_loan_offer_duplicate_name(client, test_lender_profile, auth_headers, test_loan_offer):
    """Test updating loan offer with duplicate name should fail"""
    # Create a second offer with a unique name
    response1 = client.post(
        "/loan-offers",
        headers=auth_headers,
        json={
            "offer_name": "Second Unique Offer",
            "min_amount": 10000.00,
            "max_amount": 50000.00,
            "min_tenure_months": 6,
            "max_tenure_months": 36,
            "interest_rate": 12.5
        }
    )
    
    # Debug print
    print(f"\nCreate second offer response: {response1.status_code}")
    print(f"Response body: {response1.json() if response1.content else 'No content'}")
    
    assert response1.status_code == 201, f"Expected 201, got {response1.status_code}"
    second_offer_id = response1.json()["id"]
    
    # Try to update the second offer to use the first offer's name
    response = client.put(
        f"/loan-offers/{second_offer_id}",
        headers=auth_headers,
        json={"offer_name": "Personal Loan Offer"}  # First offer's name
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "already exists" in str(data).lower()

def test_update_loan_offer_partial(client, test_loan_offer, auth_headers):
    """Test partial update of loan offer"""
    response = client.put(
        f"/loan-offers/{test_loan_offer.id}",
        headers=auth_headers,
        json={"interest_rate": 14.0}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert float(data["interest_rate"]) == 14.0
    assert data["offer_name"] == "Personal Loan Offer"  # Unchanged


def test_update_nonexistent_loan_offer(client, auth_headers):
    """Test updating non-existent loan offer"""
    fake_id = uuid.uuid4()
    response = client.put(
        f"/loan-offers/{fake_id}",
        headers=auth_headers,
        json={"offer_name": "New Name"}
    )
    
    assert response.status_code == 404


def test_update_loan_offer_as_borrower(client, test_loan_offer, borrower_auth_headers):
    """Test borrower cannot update loan offer"""
    response = client.put(
        f"/loan-offers/{test_loan_offer.id}",
        headers=borrower_auth_headers,
        json={"offer_name": "Hacked Name"}
    )
    
    assert response.status_code == 403


def test_update_loan_offer_as_admin(client, test_loan_offer, admin_auth_headers):
    """Test admin can update any loan offer"""
    response = client.put(
        f"/loan-offers/{test_loan_offer.id}",
        headers=admin_auth_headers,
        json={"offer_name": "Admin Updated Offer"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["offer_name"] == "Admin Updated Offer"


#  TEST DEACTIVATE LOAN OFFER 

def test_deactivate_loan_offer_success(client, test_loan_offer, auth_headers):
    """Test deactivating a loan offer"""
    response = client.delete(f"/loan-offers/{test_loan_offer.id}", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert "deactivated" in data["message"].lower()
    
    # Verify offer is now inactive
    get_response = client.get(f"/loan-offers/{test_loan_offer.id}")
    assert get_response.json()["status"] == "INACTIVE"


def test_deactivate_already_inactive_offer(client, test_loan_offer, auth_headers):
    """Test deactivating already inactive offer should fail"""
    # First deactivate
    client.delete(f"/loan-offers/{test_loan_offer.id}", headers=auth_headers)
    
    # Try to deactivate again
    response = client.delete(f"/loan-offers/{test_loan_offer.id}", headers=auth_headers)
    
    assert response.status_code == 400
    data = response.json()
    assert "inactive" in str(data).lower()


def test_deactivate_nonexistent_offer(client, auth_headers):
    """Test deactivating non-existent loan offer"""
    fake_id = uuid.uuid4()
    response = client.delete(f"/loan-offers/{fake_id}", headers=auth_headers)
    
    assert response.status_code == 404


def test_deactivate_loan_offer_as_borrower(client, test_loan_offer, borrower_auth_headers):
    """Test borrower cannot deactivate loan offer"""
    response = client.delete(f"/loan-offers/{test_loan_offer.id}", headers=borrower_auth_headers)
    
    assert response.status_code == 403


def test_deactivate_loan_offer_as_admin(client, test_loan_offer, admin_auth_headers):
    """Test admin can deactivate any loan offer"""
    response = client.delete(f"/loan-offers/{test_loan_offer.id}", headers=admin_auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True


#  TEST UNAUTHORIZED ACCESS 

def test_unauthorized_access_no_token(client):
    """Test accessing loan offers without authentication (GET is public)"""
    response = client.get("/loan-offers")
    assert response.status_code == 200  # Public endpoint
    
    response = client.post("/loan-offers", json={})
    assert response.status_code == 401
    
    response = client.put("/loan-offers/some-id", json={})
    assert response.status_code == 401
    
    response = client.delete("/loan-offers/some-id")
    assert response.status_code == 401


#  TEST EDGE CASES 

def test_create_loan_offer_with_expiry(client, test_user_profile, test_lender_profile, auth_headers):
    """Test creating loan offer with custom expiry date"""
    expires_at = (utc_now() + timedelta(days=15)).isoformat()
    
    response = client.post(
        "/loan-offers",
        headers=auth_headers,
        json={
            "offer_name": "Limited Time Offer",
            "min_amount": 10000.00,
            "max_amount": 50000.00,
            "min_tenure_months": 6,
            "max_tenure_months": 36,
            "interest_rate": 12.5,
            "expires_at": expires_at
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["offer_name"] == "Limited Time Offer"


def test_create_loan_offer_with_max_length_name(client, test_user_profile, test_lender_profile, auth_headers):
    """Test creating loan offer with maximum length name"""
    response = client.post(
        "/loan-offers",
        headers=auth_headers,
        json={
            "offer_name": "A" * 100,
            "min_amount": 10000.00,
            "max_amount": 50000.00,
            "min_tenure_months": 6,
            "max_tenure_months": 36,
            "interest_rate": 12.5
        }
    )
    
    assert response.status_code == 201


def test_public_cannot_see_inactive_offers(client, test_loan_offer, auth_headers):
    """Test that public users cannot see inactive offers"""
    # First deactivate the offer
    client.delete(f"/loan-offers/{test_loan_offer.id}", headers=auth_headers)
    
    # Public user tries to see it
    response = client.get("/loan-offers")
    
    # Should not include the deactivated offer
    offers = response.json()
    for offer in offers:
        assert offer["id"] != str(test_loan_offer.id)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])