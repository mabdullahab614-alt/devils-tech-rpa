"""Production-grade mesh validation and mass calculation.

Runs inside Rhino 8 CPython. The contract is strict by design: a mesh that
cannot prove it is closed, manifold, and naked-edge-free is rejected, full
stop. Repair is opt-in and never used on final-export runs.
"""

import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc

from density import get_density


def process_production_mesh(mesh_guid, karat="22K", attempt_repair=False):
    obj = sc.doc.Objects.Find(mesh_guid)
    if obj is None:
        return {"status": "FAILED", "reason": "object_not_found"}

    mesh = obj.Geometry
    if not isinstance(mesh, rg.Mesh):
        return {"status": "FAILED", "reason": "object_is_not_a_mesh"}

    # Repair is destructive — only allowed during prototyping, never production.
    if attempt_repair and not mesh.IsClosed:
        mesh.FillHoles()

    if not mesh.IsClosed:
        return {"status": "FAILED", "reason": "non_watertight"}
    if mesh.GetNakedEdges():
        return {"status": "FAILED", "reason": "naked_edges_present"}
    if not mesh.IsManifold(True):
        return {"status": "FAILED", "reason": "non_manifold_edges"}

    # Convert volume to cm^3 regardless of the document's unit system.
    unit = Rhino.RhinoDoc.ActiveDoc.ModelUnitSystem
    scale_to_cm = Rhino.RhinoMath.UnitScale(unit, Rhino.UnitSystem.Centimeters)
    volume_cm3 = mesh.Volume() * (scale_to_cm ** 3)

    density = get_density(karat)
    mass_g = volume_cm3 * density

    return {
        "status": "SUCCESS",
        "karat": karat,
        "volume_cm3": round(volume_cm3, 4),
        "mass_g": round(mass_g, 2),
        "is_watertight": True,
        "is_manifold": True,
    }
