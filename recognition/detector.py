import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
import cv2
import numpy as np
from recognition.utils import get_safe_model_path, get_safe_cascade_path

PROJECT_MODELS_DIR = Path(__file__).resolve().parent.parent / "data" / "models"

class FaceDetector:
    """
    High-performance face detector utilizing OpenCV YuNet DNN model,
    with an automatic fallback to Haar cascades if ONNX model is missing.
    """
    def __init__(
        self,
        conf_threshold: float = 0.65,
        nms_threshold: float = 0.3,
        top_k: int = 5000
    ):
        self.conf_threshold = conf_threshold
        self.nms_threshold = nms_threshold
        self.top_k = top_k
        self.detector = None
        self.haar_cascade = None
        self._init_detector()

    def _init_detector(self):
        """Initializes YuNet DNN detector or falls back to Haar cascade."""
        yunet_path = get_safe_model_path("face_detection_yunet_2023mar.onnx", PROJECT_MODELS_DIR)
        if yunet_path.exists() and yunet_path.stat().st_size > 1000:
            try:
                self.detector = cv2.FaceDetectorYN.create(
                    str(yunet_path),
                    "",
                    (320, 320),
                    self.conf_threshold,
                    self.nms_threshold,
                    self.top_k
                )
                return
            except Exception:
                pass

        # Fallback to safe Haar Cascade path
        cascade_path = get_safe_cascade_path("haarcascade_frontalface_default.xml")
        if cascade_path.exists():
            self.haar_cascade = cv2.CascadeClassifier(str(cascade_path))
        else:
            raise RuntimeError("Neither YuNet model nor OpenCV Haar Cascade found.")

    def detect_faces(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detects faces in an image (BGR format).
        Returns a list of dictionaries with bounding box, confidence, and facial landmarks:
        [
            {
                'box': (x, y, w, h),
                'confidence': float,
                'landmarks': [(x1, y1), (x2, y2), (x3, y3), (x4, y4), (x5, y5)],
                'raw': raw_face_array_for_sface
            }
        ]
        """
        if image is None or image.size == 0:
            return []

        h, w = image.shape[:2]

        if self.detector is not None:
            self.detector.setInputSize((w, h))
            _, faces = self.detector.detect(image)

            if faces is None:
                return []

            results = []
            for face in faces:
                bx, by, bw, bh = int(face[0]), int(face[1]), int(face[2]), int(face[3])
                bx = max(0, bx)
                by = max(0, by)
                bw = min(w - bx, bw)
                bh = min(h - by, bh)

                if bw <= 10 or bh <= 10:
                    continue

                conf = float(face[-1])
                landmarks = [
                    (int(face[4]), int(face[5])),
                    (int(face[6]), int(face[7])),
                    (int(face[8]), int(face[9])),
                    (int(face[10]), int(face[11])),
                    (int(face[12]), int(face[13]))
                ]

                results.append({
                    "box": (bx, by, bw, bh),
                    "confidence": conf,
                    "landmarks": landmarks,
                    "raw": face
                })
            return results

        # Fallback using Haar Cascade
        if self.haar_cascade is not None:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            rects = self.haar_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )

            results = []
            for (bx, by, bw, bh) in rects:
                re = (bx + int(bw * 0.3), by + int(bh * 0.35))
                le = (bx + int(bw * 0.7), by + int(bh * 0.35))
                nt = (bx + int(bw * 0.5), by + int(bh * 0.55))
                rc = (bx + int(bw * 0.35), by + int(bh * 0.8))
                lc = (bx + int(bw * 0.65), by + int(bh * 0.8))

                raw = np.array([bx, by, bw, bh, re[0], re[1], le[0], le[1], nt[0], nt[1], rc[0], rc[1], lc[0], lc[1], 0.95], dtype=np.float32)
                results.append({
                    "box": (bx, by, bw, bh),
                    "confidence": 0.95,
                    "landmarks": [re, le, nt, rc, lc],
                    "raw": raw
                })
            return results

        return []

    def crop_face(self, image: np.ndarray, box: Tuple[int, int, int, int], target_size: Tuple[int, int] = (112, 112)) -> np.ndarray:
        """Crops and resizes a face region from an image."""
        x, y, w, h = box
        face_roi = image[y:y+h, x:x+w]
        if face_roi.size == 0:
            return np.zeros((target_size[1], target_size[0], 3), dtype=np.uint8)
        return cv2.resize(face_roi, target_size, interpolation=cv2.INTER_AREA)
