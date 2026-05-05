"""Capture the GUID of the newly-committed Matrix mesh.

Runs INSIDE Rhino 8's embedded Python — cwd is Rhino's, not the project root.
All paths are resolved relative to this file.
"""

import os

import Rhino
import scriptcontext as sc

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
JOBS_DIR = os.path.join(ROOT, "khep_outputs", "jobs")


def _all_meshes():
    settings = Rhino.DocObjects.ObjectEnumeratorSettings()
    settings.ObjectTypeFilter = Rhino.DocObjects.ObjectType.Mesh
    settings.NormalObjects = True
    settings.LockedObjects = False
    return sc.doc.Objects.FindByFilter(settings)


def commit_and_capture_new_mesh(job_id):
    before = {o.Id for o in _all_meshes()}

    # NOTE: '_-Mesh' is a placeholder. Replace with Matrix's actual
    # history-commit command after Arham confirms it from a live session.
    Rhino.RhinoApp.RunScript("_-Mesh _Enter", False)

    after = {o.Id for o in _all_meshes()}
    new = after - before

    if len(new) != 1:
        raise RuntimeError(
            "expected 1 new mesh, got {}. History commit failed or "
            "produced multiple objects.".format(len(new))
        )

    guid = next(iter(new))

    os.makedirs(JOBS_DIR, exist_ok=True)
    sidecar = os.path.join(JOBS_DIR, "{}.guid".format(job_id))
    with open(sidecar, "w") as f:
        f.write(str(guid))

    return str(guid)
