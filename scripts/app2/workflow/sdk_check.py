#!/usr/bin/env python3
"""Read-only CVAT SDK check; use the isolated SDK interpreter, never print tokens."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import stat


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--credentials", type=Path, default=Path("/run/cvat-admin.json"))
    args = parser.parse_args()
    if stat.S_IMODE(args.credentials.stat().st_mode) & 0o077:
        raise RuntimeError("Credentials must have private permissions")
    from cvat_sdk import make_client
    credentials = json.loads(args.credentials.read_text())
    with make_client("http://localhost:18080", credentials=(credentials["username"], credentials["password"])) as client:
        del credentials
        version = str(client.get_server_version())
        if version != "2.79.0":
            raise RuntimeError("Expected CVAT 2.79.0")
        projects = client.projects.list()
        own = [{"id": p.id, "name": p.name} for p in projects if p.name in ("app2-itr-v0", "app2-infrastructure-demo-v0")]
        print(json.dumps({"status": "PASS", "sdk_version": importlib.metadata.version("cvat-sdk"),
                          "server_version": version, "app2_projects": own, "readonly": True}))


if __name__ == "__main__":
    main()
