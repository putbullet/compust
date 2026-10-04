-- Migration 016: Add canonical_transcript and parent_question_id to mock_interview_turns
-- Enables storage of normalized transcripts alongside raw ASR output and links follow-up questions.

ALTER TABLE mock_interview_turns ADD COLUMN canonical_transcript TEXT NULL;
ALTER TABLE mock_interview_turns ADD COLUMN parent_question_id VARCHAR(100) NULL;
