from app.core.database import engine, Base
from app.models import User, BankAccount,LoanProduct # Import all models

print("Creating database tables...")
Base.metadata.create_all(bind=engine)
print("✅ Tables created successfully!")