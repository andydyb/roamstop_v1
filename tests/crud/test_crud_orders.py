import pytest
from sqlalchemy.orm import Session
import uuid
from decimal import Decimal

from app.crud import crud_order, crud_reseller, crud_product
from app.schemas.order import OrderCreateInternal, OrderUpdate
from app.schemas.reseller import ResellerCreate
from app.schemas.product import ProductPackageCreate
from app.models.order import Order
from app.models.reseller import ResellerProfile
from app.models.product import ProductPackage

pytestmark = pytest.mark.crud

@pytest.fixture(scope="function")
def test_reseller_for_order(db_session: Session) -> ResellerProfile:
    email = f"reseller_order_test_{uuid.uuid4().hex[:6]}@example.com"
    reseller_in = ResellerCreate(
        email=email, password="password123", reseller_type="ORDER_TESTER", is_superuser=False
    )
    return crud_reseller.create_reseller(db=db_session, obj_in=reseller_in)

@pytest.fixture(scope="function")
def test_product_for_order(db_session: Session) -> ProductPackage:
    product_in = ProductPackageCreate(
        name=f"Order Test Product {uuid.uuid4().hex[:6]}",
        duration_days=15,
        country_code="DE",
        price=Decimal("12.50"),
        direct_commission_rate_or_amount=Decimal("1.00"),
        recruitment_commission_rate_or_amount=Decimal("0.50")
    )
    return crud_product.create_product(db=db_session, obj_in=product_in)


def test_create_order(db_session: Session, test_reseller_for_order: ResellerProfile, test_product_for_order: ProductPackage):
    customer_email = f"customer_{uuid.uuid4().hex[:6]}@example.com"

    order_in_internal = OrderCreateInternal(
        customer_email=customer_email,
        customer_name="Test Customer",
        product_package_id=test_product_for_order.id,
        reseller_id=test_reseller_for_order.id,
        price_paid=test_product_for_order.price, # Price from product
        currency_paid="USD", # Assuming USD
        duration_days_at_purchase=test_product_for_order.duration_days,
        country_code_at_purchase=test_product_for_order.country_code,
        order_status="COMPLETED", # Set a specific status for test
        stripe_payment_intent_id=f"pi_{uuid.uuid4().hex}",
        esim_provisioning_status="SUCCESS"
    )

    created_order = crud_order.create_order(db=db_session, obj_in=order_in_internal)

    assert created_order is not None
    assert created_order.customer_email == customer_email
    assert created_order.product_package_id == test_product_for_order.id
    assert created_order.reseller_id == test_reseller_for_order.id
    assert created_order.price_paid == test_product_for_order.price
    assert created_order.duration_days_at_purchase == test_product_for_order.duration_days
    assert created_order.country_code_at_purchase == test_product_for_order.country_code
    assert created_order.order_status == "COMPLETED"
    assert created_order.product_package is not None # Check relationship loaded via refresh
    assert created_order.reseller is not None     # Check relationship loaded via refresh

@pytest.fixture(scope="function")
def created_test_order(db_session: Session, test_reseller_for_order: ResellerProfile, test_product_for_order: ProductPackage) -> Order:
    order_in_internal = OrderCreateInternal(
        customer_email=f"cust_{uuid.uuid4().hex[:6]}@example.com",
        product_package_id=test_product_for_order.id,
        reseller_id=test_reseller_for_order.id,
        price_paid=test_product_for_order.price,
        currency_paid="EUR",
        duration_days_at_purchase=test_product_for_order.duration_days,
        country_code_at_purchase=test_product_for_order.country_code,
        stripe_payment_intent_id=f"pi_fixture_{uuid.uuid4().hex}"
    )
    return crud_order.create_order(db=db_session, obj_in=order_in_internal)

def test_get_order(db_session: Session, created_test_order: Order):
    retrieved_order = crud_order.get_order(db=db_session, order_id=created_test_order.id)
    assert retrieved_order is not None
    assert retrieved_order.id == created_test_order.id
    assert retrieved_order.customer_email == created_test_order.customer_email
    assert retrieved_order.product_package is not None # Eager loading check
    assert retrieved_order.product_package.name == created_test_order.product_package.name
    assert retrieved_order.reseller is not None       # Eager loading check
    assert retrieved_order.reseller.email == created_test_order.reseller.email


def test_get_orders_by_reseller(db_session: Session, test_reseller_for_order: ResellerProfile, created_test_order: Order):
    # created_test_order is already by test_reseller_for_order
    orders = crud_order.get_orders_by_reseller(db=db_session, reseller_id=test_reseller_for_order.id)
    assert len(orders) >= 1
    assert any(o.id == created_test_order.id for o in orders)

def test_get_orders_by_customer(db_session: Session, created_test_order: Order):
    orders = crud_order.get_orders_by_customer(db=db_session, customer_email=created_test_order.customer_email)
    assert len(orders) >= 1
    assert any(o.id == created_test_order.id for o in orders)

def test_update_order(db_session: Session, created_test_order: Order):
    update_data = OrderUpdate(
        order_status="PROCESSING",
        esim_provisioning_status="REQUESTED"
    )
    updated_order = crud_order.update_order(db=db_session, db_obj=created_test_order, obj_in=update_data)
    assert updated_order.order_status == "PROCESSING"
    assert updated_order.esim_provisioning_status == "REQUESTED"
    assert updated_order.stripe_payment_intent_id == created_test_order.stripe_payment_intent_id # Should not change

def test_get_order_by_stripe_payment_intent(db_session: Session, created_test_order: Order):
    if created_test_order.stripe_payment_intent_id:
        retrieved_order = crud_order.get_order_by_stripe_payment_intent(
            db=db_session, payment_intent_id=created_test_order.stripe_payment_intent_id
        )
        assert retrieved_order is not None
        assert retrieved_order.id == created_test_order.id
    else:
        pytest.skip("Test order does not have a stripe_payment_intent_id")

def test_get_order_count_for_reseller(db_session: Session, test_reseller_for_order: ResellerProfile, created_test_order: Order):
    count = crud_order.get_order_count_for_reseller(db=db_session, reseller_id=test_reseller_for_order.id)
    assert count >= 1

def test_get_order_count_for_customer(db_session: Session, created_test_order: Order):
    count = crud_order.get_order_count_for_customer(db=db_session, customer_email=created_test_order.customer_email)
    assert count >= 1
