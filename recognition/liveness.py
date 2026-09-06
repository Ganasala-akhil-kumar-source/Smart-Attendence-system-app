import time
from typing import Tuple, List, Optional
import cv2
import numpy as np
from recognition.utils import get_safe_cascade_path

class LivenessTracker:
    """
    Anti-spoofing liveness detector designed to prevent attendance fraud via
    printed paper photographs, digital phone screens, and static images.

    Uses a hybrid approach:
    1. Eye-blink detection state machine (Open -> Closed -> Open).
    2. Head/Face micro-motion variance over a temporal sliding window.
    """
    def __init__(
        self,
        required_blinks: int = 1,
        consec_closed_min: int = 1,
        consec_closed_max: int = 8,
        motion_threshold: float = 1.2
    ):
        self.required_blinks = required_blinks
        self.consec_closed_min = consec_closed_min
        self.consec_closed_max = consec_closed_max
        self.motion_threshold = motion_threshold

        # Load safe eye cascade for eye openness detection
        cascade_path = get_safe_cascade_path("haarcascade_eye.xml")
        self.eye_cascade = cv2.CascadeClassifier(str(cascade_path))

        # State variables
        self.blink_count = 0
        self.closed_counter = 0
        self.is_eye_currently_closed = False
        self.is_verified = False
        self.center_history: List[Tuple[float, float]] = []
        self.last_update_time = time.time()

    def reset(self):
        """Resets the liveness state tracker for a new subject or session."""
        self.blink_count = 0
        self.closed_counter = 0
        self.is_eye_currently_closed = False
        self.is_verified = False
        self.center_history.clear()
        self.last_update_time = time.time()

    def update(
        self,
        image: np.ndarray,
        face_box: Tuple[int, int, int, int],
        landmarks: Optional[List[Tuple[int, int]]] = None
    ) -> Tuple[bool, str, int]:
        """
        Processes a single frame for anti-spoofing verification.

        Args:
            image: Original BGR frame
            face_box: (x, y, w, h)
            landmarks: Optional 5-point landmarks list [(re), (le), ...]

        Returns:
            (is_verified: bool, status_message: str, blink_count: int)
        """
        if self.is_verified:
            return True, "Liveness: VERIFIED (Human confirmed)", self.blink_count

        x, y, w, h = face_box
        cx, cy = x + w / 2.0, y + h / 2.0
        self.center_history.append((cx, cy))
        if len(self.center_history) > 25:
            self.center_history.pop(0)

        # 1. Evaluate Eye Region Openness
        eye_region_y_end = y + int(h * 0.55)
        eye_region_y_start = y + int(h * 0.15)
        eye_region = image[max(0, eye_region_y_start):eye_region_y_end, x:x+w]

        eyes_detected = 0
        if eye_region.size > 0 and not self.eye_cascade.empty():
            gray_eyes = cv2.cvtColor(eye_region, cv2.COLOR_BGR2GRAY)
            gray_eyes = cv2.equalizeHist(gray_eyes)
            detected = self.eye_cascade.detectMultiScale(
                gray_eyes,
                scaleFactor=1.15,
                minNeighbors=4,
                minSize=(15, 15)
            )
            eyes_detected = len(detected)

        # 2. State Machine for Eye Blink
        if eyes_detected == 0:
            self.closed_counter += 1
            if self.closed_counter >= self.consec_closed_min:
                self.is_eye_currently_closed = True
        else:
            if self.is_eye_currently_closed:
                # Transition: Closed -> Open
                if self.consec_closed_min <= self.closed_counter <= self.consec_closed_max:
                    self.blink_count += 1
                self.is_eye_currently_closed = False
                self.closed_counter = 0
            else:
                self.closed_counter = 0

        # Check blink requirement
        if self.blink_count >= self.required_blinks:
            self.is_verified = True
            return True, f"Liveness: VERIFIED ({self.blink_count} blinks detected)", self.blink_count

        # 3. Micro-Motion Fallback Check
        if len(self.center_history) >= 15:
            coords = np.array(self.center_history)
            std_dev = np.std(coords, axis=0)
            motion_metric = float(np.mean(std_dev))
            if 1.2 <= motion_metric <= 25.0 and len(self.center_history) >= 20:
                self.is_verified = True
                return True, "Liveness: VERIFIED (Natural micro-motion detected)", self.blink_count

        return False, f"Liveness: PENDING (Please blink to confirm | Blinks: {self.blink_count}/{self.required_blinks})", self.blink_count
