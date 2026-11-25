"""
Webcam Optical Perception Actions for Aether.ai.
Ported & adapted from J.A.R.V.I.S. (jarvis-main) vision.mjs / camera.ts

Captures a single optical frame from the webcam on-demand, encodes as base64 JPEG,
and immediately releases hardware resources to preserve user privacy.
"""

import base64
import time
from typing import Dict, Any

def capture_webcam_frame() -> Dict[str, Any]:
    """
    Captures one high-resolution frame from the default system webcam.
    Returns base64 JPEG data for multimodal LLM vision analysis.
    """
    try:
        import cv2
    except ImportError:
        return {"success": False, "error": "OpenCV (cv2) is not installed."}

    cap = None
    try:
        # Use DirectShow on Windows for zero-latency camera capture
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            # Fallback to default backend
            cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            return {"success": False, "error": "Webcam device 0 could not be opened or is busy."}

        # Allow auto-exposure & white balance to settle (skip first 2 dummy frames)
        for _ in range(3):
            cap.grab()
            time.sleep(0.04)

        ret, frame = cap.read()
        if not ret or frame is None:
            return {"success": False, "error": "Failed to read frame from webcam sensor."}

        height, width = frame.shape[:2]

        # Encode as JPEG
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
        success, buffer = cv2.imencode(".jpg", frame, encode_params)
        if not success:
            return {"success": False, "error": "Failed to encode webcam frame to JPEG."}

        b64_str = base64.b64encode(buffer).decode("utf-8")
        return {
            "success": True,
            "base64": b64_str,
            "mime_type": "image/jpeg",
            "width": width,
            "height": height
        }
    except Exception as e:
        return {"success": False, "error": f"Webcam optical capture error: {e}"}
    finally:
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass
