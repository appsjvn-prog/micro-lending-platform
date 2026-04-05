# Micro Lending Platform API

A peer-to-peer lending platform connecting borrowers with lenders. Built with FastAPI, SQLAlchemy, and PostgreSQL.

## Features

- **User Registration** with OTP verification (SMS)
- **Role-based Access** (Admin, Lender, Borrower)
- **Bank Account Management** (Add, verify, set primary)
- **Loan Products** (Admin configurable)
- **Loan Offers** (Lenders create custom offers)
- **Loan Applications** (Borrowers apply with validation)
- **Flexible Repayment** (Any amount, auto-allocated to oldest EMIs)
- **Transaction History** (Complete audit trail)
- **KYC Document Verification**

## Tech Stack

| Category | Technology |
|----------|------------|
| Framework | FastAPI |
| ORM | SQLAlchemy |
| Database | PostgreSQL |
| Validation | Pydantic |
| Auth | JWT |
| Password | bcrypt |

## Quick Start

### Prerequisites
- Python 3.9+
- PostgreSQL 14+

### Installation

```bash
# Clone repository
git clone https://github.com/appsjvn/micro-lending-platform.git
cd micro-lending-platform

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your database URL

# Create database
createdb lending_db

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload
