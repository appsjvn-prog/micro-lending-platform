import pytest
from uuid import UUID

def test_create_bank_account_success(client):
    """Test that a bank account can be created for a user"""
    # First create a user
    user_data = {
        "email": "bankuser@example.com",
        "phone": "+919876543212",
        "role": "BORROWER",
        "password": "Test@123"
    }
    user_resp = client.post("/users", json=user_data)
    assert user_resp.status_code == 201
    user_id = user_resp.json()["id"]
    
    # Create bank account
    account_data = {
        "bank_name": "HDFC Bank",
        "account_holder_name": "Test User",
        "account_type": "SAVINGS",
        "account_number": "1234567890",
        "ifsc_code": "HDFC0001234",
        "is_primary": True
    }
    
    response = client.post(f"/users/{user_id}/bank-accounts", json=account_data)
    
    assert response.status_code == 201
    data = response.json()
    
    # ✅ Only check what's in minimal response
    assert "id" in data
    assert data["user_id"] == user_id
    assert data["is_verified"] == False
    assert "created_at" in data
    assert "updated_at" in data
    
    # Verify UUID is valid
    try:
        UUID(data["id"])
        is_valid_uuid = True
    except ValueError:
        is_valid_uuid = False
    assert is_valid_uuid

def test_create_bank_account_fails_for_nonexistent_user(client):
    """Test that creating bank account for non-existent user fails"""
    account_data = {
        "bank_name": "HDFC Bank",
        "account_holder_name": "Test User",
        "account_type": "SAVINGS",
        "account_number": "9999999999",
        "ifsc_code": "HDFC0001234",
        "is_primary": True
    }
    
    # Use random UUID that doesn't exist
    fake_user_id = "12345678-1234-1234-1234-123456789012"
    response = client.post(f"/users/{fake_user_id}/bank-accounts", json=account_data)
    
    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


def test_create_bank_account_fails_with_duplicate_account_number(client):
    """Test that duplicate account numbers are not allowed"""
    # First create a user
    user_data1 = {
        "email": "user1@example.com",
        "phone": "+919876543213",
        "role": "BORROWER",
        "password": "Test@123"
    }
    user_resp1 = client.post("/users", json=user_data1)
    assert user_resp1.status_code == 201
    user_id1 = user_resp1.json()["id"]
    
    # Create second user
    user_data2 = {
        "email": "user2@example.com",
        "phone": "+919876543214",
        "role": "BORROWER",
        "password": "Test@123"
    }
    user_resp2 = client.post("/users", json=user_data2)
    assert user_resp2.status_code == 201
    user_id2 = user_resp2.json()["id"]
    
    # Create bank account for first user
    account_data = {
        "bank_name": "HDFC Bank",
        "account_holder_name": "Test User 1",
        "account_type": "SAVINGS",
        "account_number": "5555555555",
        "ifsc_code": "HDFC0001234",
        "is_primary": True
    }
    response1 = client.post(f"/users/{user_id1}/bank-accounts", json=account_data)
    assert response1.status_code == 201
    
    # Try to create same account number for second user
    response2 = client.post(f"/users/{user_id2}/bank-accounts", json=account_data)
    
    assert response2.status_code == 400
    assert "already registered" in response2.json()["detail"].lower()


def test_get_user_bank_accounts(client):
    """Test that we can get all bank accounts for a user"""
    # First create a user
    user_data = {
        "email": "getaccounts@example.com",
        "phone": "+919876543215",
        "role": "BORROWER",
        "password": "Test@123"
    }
    user_resp = client.post("/users", json=user_data)
    assert user_resp.status_code == 201
    user_id = user_resp.json()["id"]
    
    # Create first bank account
    account1_data = {
        "bank_name": "HDFC Bank",
        "account_holder_name": "Test User",
        "account_type": "SAVINGS",
        "account_number": "1111111111",
        "ifsc_code": "HDFC0001234",
        "is_primary": True
    }
    resp1 = client.post(f"/users/{user_id}/bank-accounts", json=account1_data)
    assert resp1.status_code == 201
    
    # Create second bank account
    account2_data = {
        "bank_name": "ICICI Bank",
        "account_holder_name": "Test User",
        "account_type": "CHECKING",
        "account_number": "2222222222",
        "ifsc_code": "ICIC0001234",
        "is_primary": False
    }
    resp2 = client.post(f"/users/{user_id}/bank-accounts", json=account2_data)
    assert resp2.status_code == 201
    
    # Get all accounts
    response = client.get(f"/users/{user_id}/bank-accounts")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    
    # Check that primary is set correctly
    primary_accounts = [a for a in data if a["is_primary"] == True]
    assert len(primary_accounts) == 1


def test_update_bank_account(client):
    """Test that we can update a bank account"""
    # Create user
    user_data = {
        "email": "update@example.com",
        "phone": "+919876543216",
        "role": "BORROWER",
        "password": "Test@123"
    }
    user_resp = client.post("/users", json=user_data)
    assert user_resp.status_code == 201
    user_id = user_resp.json()["id"]
    
    # Create bank account
    account_data = {
        "bank_name": "HDFC Bank",
        "account_holder_name": "Test User",
        "account_type": "SAVINGS",
        "account_number": "7777777777",
        "ifsc_code": "HDFC0001234",
        "is_primary": True
    }
    create_resp = client.post(f"/users/{user_id}/bank-accounts", json=account_data)
    assert create_resp.status_code == 201
    account_id = create_resp.json()["id"]
    
    # Update bank account
    update_data = {
        "bank_name": "ICICI Bank",
        "is_primary": False
    }
    
    response = client.put(f"/bank-accounts/{account_id}", json=update_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["bank_name"] == "ICICI Bank"
    assert data["is_primary"] == False
    assert data["account_number"] == "7777777777"  # Unchanged


def test_delete_bank_account(client):
    """Test that we can delete a bank account"""
    # Create user
    user_data = {
        "email": "delete@example.com",
        "phone": "+919876543217",
        "role": "BORROWER",
        "password": "Test@123"
    }
    user_resp = client.post("/users", json=user_data)
    assert user_resp.status_code == 201
    user_id = user_resp.json()["id"]
    
    # Create bank account
    account_data = {
        "bank_name": "HDFC Bank",
        "account_holder_name": "Test User",
        "account_type": "SAVINGS",
        "account_number": "8888888888",
        "ifsc_code": "HDFC0001234",
        "is_primary": True
    }
    create_resp = client.post(f"/users/{user_id}/bank-accounts", json=account_data)
    assert create_resp.status_code == 201
    account_id = create_resp.json()["id"]
    
    # Delete bank account
    response = client.delete(f"/bank-accounts/{account_id}")
    
    assert response.status_code == 204
    
    # Verify it's gone - try to get it (should fail)
    # Note: You might need a GET endpoint for single bank account
    # If you don't have one, you can check the list
    get_response = client.get(f"/users/{user_id}/bank-accounts")
    accounts = get_response.json()
    assert len(accounts) == 0


def test_primary_account_uniqueness(client):
    """Test that a user can have only one primary account"""
    # Create user
    user_data = {
        "email": "primary@example.com",
        "phone": "+919876543218",
        "role": "BORROWER",
        "password": "Test@123"
    }
    user_resp = client.post("/users", json=user_data)
    assert user_resp.status_code == 201
    user_id = user_resp.json()["id"]
    
    # Create first account (primary)
    account1_data = {
        "bank_name": "HDFC Bank",
        "account_holder_name": "Test User",
        "account_type": "SAVINGS",
        "account_number": "9999999999",
        "ifsc_code": "HDFC0001234",
        "is_primary": True
    }
    resp1 = client.post(f"/users/{user_id}/bank-accounts", json=account1_data)
    assert resp1.status_code == 201
    account1_id = resp1.json()["id"]
    
    # Create second account (also primary - should auto-unset first)
    account2_data = {
        "bank_name": "ICICI Bank",
        "account_holder_name": "Test User",
        "account_type": "CHECKING",
        "account_number": "1010101010",
        "ifsc_code": "ICIC0001234",
        "is_primary": True
    }
    resp2 = client.post(f"/users/{user_id}/bank-accounts", json=account2_data)
    assert resp2.status_code == 201
    
    # Get all accounts
    get_resp = client.get(f"/users/{user_id}/bank-accounts")
    accounts = get_resp.json()
    
    # Count primary accounts
    primary_count = sum(1 for a in accounts if a["is_primary"])
    assert primary_count == 1
    
    # Find which one is primary
    primary_account = next(a for a in accounts if a["is_primary"])
    assert primary_account["id"] == resp2.json()["id"]  # New one is primary