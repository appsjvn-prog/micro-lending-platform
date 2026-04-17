
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.core.database import get_db
from app.api.dependencies.auth import get_current_admin
from app.models.user import User
from app.models.loan_product import LoanProduct
from app.schemas.loan_product import (
    LoanProductCreate, LoanProductMinimalResponse, 
    LoanProductResponse, LoanProductUpdate
)
from app.core.exceptions import (
    ValidationException,
    AppException,
    LoanProductNotFoundException,
    LoanProductAlreadyExistsException,
    LoanProductValidationException
)

router = APIRouter(prefix="/loan-products", tags=["Loan Products"])

@router.post("", response_model=LoanProductMinimalResponse, status_code=status.HTTP_201_CREATED)
def create_loan_product(
    product: LoanProductCreate, 
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin) 
): 
    """Create a new loan product (Admin only)"""
    try:
        existing = db.query(LoanProduct).filter(LoanProduct.name == product.name).first()
        if existing:
            raise LoanProductAlreadyExistsException(product.name)
        
        db_product = LoanProduct(
            name=product.name,
            min_amount=product.min_amount,
            max_amount=product.max_amount,
            min_tenure_months=product.min_tenure_months,
            max_tenure_months=product.max_tenure_months,
            interest_type=product.interest_type,
            min_interest_rate=product.min_interest_rate,
            max_interest_rate=product.max_interest_rate,
            repayment_frequency=product.repayment_frequency,
            repayment_day_source=product.repayment_day_source,
            grace_period_days=product.grace_period_days,
            late_fee_percentage=product.late_fee_percentage,
            status=product.status
        )
        
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        
        return {
            "id": db_product.id,
            "name": db_product.name,
            "status": db_product.status,
            "message": "Loan product created successfully"
        }
    
    except (LoanProductValidationException, LoanProductAlreadyExistsException):
        raise
    except Exception as e:
        db.rollback()
        raise AppException(
            f"Failed to create loan product: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.get("", response_model=List[LoanProductResponse])
def get_loan_products(
    status: str = None,
    db: Session = Depends(get_db)
):
    """Get all loan products"""
    try:
        query = db.query(LoanProduct)
        
        if status:
            status = status.upper()
            query = query.filter(LoanProduct.status == status)
        
        return query.all()
    except Exception as e:
        raise AppException(
            f"Failed to retrieve loan products: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.get("/{product_id}", response_model=LoanProductResponse)
def get_loan_product(product_id: str, db: Session = Depends(get_db)):
    """Get loan product by ID"""
    try:
        try:
            product_uuid = uuid.UUID(product_id)
        except ValueError:
            raise ValidationException("Invalid product ID format")
        
        product = db.query(LoanProduct).filter(LoanProduct.id == product_uuid).first()
        if not product:
            raise LoanProductNotFoundException()
        
        return product
    
    except (ValidationException, LoanProductNotFoundException):
        raise
    except Exception as e:
        raise AppException(
            f"Failed to retrieve loan product: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.put("/{product_id}", response_model=LoanProductResponse)
def update_loan_product(
    product_id: str,
    product_update: LoanProductUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)  
):
    """Update a loan product (Admin only)"""
    try:
        try:
            product_uuid = uuid.UUID(product_id)
        except ValueError:
            raise ValidationException("Invalid product ID format")
        
        db_product = db.query(LoanProduct).filter(LoanProduct.id == product_uuid).first()
        
        if not db_product:
            raise LoanProductNotFoundException()
        
        if product_update.name and product_update.name != db_product.name:
            existing = db.query(LoanProduct).filter(LoanProduct.name == product_update.name).first()
            if existing:
                raise LoanProductAlreadyExistsException(product_update.name)
        
        update_data = product_update.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(db_product, field, value)
        
        db.commit()
        db.refresh(db_product)
        
        return db_product
    
    except (ValidationException, LoanProductNotFoundException, LoanProductAlreadyExistsException):
        raise
    except Exception as e:
        db.rollback()
        raise AppException(
            f"Failed to update loan product: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.patch("/{product_id}/activate", response_model=LoanProductResponse)
def activate_loan_product(
    product_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)  
):
    """Activate a loan product (Admin only)"""
    try:
        try:
            product_uuid = uuid.UUID(product_id)
        except ValueError:
            raise ValidationException("Invalid product ID format")
        
        db_product = db.query(LoanProduct).filter(LoanProduct.id == product_uuid).first()
        
        if not db_product:
            raise LoanProductNotFoundException()
        
        db_product.status = "ACTIVE"
        db.commit()
        db.refresh(db_product)
        
        return db_product
    except (ValidationException, LoanProductNotFoundException):
        raise
    except Exception as e:
        db.rollback()
        raise AppException(
            f"Failed to activate loan product: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.patch("/{product_id}/deactivate", response_model=LoanProductResponse)
def deactivate_loan_product(
    product_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin) 
):
    """Deactivate a loan product (Admin only)"""
    try:
        try:
            product_uuid = uuid.UUID(product_id)
        except ValueError:
            raise ValidationException("Invalid product ID format")
        
        db_product = db.query(LoanProduct).filter(LoanProduct.id == product_uuid).first()
        
        if not db_product:
            raise LoanProductNotFoundException()
        
        db_product.status = "INACTIVE"
        db.commit()
        db.refresh(db_product)
        
        return db_product
    except (ValidationException, LoanProductNotFoundException):
        raise
    except Exception as e:
        db.rollback()
        raise AppException(
            f"Failed to deactivate loan product: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )