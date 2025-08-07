"""
Documents router for CityScrape API
"""

from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date
from db import get_pg_connection
from routers.auth import get_current_user, UserInfo
import json
import os

router = APIRouter()

class DocumentResponse(BaseModel):
    id: int
    document_id: str
    meeting_type: str
    meeting_date: datetime
    municipality: str
    title: str
    url: Optional[str]
    storage_key: Optional[str]
    status: str
    extracted_text: Optional[str]
    analysis_result: Optional[dict]
    created_at: datetime
    updated_at: datetime

class DocumentAnalysis(BaseModel):
    flagged_items: List[dict]
    relevance_score: float
    summary: str

@router.get("/", response_model=List[DocumentResponse])
async def get_documents(
    current_user: UserInfo = Depends(get_current_user),
    conn = Depends(get_pg_connection),
    municipality: Optional[str] = Query(None, description="Filter by municipality"),
    meeting_type: Optional[str] = Query(None, description="Filter by meeting type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """Get documents for the current user's company"""
    
    query = """
        SELECT 
            d.id,
            d.document_id,
            d.meeting_type,
            d.meeting_date,
            d.municipality,
            d.title,
            d.url,
            d.storage_key,
            d.status,
            d.extracted_text,
            d.analysis_result,
            d.created_at,
            d.updated_at
        FROM documents d
        WHERE d.company_id = $1
    """
    
    params = [current_user.company_id]
    param_count = 2
    
    # Add filters
    if municipality:
        query += f" AND LOWER(d.municipality) = LOWER(${param_count})"
        params.append(municipality)
        param_count += 1
    
    if meeting_type:
        query += f" AND d.meeting_type = ${param_count}"
        params.append(meeting_type)
        param_count += 1
    
    if status:
        query += f" AND d.status = ${param_count}"
        params.append(status)
        param_count += 1
    
    if start_date:
        query += f" AND d.meeting_date >= ${param_count}"
        params.append(start_date)
        param_count += 1
    
    if end_date:
        query += f" AND d.meeting_date <= ${param_count}"
        params.append(end_date)
        param_count += 1
    
    # Add ordering and pagination
    query += f" ORDER BY d.meeting_date DESC, d.created_at DESC LIMIT ${param_count} OFFSET ${param_count + 1}"
    params.extend([limit, offset])
    
    try:
        async with conn.transaction():
            rows = await conn.fetch(query, *params)
            
            documents = []
            for row in rows:
                documents.append(DocumentResponse(
                    id=row['id'],
                    document_id=row['document_id'],
                    meeting_type=row['meeting_type'],
                    meeting_date=row['meeting_date'],
                    municipality=row['municipality'],
                    title=row['title'],
                    url=row['url'],
                    storage_key=row['storage_key'],
                    status=row['status'],
                    extracted_text=row['extracted_text'][:500] if row['extracted_text'] else None,  # Truncate for list view
                    analysis_result=json.loads(row['analysis_result']) if row['analysis_result'] else None,
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                ))
            
            return documents
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: UserInfo = Depends(get_current_user),
    conn = Depends(get_pg_connection)
):
    """Get a specific document by ID"""
    
    query = """
        SELECT * FROM documents
        WHERE document_id = $1 AND company_id = $2
    """
    
    row = await conn.fetchrow(query, document_id, current_user.company_id)
    
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentResponse(
        id=row['id'],
        document_id=row['document_id'],
        meeting_type=row['meeting_type'],
        meeting_date=row['meeting_date'],
        municipality=row['municipality'],
        title=row['title'],
        url=row['url'],
        storage_key=row['storage_key'],
        status=row['status'],
        extracted_text=row['extracted_text'],
        analysis_result=json.loads(row['analysis_result']) if row['analysis_result'] else None,
        created_at=row['created_at'],
        updated_at=row['updated_at']
    )

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    municipality: str = Query(..., description="Municipality name"),
    meeting_type: str = Query(..., description="Meeting type"),
    meeting_date: date = Query(..., description="Meeting date"),
    current_user: UserInfo = Depends(get_current_user),
    conn = Depends(get_pg_connection)
):
    """Upload a new document for processing"""
    
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Generate document ID
    import uuid
    document_id = str(uuid.uuid4())
    
    # Save to S3 (simplified - would use actual S3 client in production)
    storage_key = f"{current_user.company_id}/{municipality.lower()}/{document_id}/{file.filename}"
    
    # TODO: Actually upload to S3
    # s3_client.upload_fileobj(file.file, bucket_name, storage_key)
    
    # Create database entry
    insert_query = """
        INSERT INTO documents (
            document_id, company_id, municipality, meeting_type, 
            meeting_date, title, storage_key, status, created_at, updated_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        RETURNING id
    """
    
    doc_id = await conn.fetchval(
        insert_query,
        document_id,
        current_user.company_id,
        municipality,
        meeting_type,
        meeting_date,
        file.filename,
        storage_key,
        'pending',
        datetime.utcnow(),
        datetime.utcnow()
    )
    
    # Queue for processing (would use actual queue in production)
    # queue.enqueue('process_document', document_id)
    
    return {
        "id": doc_id,
        "document_id": document_id,
        "message": "Document uploaded successfully and queued for processing"
    }

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: UserInfo = Depends(get_current_user),
    conn = Depends(get_pg_connection)
):
    """Delete a document"""
    
    # Check if document exists and belongs to user's company
    check_query = "SELECT id, storage_key FROM documents WHERE document_id = $1 AND company_id = $2"
    row = await conn.fetchrow(check_query, document_id, current_user.company_id)
    
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete from S3 (would use actual S3 client in production)
    # s3_client.delete_object(Bucket=bucket_name, Key=row['storage_key'])
    
    # Delete from database
    delete_query = "DELETE FROM documents WHERE document_id = $1"
    await conn.execute(delete_query, document_id)
    
    # Log audit trail
    audit_query = """
        INSERT INTO audit_trails (company_id, user_id, action, details, created_at)
        VALUES ($1, $2, $3, $4, $5)
    """
    
    await conn.execute(
        audit_query,
        current_user.company_id,
        current_user.id,
        'document_deleted',
        json.dumps({'document_id': document_id}),
        datetime.utcnow()
    )
    
    return {"message": "Document deleted successfully"}

@router.post("/{document_id}/reprocess")
async def reprocess_document(
    document_id: str,
    current_user: UserInfo = Depends(get_current_user),
    conn = Depends(get_pg_connection)
):
    """Reprocess a document"""
    
    # Check if document exists and belongs to user's company
    check_query = "SELECT id FROM documents WHERE document_id = $1 AND company_id = $2"
    exists = await conn.fetchval(check_query, document_id, current_user.company_id)
    
    if not exists:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Update status to pending
    update_query = """
        UPDATE documents 
        SET status = 'pending', updated_at = $1
        WHERE document_id = $2
    """
    
    await conn.execute(update_query, datetime.utcnow(), document_id)
    
    # Queue for reprocessing (would use actual queue in production)
    # queue.enqueue('process_document', document_id)
    
    return {"message": "Document queued for reprocessing"}

@router.get("/stats/summary")
async def get_document_stats(
    current_user: UserInfo = Depends(get_current_user),
    conn = Depends(get_pg_connection)
):
    """Get document statistics for the current company"""
    
    query = """
        SELECT 
            COUNT(*) as total_documents,
            COUNT(CASE WHEN status = 'analyzed' THEN 1 END) as analyzed_documents,
            COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_documents,
            COUNT(CASE WHEN status = 'error' THEN 1 END) as error_documents,
            COUNT(DISTINCT municipality) as municipalities_covered,
            MIN(meeting_date) as earliest_meeting,
            MAX(meeting_date) as latest_meeting
        FROM documents
        WHERE company_id = $1
    """
    
    row = await conn.fetchrow(query, current_user.company_id)
    
    return {
        "total_documents": row['total_documents'],
        "analyzed_documents": row['analyzed_documents'],
        "pending_documents": row['pending_documents'],
        "error_documents": row['error_documents'],
        "municipalities_covered": row['municipalities_covered'],
        "earliest_meeting": row['earliest_meeting'].isoformat() if row['earliest_meeting'] else None,
        "latest_meeting": row['latest_meeting'].isoformat() if row['latest_meeting'] else None
    }