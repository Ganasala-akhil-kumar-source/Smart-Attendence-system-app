from typing import Dict, Tuple, Optional, Any
import numpy as np

class FaceMatcher:
    """
    Performs fast vector comparison using Cosine Similarity and Euclidean Distance
    against enrolled student biometrics.
    """
    def __init__(self, similarity_threshold: float = 0.52):
        """
        similarity_threshold: Minimum cosine similarity required to accept a match.
        For SFace, cosine similarity >= 0.50 corresponds to high-confidence match.
        """
        self.similarity_threshold = similarity_threshold

    @staticmethod
    def cosine_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
        """
        Calculates cosine similarity between two vectors: dot(u, v) / (||u|| * ||v||)
        Values range from -1.0 to 1.0 (for unit vectors, simply dot(u, v)).
        """
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        if norm1 < 1e-6 or norm2 < 1e-6:
            return 0.0
        return float(np.dot(emb1, emb2) / (norm1 * norm2))

    @staticmethod
    def euclidean_distance(emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Calculates L2 Euclidean distance between two vectors."""
        return float(np.linalg.norm(emb1 - emb2))

    def match(
        self,
        query_embedding: np.ndarray,
        enrolled_students: Dict[str, Dict[str, Any]]
    ) -> Tuple[Optional[str], float, Optional[Dict[str, Any]]]:
        """
        Compares a query face embedding against all enrolled students.

        Returns:
            (student_id, confidence_score, student_metadata) if matched above threshold.
            (None, best_score, None) if unknown / no match above threshold.
        """
        if not enrolled_students or query_embedding is None:
            return None, 0.0, None

        best_score = -1.0
        best_sid = None
        best_meta = None

        # Compare against each enrolled student
        for sid, data in enrolled_students.items():
            enrolled_emb = data.get("embedding")
            if enrolled_emb is None:
                continue

            score = self.cosine_similarity(query_embedding, enrolled_emb)
            if score > best_score:
                best_score = score
                best_sid = sid
                best_meta = data

        # Apply confidence threshold
        if best_score >= self.similarity_threshold and best_sid is not None:
            return best_sid, best_score, best_meta
        else:
            return None, max(0.0, best_score), None
