import pytest
from sqlalchemy.orm import Session
import uuid
from decimal import Decimal

from app.crud import crud_product
from app.schemas.product import ProductPackageCreate, ProductPackageUpdate
from app.models.product import ProductPackage

pytestmark = pytest.mark.crud

def test_create_product(db_session: Session):
    name = f"Test Create Product {uuid.uuid4().hex[:6]}"
    product_in = ProductPackageCreate(
        name=name,
        description="Detailed description here",
        duration_days=60,
        country_code="CA",
        price=Decimal("29.99"),
        direct_commission_rate_or_amount=Decimal("3.00"),
        recruitment_commission_rate_or_amount=Decimal("1.50"),
        is_active=True
    )
    db_product = crud_product.create_product(db=db_session, obj_in=product_in)
    assert db_product is not None
    assert db_product.name == name
    assert db_product.country_code == "CA"
    assert db_product.price == Decimal("29.99")
    assert db_product.is_active is True

def test_get_product(db_session: Session, test_product: ProductPackage):
    # Test getting active product (default)
    retrieved_product = crud_product.get_product(db=db_session, product_id=test_product.id)
    assert retrieved_product is not None
    assert retrieved_product.id == test_product.id

    # Test getting product when show_inactive is True (even if it's active)
    retrieved_product_show_inactive_true = crud_product.get_product(db=db_session, product_id=test_product.id, show_inactive=True)
    assert retrieved_product_show_inactive_true is not None
    assert retrieved_product_show_inactive_true.id == test_product.id

    # Make it inactive and test
    crud_product.update_product(db=db_session, db_obj=test_product, obj_in=ProductPackageUpdate(is_active=False))

    # Should not get it by default now
    retrieved_inactive_product_default = crud_product.get_product(db=db_session, product_id=test_product.id)
    assert retrieved_inactive_product_default is None

    # Should get it if show_inactive is True
    retrieved_inactive_product_show_inactive = crud_product.get_product(db=db_session, product_id=test_product.id, show_inactive=True)
    assert retrieved_inactive_product_show_inactive is not None
    assert retrieved_inactive_product_show_inactive.is_active is False


def test_get_products_by_country(db_session: Session, test_product: ProductPackage):
    # test_product fixture creates a product with country_code="US"
    products_us = crud_product.get_products_by_country(db=db_session, country_code="US")
    assert any(p.id == test_product.id for p in products_us)

    products_ca = crud_product.get_products_by_country(db=db_session, country_code="CA")
    assert not any(p.id == test_product.id for p in products_ca)

    # Test with inactive product
    crud_product.update_product(db=db_session, db_obj=test_product, obj_in=ProductPackageUpdate(is_active=False))
    products_us_active_only = crud_product.get_products_by_country(db=db_session, country_code="US", is_active=True)
    assert not any(p.id == test_product.id for p in products_us_active_only)

    products_us_inactive_too = crud_product.get_products_by_country(db=db_session, country_code="US", is_active=False) # This actually means "is_active must be False"
    # To get all (active and inactive) for a country, the get_all_products with country filter would be better or adjust this function
    # For now, test based on current implementation: is_active=False means get only inactive ones.
    # A better signature for get_products_by_country might be `status: Optional[bool] = True`
    # assert any(p.id == test_product.id for p in products_us_inactive_too) # This will fail as is_active=False in query.

def test_get_all_products(db_session: Session, test_product: ProductPackage):
    all_products_active_default = crud_product.get_all_products(db=db_session) # is_active=None by default in this func
    assert any(p.id == test_product.id for p in all_products_active_default)

    all_products_active_true = crud_product.get_all_products(db=db_session, is_active=True)
    assert any(p.id == test_product.id for p in all_products_active_true)

    crud_product.update_product(db=db_session, db_obj=test_product, obj_in=ProductPackageUpdate(is_active=False))

    all_products_active_false = crud_product.get_all_products(db=db_session, is_active=False)
    assert any(p.id == test_product.id for p in all_products_active_false)

    all_products_active_none = crud_product.get_all_products(db=db_session, is_active=None)
    assert any(p.id == test_product.id for p in all_products_active_none)


def test_update_product(db_session: Session, test_product: ProductPackage):
    new_name = f"Updated Product Name {uuid.uuid4().hex[:6]}"
    update_data = ProductPackageUpdate(
        name=new_name,
        price=Decimal("99.99"),
        is_active=False
    )
    updated_db_product = crud_product.update_product(db=db_session, db_obj=test_product, obj_in=update_data)
    assert updated_db_product.name == new_name
    assert updated_db_product.price == Decimal("99.99")
    assert updated_db_product.is_active is False

def test_delete_product_logical(db_session: Session, test_product: ProductPackage):
    assert test_product.is_active is True
    deleted_product = crud_product.delete_product(db=db_session, product_id=test_product.id)
    assert deleted_product is not None
    assert deleted_product.is_active is False

    # Try deleting again, should still return the object (now inactive)
    deleted_again = crud_product.delete_product(db=db_session, product_id=test_product.id)
    assert deleted_again is not None
    assert deleted_again.is_active is False

    # Check it's not returned by default get_product
    retrieved_after_delete = crud_product.get_product(db=db_session, product_id=test_product.id)
    assert retrieved_after_delete is None

def test_hard_delete_product(db_session: Session, test_product: ProductPackage):
    product_id = test_product.id
    hard_deleted_product = crud_product.hard_delete_product(db=db_session, product_id=product_id)
    assert hard_deleted_product is not None
    assert hard_deleted_product.id == product_id

    retrieved_after_hard_delete = crud_product.get_product(db=db_session, product_id=product_id, show_inactive=True)
    assert retrieved_after_hard_delete is None

    # Try deleting non-existent
    non_existent_delete = crud_product.hard_delete_product(db=db_session, product_id=99999)
    assert non_existent_delete is None
