# feedback_engine.py
"""
Feedback & report generation for EchoViva 2.0

- evaluate_answer(user_answer, correct_answer) -> (score, feedback)
- generate_report(user, student_id, subject, records) -> report dict and persists to reports/user_reports.json
"""

import os
import json
from datetime import datetime
import textdistance
from utils.text_utils import clean_text, keyword_similarity, get_improvement_tips

REPORTS_FILE = os.path.join("reports", "user_reports.json")


def evaluate_answer(user_answer: str, correct_answer: str):
    """
    Evaluate the user's answer against the correct answer.
    Returns (score_percent (float), feedback_text (str)).
    """
    try:
        u = clean_text(user_answer or "")
        c = clean_text(correct_answer or "")
    except Exception:
        u = (user_answer or "").lower()
        c = (correct_answer or "").lower()

    # Semantic similarity (cosine on character n-grams via textdistance)
    try:
        similarity = textdistance.cosine.normalized_similarity(u, c)
    except Exception:
        # fallback to simple ratio
        similarity = textdistance.ratio.normalized_similarity(u, c) if u or c else 0.0

    # Keyword overlap (0..1)
    try:
        kw_sim = keyword_similarity(u, c)
    except Exception:
        kw_sim = 0.0

    # Weighted scoring: give more weight to semantic similarity
    score = round((similarity * 0.7 + kw_sim * 0.3) * 100, 2)

    # Friendly feedback messages
    if score >= 85:
        feedback = "Excellent! Your answer is accurate and complete. ✅"
    elif score >= 65:
        feedback = "Good answer — you covered most points. Try adding a short example next time. 👍"
    elif score >= 45:
        feedback = "Fair attempt. You have partial understanding; include key terms and examples. 🛠️"
    else:
        feedback = "Needs improvement. Revise the topic and practice explaining it step by step. 📘"

    # Add targeted improvement tips (keywords or concepts missed)
    try:
        tips = get_improvement_tips(user_answer, correct_answer)
        if tips:
            feedback = f"{feedback} {tips}"
    except Exception:
        pass

    return score, feedback


def generate_report(user: str, student_id: str, subject: str, records: list):
    """
    Build a structured report dict and append it to reports/user_reports.json (newline-delimited JSON).
    Returns the report dict.
    """
    # Safeguard records
    records = records or []
    count = len(records)
    if count == 0:
        avg_score = 0.0
    else:
        # ensure numeric scores exist
        total = 0.0
        for r in records:
            try:
                total += float(r.get("score", 0.0))
            except Exception:
                total += 0.0
        avg_score = round(total / count, 2)

    weak_areas = [r.get("question") for r in records if (r.get("score", 0) or 0) < 60]

    report = {
        "user": user or "Student",
        "student_id": student_id or "Unknown",
        "subject": subject or "",
        "average_score": avg_score,
        "weak_areas": weak_areas,
        "records": records,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # Ensure reports directory exists
    try:
        os.makedirs(os.path.dirname(REPORTS_FILE), exist_ok=True)
        # Append newline-delimited JSON for easy reading
        with open(REPORTS_FILE, "a", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False)
            fh.write("\n")
    except Exception as e:
        # If saving fails, print and continue (report still returned)
        print("[Report Save Error]", e)

    return report
