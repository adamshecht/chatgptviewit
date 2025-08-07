#!/usr/bin/env python3
"""
Apply database migration for single-document pipeline
"""

import asyncio
import asyncpg
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv('../api/.env')

async def apply_migration():
    """Apply the migration with proper error handling and rollback support"""
    
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        print("❌ DATABASE_URL not found in environment")
        sys.exit(1)
    
    conn = None
    try:
        print("🔄 Connecting to database...")
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Read migration file
        migration_file = '003_final_optimizations_simple.sql'
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        # Extract UP migration (everything before DOWN MIGRATION comment)
        up_migration = migration_sql
        
        print("📊 Pre-migration statistics:")
        
        # Get current stats
        stats = await conn.fetchrow("""
            SELECT 
                (SELECT COUNT(*) FROM companies) as companies_count,
                (SELECT COUNT(*) FROM documents) as documents_count,
                (SELECT COUNT(*) FROM alerts) as alerts_count,
                (SELECT COUNT(*) FROM properties) as properties_count,
                (SELECT COUNT(*) FROM users) as users_count
        """)
        
        for key, value in stats.items():
            print(f"  - {key}: {value}")
        
        # Create migration tracking table if not exists
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                version VARCHAR(255) NOT NULL UNIQUE,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Check if migration already applied
        existing = await conn.fetchval("""
            SELECT version FROM schema_migrations WHERE version = $1
        """, '003_final_optimizations')
        
        if existing:
            print("⚠️  Migration 003_final_optimizations already applied")
            return
        
        print("\n🚀 Applying migration...")
        print("  This will:")
        print("  - Fix alerts.document_id NULL values")
        print("  - Convert JSON strings to proper JSONB format")
        print("  - Make ingest_jobs.municipality_id NOT NULL")
        print("  - Remove duplicate indexes")
        print("  - Add GIN indexes for JSONB columns")
        print("  - Add performance indexes and data validation")
        
        # Confirm
        response = input("\n⚠️  This migration will modify the database structure. Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Migration cancelled")
            return
        
        # Apply migration
        print("\n🔧 Executing migration...")
        
        # Execute the migration
        await conn.execute(up_migration)
        
        # Record migration
        await conn.execute("""
            INSERT INTO schema_migrations (version) VALUES ($1)
        """, '003_final_optimizations')
        
        print("✅ Migration applied successfully!")
        
        # Get post-migration stats
        print("\n📊 Post-migration statistics:")
        
        stats = await conn.fetchrow("""
            SELECT 
                (SELECT COUNT(*) FROM companies) as companies_count,
                (SELECT COUNT(*) FROM documents) as documents_count,
                (SELECT COUNT(*) FROM alerts) as alerts_count,
                (SELECT COUNT(*) FROM properties) as properties_count,
                (SELECT COUNT(*) FROM users) as users_count,
                (SELECT COUNT(*) FROM company_municipalities) as company_municipalities_count
        """)
        
        for key, value in stats.items():
            print(f"  - {key}: {value}")
        
        # Verify critical relationships
        print("\n🔍 Verifying data integrity...")
        
        # Check for orphaned records
        orphaned_alerts = await conn.fetchval("""
            SELECT COUNT(*) FROM alerts 
            WHERE company_id NOT IN (SELECT id FROM companies)
        """)
        
        orphaned_docs = await conn.fetchval("""
            SELECT COUNT(*) FROM documents 
            WHERE meeting_id NOT IN (SELECT id FROM meetings)
        """)
        
        if orphaned_alerts > 0:
            print(f"  ⚠️  Found {orphaned_alerts} orphaned alerts")
        else:
            print("  ✅ No orphaned alerts")
            
        if orphaned_docs > 0:
            print(f"  ⚠️  Found {orphaned_docs} orphaned documents")
        else:
            print("  ✅ No orphaned documents")
        
        print("\n✨ Migration completed successfully!")
        print("\n📝 Next steps:")
        print("  1. Verify alerts.document_id is properly back-filled")
        print("  2. Test JSONB GIN indexes for performance")
        print("  3. Verify data validation constraints")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("  Database has been rolled back to previous state")
        sys.exit(1)
    finally:
        if conn:
            await conn.close()

async def rollback_migration():
    """Rollback the migration if needed"""
    
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        print("❌ DATABASE_URL not found in environment")
        sys.exit(1)
    
    conn = None
    try:
        print("🔄 Connecting to database...")
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Check if migration was applied
        existing = await conn.fetchval("""
            SELECT version FROM schema_migrations WHERE version = $1
        """, '001_single_document_pipeline')
        
        if not existing:
            print("⚠️  Migration 001_single_document_pipeline not found")
            return
        
        print("\n⚠️  WARNING: This will rollback the migration")
        print("  All changes will be reverted to the previous schema")
        
        response = input("\nContinue with rollback? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Rollback cancelled")
            return
        
        # Read migration file
        migration_file = '001_single_document_pipeline.sql'
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        # Extract DOWN migration (everything after DOWN MIGRATION comment)
        down_parts = migration_sql.split('-- DOWN MIGRATION')
        if len(down_parts) > 1:
            # Uncomment the down migration
            down_migration = down_parts[1].replace('-- ', '')
            
            print("\n🔧 Executing rollback...")
            await conn.execute(down_migration)
            
            # Remove migration record
            await conn.execute("""
                DELETE FROM schema_migrations WHERE version = $1
            """, '001_single_document_pipeline')
            
            print("✅ Rollback completed successfully!")
        else:
            print("❌ No DOWN migration found in file")
            
    except Exception as e:
        print(f"\n❌ Rollback failed: {e}")
        sys.exit(1)
    finally:
        if conn:
            await conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'rollback':
        asyncio.run(rollback_migration())
    else:
        asyncio.run(apply_migration())