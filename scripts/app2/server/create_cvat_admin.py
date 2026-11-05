#!/usr/bin/env python3
"""Create a local CVAT administrator without putting credentials in argv/logs.

Run on the server after CVAT migrations finish. Existing credentials are kept;
an existing account with a different password is never reset automatically.
"""

import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container", required=True)
    parser.add_argument("--credentials", type=Path,
                        default=Path.home() / "app2/secrets/cvat-admin.json")
    args = parser.parse_args()
    os.umask(0o077)
    args.credentials.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        with args.credentials.open("x", encoding="utf-8") as file:
            json.dump({"username": "app2_admin", "password": secrets.token_urlsafe(24),
                       "email": "admin@localhost"}, file)
            file.write("\n")
    except FileExistsError:
        pass
    args.credentials.chmod(0o600)
    data = json.loads(args.credentials.read_text())
    code = """
import json, sys
from django.contrib.auth import get_user_model
data = json.load(sys.stdin)
users = get_user_model().objects
user = users.filter(username=data['username']).first()
if user is None:
    user = users.create_superuser(**data)
elif not user.check_password(data['password']) or not user.is_superuser:
    raise RuntimeError('Existing CVAT account differs; no automatic reset performed')
print('APP2_CVAT_ADMIN_READY=1')
"""
    subprocess.run(["docker", "exec", "-i", args.container, "python", "/opt/cvat/manage.py",
                    "shell", "-c", code], input=json.dumps(data), text=True,
                   check=True, timeout=90)
    print(f"APP2_CVAT_CREDENTIALS_FILE={args.credentials}")


if __name__ == "__main__":
    main()
