"""Models package - single source of imports"""

from .user import User, UserRole, UserStatus
from .bank_account import BankAccount, AccountType
from .loan_product import LoanProduct, LoanProductStatus, InterestType
from .otp import OTPVerification, OTPPurpose
from .user_profile import UserProfile, Gender, MaritalStatus
from .address import Address, AddressType
from .borrower_profile import BorrowerProfile, EmploymentType
from .lender_profile import LenderProfile, RiskAppetite, LenderStatus
from .loan_offer import LoanOffer, LoanOfferStatus
from .loan_application import LoanApplication, LoanApplicationStatus

__all__ = [
    'User', 'UserRole', 'UserStatus',
    'BankAccount', 'AccountType',
    'LoanProduct', 'LoanProductStatus', 'InterestType',
    'OTPVerification', 'OTPPurpose',
    'UserProfile', 'Gender', 'MaritalStatus',
    'Address', 'AddressType',
    'BorrowerProfile', 'EmploymentType',
    'LenderProfile', 'RiskAppetite', 'LenderStatus',
    'LoanOffer', 'LoanOfferStatus',
    'LoanApplication', 'LoanApplicationStatus'
]