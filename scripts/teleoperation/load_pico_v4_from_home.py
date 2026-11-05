#!/usr/bin/env python3
"""Transición supervisada y única a PICO v4. Sin START PICO ni HOME automático.

Sólo ejecutar con supervisión física actual. No reintentar tras un resultado
incierto. El monitor informa pero no puede confirmar ni garantizar parada física.
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.hands.switch_effector import Transport, snapshots, loaded, safety, pose, battery, native, json_message
from scripts.lib.cruzr_home_posture_gate import classify
from scripts.teleoperation.pico_cc_mode import call

SHA = '01a5ca8acba16bbe136a3bdbcb4a593667d672f8ee9613b98631699fc429b582'
CONFIG = '/opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config/meta_teleoperation/cruzr_v4_pico_tele.yaml'
FAULT = re.compile(r'jump command|SAFEOP ERROR|excessive force|MoveToGoalFailed|servo fault|ethercat.*(?:error|fault)', re.I)


def run_local(args, env=None, timeout=60):
    r = subprocess.run(args, capture_output=True, text=True, env=env, timeout=timeout)
    if r.returncode:
        raise RuntimeError('Comprobación local fallida: '+shlex.join(args)+'\n'+r.stdout+r.stderr)
    return r.stdout


def read_topic(t, topic, timeout=12):
    shell = ('source /opt/ros/humble/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; '
             f'timeout {timeout-2} ros2 topic echo --once --no-daemon '+shlex.quote(topic))
    return t.run('motion', ['docker','exec',t.ros_container,'bash','-lc',shell], timeout+5)


def action_idle(text):
    # Empty and structured status lists are valid; missing/malformed data is not.
    if not re.search(r'(?m)^status_list:\s*(?:\[\])?\s*$', text):
        raise RuntimeError('Estado de acción ausente o inválido')
    statuses=re.findall(r'(?m)^\s*status:\s*(\d+)\s*$',text)
    goals=re.findall(r'(?m)^\s*-\s*goal_info:\s*$',text)
    explicitly_empty=bool(re.search(r'(?m)^status_list:[ \t]*\[\][ \t]*$',text))
    if explicitly_empty and goals:
        raise RuntimeError('Lista de acciones contradictoria')
    if not goals and not explicitly_empty:
        raise RuntimeError('Lista de acciones vacía sin confirmación explícita')
    if len(statuses)!=len(goals) or any(int(s)>6 for s in statuses):
        raise RuntimeError('Lista de acciones incompleta o inválida')
    if any(int(s) in (0,1,2,3) for s in statuses):
        raise RuntimeError('Acción de manipulación activa o desconocida')


def hands(t):
    code=(ROOT/'scripts/teleoperation/check_pico_v4_hand_states.py').read_text()
    shell=('source /opt/ros/humble/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; '
           'timeout 12 python3 -c '+shlex.quote(code))
    data=t.run('motion',['docker','exec',t.ros_container,'bash','-lc',shell],20)
    if 'V4_HAND_STATES_OK=' not in data: raise RuntimeError('Estados de manos no confirmados')
    return data


def sample_still(t, app):
    text=native(t, app, 'rosa topic echo --once --no-daemon --qos-reliability best_effort /mc/actuator_state')
    msg=json_message(text)
    report=classify(msg, .02)
    stamp=msg['header']['stamp']
    timestamp=stamp['sec']*1_000_000_000+stamp['nanosec']
    now=int(t.run('motion',['date','+%s%N']).strip())
    if not 0 <= now-timestamp <= 2_000_000_000: raise RuntimeError('Muestra de actuadores obsoleta')
    return report,timestamp


class Monitor:
    def __init__(self, evidence, containers):
        self.evidence=evidence
        self.processes=[]
        self.ready=[]
        self.faults=[]
        self.env=dict(os.environ, CRUZR_INTERNAL_ASKPASS='1',
                      SSH_ASKPASS=str(ROOT/'scripts/cruzr_recover_to_home.sh'),
                      SSH_ASKPASS_REQUIRE='force', DISPLAY=os.environ.get('DISPLAY',':0'))
        for label,container in containers.items():
            if label == 'motion-app-file':
                command=('set -e; latest="$(find /etc/walker/log/motion -maxdepth 1 -type f '
                         '-name \'robot_app*.log\' -printf \'%T@ %p\\n\' | sort -nr | '
                         'sed -n \'1p\' | cut -d\' \' -f2-)"; '
                         'test -n "$latest"; test -r "$latest"; '
                         'tail -n0 -F -- "$latest" & p=$!; sleep .3; '
                         'kill -0 "$p"; printf "MONITOR_READY\\n"; wait "$p"')
            else:
                command=('docker logs --tail 0 --follow '+shlex.quote(container)+
                         ' 2>&1 & p=$!; sleep .3; kill -0 "$p"; '
                         'printf "MONITOR_READY\\n"; wait "$p"')
            proc=subprocess.Popen(['setsid','-w','ssh','-o','StrictHostKeyChecking=yes',
                '-o','ConnectTimeout=5','-o','PreferredAuthentications=password',
                '-o','PubkeyAuthentication=no','-o','NumberOfPasswordPrompts=1',
                'walker@192.168.11.2',command], env=self.env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            self.processes.append(proc)
            ready=threading.Event(); self.ready.append(ready)
            threading.Thread(target=self._read,args=(proc,label,ready),daemon=True).start()
        try:
            for ready in self.ready:
                if not ready.wait(8): raise RuntimeError('Monitor remoto sin confirmación')
            self.check()
        except Exception:
            self.close()
            raise

    def _read(self, proc, label, ready):
        with (self.evidence/('monitor-'+label+'.log')).open('x') as out:
            for line in proc.stdout:
                out.write(line); out.flush()
                if line.strip()=='MONITOR_READY': ready.set()
                if FAULT.search(line):
                    self.faults.append((label,line.strip()))
                    print('ALARMA MONITOR '+label+': '+line.strip(),flush=True)

    def check(self):
        if self.faults: raise RuntimeError('Alarma de hardware o Motion; comprobar parada física')
        if any(p.poll() is not None for p in self.processes): raise RuntimeError('Monitor desconectado; estado físico por comprobar')

    def close(self):
        for p in self.processes:
            if p.poll() is None: p.terminate()
        for p in self.processes:
            try: p.wait(timeout=3)
            except subprocess.TimeoutExpired: p.kill()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--check',action='store_true', help='sólo lectura, opción predeterminada')
    mode.add_argument('--run',action='store_true', help='envía una única transición a teleop')
    parser.add_argument('--physical-confirmation', default='',
        help='constancia de comprobación presencial: MANOS VACIAS HOME ZONA LIBRE PAROS PERSONA')
    args=parser.parse_args()
    required='MANOS VACIAS HOME ZONA LIBRE PAROS PERSONA'
    if args.run and args.physical_confirmation!=required:
        parser.error('falta la constancia física exacta: '+required)
    out=ROOT.parent/'Humanoide-vla-evidence'/('PICO-V4-MODE-'+dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ'))
    out.mkdir(parents=True,exist_ok=False)
    print('EVIDENCIA='+str(out),flush=True)
    def save(name,data):
        (out/name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
    t=Transport(out)
    mon=None
    requested=False
    try:
        env=dict(os.environ,PICO_EFFECTOR='v4',PICO_TELEOP_CAMERA='off',PICO_PC_IP='127.0.0.1',CRUZR_IFACE='eno1',CRUZR_PC_IP='192.168.11.250')
        local=run_local(['bash',str(ROOT/'scripts/teleoperation/cruzr_pico_teleop_pc.sh'),'--check'],env)
        (out/'pc-preflight.txt').write_text(local)
        pgrep=subprocess.run(['pgrep','-x','pico_control'],capture_output=True)
        if pgrep.returncode!=1:
            raise RuntimeError('pico_control activo o estado de proceso no comprobado')
        ui=subprocess.run(['systemctl','--user','is-active','--quiet','ubt-remote-control.service'])
        if ui.returncode!=3: raise RuntimeError('UI de control activa o estado no comprobado')
        s=snapshots(t,'pico-v4-mode-check','v4')
        if not loaded(s,'v4') or any(v.get('active_session') for v in s.values()): raise RuntimeError('Perfil o sesión de efectores no confirmado')
        for data in s.values():
            if not all(c['State']['Running'] and c['RestartCount']==0 for c in data['containers'].values()):
                raise RuntimeError('Contenedor sin ejecución estable')
        motion=s['motion']['containers']['motion.manipulation_robot_app']
        app=motion['Id']; hw=s['motion']['containers']['motion.hw']['Id']
        envs=dict(x.split('=',1) for x in motion['Config']['Env'] if '=' in x)
        if envs.get('TELE_DEVICE')!='pico' or envs.get('transmit')!='local': raise RuntimeError('Perfil Motion PICO incorrecto')
        sha=t.run('motion',['docker','exec',app,'sha256sum',CONFIG],15).split()[0]
        if sha!=SHA: raise RuntimeError('SHA YAML v4 no corresponde a arms-only')
        safety(t,False)
        b=battery(t)
        if len(b)!=2 or min(b)<30: raise RuntimeError('Batería inferior al 30 %')
        a,ts1=pose(t,s); bpose,ts2=pose(t,s)
        if ts2<=ts1: raise RuntimeError('Muestras HOME no avanzan')
        if not re.search(r'locked:\s*false',read_topic(t,'/sys/state/module_lock_info')):
            raise RuntimeError('Bloqueo de módulos no liberado')
        action=read_topic(t,'/mc/manipulation/action/_action/status')
        action_idle(action)
        hands(t)
        state=call('cc.api.status.get',{'list':['workMode']})
        save('cc-preflight.json',state)
        mode=state.get('result',{}).get('workMode')
        if mode not in ('joystick','auto_task'): raise RuntimeError('Modo previo no admitido: '+str(mode))
        save('preflight.json',{'battery':b,'home':bpose,'home_timestamps':[ts1,ts2],
             'workMode':mode,'yaml_sha256':sha,'physical_confirmation':args.physical_confirmation})
        print('PREFLIGHT_OK=1; modo='+mode+'; HOME y manos verificados.',flush=True)
        if not args.run:
            print('SOLO_LECTURA=1; no se ha solicitado transición.')
            return 0
        mon=Monitor(out,{'motion-app-file':app,'motion-app':app,'motion-hw':hw})
        # Recheck immediately after monitor startup, not only before it.
        safety(t,False)
        current, current_stamp=pose(t,s)
        if current_stamp<=ts2: raise RuntimeError('No avanzó la muestra HOME previa a la transición')
        run_local(['bash',str(ROOT/'scripts/teleoperation/configure_pico_xr_usb.sh'),'--check'],env)
        run_local(['bash',str(ROOT/'scripts/teleoperation/cruzr_pico_teleop_pc.sh'),'--check'],env)
        mon.check()
        # A pending receipt survives timeout and prevents automatic retry.
        save('rpc-pending.json',{'method':'cc.api.work_mode.switch','params':{'workMode':'teleop'},'automatic_retry':False})
        requested=True
        request_time=time.monotonic()
        print('TRANSICIÓN SOLICITADA: vigilar la trayectoria y el paro físico.',flush=True)
        response=call('cc.api.work_mode.switch',{'workMode':'teleop'})
        save('rpc-response.json',response)
        if 'error' in response: raise RuntimeError('Control Center rechazó la transición: '+str(response['error']))
        deadline=time.monotonic()+60
        last_error=''
        while time.monotonic()<deadline:
            mon.check()
            try:
                state=call('cc.api.status.get',{'list':['workMode']})
                if state.get('result',{}).get('workMode')!='teleop': raise RuntimeError('Modo aún no confirmado')
                if time.monotonic()-request_time<15: raise RuntimeError('Inicialización todavía en curso')
                r1,t1=sample_still(t,app)
                time.sleep(1)
                mon.check()
                r2,t2=sample_still(t,app)
                if t2<=t1: raise RuntimeError('Muestras no avanzan')
                safety(t,False)
                hands(t)
                proc=subprocess.run(['bash',str(ROOT/'scripts/teleoperation/probar_pico_v4.sh'),'--check'],
                                    capture_output=True,text=True,env=env,timeout=120)
                if proc.returncode: raise RuntimeError('Perfil vivo v4 no confirmado: '+proc.stderr)
                mon.check()
                save('result.json',{'workMode':'teleop','posture':r2,'stamps':[t1,t2],'profile':proc.stdout,'start_sent':False})
                print('PICO_V4_CARGADO=1; CLIENTE_START_ENVIADO=0',flush=True)
                return 0
            except (ValueError,KeyError,RuntimeError) as e:
                last_error=str(e)
                if mon.faults or any(p.poll() is not None for p in mon.processes): raise
                time.sleep(1)
        raise RuntimeError('Inicialización no confirmada: '+last_error)
    except Exception as error:
        save('interrupted.json',{'error':str(error),'transition_requested':requested,'automatic_retry':False})
        print('INTERRUMPIDO: '+str(error)+'; sin reintento ni HOME automático. Comprobar estado físico.',file=sys.stderr)
        return 1
    finally:
        if mon is not None: mon.close()


if __name__=='__main__':
    raise SystemExit(main())
