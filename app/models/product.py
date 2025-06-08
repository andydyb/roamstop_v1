from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Numeric, ForeignKey
from sqlalchemy.sql import func
from app.db.base_class import Base

class ProductPackage(Base):
    __tablename__ = "product_package"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    duration_days = Column(Integer, nullable=False)
    country_code = Column(String(2), nullable=False, index=True)  # ISO 3166-1 alpha-2
    price = Column(Numeric(10, 2), nullable=False)
    direct_commission_rate_or_amount = Column(Numeric(10, 2), nullable=False)
    recruitment_commission_rate_or_amount = Column(Numeric(10, 2), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<ProductPackage(id={self.id}, name='{self.name}', country_code='{self.country_code}')>"
