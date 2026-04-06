import pytest
import uuid
from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User, UserRole, UserStatus
from app.models.user_profile import UserProfile
from app.models.lender_profile import LenderProfile, RiskAppetite
from app.core.security import get_password_hash, create_access_token


# ============== FIXTURES ==============

@pytest.fixture
def test_lender(db: Session):
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
def test_borrower(db: Session):
    """Create a test borrower user"""
    user = User(
        id=uuid.uuid4(),
        email=f"borrower_{uuid.uuid4().hex[:8]}@example.com",
        country_code="+91",
        national_number="9876543211",
        password_hash=get_password_hash("TestPass123"),
        role=UserRole.BORROWER,
        status=UserStatus.ACTIVE
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_admin(db: Session):
    """Create a test admin user"""
    admin = User(
        id=uuid.uuid4(),
        email=f"admin_{uuid.uuid4().hex[:8]}@example.com",
        country_code="+91",
        national_number="9876543212",
        password_hash=get_password_hash("AdminPass123"),
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@pytest.fixture
def test_user_profile(db: Session, test_lender):
    """Create a user profile for the test lender"""
    profile = UserProfile(
        user_id=test_lender.id,
        first_name="Test",
        last_name="Lender",
        dob=date(1990, 1, 1),
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
def auth_headers(test_lender):
    """Get auth headers for test lender"""
    access_token = create_access_token(data={"sub": str(test_lender.id)})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def borrower_auth_headers(test_borrower):
    """Get auth headers for test borrower"""
    access_token = create_access_token(data={"sub": str(test_borrower.id)})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def admin_auth_headers(test_admin):
    """Get auth headers for admin user"""
    access_token = create_access_token(data={"sub": str(test_admin.id)})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def sample_lender_data():
    """Sample lender profile data"""
    return {
        "profile_name": "Test Lender",
        "business_type": "INDIVIDUAL",
        "risk_appetite": "MEDIUM"
    }


# ============== TEST CREATE LENDER PROFILE ==============

def test_create_lender_profile_success(client, test_user_profile, auth_headers, sample_lender_data):
    """Test successful lender profile creation"""
    response = client.post(
        "/lender/profile",
        headers=auth_headers,
        json=sample_lender_data
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["profile_name"] == "Test Lender"
    assert data["status"] == "ACTIVE"
    assert data["is_verified"] == False
    assert "created_at" in data


def test_create_lender_profile_without_user_profile(client, test_lender, auth_headers, sample_lender_data):
    """Test creating lender profile without user profile first (should fail)"""
    response = client.post(
        "/lender/profile",
        headers=auth_headers,
        json=sample_lender_data
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "user profile" in str(data).lower()


def test_create_duplicate_lender_profile(client, test_user_profile, auth_headers, sample_lender_data):
    """Test creating duplicate lender profile (should fail)"""
    # First profile
    response1 = client.post("/lender/profile", headers=auth_headers, json=sample_lender_data)
    assert response1.status_code == 201
    
    # Second profile
    response2 = client.post("/lender/profile", headers=auth_headers, json=sample_lender_data)
    
    assert response2.status_code == 400
    data = response2.json()
    assert "already" in str(data).lower()


def test_create_lender_profile_as_borrower(client, test_borrower, db):
    """Test borrower cannot create lender profile"""
    # Create user profile for borrower first
    borrower_profile = UserProfile(
        user_id=test_borrower.id,
        first_name="Test",
        last_name="Borrower",
        dob=date(1990, 1, 1),
        gender="MALE",
        email=test_borrower.email,
        country_code="+91",
        national_number="9876543211"
    )
    db.add(borrower_profile)
    db.commit()
    
    # Get auth token for borrower
    borrower_token = create_access_token(data={"sub": str(test_borrower.id)})
    borrower_headers = {"Authorization": f"Bearer {borrower_token}"}
    
    response = client.post(
        "/lender/profile",
        headers=borrower_headers,
        json={
            "profile_name": "Test Lender",
            "business_type": "INDIVIDUAL",
            "risk_appetite": "MEDIUM"
        }
    )
    
    assert response.status_code == 403


def test_create_lender_profile_invalid_risk_appetite(client, test_user_profile, auth_headers):
    """Test creating lender profile with invalid risk appetite"""
    response = client.post(
        "/lender/profile",
        headers=auth_headers,
        json={
            "profile_name": "Test Lender",
            "business_type": "INDIVIDUAL",
            "risk_appetite": "INVALID"
        }
    )
    
    assert response.status_code == 422


def test_create_lender_profile_missing_fields(client, test_user_profile, auth_headers):
    """Test creating lender profile with missing required fields"""
    response = client.post(
        "/lender/profile",
        headers=auth_headers,
        json={
            "profile_name": "Test Lender"
            # Missing business_type and risk_appetite
        }
    )
    
    assert response.status_code == 422


# ============== TEST GET LENDER PROFILES ==============

def test_get_own_lender_profile(client, test_user_profile, auth_headers, sample_lender_data):
    """Test lender getting their own profile"""
    # Create profile first
    client.post("/lender/profile", headers=auth_headers, json=sample_lender_data)
    
    response = client.get("/lender/profiles", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["profile_name"] == "Test Lender"
    assert data["business_type"] == "INDIVIDUAL"
    assert data["risk_appetite"] == "MEDIUM"


def test_get_lender_profile_not_found(client, auth_headers):
    """Test getting lender profile when none exists"""
    response = client.get("/lender/profiles", headers=auth_headers)
    
    assert response.status_code == 404


def test_admin_get_all_lender_profiles(client, test_user_profile, auth_headers, admin_auth_headers, sample_lender_data):
    """Test admin can see all lender profiles"""
    # Create lender profile
    client.post("/lender/profile", headers=auth_headers, json=sample_lender_data)
    
    # Admin gets all profiles
    response = client.get("/lender/profiles", headers=admin_auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["profile_name"] == "Test Lender"


def test_borrower_view_lender_profile(client, test_user_profile, auth_headers, test_borrower, test_admin, db):
    """Test borrower viewing lender profiles (should see list of all lenders)"""
    # Create lender profile
    lender_response = client.post("/lender/profile", headers=auth_headers, json={
        "profile_name": "Test Lender",
        "business_type": "INDIVIDUAL",
        "risk_appetite": "MEDIUM"
    })
    assert lender_response.status_code == 201
    
    # Create user profile for borrower
    borrower_profile = UserProfile(
        user_id=test_borrower.id,
        first_name="Test",
        last_name="Borrower",
        dob=date(1990, 1, 1),
        gender="MALE",
        email=test_borrower.email,
        country_code="+91",
        national_number="9876543211"
    )
    db.add(borrower_profile)
    db.commit()
    
    # Get the profile ID from the response
    profile_id = lender_response.json()["id"]
    
    # Admin needs to verify the lender profile
    admin_token = create_access_token(data={"sub": str(test_admin.id)})
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Verify the lender profile as admin
    verify_response = client.patch(
        f"/lender/profiles/{profile_id}/verify",
        headers=admin_headers
    )
    assert verify_response.status_code == 200
    
    # Now borrower views lender profiles
    borrower_token = create_access_token(data={"sub": str(test_borrower.id)})
    borrower_headers = {"Authorization": f"Bearer {borrower_token}"}
    
    response = client.get("/lender/profiles", headers=borrower_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Check the first lender in the list
    first_lender = data[0]
    assert first_lender["profile_name"] == "Test Lender"
    assert "risk_appetite" in first_lender
    assert first_lender["is_verified"] == True


# ============== TEST UPDATE LENDER PROFILE ==============

def test_update_lender_profile_success(client, test_user_profile, auth_headers, sample_lender_data):
    """Test successfully updating lender profile"""
    # Create profile
    client.post("/lender/profile", headers=auth_headers, json=sample_lender_data)
    
    # Update profile
    response = client.put(
        "/lender/profile",
        headers=auth_headers,
        json={
            "profile_name": "Updated Lender",
            "risk_appetite": "HIGH"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["profile_name"] == "Updated Lender"
    assert data["risk_appetite"] == "HIGH"
    assert data["business_type"] == "INDIVIDUAL"  # Unchanged field


def test_update_lender_profile_not_found(client, auth_headers):
    """Test updating non-existent lender profile"""
    response = client.put(
        "/lender/profile",
        headers=auth_headers,
        json={
            "profile_name": "Updated Lender"
        }
    )
    
    assert response.status_code == 404


def test_update_lender_profile_as_borrower(client, test_user_profile, borrower_auth_headers, sample_lender_data):
    """Test borrower cannot update lender profile"""
    response = client.put(
        "/lender/profile",
        headers=borrower_auth_headers,
        json={
            "profile_name": "Hacked"
        }
    )
    
    assert response.status_code == 403


def test_update_lender_profile_partial(client, test_user_profile, auth_headers, sample_lender_data):
    """Test partial update (only send one field)"""
    # Create profile
    client.post("/lender/profile", headers=auth_headers, json=sample_lender_data)
    
    # Update only profile_name
    response = client.put(
        "/lender/profile",
        headers=auth_headers,
        json={
            "profile_name": "Partially Updated"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["profile_name"] == "Partially Updated"
    assert data["business_type"] == "INDIVIDUAL"  # Unchanged
    assert data["risk_appetite"] == "MEDIUM"  # Unchanged


# ============== TEST VERIFY LENDER PROFILE (ADMIN) ==============

def test_verify_lender_profile_success(client, test_user_profile, auth_headers, admin_auth_headers, sample_lender_data):
    """Test admin verifying lender profile"""
    # Create lender profile
    create_response = client.post("/lender/profile", headers=auth_headers, json=sample_lender_data)
    profile_id = create_response.json()["id"]
    
    # Verify profile
    response = client.patch(
        f"/lender/profiles/{profile_id}/verify",
        headers=admin_auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["is_verified"] == True


def test_verify_lender_profile_not_found(client, admin_auth_headers):
    """Test verifying non-existent lender profile"""
    fake_id = uuid.uuid4()
    response = client.patch(
        f"/lender/profiles/{fake_id}/verify",
        headers=admin_auth_headers
    )
    
    assert response.status_code == 404


def test_verify_lender_profile_as_lender(client, test_user_profile, auth_headers, sample_lender_data):
    """Test lender cannot verify their own profile (admin only)"""
    # Create profile
    create_response = client.post("/lender/profile", headers=auth_headers, json=sample_lender_data)
    profile_id = create_response.json()["id"]
    
    # Try to verify as lender
    response = client.patch(
        f"/lender/profiles/{profile_id}/verify",
        headers=auth_headers
    )
    
    assert response.status_code == 403


def test_verify_already_verified_profile(client, test_user_profile, auth_headers, admin_auth_headers, sample_lender_data):
    """Test verifying already verified profile (should be idempotent)"""
    # Create and verify profile
    create_response = client.post("/lender/profile", headers=auth_headers, json=sample_lender_data)
    profile_id = create_response.json()["id"]
    
    # First verification
    response1 = client.patch(f"/lender/profiles/{profile_id}/verify", headers=admin_auth_headers)
    assert response1.status_code == 200
    
    # Second verification (should still work)
    response2 = client.patch(f"/lender/profiles/{profile_id}/verify", headers=admin_auth_headers)
    assert response2.status_code == 200
    assert response2.json()["is_verified"] == True


# ============== TEST EDGE CASES ==============

def test_create_lender_profile_with_max_length_fields(client, test_user_profile, auth_headers):
    """Test creating profile with maximum field lengths"""
    response = client.post(
        "/lender/profile",
        headers=auth_headers,
        json={
            "profile_name": "A" * 100,  # Max 100 chars
            "business_type": "B" * 50,   # Max 50 chars
            "risk_appetite": "LOW"
        }
    )
    
    assert response.status_code == 201


def test_unauthorized_access_no_token(client):
    """Test accessing lender profiles without authentication"""
    response = client.get("/lender/profiles")
    assert response.status_code == 401


def test_lender_profile_risk_appetite_case_insensitive(client, test_user_profile, auth_headers):
    """Test that risk appetite is case-insensitive"""
    response = client.post(
        "/lender/profile",
        headers=auth_headers,
        json={
            "profile_name": "Case Test",
            "business_type": "INDIVIDUAL",
            "risk_appetite": "low"  # Lowercase
        }
    )
    
    assert response.status_code == 201
    
    # Get the profile to verify risk_appetite
    profile_response = client.get("/lender/profiles", headers=auth_headers)
    assert profile_response.status_code == 200
    profile_data = profile_response.json()
    # Should be converted to uppercase "LOW"
    assert profile_data["risk_appetite"] == "LOW"


# ============== TEST DELETE LENDER PROFILE ==============

def test_delete_lender_profile_success(client, test_user_profile, auth_headers, sample_lender_data):
    """Test successful deletion of lender profile"""
    # Create profile
    create_response = client.post("/lender/profile", headers=auth_headers, json=sample_lender_data)
    assert create_response.status_code == 201
    
    # Delete profile
    response = client.delete("/lender/profile", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert "deleted" in data["message"].lower()


def test_delete_nonexistent_lender_profile(client, auth_headers):
    """Test deleting non-existent lender profile"""
    response = client.delete("/lender/profile", headers=auth_headers)
    
    assert response.status_code == 404
    data = response.json()
    assert "not found" in str(data).lower()


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])