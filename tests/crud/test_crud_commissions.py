import pytest
from sqlalchemy.orm import Session, joinedload
import uuid
from decimal import Decimal

from app.crud import crud_commission, crud_order, crud_product, crud_reseller
from app.schemas.commission import CommissionCreate, CommissionUpdate
from app.schemas.order import OrderCreateInternal
from app.schemas.product import ProductPackageCreate
from app.schemas.reseller import ResellerCreate
from app.models.commission import Commission
from app.models.order import Order
from app.models.reseller import ResellerProfile
from app.models.product import ProductPackage
from tests.conftest import create_recruited_reseller # Import helper

pytestmark = pytest.mark.crud

@pytest.fixture(scope="function")
def db_reseller_for_commission_tests(db_session: Session) -> ResellerProfile:
    return crud_reseller.create_reseller(db_session, obj_in=ResellerCreate(
        email=f"comtest_reseller_{uuid.uuid4().hex[:6]}@example.com",
        password="password",
        reseller_type="TYPE_A"
    ))

@pytest.fixture(scope="function")
def db_product_for_commission_tests(db_session: Session) -> ProductPackage:
    return crud_product.create_product(db_session, obj_in=ProductPackageCreate(
        name=f"CommTest Product {uuid.uuid4().hex[:6]}",
        duration_days=30,
        country_code="US",
        price=Decimal("100.00"),
        direct_commission_rate_or_amount=Decimal("10.00"), # 10% direct
        recruitment_commission_rate_or_amount=Decimal("5.00") # 5% recruitment
    ))

@pytest.fixture(scope="function")
def db_order_for_commission_tests(
    db_session: Session,
    db_reseller_for_commission_tests: ResellerProfile,
    db_product_for_commission_tests: ProductPackage
) -> Order:
    order_in = OrderCreateInternal(
        customer_email=f"cust_comm_{uuid.uuid4().hex[:6]}@example.com",
        product_package_id=db_product_for_commission_tests.id,
        reseller_id=db_reseller_for_commission_tests.id,
        price_paid=db_product_for_commission_tests.price,
        currency_paid="USD",
        duration_days_at_purchase=db_product_for_commission_tests.duration_days,
        country_code_at_purchase=db_product_for_commission_tests.country_code,
        order_status="COMPLETED" # Assume order is completed for commission tests
    )
    return crud_order.create_order(db=db_session, obj_in=order_in)

def test_create_commission(db_session: Session, db_order_for_commission_tests: Order, db_reseller_for_commission_tests: ResellerProfile, db_product_for_commission_tests: ProductPackage):
    commission_in = CommissionCreate(
        order_id=db_order_for_commission_tests.id,
        reseller_id=db_reseller_for_commission_tests.id,
        commission_type="DIRECT_SALE",
        amount=Decimal("10.00"),
        currency="USD",
        product_package_id_at_sale=db_product_for_commission_tests.id,
        commission_status="UNPAID",
        calculation_details={"rate": 0.10, "base_amount": 100.00}
    )
    commission = crud_commission.create_commission(db=db_session, obj_in=commission_in)
    assert commission is not None
    assert commission.order_id == db_order_for_commission_tests.id
    assert commission.reseller_id == db_reseller_for_commission_tests.id
    assert commission.amount == Decimal("10.00")
    assert commission.commission_type == "DIRECT_SALE"

@pytest.fixture(scope="function")
def created_commission(db_session: Session, db_order_for_commission_tests: Order, db_reseller_for_commission_tests: ResellerProfile, db_product_for_commission_tests: ProductPackage) -> Commission:
    commission_in = CommissionCreate(
        order_id=db_order_for_commission_tests.id,
        reseller_id=db_reseller_for_commission_tests.id,
        commission_type="DIRECT_SALE",
        amount=Decimal("12.34"),
        currency="USD",
        product_package_id_at_sale=db_product_for_commission_tests.id,
        commission_status="UNPAID"
    )
    return crud_commission.create_commission(db=db_session, obj_in=commission_in)

def test_get_commission(db_session: Session, created_commission: Commission):
    retrieved_commission = crud_commission.get_commission(db=db_session, commission_id=created_commission.id)
    assert retrieved_commission is not None
    assert retrieved_commission.id == created_commission.id
    assert retrieved_commission.amount == Decimal("12.34")
    # Test eager loading (if applicable and makes sense for your get_commission)
    assert retrieved_commission.order is not None
    assert retrieved_commission.earning_reseller is not None
    assert retrieved_commission.product_package is not None

def test_get_commissions_by_reseller(db_session: Session, db_reseller_for_commission_tests: ResellerProfile, created_commission: Commission):
    commissions = crud_commission.get_commissions_by_reseller(db=db_session, reseller_id=db_reseller_for_commission_tests.id)
    assert len(commissions) >= 1
    assert any(c.id == created_commission.id for c in commissions)

    # Test status filter
    commissions_unpaid = crud_commission.get_commissions_by_reseller(db=db_session, reseller_id=db_reseller_for_commission_tests.id, status="UNPAID")
    assert any(c.id == created_commission.id for c in commissions_unpaid)

    commissions_paid = crud_commission.get_commissions_by_reseller(db=db_session, reseller_id=db_reseller_for_commission_tests.id, status="PAID")
    assert not any(c.id == created_commission.id for c in commissions_paid)


def test_update_commission_status(db_session: Session, created_commission: Commission):
    updated_commission = crud_commission.update_commission_status(db=db_session, commission_id=created_commission.id, status="PAID")
    assert updated_commission is not None
    assert updated_commission.commission_status == "PAID"

    fetched_commission = crud_commission.get_commission(db=db_session, commission_id=created_commission.id)
    assert fetched_commission is not None
    assert fetched_commission.commission_status == "PAID"

def test_get_unpaid_commissions_for_reseller(db_session: Session, db_reseller_for_commission_tests: ResellerProfile, created_commission: Commission):
    # created_commission is 'UNPAID'
    unpaid_commissions = crud_commission.get_unpaid_commissions_for_reseller(db=db_session, reseller_id=db_reseller_for_commission_tests.id)
    assert any(c.id == created_commission.id for c in unpaid_commissions)

    # Mark as PAID and check again
    crud_commission.update_commission_status(db=db_session, commission_id=created_commission.id, status="PAID")
    unpaid_commissions_after_paid = crud_commission.get_unpaid_commissions_for_reseller(db=db_session, reseller_id=db_reseller_for_commission_tests.id)
    assert not any(c.id == created_commission.id for c in unpaid_commissions_after_paid)

def test_get_commissions_by_order_id(db_session: Session, db_order_for_commission_tests: Order, created_commission: Commission):
    commissions = crud_commission.get_commissions_by_order_id(db=db_session, order_id=db_order_for_commission_tests.id)
    assert len(commissions) >= 1
    assert any(c.id == created_commission.id for c in commissions)

    # Create another commission for the same order for a different reseller (e.g. recruitment)
    recruiter = crud_reseller.create_reseller(db_session, obj_in=ResellerCreate(
        email=f"recruiter_{uuid.uuid4().hex[:6]}@example.com", password="foo", reseller_type="RECRUITER"
    ))
    commission_rec_in = CommissionCreate(
        order_id=db_order_for_commission_tests.id,
        reseller_id=recruiter.id, # Commission for recruiter
        commission_type="RECRUITMENT_TIER_1",
        amount=Decimal("5.00"),
        currency="USD",
        product_package_id_at_sale=created_commission.product_package_id_at_sale,
        original_order_reseller_id=created_commission.reseller_id,
        commission_status="UNPAID"
    )
    crud_commission.create_commission(db=db_session, obj_in=commission_rec_in)

    commissions_for_order = crud_commission.get_commissions_by_order_id(db=db_session, order_id=db_order_for_commission_tests.id)
    assert len(commissions_for_order) == 2
