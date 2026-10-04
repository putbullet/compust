-- Migration 017: Behavioral Mock Interview Schema Extensions
-- Supports behavioral/HR questions, language selection, personalization,
-- deterministic delivery metrics, STAR qualitative evaluation, and minute-by-minute timeline data.

-- Sessions table extensions
ALTER TABLE mock_interview_sessions ADD COLUMN language VARCHAR(10) NOT NULL DEFAULT 'en';
ALTER TABLE mock_interview_sessions ADD COLUMN interview_type VARCHAR(50) NOT NULL DEFAULT 'behavioral';
ALTER TABLE mock_interview_sessions ADD COLUMN personalize_resume BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE mock_interview_sessions ADD COLUMN voice_id VARCHAR(100) NULL;
ALTER TABLE mock_interview_sessions ADD COLUMN avatar_mode VARCHAR(50) NOT NULL DEFAULT 'voice_avatar';

-- Turns table extensions for delivery metrics and timeline offsets
ALTER TABLE mock_interview_turns ADD COLUMN competency VARCHAR(100) NULL;
ALTER TABLE mock_interview_turns ADD COLUMN wpm FLOAT NULL;
ALTER TABLE mock_interview_turns ADD COLUMN filler_word_count INT NULL;
ALTER TABLE mock_interview_turns ADD COLUMN filler_words JSON NULL;
ALTER TABLE mock_interview_turns ADD COLUMN longest_pause_seconds FLOAT NULL;
ALTER TABLE mock_interview_turns ADD COLUMN time_to_first_word_seconds FLOAT NULL;
ALTER TABLE mock_interview_turns ADD COLUMN i_vs_we_ratio FLOAT NULL;
ALTER TABLE mock_interview_turns ADD COLUMN word_count INT NULL;
ALTER TABLE mock_interview_turns ADD COLUMN start_time_offset_seconds FLOAT NULL;
ALTER TABLE mock_interview_turns ADD COLUMN end_time_offset_seconds FLOAT NULL;

-- Evaluations table extensions for grounded STAR breakdown
ALTER TABLE mock_answer_evaluations ADD COLUMN star_situation VARCHAR(50) NULL;
ALTER TABLE mock_answer_evaluations ADD COLUMN star_task VARCHAR(50) NULL;
ALTER TABLE mock_answer_evaluations ADD COLUMN star_action VARCHAR(50) NULL;
ALTER TABLE mock_answer_evaluations ADD COLUMN star_result VARCHAR(50) NULL;
ALTER TABLE mock_answer_evaluations ADD COLUMN star_evidence JSON NULL;
ALTER TABLE mock_answer_evaluations ADD COLUMN stronger_version TEXT NULL;
ALTER TABLE mock_answer_evaluations ADD COLUMN specificity_score FLOAT NULL;
ALTER TABLE mock_answer_evaluations ADD COLUMN ownership_score FLOAT NULL;
ALTER TABLE mock_answer_evaluations ADD COLUMN measurable_outcome_score FLOAT NULL;

-- Assessments table extensions for timeline chart and structured delivery
ALTER TABLE mock_interview_assessments ADD COLUMN timeline_data JSON NULL;
ALTER TABLE mock_interview_assessments ADD COLUMN competency_scores JSON NULL;
ALTER TABLE mock_interview_assessments ADD COLUMN delivery_summary JSON NULL;
ALTER TABLE mock_interview_assessments ADD COLUMN action_plan JSON NULL;
