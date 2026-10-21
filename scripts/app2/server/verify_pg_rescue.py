#!/usr/bin/env python3
"""Validate CVAT PostgreSQL ONLY from verified off-server archives in a new local copy.

Requires local Docker and the official, pinned postgres image already pulled.
Creates one isolated, temporary container without network/ports and removes only
that container. Keeps private recovered copy, logs and logical dump for review.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile
import time
import uuid

IMAGE = "docker.io/library/postgres:15-alpine@sha256:f7d23353e1b15400d22ebe31189f4d314b87a4c129cc400c8c2d8d4ca127bf81"
DB_ARCHIVE = "app2-cvat_cvat_db.tar"
DEF_ARCHIVE = "docker-definitions.tar"
COUNTS = """SELECT json_build_object(
'tasks',(SELECT count(*) FROM engine_task),
'jobs',(SELECT count(*) FROM engine_job),
'shapes',(SELECT count(*) FROM engine_labeledshape),
'task5_exists',EXISTS(SELECT 1 FROM engine_task WHERE id=5),
'job5_task5',EXISTS(SELECT 1 FROM engine_job j JOIN engine_segment s ON s.id=j.segment_id WHERE j.id=5 AND s.task_id=5),
'frame1_shape10',EXISTS(SELECT 1 FROM engine_labeledshape WHERE id=10 AND job_id=5 AND frame=1));"""


def run(*args, **kwargs):
    return subprocess.run(args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, timeout=kwargs.pop("timeout", 30), **kwargs).stdout


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(data)
    return digest.hexdigest()


def verified_archives(backup, transfer, source):
    if transfer.get("all_copied_hashes_match") is not True:
        raise ValueError("Off-server transfer has not been completely verified")
    copied = {a["file"]: a for a in transfer["archives"]}
    original = {a["file"]: a for a in source["result"]["receipt"]["archives"]}
    result = {}
    for name in (DB_ARCHIVE, DEF_ARCHIVE):
        path = backup / name
        if path.is_symlink() or not path.is_file() or copied[name].get("matches") is not True:
            raise ValueError("Required copied archive is missing or unverified")
        digest = sha(path)
        if (digest != copied[name]["sha256"] or digest != original[name]["sha256"]
                or path.stat().st_size != original[name]["bytes"]):
            raise ValueError("Copied archive does not match original backup receipt")
        result[name] = digest
    return result


def safe_members(archive):
    members, seen, total = [], set(), 0
    for member in archive:
        path = PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts or not (member.isfile() or member.isdir()):
            raise ValueError("Unsafe archive path/type, link or external PostgreSQL storage")
        key = str(path)
        if key in seen or member.size < 0:
            raise ValueError("Duplicate or invalid archive member")
        seen.add(key)
        total += member.size
        members.append(member)
        if total > 2 * 1024 ** 3 or len(members) > 200000:
            raise ValueError("Archive exceeds bounded PostgreSQL rescue allowance")
    return members


def database_config(archive):
    matches = []
    with tarfile.open(archive, "r:") as source:
        for member in safe_members(source):
            if not member.name.endswith("/config.v2.json"):
                continue
            if member.size > 2 * 1024 ** 2:
                raise ValueError("Unexpected container definition size")
            config = json.load(source.extractfile(member))
            labels = config.get("Config", {}).get("Labels", {}) or {}
            if (labels.get("com.docker.compose.project") == "app2-cvat"
                    and labels.get("com.docker.compose.service") == "cvat_db"):
                matches.append(config)
    if len(matches) != 1:
        raise ValueError("Expected one original CVAT PostgreSQL container definition")
    config = matches[0]
    reference = config["Config"]["Image"]
    if not reference.endswith("@" + IMAGE.split("@", 1)[1]) or "postgres:15-alpine@" not in reference:
        raise ValueError("PostgreSQL image differs from the locked backup version")
    variables = dict(v.split("=", 1) for v in config["Config"].get("Env", []) if "=" in v)
    user, database = variables.get("POSTGRES_USER", "postgres"), variables.get("POSTGRES_DB", "postgres")
    if not all(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", value) for value in (user, database)):
        raise ValueError("Unexpected database/user identifiers")
    mounts = [target for target, item in config.get("MountPoints", {}).items()
              if item.get("Name") == "app2-cvat_cvat_db"]
    if len(mounts) != 1:
        raise ValueError("Original PGDATA volume mapping is missing")
    relative = PurePosixPath(variables.get("PGDATA", "/var/lib/postgresql/data")).relative_to(mounts[0])
    if ".." in relative.parts:
        raise ValueError("Unexpected PGDATA path")
    return user, database, Path(*relative.parts)


def extract_copy(archive, destination):
    destination.mkdir(mode=0o700)
    with tarfile.open(archive, "r:") as source:
        members = safe_members(source)
        for member in members:
            target = destination.joinpath(*PurePosixPath(member.name).parts)
            if member.isdir():
                target.mkdir(mode=0o700, parents=True, exist_ok=True)
                continue
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with source.extractfile(member) as data, target.open("xb") as output:
                shutil.copyfileobj(data, output)
            target.chmod(member.mode & 0o777)
            os.utime(target, (member.mtime, member.mtime))


def write_private(path, value):
    data = json.dumps(value, indent=2) + "\n" if not isinstance(value, str) else value
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(data)


def snapshot():
    ids = run("docker", "ps", "--format", "{{.ID}}").split()
    return [json.loads(line) for line in run("docker", "inspect", "--format",
        "[{{json .Id}},{{json .Name}},{{json .State.StartedAt}}]", *ids).splitlines()] if ids else []


def verify(backup, transfer, original, output):
    hashes = verified_archives(backup, transfer, original)
    endpoint = json.loads(run("docker", "context", "inspect", "--format", "{{json .Endpoints.docker.Host}}"))
    if not endpoint.startswith("unix://") or not os.environ.get("DOCKER_HOST", "unix://").startswith("unix://"):
        raise ValueError("A local Unix Docker endpoint is required")
    run("docker", "image", "inspect", IMAGE, "--format", "{{.Id}}")
    output.mkdir(mode=0o700)
    before = snapshot()
    write_private(output / "existing-containers-before.json", before)
    user, database, relative = database_config(backup / DEF_ARCHIVE)
    extract_copy(backup / DB_ARCHIVE, output / "physical-copy")
    data = output / "physical-copy" / relative
    if (data / "PG_VERSION").read_text().strip() != "15":
        raise ValueError("Physical backup PG_VERSION differs from locked image major 15")
    if (data / "postmaster.pid").exists():
        (data / "postmaster.pid").rename(data / "postmaster.pid.from-backup")
    config = output / "test-config"
    config.mkdir(mode=0o700)
    uid, gid = os.getuid(), os.getgid()
    write_private(config / "passwd", f"root:x:0:0:root:/root:/bin/sh\npgrestore:x:{uid}:{gid}:Restore test:/tmp:/bin/sh\n")
    write_private(config / "pg_hba.conf", "local all all trust\n")
    write_private(config / "postgresql.conf", "shared_buffers='128MB'\nmax_connections=10\n")
    container = "app2-pg-restore-" + uuid.uuid4().hex[:12]
    started = False
    result = {"status": "FAILED", "image": IMAGE, "source_archive_hashes": hashes}
    try:
        run("docker", "run", "--detach", "--name", container, "--label", "app2.restore-test=" + container,
            "--network", "none", "--read-only", "--user", f"{uid}:{gid}", "--cap-drop=ALL",
            "--security-opt=no-new-privileges", "--pids-limit=128", "--memory=1g", "--cpus=2",
            "--tmpfs", f"/tmp:rw,nosuid,noexec,size=128m,uid={uid},gid={gid},mode=0700",
            "--mount", f"type=bind,src={data},dst=/restore",
            "--mount", f"type=bind,src={config},dst=/test,readonly",
            "--mount", f"type=bind,src={config / 'passwd'},dst=/etc/passwd,readonly",
            "--entrypoint", "postgres", IMAGE, "-D", "/restore", "-c", "config_file=/test/postgresql.conf",
            "-c", "hba_file=/test/pg_hba.conf", "-c", "listen_addresses=", "-c", "unix_socket_directories=/tmp")
        started = True
        connection = ("-h", "/tmp", "-U", user)
        for _ in range(45):
            try:
                run("docker", "exec", container, "pg_isready", *connection, "-d", database, timeout=5)
                break
            except subprocess.SubprocessError:
                time.sleep(2)
        else:
            raise ValueError("Isolated PostgreSQL recovery did not become ready within 90 seconds")
        def counts(name):
            return json.loads(run("docker", "exec", container, "psql", "-XAt", "-v", "ON_ERROR_STOP=1",
                                  *connection, "-d", name, "-c", COUNTS))
        physical_counts = counts(database)
        dump = output / "cvat-recovered.dump"
        with dump.open("xb") as stream:
            subprocess.run(("docker", "exec", container, "pg_dump", *connection, "-d", database,
                            "--format=custom", "--no-owner", "--no-privileges"), stdout=stream,
                           stderr=subprocess.PIPE, check=True, timeout=120)
        dump.chmod(0o600)
        run("docker", "exec", container, "createdb", *connection, "-T", "template0", "app2_restore_verify")
        with dump.open("rb") as stream:
            run("docker", "exec", "-i", container, "pg_restore", *connection, "-d", "app2_restore_verify",
                "--no-owner", "--no-privileges", stdin=stream, timeout=120)
        logical_counts = counts("app2_restore_verify")
        if physical_counts != logical_counts:
            raise ValueError("Logical dump restoration counts differ from recovered physical copy")
        result.update(status="PASS_PHYSICAL_RECOVERY_AND_LOGICAL_ROUNDTRIP", counts=physical_counts,
                      logical_counts=logical_counts, dump_sha256=sha(dump), dump_bytes=dump.stat().st_size,
                      historical_first_contour_preserved=all(physical_counts[key] for key in
                          ("task5_exists", "job5_task5", "frame1_shape10")))
    finally:
        if started:
            logs = subprocess.run(("docker", "logs", "--tail=300", container), capture_output=True,
                                  text=True, timeout=10)
            write_private(output / "postgres.log", logs.stdout + logs.stderr)
            label = run("docker", "inspect", "--format", '{{index .Config.Labels "app2.restore-test"}}', container).strip()
            if label != container:
                raise ValueError("Temporary container ownership label differs; refusing removal")
            run("docker", "stop", "--time=30", container, timeout=40)
            run("docker", "rm", container)
        result["temporary_container_removed"] = started
        result["original_archives_unchanged"] = all(sha(backup / name) == digest for name, digest in hashes.items())
        after = snapshot()
        write_private(output / "existing-containers-after.json", after)
        result["existing_container_ids_still_present"] = {r[0] for r in before} <= {r[0] for r in after}
        write_private(output / "result.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup-dir", type=Path, required=True)
    parser.add_argument("--transfer-receipt", type=Path, required=True)
    parser.add_argument("--source-receipt", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    try:
        result = verify(args.backup_dir.resolve(), json.loads(args.transfer_receipt.read_text()),
                        json.loads(args.source_receipt.read_text()), args.output_dir.absolute())
        print(json.dumps(result, indent=2))
    except Exception as error:
        print(f"PG_RESTORE_TEST_FAILED={type(error).__name__}; inspect private output/logs")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
