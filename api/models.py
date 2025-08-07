"""
SQLAlchemy models for BrightStone Property Monitoring System
Updated for single-document pipeline architecture
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON, ForeignKey, Float, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db import Base
import uuid

# =====================================================
# Global Entities (Company-Agnostic)
# =====================================================

class Municipality(Base):
    __tablename__ = "municipalities"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    feed_url = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    meetings = relationship("Meeting", back_populates="municipality")
    company_municipalities = relationship("CompanyMunicipality", back_populates="municipality")
    properties = relationship("Property", back_populates="municipality")

class Meeting(Base):
    __tablename__ = "meetings"
    
    id = Column(Integer, primary_key=True)
    guid = Column(String(255), unique=True, nullable=False)
    municipality_id = Column(Integer, ForeignKey("municipalities.id"), nullable=False)
    type = Column(String(100), nullable=False)
    start_at_local = Column(DateTime(timezone=True))
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    municipality = relationship("Municipality", back_populates="meetings")
    documents = relationship("Document", back_populates="meeting")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False)
    meeting_title = Column(String(500))
    kind = Column(String(50), nullable=False)
    format = Column(String(10), nullable=False)
    url = Column(Text, nullable=False)
    document_id = Column(Integer)
    downloaded = Column(Boolean, default=False)
    download_path = Column(Text)
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    storage_key = Column(String(500))
    size_bytes = Column(Integer)
    etag = Column(String(255))
    last_modified = Column(DateTime(timezone=True))
    content_hash = Column(String(32))
    storage_type = Column(String(10), default='s3')
    status = Column(String(20), default='discovered')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
    review_status = Column(String(20), default='new')
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Relationships
    meeting = relationship("Meeting", back_populates="documents")
    alerts = relationship("Alert", back_populates="document")
    audit_trails = relationship("AuditTrail", back_populates="document")
    resolved_by_user = relationship("User", foreign_keys=[resolved_by])

# =====================================================
# Company and User Models
# =====================================================

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True)
    company_id = Column(String(100), unique=True, nullable=False)  # Slug identifier
    name = Column(String(255), nullable=False)
    storage_prefix = Column(String(100))
    email_config = Column(JSON)
    rules_json = Column(JSON)  # Renamed from rules_config
    openai_api_key = Column(Text, default='')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    users = relationship("User", back_populates="company")
    properties = relationship("Property", back_populates="company")
    alerts = relationship("Alert", back_populates="company")
    audit_trails = relationship("AuditTrail", back_populates="company")
    company_municipalities = relationship("CompanyMunicipality", back_populates="company")
    ingest_jobs = relationship("IngestJob", back_populates="company")

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(Integer, ForeignKey("companies.id"))
    email = Column(Text, unique=True, nullable=False)
    role = Column(Text, nullable=False)  # 'admin' or 'analyst'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    auth0_id = Column(Text, unique=True)
    last_login = Column(DateTime(timezone=True))
    first_name = Column(String(255))
    last_name = Column(String(255))
    
    # Relationships
    company = relationship("Company", back_populates="users")
    invited_users = relationship("User", foreign_keys=[invited_by])

# =====================================================
# Link Table for Company-Municipality Subscriptions
# =====================================================

class CompanyMunicipality(Base):
    __tablename__ = "company_municipalities"
    
    company_id = Column(Integer, ForeignKey("companies.id"), primary_key=True)
    municipality_id = Column(Integer, ForeignKey("municipalities.id"), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    company = relationship("Company", back_populates="company_municipalities")
    municipality = relationship("Municipality", back_populates="company_municipalities")

# =====================================================
# Tenant-Specific Models (Company-Scoped)
# =====================================================

class Property(Base):
    __tablename__ = "properties"
    
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    municipality_id = Column(Integer, ForeignKey("municipalities.id"), nullable=False)
    address = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False)
    province = Column(String(50), nullable=False)
    postal_code = Column(String(20))
    property_type = Column(String(50))
    size_sqft = Column(Integer)
    year_built = Column(Integer)
    zoning = Column(String(100))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    company = relationship("Company", back_populates="properties")
    municipality = relationship("Municipality", back_populates="properties")
    alerts = relationship("Alert", back_populates="property")

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    property_id = Column(Integer, ForeignKey("properties.id"))
    title = Column(Text)
    url = Column(Text)
    storage_key = Column(Text)
    review_status = Column(String(50), default='pending')
    resolved_at = Column(DateTime(timezone=True))
    property_matches = Column(JSON)
    rule_matches = Column(JSON)
    relevance_score = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    company = relationship("Company", back_populates="alerts")
    document = relationship("Document", back_populates="alerts")
    property = relationship("Property", back_populates="alerts")
    comments = relationship("AlertComment", back_populates="alert")

class AlertComment(Base):
    __tablename__ = "alert_comments"
    
    id = Column(Integer, primary_key=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    comment = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    alert = relationship("Alert", back_populates="comments")
    user = relationship("User")

class AuditTrail(Base):
    __tablename__ = "audit_trails"
    
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    property_name = Column(String(255))
    total_chunks = Column(Integer)
    chunks_sent = Column(Integer)
    tokens_saved = Column(Integer)
    topic_matches = Column(JSON)  # Array
    committee_matches = Column(JSON)  # Array
    exclusion_reasons = Column(JSON)  # Array
    rules_fired = Column(JSON)  # Array
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    company_id = Column(Integer, ForeignKey("companies.id"))
    action = Column(String(50))
    details = Column(JSON)
    
    # Relationships
    document = relationship("Document", back_populates="audit_trails")
    company = relationship("Company", back_populates="audit_trails")

class IngestJob(Base):
    __tablename__ = "ingest_jobs"
    
    id = Column(Integer, primary_key=True)
    job_id = Column(String(255), unique=True, nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    municipality_id = Column(Integer, ForeignKey("municipalities.id"), nullable=False)
    meeting_types = Column(JSON)
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))
    status = Column(String(50), default='pending')
    progress = Column(Integer, default=0)
    total_documents = Column(Integer, default=0)
    processed_documents = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Relationships
    company = relationship("Company", back_populates="ingest_jobs")
    municipality = relationship("Municipality")
    created_by_user = relationship("User")

# =====================================================
# Migration Tracking
# =====================================================

class SchemaMigration(Base):
    __tablename__ = "schema_migrations"
    
    id = Column(Integer, primary_key=True)
    version = Column(String(255), unique=True, nullable=False)
    applied_at = Column(DateTime(timezone=True), server_default=func.now())