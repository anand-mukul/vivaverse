# app.py (updated - EchoViva 2.0 with color updates & improved UX)
import streamlit as st
import json
import random
import os
from datetime import datetime
from viva_manager import run_viva_session_stepwise
import streamlit.components.v1 as components

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="EchoViva 2.0 | AI Viva Assistant", page_icon="🎙️", layout="wide")

# ---------------- CUSTOM CSS ----------------
st.markdown(
    """
    <style>
    body {
        background-color: #030b16;
        color: #e6eef6;
        font-family: 'Poppins', sans-serif;
    }
    .main-header {
        text-align: center;
        color: #00FFFF;
        font-size: 36px;
        font-weight: 700;
        text-shadow: 0 0 18px rgba(0,255,255,0.12);
        margin-bottom: 6px;
    }
    .sub-header {
        text-align: center;
        color: #9aa0a6;
        margin-bottom: 18px;
    }
    .left-panel, .center-panel, .right-panel {
        background: rgba(255,255,255,0.03);
        border-radius: 12px;
        padding: 18px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.6);
    }
    .left-panel { min-height: 78vh; }
    .center-panel { min-height: 78vh; }
    .right-panel { min-height: 78vh; overflow-y:auto; }
    .control-label { color: #cfeff4; font-weight: 600; }
    .result-card { background: rgba(0,255,255,0.06); padding: 18px; border-radius: 12px; }
    .question-log { border-bottom: 1px solid rgba(255,255,255,0.03); padding: 10px 0; }
    .status-note { 
        text-align: center; 
        color: #9aa0a6; 
        margin-top: 8px;
        font-size: 16px;
        line-height: 1.6;
    }
    .status-icon {
        font-size: 24px;
        display: block;
        margin-bottom: 8px;
    }
    .countdown {
        font-size: 48px;
        font-weight: bold;
        color: #FFAA00;
        text-align: center;
        margin: 20px 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------- SESSION STATE INIT ----------------
if "stage" not in st.session_state:
    st.session_state.stage = "setup"
if "selected" not in st.session_state:
    st.session_state.selected = []
if "logs" not in st.session_state:
    st.session_state.logs = []
if "report" not in st.session_state:
    st.session_state.report = None
if "q_index" not in st.session_state:
    st.session_state.q_index = 0
if "student_name" not in st.session_state:
    st.session_state.student_name = ""
if "student_id" not in st.session_state:
    st.session_state.student_id = ""
if "current_question" not in st.session_state:
    st.session_state.current_question = None
if "orb_status" not in st.session_state:
    st.session_state.orb_status = "idle"
if "orb_color" not in st.session_state:
    st.session_state.orb_color = "#00FFFF"
if "thinking_countdown" not in st.session_state:
    st.session_state.thinking_countdown = 0

# ---------------- TITLE ----------------
# st.markdown("<div class='main-header'>EchoViva 2.0</div>", unsafe_allow_html=True)
# st.markdown("<div class='sub-header'>AI-Powered Viva Intelligence System — voice-first & proctor-ready</div>", unsafe_allow_html=True)

# ---------------- LAYOUT ----------------
col_left, col_center, col_right = st.columns([1, 2, 1])

# ---------------- LEFT: VIVA SETUP ----------------
with col_left:
    st.markdown("### 🎓 Viva Setup", unsafe_allow_html=True)

    # Student details
    st.session_state.student_name = st.text_input("👤 Student Name", value=st.session_state.student_name)
    st.session_state.student_id = st.text_input("🆔 Student ID", value=st.session_state.student_id)

    # Subjects mapping to JSON files
    subjects = {
        "Operating System": "os.json",
        "Database Management": "dbms.json",
        "Computer Networks": "cn.json",
        "Data Structures": "dsa.json",
    }
    subject_choice = st.selectbox("📘 Choose Subject", list(subjects.keys()))
    num_questions = st.slider("🔢 Number of Questions", 1, 10, 5)

    # Feature toggles
    enable_camera = st.checkbox("📷 Enable Camera Monitoring (Disabled - Future)", value=False)
    enable_anti_cheat = st.checkbox("🛡️ Enable Anti-Cheat (Tab Restriction)", value=False)

    # Inject anti-cheat JS if enabled
    if enable_anti_cheat:
        js_path = os.path.join("utils", "security.js")
        if os.path.exists(js_path):
            try:
                with open(js_path, "r", encoding="utf-8") as f_js:
                    js_code = f_js.read()
                components.html(f"<script>{js_code}</script>", height=0)
            except Exception as e:
                st.error("Could not load anti-cheat script: " + str(e))
        else:
            st.warning("Anti-cheat script not found (utils/security.js)")

    # Start / Reset controls
    start_pressed = st.button("🚀 Start Viva", key="start_viva_btn")

    if start_pressed:
        if not st.session_state.student_name.strip() or not st.session_state.student_id.strip():
            st.error("Please enter both Student Name and Student ID before starting the viva.")
        else:
            filename = os.path.join("questions", subjects[subject_choice])
            if not os.path.exists(filename):
                st.error(f"Question file not found: {filename}")
            else:
                with open(filename, "r", encoding="utf-8") as f:
                    try:
                        q_json = json.load(f)
                    except Exception as e:
                        st.error("Failed to parse question JSON: " + str(e))
                        q_json = {}

                qa_pairs = list(q_json.items())
                selected = random.sample(qa_pairs, min(num_questions, len(qa_pairs)))

                st.session_state.selected = selected
                st.session_state.subject = subject_choice
                st.session_state.logs = []
                st.session_state.report = None
                st.session_state.q_index = 0
                st.session_state.stage = "viva"
                st.session_state.current_question = None
                st.session_state.orb_status = "idle"
                st.session_state.orb_color = "#00FFFF"

                st.rerun()

    st.markdown("---")
    st.markdown(
        """
        **How it works:**  
        1. Enter name & ID, choose subject and number of questions.  
        2. Click **Start Viva**. Questions will be asked one by one.  
        3. You have 5 seconds to think, then 8 seconds to answer.  
        4. Report is generated automatically at the end.
        """
    )

# ---------------- CENTER: ORB / VIVA / RESULT ----------------
with col_center:
    # Always show the 3D orb HTML with color updates
    if st.session_state.stage in ["setup", "viva"]:
        orb_html_path = os.path.join("static", "three_orb.html")
        if os.path.exists(orb_html_path):
            try:
                with open(orb_html_path, "r", encoding="utf-8") as f_orb:
                    orb_html = f_orb.read()
                
                # Inject color update script
                color_update_script = f"""
                <script>
                setTimeout(() => {{
                    window.dispatchEvent(new CustomEvent('updateOrbColor', {{
                        detail: '{st.session_state.orb_color}'
                    }}));
                }}, 100);
                </script>
                """
                
                components.html(orb_html + color_update_script, height=440)
            except Exception as e:
                st.error("Failed to load 3D orb: " + str(e))
        else:
            st.info("3D orb file not found (static/three_orb.html)")

    # Stage-specific UI
    if st.session_state.stage == "setup":
        st.markdown("### 🌀 Ready to Start")
        st.markdown(
            "<p class='status-note'>"
            "<span class='status-icon'>✨</span>"
            "The interactive 3D orb will guide you through the viva.<br>"
            "Click <b>Start Viva</b> when ready."
            "</p>", 
            unsafe_allow_html=True
        )

    elif st.session_state.stage == "viva":
        st.markdown("### 🎤 Viva In Progress")
        
        status = st.session_state.orb_status
        
        if status == "preparing":
            st.markdown(
                "<p class='status-note'>"
                "<span class='status-icon'>🔊</span>"
                "<b>Preparing question...</b><br>"
                "Listen carefully to the question being asked."
                "</p>", 
                unsafe_allow_html=True
            )
        
        elif status == "thinking":
            countdown = st.session_state.thinking_countdown
            if countdown > 0:
                st.markdown(f"<div class='countdown'>{countdown}</div>", unsafe_allow_html=True)
                st.markdown(
                    "<p class='status-note'>"
                    "<span class='status-icon'>💭</span>"
                    "<b>Think about your answer...</b><br>"
                    "Recording will start automatically."
                    "</p>", 
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    "<p class='status-note'>"
                    "<span class='status-icon'>💭</span>"
                    "<b>Thinking time...</b>"
                    "</p>", 
                    unsafe_allow_html=True
                )
        
        elif status == "listening":
            st.markdown(
                "<p class='status-note'>"
                "<span class='status-icon'>🎤</span>"
                "<b>Recording now - Speak your answer!</b><br>"
                "You have up to 8 seconds to respond."
                "</p>", 
                unsafe_allow_html=True
            )
        
        else:
            st.markdown(
                "<p class='status-note'>"
                "<span class='status-icon'>⏳</span>"
                "Processing..."
                "</p>", 
                unsafe_allow_html=True
            )

        # Run one step
        try:
            run_viva_session_stepwise()
        except Exception as e:
            st.error("Error while running viva step: " + str(e))

    elif st.session_state.stage == "report":
        report = st.session_state.report
        if report:
            st.markdown("<h3 style='color:#00FFFF;'>📊 Viva Report Card</h3>", unsafe_allow_html=True)
            st.markdown(f"**Student:** {report.get('user', '')}  |  **ID:** {report.get('student_id', '')}  |  **Subject:** {report.get('subject', '')}")
            st.markdown(f"**Average Score:** `{report.get('average_score', 0)}%`")

            st.markdown("<div class='result-card'>", unsafe_allow_html=True)
            for rec in report.get("records", []):
                st.markdown(
                    f"""
                    <div style='padding:8px; margin-bottom:8px; border-radius:8px; background:rgba(255,255,255,0.02)'>
                      <b>Q:</b> {rec.get('question','')}<br>
                      <b>Your Answer:</b> {rec.get('user_answer','')}<br>
                      <b>Score:</b> {rec.get('score',0)}%<br>
                      <b>Feedback:</b> {rec.get('feedback','')}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

            st.download_button(
                label="💾 Download Report (JSON)",
                data=json.dumps(report, indent=4),
                file_name=f"EchoViva_Report_{report.get('user','')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
            )

            if st.button("🔁 Start New Session"):
                st.session_state.stage = "setup"
                st.session_state.selected = []
                st.session_state.logs = []
                st.session_state.report = None
                st.session_state.q_index = 0
                st.session_state.current_question = None
                st.session_state.orb_status = "idle"
                st.session_state.orb_color = "#00FFFF"
                st.rerun()
        else:
            st.info("Report not available yet.")

# ---------------- RIGHT: SESSION LOG ----------------
with col_right:
    st.markdown("### 🧾 Session Log")
    
    if st.session_state.stage == "viva" and st.session_state.current_question:
        st.markdown(
            f"**Current Question:**<br>"
            f"<div style='padding:10px; background:rgba(0,255,255,0.1); border-radius:6px; border-left:3px solid #00FFFF'>"
            f"{st.session_state.current_question}"
            f"</div>", 
            unsafe_allow_html=True
        )
        st.markdown("---")

    logs = st.session_state.get("logs", [])
    if not logs:
        if st.session_state.stage == "viva":
            st.info("Your answers will appear here as you respond to each question.")
        else:
            st.info("Questions and answers will appear here during the viva.")
    else:
        for idx, entry in enumerate(logs, start=1):
            user_ans_display = entry.get("user_answer", "") or "<i>No response</i>"
            score_html = ""
            if st.session_state.stage == "report" and entry.get("score") is not None:
                score_html = f"<br><b>Score:</b> {entry.get('score')}%"

            st.markdown(
                f"""
                <div class='question-log'>
                  <b>{idx}.</b> {entry.get('question','')}<br>
                  <b>Your Answer:</b> {user_ans_display}
                  {score_html}
                </div>
                """,
                unsafe_allow_html=True,
            )

# ---------------- FOOTER ----------------
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("<div style='text-align:center; color:gray;'>© 2025 EchoViva — Built by Mukul Anand</div>", unsafe_allow_html=True)