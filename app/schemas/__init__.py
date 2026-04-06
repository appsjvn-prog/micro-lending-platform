# Only import what's absolutely necessary for other modules
from app.schemas.user import (
    UserBase, UserCreate, UserUpdate, UserResponse,
    UserRegisterRequest, SetPasswordRequest,  # Add these
    UserAdminListResponse, UserAdminDetailResponse,
    PhoneNumber
)
from app.schemas.bank_account import (
    BankAccountBase, BankAccountCreate, BankAccountUpdate, 
    BankAccountResponse, BankAccountVerify
)
from app.schemas.loan_product import (
    LoanProductBase, LoanProductCreate, LoanProductUpdate, LoanProductResponse
)
from app.schemas.otp import (
    OTPVerifyRequest, OTPResendRequest,
    OTPSendResponse, OTPVerifyResponse, OTPPurpose
)