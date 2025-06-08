import pytest
from sqlalchemy.orm import Session, joinedload
from decimal import Decimal
import uuid

from app.core.commissions_calculator import calculate_and_record_commissions
from app.models.order import Order as OrderModel
from app.models.reseller import ResellerProfile as ResellerProfileModel
from app.models.product import ProductPackage as ProductPackageModel
from app.models.commission import Commission as CommissionModel
from app.crud import crud_reseller, crud_product, crud_order, crud_commission
from app.schemas.reseller import ResellerCreate
from app.schemas.product import ProductPackageCreate
from app.schemas.order import OrderCreateInternal
from tests.conftest import create_recruited_reseller # Helper from conftest

pytestmark = pytest.mark.crud # Or pytest.mark.core

@pytest.fixture
def reseller_a(db_session: Session) -> ResellerProfileModel:
    return crud_reseller.create_reseller(db_session, obj_in=ResellerCreate(
        email=f"reseller_a_{uuid.uuid4().hex[:4]}@example.com", password="password", reseller_type="TYPE_A", is_active=True
    ))

@pytest.fixture
def reseller_b_recruited_by_a(db_session: Session, reseller_a: ResellerProfileModel) -> ResellerProfileModel:
    return create_recruited_reseller(db_session, recruiter=reseller_a)

@pytest.fixture
def inactive_recruiter(db_session: Session) -> ResellerProfileModel:
    return crud_reseller.create_reseller(db_session, obj_in=ResellerCreate(
        email=f"inactive_recruiter_{uuid.uuid4().hex[:4]}@example.com", password="password", reseller_type="TYPE_A", is_active=False
    ))

@pytest.fixture
def reseller_c_recruited_by_inactive(db_session: Session, inactive_recruiter: ResellerProfileModel) -> ResellerProfileModel:
    return create_recruited_reseller(db_session, recruiter=inactive_recruiter)


@pytest.fixture
def product_direct_commission(db_session: Session) -> ProductPackageModel:
    return crud_product.create_product(db_session, obj_in=ProductPackageCreate(
        name="Direct Comm Prod", duration_days=30, country_code="US", price=Decimal("100"),
        direct_commission_rate_or_amount=Decimal("10"), recruitment_commission_rate_or_amount=Decimal("0")
    ))

@pytest.fixture
def product_recruitment_commission(db_session: Session) -> ProductPackageModel:
    return crud_product.create_product(db_session, obj_in=ProductPackageCreate(
        name="Recruit Comm Prod", duration_days=30, country_code="US", price=Decimal("100"),
        direct_commission_rate_or_amount=Decimal("0"), recruitment_commission_rate_or_amount=Decimal("5")
    ))

@pytest.fixture
def product_both_commissions(db_session: Session) -> ProductPackageModel:
    return crud_product.create_product(db_session, obj_in=ProductPackageCreate(
        name="Both Comm Prod", duration_days=30, country_code="US", price=Decimal("100"),
        direct_commission_rate_or_amount=Decimal("10"), recruitment_commission_rate_or_amount=Decimal("5")
    ))

@pytest.fixture
def product_no_commissions(db_session: Session) -> ProductPackageModel:
    return crud_product.create_product(db_session, obj_in=ProductPackageCreate(
        name="No Comm Prod", duration_days=30, country_code="US", price=Decimal("100"),
        direct_commission_rate_or_amount=Decimal("0"), recruitment_commission_rate_or_amount=Decimal("0")
    ))

async def create_order_for_test(db: Session, seller: ResellerProfileModel, product: ProductPackageModel) -> OrderModel:
    order_in = OrderCreateInternal(
        customer_email=f"cust_{uuid.uuid4().hex[:4]}@example.com", product_package_id=product.id,
        reseller_id=seller.id, price_paid=product.price, currency_paid="USD",
        duration_days_at_purchase=product.duration_days, country_code_at_purchase=product.country_code,
        order_status="COMPLETED" # Assume order is completed for commission calculation
    )
    return crud_order.create_order(db=db, obj_in=order_in)

@pytest.mark.asyncio
async def test_direct_commission_only(db_session: Session, reseller_a: ResellerProfileModel, product_direct_commission: ProductPackageModel):
    order = await create_order_for_test(db_session, reseller_a, product_direct_commission)
    await calculate_and_record_commissions(db_session, order)

    commissions = crud_commission.get_commissions_by_order_id(db=db_session, order_id=order.id)
    assert len(commissions) == 1
    direct_comm = commissions[0]
    assert direct_comm.reseller_id == reseller_a.id
    assert direct_comm.commission_type == "DIRECT_SALE"
    assert direct_comm.amount == product_direct_commission.direct_commission_rate_or_amount

@pytest.mark.asyncio
async def test_direct_and_recruitment_commission(db_session: Session, reseller_b_recruited_by_a: ResellerProfileModel, reseller_a: ResellerProfileModel, product_both_commissions: ProductPackageModel):
    order = await create_order_for_test(db_session, reseller_b_recruited_by_a, product_both_commissions)
    await calculate_and_record_commissions(db_session, order)

    commissions = sorted(crud_commission.get_commissions_by_order_id(db=db_session, order_id=order.id), key=lambda c: c.commission_type)
    assert len(commissions) == 2

    direct_comm = commissions[0] # DIRECT_SALE
    recruit_comm = commissions[1] # RECRUITMENT_TIER_1

    assert direct_comm.reseller_id == reseller_b_recruited_by_a.id
    assert direct_comm.commission_type == "DIRECT_SALE"
    assert direct_comm.amount == product_both_commissions.direct_commission_rate_or_amount

    assert recruit_comm.reseller_id == reseller_a.id
    assert recruit_comm.commission_type == "RECRUITMENT_TIER_1"
    assert recruit_comm.amount == product_both_commissions.recruitment_commission_rate_or_amount
    assert recruit_comm.original_order_reseller_id == reseller_b_recruited_by_a.id

@pytest.mark.asyncio
async def test_recruitment_commission_only_active_recruiter(db_session: Session, reseller_b_recruited_by_a: ResellerProfileModel, reseller_a: ResellerProfileModel, product_recruitment_commission: ProductPackageModel):
    order = await create_order_for_test(db_session, reseller_b_recruited_by_a, product_recruitment_commission)
    await calculate_and_record_commissions(db_session, order)

    commissions = crud_commission.get_commissions_by_order_id(db=db_session, order_id=order.id)
    assert len(commissions) == 1
    recruit_comm = commissions[0]

    assert recruit_comm.reseller_id == reseller_a.id
    assert recruit_comm.commission_type == "RECRUITMENT_TIER_1"
    assert recruit_comm.amount == product_recruitment_commission.recruitment_commission_rate_or_amount

@pytest.mark.asyncio
async def test_no_recruitment_commission_if_recruiter_inactive(db_session: Session, reseller_c_recruited_by_inactive: ResellerProfileModel, product_both_commissions: ProductPackageModel, inactive_recruiter: ResellerProfileModel):
    # Ensure the recruiter is indeed inactive in the current session state before calculation
    # inactive_recruiter_from_db = db_session.query(ResellerProfileModel).filter(ResellerProfileModel.id == reseller_c_recruited_by_inactive.recruiter_id).first()
    # assert inactive_recruiter_from_db is not None
    # assert inactive_recruiter_from_db.is_active is False, "Test setup error: inactive_recruiter fixture should be inactive."

    # A more direct check on the fixture instance itself, assuming it reflects DB state after its own creation
    db_session.refresh(inactive_recruiter) # Ensure we have the latest state from the DB for this check
    assert inactive_recruiter.is_active is False, "Test setup error: inactive_recruiter fixture should be inactive in DB."


    order = await create_order_for_test(db_session, reseller_c_recruited_by_inactive, product_both_commissions)
    await calculate_and_record_commissions(db_session, order)

    commissions = crud_commission.get_commissions_by_order_id(db=db_session, order_id=order.id)
    # Only direct commission for reseller_c should exist
    assert len(commissions) == 1
    direct_comm = commissions[0]
    assert direct_comm.reseller_id == reseller_c_recruited_by_inactive.id
    assert direct_comm.commission_type == "DIRECT_SALE"

@pytest.mark.asyncio
async def test_no_commission_if_amounts_zero(db_session: Session, reseller_b_recruited_by_a: ResellerProfileModel, product_no_commissions: ProductPackageModel):
    order = await create_order_for_test(db_session, reseller_b_recruited_by_a, product_no_commissions)
    await calculate_and_record_commissions(db_session, order)

    commissions = crud_commission.get_commissions_by_order_id(db=db_session, order_id=order.id)
    assert len(commissions) == 0

@pytest.mark.asyncio
async def test_no_commission_if_direct_seller_inactive(db_session: Session, reseller_a: ResellerProfileModel, product_both_commissions: ProductPackageModel):
    # Make reseller_a inactive
    reseller_a.is_active = False
    db_session.add(reseller_a)
    db_session.commit()
    db_session.refresh(reseller_a)

    order = await create_order_for_test(db_session, reseller_a, product_both_commissions)
    await calculate_and_record_commissions(db_session, order)

    commissions = crud_commission.get_commissions_by_order_id(db=db_session, order_id=order.id)
    assert len(commissions) == 0

@pytest.mark.asyncio
async def test_commission_calculator_loads_product_and_reseller_if_not_eager(db_session: Session, reseller_a: ResellerProfileModel, product_direct_commission: ProductPackageModel):
    # Create order without eager loading product_package and reseller
    order_data = OrderCreateInternal(
        customer_email=f"cust_lazy_{uuid.uuid4().hex[:4]}@example.com", product_package_id=product_direct_commission.id,
        reseller_id=reseller_a.id, price_paid=product_direct_commission.price, currency_paid="USD",
        duration_days_at_purchase=product_direct_commission.duration_days, country_code_at_purchase=product_direct_commission.country_code,
        order_status="COMPLETED"
    )
    order_obj_basic = crud_order.create_order(db=db_session, obj_in=order_data)

    # Fetch a minimal version of the order that definitely doesn't have relations loaded
    # Use joinedload(OrderModel.commissions) to ensure it's not already loaded by that
    order_detached = db_session.query(OrderModel).filter(OrderModel.id == order_obj_basic.id).first()

    assert order_detached is not None
    # At this point, order_detached.product_package and order_detached.reseller might be unloaded (depending on session/identity map)
    # The calculator should handle this by loading them itself.

    await calculate_and_record_commissions(db_session, order_detached)

    commissions = crud_commission.get_commissions_by_order_id(db=db_session, order_id=order_detached.id)
    assert len(commissions) == 1
    direct_comm = commissions[0]
    assert direct_comm.reseller_id == reseller_a.id
    assert direct_comm.commission_type == "DIRECT_SALE"
    assert direct_comm.amount == product_direct_commission.direct_commission_rate_or_amount
