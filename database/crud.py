import os
import hashlib
import hmac
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any
import numpy as np
from database.connection import get_connection, get_db_cursor, DB_PATH

# ==========================================================
# 1. SECURITY & ADMIN AUTHENTICATION
# ==========================================================

def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    """
    Hashes a password using PBKDF2-HMAC-SHA256 with 100,000 iterations and a random salt.
    Returns format: hex_salt:hex_hash
    """
    if salt is None:
        salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return f"{salt.hex()}:{key.hex()}"

def verify_password(password: str, stored_hash: str) -> bool:
    """
    Verifies a plaintext password against the stored salt:hash string using constant-time comparison.
    """
    try:
        salt_hex, key_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        expected_key = bytes.fromhex(key_hex)
        actual_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        return hmac.compare_digest(expected_key, actual_key)
    except Exception:
        return False

def create_admin(username: str, password: str, db_path: Path = DB_PATH) -> bool:
    """Creates a new admin user with a hashed password."""
    pwd_hash = hash_password(password)
    try:
        with get_db_cursor(db_path) as cur:
            cur.execute(
                "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
                (username.strip(), pwd_hash)
            )
        return True
    except sqlite3.IntegrityError:
        return False

def verify_admin_login(username: str, password: str, db_path: Path = DB_PATH) -> bool:
    """Verifies administrator credentials during login."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT password_hash FROM admins WHERE username = ?", (username.strip(),))
    row = cur.fetchone()
    conn.close()
    if not row:
        return False
    return verify_password(password, row["password_hash"])

def get_admin_by_username(username: str, db_path: Path = DB_PATH) -> Optional[dict]:
    """Retrieves admin record by username."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, username, created_at FROM admins WHERE username = ?", (username.strip(),))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def update_admin_password(username: str, new_password: str, db_path: Path = DB_PATH) -> bool:
    """Updates password for an existing admin."""
    new_hash = hash_password(new_password)
    with get_db_cursor(db_path) as cur:
        cur.execute(
            "UPDATE admins SET password_hash = ? WHERE username = ?",
            (new_hash, username.strip())
        )
        return cur.rowcount > 0

# ==========================================================
# 2. STUDENT MANAGEMENT
# ==========================================================

def add_student(
    student_id: str,
    name: str,
    department: str,
    year: int,
    section: str,
    db_path: Path = DB_PATH
) -> bool:
    """Enrolls a new student profile."""
    try:
        with get_db_cursor(db_path) as cur:
            cur.execute(
                """
                INSERT INTO students (student_id, name, department, year, section)
                VALUES (?, ?, ?, ?, ?)
                """,
                (student_id.strip().upper(), name.strip(), department.strip(), int(year), section.strip().upper())
            )
        return True
    except sqlite3.IntegrityError:
        return False

def get_student(student_id: str, db_path: Path = DB_PATH) -> Optional[dict]:
    """Fetches student record by ID."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM students WHERE student_id = ?", (student_id.strip().upper(),))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_students(db_path: Path = DB_PATH) -> List[dict]:
    """Returns list of all enrolled students with biometric registration status."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT s.student_id, s.name, s.department, s.year, s.section, s.created_at,
               CASE WHEN b.student_id IS NOT NULL THEN 1 ELSE 0 END AS has_biometrics
        FROM students s
        LEFT JOIN student_biometrics b ON s.student_id = b.student_id
        ORDER BY s.student_id ASC
        """
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_student(student_id: str, db_path: Path = DB_PATH) -> bool:
    """
    Deletes a student. Relational constraints cascade deletion to biometrics
    and attendance history.
    """
    with get_db_cursor(db_path) as cur:
        cur.execute("DELETE FROM students WHERE student_id = ?", (student_id.strip().upper(),))
        return cur.rowcount > 0

# ==========================================================
# 3. BIOMETRIC EMBEDDINGS (PRIVACY-COMPLIANT STORAGE)
# ==========================================================

def save_biometric_embedding(
    student_id: str,
    embedding: np.ndarray,
    db_path: Path = DB_PATH
) -> bool:
    """
    Converts a 128-D float32 numpy vector into bytes and stores it in the database.
    Updates if already present.
    """
    student_id_clean = student_id.strip().upper()
    vec = np.ascontiguousarray(embedding, dtype=np.float32)
    embedding_blob = vec.tobytes()
    dim = int(vec.size)

    with get_db_cursor(db_path) as cur:
        cur.execute(
            """
            INSERT INTO student_biometrics (student_id, embedding, embedding_dim, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(student_id) DO UPDATE SET
                embedding = excluded.embedding,
                embedding_dim = excluded.embedding_dim,
                updated_at = CURRENT_TIMESTAMP
            """,
            (student_id_clean, sqlite3.Binary(embedding_blob), dim)
        )
    return True

def get_biometric_embedding(student_id: str, db_path: Path = DB_PATH) -> Optional[np.ndarray]:
    """Retrieves and deserializes the 128-D numpy embedding for a student."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT embedding, embedding_dim FROM student_biometrics WHERE student_id = ?",
        (student_id.strip().upper(),)
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    raw_blob = row["embedding"]
    dim = row["embedding_dim"]
    return np.frombuffer(raw_blob, dtype=np.float32).reshape(dim)

def get_all_student_embeddings(db_path: Path = DB_PATH) -> Dict[str, Dict[str, Any]]:
    """
    Loads all enrolled biometric face vectors into memory for fast batch cosine similarity comparison.
    Returns: {student_id: {'name': str, 'dept': str, 'section': str, 'embedding': np.ndarray}}
    """
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT b.student_id, b.embedding, b.embedding_dim, s.name, s.department, s.section
        FROM student_biometrics b
        JOIN students s ON b.student_id = s.student_id
        """
    )
    rows = cur.fetchall()
    conn.close()

    result = {}
    for r in rows:
        sid = r["student_id"]
        raw = r["embedding"]
        dim = r["embedding_dim"]
        emb = np.frombuffer(raw, dtype=np.float32).reshape(dim)
        result[sid] = {
            "name": r["name"],
            "department": r["department"],
            "section": r["section"],
            "embedding": emb
        }
    return result

def delete_student_biometrics(student_id: str, db_path: Path = DB_PATH) -> bool:
    """Deletes biometric embedding data for a student upon request without removing their academic profile."""
    with get_db_cursor(db_path) as cur:
        cur.execute("DELETE FROM student_biometrics WHERE student_id = ?", (student_id.strip().upper(),))
        return cur.rowcount > 0

# ==========================================================
# 4. SESSION MANAGEMENT
# ==========================================================

def create_session(
    subject: str,
    faculty: str,
    section: str,
    session_date: str,
    start_time: str,
    end_time: str,
    db_path: Path = DB_PATH
) -> int:
    """Creates a new classroom attendance session and returns session_id."""
    with get_db_cursor(db_path) as cur:
        cur.execute(
            """
            INSERT INTO sessions (subject, faculty, section, session_date, start_time, end_time, status)
            VALUES (?, ?, ?, ?, ?, ?, 'active')
            """,
            (subject.strip(), faculty.strip(), section.strip().upper(), session_date, start_time, end_time)
        )
        return cur.lastrowid

def get_session(session_id: int, db_path: Path = DB_PATH) -> Optional[dict]:
    """Fetches session metadata by ID."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def get_active_sessions(db_path: Path = DB_PATH) -> List[dict]:
    """Retrieves all sessions currently marked as 'active'."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM sessions WHERE status = 'active' ORDER BY session_date DESC, start_time DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_sessions(limit: int = 100, db_path: Path = DB_PATH) -> List[dict]:
    """Retrieves list of sessions ordered by most recent."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM sessions ORDER BY session_date DESC, start_time DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def close_session(session_id: int, db_path: Path = DB_PATH) -> bool:
    """Marks an active session as completed."""
    with get_db_cursor(db_path) as cur:
        cur.execute("UPDATE sessions SET status = 'completed' WHERE session_id = ?", (session_id,))
        return cur.rowcount > 0

# ==========================================================
# 5. ATTENDANCE OPERATIONS
# ==========================================================

def is_attendance_marked(session_id: int, student_id: str, db_path: Path = DB_PATH) -> bool:
    """Checks if a student already has attendance recorded for a session."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM attendance WHERE session_id = ? AND student_id = ?",
        (session_id, student_id.strip().upper())
    )
    marked = cur.fetchone() is not None
    conn.close()
    return marked

def record_attendance(
    session_id: int,
    student_id: str,
    confidence: float,
    verified_liveness: int = 1,
    status: str = "Present",
    db_path: Path = DB_PATH
) -> Tuple[bool, str]:
    """
    Records attendance.
    Returns: (True, "Success message") if recorded.
             (False, "Duplicate or error message") if already marked or invalid.
    """
    clean_sid = student_id.strip().upper()
    if is_attendance_marked(session_id, clean_sid, db_path):
        return False, f"Attendance for Student {clean_sid} is already marked for this session."

    try:
        with get_db_cursor(db_path) as cur:
            cur.execute(
                """
                INSERT INTO attendance (session_id, student_id, confidence, verified_liveness, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, clean_sid, float(confidence), int(verified_liveness), status)
            )
        return True, f"Attendance marked successfully for {clean_sid} (Confidence: {confidence*100:.1f}%)."
    except sqlite3.IntegrityError as e:
        return False, f"Duplicate check failed: {str(e)}"

def get_attendance_for_session(session_id: int, db_path: Path = DB_PATH) -> List[dict]:
    """Retrieves all attendance logs for a specific session."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT a.id, a.session_id, a.student_id, s.name, s.department, s.section,
               a.timestamp, a.status, a.confidence, a.verified_liveness
        FROM attendance a
        JOIN students s ON a.student_id = s.student_id
        WHERE a.session_id = ?
        ORDER BY a.timestamp DESC
        """,
        (session_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_attendance_history(
    student_id: Optional[str] = None,
    subject: Optional[str] = None,
    section: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 500,
    db_path: Path = DB_PATH
) -> List[dict]:
    """
    Query attendance records with dynamic search filters.
    """
    conn = get_connection(db_path)
    cur = conn.cursor()

    query = """
        SELECT a.id, a.session_id, sess.subject, sess.faculty, sess.session_date,
               a.student_id, s.name, s.department, s.section,
               a.timestamp, a.status, a.confidence, a.verified_liveness
        FROM attendance a
        JOIN sessions sess ON a.session_id = sess.session_id
        JOIN students s ON a.student_id = s.student_id
        WHERE 1=1
    """
    params = []

    if student_id:
        query += " AND (a.student_id LIKE ? OR s.name LIKE ?)"
        like_val = f"%{student_id.strip()}%"
        params.extend([like_val, like_val])
    if subject:
        query += " AND sess.subject LIKE ?"
        params.append(f"%{subject.strip()}%")
    if section:
        query += " AND s.section = ?"
        params.append(section.strip().upper())
    if date_from:
        query += " AND sess.session_date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND sess.session_date <= ?"
        params.append(date_to)

    query += " ORDER BY a.timestamp DESC LIMIT ?"
    params.append(limit)

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_student_attendance_summary(student_id: str, db_path: Path = DB_PATH) -> Optional[dict]:
    """
    Retrieves comprehensive attendance summary for a student:
    - Personal profile
    - Total sessions held in student's section
    - Total sessions attended
    - Attendance percentage
    - Subject-wise breakdown
    - Attendance history records
    """
    clean_sid = student_id.strip().upper()
    student = get_student(clean_sid, db_path)
    if not student:
        return None

    conn = get_connection(db_path)
    cur = conn.cursor()

    # Total sessions for section
    cur.execute(
        "SELECT COUNT(*) AS total_held FROM sessions WHERE section = ?",
        (student["section"],)
    )
    total_held = cur.fetchone()["total_held"]

    # Sessions attended by student
    cur.execute(
        """
        SELECT COUNT(*) AS total_attended
        FROM attendance a
        JOIN sessions s ON a.session_id = s.session_id
        WHERE a.student_id = ?
        """,
        (clean_sid,)
    )
    total_attended = cur.fetchone()["total_attended"]

    overall_pct = (total_attended / total_held * 100.0) if total_held > 0 else (100.0 if total_attended > 0 else 0.0)
    overall_pct = round(min(100.0, overall_pct), 1)

    # Subject-wise breakdown
    cur.execute(
        """
        SELECT s.subject,
               COUNT(s.session_id) AS total_classes,
               COUNT(a.id) AS attended_classes,
               ROUND(AVG(a.confidence) * 100, 1) AS avg_confidence
        FROM sessions s
        LEFT JOIN attendance a ON s.session_id = a.session_id AND a.student_id = ?
        WHERE s.section = ?
        GROUP BY s.subject
        ORDER BY s.subject ASC
        """,
        (clean_sid, student["section"])
    )
    subjects_raw = cur.fetchall()
    subject_breakdown = []
    for row in subjects_raw:
        held = row["total_classes"]
        att = row["attended_classes"]
        pct = round((att / held * 100.0), 1) if held > 0 else 0.0
        subject_breakdown.append({
            "subject": row["subject"],
            "total_classes": held,
            "attended_classes": att,
            "missed_classes": max(0, held - att),
            "attendance_pct": pct,
            "avg_confidence": row["avg_confidence"] or 0.0
        })

    # Chronological history
    cur.execute(
        """
        SELECT a.id, a.timestamp, s.session_date, s.subject, s.faculty,
               a.status, a.confidence, a.verified_liveness
        FROM attendance a
        JOIN sessions s ON a.session_id = s.session_id
        WHERE a.student_id = ?
        ORDER BY a.timestamp DESC
        """,
        (clean_sid,)
    )
    history = [dict(r) for r in cur.fetchall()]
    conn.close()

    return {
        "student": student,
        "total_held": total_held,
        "total_attended": total_attended,
        "total_missed": max(0, total_held - total_attended),
        "overall_percentage": overall_pct,
        "is_eligible": overall_pct >= 75.0,
        "subjects": subject_breakdown,
        "history": history
    }

