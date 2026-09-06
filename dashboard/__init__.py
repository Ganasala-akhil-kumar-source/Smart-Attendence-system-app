"""Dashboard package for Smart Attendance System"""
from dashboard.analytics import get_kpis, get_today_attendance, get_student_analytics, get_subject_analytics, get_daily_trend
from dashboard.charts import create_donut_chart, create_daily_trend_chart, create_subject_bar_chart, create_department_bar_chart

__all__ = [
    "get_kpis",
    "get_today_attendance",
    "get_student_analytics",
    "get_subject_analytics",
    "get_daily_trend",
    "create_donut_chart",
    "create_daily_trend_chart",
    "create_subject_bar_chart",
    "create_department_bar_chart"
]
