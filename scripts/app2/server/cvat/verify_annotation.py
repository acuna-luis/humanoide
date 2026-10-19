#!/usr/bin/env python3
"""CVAT 2.79 HTTP smoke: synthetic PNG -> polygon -> COCO -> own task cleanup.

Run on the app2 server, e.g.:
  python3 verify_annotation.py --output-dir "$HOME/app2/evidence/cvat-smoke"

Only Python's standard library is required. Credentials JSON (username/password)
defaults to ~/app2/secrets/cvat-admin.json and is never printed. The only remote
resource modified/deleted is the task whose ID this process creates. Sources:
https://github.com/cvat-ai/cvat/blob/9176834830e2e931a8d3a6857dcf43c6cc0ee927/tests/python/rest_api/utils.py
https://docs.cvat.ai/docs/api_sdk/sdk/reference/apis/tasks-api/
"""

import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path
import stat
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
import zlib


WIDTH, HEIGHT = 128, 96
POINTS = [16, 16, 80, 16, 80, 64, 16, 64]
CLASS_NAME = "synthetic_app2_probe_only"


def synthetic_png():
    def chunk(kind, payload):
        return (struct.pack(">I", len(payload)) + kind + payload
                + struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff))

    raw = bytearray()
    for y in range(HEIGHT):
        raw.append(0)  # PNG filter: none.
        for x in range(WIDTH):
            raw.extend((230, 60, 40) if 16 <= x < 80 and 16 <= y < 64 else (40, 50, 70))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw))) + chunk(b"IEND", b""))


def multipart(image):
    boundary = "app2-" + uuid.uuid4().hex
    prefix = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="image_quality"\r\n\r\n100\r\n'
        f'--{boundary}\r\nContent-Disposition: form-data; name="client_files[0]"; '
        'filename="synthetic_app2_probe.png"\r\nContent-Type: image/png\r\n\r\n'
    ).encode()
    return prefix + image + f"\r\n--{boundary}--\r\n".encode(), f"multipart/form-data; boundary={boundary}"


class LocalRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(req.full_url)[:2] != urllib.parse.urlsplit(newurl)[:2]:
            raise RuntimeError("Refusing redirect outside the configured local CVAT origin")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class API:
    def __init__(self, base):
        parts = urllib.parse.urlsplit(base)
        if (parts.scheme != "http" or parts.hostname != "localhost" or parts.port != 18080
                or parts.username or parts.password or parts.query or parts.fragment):
            raise ValueError("This helper requires http://localhost:18080")
        self.base = base.rstrip("/")
        self.token = None
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), LocalRedirects())

    def request(self, method, path, *, data=None, content_type=None, raw=False, expected=(200,)):
        url = urllib.parse.urljoin(self.base + "/", path)
        if urllib.parse.urlsplit(url)[:2] != urllib.parse.urlsplit(self.base)[:2]:
            raise RuntimeError("Refusing a result URL outside local CVAT")
        # v2.79 uses CVATAPIRenderer and AcceptHeaderVersioning. A plain
        # application/json Accept header is rejected with HTTP 406.
        headers = {"Accept": "*/*" if raw else "application/vnd.cvat+json"}
        if self.token:
            headers["Authorization"] = "Token " + self.token
        if data is not None and not isinstance(data, bytes):
            data = json.dumps(data).encode()
            content_type = "application/json"
        if content_type:
            headers["Content-Type"] = content_type
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with self.opener.open(req, timeout=60) as response:
                if response.status not in expected:
                    raise RuntimeError(f"Unexpected HTTP {response.status} during {method}")
                body = response.read(32 * 1024 * 1024 + 1)
                if len(body) > 32 * 1024 * 1024:
                    raise RuntimeError("Unexpectedly large response for one synthetic image")
                return body if raw else (json.loads(body) if body else None)
        except urllib.error.HTTPError as error:
            # Do not print server response bodies, request bodies, headers, or tokens.
            raise RuntimeError(f"HTTP {error.code} during {method} {urllib.parse.urlsplit(url).path}") from None
        except urllib.error.URLError:
            raise RuntimeError("Local CVAT connection failed") from None

    def wait(self, rq_id, seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            result = self.request("GET", "/api/requests/" + urllib.parse.quote(str(rq_id), safe=""))
            if result.get("status") == "finished":
                return result
            if result.get("status") in ("failed", "canceled", "cancelled"):
                raise RuntimeError("CVAT background request failed; inspect its ID in private evidence")
            time.sleep(1)
        raise RuntimeError("Timed out waiting for CVAT background request")


def inside(x, y, polygon):
    vertices = list(zip(polygon[::2], polygon[1::2]))
    odd = False
    previous = vertices[-1]
    for current in vertices:
        ax, ay = previous
        bx, by = current
        if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
            odd = not odd
        previous = current
    return odd


def verify_coco(archive):
    with zipfile.ZipFile(io.BytesIO(archive)) as exported:
        candidates = [n for n in exported.namelist()
                      if n.startswith("annotations/") and n.endswith(".json")]
        assert len(candidates) == 1, "Expected a single COCO annotation document"
        content = json.loads(exported.read(candidates[0]))
        assert len(content["images"]) == 1, "Expected one synthetic image"
        assert len(content["annotations"]) == 1, "Expected one instance"
        image = content["images"][0]
        assert (image["width"], image["height"]) == (WIDTH, HEIGHT)
        annotation = content["annotations"][0]
        category = next(c for c in content["categories"] if c["id"] == annotation["category_id"])
        assert category["name"] == CLASS_NAME
        assert annotation["image_id"] == image["id"]
        assert not annotation.get("iscrowd", False)
        segmentation = annotation["segmentation"]
        assert isinstance(segmentation, list) and segmentation, "Expected polygon segmentation"
        assert all(len(p) >= 6 and len(p) % 2 == 0 for p in segmentation)
        assert all(math.isfinite(v) for p in segmentation for v in p)
        for actual, expected in zip(annotation["bbox"], [16, 16, 64, 48], strict=True):
            assert abs(actual - expected) <= 1, "Unexpected bounding box"
        mask_pixels = sum(any(inside(x + 0.5, y + 0.5, p) for p in segmentation)
                          for y in range(HEIGHT) for x in range(WIDTH))
        assert mask_pixels == 64 * 48, "Exported instance mask differs from synthetic ground truth"
        assert abs(annotation["area"] - mask_pixels) <= 1
        media = [n for n in exported.namelist()
                 if n.startswith("images/") and not n.endswith("/")]
        assert len(media) == 1, "Export did not include the synthetic image"
        return {"images": 1, "instances": 1, "mask_pixels": mask_pixels,
                "category": CLASS_NAME, "media_files": len(media)}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--credentials", type=Path, default=Path.home() / "app2/secrets/cvat-admin.json")
    parser.add_argument("--base-url", default="http://localhost:18080")
    parser.add_argument("--output-dir", type=Path, required=True, help="Private evidence directory; unique filenames")
    parser.add_argument("--timeout", type=int, default=300, help="Seconds per asynchronous operation")
    args = parser.parse_args()
    os.umask(0o077)
    run_id = "app2-synthetic-smoke-" + uuid.uuid4().hex
    api = API(args.base_url)
    task_id = None
    receipt = {"run_id": run_id, "synthetic_only": True, "success": False,
               "created_task_id": None, "deleted_own_task": False}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    receipt_file = args.output_dir / (run_id + ".json")
    exit_code = 1
    try:
        mode = args.credentials.stat().st_mode
        if stat.S_IMODE(mode) & 0o077:
            raise RuntimeError("Credentials file must have private permissions (0600)")
        credentials = json.loads(args.credentials.read_text())
        login = api.request("POST", "/api/auth/login", data={
            "username": credentials["username"], "password": credentials["password"]})
        api.token = login["key"]
        del credentials, login
        receipt["login_ok"] = True
        about = api.request("GET", "/api/server/about")
        receipt["server_version"] = about.get("version")
        api.request("GET", "/api/users/self")
        receipt["authenticated_api_ok"] = True
        task = api.request("POST", "/api/tasks", data={
            "name": run_id, "labels": [{"name": CLASS_NAME, "type": "polygon", "attributes": []}]},
            expected=(201,))
        task_id = int(task["id"])
        receipt["created_task_id"] = task_id
        receipt_file.write_text(json.dumps(receipt, indent=2) + "\n")
        image = synthetic_png()
        (args.output_dir / (run_id + ".png")).write_bytes(image)
        body, content_type = multipart(image)
        created = api.request("POST", f"/api/tasks/{task_id}/data", data=body,
                              content_type=content_type, expected=(202,))
        receipt["upload_rq_id"] = created["rq_id"]
        api.wait(created["rq_id"], args.timeout)
        assert api.request("GET", f"/api/tasks/{task_id}")["size"] == 1
        labels = api.request("GET", f"/api/labels?task_id={task_id}")
        labels = labels.get("results", []) if isinstance(labels, dict) else labels
        assert len(labels) == 1 and labels[0]["name"] == CLASS_NAME
        api.request("PUT", f"/api/tasks/{task_id}/annotations", data={
            "version": 0, "tags": [], "tracks": [], "shapes": [{
                "type": "polygon", "frame": 0, "label_id": labels[0]["id"],
                "points": POINTS, "occluded": False, "outside": False,
                "z_order": 0, "rotation": 0, "attributes": [], "source": "manual"}]})
        saved = api.request("GET", f"/api/tasks/{task_id}/annotations")
        assert len(saved["shapes"]) == 1 and saved["shapes"][0]["points"] == POINTS
        receipt["polygon_saved_and_reloaded"] = True
        query = urllib.parse.urlencode({"format": "COCO 1.0", "save_images": "true", "location": "local"})
        export = api.request("POST", f"/api/tasks/{task_id}/dataset/export?{query}", expected=(202,))
        receipt["export_rq_id"] = export["rq_id"]
        ready = api.wait(export["rq_id"], args.timeout)
        archive = api.request("GET", ready["result_url"], raw=True)
        (args.output_dir / (run_id + ".zip")).write_bytes(archive)
        receipt["coco"] = verify_coco(archive)
        receipt["export_sha256"] = hashlib.sha256(archive).hexdigest()
        receipt["success"] = True
        exit_code = 0
    except (Exception, KeyboardInterrupt) as error:
        # Exception bodies from HTTP are suppressed above. No credentials are formatted.
        receipt["error_type"] = type(error).__name__
        receipt["error"] = str(error) if isinstance(error, (RuntimeError, AssertionError)) else "See error_type"
    finally:
        if task_id is not None:
            try:
                own_task = api.request("GET", f"/api/tasks/{task_id}")
                if own_task.get("name") != run_id:
                    raise RuntimeError("Task identity changed; refusing deletion")
                api.request("DELETE", f"/api/tasks/{task_id}", expected=(204,))
                receipt["deleted_own_task"] = True
            except Exception as error:
                receipt["cleanup_error_type"] = type(error).__name__
                receipt["success"] = False
                exit_code = 1
        receipt_file.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
        print(json.dumps(receipt, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
