-- Migration: Schema Optimizations
-- Purpose: Implement edge-case tweaks to prevent issues as data grows
-- Date: 2025-01-09

BEGIN;

-- =====================================================
-- 1. Documents uniqueness - Add content_hash uniqueness
-- =====================================================

-- Add unique constraint on content_hash to prevent duplicate files
ALTER TABLE documents 
ADD CONSTRAINT documents_content_hash_unique 
UNIQUE (content_hash);

-- =====================================================
-- 2. Properties - Make municipality_id NOT NULL
-- =====================================================

-- First check if there are any null municipality_id values
DO $$
DECLARE
    null_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO null_count 
    FROM properties 
    WHERE municipality_id IS NULL;
    
    IF null_count > 0 THEN
        RAISE NOTICE 'Found % properties with null municipality_id. Back-filling...', null_count;
        
        -- Try to back-fill based on city name matching municipality name
        UPDATE properties p
        SET municipality_id = m.id
        FROM municipalities m
        WHERE p.municipality_id IS NULL 
        AND LOWER(p.city) = LOWER(m.name);
        
        -- Check again after back-fill
        SELECT COUNT(*) INTO null_count 
        FROM properties 
        WHERE municipality_id IS NULL;
        
        IF null_count > 0 THEN
            RAISE NOTICE 'Still have % properties with null municipality_id after back-fill', null_count;
        END IF;
    END IF;
END $$;

-- Now make municipality_id NOT NULL
ALTER TABLE properties 
ALTER COLUMN municipality_id SET NOT NULL;

-- =====================================================
-- 3. Ingest_jobs - Change municipality to municipality_id FK
-- =====================================================

-- Add municipality_id column
ALTER TABLE ingest_jobs 
ADD COLUMN municipality_id INT;

-- Back-fill municipality_id based on municipality name
UPDATE ingest_jobs i
SET municipality_id = m.id
FROM municipalities m
WHERE i.municipality = m.name;

-- Add foreign key constraint
ALTER TABLE ingest_jobs
ADD CONSTRAINT ingest_jobs_municipality_id_fkey 
FOREIGN KEY (municipality_id) REFERENCES municipalities(id);

-- Drop old municipality column
ALTER TABLE ingest_jobs 
DROP COLUMN municipality;

-- =====================================================
-- 4. Companies - Rename rules_config to rules_json
-- =====================================================

-- Rename the column to follow naming convention
ALTER TABLE companies 
RENAME COLUMN rules_config TO rules_json;

-- =====================================================
-- 5. Alerts - Add index on (document_id, company_id)
-- =====================================================

-- Add composite index for querying all alerts for a document across companies
CREATE INDEX IF NOT EXISTS idx_alerts_document_company 
ON alerts(document_id, company_id);

-- =====================================================
-- 6. Audit_trails - Add created_at index
-- =====================================================

-- Add index for pruning old audit rows and daily reports
CREATE INDEX IF NOT EXISTS idx_audit_trails_created_at 
ON audit_trails(created_at);

-- =====================================================
-- 7. Municipalities - Add unique constraint on feed_url
-- =====================================================

-- Add unique constraint to prevent duplicate municipality entries
ALTER TABLE municipalities 
ADD CONSTRAINT municipalities_feed_url_unique 
UNIQUE (feed_url);

-- =====================================================
-- 8. Alerts - Add check constraint for review_status enum
-- =====================================================

-- First update existing 'reviewing' status to 'reviewed'
UPDATE alerts 
SET review_status = 'reviewed' 
WHERE review_status = 'reviewing';

-- Add check constraint to match documents.review_status pattern
ALTER TABLE alerts 
ADD CONSTRAINT alerts_review_status_check 
CHECK (review_status IN ('pending', 'reviewed', 'resolved'));

-- =====================================================
-- 9. Documents - Add ON UPDATE CASCADE to meeting_id FK
-- =====================================================

-- Drop existing constraint
ALTER TABLE documents 
DROP CONSTRAINT documents_meeting_id_fkey;

-- Re-add with ON UPDATE CASCADE
ALTER TABLE documents
ADD CONSTRAINT documents_meeting_id_fkey 
FOREIGN KEY (meeting_id) REFERENCES meetings(id) 
ON DELETE CASCADE ON UPDATE CASCADE;

-- =====================================================
-- 10. Additional performance optimizations
-- =====================================================

-- Add index on properties for common filtering
CREATE INDEX IF NOT EXISTS idx_properties_company_municipality 
ON properties(company_id, municipality_id);

-- Add index on company_municipalities for subscription queries
CREATE INDEX IF NOT EXISTS idx_company_municipalities_subscription 
ON company_municipalities(company_id, municipality_id);

-- Add index on meetings for date-based queries
CREATE INDEX IF NOT EXISTS idx_meetings_start_date 
ON meetings(start_at_local);

-- Add index on documents for status-based queries
CREATE INDEX IF NOT EXISTS idx_documents_status_created 
ON documents(status, created_at);

-- =====================================================
-- 11. Data validation and cleanup
-- =====================================================

-- Clean up any orphaned records
DELETE FROM alerts 
WHERE document_id IS NOT NULL 
AND document_id NOT IN (SELECT id FROM documents);

DELETE FROM audit_trails 
WHERE document_id IS NOT NULL 
AND document_id NOT IN (SELECT id FROM documents);

DELETE FROM properties 
WHERE municipality_id IS NOT NULL 
AND municipality_id NOT IN (SELECT id FROM municipalities);

-- =====================================================
-- 12. Update migration tracking
-- =====================================================

-- Record this migration
INSERT INTO schema_migrations (version) 
VALUES ('002_schema_optimizations')
ON CONFLICT (version) DO NOTHING;

COMMIT;

-- =====================================================
-- DOWN MIGRATION (if needed)
-- =====================================================

-- BEGIN;

-- -- Revert municipality_id to nullable
-- ALTER TABLE properties 
-- ALTER COLUMN municipality_id DROP NOT NULL;

-- -- Revert ingest_jobs changes
-- ALTER TABLE ingest_jobs 
-- ADD COLUMN municipality VARCHAR(100);
-- 
-- UPDATE ingest_jobs i
-- SET municipality = m.name
-- FROM municipalities m
-- WHERE i.municipality_id = m.id;
-- 
-- ALTER TABLE ingest_jobs 
-- DROP CONSTRAINT ingest_jobs_municipality_id_fkey;
-- ALTER TABLE ingest_jobs 
-- DROP COLUMN municipality_id;
-- 
-- -- Revert companies column rename
-- ALTER TABLE companies 
-- RENAME COLUMN rules_json TO rules_config;
-- 
-- -- Drop new indexes
-- DROP INDEX IF EXISTS idx_alerts_document_company;
-- DROP INDEX IF EXISTS idx_audit_trails_created_at;
-- DROP INDEX IF EXISTS idx_properties_company_municipality;
-- DROP INDEX IF EXISTS idx_company_municipalities_subscription;
-- DROP INDEX IF EXISTS idx_meetings_start_date;
-- DROP INDEX IF EXISTS idx_documents_status_created;
-- 
-- -- Drop new constraints
-- ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_content_hash_unique;
-- ALTER TABLE municipalities DROP CONSTRAINT IF EXISTS municipalities_feed_url_unique;
-- ALTER TABLE alerts DROP CONSTRAINT IF EXISTS alerts_review_status_check;
-- 
-- -- Revert documents FK
-- ALTER TABLE documents 
-- DROP CONSTRAINT documents_meeting_id_fkey;
-- 
-- ALTER TABLE documents
-- ADD CONSTRAINT documents_meeting_id_fkey 
-- FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE;
-- 
-- -- Remove migration record
-- DELETE FROM schema_migrations WHERE version = '002_schema_optimizations';
-- 
-- COMMIT; 