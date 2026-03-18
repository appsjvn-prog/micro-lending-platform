"""Routes package"""
from . import otp
from . import auth
from . import user_profile
from . import address
from . import borrower
from . import lender
from . import loan_offer
from . import loan_application

__all__ = [
    'otp', 'auth', 'user_profile', 'address', 
    'borrower', 'lender', 'loan_offer', 'loan_application'
]