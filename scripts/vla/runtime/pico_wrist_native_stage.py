#!/usr/bin/env python3
"""Additive task staging primitive for a reviewed wrist probe.

Does not dispatch an action, reload the robot or modify the SDK. The caller
must first verify fresh physical conditions, exclusive control, current hashes,
and a live guard. Staging is a system change that requires durable receipts
and project documentation. Never call this primitive automatically on import.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat

import prepare_pico_wrist_native_probe as probe


def stage_task(manifest, urdf_text, transmissions_text, *, intent_path, session_id, intent_owner_uid,
               root=probe.TASK_ROOT):
    probe.validate(manifest, urdf_text, transmissions_text)
    candidate = manifest['candidate']
    if not isinstance(session_id, str) or not re.fullmatch('[0-9a-f]{32}', session_id):
        raise ValueError('invalid_stage_session')
    if type(intent_owner_uid) is not int or intent_owner_uid < 0:
        raise ValueError('invalid_intent_owner')
    intent_parent = Path(intent_path).parent
    parent_info = intent_parent.lstat()
    if (not stat.S_ISDIR(parent_info.st_mode) or parent_info.st_uid != intent_owner_uid or
            stat.S_IMODE(parent_info.st_mode) & 0o077 or intent_parent.resolve() != intent_parent):
        raise ValueError('intent_directory_not_private_or_owned')
    # Receipt is made and fsynced by the host coordinator BEFORE this function
    # runs, so a partial file/directory remains discoverable on failure.
    flags_read = os.O_RDONLY | os.O_CLOEXEC | getattr(os, 'O_NOFOLLOW', 0)
    intent_fd = os.open(intent_path, flags_read)
    try:
        info = os.fstat(intent_fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != intent_owner_uid or info.st_size > 4096
                or stat.S_IMODE(info.st_mode) & 0o077):
            raise ValueError('invalid_stage_intent_file')
        with os.fdopen(intent_fd, 'r', encoding='utf-8') as stream:
            intent_fd = None
            intent = json.load(stream)
    finally:
        if intent_fd is not None: os.close(intent_fd)
    if intent != {'session_id': session_id, 'task_path': candidate['runtime_path'],
                  'task_sha256': candidate['xml_sha256'], 'state': 'intent_before_stage_or_send'}:
        raise ValueError('stage_intent_mismatch')
    if (not os.path.isabs(root) or os.path.realpath(root) != os.path.normpath(root)):
        raise ValueError('task_root_not_canonical')
    # Task name is recomputed by probe.validate and cannot contain traversal.
    task_name = candidate['task_name']
    directory, name = task_name.rsplit('/', 1)
    if directory != 'diagnostics' or not name.startswith('pico_v4_wrist_'):
        raise ValueError('unexpected_task_name')
    flags_dir = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | getattr(os, 'O_NOFOLLOW', 0)
    root_fd = os.open(root, flags_dir)
    try:
        created_directory = False
        try:
            os.mkdir('diagnostics', 0o755, dir_fd=root_fd)
            created_directory = True
            os.fsync(root_fd)
        except FileExistsError:
            pass
        diagnostic_fd = os.open('diagnostics', flags_dir, dir_fd=root_fd)
        try:
            dir_info = os.fstat(diagnostic_fd)
            name += '.xml'
            data = candidate['xml'].encode('utf-8')
            if hashlib.sha256(data).hexdigest() != candidate['xml_sha256']:
                raise ValueError('task_xml_hash_mismatch')
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | getattr(os, 'O_NOFOLLOW', 0)
            fd = os.open(name, flags, 0o600, dir_fd=diagnostic_fd)
            try:
                info = os.fstat(fd)
                view = memoryview(data)
                while view:
                    count = os.write(fd, view)
                    if count <= 0: raise OSError('incomplete_task_write')
                    view = view[count:]
                os.fsync(fd)
            finally:
                os.close(fd)
            # Read via dirfd with O_NOFOLLOW, so a replacement is detected.
            fd = os.open(name, os.O_RDONLY | os.O_CLOEXEC | getattr(os, 'O_NOFOLLOW', 0), dir_fd=diagnostic_fd)
            try:
                now = os.fstat(fd)
                if (not stat.S_ISREG(now.st_mode) or (now.st_dev, now.st_ino) != (info.st_dev, info.st_ino)):
                    raise RuntimeError('staged_file_identity_changed')
                with os.fdopen(fd, 'rb') as stream:
                    fd = None
                    observed = hashlib.sha256(stream.read()).hexdigest()
            finally:
                if fd is not None: os.close(fd)
            if observed != candidate['xml_sha256']:
                raise RuntimeError('staged_hash_mismatch')
            os.fsync(diagnostic_fd)
            return {'status': 'STAGED_NOT_LOADED_OR_EXECUTED', 'runtime_path': str(Path(root)/task_name)+'.xml',
                    'sha256': observed, 'device': info.st_dev, 'inode': info.st_ino,
                    'directory_created': created_directory, 'directory_device': dir_info.st_dev,
                    'directory_inode': dir_info.st_ino,
                    'movement_commands': 0, 'mode_changes': 0, 'automatic_cleanup': False}
        finally:
            os.close(diagnostic_fd)
    finally:
        os.close(root_fd)


def verify_staged(manifest, receipt, *, root=probe.TASK_ROOT):
    """Re-read exact directory/file identity and bytes; does not lock the loader."""
    candidate = manifest['candidate']
    if (not isinstance(candidate.get('task_name'), str) or
            not re.fullmatch(r'diagnostics/pico_v4_wrist_[0-9a-f]{16}', candidate['task_name'])):
        raise ValueError('invalid_staged_task_name')
    if (not isinstance(receipt, dict) or receipt.get('status') != 'STAGED_NOT_LOADED_OR_EXECUTED'
            or receipt.get('runtime_path') != str(Path(root)/candidate['task_name'])+'.xml'
            or receipt.get('sha256') != candidate['xml_sha256']):
        raise ValueError('staged_receipt_mismatch')
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | getattr(os, 'O_NOFOLLOW', 0))
    try:
        directory_fd = os.open('diagnostics', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC |
                               getattr(os, 'O_NOFOLLOW', 0), dir_fd=root_fd)
        try:
            dinfo = os.fstat(directory_fd)
            if (dinfo.st_dev, dinfo.st_ino) != (receipt.get('directory_device'), receipt.get('directory_inode')):
                raise RuntimeError('staged_directory_identity_changed')
            filename = candidate['task_name'].split('/')[-1] + '.xml'
            fd = os.open(filename, os.O_RDONLY | os.O_CLOEXEC | getattr(os, 'O_NOFOLLOW', 0), dir_fd=directory_fd)
            try:
                info = os.fstat(fd)
                if (not stat.S_ISREG(info.st_mode) or
                        (info.st_dev, info.st_ino) != (receipt.get('device'), receipt.get('inode'))):
                    raise RuntimeError('staged_file_identity_changed')
                with os.fdopen(fd, 'rb') as stream:
                    fd = None
                    digest = hashlib.sha256(stream.read()).hexdigest()
            finally:
                if fd is not None: os.close(fd)
            if digest != candidate['xml_sha256']:
                raise RuntimeError('staged_hash_changed')
            return True
        finally:
            os.close(directory_fd)
    finally:
        os.close(root_fd)


if __name__ == '__main__':
    raise SystemExit('No direct staging or execution; use a reviewed coordinator.')
