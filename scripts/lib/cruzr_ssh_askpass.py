#!/usr/bin/env python3
"""Proveedor SSH_ASKPASS: entorno o archivo privado del PC, sin clave embebida."""

import os
from pathlib import Path
import stat
import sys


def read_password():
    value = os.environ.get("CRUZR_SSH_PASSWORD")
    if not value:
        path = os.environ.get("CRUZR_SSH_PASSWORD_FILE") or str(
            Path(__file__).resolve().parents[2] / ".secrets/cruzr_ssh_password"
        )
        # No seguir un enlace ni bloquearse al abrir un FIFO como contraseña.
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as source:
            info = os.fstat(source.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                    or info.st_mode & 0o077):
                raise ValueError("archivo privado inválido")
            raw = source.read(4097)
        if len(raw) > 4096:
            raise ValueError("archivo demasiado grande")
        # Se admite un único salto de línea final, propio de un archivo de texto.
        if raw.endswith(b"\n"):
            raw = raw[:-1]
        value = raw.decode("utf-8")
    if not value or any(char in value for char in "\n\r\0"):
        raise ValueError("contraseña vacía o con varias líneas")
    return value


def main():
    try:
        password = read_password()
    except (OSError, ValueError, UnicodeError):
        print(
            "ERROR: configure CRUZR_SSH_PASSWORD o un archivo privado de una línea "
            "en .secrets/cruzr_ssh_password (permisos 600); "
            "CRUZR_SSH_PASSWORD_FILE permite elegir otra ruta.",
            file=sys.stderr,
        )
        return 1
    # stdout se entrega exclusivamente a SSH_ASKPASS; nunca registrarlo en logs.
    print(password)
    return 0


if __name__ == "__main__":
    sys.exit(main())
