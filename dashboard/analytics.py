from datetime import date
from typing import Dict, Any, List, Optional
import pandas as pd
from database.connection import get_connection

def get_kpis(session_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Computes top-level attendance metrics:
    - Total enrolled students
    - Total students present (in active session or today)
    - Total absent
    - Attendance percentage
    """
    conn = get_connection()
    cur = conn.cursor()

    # Total registered students
    cur.execute("SELECT COUNT(*) AS total FROM students")
    total_students = cur.fetchone()["total"]

    if session_id:
        # Metrics for specific session
        cur.execute("SELECT COUNT(DISTINCT student_id) AS present FROM attendance WHERE session_id = ?", (session_id,))
        present_count = cur.fetchone()["present"]
    else:
        # Metrics for today across all sessions
        today_str = date.today().isoformat()
        cur.execute(
            """
            SELECT COUNT(DISTINCT a.student_id) AS present
            FROM attendance a
            JOIN sessions s ON a.session_id = s.session_id
            WHERE s.session_date = ?
            """,
            (today_str,)
        )
        present_count = cur.fetchone()["present"]

    absent_count = max(0, total_students - present_count)
    rate = (present_count / total_students * 100.0) if total_students > 0 else 0.0

    conn.close()

    return {
        "total_students": total_students,
        "present_count": present_count,
        "absent_count": absent_count,
        "attendance_percentage": round(rate, 1)
    }

def get_today_attendance() -> List[Dict[str, Any]]:
    """Returns all attendance logs recorded today."""
    conn = get_connection()
    cur = conn.cursor()
    today_str = date.today().isoformat()
    cur.execute(
        """
        SELECT a.id, a.session_id, sess.subject, sess.faculty, sess.section,
               a.student_id, s.name, s.department, a.timestamp, a.status, a.confidence
        FROM attendance a
        JOIN sessions sess ON a.session_id = sess.session_id
        JOIN students s ON a.student_id = s.student_id
        WHERE sess.session_date = ?
        ORDER BY a.timestamp DESC
        """,
        (today_str,)
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_student_analytics() -> pd.DataFrame:
    """
    Computes student-wise performance:
    Total sessions attended, total classes held in their section, attendance %.
    """
    conn = get_connection()

    # Total sessions per section
    df_sessions = pd.read_sql_query(
        "SELECT section, COUNT(*) as total_sessions FROM sessions GROUP BY section",
        conn
    )
    # Attendance count per student
    df_attendance = pd.read_sql_query(
        """
        SELECT s.student_id, s.name, s.department, s.section,
               COUNT(a.id) as sessions_attended,
               ROUND(AVG(a.confidence) * 100, 1) as avg_confidence
        FROM students s
        LEFT JOIN attendance a ON s.student_id = a.student_id
        GROUP BY s.student_id
        """,
        conn
    )
    conn.close()

    if df_attendance.empty:
        return pd.DataFrame(columns=["student_id", "name", "department", "section", "sessions_attended", "attendance_pct", "avg_confidence"])

    merged = df_attendance.merge(df_sessions, on="section", how="left")
    merged["total_sessions"] = merged["total_sessions"].fillna(0).astype(int)

    def calc_pct(row):
        tot = row["total_sessions"]
        att = row["sessions_attended"]
        if tot == 0:
            return 100.0 if att > 0 else 0.0
        return round(min(100.0, (att / tot) * 100.0), 1)

    merged["attendance_pct"] = merged.apply(calc_pct, axis=1)
    return merged[["student_id", "name", "department", "section", "sessions_attended", "attendance_pct", "avg_confidence"]]

def get_subject_analytics() -> pd.DataFrame:
    """
    Aggregates attendance metrics per subject.
    """
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT s.subject,
               COUNT(DISTINCT s.session_id) as total_sessions,
               COUNT(a.id) as total_attendees,
               ROUND(AVG(a.confidence) * 100, 1) as avg_confidence
        FROM sessions s
        LEFT JOIN attendance a ON s.session_id = a.session_id
        GROUP BY s.subject
        ORDER BY total_attendees DESC
        """,
        conn
    )
    conn.close()
    return df

def get_daily_trend(days: int = 14) -> pd.DataFrame:
    """
    Returns daily attendance trend for the past N days.
    """
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT s.session_date as date,
               COUNT(a.id) as present_count
        FROM sessions s
        JOIN attendance a ON s.session_id = a.session_id
        GROUP BY s.session_date
        ORDER BY s.session_date ASC
        LIMIT ?
        """,
        conn,
        params=(days,)
    )
    conn.close()
    return df
