#!/usr/bin/env python3
"""Finish a supported table74 deposit with one explicit supervised phase.

Use pin-relief first, then a separate open invocation from its successful trial
directory after physically checking that the pins are free. Default --plan is
offline and creates no files. --check checks installed files only, without
installing, checking live health or moving. --run installs the additive task,
checks live health through the existing runner and requests its physical token
before one action. No HOME, navigation, grasp or automatic phase chaining exists.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time

if __name__=='__main__' and not __package__:
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
    __package__='scripts.box_handling'

from . import scenario1_cli as cli
from . import scenario1_table74_current_release as release
from . import scenario1_table74_current_release_run as runner
from . import scenario1_table74_trial_install as installer
from . import scenario1_table74_recipe as recipe


HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PHASES={'pin-relief':'pin_relief','open':'lateral_open'}
PROFILE=HERE/'scenario1_table74_preparation.json'
SNAPSHOT=ROOT/'vendor/ubtech/cruzr_s2/snapshot_20260916/motion'


def parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--finish-deposit',action='store_true',required=True)
    p.add_argument('--table-height-cm',type=float,choices=(74.,),required=True)
    p.add_argument('--phase',choices=tuple(PHASES),required=True)
    p.add_argument('--after',type=Path,required=True,help='Authentic successful support/settle or pin-relief trial directory')
    mode=p.add_mutually_exclusive_group()
    mode.add_argument('--plan',action='store_true',help='Offline default: report current requirements and optional candidate')
    mode.add_argument('--check',action='store_true',help='Check installed files only; never install or move')
    mode.add_argument('--run',action='store_true',help='Install, perform live read-only preflight, then run this phase with a TTY token')
    p.add_argument('--supported',action='store_true',help='Current box is fully supported, flat and stable; arms do not carry its weight')
    p.add_argument('--tool-clearance-cm',type=float,help='Current entire-tool/table clearance: at least5cm before pin-relief, at least4cm before open')
    p.add_argument('--pin-exit-cm',type=float,help='Current required pin exit, positive and at most4cm; nominal pin-relief is4cm')
    p.add_argument('--path-clear',action='store_true',help='Current entire lateral10cm-per-side path is clear')
    p.add_argument('--pins-free',action='store_true',help='Required for open, after direct inspection following pin relief')
    p.add_argument('--operator-note',help='Optional current-state provenance, preserved literally; at most1500characters')
    p.add_argument('--evidence-dir',type=Path,help='New private artifact directory; never reuse an existing directory')
    return p


def reference_for(args,info,execution_policy=None):
    """Keep missing declarations false; no actionable reference is fabricated."""
    stage=PHASES[args.phase]
    expected=('support','settle') if stage=='pin_relief' else ('pin_relief',)
    if info['completed_stage']not in expected:
        raise ValueError('FINISH_PHASE_MISMATCH: phase does not follow its authenticated predecessor')
    if args.phase=='pin-relief' and args.pins_free:
        raise ValueError('--pins-free belongs only to --phase open; no pin-relief replay or skip is inferred')
    if args.operator_note is not None and (not args.operator_note.strip() or len(args.operator_note)>1500):
        raise ValueError('--operator-note must contain nonblank text and at most1500characters')
    if execution_policy is not None:
        recipe.assert_policy(execution_policy)
        if args.supported or args.pins_free or args.path_clear or args.operator_note is not None:
            raise ValueError('Recipe mode cannot claim fresh operator support, pin or path declarations')
        fixed=execution_policy.facts()
        clearance=fixed['tool_clearance_before_relief_cm'if stage=='pin_relief'else'tool_clearance_after_relief_cm']
        pin_exit=fixed['required_pin_exit_cm']
        if (args.tool_clearance_cm is not None and args.tool_clearance_cm!=clearance or
                args.pin_exit_cm is not None and args.pin_exit_cm!=pin_exit):
            raise ValueError('Release dimensions differ from the fixed recorded recipe')
        provenance=execution_policy.as_dict()
        facts=dict(supported=False,tool_clearance_cm=clearance,pin_exit_cm=pin_exit,
            path_clear=False,pins_free=False,support_assumed=fixed['support_assumed'],
            lateral_path_assumed_clear=fixed['lateral_path_assumed_clear'],
            pins_free_assumed=stage=='lateral_open'and fixed['pins_free_assumed'],
            current_physical_measurement=False,assumption_provenance=provenance)
        reference=dict(version=release.RECIPE_BUILDER_VERSION,stage=stage,surface_height_m=.74,
            predecessor_bundle_id=info['bundle_id'],predecessor_goal_id=info['goal_id'],
            operator_support_confirmed=False,tool_table_clearance_m=clearance/100.,
            required_pin_exit_m=pin_exit/100.,operator_pins_free=False,lateral_path_clear=False,
            evidence='optimistic table74; historical recipe assumptions, no new physical observation; predecessor_sha256='+info['predecessor_sha256'],
            scope='recorded_recipe_supported_box_assumption_only',assumption_provenance=provenance)
        return release.validate_reference(reference),[],facts
    missing=[]
    if not args.supported:missing.append('--supported')
    if args.tool_clearance_cm is None:missing.append('--tool-clearance-cm')
    if args.pin_exit_cm is None:missing.append('--pin-exit-cm')
    if not args.path_clear:missing.append('--path-clear')
    if args.phase=='open' and not args.pins_free:missing.append('--pins-free')
    facts=dict(supported=args.supported,tool_clearance_cm=args.tool_clearance_cm,
        pin_exit_cm=args.pin_exit_cm,path_clear=args.path_clear,pins_free=args.pins_free)
    if missing:return None,missing,facts
    evidence='optimistic --finish-deposit; explicit current operator declarations; predecessor_sha256='+info['predecessor_sha256']+'; facts='+release.canonical(facts)
    if args.operator_note is not None:evidence+='; operator_note='+args.operator_note
    reference=dict(version=release.BUILDER_VERSION,stage=stage,surface_height_m=.74,
        predecessor_bundle_id=info['bundle_id'],predecessor_goal_id=info['goal_id'],
        operator_support_confirmed=args.supported,tool_table_clearance_m=args.tool_clearance_cm/100.,
        required_pin_exit_m=args.pin_exit_cm/100.,operator_pins_free=args.pins_free,
        lateral_path_clear=args.path_clear,evidence=evidence,scope='current_supported_box_only')
    return release.validate_reference(reference),[],facts


def build_bundle(reference):
    return release.build_bundle(reference,
        (SNAPSHOT/'tasks/wrc_cruzr/put_cruzr_wrc_low.xml').read_text(),
        (SNAPSHOT/'meta_clamp/wrc/open_arm_cruzr.yaml').read_text())


def installer_call(bundle_path,operation,evidence,bundle):
    """Use the existing additive installer; its receipt must match this phase."""
    result=subprocess.run([sys.executable,'-B',str(Path(installer.__file__)),
        '--bundle',str(bundle_path),'--'+operation],capture_output=True,text=True,timeout=210)
    (evidence/('installer-'+operation+'.stdout')).write_text(result.stdout)
    (evidence/('installer-'+operation+'.stderr')).write_text(result.stderr)
    if result.returncode:
        raise RuntimeError('FINISH_INSTALLER_FAILED: '+operation+' rc='+str(result.returncode))
    try:receipt=json.loads(result.stdout)
    except (ValueError,TypeError)as exc:raise RuntimeError('FINISH_INSTALLER_RECEIPT_INVALID')from exc
    expected_status='checked' if operation=='check' else 'installed'
    if (not isinstance(receipt,dict) or receipt.get('status')!=expected_status or
            receipt.get('id')!=bundle['manifest']['id'] or receipt.get('phase')!=release.PHASE or
            type(receipt.get('movement_commands'))is not int or receipt['movement_commands']!=0 or
            type(receipt.get('restarts'))is not int or receipt['restarts']!=0 or
            operation=='check' and type(receipt.get('installed'))is not bool):
        raise RuntimeError('FINISH_INSTALLER_RECEIPT_MISMATCH')
    cli.atomic_json(evidence/('installer-'+operation+'.json'),receipt)
    return receipt


def main(argv=None,*,execution_policy=None):
    if execution_policy is not None:recipe.assert_policy(execution_policy)
    args=parser().parse_args(argv)
    profile=json.loads(PROFILE.read_text())
    proof,info,hashes=runner.load_predecessor(args.after,profile)
    reference,missing,facts=reference_for(args,info,execution_policy)
    candidate=build_bundle(reference)if reference is not None else None
    if candidate is not None:runner.validate_entry(proof,profile,candidate)
    report=dict(mode='run'if args.run else'check'if args.check else'plan',phase=args.phase,
        source=str(args.after.resolve()),predecessor_sha256=info['predecessor_sha256'],
        predecessor_bundle_id=info['bundle_id'],predecessor_goal_id=info['goal_id'],
        declarations=facts,operator_note=args.operator_note,requirements_missing=missing,operator_reference_complete=not missing,
        reference_created=False,installed=False,health_ready=False,movement_commands_sent=0,
        ordinary_deposit_authorized=False,automatic_retries=0,next_phase_automatic=False,
        task_name=candidate['task_name']if candidate else None,
        bundle_id=candidate['manifest']['id']if candidate else None)
    if execution_policy is not None:
        report.update(operator_reference_complete=False,recipe_reference_complete=not missing,
            assumption_provenance=execution_policy.as_dict(),current_physical_measurement=False,
            duplicate_standalone_live_check_omitted=True,
            live_preflight_performed_by='physical_phase_runner')
    if not args.run and not args.check:
        print(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False));return 0
    if missing:
        print(json.dumps(dict(report,status='CURRENT_PHYSICAL_DECLARATIONS_REQUIRED'),indent=2,ensure_ascii=False))
        return 78
    if args.run and execution_policy is None and not sys.stdin.isatty():raise RuntimeError('A physical operator and TTY confirmation are required')
    # Re-read before writing or contacting the robot. A previous action may
    # have consumed this source between argument parsing and artifact creation.
    current,_,current_hashes=runner.load_predecessor(args.after,profile)
    if current!=proof or current_hashes!=hashes:raise RuntimeError('FINISH_PREDECESSOR_CHANGED')
    evidence=args.evidence_dir or ROOT.parent/'Humanoide-vla-evidence'/(
        time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'_TABLE74_FINISH_'+args.phase+'_'+str(os.getpid()))
    evidence.mkdir(parents=True,exist_ok=False);os.chmod(evidence,0o700)
    bundle_path=evidence/'bundle.json'
    cli.atomic_json(evidence/'reference.json',reference);cli.atomic_json(bundle_path,candidate)
    recorded_ns=time.time_ns()
    report.update(reference_created=True,status='prepared',artifact=str(evidence.resolve()),
        declarations_kind='explicit_current_operator_state_not_sensor_measurements',
        created_ns=recorded_ns,declarations_recorded_ns=recorded_ns,
        recording_timestamp_verifies_physical_state=False,
        original_checkpoint_modified=False,source_journal_consumed=False)
    if execution_policy is not None:
        report.update(declarations_kind='historical_recipe_assumptions_not_current_operator_state',
            declarations_recorded_ns=None,recipe_recorded_ns=recorded_ns)
    cli.atomic_json(evidence/'supervisor.json',report)
    cli.atomic_json(evidence/'source-sha256.json',dict(finish=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        optimistic_wrapper=hashlib.sha256((ROOT/'scripts/optimistic_scenario1.sh').read_bytes()).hexdigest(),
        predecessor_files=hashes,bundle=hashlib.sha256(release.canonical(candidate).encode()).hexdigest()))
    print('Finalización '+args.phase+'; artefacto: '+str(evidence),flush=True)
    try:
        if args.check:
            receipt=installer_call(bundle_path,'check',evidence,candidate)
            report.update(status='FILES_VERIFIED'if receipt['installed']else'INSTALLATION_PENDING',
                          installed=receipt['installed'],health_ready=False)
            cli.atomic_json(evidence/'supervisor.json',report)
            print(json.dumps(report,indent=2,ensure_ascii=False))
            return 0 if receipt['installed'] else 55
        installer_call(bundle_path,'install',evidence,candidate)
        report.update(status='installed',installed=True)
        cli.atomic_json(evidence/'supervisor.json',report)
        common=['--after',str(args.after),'--bundle',str(bundle_path)]
        if execution_policy is None:
            check_args=['--check',*common,'--evidence-dir',str(evidence/'technical-check')]
            if runner.cli_main(check_args)!=0:raise RuntimeError('FINISH_LIVE_CHECK_FAILED')
            report.update(status='live_check_passed',health_ready=True)
            cli.atomic_json(evidence/'supervisor.json',report)
            result=runner.cli_main(['--run',*common,'--evidence-dir',str(evidence/'physical-run')])
        else:
            # --run performs the same fresh Runtime.ready gate immediately
            # before dispatch. Do not create a second read-only session first.
            result=runner.cli_main(['--run',*common,'--evidence-dir',str(evidence/'physical-run')],
                execution_policy=execution_policy)
        if result!=0:raise RuntimeError('FINISH_PHASE_FAILED: rc='+str(result))
        report.update(status='phase_completed',source_journal_consumed=True,
            physical_result=str((evidence/'physical-run').resolve()),physical_release_measured=False,
            movement_commands_sent=1,health_ready=True)
        cli.atomic_json(evidence/'supervisor.json',report)
        print('Fase '+args.phase+' terminada. '+('Se conserva la hipótesis de la receta registrada.'if execution_policy is not None else'Compruebe el estado físico; no se ejecutó HOME ni otra fase.'))
        if args.phase=='pin-relief'and execution_policy is None:
            print('Para abrir use otra invocación con --phase open --after '+shlex.quote(str(evidence/'physical-run'))+
                  ' y nuevas declaraciones actuales, incluyendo --pins-free.')
        return 0
    except BaseException as exc:
        report.update(status='interrupted',error=str(exc)or type(exc).__name__,
                      source_journal_consumed=(args.after/'trial.json.consumed.json').exists(),health_ready=False)
        if report['source_journal_consumed']:report['movement_commands_sent']=None
        cli.atomic_json(evidence/'supervisor.json',report)
        raise


def entrypoint(argv=None):
    try:return main(argv)
    except (Exception,KeyboardInterrupt)as exc:
        print('FINISH_DEPOSIT_BLOCKED: '+str(exc),file=sys.stderr)
        print('Sin reintento, HOME ni avance automático de fase.',file=sys.stderr)
        return 78


if __name__=='__main__':raise SystemExit(entrypoint())
