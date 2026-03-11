import pytest
from uuid import UUID

def test_create_loan_product_success(client, admin_key):
    """Test that a loan product can be created successfully (admin only)"""
    product_data = {
        "name": "Test Personal Loan",
        "min_amount": 10000,
        "max_amount": 500000,
        "min_tenure_months": 6,
        "max_tenure_months": 24,  
        "interest_type": "REDUCING",
        "min_interest_rate": 10.5,
        "max_interest_rate": 18.0,
        "status": "ACTIVE"
    }
    
    # Try without admin key - should fail
    response = client.post("/loan-products", json=product_data)
    assert response.status_code == 401
    assert "Admin key required" in response.json()["detail"]
    
    # Try with admin key - should succeed
    response = client.post(
        "/loan-products", 
        json=product_data,
        headers={"X-Admin-Key": admin_key}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Personal Loan"
    assert float(data["min_amount"]) == 10000  
    assert float(data["max_amount"]) == 500000
    assert data["min_tenure_months"] == 6
    assert data["max_tenure_months"] == 24 
    assert data["interest_type"] == "REDUCING"
    assert float(data["min_interest_rate"]) == 10.5  
    assert float(data["max_interest_rate"]) == 18.0 
    assert data["status"] == "ACTIVE"
    assert "id" in data
    
    # Verify ID is valid UUID
    try:
        UUID(data["id"])
        is_valid_uuid = True
    except ValueError:
        is_valid_uuid = False
    assert is_valid_uuid


def test_create_loan_product_fails_with_duplicate_name(client, admin_key):
    """Test that creating a loan product with existing name fails"""
    product_data = {
        "name": "Unique Loan Product",
        "min_amount": 10000,
        "max_amount": 500000,
        "min_tenure_months": 6,
        "max_tenure_months": 24,  
        "interest_type": "REDUCING",
        "min_interest_rate": 10.5,
        "max_interest_rate": 18.0,
        "status": "ACTIVE"
    }
    
    # Create first product
    response1 = client.post(
        "/loan-products", 
        json=product_data,
        headers={"X-Admin-Key": admin_key}
    )
    assert response1.status_code == 201
    
    # Try to create same product again
    response2 = client.post(
        "/loan-products", 
        json=product_data,
        headers={"X-Admin-Key": admin_key}
    )
    
    assert response2.status_code == 400
    assert "already exists" in response2.json()["detail"].lower()


def test_create_loan_product_validates_ranges(client, admin_key):
    """Test that loan product validates min < max for all ranges"""
    # Test invalid amount range (min > max)
    invalid_amount = {
        "name": "Invalid Amount Loan",
        "min_amount": 500000,
        "max_amount": 10000,
        "min_tenure_months": 6,
        "max_tenure_months": 24,  
        "interest_type": "REDUCING",
        "min_interest_rate": 10.5,
        "max_interest_rate": 18.0,
        "status": "ACTIVE"
    }
    
    response = client.post(
        "/loan-products",
        json=invalid_amount,
        headers={"X-Admin-Key": admin_key}
    )
    assert response.status_code == 422
    
    # Test invalid tenure range (min > max)
    invalid_tenure = {
        "name": "Invalid Tenure Loan",
        "min_amount": 10000,
        "max_amount": 500000,
        "min_tenure_months": 24,
        "max_tenure_months": 6,
        "interest_type": "REDUCING",
        "min_interest_rate": 10.5,
        "max_interest_rate": 18.0,
        "status": "ACTIVE"
    }
    
    response = client.post(
        "/loan-products",
        json=invalid_tenure,
        headers={"X-Admin-Key": admin_key}
    )
    assert response.status_code == 422
    
    # Test invalid interest rate range (min > max)
    invalid_interest = {
        "name": "Invalid Interest Loan",
        "min_amount": 10000,
        "max_amount": 500000,
        "min_tenure_months": 6,
        "max_tenure_months": 24,  
        "interest_type": "REDUCING",
        "min_interest_rate": 18.0,
        "max_interest_rate": 10.5,
        "status": "ACTIVE"
    }
    
    response = client.post(
        "/loan-products",
        json=invalid_interest,
        headers={"X-Admin-Key": admin_key}
    )
    assert response.status_code == 422


def test_get_loan_products_public(client, admin_key):
    """Test that getting all loan products is public (no admin key needed)"""
    # First create a loan product (as admin)
    product_data = {
        "name": "Public Test Loan",
        "min_amount": 10000,
        "max_amount": 500000,
        "min_tenure_months": 6,
        "max_tenure_months": 24,  
        "interest_type": "REDUCING",
        "min_interest_rate": 10.5,
        "max_interest_rate": 18.0,
        "status": "ACTIVE"
    }
    create_resp = client.post(
        "/loan-products",
        json=product_data,
        headers={"X-Admin-Key": admin_key}
    )
    assert create_resp.status_code == 201
    
    # Get all loan products (no admin key needed)
    response = client.get("/loan-products")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    
    # Check that our created product is in the list
    names = [p["name"] for p in data]
    assert "Public Test Loan" in names


def test_get_single_loan_product_public(client, admin_key):
    """Test that getting a single loan product is public (no admin key needed)"""
    # First create a loan product (as admin)
    product_data = {
        "name": "Single Test Loan",
        "min_amount": 10000,
        "max_amount": 500000,
        "min_tenure_months": 6,
        "max_tenure_months": 24,  
        "interest_type": "REDUCING",
        "min_interest_rate": 10.5,
        "max_interest_rate": 18.0,
        "status": "ACTIVE"
    }
    create_resp = client.post(
        "/loan-products",
        json=product_data,
        headers={"X-Admin-Key": admin_key}
    )
    assert create_resp.status_code == 201
    product_id = create_resp.json()["id"]
    
    # Get single loan product (no admin key needed)
    response = client.get(f"/loan-products/{product_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Single Test Loan"
    assert data["id"] == product_id


def test_update_loan_product_admin_only(client, admin_key):
    """Test that updating a loan product requires admin key"""
    # First create a loan product (as admin)
    product_data = {
        "name": "Update Test Loan",
        "min_amount": 10000,
        "max_amount": 500000,
        "min_tenure_months": 6,
        "max_tenure_months": 24,  
        "interest_type": "REDUCING",
        "min_interest_rate": 10.5,
        "max_interest_rate": 18.0,
        "status": "ACTIVE"
    }
    create_resp = client.post(
        "/loan-products",
        json=product_data,
        headers={"X-Admin-Key": admin_key}
    )
    assert create_resp.status_code == 201
    product_id = create_resp.json()["id"]
    
    # Update data
    update_data = {
        "name": "Updated Loan Name",
        "max_amount": 600000,
        "status": "INACTIVE"
    }
    
    # Try without admin key - should fail
    response = client.put(f"/loan-products/{product_id}", json=update_data)
    assert response.status_code == 401
    
    # Try with admin key - should succeed
    response = client.put(
        f"/loan-products/{product_id}", 
        json=update_data,
        headers={"X-Admin-Key": admin_key}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Loan Name"
    assert float(data["max_amount"]) == 600000
    assert data["status"] == "INACTIVE"
    assert float(data["min_amount"]) == 10000


def test_delete_loan_product_admin_only(client, admin_key):
    """Test that deleting a loan product requires admin key"""
    # First create a loan product (as admin)
    product_data = {
        "name": "Delete Test Loan",
        "min_amount": 10000,
        "max_amount": 500000,
        "min_tenure_months": 6,
        "max_tenure_months": 24,  
        "interest_type": "REDUCING",
        "min_interest_rate": 10.5,
        "max_interest_rate": 18.0,
        "status": "ACTIVE"
    }
    create_resp = client.post(
        "/loan-products",
        json=product_data,
        headers={"X-Admin-Key": admin_key}
    )
    assert create_resp.status_code == 201
    product_id = create_resp.json()["id"]
    
    # Try without admin key - should fail
    response = client.delete(f"/loan-products/{product_id}")
    assert response.status_code == 401
    
    # Try with admin key - should succeed (soft delete)
    response = client.delete(
        f"/loan-products/{product_id}",
        headers={"X-Admin-Key": admin_key}
    )
    assert response.status_code == 204
    
    # Verify it's soft deleted (status should be INACTIVE)
    get_response = client.get(f"/loan-products/{product_id}")
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["status"] == "INACTIVE"


def test_activate_deactivate_loan_product(client, admin_key):
    """Test activating and deactivating a loan product"""
    # First create a loan product (as admin)
    product_data = {
        "name": "Activate Test Loan",
        "min_amount": 10000,
        "max_amount": 500000,
        "min_tenure_months": 6,
        "max_tenure_months": 24,  
        "interest_type": "REDUCING",
        "min_interest_rate": 10.5,
        "max_interest_rate": 18.0,
        "status": "ACTIVE"
    }
    create_resp = client.post(
        "/loan-products",
        json=product_data,
        headers={"X-Admin-Key": admin_key}
    )
    assert create_resp.status_code == 201
    product_id = create_resp.json()["id"]
    
    # Deactivate (admin only)
    response = client.patch(
        f"/loan-products/{product_id}/deactivate",
        headers={"X-Admin-Key": admin_key}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "INACTIVE"
    
    # Activate (admin only)
    response = client.patch(
        f"/loan-products/{product_id}/activate",
        headers={"X-Admin-Key": admin_key}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ACTIVE"
    
    # Try without admin key - should fail
    response = client.patch(f"/loan-products/{product_id}/deactivate")
    assert response.status_code == 401


def test_get_nonexistent_loan_product_returns_404(client):
    """Test that getting a non-existent loan product returns 404"""
    fake_id = "12345678-1234-1234-1234-123456789012"
    
    response = client.get(f"/loan-products/{fake_id}")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_loan_product_with_invalid_uuid_returns_400(client):
    """Test that invalid UUID format returns 400"""
    invalid_id = "not-a-uuid"
    
    response = client.get(f"/loan-products/{invalid_id}")
    
    assert response.status_code == 400
    assert "Invalid product ID format" in response.json()["detail"]