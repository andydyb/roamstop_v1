from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional

from app.crud import crud_order, crud_product # crud_reseller is not directly used here
from app.schemas.order import (
    Order,
    OrderCreate,
    OrderUpdate,
    OrderCreateInternal,
)
# from app.models.product import ProductPackage # Not directly needed if using CRUD
from app.models.reseller import ResellerProfile # For type hinting current_user
from app.db.session import get_db
from app.core.dependencies import get_current_active_user, get_current_active_superuser

router = APIRouter()

@router.post("/", response_model=Order, status_code=201)
async def create_new_order(
    order_in: OrderCreate,
    db: Session = Depends(get_db),
    current_user: ResellerProfile = Depends(get_current_active_user)
):
    """
    Create a new order. The authenticated user is the reseller for this sale.
    Product details (price, duration, country) are fetched from the database.
    """
    reseller_id = current_user.id

    # Get product details to confirm price, duration, country_code
    product = crud_product.get_product(db, product_id=order_in.product_package_id, show_inactive=False) # Ensure product is active
    if not product: # crud_product.get_product returns None if not found or not active (if show_inactive=False)
        raise HTTPException(status_code=404, detail="Product not found or not active")

    # Prepare OrderCreateInternal data
    order_internal_data = OrderCreateInternal(
        customer_email=order_in.customer_email,
        customer_name=order_in.customer_name,
        product_package_id=order_in.product_package_id,
        reseller_id=reseller_id,
        price_paid=product.price,  # Price from product at time of purchase
        currency_paid="USD",      # Assuming USD for now, or from product/system config
        duration_days_at_purchase=product.duration_days,
        country_code_at_purchase=product.country_code
        # Default status (PENDING_PAYMENT) and other defaults will be set by OrderCreateInternal schema
    )

    return crud_order.create_order(db=db, obj_in=order_internal_data)

@router.get("/my-sales/", response_model=List[Order])
async def read_my_sales(
    db: Session = Depends(get_db),
    current_user: ResellerProfile = Depends(get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200)
):
    """
    Retrieve sales made by the currently authenticated reseller.
    """
    return crud_order.get_orders_by_reseller(db, reseller_id=current_user.id, skip=skip, limit=limit)

@router.get("/{order_id}", response_model=Order)
async def read_order_details(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: ResellerProfile = Depends(get_current_active_user)
):
    """
    Retrieve details for a specific order.
    A reseller can only view their own sales. Superusers can view any order.
    """
    db_order = crud_order.get_order(db, order_id=order_id)
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")

    if not current_user.is_superuser and db_order.reseller_id != current_user.id:
        # Future: Could allow customer to view their own order if customer auth is implemented
        raise HTTPException(status_code=403, detail="Not authorized to view this order")

    return db_order

@router.patch("/{order_id}", response_model=Order, tags=["Admin Orders"]) # Tagging as Admin as it's a privileged op
async def update_existing_order_status( # Renamed for clarity, as OrderUpdate is limited
    order_id: int,
    order_in: OrderUpdate,
    db: Session = Depends(get_db),
    current_user: ResellerProfile = Depends(get_current_active_superuser) # Only superusers can update
):
    """
    Update an existing order's status, Stripe ID, or E-SIM provisioning status.
    Requires superuser privileges.
    """
    db_order = crud_order.get_order(db, order_id=order_id) # get_order fetches with relations
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")

    return crud_order.update_order(db=db, db_obj=db_order, obj_in=order_in)

# Admin specific endpoints
@router.get("/admin/by-reseller/{reseller_id}", response_model=List[Order], tags=["Admin Orders"])
async def admin_read_orders_by_reseller(
    reseller_id: int,
    db: Session = Depends(get_db),
    current_user: ResellerProfile = Depends(get_current_active_superuser),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200)
):
    """
    Admin: Retrieve all orders associated with a specific reseller ID.
    """
    # Check if reseller exists (optional, but good practice)
    # existing_reseller = crud_reseller.get_reseller(db, reseller_id=reseller_id)
    # if not existing_reseller:
    #     raise HTTPException(status_code=404, detail=f"Reseller with id {reseller_id} not found.")
    return crud_order.get_orders_by_reseller(db, reseller_id=reseller_id, skip=skip, limit=limit)

@router.get("/admin/by-customer/", response_model=List[Order], tags=["Admin Orders"])
async def admin_read_orders_by_customer(
    customer_email: str = Query(..., description="Customer email to search orders for."),
    db: Session = Depends(get_db),
    current_user: ResellerProfile = Depends(get_current_active_superuser),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200)
):
    """
    Admin: Retrieve all orders for a specific customer email.
    """
    return crud_order.get_orders_by_customer(db, customer_email=customer_email, skip=skip, limit=limit)
