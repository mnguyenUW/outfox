"""Database models for Healthcare Cost Navigator."""
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

from sqlalchemy import (
    Column, Integer, String, DECIMAL, DateTime, 
    ForeignKey, UniqueConstraint, CheckConstraint,
    Index, text, Float
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from geoalchemy2 import Geography
from app.database import Base


class ZipCode(Base):
    """ZIP codes with geographic data."""
    __tablename__ = "zip_codes"
    
    zip_code: Mapped[str] = mapped_column(String(5), primary_key=True)
    city: Mapped[Optional[str]] = mapped_column(String(100))
    state_code: Mapped[Optional[str]] = mapped_column(String(2))
    state_name: Mapped[Optional[str]] = mapped_column(String(50))
    latitude: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 8))
    longitude: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(11, 8))
    location = Column(Geography(geometry_type='POINT', srid=4326))
    county: Mapped[Optional[str]] = mapped_column(String(100))
    timezone: Mapped[Optional[str]] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    def __repr__(self):
        return f"<ZipCode(zip={self.zip_code}, city='{self.city}', state='{self.state_code}')>"


class Provider(Base):
    """Healthcare providers table - matches CSV structure exactly."""
    __tablename__ = "providers"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Provider Information (from CSV)
    rndrng_prvdr_ccn: Mapped[Optional[str]] = mapped_column(String(10), index=True)
    rndrng_prvdr_org_name: Mapped[str] = mapped_column(String(255), nullable=False)
    rndrng_prvdr_city: Mapped[Optional[str]] = mapped_column(String(100))
    rndrng_prvdr_st: Mapped[Optional[str]] = mapped_column(String)  # Street address
    rndrng_prvdr_state_fips: Mapped[Optional[int]] = mapped_column(Integer)
    rndrng_prvdr_zip5: Mapped[Optional[str]] = mapped_column(String(5), index=True)
    rndrng_prvdr_state_abrvtn: Mapped[Optional[str]] = mapped_column(String(2), index=True)
    rndrng_prvdr_ruca: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(3, 1))
    rndrng_prvdr_ruca_desc: Mapped[Optional[str]] = mapped_column(String)
    
    # Medical Procedure Information
    drg_cd: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    drg_desc: Mapped[Optional[str]] = mapped_column(String)
    
    # Financial Data
    tot_dschrgs: Mapped[Optional[int]] = mapped_column(Integer)
    avg_submtd_cvrd_chrg: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(12, 2))
    avg_tot_pymt_amt: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(12, 2))
    avg_mdcr_pymt_amt: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(12, 2))
    
    # Geographic data (populated from zip_codes)
    latitude: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 8))
    longitude: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(11, 8))
    location = Column(Geography(geometry_type='POINT', srid=4326))
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    
    # Relationships
    ratings: Mapped[List["ProviderRating"]] = relationship(
        "ProviderRating",
        primaryjoin="Provider.rndrng_prvdr_ccn == foreign(ProviderRating.provider_ccn)",
        viewonly=True
    )
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("rndrng_prvdr_ccn", "drg_cd", name="uq_provider_drg"),
        CheckConstraint("tot_dschrgs >= 0", name="check_discharges_positive"),
        CheckConstraint("avg_submtd_cvrd_chrg >= 0", name="check_charges_positive"),
        CheckConstraint("avg_tot_pymt_amt >= 0", name="check_payment_positive"),
        CheckConstraint("avg_mdcr_pymt_amt >= 0", name="check_medicare_positive"),
        Index("idx_providers_drg_charges", "drg_cd", "avg_submtd_cvrd_chrg"),
    )
    
    def __repr__(self):
        return f"<Provider(ccn={self.rndrng_prvdr_ccn}, name='{self.rndrng_prvdr_org_name[:30]}...', drg={self.drg_cd})>"
    
    @property
    def average_rating(self) -> Optional[float]:
        """Calculate average rating across all categories."""
        if not self.ratings:
            return None
        total = sum(float(r.rating) for r in self.ratings)
        return round(total / len(self.ratings), 1)


class ProviderRating(Base):
    """Provider ratings table."""
    __tablename__ = "provider_ratings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider_ccn: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    rating: Mapped[Decimal] = mapped_column(DECIMAL(3, 1), nullable=False)
    rating_category: Mapped[Optional[str]] = mapped_column(String(50))
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("provider_ccn", "rating_category", name="uq_provider_rating_category"),
        CheckConstraint("rating >= 1.0 AND rating <= 10.0", name="check_rating_range"),
        Index("idx_provider_ratings_rating", "rating", postgresql_using="btree"),
    )
    
    def __repr__(self):
        return f"<ProviderRating(ccn={self.provider_ccn}, rating={self.rating}, category='{self.rating_category}')>"