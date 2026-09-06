from datetime import date, datetime, timedelta
import numpy as np
from database.connection import init_db
from database import crud
from attendance.session import SessionManager

def seed_sample_data():
    """Seeds the database with realistic sample students, sessions, and attendance records."""
    print("[Seed] Initializing database...")
    init_db()

    # 1. Enrolled Students
    sample_students = [
        {"id": "CS202401", "name": "Aarav Sharma", "dept": "Computer Science", "year": 3, "section": "A"},
        {"id": "CS202402", "name": "Diya Patel", "dept": "Computer Science", "year": 3, "section": "A"},
        {"id": "CS202403", "name": "Rohan Gupta", "dept": "Computer Science", "year": 3, "section": "B"},
        {"id": "IT202401", "name": "Ananya Reddy", "dept": "Information Technology", "year": 2, "section": "A"},
        {"id": "IT202402", "name": "Vikram Singh", "dept": "Information Technology", "year": 2, "section": "B"},
        {"id": "EC202401", "name": "Pooja Verma", "dept": "Electronics & Comm", "year": 4, "section": "A"}
    ]

    for s in sample_students:
        crud.add_student(
            student_id=s["id"],
            name=s["name"],
            department=s["dept"],
            year=s["year"],
            section=s["section"]
        )
        # Generate realistic 128-D unit embedding
        rng = np.random.RandomState(seed=abs(hash(s["id"])) % 10000)
        raw_vec = rng.randn(128).astype(np.float32)
        norm_vec = raw_vec / np.linalg.norm(raw_vec)
        crud.save_biometric_embedding(s["id"], norm_vec)

    print(f"[Seed] Successfully seeded {len(sample_students)} students with 128-D biometric embeddings.")

    # 2. Classroom Sessions
    today = date.today()
    s1 = SessionManager.create_session("Artificial Intelligence", "Dr. Andrew Ng", "A", today.isoformat(), "09:00", "10:00")
    s2 = SessionManager.create_session("Computer Networks", "Prof. James Kurose", "A", today.isoformat(), "10:30", "11:30")
    s3 = SessionManager.create_session("Database Systems", "Dr. Raghu Ramakrishnan", "B", (today - timedelta(days=1)).isoformat(), "14:00", "15:00")

    # 3. Attendance Records
    # Session 1 attendance (Today AI)
    crud.record_attendance(s1, "CS202401", confidence=0.94, verified_liveness=1)
    crud.record_attendance(s1, "CS202402", confidence=0.91, verified_liveness=1)
    crud.record_attendance(s1, "IT202401", confidence=0.88, verified_liveness=1)

    # Session 2 attendance (Today CN)
    crud.record_attendance(s2, "CS202401", confidence=0.95, verified_liveness=1)
    crud.record_attendance(s2, "IT202401", confidence=0.92, verified_liveness=1)

    # Session 3 attendance (Yesterday DB)
    crud.record_attendance(s3, "CS202403", confidence=0.89, verified_liveness=1)
    crud.record_attendance(s3, "IT202402", confidence=0.93, verified_liveness=1)

    print(f"[Seed] Successfully seeded 3 sessions and attendance records.")
    print("[Seed] Database ready for interactive testing and demonstration!")

if __name__ == "__main__":
    seed_sample_data()
