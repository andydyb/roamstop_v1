# app/api/endpoints/payments.py
import stripe # Stripe library
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Any # For type hinting if needed for stripe objects
from decimal import Decimal # For handling currency amounts

from app import crud
from app.models.order import Order as OrderModel
from app.models.reseller import ResellerProfile
from app.schemas.payment import PaymentIntentCreateRequest, PaymentIntentCreateResponse
from app.schemas.order import OrderUpdate
from app.db.session import get_db
from app.core.dependencies import get_current_active_user
from app.core.config import STRIPE_SECRET_KEY # For direct use if not globally set, or just rely on global set
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Ensure stripe.api_key is set. It should be set in config.py when imported.
# This check is more for runtime verification if config.py didn't log a warning.
if not stripe.api_key:
    if STRIPE_SECRET_KEY and "YOUR_STRIPE_SECRET_KEY" not in STRIPE_SECRET_KEY:
        stripe.api_key = STRIPE_SECRET_KEY
        logger.info("Stripe API key configured in payments.py (was not set by config.py import).")
    else:
        logger.warning("Stripe secret key is not properly configured. Payment endpoints may not work.")


@router.post("/create-payment-intent", response_model=PaymentIntentCreateResponse)
async def create_payment_intent_endpoint(
    *,
    db: Session = Depends(get_db),
    payload: PaymentIntentCreateRequest,
    current_user: ResellerProfile = Depends(get_current_active_user)
):
    order_id = payload.order_id
    logger.info(f"User {current_user.email} (ID: {current_user.id}) creating payment intent for order ID: {order_id}")

    order = crud.order.get_order(db, order_id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.reseller_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to create payment intent for this order")

    if order.order_status not in ["PENDING_PAYMENT", "AWAITING_PAYMENT"]:
        raise HTTPException(status_code=400, detail=f"Cannot create payment intent for order with status: {order.order_status}")

    if not stripe.api_key: # Check again in case it wasn't set by any means
        logger.error("Stripe API key is not configured. Cannot create payment intent.")
        raise HTTPException(status_code=500, detail="Payment system configuration error.")

    try:
        amount_in_cents = int(Decimal(order.price_paid) * 100) # Ensure price_paid is Decimal

        payment_intent_params = {
            'amount': amount_in_cents,
            'currency': order.currency_paid.lower(),
            'metadata': {
                'roamstop_order_id': str(order.id),
                'customer_email': order.customer_email,
                'reseller_id': str(order.reseller_id)
            }
        }

        payment_intent = None
        existing_pi_id = order.stripe_payment_intent_id
        if existing_pi_id:
            try:
                pi = stripe.PaymentIntent.retrieve(existing_pi_id)
                # Check if PI is still in a state that can be confirmed or needs a new payment method
                if pi.status in ['requires_payment_method', 'requires_confirmation', 'requires_action']:
                     # Check if key parameters like amount or currency have changed
                    if pi.amount == amount_in_cents and pi.currency == order.currency_paid.lower():
                        logger.info(f"Using existing PaymentIntent ID: {existing_pi_id} for order ID: {order_id}")
                        payment_intent = pi
                    else:
                        logger.info(f"Amount/currency changed for order ID: {order_id}. Creating new PaymentIntent.")
                        # Potentially cancel the old PI if appropriate: stripe.PaymentIntent.cancel(existing_pi_id)
                        payment_intent = stripe.PaymentIntent.create(**payment_intent_params)
                else:
                    logger.info(f"Existing PaymentIntent {existing_pi_id} status is {pi.status}. Creating new PaymentIntent for order ID: {order_id}")
                    payment_intent = stripe.PaymentIntent.create(**payment_intent_params)
            except stripe.error.StripeError as e:
                logger.warning(f"Error retrieving/updating existing PaymentIntent {existing_pi_id}: {e}. Creating new one.")
                payment_intent = stripe.PaymentIntent.create(**payment_intent_params)
        else:
            payment_intent = stripe.PaymentIntent.create(**payment_intent_params)

        order_update_data = OrderUpdate(
            stripe_payment_intent_id=payment_intent.id,
            order_status="AWAITING_PAYMENT"
        )
        crud.order.update_order(db=db, db_obj=order, obj_in=order_update_data)

        logger.info(f"PaymentIntent {payment_intent.id} created/retrieved for order ID: {order.id}")
        return PaymentIntentCreateResponse(
            client_secret=payment_intent.client_secret,
            order_id=order.id,
            payment_intent_id=payment_intent.id
        )

    except stripe.error.StripeError as e:
        logger.error(f"Stripe API error for order {order.id}: {e}")
        user_message = getattr(e, 'user_message', str(e))
        raise HTTPException(status_code=500, detail=f"Payment gateway error: {user_message}")
    except Exception as e:
        logger.error(f"Generic error creating payment intent for order {order.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error while creating payment intent.")
