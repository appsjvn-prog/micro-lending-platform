from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

class AppException(Exception):
    """Base application exception"""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code

# 👇 ADD THESE SPECIFIC EXCEPTIONS
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
            status_code=status.HTTP_400_BAD_REQUEST
        )

async def app_exception_handler(request: Request, exc: AppException):
    """Handle custom app exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.message,
            "error_code": exc.__class__.__name__
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append(f"{field}: {error['msg']}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Validation error",
            "errors": errors
        }
    )

async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Handle database integrity errors"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "message": "Data integrity error. This record may already exist.",
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