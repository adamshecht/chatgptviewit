"""
Ingest router for CityScrape API
Handles document ingestion and processing
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from db import get_pg_connection
from routers.auth import get_current_user, UserInfo
import json
import asyncio

router = APIRouter()

class IngestRequest(BaseModel):
    municipality: str
    meeting_types: Optional[List[str]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class IngestStatus(BaseModel):
    job_id: str
    status: str
    progress: int
    total_documents: int
    processed_documents: int
    error_count: int
    started_at: datetime
    completed_at: Optional[datetime]

@router.post("/scrape")
async def trigger_scrape(
    request: IngestRequest,
    background_tasks: BackgroundTasks,
    current_user: UserInfo = Depends(get_current_user),
    conn = Depends(get_pg_connection)
):
    """Trigger a new scraping job for a municipality"""
    
    # Check if user has permission (admin only)
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Only admins can trigger scraping")
    
    # Generate job ID
    import uuid
    job_id = str(uuid.uuid4())
    
    # Create job entry
    insert_query = """
        INSERT INTO ingest_jobs (
            job_id, company_id, municipality, meeting_types,
            start_date, end_date, status, created_at, created_by
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING id
    """
    
    job_record_id = await conn.fetchval(
        insert_query,
        job_id,
        current_user.company_id,
        request.municipality,
        json.dumps(request.meeting_types) if request.meeting_types else None,
        request.start_date,
        request.end_date,
        'pending',
        datetime.utcnow(),
        current_user.id
    )
    
    # Queue the scraping job (would use actual queue in production)
    # In production, this would be handled by a worker service
    background_tasks.add_task(
        run_scraping_job,
        job_id,
        request.municipality,
        request.meeting_types,
        current_user.company_id
    )
    
    return {
        "job_id": job_id,
        "message": f"Scraping job queued for {request.municipality}",
        "status": "pending"
    }

@router.get("/jobs", response_model=List[IngestStatus])
async def get_ingest_jobs(
    current_user: UserInfo = Depends(get_current_user),
    conn = Depends(get_pg_connection),
    limit: int = 50
):
    """Get list of ingest jobs for the company"""
    
    query = """
        SELECT 
            job_id,
            status,
            progress,
            total_documents,
            processed_documents,
            error_count,
            started_at,
            completed_at
        FROM ingest_jobs
        WHERE company_id = $1
        ORDER BY created_at DESC
        LIMIT $2
    """
    
    rows = await conn.fetch(query, current_user.company_id, limit)
    
    jobs = []
    for row in rows:
        jobs.append(IngestStatus(
            job_id=row['job_id'],
            status=row['status'],
            progress=row['progress'] or 0,
            total_documents=row['total_documents'] or 0,
            processed_documents=row['processed_documents'] or 0,
            error_count=row['error_count'] or 0,
            started_at=row['started_at'] or datetime.utcnow(),
            completed_at=row['completed_at']
        ))
    
    return jobs

@router.get("/jobs/{job_id}", response_model=IngestStatus)
async def get_ingest_job(
    job_id: str,
    current_user: UserInfo = Depends(get_current_user),
    conn = Depends(get_pg_connection)
):
    """Get status of a specific ingest job"""
    
    query = """
        SELECT 
            job_id,
            status,
            progress,
            total_documents,
            processed_documents,
            error_count,
            started_at,
            completed_at
        FROM ingest_jobs
        WHERE job_id = $1 AND company_id = $2
    """
    
    row = await conn.fetchrow(query, job_id, current_user.company_id)
    
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return IngestStatus(
        job_id=row['job_id'],
        status=row['status'],
        progress=row['progress'] or 0,
        total_documents=row['total_documents'] or 0,
        processed_documents=row['processed_documents'] or 0,
        error_count=row['error_count'] or 0,
        started_at=row['started_at'] or datetime.utcnow(),
        completed_at=row['completed_at']
    )

@router.post("/jobs/{job_id}/cancel")
async def cancel_ingest_job(
    job_id: str,
    current_user: UserInfo = Depends(get_current_user),
    conn = Depends(get_pg_connection)
):
    """Cancel an ingest job"""
    
    # Check if user has permission (admin only)
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Only admins can cancel jobs")
    
    # Check if job exists and is cancellable
    check_query = """
        SELECT status 
        FROM ingest_jobs 
        WHERE job_id = $1 AND company_id = $2
    """
    
    status = await conn.fetchval(check_query, job_id, current_user.company_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if status in ['completed', 'cancelled', 'failed']:
        raise HTTPException(status_code=400, detail=f"Cannot cancel job with status: {status}")
    
    # Update job status
    update_query = """
        UPDATE ingest_jobs
        SET status = 'cancelled', completed_at = $1
        WHERE job_id = $2
    """
    
    await conn.execute(update_query, datetime.utcnow(), job_id)
    
    # TODO: Actually cancel the running job in the worker
    
    return {"message": "Job cancellation requested"}

@router.post("/process-document/{document_id}")
async def process_single_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    current_user: UserInfo = Depends(get_current_user),
    conn = Depends(get_pg_connection)
):
    """Process a single document"""
    
    # Check if document exists and belongs to company
    check_query = """
        SELECT id, status 
        FROM documents 
        WHERE document_id = $1 AND company_id = $2
    """
    
    row = await conn.fetchrow(check_query, document_id, current_user.company_id)
    
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if row['status'] == 'processing':
        raise HTTPException(status_code=400, detail="Document is already being processed")
    
    # Update status to processing
    update_query = """
        UPDATE documents
        SET status = 'processing', updated_at = $1
        WHERE document_id = $2
    """
    
    await conn.execute(update_query, datetime.utcnow(), document_id)
    
    # Queue processing (would use actual queue in production)
    background_tasks.add_task(
        process_document,
        document_id,
        current_user.company_id
    )
    
    return {"message": "Document queued for processing"}

# Helper functions (would be in separate service in production)
async def run_scraping_job(
    job_id: str,
    municipality: str,
    meeting_types: Optional[List[str]],
    company_id: str
):
    """Run the actual scraping job (simplified)"""
    # This would be handled by a worker service in production
    # For now, just simulate the job
    await asyncio.sleep(5)  # Simulate work
    
    # Update job status
    # In production, this would update progress incrementally
    pass

async def process_document(document_id: str, company_id: str):
    """Process a document (simplified)"""
    # This would be handled by a worker service in production
    # Would include:
    # 1. Download from S3
    # 2. Extract text
    # 3. Run analysis
    # 4. Create alerts if needed
    # 5. Update document status
    await asyncio.sleep(3)  # Simulate work
    pass

@router.get("/municipalities")
async def get_available_municipalities(
    current_user: UserInfo = Depends(get_current_user)
):
    """Get list of available municipalities for scraping"""
    
    # This would be dynamically loaded from configuration
    municipalities = [
        "Toronto",
        "Mississauga",
        "Brampton",
        "Hamilton",
        "Ottawa",
        "London",
        "Markham",
        "Vaughan",
        "Kitchener",
        "Windsor",
        "Richmond Hill",
        "Oakville",
        "Burlington",
        "Oshawa",
        "Barrie"
    ]
    
    return municipalities

@router.get("/meeting-types")
async def get_meeting_types(
    current_user: UserInfo = Depends(get_current_user)
):
    """Get list of available meeting types"""
    
    meeting_types = [
        "Council",
        "Planning Committee",
        "Committee of Adjustment",
        "Executive Committee",
        "Community Council",
        "Board Meeting",
        "Public Meeting",
        "Special Meeting"
    ]
    
    return meeting_types