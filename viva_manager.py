# viva_manager.py (FIXED - proper state machine to prevent repeated TTS)
import streamlit as st
import time
import threading
import os
from datetime import datetime
from utils.audio_utils import speak, record_answer
from feedback_engine import evaluate_answer, generate_report

# Ensure session keys used by this module exist
if "records" not in st.session_state:
    st.session_state.records = []


def speak_async(text: str):
    """Run TTS in a separate thread to avoid blocking Streamlit UI."""
    def _s():
        try:
            speak(text)
        except Exception as e:
            # don't crash the app if TTS fails
            print("[TTS Error]", e)
    threading.Thread(target=_s, daemon=True).start()


def update_orb_color(color: str):
    """Send color update to the orb using component communication."""
    st.session_state.orb_color = color


def run_viva_session_stepwise():
    """
    Run exactly one viva step (one question) per Streamlit run.
    Uses a state machine to prevent repeated TTS calls and handle countdown properly.
    """
    # Initialize state items if missing
    if "q_index" not in st.session_state:
        st.session_state.q_index = 0
    if "selected" not in st.session_state:
        st.session_state.selected = []
    if "logs" not in st.session_state:
        st.session_state.logs = []
    if "records" not in st.session_state:
        st.session_state.records = []
    if "subject" not in st.session_state:
        st.session_state.subject = ""
    if "student_name" not in st.session_state:
        st.session_state.student_name = ""
    if "student_id" not in st.session_state:
        st.session_state.student_id = ""
    if "thinking_countdown" not in st.session_state:
        st.session_state.thinking_countdown = 0
    if "question_phase" not in st.session_state:
        st.session_state.question_phase = "start"  # start, speaking, thinking, recording, done
    if "phase_start_time" not in st.session_state:
        st.session_state.phase_start_time = None

    q_index = st.session_state.q_index
    questions = st.session_state.selected
    total = len(questions)

    # Safety: nothing to do if no questions selected
    if total == 0:
        st.warning("No questions selected. Please start a new session from the left panel.")
        return

    # If still questions remaining -> handle the current one
    if q_index < total:
        question, correct_answer = questions[q_index]
        phase = st.session_state.question_phase

        # === PHASE 1: START (Initial setup) ===
        if phase == "start":
            st.session_state.current_question = question
            
            # Add placeholder entry to session log
            if len(st.session_state.logs) <= q_index:
                st.session_state.logs.append({
                    "question": question,
                    "user_answer": "<i>Waiting for your response...</i>"
                })
            
            # Move to speaking phase
            st.session_state.question_phase = "speaking"
            st.session_state.orb_status = "preparing"
            update_orb_color("#00FFFF")
            
            # Speak question ONCE
            speak_async(f"Question {q_index + 1}. {question}")
            st.session_state.phase_start_time = time.time()
            
            # Wait 2 seconds then rerun to move to thinking phase
            time.sleep(2)
            st.rerun()

        # === PHASE 2: SPEAKING (Question being spoken) ===
        elif phase == "speaking":
            st.session_state.orb_status = "preparing"
            
            # Check if enough time has passed (3 seconds for speaking)
            elapsed = time.time() - st.session_state.phase_start_time
            if elapsed >= 3:
                # Move to thinking phase
                st.session_state.question_phase = "thinking"
                st.session_state.thinking_countdown = 5
                st.session_state.orb_status = "thinking"
                update_orb_color("#FFAA00")
                st.session_state.phase_start_time = time.time()
                st.rerun()
            else:
                # Still speaking, wait a bit more
                time.sleep(0.5)
                st.rerun()

        # === PHASE 3: THINKING (5-second countdown) ===
        elif phase == "thinking":
            st.session_state.orb_status = "thinking"
            update_orb_color("#FFAA00")
            
            countdown = st.session_state.thinking_countdown
            
            if countdown > 0:
                # Decrement countdown
                st.session_state.thinking_countdown = countdown - 1
                time.sleep(1)
                st.rerun()
            else:
                # Countdown done, move to recording
                st.session_state.question_phase = "recording"
                st.session_state.orb_status = "listening"
                update_orb_color("#00FF00")
                st.rerun()

        # === PHASE 4: RECORDING (8 seconds) ===
        elif phase == "recording":
            st.session_state.orb_status = "listening"
            update_orb_color("#00FF00")
            
            # Record answer
            try:
                result = record_answer(duration=10, get_volume=True)
                if isinstance(result, tuple) and len(result) == 2:
                    user_answer, avg_volume = result
                else:
                    user_answer = result if result is not None else ""
                    avg_volume = 0.0
            except Exception as e:
                print("[Record Error]", e)
                user_answer, avg_volume = "", 0.0

            # Update orb color based on voice volume
            orb_color = volume_to_color(avg_volume)
            update_orb_color(orb_color)

            # Evaluate answer
            if not user_answer or not user_answer.strip():
                score, feedback = 0, "No answer detected."
            else:
                score, feedback = evaluate_answer(user_answer, correct_answer)

            # Update log entry
            if len(st.session_state.logs) > q_index:
                st.session_state.logs[q_index]["user_answer"] = user_answer or "<i>No response</i>"
            else:
                st.session_state.logs.append({
                    "question": question,
                    "user_answer": user_answer or "<i>No response</i>"
                })

            # Save full record
            st.session_state.records.append({
                "question": question,
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "score": score,
                "feedback": feedback
            })

            # Move to next question
            st.session_state.q_index = q_index + 1
            st.session_state.question_phase = "start"  # Reset phase for next question
            st.session_state.thinking_countdown = 0
            
            # Small pause before next question
            time.sleep(1)
            st.rerun()

    else:
        # All questions done: generate final report
        records = st.session_state.get("records", [])
        try:
            report = generate_report(
                st.session_state.get("student_name", "Student"),
                st.session_state.get("student_id", "Unknown"),
                st.session_state.get("subject", ""),
                records
            )
        except Exception:
            avg_score = round(sum([r.get("score", 0) for r in records]) / len(records), 2) if records else 0.0
            report = {
                "user": st.session_state.get("student_name", "Student"),
                "student_id": st.session_state.get("student_id", "Unknown"),
                "subject": st.session_state.get("subject", ""),
                "average_score": avg_score,
                "weak_areas": [r["question"] for r in records if r.get("score", 0) < 60],
                "records": records,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        st.session_state.report = report
        st.session_state.stage = "report"
        st.session_state.current_question = None
        st.session_state.orb_status = "idle"
        st.session_state.question_phase = "start"
        update_orb_color("#00FFFF")
        
        time.sleep(0.6)
        st.rerun()


def volume_to_color(volume: float) -> str:
    """
    Map average voice volume (0..1) to a hex color for the orb.
    Low -> blue, medium -> cyan, high -> pink.
    """
    try:
        v = float(volume)
    except Exception:
        v = 0.0
    if v < 0.03:
        return "#0011FF"  # Blue
    if v < 0.06:
        return "#00FFFF"  # Cyan
    return "#FF33FF"     # Pink