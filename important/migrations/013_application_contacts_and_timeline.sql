-- Migration 013: Application Contacts, Interactions, and Enhanced Timeline Tracking
-- Adds dedicated contacts management, interactions activity, and enhanced application event history.

CREATE TABLE IF NOT EXISTS contacts (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL,
    first_name VARCHAR(100) NULL,
    last_name VARCHAR(100) NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NULL,
    phone VARCHAR(100) NULL,
    company VARCHAR(255) NULL,
    role VARCHAR(255) NULL,
    linkedin_url VARCHAR(1024) NULL,
    location VARCHAR(255) NULL,
    notes TEXT NULL,
    tags VARCHAR(500) NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    INDEX idx_contacts_user (user_id),
    INDEX idx_contacts_email (email),
    INDEX idx_contacts_company (company),
    CONSTRAINT fk_contacts_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS contact_interactions (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    contact_id INT UNSIGNED NOT NULL,
    application_id INT UNSIGNED NULL,
    user_id INT UNSIGNED NOT NULL,
    type VARCHAR(50) NOT NULL,
    interaction_date DATETIME NOT NULL,
    summary VARCHAR(255) NOT NULL,
    details TEXT NULL,
    created_at DATETIME NOT NULL,
    INDEX idx_ci_contact (contact_id),
    INDEX idx_ci_app (application_id),
    INDEX idx_ci_user (user_id),
    CONSTRAINT fk_ci_contact FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE,
    CONSTRAINT fk_ci_app FOREIGN KEY (application_id) REFERENCES user_applications(id) ON DELETE SET NULL,
    CONSTRAINT fk_ci_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE user_applications ADD COLUMN contact_id INT UNSIGNED NULL;
ALTER TABLE user_applications ADD CONSTRAINT fk_user_apps_contact FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE SET NULL;

ALTER TABLE user_application_history ADD COLUMN event_type VARCHAR(50) NOT NULL DEFAULT 'status_change';
ALTER TABLE user_application_history ADD COLUMN event_title VARCHAR(255) NULL;
