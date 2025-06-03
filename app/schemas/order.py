from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal

from app.schemas.product import ProductPackage  # For nesting in Order schema
from app.schemas.reseller import Reseller     # For nesting in Order schema

class OrderBase(BaseModel):
    customer_email: EmailStr
    customer_name: Optional[str] = Field(default=None, max_length=255)
    product_package_id: int

class OrderCreate(OrderBase):
    """
    Schema for data provided by the user/client when initiating an order.
    - reseller_id is typically derived from the authenticated user or context.
    - price, currency, duration, country_code are derived from product_package_id.
    """
    pass

class OrderCreateInternal(OrderBase): # Used by CRUD operations internally
    """
    Schema for creating an order in the database, including fields derived
    by the system or set by default.
    """
    reseller_id: int
    price_paid: Decimal
    currency_paid: str = Field(default="USD", max_length=3)
    duration_days_at_purchase: int
    country_code_at_purchase: str = Field(max_length=2)
    order_status: str = Field(default="PENDING_PAYMENT", max_length=50)
    stripe_payment_intent_id: Optional[str] = Field(default=None, max_length=255)
    esim_provisioning_status: Optional[str] = Field(default="NOT_STARTED", max_length=50)


class OrderUpdate(BaseModel):
    """
    Schema for updating an order, typically for status changes by the system or an admin.
    """
    order_status: Optional[str] = Field(default=None, max_length=50)
    stripe_payment_intent_id: Optional[str] = Field(default=None, max_length=255)
    esim_provisioning_status: Optional[str] = Field(default=None, max_length=50)


class Order(OrderBase): # Full schema for returning order data to the client
    id: int
    reseller_id: int
    price_paid: Decimal
    currency_paid: str
    duration_days_at_purchase: int
    country_code_at_purchase: str
    order_status: str
    stripe_payment_intent_id: Optional[str] = None
    esim_provisioning_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    product_package: ProductPackage  # Nested product details
    reseller: Reseller               # Nested reseller details

    class Config:
        from_attributes = True
