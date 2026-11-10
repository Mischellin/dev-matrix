from __future__ import annotations

import copy

import pytest
from k8s_admission.mutator import AdmissionPolicyViolation, mutate_and_validate


def test_reject_host_network() -> None:
    manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": "net-sniffer"},
        "spec": {
            "hostNetwork": True,
            "containers": [{"name": "app", "image": "busybox"}],
        },
    }
    with pytest.raises(AdmissionPolicyViolation, match="hostNetwork|prohibited|forbidden"):
        mutate_and_validate(manifest)


def test_reject_host_pid() -> None:
    manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": "proc-spy"},
        "spec": {
            "hostPID": True,
            "containers": [{"name": "app", "image": "busybox"}],
        },
    }
    with pytest.raises(AdmissionPolicyViolation, match="hostPID|prohibited|forbidden"):
        mutate_and_validate(manifest)


def test_reject_host_ipc() -> None:
    manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": "ipc-spy"},
        "spec": {
            "hostIPC": True,
            "containers": [{"name": "app", "image": "busybox"}],
        },
    }
    with pytest.raises(AdmissionPolicyViolation, match="hostIPC|prohibited|forbidden"):
        mutate_and_validate(manifest)


def test_reject_unsafe_host_path_root() -> None:
    manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": "root-escape"},
        "spec": {
            "volumes": [{"name": "root", "hostPath": {"path": "/"}}],
            "containers": [{"name": "app", "image": "busybox"}],
        },
    }
    with pytest.raises(AdmissionPolicyViolation, match="hostPath"):
        mutate_and_validate(manifest)


def test_reject_unsafe_host_path_docker_sock() -> None:
    manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": "sock-escape"},
        "spec": {
            "volumes": [{"name": "sock", "hostPath": {"path": "/var/run/docker.sock"}}],
            "containers": [{"name": "app", "image": "busybox"}],
        },
    }
    with pytest.raises(AdmissionPolicyViolation, match="hostPath"):
        mutate_and_validate(manifest)


def test_reject_unsafe_host_path_etc() -> None:
    manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": "etc-escape"},
        "spec": {
            "volumes": [{"name": "etc", "hostPath": {"path": "/etc/shadow"}}],
            "containers": [{"name": "app", "image": "busybox"}],
        },
    }
    with pytest.raises(AdmissionPolicyViolation, match="hostPath"):
        mutate_and_validate(manifest)


def test_allow_safe_host_path_custom_data() -> None:
    manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": "safe-pod"},
        "spec": {
            "volumes": [{"name": "data", "hostPath": {"path": "/mnt/storage/shared"}}],
            "containers": [{"name": "app", "image": "app:v1"}],
        },
    }
    res = mutate_and_validate(manifest)
    assert res["spec"]["volumes"][0]["hostPath"]["path"] == "/mnt/storage/shared"


def test_reject_root_uid_zero() -> None:
    manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": "root-pod"},
        "spec": {
            "securityContext": {"runAsUser": 0},
            "containers": [{"name": "app", "image": "app:v1"}],
        },
    }
    with pytest.raises(AdmissionPolicyViolation, match="Root user|UID 0"):
        mutate_and_validate(manifest)


def test_enforce_capabilities_drop_all() -> None:
    manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": "cap-pod"},
        "spec": {
            "containers": [{"name": "app", "image": "app:v1"}],
        },
    }
    res = mutate_and_validate(manifest)
    caps = res["spec"]["containers"][0]["securityContext"]["capabilities"]
    assert "ALL" in caps["drop"]


def test_enforce_read_only_root_filesystem_on_init_containers() -> None:
    manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": "init-pod"},
        "spec": {
            "initContainers": [{"name": "init-schema", "image": "migrate:v1"}],
            "containers": [{"name": "app", "image": "app:v1"}],
        },
    }
    res = mutate_and_validate(manifest)
    ic = res["spec"]["initContainers"][0]
    assert ic["securityContext"]["readOnlyRootFilesystem"] is True
    assert ic["resources"]["requests"]["cpu"] == "100m"
    assert "ALL" in ic["securityContext"]["capabilities"]["drop"]


def test_reject_cpu_limit_less_than_request() -> None:
    manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": "bad-cpu"},
        "spec": {
            "containers": [
                {
                    "name": "app",
                    "image": "app:v1",
                    "resources": {
                        "requests": {"cpu": "2000m"},
                        "limits": {"cpu": "1"},  # 1 core = 1000m < 2000m
                    },
                }
            ],
        },
    }
    with pytest.raises(AdmissionPolicyViolation, match="CPU limit"):
        mutate_and_validate(manifest)


def test_reject_memory_limit_less_than_request_binary_units() -> None:
    manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": "bad-mem"},
        "spec": {
            "containers": [
                {
                    "name": "app",
                    "image": "app:v1",
                    "resources": {
                        "requests": {"memory": "1Gi"},
                        "limits": {"memory": "512Mi"},  # 512Mi < 1Gi
                    },
                }
            ],
        },
    }
    with pytest.raises(AdmissionPolicyViolation, match="Memory limit"):
        mutate_and_validate(manifest)


def test_memory_unit_conversion_gi_vs_mi() -> None:
    manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": "good-mem"},
        "spec": {
            "containers": [
                {
                    "name": "app",
                    "image": "app:v1",
                    "resources": {
                        "requests": {"memory": "512Mi"},
                        "limits": {"memory": "1Gi"},  # 1Gi > 512Mi
                    },
                }
            ],
        },
    }
    res = mutate_and_validate(manifest)
    assert res["spec"]["containers"][0]["resources"]["limits"]["memory"] == "1Gi"


def test_inject_topology_spread_constraints_multi_replica_deployment() -> None:
    manifest = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "ha-service"},
        "spec": {
            "replicas": 3,
            "selector": {"matchLabels": {"app": "order-api", "tier": "backend"}},
            "template": {
                "metadata": {"labels": {"app": "order-api", "tier": "backend"}},
                "spec": {
                    "containers": [{"name": "api", "image": "order:v2"}],
                },
            },
        },
    }
    res = mutate_and_validate(manifest)
    pod_spec = res["spec"]["template"]["spec"]
    assert "topologySpreadConstraints" in pod_spec
    tsc = pod_spec["topologySpreadConstraints"][0]
    assert tsc["maxSkew"] == 1
    assert tsc["topologyKey"] == "topology.kubernetes.io/zone"
    assert tsc["whenUnsatisfiable"] == "DoNotSchedule"
    assert tsc["labelSelector"]["matchLabels"] == {"app": "order-api", "tier": "backend"}


def test_do_not_duplicate_existing_topology_spread_constraint() -> None:
    custom_tsc = {
        "maxSkew": 2,
        "topologyKey": "topology.kubernetes.io/zone",
        "whenUnsatisfiable": "ScheduleAnyway",
        "labelSelector": {"matchLabels": {"app": "order-api"}},
    }
    manifest = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "custom-ha-service"},
        "spec": {
            "replicas": 2,
            "selector": {"matchLabels": {"app": "order-api"}},
            "template": {
                "metadata": {"labels": {"app": "order-api"}},
                "spec": {
                    "topologySpreadConstraints": [copy.deepcopy(custom_tsc)],
                    "containers": [{"name": "api", "image": "order:v2"}],
                },
            },
        },
    }
    res = mutate_and_validate(manifest)
    pod_spec = res["spec"]["template"]["spec"]
    assert len(pod_spec["topologySpreadConstraints"]) == 1
    assert pod_spec["topologySpreadConstraints"][0]["maxSkew"] == 2


def test_admitted_annotation_injected_at_root_and_pod_template() -> None:
    manifest = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "annotated-deploy"},
        "spec": {
            "replicas": 1,
            "selector": {"matchLabels": {"app": "demo"}},
            "template": {
                "metadata": {"labels": {"app": "demo"}},
                "spec": {
                    "containers": [{"name": "demo", "image": "demo:v1"}],
                },
            },
        },
    }
    res = mutate_and_validate(manifest)
    assert res["metadata"]["annotations"]["policy.dev-matrix.io/admitted"] == "true"
    assert (
        res["spec"]["template"]["metadata"]["annotations"]["policy.dev-matrix.io/admitted"]
        == "true"
    )
