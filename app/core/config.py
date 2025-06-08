import os
import stripe # Import stripe
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./roamstop.db")
SQLALCHEMY_DATABASE_URI = DATABASE_URL

# JWT Settings
SECRET_KEY: str = os.getenv("SECRET_KEY", "a_very_secret_key_that_should_be_in_env_file_and_much_stronger") # In a real app, use a strong, randomly generated key
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

# Stripe API Keys
STRIPE_PUBLISHABLE_KEY: str = os.getenv("STRIPE_PUBLISHABLE_KEY", "pk_test_YOUR_STRIPE_PUBLISHABLE_KEY")
STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "sk_test_YOUR_STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_YOUR_STRIPE_WEBHOOK_SECRET")

# Initialize Stripe API key
if STRIPE_SECRET_KEY and "YOUR_STRIPE_SECRET_KEY" not in STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
else:
    # Optionally log a warning if the key is a placeholder or not set,
    # but avoid logging the key itself.
    print("WARNING: Stripe secret key is not configured or is using a placeholder value.")
