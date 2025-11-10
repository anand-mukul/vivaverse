# viva_manager.py (updated for EchoViva 2.0 — stepwise, non-blocking, no orb injection)
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


def run_viva_session_stepwise():
    """
    Run exactly one viva step (one question) per Streamlit run.
    Uses st.rerun() to proceed to the next question so the UI (orb + logs)
    remain responsive and the orb is rendered only by app.py.
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

        # Set current question visible only in the right panel
        st.session_state.current_question = question
        # Add placeholder entry to session log immediately (for real-time display)
        if len(st.session_state.logs) <= q_index:
            st.session_state.logs.append({
                "question": question,
                "user_answer": "<i>Waiting for your response...</i>"
            })

        # Update orb status for UI (app.py reads orb_status to show status message)
        st.session_state.orb_status = "thinking"
        # Speak question asynchronously
        speak_async(f"Question {q_index + 1}. {question}")

        # Give 5 seconds thinking time
        time.sleep(5)

        # Update orb status to listening
        st.session_state.orb_status = "listening"

        # Attempt to record answer (8s max) and get volume for orb color
        try:
            result = record_answer(duration=8, get_volume=True)
            # record_answer should return (text, avg_volume)
            if isinstance(result, tuple) and len(result) == 2:
                user_answer, avg_volume = result
            else:
                # fallback if record_answer returns only text
                user_answer = result if result is not None else ""
                avg_volume = 0.0
        except Exception as e:
            # In case of errors with microphone or API
            print("[Record Error]", e)
            user_answer, avg_volume = "", 0.0

        # Send orb color update event (app's orb listens for updateOrbColor)
        orb_color = volume_to_color(avg_volume)
        # Use a script injection so the orb (Three.js) can react
        st.markdown(
            f"<script>window.dispatchEvent(new CustomEvent('updateOrbColor', {{detail: '{orb_color}'}}));</script>",
            unsafe_allow_html=True,
        )

        # Evaluate (silently) — do not display score in the right log until report stage
        if not user_answer or not user_answer.strip():
            score, feedback = 0, "No answer detected."
        else:
            score, feedback = evaluate_answer(user_answer, correct_answer)

        # Save entry in logs (right panel shows logs live)
        # Update the log entry for this question
        if len(st.session_state.logs) > q_index:
            st.session_state.logs[q_index]["user_answer"] = user_answer or "<i>No response</i>"
        else:
            st.session_state.logs.append({
                "question": question,
                "user_answer": user_answer or "<i>No response</i>"
            })

        # Save full record (for report & saving)
        st.session_state.records.append({
            "question": question,
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "score": score,
            "feedback": feedback
        })

        # Move to next question
        st.session_state.q_index = q_index + 1

        # Small UX pause
        time.sleep(0.8)

        # Rerun the app to process the next question step
        st.rerun()

    else:
        # All questions done: generate final report and switch to report stage
        records = st.session_state.get("records", [])
        # Use the generate_report function to save the report to disk and get structured output
        try:
            report = generate_report(
                st.session_state.get("student_name", "Student"),
                st.session_state.get("student_id", "Unknown"),
                st.session_state.get("subject", ""),
                records
            )
        except Exception:
            # If saving via generate_report fails, build a fallback report object
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

        # Clear current question and update orb status
        st.session_state.current_question = None
        st.session_state.orb_status = "idle"

        # Short pause and rerun so app shows the report immediately
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
