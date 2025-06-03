import pytest
from fastapi.testclient import TestClient
import uuid

# from app.schemas.reseller import ResellerCreate # Not directly used if constructing dicts
# from app.crud import crud_reseller # For pre-populating data if needed via CRUD

# Tests are marked with @pytest.mark.api to be potentially filtered later
pytestmark = pytest.mark.api


def test_register_reseller_success(client: TestClient):
    unique_email = f"testuser_{uuid.uuid4().hex[:8]}@example.com"
    reseller_data = {
        "email": unique_email,
        "password": "testpassword123",
        "reseller_type": "MOBILE_FIELD"
    }
    response = client.post("/api/v1/resellers/register", json=reseller_data)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == reseller_data["email"]
    assert "id" in data
    assert data["is_active"] is True
    assert "hashed_password" not in data  # Ensure password is not returned

def test_register_reseller_duplicate_email(client: TestClient, db_session): # db_session to ensure clean DB state
    # For this test, db_session fixture ensures the DB is clean before this test runs.
    # So, the first registration within this test will be unique for this test's scope.
    duplicate_email = f"test_dup_{uuid.uuid4().hex[:8]}@example.com"
    reseller_data = {
        "email": duplicate_email,
        "password": "testpassword123",
        "reseller_type": "MOBILE_FIELD"
    }
    # First registration
    response1 = client.post("/api/v1/resellers/register", json=reseller_data)
    assert response1.status_code == 201

    # Attempt duplicate registration
    response2 = client.post("/api/v1/resellers/register", json=reseller_data)
    assert response2.status_code == 400
    # Updated detail message check based on the API implementation
    assert response2.json()["detail"] == "The reseller with this email already exists in the system."


def test_login_success(client: TestClient, db_session): # db_session for clean state
    login_email = f"login_test_{uuid.uuid4().hex[:8]}@example.com"
    login_password = "testpassword123"

    # Register user first
    client.post(
        "/api/v1/resellers/register",
        json={"email": login_email, "password": login_password, "reseller_type": "VENUE_PARTNER"}
    )

    login_data = {"username": login_email, "password": login_password}
    response = client.post("/api/v1/auth/login", data=login_data) # form data for OAuth2PasswordRequestForm

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_failure_wrong_password(client: TestClient, db_session): # db_session for clean state
    user_email = f"wrongpass_{uuid.uuid4().hex[:8]}@example.com"
    correct_password = "realpassword"
    wrong_password = "fakepassword"

    # Register user
    client.post(
        "/api/v1/resellers/register",
        json={"email": user_email, "password": correct_password, "reseller_type": "MOBILE_FIELD"}
    )

    # Attempt login with wrong password
    response = client.post(
        "/api/v1/auth/login",
        data={"username": user_email, "password": wrong_password}
    )
    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Incorrect email or password"

def test_login_failure_user_not_exist(client: TestClient): # No db_session needed if user never existed
    non_existent_email = f"nonexistent_{uuid.uuid4().hex[:8]}@example.com"
    response = client.post(
        "/api/v1/auth/login",
        data={"username": non_existent_email, "password": "somepassword"}
    )
    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Incorrect email or password"

def test_register_reseller_with_recruiter_success(client: TestClient, db_session):
    recruiter_email = f"recruiter_{uuid.uuid4().hex[:8]}@example.com"
    recruit_email = f"recruit_{uuid.uuid4().hex[:8]}@example.com"

    # 1. Register Recruiter
    recruiter_data = {"email": recruiter_email, "password": "password123", "reseller_type": "MOBILE_FIELD"}
    response_recruiter = client.post("/api/v1/resellers/register", json=recruiter_data)
    assert response_recruiter.status_code == 201
    recruiter_id = response_recruiter.json()["id"]

    # 2. Register Recruit with recruiter_id
    recruit_data = {
        "email": recruit_email,
        "password": "newpassword123",
        "reseller_type": "VENUE_PARTNER",
        "recruiter_id": recruiter_id
    }
    response_recruit = client.post("/api/v1/resellers/register", json=recruit_data)
    assert response_recruit.status_code == 201
    data_recruit = response_recruit.json()
    assert data_recruit["email"] == recruit_email
    assert data_recruit["recruiter_id"] == recruiter_id

def test_register_reseller_with_nonexistent_recruiter(client: TestClient, db_session):
    recruit_email = f"recruit_fail_{uuid.uuid4().hex[:8]}@example.com"
    non_existent_recruiter_id = 99999

    recruit_data = {
        "email": recruit_email,
        "password": "newpassword123",
        "reseller_type": "VENUE_PARTNER",
        "recruiter_id": non_existent_recruiter_id
    }
    response_recruit = client.post("/api/v1/resellers/register", json=recruit_data)
    assert response_recruit.status_code == 404 # As per current endpoint logic
    assert response_recruit.json()["detail"] == f"Recruiter with id {non_existent_recruiter_id} not found."
