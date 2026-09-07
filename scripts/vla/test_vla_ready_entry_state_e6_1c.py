#!/usr/bin/env python3
"""Offline regression tests for the E6.1C 20D endpoint gate."""

from __future__ import annotations

import json
import copy
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def run(checker: Path, contract: Path, state: Path, endpoint: str):
    return subprocess.run(
        [sys.executable, str(checker), "--contract", str(contract),
         "--state-json", str(state), "--expect", endpoint, "--require-fresh"],
        check=False, text=True, capture_output=True,
    )


def main() -> int:
    root = Path(__file__).resolve().parent
    checker = root / "check_vla_ready_entry_state_e6_1c.py"
    contract_path = root / "runtime/cruzr_s2_vla_ready_entry_transition_e6_1c.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="e6_1c_state_") as raw:
        state_path = Path(raw) / "state.json"

        def state_at(values):
            return {
                "names": contract["joint_order"],
                "positions": list(values),
                "velocities": [0.0] * 20,
                "observed_at_unix": time.time(),
            }

        state_path.write_text(json.dumps(state_at(contract["observed_ready_reference_20d_rad"])))
        accepted_ready = run(checker, contract_path, state_path, "ready")
        assert accepted_ready.returncode == 0, accepted_ready.stderr
        assert json.loads(accepted_ready.stdout)["qualified"] is True

        state_path.write_text(json.dumps(state_at(contract["entry_target_20d_rad"])))
        accepted_entry = run(checker, contract_path, state_path, "entry")
        assert accepted_entry.returncode == 0, accepted_entry.stderr
        assert json.loads(accepted_entry.stdout)["qualified"] is True

        bad = state_at(contract["entry_target_20d_rad"])
        bad["positions"][16] += 0.011
        state_path.write_text(json.dumps(bad))
        rejected_position = run(checker, contract_path, state_path, "entry")
        assert rejected_position.returncode == 3, rejected_position.stderr
        assert "state_not_entry" in json.loads(rejected_position.stdout)["rejection_reasons"]

        bad = state_at(contract["entry_target_20d_rad"])
        bad["velocities"][0] = 0.011
        state_path.write_text(json.dumps(bad))
        rejected_velocity = run(checker, contract_path, state_path, "entry")
        assert rejected_velocity.returncode == 3, rejected_velocity.stderr
        assert "state_not_stationary" in json.loads(rejected_velocity.stdout)["rejection_reasons"]

        bad = state_at(contract["entry_target_20d_rad"])
        bad["observed_at_unix"] = time.time() - 3.0
        state_path.write_text(json.dumps(bad))
        rejected_age = run(checker, contract_path, state_path, "entry")
        assert rejected_age.returncode == 3, rejected_age.stderr
        assert "state_not_fresh" in json.loads(rejected_age.stdout)["rejection_reasons"]

        cases = 5
        for field in ('positions', 'velocities'):
            for invalid in (True, None, '0', float('nan'), float('inf')):
                bad = state_at(contract['entry_target_20d_rad'])
                bad[field][0] = invalid
                state_path.write_text(json.dumps(bad))
                result = run(checker,contract_path,state_path,'entry')
                assert result.returncode == 2, (field,invalid,result.stdout,result.stderr)
                cases += 1
        for invalid in (True, None, '0', float('nan'), float('inf')):
            bad = state_at(contract['entry_target_20d_rad'])
            bad['observed_at_unix'] = invalid
            state_path.write_text(json.dumps(bad))
            assert run(checker,contract_path,state_path,'entry').returncode == 2
            cases += 1
        altered_contract = Path(raw)/'contract.json'
        state_path.write_text(json.dumps(state_at(contract['entry_target_20d_rad'])))
        for key in ('maximum_chebyshev_distance_rad','maximum_absolute_velocity_rad_s','maximum_state_age_seconds'):
            for invalid in (True, 0, -1, float('nan'), float('inf')):
                altered = copy.deepcopy(contract)
                altered['state_gate'][key] = invalid
                altered_contract.write_text(json.dumps(altered))
                assert run(checker,altered_contract,state_path,'entry').returncode == 2
                cases += 1
        altered = copy.deepcopy(contract)
        altered['joint_order'][1] = altered['joint_order'][0]
        altered_contract.write_text(json.dumps(altered))
        bad = state_at(contract['entry_target_20d_rad'])
        bad['names'] = altered['joint_order']
        state_path.write_text(json.dumps(bad))
        assert run(checker,altered_contract,state_path,'entry').returncode == 2
        cases += 1

    print(f"E6.1C_STATE_GATE_CASES={cases}")
    print("E6.1C_STATE_GATE_FAILED_EXPECTATIONS=0")
    print("E6.1C_STATE_GATE_NETWORK_CALLS=0")
    print("E6.1C_STATE_GATE_PHYSICAL_PUBLISHERS=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
