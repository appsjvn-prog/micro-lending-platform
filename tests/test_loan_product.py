import pytest
import uuid
from decimal import Decimal
from app.models.user import User, UserRole, UserStatus
from app.models.loan_product import LoanProduct, InterestType, LoanProductStatus, RepaymentFrequency, RepaymentDaySource
from app.core.security import get_password_hash, create_access_token


# ============== FIXTURES ==============

@pytest.fixture
def test_admin(db):
    """Create a test admin user"""
    admin = User(
        id=uuid.uuid4(),
        email=f"admin_{uuid.uuid4().hex[:8]}@example.com",
        country_code="+91",
        national_number="9876543210",
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
    """Create a test borrower user (non-admin)"""
    borrower = User(
        id=uuid.uuid4(),
        email=f"borrower_{uuid.uuid4().hex[:8]}@example.com",
        country_code="+91",
        national_number="9876543211",
        password_hash=get_password_hash("TestPass123"),
        role=UserRole.BORROWER,
        status=UserStatus.ACTIVE
    )
    db.add(borrower)
    db.commit()
    db.refresh(borrower)
    return borrower


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
def sample_loan_product_data():
    """Sample loan product data"""
    return {
        "name": "Personal Loan",
        "min_amount": 5000.00,
        "max_amount": 500000.00,
        "min_tenure_months": 6,
        "max_tenure_months": 24,
        "interest_type": "FLAT",
        "min_interest_rate": 5.0,
        "max_interest_rate": 20.0,
        "repayment_frequency": "MONTHLY",
        "repayment_day_source": "DISBURSEMENT_DATE",
        "grace_period_days": 3,
        "late_fee_percentage": 2.0,
        "status": "ACTIVE"
    }


@pytest.fixture
def test_loan_product(db, sample_loan_product_data):
    """Create a test loan product"""
    product = LoanProduct(
        name=sample_loan_product_data["name"],
        min_amount=Decimal(str(sample_loan_product_data["min_amount"])),
        max_amount=Decimal(str(sample_loan_product_data["max_amount"])),
        min_tenure_months=sample_loan_product_data["min_tenure_months"],
        max_tenure_months=sample_loan_product_data["max_tenure_months"],
        interest_type=InterestType.FLAT,
        min_interest_rate=Decimal(str(sample_loan_product_data["min_interest_rate"])),
        max_interest_rate=Decimal(str(sample_loan_product_data["max_interest_rate"])),
        repayment_frequency=RepaymentFrequency.MONTHLY,
        repayment_day_source=RepaymentDaySource.DISBURSEMENT_DATE,
        grace_period_days=sample_loan_product_data["grace_period_days"],
        late_fee_percentage=Decimal(str(sample_loan_product_data["late_fee_percentage"])),
        status=LoanProductStatus.ACTIVE
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


# ============== TEST CREATE LOAN PRODUCT ==============

def test_create_loan_product_success(client, admin_auth_headers, sample_loan_product_data):
    """Test successful loan product creation by admin"""
    response = client.post(
        "/loan-products",
        headers=admin_auth_headers,
        json=sample_loan_product_data
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == "Personal Loan"
    assert data["status"] == "ACTIVE"
    assert "created successfully" in data["message"]


def test_create_loan_product_duplicate_name(client, admin_auth_headers, test_loan_product, sample_loan_product_data):
    """Test creating loan product with duplicate name should fail"""
    response = client.post(
        "/loan-products",
        headers=admin_auth_headers,
        json=sample_loan_product_data
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "already exists" in str(data).lower()


def test_create_loan_product_invalid_amount_range(client, admin_auth_headers):
    """Test creating loan product with invalid amount range (min > max)"""
    response = client.post(
        "/loan-products",
        headers=admin_auth_headers,
        json={
            "name": "Invalid Product",
            "min_amount": 50000.00,
            "max_amount": 10000.00,
            "min_tenure_months": 6,
            "max_tenure_months": 24,
            "interest_type": "FLAT",
            "min_interest_rate": 5.0,
            "max_interest_rate": 20.0,
            "status": "ACTIVE"
        }
    )
    
    assert response.status_code == 422


def test_create_loan_product_invalid_tenure_range(client, admin_auth_headers):
    """Test creating loan product with invalid tenure range"""
    response = client.post(
        "/loan-products",
        headers=admin_auth_headers,
        json={
            "name": "Invalid Tenure",
            "min_amount": 5000.00,
            "max_amount": 50000.00,
            "min_tenure_months": 24,
            "max_tenure_months": 6,
            "interest_type": "FLAT",
            "min_interest_rate": 5.0,
            "max_interest_rate": 20.0,
            "status": "ACTIVE"
        }
    )
    
    assert response.status_code == 422


def test_create_loan_product_invalid_interest_range(client, admin_auth_headers):
    """Test creating loan product with invalid interest rate range"""
    response = client.post(
        "/loan-products",
        headers=admin_auth_headers,
        json={
            "name": "Invalid Interest",
            "min_amount": 5000.00,
            "max_amount": 50000.00,
            "min_tenure_months": 6,
            "max_tenure_months": 24,
            "interest_type": "FLAT",
            "min_interest_rate": 20.0,
            "max_interest_rate": 5.0,
            "status": "ACTIVE"
        }
    )
    
    assert response.status_code == 422


def test_create_loan_product_missing_required_fields(client, admin_auth_headers):
    """Test creating loan product with missing required fields"""
    response = client.post(
        "/loan-products",
        headers=admin_auth_headers,
        json={
            "name": "Incomplete Product"
        }
    )
    
    assert response.status_code == 422


def test_create_loan_product_non_admin_fails(client, borrower_auth_headers, sample_loan_product_data):
    """Test non-admin cannot create loan product"""
    response = client.post(
        "/loan-products",
        headers=borrower_auth_headers,
        json=sample_loan_product_data
    )
    
    assert response.status_code == 403


def test_create_loan_product_unauthorized(client, sample_loan_product_data):
    """Test unauthenticated user cannot create loan product"""
    response = client.post("/loan-products", json=sample_loan_product_data)
    
    assert response.status_code == 401


# ============== TEST GET LOAN PRODUCTS ==============

def test_get_all_loan_products(client, test_loan_product):
    """Test getting all loan products (public - no auth required)"""
    response = client.get("/loan-products")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["name"] == "Personal Loan"


def test_get_loan_products_filter_by_status(client, test_loan_product):
    """Test filtering loan products by status"""
    response = client.get("/loan-products?status=ACTIVE")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    
    response = client.get("/loan-products?status=INACTIVE")
    assert response.status_code == 200
    data = response.json()
    # May be empty if no inactive products


def test_get_loan_product_by_id(client, test_loan_product):
    """Test getting loan product by ID"""
    response = client.get(f"/loan-products/{test_loan_product.id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_loan_product.id)
    assert data["name"] == "Personal Loan"
    assert data["min_amount"] == "5000.00"
    assert data["max_amount"] == "500000.00"


def test_get_loan_product_not_found(client):
    """Test getting non-existent loan product"""
    fake_id = uuid.uuid4()
    response = client.get(f"/loan-products/{fake_id}")
    
    assert response.status_code == 404
    data = response.json()
    assert "not found" in str(data).lower()


def test_get_loan_product_invalid_id(client):
    """Test getting loan product with invalid ID format"""
    response = client.get("/loan-products/invalid-id-format")
    
    assert response.status_code == 400 
    data = response.json()

    error_msg = str(data).lower()
    assert "invalid" in error_msg or "format" in error_msg


# ============== TEST UPDATE LOAN PRODUCT ==============

def test_update_loan_product_success(client, admin_auth_headers, test_loan_product):
    """Test successfully updating loan product"""
    response = client.put(
        f"/loan-products/{test_loan_product.id}",
        headers=admin_auth_headers,
        json={
            "name": "Updated Personal Loan",
            "min_interest_rate": 6.0,
            "max_interest_rate": 18.0
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Personal Loan"
    assert float(data["min_interest_rate"]) == 6.0
    assert float(data["max_interest_rate"]) == 18.0


def test_update_loan_product_duplicate_name(client, admin_auth_headers, test_loan_product):
    """Test updating loan product with duplicate name should fail"""
    # Create another product first
    response1 = client.post(
        "/loan-products",
        headers=admin_auth_headers,
        json={
            "name": "Another Product",
            "min_amount": 5000.00,
            "max_amount": 50000.00,
            "min_tenure_months": 6,
            "max_tenure_months": 24,
            "interest_type": "FLAT",
            "min_interest_rate": 5.0,
            "max_interest_rate": 20.0,
            "status": "ACTIVE"
        }
    )
    assert response1.status_code == 201
    
    # Try to update first product with second product's name
    response = client.put(
        f"/loan-products/{test_loan_product.id}",
        headers=admin_auth_headers,
        json={"name": "Another Product"}
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "already exists" in str(data).lower()


def test_update_loan_product_partial(client, admin_auth_headers, test_loan_product):
    """Test partial update of loan product"""
    response = client.put(
        f"/loan-products/{test_loan_product.id}",
        headers=admin_auth_headers,
        json={"min_interest_rate": 7.5}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert float(data["min_interest_rate"]) == 7.5
    # Other fields should remain unchanged
    assert data["name"] == "Personal Loan"


def test_update_loan_product_non_admin_fails(client, borrower_auth_headers, test_loan_product):
    """Test non-admin cannot update loan product"""
    response = client.put(
        f"/loan-products/{test_loan_product.id}",
        headers=borrower_auth_headers,
        json={"name": "Hacked Name"}
    )
    
    assert response.status_code == 403


def test_update_nonexistent_loan_product(client, admin_auth_headers):
    """Test updating non-existent loan product"""
    fake_id = uuid.uuid4()
    response = client.put(
        f"/loan-products/{fake_id}",
        headers=admin_auth_headers,
        json={"name": "New Name"}
    )
    
    assert response.status_code == 404


def test_update_loan_product_invalid_amount_range(client, admin_auth_headers, test_loan_product):
    """Test updating loan product with invalid amount range"""
    response = client.put(
        f"/loan-products/{test_loan_product.id}",
        headers=admin_auth_headers,
        json={
            "min_amount": 100000.00,
            "max_amount": 50000.00
        }
    )
    
    # Schema validation returns 422 (Unprocessable Entity)
    assert response.status_code == 422

# ============== TEST ACTIVATE/DEACTIVATE LOAN PRODUCT ==============

def test_activate_loan_product(client, admin_auth_headers, test_loan_product):
    """Test activating a loan product"""
    # First deactivate
    deactivate_response = client.patch(
        f"/loan-products/{test_loan_product.id}/deactivate",
        headers=admin_auth_headers
    )
    assert deactivate_response.status_code == 200
    
    # Then activate
    response = client.patch(
        f"/loan-products/{test_loan_product.id}/activate",
        headers=admin_auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ACTIVE"


def test_deactivate_loan_product(client, admin_auth_headers, test_loan_product):
    """Test deactivating a loan product"""
    response = client.patch(
        f"/loan-products/{test_loan_product.id}/deactivate",
        headers=admin_auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "INACTIVE"


def test_activate_already_active_product(client, admin_auth_headers, test_loan_product):
    """Test activating already active product (should still work)"""
    response = client.patch(
        f"/loan-products/{test_loan_product.id}/activate",
        headers=admin_auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ACTIVE"


def test_activate_nonexistent_loan_product(client, admin_auth_headers):
    """Test activating non-existent loan product"""
    fake_id = uuid.uuid4()
    response = client.patch(f"/loan-products/{fake_id}/activate", headers=admin_auth_headers)
    
    assert response.status_code == 404


def test_deactivate_nonexistent_loan_product(client, admin_auth_headers):
    """Test deactivating non-existent loan product"""
    fake_id = uuid.uuid4()
    response = client.patch(f"/loan-products/{fake_id}/deactivate", headers=admin_auth_headers)
    
    assert response.status_code == 404


def test_activate_loan_product_non_admin_fails(client, borrower_auth_headers, test_loan_product):
    """Test non-admin cannot activate loan product"""
    response = client.patch(
        f"/loan-products/{test_loan_product.id}/activate",
        headers=borrower_auth_headers
    )
    
    assert response.status_code == 403

def test_deactivate_loan_product_success(client, admin_auth_headers, test_loan_product):
    """Test deactivating a loan product"""
    response = client.patch(
        f"/loan-products/{test_loan_product.id}/deactivate",
        headers=admin_auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "INACTIVE"

# ============== TEST EDGE CASES ==============

def test_create_loan_product_with_boundary_values(client, admin_auth_headers):
    """Test creating loan product with boundary values"""
    response = client.post(
        "/loan-products",
        headers=admin_auth_headers,
        json={
            "name": "Boundary Product",
            "min_amount": 5000.00,
            "max_amount": 5000.00,  # Equal values - should fail validation
            "min_tenure_months": 6,
            "max_tenure_months": 24,
            "interest_type": "FLAT",
            "min_interest_rate": 5.0,
            "max_interest_rate": 20.0,
            "status": "ACTIVE"
        }
    )
    
    # min_amount == max_amount should fail
    assert response.status_code == 422


def test_create_loan_product_with_max_length_name(client, admin_auth_headers):
    """Test creating loan product with maximum length name"""
    response = client.post(
        "/loan-products",
        headers=admin_auth_headers,
        json={
            "name": "A" * 100,  # Max 100 characters
            "min_amount": 5000.00,
            "max_amount": 50000.00,
            "min_tenure_months": 6,
            "max_tenure_months": 24,
            "interest_type": "FLAT",
            "min_interest_rate": 5.0,
            "max_interest_rate": 20.0,
            "status": "ACTIVE"
        }
    )
    
    assert response.status_code == 201


def test_get_all_loan_products_pagination_handling(client, test_loan_product):
    """Test that get all loan products works without pagination params"""
    response = client.get("/loan-products")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])