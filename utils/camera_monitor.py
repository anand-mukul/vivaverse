# utils/camera_monitor.py
import cv2
import streamlit as st
import time

def start_camera_monitor():
    """
    Opens webcam and monitors presence using face detection.
    Displays live feed in Streamlit app.
    Uses Streamlit's native loop instead of threading.
    """
    st.markdown("### 📷 Camera Monitor (Active)")
    st.info("Your webcam is on. Stay visible during the viva session.")

    # Placeholders for dynamic updates
    camera_placeholder = st.empty()
    status_placeholder = st.empty()
    
    # Stop button
    stop_button = st.button("Stop Camera", key="stop_camera")

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        st.error("⚠️ Cannot access webcam. Please check permissions.")
        return

    last_seen_time = time.time()
    alert_triggered = False

    # Run loop - will update on each Streamlit rerun
    while not stop_button:
        ret, frame = cap.read()
        if not ret:
            st.error("⚠️ Error reading from webcam.")
            break

        # Convert to grayscale for face detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        # Draw rectangles around detected faces
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Update detection status
        current_time = time.time()
        if len(faces) > 0:
            last_seen_time = current_time
            alert_triggered = False
            status_placeholder.success(f"✅ Face detected ({len(faces)} face(s))")
        else:
            time_away = current_time - last_seen_time
            if time_away > 5 and not alert_triggered:
                status_placeholder.warning(
                    f"⚠️ Face not detected for {int(time_away)} seconds! Stay focused."
                )
                alert_triggered = True
            elif time_away <= 5:
                status_placeholder.info("👤 Monitoring...")

        # Convert to RGB and display
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        camera_placeholder.image(frame_rgb, channels="RGB", width='stretch')

        # Small delay
        time.sleep(0.03)

    cap.release()
    cv2.destroyAllWindows()
    st.success("Camera stopped.")


def start_camera_with_session_state():
    """
    Alternative approach using session state for continuous monitoring.
    Better for concurrent viva functionality.
    """
    if 'camera_active' not in st.session_state:
        st.session_state.camera_active = False
    
    if 'last_seen' not in st.session_state:
        st.session_state.last_seen = time.time()

    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("### 📷 Camera Monitor")
    
    with col2:
        if st.button("Toggle Camera"):
            st.session_state.camera_active = not st.session_state.camera_active
    
    if not st.session_state.camera_active:
        st.info("Camera is off. Click 'Toggle Camera' to start monitoring.")
        return

    # Camera feed section
    camera_placeholder = st.empty()
    status_placeholder = st.empty()

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        st.error("⚠️ Cannot access webcam. Please check permissions.")
        st.session_state.camera_active = False
        return

    # Single frame capture (for non-blocking behavior)
    ret, frame = cap.read()
    
    if ret:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        current_time = time.time()
        if len(faces) > 0:
            st.session_state.last_seen = current_time
            status_placeholder.success(f"✅ Face detected")
        else:
            time_away = current_time - st.session_state.last_seen
            if time_away > 5:
                status_placeholder.warning(
                    f"⚠️ No face detected for {int(time_away)}s"
                )
            else:
                status_placeholder.info("👤 Monitoring...")

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        camera_placeholder.image(frame_rgb, channels="RGB", width='stretch')

    cap.release()
    
    # Auto-refresh for continuous monitoring
    time.sleep(0.1)
    st.rerun()