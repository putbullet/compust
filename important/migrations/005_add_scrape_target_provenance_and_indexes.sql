ALTER TABLE jobs ADD COLUMN scrape_target_id INT UNSIGNED NULL;
ALTER TABLE jobs ADD CONSTRAINT fk_jobs_scrape_target FOREIGN KEY (scrape_target_id) REFERENCES scrape_targets(id) ON DELETE SET NULL;

CREATE INDEX idx_jobs_company_external ON jobs (company_id, external_job_id);
CREATE INDEX idx_jobs_company_url ON jobs (company_id, job_url(255));
CREATE INDEX idx_jobs_target_seen ON jobs (scrape_target_id, last_seen_at);
CREATE INDEX idx_jobs_active ON jobs (active);
