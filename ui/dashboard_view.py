import streamlit as st
import pandas as pd
from dashboard.analytics import (
    get_kpis,
    get_today_attendance,
    get_student_analytics,
    get_subject_analytics,
    get_daily_trend
)
from dashboard.charts import (
    create_donut_chart,
    create_daily_trend_chart,
    create_subject_bar_chart,
    create_department_bar_chart
)
from database import crud

def render_dashboard_view():
    """Renders the executive attendance analytics dashboard."""
    st.header("📊 Attendance Analytics Dashboard")
    st.markdown("Real-time summary of attendance volume, daily trends, student rates, and subject analytics.")

    # 1. Top KPI Cards
    kpis = get_kpis()
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Registered Students", kpis["total_students"], help="Total students currently in system database")
    with c2:
        st.metric("Present Today", kpis["present_count"], delta=f"{kpis['present_count']} logged", delta_color="normal")
    with c3:
        st.metric("Absent Today", kpis["absent_count"], delta=f"-{kpis['absent_count']}", delta_color="inverse")
    with c4:
        st.metric("Attendance Rate", f"{kpis['attendance_percentage']}%")

    st.markdown("---")

    # 2. Charts Row
    col_chart1, col_chart2 = st.columns([1, 2], gap="large")

    with col_chart1:
        donut_fig = create_donut_chart(kpis["present_count"], kpis["absent_count"])
        st.plotly_chart(donut_fig, use_container_width=True)

    with col_chart2:
        df_trend = get_daily_trend(days=14)
        trend_fig = create_daily_trend_chart(df_trend)
        st.plotly_chart(trend_fig, use_container_width=True)

    st.markdown("---")

    # 3. Subject-wise & Department Analytics Row
    col_subj, col_dept = st.columns([1, 1], gap="large")

    with col_subj:
        df_subject = get_subject_analytics()
        subj_fig = create_subject_bar_chart(df_subject)
        st.plotly_chart(subj_fig, use_container_width=True)

    with col_dept:
        all_students = crud.get_all_students()
        df_students = pd.DataFrame(all_students) if all_students else pd.DataFrame()
        dept_fig = create_department_bar_chart(df_students)
        st.plotly_chart(dept_fig, use_container_width=True)

    st.markdown("---")

    # 4. Student-wise Analytics & Today's Attendance Table
    tab_today, tab_students = st.tabs(["📅 Today's Live Attendance Records", "🎓 Student-Wise Performance Analytics"])

    with tab_today:
        today_records = get_today_attendance()
        if today_records:
            df_today = pd.DataFrame(today_records)
            df_today["confidence"] = df_today["confidence"].apply(lambda c: f"{c*100:.1f}%")
            disp_cols = ["timestamp", "student_id", "name", "subject", "faculty", "section", "status", "confidence"]
            disp_df = df_today[disp_cols]
            disp_df.columns = ["Time", "Student ID", "Name", "Subject", "Faculty", "Section", "Status", "Confidence"]
            st.dataframe(disp_df, use_container_width=True, hide_index=True)
        else:
            st.info("No attendance records logged for today yet.")

    with tab_students:
        df_stud_analytics = get_student_analytics()
        if not df_stud_analytics.empty:
            def highlight_attendance(val):
                if val >= 75:
                    return "color: #16a34a; font-weight: bold;"
                elif val >= 60:
                    return "color: #ca8a04; font-weight: bold;"
                else:
                    return "color: #dc2626; font-weight: bold;"

            disp_stud = df_stud_analytics.copy()
            disp_stud.columns = ["Student ID", "Full Name", "Department", "Section", "Sessions Attended", "Attendance %", "Avg Confidence %"]
            st.dataframe(disp_stud, use_container_width=True, hide_index=True)
        else:
            st.info("No student performance records available.")
