import os
from dotenv import load_dotenv

load_dotenv()  # take environment variables from .env file if available

class Settings:
    PROJECT_NAME: str = "blog-api"
    SQLITE_URL: str = os.getenv("SQLITE_URL", "sqlite+aiosqlite:///./blog.db")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

settings = Settings()
