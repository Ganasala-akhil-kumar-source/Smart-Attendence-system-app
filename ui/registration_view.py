import streamlit as st
import cv2
import numpy as np
import pandas as pd
from database import crud
from recognition import FaceDetector, FaceEmbedder

@st.cache_resource
def get_recognition_models():
    """Caches FaceDetector and FaceEmbedder in memory across re-renders."""
    detector = FaceDetector()
    embedder = FaceEmbedder()
    return detector, embedder

def render_registration_view():
    """Renders the student registration and biometric enrollment interface."""
    st.header("📝 Student Registration & Biometric Enrollment")
    st.markdown("Register student academic profiles and securely enroll 128-dimensional facial biometric vectors.")

    detector, embedder = get_recognition_models()

    tab1, tab2 = st.tabs(["➕ New Student Enrollment", "👥 Enrolled Students Directory"])

    with tab1:
        col_form, col_cam = st.columns([1, 1], gap="large")

        with col_form:
            st.subheader("1. Student Information")
            student_id = st.text_input("Student ID / Roll No *", placeholder="e.g. CS202401").strip().upper()
            full_name = st.text_input("Full Name *", placeholder="e.g. John Doe").strip()

            dept_col, year_col = st.columns(2)
            with dept_col:
                department = st.selectbox(
                    "Department *",
                    ["Computer Science", "Information Technology", "Electronics & Comm", "Mechanical", "Civil", "Electrical", "Other"]
                )
            with year_col:
                year = st.selectbox("Year *", [1, 2, 3, 4], index=2)

            section = st.text_input("Section *", value="A", placeholder="e.g. A, B, C").strip().upper()

        with col_cam:
            st.subheader("2. Biometric Face Capture")
            st.caption("Privacy Notice: Raw photos are never stored. Only mathematical embeddings are saved.")

            input_method = st.radio("Capture Method", ["Webcam Snapshot", "Upload Image File"], horizontal=True)

            captured_image = None
            if input_method == "Webcam Snapshot":
                camera_file = st.camera_input("Capture Student Face")
                if camera_file is not None:
                    bytes_data = camera_file.getvalue()
                    captured_image = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
            else:
                uploaded_file = st.file_uploader("Upload Clear Face Photo", type=["jpg", "jpeg", "png"])
                if uploaded_file is not None:
                    bytes_data = uploaded_file.getvalue()
                    captured_image = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)

            face_detected = False
            embedding_vector = None

            if captured_image is not None:
                faces = detector.detect_faces(captured_image)
                if len(faces) == 0:
                    st.warning("⚠️ No face detected. Please ensure adequate lighting and center your face.")
                elif len(faces) > 1:
                    st.warning(f"⚠️ Multiple faces detected ({len(faces)}). Please ensure only one person is in frame.")
                else:
                    face = faces[0]
                    bx, by, bw, bh = face["box"]
                    # Draw visual verification box on preview
                    preview_img = captured_image.copy()
                    cv2.rectangle(preview_img, (bx, by), (bx + bw, by + bh), (0, 255, 0), 2)
                    cv2.putText(preview_img, f"Face: {face['confidence']*100:.1f}%", (bx, max(20, by - 10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                    preview_rgb = cv2.cvtColor(preview_img, cv2.COLOR_BGR2RGB)
                    st.image(preview_rgb, caption="Face Detection Verified", use_container_width=True)

                    # Extract 128-D embedding
                    embedding_vector = embedder.extract_embedding(captured_image, face["raw"])
                    face_detected = True
                    st.success(f"✓ 128-D Biometric Embedding extracted successfully (Confidence: {face['confidence']*100:.1f}%)")

        st.markdown("---")
        submit_btn = st.button("Complete Student Enrollment", type="primary", use_container_width=True)
        if submit_btn:
            if not student_id or not full_name or not section:
                st.error("Please fill in all mandatory fields marked with *.")
            elif not face_detected or embedding_vector is None:
                st.error("Please capture or upload a valid single face photo to extract biometric embeddings.")
            else:
                # 1. Add student demographic profile
                student_added = crud.add_student(
                    student_id=student_id,
                    name=full_name,
                    department=department,
                    year=year,
                    section=section
                )
                if not student_added:
                    # Check if student already exists
                    existing = crud.get_student(student_id)
                    if existing:
                        st.info(f"Student ID {student_id} already exists. Updating biometrics...")
                    else:
                        st.error(f"Failed to create student profile for {student_id}.")
                        return

                # 2. Save 128-D Biometric Embedding
                crud.save_biometric_embedding(student_id, embedding_vector)
                st.success(f"🎉 Student {full_name} ({student_id}) enrolled successfully!")
                st.balloons()

    with tab2:
        st.subheader("Enrolled Students Directory")
        students = crud.get_all_students()

        if not students:
            st.info("No students enrolled yet. Use the tab above to add students.")
        else:
            df = pd.DataFrame(students)
            df["Biometrics"] = df["has_biometrics"].apply(lambda x: "✅ Enrolled" if x == 1 else "❌ Missing")
            df_display = df[["student_id", "name", "department", "year", "section", "Biometrics", "created_at"]]
            df_display.columns = ["Student ID", "Full Name", "Department", "Year", "Section", "Biometric Status", "Enrolled At"]

            st.dataframe(df_display, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.subheader("Student Data & Biometric Management (Security & Privacy)")
            col_sel, col_action1, col_action2 = st.columns([2, 1, 1])

            with col_sel:
                selected_sid = st.selectbox(
                    "Select Student ID for Management",
                    options=[s["student_id"] for s in students],
                    format_func=lambda sid: f"{sid} - {next((s['name'] for s in students if s['student_id'] == sid), '')}"
                )

            with col_action1:
                st.write("&nbsp;")
                if st.button("🗑️ Delete Biometrics Only", help="Wipes facial embeddings while retaining student records."):
                    if crud.delete_student_biometrics(selected_sid):
                        st.warning(f"Biometric data deleted for {selected_sid}.")
                        st.rerun()
                    else:
                        st.error("Failed to delete biometrics.")

            with col_action2:
                st.write("&nbsp;")
                if st.button("❌ Delete Student Entirely", type="primary", help="Completely removes student, biometrics, and attendance."):
                    if crud.delete_student(selected_sid):
                        st.success(f"Student {selected_sid} and associated data removed.")
                        st.rerun()
                    else:
                        st.error("Failed to delete student.")
