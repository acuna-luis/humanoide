"""Pruebas locales del bloqueo y del análisis histórico de cabeza desde PICO."""

import contextlib
import builtins
import importlib.util
import io
import json
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).with_name("mover_cabeza_desde_pico.py")
SPEC = importlib.util.spec_from_file_location("head_pico_check", SCRIPT)
HEAD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HEAD)


class HeadPicoTests(unittest.TestCase):
    def test_run_rejects_without_files_network_or_action_client(self):
        # El camino de ejecución no consulta evidencias ni toca los locks, ni
        # crea conexiones o procesos. Los módulos ROS no se importan en main.
        real_import = builtins.__import__
        def guarded_import(name, *args, **kwargs):
            if name == "rclpy" or name.startswith(("rclpy.", "mc_task_msgs")):
                raise AssertionError("importación ROS")
            return real_import(name, *args, **kwargs)
        with (patch.object(Path, "open", side_effect=AssertionError("acceso a archivo")),
              patch.object(socket, "socket", side_effect=AssertionError("socket")),
              patch.object(subprocess, "Popen", side_effect=AssertionError("proceso")),
              patch("builtins.__import__", side_effect=guarded_import),
              contextlib.redirect_stderr(io.StringIO())):
            self.assertEqual(HEAD.main(["--run", "--estado", "does-not-exist"]), 2)

    def test_snapshot_validation_and_result_remains_blocked(self):
        names = list(HEAD.BODY_JOINTS)
        message = {"name": names, "position": [0.0] * len(names)}
        document = {"captured_utc": "2026-11-09T20:29:47+00:00",
                    "checks": {"whole_joint_states": {
                        "returncode": 0, "stdout": "diagnóstico\n" + json.dumps(message)}}}
        with tempfile.TemporaryDirectory() as temporary:
            snapshot = Path(temporary) / "control-read.json"
            snapshot.write_text(json.dumps(document), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(HEAD.main(["--check", "--estado", str(snapshot)]), 1)
            self.assertIn("NO HABILITADO", output.getvalue())
            self.assertIn("no acredita postura", output.getvalue())

            message["name"].append(names[0])
            message["position"].append(0.0)
            document["checks"]["whole_joint_states"]["stdout"] = json.dumps(message)
            snapshot.write_text(json.dumps(document), encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(HEAD.main(["--check", "--estado", str(snapshot)]), 2)

    def test_finite_complete_body_values_required(self):
        with tempfile.TemporaryDirectory() as temporary:
            snapshot = Path(temporary) / "control-read.json"
            for positions in ([float("nan")] + [0.0] * 19, [False] + [0.0] * 19, [0.0] * 19):
                message = {"name": list(HEAD.BODY_JOINTS), "position": positions}
                snapshot.write_text(json.dumps({"captured_utc": "2026-11-09T20:29:47+00:00",
                    "checks": {"whole_joint_states": {"returncode": 0,
                        "stdout": json.dumps(message)}}}), encoding="utf-8")
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(HEAD.main(["--check", "--estado", str(snapshot)]), 2)


if __name__ == "__main__":
    unittest.main()
