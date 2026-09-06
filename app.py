import streamlit as st
from database.connection import init_db
from database import crud
from attendance.session import SessionManager
from ui import (
    render_login_view,
    render_security_view,
    render_registration_view,
    render_session_view,
    render_attendance_view,
    render_dashboard_view,
    render_reports_view,
    render_student_portal_view
)

# 1. Page Configuration
st.set_page_config(
    page_title="Smart Attendance System",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Initialize SQLite Database Schema & Default Admin
init_db()

# 3. Session State Initialization
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "role" not in st.session_state:
    st.session_state["role"] = None
if "admin_user" not in st.session_state:
    st.session_state["admin_user"] = None
if "student_id" not in st.session_state:
    st.session_state["student_id"] = None
if "student_name" not in st.session_state:
    st.session_state["student_name"] = None
if "nav_menu" not in st.session_state:
    st.session_state["nav_menu"] = "📊 Dashboard"

# 4. Authentication Guard
if not st.session_state["authenticated"]:
    render_login_view()
    st.stop()

# 5. Role-Based Sidebar Navigation & Routing
user_role = st.session_state.get("role", "admin")

with st.sidebar:
    st.markdown(
        """
        <div style="padding: 10px 0;">
            <h2 style="margin: 0; color: #1e293b;">🎓 Smart Attendance</h2>
            <p style="margin: 0; font-size: 0.85rem; color: #64748b;">AI Biometric & Liveness System</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown("---")

    if user_role == "student":
        student_id = st.session_state.get("student_id", "")
        student_name = st.session_state.get("student_name", "Student")
        st.markdown(f"**Student Portal**\n\n👤 `{student_name}`\n\n🆔 `{student_id}`")
        st.markdown("---")

        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state["authenticated"] = False
            st.session_state["role"] = None
            st.session_state["student_id"] = None
            st.session_state["student_name"] = None
            st.rerun()

    else:
        # Admin Profile Badge
        current_admin = st.session_state.get("admin_user", "admin")
        st.caption(f"Logged in as: **{current_admin}** (Administrator)")

        nav_options = [
            "📊 Dashboard",
            "📷 Mark Attendance",
            "📝 Student Registration",
            "📅 Session Management",
            "📋 Attendance Reports",
            "⚙️ Security & Settings"
        ]

        selected_menu = st.radio(
            "Navigation",
            options=nav_options,
            index=nav_options.index(st.session_state["nav_menu"]) if st.session_state["nav_menu"] in nav_options else 0
        )
        st.session_state["nav_menu"] = selected_menu

        st.markdown("---")

        # Quick System Stats in Sidebar
        total_students = len(crud.get_all_students())
        active_sessions = len(SessionManager.get_active_sessions())

        st.metric("Enrolled Students", total_students)
        st.metric("Active Sessions", active_sessions)

        st.markdown("---")
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state["authenticated"] = False
            st.session_state["role"] = None
            st.session_state["admin_user"] = None
            st.session_state["camera_running"] = False
            st.rerun()

# 6. Route to Selected View Based on Role
if user_role == "student":
    render_student_portal_view(st.session_state["student_id"])
else:
    if selected_menu == "📊 Dashboard":
        render_dashboard_view()
    elif selected_menu == "📷 Mark Attendance":
        render_attendance_view()
    elif selected_menu == "📝 Student Registration":
        render_registration_view()
    elif selected_menu == "📅 Session Management":
        render_session_view()
    elif selected_menu == "📋 Attendance Reports":
        render_reports_view()
    elif selected_menu == "⚙️ Security & Settings":
        render_security_view()
