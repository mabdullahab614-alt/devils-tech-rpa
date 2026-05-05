"""Matrix Gold RPA build sequences for Mala designs.

Hybrid split (locked): Rhino-Python opens templates and reads geometry;
PyAutoGUI + OpenCV ONLY for Matrix-specific builder panels with no script
surface. Anything that can be deterministic via Rhino-Python must be.
"""

import logging
import time
from pathlib import Path

import pyautogui

from rpa.click import cv_click_with_retry, cv_wait_for

log = logging.getLogger("rpa.build_mala")

ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = ROOT / "rhino_worker" / "templates"
ICONS = ROOT / "rpa" / "icons"

# Order in which Matrix's "Finish" dropdown lists the chandak finishes.
# UPDATE if Matrix changes the option order.
CHANDAK_FINISH_INDEX = {
    "smooth": 0,
    "granulated": 1,
    "engraved": 2,
    "filigreed": 3,
}


def _open_template_via_rhino(template_filename: str) -> None:
    """Open template via Rhino's _-Open command, not the OS file dialog."""
    abs_path = (TEMPLATES_DIR / template_filename).resolve()
    if not abs_path.exists():
        raise FileNotFoundError(f"template not found: {abs_path}")

    cv_wait_for(ICONS / "rhino_command_prompt.png", timeout=10)
    pyautogui.typewrite(f'_-Open "{abs_path}"', interval=0.01)
    pyautogui.press("enter")
    cv_wait_for(ICONS / "matrix_history_panel.png", timeout=20)
    log.info("template_opened path=%s", abs_path)


def _set_dropdown_by_index(icon_path: Path, index: int) -> None:
    cv_click_with_retry(icon_path)
    pyautogui.press("home")
    if index > 0:
        pyautogui.press("down", presses=index)
    pyautogui.press("enter")


def _replace_input(field_icon: Path, value) -> None:
    cv_click_with_retry(field_icon)
    pyautogui.hotkey("ctrl", "a")
    pyautogui.press("delete")
    pyautogui.typewrite(str(value))
    pyautogui.press("tab")


def set_chandak(count: int, diameter_mm: float, finish: str) -> None:
    cv_click_with_retry(ICONS / "builder_chandak.png")
    cv_wait_for(ICONS / "panel_chandak_open.png", timeout=5)
    _replace_input(ICONS / "input_count.png", count)
    _replace_input(ICONS / "input_diameter.png", diameter_mm)
    _set_dropdown_by_index(ICONS / "dropdown_finish.png", CHANDAK_FINISH_INDEX[finish])
    cv_click_with_retry(ICONS / "panel_apply.png")
    log.info("chandak_set count=%s dia=%s finish=%s", count, diameter_mm, finish)


def set_paroi(style: str, wire_gauge_mm: float) -> None:
    raise NotImplementedError("blocked: requires icon harvest from Matrix Paroi builder")


def set_latkan(count: int, motif: str, treatment: str,
               length_mm: float, min_thickness_mm: float) -> None:
    raise NotImplementedError("blocked: requires icon harvest from Matrix Latkan placer")


def set_filigree(density_pct: int, tier_ref: str) -> None:
    raise NotImplementedError("blocked: requires icon harvest from Matrix Filigree tool")


def _commit_and_get_mesh_guid() -> str:
    """Commit Matrix history → final mesh, return its GUID.

    Implementation note: PyAutoGUI cannot read a Rhino object GUID from screen.
    The clean path is a tiny Rhino-Python sidecar (rhino_worker/commit_helper.py)
    that runs `_-Mesh` on the active history result and writes the new mesh's
    GUID to khep_outputs/jobs/<job_id>.guid. We then read that file here.

    Blocked until that helper is written (next session, alongside icon harvest).
    """
    raise NotImplementedError(
        "blocked: needs rhino_worker/commit_helper.py to export the committed "
        "mesh GUID to a sidecar file we can read"
    )


def build_mala(payload: dict) -> str:
    log.info("build_started job_id=%s template=%s",
             payload["job_id"], payload["base_template"])
    _open_template_via_rhino(payload["base_template"])

    p = payload["parameters"]
    set_chandak(**p["chandak"])
    set_paroi(**p["paroi"])
    set_latkan(**p["latkan"])
    set_filigree(**p["filigree"])

    return _commit_and_get_mesh_guid()
