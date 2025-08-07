"""
SQLAlchemy models for CityScrape
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db import Base
import uuid

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True)
    company_id = Column(String, unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    storage_prefix = Column(String)
    email_config = Column(JSON)
    rules_config = Column(JSON)
    openai_api_key = Column(String)
    terms_of_reference = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    users = relationship("User", back_populates="company")
    properties = relationship("Property", back_populates="company")
    meetings = relationship("Meeting", back_populates="company")
    notifications = relationship("Notification", back_populates="company")

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    company_id = Column(String, ForeignKey("companies.company_id"))
    email = Column(String, unique=True, nullable=False)
    first_name = Column(String)
    last_name = Column(String)
    role = Column(String, default="analyst")
    auth0_id = Column(String, unique=True)
    last_login = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    company = relationship("Company", back_populates="users")

class Property(Base):
    __tablename__ = "properties"
    
    id = Column(Integer, primary_key=True)
    company_id = Column(String, ForeignKey("companies.company_id"))
    name = Column(String, nullable=False)
    address = Column(String)
    legal_description = Column(String)
    aliases = Column(JSON)
    active = Column(Boolean, default=True)
    payment_status = Column(String, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    company = relationship("Company", back_populates="properties")

class Municipality(Base):
    __tablename__ = "municipalities"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    province = Column(String)
    rss_feed_url = Column(String)
    web_scraper_url = Column(String)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    meetings = relationship("Meeting", back_populates="municipality")

class Meeting(Base):
    __tablename__ = "meetings"
    
    id = Column(Integer, primary_key=True)
    municipality_id = Column(Integer, ForeignKey("municipalities.id"))
    company_id = Column(String, ForeignKey("companies.company_id"))
    meeting_date = Column(DateTime(timezone=True))
    type = Column(String)
    title = Column(String)
    url = Column(String)
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    municipality = relationship("Municipality", back_populates="meetings")
    company = relationship("Company", back_populates="meetings")
    documents = relationship("Document", back_populates="meeting")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"))
    company_id = Column(String, ForeignKey("companies.company_id"))
    document_id = Column(String, unique=True)
    type = Column(String)
    title = Column(String)
    url = Column(String)
    storage_key = Column(String)
    content_hash = Column(String)
    status = Column(String, default="discovered")
    extracted_text = Column(Text)
    analysis_result = Column(JSON)
    review_status = Column(String, default="pending")
    resolved_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    meeting = relationship("Meeting", back_populates="documents")
    audit_trails = relationship("AuditTrail", back_populates="document")

class AuditTrail(Base):
    __tablename__ = "audit_trails"
    
    id = Column(Integer, primary_key=True)
    document_id = Column(String, ForeignKey("documents.document_id"))
    stage = Column(String)
    details = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="audit_trails")

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True)
    company_id = Column(String, ForeignKey("companies.company_id"))
    document_id = Column(String)
    type = Column(String)
    recipients = Column(JSON)
    subject = Column(String)
    body = Column(Text)
    status = Column(String, default="pending")
    sent_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    company = relationship("Company", back_populates="notifications")