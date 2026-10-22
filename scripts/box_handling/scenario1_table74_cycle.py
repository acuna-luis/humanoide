"""One supervised table74 cycle using separately authenticated native phases.

The pending ordinary deposit profile is never promoted. Geometry, physical
support and free pins require new operator observations at phase boundaries;
native SUCCEED cannot establish these facts. No automatic retry exists.
"""
from contextlib import contextmanager
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = 'scripts.box_handling'

from . import scenario1_cli as cli
from . import scenario1_contract as contract
from . import scenario1_table74_current_trial as approach
from . import scenario1_table74_current_trial_run as approach_run
from . import scenario1_table74_current_lower as lower
from . import scenario1_table74_current_lower_run as lower_run
from . import scenario1_table74_current_release_run as release_run
from . import scenario1_table74_finish as finish
from . import scenario1_table74_home as home
from . import scenario1_table74_trial_install as installer

HERE = Path(__file__).resolve().parent
PROFILE = HERE/'scenario1_table74_preparation.json'
SNAPSHOT = cli.ROOT/'vendor/ubtech/cruzr_s2/snapshot_20260916/motion'
LOCK = Path('/tmp/cruzr-table74-supervised-cycle.lock')


class SafePause(RuntimeError):
    """A physical phase boundary needs a different, separately reviewed action."""


def guard(stop):
    if stop is not None and stop.requested:
        raise SafePause('Parada solicitada; no se iniciará otra fase')


@contextmanager
def interruptible():
    # The outer pickup handler finishes its current stage. Phase runners need
    # KeyboardInterrupt instead so their own finally blocks close the worker.
    previous = signal.signal(signal.SIGINT, signal.default_int_handler)
    try:
        yield
    finally:
        signal.signal(signal.SIGINT, previous)


def observe(message, stop):
    guard(stop)
    with interruptible():
        answer = input(message+'\n> ').strip()
    guard(stop)
    return answer


def confirm(message, token, stop):
    if observe(message+' Escriba '+token+'.', stop) != token:
        raise SafePause('Confirmación física no recibida: '+token)


def number(message, minimum, maximum, stop):
    try:
        result = float(observe(message, stop).replace(',', '.'))
    except ValueError as exc:
        raise SafePause('Medición actual no válida') from exc
    if not math.isfinite(result) or not minimum <= result <= maximum:
        raise SafePause('Medición actual fuera de los límites admitidos')
    return result


def validate_args(args):
    if (args.policy != 'assume' or args.execution_profile != 'optimistic_v1' or
            args.table_height_cm != 74. or args.stop_after != 'cycle'):
        raise ValueError('El supervisor requiere optimistic, mesa74 y ciclo completo')
    if getattr(args, 'cycle', False):
        raise ValueError('Mesa74 permite un único ciclo supervisado; quite --cycle')
    if args.from_stage or args.recovery_confirmed or args.box_state not in (None, 'held'):
        raise ValueError('El supervisor sólo admite reanudación limpia; no saltos ni recuperación de estado desconocido')
    if args.box_state and not args.resume:
        raise ValueError('--box-state requiere --resume')
    if getattr(args, 'benchmark_checks', 0):
        raise ValueError('--benchmark-checks no pertenece al ciclo supervisado74')
    if args.wifi:
        raise ValueError('El ciclo74 completo requiere la conexión Motion Ethernet actual; --wifi sigue disponible en los segmentos parciales')


def plan(args):
    return dict(mode='plan', application='table74_supervised_cycle', cycles=1,
        pickup_stop_after='navigate_put1', pickup_and_alignment_unchanged=True,
        box_alignment_attempts=args.box_alignment_attempts, arm_task_unchanged=True,
        stages=['pickup_to_put1', 'approach_absolute_z_0.94', 'precontact_14cm',
                'support_5cm', 'optional_single_settle_1cm', 'pin_relief_4cm',
                'lateral_open_10cm_per_side', 'empty_measured_home'],
        operator_gates=['CONTINUAR74', 'HUECO19', 'HUECO5', 'APOYADA|HUECO1|PARCIAL',
                        'actual_clearance_at_least_5cm_and_pin_exit_at_most_4cm',
                        'fresh_free_pins_and_clearance_at_least_4cm', 'LIBRE', 'HOME74'],
        phase_runner_tokens_preserved=True, automatic_retries=0,
        ordinary_deposit_profile_qualified=False, support_measured_by_sensors=False,
        qualification='supervised; manual assistance must be recorded explicitly',
        native_success_does_not_prove_support=True, commands_sent=0, files_created=0,
        resume_source=str(args.resume) if args.resume else None,
        resume_source_validated=False, default_action='read_only_check')


def clean_source(path, profile, *, at_put1=False):
    path = Path(path)
    if path.with_name(path.name+'.consumed.json').exists():
        raise ValueError('El checkpoint ya fue consumido; no se repite la recogida')
    source = contract.validate_checkpoint(json.loads(path.read_text()), profile)
    progress = contract.progress_index(source)
    if (source['profile_id'] != approach_run.PROFILE_ID or
            source['profile_sha256'] != approach_run.PROFILE_SHA256 or
            source.get('policy') != 'assume' or contract.execution_profile(source) != 'optimistic_v1' or
            source['box_state'] != 'held' or source['failure'] is not None or
            source['in_flight'] is not None or progress not in (4, 5, 6)):
        raise ValueError('Se requiere un checkpoint auténtico, limpio y con caja sujeta tras verify_held')
    if at_put1 and (progress != 6 or source['stop_after'] != 'navigate_put1'):
        raise ValueError('La recogida no dejó su checkpoint limpio de llegada put1')
    return source


def pickup(args, stop, evidence):
    child = copy.deepcopy(args)
    child.stop_after = 'put1'
    child.evidence_dir = evidence
    child.cycle = False
    child.plan = False
    child.run = cli.is_moving(args)
    child.check = not child.run
    code = cli._main(child, stop)
    if code:
        raise RuntimeError('PICKUP_FAILED: rc='+str(code)+'; consulte '+str(evidence))
    guard(stop)
    return evidence/'checkpoint.json'


def build_approach(source):
    reference = dict(version=1, mode='operator_assumed_vendor45',
        source_checkpoint_sha256=hashlib.sha256(json.dumps(source, sort_keys=True,
            separators=(',', ':'), allow_nan=False).encode()).hexdigest(),
        surface_height_m=.74, reference_surface_height_m=.45,
        scope='current_held_put1_only',
        evidence='Supervised table74; explicit nominal vendor45 assumption; actual geometry remains subject to phase checks')
    return approach.build_bundle(reference,
        (SNAPSHOT/'tasks/wrc_cruzr/put_cruzr_wrc_low.xml').read_text(),
        (SNAPSHOT/'meta_clamp/wrc/put_cruzr_wrc_low.yaml').read_text())


def installer_call(bundle_path, operation, evidence, bundle):
    response = subprocess.run([sys.executable, '-B', str(Path(installer.__file__)),
        '--bundle', str(bundle_path), '--'+operation], capture_output=True, text=True, timeout=210)
    (evidence/('installer-'+operation+'.stdout')).write_text(response.stdout)
    (evidence/('installer-'+operation+'.stderr')).write_text(response.stderr)
    if response.returncode:
        raise RuntimeError('TABLE74_INSTALLER_FAILED: '+operation+' rc='+str(response.returncode))
    receipt = json.loads(response.stdout)
    if (not isinstance(receipt, dict) or receipt.get('status') != ('checked' if operation == 'check' else 'installed') or
            receipt.get('id') != bundle['manifest']['id'] or receipt.get('phase') != bundle['manifest']['phase'] or
            type(receipt.get('movement_commands')) is not int or receipt['movement_commands'] != 0 or
            type(receipt.get('restarts')) is not int or receipt['restarts'] != 0 or
            operation == 'check' and type(receipt.get('installed')) is not bool):
        raise ValueError('TABLE74_INSTALLER_RECEIPT_MISMATCH')
    cli.atomic_json(evidence/('installer-'+operation+'.json'), receipt)
    return receipt


def completed(after, profile, stage):
    loader = lower_run.load_predecessor if stage in ('approach', 'precontact') else release_run.load_predecessor
    _, info, _ = loader(after, profile)
    if info['completed_stage'] != stage:
        raise ValueError('La prueba terminada no corresponde a la fase '+stage)
    return info


def archive_installation(bundle, evidence):
    """Copy and authenticate the installer's rollback package outside the robot."""
    package = str(installer.EVIDENCE_ROOT/bundle['manifest']['id'])
    source = '''import json,pathlib,sys
p=pathlib.Path(sys.argv[1]);r={}
for name in ('bundle.json','manifest.json','originals.json','install-receipt.json'):
 f=p/name
 if any(x.is_symlink() for x in (f,*f.parents)) or not f.is_file():raise ValueError('unsafe package file')
 if f.stat().st_size>4194304:raise ValueError('package file too large')
 r[name]=f.read_text()
print(json.dumps(r))
'''
    response = home.execute(['python3', '-B', '-c', source, package])
    raw = json.loads(response['stdout'])
    names = {'bundle.json', 'manifest.json', 'originals.json', 'install-receipt.json'}
    if not isinstance(raw, dict) or set(raw) != names or any(type(v) is not str for v in raw.values()):
        raise ValueError('TABLE74_BACKUP_PACKAGE_INVALID')
    objects = {name: json.loads(value) for name, value in raw.items()}
    receipt = objects['install-receipt.json']
    if (objects['bundle.json'] != bundle or objects['manifest.json'] != bundle['manifest'] or
            receipt.get('id') != bundle['manifest']['id'] or receipt.get('status') != 'installed' or
            receipt.get('phase') != bundle['manifest']['phase'] or receipt.get('package') != package or
            receipt.get('originals_overwritten') is not False or
            type(receipt.get('movement_commands')) is not int or receipt['movement_commands'] != 0 or
            type(receipt.get('restarts')) is not int or receipt['restarts'] != 0):
        raise ValueError('TABLE74_BACKUP_PACKAGE_MISMATCH')
    expected = bundle['dependencies']
    originals = objects['originals.json']
    if set(originals) != set(expected):
        raise ValueError('TABLE74_BACKUP_DEPENDENCIES_DIFFER')
    for path, item in originals.items():
        if not isinstance(item, dict) or item.get('sha256') != expected[path]:
            raise ValueError('TABLE74_BACKUP_DEPENDENCY_HASH_MISMATCH')
        if 'text' in item and hashlib.sha256(item['text'].encode()).hexdigest() != expected[path]:
            raise ValueError('TABLE74_BACKUP_ORIGINAL_TEXT_MISMATCH')
    destination = evidence/'robot-installation-backup'
    destination.mkdir(exist_ok=False)
    for name, value in raw.items():
        (destination/name).write_text(value)
    cli.atomic_json(destination/'copy-receipt.json', dict(remote_package=package,
        start_ns=response['start_ns'], finished_ns=response['finished_ns'],
        sha256={name: hashlib.sha256(value.encode()).hexdigest() for name, value in raw.items()},
        verified=True, location='PC; outside robot', movement_commands_sent=0))


def execute_phase(kind, after, source, evidence, wifi=False, *, check_only=False):
    """Use existing authenticators, installer, live checks and one-shot runners."""
    profile = json.loads(PROFILE.read_text())
    evidence.mkdir(parents=True, exist_ok=False)
    os.chmod(evidence, 0o700)
    if kind == 'approach':
        checkpoint = clean_source(source, profile, at_put1=True)
        bundle = build_approach(checkpoint)
        approach_run.prepare_entry(checkpoint, profile, bundle)
        runner, common = approach_run, ['--resume', str(source)]
    else:
        proof, info, _ = lower_run.load_predecessor(after, profile)
        gap, clearance = dict(precontact=(.19, .05), support=(.05, 0.), settle=(.01, 0.))[kind]
        reference = dict(version=1, stage=kind, gap_above_surface_m=gap,
            target_clearance_m=clearance, surface_height_m=.74,
            predecessor_bundle_id=info['bundle_id'], predecessor_goal_id=info['goal_id'],
            scope='current_post_trial_box_only', evidence='Supervised cycle; new explicit geometry observation before '+kind)
        bundle = lower.build_bundle(reference,
            (SNAPSHOT/'tasks/wrc_cruzr/put_cruzr_wrc_low.xml').read_text(),
            (SNAPSHOT/'meta_clamp/wrc/put_cruzr_wrc_low.yaml').read_text())
        lower_run.validate_entry(proof, profile, bundle)
        runner, common = lower_run, ['--after', str(after)]
    bundle_path = evidence/'bundle.json'
    cli.atomic_json(bundle_path, bundle)
    cli.atomic_json(evidence/'reference.json', bundle['review']['reference'])
    cli.atomic_json(evidence/'sources.json', dict(builder=bundle['manifest'],
        cycle_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    receipt = installer_call(bundle_path, 'check', evidence, bundle)
    if check_only and not receipt['installed']:
        print('INSTALLATION_PENDING: no se instaló ni se comprobó salud; '+str(evidence))
        return 55
    if not check_only and not receipt['installed']:
        installer_call(bundle_path, 'install', evidence, bundle)
    if not check_only:
        archive_installation(bundle, evidence)
    common += ['--bundle', str(bundle_path)] + (['--wifi'] if wifi else [])
    with interruptible():
        result = runner.cli_main(['--check', *common, '--evidence-dir', str(evidence/'technical-check')])
        if result:
            raise RuntimeError('TABLE74_PHASE_CHECK_FAILED: '+kind+' rc='+str(result))
        if check_only:
            return 0
        result = runner.cli_main(['--run', *common, '--evidence-dir', str(evidence/'physical-run')])
        if result:
            raise RuntimeError('TABLE74_PHASE_FAILED: '+kind+' rc='+str(result))
    output = evidence/'physical-run'
    completed(output, profile, kind)
    return output


def stage_release(arguments, evidence):
    """Keep a PC rollback package before finish.main can dispatch its action."""
    args = finish.parser().parse_args(arguments)
    profile = json.loads(PROFILE.read_text())
    proof, info, _ = release_run.load_predecessor(args.after, profile)
    reference, missing, _ = finish.reference_for(args, info)
    if missing:
        raise ValueError('Current release declarations are incomplete')
    bundle = finish.build_bundle(reference)
    release_run.validate_entry(proof, profile, bundle)
    evidence.mkdir(parents=True, exist_ok=False)
    os.chmod(evidence, 0o700)
    bundle_path = evidence/'bundle.json'
    cli.atomic_json(bundle_path, bundle)
    cli.atomic_json(evidence/'reference.json', reference)
    receipt = installer_call(bundle_path, 'check', evidence, bundle)
    if not receipt['installed']:
        installer_call(bundle_path, 'install', evidence, bundle)
    archive_installation(bundle, evidence)


def release_phase(after, evidence, stage, clearance, pin_exit, pins_free=False):
    arguments = ['--finish-deposit', '--table-height-cm', '74', '--phase', stage,
        '--after', str(after), '--run', '--supported', '--tool-clearance-cm', str(clearance),
        '--pin-exit-cm', str(pin_exit), '--path-clear', '--evidence-dir', str(evidence),
        '--operator-note', 'Fresh supervised-cycle physical declarations; support and clearance are operator observations, not inferred from native success']
    if pins_free:
        arguments += ['--pins-free']
    with interruptible():
        if evidence.exists():
            raise ValueError('La evidencia de liberación debe ser nueva')
        stage_release(arguments, evidence.with_name(evidence.name+'-staging'))
        code = finish.main(arguments)
    if code:
        raise RuntimeError('TABLE74_RELEASE_FAILED: '+stage+' rc='+str(code))
    return evidence/'physical-run'


def run(args, stop):
    validate_args(args)
    if args.plan:
        print(json.dumps(plan(args), indent=2, ensure_ascii=False))
        return 0
    moving = not args.check and bool(args.run or args.resume)
    if moving and not sys.stdin.isatty():
        raise RuntimeError('El ciclo supervisado requiere operador presencial y terminal TTY')
    print('MESA74_CICLO_SUPERVISADO: '+('UN ciclo con confirmaciones de apoyo, pines y HOME' if moving
          else 'comprobación de lectura; sin movimiento'), flush=True)
    profile = json.loads(PROFILE.read_text())
    source = clean_source(args.resume, profile) if args.resume else None
    evidence = args.evidence_dir or cli.ROOT.parent/'Humanoide-vla-evidence'/(
        time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())+'_TABLE74_SUPERVISED_CYCLE_'+str(os.getpid()))
    lock = installer._lock(LOCK)
    journal = dict(artifact='table74_supervised_cycle', executable=False, status='prepared',
        qualification='supervised; operator support observations; manual assistance requires a new recorded observation',
        ordinary_profile_qualified=False, automatic_retry=False, created_ns=time.time_ns(),
        phase_boundary=None, in_flight=None, after=None, physical_support_measured=False)
    created = False
    try:
        evidence.mkdir(parents=True, exist_ok=False)
        created = True
        os.chmod(evidence, 0o700)
        def record(**values):
            journal.update(values, updated_ns=time.time_ns())
            cli.atomic_json(evidence/'cycle.json', journal)
        record()
        if not moving:
            if source is not None and contract.progress_index(source) == 6:
                code = execute_phase('approach', None, args.resume, evidence/'approach-check',
                    args.wifi, check_only=True)
                record(status='installation_pending' if code == 55 else 'checked',
                    health_ready=code == 0, health_scope='current_held_put1_approach_only',
                    movement_commands_sent=0)
                if code == 0:
                    print('MESA74_CHECK_OK: llegada actual y aproximación comprobadas; sin movimiento ni instalación')
                return code
            pickup(args, stop, evidence/'pickup-check')
            record(status='checked', health_scope='pickup_to_put1_only', movement_commands_sent=0)
            print('MESA74_CHECK_OK: segmento de recogida comprobado; apoyo, pines y fases posteriores requieren nuevas comprobaciones; sin movimiento')
            return 0
        confirm(('Reanudación con caja sujeta estable; no se repetirá el agarre. ' if source else
                 'Abrazaderas vacías, HOME y pila estable. ')+
            'Confirme mesa74, recorrido libre, batería suficiente, cargador fuera, paros liberados, '
            'ruedas en navegación, otros mandos detenidos y persona junto al paro. '
            'Acepta aproximación nominal desde referencia vendor45, con pausas de medida y apoyo.', 'CONTINUAR74', stop)
        if source is not None and contract.progress_index(source) == 6:
            source_path = args.resume
        else:
            record(in_flight='pickup_to_put1')
            source_path = pickup(args, stop, evidence/'pickup')
        clean_source(source_path, profile, at_put1=True)
        record(phase_boundary='held_put1', in_flight=None, after=str(source_path))
        def phase(kind, after=None):
            guard(stop)
            record(in_flight=kind)
            output = execute_phase(kind, after, source_path, evidence/kind, args.wifi)
            record(phase_boundary=kind, in_flight=None, after=str(output))
            guard(stop)
            return output
        after = phase('approach')
        confirm('Mida ambos lados: hueco19cm igual, caja estable y ningún punto en contacto. '
                'Si difiere, pare para revisar geometría.', 'HUECO19', stop)
        after = phase('precontact', after)
        confirm('Mida ambos lados: hueco5cm igual, caja estable y ningún punto en contacto.', 'HUECO5', stop)
        after = phase('support', after)
        state = observe('Inspeccione toda la base: APOYADA = apoyo plano completo, estable y sin peso en brazos; '
                        'HUECO1 = hueco1cm uniforme en ambos lados sin contacto en esquinas; '
                        'PARCIAL = contacto parcial o cualquier otro estado.', stop)
        record(operator_support_observation=state, observation_recorded_ns=time.time_ns())
        if state == 'HUECO1':
            after = phase('settle', after)
            confirm('Compruebe apoyo plano completo de toda la caja, estable y sin peso en brazos. '
                    'Un apoyo parcial exige parar; no se bajará otra vez.', 'APOYADA', stop)
        elif state != 'APOYADA':
            raise SafePause('Apoyo completo no confirmado; se conserva la postura, sin apertura ni HOME')
        record(operator_support_confirmed=True, support_recorded_ns=time.time_ns())
        clearance = number('Holgura ACTUAL mínima entre todo el útil y la mesa, en cm (mínimo5):', 5., 100., stop)
        pin_exit = number('Salida de pin necesaria ACTUAL, en cm (positiva y como máximo4):', 0.000001, 4., stop)
        confirm('Recorrido lateral completo10cm por lado libre; caja sigue totalmente apoyada.', 'DESPEJADO10', stop)
        guard(stop)
        record(in_flight='pin_relief', current_clearance_cm=clearance, required_pin_exit_cm=pin_exit)
        after = release_phase(after, evidence/'pin-relief', 'pin-relief', clearance, pin_exit)
        record(phase_boundary='pin_relief', in_flight=None, after=str(after))
        guard(stop)
        confirm('Inspeccione ambos pines tras alivio: completamente fuera; caja plana, apoyada y estable.', 'PINES_LIBRES', stop)
        clearance = number('Holgura ACTUAL tras alivio de todo el útil a la mesa, en cm (mínimo4):', 4., 100., stop)
        confirm('Compruebe de nuevo todo el recorrido lateral10cm por lado libre.', 'DESPEJADO10', stop)
        record(in_flight='lateral_open', current_clearance_cm=clearance)
        after = release_phase(after, evidence/'open', 'open', clearance, pin_exit, pins_free=True)
        record(phase_boundary='lateral_open', in_flight=None, after=str(after))
        guard(stop)
        confirm('Caja apoyada y estable; ambos útiles vacíos, pines libres y trayectoria HOME completa despejada.', 'LIBRE', stop)
        record(in_flight='home')
        with interruptible():
            result = home.run(after=after, evidence=evidence/'home', wifi=args.wifi)
        if not isinstance(result, dict) or result.get('phase') != 'succeeded' or result.get('measured_home') is not True:
            raise RuntimeError('HOME no tiene confirmación terminal y postura medida')
        record(status='succeeded', phase_boundary='measured_home', in_flight=None, home=result)
        print('Ciclo74 supervisado terminado; HOME medido. Evidencia: '+str(evidence))
        return 0
    except (Exception, KeyboardInterrupt) as exc:
        journal.update(status='paused' if isinstance(exc, SafePause) else 'interrupted',
            error=str(exc) or type(exc).__name__, updated_ns=time.time_ns(),
            next_action='review last authenticated phase; no automatic retry or HOME')
        if created:
            cli.atomic_json(evidence/'cycle.json', journal)
        print('CICLO74_DETENIDO: '+journal['error']+'; evidencia: '+str(evidence), file=sys.stderr)
        if journal['after']:
            print('Última frontera: '+str(journal['after'])+'; compruebe consumo y estado físico antes de reanudar.', file=sys.stderr)
        return 55 if isinstance(exc, SafePause) else 130 if isinstance(exc, KeyboardInterrupt) else 78
    finally:
        lock.close()
