import streamlit as st
from database.crud import verify_admin_login, update_admin_password, get_student

def render_login_view():
    """Renders dual-role login interface for Administrators and Students."""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            """
            <div style="text-align: center; padding: 20px 0;">
                <h2 style="margin-bottom: 5px;">🎓 Smart Attendance System</h2>
                <p style="color: #64748b;">Facial Biometrics & Academic Attendance Portal</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        tab_student, tab_admin = st.tabs(["🎓 Student Login", "👨‍💼 Faculty / Admin Login"])

        # Tab 1: Student Login (Self-Service)
        with tab_student:
            st.subheader("Student Self-Service Portal")
            st.caption("Enter your Student ID / Roll Number to view your personal attendance records.")

            with st.form("student_login_form"):
                student_id = st.text_input("Student ID / Roll Number", placeholder="e.g. CS202401").strip().upper()
                student_btn = st.form_submit_button("Check My Attendance", use_container_width=True, type="primary")

                if student_btn:
                    if not student_id:
                        st.error("Please enter your Student ID.")
                    else:
                        student = get_student(student_id)
                        if student:
                            st.session_state["authenticated"] = True
                            st.session_state["role"] = "student"
                            st.session_state["student_id"] = student_id
                            st.session_state["student_name"] = student["name"]
                            st.success(f"Welcome, {student['name']}!")
                            st.rerun()
                        else:
                            st.error(f"Student ID '{student_id}' not found in registry. Please contact administration.")

            st.markdown(
                """
                <div style="font-size: 0.82rem; color: #64748b; margin-top: 10px;">
                    💡 <i>Try demo student IDs: <code>CS202401</code>, <code>CS202402</code>, <code>IT202401</code></i>
                </div>
                """,
                unsafe_allow_html=True
            )

        # Tab 2: Admin Login
        with tab_admin:
            st.subheader("Administrator / Faculty Sign In")
            with st.form("admin_login_form"):
                username = st.text_input("Admin Username", value="", placeholder="e.g. admin")
                password = st.text_input("Password", type="password", placeholder="••••••••")
                submitted = st.form_submit_button("Sign In as Admin", use_container_width=True, type="primary")

                if submitted:
                    if not username or not password:
                        st.error("Please enter both username and password.")
                    elif verify_admin_login(username, password):
                        st.session_state["authenticated"] = True
                        st.session_state["role"] = "admin"
                        st.session_state["admin_user"] = username
                        st.success(f"Welcome back, {username}!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials. Please try again.")

            st.caption("Default admin credentials: `admin` / `admin123`")

def render_security_view():
    """Renders password management and administrative settings."""
    st.header("⚙️ Admin & Security Settings")
    st.markdown("Manage administrative credentials and security policies.")

    current_admin = st.session_state.get("admin_user", "admin")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Change Administrator Password")
        with st.form("change_password_form"):
            curr_pwd = st.text_input("Current Password", type="password")
            new_pwd = st.text_input("New Password", type="password")
            confirm_pwd = st.text_input("Confirm New Password", type="password")
            change_btn = st.form_submit_button("Update Password", type="primary")

            if change_btn:
                if not verify_admin_login(current_admin, curr_pwd):
                    st.error("Current password is incorrect.")
                elif len(new_pwd) < 6:
                    st.error("New password must be at least 6 characters long.")
                elif new_pwd != confirm_pwd:
                    st.error("New passwords do not match.")
                else:
                    if update_admin_password(current_admin, new_pwd):
                        st.success("Password successfully updated!")
                    else:
                        st.error("Failed to update password.")

    with col2:
        st.subheader("Security Architecture Information")
        st.info(
            """
            - **Password Storage**: Hashed with salted `PBKDF2-HMAC-SHA256` (100,000 iterations).
            - **Biometric Storage**: 128-dimensional unit embeddings only. No raw face photos stored.
            - **Anti-Spoofing**: Temporal eye-blink detection & micro-motion variance.
            - **Relational Integrity**: Foreign keys with `ON DELETE CASCADE` enabled.
            """
        )
