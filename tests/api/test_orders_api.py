import pytest
from fastapi.testclient import TestClient
import uuid
from decimal import Decimal
from sqlalchemy.orm import Session # Import Session

from app.schemas.order import OrderCreate, OrderUpdate, Order as OrderSchema, OrderCreateInternal
from app.schemas.product import ProductPackageUpdate, ProductPackageCreate
from app.schemas.reseller import ResellerCreate
from app.crud import crud_order, crud_reseller, crud_product, crud_commission # Added crud_commission
from app.models.product import ProductPackage
from app.models.reseller import ResellerProfile
from app.models.reseller import ResellerProfile as ResellerModel # Explicit import for the alias
from app.models.order import Order as OrderModel


pytestmark = pytest.mark.api

# --- Order Creation (POST /orders/) ---
def test_create_order_success_normal_user(
    client: TestClient, normal_user_token_headers: tuple, test_product: ProductPackage, db_session
):
    headers, normal_user = normal_user_token_headers
    order_data = {
        "customer_email": f"customer_{uuid.uuid4().hex[:6]}@example.com",
        "customer_name": "API Test Customer",
        "product_package_id": test_product.id
    }
    response = client.post("/api/v1/orders/", json=order_data, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["customer_email"] == order_data["customer_email"]
    assert data["product_package_id"] == test_product.id
    assert data["reseller_id"] == normal_user.id
    assert Decimal(data["price_paid"]) == test_product.price # Ensure price is derived correctly
    assert data["duration_days_at_purchase"] == test_product.duration_days
    assert data["country_code_at_purchase"] == test_product.country_code
    assert data["order_status"] == "PENDING_PAYMENT" # Default status

def test_create_order_product_not_found_or_inactive(
    client: TestClient, normal_user_token_headers: tuple, test_product: ProductPackage, db_session
):
    headers, _ = normal_user_token_headers

    # Case 1: Product does not exist
    order_data_non_existent_product = {
        "customer_email": f"cust_{uuid.uuid4().hex[:4]}@example.com",
        "product_package_id": 99999
    }
    response_non_existent = client.post("/api/v1/orders/", json=order_data_non_existent_product, headers=headers)
    assert response_non_existent.status_code == 404
    assert "Product not found or not active" in response_non_existent.json()["detail"]

    # Case 2: Product is inactive
    crud_product.update_product(db=db_session, db_obj=test_product, obj_in=ProductPackageUpdate(is_active=False)) # Use schema
    order_data_inactive_product = {
        "customer_email": f"cust_{uuid.uuid4().hex[:4]}@example.com",
        "product_package_id": test_product.id
    }
    response_inactive = client.post("/api/v1/orders/", json=order_data_inactive_product, headers=headers)
    assert response_inactive.status_code == 404
    assert "Product not found or not active" in response_inactive.json()["detail"]


def test_create_order_unauthenticated(client: TestClient, test_product: ProductPackage):
    order_data = {"customer_email": "unauth@example.com", "product_package_id": test_product.id}
    response = client.post("/api/v1/orders/", json=order_data)
    assert response.status_code == 401


# --- Order Reading Tests ---
@pytest.fixture(scope="function")
def created_order_for_normal_user(client: TestClient, normal_user_token_headers: tuple, test_product: ProductPackage) -> OrderModel:
    headers, user = normal_user_token_headers
    order_data = {
        "customer_email": f"my_cust_{uuid.uuid4().hex[:6]}@example.com",
        "product_package_id": test_product.id
    }
    response = client.post("/api/v1/orders/", json=order_data, headers=headers)
    assert response.status_code == 201
    # Fetch the full order object from DB to return for other tests
    # This assumes the response.json()["id"] is the new order's ID
    # For simplicity, we'll query it, but in a real scenario, you might trust the response if it's complete.
    # However, the response is OrderSchema, not OrderModel. So we fetch from DB.
    # For now, let's just return the ID and the test_normal_user for auth in subsequent tests.
    # This fixture is becoming complex, direct creation in tests might be simpler.
    # Let's return the created order dict from API and the user.
    return response.json(), user


def test_read_my_sales_normal_user(client: TestClient, normal_user_token_headers: tuple, created_order_for_normal_user):
    headers, _ = normal_user_token_headers
    created_order_data, _ = created_order_for_normal_user # We need its ID

    response = client.get("/api/v1/orders/my-sales/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(order["id"] == created_order_data["id"] for order in data)

def test_read_order_details_success_owner(client: TestClient, normal_user_token_headers: tuple, created_order_for_normal_user):
    headers, _ = normal_user_token_headers
    created_order_data, _ = created_order_for_normal_user

    response = client.get(f"/api/v1/orders/{created_order_data['id']}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == created_order_data["id"]
    assert data["customer_email"] == created_order_data["customer_email"]

def test_read_order_details_failure_other_user(
    client: TestClient, superuser_token_headers: tuple, normal_user_token_headers:tuple, created_order_for_normal_user, db_session: Session # Changed db_session_module to db_session
):
    # Order created by normal_user
    created_order_data, _ = created_order_for_normal_user

    # Attempt to read with another normal user (create a new one for this)
    other_normal_user_email = f"other_normal_{uuid.uuid4().hex[:6]}@example.com"
    other_normal_user_pass = "password123"
    # Use db_session (function-scoped) for creating this temporary user
    crud_reseller.create_reseller(db_session, obj_in=ResellerCreate(email=other_normal_user_email, password=other_normal_user_pass, reseller_type="OTHER"))

    login_resp = client.post("/api/v1/auth/login", data={"username": other_normal_user_email, "password": other_normal_user_pass})
    other_normal_user_token = login_resp.json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_normal_user_token}"}

    response_other_normal = client.get(f"/api/v1/orders/{created_order_data['id']}", headers=other_headers)
    assert response_other_normal.status_code == 403 # Forbidden

    # Superuser should be able to read it
    su_headers, _ = superuser_token_headers
    response_su = client.get(f"/api/v1/orders/{created_order_data['id']}", headers=su_headers)
    assert response_su.status_code == 200
    assert response_su.json()["id"] == created_order_data["id"]


def test_read_order_details_not_found(client: TestClient, normal_user_token_headers: tuple):
    headers, _ = normal_user_token_headers
    response = client.get("/api/v1/orders/99999", headers=headers)
    assert response.status_code == 404


# --- Order Update (PATCH /orders/{order_id}) ---
def test_update_order_status_superuser(client: TestClient, superuser_token_headers: tuple, created_order_for_normal_user):
    headers_su, _ = superuser_token_headers
    created_order_data, _ = created_order_for_normal_user # This order was created by normal_user

    update_payload = {"order_status": "COMPLETED", "esim_provisioning_status": "SUCCESS"}
    response = client.patch(f"/api/v1/orders/{created_order_data['id']}", json=update_payload, headers=headers_su)
    assert response.status_code == 200
    data = response.json()
    assert data["order_status"] == "COMPLETED"
    assert data["esim_provisioning_status"] == "SUCCESS"

def test_update_order_status_failure_normal_user(client: TestClient, normal_user_token_headers: tuple, created_order_for_normal_user):
    headers_normal, _ = normal_user_token_headers
    created_order_data, _ = created_order_for_normal_user

    update_payload = {"order_status": "PROCESSING"}
    response = client.patch(f"/api/v1/orders/{created_order_data['id']}", json=update_payload, headers=headers_normal)
    assert response.status_code == 403 # Normal user cannot update order status via this endpoint

def test_update_order_unauthenticated(client: TestClient, created_order_for_normal_user):
    created_order_data, _ = created_order_for_normal_user
    update_payload = {"order_status": "CANCELLED"}
    response = client.patch(f"/api/v1/orders/{created_order_data['id']}", json=update_payload)
    assert response.status_code == 401


# --- Admin Order Endpoints ---
def test_admin_read_orders_by_reseller(
    client: TestClient, superuser_token_headers: tuple, normal_user_token_headers: tuple, created_order_for_normal_user, db_session
):
    su_headers, _ = superuser_token_headers
    _, normal_user_obj = normal_user_token_headers # normal_user_obj is the ResellerProfile model instance
    created_order_data, _ = created_order_for_normal_user # This order belongs to normal_user_obj

    # Admin gets orders for the specific normal_user
    response = client.get(f"/api/v1/orders/admin/by-reseller/{normal_user_obj.id}", headers=su_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(order["id"] == created_order_data["id"] for order in data)

def test_admin_read_orders_by_reseller_failure_normal_user(client: TestClient, normal_user_token_headers: tuple):
    headers, user = normal_user_token_headers
    response = client.get(f"/api/v1/orders/admin/by-reseller/{user.id}", headers=headers) # Attempt to access admin route
    assert response.status_code == 403


# --- Commission Triggering Tests ---

def test_order_update_to_completed_triggers_commission(
    client: TestClient, db_session: Session,
    superuser_token_headers: tuple, # For updating order status
    test_normal_user: ResellerModel, # This will be reseller B (direct seller)
    test_product: ProductPackage, # Use a product with known commission rates
):
    # Setup: Reseller A (recruiter) and Reseller B (recruited by A)
    reseller_a_in = ResellerCreate(email=f"recruiter_comm_test_{uuid.uuid4().hex[:4]}@example.com", password="password", reseller_type="RECRUITER_A")
    reseller_a = crud_reseller.create_reseller(db_session, obj_in=reseller_a_in)

    # Re-create test_normal_user (reseller_b) to be recruited by reseller_a
    # To do this cleanly, we might need to delete the existing test_normal_user if IDs clash or make a new one
    # For simplicity, let's assume test_normal_user can be 'updated' or a new one is used.
    # Let's use the existing test_normal_user fixture and update its recruiter_id for this test.
    # However, test_normal_user fixture uses _create_reseller_and_get_token which creates a new user each time.
    # So, we need to create a new reseller B that is recruited by A.

    reseller_b_email = f"seller_b_{uuid.uuid4().hex[:4]}@example.com"
    reseller_b_in = ResellerCreate(
        email=reseller_b_email, password="password123", reseller_type="SELLER_B",
        recruiter_id=reseller_a.id
    )
    reseller_b = crud_reseller.create_reseller(db_session, obj_in=reseller_b_in)
    db_session.commit() # Ensure reseller_b is committed

    # Product with direct and recruitment commission
    product_for_commission_test = crud_product.create_product(db_session, obj_in=ProductPackageCreate(
        name=f"CommissionTestProd-{uuid.uuid4().hex[:4]}", duration_days=10, country_code="XT", price=Decimal("100.00"),
        direct_commission_rate_or_amount=Decimal("15.00"), # 15 USD direct
        recruitment_commission_rate_or_amount=Decimal("7.50") # 7.5 USD recruitment
    ))

    # Reseller B creates an order (status PENDING_PAYMENT by default from schema)
    order_data_internal = OrderCreateInternal(
        customer_email=f"cust_comm_trig_{uuid.uuid4().hex[:4]}@example.com",
        product_package_id=product_for_commission_test.id,
        reseller_id=reseller_b.id,
        price_paid=product_for_commission_test.price,
        currency_paid="USD",
        duration_days_at_purchase=product_for_commission_test.duration_days,
        country_code_at_purchase=product_for_commission_test.country_code
    )
    order = crud_order.create_order(db=db_session, obj_in=order_data_internal)
    assert order.order_status == "PENDING_PAYMENT"

    # Superuser updates order status to COMPLETED
    su_headers, _ = superuser_token_headers
    update_payload = OrderUpdate(order_status="COMPLETED")
    response_update = client.patch(f"/api/v1/orders/{order.id}", json=update_payload.model_dump(), headers=su_headers)
    assert response_update.status_code == 200
    assert response_update.json()["order_status"] == "COMPLETED"

    # Verify commissions
    commissions = crud_commission.get_commissions_by_order_id(db=db_session, order_id=order.id)
    assert len(commissions) == 2, "Should create direct and recruitment commissions"

    direct_commission_found = False
    recruitment_commission_found = False
    for comm in commissions:
        if comm.commission_type == "DIRECT_SALE" and comm.reseller_id == reseller_b.id:
            direct_commission_found = True
            assert comm.amount == product_for_commission_test.direct_commission_rate_or_amount
        elif comm.commission_type == "RECRUITMENT_TIER_1" and comm.reseller_id == reseller_a.id:
            recruitment_commission_found = True
            assert comm.amount == product_for_commission_test.recruitment_commission_rate_or_amount
            assert comm.original_order_reseller_id == reseller_b.id

    assert direct_commission_found, "Direct commission for seller B not found"
    assert recruitment_commission_found, "Recruitment commission for recruiter A not found"

def test_order_update_to_completed_idempotency(
    client: TestClient, db_session: Session,
    superuser_token_headers: tuple,
    test_normal_user: ResellerModel, # Direct seller
    test_product: ProductPackage # Ensure this product has commission values
):
    # Ensure product has commission values
    if test_product.direct_commission_rate_or_amount == 0:
        test_product.direct_commission_rate_or_amount = Decimal("10.00") # Ensure some commission
        db_session.add(test_product)
        db_session.commit()
        db_session.refresh(test_product)

    order_data_internal = OrderCreateInternal(
        customer_email=f"cust_idem_{uuid.uuid4().hex[:4]}@example.com",
        product_package_id=test_product.id,
        reseller_id=test_normal_user.id,
        price_paid=test_product.price, currency_paid="USD",
        duration_days_at_purchase=test_product.duration_days,
        country_code_at_purchase=test_product.country_code,
        order_status="PENDING_PAYMENT"
    )
    order = crud_order.create_order(db=db_session, obj_in=order_data_internal)

    su_headers, _ = superuser_token_headers
    update_payload = OrderUpdate(order_status="COMPLETED")

    # First update to COMPLETED
    response_update1 = client.patch(f"/api/v1/orders/{order.id}", json=update_payload.model_dump(), headers=su_headers)
    assert response_update1.status_code == 200
    commissions1 = crud_commission.get_commissions_by_order_id(db=db_session, order_id=order.id)
    assert len(commissions1) >= 1 # At least direct commission

    # Second update to COMPLETED
    response_update2 = client.patch(f"/api/v1/orders/{order.id}", json=update_payload.model_dump(), headers=su_headers)
    assert response_update2.status_code == 200
    commissions2 = crud_commission.get_commissions_by_order_id(db=db_session, order_id=order.id)
    assert len(commissions2) == len(commissions1), "Commission records should not be duplicated"


def test_order_update_to_other_status_no_commission(
    client: TestClient, db_session: Session,
    superuser_token_headers: tuple,
    test_normal_user: ResellerModel,
    test_product: ProductPackage
):
    order_data_internal = OrderCreateInternal(
        customer_email=f"cust_other_stat_{uuid.uuid4().hex[:4]}@example.com",
        product_package_id=test_product.id,
        reseller_id=test_normal_user.id,
        price_paid=test_product.price, currency_paid="USD",
        duration_days_at_purchase=test_product.duration_days,
        country_code_at_purchase=test_product.country_code,
        order_status="PENDING_PAYMENT"
    )
    order = crud_order.create_order(db=db_session, obj_in=order_data_internal)

    su_headers, _ = superuser_token_headers
    update_payload = OrderUpdate(order_status="PROCESSING") # Not COMPLETED
    response_update = client.patch(f"/api/v1/orders/{order.id}", json=update_payload.model_dump(), headers=su_headers)
    assert response_update.status_code == 200

    commissions = crud_commission.get_commissions_by_order_id(db=db_session, order_id=order.id)
    assert len(commissions) == 0, "No commissions should be created for non-COMPLETED status updates"

def test_admin_read_orders_by_customer(client: TestClient, superuser_token_headers: tuple, created_order_for_normal_user):
    su_headers, _ = superuser_token_headers
    created_order_data, _ = created_order_for_normal_user
    customer_email_to_search = created_order_data["customer_email"]

    response = client.get(f"/api/v1/orders/admin/by-customer/?customer_email={customer_email_to_search}", headers=su_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(order["id"] == created_order_data["id"] and order["customer_email"] == customer_email_to_search for order in data)

def test_admin_read_orders_by_customer_failure_normal_user(client: TestClient, normal_user_token_headers: tuple, created_order_for_normal_user):
    headers, _ = normal_user_token_headers
    created_order_data, _ = created_order_for_normal_user
    customer_email_to_search = created_order_data["customer_email"]
    response = client.get(f"/api/v1/orders/admin/by-customer/?customer_email={customer_email_to_search}", headers=headers)
    assert response.status_code == 403
