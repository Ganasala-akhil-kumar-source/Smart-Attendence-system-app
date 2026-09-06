import os
import unittest
import tempfile
from pathlib import Path
import numpy as np

from database.connection import get_connection, init_db
from database import crud
from attendance.session import SessionManager
from attendance.manager import AttendanceManager
from recognition.matcher import FaceMatcher
from recognition.liveness import LivenessTracker

class TestSmartAttendance(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = Path(self.temp_db.name)
        self.temp_db.close()
        init_db(self.db_path)

    def tearDown(self):
        try:
            if self.db_path.exists():
                os.remove(self.db_path)
        except Exception:
            pass

    def test_admin_authentication(self):
        """Tests admin login and password hashing."""
        self.assertTrue(crud.verify_admin_login("admin", "admin123", self.db_path))
        self.assertFalse(crud.verify_admin_login("admin", "wrongpass", self.db_path))
        self.assertFalse(crud.verify_admin_login("nonexistent", "admin123", self.db_path))

        # Test password update
        crud.update_admin_password("admin", "newsecret99", self.db_path)
        self.assertTrue(crud.verify_admin_login("admin", "newsecret99", self.db_path))
        self.assertFalse(crud.verify_admin_login("admin", "admin123", self.db_path))

    def test_student_and_biometrics(self):
        """Tests student enrollment, 128-D embedding storage, retrieval, and privacy deletion."""
        added = crud.add_student("S101", "Alice Wonder", "Computer Science", 2, "A", self.db_path)
        self.assertTrue(added)

        # Test embedding serialization
        sample_emb = np.random.randn(128).astype(np.float32)
        sample_emb = sample_emb / np.linalg.norm(sample_emb)
        crud.save_biometric_embedding("S101", sample_emb, self.db_path)

        # Retrieve and verify round-trip
        retrieved_emb = crud.get_biometric_embedding("S101", self.db_path)
        self.assertIsNotNone(retrieved_emb)
        self.assertEqual(retrieved_emb.shape, (128,))
        self.assertTrue(np.allclose(sample_emb, retrieved_emb, atol=1e-5))

        # Test privacy biometric deletion
        crud.delete_student_biometrics("S101", self.db_path)
        self.assertIsNone(crud.get_biometric_embedding("S101", self.db_path))
        # Student record itself should still exist
        stud = crud.get_student("S101", self.db_path)
        self.assertIsNotNone(stud)

    def test_session_lifecycle(self):
        """Tests session creation, active querying, and completion."""
        sess_id = crud.create_session("Machine Learning", "Dr. Turing", "A", "2026-09-06", "09:00", "10:00", self.db_path)
        self.assertGreater(sess_id, 0)

        active = crud.get_active_sessions(self.db_path)
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["subject"], "Machine Learning")

        crud.close_session(sess_id, self.db_path)
        active_after = crud.get_active_sessions(self.db_path)
        self.assertEqual(len(active_after), 0)

    def test_duplicate_attendance_prevention(self):
        """Tests that attendance cannot be duplicated for the same student in the same session."""
        crud.add_student("S201", "Bob Builder", "Civil", 1, "B", self.db_path)
        sess_id = crud.create_session("Structures", "Prof. Brick", "B", "2026-09-06", "11:00", "12:00", self.db_path)

        # First attendance record: Should succeed
        ok1, msg1 = crud.record_attendance(sess_id, "S201", 0.95, 1, "Present", self.db_path)
        self.assertTrue(ok1)

        # Second attendance record: Must fail (Duplicate rejected)
        ok2, msg2 = crud.record_attendance(sess_id, "S201", 0.97, 1, "Present", self.db_path)
        self.assertFalse(ok2)
        self.assertIn("already marked", msg2)

    def test_face_matcher(self):
        """Tests cosine similarity threshold and top-1 identity determination."""
        matcher = FaceMatcher(similarity_threshold=0.55)

        vec_alice = np.random.randn(128).astype(np.float32)
        vec_alice = vec_alice / np.linalg.norm(vec_alice)

        vec_bob = np.random.randn(128).astype(np.float32)
        vec_bob = vec_bob / np.linalg.norm(vec_bob)

        enrolled = {
            "S01": {"name": "Alice", "embedding": vec_alice},
            "S02": {"name": "Bob", "embedding": vec_bob}
        }

        # Query with exact Alice vector
        matched_id, score, meta = matcher.match(vec_alice, enrolled)
        self.assertEqual(matched_id, "S01")
        self.assertAlmostEqual(score, 1.0, places=4)

        # Query with random unknown vector
        unknown_vec = np.random.randn(128).astype(np.float32)
        unknown_vec = unknown_vec / np.linalg.norm(unknown_vec)
        matched_unk, score_unk, _ = matcher.match(unknown_vec, enrolled)
        self.assertIsNone(matched_unk)

    def test_anti_spoofing_tracker(self):
        """Tests liveness state tracker reset and verification logic."""
        tracker = LivenessTracker(required_blinks=1)
        self.assertFalse(tracker.is_verified)
        tracker.reset()
        self.assertEqual(tracker.blink_count, 0)

    def test_student_portal_summary(self):
        """Tests retrieval of student personal attendance summary and metrics."""
        crud.add_student("STU99", "Clark Kent", "Journalism", 1, "A", self.db_path)
        s1 = crud.create_session("Ethics", "Prof. White", "A", "2026-09-06", "09:00", "10:00", self.db_path)
        crud.record_attendance(s1, "STU99", 0.96, 1, "Present", self.db_path)

        summary = crud.get_student_attendance_summary("STU99", self.db_path)
        self.assertIsNotNone(summary)
        self.assertEqual(summary["student"]["name"], "Clark Kent")
        self.assertEqual(summary["total_attended"], 1)
        self.assertEqual(summary["total_held"], 1)
        self.assertEqual(summary["overall_percentage"], 100.0)
        self.assertTrue(summary["is_eligible"])
        self.assertEqual(len(summary["subjects"]), 1)
        self.assertEqual(len(summary["history"]), 1)

if __name__ == "__main__":
    unittest.main()

