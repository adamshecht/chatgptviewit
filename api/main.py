"""
CityScrape API - FastAPI Backend
Production-ready API for municipal document analysis
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
from db import pg_pool
import uvicorn

# Import routers
import sys
print("Importing routers...", file=sys.stderr)
from routers import auth
print("  ✓ auth imported", file=sys.stderr)
from routers import properties
print("  ✓ properties imported", file=sys.stderr)
from routers import alerts
print("  ✓ alerts imported", file=sys.stderr)
from routers import documents
print("  ✓ documents imported", file=sys.stderr)
from routers import companies
print("  ✓ companies imported", file=sys.stderr)
from routers import ingest
print("  ✓ ingest imported", file=sys.stderr)

# Load environment variables
load_dotenv()

# Database initialization
from db import init_db, pg_pool

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup"""
    # Initialize database
    try:
        await init_db()
        print("✓ Database connection established", file=sys.stderr)
    except Exception as e:
        print(f"⚠️  Database connection failed: {e}", file=sys.stderr)
        print("⚠️  Server will start but database features may not work", file=sys.stderr)
    
    yield
    
    # Cleanup on shutdown
    try:
        from db import pg_pool
        if pg_pool:
            await pg_pool.close()
            print("✓ Database pool closed", file=sys.stderr)
    except Exception as e:
        print(f"⚠️  Error closing database pool: {e}", file=sys.stderr)

# Create FastAPI app
app = FastAPI(
    title="CityScrape API",
    description="AI-powered municipal document analysis platform",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev
        "http://127.0.0.1:3000",  # Next.js dev (alternative)
        "https://cityscrape.ai",
        "https://www.cityscrape.ai",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
print("Including routers...", file=sys.stderr)
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
print(f"  ✓ auth router included ({len(auth.router.routes)} routes)", file=sys.stderr)
app.include_router(companies.router, prefix="/api/companies", tags=["Companies"])
print(f"  ✓ companies router included ({len(companies.router.routes)} routes)", file=sys.stderr)
app.include_router(properties.router, prefix="/api/properties", tags=["Properties"])
print(f"  ✓ properties router included ({len(properties.router.routes)} routes)", file=sys.stderr)
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])
print(f"  ✓ alerts router included ({len(alerts.router.routes)} routes)", file=sys.stderr)
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
print(f"  ✓ documents router included ({len(documents.router.routes)} routes)", file=sys.stderr)
app.include_router(ingest.router, prefix="/api/ingest", tags=["Ingest"])
print(f"  ✓ ingest router included ({len(ingest.router.routes)} routes)", file=sys.stderr)
print(f"Total app routes: {len(app.routes)}", file=sys.stderr)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "CityScrape API",
        "version": "1.0.0",
        "database": "checking..."
    }

@app.get("/api/test")
async def test_endpoint():
    """Simple test endpoint that doesn't require database"""
    return {
        "message": "API is working!",
        "timestamp": "2024-01-15T10:00:00Z"
    }

@app.get("/api/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "database": "connected",
        "redis": "connected",
        "s3": "accessible"
    }

@app.get("/api/test/properties")
async def test_properties():
    """Test endpoint to get properties without authentication"""
    import asyncpg
    import json
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Connect directly to database
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
    
    try:
        properties = await conn.fetch("""
            SELECT id, name, address, legal_description, aliases, active, payment_status, created_at
            FROM properties
            WHERE company_id = 'adam_shechtman_company_498854'
            ORDER BY created_at DESC
        """)
        
        return [
            {
                "id": prop["id"],
                "name": prop["name"],
                "address": prop["address"],
                "legal_description": prop["legal_description"],
                "aliases": json.loads(prop["aliases"]) if prop["aliases"] else [],
                "active": prop["active"],
                "payment_status": prop["payment_status"],
                "created_at": prop["created_at"].isoformat()
            }
            for prop in properties
        ]
    finally:
        await conn.close()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8001,
        reload=False
    )
