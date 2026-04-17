"""
Micro Lending Platform - Main Application Entry Point

"""
import sys
import os
import logging
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


# Local application imports - Core
from app.core.database import engine, Base, get_db
from app.core.exceptions import (
    AppException,
    OTPException,
    ValidationException,
    OTPExpiredException,
    OTPInvalidException,
    OTPSendLimitException,
    BankAccountNotFoundException,
    BankAccountAlreadyExistsException,
    BankAccountLimitExceededException,
    PrimaryBankAccountException,
    BankAccountVerificationException,
    LoanProductAlreadyExistsException,
    LoanProductNotFoundException,
    LoanProductValidationException,
    app_exception_handler,
    validation_exception_handler,
    integrity_error_handler,
    sqlalchemy_error_handler,
    generic_exception_handler,
    AuthenticationException,
    UserNotFoundException,
    UserInactiveException
)

# Local application imports - Routers
from app.api.routes import (
    otp, auth, user_profile, address, borrower, 
    lender, loan_offer, loan_application, kyc,
    registration, bank_accounts, loan_products
)
from app.api.routes.transaction import router as transaction_router
from app.api.routes.loan import router as loan_router


app = FastAPI(
    title="Micro Lending Platform",
    description="API for connecting borrowers with lenders",
    version="1.0.0"
)

# OTP Exceptions
app.add_exception_handler(OTPExpiredException, app_exception_handler)
app.add_exception_handler(OTPInvalidException, app_exception_handler)
app.add_exception_handler(OTPSendLimitException, app_exception_handler)
app.add_exception_handler(OTPException, app_exception_handler)

# Auth Exceptions
app.add_exception_handler(AuthenticationException, app_exception_handler)
app.add_exception_handler(UserNotFoundException, app_exception_handler)
app.add_exception_handler(UserInactiveException, app_exception_handler)

# Bank Account Exceptions
app.add_exception_handler(BankAccountNotFoundException, app_exception_handler)
app.add_exception_handler(BankAccountAlreadyExistsException, app_exception_handler)
app.add_exception_handler(BankAccountLimitExceededException, app_exception_handler)
app.add_exception_handler(PrimaryBankAccountException, app_exception_handler)
app.add_exception_handler(BankAccountVerificationException, app_exception_handler)

# Loan Product Exceptions
app.add_exception_handler(LoanProductNotFoundException, app_exception_handler)
app.add_exception_handler(LoanProductAlreadyExistsException, app_exception_handler)
app.add_exception_handler(LoanProductValidationException, app_exception_handler)

# General Exceptions
app.add_exception_handler(ValidationException, app_exception_handler)
app.add_exception_handler(AppException, app_exception_handler)

# Framework Exceptions
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(IntegrityError, integrity_error_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)
app.add_exception_handler(Exception, generic_exception_handler)



app.include_router(registration.router)
app.include_router(otp.router)
app.include_router(auth.router)
app.include_router(user_profile.router) 
app.include_router(address.router)
app.include_router(borrower.router)
app.include_router(lender.router)
app.include_router(kyc.router)
app.include_router(bank_accounts.router)
app.include_router(loan_products.router)
app.include_router(loan_offer.router)
app.include_router(loan_application.router)
app.include_router(loan_router)
app.include_router(transaction_router)


# ---------- Root Endpoints ----------
@app.get("/")
def root():
    return {
        "message": "Welcome to Micro Lending Platform API",
        "docs": "/docs",
        "redoc": "/redoc"
    }

# Set up logging to file
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('error.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )