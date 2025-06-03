from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from app.db.base_class import Base # Adjusted import path

class ResellerProfile(Base):
    __tablename__ = "reseller_profile"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)
    reseller_type = Column(String, nullable=False) # e.g., "MOBILE_FIELD", "VENUE_PARTNER"
    recruiter_id = Column(Integer, ForeignKey("reseller_profile.id"), nullable=True)
    business_name = Column(String, nullable=True)
    shipping_address = Column(String, nullable=True)
    promotion_details = Column(Text, nullable=True)
    oauth_provider = Column(String, nullable=True) # e.g., "google", "facebook"
    oauth_user_id = Column(String, nullable=True) # User ID from the OAuth provider
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False) # New field
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Self-referential relationship for recruiter/recruited
    recruiter = relationship("ResellerProfile", remote_side=[id], back_populates="recruited_resellers")
    recruited_resellers = relationship("ResellerProfile", back_populates="recruiter")

    # Add a unique constraint for oauth_provider and oauth_user_id if needed
    # For example, if a user can only link one account per provider
    # __table_args__ = (UniqueConstraint('oauth_provider', 'oauth_user_id', name='_oauth_user_provider_uc'),)

    def __repr__(self):
        return f"<ResellerProfile(id={self.id}, email='{self.email}', type='{self.reseller_type}')>"
