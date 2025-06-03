from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

class Order(Base):
    __tablename__ = "order"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    customer_email = Column(String(255), nullable=False, index=True)
    customer_name = Column(String(255), nullable=True)

    product_package_id = Column(Integer, ForeignKey("product_package.id"), nullable=False)
    reseller_id = Column(Integer, ForeignKey("reseller_profile.id"), nullable=False) # Direct sale reseller

    price_paid = Column(Numeric(10, 2), nullable=False)
    currency_paid = Column(String(3), nullable=False, default="USD") # e.g., "USD", "EUR"
    duration_days_at_purchase = Column(Integer, nullable=False)
    country_code_at_purchase = Column(String(2), nullable=False)

    order_status = Column(String(50), nullable=False, default="PENDING_PAYMENT", index=True)
    # e.g., PENDING_PAYMENT, PROCESSING, COMPLETED, FAILED_PAYMENT, FAILED_PROVISIONING, CANCELLED, REFUNDED

    stripe_payment_intent_id = Column(String(255), nullable=True, index=True, unique=True)
    esim_provisioning_status = Column(String(50), nullable=True, default="NOT_STARTED")
    # e.g., NOT_STARTED, REQUESTED, SUCCESS, FAILED

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    product_package = relationship("ProductPackage")
    reseller = relationship("ResellerProfile")

    def __repr__(self):
        return f"<Order(id={self.id}, customer_email='{self.customer_email}', product_package_id={self.product_package_id}, status='{self.order_status}')>"
