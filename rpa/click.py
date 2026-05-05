"""OpenCV-backed click and wait helpers for Matrix Gold UI control.

`cv_click_with_retry` and `cv_wait_for` are the only primitives the build
sequences should use. Naked `pyautogui.click(coords)` is forbidden — Matrix's
panels move when its window is resized, themed, or scaled.
"""

import logging
import time
from pathlib import Path
from typing import Union

import pyautogui

log = logging.getLogger("rpa.click")

PathLike = Union[str, Path]


def cv_wait_for(
    icon_path: PathLike,
    timeout: float = 10.0,
    confidence: float = 0.92,
    poll_interval: float = 0.25,
):
    """Block until the icon is visible on screen, or raise TimeoutError."""
    deadline = time.monotonic() + timeout
    icon = str(icon_path)
    while time.monotonic() < deadline:
        try:
            box = pyautogui.locateOnScreen(icon, confidence=confidence)
        except pyautogui.ImageNotFoundException:
            box = None
        if box is not None:
            return box
        time.sleep(poll_interval)
    raise TimeoutError(f"icon never appeared: {icon_path}")


def cv_click_with_retry(
    icon_path: PathLike,
    timeout: float = 10.0,
    confidence: float = 0.92,
    settle_ms: int = 150,
):
    """Locate, click, and verify. Retries until timeout. Settle pause after click."""
    box = cv_wait_for(icon_path, timeout=timeout, confidence=confidence)
    center = pyautogui.center(box)
    pyautogui.click(center)
    time.sleep(settle_ms / 1000.0)
    log.info("clicked icon=%s at=%s", Path(icon_path).name, center)
    return center
