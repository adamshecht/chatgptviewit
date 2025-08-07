"""
Companies router for CityScrape API
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from db import get_pg_connection
from routers.auth import get_current_user, UserInfo
import json

router = APIRouter()

class CompanyInfo(BaseModel):
    company_id: str
    company_name: str
    created_at: datetime
    subscription_tier: str
    max_properties: int
    max_users: int

class UserInvite(BaseModel):
    email: str
    role: str = "analyst"

class RulesConfig(BaseModel):
    committees: List[str]
    topics: List[str]
    exclusions: List[str]

@router.get("/me", response_model=CompanyInfo)
async def get_company_info(
    current_user: UserInfo = Depends(get_current_user),
    conn = Depends(get_pg_connection)
):
    """Get current company information"""
    
    query = """
        SELECT 
            company_id,
            company_name,
            created_at,
            subscription_tier,
            max_properties,
            max_users
        FROM companies
        WHERE company_id = $1
    """
    
    row = await conn.fetchrow(query, current_user.company_id)
    
    if not row:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return CompanyInfo(
        company_id=row['company_id'],
        company_name=row['company_name'],
        created_at=row['created_at'],
        subscription_tier=row['subscription_tier'] or 'free',
        max_properties=row['max_properties'] or 3,
        max_users=row['max_users'] or 5
    )

@router.get("/users")
async def get_company_users(
    current_user: UserInfo = Depends(get_current_user),
    conn = Depends(get_pg_connection)
):
    """Get all users in the company"""
    
    # Only admins can view all users
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Only admins can view company users")
    
    query = """
        SELECT 
            id,
            email,
            first_name,
            last_name,
            role,
            created_at,
            last_login
        FROM users
        WHERE company_id = $1
        ORDER BY created_at DESC
    """
    
    rows = await conn.fetch(query, current_user.company_id)
    
    users = []
    for row in rows:
        users.append({
            "id": row['id'],
            "email": row['email'],
            "first_name": row['first_name'],
            "last_name": row['last_name'],
            "role": row['role'],
            "created_at": row['created_at'].isoformat(),
            "last_login": row['last_login'].isoformat() if row['last_login'] else None
        })
    
    return users

@router.post("/invite-user")
async def invite_user(
    invite: UserInvite,
    current_user: UserInfo = Depends(get_current_user),
    conn = Depends(get_pg_connection)
):
    """Invite a new user to the company"""
    
    # Only admins can invite users
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Only admins can invite users")
    
    # Check if user already exists
    existing = await conn.fetchval(
        "SELECT id FROM users WHERE email = $1 AND company_id = $2",
        invite.email,
        current_user.company_id
    )
    
    if existing:
        raise HTTPException(status_code=400, detail="User already exists in this company")
    
    # Create user (would send actual invite email in production)
    insert_query = """
        INSERT INTO users (company_id, email, role, created_at, invited_by)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id
    """
    
    user_id = await conn.fetchval(
        insert_query,
        current_user.company_id,
        invite.email,
        invite.role,
        datetime.utcnow(),
        current_user.id
    )
    
    # Log audit trail
    audit_query = """
        INSERT INTO audit_trails (company_id, user_id, action, details, created_at)
        VALUES ($1, $2, $3, $4, $5)
    """
    
    await conn.execute(
        audit_query,
        current_user.company_id,
        current_user.id,
        'user_invited',
        json.dumps({'invited_email': invite.email, 'role': invite.role}),
        datetime.utcnow()
    )
    
    return {"id": user_id, "message": f"Invitation sent to {invite.email}"}

@router.post("/terms-of-reference")
async def upload_terms_of_reference(
    file: UploadFile = File(...),
    current_user: UserInfo = Depends(get_current_user),
    conn = Depends(get_pg_connection)
):
    """Upload terms of reference document"""
    
    # Only admins can upload ToR
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Only admins can upload terms of reference")
    
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Save to S3 (simplified)
    storage_key = f"{current_user.company_id}/terms_of_reference/{file.filename}"
    
    # TODO: Actually upload to S3
    # s3_client.upload_fileobj(file.file, bucket_name, storage_key)
    
    # Update company record
    update_query = """
        UPDATE companies
        SET terms_of_reference_key = $1, updated_at = $2
        WHERE company_id = $3
    """
    
    await conn.execute(
        update_query,
        storage_key,
        datetime.utcnow(),
        current_user.company_id
    )
    
    return {"message": "Terms of reference uploaded successfully"}

@router.get("/rules-config", response_model=RulesConfig)
async def get_rules_config(
    current_user: UserInfo = Depends(get_current_user),
    conn = Depends(get_pg_connection)
):
    """Get company's rules configuration"""
    
    query = """
        SELECT rules_config
        FROM companies
        WHERE company_id = $1
    """
    
    config_json = await conn.fetchval(query, current_user.company_id)
    
    if config_json:
        config = json.loads(config_json)
        return RulesConfig(
            committees=config.get('committees', []),
            topics=config.get('topics', []),
            exclusions=config.get('exclusions', [])
        )
    
    # Return default config
    return RulesConfig(
        committees=[],
        topics=[],
        exclusions=["housekeeping", "administrative", "procedural"]
    )

@router.put("/rules-config")
async def update_rules_config(
    config: RulesConfig,
    current_user: UserInfo = Depends(get_current_user),
    conn = Depends(get_pg_connection)
):
    """Update company's rules configuration"""
    
    # Only admins can update rules
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Only admins can update rules configuration")
    
    config_json = json.dumps({
        "committees": config.committees,
        "topics": config.topics,
        "exclusions": config.exclusions
    })
    
    update_query = """
        UPDATE companies
        SET rules_config = $1, updated_at = $2
        WHERE company_id = $3
    """
    
    await conn.execute(
        update_query,
        config_json,
        datetime.utcnow(),
        current_user.company_id
    )
    
    # Log audit trail
    audit_query = """
        INSERT INTO audit_trails (company_id, user_id, action, details, created_at)
        VALUES ($1, $2, $3, $4, $5)
    """
    
    await conn.execute(
        audit_query,
        current_user.company_id,
        current_user.id,
        'rules_config_updated',
        config_json,
        datetime.utcnow()
    )
    
    return {"message": "Rules configuration updated successfully"}

@router.delete("/users/{user_id}")
async def remove_user(
    user_id: int,
    current_user: UserInfo = Depends(get_current_user),
    conn = Depends(get_pg_connection)
):
    """Remove a user from the company"""
    
    # Only admins can remove users
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Only admins can remove users")
    
    # Can't remove yourself
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself")
    
    # Check if user exists in company
    check_query = "SELECT email FROM users WHERE id = $1 AND company_id = $2"
    user_email = await conn.fetchval(check_query, user_id, current_user.company_id)
    
    if not user_email:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Delete user
    delete_query = "DELETE FROM users WHERE id = $1"
    await conn.execute(delete_query, user_id)
    
    # Log audit trail
    audit_query = """
        INSERT INTO audit_trails (company_id, user_id, action, details, created_at)
        VALUES ($1, $2, $3, $4, $5)
    """
    
    await conn.execute(
        audit_query,
        current_user.company_id,
        current_user.id,
        'user_removed',
        json.dumps({'removed_user_id': user_id, 'removed_email': user_email}),
        datetime.utcnow()
    )
    
    return {"message": f"User {user_email} removed successfully"}

@router.get("/municipalities")
async def get_company_municipalities(
    current_user: UserInfo = Depends(get_current_user),
    conn = Depends(get_pg_connection)
):
    """Get municipalities that the company is subscribed to"""
    
    query = """
        SELECT 
            m.id,
            m.name,
            m.feed_url,
            cm.created_at as subscribed_at
        FROM municipalities m
        JOIN company_municipalities cm ON cm.municipality_id = m.id
        WHERE cm.company_id = $1
        ORDER BY m.name
    """
    
    rows = await conn.fetch(query, current_user.company_id)
    
    municipalities = []
    for row in rows:
        municipalities.append({
            "id": row['id'],
            "name": row['name'],
            "feed_url": row['feed_url'],
            "subscribed_at": row['subscribed_at'].isoformat()
        })
    
    return municipalities

@router.put("/municipalities")
async def update_company_municipalities(
    municipality_ids: List[int],
    current_user: UserInfo = Depends(get_current_user),
    conn = Depends(get_pg_connection)
):
    """Update company's municipality subscriptions"""
    
    # Only admins can update municipality subscriptions
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Only admins can update municipality subscriptions")
    
    # Remove existing subscriptions
    delete_query = "DELETE FROM company_municipalities WHERE company_id = $1"
    await conn.execute(delete_query, current_user.company_id)
    
    # Add new subscriptions
    if municipality_ids:
        insert_query = """
            INSERT INTO company_municipalities (company_id, municipality_id, created_at)
            VALUES ($1, $2, $3)
        """
        for municipality_id in municipality_ids:
            await conn.execute(
                insert_query,
                current_user.company_id,
                municipality_id,
                datetime.utcnow()
            )
    
    # Log audit trail
    audit_query = """
        INSERT INTO audit_trails (company_id, action, details, created_at)
        VALUES ($1, $2, $3, $4)
    """
    
    await conn.execute(
        audit_query,
        current_user.company_id,
        'municipalities_updated',
        json.dumps({'municipality_ids': municipality_ids}),
        datetime.utcnow()
    )
    
    return {"message": f"Updated to {len(municipality_ids)} municipalities"}

@router.get("/settings")
async def get_company_settings(
    current_user: UserInfo = Depends(get_current_user),
    conn = Depends(get_pg_connection)
):
    """Get company settings"""
    
    query = """
        SELECT 
            name,
            email_config,
            rules_json,
            storage_prefix,
            created_at,
            updated_at
        FROM companies
        WHERE id = $1
    """
    
    row = await conn.fetchrow(query, current_user.company_id)
    
    if not row:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return {
        "name": row['name'],
        "email_config": row['email_config'],
        "rules_json": row['rules_json'],
        "storage_prefix": row['storage_prefix'],
        "created_at": row['created_at'].isoformat(),
        "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None
    }

@router.put("/settings")
async def update_company_settings(
    settings: dict,
    current_user: UserInfo = Depends(get_current_user),
    conn = Depends(get_pg_connection)
):
    """Update company settings"""
    
    # Only admins can update settings
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Only admins can update company settings")
    
    update_query = """
        UPDATE companies
        SET 
            name = COALESCE($1, name),
            email_config = COALESCE($2, email_config),
            rules_json = COALESCE($3, rules_json),
            storage_prefix = COALESCE($4, storage_prefix),
            updated_at = $5
        WHERE id = $6
    """
    
    await conn.execute(
        update_query,
        settings.get('name'),
        json.dumps(settings.get('email_config')) if settings.get('email_config') else None,
        json.dumps(settings.get('rules_json')) if settings.get('rules_json') else None,
        settings.get('storage_prefix'),
        datetime.utcnow(),
        current_user.company_id
    )
    
    return {"message": "Company settings updated successfully"}