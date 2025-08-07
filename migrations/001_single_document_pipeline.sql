-- Migration: Single-Copy Document Pipeline
-- Purpose: Refactor database to share documents globally while maintaining per-company alerts
-- Date: 2025-01-09

-- =====================================================
-- UP MIGRATION
-- =====================================================

BEGIN;

-- =====================================================
-- 1. GLOBAL ENTITIES - Make them company-agnostic
-- =====================================================

-- municipalities: Remove company_id
ALTER TABLE municipalities 
DROP COLUMN IF EXISTS company_id CASCADE;

-- meetings: Remove company_id and location
ALTER TABLE meetings 
DROP COLUMN IF EXISTS company_id CASCADE,
DROP COLUMN IF EXISTS location CASCADE;

-- Ensure proper foreign key for municipality_id if not exists
ALTER TABLE meetings 
DROP CONSTRAINT IF EXISTS meetings_new_municipality_id_fkey;

ALTER TABLE meetings 
ADD CONSTRAINT meetings_municipality_id_fkey 
FOREIGN KEY (municipality_id) REFERENCES municipalities(id) ON DELETE CASCADE;

-- documents: Clean up and rename
-- First, store the meeting_guid to meeting_id mapping
CREATE TEMP TABLE temp_meeting_mapping AS
SELECT d.id as document_id, m.id as meeting_id_int
FROM documents d
JOIN meetings m ON d.meeting_guid = m.guid;

-- Drop company-specific columns
ALTER TABLE documents 
DROP COLUMN IF EXISTS company_id CASCADE,
DROP COLUMN IF EXISTS municipality_name CASCADE;

-- Add new meeting_id column as INT
ALTER TABLE documents 
ADD COLUMN meeting_id_new INT;

-- Populate the new meeting_id column
UPDATE documents d
SET meeting_id_new = t.meeting_id_int
FROM temp_meeting_mapping t
WHERE d.id = t.document_id;

-- Drop old meeting_guid column and rename new one
ALTER TABLE documents 
DROP COLUMN meeting_guid CASCADE;

ALTER TABLE documents 
RENAME COLUMN meeting_id_new TO meeting_id;

-- Add foreign key constraint
ALTER TABLE documents
ADD CONSTRAINT documents_meeting_id_fkey 
FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE;

-- Make meeting_id NOT NULL after population
ALTER TABLE documents 
ALTER COLUMN meeting_id SET NOT NULL;

-- =====================================================
-- 2. LINK TABLES
-- =====================================================

-- Create company_municipalities link table
CREATE TABLE IF NOT EXISTS company_municipalities (
    company_id INT NOT NULL,
    municipality_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (company_id, municipality_id)
);

-- We need to update this after we fix the companies table references
-- Will add foreign keys after company_id migration

-- =====================================================
-- 3. TENANT-SPECIFIC TABLES - Convert VARCHAR to INT FKs
-- =====================================================

-- First, ensure companies table has an integer ID
-- Assuming it already has id as SERIAL PRIMARY KEY

-- ALERTS table migration
ALTER TABLE alerts ADD COLUMN company_id_int INT;

UPDATE alerts a
SET company_id_int = c.id
FROM companies c
WHERE a.company_id = c.company_id;

ALTER TABLE alerts DROP COLUMN company_id CASCADE;
ALTER TABLE alerts RENAME COLUMN company_id_int TO company_id;
ALTER TABLE alerts ADD CONSTRAINT alerts_company_id_fkey 
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE;
ALTER TABLE alerts ALTER COLUMN company_id SET NOT NULL;

-- Drop unnecessary columns from alerts
ALTER TABLE alerts 
DROP COLUMN IF EXISTS municipality CASCADE,
DROP COLUMN IF EXISTS meeting_type CASCADE,
DROP COLUMN IF EXISTS meeting_date CASCADE;

-- Ensure document_id is INT and has proper FK (it's currently VARCHAR)
ALTER TABLE alerts ADD COLUMN document_id_int INT;

-- Try to convert document_id if it's numeric
UPDATE alerts 
SET document_id_int = CASE 
    WHEN document_id ~ '^\d+$' THEN document_id::INT 
    ELSE NULL 
END;

ALTER TABLE alerts DROP COLUMN document_id CASCADE;
ALTER TABLE alerts RENAME COLUMN document_id_int TO document_id;
ALTER TABLE alerts ADD CONSTRAINT alerts_document_id_fkey 
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE;

-- AUDIT_TRAILS table migration
ALTER TABLE audit_trails ADD COLUMN company_id_int INT;

UPDATE audit_trails a
SET company_id_int = c.id
FROM companies c
WHERE a.company_id = c.company_id;

ALTER TABLE audit_trails DROP COLUMN company_id CASCADE;
ALTER TABLE audit_trails RENAME COLUMN company_id_int TO company_id;
ALTER TABLE audit_trails ADD CONSTRAINT audit_trails_company_id_fkey 
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE;

-- INGEST_JOBS table migration
ALTER TABLE ingest_jobs ADD COLUMN company_id_int INT;

UPDATE ingest_jobs i
SET company_id_int = c.id
FROM companies c
WHERE i.company_id = c.company_id;

ALTER TABLE ingest_jobs DROP COLUMN company_id CASCADE;
ALTER TABLE ingest_jobs RENAME COLUMN company_id_int TO company_id;
ALTER TABLE ingest_jobs ADD CONSTRAINT ingest_jobs_company_id_fkey 
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE;
ALTER TABLE ingest_jobs ALTER COLUMN company_id SET NOT NULL;

-- USERS table migration
ALTER TABLE users ADD COLUMN company_id_int INT;

UPDATE users u
SET company_id_int = c.id
FROM companies c
WHERE u.company_id = c.company_id;

ALTER TABLE users DROP COLUMN company_id CASCADE;
ALTER TABLE users RENAME COLUMN company_id_int TO company_id;
ALTER TABLE users ADD CONSTRAINT users_company_id_fkey 
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE;

-- PROPERTIES table migration
ALTER TABLE properties ADD COLUMN company_id_int INT;

UPDATE properties p
SET company_id_int = c.id
FROM companies c
WHERE p.company_id = c.company_id;

ALTER TABLE properties DROP COLUMN company_id CASCADE;
ALTER TABLE properties RENAME COLUMN company_id_int TO company_id;
ALTER TABLE properties ADD CONSTRAINT properties_company_id_fkey 
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE;
ALTER TABLE properties ALTER COLUMN company_id SET NOT NULL;

-- =====================================================
-- 4. TABLE-SPECIFIC CHANGES
-- =====================================================

-- Properties: Add municipality_id
ALTER TABLE properties 
ADD COLUMN municipality_id INT REFERENCES municipalities(id);

-- Update unique constraint for properties
ALTER TABLE properties 
DROP CONSTRAINT IF EXISTS properties_company_id_address_city_key;

ALTER TABLE properties 
ADD CONSTRAINT properties_company_address_unique 
UNIQUE (company_id, address);

-- Now add foreign keys to company_municipalities
ALTER TABLE company_municipalities
ADD CONSTRAINT company_municipalities_company_id_fkey 
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
ADD CONSTRAINT company_municipalities_municipality_id_fkey 
    FOREIGN KEY (municipality_id) REFERENCES municipalities(id) ON DELETE CASCADE;

-- Populate company_municipalities from existing data
-- This assumes all companies were watching all municipalities they had data for
INSERT INTO company_municipalities (company_id, municipality_id)
SELECT DISTINCT c.id, m.id
FROM companies c
CROSS JOIN municipalities m
WHERE EXISTS (
    SELECT 1 FROM alerts a 
    JOIN documents d ON a.document_id = d.id
    JOIN meetings mt ON d.meeting_id = mt.id
    WHERE mt.municipality_id = m.id 
    AND a.company_id = c.id
)
ON CONFLICT DO NOTHING;

-- =====================================================
-- 5. DELETIONS / CONSOLIDATION
-- =====================================================

-- Drop notifications table
DROP TABLE IF EXISTS notifications CASCADE;

-- Drop flagged_item_comments table
DROP TABLE IF EXISTS flagged_item_comments CASCADE;

-- =====================================================
-- 6. ENUMS & INDEXES
-- =====================================================

-- Drop old indexes that reference dropped columns
DROP INDEX IF EXISTS idx_documents_company_id;
DROP INDEX IF EXISTS idx_documents_company;
DROP INDEX IF EXISTS idx_meetings_company_id;
DROP INDEX IF EXISTS idx_municipalities_company_id;

-- Create new optimized indexes
CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(content_hash);
CREATE INDEX IF NOT EXISTS idx_documents_meeting ON documents(meeting_id);
CREATE INDEX IF NOT EXISTS idx_alerts_company_status ON alerts(company_id, review_status);
CREATE INDEX IF NOT EXISTS idx_alerts_document ON alerts(document_id);
CREATE INDEX IF NOT EXISTS idx_properties_company ON properties(company_id);
CREATE INDEX IF NOT EXISTS idx_properties_municipality ON properties(municipality_id);
CREATE INDEX IF NOT EXISTS idx_meetings_municipality ON meetings(municipality_id);
CREATE INDEX IF NOT EXISTS idx_company_municipalities_company ON company_municipalities(company_id);
CREATE INDEX IF NOT EXISTS idx_company_municipalities_municipality ON company_municipalities(municipality_id);

-- Clean up temp table
DROP TABLE IF EXISTS temp_meeting_mapping;

COMMIT;

-- =====================================================
-- DOWN MIGRATION
-- =====================================================

-- BEGIN;

-- -- Restore notifications table
-- CREATE TABLE notifications (
--     id SERIAL PRIMARY KEY,
--     document_id INT REFERENCES documents(id),
--     property_name VARCHAR(255),
--     municipality_name VARCHAR(255),
--     email_to VARCHAR(500),
--     email_subject VARCHAR(500),
--     email_body TEXT,
--     status VARCHAR(20) DEFAULT 'pending',
--     retry_count INT DEFAULT 0,
--     max_retries INT DEFAULT 3,
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     sent_at TIMESTAMP,
--     error_message TEXT
-- );

-- -- Restore flagged_item_comments table
-- CREATE TABLE flagged_item_comments (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     document_id INT REFERENCES documents(id) ON DELETE CASCADE,
--     user_id UUID REFERENCES users(id) ON DELETE CASCADE,
--     comment TEXT NOT NULL,
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );

-- -- Restore VARCHAR company_id columns
-- -- ALERTS
-- ALTER TABLE alerts ADD COLUMN company_id_varchar VARCHAR(255);
-- UPDATE alerts a SET company_id_varchar = c.company_id FROM companies c WHERE a.company_id = c.id;
-- ALTER TABLE alerts DROP COLUMN company_id CASCADE;
-- ALTER TABLE alerts RENAME COLUMN company_id_varchar TO company_id;
-- ALTER TABLE alerts ALTER COLUMN company_id SET NOT NULL;

-- ALTER TABLE alerts 
-- ADD COLUMN municipality VARCHAR(100),
-- ADD COLUMN meeting_type VARCHAR(100),
-- ADD COLUMN meeting_date TIMESTAMP;

-- ALTER TABLE alerts ADD COLUMN document_id_varchar VARCHAR(255);
-- UPDATE alerts SET document_id_varchar = document_id::VARCHAR WHERE document_id IS NOT NULL;
-- ALTER TABLE alerts DROP COLUMN document_id CASCADE;
-- ALTER TABLE alerts RENAME COLUMN document_id_varchar TO document_id;
-- ALTER TABLE alerts ALTER COLUMN document_id SET NOT NULL;

-- -- AUDIT_TRAILS
-- ALTER TABLE audit_trails ADD COLUMN company_id_varchar VARCHAR(50);
-- UPDATE audit_trails a SET company_id_varchar = c.company_id FROM companies c WHERE a.company_id = c.id;
-- ALTER TABLE audit_trails DROP COLUMN company_id CASCADE;
-- ALTER TABLE audit_trails RENAME COLUMN company_id_varchar TO company_id;

-- -- INGEST_JOBS
-- ALTER TABLE ingest_jobs ADD COLUMN company_id_varchar VARCHAR(255);
-- UPDATE ingest_jobs i SET company_id_varchar = c.company_id FROM companies c WHERE i.company_id = c.id;
-- ALTER TABLE ingest_jobs DROP COLUMN company_id CASCADE;
-- ALTER TABLE ingest_jobs RENAME COLUMN company_id_varchar TO company_id;
-- ALTER TABLE ingest_jobs ALTER COLUMN company_id SET NOT NULL;

-- -- USERS
-- ALTER TABLE users ADD COLUMN company_id_varchar VARCHAR(100);
-- UPDATE users u SET company_id_varchar = c.company_id FROM companies c WHERE u.company_id = c.id;
-- ALTER TABLE users DROP COLUMN company_id CASCADE;
-- ALTER TABLE users RENAME COLUMN company_id_varchar TO company_id;

-- -- PROPERTIES
-- ALTER TABLE properties ADD COLUMN company_id_varchar VARCHAR(255);
-- UPDATE properties p SET company_id_varchar = c.company_id FROM companies c WHERE p.company_id = c.id;
-- ALTER TABLE properties DROP COLUMN company_id CASCADE;
-- ALTER TABLE properties RENAME COLUMN company_id_varchar TO company_id;
-- ALTER TABLE properties ALTER COLUMN company_id SET NOT NULL;
-- ALTER TABLE properties DROP COLUMN municipality_id;

-- ALTER TABLE properties DROP CONSTRAINT properties_company_address_unique;
-- ALTER TABLE properties ADD CONSTRAINT properties_company_id_address_city_key UNIQUE (company_id, address, city);

-- -- DOCUMENTS
-- ALTER TABLE documents ADD COLUMN meeting_guid VARCHAR(255);
-- UPDATE documents d SET meeting_guid = m.guid FROM meetings m WHERE d.meeting_id = m.id;
-- ALTER TABLE documents DROP COLUMN meeting_id CASCADE;
-- ALTER TABLE documents RENAME COLUMN meeting_guid TO meeting_guid;
-- ALTER TABLE documents ALTER COLUMN meeting_guid SET NOT NULL;

-- ALTER TABLE documents 
-- ADD COLUMN company_id VARCHAR(100) DEFAULT 'default',
-- ADD COLUMN municipality_name VARCHAR(100);

-- ALTER TABLE documents ADD CONSTRAINT documents_meeting_guid_fkey 
--     FOREIGN KEY (meeting_guid) REFERENCES meetings(guid);

-- -- MEETINGS
-- ALTER TABLE meetings 
-- ADD COLUMN company_id VARCHAR(100) DEFAULT 'default',
-- ADD COLUMN location VARCHAR(500);

-- -- MUNICIPALITIES
-- ALTER TABLE municipalities 
-- ADD COLUMN company_id VARCHAR(100) DEFAULT 'default';

-- -- Drop link table
-- DROP TABLE IF EXISTS company_municipalities CASCADE;

-- -- Restore old indexes
-- CREATE INDEX idx_documents_company_id ON documents(company_id);
-- CREATE INDEX idx_meetings_company_id ON meetings(company_id);
-- CREATE INDEX idx_municipalities_company_id ON municipalities(company_id);

-- -- Drop new indexes
-- DROP INDEX IF EXISTS idx_documents_hash;
-- DROP INDEX IF EXISTS idx_documents_meeting;
-- DROP INDEX IF EXISTS idx_alerts_company_status;
-- DROP INDEX IF EXISTS idx_alerts_document;
-- DROP INDEX IF EXISTS idx_properties_company;
-- DROP INDEX IF EXISTS idx_properties_municipality;
-- DROP INDEX IF EXISTS idx_meetings_municipality;
-- DROP INDEX IF EXISTS idx_company_municipalities_company;
-- DROP INDEX IF EXISTS idx_company_municipalities_municipality;

-- COMMIT;