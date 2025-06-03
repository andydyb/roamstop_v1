from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.reseller import ResellerCreate, Reseller as ResellerSchema
from app.crud import crud_reseller
# from app.models.reseller import ResellerProfile # Not strictly needed if CRUD handles all model interactions

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
