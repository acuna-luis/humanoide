#!/usr/bin/env python3
"""File-only integration acceptance for the development infrastructure."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    def run(script, *options):
        subprocess.run([sys.executable, script, *map(str, options)], check=True)
    receipt = {"status": "IN_PROGRESS", "synthetic_only": True, "robot_or_plc_connected": False}
    try:
        run("code_smoke.py", "--output-dir", args.output_dir / "codes")
        run("checkpoint_smoke.py", "--dataset", args.dataset,
            "--output-root", args.output_dir / "training", "--synthetic-only")
        results = list((args.output_dir / "training").glob("*/result.json"))
        if len(results) != 1:
            raise RuntimeError("Expected one training receipt")
        training = json.loads(results[0].read_text())
        if training["status"] != "PASS":
            raise RuntimeError("Training did not pass")
        checkpoint = training["checkpoint"]
        run("demo.py", "--sequence", args.output_dir / "codes/inputs", "--output-root", args.output_dir / "demo",
            "--expected-material", "APP2-SYNTHETIC-MATERIAL-A", "--identity-scope", "box",
            "--model", "checkpoint", "--checkpoint", checkpoint, "--threshold", "0.1", "--synthetic-input")
        records = [json.loads(line) for line in (args.output_dir / "demo/events.jsonl").read_text().splitlines()]
        if not records or any(r["perception"]["status"] == "PROCESSING_ERROR" for r in records):
            raise RuntimeError("Integrated inference failed")
        states = {r["material"]["result"] for r in records}
        if not {"MATCH", "NO_READ", "AMBIGUOUS"}.issubset(states):
            raise RuntimeError(f"Missing integrated read outcomes: {states}")
        receipt.update(status="PASS", training=training, frames=len(records), code_states=sorted(states),
            limitations=["No real ITR training or material identification accuracy", "No physical cycle or calibration",
                         "Synthetic input pixels and simulated robot/PLC interfaces"])
    except Exception as error:
        receipt.update(status="FAIL", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        (args.output_dir / "result.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps(receipt))


if __name__ == "__main__":
    main()
