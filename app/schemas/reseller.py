from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class ResellerBase(BaseModel):
    email: EmailStr
    reseller_type: str
    business_name: Optional[str] = None
    shipping_address: Optional[str] = None
    promotion_details: Optional[str] = None
    oauth_provider: Optional[str] = None
    oauth_user_id: Optional[str] = None
    is_superuser: bool = False

class ResellerCreate(ResellerBase):
    password: str
    recruiter_id: Optional[int] = None

class ResellerUpdate(BaseModel): # Changed to BaseModel for more flexibility, only include fields that can be updated
    email: Optional[EmailStr] = None
    reseller_type: Optional[str] = None
    business_name: Optional[str] = None
    shipping_address: Optional[str] = None
    promotion_details: Optional[str] = None
    oauth_provider: Optional[str] = None # Usually not updated, but can be if needed
    oauth_user_id: Optional[str] = None  # Usually not updated
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    password: Optional[str] = None
    recruiter_id: Optional[int] = None # Allow changing recruiter if necessary

class ResellerInDBBase(ResellerBase):
    id: int
    is_active: bool
    is_superuser: bool # Ensure this is reflected from DB
    created_at: datetime
    updated_at: datetime
    recruiter_id: Optional[int] = None
    # is_superuser is inherited from ResellerBase and should be correctly populated by orm_mode / from_attributes

    class Config:
        from_attributes = True

class Reseller(ResellerInDBBase):
    # is_superuser will be available here through ResellerInDBBase -> ResellerBase
    pass

class ResellerWithRecruits(Reseller):
    recruited_resellers: List[Reseller] = []
    # is_superuser will be available here
