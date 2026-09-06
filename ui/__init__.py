"""UI Views package for Smart Attendance System"""
from ui.auth_view import render_login_view, render_security_view
from ui.registration_view import render_registration_view
from ui.session_view import render_session_view
from ui.attendance_view import render_attendance_view
from ui.dashboard_view import render_dashboard_view
from ui.reports_view import render_reports_view
from ui.student_view import render_student_portal_view

__all__ = [
    "render_login_view",
    "render_security_view",
    "render_registration_view",
    "render_session_view",
    "render_attendance_view",
    "render_dashboard_view",
    "render_reports_view",
    "render_student_portal_view"
]
