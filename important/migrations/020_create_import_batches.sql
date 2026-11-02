CREATE TABLE IF NOT EXISTS import_batches (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    batch_id VARCHAR(64) NOT NULL UNIQUE,
    source_type VARCHAR(50) NOT NULL,
    source_location VARCHAR(500) NOT NULL,
    strategy VARCHAR(50) NOT NULL,
    target_user_id INT UNSIGNED NULL,
    imported_at DATETIME NOT NULL,
    counts JSON NULL,
    created_row_ids JSON NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'completed',
    undone_at DATETIME NULL,
    INDEX idx_import_batches_batch_id (batch_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
