"""Passive liveness detection (S1).

Heuristic anti-spoof check that runs without user interaction (no blink/turn
head prompts). It analyses the cropped face image for artifacts typical of a
photo-of-a-photo or screen-capture attack:

  * Low-frequency moire / screen pixel grid (high-frequency energy in flat areas)
  * Unnatural colour uniformity (print media lacks skin-tone micro-variation)
  * Strong glass reflections / uniform backlight glow
  * Excessive blur from re-photographing a display

Returns (is_live: bool, score: float, reason: str).
A score >= 0.5 is considered live. Below 0.5 suggests a spoof attempt.
"""
from __future__ import annotations

import cv2
import numpy as np


def _laplacian_variance(gray: np.ndarray) -> float:
    """Blur measure: sharp faces have high Laplacian variance."""
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _screen_grid_score(gray: np.ndarray) -> float:
    """Detect moire/pixel grid from photographing a screen.

    Screen pixels create regular high-frequency patterns in otherwise flat
    regions. We look at the high-frequency energy after a light blur.
    """
    blurred = cv2.GaussianBlur(gray, (0, 0), 3)
    high_freq = cv2.subtract(gray, blurred)
    # Energy in the mid-high frequency band where screen grid lives
    hf_energy = float(np.mean(high_freq ** 2))
    # Normalise by overall contrast so low-contrast images don't false-positive
    contrast = float(np.std(gray)) + 1e-6
    return hf_energy / (contrast * contrast + 1e-6)


def _colour_variance_score(bgr: np.ndarray) -> float:
    """Real skin has micro-variation in colour; print/screens are flatter."""
    # Work in a small central region (avoid edges / background)
    h, w = bgr.shape[:2]
    crop = bgr[int(h * 0.3):int(h * 0.7), int(w * 0.3):int(w * 0.7)]
    if crop.size == 0:
        crop = bgr
    # Per-channel std in the central face region
    std_b = float(np.std(crop[:, :, 0]))
    std_g = float(np.std(crop[:, :, 1]))
    std_r = float(np.std(crop[:, :, 2]))
    # Combined colour variation score
    return float((std_b + std_g + std_r) / 3.0)


def _reflection_score(bgr: np.ndarray) -> float:
    """Strong uniform backlight or glass reflections suggest a screen/photo."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    # Count near-white pixels (specular reflections)
    bright = float(np.sum(gray > 240)) / max(gray.size, 1)
    return bright


def assess_liveness(face_bgr: np.ndarray) -> tuple[bool, float, str]:
    """Passive liveness assessment.

    Returns (is_live, score, reason). score >= 0.5 => likely live.
    """
    if face_bgr.size == 0:
        return False, 0.0, "empty_face_crop"

    gray = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY)

    blur = _laplacian_variance(gray)
    screen = _screen_grid_score(gray)
    colour_var = _colour_variance_score(face_bgr)
    reflection = _reflection_score(face_bgr)

    # Normalise blur (0-1): very sharp > 100, very blurry < 10
    blur_score = min(blur / 200.0, 1.0)
    # Screen grid: low is good (< 0.02), high suggests screen
    screen_score = max(0.0, 1.0 - min(screen * 50.0, 1.0))
    # Colour variation: higher is better (real skin varies)
    colour_score = min(colour_var / 30.0, 1.0)
    # Reflection: lower is better
    reflection_score = max(0.0, 1.0 - min(reflection * 10.0, 1.0))

    # Weighted combination
    score = (
        0.20 * blur_score +
        0.35 * screen_score +
        0.20 * colour_score +
        0.25 * reflection_score
    )

    reasons = []
    if blur_score < 0.3:
        reasons.append("blurry")
    if screen_score < 0.4:
        reasons.append("screen_pattern")
    if colour_score < 0.3:
        reasons.append("flat_colour")
    if reflection_score < 0.4:
        reasons.append("reflection")

    reason = "; ".join(reasons) if reasons else "ok"
    is_live = score >= 0.5
    return is_live, round(score, 3), reason
