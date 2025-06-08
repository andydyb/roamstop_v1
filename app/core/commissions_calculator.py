import logging
from sqlalchemy.orm import Session, joinedload, selectinload
from decimal import Decimal # Import Decimal for type checks if needed

from app.models.order import Order as OrderModel
from app.models.reseller import ResellerProfile as ResellerProfileModel
from app.models.product import ProductPackage as ProductPackageModel
from app.crud import crud_commission
from app.schemas.commission import CommissionCreate

logger = logging.getLogger(__name__)

async def calculate_and_record_commissions(db: Session, order: OrderModel):
    logger.info(f"Starting commission calculation for order ID: {order.id}")

    # Ensure product_package and reseller are loaded.
    # The order object passed might already have these eager-loaded.
    # If not, explicit loading is necessary.
    if not order.product_package:
        logger.info(f"Order ID: {order.id} - product_package not loaded, attempting to load.")
        # Option 1: Refresh (if order is already a persistent object from the same session)
        # db.refresh(order, ['product_package'])
        # Option 2: Query explicitly (safer if unsure about session state or if order is detached)
        order = db.query(OrderModel).options(joinedload(OrderModel.product_package)).filter(OrderModel.id == order.id).first()
        if not order: # Should not happen if order ID is valid
            logger.error(f"Failed to reload order ID: {order.id} to get product_package.")
            return

    if not order.product_package:
        logger.error(f"Order ID: {order.id} is still missing product_package information after attempting load. Cannot calculate commissions.")
        return
    product = order.product_package

    if not order.reseller:
        logger.info(f"Order ID: {order.id} - reseller (direct_seller) not loaded, attempting to load.")
        # Similar to product_package, ensure reseller is loaded
        if not order: # Re-fetch order if not already done for product_package
             order = db.query(OrderModel).options(joinedload(OrderModel.reseller)).filter(OrderModel.id == order.id).first()
        else: # If order was fetched for product, try to load reseller for that instance
             db.refresh(order, ['reseller']) # Or use selectinload if order is already loaded

        if not order or not order.reseller: # Check again after attempting load
            logger.error(f"Failed to reload order ID: {order.id} or reseller for it.")
            return
    direct_seller = order.reseller

    if not direct_seller.is_active:
        logger.info(f"Direct seller ID: {direct_seller.id} is inactive. No commissions will be recorded for order ID: {order.id}.")
        return

    # 1. Direct Sale Commission
    # Ensure direct_commission_rate_or_amount is Decimal or can be converted
    direct_commission_amount = Decimal(product.direct_commission_rate_or_amount or 0)

    if direct_commission_amount > 0:
        commission_direct_data = CommissionCreate(
            order_id=order.id,
            reseller_id=direct_seller.id,
            commission_type="DIRECT_SALE",
            amount=direct_commission_amount,
            currency=order.currency_paid,
            product_package_id_at_sale=product.id,
            original_order_reseller_id=direct_seller.id, # For direct sale, this is the same
            commission_status="UNPAID",
            calculation_details={
                "type": "fixed_amount", # Assuming it's a fixed amount, adjust if it's a rate
                "source_field": "direct_commission_rate_or_amount",
                "value": float(direct_commission_amount) # Store as float for JSON
            }
        )
        crud_commission.create_commission(db=db, obj_in=commission_direct_data)
        logger.info(f"Created DIRECT_SALE commission for order ID: {order.id}, reseller ID: {direct_seller.id}, amount: {direct_commission_amount}")
    else:
        logger.info(f"No direct commission applicable or amount is zero for order ID: {order.id}, product ID: {product.id}")

    # 2. Recruitment Commission (Tier 1)
    if direct_seller.recruiter_id:
        # Fetch the recruiter with is_active check
        recruiter = db.query(ResellerProfileModel).filter(
            ResellerProfileModel.id == direct_seller.recruiter_id,
            ResellerProfileModel.is_active == True # Ensure recruiter is active
        ).first()

        if recruiter:
            recruitment_commission_amount = Decimal(product.recruitment_commission_rate_or_amount or 0)
            if recruitment_commission_amount > 0:
                commission_recruitment_data = CommissionCreate(
                    order_id=order.id,
                    reseller_id=recruiter.id,
                    commission_type="RECRUITMENT_TIER_1",
                    amount=recruitment_commission_amount,
                    currency=order.currency_paid,
                    product_package_id_at_sale=product.id,
                    original_order_reseller_id=direct_seller.id,
                    commission_status="UNPAID",
                    calculation_details={
                        "type": "fixed_amount", # Assuming fixed amount
                        "source_field": "recruitment_commission_rate_or_amount",
                        "value": float(recruitment_commission_amount)
                    }
                )
                crud_commission.create_commission(db=db, obj_in=commission_recruitment_data)
                logger.info(f"Created RECRUITMENT_TIER_1 commission for order ID: {order.id}, recruiter ID: {recruiter.id}, amount: {recruitment_commission_amount}")
            else:
                logger.info(f"No recruitment commission applicable or amount is zero for order ID: {order.id}, product ID: {product.id}")
        else:
            logger.info(f"Recruiter ID: {direct_seller.recruiter_id} not found or is inactive for direct seller ID: {direct_seller.id}. No recruitment commission for order ID: {order.id}.")
    else:
        logger.info(f"Direct seller ID: {direct_seller.id} has no recruiter. No recruitment commission for order ID: {order.id}.")

    logger.info(f"Commission calculation finished for order ID: {order.id}")
