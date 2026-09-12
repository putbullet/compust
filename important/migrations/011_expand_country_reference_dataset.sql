-- Migration 011: Expand Standard Country Reference Dataset
-- Adds standard global and regional recruiting markets without breaking existing IDs or duplicating records.

CREATE TABLE IF NOT EXISTS countries (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(10) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO countries (name, code)
SELECT 'United Arab Emirates', 'AE'
WHERE NOT EXISTS (SELECT 1 FROM countries WHERE code = 'AE');

INSERT INTO countries (name, code)
SELECT 'Saudi Arabia', 'SA'
WHERE NOT EXISTS (SELECT 1 FROM countries WHERE code = 'SA');

INSERT INTO countries (name, code)
SELECT 'Switzerland', 'CH'
WHERE NOT EXISTS (SELECT 1 FROM countries WHERE code = 'CH');

INSERT INTO countries (name, code)
SELECT 'Italy', 'IT'
WHERE NOT EXISTS (SELECT 1 FROM countries WHERE code = 'IT');

INSERT INTO countries (name, code)
SELECT 'Ireland', 'IE'
WHERE NOT EXISTS (SELECT 1 FROM countries WHERE code = 'IE');

INSERT INTO countries (name, code)
SELECT 'Sweden', 'SE'
WHERE NOT EXISTS (SELECT 1 FROM countries WHERE code = 'SE');

INSERT INTO countries (name, code)
SELECT 'Portugal', 'PT'
WHERE NOT EXISTS (SELECT 1 FROM countries WHERE code = 'PT');

INSERT INTO countries (name, code)
SELECT 'Poland', 'PL'
WHERE NOT EXISTS (SELECT 1 FROM countries WHERE code = 'PL');

INSERT INTO countries (name, code)
SELECT 'Singapore', 'SG'
WHERE NOT EXISTS (SELECT 1 FROM countries WHERE code = 'SG');

INSERT INTO countries (name, code)
SELECT 'Australia', 'AU'
WHERE NOT EXISTS (SELECT 1 FROM countries WHERE code = 'AU');

INSERT INTO countries (name, code)
SELECT 'Japan', 'JP'
WHERE NOT EXISTS (SELECT 1 FROM countries WHERE code = 'JP');

INSERT INTO countries (name, code)
SELECT 'Brazil', 'BR'
WHERE NOT EXISTS (SELECT 1 FROM countries WHERE code = 'BR');

INSERT INTO countries (name, code)
SELECT 'India', 'IN'
WHERE NOT EXISTS (SELECT 1 FROM countries WHERE code = 'IN');

INSERT INTO countries (name, code)
SELECT 'Egypt', 'EG'
WHERE NOT EXISTS (SELECT 1 FROM countries WHERE code = 'EG');

INSERT INTO countries (name, code)
SELECT 'Tunisia', 'TN'
WHERE NOT EXISTS (SELECT 1 FROM countries WHERE code = 'TN');

INSERT INTO countries (name, code)
SELECT 'Qatar', 'QA'
WHERE NOT EXISTS (SELECT 1 FROM countries WHERE code = 'QA');

INSERT INTO countries (name, code)
SELECT 'Kuwait', 'KW'
WHERE NOT EXISTS (SELECT 1 FROM countries WHERE code = 'KW');

INSERT INTO countries (name, code)
SELECT 'Bahrain', 'BH'
WHERE NOT EXISTS (SELECT 1 FROM countries WHERE code = 'BH');

INSERT INTO countries (name, code)
SELECT 'Oman', 'OM'
WHERE NOT EXISTS (SELECT 1 FROM countries WHERE code = 'OM');

INSERT INTO countries (name, code)
SELECT 'Luxembourg', 'LU'
WHERE NOT EXISTS (SELECT 1 FROM countries WHERE code = 'LU');

INSERT INTO countries (name, code)
SELECT 'Austria', 'AT'
WHERE NOT EXISTS (SELECT 1 FROM countries WHERE code = 'AT');

INSERT INTO countries (name, code)
SELECT 'Denmark', 'DK'
WHERE NOT EXISTS (SELECT 1 FROM countries WHERE code = 'DK');

INSERT INTO countries (name, code)
SELECT 'Norway', 'NO'
WHERE NOT EXISTS (SELECT 1 FROM countries WHERE code = 'NO');

INSERT INTO countries (name, code)
SELECT 'Finland', 'FI'
WHERE NOT EXISTS (SELECT 1 FROM countries WHERE code = 'FI');

INSERT INTO countries (name, code)
SELECT 'South Korea', 'KR'
WHERE NOT EXISTS (SELECT 1 FROM countries WHERE code = 'KR');

INSERT INTO countries (name, code)
SELECT 'China', 'CN'
WHERE NOT EXISTS (SELECT 1 FROM countries WHERE code = 'CN');

INSERT INTO countries (name, code)
SELECT 'Mexico', 'MX'
WHERE NOT EXISTS (SELECT 1 FROM countries WHERE code = 'MX');

INSERT INTO countries (name, code)
SELECT 'Turkey', 'TR'
WHERE NOT EXISTS (SELECT 1 FROM countries WHERE code = 'TR');

INSERT INTO countries (name, code)
SELECT 'South Africa', 'ZA'
WHERE NOT EXISTS (SELECT 1 FROM countries WHERE code = 'ZA');

INSERT INTO countries (name, code)
SELECT 'New Zealand', 'NZ'
WHERE NOT EXISTS (SELECT 1 FROM countries WHERE code = 'NZ');
