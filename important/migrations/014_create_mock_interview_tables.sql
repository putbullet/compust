-- Migration 014: Create AI Mock Interview & Skills Assessment Tables
-- Provides persistence for interview sessions, candidate turns, evaluations, assessments, and rubrics.

CREATE TABLE IF NOT EXISTS mock_interview_sessions (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NULL,
    domain_id VARCHAR(100) NOT NULL,
    role VARCHAR(255) NULL,
    difficulty VARCHAR(50) NOT NULL,
    duration_minutes INT NOT NULL,
    job_id INT UNSIGNED NULL,
    resume_id INT UNSIGNED NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'setup',
    started_at DATETIME NULL,
    ended_at DATETIME NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    interview_plan JSON NULL,
    evaluation_status VARCHAR(50) NOT NULL DEFAULT 'pending',
    INDEX idx_mock_sessions_user (user_id),
    INDEX idx_mock_sessions_domain (domain_id),
    CONSTRAINT fk_mock_sessions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_mock_sessions_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE SET NULL,
    CONSTRAINT fk_mock_sessions_resume FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS mock_interview_turns (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_id INT UNSIGNED NOT NULL,
    turn_index INT NOT NULL,
    question_id VARCHAR(100) NOT NULL,
    question_domain_id VARCHAR(100) NOT NULL,
    question_title VARCHAR(500) NOT NULL,
    question_category VARCHAR(255) NOT NULL,
    question_topic VARCHAR(255) NOT NULL,
    question_difficulty VARCHAR(50) NOT NULL,
    is_follow_up BOOLEAN NOT NULL DEFAULT FALSE,
    follow_up_focus VARCHAR(500) NULL,
    transcript_text TEXT NULL,
    stt_engine VARCHAR(50) NULL,
    stt_confidence FLOAT NULL,
    asked_at DATETIME NULL,
    answered_at DATETIME NULL,
    answer_duration_seconds FLOAT NULL,
    followup_verdict JSON NULL,
    INDEX idx_mock_turns_session (session_id),
    CONSTRAINT fk_mock_turns_session FOREIGN KEY (session_id) REFERENCES mock_interview_sessions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS mock_answer_evaluations (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    turn_id INT UNSIGNED NOT NULL UNIQUE,
    correctness FLOAT NULL,
    completeness FLOAT NULL,
    relevance FLOAT NULL,
    technical_depth FLOAT NULL,
    clarity FLOAT NULL,
    star_breakdown JSON NULL,
    missing_concepts JSON NULL,
    incorrect_claims JSON NULL,
    positive_points JSON NULL,
    improvement_points JSON NULL,
    better_answer_notes TEXT NULL,
    ai_model_used VARCHAR(100) NULL,
    evaluated_at DATETIME NOT NULL,
    evaluation_error VARCHAR(500) NULL,
    INDEX idx_mock_eval_turn (turn_id),
    CONSTRAINT fk_mock_eval_turn FOREIGN KEY (turn_id) REFERENCES mock_interview_turns(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS mock_interview_assessments (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_id INT UNSIGNED NOT NULL UNIQUE,
    overall_score FLOAT NULL,
    skill_matrix JSON NULL,
    weak_areas JSON NULL,
    recommendations JSON NULL,
    summary_text TEXT NULL,
    generated_at DATETIME NOT NULL,
    ai_model_used VARCHAR(100) NULL,
    INDEX idx_mock_assessment_session (session_id),
    CONSTRAINT fk_mock_assessment_session FOREIGN KEY (session_id) REFERENCES mock_interview_sessions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS mock_question_rubrics (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    question_id VARCHAR(100) NOT NULL,
    domain_id VARCHAR(100) NOT NULL,
    key_concepts JSON NULL,
    extraction_method VARCHAR(50) NOT NULL DEFAULT 'heuristic',
    model_used VARCHAR(100) NULL,
    generated_at DATETIME NOT NULL,
    INDEX idx_mock_rubrics_qid (question_id),
    CONSTRAINT uq_mock_rubric_q_domain UNIQUE (question_id, domain_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
