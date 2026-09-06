"""Recognition package for Smart Attendance System"""
from recognition.detector import FaceDetector
from recognition.embedder import FaceEmbedder
from recognition.matcher import FaceMatcher
from recognition.liveness import LivenessTracker

__all__ = ["FaceDetector", "FaceEmbedder", "FaceMatcher", "LivenessTracker"]
