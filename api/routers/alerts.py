"""
Alerts router for BrightStone Property Monitoring System
Updated for single-document pipeline architecture
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from db import get_pg_connection
from routers.auth import get_current_user, UserInfo
import json

router = APIRouter()

class AlertResponse(BaseModel):
    id: int
    company_id: int
    document_id: int
    property_id: Optional[int]
    # Joined data from document -> meeting -> municipality
    municipality_name: Optional[str]
    meeting_type: Optional[str]
    meeting_date: Optional[datetime]
    title: Optional[str]
    url: Optional[str]
    storage_key: Optional[str]
    review_status: str
    resolved_at: Optional[datetime]
    property_matches: Optional[Dict[str, Any]]
    rule_matches: Optional[Dict[str, Any]]
    relevance_score: Optional[float]
    created_at: datetime
    updated_at: datetime
    comment_count: int

class AlertComment(BaseModel):
    comment: str

class AlertStatusUpdate(BaseModel):
    status: str  # pending, reviewed, resolved

@router.get("/", response_model=List[AlertResponse])
async def get_alerts(
    current_user: UserInfo = Depends(get_current_user),
    conn = Depends(get_pg_connection),
    status: Optional[str] = Query(None, description="Filter by review status"),
    municipality: Optional[str] = Query(None, description="Filter by municipality"),
    property_id: Optional[int] = Query(None, description="Filter by property"),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """Get alerts for the current user's company"""
    
    query = """
        WITH alert_comments AS (
            SELECT 
                alert_id,
                COUNT(*) as comment_count
            FROM alert_comments
            GROUP BY alert_id
        )
        SELECT 
            a.id,
            a.company_id,
            a.document_id,
            a.property_id,
            a.title,
            a.url,
            a.storage_key,
            a.review_status,
            a.resolved_at,
            a.property_matches,
            a.rule_matches,
            a.relevance_score,
            a.created_at,
            a.updated_at,
            -- Joined data from document -> meeting -> municipality
            m.name as municipality_name,
            mt.type as meeting_type,
            mt.start_at_local as meeting_date,
            COALESCE(ac.comment_count, 0) as comment_count
        FROM alerts a
        JOIN documents d ON d.id = a.document_id
        JOIN meetings mt ON mt.id = d.meeting_id
        JOIN municipalities m ON m.id = mt.municipality_id
        LEFT JOIN alert_comments ac ON a.id = ac.alert_id
        WHERE a.company_id = $1
    """
    
    params = [current_user.company_id]
    param_count = 2
    
    # Add filters
    if status:
        query += f" AND a.review_status = ${param_count}"
        params.append(status)
        param_count += 1
    
    if municipality:
        query += f" AND LOWER(m.name) = LOWER(${param_count})"
        params.append(municipality)
        param_count += 1
    
    if property_id:
        query += f" AND a.property_id = ${param_count}"
        params.append(property_id)
        param_count += 1
    
    if start_date:
        query += f" AND mt.start_at_local >= ${param_count}"
        params.append(start_date)
        param_count += 1
    
    if end_date:
        query += f" AND mt.start_at_local <= ${param_count}"
        params.append(end_date)
        param_count += 1
    
    # Add ordering and pagination
    query += f" ORDER BY a.created_at DESC LIMIT ${param_count} OFFSET ${param_count + 1}"
    params.extend([limit, offset])
    
    try:
        async with conn.transaction():
            rows = await conn.fetch(query, *params)
            
            alerts = []
            for row in rows:
                alerts.append(AlertResponse(
                    id=row['id'],
                    company_id=row['company_id'],
                    document_id=row['document_id'],
                    property_id=row['property_id'],
                    municipality_name=row['municipality_name'],
                    meeting_type=row['meeting_type'],
                    meeting_date=row['meeting_date'],
                    title=row['title'],
                    url=row['url'],
                    storage_key=row['storage_key'],
                    review_status=row['review_status'],
                    resolved_at=row['resolved_at'],
                    property_matches=row['property_matches'],
                    rule_matches=row['rule_matches'],
                    relevance_score=row['relevance_score'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    comment_count=row['comment_count']
                ))
            
            return alerts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int,
    current_user: UserInfo = Depends(get_current_user),
    conn = Depends(get_pg_connection)
):
    """Get a specific alert by ID"""
    
    query = """
        WITH alert_comments AS (
            SELECT 
                alert_id,
                COUNT(*) as comment_count
            FROM alert_comments
            GROUP BY alert_id
        )
        SELECT 
            a.*,
            -- Joined data from document -> meeting -> municipality
            m.name as municipality_name,
            mt.type as meeting_type,
            mt.start_at_local as meeting_date,
            COALESCE(ac.comment_count, 0) as comment_count
        FROM alerts a
        JOIN documents d ON d.id = a.document_id
        JOIN meetings mt ON mt.id = d.meeting_id
        JOIN municipalities m ON m.id = mt.municipality_id
        LEFT JOIN alert_comments ac ON a.id = ac.alert_id
        WHERE a.id = $1 AND a.company_id = $2
    """
    
    row = await conn.fetchrow(query, alert_id, current_user.company_id)
    
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return AlertResponse(
        id=row['id'],
        company_id=row['company_id'],
        document_id=row['document_id'],
        property_id=row['property_id'],
        municipality_name=row['municipality_name'],
        meeting_type=row['meeting_type'],
        meeting_date=row['meeting_date'],
        title=row['title'],
        url=row['url'],
        storage_key=row['storage_key'],
        review_status=row['review_status'],
        resolved_at=row['resolved_at'],
        property_matches=row['property_matches'],
        rule_matches=row['rule_matches'],
        relevance_score=row['relevance_score'],
        created_at=row['created_at'],
        updated_at=row['updated_at'],
        comment_count=row['comment_count']
    )

@router.patch("/{alert_id}/status")
async def update_alert_status(
    alert_id: int,
    status_update: AlertStatusUpdate,
    current_user: UserInfo = Depends(get_current_user),
    conn = Depends(get_pg_connection)
):
    """Update the review status of an alert"""
    
    # Check if alert exists and belongs to user's company
    check_query = "SELECT id FROM alerts WHERE id = $1 AND company_id = $2"
    exists = await conn.fetchval(check_query, alert_id, current_user.company_id)
    
    if not exists:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Update status
    resolved_at = datetime.utcnow() if status_update.status == 'resolved' else None
    
    update_query = """
        UPDATE alerts 
        SET review_status = $1, resolved_at = $2, updated_at = $3
        WHERE id = $4
        RETURNING id
    """
    
    await conn.execute(
        update_query,
        status_update.status,
        resolved_at,
        datetime.utcnow(),
        alert_id
    )
    
    # Log audit trail
    audit_query = """
        INSERT INTO audit_trails (company_id, action, details, created_at)
        VALUES ($1, $2, $3, $4)
    """
    
    await conn.execute(
        audit_query,
        current_user.company_id,
        'alert_status_updated',
        json.dumps({
            'alert_id': alert_id,
            'new_status': status_update.status
        }),
        datetime.utcnow()
    )
    
    return {"message": "Alert status updated successfully"}

@router.post("/{alert_id}/comments")
async def add_alert_comment(
    alert_id: int,
    comment: AlertComment,
    current_user: UserInfo = Depends(get_current_user),
    conn = Depends(get_pg_connection)
):
    """Add a comment to an alert"""
    
    # Check if alert exists and belongs to user's company
    check_query = "SELECT id FROM alerts WHERE id = $1 AND company_id = $2"
    exists = await conn.fetchval(check_query, alert_id, current_user.company_id)
    
    if not exists:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Add comment
    insert_query = """
        INSERT INTO alert_comments (alert_id, user_id, comment, created_at)
        VALUES ($1, $2, $3, $4)
        RETURNING id
    """
    
    comment_id = await conn.fetchval(
        insert_query,
        alert_id,
        current_user.id,
        comment.comment,
        datetime.utcnow()
    )
    
    return {"id": comment_id, "message": "Comment added successfully"}

@router.get("/{alert_id}/comments")
async def get_alert_comments(
    alert_id: int,
    current_user: UserInfo = Depends(get_current_user),
    conn = Depends(get_pg_connection)
):
    """Get all comments for an alert"""
    
    # Check if alert exists and belongs to user's company
    check_query = "SELECT id FROM alerts WHERE id = $1 AND company_id = $2"
    exists = await conn.fetchval(check_query, alert_id, current_user.company_id)
    
    if not exists:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Get comments
    query = """
        SELECT 
            ac.id,
            ac.comment,
            ac.created_at,
            u.email as user_email,
            u.first_name,
            u.last_name
        FROM alert_comments ac
        JOIN users u ON ac.user_id = u.id
        WHERE ac.alert_id = $1
        ORDER BY ac.created_at DESC
    """
    
    rows = await conn.fetch(query, alert_id)
    
    comments = []
    for row in rows:
        comments.append({
            "id": row['id'],
            "comment": row['comment'],
            "created_at": row['created_at'].isoformat(),
            "user": {
                "email": row['user_email'],
                "first_name": row['first_name'],
                "last_name": row['last_name']
            }
        })
    
    return comments