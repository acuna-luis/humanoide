# Adaptación de PICO a manos v4 — 15-10-2026

ID: **PICO-V4-PROFILE-20261015**, Europe/Madrid.
Estado actual: **SPS INSTALADO y CARGADO; HOME y estados de manos VERIFICADOS**.
Teleoperación PICO y grabación/reproducción v4 aún no ensayadas; véase resultado al final.
Este documento conserva el punto de reanudación; no certifica teleoperación.

El operador instaló las manos con el robot apagado. La corrección de identidad
EtherCAT HANDS-V4-BUS-IDENTITY-20261015 ya permitió OP y HOME; ambas manos
publican siete servos y el servicio get_version informa 4003/LoadSuccess.
El control de alto nivel seguía usando el perfil de abrazaderas y no publicaba
`/mc/left_hand/joint_states` ni su equivalente derecho. No omitir esa comprobación.

## Cambios preparados y aplicados

- PC: `scripts/teleoperation/pico_effector_profile.sh` selecciona clamp por
  defecto o v4 explícito. `probar_pico_v4.sh` restringe las opciones a chequeo,
  brazos/manos, teleoperación y STOP; rechaza el perfil de cuerpo completo.
- `cruzr_pico_teleop_pc.sh` usa cliente oficial `--arm_type hand` para v4 y
  exige tarea v4, torso desactivado y estados frescos de ambas manos. Backend
  global conserva su baseline clamp; el override por cliente está pendiente
  de verificación en ejecución. `--enable_hand_pose 0` no es captura óptica
  individual de dedos. Según SOP, grips mueven brazos y gatillos cierran/abren
  manos; comprobar físicamente tras completar la configuración nativa.
- `check_pico_v4_hand_states.py` sólo suscribe: dos timestamps crecientes por
  mano, siete nombres exactos, valores finitos y velocidad <=0,02. La prueba
  anterior a la migración falla correctamente sin muestras; no publica comandos.
- Motion/app: instalado YAML v4 sólo brazos, cintura0/elevador0 y colisión
  conservada. Vendor SHA256
  `48d2ee0f61ab3dddaceec31e7468d0a764ef0900b2e09b687281b5e02465e74e`;
  instalado `01a5ca8acba16bbe136a3bdbcb4a593667d672f8ee9613b98631699fc429b582`.
  Ruta `/opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config/meta_teleoperation/cruzr_v4_pico_tele.yaml`.
  Backup host `/home/walker/.local/share/cruzr-pico-arms-only/cruzr_v4_pico_tele.vendor.yaml`.
  Instalación con `PICO_EFFECTOR=v4 bash scripts/teleoperation/install_cruzr_pico_arms_only.sh --install`;
  su `--check` verifica archivos. **Todavía no cargado en una tarea activa**.
  Perfil clamp comprobado sin cambio.

## Migración nativa pendiente

SOP local `utats/Utars╥ú▓┘╫≈SOP-2.pdf`, §3.5.2, prescribe
`HW_TYPE=cruzr_s2_v1_sps` para manos v3/v4 y recreación de contenedores, no sólo
cambiar una variable dentro de una shell. Los módulos instalados incluyen
`dexterous_hand_controller`, configuración v4 de siete ejes y detección nativa
ModifyConfigurationForDexterousHand. No sustituir la calibración del cuerpo por
una plantilla. Compatibilidad completa de la build actual aún no demostrada;
no se ha cambiado firmware, SDK ni imágenes.

Se preparó una transformación reproducible que cambia únicamente HW_TYPE en:
Motion `/home/walker/.config/udoke/walker/compose.yml` y
`/home/walker/.config/udoke/db.json`. Fuentes:
`prepare_pico_v4_motion_env.py`, `stage_pico_v4_migration.py`,
`install_pico_v4_motion_env.py`, en scripts/teleoperation.
El instalador no reinicia procesos y rechaza drift; `--rollback` restaura sólo
las dos versiones anteriores del stage, tras comprobar que siguen reconocibles.
Stage remoto privado `/home/walker/.local/share/cruzr-pico-v4-migration-20261015`.
SHA antes compose/db: f59729e7… /957a2ecd…; candidatos da83b750… /58e4ac95…;
hashes completos en env-stage-receipt.json privado. Validación de compose:
único cambio efectivo HW_TYPE en diez servicios, incluido debug detenido.
**No arrancar debug**. Actualmente todavía no aplicado.

Antes de recrear: HOME20D medido, máximo0,002876rad, velocidad0, fallos0.
Después operador confirma paro principal pulsado. Manos vacías, zona libre,
cargador desconectado, otros mandos detenidos y persona junto al paro confirmados.
Dejarlo pulsado durante instalación. Revalidar estados antes de recargar.

Secuencia prevista: parar CC de Vision; parar los nueve servicios Motion activos
que heredan HW_TYPE; instalar env; crear esos mismos servicios con compose
`create --no-build --pull never --force-recreate`, sin descargar otra imagen ni iniciar debug;
restaurar en los contenedores detenidos exclusivamente los archivos revisados
hw/app; comprobar sus hashes; arrancar Motion y CC con paro pulsado. Verificar
espera de paro y disponibilidad antes de solicitar liberación al operador.
La liberación puede continuar el HOME nativo, incluidos dedos: no enviar otro
HOME ni un start ROS paralelo. Después comprobar HOME, fallos, controladores y
estados frescos de manos. Cargar PICO v4 y hacer ensayo supervisado son pasos
posteriores, sin START automático por esta migración.

Rollback requiere volver a parar CC/Motion bajo paro, restaurar env anterior,
recrear las mismas imágenes y reaplicar los archivos revisados. No restaurar
un compose viejo completo ni una calibración distinta. Nunca reactivar tareas
VLA ni estados transitorios de mando desde el backup.

## Respaldos, cobertura y evidencia

Privado fuera de Git:
`../Humanoide-vla-evidence/20261015_PICO_V4_PROFILE/` (0700).
Respaldos remotos `/home/walker/preupgrade-v0.2.0-20261015-080903` en ambos hosts.
Motion completo y copiado externo; 2634 archivos del manifest verificados.
Vision sigue terminando su inventario de 68 contenedores: no tratar IN_PROGRESS
como respaldo final. La primera conexión SSH agotó300s, pero el proceso remoto
continuó; se sigue el mismo proceso, sin duplicarlo.
El operador conectó Ethernet: rutas .11.2 y .11.3 directas por eno1/192.168.11.250
comprobadas. Antes la transferencia de Motion usaba Wi-Fi.

Suplemento externo `selected-writable-files.tar`: dos archivos internos hw/app y
cuatro versiones env, seis hashes verificados. hw.tar SHA256
07219ab5d8f60212c992c98a19b2f98b01b4d0bc6e1ff1841b5cccc125b11f61;
app.tar ebd7bbb1f42b13da6d9779dd6bfd360088f662d3f4aeabf6165607b28e96c816.
Conservan setup.bash/COMM, ENI corregido y selección actual, YAMLs/XMLs modificados,
HOME y tareas locales, perfiles clamp/v4 y grabación06 en raíz. Otros siete
servicios Motion activos: ninguna modificación de archivo seleccionada en diff.
Los workers efímeros /opt/cruzr-front-box no se restauran: sus fuentes versionadas
se transmiten al ejecutar el escenario. Vision no se recrea; revisar además
cobertura de voz/web fusion, que el backup genérico no incluye completamente.
No instalar env hasta tener ambos backups externos y verificaciones completas.
`verify_pico_v4_backups.py` verifica manifests sin extraer sobre el sistema.

Pruebas PC:19 unit tests del selector/estados/preflight/inspector y sintaxis Bash
pasan. shellcheck no disponible. No prueba física de dedos, teleop v4, grabación
v4 ni arranque en frío por esta fase. No commit/push.

Al quedar listo, primera comprobación desde PC (sin movimiento):

```bash
PICO_TELEOP_CAMERA=off CRUZR_IFACE=eno1 CRUZR_PC_IP=192.168.11.250 \
  bash scripts/teleoperation/probar_pico_v4.sh --check
```

No usar el reproductor ni inspector de abrazaderas para certificar una toma v4.
El SDK requiere `--robot utars_with_v4_hand` en record/player; comprobar contrato
actual y estado inicial antes de reproducir.

## Receta de activación por fases

`migrate_pico_v4_motion.py` no libera paros ni inicia PICO. Sus fases modifican
servicios, por lo que requieren el estado físico confirmado y paro principal
pulsado. Usa exactamente los nueve servicios activos inventariados; debug no se
incluye. Se comprobó que no tienen depends_on. `compose create` de esta versión
no admite --no-deps; no usar esa opción.

```bash
CRUZR_V4_EVIDENCE=../Humanoide-vla-evidence/20261015_PICO_V4_PROFILE
python scripts/teleoperation/migrate_pico_v4_motion.py --phase inventory --evidence "$CRUZR_V4_EVIDENCE"
# Sólo después de copias externas verificadas y preparación física:
python scripts/teleoperation/migrate_pico_v4_motion.py --phase stop --evidence "$CRUZR_V4_EVIDENCE"
python scripts/teleoperation/install_pico_v4_motion_env.py --install --evidence "$CRUZR_V4_EVIDENCE"
python scripts/teleoperation/migrate_pico_v4_motion.py --phase create --evidence "$CRUZR_V4_EVIDENCE"
python scripts/teleoperation/migrate_pico_v4_motion.py --phase restore --evidence "$CRUZR_V4_EVIDENCE"
python scripts/teleoperation/migrate_pico_v4_motion.py --phase start-motion --evidence "$CRUZR_V4_EVIDENCE"
python scripts/teleoperation/migrate_pico_v4_motion.py --phase verify-files --evidence "$CRUZR_V4_EVIDENCE"
python scripts/teleoperation/migrate_pico_v4_motion.py --phase start-cc --evidence "$CRUZR_V4_EVIDENCE"
```

Detenerse ante cualquier salida distinta de cero; no encadenar ignorando errores.
La verificación de archivos ocurre con CC detenido y hardware esperando arranque.
Cada fase comprueba principal1/cargador0; todas comparan las imágenes con el
inventario anterior. `stop` detiene CC antes de Motion; `restore` sólo usa hw/app
de hashes fijados. Las fuentes y recibos se conservan en evidencia externa.

## Aplicación 15-10, 08:33–08:35 UTC

VERIFICADO: respaldos Motion2634/Vision215 archivos de manifest íntegros y
suplemento seleccionado6 hashes. Vision externo2.471.618.560bytes SHA256
0e0ce089c622d8387d4c72a411e847ed0bc2866a4b977e472e8c07570d978a0d.
Suplemento Vision voz/customizations109.086.720bytes SHA256
fd73bf58b73ddc4df3f16fe7f6d18ecb203c4c1c01e522807d2076de5bc7ef19.
La copia de trabajo local se renovó antes de recrear, incluidos scripts nuevos.

APLICADO: CC detenido, nueve servicios Motion detenidos, compose/db cambiados
únicamente a HW_TYPE SPS. Nueve contenedores recreados con las mismas imágenes,
archivos seleccionados restaurados con docker cp -a y Motion arrancado.
Verificación posterior:3 archivos hw +59 app con hashes idénticos al stage.
COMM sinSHM y ENI corregido conservados; no debug ni VLA activado.
Principal1/servo0/cargador0 medidos antes; cada fase verifica principal1/cargador0.
Control Center arrancado después de comprobar archivos; guard en MOTION1/3
al primer seguimiento. HW confirma HW_TYPE SPS y espera /mc/rosa_control/start.
Todavía no se solicita liberar el paro ni se confirma HOME/controladores v4.
No PICO START. Recibos migration-*.json y logs en evidencia privada.

### Punto actual de reanudación

CC completó guard Motion3/3 y cámaras2/2, Recover y alcanzó
WaitEStopRelease a08:34:55Z hora Docker/Vision (reloj~52s retrasado respectoPC).
Paro principal1/servo0; baterías nuevas74,6%/69,8%, ambas discharging.
Se pide al operador liberar el principal sólo manteniendo manos vacías, zona
libre, otros mandos detenidos y persona junto al paro: puede comenzar HOME.
**Respuesta pendiente; no se libera por software ni se envía start adicional.**

Para revertir sin iniciar movimiento: con el paro pulsado y los servicios
nuevamente detenidos, usar `install_pico_v4_motion_env.py --rollback`, después
`migrate_pico_v4_motion.py --phase create --rollback` y fase restore. Conservar
los recibos de la intervención antes de reutilizar una fase. Una posterior
activación sigue requiriendo estado físico preparado; no arrancar automáticamente.
Volver al perfil anterior no certifica dedos operativos con manos instaladas.

## Resultado después de liberar el paro — 15-10-2026

Operador confirma liberación y condiciones físicas mantenidas. Seguimiento del
agente sólo lectura: no nuevo restart, HOME, enable, cambio de modo ni START.
CC detecta liberación08:36:55Z horaDocker/Vision, completa SelfCheck y
StartMotion/LimbMotion, entra JoystickMode08:37:36Z. El chequeo general vendor
pasa, aunque audio_loopback dafalse (similitud0,377329<0,4); no se anula ningún
gate. No afirmar que todos los chequeos individuales pasan.

Bus conserva ENI corregido y alcanza SAFEOP→OP08:37:15Z. Los dos efectores son
v4/EVT3/sinpiel/7servos (código4003). Control dexterous carga
left_v4_hand_controller y right_v4_hand_controller, inicia back-zero y la app
incorpora los componentes de manos en memoria, manteniendo calibración del
cuerpo. Los mensajes DecodeHandType de nivelE con4003 no impiden la posterior
inicialización exitosa; no deducir fallo sólo del nivel de log. Persisten avisos
SDO18001/18002 y objeto2004:7, ya documentados; impacto pendiente.

Muestra nueva /mc/actuator_state:20 ejes del cuerpo, máximo absoluto0,002492719rad,
velocidad0, error_code0 en todos; HOME20D comprobado en esa muestra. No extiende
HOME20D a dedos. /mc/left_hand/joint_states y right están presentes; el checker
ROS2 recibe dos timestamps crecientes por mano, exactamente7nombres, valores
finitos y velocidades <=0,02: **V4_HAND_STATES_OK**. No se ordenó una trayectoria
de dedos ni se certifica agarre/contacto mediante este chequeo.

Dos consultas iniciales del agente fueron incorrectas: rclpy ejecutado en app
nativa sin ese módulo y ListControllers en /mc/rosa_control/list_controllers.
No prueban fallo robot. Se corrigieron usando walker-ros.ros2-1/setupHumble para
el checker y redescubriendo /mc/controller_manager/list_controllers para ROSA.
El lanzador versionado ya ejecutaba el checker en el contenedor ROS2 correcto;
no necesitó modificación por ese error de consulta.

Estado final: JoystickMode, bodyHOME medido y manos con telemetría válida.
**No hace falta reiniciar para completar este arranque.** El YAML v4 sólo brazos
está instalado pero todavía no se ha cargado una tarea TeleopMode v4. Ese cambio
puede mover los brazos a postura PICO: es siguiente etapa supervisada, no se
realizó durante este seguimiento. Cliente PC `--arm_type hand`, gatillos y ensayo
PICO físico siguen pendientes; no declarar CHECK_OK/teleop operativa todavía.
Tampoco grabación/replay v4 ni arranque frío posterior verificados.
Evidencia: cc-release-followup.json, hw-v4-init.json, app-v4-init.json,
body-post-sps.json/classification, hand-gate-ros2-after-release.json,
controllers-correct-endpoint.json. No commit/push.


**15-10-2026 10:42 CEST — continuación PICO v4, pendiente conexión XR.**
Operador pide seguir. Chequeo PC con cámaraoff y Etherneteno1 se detiene enCHECK2:
ADB no muestra dispositivos y no se detecta peerXR activo en63901. El clienteADB
arranca automáticamente su servidor localtcp5037 (antes detenido); no se cambia
configuración persistente. configure_pico_xr_usb.sh --check confirma visor físico
PA94Y0MGKB070822G ausente porUSB. No se configura túnel ni se envía START, modo
robot, HOME o movimiento. Tarea TeleopMode v4 todavía sin cargar; robot permanece
en modo anterior. Se solicita al operador elecciónUSB/Wi-Fi y preparar visor.
Reanudación: establecer XR y tracking neutro, comprobar STOP y seguridad frescos,
cargar modo v4 sólo brazos y verificar0/0 antes de ensayo. Evidencia privada
20261015_PICO_V4_PROFILE/pico-connection-before-mode.json ycc-before-pico-mode.json.
ServidorADB transitorio; dejarlo activo permite continuar, sin autorizar control.


**15-10-2026 10:46 CEST — PICO-V4-PROFILE: USB reconectado; XR pendiente de interfaz.**
Operador eligeUSB. PICO PA94Y0MGKB070822G reconocido deviceusb1-3.
Reverse anterior vacío; con backendSTOP confirmado por log pasivo, receta
`bash scripts/teleoperation/configure_pico_xr_usb.sh --configure` instala sólo
`tcp:63901 tcp:63901`; --check posterior confirma túnel e identidad.
Check PC descubre XRoboToolkit cerrado. Se abre únicamente su actividad
com.xrobotoolkit.client/com.unity3d.player.UnityPlayerActivity mediante ADB;
rc0. No modifica APK/configuración persistente, no START ni modo/movimiento robot.
Se pide al operador IP127.0.0.1, conectar, Head+Controllers/Senddata, sinY/grips.
Connected/Working y tracking aún pendientes. Evidencia usb-before.json,
usb-configure.json,usb-after-check.json,xr-activity.json,xr-open-app.json en
20261015_PICO_V4_PROFILE privado. Rollback transporte: con backendSTOP,
`bash scripts/teleoperation/configure_pico_xr_usb.sh --remove` retira sólo63901;
volver a IPWi-Fi real en interfaz si se elige otro transporte. Túnel transitorio,
puede desaparecer al desconectar/reiniciar. No se cerró app ni se quitó túnel.


## PICO-V4-CC-SELECTION-20261015 — selección incorrecta y postura inicial incompleta

15-10-2026 Europe/Madrid. **OBSERVADO; PICO v4 no habilitado para uso físico.**
Durante preparación USB, el reverse63901 desaparece: ADB transport_id cambia1→2,
compatible con reconexión, causa física no demostrada. Con backendSTOP se
restaura mediante configure_pico_xr_usb.sh --configure. Operador confirma conexión
pero primero vr_status0; tras activar Head+Controllers/Senddata, chequeo PC v4
pasa con peerloopback,vr_status1 y ruta Motion/Vision poreno1. No START del
clientePC ni Y enviado por agente. Túnel transitorio, sin daemon de reparación.

Operador confirma manos vacías, zona libre, otros mandos detenidos, grips/gatillos
libres y persona junto al paro. Preflight fresco: paros0/0,cargador0, dosSOC>=30,
module_lockfalse, HOME20D20ejes sinfallos/velocidad0 y YAML v4 sólo brazos hash
01a5ca8a… instalado. Control Center informa joystick.

Se descubre el protocolo vigente de la web servida: rosbridge Vision9090,
/cc/api/connect y /cc/api/in|out/SESSION, std_msgs/String, handshake
ubt.walker.local_web. **No es WebSocket PC8082**, que puede iniciar publishers.
Herramienta scripts/teleoperation/pico_cc_mode.py: CLI sólo consulta workMode;
call() realiza el RPC expresamente solicitado por el llamador. Status requiere
params {list:[workMode]}; consultas iniciales sinlist/conwork_mode fallan sin
cambio de estado. Sesión se desconecta al finalizar. No credenciales nuevas.

RPC autorizado cc.api.work_mode.switch {workMode:teleop} aceptado. CC entra
TeleopMode pero selecciona **teleoperation/cruzr_clamp_pico_teleoperation**,
hand_typeclamp,hand_tele_mode0,waist0,leg0. Motion detecta por sí mismo armtypehand,
pero eso no convierte el YAML clamp en v4. El preflight v4 sigue bloqueándolo.
Faltó contrastar el selector del Control Center antes de entrar; la selección
incorrecta fue detectada por lectura antes de cualquier START PC.

Causa de selección: Motion fue migrado a HW_TYPE=cruzr_s2_v1_sps, mientras el
contenedor Vision walker-system.control_center-1 conserva HW_TYPE=cruzr_s2_v1.
Desensamblado de HalfTeleopImpl::startTeleop lee getenv(HW_TYPE), busca sufijos
s2_v1_gripper/s2_v1_sps/s2_v1 y construye la tarea; ramaSPS utiliza leftHandType
(UbtV3Hand→v3, otra variante→v4). Literales y rama guardados en evidencia.
No cambiar todas las configuraciones de Vision sin revisar compatibilidad.
**Todavía no corregido el env de CC ni recreado ese contenedor en esta fase.**

Operador informa brazos/muñecas asimétricos y aporta foto. Telemetría confirma
inicialización no alcanzada: L_shoulder_yaw~0 vsconsigna−1,57rad,
L_elbow_roll~0 vs−1,57; R_shoulder_yaw~1,56965rad y R_elbow_roll~0 vs+1,57.
No se atribuye la causa única al YAML, a IK, colisión, servos o calibración sin
prueba. Dos manos:7estadosválidos, velocidades0; posiciones de dedos cercanas a
0,04/0,1rad izquierda y0,018–0,092rad derecha. Diferencia observada es de brazos,
confirmada por operador, no prueba de cierre involuntario de dedos.

Se cancela la preparación mediante mismo RPC a auto_task, aceptado; status
posterior confirma auto_task, app registra interrupción/FAILURE de la tarea.
Sin HOME, restart, servoenable ni nueva trayectoria. Muestra posterior: velocidades
publicadas0 y error_code0; **consignas antiguas aún difieren hasta1,57029rad**.
No afirmar seguimiento correcto ni parada física continua desde una muestra;
no habilitar PICO ni reiniciar/cambiar perfiles con esa discrepancia sin resolver.
Backend PC se mantuvoSTOP; no se envió START, no ensayo de grips/gatillos.

Estado actual: auto_task, postura distinta de HOME, inicialización incompleta,
control de dedos v4 nativo cargado pero sesión PICO v4 aún pendiente.
Próximos pasos: comprobar cancelación/estado físico/reposo y origen de diferencia
medida/consigna; preparar recuperación específica a HOME con trayectoria libre;
corregir selectivamente selector de CC con backup y misma imagen, conservar
boot/voz y resto de Vision, después verificar tarea v4/0/0 viva. No pulsar paro
ni apagar como sustituto de recuperación a HOME salvo emergencia real.
Recuperación y prueba física de PICO todavía PENDIENTES.

Evidencia privada20261015_PICO_V4_PROFILE: USB failure/restore, PC/preflight,
cc-enter-teleop.json,cc-teleop-entry.json,app-teleop-entry.json,
cc-type-config-discovery.json,cc-selector-symbols/disassembly/literals.json,
body-during-teleop-wait.json,hand-posture-left/right.json,
cc-stop-mismatched-teleop.json,cc-mode-after-teleop-cancel.json,
body-after-cancel-classification.json y app-after-teleop-cancel.json.
Fuentes y documentación antes/después conservadas fueraGit; sin commit/push.


### Ampliación PICO-V4-CC-SELECTION-20261015: rechazo por salto confirmado

Operador confirma brazos/manos siempre libres, sin contacto ni enganche, y que
la diferencia observada es de brazos/muñecas. Foto no sustituye medición.
Se consultan logs HW: ecat_hardware.cpp:348 write rechaza repetidamente cuatro
consignas mediante `send a jump command`, umbral0,087rad. Ejes L_shoulder_yaw,
L_elbow_roll,L_elbow_yaw yR_elbow_roll conservan valores medidos próximos0
frente a−1,57/−1,57/−0,3745/+1,57rad. Explica inicialización parcial/asimétrica;
no queda demostrada todavía la razón de software por la que se enviaron esos
saltos pese a init_time12s, ni que corregir sólo la tarea elimine el problema.
No se cambia umbral, watchdog, límite, anticolisión ni protección de seguimiento.
Aviso adicional `Not all EtherCAT slave devices in operational state` a17:02:32
hora nativa observado, sin atribución causal; investigar antes de recuperación.

Segundo snapshot posterior a cancelación registra reposo; delta posición/consigna
permanece~1,57rad. La consulta pasiva action/status transiente agota7s: no usarla
como prueba de ceroacciones. CC confirma auto_task y app informa interrupción.
No nuevos objetivos, HOME, reset, rearme o restart. La guía de recuperación,
fasesC/D, bloquea HOME con abs(cmd_pos-position)>0,01 y exige reset documentado
si hay consignas latentes; no existe método validado aquí para limpiarlas.
No reutilizar automáticamente recorrido de abrazaderas con manosv4.
La recuperación queda pendiente de procedimiento adecuado/soporte; no forzar
consignas crudas, relajación del umbral o reinicio individual como ensayo.

Corrección de selector **preparada sólo offline**, NO instalada:
`python scripts/teleoperation/prepare_pico_v4_cc_env.py --before-directory BEFORE --output-directory NUEVO`.
Cambia únicamente HW_TYPE de system.control_center en compose Vision y de
nodes.control_center en su fuente .metafiles/system.metafile.yml a
cruzr_s2_v1_sps. Mantiene DBglobal/HW_TYPE de los otros servicios Vision y todos
los demás campos/bytes; comparación YAML profunda correcta. No se editó SDK.
Destinos previstos /home/walker/.config/udoke/walker/compose.yml y
/home/walker/.config/udoke/walker/.metafiles/system.metafile.yml, hostVision.
Originales externos privados vision-cc-env-before; candidatos y manifiesto en
vision-cc-env-candidate. Hashes antes/después:
compose47ec176b30008d652814321780319d45c177fc6e48e7b91366c5e6871b9d785a →
b5658b0237225f001e41bc84fafa3f5620d7314b952212624ca1de06bd0fd127;
metafilecdec690e783e57d9e562d4f41d53146abe7f79eab345bb4a3dd3506ef44fde7b →
052db6d7e3ceb29a4cf2938b18e90d198a330bba1405299210cc9f74c088f725.
CC no presenta archivos de configuración/binarios modificados en diff del backup
(excepto caches/dirs); boot/voz persisten en host y siguen respaldados. Antes de
aplicar/recrear: resolver postura/consignas, revalidar estado y conservar imagen,
montajes y gate de arranque. No recargar CC desde postura desconocida para forzar
HOME. Reversión prevista sólo de esos dos archivos, verificando hashes y
recargando de forma supervisada. Instalación/carga/ensayo de esa corrección
PENDIENTES; currentCCenv siguecruzr_s2_v1.


## PICO-V4-CC-SELECTION / BOOT-CC-SPS-20261015 — corrección instalada y preparación de apagado

15-10-2026, Europe/Madrid. Usuario pide siguiente paso. Nueva muestra confirma
20ejes, velocidad0, sinerror_code y delta~1,57029rad: no HOME/reset/rearme.
Operador confirma personal/medios y después **brazos asegurados contra caída o
golpe, manos vacías, robot estable y paro principal pulsado**. Es recuperación
fueraHOME, no apagado normal. Se sigue caso supervisado de la guía de apagado;
no pulsar KEY1 ni chasis antes de terminación lógica y confirmación visual.

Selector CC **INSTALADO** con install_pico_v4_cc_env.py --install; no SDK/vendor
alterado. Check posterior y comparación efectiva compose correctos: único cambio
services/system.control_center/environment/HW_TYPE→cruzr_s2_v1_sps. Mismo cambio
en nodes.control_center de .metafiles/system.metafile.yml para conservarlo al
regenerar. DBglobal y demás serviciosVision intactos. Hashes completos en ficha
anterior; backup remoto /home/walker/.local/share/cruzr-pico-v4-cc-20261015/ y
externo vision-cc-env-before. --rollback restaura los dos originales sin recarga.

Con principal1 recién medido y soportes confirmados, se recrea **sólo CC** usando
activate_pico_v4_cc.py --activate --estop-arms-secured. Antes se comprueban copias
externas, ausencia de pico_control y que no tiene depends_on. Después se exige
mismaimagen302d2d6a012f3bef89d126dfe8aa1dee5b5c419043f01192284dac1bb1e798dd,
mismaorden guard/montajes y mismos env salvo HW_TYPE. Contenedor anterior4a7eab…
y nuevo7d1632…. No Motionrestart, HOME, release de paro niSTARTPC.

Hallazgo tras recrear: guard local de arranque estaba fijado a HW_TYPEbase y
sale78 unexpected_hardware con SPS, causando reinicios automáticos del CC.
Se detiene explícitamente el contenedor y se conserva evidencia; no se insiste
ni se cambia a tarea clamp. Faltó revisar ese predicado antes de la recreación.
Consulta SWIG durante el cambio de contenedor produjo errornamespace OCI;
no se interpreta como fallo del hardware. Lectura final en app Motion confirma
contratoShutDown DEF_DEADLINE15,CONFIRM_STR confirm-to-shutdown ycampos correctos.

BOOT-CC-SPS-20261015: actualización selectiva del predicado para aceptar
exactamentecruzr_s2_v1 ycruzr_s2_v1_sps. Resto de guard Motion/cámaras/binario,
deadline y lógica de paros original intactos. No se deshabilita watchdog ni
comprobación de hardware: se añade el identificador que corresponde al efector
verificado. Fuente local scripts/upgrade/cruzr_cc_start_when_ready.py ytest;
18tests pasan incluyendo SPS requiere Motion/cámaras y unknownrechazado.
Primer test esperaba78 para faltaMotion; código real75 conservado, expectativa
corregida. No cambió comportamiento de fallo ni retorno del guard.

Instalador versionado scripts/upgrade/allow_pico_v4_cc_guard.py, --check por
defecto; --install sólo con CCdetenido yhashlive exactoff9e119846c89ecc8ed3a3682c6d513abd4956cd2dff1af24da3ef932092184a.
Destino Visionhost /etc/walker/boot/cruzr_cc_start_when_ready.py. Conserva byte a
byte el hookVOICE-BOOT-05 que no figura en la plantilla local (no sobrescribir
con plantilla). Backup /etc/walker/boot/backups/pico-v4-20261015/guard.before.py,
y cc-boot-guard.before.py externo. SHAinstalado
9f3f2e8363358c0fdb83486153f80145fddb3278ec6332bbf2425dbe8db993c7.
Rollback del instalador restaura el liveanterior bajo CCdetenido; no ejecutarlo
conenvSPS porque volvería a rechazarlo. Recargar sólo tras estado físico preparado.

Se verifica principal1 de nuevo y se arrancaCC; guard ya progresa Motion1/3→2/3.
Sin liberación de paro ni nuevoHOME. Apagado lógico todavía NO solicitado en este
punto. Esperar CCnativo preparado, después una única solicitud al servicio
/emb/pm_shutdown; verificar aceptación,hosts yconfirmación visual antes de KEY1.
Persistencia del selector requiere recreación realizada (un simple reboot del
contenedor antiguo no cargaba el nuevo env); recreación comprobada. Sesión PICOv4
real y eliminación del problema de saltos aún PENDIENTES, no certificadas.


### 15-10-2026 — apagado completo y nuevo arranque supervisado (OBSERVADO)

El guard de CC con SPS completó Motion 3/3 y cámaras 2/2; CC alcanzó
`WaitEStopRelease`. Con brazos asegurados contra caída, manos vacías y paro
principal pulsado, se solicitó una única vez `/emb/pm_shutdown`
(`emb_task_msgs/srv/ShutDown`, deadline_sec=15, confirm_str=confirm-to-shutdown).
Respuesta `success=True`; evidencia privada `shutdown-logical-request.json` en
`../Humanoide-vla-evidence/20261015_PICO_V4_PROFILE/`. El operador confirmó
pantalla y luces superiores apagadas, después apagado completo de ambas partes,
indicador verde del chasis apagado y brazos estables. Recuperación fuera de HOME
con soportes; no se envió HOME ni se alteraron límites o protección de saltos.

El operador informa nuevo encendido en orden chasis → KEY1 → botón de encendido
y mantiene el paro principal pulsado. Consulta de lectura descubre de nuevo
Motion y Vision activos (`reboot-container-discovery.json`). Se comprueba
arranque sin liberar el paro ni activar PICO. HOME actual, eliminación de
consignas latentes y funcionamiento físico de PICO v4 siguen PENDIENTES.

Verificación posterior del nuevo arranque: gate Motion 3/3, cámaras 2/2 con
timestamps avanzando; HW_TYPE efectivo SPS tanto en app Motion como en CC.
CC nativo alcanza `WaitEStopRelease`, principal=1 y servos=0. No se libera paro
ni se envía movimiento. Avisos MQTT rc14 y consulta de versión embedded agotada
observados; no se atribuyen automáticamente a fallo de brazos. Evidencia:
`reboot-first-readiness.json`, `reboot-cc-profile.json`, `reboot-native-cc.json`.


### 15-10-2026 — HOME tras ciclo completo (VERIFICADO)

El operador informa liberación del paro principal y HOME normal. Lectura nueva
confirma StartMotion terminado con éxito y CC en AutoTaskMode. Telemetría:
{"axis_count": 20, "max_abs_position_rad": 0.002684466378799872, "max_cmd_position_delta_rad": 0.002684466378799983, "max_velocity": 0.0, "faults": []}. Las diferencias anteriores de ~1,57 rad ya no
aparecen en esta muestra. Evidencia privada reboot-home-verification.json y
reboot-home-summary.json en 20261015_PICO_V4_PROFILE. Sin órdenes nuevas del
agente. No demuestra todavía inicialización PICO v4 correcta. Selfcheck general
passed=true, con avisos individuales audio_loopback y señal Wi-Fi; MQTT rc14
persiste. No se alteró ni omitió ninguna comprobación. Próximo paso: comprobar
seguimiento USB y continuidad de inicialización v4 antes de activar teleop.


### PICO-V4-SSH-ALLOWLIST-20261015 — transporte de lista de hardware (15-10-2026)

Tras HOME, USB XR vuelve a enviar HEAD+CONTROLLERS (vr_status=1), enlace robot
Ethernet eno1 y backend STOP. Check v4 rechazó erróneamente HW_TYPE SPS: SSH
concatena argumentos remotos y separaba la lista con espacios en dos argumentos.
Se corrige sólo transporte de expected_hw_types a un token separado por comas y
se reconstruye la lista en remoto. Se conserva la misma lista permitida por
perfil: clamp sólo base; v4 base/SPS. Sin cambio de gates físicos o hardware.
Fuente PC scripts/teleoperation/cruzr_pico_teleop_pc.sh; prueba de regresión en
test_pico_motion_preflight_diagnostics.py simula reconstrucción SSH y rechazo
de hardware desconocido. 16 tests pasan y bash -n correcto. Backup externo
20261015_PICO_V4_PROFILE/before-ssh-hw-list-fix; reversión del fragmento desde
esa copia, sin reinstalar cambios ajenos del archivo. Activación próxima
ejecución del script; no requiere reiniciar robot/PC. Sin START ni cambio de
modo durante estas comprobaciones. Control de manos desde XR aún no habilitado.

Check real posterior: HW_TYPE SPS aceptado; siguiente gate rechaza correctamente
ACTIVE_TASK_ERROR=cruzr/home (rc26). Aún no se ha cargado tarea PICO v4.
Tracking USB vr_status=1 y STOP confirmados; no START ni cambio de modo.


### 15-10-2026 — tarea PICO v4 inicializada (VERIFICADO; sesión manual pendiente)

Con confirmación física actual: manos vacías, recorrido libre, soportes retirados,
cargador fuera, otros mandos detenidos y persona junto al paro. Lecturas nuevas
pre-v4-mode-safety.json: paros0/0, batería64,1/67,1%, cargador0, módulos sin
bloqueo. Cuerpo20D en reposo sinfaults/delta máximo0,002589rad y siete estados
v4 válidos por mano. Perfil v4 instalado con init_time12, init_resettrue,
anticolisióntrue, cintura0/elevador0, sin modificar parámetros de inicialización.

Cambio autorizado mediante cc.api.work_mode.switch workMode=teleop aceptado.
Ahora sí selecciona teleoperation/cruzr_v4_pico_teleoperation, Hand typev4,
waist0/leg0. Vigilancia de hardware durante inicialización no observa nuevos
'jump command', SAFEOP ERROR ni avisos de fuerza/fault del patrón vigilado.
Telemetría final:20D, velocidad0, sinerror_code y delta máximo0,00342212rad
(~0,20°); ambos brazos alcanzan consignas iniciales v4. Operador confirma ambos
brazos estables. Perfil cargado SHA01a5ca8acba16bbe136a3bdbcb4a593667d672f8ee9613b98631699fc429b582.
No demuestra aún respuesta a grips/gatillos ni ensayo de agarre.

Evidencia privada: v4-mode-switch-after-reboot.json, v4-init-app-log.json,
v4-init-hw-watch-0..7.json, v4-mode-status-after-init.json y
v4-init-actuator-check/summary.json. Estado vigente teleop, PC STOP, sinSTART.
No HOME adicional, reboot ni reset. Para salir, usar STOP oficial y transición
controlada; no apagar desde la postura PICO sin recuperación adecuada.

Durante check posterior tracking cae a vr_status0: USB reverse aún válido,
XRoboToolkit resumed, pero Android mWakefulness=Asleep. Operador despierta y
se coloca el visor; se repite check antes de START. No se deshabilita tracking,
watchdog o suspensión del dispositivo. No seleccionar seguimiento óptico Hands:
perfil actual Head+Controllers, cliente hand con enable_hand_pose0.

Actualización de seguimiento: tras despertar, mWakefulness=Awake confirmado
pero check aún vr_status0. Suspensión observada no explica por sí sola la
persistencia; USB TCP sigue ESTAB y reverse válido. Se solicita reactivar
Send data/reconectar dentro de XRoboToolkit. Sin START ni cambio adicional
del robot. Evidencia xr-awake-tracking-still-inactive.json.


### PICO-XR-USB-20261015 — recuperación tras suspensión (OBSERVADO)

Tras reactivar Send data, check aún vr_status0. Captura privada
xr-current-screen.png confirma Head/Controller/Send seleccionados, Hands no,
PC127.0.0.1 yWorking; visorAwake yTCP/reverse activos. Journal del PC registra
`device missing` a11:26:41 Europe/Madrid; reconexión efectiva aún no demostrada.
No atribuir el bloqueo a una configuración incorrecta del operador ni afirmar
que Working equivale a seguimiento válido.

Se reinicia sólo app PICO com.xrobotoolkit.client mediante ADB force-stop y
am start de UnityPlayerActivity. Sin reinicio de PC/robot ni START, backendSTOP,
tarea v4 permanece cargada. Evidencia xr-app-restart-after-sleep.json; capturas
y logs privados fueraGit. Receta reproducible: confirmar backendSTOP con
configure_pico_xr_usb.sh --check, adb -s PA94Y0MGKB070822G shell am force-stop
com.xrobotoolkit.client; adb -s PA94Y0MGKB070822G shell am start -n
com.xrobotoolkit.client/com.unity3d.player.UnityPlayerActivity; reconectar
127.0.0.1 yactivar Head+Controllers/Send data; repetir probar_pico_v4.sh --check.
No se cambiaron ajustes persistentes de suspensión ni binarios. Reversión:
cerrar app si no se usa; no restaurar sesiones de control transitorias.
Resultado de recuperación PENDIENTE al registrar este punto.


### 15-10-2026 — XR recuperado y corrección de lector ROS (VERIFICADO)

Tras reinicio de app y reconexión del operador, vr_status1 comprobado. App con
Shared network ha activado redUSB: PICO192.168.224.184→PC192.168.224.6:63901,
ruta por enxdabcd609068b, sysfs usb1/1-3:1.0. PC→robot sigue eno1/.11.250.
No se cambió NetworkManager desde el agente; el reverse anterior queda
configurado pero el stream actual usa redUSB directa. No llamarlo Wi-Fi.

Preflight real pasa paros, baterías63,3/66,3%, cargador fuera, reposo, tarea
v4 activa, una acción. Lector de manos aborta por AMENT_TRACE_SETUP_FILES no
definida al source del setupROS bajo nounset. Se corrige únicamente ese source
en check_v4_hand_states de scripts/teleoperation/cruzr_pico_teleop_pc.sh:
carga con set -Eeo pipefail y restaura set -u inmediatamente después; sin
omitir lectura, nombres/velocidades/timestamps. Prueba de regresión con
variable opcional ausente, 17tests pasan y bash -n correcto. Backup previo en
before-v4-ros-setup-fix, misma evidencia externa. Activación próxima ejecución;
reversión selectiva del fragmento desde backup. Sin cambios robot/SDK.

Se abre lanzador oficial v4, ventana120s, mismo cliente vendor hand y
enable_hand_pose0, cámaraoff. Perfil cargado0/0 ytracking1 comprobados.
Confirmación textual basada en condiciones físicas que el operador acaba de
confirmar. Al registrar este punto está revalidando preflight antes de START;
resultado, enable y efectos físicos aún PENDIENTES. No se marca ensayo completo.

Ensayo11:33–11:34 Europe/Madrid: preflight completo, V4_HAND_STATES_OK,
START oficial arm_typehand/enable_hand_pose0 y mandos frescos/neutros. No se
observa Y/enable1 en15s; cliente solicita STOP y confirma operation_type1.
Sin habilitación física demostrada. Operador confirma estar preparado para
siguiente aviso; se reintenta una ventana idéntica, sin ampliar timeout.


### 15-10-2026 — primer control PICO v4 con respuesta física confirmada

Segundo intento oficial ~11:35 Europe/Madrid: preflight nuevo pasa, estados
v4 válidos, mandos frescos/neutros; START arm_typehand y Y/enable1 observados.
Ventana120s, sólo brazos/manos, cabeza según perfil, cintura/elevador0. El
operador confirma: «Sí, brazo y mano responden bien», siguiendo grip y apertura/
cierre con gatillo, ensayo en vacío. Consulta de logs durante sesión sin los
patrones de salto/Excessive force/SAFEOP/fault en alcance recogido; no equivale
a certificar cualquier trayectoria. Evidencias v4-physical-test-operator-report
y v4-session-live-log-check.json. Captura/dataset/replay con v4 NO ensayados.
Sesión aún activa al registrar; STOP final pendiente de verificación. No
modificaciones de parámetros de movimiento ni protecciones durante la prueba.


### 15-10-2026 11:37 Europe/Madrid — PICO v4 probado en vacío; STOP final verificado

Ventana oficial120s terminada con código0. Cliente envía operation_type1 y
confirma OFFICIAL_TELEOP_STOP_CONFIRMED1; UI detenida, sinnuevoHOME ni cambio
de modo. CC mantiene teleop, brazos en postura final PICO, NO declarar HOME.
Lectura final cuerpo20D: velocidad0, sinfaults, delta máximo0,00235399rad.
Manos: dos muestras avanzando por lado, siete nombres correctos, velocidades
≤0,02rad/s, V4_HAND_STATES_OK. Estado estable medido después de STOP.

Resultado: inicialización v4 correcta y operador confirma movimiento de brazo
porgrip y apertura/cierre de mano porgatillo. No se ensayó agarre de objeto,
seguimiento óptico de dedos, captura ni replayv4. Sin cambio de límites, fuerza,
watchdogs o anticolisión. Fuente de control PCvendorarmhand y perfil v4 0/0.
Se conserva baseline globalPCclamp: override del cliente hand comprobado ahora
en esta sesión. Evidence v4-session-final-actuators/summary/hands.json y
v4-official-session-backend.log (privados). Fuentes exactas respaldadas en
after-v4-teleop-verified-sources conSHA256SUMS.

Repetición con tarea v4 ya cargada y condiciones físicas comprobadas:
PICO_TELEOP_CAMERA=off CRUZR_IFACE=eno1 CRUZR_PC_IP=192.168.11.250
PICO_OFFICIAL_TELEOP_SECONDS=120 bash scripts/teleoperation/probar_pico_v4.sh
--teleoperate (una única línea). El script exige confirmación y gates de nuevo;
Y una vez sólo al aviso, sin grip/gatillo hasta enableconfirmado. Si tras
reinicio está auto_task/HOME, hace falta cargar tarea v4 de forma supervisada;
no sustituir automáticamente por clamp ni saltarse ACTIVE_TASK_ERROR.
Mantener visor despierto/puesto; tras sueño, Working solo no demuestra vr_status1.


15-10-2026 — consulta de fuerza de cierre (OBSERVADO / PENDIENTE): lectura
del YAML v4 instalado confirma hand_ctrl_mode="cur", joint_closed
[1.8,1.2,1.2,1.2,1.2,1.2,1.2] y effort_ub [1.1]*7 en ambas manos. Esto
no demuestra adaptación automática al peso/deslizamiento ni fuerza mínima
necesaria de sujeción; tampoco demuestra uso de fuerza máxima física. Unidades
y traducción real del límite a fuerza de contacto pendientes de contrato
vendor/implementación. No se modifican parámetros ni se realiza agarre.


### Grabación v4 — receta, 15-10-2026 (ayuda instalada VERIFICADA; toma pendiente)

Consulta record -- --help en contenedor actual confirma utars_with_v4_hand y
--output. Grabador pasivo compatible con sesión PICO; no iniciar player a la vez.
Desde PC abrir segunda terminal, conectar Motion y entrar al contenedor:

```bash
ssh walker@192.168.11.2
docker exec -it walker-motion.manipulation_robot_app-1 bash
source /opt/walker/setup.bash
export ROS2CLI_DISABLE_DAEMON=1
mkdir -p /tmp/pico_grabaciones_v4
rosa run manipulation_outline_sdk record -- --robot utars_with_v4_hand --output /tmp/pico_grabaciones_v4/prueba_v4_01
```

Iniciar grabador antes de demostrar el movimiento en sesión teleop comprobada.
Ctrl+C en terminal del grabador guarda; no detiene la sesión teleop. Anotar
archivo real de Saved to, fecha añadida por SDK, y comprobar tamaño. Para sacar
carpeta desde shellhostMotion (salir sólo del contenedor):

```bash
exit
mkdir -p /home/walker/grabaciones_v4
docker cp walker-motion.manipulation_robot_app-1:/tmp/pico_grabaciones_v4/. /home/walker/grabaciones_v4/
ls -lh /home/walker/grabaciones_v4/
```

Desde PC se puede copiar con scp -r walker@192.168.11.2:/home/walker/grabaciones_v4 .
Al verificar toma: modelo/orden/grupos v4 y dedos, duración y datos válidos;
inspector actual clamp no certifica toma v4. Captura/replay v4 aún no ensayados.
El agente sólo consulta --help, no inicia grabación ni mueve en esta explicación.


### 15-10-2026 — inspección primera toma v4 (VERIFICADO; manos constantes)

Archivo hostMotion /home/walker/grabaciones_v4/prueba_v4_01_20261015_175142.motion,
29.979.113 bytes, SHA256
6cc5b2294b38168abe8786d9b4b7b296ef7cc99073fa1f76319785eae5a54f43.
Lectura JSON de sólo lectura, sinplayer ni órdenes físicas. Metadatos robotUtars,
sourceutars_teleop; grupos head2, left/right_arm7, left/right_hand7.
~29.116 muestras/grupo a~500Hz, duración máxima58,23999s; valores finitos,
dimensiones coherentes, tiempos estrictamente crecientes, gap máximo~4,013ms.
Movimiento significativo en cabeza y ambos brazos. Ambos canales de manos
permanecen constantes (variación máxima~1,73e-14rad), postura [0.8,0,0,0,0,0,0].
No afirmar que quedaron grabadas aperturas/cierres. Se pregunta al operador si
los ejecutó durante esta toma. Posible relación con modo corriente y canal
registrado es HIPÓTESIS, no demostrada. No certifica fidelidad de captura ni
admisión de reproducción. Inicio es postura PICO; final distinto, sinHOME.
Evidencia privada v4-record-01-structure.json y v4-record-01-validation.json.
Archivo original intacto, sólo se consultó en Motion; no se copió aún al PC.


### 15-10-2026 — limitación record v4 con perfil corriente (hallazgo)

Operador confirma que sí abrió/cerró manos físicamente durante toma01. Sus
canales q constantes no representan esos movimientos. No certificar captura
v4 completa sólo porque existen left_hand/right_hand y perfilSDKv4.
Binario instalado record444512bytes: strings/símbolos demuestran lectores
/mc/left_hand/command y /mc/right_hand/command de mc_task_msgs/JointCommand,
UtarsRecorder::RecordHandFrame. Disassembly de función identifica lectura del
vector aoffset0x40 al construir q, coherente con campo position de JointCommand
(Header40B, mode24B, position en64B). Mensaje verificado mediante ros2 interface
show en contenedor ROS: mode,position,velocity,torque,acceleration,names,kp,kd.
ROSA no tiene subcomando interface: primera consulta falló sin efectos, sustituida
por interfaz ROS2. Primer objdump con -C y símbolo mangled no mostró función;
se repitió sin-C y se obtuvo cuerpo. Evidencia v4-recorder-symbols.json y
v4-recorder-hand-reader-disassembly.json.

Perfil live hand_ctrl_modecur + capturaq constante + confirmación física apoyan
incompatibilidad entre formato de posiciones del grabador y cierre por corriente.
Falta verificar en una nueva muestra durante cierre la correlación mode/torque/
position: consulta actual /mc/left_hand/command agota8s (no se solicita movimiento
para producirla). /mc/left_hand/joint_states sí publica posiciones medidas
finitas y reposo; evidencia v4-recorder-command-vs-measured.json.

Consecuencia: toma01 válida estructuralmente para cabeza/brazos, insuficiente
para repetir fielmente dedos. Q no contiene la trayectoria perdida de manos.
Siguiente solución pendiente: capturar simultáneamente estados medidos y órdenes
completas (modo/esfuerzo incluidos), verificar apertura/cierre en toma corta y
compatibilidad del reproductor. No cambiar controlcur a posición ni relajarlímites
como supuesto arreglo. No alterar SDKoriginal ni reproducir el archivo actual
como si contuviera el cierre. Sin movimiento/configuración durante diagnóstico.


### PICO-V4-COMPLETE-CAPTURE-20261015 — grabador pasivo complementario

15-10-2026 Europe/Madrid. Fuente nueva PC:
`scripts/teleoperation/record_pico_v4_complete.sh`; SHA256 dc6735d24ec3dba975f8e4f2d97f1c2773c1352e3c48120e39c65f4e9678fde8.
Motivo: record nativo sólo conserva posiciones mandadas, insuficientes para
cierre cur observado en toma01. Nuevo lanzador añade ROSbag con mensajes
completos de manos (órdenes/estados MC y EtherCAT), órdenes cabeza/brazos,
estado articular del cuerpo y estados medidos de manos. Mantener .motion nativo
en paralelo si se necesita formatoSDK. Bag incluye datos para estudiar modos/
esfuerzos; no es un player ni transforma automáticamente bag a.motion.

Descubrimiento actual: walker-ros.ros2-1 incluye ros2bag con sqlite3; topics
y tipos contrastados. --check predeterminado consulta herramientas y canales
manos, sin escribir ni iniciar captura. --record NOMBRE exige terminal, nombre
alfanumérico/_/-, usaSSH interactivo conocido hacia walker@192.168.11.2.
No SDKedit, parámetros del robot, START, cambio de modo o reproducción.
QoS best_effort/volatile keep_last2000 por topic, caché16MiB; suscripción
compatible con publishers BEST_EFFORT. QoS se escribe sólo para sesión nueva.

Archivos nuevos sesión: /tmp/pico_v4_capture_NOMBRE_UTC_PID en ROScontainer,
rosbag/sqlite+metadata yqos.yaml. TrasCtrl+C exporta a hostMotion
/home/walker/grabaciones_v4_completas/NOMBRE_UTC_PID y ejecuta baginfo. Rechaza
sobrescritura. No depende de mantener sólo /tmp: copiahost comprobada.
Reversión: conservar/exportar grabaciones, retirar selectivamente lanzador y
sus carpetas de prueba si se decide; no restaurar estado transitorio de control.
No servicio/autostart instalado ni configuración persistente de robot/PC cambiada.

VALIDACIÓN: bash-n y --help correctos; --check real pasa. --record ensayado
pasivamente, Ctrl+C limpia/cierra, copiahost ybaginfo terminan rc0. Prueba
8,4006s, 9190mensajes, sqlite8.175.616B, cuenta manos medidas832/830,
whole_joint_states4184, buscmd834/832, busstate840/838. No mensajes de
órdenesMC en esta captura en reposo; captura durante teleop aún PENDIENTE.
No afirmar que una simple creación de bag garantiza cobertura de toda demo:
revisar recuentos y rango de dedos en toma corta activa antes de reproducción.
Carpeta host /home/walker/grabaciones_v4_completas/
comprobacion_pasiva_20261015T100041Z_431556. SHA256 DB
a36c35802f2ae67cdc890b14e2ceaa3fdff5a82f4e7bde15bc33f046cded85a8.
Evidencia privada v4-complete-capture-tools.json y
v4-complete-capture-passive-proof.json con hashes yrecuentos.

Procedimiento para operador desde raíz repoPC:

```bash
bash scripts/teleoperation/record_pico_v4_complete.sh --record prueba_v4_02
```

Dejar abierto hasta Subscribed, mantener grabador.motion anterior en otra
terminal si se requiere. Iniciar teleop v4 por procedimiento ya comprobado y
hacer toma corta en vacío con condiciones físicas actuales. Ctrl+C sólo en
terminal de grabación guarda/copia; no detiene teleop. Revisar datos antes de
repetición. No ejecutar ros2bagplay sobre topics de mando directamente: el
reproductor/continuidad/modos de esfuerzo requieren adaptación y validación
propias. Reproducción bag completa y nueva toma activa PENDIENTES.


### PICO-V4-TAKE05-20261015 — captura activa validada; reproducción pendiente

Archivo hostMotion /home/walker/grabaciones_v4_completas/
prueba_v4_05_20261015T101134Z_462191/rosbag/rosbag_0.db3.
SHA256 be1bc75a17c9e06c97cddff6ef320c371eef9d7a197b66e11fc9b3fdbb462bcb
coincide en copia host y original ROScontainer. Duración44,33s,159430mensajes,
97,9MiB; sqlitequick_checkok. Sólo lectura; no reproducción ni movimiento.

Nuevo inspector PC scripts/teleoperation/inspect_pico_v4_bag.py: abre SQLite
mode=ro, verifica metadata/DBúnica, estabilidad del archivo y quick_check,
deserializa sin crear nodoROS, resume campos position/velocity/effort/torque,
modos, dimensiones/finitos y tiempos; hashSHA256. Requiere entornoROScon tipos,
no se instala paquete adicional. Fuente guardada en evidencia conhash; fuente
reproducible versionada. Reversión retirar helper, conservar grabaciones.
Validación real toma05 completa y compilación Python; no confundir esta revisión
de datos con admisión de replay o certificación de trayectoria.

Resultados: movimiento cabeza/ambos brazos; estadoswhole22149 contienen
head_pitch/head_yaw aunque topic separado /mc/head/joint_states tiene0.
No significa pérdida de cabeza: órdeneshead22169 y medición enwhole. Manoizq
medida4394 muestras, rango máximo1,262869rad(~72,36°), ordencorriente/torque
rango1,1 y modos5/7 observados, unidades/semántica exacta pendientes. Mandos
de posición permanecen constantes como toma01; ahora sí se conservan las
variaciones reales/órdenes completas. Manodcha4394muestras, rango máximo
0,023394rad(~1,34°); orden position/torque constante, modo5. No afirmar ciclo
amplio de apertura/cierre de ambas manos: en derecha casi no hubo variación.
Ambasórdenesmano22168muestras porlado; ordencada brazo22169.

Sin valores nofinitos/dimensiones incoherentes ni retrocesos de tiempos en
canales analizados. Mayorhueco de recepción~31,8ms; whole incluye19cabeceras
repetidas. No afirmar captura sinpérdida o continuidad perfecta. Evidencia
v4-take05-analysis.json, -analysis-receipt.json, -first-messages.json y
-host-copy-checksum.json. Primera consulta de tipos falló por quoting del
fragmento Python, corregido con shlex.quote; sin efectosrobot.
Resultado captura activa útil para preparar replay, incluido cierreizquierdo;
reproducción adaptada y revisión de modos5/7 siguen PENDIENTES.


### PICO-V4-GEOMETRIC-REPLAY-20261015 — derivado preparado, ejecución pendiente

Usuario solicita reproducir toma05 y confirma manos vacías, trayectoria libre,
cargador fuera, persona junto al paro y otros mandos detenidos. Estado técnico
leído: CCJoystickMode, PCSTOP/UIinactiva/sinpico_control; cuerpo/manos reposo,
sinfaults/deltaactuador máximo0,003284rad, paros0/0, batería56,3/60,5%,
cargador0, móduloslibres. SDK OutlineSdkPlay tiene1server/0clientes; controladores
manipulation/force_torque/dexterous_hand running. Primera consulta a endpoint
ROS2supuesto de controllers falló sin invocar movimiento; descubrimiento real
/mc/controller_manager/list_controllers rosa_control_msgs/srv/ListControllers
y consulta correcta. No asumir nombres/tipos antiguos.

Preparación geométrica: scripts/teleoperation/pico_v4_bag_to_motion.py, sin
publicadores ni cambiosSDK. Consume bagSHAverificado sólo lectura; cabeza y
brazos desde órdenes por nombre, dedos desde posiciones medidas. Valida nombres,
finitos, tiempos estrictos, SQLite yhash; salida exclusiva nueva. Usa cabeceras
con origen común para sincronía, retiene primera/última postura hasta cubrir
ventana común, factor2 tiempos (mitadvelocidad), sin cambio de posiciones.
No reproducecorriente/torque ni modos5/7 originales. Se ha comunicado al usuario
que esta prueba vacía repite geometría, sin demostrar sujeción o fuerza.
SDKinstalado soporta --robot utars_with_v4_hand; ordencontrastado YAML instalado.
Playerhash8744a30ecce20c414dcf67b60d9aa7ac486bab752d5eee3de08a7336d65ddf0d.
No --loop por bugconocido; no se modifica SDK/interpone código para ejecutar.

Derivado88,6730752s, SHA256
c2aa12373b4209a77cdc594787f475762b130b468c7fda403473b95f414b2003.
HostMotion .../prueba_v4_05_20261015T101134Z_462191/derived/
take05_geometry_slow.motion; appMotion /tmp/pico_v4_replay_take05_20261015/
take05_geometry_slow.motion. Hashes comparados después de copiar; originalbag
intacto. Archivo .motion no conserva el esfuerzodeagarre; no confundirlo con
réplica exacta de mando corriente. Mayorpaso por muestra0,03682rad en dedos;
brazos≤0,003287rad, cabeza0,004rad; interpolaciónSDK a mitadvelocidad.
Comparacióninicio por nombres: cabeza0,004410rad, brazoizq0,005340,
brazodcha0,005435, manoizq0,001151, manodcha0,003643 (<0,02rad).

Evidencia take05-conversion/receipt.json, take05-derived-stage.json,
take05-replay-current-state.json, take05-initial-comparison.json,
take05-pc-control-exclusion.json y take05-running-controllers.json.
Recrear: ejecutar convertidor en entornoROS con tipos del bag y --time-scale2
--expected-sha256 del original, copiar derivado nuevo al appMotion y comparar
hash; freshpreflight + físico antes de ejecutar una sola vez playerSDK.
Reversión: conservarbag original, retirar selectivamente derivado/helper si se
descarta; sinconfiguraciónpersistente de robot cambiada. Ensayo físico de este
derivado aún PENDIENTE; no se envió movimiento por la preparación.

Primera pasada iniciada por SDKOutlineSdkPlay, goal5080f40a-2f44-4111-bf13-3fa1b6c02957,
robotutars_with_v4_hand/loop1, sin--loopexplícito. SDK confirma aproximación inicial
de ambas manos; operador informa «Sí, está repitiéndolo bien», incluido cierre
izquierdo, sin resistencia/movimientoinesperado reportados. En curso todavía,
resultado y reposo final pendientes. Evidencia take05-replay-invocation.json,
stdout/stderr.log y take05-replay-live-log1.json; sin nuevos objetivos ni HOME.


### PICO-V4-GEOMETRIC-REPLAY-20261015 — PROBADO FÍSICAMENTE, terminado

15-10-2026 Europe/Madrid: 12:21:54–12:23:24. Una ejecución del
player oficial --robot utars_with_v4_hand --input
/tmp/pico_v4_replay_take05_20261015/take05_geometry_slow.motion, sin--loop.
returncode0, stderrvacío, resultado textual `Action finished with
is_finished=true, bag has been played successfully`. Usuario confirma durante
la pasada que repite bien movimiento y cierreizquierdo, sin resistencia ni
movimiento inesperado reportado. Hardwarelogs de vigilancia sin patrones de
salto/SAFEOP/sobreesfuerzo/fault en el alcanceconsultado.

Postflight nuevo: velocidadmáxima0 en cuerpo ydedos, sinerror_code, delta
actuador/consignamáximo0.003044677rad. Errores respecto
al final del derivado porgrupo: {"head": 0.0013271863844168674, "left_arm": 0.002721995185922088, "right_arm": 0.003044676516222866, "left_hand": 0.005752515730995, "right_hand": 0.0013422536705656185}. Máximo
~0,005753rad en manoizquierda. Estado medido enreposo, conserva postura final
de la toma; NO HOME. Sin nuevos objetivos, cambios de modo o reinicios alfinal.
Clienteplayer terminó; PICO/web se mantuvieron sin mando durante replay.

Queda demostrada reproducción GEOMÉTRICA en vacío de cabeza/brazos/dedos a
mitadvelocidad. No se reproduce el esfuerzo original ni se valida agarrar una
pieza. La escasa variación de mano derecha pertenece a esta toma; no se añade
un cierre inventado. Bagoriginal y sus corrientes/modos se conservan intactos.
No se reprodujeron directamente topics ROS/EtherCAT ni se desactivaron
protecciones; se usó SDK nativo ya instalado. No extrapolar a replay de fuerza
o retención de objetos.

Evidencia: take05-replay-result.json, .stdout/.stderr.log,
take05-replay-postflight.json y -postflight-summary.json, comparacióninicio
y archivos de conversión/stage. Fuentes reproducibles del convertidor nuevo y
los helpers de captura/inspección en repo; before/after/hash externos en esta
carpeta privada. No commit/push.

Próximas tomas con mismoSDK/perfil: reutilizar conversor, nombres/orden y
recetaSDK comprobados; no repetir investigación binaria/interposer. Sí validar
bag/hash/cobertura/rangos, derivado y comparaciónactual de postura/repose/
paros/cargador/fallos/exclusividad. No usar rawactuator para compararq: comparar
por nombres con whole_joint_states y estados reales de manos. No--loop1.
Cambios de efector/software requieren redescubrimiento del contrato.
