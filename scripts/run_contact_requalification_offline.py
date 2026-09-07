#!/usr/bin/env python3
"""Fixed local regression suite; no live checks, installation or robot commands."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TESTS = [
    'scripts/test_contact_audit.py',
    'scripts/test_contact_requalification.py',
    'scripts/test_clamp_photo_correspondence.py',
    'scripts/test_clamp_sensor_asymmetry.py',
    'scripts/test_clamp_simplified_model.py',
    'scripts/test_clamp_orientation_bound.py',
    'scripts/test_clamp_pessimistic_screen.py',
    'scripts/test_clamp_pessimistic_path.py',
    'scripts/test_home_group_timing.py',
    'scripts/test_home_posture_gate.py',
    'scripts/vla/test_vla_ready_entry_state_e6_1c.py',
]
SHELLS = [
    'scripts/vla/install_vla_recovery_task_e6_0n.sh',
    'scripts/vla/reload_vla_recovery_task_e6_0o.sh',
    'scripts/vla/patch_vla_ready_s2_waist_e6_0p.sh',
    'scripts/cruzr_recover_to_home.sh',
    'scripts/vla/install_vla_ready_entry_tasks_e6_1c.sh',
    'scripts/vla/reload_vla_ready_entry_tasks_e6_1c.sh',
    'scripts/vla/audit_vla_ready_entry_transition_e6_1c.sh',
]
INPUTS = TESTS + SHELLS + [
    'scripts/lib/cruzr_home_posture_gate.py',
    'scripts/lib/cruzr_contact_motion_lock.sh',
    'scripts/audit_clamp_mount_requalification.py',
    'scripts/audit_clamp_sensor_reference.py',
    'scripts/audit_clamp_photo_correspondence.py',
    'scripts/audit_clamp_outer_correspondence.py',
    'scripts/audit_clamp_sensor_asymmetry.py',
    'scripts/build_clamp_simplified_model.py',
    'scripts/audit_clamp_orientation_bound.py',
    'scripts/audit_clamp_pessimistic_screen.py',
    'scripts/audit_clamp_pessimistic_path.py',
    'scripts/vla/analyze_vla_fixture_collision_e4_1c.py',
    'scripts/audit_home_group_timing.py',
    'scripts/vla/check_vla_ready_entry_state_e6_1c.py',
    'scripts/vla/analyze_vla_ready_entry_transition_e6_1c.py',
    'scripts/vla/runtime/cruzr_s2_vla_ready_entry_transition_e6_1c.json',
    'config/clamp_mount_requalification.json',
    'config/clamp_photo_landmarks.json',
    'scripts/run_contact_requalification_offline.py',
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    # Reserve exclusively before work: preserve all prior reports.
    with args.output.open('x') as out:
        env = dict(os.environ, CRUZR_INTERNAL_ASKPASS='0', PYTHONDONTWRITEBYTECODE='1')
        commands = [[sys.executable, p] for p in TESTS]
        commands += [['bash', '-n', p] for p in SHELLS]
        commands += [['bash','scripts/cruzr_recover_to_home.sh','--self-test']]
        results = []
        for command in commands:
            try:
                run = subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,timeout=60)
                entry = dict(command=command,returncode=run.returncode,stdout=run.stdout,stderr=run.stderr)
            except (subprocess.TimeoutExpired,OSError) as exc:
                entry = dict(command=command,returncode=None,error=str(exc))
            results.append(entry)
            print(('OK ' if entry['returncode'] == 0 else 'FAILED ')+ ' '.join(command), flush=True)
        ok = all(r['returncode'] == 0 for r in results)
        result = dict(status='OFFLINE_REGRESSIONS_OK_PHYSICAL_BLOCKED' if ok else 'OFFLINE_REGRESSIONS_FAILED',
                      created_at_utc=datetime.now(timezone.utc).isoformat(),
                      checks=results,
                      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in INPUTS},
                      physical_authorized=False,
                      scope='fixed_local_tests_and_syntax_only_no_live_robot_checks',
                      not_covered=['physical_clamp_registration_and_full_support_volume',
                                   'actual_motion_interpolator_and_stop_envelope',
                                   'internal_boot_HOME_UI_PICO_raw_SDK',
                                   'installed_Vision_guard',
                                   'physical_inspection_or_current_robot_state'])
        json.dump(result,out,indent=2,allow_nan=False)
        out.write('\n')
    print(result['status'])
    print(args.output)
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
