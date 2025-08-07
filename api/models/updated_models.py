"""
Updated Pydantic models for single-document pipeline
These models reflect the new schema after migration 001
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID

# =====================================================
# Company Models
# =====================================================

class Company(BaseModel):
    """Company entity - unchanged, still uses id (INT) and company_id (VARCHAR)"""
    id: int
    company_id: str  # This remains VARCHAR as the slug identifier
    name: str
    storage_prefix: Optional[str] = None
    email_config: Optional[Dict[str, Any]] = None
    rules_config: Optional[Dict[str, Any]] = None
    openai_api_key: Optional[str] = None
    created_at: datetime
    updated_at: datetime

# =====================================================
# Global Entity Models (Company-Agnostic)
# =====================================================

class Municipality(BaseModel):
    """Municipality - now global without company_id"""
    id: int
    name: str
    feed_url: str
    created_at: datetime

class Meeting(BaseModel):
    """Meeting - now global without company_id or location"""
    id: int
    guid: str
    municipality_id: int
    type: str
    start_at_local: Optional[datetime] = None
    first_seen_at: datetime
    last_seen_at: datetime

class Document(BaseModel):
    """Document - now global with meeting_id as INT"""
    id: int
    meeting_id: int  # Changed from meeting_guid VARCHAR to meeting_id INT
    meeting_title: Optional[str] = None
    # municipality_name removed - get from meeting->municipality
    kind: str
    format: str
    url: str
    document_id: Optional[int] = None
    downloaded: bool = False
    download_path: Optional[str] = None
    first_seen_at: datetime
    last_seen_at: datetime
    storage_key: Optional[str] = None
    size_bytes: Optional[int] = None
    etag: Optional[str] = None
    last_modified: Optional[datetime] = None
    content_hash: Optional[str] = None
    storage_type: str = 's3'
    status: str = 'discovered'
    # company_id removed - documents are global
    created_at: datetime
    updated_at: datetime
    review_status: str = 'new'
    resolved_by: Optional[UUID] = None
    resolved_at: Optional[datetime] = None

# =====================================================
# Link Table Models
# =====================================================

class CompanyMunicipality(BaseModel):
    """Link table for company municipality subscriptions"""
    company_id: int  # FK to companies.id
    municipality_id: int  # FK to municipalities.id
    created_at: datetime

# =====================================================
# Tenant-Specific Models (Company-Scoped)
# =====================================================

class User(BaseModel):
    """User - company_id now INT"""
    id: UUID
    company_id: Optional[int] = None  # Changed from VARCHAR to INT
    email: str
    role: str  # 'admin' or 'analyst'
    created_at: datetime
    invited_by: Optional[UUID] = None
    auth0_id: Optional[str] = None
    last_login: Optional[datetime] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class Property(BaseModel):
    """Property - company_id now INT, added municipality_id"""
    id: int
    company_id: int  # Changed from VARCHAR to INT
    municipality_id: Optional[int] = None  # NEW: link to municipality
    address: str
    city: str
    province: str
    postal_code: Optional[str] = None
    property_type: Optional[str] = None
    size_sqft: Optional[int] = None
    year_built: Optional[int] = None
    zoning: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class Alert(BaseModel):
    """Alert - company_id and document_id now INT, removed redundant fields"""
    id: int
    company_id: int  # Changed from VARCHAR to INT
    document_id: int  # Changed from VARCHAR to INT
    property_id: Optional[int] = None
    # Removed: municipality, meeting_type, meeting_date (get from document->meeting)
    title: Optional[str] = None
    url: Optional[str] = None
    storage_key: Optional[str] = None
    review_status: str = 'pending'
    resolved_at: Optional[datetime] = None
    property_matches: Optional[Dict[str, Any]] = None
    rule_matches: Optional[Dict[str, Any]] = None
    relevance_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime

class AlertComment(BaseModel):
    """Alert comment - unchanged"""
    id: int
    alert_id: int
    user_id: UUID
    comment: str
    created_at: datetime

class AuditTrail(BaseModel):
    """Audit trail - company_id now INT"""
    id: int
    document_id: Optional[int] = None
    property_name: Optional[str] = None
    total_chunks: Optional[int] = None
    chunks_sent: Optional[int] = None
    tokens_saved: Optional[int] = None
    topic_matches: Optional[List[str]] = None
    committee_matches: Optional[List[str]] = None
    exclusion_reasons: Optional[List[str]] = None
    rules_fired: Optional[List[str]] = None
    created_at: datetime
    company_id: Optional[int] = None  # Changed from VARCHAR to INT
    action: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class IngestJob(BaseModel):
    """Ingest job - company_id now INT"""
    id: int
    job_id: str
    company_id: int  # Changed from VARCHAR to INT
    municipality: Optional[str] = None
    meeting_types: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: str = 'pending'
    progress: int = 0
    total_documents: int = 0
    processed_documents: int = 0
    error_count: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    created_by: Optional[UUID] = None

# =====================================================
# Response Models for API
# =====================================================

class PropertyResponse(BaseModel):
    """API response for property with municipality details"""
    id: int
    company_id: int
    municipality_id: Optional[int] = None
    municipality_name: Optional[str] = None  # Joined from municipality table
    address: str
    city: str
    province: str
    postal_code: Optional[str] = None
    property_type: Optional[str] = None
    size_sqft: Optional[int] = None
    year_built: Optional[int] = None
    zoning: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class AlertResponse(BaseModel):
    """API response for alert with joined document/meeting data"""
    id: int
    company_id: int
    document_id: int
    property_id: Optional[int] = None
    # Joined from document->meeting->municipality
    municipality_name: Optional[str] = None
    meeting_type: Optional[str] = None
    meeting_date: Optional[datetime] = None
    title: Optional[str] = None
    url: Optional[str] = None
    storage_key: Optional[str] = None
    review_status: str
    resolved_at: Optional[datetime] = None
    property_matches: Optional[Dict[str, Any]] = None
    rule_matches: Optional[Dict[str, Any]] = None
    relevance_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime

class DocumentResponse(BaseModel):
    """API response for document with meeting details"""
    id: int
    meeting_id: int
    meeting_title: Optional[str] = None
    # Joined from meeting->municipality
    municipality_name: Optional[str] = None
    meeting_type: Optional[str] = None
    meeting_date: Optional[datetime] = None
    kind: str
    format: str
    url: str
    storage_key: Optional[str] = None
    size_bytes: Optional[int] = None
    content_hash: Optional[str] = None
    status: str
    review_status: str
    created_at: datetime
    updated_at: datetime

# =====================================================
# Request Models for API
# =====================================================

class PropertyCreate(BaseModel):
    """Create a new property"""
    address: str
    city: str
    province: str
    municipality_id: Optional[int] = None
    postal_code: Optional[str] = None
    property_type: Optional[str] = None
    size_sqft: Optional[int] = None
    year_built: Optional[int] = None
    zoning: Optional[str] = None
    notes: Optional[str] = None

class AlertCreate(BaseModel):
    """Create a new alert"""
    document_id: int
    property_id: Optional[int] = None
    title: Optional[str] = None
    property_matches: Optional[Dict[str, Any]] = None
    rule_matches: Optional[Dict[str, Any]] = None
    relevance_score: Optional[float] = None

class CompanyMunicipalitySubscribe(BaseModel):
    """Subscribe a company to a municipality"""
    municipality_id: int

# =====================================================
# Utility Functions
# =====================================================

def convert_company_id_to_int(company_slug: str, companies_map: Dict[str, int]) -> int:
    """
    Helper to convert old VARCHAR company_id to new INT id
    
    Args:
        company_slug: The old VARCHAR company_id (e.g., 'adam_shechtman_company_498854')
        companies_map: Dict mapping company_id slug to id integer
    
    Returns:
        The integer company id
    """
    if company_slug not in companies_map:
        raise ValueError(f"Unknown company_id: {company_slug}")
    return companies_map[company_slug]