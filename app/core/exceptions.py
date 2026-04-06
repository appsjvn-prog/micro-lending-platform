# app/core/exceptions.py

from fastapi import Request, status
from decimal import Decimal
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

# ==================== BASE EXCEPTION ====================

class AppException(Exception):
    """Base application exception"""
    def __init__(self, message: str, status_code: int = 400, error_code: str = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__

# ==================== EXISTING EXCEPTIONS (KEEP THESE) ====================

class NotFoundException(AppException):
    def __init__(self, resource: str):
        super().__init__(
            message=f"{resource} not found",
            status_code=status.HTTP_404_NOT_FOUND
        )

class UnauthorizedException(AppException):
    def __init__(self, action: str = "perform this action"):
        super().__init__(
            message=f"You are not authorized to {action}",
            status_code=status.HTTP_403_FORBIDDEN
        )

class ValidationException(AppException):
    def __init__(self, message: str):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="VALIDATION_ERROR"
        )

# ==================== NEW EXCEPTIONS FOR YOUR USE CASE ====================

class AuthenticationException(AppException):
    """For login failures, invalid tokens"""
    def __init__(self, message: str = "Invalid credentials", status_code: int = 401):
        super().__init__(
            message=message,
            status_code=status_code,
            error_code="AUTHENTICATION_FAILED"
        )

class DuplicateResourceException(AppException):
    """For duplicate email, phone, etc."""
    def __init__(self, resource: str, field: str, value: str):
        super().__init__(
            message=f"{resource} '{value}' already exists",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="DUPLICATE_RESOURCE"
        )

class UserNotFoundException(NotFoundException):
    """Specific user not found"""
    def __init__(self, user_id=None, email=None):
        if user_id:
            super().__init__(f"User with ID {user_id}")
        elif email:
            super().__init__(f"User with email {email}")
        else:
            super().__init__("User")

class UserInactiveException(AppException):
    """When user account is inactive"""
    def __init__(self, user_id=None):
        message = "Your account is inactive. Please verify your email/phone first."
        if user_id:
            message = f"User account is inactive. Please verify your account."
        super().__init__(
            message=message,
            status_code=403,
            error_code="USER_INACTIVE"
        )

class AdminCreationException(AppException):
    """When someone tries to create admin account"""
    def __init__(self):
        super().__init__(
            message="Admin accounts cannot be created via signup",
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="ADMIN_CREATION_NOT_ALLOWED"
        )

class OTPException(AppException):
    """For OTP-related errors"""
    def __init__(self, message: str,status_code: int = 400, error_code: str = None):
        super().__init__(
            message=message,
            status_code=status_code,
            error_code=error_code or "OTP_ERROR"
        )

class OTPExpiredException(OTPException):
    def __init__(self):
        super().__init__(
            message = "OTP has expired. Please request a new one.",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="OTP_EXPIRED"
            )

class OTPInvalidException(OTPException):
    def __init__(self):
        super().__init__(
            message = "Invalid OTP code. Please try again.",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="OTP_INVALID"
        )

class OTPSendLimitException(OTPException):
    def __init__(self, wait_minutes: int = 2):
        super().__init__(
            message=f"Too many OTP requests. Please try again in {wait_minutes} minutes.",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="OTP_RATE_LIMIT"
        )

class TokenException(AppException):
    """For token-related errors"""
    def __init__(self, message: str = "Invalid or expired token"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="TOKEN_ERROR"
        )

class InvalidTokenException(AppException):
    """For invalid or expired tokens"""
    def __init__(self, message: str = "Invalid or expired token"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="INVALID_TOKEN"
        )

class TokenExpiredException(TokenException):
    def __init__(self):
        super().__init__("Token has expired. Please login again.")

class PasswordSetupException(AppException):
    """For password setup errors"""
    def __init__(self, message: str):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="PASSWORD_SETUP_ERROR"
        )

class UserAlreadyActiveException(AppException):
    """When user is already active"""
    def __init__(self):
        super().__init__(
            message="User is already active. Please login.",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="USER_ALREADY_ACTIVE"
        )

class ProfileNotFoundException(NotFoundException):
    """Profile not found exception"""
    def __init__(self):
        super().__init__("User profile")
        self.error_code = "PROFILE_NOT_FOUND"

class ProfileAlreadyExistsException(AppException):
    """Profile already exists exception"""
    def __init__(self):
        super().__init__(
            message="User profile already exists. Use update instead.",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="PROFILE_ALREADY_EXISTS"
        )

class ProfilePhoneMismatchException(ValidationException):
    """Phone number mismatch exception"""
    def __init__(self):
        super().__init__(
            message="Primary phone number must match the registered phone number"
        )
        self.error_code = "PROFILE_PHONE_MISMATCH"

class ProfileEmailMismatchException(ValidationException):
    def __init__(self):
        super().__init__(
            message="Profile email must match your registered email address"
        )
        self.error_code = "EMAIL_MISMATCH"

class DuplicateAddressException(AppException):
    """When user tries to create duplicate address"""
    def __init__(self):
        super().__init__(
            message="You already have this address. Please update existing address instead.",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="DUPLICATE_ADDRESS"
        )

class AddressNotFoundException(NotFoundException):
    """Address not found exception"""
    def __init__(self):
        super().__init__("Address")
        self.error_code = "ADDRESS_NOT_FOUND"

class AddressLimitExceededException(AppException):
    """Address limit exceeded exception"""
    def __init__(self, limit: int = 5):
        super().__init__(
            message=f"Maximum {limit} addresses allowed per user",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="ADDRESS_LIMIT_EXCEEDED"
        )

class PrimaryAddressException(AppException):
    """Primary address related exceptions"""
    def __init__(self, message: str):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="PRIMARY_ADDRESS_ERROR"
        )

class AddressValidationException(ValidationException):
    """Address validation exceptions"""
    def __init__(self, message: str):
        super().__init__(message)
        self.error_code = "ADDRESS_VALIDATION_ERROR"

class ProfileRequiredException(AppException):
    """Profile required exception"""
    def __init__(self):
        super().__init__(
            message="Please create your user profile before adding addresses",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="PROFILE_REQUIRED"
        )

class LenderProfileNotFoundException(NotFoundException):
    """Lender profile not found exception"""
    def __init__(self):
        super().__init__("Lender profile")
        self.error_code = "LENDER_PROFILE_NOT_FOUND"

class KYCNotFoundException(NotFoundException):
    """KYC not found exception"""
    def __init__(self):
        super().__init__("KYC record")
        self.error_code = "KYC_NOT_FOUND"


class KYCAlreadyExistsException(AppException):
    """KYC already submitted exception"""
    def __init__(self):
        super().__init__(
            message="KYC already submitted for this user",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="KYC_ALREADY_EXISTS"
        )


class KYCAlreadyVerifiedException(AppException):
    """KYC already verified exception"""
    def __init__(self):
        super().__init__(
            message="KYC already verified",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="KYC_ALREADY_VERIFIED"
        )


class KYCDocumentNotFoundException(NotFoundException):
    """KYC document not found exception"""
    def __init__(self):
        super().__init__("KYC document")
        self.error_code = "KYC_DOCUMENT_NOT_FOUND"


class KYCDocumentAlreadyExistsException(AppException):
    """Document already uploaded exception"""
    def __init__(self, doc_type: str):
        super().__init__(
            message=f"{doc_type} document already uploaded and pending verification",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="KYC_DOCUMENT_ALREADY_EXISTS"
        )

class KYCNotSubmittedException(AppException):
    """KYC not submitted before uploading documents"""
    def __init__(self):
        super().__init__(
            message="Please submit KYC request before uploading documents",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="KYC_NOT_SUBMITTED"
        )

class BankAccountNotFoundException(NotFoundException):
    """Bank account not found exception"""
    def __init__(self):
        super().__init__("Bank account")
        self.error_code = "BANK_ACCOUNT_NOT_FOUND"


class BankAccountAlreadyExistsException(AppException):
    """Bank account already exists exception"""
    def __init__(self):
        super().__init__(
            message="Bank account with this number already registered",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="BANK_ACCOUNT_ALREADY_EXISTS"
        )


class BankAccountLimitExceededException(AppException):
    """Bank account limit exceeded exception"""
    def __init__(self, limit: int = 5):
        super().__init__(
            message=f"Maximum {limit} bank accounts allowed per user",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="BANK_ACCOUNT_LIMIT_EXCEEDED"
        )


class PrimaryBankAccountException(AppException):
    """Primary bank account related exceptions"""
    def __init__(self, message: str):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="PRIMARY_BANK_ACCOUNT_ERROR"
        )


class BankAccountVerificationException(AppException):
    """Bank account verification exceptions"""
    def __init__(self, message: str):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="BANK_ACCOUNT_VERIFICATION_ERROR"
        )

class LoanProductNotFoundException(NotFoundException):
    """Loan product not found exception"""
    def __init__(self):
        super().__init__("Loan product")
        self.error_code = "LOAN_PRODUCT_NOT_FOUND"


class LoanProductAlreadyExistsException(AppException):
    """Loan product name already exists exception"""
    def __init__(self, name: str):
        super().__init__(
            message=f"Loan product with name '{name}' already exists",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="LOAN_PRODUCT_ALREADY_EXISTS"
        )


class LoanProductInvalidStatusException(AppException):
    """Invalid loan product status exception"""
    def __init__(self, status: str):
        super().__init__(
            message=f"Invalid loan product status: {status}",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="LOAN_PRODUCT_INVALID_STATUS"
        )


class LoanProductValidationException(ValidationException):
    """Loan product validation exception"""
    def __init__(self, message: str):
        super().__init__(message)
        self.error_code = "LOAN_PRODUCT_VALIDATION_ERROR"

class LoanOfferNotFoundException(NotFoundException):
    """Loan offer not found exception"""
    def __init__(self):
        super().__init__("Loan offer")
        self.error_code = "LOAN_OFFER_NOT_FOUND"


class LoanOfferAlreadyExistsException(AppException):
    """Loan offer already exists exception"""
    def __init__(self, name: str):
        super().__init__(
            message=f"Loan offer with name '{name}' already exists",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="LOAN_OFFER_ALREADY_EXISTS"
        )


class LoanOfferExpiredException(AppException):
    """Loan offer expired exception"""
    def __init__(self):
        super().__init__(
            message="Loan offer has expired",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="LOAN_OFFER_EXPIRED"
        )


class LoanOfferInactiveException(AppException):
    """Loan offer inactive exception"""
    def __init__(self):
        super().__init__(
            message="Loan offer is inactive",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="LOAN_OFFER_INACTIVE"
        )

class LoanApplicationNotFoundException(NotFoundException):
    """Loan application not found exception"""
    def __init__(self):
        super().__init__("Loan application")
        self.error_code = "LOAN_APPLICATION_NOT_FOUND"


class LoanApplicationAlreadyExistsException(AppException):
    """Loan application already exists exception"""
    def __init__(self):
        super().__init__(
            message="You already have a pending application for this offer",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="LOAN_APPLICATION_ALREADY_EXISTS"
        )


class LoanApplicationInvalidStatusException(ValidationException):
    """Invalid loan application status exception"""
    def __init__(self, current_status: str, allowed_statuses: list):
        super().__init__(
            message=f"Cannot update application with status {current_status}. Allowed: {', '.join(allowed_statuses)}"
        )
        self.error_code = "LOAN_APPLICATION_INVALID_STATUS"


class LoanApplicationAlreadyReviewedException(AppException):
    """Loan application already reviewed exception"""
    def __init__(self):
        super().__init__(
            message="This application has already been reviewed",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="LOAN_APPLICATION_ALREADY_REVIEWED"
        )

class TransactionNotFoundException(NotFoundException):
    """Transaction not found exception"""
    def __init__(self):
        super().__init__("Transaction")
        self.error_code = "TRANSACTION_NOT_FOUND"


class InsufficientBalanceException(AppException):
    """Insufficient balance exception"""
    def __init__(self, required: Decimal, available: Decimal):
        super().__init__(
            message=f"Insufficient balance. Required: ₹{required}, Available: ₹{available}",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="INSUFFICIENT_BALANCE"
        )


class RepaymentValidationException(ValidationException):
    """Repayment validation exception"""
    def __init__(self, message: str):
        super().__init__(message)
        self.error_code = "REPAYMENT_VALIDATION_ERROR"


class LoanNotDisbursedException(AppException):
    """Loan not disbursed exception"""
    def __init__(self):
        super().__init__(
            message="Loan has not been disbursed yet",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="LOAN_NOT_DISBURSED"
        )
# ==================== EXCEPTION HANDLERS ====================

async def app_exception_handler(request: Request, exc: AppException):
    """Handle custom app exceptions"""
    print(f"🔴 app_exception_handler called with: {type(exc).__name__}")
    print(f"   Status: {exc.status_code}, Message: {exc.message}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.message,
            "error_code": exc.error_code,
            "status_code": exc.status_code
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error['msg'],
            "type": error['type']
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Validation error",
            "error_code": "VALIDATION_ERROR",
            "errors": errors
        }
    )

async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Handle database integrity errors"""
    error_message = "Data integrity error"
    error_str = str(exc).lower()
    
    if "email" in error_str:
        error_message = "A user with this email already exists"
    elif "phone" in error_str or "national_number" in error_str:
        error_message = "A user with this phone number already exists"
    elif "unique_phone" in error_str:
        error_message = "This phone number is already registered"
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "message": error_message,
            "error_code": "DUPLICATE_ENTRY"
        }
    )

async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    """Handle database errors"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Database error occurred. Please try again later.",
            "error_code": "DATABASE_ERROR"
        }
    )

async def generic_exception_handler(request: Request, exc: Exception):
    """Handle any unhandled exceptions"""
    print(f"🔴 GENERIC exception handler called with: {type(exc).__name__}")
    print(f"   Error: {str(exc)}")
    import traceback
    traceback.print_exc()
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "An unexpected error occurred",
            "error_code": "INTERNAL_SERVER_ERROR"
        }
    )