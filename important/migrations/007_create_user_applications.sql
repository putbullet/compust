CREATE TABLE IF NOT EXISTS user_applications (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL,
    job_id INT UNSIGNED NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'saved',
    notes TEXT NULL,
    applied_at DATETIME NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    CONSTRAINT uq_user_job UNIQUE (user_id, job_id),
    INDEX idx_user_applications_user (user_id),
    INDEX idx_user_applications_status (status),
    CONSTRAINT fk_user_applications_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_user_applications_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
