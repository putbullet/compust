CREATE TABLE IF NOT EXISTS scrape_targets (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    company_id INT UNSIGNED NOT NULL,
    url VARCHAR(1000) NOT NULL,
    type VARCHAR(50) NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    last_scraped_at DATETIME NULL,
    status VARCHAR(50) NULL,
    PRIMARY KEY (id),
    INDEX idx_scrape_targets_company (company_id),
    INDEX idx_scrape_targets_active (active),
    CONSTRAINT fk_scrape_targets_company
        FOREIGN KEY (company_id) REFERENCES companies (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
