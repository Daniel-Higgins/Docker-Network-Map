from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import docker
from docker.errors import DockerException


@dataclass(frozen=True)
class GraphNode:
    id: str
    label: str
    type: str
    status: str | None = None
    image: str | None = None
    driver: str | None = None
    ip: str | None = None
    ports: list[str] | None = None
    volumes: list[str] = field(default_factory=list)
    networks: list[str] = field(default_factory=list)
    network_count: int = 0
    member_count: int = 0
    classes: str = ""


@dataclass(frozen=True)
class GraphEdge:
    source: str
    target: str
    label: str | None = None
    type: str = "membership"


def _short_id(container_id: str) -> str:
    return container_id[:12]


def _container_display_name(container: Any) -> str:
    name = getattr(container, "name", None)
    if name:
        return name
    return _short_id(container.id)


def _image_name(container: Any) -> str:
    try:
        tags = container.image.tags
        if tags:
            return tags[0]
    except Exception:
        pass
    return container.attrs.get("Config", {}).get("Image", "unknown")


def _container_volumes(container: Any) -> list[str]:
    mounts = container.attrs.get("Mounts") or []
    result: list[str] = []

    for mount in mounts:
        mount_type = mount.get("Type", "unknown")
        source = mount.get("Source") or mount.get("Name") or "unknown"
        destination = mount.get("Destination") or "unknown"
        read_write = "rw" if mount.get("RW", False) else "ro"

        result.append(f"{mount_type}: {source} -> {destination} ({read_write})")

    return sorted(result)


def _published_ports(container: Any) -> list[str]:
    ports = container.attrs.get("NetworkSettings", {}).get("Ports") or {}
    result: list[str] = []

    for container_port, bindings in ports.items():
        if not bindings:
            continue

        for binding in bindings:
            host_ip = binding.get("HostIp", "0.0.0.0")
            host_port = binding.get("HostPort", "")
            result.append(f"{host_ip}:{host_port} -> {container_port}")

    return sorted(result)


def _container_networks(container: Any) -> dict[str, dict[str, Any]]:
    return container.attrs.get("NetworkSettings", {}).get("Networks") or {}


def _container_ip_map(container: Any) -> dict[str, str]:
    result: dict[str, str] = {}
    for network_name, endpoint in _container_networks(container).items():
        ip = (endpoint.get("IPAddress") or "").strip()
        if ip:
            result[network_name] = ip
    return result


def build_docker_graph(include_stopped: bool = True) -> dict[str, Any]:
    """
    Build a Docker network graph from the local Docker daemon.

    Shape:
    {
      "nodes": [{...}],
      "edges": [{...}],
      "summary": {...}
    }
    """
    try:
        client = docker.from_env()
        client.ping()
    except DockerException as exc:
        return {
            "nodes": [],
            "edges": [],
            "summary": {
                "error": f"Could not connect to Docker daemon: {exc}",
                "containers": 0,
                "networks": 0,
                "published_ports": 0,
                "multi_network_containers": 0,
            },
        }

    containers = client.containers.list(all=include_stopped)
    networks = client.networks.list()

    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []

    container_by_id: dict[str, Any] = {}
    container_node_ids: list[str] = []
    container_network_names: dict[str, set[str]] = {}
    container_network_ips: dict[str, dict[str, str]] = {}
    network_member_count: dict[str, int] = {}

    for container in containers:
        container.reload()
        node_id = f"container:{container.id}"
        container_by_id[container.id] = container
        container_node_ids.append(node_id)

        network_names = set(_container_networks(container).keys())
        ip_map = _container_ip_map(container)
        container_network_names[node_id] = network_names
        container_network_ips[node_id] = ip_map

        network_count = len(network_names)
        classes = []
        if network_count > 1:
            classes.append("multi-network")

        display_label = _container_display_name(container)
        if network_count > 1:
            display_label = f"{display_label}\n({network_count} nets)"

        nodes[node_id] = GraphNode(
            id=node_id,
            label=display_label,
            type="container",
            status=container.status,
            image=_image_name(container),
            ip=", ".join(ip_map.values()) if ip_map else None,
            ports=_published_ports(container),
            networks=sorted(network_names),
            network_count=network_count,
            classes=" ".join(classes),
            volumes=_container_volumes(container),
        )

    for network in networks:
        network.reload()
        attrs = network.attrs
        net_id = f"network:{network.id}"
        attached = attrs.get("Containers") or {}
        member_count = len(attached)
        network_member_count[net_id] = member_count

        classes = []
        if member_count == 0:
            classes.append("unused-network")

        nodes[net_id] = GraphNode(
            id=net_id,
            label=attrs.get("Name", network.name),
            type="network",
            driver=attrs.get("Driver", "unknown"),
            member_count=member_count,
            classes=" ".join(classes),
        )

        for container_id, endpoint in attached.items():
            full_id = None
            for known_id in container_by_id:
                if known_id.startswith(container_id) or container_id.startswith(
                    known_id
                ):
                    full_id = known_id
                    break

            if full_id is None:
                full_id = container_id
                c_node_id = f"container:{container_id}"
                if c_node_id not in nodes:
                    nodes[c_node_id] = GraphNode(
                        id=c_node_id,
                        label=_short_id(container_id),
                        type="container",
                        status="unknown",
                        image="unknown",
                        ports=[],
                        network_count=0,
                        classes="",
                    )
            else:
                c_node_id = f"container:{full_id}"

            ip = endpoint.get("IPv4Address", "").split("/")[0]
            edges.append(
                GraphEdge(
                    source=c_node_id, target=net_id, label=ip or None, type="membership"
                )
            )

    # Container-to-container reachability edges.
    # If two containers share at least one network, they can normally talk to each other by name/IP on that network.
    # These are dashed helper edges in the UI.
    seen_pairs: set[tuple[str, str]] = set()
    for idx, source_id in enumerate(container_node_ids):
        for target_id in container_node_ids[idx + 1 :]:
            shared_networks = sorted(
                container_network_names.get(source_id, set())
                & container_network_names.get(target_id, set())
            )
            if not shared_networks:
                continue

            pair = tuple(sorted((source_id, target_id)))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            label = ", ".join(shared_networks[:2])
            if len(shared_networks) > 2:
                label += f" +{len(shared_networks) - 2}"

            edges.append(
                GraphEdge(
                    source=source_id,
                    target=target_id,
                    label=label,
                    type="container-link",
                )
            )

    serialized_nodes = [node.__dict__ for node in nodes.values()]
    serialized_edges = [edge.__dict__ for edge in edges]
    published_port_count = sum(
        len(n.ports or []) for n in nodes.values() if n.type == "container"
    )

    return {
        "nodes": serialized_nodes,
        "edges": serialized_edges,
        "summary": {
            "containers": sum(1 for n in nodes.values() if n.type == "container"),
            "networks": sum(1 for n in nodes.values() if n.type == "network"),
            "published_ports": published_port_count,
            "multi_network_containers": sum(
                1
                for n in nodes.values()
                if n.type == "container" and n.network_count > 1
            ),
        },
    }
