import streamlit as st
import pandas as pd
import plotly.express as px
from database import crud

def render_student_portal_view(student_id: str):
    """
    Renders dedicated self-service attendance portal for an individual student.
    """
    summary = crud.get_student_attendance_summary(student_id)
    if not summary:
        st.error(f"Could not load records for Student ID: {student_id}")
        return

    student = summary["student"]

    # Student Header Banner
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); padding: 24px; border-radius: 12px; color: white; margin-bottom: 25px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <h2 style="margin: 0; color: white;">👋 Welcome, {student['name']}</h2>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">
                        Roll No: <b>{student['student_id']}</b> | Dept: <b>{student['department']}</b> | Year {student['year']} (Section {student['section']})
                    </p>
                </div>
                <div style="text-align: right; margin-top: 10px;">
                    <span style="background: {'#16a34a' if summary['is_eligible'] else '#dc2626'}; padding: 6px 14px; border-radius: 20px; font-weight: bold; font-size: 0.9rem;">
                        {'✓ EXAM ELIGIBLE (>= 75%)' if summary['is_eligible'] else '⚠️ LOW ATTENDANCE WARNING (< 75%)'}
                    </span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 1. Metric Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Overall Attendance", f"{summary['overall_percentage']}%")
    with c2:
        st.metric("Classes Attended", summary["total_attended"])
    with c3:
        st.metric("Total Classes Held", summary["total_held"])
    with c4:
        st.metric("Classes Missed", summary["total_missed"])

    st.markdown("---")

    # 2. Subject-wise Attendance Breakdown
    st.subheader("📚 Subject-Wise Attendance Breakdown")
    subjects = summary["subjects"]

    if subjects:
        df_sub = pd.DataFrame(subjects)

        col_chart, col_table = st.columns([1, 1], gap="large")

        with col_chart:
            # Color subjects based on >=75%
            df_sub["color"] = df_sub["attendance_pct"].apply(lambda p: "#16a34a" if p >= 75 else "#ea580c" if p >= 60 else "#dc2626")
            fig = px.bar(
                df_sub,
                x="subject",
                y="attendance_pct",
                color="attendance_pct",
                color_continuous_scale=["#dc2626", "#eab308", "#16a34a"],
                range_color=[0, 100],
                labels={"subject": "Course", "attendance_pct": "Attendance %"},
                title="Subject Attendance % (75% Minimum Required)"
            )
            fig.add_hline(y=75, line_dash="dash", line_color="red", annotation_text="75% Requirement", annotation_position="bottom right")
            fig.update_layout(height=320, margin=dict(t=40, b=20, l=20, r=20))
            st.plotly_chart(fig, use_container_width=True)

        with col_table:
            disp_sub = df_sub[["subject", "attended_classes", "total_classes", "missed_classes", "attendance_pct"]].copy()
            disp_sub["Status"] = disp_sub["attendance_pct"].apply(
                lambda p: "✅ Good (>=75%)" if p >= 75 else "⚠️ Warning (<75%)"
            )
            disp_sub.columns = ["Subject", "Attended", "Total Held", "Missed", "Attendance %", "Status"]
            st.dataframe(disp_sub, use_container_width=True, hide_index=True)
    else:
        st.info("No class sessions recorded yet for your section.")

    st.markdown("---")

    # 3. Chronological Attendance History
    st.subheader("🗓️ Personal Attendance History")
    history = summary["history"]

    if history:
        df_hist = pd.DataFrame(history)
        df_hist["confidence"] = df_hist["confidence"].apply(lambda c: f"{c*100:.1f}%")
        disp_hist = df_hist[["session_date", "timestamp", "subject", "faculty", "status", "confidence"]].copy()
        disp_hist.columns = ["Date", "Timestamp", "Subject", "Faculty", "Status", "Recognition Confidence"]

        st.dataframe(disp_hist, use_container_width=True, hide_index=True)

        # Download Personal Attendance Slip
        csv_data = disp_hist.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📄 Download My Attendance Report (CSV)",
            data=csv_data,
            file_name=f"attendance_{student_id}.csv",
            mime="text/csv"
        )
    else:
        st.info("You have not attended any recorded sessions yet.")
