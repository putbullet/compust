CREATE TABLE IF NOT EXISTS job_translations (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    job_id INT UNSIGNED NOT NULL,
    language VARCHAR(10) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT NULL,
    source_language VARCHAR(10) NOT NULL DEFAULT 'auto',
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    CONSTRAINT uq_job_translation_lang UNIQUE (job_id, language),
    INDEX idx_job_translations_job (job_id),
    INDEX idx_job_translations_lang (language),
    CONSTRAINT fk_job_translations_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
