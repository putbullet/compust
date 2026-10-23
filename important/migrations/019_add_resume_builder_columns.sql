-- Migration 019: Add resume builder and versioning columns to resumes table
-- Ensures full schema parity between SQLite and MySQL environments.

ALTER TABLE resumes ADD COLUMN title VARCHAR(255) DEFAULT 'My Resume';
ALTER TABLE resumes ADD COLUMN is_default BOOLEAN DEFAULT 0;
ALTER TABLE resumes ADD COLUMN target_job_id INT UNSIGNED NULL;
ALTER TABLE resumes ADD COLUMN source_resume_id INT UNSIGNED NULL;
ALTER TABLE resumes ADD COLUMN structured_data JSON NULL;
ALTER TABLE resumes ADD COLUMN settings JSON NULL;
ALTER TABLE resumes ADD COLUMN is_original_upload BOOLEAN DEFAULT 0;
