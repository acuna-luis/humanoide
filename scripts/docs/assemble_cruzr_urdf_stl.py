#!/usr/bin/env python3
"""Assemble URDF visual meshes at q=0 into one binary STL, in millimetres.

Offline visualization only: q=0 does not certify physical HOME, tool identity,
dimensions, watertightness, collision clearance, or suitability for engineering.
Only NumPy and the Python standard library are used; no vendor code is loaded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import xml.etree.ElementTree as ET

import numpy as np


FACET = np.dtype([
    ("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attribute", "<u2"),
])
HEADER = b"URDF visual assembly; all joints q=0; units mm; visualization only".ljust(80, b" ")
NOTICE = "Visualization at URDF q=0; not physical HOME or an engineering model."


def vector(raw: str | None, default=(0.0, 0.0, 0.0)) -> np.ndarray:
    value = np.asarray(default if raw is None else [float(x) for x in raw.split()], dtype=float)
    if value.shape != (3,) or not np.isfinite(value).all():
        raise ValueError(f"Expected a finite 3-vector: {raw!r}")
    return value


def one(parent: ET.Element, tag: str, required=False) -> ET.Element | None:
    values = parent.findall(tag)
    if len(values) > 1 or (required and len(values) != 1):
        raise ValueError(f"Expected {'exactly one' if required else 'at most one'} <{tag}>")
    return values[0] if values else None


def origin(element: ET.Element | None) -> np.ndarray:
    result = np.eye(4)
    if element is None:
        return result
    roll, pitch, yaw = vector(element.get("rpy"))
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    # URDF fixed-axis roll/pitch/yaw: Rz(yaw) @ Ry(pitch) @ Rx(roll).
    result[:3, :3] = [
        [cy*cp, cy*sp*sr-sy*cr, cy*sp*cr+sy*sr],
        [sy*cp, sy*sp*sr+cy*cr, sy*sp*cr-cy*sr],
        [-sp, cp*sr, cp*cr],
    ]
    result[:3, 3] = vector(element.get("xyz"))
    return result


def contained(root: Path, candidate: Path) -> Path:
    path = candidate.resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f"Referenced file must be inside the package: {candidate}")
    return path


def read_xml(path: Path, inputs: dict[str, str], root: Path) -> ET.Element:
    raw = path.read_bytes()
    if b"<!DOCTYPE" in raw or b"<!ENTITY" in raw:
        raise ValueError(f"XML declarations/entities are not supported: {path}")
    inputs[path.relative_to(root).as_posix()] = hashlib.sha256(raw).hexdigest()
    return ET.fromstring(raw)


def mesh_path(filename: str, root: Path, urdf: Path, package: str) -> Path:
    if not filename or "\\" in filename or "\x00" in filename:
        raise ValueError(f"Invalid mesh reference: {filename!r}")
    if filename.startswith("package://"):
        prefix = "package://" + package + "/"
        if not filename.startswith(prefix):
            raise ValueError(f"Mesh refers to another package: {filename}")
        relative = Path(filename[len(prefix):])
        candidate = root / relative
    else:
        if ":" in filename or filename.startswith("/"):
            raise ValueError(f"Only package:// or relative mesh paths are supported: {filename}")
        candidate = urdf.parent / filename
    path = contained(root, candidate)
    if path.suffix.lower() != ".stl":
        raise ValueError(f"Only STL visual meshes are supported: {filename}")
    return path


def tree(robot: ET.Element) -> tuple[dict[str, ET.Element], dict[str, np.ndarray], str]:
    if robot.tag != "robot":
        raise ValueError("Expected a complete <robot> URDF")
    links = {}
    for link in robot.findall("link"):
        name = link.get("name", "")
        if not name or name.strip() != name or name in links:
            raise ValueError(f"Missing or duplicate link name: {name!r}")
        links[name] = link
    if not links:
        raise ValueError("URDF has no links")
    children: dict[str, list[tuple[str, np.ndarray]]] = {name: [] for name in links}
    attached, joints = set(), set()
    for joint in robot.findall("joint"):
        name = joint.get("name", "")
        if not name or name.strip() != name or name in joints:
            raise ValueError(f"Missing or duplicate joint name: {name!r}")
        joints.add(name)
        kind = joint.get("type")
        if kind not in {"fixed", "revolute", "continuous", "prismatic"}:
            raise ValueError(f"Unsupported joint type {kind!r}: {name}")
        if one(joint, "mimic") is not None:
            raise ValueError(f"Mimic joints need an explicit pose policy: {name}")
        parent = one(joint, "parent", required=True).get("link")
        child = one(joint, "child", required=True).get("link")
        if parent not in links or child not in links or child == parent:
            raise ValueError(f"Invalid joint link reference: {name}")
        if child in attached:
            raise ValueError(f"Link has multiple parents: {child}")
        attached.add(child)
        axis = one(joint, "axis")
        if kind != "fixed":
            value = vector(axis.get("xyz") if axis is not None else None, (1, 0, 0))
            if not np.any(value):
                raise ValueError(f"Zero joint axis: {name}")
        # Revolute/continuous rotation and prismatic displacement are identity at q=0.
        children[parent].append((child, origin(one(joint, "origin"))))
    roots = set(links) - attached
    if len(roots) != 1:
        raise ValueError(f"Expected one root link, found: {sorted(roots)}")
    base = next(iter(roots))
    poses = {base: np.eye(4)}
    pending = [base]
    while pending:
        parent = pending.pop()
        for child, local in children[parent]:
            if child in poses:
                raise ValueError(f"Cycle in URDF tree at {child}")
            poses[child] = poses[parent] @ local
            pending.append(child)
    if poses.keys() != links.keys():
        raise ValueError("URDF contains a disconnected component or cycle")
    return links, poses, base


def binary_stl(path: Path, inputs: dict[str, str], root: Path) -> np.ndarray:
    raw = path.read_bytes()
    if len(raw) < 84:
        raise ValueError(f"STL is shorter than its binary header: {path}")
    count = struct.unpack_from("<I", raw, 80)[0]
    if not count or len(raw) != 84 + 50 * count:
        raise ValueError(f"STL must be binary with an exact, nonzero facet count: {path}")
    facets = np.frombuffer(raw, dtype=FACET, count=count, offset=84)
    if not np.isfinite(facets["vertices"]).all() or not np.isfinite(facets["normal"]).all():
        raise ValueError(f"STL contains nonfinite coordinates/normals: {path}")
    inputs[path.relative_to(root).as_posix()] = hashlib.sha256(raw).hexdigest()
    return facets["vertices"].astype(float)


def assemble(package_root: Path) -> tuple[bytes, dict]:
    root = package_root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("--package-root must be an extracted package directory")
    candidates = sorted(root.rglob("*.urdf"))
    if len(candidates) != 1:
        raise ValueError(f"Expected exactly one .urdf in the package, found {len(candidates)}")
    urdf = contained(root, candidates[0])
    inputs: dict[str, str] = {}
    package = root.name
    metadata = root / "package.xml"
    if metadata.exists():
        package_xml = read_xml(contained(root, metadata), inputs, root)
        package = (one(package_xml, "name", required=True).text or "").strip()
        if not package or "/" in package or "\\" in package:
            raise ValueError("Invalid package.xml name")
    links, poses, base = tree(read_xml(urdf, inputs, root))
    cache, pieces, visual_links = {}, [], []
    instances = 0
    for name, link in links.items():
        visuals = link.findall("visual")
        if visuals:
            visual_links.append(name)
        for visual in visuals:
            geometry = one(visual, "geometry", required=True)
            if len(geometry) != 1 or geometry[0].tag != "mesh":
                raise ValueError(f"Only mesh visual geometry is supported: {name}")
            mesh = geometry[0]
            path = mesh_path(mesh.get("filename", ""), root, urdf, package)
            if path not in cache:
                cache[path] = binary_stl(path, inputs, root)
            scale = vector(mesh.get("scale"), (1, 1, 1))
            if np.any(scale == 0):
                raise ValueError(f"Zero visual mesh scale: {name}")
            pose = poses[name] @ origin(one(visual, "origin"))
            vertices = ((cache[path] * scale) @ pose[:3, :3].T + pose[:3, 3]) * 1000.0
            if not np.isfinite(vertices).all():
                raise ValueError(f"Nonfinite transformed vertices: {name}")
            pieces.append(vertices)
            instances += 1
    count = sum(len(piece) for piece in pieces)
    if not 0 < count <= 0xFFFFFFFF:
        raise ValueError("No visual triangles, or binary STL facet count exceeded")
    triangles = np.concatenate(pieces)
    output = np.zeros(count, dtype=FACET)
    with np.errstate(over="ignore", invalid="ignore"):
        output["vertices"] = triangles
    if not np.isfinite(output["vertices"]).all():
        raise ValueError("Transformed coordinates exceed binary STL float32 range")
    # Recompute normals after scaling/rotation, consistent with exported winding.
    # This also handles nonuniform/reflected mesh scales and zero source normals.
    vertices = output["vertices"].astype(float)
    normals = np.cross(vertices[:, 1] - vertices[:, 0], vertices[:, 2] - vertices[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    nonzero = lengths > 0
    normals[nonzero] /= lengths[nonzero, None]
    output["normal"] = normals
    data = HEADER + struct.pack("<I", count) + output.tobytes()
    report = {
        "notice": NOTICE, "units": "mm", "pose": "all joints q=0", "root_link": base,
        "urdf": urdf.relative_to(root).as_posix(), "links": list(links),
        "visual_links": visual_links, "visual_instances": instances, "triangles": count,
        "degenerate_triangles": int((~nonzero).sum()),
        "bounds_mm": {"min": vertices.min(axis=(0, 1)).tolist(), "max": vertices.max(axis=(0, 1)).tolist()},
        "input_sha256": inputs, "output_sha256": hashlib.sha256(data).hexdigest(),
    }
    return data, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New binary STL file; never overwritten")
    parser.add_argument("--report", type=Path, help="Optional new JSON report; never overwritten")
    args = parser.parse_args()
    created = []
    try:
        paths = [args.output] + ([args.report] if args.report else [])
        resolved = [path.parent.resolve(strict=True) / path.name for path in paths]
        if len(set(resolved)) != len(resolved) or any(path.exists() or path.is_symlink() for path in resolved):
            raise ValueError("Output/report must be distinct new files")
        data, report = assemble(args.package_root)
        # Reserve all destinations exclusively before writing either artifact.
        with args.output.open("xb") as target:
            created.append(args.output)
            if args.report:
                with args.report.open("x", encoding="utf-8") as metadata:
                    created.append(args.report)
                    metadata.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
            target.write(data)
        print(json.dumps({"output": str(args.output), "triangles": report["triangles"], "bounds_mm": report["bounds_mm"], "notice": NOTICE}))
        return 0
    except (OSError, ValueError, ET.ParseError) as error:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        print(f"Assembly failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
