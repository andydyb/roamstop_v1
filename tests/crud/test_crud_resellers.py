import pytest
from sqlalchemy.orm import Session
import uuid

from app.crud import crud_reseller
from app.schemas.reseller import ResellerCreate, ResellerUpdate
from app.models.reseller import ResellerProfile
# from app.core.security import get_password_hash # Not strictly needed if we check for non-None hashed_password

pytestmark = pytest.mark.crud

def test_create_reseller(db_session: Session):
    email = f"crud_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "password123"
    reseller_type = "MOBILE_FIELD"

    reseller_in = ResellerCreate(
        email=email,
        password=password,
        reseller_type=reseller_type,
        business_name="Test Biz",
        shipping_address="123 Test St"
    )

    db_reseller = crud_reseller.create_reseller(db=db_session, obj_in=reseller_in)

    assert db_reseller is not None
    assert db_reseller.email == email
    assert db_reseller.reseller_type == reseller_type
    assert db_reseller.business_name == "Test Biz"
    assert db_reseller.id is not None
    assert db_reseller.hashed_password is not None # Check that password got hashed
    assert db_reseller.is_active is True

def test_get_reseller(db_session: Session):
    email = f"get_test_{uuid.uuid4().hex[:8]}@example.com"
    reseller_in = ResellerCreate(email=email, password="password123", reseller_type="VENUE_PARTNER")
    created_reseller = crud_reseller.create_reseller(db=db_session, obj_in=reseller_in)

    retrieved_reseller = crud_reseller.get_reseller(db=db_session, reseller_id=created_reseller.id)

    assert retrieved_reseller is not None
    assert retrieved_reseller.id == created_reseller.id
    assert retrieved_reseller.email == email

def test_get_reseller_non_existent(db_session: Session):
    retrieved_reseller = crud_reseller.get_reseller(db=db_session, reseller_id=99999)
    assert retrieved_reseller is None

def test_get_reseller_by_email(db_session: Session):
    email = f"get_email_test_{uuid.uuid4().hex[:8]}@example.com"
    reseller_in = ResellerCreate(email=email, password="password123", reseller_type="MOBILE_FIELD")
    created_reseller = crud_reseller.create_reseller(db=db_session, obj_in=reseller_in)

    retrieved_reseller = crud_reseller.get_reseller_by_email(db=db_session, email=email)

    assert retrieved_reseller is not None
    assert retrieved_reseller.id == created_reseller.id
    assert retrieved_reseller.email == email

def test_get_reseller_by_email_non_existent(db_session: Session):
    retrieved_reseller = crud_reseller.get_reseller_by_email(db=db_session, email="nonexistent@example.com")
    assert retrieved_reseller is None

def test_update_reseller(db_session: Session):
    email = f"update_test_{uuid.uuid4().hex[:8]}@example.com"
    reseller_in = ResellerCreate(email=email, password="password123", reseller_type="VENUE_PARTNER")
    db_obj = crud_reseller.create_reseller(db=db_session, obj_in=reseller_in)

    update_data_dict = {
        "business_name": "Updated Biz Name",
        "promotion_details": "Updated promo details for reseller",
        "is_active": False
    }
    reseller_update_schema = ResellerUpdate(**update_data_dict)

    updated_reseller = crud_reseller.update_reseller(db=db_session, db_obj=db_obj, obj_in=reseller_update_schema)

    assert updated_reseller is not None
    assert updated_reseller.business_name == "Updated Biz Name"
    assert updated_reseller.promotion_details == "Updated promo details for reseller"
    assert updated_reseller.is_active is False
    assert updated_reseller.email == email # Email should not change unless specified

def test_update_reseller_password(db_session: Session):
    email = f"update_pass_test_{uuid.uuid4().hex[:8]}@example.com"
    old_password = "oldpassword"
    new_password = "newpassword"

    reseller_in = ResellerCreate(email=email, password=old_password, reseller_type="MOBILE_FIELD")
    db_obj = crud_reseller.create_reseller(db=db_session, obj_in=reseller_in)
    original_hashed_password = db_obj.hashed_password

    reseller_update_schema = ResellerUpdate(password=new_password)
    updated_reseller = crud_reseller.update_reseller(db=db_session, db_obj=db_obj, obj_in=reseller_update_schema)

    assert updated_reseller is not None
    assert updated_reseller.hashed_password is not None
    assert updated_reseller.hashed_password != original_hashed_password
    # To fully verify, you'd use verify_password from security.py
    # from app.core.security import verify_password
    # assert verify_password(new_password, updated_reseller.hashed_password)
    # assert not verify_password(old_password, updated_reseller.hashed_password)

def test_get_recruited_resellers(db_session: Session):
    # 1. Create Recruiter
    recruiter_email = f"recruiter_crud_{uuid.uuid4().hex[:8]}@example.com"
    recruiter_in = ResellerCreate(email=recruiter_email, password="password123", reseller_type="MOBILE_FIELD")
    recruiter = crud_reseller.create_reseller(db=db_session, obj_in=recruiter_in)

    # 2. Create Recruits
    recruit1_email = f"recruit1_crud_{uuid.uuid4().hex[:8]}@example.com"
    recruit1_in = ResellerCreate(email=recruit1_email, password="password123", reseller_type="VENUE_PARTNER", recruiter_id=recruiter.id)
    crud_reseller.create_reseller(db=db_session, obj_in=recruit1_in)

    recruit2_email = f"recruit2_crud_{uuid.uuid4().hex[:8]}@example.com"
    recruit2_in = ResellerCreate(email=recruit2_email, password="password123", reseller_type="MOBILE_FIELD", recruiter_id=recruiter.id)
    crud_reseller.create_reseller(db=db_session, obj_in=recruit2_in)

    # 3. Create another reseller not recruited by this recruiter
    other_reseller_email = f"other_crud_{uuid.uuid4().hex[:8]}@example.com"
    other_reseller_in = ResellerCreate(email=other_reseller_email, password="password123", reseller_type="VENUE_PARTNER")
    crud_reseller.create_reseller(db=db_session, obj_in=other_reseller_in)

    # 4. Get recruited resellers
    recruited_list = crud_reseller.get_recruited_resellers(db=db_session, recruiter_id=recruiter.id)
    assert len(recruited_list) == 2
    recruited_emails = {r.email for r in recruited_list}
    assert recruit1_email in recruited_emails
    assert recruit2_email in recruited_emails

    # Test pagination (limit)
    recruited_limited = crud_reseller.get_recruited_resellers(db=db_session, recruiter_id=recruiter.id, limit=1)
    assert len(recruited_limited) == 1

    # Test pagination (skip)
    recruited_skipped = crud_reseller.get_recruited_resellers(db=db_session, recruiter_id=recruiter.id, skip=1, limit=1)
    assert len(recruited_skipped) == 1
    # Ensure skipped one is different from the first one if order is consistent (requires ordering in query for robust test)
    # For now, just checking count is fine based on current get_recruited_resellers implementation.

def test_get_recruited_resellers_no_recruits(db_session: Session):
    recruiter_email = f"lonely_recruiter_{uuid.uuid4().hex[:8]}@example.com"
    recruiter_in = ResellerCreate(email=recruiter_email, password="password123", reseller_type="MOBILE_FIELD")
    recruiter = crud_reseller.create_reseller(db=db_session, obj_in=recruiter_in)

    recruited_list = crud_reseller.get_recruited_resellers(db=db_session, recruiter_id=recruiter.id)
    assert len(recruited_list) == 0
