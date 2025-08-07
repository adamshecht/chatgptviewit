#!/usr/bin/env python3
"""
Verify the database migration status and data integrity
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv('../api/.env')

async def verify_migration():
    """Verify migration was applied correctly"""
    
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        print("❌ DATABASE_URL not found")
        return
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    print("=" * 60)
    print("DATABASE MIGRATION VERIFICATION")
    print("=" * 60)
    
    try:
        # Check migration status
        print("\n📋 Migration Status:")
        migrations = await conn.fetch("""
            SELECT version, applied_at 
            FROM schema_migrations 
            ORDER BY applied_at DESC
        """)
        
        if migrations:
            for m in migrations:
                print(f"  ✅ {m['version']} - Applied: {m['applied_at']}")
        else:
            print("  ⚠️  No migrations found")
        
        # Check table structure
        print("\n🔍 Schema Verification:")
        
        # Check if old VARCHAR company_id columns exist
        old_columns = await conn.fetch("""
            SELECT table_name, column_name, data_type 
            FROM information_schema.columns 
            WHERE column_name = 'company_id' 
            AND table_schema = 'public'
            ORDER BY table_name
        """)
        
        print("\n  Company ID columns:")
        for col in old_columns:
            if 'character' in col['data_type']:
                print(f"    ⚠️  {col['table_name']}.company_id is still VARCHAR")
            else:
                print(f"    ✅ {col['table_name']}.company_id is {col['data_type']}")
        
        # Check for new tables
        print("\n  New tables:")
        company_mun = await conn.fetchval("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_name = 'company_municipalities'
        """)
        if company_mun:
            count = await conn.fetchval("SELECT COUNT(*) FROM company_municipalities")
            print(f"    ✅ company_municipalities exists ({count} records)")
        else:
            print(f"    ❌ company_municipalities missing")
        
        # Check for removed tables
        print("\n  Removed tables:")
        notifications = await conn.fetchval("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_name = 'notifications'
        """)
        if notifications:
            print(f"    ❌ notifications table still exists (should be removed)")
        else:
            print(f"    ✅ notifications table removed")
        
        flagged = await conn.fetchval("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_name = 'flagged_item_comments'
        """)
        if flagged:
            print(f"    ❌ flagged_item_comments table still exists (should be removed)")
        else:
            print(f"    ✅ flagged_item_comments table removed")
        
        # Check data integrity
        print("\n📊 Data Integrity:")
        
        # Check for orphaned alerts
        orphaned_alerts = await conn.fetchval("""
            SELECT COUNT(*) FROM alerts a
            LEFT JOIN companies c ON a.company_id = c.id
            WHERE c.id IS NULL
        """)
        if orphaned_alerts > 0:
            print(f"  ❌ {orphaned_alerts} orphaned alerts found")
        else:
            print(f"  ✅ No orphaned alerts")
        
        # Check for orphaned documents
        orphaned_docs = await conn.fetchval("""
            SELECT COUNT(*) FROM documents d
            LEFT JOIN meetings m ON d.meeting_id = m.id
            WHERE m.id IS NULL
        """)
        if orphaned_docs > 0:
            print(f"  ❌ {orphaned_docs} orphaned documents found")
        else:
            print(f"  ✅ No orphaned documents")
        
        # Check document uniqueness
        duplicate_docs = await conn.fetch("""
            SELECT content_hash, COUNT(*) as count
            FROM documents 
            WHERE content_hash IS NOT NULL
            GROUP BY content_hash 
            HAVING COUNT(*) > 1
        """)
        if duplicate_docs:
            print(f"  ⚠️  {len(duplicate_docs)} duplicate documents by content_hash")
            for doc in duplicate_docs[:5]:  # Show first 5
                print(f"      - Hash {doc['content_hash'][:16]}... has {doc['count']} copies")
        else:
            print(f"  ✅ No duplicate documents")
        
        # Statistics
        print("\n📈 Database Statistics:")
        stats = await conn.fetchrow("""
            SELECT 
                (SELECT COUNT(*) FROM companies) as companies,
                (SELECT COUNT(*) FROM users) as users,
                (SELECT COUNT(*) FROM municipalities) as municipalities,
                (SELECT COUNT(*) FROM meetings) as meetings,
                (SELECT COUNT(*) FROM documents) as documents,
                (SELECT COUNT(*) FROM alerts) as alerts,
                (SELECT COUNT(*) FROM properties) as properties,
                (SELECT COUNT(*) FROM company_municipalities) as subscriptions
        """)
        
        for key, value in stats.items():
            print(f"  {key:15}: {value:,}")
        
        # Check indexes
        print("\n🔧 Index Verification:")
        important_indexes = [
            'idx_documents_hash',
            'idx_alerts_company_status',
            'idx_properties_company',
            'idx_meetings_municipality'
        ]
        
        for idx_name in important_indexes:
            exists = await conn.fetchval("""
                SELECT COUNT(*) FROM pg_indexes 
                WHERE indexname = $1
            """, idx_name)
            if exists:
                print(f"  ✅ {idx_name}")
            else:
                print(f"  ❌ {idx_name} missing")
        
        # Summary
        print("\n" + "=" * 60)
        print("VERIFICATION COMPLETE")
        print("=" * 60)
        
        # Determine overall status
        if orphaned_alerts == 0 and orphaned_docs == 0 and company_mun > 0:
            print("\n✅ Migration appears successful!")
            print("   All critical checks passed.")
        else:
            print("\n⚠️  Some issues detected.")
            print("   Review the warnings above.")
        
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(verify_migration())