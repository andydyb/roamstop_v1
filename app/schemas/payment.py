# app/schemas/payment.py
from pydantic import BaseModel

class PaymentIntentCreateRequest(BaseModel):
    order_id: int

class PaymentIntentCreateResponse(BaseModel):
    client_secret: str
    order_id: int
    payment_intent_id: str
