from sqlalchemy.orm import Session, joinedload
from typing import Optional, List

from app.models.commission import Commission
from app.models.order import Order # For relationship loading
from app.models.reseller import ResellerProfile # For relationship loading
from app.models.product import ProductPackage # For relationship loading
from app.schemas.commission import CommissionCreate, CommissionUpdate
# CommissionUpdate might be used if we make a generic update function later

def create_commission(db: Session, *, obj_in: CommissionCreate) -> Commission:
    """
    Create a new commission record.
    """
    db_obj = Commission(**obj_in.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_commission(db: Session, commission_id: int) -> Optional[Commission]:
    """
    Get a single commission by ID with related data eagerly loaded.
    """
    return (
        db.query(Commission)
        .options(
            joinedload(Commission.order).joinedload(Order.product_package), # Order -> ProductPackage
            joinedload(Commission.order).joinedload(Order.reseller), # Order -> Reseller who made the sale
            joinedload(Commission.earning_reseller), # Reseller who earned this specific commission
            joinedload(Commission.product_package), # Product package linked directly to commission (snapshot)
            joinedload(Commission.triggering_reseller) # Reseller whose sale triggered this (for recruitment)
        )
        .filter(Commission.id == commission_id)
        .first()
    )

def get_commissions_by_reseller(
    db: Session, *, reseller_id: int, status: Optional[str] = None, skip: int = 0, limit: int = 100
) -> List[Commission]:
    """
    Get commissions for a specific reseller, optionally filtered by status.
    Eager loads order and product_package (snapshot).
    """
    query = (
        db.query(Commission)
        .options(
            joinedload(Commission.order),
            joinedload(Commission.product_package) # Product package snapshot
        )
        .filter(Commission.reseller_id == reseller_id)
    )
    if status:
        query = query.filter(Commission.commission_status == status)

    return query.order_by(Commission.created_at.desc()).offset(skip).limit(limit).all()

def update_commission_status(db: Session, *, commission_id: int, status: str) -> Optional[Commission]:
    """
    Update the status of a specific commission.
    """
    db_commission = db.query(Commission).filter(Commission.id == commission_id).first()
    if db_commission:
        db_commission.commission_status = status
        # db.add(db_commission) # Not strictly necessary as object is already in session
        db.commit()
        db.refresh(db_commission)
        return db_commission
    return None

def get_unpaid_commissions_for_reseller(
    db: Session, *, reseller_id: int, skip: int = 0, limit: int = 100
) -> List[Commission]:
    """
    Get 'unpaid' commissions for a reseller.
    'Unpaid' includes PENDING_VALIDATION, UNPAID, READY_FOR_PAYOUT.
    Orders by creation date ascending to process older ones first.
    """
    unpaid_statuses = ["PENDING_VALIDATION", "UNPAID", "READY_FOR_PAYOUT"]
    return (
        db.query(Commission)
        .options(joinedload(Commission.order)) # Eager load order for context
        .filter(
            Commission.reseller_id == reseller_id,
            Commission.commission_status.in_(unpaid_statuses)
        )
        .order_by(Commission.created_at.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )

def get_commissions_by_order_id(db: Session, *, order_id: int) -> List[Commission]:
    """
    Get all commissions associated with a specific order ID.
    Eager loads related data for context.
    """
    return (
        db.query(Commission)
        .options(
            joinedload(Commission.earning_reseller),
            joinedload(Commission.product_package),
            joinedload(Commission.triggering_reseller)
        )
        .filter(Commission.order_id == order_id)
        .all()
    )
