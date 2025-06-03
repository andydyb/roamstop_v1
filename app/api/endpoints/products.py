from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.crud import crud_product
from app.schemas.product import (
    ProductPackage,
    ProductPackageCreate,
    ProductPackageUpdate,
    ProductPackage as ProductPackageSchema
)
from app.db.session import get_db
from app.core.dependencies import get_current_active_superuser, get_current_active_user, get_current_user # Explicitly import get_current_user
from app.models.reseller import ResellerProfile # For type hinting current_user

router = APIRouter()

@router.post("/", response_model=ProductPackageSchema, status_code=201)
def create_product_package(
    product_in: ProductPackageCreate,
    db: Session = Depends(get_db),
    current_user: ResellerProfile = Depends(get_current_active_superuser) # Admin only
):
    """
    Create a new product package. Requires superuser privileges.
    """
    return crud_product.create_product(db=db, obj_in=product_in)

@router.get("/", response_model=List[ProductPackageSchema])
def read_products(
    db: Session = Depends(get_db),
    country_code: Optional[str] = Query(None, min_length=2, max_length=2, description="Filter by ISO 3166-1 alpha-2 country code"),
    is_active: Optional[bool] = Query(True, description="Filter by active status. Set to None to get all (admin might need this)."), # Default true for public
    show_inactive_for_admin: bool = Query(False, description="Admin flag to also show inactive products when is_active is None or True."),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: Optional[ResellerProfile] = Depends(get_current_user) # Optional current user to adjust behavior
):
    """
    Retrieve product packages.
    - Public users see active products by default.
    - Admins can see inactive products using `show_inactive_for_admin=True` combined with `is_active` flags.
    """
    effective_is_active_filter = is_active
    if current_user and current_user.is_superuser and show_inactive_for_admin:
        # If admin wants to see all (active=None) or specifically inactive (active=False) including those marked inactive
        if is_active is None: # Admin wants all (active and inactive)
             effective_is_active_filter = None
        # if is_active is True, admin sees active. If is_active is False, admin sees inactive.
        # This logic simplifies: admin can use is_active=None to see all, or is_active=False for only inactive.
        # The `show_inactive_for_admin` isn't strictly necessary if admin can set `is_active=None`.
        # Let's simplify: if admin, they can set is_active to None.
        pass # Admin can use the is_active filter as is.
    elif not (current_user and current_user.is_superuser): # Non-admin or anonymous
        effective_is_active_filter = True # Force active for non-admins if they try to set it to False or None


    if country_code:
        return crud_product.get_products_by_country(
            db=db, country_code=country_code, is_active=effective_is_active_filter, skip=skip, limit=limit
        )
    else:
        return crud_product.get_all_products(db=db, is_active=effective_is_active_filter, skip=skip, limit=limit)


@router.get("/{product_id}", response_model=ProductPackageSchema)
def read_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[ResellerProfile] = Depends(get_current_user) # Optional: to allow admin to see inactive
):
    """
    Get a specific product package by ID.
    Admins can see inactive products, public users only see active ones.
    """
    show_inactive_product = False
    if current_user and current_user.is_superuser:
        show_inactive_product = True

    db_product = crud_product.get_product(db, product_id=product_id, show_inactive=show_inactive_product)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found or not accessible")

    # Additional check if non-admin tries to access an inactive product directly if get_product didn't filter
    if not show_inactive_product and not db_product.is_active:
         raise HTTPException(status_code=404, detail="Product not found or not accessible")

    return db_product

@router.put("/{product_id}", response_model=ProductPackageSchema)
def update_product_package(
    product_id: int,
    product_in: ProductPackageUpdate,
    db: Session = Depends(get_db),
    current_user: ResellerProfile = Depends(get_current_active_superuser) # Admin only
):
    """
    Update a product package. Requires superuser privileges.
    Superusers can update a product even if it's inactive.
    """
    db_product = crud_product.get_product(db, product_id=product_id, show_inactive=True) # Superuser can see/update inactive
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return crud_product.update_product(db=db, db_obj=db_product, obj_in=product_in)

@router.delete("/{product_id}", response_model=ProductPackageSchema)
def delete_product_package(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: ResellerProfile = Depends(get_current_active_superuser) # Admin only
):
    """
    Logically delete a product package (set as inactive). Requires superuser privileges.
    """
    deleted_product = crud_product.delete_product(db=db, product_id=product_id)
    if not deleted_product : # crud_product.delete_product returns the object even if it was already inactive
        raise HTTPException(status_code=404, detail="Product not found")
    # If delete_product now only returns if it *was* active and changed, this check is fine.
    # If it returns the object if found (even if already inactive), then no specific error if already inactive.
    # Based on current crud_product.delete_product, it returns the object if found.
    return deleted_product
