from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os
from urllib.parse import quote_plus

load_dotenv()

class Settings(BaseSettings):
    # App
    APP_NAME: str = os.getenv("APP_NAME", "Micro Lending Platform")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "True") == "True"
    
    # Database
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "micro_lending_db")
    
    # Hardcoded working URL
    DATABASE_URL: str = "postgresql://postgres:root@localhost:5432/micro_lending_db"

settings = Settings()