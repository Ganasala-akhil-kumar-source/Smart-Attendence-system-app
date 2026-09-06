import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

def create_donut_chart(present_count: int, absent_count: int) -> go.Figure:
    """Creates an interactive donut chart showing Present vs Absent breakdown."""
    labels = ["Present", "Absent"]
    values = [present_count, absent_count]
    colors = ["#22c55e", "#ef4444"]

    if present_count == 0 and absent_count == 0:
        values = [1]
        labels = ["No Data"]
        colors = ["#94a3b8"]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.6,
        marker=dict(colors=colors),
        textinfo="label+percent",
        hoverinfo="label+value"
    )])
    fig.update_layout(
        title="Today's Attendance Status",
        showlegend=True,
        margin=dict(t=40, b=20, l=20, r=20),
        height=280
    )
    return fig

def create_daily_trend_chart(df_trend: pd.DataFrame) -> go.Figure:
    """Creates a line chart for attendance trend over time."""
    if df_trend.empty:
        fig = go.Figure()
        fig.add_annotation(text="No historical attendance records available", showarrow=False)
        fig.update_layout(height=300, margin=dict(t=30, b=20, l=20, r=20))
        return fig

    fig = px.line(
        df_trend,
        x="date",
        y="present_count",
        markers=True,
        labels={"date": "Date", "present_count": "Students Present"},
        title="Daily Attendance Trend"
    )
    fig.update_traces(line_color="#3b82f6", line_width=3, marker=dict(size=8, color="#1d4ed8"))
    fig.update_layout(
        margin=dict(t=40, b=30, l=30, r=20),
        height=300,
        hovermode="x unified"
    )
    return fig

def create_subject_bar_chart(df_subject: pd.DataFrame) -> go.Figure:
    """Creates a bar chart comparing attendance volume across subjects."""
    if df_subject.empty:
        fig = go.Figure()
        fig.add_annotation(text="No subject attendance records found", showarrow=False)
        fig.update_layout(height=300, margin=dict(t=30, b=20, l=20, r=20))
        return fig

    fig = px.bar(
        df_subject,
        x="subject",
        y="total_attendees",
        color="total_attendees",
        color_continuous_scale="Viridis",
        labels={"subject": "Subject", "total_attendees": "Total Attendees"},
        title="Attendance Volume by Subject"
    )
    fig.update_layout(
        margin=dict(t=40, b=30, l=30, r=20),
        height=300
    )
    return fig

def create_department_bar_chart(df_students: pd.DataFrame) -> go.Figure:
    """Creates a bar chart for enrolled student distribution across departments."""
    if df_students.empty or "department" not in df_students.columns:
        fig = go.Figure()
        fig.add_annotation(text="No department data", showarrow=False)
        return fig

    dept_counts = df_students["department"].value_counts().reset_index()
    dept_counts.columns = ["department", "count"]

    fig = px.pie(
        dept_counts,
        names="department",
        values="count",
        title="Enrolled Students by Department",
        hole=0.4
    )
    fig.update_layout(
        margin=dict(t=40, b=20, l=20, r=20),
        height=280
    )
    return fig
