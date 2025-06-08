from fastapi import APIRouter, Depends, HTTPException, Query # Added Query
from sqlalchemy.orm import Session

from typing import List, Optional # Added List, Optional

from app.crud import crud_reseller # Changed to import specific module
from app import schemas # Import schemas module
from app.core import dependencies # Import dependencies module
from app.db.session import get_db # Changed to import specific get_db
from app.models.reseller import ResellerProfile as ResellerModel # For type hinting
from app.schemas.commission import Commission as CommissionSchema # Explicit import for clarity

router = APIRouter()

@router.post("/register", response_model=schemas.reseller.Reseller, status_code=201) # Corrected path
def register_reseller(reseller_in: schemas.reseller.ResellerCreate, db: Session = Depends(get_db)): # Corrected path
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

@router.get("/me", response_model=schemas.reseller.Reseller) # Corrected path
async def read_reseller_me(
    current_user: ResellerModel = Depends(dependencies.get_current_active_user)
):
    """
    Get current logged-in reseller's profile.
    """
    return current_user

@router.put("/me/promotion-details", response_model=schemas.reseller.Reseller) # Corrected path
async def update_reseller_promotion(
    *,
    db: Session = Depends(get_db),
    promotion_update: schemas.reseller.ResellerPromotionUpdate, # Corrected path
    current_user: ResellerModel = Depends(dependencies.get_current_active_user)
):
    """
    Update promotion details for the current logged-in reseller.
    """
    # We construct a ResellerUpdate schema to pass to the CRUD function,
    # ensuring only promotion_details is updated.
    reseller_update_schema = schemas.reseller.ResellerUpdate(promotion_details=promotion_update.promotion_details) # Corrected path

    updated_reseller = crud_reseller.update_reseller(
        db=db,
        db_obj=current_user,
        obj_in=reseller_update_schema
    )
    return updated_reseller

@router.get("/me/commissions", response_model=List[CommissionSchema]) # Use imported CommissionSchema
async def read_my_commissions(
    db: Session = Depends(get_db),
    current_user: ResellerModel = Depends(dependencies.get_current_active_user),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200)
):
    """
    Retrieve commissions for the currently authenticated reseller.
    Optionally filter by commission status.
    """
    # Need to import crud_commission for this
    from app.crud import crud_commission as crud_commission_module
    commissions = crud_commission_module.get_commissions_by_reseller(
        db, reseller_id=current_user.id, status=status, skip=skip, limit=limit
    )
    if not commissions and status is None: # Only raise 404 if no commissions at all and no filter
        # Or simply return empty list, which is often preferred for list endpoints
        # For now, let's align with how test_read_my_commissions_empty expects a 200 with empty list
        pass
    # If status is provided and no commissions match, an empty list is also fine.
    # The 404 in tests for this was because the endpoint itself was missing.
    return commissions
