import os
import random
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import streamlit as st

DEFAULT_ADMIN_EMAIL = "arjunakhil977@gmail.com"

def generate_otp(length: int = 6) -> str:
    """Generates a secure 6-digit random numeric verification code."""
    return "".join(str(random.randint(0, 9)) for _ in range(length))

def get_smtp_config():
    if hasattr(st, "secrets") and "email" in st.secrets:
        return {
            "server": st.secrets["email"].get("smtp_server", "smtp.gmail.com"),
            "port": int(st.secrets["email"].get("smtp_port", 587)),
            "sender": st.secrets["email"].get("sender_email", ""),
            "password": st.secrets["email"].get("sender_password", "")
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
    now_str = datetime.now().strftime("%d-%b-%Y at %I:%M %p")
    config = get_smtp_config()
    subject = "🚨 Security Alert: Admin Password Change Request - Smart Attendance"

    body_text = f"""
Hello,

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

    return False, f"SMTP sender credentials not configured yet. (Verification Code: {otp_code})"
