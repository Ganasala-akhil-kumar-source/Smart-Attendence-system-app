from datetime import datetime, date
from typing import Optional, List, Dict, Any
from database import crud

class SessionManager:
    """
    Handles lifecycle operations for classroom/lecture attendance sessions.
    """
    @staticmethod
    def create_session(
        subject: str,
        faculty: str,
        section: str,
        session_date: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> int:
        """
        Creates a new classroom attendance session with active status.
        """
        if not session_date:
            session_date = date.today().isoformat()
        if not start_time:
            start_time = datetime.now().strftime("%H:%M")
        if not end_time:
            # Default session length 1 hour
            end_time = datetime.now().strftime("%H:%M")

        session_id = crud.create_session(
            subject=subject,
            faculty=faculty,
            section=section,
            session_date=session_date,
            start_time=start_time,
            end_time=end_time
        )
        return session_id

    @staticmethod
    def get_active_sessions() -> List[Dict[str, Any]]:
        """Returns all currently active attendance sessions."""
        return crud.get_active_sessions()

    @staticmethod
    def get_all_sessions(limit: int = 100) -> List[Dict[str, Any]]:
        """Returns past and active sessions."""
        return crud.get_all_sessions(limit=limit)

    @staticmethod
    def close_session(session_id: int) -> bool:
        """Marks a session as completed."""
        return crud.close_session(session_id)

    @staticmethod
    def get_session(session_id: int) -> Optional[Dict[str, Any]]:
        """Fetches metadata for a specific session."""
        return crud.get_session(session_id)
