from typing import Dict, Any, Optional, List
from database import crud

class AttendanceManager:
    """
    Coordinates real-time attendance decisions, enforcing:
    1. Active session requirements.
    2. Unknown face rejection.
    3. Anti-spoofing liveness verification.
    4. Strict duplicate prevention for the same session.
    """
    @staticmethod
    def process_recognition_event(
        session_id: Optional[int],
        student_id: Optional[str],
        student_name: Optional[str],
        confidence: float,
        is_live: bool
    ) -> Dict[str, Any]:
        """
        Evaluates a face recognition event and records attendance if all rules pass.

        Returns structured result:
        {
            'status': 'SUCCESS' | 'DUPLICATE' | 'UNKNOWN' | 'LIVENESS_PENDING' | 'NO_SESSION',
            'marked': bool,
            'student_id': str or None,
            'name': str or None,
            'confidence': float,
            'message': str
        }
        """
        if not session_id:
            return {
                "status": "NO_SESSION",
                "marked": False,
                "student_id": None,
                "name": None,
                "confidence": confidence,
                "message": "Select an active session before marking attendance."
            }

        if not student_id:
            return {
                "status": "UNKNOWN",
                "marked": False,
                "student_id": None,
                "name": "Unknown Person",
                "confidence": confidence,
                "message": "Unregistered face detected. Attendance cannot be recorded."
            }

        name_display = student_name or student_id

        # Anti-spoofing check
        if not is_live:
            return {
                "status": "LIVENESS_PENDING",
                "marked": False,
                "student_id": student_id,
                "name": name_display,
                "confidence": confidence,
                "message": f"Recognized: {name_display}. Please blink to verify live presence."
            }

        # Duplicate check
        if crud.is_attendance_marked(session_id, student_id):
            return {
                "status": "DUPLICATE",
                "marked": False,
                "student_id": student_id,
                "name": name_display,
                "confidence": confidence,
                "message": f"Attendance already marked for {name_display} ({student_id}) in this session."
            }

        # Record attendance in database
        success, msg = crud.record_attendance(
            session_id=session_id,
            student_id=student_id,
            confidence=confidence,
            verified_liveness=1,
            status="Present"
        )

        if success:
            return {
                "status": "SUCCESS",
                "marked": True,
                "student_id": student_id,
                "name": name_display,
                "confidence": confidence,
                "message": f"Verified Present: {name_display} ({student_id}) - Confidence: {confidence*100:.1f}%"
            }
        else:
            return {
                "status": "DUPLICATE",
                "marked": False,
                "student_id": student_id,
                "name": name_display,
                "confidence": confidence,
                "message": msg
            }

    @staticmethod
    def get_session_attendance(session_id: int) -> List[Dict[str, Any]]:
        """Fetches attendance records for a session."""
        return crud.get_attendance_for_session(session_id)

    @staticmethod
    def get_attendance_history(**filters) -> List[Dict[str, Any]]:
        """Fetches filtered attendance history."""
        return crud.get_attendance_history(**filters)
