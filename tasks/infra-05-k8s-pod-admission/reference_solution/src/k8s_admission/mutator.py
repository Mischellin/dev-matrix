"""Kubernetes Pod Security & Topology Admission Mutator (Reference Solution)."""

from __future__ import annotations

import copy
import posixpath
import re
from typing import Any

DEFAULT_CPU_REQUEST = "100m"
DEFAULT_MEM_REQUEST = "128Mi"
DEFAULT_CPU_LIMIT = "500m"
DEFAULT_MEM_LIMIT = "512Mi"

FORBIDDEN_HOST_PREFIXES = (
    "/",
    "/etc",
    "/proc",
    "/sys",
    "/var/run",
    "/var/run/docker.sock",
)

MEMORY_BINARY_MULTIPLIERS = {
    "Ki": 1024,
    "Mi": 1024**2,
    "Gi": 1024**3,
    "Ti": 1024**4,
}

MEMORY_DECIMAL_MULTIPLIERS = {
    "k": 1000,
    "K": 1000,
    "M": 1000**2,
    "G": 1000**3,
    "T": 1000**4,
}


class AdmissionPolicyViolation(ValueError):
    """Raised when an admission policy check fails."""


def parse_cpu_millicores(val: str | float) -> int:
    """Parse CPU resource string or number into integer millicores."""
    if isinstance(val, (int, float)):
        res = int(float(val) * 1000)
    elif isinstance(val, str):
        v = val.strip()
        if v.endswith("m"):
            try:
                res = int(v[:-1])
            except ValueError as err:
                raise AdmissionPolicyViolation(
                    f"Invalid CPU millicores specification: {val}"
                ) from err
        else:
            try:
                res = int(float(v) * 1000)
            except ValueError as err:
                raise AdmissionPolicyViolation(f"Invalid CPU specification: {val}") from err
    else:
        raise AdmissionPolicyViolation(f"Unsupported CPU type: {type(val)}")

    if res <= 0:
        raise AdmissionPolicyViolation(f"CPU request/limit must be positive, got: {val}")
    return res


def parse_memory_bytes(val: str | int) -> int:
    """Parse memory string into integer bytes."""
    if isinstance(val, int):
        res = val
    elif isinstance(val, str):
        v = val.strip()
        m = re.match(r"^(\d+(?:\.\d+)?)\s*([a-zA-Z]+)?$", v)
        if not m:
            raise AdmissionPolicyViolation(f"Invalid memory specification: {val}")
        num_str, unit = m.group(1), m.group(2)
        num = float(num_str)
        if unit is None:
            res = int(num)
        elif unit in MEMORY_BINARY_MULTIPLIERS:
            res = int(num * MEMORY_BINARY_MULTIPLIERS[unit])
        elif unit in MEMORY_DECIMAL_MULTIPLIERS:
            res = int(num * MEMORY_DECIMAL_MULTIPLIERS[unit])
        else:
            raise AdmissionPolicyViolation(f"Unknown memory unit: {unit} in {val}")
    else:
        raise AdmissionPolicyViolation(f"Unsupported memory type: {type(val)}")

    if res <= 0:
        raise AdmissionPolicyViolation(f"Memory request/limit must be positive, got: {val}")
    return res


def _normalize_host_path(path: str) -> str:
    cleaned = re.sub(r"/+", "/", path.strip())
    # Схлопываем «..» и «.», иначе /tmp/../etc обходит запрет.
    return posixpath.normpath(cleaned) if cleaned else cleaned


def _validate_and_mutate_container(c: dict[str, Any]) -> None:
    if not isinstance(c, dict):
        raise AdmissionPolicyViolation("Container definition must be a dictionary")
    if not c.get("name") or not c.get("image"):
        raise AdmissionPolicyViolation("Container must have name and image")

    # Security Context
    c_sec = c.setdefault("securityContext", {})
    c_sec["readOnlyRootFilesystem"] = True
    c_sec["allowPrivilegeEscalation"] = False

    caps = c_sec.setdefault("capabilities", {})
    drop_list = caps.setdefault("drop", [])
    if "ALL" not in drop_list:
        drop_list.append("ALL")

    # Resources
    r = c.setdefault("resources", {})
    reqs = r.setdefault("requests", {})
    limits = r.setdefault("limits", {})

    if "cpu" not in reqs:
        reqs["cpu"] = DEFAULT_CPU_REQUEST
    if "memory" not in reqs:
        reqs["memory"] = DEFAULT_MEM_REQUEST
    if "cpu" not in limits:
        limits["cpu"] = DEFAULT_CPU_LIMIT
    if "memory" not in limits:
        limits["memory"] = DEFAULT_MEM_LIMIT

    # Validate limits >= requests
    req_cpu = parse_cpu_millicores(reqs["cpu"])
    lim_cpu = parse_cpu_millicores(limits["cpu"])
    if lim_cpu < req_cpu:
        raise AdmissionPolicyViolation(
            f"CPU limit ({limits['cpu']}) cannot be less than request ({reqs['cpu']})"
        )

    req_mem = parse_memory_bytes(reqs["memory"])
    lim_mem = parse_memory_bytes(limits["memory"])
    if lim_mem < req_mem:
        raise AdmissionPolicyViolation(
            f"Memory limit ({limits['memory']}) cannot be less than request ({reqs['memory']})"
        )


def _check_host_namespaces(pod_spec: dict[str, Any]) -> None:
    for ns in ("hostNetwork", "hostPID", "hostIPC"):
        if pod_spec.get(ns) is True:
            raise AdmissionPolicyViolation(f"Host namespace '{ns}' is strictly prohibited")


def _check_volumes(pod_spec: dict[str, Any]) -> None:
    for vol in pod_spec.get("volumes", []):
        if not isinstance(vol, dict):
            continue
        hp = vol.get("hostPath")
        if hp and isinstance(hp, dict):
            raw_path = hp.get("path", "")
            norm = _normalize_host_path(raw_path)
            if norm == "/" or norm in FORBIDDEN_HOST_PREFIXES:
                raise AdmissionPolicyViolation(f"Unsafe hostPath mount prohibited: {norm}")
            for prefix in ("/etc", "/proc", "/sys", "/var/run"):
                if norm == prefix or norm.startswith(prefix + "/"):
                    raise AdmissionPolicyViolation(f"Unsafe hostPath mount prohibited: {norm}")


def _mutate_pod_spec(pod_spec: dict[str, Any]) -> None:
    _check_host_namespaces(pod_spec)
    _check_volumes(pod_spec)

    pod_sec = pod_spec.setdefault("securityContext", {})
    if pod_sec.get("runAsUser") == 0:
        raise AdmissionPolicyViolation("Root user (UID 0) is forbidden in securityContext")
    pod_sec["runAsNonRoot"] = True

    containers = pod_spec.get("containers", [])
    if not containers:
        raise AdmissionPolicyViolation("Pod specification must include at least one container")

    for c in containers:
        _validate_and_mutate_container(c)

    for ic in pod_spec.get("initContainers", []):
        _validate_and_mutate_container(ic)


def mutate_and_validate(manifest: dict[str, Any]) -> dict[str, Any]:
    """Mutate and enforce production security and HA topology policies on K8s manifests."""
    if not isinstance(manifest, dict):
        raise AdmissionPolicyViolation("Manifest must be a dictionary")

    res = copy.deepcopy(manifest)
    kind = res.get("kind")
    if kind not in ("Pod", "Deployment"):
        return res

    if "apiVersion" not in res or "metadata" not in res:
        raise AdmissionPolicyViolation("Manifest must contain 'apiVersion' and 'metadata'")

    # Annotate top-level metadata
    res.setdefault("metadata", {}).setdefault("annotations", {})[
        "policy.dev-matrix.io/admitted"
    ] = "true"

    if kind == "Pod":
        pod_spec = res.setdefault("spec", {})
        _mutate_pod_spec(pod_spec)
    elif kind == "Deployment":
        spec = res.setdefault("spec", {})
        template = spec.setdefault("template", {})
        template.setdefault("metadata", {}).setdefault("annotations", {})[
            "policy.dev-matrix.io/admitted"
        ] = "true"
        pod_spec = template.setdefault("spec", {})
        _mutate_pod_spec(pod_spec)

        replicas = spec.get("replicas", 1)
        if isinstance(replicas, int) and replicas >= 2:
            tsc_list = pod_spec.setdefault("topologySpreadConstraints", [])
            has_zone_spread = any(
                isinstance(tsc, dict) and tsc.get("topologyKey") == "topology.kubernetes.io/zone"
                for tsc in tsc_list
            )
            if not has_zone_spread:
                match_labels = spec.get("selector", {}).get("matchLabels", {})
                tsc_list.append(
                    {
                        "maxSkew": 1,
                        "topologyKey": "topology.kubernetes.io/zone",
                        "whenUnsatisfiable": "DoNotSchedule",
                        "labelSelector": {"matchLabels": copy.deepcopy(match_labels)},
                    }
                )

    return res
