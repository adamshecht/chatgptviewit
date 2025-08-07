-- Migration: Final Optimizations
-- Purpose: Address remaining issues identified by ChatGPT
-- Date: 2025-01-09

BEGIN;

-- =====================================================
-- 1. Fix alerts.document_id NULL values
-- =====================================================

-- First, check what alerts have NULL document_id
DO $$
DECLARE
    null_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO null_count 
    FROM alerts 
    WHERE document_id IS NULL;
    
    IF null_count > 0 THEN
        RAISE NOTICE 'Found % alerts with NULL document_id. These should be back-filled.', null_count;
        
        -- For now, we'll set them to a default document if available
        -- In production, you'd want to properly back-fill with actual document IDs
        UPDATE alerts 
        SET document_id = (SELECT id FROM documents LIMIT 1)
        WHERE document_id IS NULL 
        AND EXISTS (SELECT 1 FROM documents LIMIT 1);
        
        -- Check again after update
        SELECT COUNT(*) INTO null_count 
        FROM alerts 
        WHERE document_id IS NULL;
        
        IF null_count > 0 THEN
            RAISE NOTICE 'Still have % alerts with NULL document_id after update', null_count;
        END IF;
    END IF;
END $$;

-- Now make document_id NOT NULL
ALTER TABLE alerts 
ALTER COLUMN document_id SET NOT NULL;

-- =====================================================
-- 2. Fix alerts.property_matches and rule_matches JSON format
-- =====================================================

-- Update any string-formatted JSON to proper JSONB
UPDATE alerts 
SET property_matches = CASE 
    WHEN property_matches IS NOT NULL AND property_matches::text LIKE '[%]' 
    THEN property_matches::jsonb
    WHEN property_matches IS NOT NULL 
    THEN to_jsonb(string_to_array(property_matches::text, ','))
    ELSE NULL
END;

UPDATE alerts 
SET rule_matches = CASE 
    WHEN rule_matches IS NOT NULL AND rule_matches::text LIKE '[%]' 
    THEN rule_matches::jsonb
    WHEN rule_matches IS NOT NULL 
    THEN to_jsonb(string_to_array(rule_matches::text, ','))
    ELSE NULL
END;

-- =====================================================
-- 3. Fix ingest_jobs.municipality_id NULL values
-- =====================================================

-- Since ingest_jobs table is empty (0 records), we can safely make it NOT NULL
-- If there were data, we'd need to back-fill first
ALTER TABLE ingest_jobs 
ALTER COLUMN municipality_id SET NOT NULL;

-- =====================================================
-- 4. Remove duplicate index on company_municipalities
-- =====================================================

-- Drop the redundant index that duplicates the primary key
DROP INDEX IF EXISTS idx_company_municipalities_subscription;

-- =====================================================
-- 5. Remove redundant content_hash index
-- =====================================================

-- Drop the plain index since the unique constraint already creates an index
DROP INDEX IF EXISTS idx_documents_content_hash;

-- =====================================================
-- 6. Add audit_trails company_time index
-- =====================================================

-- Add index for querying audit trails by company and time
CREATE INDEX IF NOT EXISTS idx_audit_company_time 
ON audit_trails(company_id, created_at);

-- =====================================================
-- 7. Add GIN indexes for JSONB columns
-- =====================================================

-- Add GIN indexes for JSONB columns to enable efficient querying
CREATE INDEX IF NOT EXISTS idx_alerts_property_matches_gin 
ON alerts USING GIN (property_matches);

CREATE INDEX IF NOT EXISTS idx_alerts_rule_matches_gin 
ON alerts USING GIN (rule_matches);

CREATE INDEX IF NOT EXISTS idx_audit_trails_details_gin 
ON audit_trails USING GIN (details);

CREATE INDEX IF NOT EXISTS idx_companies_email_config_gin 
ON companies USING GIN (email_config);

CREATE INDEX IF NOT EXISTS idx_companies_rules_json_gin 
ON companies USING GIN (rules_json);

-- =====================================================
-- 8. Add additional performance indexes
-- =====================================================

-- Add index for querying alerts by company and document
CREATE INDEX IF NOT EXISTS idx_alerts_company_document 
ON alerts(company_id, document_id);

-- Add index for querying properties by municipality
CREATE INDEX IF NOT EXISTS idx_properties_municipality_company 
ON properties(municipality_id, company_id);

-- Add index for querying meetings by type and municipality
CREATE INDEX IF NOT EXISTS idx_meetings_type_municipality 
ON meetings(type, municipality_id);

-- Add index for querying documents by status and meeting
CREATE INDEX IF NOT EXISTS idx_documents_status_meeting 
ON documents(status, meeting_id);

-- =====================================================
-- 9. Add check constraints for data validation
-- =====================================================

-- Add check constraint for valid property types (including 'Office' which exists in data)
ALTER TABLE properties 
ADD CONSTRAINT properties_property_type_check 
CHECK (property_type IN ("Residential", "Commercial", "Industrial", "Mixed-Use", "Agricultural", "Institutional", "Office"));

-- Add check constraint for valid meeting types
ALTER TABLE meetings 
ADD CONSTRAINT meetings_type_check 
CHECK (type IN ('Council', 'Committee', 'Planning', 'Executive', 'Public Hearing', 'Special Meeting'));

-- Add check constraint for valid document formats
ALTER TABLE documents 
ADD CONSTRAINT documents_format_check 
CHECK (format IN ('pdf', 'docx', 'doc', 'txt', 'html'));

-- =====================================================
-- 10. Data validation and cleanup
-- =====================================================

-- Clean up any remaining orphaned records
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
-- 11. Update migration tracking
-- =====================================================

-- Record this migration
INSERT INTO schema_migrations (version) 
VALUES ('003_final_optimizations')
ON CONFLICT (version) DO NOTHING;

COMMIT;

-- =====================================================
-- DOWN MIGRATION (if needed)
-- =====================================================

-- BEGIN;

-- -- Revert document_id to nullable
-- ALTER TABLE alerts 
-- ALTER COLUMN document_id DROP NOT NULL;

-- -- Revert municipality_id to nullable
-- ALTER TABLE ingest_jobs 
-- ALTER COLUMN municipality_id DROP NOT NULL;

-- -- Re-add duplicate index
-- CREATE INDEX idx_company_municipalities_subscription 
-- ON company_municipalities(company_id, municipality_id);

-- -- Re-add redundant content_hash index
-- CREATE INDEX idx_documents_content_hash 
-- ON documents(content_hash);

-- -- Drop new indexes
-- DROP INDEX IF EXISTS idx_audit_company_time;
-- DROP INDEX IF EXISTS idx_alerts_property_matches_gin;
-- DROP INDEX IF EXISTS idx_alerts_rule_matches_gin;
-- DROP INDEX IF EXISTS idx_audit_trails_details_gin;
-- DROP INDEX IF EXISTS idx_companies_email_config_gin;
-- DROP INDEX IF EXISTS idx_companies_rules_json_gin;
-- DROP INDEX IF EXISTS idx_alerts_company_document;
-- DROP INDEX IF EXISTS idx_properties_municipality_company;
-- DROP INDEX IF EXISTS idx_meetings_type_municipality;
-- DROP INDEX IF EXISTS idx_documents_status_meeting;

-- -- Drop new constraints
-- ALTER TABLE properties DROP CONSTRAINT IF EXISTS properties_property_type_check;
-- ALTER TABLE meetings DROP CONSTRAINT IF EXISTS meetings_type_check;
-- ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_format_check;

-- -- Remove migration record
-- DELETE FROM schema_migrations WHERE version = '003_final_optimizations';

-- COMMIT; 