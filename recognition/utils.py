import shutil
from pathlib import Path
import cv2

# ASCII-safe directory in user home directory to prevent OpenCV C++ Unicode path bugs on Windows
SAFE_ROOT = Path.home() / ".smart_attendance"
SAFE_ROOT.mkdir(parents=True, exist_ok=True)

def get_safe_model_path(filename: str, source_dir: Path) -> Path:
    """
    Copies a model file from a source directory into an ASCII-safe user path
    if it does not already exist, and returns the safe path.
    """
    models_dir = SAFE_ROOT / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    target_file = models_dir / filename

    if target_file.exists() and target_file.stat().st_size > 1000:
        return target_file

    src_file = source_dir / filename
    if src_file.exists() and src_file.stat().st_size > 1000:
        try:
            shutil.copyfile(src_file, target_file)
            return target_file
        except Exception:
            return src_file

    return target_file

def get_safe_cascade_path(xml_filename: str) -> Path:
    """
    Copies OpenCV cascade XML files to an ASCII-safe directory to ensure
    cv2.CascadeClassifier can load it on Windows machines where OneDrive
    or user folders have Unicode/non-ASCII characters.
    """
    cascades_dir = SAFE_ROOT / "cascades"
    cascades_dir.mkdir(parents=True, exist_ok=True)
    target_file = cascades_dir / xml_filename

    if target_file.exists() and target_file.stat().st_size > 100:
        return target_file

    try:
        src_path = Path(cv2.data.haarcascades) / xml_filename
        if src_path.exists():
            shutil.copyfile(src_path, target_file)
            return target_file
    except Exception:
        pass

    return target_file
