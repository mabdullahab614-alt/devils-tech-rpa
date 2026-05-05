"""Calibrate the OpenCV icon library — locate-only, NEVER clicks.

Run after icon harvest to verify every PNG in rpa/icons/ can be located on
the live Matrix Gold UI. Locating is read-only; this script will not move
or fire any UI actions.
"""

import time
from pathlib import Path

import pyautogui

ROOT = Path(__file__).resolve().parent
ICONS_DIR = ROOT / "icons"
CALIBRATION_CONFIDENCE = 0.85  # looser than production (0.92) to flag near-misses


def test_all_icons():
    print("Vision calibration starting. Bring Matrix Gold to the foreground (3s)...")
    time.sleep(3)

    icons = sorted(ICONS_DIR.glob("*.png"))
    if not icons:
        print(f"No icons found in {ICONS_DIR}. Harvest them first.")
        return

    success = 0
    for icon_path in icons:
        try:
            box = pyautogui.locateOnScreen(
                str(icon_path), confidence=CALIBRATION_CONFIDENCE
            )
        except pyautogui.ImageNotFoundException:
            box = None
        if box:
            print(f"[OK]   {icon_path.name}")
            success += 1
        else:
            print(f"[FAIL] {icon_path.name} — re-snip or lower confidence")

    print(f"\nCalibration: {success}/{len(icons)} icons verified.")


if __name__ == "__main__":
    test_all_icons()
