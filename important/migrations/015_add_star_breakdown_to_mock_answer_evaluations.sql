-- Migration 015: Add star_breakdown to mock_answer_evaluations
-- Enables structured STAR evaluation storage for behavioral interview questions.

ALTER TABLE mock_answer_evaluations ADD COLUMN star_breakdown JSON NULL;
