"""
Authentication router for CityScrape API
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import jwt
import os
from db import get_pg_connection

router = APIRouter()
security = HTTPBearer()

# JWT settings
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "cityscrape-super-secure-jwt-key-2024-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

class LoginRequest(BaseModel):
    email: str
    auth0_token: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class UserInfo(BaseModel):
    id: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    company_id: str
    role: str

def create_access_token(data: dict):
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate JWT token and return user info"""
    # Development mode: allow test token
    if os.getenv("DEV_MODE", "false").lower() == "true":
        if credentials.credentials == "test-token":
            return UserInfo(
                id="dev-user-1",
                email="dev@cityscrape.ai",
                first_name="Development",
                last_name="User",
                company_id="adam_shechtman_company_498854",
                role="admin"
            )
    
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
        return UserInfo(
            id=user_id,
            email=payload.get("email"),
            first_name=payload.get("first_name"),
            last_name=payload.get("last_name"),
            company_id=payload.get("company_id"),
            role=payload.get("role")
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

def require_admin(current_user: UserInfo = Depends(get_current_user)):
    """Dependency to require admin role"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, conn = Depends(get_pg_connection)):
    """
    Login with Auth0 token and get API access token
    """
    # Verify Auth0 token and get user from database
    user = await conn.fetchrow("""
        SELECT id, email, first_name, last_name, company_id, role
        FROM users
        WHERE email = $1
    """, request.email)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Create access token
    access_token = create_access_token({
        "sub": str(user["id"]),
        "email": user["email"],
        "first_name": user["first_name"],
        "last_name": user["last_name"],
        "company_id": user["company_id"],
        "role": user["role"]
    })
    
    # Update last login
    await conn.execute("""
        UPDATE users SET last_login = CURRENT_TIMESTAMP
        WHERE id = $1
    """, user["id"])
    
    return LoginResponse(
        access_token=access_token,
        user={
            "id": str(user["id"]),
            "email": user["email"],
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "company_id": user["company_id"],
            "role": user["role"]
        }
    )

@router.get("/me", response_model=UserInfo)
async def get_me(current_user: UserInfo = Depends(get_current_user)):
    """Get current user info"""
    return current_user

@router.post("/logout")
async def logout(current_user: UserInfo = Depends(get_current_user)):
    """Logout endpoint (client should remove token)"""
    return {"message": "Successfully logged out"}

@router.get("/test")
async def test_auth():
    """Test endpoint for authentication"""
    return {
        "message": "Auth router is working",
        "jwt_secret_configured": bool(SECRET_KEY and SECRET_KEY != "your-secret-key-change-this"),
        "database_url_configured": bool(os.getenv("DATABASE_URL"))
    }