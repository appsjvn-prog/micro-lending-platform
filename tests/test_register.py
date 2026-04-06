import pytest
import uuid
from typing import Dict, Any

# Helper function for consistent error assertion
def assert_error_response(data: Dict[str, Any], expected_message: str, expected_code: str = None):
    """
    Assert error response format (handles both AppException and HTTPException)
    """
    if "success" in data:
        # Custom AppException format
        assert data["success"] == False
        assert expected_message.lower() in data["message"].lower()
        if expected_code:
            assert data["error_code"] == expected_code
    elif "detail" in data:
        # HTTPException format
        assert expected_message.lower() in data["detail"].lower()
    else:
        pytest.fail(f"Unexpected error response format: {data}")

def test_register_success(client):
    """Test successful registration"""
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    
    response = client.post(
        "/register",
        json={
            "email": email,
            "phone": {"country_code": "+91", "national_number": "9876543210"},
            "role": "BORROWER"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] in ["ACTIVE", "INACTIVE"]
    assert "created_at" in data
    assert "updated_at" in data

def test_register_duplicate_email(client):
    """Test duplicate email"""
    email = f"dup_{uuid.uuid4().hex[:8]}@example.com"

    # First registration
    response1 = client.post(
        "/register",
        json={
            "email": email,
            "phone": {"country_code": "+91", "national_number": "9876543210"},
            "role": "BORROWER"
        }
    )
    assert response1.status_code == 201

    # Second registration with same email
    response2 = client.post(
        "/register",
        json={
            "email": email,
            "phone": {"country_code": "+91", "national_number": "9876543211"},
            "role": "BORROWER"
        }
    )

    assert response2.status_code == 400
    assert_error_response(
        response2.json(), 
        "already exists", 
        "DUPLICATE_RESOURCE"
    )

def test_register_duplicate_phone(client):
    """Test duplicate phone number"""
    phone_number = "9999999999"
    
    # First registration
    response1 = client.post(
        "/register",
        json={
            "email": f"user1_{uuid.uuid4().hex[:8]}@example.com",
            "phone": {"country_code": "+91", "national_number": phone_number},
            "role": "BORROWER"
        }
    )
    assert response1.status_code == 201
    
    # Second registration with same phone
    response2 = client.post(
        "/register",
        json={
            "email": f"user2_{uuid.uuid4().hex[:8]}@example.com",
            "phone": {"country_code": "+91", "national_number": phone_number},
            "role": "BORROWER"
        }
    )
    
    assert response2.status_code == 400
    assert_error_response(
        response2.json(), 
        "already exists", 
        "DUPLICATE_RESOURCE"
    )

def test_register_invalid_phone(client):
    """Test registration with invalid phone"""
    response = client.post(
        "/register",
        json={
            "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
            "phone": {"country_code": "+91", "national_number": "123"},
            "role": "BORROWER"
        }
    )
    
    assert response.status_code == 422
    data = response.json()
    
    # Handle validation error format
    if "success" in data:
        assert data["success"] == False
        assert "validation" in data["message"].lower()
    else:
        assert "detail" in data