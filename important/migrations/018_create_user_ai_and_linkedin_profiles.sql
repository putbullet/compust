CREATE TABLE IF NOT EXISTS user_ai_configs (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL UNIQUE,
    active_provider VARCHAR(50) NOT NULL DEFAULT 'ollama',
    selected_model VARCHAR(100) NULL,
    gemini_model VARCHAR(100) NULL DEFAULT 'gemini-2.5-flash',
    openai_model VARCHAR(100) NULL DEFAULT 'gpt-4o-mini',
    consent_granted BOOLEAN NOT NULL DEFAULT 0,
    gemini_api_key_encrypted TEXT NULL,
    openai_api_key_encrypted TEXT NULL,
    fallback_policy VARCHAR(50) NOT NULL DEFAULT 'deterministic',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_ai_configs_user (user_id),
    CONSTRAINT fk_user_ai_configs_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS user_linkedin_profiles (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL UNIQUE,
    linkedin_url VARCHAR(500) NOT NULL,
    handle VARCHAR(100) NOT NULL,
    import_source VARCHAR(50) NOT NULL DEFAULT 'manual',
    imported_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    raw_data JSON NULL,
    INDEX idx_user_linkedin_profiles_user (user_id),
    CONSTRAINT fk_user_linkedin_profiles_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS user_unified_profiles (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL UNIQUE,
    version_hash VARCHAR(64) NOT NULL DEFAULT '',
    use_linkedin_in_matching BOOLEAN NOT NULL DEFAULT 1,
    unified_data JSON NULL,
    conflicts JSON NULL,
    user_overrides JSON NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_unified_profiles_user (user_id),
    CONSTRAINT fk_user_unified_profiles_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
