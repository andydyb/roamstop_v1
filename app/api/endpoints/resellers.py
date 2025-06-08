from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from sqlalchemy.orm import Session
from typing import List, Optional # Added List, Optional

from app.crud import crud_reseller # Changed to import specific module
from app import schemas # Import schemas module
from app.core import dependencies # Import dependencies module
from app.db.session import get_db # Changed to import specific get_db
from app.models.reseller import ResellerProfile as ResellerModel # For type hinting

router = APIRouter()

@router.post("/register", response_model=ResellerSchema, status_code=201)
def register_reseller(reseller_in: ResellerCreate, db: Session = Depends(get_db)):
    """
    Register a new reseller.
    """
    existing_reseller = crud_reseller.get_reseller_by_email(db, email=reseller_in.email)
    if existing_reseller:
        raise HTTPException(
            status_code=400,
            detail="The reseller with this email already exists in the system.",
        )

    # Check for recruiter if ID is provided
    if reseller_in.recruiter_id:
        recruiter = crud_reseller.get_reseller(db, reseller_id=reseller_in.recruiter_id)
        if not recruiter:
            raise HTTPException(
                status_code=404,
                detail=f"Recruiter with id {reseller_in.recruiter_id} not found.",
            )
        # Potentially add logic here to check if the recruiter is allowed to recruit,
        # or if there are limits on recruitment, etc.

    new_reseller = crud_reseller.create_reseller(db=db, obj_in=reseller_in)
    return new_reseller

@router.get("/me", response_model=schemas.Reseller)
async def read_reseller_me(
    current_user: ResellerModel = Depends(dependencies.get_current_active_user)
):
    """
    Get current logged-in reseller's profile.
    """
    return current_user

@router.put("/me/promotion-details", response_model=schemas.Reseller)
async def update_reseller_promotion(
    *,
    db: Session = Depends(get_db),
    promotion_update: schemas.ResellerPromotionUpdate,
    current_user: ResellerModel = Depends(dependencies.get_current_active_user)
):
    """
    Update promotion details for the current logged-in reseller.
    """
    # We construct a ResellerUpdate schema to pass to the CRUD function,
    # ensuring only promotion_details is updated.
    reseller_update_schema = schemas.ResellerUpdate(promotion_details=promotion_update.promotion_details)

    updated_reseller = crud_reseller.update_reseller( # Corrected module access
        db=db,
        db_obj=current_user,
        obj_in=reseller_update_schema
    )
    return updated_reseller
