CREATE TABLE IF NOT EXISTS customized_resumes (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL,
    base_resume_id INT UNSIGNED NOT NULL,
    job_id INT UNSIGNED NOT NULL,
    version INT NOT NULL DEFAULT 1,
    pdf_filename VARCHAR(255) NULL,
    docx_filename VARCHAR(255) NULL,
    raw_text MEDIUMTEXT NOT NULL,
    parsed_sections JSON NULL,
    ats_analysis JSON NULL,
    recommendations JSON NULL,
    created_at DATETIME NOT NULL,
    INDEX idx_cust_resume_user_job (user_id, job_id),
    CONSTRAINT fk_cust_resume_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_cust_resume_base FOREIGN KEY (base_resume_id) REFERENCES resumes(id) ON DELETE CASCADE,
    CONSTRAINT fk_cust_resume_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
