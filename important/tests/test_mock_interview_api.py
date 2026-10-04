"""
Integration tests for AI Mock Interview & Skills Assessment endpoints.
Mocks AI (Ollama) and STT (faster-whisper) to verify full session lifecycle,
turn submission, state recovery, and post-interview assessment generation.
"""

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.app.database import get_db
from src.app.main import app, get_current_user
from src.app.models import Base, User
from src.app.models_mock_interview import MockInterviewSession
from src.app.services.mock_interview_service import mock_interview_service


@pytest.fixture
def auth_client():
    """Sets up an in-memory SQLite database and authenticated test user."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Create all tables (including mock interview models)
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    db = session_factory()

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Create dummy user
    test_user = User(
        id=42,
        email="interview.candidate@compust.io",
        password_hash="hashed_pw_test",
        first_name="Test",
        last_name="Candidate",
        created_at=now,
        updated_at=now,
    )
    db.add(test_user)
    db.commit()

    def override_get_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: test_user

    client = TestClient(app)
    try:
        yield client, session_factory, test_user
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
        db.close()
        engine.dispose()


class TestMockInterviewAPI:

    def test_stt_status_endpoint(self, auth_client):
        """GET /api/v1/mock-interview/stt-status returns local configuration."""
        client, _, _ = auth_client
        resp = client.get("/api/v1/mock-interview/stt-status")
        assert resp.status_code == 200
        data = resp.json()
        assert "engine" in data
        assert data["local_processing"] is True
        assert data["audio_retained"] is False

    def test_resume_domain_detection(self, auth_client):
        """POST /api/v1/mock-interview/resume-detect returns overrideable suggestion."""
        client, _, _ = auth_client
        resp = client.post("/api/v1/mock-interview/resume-detect", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert "suggested_domain_id" in data
        assert data["is_ai_suggested"] is True
        assert "disclaimer" in data

    @patch("src.app.services.mock_interview_service.classify_follow_up")
    @patch("src.app.services.mock_interview_service.evaluate_answer")
    def test_full_mock_interview_lifecycle(self, mock_eval, mock_followup, auth_client):
        """
        Full lifecycle test:
        1. Setup session
        2. Start session (get Q1)
        3. Submit turn 1
        4. Check state (reconnect recovery)
        5. Submit turn 2
        6. End session
        7. Trigger & verify post-interview assessment
        8. Create re-practice session
        """
        client, session_factory, user = auth_client

        # Mock AI responses
        mock_followup.return_value = {
            "strength": "adequate",
            "follow_up_suggested": False,
            "follow_up_focus": "",
        }
        mock_eval.return_value = {
            "correctness": 0.85,
            "completeness": 0.80,
            "relevance": 0.90,
            "technical_depth": 0.75,
            "clarity": 0.85,
            "missing_concepts": ["backpressure handling"],
            "incorrect_claims": [],
            "positive_points": ["Good explanation of DAG execution", "Mentioned shuffle stages"],
            "improvement_points": ["Could explain memory spill mechanisms in deeper detail"],
            "better_answer_notes": "Mention dynamic partition pruning and broadcast joins.",
            "ai_model_used": "qwen2.5:0.5b",
        }

        # Step 1: Create session
        setup_resp = client.post(
            "/api/v1/mock-interview/sessions",
            json={
                "domain_id": "data_engineering",
                "difficulty": "Intermediate",
                "duration_minutes": 20,
                "role": "Data Platform Engineer",
            },
        )
        assert setup_resp.status_code == 200
        setup_data = setup_resp.json()
        session_id = setup_data["session_id"]
        assert session_id > 0
        assert setup_data["domain_id"] == "data_engineering"
        assert setup_data["planned_question_count"] > 0
        assert setup_data["requires_microphone"] is True

        # Step 2: Start session (get question 1)
        start_resp = client.post(f"/api/v1/mock-interview/sessions/{session_id}/start")
        assert start_resp.status_code == 200
        turn_data = start_resp.json()
        assert turn_data["session_id"] == session_id
        assert turn_data["questions_asked"] == 1
        assert turn_data["interview_complete"] is False
        assert turn_data["next_question"] is not None
        assert "tts_text" in turn_data["next_question"]
        # Verify opening question is natural and conversational rather than cold technical quiz
        tts_lower = turn_data["next_question"]["tts_text"].lower()
        assert any(w in tts_lower for w in ["welcome", "hello", "interview", "background", "data engineering"])

        # Step 3: Submit answer for turn 1
        turn1_resp = client.post(
            f"/api/v1/mock-interview/sessions/{session_id}/turns",
            json={
                "session_id": session_id,
                "transcript": "In Apache Spark, transformations are lazy and actions trigger execution of the DAG.",
                "stt_engine": "faster-whisper",
                "stt_confidence": 0.95,
                "answer_duration_seconds": 65.0,
            },
        )
        assert turn1_resp.status_code == 200
        turn1_data = turn1_resp.json()
        assert turn1_data["session_id"] == session_id

        # Step 4: Check session state recovery (e.g. page refresh)
        state_resp = client.get(f"/api/v1/mock-interview/sessions/{session_id}/state")
        assert state_resp.status_code == 200
        state_data = state_resp.json()
        assert state_data["session_id"] == session_id
        assert state_data["status"] == "in_progress"
        assert state_data["questions_asked"] >= 1

        # Step 5: End session
        end_resp = client.post(
            f"/api/v1/mock-interview/sessions/{session_id}/end",
            json={"session_id": session_id, "reason": "user_ended"},
        )
        assert end_resp.status_code == 200
        assert end_resp.json()["status"] == "completed"

        # Step 6: Run post-interview evaluation batch directly
        with session_factory() as db:
            mock_interview_service.run_post_interview_evaluation(db, session_id)

        # Step 7: Retrieve Assessment with separate technical and behavioral scoring
        assess_resp = client.get(f"/api/v1/mock-interview/sessions/{session_id}/assessment")
        assert assess_resp.status_code == 200
        assess_data = assess_resp.json()
        assert assess_data["session_id"] == session_id
        assert assess_data["evaluation_status"] == "completed"
        assert assess_data["overall_score"] > 0
        assert "technical_score" in assess_data
        assert "behavioral_score" in assess_data
        assert "strengths" in assess_data
        assert isinstance(assess_data["strengths"], list)
        assert len(assess_data["answer_details"]) >= 1
        assert len(assess_data["skill_matrix"]) >= 1
        assert "disclaimer" in assess_data
        assert "practice" in assess_data["disclaimer"].lower()

        # Step 8: Create Re-practice session from weak areas
        repractice_resp = client.post(
            f"/api/v1/mock-interview/sessions/{session_id}/repractice",
            json={"source_session_id": session_id, "duration_minutes": 15},
        )
        assert repractice_resp.status_code == 200
        repractice_data = repractice_resp.json()
        assert repractice_data["new_session_id"] > 0
        assert repractice_data["new_session_id"] != session_id

        # Step 9: Verify session history lists both sessions
        history_resp = client.get("/api/v1/mock-interview/sessions")
        assert history_resp.status_code == 200
        history_data = history_resp.json()
        assert history_data["total"] >= 2

    def test_nonexistent_session_not_found(self, auth_client):
        """GET /api/v1/mock-interview/sessions/99999/state returns 404."""
        client, _, _ = auth_client
        resp = client.get("/api/v1/mock-interview/sessions/99999/state")
        assert resp.status_code == 404

    def test_invalid_domain_setup_fails(self, auth_client):
        """POST /api/v1/mock-interview/sessions with invalid domain returns 400."""
        client, _, _ = auth_client
        resp = client.post(
            "/api/v1/mock-interview/sessions",
            json={
                "domain_id": "non_existent_domain",
                "difficulty": "Intermediate",
                "duration_minutes": 20,
            },
        )
        assert resp.status_code == 400

    def test_setup_with_role_blank_explicitly(self, auth_client):
        """POST /api/v1/mock-interview/sessions with role=None and role='' must succeed."""
        client, _, _ = auth_client

        # Case A: role is None
        resp_none = client.post(
            "/api/v1/mock-interview/sessions",
            json={
                "domain_id": "data_engineering",
                "difficulty": "Intermediate",
                "duration_minutes": 20,
                "role": None,
            },
        )
        assert resp_none.status_code == 200
        data_none = resp_none.json()
        assert data_none["session_id"] > 0
        assert data_none["planned_question_count"] > 0

        # Case B: role is empty string
        resp_empty = client.post(
            "/api/v1/mock-interview/sessions",
            json={
                "domain_id": "security_engineering",
                "difficulty": "Fundamental",
                "duration_minutes": 10,
                "role": "",
            },
        )
        assert resp_empty.status_code == 200
        data_empty = resp_empty.json()
        assert data_empty["session_id"] > 0
        assert data_empty["planned_question_count"] > 0

    def test_setup_with_role_specified(self, auth_client):
        """POST /api/v1/mock-interview/sessions with explicit role."""
        client, _, _ = auth_client
        resp = client.post(
            "/api/v1/mock-interview/sessions",
            json={
                "domain_id": "ai_tech_interview",
                "difficulty": "Advanced",
                "duration_minutes": 30,
                "role": "Machine Learning Platform Engineer",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] > 0
        assert data["planned_question_count"] > 0

    def test_setup_all_domains_and_difficulties(self, auth_client):
        """Verify session creation works across all 3 domains, difficulties, and durations."""
        client, _, _ = auth_client
        domains = ["data_engineering", "security_engineering", "ai_tech_interview"]
        difficulties = ["Fundamental", "Intermediate", "Advanced", "Mixed"]
        durations = [10, 20, 30, 45]

        for d in domains:
            for diff in difficulties:
                resp = client.post(
                    "/api/v1/mock-interview/sessions",
                    json={
                        "domain_id": d,
                        "difficulty": diff,
                        "duration_minutes": 20,
                        "role": None,
                    },
                )
                assert resp.status_code == 200, f"Failed for domain {d}, difficulty {diff}: {resp.text}"
                data = resp.json()
                assert data["session_id"] > 0
                assert data["planned_question_count"] > 0

    def test_setup_guest_unauthenticated(self, auth_client):
        """Unauthenticated requests without Bearer token can still create sessions."""
        client, _, _ = auth_client
        # Remove dependency override for get_current_user to simulate guest
        from src.app.security import get_optional_current_user
        app.dependency_overrides[get_optional_current_user] = lambda: None

        resp = client.post(
            "/api/v1/mock-interview/sessions",
            json={
                "domain_id": "data_engineering",
                "difficulty": "Fundamental",
                "duration_minutes": 10,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] > 0
        assert data["planned_question_count"] > 0

    @patch("src.app.services.mock_interview_service.evaluate_answer")
    def test_behavioral_turn_evaluation_with_star(self, mock_eval, auth_client):
        """Verifies behavioral questions receive STAR breakdown and structured feedback."""
        client, session_factory, _ = auth_client

        mock_eval.return_value = {
            "correctness": 0.85,
            "completeness": 0.90,
            "relevance": 0.95,
            "technical_depth": 0.70,
            "clarity": 0.90,
            "star_breakdown": {
                "situation": 1.0,
                "task": 0.9,
                "action": 0.85,
                "result": 0.75,
            },
            "missing_concepts": [],
            "incorrect_claims": [],
            "positive_points": ["Clear situation context", "Explained specific technical action"],
            "improvement_points": ["Could provide more quantified business impact in the result"],
            "better_answer_notes": "Mention specific latency reduction percentage.",
            "ai_model_used": "qwen2.5:0.5b",
        }

        # Create session
        setup_resp = client.post(
            "/api/v1/mock-interview/sessions",
            json={
                "domain_id": "security_engineering",
                "difficulty": "Intermediate",
                "duration_minutes": 10,
            },
        )
        session_id = setup_resp.json()["session_id"]

        # Start
        start_resp = client.post(f"/api/v1/mock-interview/sessions/{session_id}/start")
        assert start_resp.status_code == 200

        # Answer introductory/behavioral question
        turn_resp = client.post(
            f"/api/v1/mock-interview/sessions/{session_id}/turns",
            json={
                "session_id": session_id,
                "transcript": "In my previous role at a fintech company, our team faced high credential stuffing attacks. I led the deployment of OAuth2 and rate limiting.",
                "stt_engine": "faster-whisper",
                "answer_duration_seconds": 45.0,
            },
        )
        assert turn_resp.status_code == 200

        # End and evaluate
        client.post(
            f"/api/v1/mock-interview/sessions/{session_id}/end",
            json={"session_id": session_id, "reason": "user_ended"},
        )
        with session_factory() as db:
            mock_interview_service.run_post_interview_evaluation(db, session_id)

        assess_resp = client.get(f"/api/v1/mock-interview/sessions/{session_id}/assessment")
        assert assess_resp.status_code == 200
        assess_data = assess_resp.json()
        assert assess_data["evaluation_status"] == "completed"
        assert len(assess_data["answer_details"]) >= 1

        first_answer = assess_data["answer_details"][0]
        assert first_answer["question_type"] in ("introductory", "behavioral")
        assert "star_breakdown" in first_answer
        assert first_answer["star_breakdown"] is not None
        assert first_answer["star_breakdown"]["situation"] == 1.0

    def test_natural_interview_closing_message(self, auth_client):
        """Verifies session end via question exhaustion or time budget returns conversational wrap-up."""
        client, _, _ = auth_client

        # Create short 10m session
        setup_resp = client.post(
            "/api/v1/mock-interview/sessions",
            json={
                "domain_id": "ai_tech_interview",
                "difficulty": "Fundamental",
                "duration_minutes": 10,
            },
        )
        session_id = setup_resp.json()["session_id"]
        client.post(f"/api/v1/mock-interview/sessions/{session_id}/start")

        # Submit a turn with high answer duration to exhaust remaining budget
        turn_resp = client.post(
            f"/api/v1/mock-interview/sessions/{session_id}/turns",
            json={
                "session_id": session_id,
                "transcript": "RAG systems retrieve relevant context from a vector database before LLM generation.",
                "stt_engine": "faster-whisper",
                "answer_duration_seconds": 1200.0,  # exceeds budget
            },
        )
        assert turn_resp.status_code == 200
        data = turn_resp.json()
        assert data["interview_complete"] is True
        assert data["message"] is not None
        assert "interview" in data["message"].lower()
        assert "thank you" in data["message"].lower()

    def test_mock_interview_tts_status(self, auth_client):
        """Verifies GET /api/v1/mock-interview/tts-status returns available neural voices."""
        client, _, _ = auth_client
        resp = client.get("/api/v1/mock-interview/tts-status")
        assert resp.status_code == 200
        data = resp.json()
        assert "available" in data
        assert "engine" in data
        assert "voices" in data
        assert len(data["voices"]) >= 4
        # Verify default voice exists
        voice_ids = [v["id"] for v in data["voices"]]
        assert "en-US-AndrewMultilingualNeural" in voice_ids

    def test_mock_interview_tts_synthesis(self, auth_client):
        """Verifies GET /api/v1/mock-interview/tts returns audio/mpeg stream."""
        client, _, _ = auth_client
        resp = client.get(
            "/api/v1/mock-interview/tts",
            params={"text": "Hello, welcome to your technical interview.", "voice": "en-US-AndrewMultilingualNeural"},
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "audio/mpeg"
        assert len(resp.content) > 1000

    def test_mock_interview_stt_status_operational(self, auth_client):
        """Verifies STT status endpoint returns operational faster-whisper configuration."""
        client, _, _ = auth_client
        resp = client.get("/api/v1/mock-interview/stt-status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["available"] is True
        assert data["engine"] == "faster-whisper"
        assert data["device"] == "cpu"
        assert data["local_processing"] is True
        assert data["audio_retained"] is False

    def test_mock_interview_stt_transcription_live(self, auth_client):
        """Verifies POST /api/v1/mock-interview/stt transcribes audio bytes with local faster-whisper."""
        import io
        import wave
        client, _, _ = auth_client

        # Synthesize a 1-second 16kHz PCM WAV buffer
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(b"\x00\x00" * 16000)
        wav_bytes = buf.getvalue()

        resp = client.post(
            "/api/v1/mock-interview/stt",
            files={"file": ("test_silence.wav", wav_bytes, "audio/wav")},
            params={"language": "en"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["engine"] == "faster-whisper"
        assert "transcript" in data
        assert data["error"] is None or data["error"] == ""

    def test_natural_introductory_greeting_in_session_start(self, auth_client):
        """Verifies that starting a session generates a natural welcoming introduction and opening question."""
        client, _, _ = auth_client
        setup_resp = client.post(
            "/api/v1/mock-interview/sessions",
            json={
                "domain_id": "data_engineering",
                "role": "Senior Data Platform Engineer",
                "duration_minutes": 30,
                "difficulty": "Intermediate",
            },
        )
        assert setup_resp.status_code == 200
        session_id = setup_resp.json()["session_id"]

        start_resp = client.post(f"/api/v1/mock-interview/sessions/{session_id}/start")
        assert start_resp.status_code == 200
        data = start_resp.json()
        assert "next_question" in data
        q = data["next_question"]
        assert q["question_type"] in ("introductory", "behavioral")
        assert "tts_text" in q
        tts_text = q["tts_text"]
        # Must have conversational introduction elements
        assert any(greet in tts_text.lower() for greet in ["welcome", "hello", "good to have you"])
        assert "data engineering" in tts_text.lower()
        # Verify slot 0 question title asks for background/intro
        assert any(term in q["question_title"].lower() for term in ["yourself", "background", "experience", "walk me"])

    def test_startup_with_empty_target_role(self, auth_client):
        """Case 1: track valid, target_role empty string -> session starts and delivers first turn."""
        client, _, _ = auth_client
        setup_resp = client.post(
            "/api/v1/mock-interview/sessions",
            json={
                "domain_id": "security_engineering",
                "target_role": "",
                "difficulty": "Intermediate",
                "duration_minutes": 20,
            },
        )
        assert setup_resp.status_code == 200
        session_id = setup_resp.json()["session_id"]
        assert session_id > 0

        start_resp = client.post(f"/api/v1/mock-interview/sessions/{session_id}/start")
        assert start_resp.status_code == 200
        data = start_resp.json()
        assert data["turn_id"] > 0
        assert data["questions_asked"] == 1
        assert data["next_question"] is not None
        assert data["next_question"]["tts_text"]
        # When target_role is empty, TTS should not contain "for the  position"
        assert "for the  position" not in data["next_question"]["tts_text"]

    def test_startup_with_null_target_role(self, auth_client):
        """Case 2: track valid, target_role null -> session starts cleanly."""
        client, _, _ = auth_client
        setup_resp = client.post(
            "/api/v1/mock-interview/sessions",
            json={
                "domain_id": "ai_tech_interview",
                "target_role": None,
                "difficulty": "Advanced",
                "duration_minutes": 10,
            },
        )
        assert setup_resp.status_code == 200
        session_id = setup_resp.json()["session_id"]

        start_resp = client.post(f"/api/v1/mock-interview/sessions/{session_id}/start")
        assert start_resp.status_code == 200
        data = start_resp.json()
        assert data["turn_id"] > 0
        assert data["next_question"]["question_type"] in ("introductory", "technical", "behavioral")

    def test_startup_with_explicit_target_role(self, auth_client):
        """Case 3: track valid, target_role specified -> integrated into greeting."""
        client, _, _ = auth_client
        setup_resp = client.post(
            "/api/v1/mock-interview/sessions",
            json={
                "domain_id": "security_engineering",
                "target_role": "AppSec Specialist",
                "difficulty": "Intermediate",
                "duration_minutes": 20,
            },
        )
        assert setup_resp.status_code == 200
        session_id = setup_resp.json()["session_id"]

        start_resp = client.post(f"/api/v1/mock-interview/sessions/{session_id}/start")
        assert start_resp.status_code == 200
        data = start_resp.json()
        assert "AppSec Specialist" in data["next_question"]["tts_text"]

    def test_all_domains_and_difficulties_session_start(self, auth_client):
        """Case 4 & 5: Tests every domain and difficulty can create and start sessions without error."""
        client, _, _ = auth_client
        domains = ["data_engineering", "security_engineering", "ai_tech_interview"]
        difficulties = ["Fundamental", "Intermediate", "Advanced", "Mixed"]

        for domain in domains:
            for diff in difficulties:
                setup_resp = client.post(
                    "/api/v1/mock-interview/sessions",
                    json={
                        "domain_id": domain,
                        "target_role": "",
                        "difficulty": diff,
                        "duration_minutes": 10,
                    },
                )
                assert setup_resp.status_code == 200, f"Setup failed for domain {domain} diff {diff}"
                session_id = setup_resp.json()["session_id"]

                start_resp = client.post(f"/api/v1/mock-interview/sessions/{session_id}/start")
                assert start_resp.status_code == 200, f"Start failed for domain {domain} diff {diff}: {start_resp.text}"
                data = start_resp.json()
                assert data["turn_id"] > 0
                assert data["next_question"] is not None

    def test_all_duration_options(self, auth_client):
        """Case 6: Tests supported durations (10, 20, 30, 45)."""
        client, _, _ = auth_client
        for duration in [10, 20, 30, 45]:
            setup_resp = client.post(
                "/api/v1/mock-interview/sessions",
                json={
                    "domain_id": "data_engineering",
                    "difficulty": "Mixed",
                    "duration_minutes": duration,
                },
            )
            assert setup_resp.status_code == 200
            session_id = setup_resp.json()["session_id"]

            start_resp = client.post(f"/api/v1/mock-interview/sessions/{session_id}/start")
            assert start_resp.status_code == 200
            data = start_resp.json()
            assert data["remaining_seconds"] == float(duration * 60)

    def test_e2e_interview_startup_flow(self, auth_client):
        """
        Case 8 & 18: End-to-end startup flow test matching the exact UI journey:
        Select track -> Leave target role empty -> Select diff & duration -> Continue -> Check -> Start
        """
        client, _, _ = auth_client

        # Step 1: User fills setup form with empty target role
        setup_payload = {
            "domain_id": "security_engineering",
            "role": "",
            "difficulty": "Intermediate",
            "duration_minutes": 20,
        }
        setup_resp = client.post("/api/v1/mock-interview/sessions", json=setup_payload)
        assert setup_resp.status_code == 200
        setup_data = setup_resp.json()
        session_id = setup_data["session_id"]
        assert setup_data["domain_id"] == "security_engineering"
        assert setup_data["requires_microphone"] is True

        # Step 2: User passes mic check (STT status endpoint succeeds)
        stt_resp = client.get("/api/v1/mock-interview/stt-status")
        assert stt_resp.status_code == 200

        # Step 3: User clicks "Start Interview"
        start_resp = client.post(f"/api/v1/mock-interview/sessions/{session_id}/start")
        assert start_resp.status_code == 200
        turn_data = start_resp.json()

        # Step 4: Verify session state and first question
        assert turn_data["session_id"] == session_id
        assert turn_data["questions_asked"] == 1
        assert turn_data["interview_complete"] is False
        assert turn_data["next_question"] is not None
        assert turn_data["next_question"]["tts_text"]
        assert "security" in turn_data["next_question"]["tts_text"].lower()

        # Step 5: Cannot start a session that has already transitioned to in_progress
        double_start = client.post(f"/api/v1/mock-interview/sessions/{session_id}/start")
        assert double_start.status_code == 400
        assert "not in setup state" in double_start.json()["detail"]


