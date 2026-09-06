-- ==========================================================
-- Smart Attendance System Database Schema (SQLite)
-- Enforces Foreign Keys, Unique Session-Student constraints,
-- and indexed lookups for high performance.
-- ==========================================================

PRAGMA foreign_keys = ON;

-- Admins Table (Secure Auth)
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Students Table (Demographic metadata)
CREATE TABLE IF NOT EXISTS students (
    student_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    year INTEGER NOT NULL,
    section TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Student Biometrics (128-D Unit Normalized Embeddings)
-- Note: Raw webcam images are NEVER saved to preserve privacy.
CREATE TABLE IF NOT EXISTS student_biometrics (
    student_id TEXT PRIMARY KEY,
    embedding BLOB NOT NULL,
    embedding_dim INTEGER NOT NULL DEFAULT 128,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
);

-- Classroom / Lecture Sessions
CREATE TABLE IF NOT EXISTS sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    faculty TEXT NOT NULL,
    section TEXT NOT NULL,
    session_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'cancelled')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Attendance Records
-- Composite UNIQUE(session_id, student_id) guarantees no duplicate attendance marks.
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    student_id TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'Present' CHECK (status IN ('Present', 'Late', 'Excused')),
    confidence REAL NOT NULL,
    verified_liveness INTEGER DEFAULT 1,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    UNIQUE(session_id, student_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_students_dept_section ON students(department, section);
CREATE INDEX IF NOT EXISTS idx_sessions_date ON sessions(session_date, status);
CREATE INDEX IF NOT EXISTS idx_attendance_session ON attendance(session_id);
CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance(student_id);
