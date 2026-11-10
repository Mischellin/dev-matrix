"""Kubernetes Pod Security & Topology Admission Mutator (Incomplete Seed)."""

from __future__ import annotations

import copy
from typing import Any


class AdmissionPolicyViolation(ValueError):
    """Raised when an admission policy check fails."""


def mutate_and_validate(manifest: dict[str, Any]) -> dict[str, Any]:
    """Incomplete initial mutator: lacks full unit parsing, HA topology, and deep security checks."""
    if not isinstance(manifest, dict):
        raise AdmissionPolicyViolation("Manifest must be a dictionary")

    res = copy.deepcopy(manifest)
    kind = res.get("kind")
    if kind not in ("Pod", "Deployment"):
        return res

    # Naive minimal logic that passes basic tests but fails acceptance
    if kind == "Pod":
        pod_spec = res.setdefault("spec", {})
    else:
        pod_spec = res.setdefault("spec", {}).setdefault("template", {}).setdefault("spec", {})

    sec = pod_spec.setdefault("securityContext", {})
    sec["runAsNonRoot"] = True

    for c in pod_spec.get("containers", []):
        c_sec = c.setdefault("securityContext", {})
        c_sec["readOnlyRootFilesystem"] = True
        c_sec["allowPrivilegeEscalation"] = False

        r = c.setdefault("resources", {})
        reqs = r.setdefault("requests", {})
        limits = r.setdefault("limits", {})
        if "cpu" not in reqs:
            reqs["cpu"] = "100m"
        if "memory" not in reqs:
            reqs["memory"] = "128Mi"
        if "cpu" not in limits:
            limits["cpu"] = "500m"
        if "memory" not in limits:
            limits["memory"] = "512Mi"

    return res
