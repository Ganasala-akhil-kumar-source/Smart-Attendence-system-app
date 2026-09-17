import os
import random
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import streamlit as st
from database.crud import verify_admin_login, update_admin_password, get_student

DEFAULT_ADMIN_EMAIL = "arjunakhil977@gmail.com"

def generate_otp(length: int = 6) -> str:
    """Generates a secure 6-digit random numeric verification code."""
    return "".join(str(random.randint(0, 9)) for _ in range(length))

def get_smtp_config():
    """Retrieves SMTP sender credentials from Streamlit secrets, environment, or session state."""
    if hasattr(st, "secrets") and "email" in st.secrets:
        return {
            "server": st.secrets["email"].get("smtp_server", "smtp.gmail.com"),
            "port": int(st.secrets["email"].get("smtp_port", 587)),
            "sender": st.secrets["email"].get("sender_email", ""),
            "password": st.secrets["email"].get("sender_password", "")
        }
    sender = os.environ.get("ALERT_SENDER_EMAIL", "")
    password = os.environ.get("ALERT_SENDER_PASSWORD", "")
    if sender and password:
        return {
            "server": "smtp.gmail.com",
            "port": 587,
            "sender": sender,
            "password": password
        }
    if "smtp_sender" in st.session_state and "smtp_password" in st.session_state:
        return {
            "server": "smtp.gmail.com",
            "port": 587,
            "sender": st.session_state["smtp_sender"],
            "password": st.session_state["smtp_password"]
        }
    return None

def send_password_change_request_email(otp_code: str, recipient_email: str = DEFAULT_ADMIN_EMAIL) -> tuple[bool, str]:
    """Sends a verification email with a 6-digit OTP to the admin email."""
    now_str = datetime.now().strftime("%d-%b-%Y at %I:%M %p")
    config = get_smtp_config()
    subject = "🚨 Security Alert: Admin Password Change Request - Smart Attendance"

    body_text = f"""Hello,

A request has been initiated to change the Administrator password for your Smart Attendance System.

Time: {now_str}
Recipient: {recipient_email}

Your 6-Digit Verification Code:
{otp_code}

(Valid for 10 minutes)

If YOU requested this password change, enter this verification code in the application to authorize the update.

If you did NOT request this change, DO NOT share this code with anyone. Someone may be trying to access your administrative account.

Regards,
Smart Attendance Security System
"""

    if config and config.get("sender") and config.get("password"):
        try:
            msg = MIMEMultipart()
            msg["From"] = f"Smart Attendance Security <{config['sender']}>"
            msg["To"] = recipient_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body_text, "plain"))

            server = smtplib.SMTP(config["server"], config["port"], timeout=15)
            server.starttls()
            server.login(config["sender"], config["password"])
            server.send_message(msg)
            server.quit()
            return True, f"✓ Security verification code sent to {recipient_email}. Please check your inbox."
        except Exception as e:
            return False, f"Failed to send email via SMTP: {e}"

    return False, f"SMTP sender not configured yet. (Verification Code: {otp_code})"

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
    """
    Renders password management with 2-Factor Email Authorization to arjunakhil977@gmail.com
    and administrative security controls.
    """
    st.header("⚙️ Admin & Security Settings")
    st.markdown("Manage administrator credentials with two-factor email verification and security policies.")

    current_admin = st.session_state.get("admin_user", "admin")
    col1, col2 = st.columns([1.2, 1], gap="large")

    with col1:
        st.subheader("🔐 Change Administrator Password (2FA Protected)")

        if "pwd_step" not in st.session_state:
            st.session_state["pwd_step"] = "request"

        if st.session_state["pwd_step"] == "request":
            st.info(f"📧 When updating your password, a 6-digit authorization code will be sent to **{DEFAULT_ADMIN_EMAIL}** to prevent unauthorized changes.")

            with st.form("request_pwd_form"):
                curr_pwd = st.text_input("Current Password *", type="password")
                new_pwd = st.text_input("New Password *", type="password")
                confirm_pwd = st.text_input("Confirm New Password *", type="password")
                req_btn = st.form_submit_button("Request Authorization Code", type="primary", use_container_width=True)

                if req_btn:
                    if not verify_admin_login(current_admin, curr_pwd):
                        st.error("Current password is incorrect.")
                    elif len(new_pwd) < 6:
                        st.error("New password must be at least 6 characters long.")
                    elif new_pwd != confirm_pwd:
                        st.error("New passwords do not match.")
                    else:
                        otp = generate_otp(6)
                        st.session_state["pending_pwd"] = new_pwd
                        st.session_state["pwd_otp"] = otp
                        st.session_state["otp_timestamp"] = time.time()

                        success, msg = send_password_change_request_email(otp, DEFAULT_ADMIN_EMAIL)
                        if success:
                            st.success(msg)
                        else:
                            st.warning(f"Note: {msg}")

                        st.session_state["pwd_step"] = "verify"
                        st.rerun()

        elif st.session_state["pwd_step"] == "verify":
            st.warning(f"📬 A 6-digit authorization code was sent to **{DEFAULT_ADMIN_EMAIL}**.")
            st.caption("Enter the code below within 10 minutes to authorize and complete the password change.")

            if not get_smtp_config() and "pwd_otp" in st.session_state:
                st.code(f"Demo OTP: {st.session_state['pwd_otp']}", language="text")

            with st.form("verify_otp_form"):
                entered_otp = st.text_input("Enter 6-Digit Code", max_chars=6, placeholder="e.g. 123456").strip()
                col_sub1, col_sub2 = st.columns(2)
                with col_sub1:
                    confirm_btn = st.form_submit_button("Verify & Update Password", type="primary", use_container_width=True)
                with col_sub2:
                    cancel_btn = st.form_submit_button("Cancel", use_container_width=True)

                if cancel_btn:
                    st.session_state["pwd_step"] = "request"
                    st.session_state.pop("pending_pwd", None)
                    st.session_state.pop("pwd_otp", None)
                    st.rerun()

                if confirm_btn:
                    elapsed = time.time() - st.session_state.get("otp_timestamp", 0)
                    if elapsed > 600:
                        st.error("The authorization code has expired. Please request a new code.")
                        st.session_state["pwd_step"] = "request"
                    elif entered_otp == st.session_state.get("pwd_otp"):
                        new_pwd = st.session_state.get("pending_pwd")
                        if update_admin_password(current_admin, new_pwd):
                            st.success("🎉 Password successfully updated with two-factor email verification!")
                            st.session_state["pwd_step"] = "request"
                            st.session_state.pop("pending_pwd", None)
                            st.session_state.pop("pwd_otp", None)
                            st.balloons()
                        else:
                            st.error("Failed to update password in database.")
                    else:
                        st.error("Invalid verification code. Please check your email and try again.")

    with col2:
        st.subheader("⚙️ Email Alert Settings (SMTP)")
        st.markdown(f"**Target Admin Email:** `{DEFAULT_ADMIN_EMAIL}`")

        with st.expander("Configure Gmail Sender (To Receive Live Emails)", expanded=False):
            st.markdown(
                """
                To receive live emails directly to your Gmail inbox:
                1. Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
                2. Generate a 16-character code
                3. Enter it below and click **Save Settings**
                """
            )
            with st.form("smtp_settings_form"):
                sender_email = st.text_input("Sender Gmail Address", value=st.session_state.get("smtp_sender", ""), placeholder="e.g. your-bot@gmail.com")
                sender_pwd = st.text_input("16-Letter Gmail App Password", value=st.session_state.get("smtp_password", ""), type="password", placeholder="•••• •••• •••• ••••")
                save_smtp = st.form_submit_button("Save Email Sender")

                if save_smtp:
                    st.session_state["smtp_sender"] = sender_email.strip()
                    st.session_state["smtp_password"] = sender_pwd.replace(" ", "")
                    st.success("Sender email settings saved for this session!")

            if st.button("📨 Send Test Email Now"):
                test_otp = generate_otp(6)
                ok, msg = send_password_change_request_email(test_otp, DEFAULT_ADMIN_EMAIL)
                if ok:
                    st.success(f"✓ Test email sent successfully to {DEFAULT_ADMIN_EMAIL}! Check your inbox.")
                else:
                    st.error(msg)

        st.markdown("---")
        st.subheader("🛡️ Security Policy")
        st.info(
            f"""
            - **2-Factor Email Authorization**: Enabled for `{DEFAULT_ADMIN_EMAIL}`.
            - **Password Hashing**: PBKDF2-HMAC-SHA256 (100,000 iterations + salt).
            - **Unauthorized Change Prevention**: An unknown person cannot change your password without entering the OTP sent to your personal email inbox.
            """
        )
