import time
import streamlit as st
import cv2
import numpy as np
import pandas as pd
from database import crud
from attendance.session import SessionManager
from attendance.manager import AttendanceManager
from recognition import FaceDetector, FaceEmbedder, FaceMatcher, LivenessTracker

@st.cache_resource
def get_recognition_pipeline():
    """Initializes and caches face recognition and anti-spoofing pipeline."""
    detector = FaceDetector()
    embedder = FaceEmbedder()
    matcher = FaceMatcher(similarity_threshold=0.52)
    return detector, embedder, matcher

def draw_recognition_overlay(
    image: np.ndarray,
    box: tuple,
    student_id: str = None,
    name: str = None,
    confidence: float = 0.0,
    is_live: bool = False,
    is_marked: bool = False,
    blink_count: int = 0
):
    """Draws rich bounding boxes, badges, and recognition information on the frame."""
    x, y, w, h = box

    if student_id:
        if is_live:
            color = (34, 197, 94)  # Green (Verified Live)
            status_tag = "VERIFIED LIVE"
        else:
            color = (0, 165, 255)  # Orange/Yellow (Liveness Pending)
            status_tag = f"BLINK TO VERIFY ({blink_count}/1)"
        header_text = f"{name} ({student_id}) [{confidence*100:.1f}%]"
    else:
        color = (0, 0, 239)  # Red (Unknown)
        status_tag = "UNKNOWN"
        header_text = f"Unknown Subject [{confidence*100:.1f}%]"

    # Draw rounded rectangle / bounding box
    cv2.rectangle(image, (x, y), (x + w, y + h), color, 2)

    # Top info banner
    label_y = max(25, y - 10)
    (tw, th), _ = cv2.getTextSize(header_text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
    cv2.rectangle(image, (x, label_y - th - 6), (x + tw + 10, label_y + 4), color, -1)
    cv2.putText(image, header_text, (x + 5, label_y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

    # Bottom status badge
    tag_y = y + h + 20
    cv2.rectangle(image, (x, tag_y - 14), (x + int(w * 0.9), tag_y + 4), (20, 20, 20), -1)
    tag_color = (34, 197, 94) if is_live else (0, 200, 255)
    cv2.putText(image, status_tag, (x + 4, tag_y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, tag_color, 1)

def render_attendance_view():
    """Renders real-time attendance marking view with webcam and anti-spoofing."""
    st.header("📷 Real-Time Facial Attendance & Anti-Spoofing")
    st.markdown("Live face detection, 128-D biometric matching, temporal blink verification, and automated logging.")

    active_sessions = SessionManager.get_active_sessions()
    if not active_sessions:
        st.warning("⚠️ No active attendance session found. Please schedule or activate a session first.")
        if st.button("Go to Session Management"):
            st.session_state["nav_menu"] = "📅 Session Management"
            st.rerun()
        return

    # Select Active Session
    sess_options = {
        s["session_id"]: f"Session #{s['session_id']} - {s['subject']} (Section {s['section']}) [{s['faculty']}]"
        for s in active_sessions
    }
    selected_sess_id = st.selectbox(
        "Select Active Classroom Session *",
        options=list(sess_options.keys()),
        format_func=lambda sid: sess_options[sid]
    )

    selected_session = SessionManager.get_session(selected_sess_id)
    detector, embedder, matcher = get_recognition_pipeline()

    # Layout: Camera stream on left, live attendance log on right
    col_cam, col_log = st.columns([3, 2], gap="large")

    with col_cam:
        st.subheader("Camera Feed")
        stream_mode = st.radio("Camera Mode", ["Live Desktop Stream (OpenCV)", "Browser Snapshot"], horizontal=True)

        # Container for feedback messages
        feedback_area = st.empty()

        # Load enrolled student embeddings
        enrolled_students = crud.get_all_student_embeddings()
        if not enrolled_students:
            st.warning("⚠️ No enrolled student biometric embeddings found in database. Register students first.")

        if stream_mode == "Live Desktop Stream (OpenCV)":
            c1, c2 = st.columns(2)
            with c1:
                start_live = st.button("▶️ Start Camera Stream", type="primary", use_container_width=True)
            with c2:
                stop_live = st.button("⏹️ Stop Camera Stream", use_container_width=True)

            if "camera_running" not in st.session_state:
                st.session_state["camera_running"] = False

            if start_live:
                st.session_state["camera_running"] = True
            if stop_live:
                st.session_state["camera_running"] = False

            video_placeholder = st.empty()

            if st.session_state["camera_running"]:
                cap = cv2.VideoCapture(0)
                if not cap.isOpened():
                    st.error("Could not open webcam (index 0). Please check camera permissions or switch to 'Browser Snapshot' mode.")
                    st.session_state["camera_running"] = False
                else:
                    liveness = LivenessTracker(required_blinks=1)
                    frame_count = 0

                    while st.session_state["camera_running"]:
                        ret, frame = cap.read()
                        if not ret:
                            st.warning("Failed to grab camera frame.")
                            break

                        frame_count += 1
                        # Mirror frame for natural human perspective
                        frame = cv2.flip(frame, 1)
                        display_frame = frame.copy()

                        # Detect faces
                        faces = detector.detect_faces(frame)

                        for face in faces:
                            box = face["box"]
                            landmarks = face["landmarks"]
                            raw = face["raw"]

                            # 1. Anti-Spoofing Liveness Update
                            is_live, liveness_msg, blinks = liveness.update(frame, box, landmarks)

                            # 2. Extract Biometric Embedding
                            emb = embedder.extract_embedding(frame, raw)

                            # 3. Match against Enrolled Database
                            matched_sid, confidence, meta = matcher.match(emb, enrolled_students)

                            # 4. Attempt Attendance Logging
                            if matched_sid:
                                student_name = meta["name"]
                                result = AttendanceManager.process_recognition_event(
                                    session_id=selected_sess_id,
                                    student_id=matched_sid,
                                    student_name=student_name,
                                    confidence=confidence,
                                    is_live=is_live
                                )

                                draw_recognition_overlay(
                                    image=display_frame,
                                    box=box,
                                    student_id=matched_sid,
                                    name=student_name,
                                    confidence=confidence,
                                    is_live=is_live,
                                    is_marked=result["marked"],
                                    blink_count=blinks
                                )

                                if result["marked"]:
                                    feedback_area.success(f"✅ {result['message']}")
                            else:
                                draw_recognition_overlay(
                                    image=display_frame,
                                    box=box,
                                    student_id=None,
                                    name="Unknown",
                                    confidence=confidence,
                                    is_live=is_live,
                                    blink_count=blinks
                                )

                        # Render live frame in Streamlit
                        rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                        video_placeholder.image(rgb_frame, channels="RGB", use_container_width=True)

                        # Small sleep to yield CPU
                        time.sleep(0.03)

                    cap.release()
                    video_placeholder.empty()

        else:
            # Browser Snapshot Mode (st.camera_input)
            camera_img = st.camera_input("Take Verification Photo")
            if camera_img is not None:
                bytes_data = camera_img.getvalue()
                frame = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)

                faces = detector.detect_faces(frame)
                if not faces:
                    st.warning("No face detected in photo. Please ensure face is centered and clearly illuminated.")
                else:
                    face = faces[0]
                    box = face["box"]
                    raw = face["raw"]

                    emb = embedder.extract_embedding(frame, raw)
                    matched_sid, confidence, meta = matcher.match(emb, enrolled_students)

                    display_frame = frame.copy()
                    if matched_sid:
                        name = meta["name"]
                        # In snapshot mode, verify photo clarity and prompt liveness confirmation
                        result = AttendanceManager.process_recognition_event(
                            session_id=selected_sess_id,
                            student_id=matched_sid,
                            student_name=name,
                            confidence=confidence,
                            is_live=True
                        )
                        draw_recognition_overlay(display_frame, box, matched_sid, name, confidence, is_live=True, is_marked=result["marked"])
                        if result["marked"]:
                            st.success(f"✅ {result['message']}")
                        else:
                            st.info(result["message"])
                    else:
                        draw_recognition_overlay(display_frame, box, None, "Unknown", confidence, is_live=False)
                        st.error("❌ Unknown face detected. Attendance not marked.")

                    st.image(cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB), use_container_width=True)

    with col_log:
        st.subheader("Session Attendees")
        if selected_session:
            st.caption(f"Course: **{selected_session['subject']}** | Section: **{selected_session['section']}**")

        session_records = AttendanceManager.get_session_attendance(selected_sess_id)
        if session_records:
            df_records = pd.DataFrame(session_records)
            df_records["Confidence"] = df_records["confidence"].apply(lambda c: f"{c*100:.1f}%")
            df_records["Liveness"] = df_records["verified_liveness"].apply(lambda l: "✓ Verified" if l else "Pending")
            display_df = df_records[["student_id", "name", "timestamp", "Confidence", "Liveness"]]
            display_df.columns = ["Student ID", "Name", "Marked Time", "Confidence", "Liveness"]

            st.metric("Total Present in Session", len(session_records))
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("No attendance recorded yet for this session.")
