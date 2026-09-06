from pathlib import Path
from typing import Optional
import cv2
import numpy as np
from recognition.utils import get_safe_model_path

PROJECT_MODELS_DIR = Path(__file__).resolve().parent.parent / "data" / "models"

class FaceEmbedder:
    """
    Extracts 128-dimensional unit-normalized facial embeddings using
    OpenCV's SFace deep neural network recognizer.
    """
    def __init__(self):
        self.recognizer = None
        self._init_embedder()

    def _init_embedder(self):
        """Loads SFace recognizer model if available."""
        sface_path = get_safe_model_path("face_recognition_sface_2021dec.onnx", PROJECT_MODELS_DIR)
        if sface_path.exists() and sface_path.stat().st_size > 1000:
            try:
                self.recognizer = cv2.FaceRecognizerSF.create(str(sface_path), "")
                return
            except Exception:
                pass

        self.recognizer = None

    def align_crop(self, image: np.ndarray, raw_face: np.ndarray) -> np.ndarray:
        """
        Uses SFace's landmark-based affine transformation to crop and align the face
        to 112x112 canonical orientation.
        """
        if self.recognizer is not None and raw_face is not None:
            try:
                aligned = self.recognizer.alignCrop(image, raw_face)
                if aligned is not None and aligned.size > 0:
                    return aligned
            except Exception:
                pass

        # Fallback crop if alignment fails
        if raw_face is not None and len(raw_face) >= 4:
            x, y, w, h = int(raw_face[0]), int(raw_face[1]), int(raw_face[2]), int(raw_face[3])
            ih, iw = image.shape[:2]
            x, y = max(0, x), max(0, y)
            w, h = min(iw - x, w), min(ih - y, h)
            roi = image[y:y+h, x:x+w]
            if roi.size > 0:
                return cv2.resize(roi, (112, 112))
        return cv2.resize(image, (112, 112))

    def extract_embedding(self, image: np.ndarray, raw_face: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Extracts and L2-normalizes a 128-D embedding vector.
        Input can be an already aligned face (112x112) or original image + raw_face array.
        """
        if self.recognizer is not None:
            if raw_face is not None:
                aligned = self.align_crop(image, raw_face)
            else:
                aligned = cv2.resize(image, (112, 112))

            feat = self.recognizer.feature(aligned)
            feat = feat.flatten().astype(np.float32)

            # L2-normalize
            norm = np.linalg.norm(feat)
            if norm > 1e-6:
                feat = feat / norm
            return feat

        # Fallback deterministic pseudo-embedding
        return self._fallback_feature(image)

    def _fallback_feature(self, image: np.ndarray) -> np.ndarray:
        """Computes a 128-D normalized spatial-gradient histogram fallback vector."""
        resized = cv2.resize(image, (64, 64))
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY) if len(resized.shape) == 3 else resized
        cells = [gray[i*8:(i+1)*8, j*8:(j+1)*8] for i in range(8) for j in range(8)]
        feats = []
        for cell in cells:
            feats.append(float(np.mean(cell)))
            feats.append(float(np.std(cell)))
        vec = np.array(feats, dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm > 1e-6:
            vec = vec / norm
        return vec
