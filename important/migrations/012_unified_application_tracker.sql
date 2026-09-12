-- Migration 012: Unified Application Management & Spreadsheet Tracker
-- Enables manual external applications, contact tracking, transition history, and source attribution.

ALTER TABLE user_applications MODIFY job_id INT UNSIGNED NULL;

ALTER TABLE user_applications ADD COLUMN custom_job_title VARCHAR(255) NULL;
ALTER TABLE user_applications ADD COLUMN custom_company_name VARCHAR(255) NULL;
ALTER TABLE user_applications ADD COLUMN custom_location VARCHAR(255) NULL;
ALTER TABLE user_applications ADD COLUMN custom_country VARCHAR(100) NULL;
ALTER TABLE user_applications ADD COLUMN custom_job_url VARCHAR(1024) NULL;
ALTER TABLE user_applications ADD COLUMN source VARCHAR(100) NOT NULL DEFAULT 'Compust';
ALTER TABLE user_applications ADD COLUMN salary VARCHAR(100) NULL;
ALTER TABLE user_applications ADD COLUMN employment_type VARCHAR(100) NULL;
ALTER TABLE user_applications ADD COLUMN contact_name VARCHAR(255) NULL;
ALTER TABLE user_applications ADD COLUMN contact_email VARCHAR(255) NULL;
ALTER TABLE user_applications ADD COLUMN contact_phone VARCHAR(100) NULL;
ALTER TABLE user_applications ADD COLUMN recruiter VARCHAR(255) NULL;
ALTER TABLE user_applications ADD COLUMN referral VARCHAR(255) NULL;
ALTER TABLE user_applications ADD COLUMN priority VARCHAR(50) NOT NULL DEFAULT 'medium';
ALTER TABLE user_applications ADD COLUMN next_follow_up DATE NULL;
ALTER TABLE user_applications ADD COLUMN interview_date DATETIME NULL;

CREATE TABLE IF NOT EXISTS user_application_history (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    application_id INT UNSIGNED NOT NULL,
    from_status VARCHAR(50) NULL,
    to_status VARCHAR(50) NOT NULL,
    changed_at DATETIME NOT NULL,
    notes TEXT NULL,
    INDEX idx_uah_app (application_id),
    CONSTRAINT fk_uah_app FOREIGN KEY (application_id) REFERENCES user_applications(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
