from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal

class ProductPackageBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    duration_days: int = Field(..., gt=0) # Duration must be positive
    country_code: str = Field(..., min_length=2, max_length=2) # Basic validation for 2 chars
    price: Decimal = Field(..., gt=0) # Price must be positive
    direct_commission_rate_or_amount: Decimal = Field(..., ge=0) # Commission can be 0
    recruitment_commission_rate_or_amount: Decimal = Field(..., ge=0) # Commission can be 0
    is_active: bool = True

class ProductPackageCreate(ProductPackageBase):
    pass

class ProductPackageUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    duration_days: Optional[int] = Field(default=None, gt=0)
    country_code: Optional[str] = Field(default=None, min_length=2, max_length=2)
    price: Optional[Decimal] = Field(default=None, gt=0)
    direct_commission_rate_or_amount: Optional[Decimal] = Field(default=None, ge=0)
    recruitment_commission_rate_or_amount: Optional[Decimal] = Field(default=None, ge=0)
    is_active: Optional[bool] = None

class ProductPackageInDBBase(ProductPackageBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ProductPackage(ProductPackageInDBBase):
    pass
