from sqlalchemy.orm import Session, joinedload
from typing import Optional, List

from app.models.order import Order
# from app.models.product import ProductPackage # Not directly needed if OrderCreateInternal has all data
from app.schemas.order import OrderCreateInternal, OrderUpdate
# from sqlalchemy import select # Not needed for these specific queries

def create_order(db: Session, *, obj_in: OrderCreateInternal) -> Order:
    """
    Create a new order.
    obj_in should be of type OrderCreateInternal which includes all necessary fields.
    """
    db_obj = Order(**obj_in.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_order(db: Session, order_id: int) -> Optional[Order]:
    """
    Get a single order by ID, with related product_package and reseller data eagerly loaded.
    """
    return (
        db.query(Order)
        .options(
            joinedload(Order.product_package),
            joinedload(Order.reseller)
        )
        .filter(Order.id == order_id)
        .first()
    )

def get_orders_by_reseller(
    db: Session, *, reseller_id: int, skip: int = 0, limit: int = 100
) -> List[Order]:
    """
    Get a list of orders for a specific reseller, ordered by creation date descending.
    Related product_package and reseller data are eagerly loaded.
    """
    return (
        db.query(Order)
        .options(
            joinedload(Order.product_package),
            joinedload(Order.reseller)
        )
        .filter(Order.reseller_id == reseller_id)
        .order_by(Order.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

def get_orders_by_customer(
    db: Session, *, customer_email: str, skip: int = 0, limit: int = 100
) -> List[Order]:
    """
    Get a list of orders for a specific customer email, ordered by creation date descending.
    Related product_package and reseller data are eagerly loaded.
    """
    return (
        db.query(Order)
        .options(
            joinedload(Order.product_package),
            joinedload(Order.reseller) # Reseller who made the sale
        )
        .filter(Order.customer_email == customer_email)
        .order_by(Order.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

def update_order(db: Session, *, db_obj: Order, obj_in: OrderUpdate) -> Order:
    """
    Update an order. Primarily used for updating status, stripe_payment_intent_id,
    and esim_provisioning_status.
    """
    update_data = obj_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_order_by_stripe_payment_intent(
    db: Session, *, payment_intent_id: str
) -> Optional[Order]:
    """
    Get a single order by its Stripe Payment Intent ID.
    Useful for webhooks. Eager loads product_package and reseller.
    """
    return (
        db.query(Order)
        .options(
            joinedload(Order.product_package),
            joinedload(Order.reseller)
        )
        .filter(Order.stripe_payment_intent_id == payment_intent_id)
        .first()
    )

def get_order_count_for_reseller(db: Session, *, reseller_id: int) -> int:
    """
    Get the total count of orders for a specific reseller.
    """
    return db.query(Order).filter(Order.reseller_id == reseller_id).count()

def get_order_count_for_customer(db: Session, *, customer_email: str) -> int:
    """
    Get the total count of orders for a specific customer email.
    """
    return db.query(Order).filter(Order.customer_email == customer_email).count()
