from datetime import date, datetime, time
import streamlit as st
import pandas as pd
from attendance.session import SessionManager
from database import crud

def render_session_view():
    """Renders the session management view."""
    st.header("📅 Classroom Session Management")
    st.markdown("Schedule, activate, and monitor attendance sessions for specific subjects and sections.")

    tab1, tab2, tab3 = st.tabs(["➕ Schedule New Session", "🟢 Active Sessions", "📜 Session History"])

    with tab1:
        st.subheader("Create Attendance Session")
        with st.form("create_session_form"):
            col1, col2 = st.columns(2)
            with col1:
                subject = st.text_input("Subject / Course Name *", placeholder="e.g. Artificial Intelligence")
                faculty = st.text_input("Faculty / Instructor *", placeholder="e.g. Prof. Alan Turing")
                section = st.text_input("Target Section *", value="A", placeholder="e.g. A, B, C").strip().upper()

            with col2:
                session_date = st.date_input("Session Date *", value=date.today())
                col_start, col_end = st.columns(2)
                with col_start:
                    start_time = st.time_input("Start Time *", value=datetime.now().time())
                with col_end:
                    # Default 1 hour later
                    now_plus_one = (datetime.now().hour + 1) % 24
                    end_time = st.time_input("End Time *", value=time(now_plus_one, 0))

            create_btn = st.form_submit_button("Create & Activate Session", type="primary", use_container_width=True)

            if create_btn:
                if not subject or not faculty or not section:
                    st.error("Please fill in Subject, Faculty, and Section.")
                else:
                    sess_id = SessionManager.create_session(
                        subject=subject,
                        faculty=faculty,
                        section=section,
                        session_date=session_date.isoformat(),
                        start_time=start_time.strftime("%H:%M"),
                        end_time=end_time.strftime("%H:%M")
                    )
                    st.success(f"✓ Session #{sess_id} for '{subject}' ({section}) created and marked active!")
                    st.rerun()

    with tab2:
        st.subheader("Currently Active Sessions")
        active_sessions = SessionManager.get_active_sessions()

        if not active_sessions:
            st.info("No active sessions currently running. Schedule one above to start logging attendance.")
        else:
            for s in active_sessions:
                with st.container():
                    sess_id = s["session_id"]
                    attendees = crud.get_attendance_for_session(sess_id)

                    col_info, col_count, col_action = st.columns([3, 1, 1])
                    with col_info:
                        st.markdown(
                            f"""
                            **Session #{sess_id} — {s['subject']}**  
                            Faculty: `{s['faculty']}` | Section: `{s['section']}` | Date: `{s['session_date']}` ({s['start_time']} - {s['end_time']})
                            """
                        )
                    with col_count:
                        st.metric("Attendees", len(attendees))
                    with col_action:
                        st.write("&nbsp;")
                        if st.button("Close Session", key=f"close_{sess_id}", type="secondary"):
                            SessionManager.close_session(sess_id)
                            st.warning(f"Session #{sess_id} closed.")
                            st.rerun()
                    st.markdown("---")

    with tab3:
        st.subheader("All Sessions Record")
        all_sessions = SessionManager.get_all_sessions(limit=100)
        if all_sessions:
            df = pd.DataFrame(all_sessions)
            df_display = df[["session_id", "subject", "faculty", "section", "session_date", "start_time", "end_time", "status", "created_at"]]
            df_display.columns = ["ID", "Subject", "Faculty", "Section", "Date", "Start", "End", "Status", "Created At"]
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        else:
            st.info("No session records found.")
