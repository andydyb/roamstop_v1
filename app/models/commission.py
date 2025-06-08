from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Numeric, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

class Commission(Base):
    __tablename__ = "commission"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("order.id"), nullable=False, index=True)
    reseller_id = Column(Integer, ForeignKey("reseller_profile.id"), nullable=False, index=True) # Reseller who earned this commission

    commission_type = Column(String(50), nullable=False, index=True) # E.g., "DIRECT_SALE", "RECRUITMENT_TIER_1"
    amount = Column(Numeric(10, 2), nullable=False) # Calculated commission amount
    currency = Column(String(3), nullable=False, default="USD") # E.g., "USD"

    product_package_id_at_sale = Column(Integer, ForeignKey("product_package.id"), nullable=False)
    original_order_reseller_id = Column(Integer, ForeignKey("reseller_profile.id"), nullable=True, index=True) # For recruitment commissions: the reseller who made the actual sale

    commission_status = Column(String(50), nullable=False, default="PENDING_VALIDATION", index=True) # E.g., PENDING_VALIDATION, UNPAID, READY_FOR_PAYOUT, PAID, CANCELLED
    calculation_details = Column(JSON, nullable=True) # Store how commission was derived (e.g., rate, base price)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    order = relationship("Order", backref="commissions") # Added backref to Order

    # Reseller who earned this commission
    earning_reseller = relationship("ResellerProfile", foreign_keys=[reseller_id], backref="commissions_earned")

    # Product package for which this commission was generated
    product_package = relationship("ProductPackage") # No backref specified, as per plan

    # For recruitment commissions, this is the reseller whose direct sale triggered this commission
    # This relationship helps trace the origin of a recruitment commission.
    triggering_reseller = relationship("ResellerProfile", foreign_keys=[original_order_reseller_id], backref="triggered_recruitment_commissions")

    def __repr__(self):
        return f"<Commission(id={self.id}, order_id={self.order_id}, reseller_id={self.reseller_id}, type='{self.commission_type}', amount={self.amount})>"
