import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient
import os

# Add project root to sys.path to allow imports from app
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from app.main import app
from app.db.base_class import Base
from app.db.session import get_db
# We will use the actual DATABASE_URL from config for now,
# but ideally, this should point to a separate test database.
# For simplicity in this exercise, we use a file-based SQLite DB.
# If your config already points to a suitable test DB, that's fine.
# from app.core.config import SQLALCHEMY_DATABASE_URI

# Use a separate SQLite database for testing
TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    TEST_SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Apply migrations to the test database (or create all tables)
# This ensures the test DB has the latest schema
# For a more robust setup, you might run Alembic migrations here
Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session")
def test_engine():
    # Create tables if they don't exist.
    # This is a simplified setup. For more complex scenarios,
    # you might manage migrations with Alembic.
    Base.metadata.create_all(bind=engine)
    yield engine
    # Optional: cleanup after tests if needed, though test.db can be deleted manually
    # Base.metadata.drop_all(bind=engine) # Or os.remove("./test.db") if it's a file

@pytest.fixture(scope="function")
def db_session(test_engine):
    """
    Provides a database session for each test function.
    It also cleans up (drops and recreates) tables for each test
    to ensure test isolation.
    """
    # Drop and recreate tables for each test function for isolation
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine) # Ensures schema is fresh for each test

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
    # Commits made within the test (e.g., by CRUD functions) will be effective
    # for API calls made via TestClient within that same test.
    # The drop_all() at the beginning of the fixture ensures isolation between tests.


@pytest.fixture(scope="function") # Changed client to function scope for better isolation
def client():
    # The TestClient uses the app with the overridden get_db dependency
    with TestClient(app) as c:
        yield c

import uuid
from app.crud import crud_reseller
from app.schemas.reseller import ResellerCreate
from app.models.reseller import ResellerProfile as ResellerModel
from app.core.security import create_access_token, verify_password # Added verify_password
from app.models.product import ProductPackage as ProductPackageModel
from app.schemas.product import ProductPackageCreate as ProductPackageCreateSchema
from app.crud import crud_product
from decimal import Decimal

# Helper function to create a reseller and get token
def _create_reseller_and_get_token(db: Session, client: TestClient, is_superuser: bool = False):
    unique_suffix = uuid.uuid4().hex[:6]
    email = f"testuser_{'super_' if is_superuser else ''}{unique_suffix}@example.com"
    password = "testpassword123"

    reseller_in = ResellerCreate(
        email=email,
        password=password,
        reseller_type="TEST_TYPE",
        is_superuser=is_superuser
    )
    # Ensure user doesn't exist, or handle appropriately for tests
    existing_user = crud_reseller.get_reseller_by_email(db, email=email)
    if existing_user:
        # This can happen if db_session fixture is not cleaning up properly or if email is not unique enough
        # For now, let's assume db_session cleans up, or we could delete/update existing
        # For simplicity, we'll raise an error if this happens during fixture setup, implying a test setup issue
        raise Exception(f"User {email} already exists during fixture setup. Ensure test isolation.")

    user_created = crud_reseller.create_reseller(db=db, obj_in=reseller_in)
    db.commit() # Ensure commit before trying to fetch again

    # Introduce a small delay to help with potential DB visibility issues in tests
    import time
    time.sleep(0.05) # 50 milliseconds, adjust if needed

    # Debugging password verification
    # Fetch the user again, like the login endpoint would
    user_from_db_for_check = crud_reseller.get_reseller_by_email(db, email=email)
    if not user_from_db_for_check:
        raise Exception(f"User {email} not found in DB after creation for verification.")

    print(f"User created: {user_created.email}, Hashed Pwd on created obj: {user_created.hashed_password}")
    print(f"User fetched: {user_from_db_for_check.email}, Hashed Pwd in DB: {user_from_db_for_check.hashed_password}")

    is_password_correct_on_created_obj = verify_password(password, user_created.hashed_password)
    print(f"Verification on created obj for {user_created.email} with '{password}': {is_password_correct_on_created_obj}")

    is_password_correct_on_fetched_obj = verify_password(password, user_from_db_for_check.hashed_password)
    print(f"Verification on fetched obj for {user_from_db_for_check.email} with '{password}': {is_password_correct_on_fetched_obj}")

    # Login to get token
    login_data = {"username": email, "password": password}
    response = client.post("/api/v1/auth/login", data=login_data)
    if response.status_code != 200:
        print(f"Login failed for {email}. Response: {response.text}") # More detailed log
        raise Exception(f"Failed to log in user {email} during fixture setup. Status: {response.status_code}, Detail: {response.text}")

    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return headers, user_created # Return the initially created user object

@pytest.fixture(scope="function") # Changed to function scope
def normal_user_token_headers(db_session: Session, client: TestClient):
    # Uses function-scoped db_session
    return _create_reseller_and_get_token(db_session, client, is_superuser=False)

@pytest.fixture(scope="function") # Changed to function scope
def superuser_token_headers(db_session: Session, client: TestClient):
    # Uses function-scoped db_session
    return _create_reseller_and_get_token(db_session, client, is_superuser=True)

@pytest.fixture(scope="function") # Changed to function scope
def test_normal_user(normal_user_token_headers: tuple): # db_session implicitly used by normal_user_token_headers
    return normal_user_token_headers[1]

@pytest.fixture(scope="function") # Changed to function scope
def test_superuser(superuser_token_headers: tuple): # db_session implicitly used by superuser_token_headers
    return superuser_token_headers[1]


# Fixture for db_session with module scope, for module-scoped fixtures that need DB access
# This is no longer needed if all user fixtures are function-scoped
# @pytest.fixture(scope="module")
# def db_session_module(test_engine):
#     Base.metadata.drop_all(bind=test_engine) # Clean once before module tests
#     Base.metadata.create_all(bind=test_engine)
#     connection = test_engine.connect()
#     trans = connection.begin()
#     session = TestingSessionLocal(bind=connection)
#     yield session
#     session.close()
#     trans.rollback()
#     connection.close()
#     Base.metadata.drop_all(bind=test_engine) # Clean once after module tests


@pytest.fixture(scope="function")
def test_product(db_session: Session) -> ProductPackageModel:
    product_in = ProductPackageCreateSchema(
        name=f"Test Product {uuid.uuid4().hex[:6]}",
        description="A great test product",
        duration_days=30,
        country_code="US",
        price=Decimal("19.99"),
        direct_commission_rate_or_amount=Decimal("2.50"),
        recruitment_commission_rate_or_amount=Decimal("1.00"),
        is_active=True
    )
    return crud_product.create_product(db=db_session, obj_in=product_in)

# Helper function to create a recruited reseller
def create_recruited_reseller(db: Session, recruiter: ResellerModel) -> ResellerModel:
    email = f"recruited_{uuid.uuid4().hex[:6]}@example.com"
    password = "password123" # Standard password for test users
    reseller_in = ResellerCreate(
        email=email,
        password=password,
        reseller_type="MOBILE_FIELD", # Example type
        recruiter_id=recruiter.id,
        is_superuser=False # Recruited users are not superusers by default
    )
    return crud_reseller.create_reseller(db=db, obj_in=reseller_in)
