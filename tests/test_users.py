import pytest
from uuid import UUID

from uuid import UUID

def test_create_user_success(client):
    # Test data
    user_data = {
        "email": "john@example.com",
        "phone": "+919876543210",
        "role": "BORROWER",
        "password": "Test@123"
    }
    
    # Make API call
    response = client.post("/users", json=user_data)
    
    # Check response
    assert response.status_code == 201
    data = response.json()
    # assert data["email"] == "john@example.com"
    # assert data["phone"] == "+919876543210"
    # assert data["role"] == "BORROWER"
    assert "id" in data
    
    # Verify ID is valid UUID
    try:
        UUID(data["id"])  # This will raise ValueError if invalid
        is_valid_uuid = True
    except ValueError:
        is_valid_uuid = False
    
    assert is_valid_uuid, f"ID '{data['id']}' is not a valid UUID"

    
def test_create_user_fails_with_duplicate_email(client):
    """Test that creating a user with existing email fails"""
    # Create first user
    user_data = {
        "email": "duplicate@example.com",
        "phone": "+919876543211",
        "role": "BORROWER",
        "password": "Test@123"
    }
    response1 = client.post("/users", json=user_data)
    assert response1.status_code == 201
    
    # Try to create same user again
    response2 = client.post("/users", json=user_data)
    
    # Should fail
    assert response2.status_code == 400
    error_data = response2.json()
    assert "already exists" in error_data["detail"].lower()


def test_create_user_fails_with_duplicate_phone(client):
    """Test that creating a user with existing phone fails"""
    # Create first user
    user_data1 = {
        "email": "user1@example.com",
        "phone": "+919876543211",
        "role": "BORROWER",
        "password": "Test@123"
    }
    response1 = client.post("/users", json=user_data1)
    assert response1.status_code == 201
    
    # Try to create another user with same phone
    user_data2 = {
        "email": "user2@example.com",  # Different email
        "phone": "+919876543211",       # Same phone
        "role": "BORROWER",
        "password": "Test@123"
    }
    response2 = client.post("/users", json=user_data2)
    
    # Should fail
    assert response2.status_code == 400
    error_data = response2.json()
    assert "already exists" in error_data["detail"].lower()


def test_create_user_fails_with_invalid_email(client):
    """Test that invalid email format is rejected"""
    user_data = {
        "email": "not-an-email",  # Invalid email
        "phone": "+919876543211",
        "role": "BORROWER",
        "password": "Test@123"
    }
    
    response = client.post("/users", json=user_data)
    
    # Should fail with 422 validation error
    assert response.status_code == 422


def test_create_user_fails_with_invalid_phone(client):
    """Test that invalid phone format is rejected"""
    user_data = {
        "email": "test@example.com",
        "phone": "12345",  # Invalid phone (no + and country code)
        "role": "BORROWER",
        "password": "Test@123"
    }
    
    response = client.post("/users", json=user_data)
    
    # Should fail with 422 validation error
    assert response.status_code == 422


def test_get_users_requires_admin(client, admin_key):
    """Test that getting all users requires admin key"""
    # First create a user - with debug prints
    user_data = {
        "email": "test@example.com",
        "phone": "+919876543210",
        "role": "BORROWER",
        "password": "Test@123"
    }
    
    # Print what we're sending
    print(f"\n📤 Sending user data: {user_data}")
    
    create_response = client.post("/users", json=user_data)
    
    # Print the response
    print(f"📥 Create user status: {create_response.status_code}")
    print(f"📥 Create user response: {create_response.json()}")
    
    # Assert creation worked
    assert create_response.status_code == 201, f"User creation failed: {create_response.json()}"
    user_id = create_response.json()["id"]
    print(f"✅ User created with ID: {user_id}")
    
    # Try without admin key
    response = client.get("/users")
    assert response.status_code == 401
    assert "Admin key required" in response.json()["detail"]
    
    # Try with admin key
    response = client.get(
        "/users",
        headers={"X-Admin-Key": admin_key}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    
    print(f"✅ Test passed! Found {len(data)} users")


def test_get_single_user_requires_admin(client, admin_key):
    """Test that getting a single user requires admin key"""
    # First create a user
    user_data = {
        "email": "single@example.com",
        "phone": "+919876543210",
        "role": "BORROWER",
        "password": "Test@123"
    }
    create_resp = client.post("/users", json=user_data)
    user_id = create_resp.json()["id"]
    
    # Try without admin key
    response = client.get(f"/users/{user_id}")
    assert response.status_code == 401
    
    # Try with admin key
    response = client.get(
        f"/users/{user_id}",
        headers={"X-Admin-Key": admin_key}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "single@example.com"
    assert data["id"] == user_id


def test_get_nonexistent_user_returns_404(client, admin_key):
    """Test that getting a non-existent user returns 404"""
    fake_id = "12345678-1234-1234-1234-123456789012"
    
    response = client.get(
        f"/users/{fake_id}",
        headers={"X-Admin-Key": admin_key}
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_user_with_invalid_uuid_returns_400(client, admin_key):
    """Test that invalid UUID format returns 400"""
    invalid_id = "not-a-uuid"
    
    response = client.get(
        f"/users/{invalid_id}",
        headers={"X-Admin-Key": admin_key}
    )
    
    assert response.status_code == 400
    assert "Invalid user ID format" in response.json()["detail"]