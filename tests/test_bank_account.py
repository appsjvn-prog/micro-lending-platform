import pytest
import uuid
from decimal import Decimal
from app.models.user import User, UserRole, UserStatus
from app.models.user_profile import UserProfile
from app.models.bank_account import BankAccount, AccountType
from app.core.security import get_password_hash, create_access_token
from datetime import date

#  FIXTURES 

@pytest.fixture
def test_user(db):
    """Create a test user"""
    user = User(
        id=uuid.uuid4(),
        email=f"user_{uuid.uuid4().hex[:8]}@example.com",
        country_code="+91",
        national_number="9876543210",
        password_hash=get_password_hash("TestPass123"),
        role=UserRole.BORROWER,
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
def test_user_profile(db, test_user):
    """Create a user profile for the test user"""
    profile = UserProfile(
        user_id=test_user.id,
        first_name="Test",
        last_name="User",
        dob=date(1990, 1, 1),
        gender="MALE",
        email=test_user.email,
        country_code="+91",
        national_number="9876543210"
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@pytest.fixture
def auth_headers(test_user):
    """Get auth headers for test user"""
    access_token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def admin_auth_headers(test_admin):
    """Get auth headers for admin user"""
    access_token = create_access_token(data={"sub": str(test_admin.id)})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def sample_bank_account_data():
    """Sample bank account data"""
    return {
        "bank_name": "HDFC Bank",
        "account_holder_name": "Test User",
        "account_type": "SAVINGS",
        "account_number": "123456789012",
        "ifsc_code": "HDFC0001234",
        "is_primary": True
    }


@pytest.fixture
def test_bank_account(db, test_user, sample_bank_account_data):
    """Create a test bank account"""
    account = BankAccount(
        user_id=test_user.id,
        bank_name=sample_bank_account_data["bank_name"],
        account_holder_name=sample_bank_account_data["account_holder_name"],
        account_type=AccountType.SAVINGS,
        account_number=sample_bank_account_data["account_number"],
        ifsc_code=sample_bank_account_data["ifsc_code"],
        is_primary=True
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


#  TEST CREATE BANK ACCOUNT 

def test_create_bank_account_success(client, test_user_profile, auth_headers, sample_bank_account_data):
    """Test successful bank account creation"""
    response = client.post(
        "/bank-accounts",
        headers=auth_headers,
        json=sample_bank_account_data
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["is_verified"] == False
    assert data["is_primary"] == True  # First account becomes primary


def test_create_duplicate_bank_account(client, test_user_profile, auth_headers, sample_bank_account_data):
    """Test creating duplicate bank account should fail"""
    # First account
    response1 = client.post("/bank-accounts", headers=auth_headers, json=sample_bank_account_data)
    assert response1.status_code == 201
    
    # Second account with same account number
    response2 = client.post("/bank-accounts", headers=auth_headers, json=sample_bank_account_data)
    
    assert response2.status_code == 400
    data = response2.json()
    assert "already registered" in str(data).lower()


def test_create_bank_account_limit_exceeded(client, test_user_profile, auth_headers):
    """Test creating more than maximum allowed bank accounts"""
    MAX_ACCOUNTS = 5
    
    for i in range(MAX_ACCOUNTS):
        response = client.post(
            "/bank-accounts",
            headers=auth_headers,
            json={
                "bank_name": f"Bank {i+1}",
                "account_holder_name": "Test User",
                "account_type": "SAVINGS",
                "account_number": f"1234567890{i}",
                "ifsc_code": "HDFC0001234",
                "is_primary": False
            }
        )
        assert response.status_code == 201
    
    # Try to create 6th account
    response = client.post(
        "/bank-accounts",
        headers=auth_headers,
        json={
            "bank_name": "Extra Bank",
            "account_holder_name": "Test User",
            "account_type": "SAVINGS",
            "account_number": "999999999999",
            "ifsc_code": "HDFC0001234",
            "is_primary": False
        }
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "maximum" in str(data).lower() or "limit" in str(data).lower()


def test_create_bank_account_invalid_ifsc(client, test_user_profile, auth_headers):
    """Test creating bank account with invalid IFSC code"""
    response = client.post(
        "/bank-accounts",
        headers=auth_headers,
        json={
            "bank_name": "Test Bank",
            "account_holder_name": "Test User",
            "account_type": "SAVINGS",
            "account_number": "123456789012",
            "ifsc_code": "INVALID",
            "is_primary": False
        }
    )
    
    assert response.status_code == 422  # Validation error


def test_create_bank_account_invalid_account_number(client, test_user_profile, auth_headers):
    """Test creating bank account with invalid account number"""
    response = client.post(
        "/bank-accounts",
        headers=auth_headers,
        json={
            "bank_name": "Test Bank",
            "account_holder_name": "Test User",
            "account_type": "SAVINGS",
            "account_number": "123",  # Too short
            "ifsc_code": "HDFC0001234",
            "is_primary": False
        }
    )
    
    assert response.status_code == 422


#  TEST GET BANK ACCOUNTS 

def test_get_my_bank_accounts(client, test_bank_account, auth_headers):
    """Test getting all bank accounts for user"""
    response = client.get("/bank-accounts", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["account_number"] == "123456789012"

#  TEST UPDATE BANK ACCOUNT 

def test_update_bank_account_success(client, test_bank_account, auth_headers):
    """Test successfully updating bank account"""
    response = client.put(
        f"/bank-accounts/{test_bank_account.id}",
        headers=auth_headers,
        json={
            "bank_name": "ICICI Bank",
            "account_holder_name": "Updated Name"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["bank_name"] == "ICICI Bank"
    assert data["account_holder_name"] == "Updated Name"


def test_update_bank_account_set_primary(client, test_bank_account, auth_headers):
    """Test setting bank account as primary"""
    # Create second account first
    response1 = client.post(
        "/bank-accounts",
        headers=auth_headers,
        json={
            "bank_name": "Second Bank",
            "account_holder_name": "Test User",
            "account_type": "SAVINGS",
            "account_number": "999999999999",
            "ifsc_code": "HDFC0001234",
            "is_primary": False
        }
    )
    assert response1.status_code == 201
    second_id = response1.json()["id"]
    
    # Set second account as primary
    response = client.put(
        f"/bank-accounts/{second_id}",
        headers=auth_headers,
        json={"is_primary": True}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["is_primary"] == True


def test_update_nonexistent_bank_account(client, auth_headers):
    """Test updating non-existent bank account"""
    fake_id = uuid.uuid4()
    response = client.put(
        f"/bank-accounts/{fake_id}",
        headers=auth_headers,
        json={"bank_name": "New Bank"}
    )
    
    assert response.status_code == 404


#  TEST DELETE BANK ACCOUNT 

def test_delete_bank_account_success(client, test_bank_account, auth_headers):
    """Test successfully deleting bank account"""
    # Create second account first (can't delete last account)
    client.post(
        "/bank-accounts",
        headers=auth_headers,
        json={
            "bank_name": "Second Bank",
            "account_holder_name": "Test User",
            "account_type": "SAVINGS",
            "account_number": "999999999999",
            "ifsc_code": "HDFC0001234",
            "is_primary": False
        }
    )
    
    response = client.delete(f"/bank-accounts/{test_bank_account.id}", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert "deleted" in data["message"].lower()


def test_delete_last_bank_account_fails(client, test_bank_account, auth_headers):
    """Test deleting the last bank account should fail"""
    response = client.delete(f"/bank-accounts/{test_bank_account.id}", headers=auth_headers)
    
    assert response.status_code == 400
    data = response.json()
    assert "cannot delete" in str(data).lower() or "only account" in str(data).lower()


def test_delete_nonexistent_bank_account(client, auth_headers):
    """Test deleting non-existent bank account"""
    fake_id = uuid.uuid4()
    response = client.delete(f"/bank-accounts/{fake_id}", headers=auth_headers)
    
    assert response.status_code == 404


#  TEST VERIFY BANK ACCOUNT (ADMIN) 

def test_admin_verify_bank_account(client, test_bank_account, admin_auth_headers):
    """Test admin verifying a bank account"""
    response = client.post(
        f"/bank-accounts/{test_bank_account.id}/verify",
        headers=admin_auth_headers,
        json={"verification_method": "MANUAL"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert data["is_verified"] == True


def test_non_admin_cannot_verify(client, test_bank_account, auth_headers):
    """Test non-admin cannot verify bank account"""
    response = client.post(
        f"/bank-accounts/{test_bank_account.id}/verify",
        headers=auth_headers,
        json={"verification_method": "MANUAL"}
    )
    
    assert response.status_code == 403


#  TEST UNAUTHORIZED ACCESS 

def test_unauthorized_access_no_token(client):
    """Test accessing bank accounts without authentication"""
    response = client.get("/bank-accounts")
    assert response.status_code == 401

# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
