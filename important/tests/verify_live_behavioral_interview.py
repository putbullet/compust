"""
Live verification script for the AI Behavioral & HR Mock Interview Rebuild.
Uses Python standard library (urllib.request, json, time) to run against http://127.0.0.1:8000.
"""

import json
import time
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8000/api/v1/mock-interview"

def make_req(endpoint: str, method: str = "GET", data: dict | None = None):
    url = f"{BASE_URL}{endpoint}"
    encoded_data = json.dumps(data).encode("utf-8") if data is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    req = urllib.request.Request(url, data=encoded_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            status_code = resp.getcode()
            body = resp.read().decode("utf-8")
            parsed = json.loads(body) if body else {}
            return status_code, parsed
    except urllib.error.HTTPError as err:
        err_body = err.read().decode("utf-8")
        try:
            parsed = json.loads(err_body)
        except Exception:
            parsed = {"detail": err_body}
        return err.code, parsed

def main():
    print("=== LIVE VERIFICATION: AI Behavioral & HR Mock Interview ===")
    
    # 1. STT Status
    stt_code, stt_data = make_req("/stt-status")
    print(f"STT Status Code: {stt_code}")
    assert stt_code == 200, f"STT failed: {stt_data}"
    print(f"STT Engine: {stt_data.get('engine')} (Device: {stt_data.get('device')}, Local: {stt_data.get('local_processing')})")
    
    # 2. TTS Status
    tts_code, tts_data = make_req("/tts-status")
    print(f"TTS Status Code: {tts_code}")
    assert tts_code == 200, f"TTS failed: {tts_data}"
    print(f"TTS Engine: {tts_data.get('engine')} (Default voice: {tts_data.get('default_voice')})")
    print(f"Available voices: {len(tts_data.get('voices', []))}")
    
    # 3. Create Session (Behavioral, target_role specified, 10 min)
    setup_payload = {
        "domain_id": "behavioral",
        "target_role": "Staff Engineering Manager",
        "duration_minutes": 10,
        "difficulty": "Intermediate",
        "personalize_resume": False,
        "language": "en"
    }
    setup_code, session_data = make_req("/sessions", method="POST", data=setup_payload)
    print(f"Create Session Code: {setup_code}")
    assert setup_code == 200, f"Create session failed: {session_data}"
    session_id = session_data["session_id"]
    print(f"Session Created: ID={session_id}, Domain={session_data.get('domain_id')}, Duration={session_data.get('duration_minutes')}m")
    
    # 4. Start Session
    start_code, start_data = make_req(f"/sessions/{session_id}/start", method="POST")
    print(f"Start Session Code: {start_code}")
    assert start_code == 200, f"Start failed: {start_data}"
    q1 = start_data["next_question"]
    print(f"Question 1 (Turn {start_data['turn_id']}): {q1['question_title']}")
    print(f"Greeting / TTS Prompt: {q1['tts_text'][:120]}...")
    assert "behavioral" in q1["question_type"] or "introductory" in q1["question_type"]
    
    # 5. Submit Answer 1 (STAR formatted answer to opening/intro)
    turn1_payload = {
        "session_id": session_id,
        "transcript": "In my previous role as Engineering Lead at TechCorp, our deployment velocity had slowed by 50% due to manual release verification. As the lead, my responsibility was to modernize our release workflow while maintaining zero downtime. I designed and implemented an automated CI/CD pipeline using GitHub Actions with canary deployments and automated smoke tests. As a result, our release cycle dropped from two weeks to under two hours, and our team eliminated 95% of deployment-related incidents over the next two quarters.",
        "stt_engine": "faster-whisper",
        "answer_duration_seconds": 65.0,
        "audio_metrics": {
            "filler_words_count": 2,
            "longest_pause_seconds": 1.4,
            "words_per_minute": 132.0,
            "time_to_first_word": 0.8
        }
    }
    turn1_code, turn1_data = make_req(f"/sessions/{session_id}/turns", method="POST", data=turn1_payload)
    print(f"Turn 1 Submit Code: {turn1_code}")
    assert turn1_code == 200, f"Turn 1 failed: {turn1_data}"
    q2 = turn1_data.get("next_question")
    if q2:
        print(f"Question 2 (Turn {turn1_data['turn_id']}): {q2['question_title']}")
        print(f"Interviewer Ack / TTS: {q2.get('tts_text', '')[:100]}...")
        
        # 6. Submit Answer 2 (Conflict/Collaboration STAR answer)
        turn2_payload = {
            "session_id": session_id,
            "transcript": "During a major cloud migration, our infrastructure engineer and product designer disagreed on whether to prioritize latency SLAs or rich client-side animations. My role as project coordinator was to align both perspectives without missing our Q3 deliverable. I organized a data-driven workshop where we benchmarked user drop-off against load times, establishing clear performance budgets that allowed 80% of proposed animations within strict 200ms latency limits. Consequently, both engineering and design signed off on the compromise, and we launched on schedule with 99.9% uptime.",
            "stt_engine": "faster-whisper",
            "answer_duration_seconds": 72.0,
            "audio_metrics": {
                "filler_words_count": 1,
                "longest_pause_seconds": 1.8,
                "words_per_minute": 128.0,
                "time_to_first_word": 1.1
            }
        }
        turn2_code, turn2_data = make_req(f"/sessions/{session_id}/turns", method="POST", data=turn2_payload)
        print(f"Turn 2 Submit Code: {turn2_code}")
        assert turn2_code == 200
    
    # 7. End Session
    end_code, end_data = make_req(f"/sessions/{session_id}/end", method="POST", data={"session_id": session_id, "reason": "user_ended"})
    print(f"End Session Code: {end_code}")
    assert end_code == 200
    print(f"Session Ended. Status: {end_data.get('status')}")
    
    # 8. Post-Interview Assessment - Poll until complete
    print("Fetching Post-Interview Assessment (polling background evaluation)...")
    report = {}
    for poll_idx in range(50):
        time.sleep(1.5)
        assess_code, report = make_req(f"/sessions/{session_id}/assessment")
        assert assess_code == 200
        status = report.get("evaluation_status")
        print(f"  Poll {poll_idx + 1}: evaluation_status = {status}")
        if status in ("completed", "failed"):
            break
    
    print("\n--- ASSESSMENT REPORT DETAILS ---")
    print(f"Evaluation Status: {report.get('evaluation_status')}")
    print(f"Overall Score: {report.get('overall_score')}/100 (Behavioral: {report.get('behavioral_score')}/100)")
    print(f"Summary Text: {report.get('summary_text')}")
    print(f"Headline Strengths: {json.dumps(report.get('headline_strengths', []), indent=2)}")
    print(f"Headline Improvements: {json.dumps(report.get('headline_improvements', []), indent=2)}")
    
    # Check Timeline Data
    timeline = report.get("timeline_data", [])
    print(f"\nTimeline Segments Count: {len(timeline)}")
    for i, seg in enumerate(timeline):
        print(f"  Segment {i+1}: min {seg.get('start_minute')}-{seg.get('end_minute')} | Quality={seg.get('quality_score')} ({seg.get('quality_band')}) | Title='{seg.get('question_title')}' | Verdict='{seg.get('verdict_line')}'")
    
    # Check STAR Breakdown on Turn 1 & 2
    answer_details = report.get("answer_details", [])
    print(f"\nAnswer Details Count: {len(answer_details)}")
    for i, ans in enumerate(answer_details):
        print(f"  Answer {i+1}: {ans.get('question_title')}")
        star = ans.get("star_breakdown") or {}
        print(f"    STAR Breakdown: S={star.get('situation')}, T={star.get('task')}, A={star.get('action')}, R={star.get('result')}")
        pos_pts = ans.get("positive_points") or []
        imp_pts = ans.get("improvement_points") or []
        print(f"    Positive points: {pos_pts[:2]}")
        print(f"    Improvement points: {imp_pts[:2]}")
        stronger = ans.get("stronger_version") or ans.get("better_answer_notes") or ""
        print(f"    Stronger version preview: {stronger[:100]}...")
    
    # Check Skill Matrix
    skill_matrix = report.get("skill_matrix", [])
    print(f"\nCompetencies / Skill Matrix Count: {len(skill_matrix)}")
    for sm in skill_matrix[:4]:
        print(f"  - {sm.get('category_name')}: Rating={sm.get('rating')} (Score={sm.get('score')}) | Basis='{sm.get('basis')}'")
    
    # Check Action Plan
    action_plan = report.get("action_plan", [])
    print(f"\nAction Plan Steps: {len(action_plan)}")
    for ap in action_plan:
        print(f"  - [{ap.get('priority', 'medium').upper()}] {ap.get('title')}: {ap.get('description')} (Prep Link: {ap.get('prep_link')})")
    
    # Check Disclaimer
    print(f"\nDisclaimer: {report.get('disclaimer')}")
    
    # 9. Verify Session Deletion
    print("\nTesting Session Deletion...")
    del_code, del_data = make_req(f"/sessions/{session_id}", method="DELETE")
    print(f"Delete Session Code: {del_code}")
    assert del_code == 200
    assert del_data.get("deleted") is True
    
    # Verify session is gone
    list_code, list_data = make_req("/sessions")
    ids = [s["session_id"] for s in list_data.get("sessions", [])]
    assert session_id not in ids, f"Session {session_id} was not deleted from session list!"
    print(f"Session {session_id} successfully deleted and purged from session history.")
    
    print("\n=== ALL LIVE VERIFICATION CHECKS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    main()
