"""
Properties router for BrightStone Property Monitoring System
Updated for single-document pipeline architecture
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import os
from db import get_pg_connection
from routers.auth import get_current_user, require_admin, UserInfo

router = APIRouter()

class PropertyCreate(BaseModel):
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

class PropertyUpdate(BaseModel):
    address: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    municipality_id: Optional[int] = None
    postal_code: Optional[str] = None
    property_type: Optional[str] = None
    size_sqft: Optional[int] = None
    year_built: Optional[int] = None
    zoning: Optional[str] = None
    notes: Optional[str] = None

class PropertyResponse(BaseModel):
    id: int
    company_id: int
    municipality_id: Optional[int]
    municipality_name: Optional[str]  # Joined from municipality table
    address: str
    city: str
    province: str
    postal_code: Optional[str]
    property_type: Optional[str]
    zoning: Optional[str]
    size_sqft: Optional[int]
    year_built: Optional[int]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

@router.get("/", response_model=List[PropertyResponse])
async def get_properties(
    current_user: UserInfo = Depends(get_current_user),
    conn = Depends(get_pg_connection)
):
    """Get all properties for the current user's company"""
    properties = await conn.fetch("""
        SELECT p.id, p.company_id, p.municipality_id, p.address, p.city, p.province, 
               p.postal_code, p.property_type, p.zoning, p.size_sqft, p.year_built, 
               p.notes, p.created_at, p.updated_at,
               m.name as municipality_name
        FROM properties p
        LEFT JOIN municipalities m ON m.id = p.municipality_id
        WHERE p.company_id = $1
        ORDER BY p.created_at DESC
    """, current_user.company_id)
    
    return [
        PropertyResponse(
            id=prop["id"],
            company_id=prop["company_id"],
            municipality_id=prop["municipality_id"],
            municipality_name=prop["municipality_name"],
            address=prop["address"],
            city=prop["city"],
            province=prop["province"],
            postal_code=prop["postal_code"],
            property_type=prop["property_type"],
            zoning=prop["zoning"],
            size_sqft=prop["size_sqft"],
            year_built=prop["year_built"],
            notes=prop["notes"],
            created_at=prop["created_at"],
            updated_at=prop["updated_at"]
        )
        for prop in properties
    ]

@router.post("/", response_model=PropertyResponse)
async def create_property(
    property: PropertyCreate,
    current_user: UserInfo = Depends(require_admin),
    conn = Depends(get_pg_connection)
):
    """Create a new property (admin only)"""
    result = await conn.fetchrow("""
        INSERT INTO properties (
            company_id, municipality_id, address, city, province, postal_code,
            property_type, size_sqft, year_built, zoning, notes
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
        )
        RETURNING id, company_id, municipality_id, address, city, province, postal_code, 
                  property_type, size_sqft, year_built, zoning, notes, created_at, updated_at
    """,
        current_user.company_id,
        property.municipality_id,
        property.address,
        property.city,
        property.province,
        property.postal_code,
        property.property_type,
        property.size_sqft,
        property.year_built,
        property.zoning,
        property.notes)
    
    # Get municipality name
    municipality_name = None
    if result["municipality_id"]:
        municipality_name = await conn.fetchval(
            "SELECT name FROM municipalities WHERE id = $1",
            result["municipality_id"]
        )
    
    return PropertyResponse(
        id=result["id"],
        company_id=result["company_id"],
        municipality_id=result["municipality_id"],
        municipality_name=municipality_name,
        address=result["address"],
        city=result["city"],
        province=result["province"],
        postal_code=result["postal_code"],
        property_type=result["property_type"],
        size_sqft=result["size_sqft"],
        year_built=result["year_built"],
        zoning=result["zoning"],
        notes=result["notes"],
        created_at=result["created_at"],
        updated_at=result["updated_at"]
    )

@router.get("/{property_id}", response_model=PropertyResponse)
async def get_property(
    property_id: int,
    current_user: UserInfo = Depends(get_current_user),
    conn = Depends(get_pg_connection)
):
    """Get a specific property"""
    property = await conn.fetchrow("""
        SELECT p.id, p.company_id, p.municipality_id, p.address, p.city, p.province, 
               p.postal_code, p.property_type, p.zoning, p.size_sqft, p.year_built, 
               p.notes, p.created_at, p.updated_at,
               m.name as municipality_name
        FROM properties p
        LEFT JOIN municipalities m ON m.id = p.municipality_id
        WHERE p.id = $1 AND p.company_id = $2
    """, property_id, current_user.company_id)
    
    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found"
        )
    
    return PropertyResponse(
        id=property["id"],
        company_id=property["company_id"],
        municipality_id=property["municipality_id"],
        municipality_name=property["municipality_name"],
        address=property["address"],
        city=property["city"],
        province=property["province"],
        postal_code=property["postal_code"],
        property_type=property["property_type"],
        size_sqft=property["size_sqft"],
        year_built=property["year_built"],
        zoning=property["zoning"],
        notes=property["notes"],
        created_at=property["created_at"],
        updated_at=property["updated_at"]
    )

@router.put("/{property_id}", response_model=PropertyResponse)
async def update_property(
    property_id: int,
    property_update: PropertyUpdate,
    current_user: UserInfo = Depends(require_admin),
    conn = Depends(get_pg_connection)
):
    """Update a property (admin only)"""
    # Build update query dynamically
    field_map = {
        "address": property_update.address,
        "city": property_update.city,
        "province": property_update.province,
        "municipality_id": property_update.municipality_id,
        "postal_code": property_update.postal_code,
        "property_type": property_update.property_type,
        "size_sqft": property_update.size_sqft,
        "year_built": property_update.year_built,
        "zoning": property_update.zoning,
        "notes": property_update.notes,
    }
    updates = []
    values = []
    param_count = 1
    for col, val in field_map.items():
        if val is not None:
            updates.append(f"{col} = ${{param_count}}")
            values.append(val)
            param_count += 1
    
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    # Add property_id and company_id to values
    values.extend([property_id, current_user.company_id])
    
    query = f"""
        UPDATE properties
        SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP
        WHERE id = ${param_count} AND company_id = ${param_count + 1}
        RETURNING id, company_id, municipality_id, address, city, province, postal_code, 
                  property_type, size_sqft, year_built, zoning, notes, created_at, updated_at
    """
    
    result = await conn.fetchrow(query, *values)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found"
        )
    
    # Get municipality name
    municipality_name = None
    if result["municipality_id"]:
        municipality_name = await conn.fetchval(
            "SELECT name FROM municipalities WHERE id = $1",
            result["municipality_id"]
        )
    
    return PropertyResponse(
        id=result["id"],
        company_id=result["company_id"],
        municipality_id=result["municipality_id"],
        municipality_name=municipality_name,
        address=result["address"],
        city=result["city"],
        province=result["province"],
        postal_code=result["postal_code"],
        property_type=result["property_type"],
        size_sqft=result["size_sqft"],
        year_built=result["year_built"],
        zoning=result["zoning"],
        notes=result["notes"],
        created_at=result["created_at"],
        updated_at=result["updated_at"]
    )

@router.delete("/{property_id}")
async def delete_property(
    property_id: int,
    current_user: UserInfo = Depends(require_admin),
    conn = Depends(get_pg_connection)
):
    """Delete a property (admin only)"""
    result = await conn.execute("""
        DELETE FROM properties
        WHERE id = $1 AND company_id = $2
    """, property_id, current_user.company_id)
    
    if result == "DELETE 0":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found"
        )
    
    return {"message": "Property deleted successfully"}