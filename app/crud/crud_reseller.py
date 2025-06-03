from sqlalchemy.orm import Session
from typing import Optional, List

from app.models.reseller import ResellerProfile
from app.schemas.reseller import ResellerCreate, ResellerUpdate
from app.core.security import get_password_hash

def get_reseller(db: Session, reseller_id: int) -> Optional[ResellerProfile]:
    return db.query(ResellerProfile).filter(ResellerProfile.id == reseller_id).first()

def get_reseller_by_email(db: Session, email: str) -> Optional[ResellerProfile]:
    return db.query(ResellerProfile).filter(ResellerProfile.email == email).first()

def create_reseller(db: Session, *, obj_in: ResellerCreate) -> ResellerProfile:
    hashed_password = get_password_hash(obj_in.password)

    db_obj = ResellerProfile(
        email=obj_in.email,
        hashed_password=hashed_password,
        reseller_type=obj_in.reseller_type,
        recruiter_id=obj_in.recruiter_id,
        business_name=obj_in.business_name,
        shipping_address=obj_in.shipping_address,
        promotion_details=obj_in.promotion_details,
        oauth_provider=obj_in.oauth_provider,
        oauth_user_id=obj_in.oauth_user_id,
        is_active=True, # Default to active on creation
        is_superuser=obj_in.is_superuser # Handle is_superuser from schema
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def update_reseller(db: Session, *, db_obj: ResellerProfile, obj_in: ResellerUpdate) -> ResellerProfile:
    # Pydantic V2 uses model_dump
    update_data = obj_in.model_dump(exclude_unset=True)

    if "password" in update_data and update_data["password"] is not None:
        hashed_password = get_password_hash(update_data["password"])
        update_data["hashed_password"] = hashed_password
        del update_data["password"]
    else:
        # Ensure password field is not accidentally set to None if not provided
        if "password" in update_data:
            del update_data["password"]

    for field, value in update_data.items():
        setattr(db_obj, field, value)

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_recruited_resellers(db: Session, *, recruiter_id: int, skip: int = 0, limit: int = 100) -> List[ResellerProfile]:
    return db.query(ResellerProfile).filter(ResellerProfile.recruiter_id == recruiter_id).offset(skip).limit(limit).all()
