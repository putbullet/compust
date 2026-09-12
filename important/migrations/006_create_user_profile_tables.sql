CREATE TABLE IF NOT EXISTS user_experience (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL,
    title VARCHAR(255) NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    experience_type VARCHAR(100) NULL DEFAULT 'professional',
    start_date DATE NULL,
    end_date DATE NULL,
    description TEXT NULL,
    INDEX idx_user_experience_user (user_id),
    CONSTRAINT fk_user_experience_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS user_education (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL,
    institution VARCHAR(255) NOT NULL,
    degree VARCHAR(255) NULL,
    field_of_study VARCHAR(255) NULL,
    start_date DATE NULL,
    end_date DATE NULL,
    description TEXT NULL,
    INDEX idx_user_education_user (user_id),
    CONSTRAINT fk_user_education_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS user_languages (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL,
    language VARCHAR(100) NOT NULL,
    proficiency VARCHAR(50) NULL DEFAULT 'fluent',
    INDEX idx_user_languages_user (user_id),
    CONSTRAINT fk_user_languages_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
