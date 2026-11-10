from __future__ import annotations

import pytest
from k8s_admission.mutator import AdmissionPolicyViolation, mutate_and_validate


def test_basic_pod_defaults_injected() -> None:
    raw = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": "frontend"},
        "spec": {
            "containers": [
                {"name": "web", "image": "nginx:1.27"},
            ],
        },
    }
    mutated = mutate_and_validate(raw)
    assert mutated["kind"] == "Pod"
    spec = mutated["spec"]
    assert spec["securityContext"]["runAsNonRoot"] is True
    container = spec["containers"][0]
    assert container["securityContext"]["readOnlyRootFilesystem"] is True
    assert container["resources"]["requests"]["cpu"] == "100m"
    assert container["resources"]["limits"]["memory"] == "512Mi"


def test_basic_deployment_defaults_injected() -> None:
    raw = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "api-service"},
        "spec": {
            "replicas": 1,
            "selector": {"matchLabels": {"app": "api"}},
            "template": {
                "metadata": {"labels": {"app": "api"}},
                "spec": {
                    "containers": [
                        {"name": "api", "image": "api:v1.0"},
                    ],
                },
            },
        },
    }
    mutated = mutate_and_validate(raw)
    c = mutated["spec"]["template"]["spec"]["containers"][0]
    assert c["resources"]["requests"]["memory"] == "128Mi"
    assert c["securityContext"]["allowPrivilegeEscalation"] is False


def test_non_pod_resource_unmodified() -> None:
    svc = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {"name": "db-service"},
        "spec": {"ports": [{"port": 5432}]},
    }
    res = mutate_and_validate(svc)
    assert res == svc
    assert res is not svc


def test_reject_non_dict_manifest() -> None:
    with pytest.raises(AdmissionPolicyViolation, match="dictionary"):
        mutate_and_validate("not-a-dict")  # type: ignore[arg-type]
