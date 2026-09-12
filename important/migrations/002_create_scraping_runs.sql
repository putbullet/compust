CREATE TABLE IF NOT EXISTS scraping_runs (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    scrape_target_id INT UNSIGNED NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    started_at DATETIME NULL,
    finished_at DATETIME NULL,
    jobs_found INT NOT NULL DEFAULT 0,
    jobs_added INT NOT NULL DEFAULT 0,
    jobs_updated INT NOT NULL DEFAULT 0,
    parser_errors JSON NULL,
    request_error TEXT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    INDEX idx_scraping_runs_target (scrape_target_id),
    INDEX idx_scraping_runs_status (status),
    CONSTRAINT fk_scraping_runs_target
        FOREIGN KEY (scrape_target_id) REFERENCES scrape_targets (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
