import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./roamstop.db")
SQLALCHEMY_DATABASE_URI = DATABASE_URL

# JWT Settings
SECRET_KEY: str = os.getenv("SECRET_KEY", "a_very_secret_key_that_should_be_in_env_file_and_much_stronger") # In a real app, use a strong, randomly generated key
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
