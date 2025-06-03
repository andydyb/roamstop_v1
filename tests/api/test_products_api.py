import pytest
from fastapi.testclient import TestClient
import uuid
from decimal import Decimal

from app.schemas.product import ProductPackageCreate, ProductPackageUpdate, ProductPackage as ProductPackageSchema
from app.crud import crud_product # For creating products to test against if needed for GET/PUT/DELETE
from app.models.product import ProductPackage as ProductPackageModel # Import the model for type hinting

pytestmark = pytest.mark.api

# Product data for tests
def get_valid_product_data(name_suffix: str = ""):
    return {
        "name": f"API Test Product {name_suffix} {uuid.uuid4().hex[:4]}",
        "description": "An amazing product tested via API.",
        "duration_days": 30,
        "country_code": "US",
        "price": "25.99", # FastAPI will convert to Decimal
        "direct_commission_rate_or_amount": "2.00",
        "recruitment_commission_rate_or_amount": "0.50",
        "is_active": True
    }

# --- Product Creation Tests (POST /products/) ---
def test_create_product_success_superuser(client: TestClient, superuser_token_headers: tuple):
    headers, _ = superuser_token_headers
    product_data = get_valid_product_data("superuser_create")
    response = client.post("/api/v1/products/", json=product_data, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == product_data["name"]
    assert data["price"] == product_data["price"] # Pydantic serializes Decimal to str
    assert data["is_active"] is True

def test_create_product_failure_normal_user(client: TestClient, normal_user_token_headers: tuple):
    headers, _ = normal_user_token_headers
    product_data = get_valid_product_data("normal_user_create_fail")
    response = client.post("/api/v1/products/", json=product_data, headers=headers)
    assert response.status_code == 403 # Forbidden

def test_create_product_failure_unauthenticated(client: TestClient):
    product_data = get_valid_product_data("unauth_create_fail")
    response = client.post("/api/v1/products/", json=product_data)
    assert response.status_code == 401 # Unauthorized

def test_create_product_invalid_data(client: TestClient, superuser_token_headers: tuple):
    headers, _ = superuser_token_headers
    invalid_data = get_valid_product_data("invalid_data")
    invalid_data["duration_days"] = -5 # Invalid
    response = client.post("/api/v1/products/", json=invalid_data, headers=headers)
    assert response.status_code == 422 # Unprocessable Entity

# --- Product Reading Tests (GET /products/ and GET /products/{product_id}) ---
def test_read_products_public_access(client: TestClient, db_session, superuser_token_headers): # Use superuser to create a product first
    # Create a product to ensure there's something to read
    headers_su, _ = superuser_token_headers
    client.post("/api/v1/products/", json=get_valid_product_data("public_read"), headers=headers_su)

    response = client.get("/api/v1/products/?is_active=true") # Public should only see active by default in API
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if data: # If other tests didn't clean up, or if this is the first product
      assert all(p["is_active"] for p in data if "is_active" in p)


def test_read_single_product_public(client: TestClient, test_product: ProductPackageModel): # test_product is active by default
    response = client.get(f"/api/v1/products/{test_product.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == test_product.name
    assert data["is_active"] is True

def test_read_inactive_product_public_fails_or_filters(client: TestClient, test_product: ProductPackageModel, db_session, superuser_token_headers):
    headers_su, _ = superuser_token_headers
    # Make product inactive using superuser
    client.put(f"/api/v1/products/{test_product.id}", json={"is_active": False}, headers=headers_su)

    response = client.get(f"/api/v1/products/{test_product.id}") # Public access
    # The API's read_product logic might return 404 if product is inactive and user is not superuser
    assert response.status_code == 404 # or it might return it if show_inactive is not correctly handled for public

def test_read_products_superuser_can_see_inactive(client: TestClient, test_product: ProductPackageModel, db_session, superuser_token_headers):
    headers_su, _ = superuser_token_headers
    # Make product inactive
    crud_product.update_product(db=db_session, db_obj=test_product, obj_in=ProductPackageUpdate(is_active=False))

    # Superuser requests specific inactive product
    response = client.get(f"/api/v1/products/{test_product.id}", headers=headers_su) # show_inactive defaults to False in API
    # The API read_product endpoint needs to check if user is superuser to show inactive, or take show_inactive param
    # Based on current API, it seems superuser will see it if it exists, regardless of show_inactive param in get_product CRUD
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    # Superuser requests list of products, can filter for inactive
    response_list = client.get("/api/v1/products/?is_active=false", headers=headers_su)
    assert response_list.status_code == 200
    assert any(p["id"] == test_product.id and not p["is_active"] for p in response_list.json())


def test_read_products_filter_country_code(client: TestClient, test_product: ProductPackageModel):
    # test_product has country_code "US"
    response = client.get(f"/api/v1/products/?country_code=US&is_active=true")
    assert response.status_code == 200
    assert any(p["id"] == test_product.id for p in response.json())

    response_wrong_country = client.get(f"/api/v1/products/?country_code=CA&is_active=true")
    assert response_wrong_country.status_code == 200
    assert not any(p["id"] == test_product.id for p in response_wrong_country.json())

def test_read_product_not_found(client: TestClient):
    response = client.get("/api/v1/products/99999")
    assert response.status_code == 404

# --- Product Update Tests (PUT /products/{product_id}) ---
def test_update_product_success_superuser(client: TestClient, test_product: ProductPackageModel, superuser_token_headers: tuple):
    headers, _ = superuser_token_headers
    update_data = {"name": "Super Updated Name", "price": "30.50"}
    response = client.put(f"/api/v1/products/{test_product.id}", json=update_data, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Super Updated Name"
    assert data["price"] == "30.50"

def test_update_product_failure_normal_user(client: TestClient, test_product: ProductPackageModel, normal_user_token_headers: tuple):
    headers, _ = normal_user_token_headers
    update_data = {"name": "Normal User Update Fail"}
    response = client.put(f"/api/v1/products/{test_product.id}", json=update_data, headers=headers)
    assert response.status_code == 403

def test_update_product_failure_unauthenticated(client: TestClient, test_product: ProductPackageModel):
    update_data = {"name": "Unauth Update Fail"}
    response = client.put(f"/api/v1/products/{test_product.id}", json=update_data)
    assert response.status_code == 401

def test_update_inactive_product_superuser(client: TestClient, test_product: ProductPackageModel, db_session, superuser_token_headers: tuple):
    headers, _ = superuser_token_headers
    # Make product inactive first
    crud_product.update_product(db=db_session, db_obj=test_product, obj_in=ProductPackageUpdate(is_active=False))

    update_data = {"description": "Updating an inactive product by SU"}
    response = client.put(f"/api/v1/products/{test_product.id}", json=update_data, headers=headers)
    assert response.status_code == 200
    assert response.json()["description"] == "Updating an inactive product by SU"
    assert response.json()["is_active"] is False # Should remain inactive unless explicitly set

# --- Product Deletion Tests (DELETE /products/{product_id}) ---
def test_delete_product_success_superuser(client: TestClient, test_product: ProductPackageModel, superuser_token_headers: tuple):
    headers, _ = superuser_token_headers
    response = client.delete(f"/api/v1/products/{test_product.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is False # Logical delete

    # Verify it's not publicly accessible as active
    public_response = client.get(f"/api/v1/products/{test_product.id}")
    assert public_response.status_code == 404 # or filtered by active status

def test_delete_product_failure_normal_user(client: TestClient, test_product: ProductPackageModel, normal_user_token_headers: tuple):
    headers, _ = normal_user_token_headers
    response = client.delete(f"/api/v1/products/{test_product.id}", headers=headers)
    assert response.status_code == 403

def test_delete_product_failure_unauthenticated(client: TestClient, test_product: ProductPackageModel):
    response = client.delete(f"/api/v1/products/{test_product.id}")
    assert response.status_code == 401

def test_delete_non_existent_product_superuser(client: TestClient, superuser_token_headers: tuple):
    headers, _ = superuser_token_headers
    response = client.delete("/api/v1/products/999888", headers=headers)
    assert response.status_code == 404
