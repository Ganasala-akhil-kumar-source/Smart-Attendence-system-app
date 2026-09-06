import io
from datetime import date, timedelta
from pathlib import Path
import streamlit as st
import pandas as pd
from attendance.manager import AttendanceManager
from database import crud

EXPORTS_DIR = Path(__file__).resolve().parent.parent / "exports"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

def render_reports_view():
    """Renders attendance history search, filtering, and CSV/Excel export view."""
    st.header("📋 Attendance Reports & Export")
    st.markdown("Filter comprehensive attendance logs by student, subject, section, or date range and export to CSV or Excel.")

    # 1. Search & Filter Bar
    with st.expander("🔍 Search & Filter Criteria", expanded=True):
        fcol1, fcol2, fcol3 = st.columns(3)
        with fcol1:
            search_query = st.text_input("Search Student ID or Name", placeholder="e.g. CS2024 or John").strip()
        with fcol2:
            all_sessions = crud.get_all_sessions(limit=200)
            subjects = sorted(list(set(s["subject"] for s in all_sessions))) if all_sessions else []
            subject_filter = st.selectbox("Filter by Subject", options=["All Subjects"] + subjects)
        with fcol3:
            all_students = crud.get_all_students()
            sections = sorted(list(set(s["section"] for s in all_students))) if all_students else []
            section_filter = st.selectbox("Filter by Section", options=["All Sections"] + sections)

        dcol1, dcol2 = st.columns(2)
        with dcol1:
            start_date = st.date_input("From Date", value=date.today() - timedelta(days=30))
        with dcol2:
            end_date = st.date_input("To Date", value=date.today())

    # 2. Query Database with Filters
    records = AttendanceManager.get_attendance_history(
        student_id=search_query if search_query else None,
        subject=subject_filter if subject_filter != "All Subjects" else None,
        section=section_filter if section_filter != "All Sections" else None,
        date_from=start_date.isoformat() if start_date else None,
        date_to=end_date.isoformat() if end_date else None,
        limit=1000
    )

    st.markdown(f"**Found {len(records)} matching attendance records**")

    if not records:
        st.info("No attendance records match the selected criteria.")
        return

    df = pd.DataFrame(records)
    df["confidence_pct"] = df["confidence"].apply(lambda c: f"{c*100:.1f}%")
    df["liveness_status"] = df["verified_liveness"].apply(lambda l: "Verified" if l else "Pending")

    display_cols = [
        "id", "timestamp", "session_date", "subject", "faculty",
        "student_id", "name", "department", "section",
        "status", "confidence_pct", "liveness_status"
    ]
    df_display = df[display_cols].copy()
    df_display.columns = [
        "Record ID", "Marked Time", "Session Date", "Subject", "Faculty",
        "Student ID", "Full Name", "Department", "Section",
        "Attendance Status", "Confidence", "Anti-Spoofing Liveness"
    ]

    st.dataframe(df_display, use_container_width=True, hide_index=True)

    # 3. Export to CSV and Excel
    st.markdown("---")
    st.subheader("📥 Export Attendance Report")

    exp_col1, exp_col2 = st.columns(2)

    # CSV Export
    with exp_col1:
        csv_data = df_display.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📄 Download as CSV",
            data=csv_data,
            file_name=f"attendance_report_{date.today().isoformat()}.csv",
            mime="text/csv",
            use_container_width=True,
            type="primary"
        )

    # Excel (.xlsx) Export
    with exp_col2:
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            df_display.to_excel(writer, index=False, sheet_name="Attendance Records")
        excel_data = excel_buffer.getvalue()

        st.download_button(
            label="📊 Download as Excel (.xlsx)",
            data=excel_data,
            file_name=f"attendance_report_{date.today().isoformat()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary"
        )
