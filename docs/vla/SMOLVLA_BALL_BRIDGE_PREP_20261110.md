# Preparación del puente SmolVLA de pelota — 10-11-2026

**Estado: inferencia histórica a bordo verificada; ejecución física pendiente.**
El usuario pidió crear las piezas que faltan para el piloto. No se enviaron
órdenes de movimiento ni llamadas a servicios de cambio de controlador. Las
lecturas son puntuales y no acreditan el estado físico posterior.

## Revisión en postura PICO y solicitud de cabeza — 10-11-2026

El usuario comunicó que había llevado el robot a PICO y autorizó mover la
cabeza. Lecturas puntuales a las 10:13 CET: 20 ejes corporales y dos ruedas
con velocidad cero en una muestra, brazos compatibles con la postura PICO
comunicada; ambas manos con siete ejes y velocidad cero en sus respectivas
muestras. Baterías 77,5/79,6 %, cargador 0 y paros 0/0. El primer intento de
`/mc/actuator_state` agotó plazo; a las 10:14:57 CET la lectura `best_effort`
mostró 20 actuadores corporales y dos ruedas con error 0 y velocidad 0; los
corporales indicaron status 4663. La postura, velocidades y salud puntuales no
acreditan comportamiento continuo ni condiciones físicas posteriores.

Controladores de manipulación, mano y chasis aparecían `running`, y los dos
SDK `initialized`; `/mc/sdk/robot_command` tenía 0 escritores y 2 lectores.
El último estado de acción recibido era `5` (cancelado); el último registro
visible indicaba transición de teleoperación a modo joystick. No demuestra
control exclusivo ni estado posterior. La UI del PC aparecía inactiva, sin
proceso `pico_control`; no demuestra que nadie use otra interfaz.

Se recibieron cuatro imágenes pasivas durante 3 s desde Vision y se visualizó
en memoria la última: sólo se aprecia una parte de la mesa, sin distinguir la
pelota ni identificar el aro con certeza. El sello de origen de la imagen
corresponde a 10:12:58 CET según el reloj del PC, pero los relojes no se han
calibrado y no se establece la antigüedad absoluta. No se conservaron píxeles.
Terminó el colector y `docker top` no mostró el proceso temporal. La lectura
usó `discover_vision`, `collector_command` y la fuente pasiva versionados en
`scripts/vla/run_ball_live_shadow.py` y `passive_episode_remote.py`.

No se movió la cabeza: `scripts/mover_cabeza_desde_pico.py --run` bloquea el
movimiento y el ejecutor físico anterior requiere HOME20D y otra configuración
de efector. La tarea histórica de cabeza sola no cualifica su recorrido ni
parada desde PICO/v4. Reactivar la teleoperación puede inicializar también
brazos y manos; el seguimiento histórico de cabeza no demuestra una vía
aislada segura. La autorización del usuario existe; la limitación es técnica.
No se enviaron órdenes, cancelaciones ni cambios de modo.

## Análisis de independencia de cabeza — 10-11-2026

El usuario pidió usar la tarea de HOME y otro efector desde PICO, y confirmó
en ese momento manos vacías, cabeza y recorrido despejados, ruedas bloqueadas,
cargador desconectado, paros accesibles, persona junto al paro y ausencia de
otros mandos. Lecturas posteriores no sustituyen una nueva comprobación antes
de una acción. A las 10:18 CET se observó posición PICO, velocidades cero en
una muestra de 20 ejes y manos, actuadores error 0, paros0/0, cargador0 y
baterías77,1/79,1 %. Manipulación/manos/chasis `running`, VLA/SDK `initialized`,
topic SDK sin escritores y último status de acción `5`; no prueba exclusividad
futura. En PC la UI estaba inactiva y no se observaron procesos ni conexiones
PICO en la consulta. No se enviaron órdenes ni se cambiaron modos.

La tarea instalada `cruzr/move_head_lower` conserva SHA256
`f3a73626f97b471d4a0a03c98c24de32243651116c497328e69b5ddc57ea46c1`
y está disponible en el catálogo: un solo MetaMove de cabeza, yaw0,
pitch−0,43 rad, duración2s. En el ensayo histórico desde HOME con abrazaderas
terminó normalmente y los otros ejes cambiaron como máximo 0,0000959 rad.
Eso apoya que la orden es de cabeza, no demuestra cobertura de colisión o
parada física desde PICO con v4. El cliente no llama explícitamente un cambio
de modo; tampoco se ha establecido si el servidor introduce alguna transición
al recibir `ArmTask` en el estado actual. El incidente de HOME conocido
ocurrió tras un cambio explícito a `auto_task`, no demuestra que un goal
directo cause HOME. El ejecutor existente conserva su preflight HOME y el
monitor documenta que la cancelación no prueba frenado; no se han saltado.

Como revisión geométrica **parcial**, la muestra de articulaciones con sello de
origen `1794302254.881649502` se evaluó en 101 posiciones interpoladas de
cabeza desde pitch−0,003451 a −0,43 rad, con el resto fijo. Cinemática del URDF
vendor `06083544f182b9336ad6f40040a5a79955c19897cb0b78d9f597888dce0c2fa0`
y mallas del ZIP SDK `7cb7f856223ce99a86d44349be475a2b5925d57ca694ee069a96c808802e297e`:
distancia mínima de orígenes `L/R_sixforce_link` a caja modelada de cabeza
0,49319/0,49313 m; sin intersecciones muestreadas con cajas de brazos,
excluidos efectores. La muestra no se conservó en archivo y los relojes no se
calibraron. Una cota geométrica del URDF v4 EVT3 de Descargas,
SHA256 `96f957ee0d346b8ff0654e219891ba23ebe5f2a315ca793a83dde9741019e561`,
encierra cada modelo de mano en radio 0,259076/0,258927 m desde su propia base.
No se conoce el montaje real base↔sensor, correspondencia hardware/modelo,
salientes de cabeza o escena. Muestreo discreto no certifica el recorrido
continuo ni sus tolerancias. No se movió la cabeza.

La revisión de 101 puntos se reproduce con una **nueva** lectura pasiva; no
reconstruye la muestra puntual no guardada. Desde la raíz del repositorio:

```bash
.venv/general-home/bin/python -B - <<'PY'
import sys,json,math
from pathlib import Path
import numpy as np
sys.path.insert(0,'scripts'); sys.path.insert(0,'scripts/vla')
from collect_estop_available_readonly import execute,ros
import analyze_vla_fixture_collision_e4_1c as fk
import analyze_vla_self_collision_e6_0b as ob
# Descubrir primero el contenedor actual; el nombre es el observado en esta sesión.
r=execute('motion',ros('walker-motion.manipulation_robot_app-1','rosa topic echo --once --no-daemon --qos-reliability best_effort /mc/whole_joint_states',True))
assert r['returncode']==0
s=r['stdout']; msg=json.loads(s[s.find('{'):]); state=dict(zip(msg['name'],msg['position']))
u=Path('../Humanoide-vla-evidence/20260903T093408_E4.1C/artifacts/vendor_cruzr_s2_v1.urdf')
z=Path('Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/URDF/cruzr_s2_description.zip')
j,b,_=fk.load_robot(u,z); mins={side:[math.inf,None] for side in ('L','R')}; overlaps={}
for i in range(101):
 t=i/100; q=dict(state); q['head_pitch_joint']=state['head_pitch_joint']*(1-t)-.43*t; q['head_yaw_joint']=state['head_yaw_joint']*(1-t)
 poses=fk.forward_kinematics(j,q); c,a,e=ob.obb_for_link(poses['head_pitch_link'],b['head_pitch_link'])
 for side in ('L','R'):
  point=poses[side+'_sixforce_link'][:3,3]; local=a.T@(point-c); d=float(np.linalg.norm(np.maximum(np.abs(local)-e,0)))
  if d<mins[side][0]: mins[side]=[d,i]
  for link in b:
   if not link.startswith(side+'_') or any(x in link for x in ('pgc','finger')): continue
   if ob.obb_overlap((c,a,e),ob.obb_for_link(poses[link],b[link])): overlaps.setdefault(link,[]).append(i)
print(msg['header']['stamp'],mins,overlaps)
PY
```

La esfera de cada mano se calculó en memoria sumando, para cada enlace de
colisión, las normas de las traslaciones de sus juntas desde la base, la
traslación de la malla y el máximo radio de sus vértices; se tomó el máximo
por lado. No es una medición de la mano instalada ni del montaje.

## Prueba breve en vivo — 10-11-2026

Tras la petición de acortar las pruebas, a las 10:04 CET se ejecutó la
[receta de shadow](../../scripts/vla/SMOLVLA_BALL_LIVE_SHADOW.md) existente
con `--seconds 5 --fps 1 --max-samples 100`. Los cinco scripts remotos se
compararon con sus fuentes locales por SHA256; Vision se descubrió de nuevo.
El checkpoint `e707eea07b58e14b979e78463b94ba75a52b1c18abf8076aebc8aa34ac77f8da`
produjo cuatro propuestas a partir de cuatro observaciones emparejadas,
sin descartes en el adaptador ni órdenes. Inferencia: 0,171–0,603 s;
adaptador PC hasta recepción de la predicción: 0,287–0,741 s, sin transporte
Vision→PC ni calibración de relojes. La mayor diferencia propuesta−estado
fue 2,271476 rad (aprox. 130°), no un movimiento ni un límite de seguridad.
No se conservaron píxeles ni se verificó que la pelota fuese visible. El
resultado se observó en la salida de esta intervención, no se guardó un log.

El primer intento terminó antes de arrancar el modelo por un error de ruta del
checkpoint; se corrigió el argumento y el segundo terminó rc0. Después no se
encontró el contenedor temporal propio en Ada ni el colector en el contenedor
ROS de Vision. No se llamó a servicios de control ni se cambiaron modos.
El sistema conserva procesos y registros normales de ejecución; no se guardaron
datos de la captura en archivos del proyecto o del robot.

## Preparación local posterior — 10-11-2026

Con autorización expresa para modificar los archivos necesarios se añadieron
dos piezas de revisión. No son un puente físico ni se han instalado en Motion:

* [`ball_arm_trajectory_preview.py`](../../scripts/vla/ball_arm_trajectory_preview.py)
  produce una interpolación conjunta hipotética sólo si pasan comprobaciones
  usando límites y tiempos proporcionados por quien la ejecuta, y verifica
  también la velocidad declarada de las otras 13 articulaciones. Su salida
  no demuestra colisiones, seguimiento, parada o límites del hardware.
  [Formato y receta](../../scripts/vla/BALL_ARM_TRAJECTORY_PREVIEW.md).
* [`ball_hand_bridge_preview.py`](../../scripts/vla/ball_hand_bridge_preview.py)
  recibe predicciones y señales externas de fase asociadas por hash y sello de
  imagen. Da etiquetas simbólicas y conserva el cierre hasta la fase de suelta
  con apoyo declarado; el escalar del modelo no acciona los dedos. La identidad
  declarada no verifica percepción, frescura ni estado real. No genera ROS,
  posiciones de dedos, corriente ni comandos.

Pasaron 20 pruebas locales de ambas piezas y sus guardias previos. Las cuatro
predicciones reales de la prueba breve se pasaron en memoria a la pieza de mano
con señales externas vacías: cuatro etiquetas `approach/open`, cero comandos.
Es una comprobación de integración; no observa el agarre ni indica la posición
real de los dedos. La vista previa de brazo sólo se verificó con datos y límites
sintéticos, no con una trayectoria real completa ni parámetros validados.

El revisor de mano lee líneas JSON por stdin con `sequence`, `prediction`
(evento de shadow de ocho valores, sello y hash) y `phase_evidence` (el mismo
sello y hash, más `signals`). El formato reproducible y ejemplos de las fases
están en `test_ball_hand_bridge_preview.py`. Las señales deben proceder de una
fuente externa; ese formato no constituye una interfaz de percepción ni una
prueba de su veracidad. Uso: `python3 -B scripts/vla/ball_hand_bridge_preview.py`.

La vía SDK existente requiere una transición de controlador cuyo resultado
histórico quedó incierto tras timeout. `stop()` destruye el publicador, pero no
demuestra la cancelación de la última consigna ni el frenado. El análisis
estático indica que, tras un retorno exitoso, se actualizan consignas
corporales; esa transición tampoco está cualificada como parada.
No reintentar una transición cuyo resultado sea desconocido. La solicitud al
fabricante de watchdog, deadman y transición SDK segura está en
[`UBTECH_OPEN_QUESTIONS.md`](../support/UBTECH_OPEN_QUESTIONS.md).

## Consulta del catálogo de mano — 10-11-2026

A las 10:10:23 CET, lectura del servicio de catálogo `/mc/action/list` en el
contenedor Motion redescubierto `walker-motion.manipulation_robot_app-1`, con
filtro `v4hand_right` e `include_custom=true`: respuesta `success=true`, seis
entradas, incluyendo `sps_v4/v4hand_right_open` y `sps_v4/v4hand_right_close`
como disponibles y de duración 2 s. Es sólo un catálogo: no se llamó al
servicio de ejecución ni a la acción ArmTask. Disponibilidad no demuestra
trayectoria libre, exclusividad de mano, efecto en postura PICO o cancelación.
El reloj observado de Motion marca 17:10:23 y no está calibrado con el PC.

Para reproducir la consulta desde el PC, con acceso habitual a Motion:

```bash
python3 -B - <<'PY'
import sys
sys.path.insert(0, 'scripts')
from collect_estop_available_readonly import execute
cmd = '''source /opt/walker/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; timeout 8 rosa service call --no-daemon /mc/action/list mc_task_msgs/srv/GetMnpActionList '{"keyword":"v4hand_right","include_custom":true,"model":"","hand_version":0}' '''
print(execute('motion', ['docker', 'exec', 'walker-motion.manipulation_robot_app-1', 'bash', '-lc', cmd]))
PY
```

Antes de repetir, descubrir de nuevo el nombre del contenedor; la consulta de
catálogo no ejecuta acciones. Se observó que `/mc/action/exec` es otro
servicio, de ejecución, y `/mc/manipulation/action` usa `ArmTask`; no se han
validado ni ejecutado para esta prueba. La demo histórica `demo_ceo.sh`
documenta un aborto por seguimiento del pulgar; un objetivo de cierre del XML
no demuestra que el cierre completo sea alcanzable o seguro en esta unidad.

El catálogo también incluía `s2/basic_motion/v4hand_right_open` y `...close`
de 8 s. El XML instalado `.../config/s2/basic_motion/v4hand_right_open.xml`,
SHA256 `66516cf99a9298097bbfe7018ddf2a5c1c5c8540236761ce91f0a2e78d35a6b0`,
ordena primero cuatro dedos a 1,4 rad durante 4 s y después los lleva a cero:
su nombre no acredita apertura inmediata ni función de parada. Lectura
estática, no ejecución. Los wrappers de demos usan `/mc/manipulation/action`,
pero sus resultados no prueban la cancelación física de estos XML específicos.

## Brazo y controladores

**Revisión posterior 10-11 — SMOLVLA-BALL-ARM-PREVIEW-20261110.**
`scripts/vla/ball_arm_preview_guard.py --input RUTA.json` evalúa offline una
propuesta y estados 20D nombrados con límites y tiempos aportados. Comprueba
integridad, antigüedad nominal, posición, salto y límites matemáticos de
duración mínima para una curva hipotética; no emite trayectorias ni órdenes.
La prueba contra un frame histórico usó reloj sintético y límites hipotéticos,
incluido salto0,2rad; rechazó cuatro ejes y una diferencia1,167653rad de
codo. Estos valores no son límites del robot. Sólo se revisa la velocidad de
los siete ejes derechos, no los otros 13; no evalúa colisión, mano, escena,
controlador o parada. Ningún resultado autoriza control físico. Entrada y
reporte privados en `../Humanoide-vla-evidence/20261110_BALL_ARM_PREVIEW_REAL/`;
[receta reproducible](../../scripts/vla/BALL_ARM_PREVIEW_REPLAY.md).

`scripts/vla/audit_ball_arm_proposals.py --check RUTA/live-run.jsonl` comprueba
el checkpoint, estructura y secuencia de un resultado shadow y relaciona sus
siete valores de brazo por nombre con el orden histórico del SDK. `--run` se
rechaza. Sobre la sesión del 09-11 procesó nueve propuestas y reprodujo la
diferencia máxima propuesta−estado de 1,165707 rad en `R_elbow_yaw_joint`.
No genera `RobotCommand`, no prueba trayectoria ni verifica límites físicos.

En una lectura Motion del 10-11 aparecieron `manipulation_controller`,
`dexterous_hand_controller` y `chassis_controller` activos, y ambos controladores
SDK inicializados. ROS2 anunciaba `/mc/motion_sdk/switch_to_vla` y
`/mc/motion_sdk/switch_to_manipulation`, sin llamarlos. El perfil declarado era
`cruzr_s2_v1_sps`. El `switch_controllers.yaml` SPS leído, SHA256
`21eb3b878f578c3e9ecc29914e34d2079f1154f40f76fae28b23a7b4c0b8b317`, menciona
iniciar `sdk_controller` y detener tanto manipulación como chasis, distinto del
archivo v1 histórico. No se ha demostrado qué archivo usa cada servicio ni su
efecto real; no extrapolar el cambio v1 a SPS. El YAML del controlador VLA de
ambos perfiles coincide, pero el orden de archivo no valida el transporte:
mapear siempre por nombre. Lecturas y comandos reproducibles están en
`../Humanoide-vla-evidence/20261110_SMOLVLA_BRIDGE_PREP/controller/`.

El backend histórico conserva el último setpoint en Motion. Destruir el
publicador no demuestra frenado, anulación de consigna ni retorno a
manipulación. Siguen pendientes semántica oficial, estrategia de exclusividad,
monitor y parada efectiva comprobados, trayectoria y límites para PICO/v4.

## Mano derecha

**Fuentes adicionales 10-11:** el manual SDK documenta posición para siete
ejes de mano v4; el demo Cruzr inspeccionado contiene seis. Se localizó en
Descargas un URDF v4 EVT3 articulado con 11 ejes móviles sin relaciones
`mimic`: no está probado su montaje ni correspondencia con los siete estados.
Se añadió una secuencia de fases simbólica, sin ROS, órdenes o verificación de
sensores. Véase [análisis y fuentes](SMOLVLA_MANO_V4_FUENTES_20261110.md).

`scripts/vla/audit_ball_hand_recordings.py RUTA/samples.jsonl` analiza las
grabaciones originales sin escribirlas. Se contaron 52.754 y 98.944 comandos
derechos, respectivamente, con siete nombres; todos los arrays de aceleración
estaban vacíos. Los modos uniformes 5 y 7 aparecen en ambas tomas; algunos
vectores del campo `torque` se repiten en ambos. La observación no identifica
por sí sola el gatillo ni prueba que las órdenes se aplicaran.

El análisis estático independiente de la biblioteca instalada del controlador
de manos, SHA256
`5f0bf11b51040346cfc8cb750617af50ae83c277ae68bdf0f83a70ceeb7f58ba`,
indica que el modo 5 se traduce a `Position` y copia el campo `position`;
el modo 7 a `Current` y copia el campo llamado `torque`. El getter instalado
confirma los offsets leídos y se observó un proceso que tiene mapeada la ruta
de la biblioteca. Esto es evidencia estática, no confirma que los bytes en
memoria sean idénticos ni establece unidades, conversión corriente/par, límites
o efecto físico. No equiparar corriente y par ni reutilizar valores capturados
como receta. La evidencia y comandos están en
`../Humanoide-vla-evidence/20261110_SMOLVLA_BRIDGE_PREP/hand/`.

Los XML vendor individuales de apertura y cierre derechos describen un solo
`MetaMove` de efector derecho, pero no se comprobó su registro/carga ni su
seguridad desde PICO. `scripts/vla/audit_ball_hand_intent.py --predictions
RUTA/live-run.jsonl` permite comparar el escalar con anotaciones opcionales de
fases. El umbral es exploratorio, las fases son externas y no verificadas, y no
produce comandos. En el shadow de nueve muestras faltan anotaciones y las
imágenes no se guardaron; no permite evaluar cierres correctos.

## Entorno ARM64 de inferencia

Vision es ARM64 con L4T 36.3; el entorno CUDA Ada del entrenamiento es x86-64
y no es directamente ejecutable allí. El host observado no tiene Python 3.12,
PyTorch ni LeRobot, ni ruta de Internet general; no alterar la red del robot.
`scripts/vla/prepare_arm64_cpu_wheelhouse.py --help` prepara y verifica ocho
artefactos fijados en una carpeta nueva. Se descargaron ocho en el PC en
`../Humanoide-vla-evidence/20261110_SMOLVLA_CPU_ARM64_PREP_V2/`; la salida marca
`complete_wheelhouse=false`. Las 331 fuentes Python del wheel de LeRobot 0.5.1
coinciden byte a byte con el commit de entrenamiento
`1396b9fab7aecddd10006c33c47a487ffdcb54b4`; esto no compara metadatos extra.

En el Docker del PC se descargó por digest la base ARM64 Python 3.12, antes
ausente: manifiesto
`sha256:df540bfd30bd380e89a349611ce42aa67bcb542d58c047706616eb6ba2f86a1b`,
ID `sha256:4703adf8fdd93b1441114e4f87ce2c62f7373fc5f88bda6a546c551625bcc71c`,
sin tag. Su copia privada `python312-arm64-base.tar` tiene SHA256
`47a52dc83e013b728d74aafdedf0f365881632e64f88c4aa1a1bd913471309e6`.
Para revertir, confirmar que nadie use esa imagen y retirar selectivamente su
referencia por digest; conservar o retirar la copia privada según necesidad.
No borrar otras imágenes ni limpiar Docker globalmente.

Existe un Dockerfile candidato y un compilador experimental con herramientas
host montadas sólo lectura; ver
[`smolvla_arm64_cpu/README.md`](../../scripts/vla/smolvla_arm64_cpu/README.md).
En Vision se cargó la base en Docker y se preparó un directorio nuevo con
fuentes fijadas. El constructor aislado produjo la wheel
`evdev-2.0.0-cp312-cp312-linux_aarch64.whl` SHA256
`608caec9870027cc36b7c1b552b849b096e5fa001fb3264da49e2efb698f98bb`;
un segundo contenedor ARM64 sin red la instaló en un venv temporal e importó
sus tres extensiones. Ensayos fallidos anteriores y correcciones se conservan.
El contenedor temporal terminó y no se actualizó firmware. Esto verifica
`evdev`, no el modelo.

En el PC se reunieron 100 wheels candidatas (492 MiB), con manifiesto
`SHA256SUMS` SHA256 `a92db7e630c79b22f5b36f5eabf6f136a36b51db40bf314b456bc39258daed4f`;
el comprobador verificó cobertura y hashes. La copia a Vision se interrumpió
tras unos 239 MiB; el usuario restableció el Wi-Fi y se reanudó sin sustituir
archivos. La comprobación de hashes pasó y se instaló el venv CPU en un
contenedor acotado: `pip check` no encontró conflictos y la clase SmolVLA se
importó en aarch64. El usuario conectó Ethernet y las entradas del checkpoint
se copiaron y verificaron. Un primer intento rechazó la ruta VLM, sin cargar
el modelo; se corrigió el wrapper y un segundo contenedor CPU sin red/ROS
produjo una predicción para una muestra **grabada**, no en vivo. El cálculo
tardó 62,932s y la mayor diferencia propuesta−estado fue 1,188865 rad en
`R_elbow_yaw_joint`, que no es movimiento ni límite seguro. Terminó rc0 y el
contenedor fue retirado. Evidencia `vision-inference-run-v2.jsonl` SHA256
`d08bf262b984c8388bb87a6a7d1c30060bc2f939e76ef065f882cab37c9a80d2`, log
`169b7b887c1f29ec23a4b165d9ae1466d9d1357a5ae9cdc005cbab4d14edf133`.
No se modificó configuración de red por el agente.

Faltan prueba con observaciones en vivo a bordo y evaluación de rendimiento
sostenido. Una inferencia aislada en CPU no habilita control. Véase la ficha
para rutas exactas y reversión.

## Reanudación

Evaluar el checkpoint en vivo y rendimiento sostenido; aclarar con evidencia
el handoff SPS y la parada; establecer la semántica y los límites
de mano, correlacionando gatillo y estados y ensayando supervisadamente en
vacío; construir el puente con límites, control exclusivo y monitor. Antes de
cualquier movimiento comprobar de nuevo hardware, postura, entorno y paros.
El shadow y los auditores no son ese puente físico ni su certificación.
