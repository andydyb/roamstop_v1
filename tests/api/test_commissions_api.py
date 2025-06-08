import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import uuid
from decimal import Decimal

from app.crud import crud_commission, crud_reseller, crud_product, crud_order
from app.schemas.commission import CommissionCreate
from app.schemas.order import OrderCreateInternal
from app.schemas.product import ProductPackageCreate
from app.schemas.reseller import ResellerCreate
from app.models.reseller import ResellerProfile as ResellerModel

pytestmark = pytest.mark.api

def test_read_my_commissions_empty(client: TestClient, normal_user_token_headers: tuple):
    headers, _ = normal_user_token_headers
    response = client.get("/api/v1/resellers/me/commissions", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0

def test_read_my_commissions_with_data(
    client: TestClient, db_session: Session,
    normal_user_token_headers: tuple,
    test_normal_user: ResellerModel # This is the ResellerProfile model instance
):
    headers, _ = normal_user_token_headers

    # Create a product and an order that would generate commissions
    product = crud_product.create_product(db_session, obj_in=ProductPackageCreate(
        name=f"P-{uuid.uuid4().hex[:4]}", duration_days=30, country_code="US", price=Decimal("100"),
        direct_commission_rate_or_amount=Decimal("10"), recruitment_commission_rate_or_amount=Decimal("5")
    ))
    order = crud_order.create_order(db_session, obj_in=OrderCreateInternal(
        customer_email="cust@example.com", product_package_id=product.id, reseller_id=test_normal_user.id,
        price_paid=product.price, currency_paid="USD", duration_days_at_purchase=product.duration_days,
        country_code_at_purchase=product.country_code, order_status="COMPLETED" # Important for commission creation
    ))

    # Manually create commission records for this user via CRUD
    # (assuming calculate_and_record_commissions is not automatically called by order creation via CRUD)
    # For this test, we'll directly create commissions to ensure this endpoint works.
    # The commission calculator logic is tested separately.

    commission1 = crud_commission.create_commission(db_session, obj_in=CommissionCreate(
        order_id=order.id, reseller_id=test_normal_user.id, commission_type="DIRECT_SALE",
        amount=Decimal("10.00"), currency="USD", product_package_id_at_sale=product.id,
        commission_status="UNPAID"
    ))
    commission2 = crud_commission.create_commission(db_session, obj_in=CommissionCreate(
        order_id=order.id, reseller_id=test_normal_user.id, commission_type="BONUS", # Example
        amount=Decimal("2.00"), currency="USD", product_package_id_at_sale=product.id,
        commission_status="PAID"
    ))

    response = client.get("/api/v1/resellers/me/commissions", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2 # Could be more if other tests created some for this user

    ids_in_response = [c["id"] for c in data]
    assert commission1.id in ids_in_response
    assert commission2.id in ids_in_response

    # Test status filtering
    response_unpaid = client.get("/api/v1/resellers/me/commissions?status=UNPAID", headers=headers)
    assert response_unpaid.status_code == 200
    data_unpaid = response_unpaid.json()
    assert any(c["id"] == commission1.id and c["commission_status"] == "UNPAID" for c in data_unpaid)
    assert not any(c["id"] == commission2.id for c in data_unpaid) # commission2 is PAID

    response_paid = client.get("/api/v1/resellers/me/commissions?status=PAID", headers=headers)
    assert response_paid.status_code == 200
    data_paid = response_paid.json()
    assert any(c["id"] == commission2.id and c["commission_status"] == "PAID" for c in data_paid)
    assert not any(c["id"] == commission1.id for c in data_paid)

    # Test pagination (simple check)
    response_limit1 = client.get("/api/v1/resellers/me/commissions?limit=1", headers=headers)
    assert response_limit1.status_code == 200
    assert len(response_limit1.json()) == 1


def test_read_my_commissions_unauthenticated(client: TestClient):
    response = client.get("/api/v1/resellers/me/commissions")
    assert response.status_code == 401 # or 403 if auto_error=False and endpoint expects user

# The endpoint for reseller commissions is /api/v1/resellers/me/commissions, not /api/v1/commissions
# No other commission-specific API endpoints were defined in the original plan for this step
# other than those implicitly tested by order updates.
