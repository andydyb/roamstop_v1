from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any
from datetime import datetime
from decimal import Decimal

# Forward references might be needed if full schemas are used and circular dependencies arise.
# However, for nested representations, it's often better to create specific, simplified schemas.

class CommissionNestedOrder(BaseModel):
    """A simplified Order schema for nesting within Commission."""
    id: int
    customer_email: Optional[EmailStr] = None # Changed to EmailStr for consistency
    created_at: datetime

    class Config:
        from_attributes = True

class CommissionNestedReseller(BaseModel):
    """A simplified Reseller schema for nesting within Commission."""
    id: int
    email: Optional[EmailStr] = None
    # business_name: Optional[str] = None # Example: could be added if needed

    class Config:
        from_attributes = True

class CommissionNestedProductPackage(BaseModel):
    """A simplified ProductPackage schema for nesting within Commission."""
    id: int
    name: Optional[str] = None

    class Config:
        from_attributes = True


class CommissionBase(BaseModel):
    order_id: int
    reseller_id: int # Earning reseller
    commission_type: str = Field(..., max_length=50)
    amount: Decimal
    currency: str = Field(..., max_length=3)
    product_package_id_at_sale: int
    original_order_reseller_id: Optional[int] = None
    commission_status: str = Field(..., max_length=50)
    calculation_details: Optional[Any] = None

class CommissionCreate(CommissionBase):
    """Schema for creating a commission record. Typically used internally by the system."""
    # Defaults from CommissionBase are usually sufficient if status is set upon creation logic
    pass

class CommissionUpdate(BaseModel):
    """Schema for updating a commission, primarily its status."""
    commission_status: str = Field(..., max_length=50)
    # calculation_details: Optional[Any] = None # If details can be updated
    # notes: Optional[str] = None # Example of another updatable field

class Commission(CommissionBase):
    """Full schema for returning commission data to the client."""
    id: int
    created_at: datetime
    updated_at: datetime

    order: Optional[CommissionNestedOrder] = None
    earning_reseller: Optional[CommissionNestedReseller] = None
    product_package: Optional[CommissionNestedProductPackage] = None # Added for product context
    triggering_reseller: Optional[CommissionNestedReseller] = None

    class Config:
        from_attributes = True
