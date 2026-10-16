# Demostraciones de manos Cruzr S2

**16-10-2026 — SWITCH-EFFECTOR-RESTORE-20261016: restauración CORREGIDA y cambio a v4 VERIFICADO.**
La sesión `EFFECTOR-20261016T081258Z-1bddf143` instaló SPS y recreó los nueve
servicios Motion y CC; falló antes de arrancarlos al restaurar historiales sobre
bind mounts de CC. Respaldos externos e internos íntegros. Lectura fresca:
contenedores creados/detenidos, principal pulsado, servos liberado, cargador fuera,
baterías 88,3/89,2%. Sin HOME ni START PICO enviados.
Corrección local: excluir montajes también en respaldos antiguos y omitir copia
vacía; reanudar la misma sesión mediante `--resume-from`, sin repetir recreación.
[Receta y límites](../../docs/guides/CAMBIO_EFECTOR_ABRAZADERAS_MANOS_V4.md). Reanudación ejecutada: Motion restaurado verificado, Vision sin copia sobre
montajes (restauración efectiva vacía), servicios arrancados bajo paro. Tras
confirmación del operador y liberación manual, HOME20D medido en dos muestras
avanzantes, velocidad0, sin fallos, delta máximo0,002876rad y estados válidos
avanzantes de siete ejes por mano. dexterous_hand_controller running.
Resultado PERFIL_Y_HOME_VERIFICADOS=v4; sesión cerrada en ambos hosts tras
comprobar archivos. No reinicio físico ni HOME adicional. Siguiente paso:
entrada controlada a PICO v4 con sus gates actuales; no se inició teleoperación.
Evidencia privada: sesión original, `recovery/` y
`EFFECTOR-20261016T082431Z-0cf31f55`. No borrar `active.json`.

**16-10-2026 — PICO-V4-GATE-20261016: bloqueo por tarea clamp, diagnóstico VERIFICADO.**
Operador confirma reinstalación de manos v4 ante pregunta de montaje con robot
apagado. Lectura nueva: hw/app/CC siguen HW_TYPE=cruzr_s2_v1 y restart0.
CC entra TeleopMode y el último arranque de tarea es cruzr_clamp_pico_teleoperation,
Hand type clamp, waist0/leg0. YAML v4 conserva SHA esperado01a5ca8…; no es
corrupción del archivo. Faltan topics MC de estados de manos bajo este perfil.
El mensaje genérico del lanzador es anterior a START; en este caso no encontró
la tarea v4 requerida. Repetir el mismo --teleoperate no cambia el perfil nativo.
Muestra20D: reposo0, sinfallos, delta0,003230rad, maxposición1,568783rad,
MEASURED_HOME0: postura inicial PICO/clamp. No inferir HOME del chequeo de arranque
anterior. No enviar HOME, reiniciar ni cambiar modos para probar desde ahí.
Migración SPS y posterior entrada controlada a Teleop v4 pendientes. La guía del
selector contempla --secured-recovery con brazos asegurados, paros/cargador y
verificación; no se ejecutó en esta intervención. El selector termina en HOME,
no activa por sí mismo TeleopMode ni STARTPICO.
Evidencia privada `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20261016T081039Z_PICO_V4_GATE_READONLY`: perfiles/instancias, logs actuales, último bloque de
tarea, hashYAML, inventario y muestra/clasificación. Solo lectura, cero cambios
remotos/movimientos; copias documentales before-docs y SHA256SUMS en evidencia.


**16-10-2026 — WUJI-COMPATIBILITY-20261016. Evaluación documental, sin instalación.**
Publicación identifica WUJI Hand2; manual actual corresponde a2.2 Beta no táctil:
20ejes, Ethernet100BASE-TX/RJ45, XT30 y11–13V DC nominal12V. Fabricante avisa
que interfaces cambiarán en revisiones posteriores. SKU/versión ofertada pendientes.
La unidad S2 observada el15-10 integra manos nativas en cadenaEtherCAT con puente
EtherCAT-CAN y siete servos publicados por mano; esto NO identifica el pinout de
la muñeca ni acredita compatibilidad eléctrica/protocolaria con WUJI. Pinout,
tensión/potencia disponible, brida, carga/TCP e integración de paros pendientes.
Nuestro selector clamp/v4 sólo contempla perfiles nativos; no habilita WUJI.
Se requiere integración específica y confirmación de interfaces por proveedores;
no basta un adaptador pasivo ni disponer de ambosSDK. Sin conexión al robot,
movimiento, configuración, instalación ni contacto con terceros en esta revisión.
Fuentes: [manual WUJI2.2 Beta](https://docs.wuji.tech/docs/wuji-hand/latest/product-introduction),
[SDK oficial](https://github.com/wuji-technology/wuji-sdk),
[producto](https://wuji.tech/en/hand2).
Evidencia local previa HANDS-V4-BUS-IDENTITY-20261015; índice de consulta privado
20261016_WUJI_COMPATIBILITY. Las afirmaciones comerciales no son ensayos en S2.


## Cambio coordinado entre abrazaderas y manos v4

Usar la entrada única del PC:

```bash
bash scripts/hands/cambiar_efector.sh --to v4 --check
bash scripts/hands/cambiar_efector.sh --to v4 --apply
# En sentido contrario, después del cambio físico con el robot apagado:
bash scripts/hands/cambiar_efector.sh --to clamp --apply
```

`--check` es el modo por defecto; `--apply` es interactivo y puede continuar HOME
al liberar físicamente el paro. No se cambia el hardware con el robot encendido.
[Secuencia, recuperación, verificaciones y estado de validación](../../docs/guides/CAMBIO_EFECTOR_ABRAZADERAS_MANOS_V4.md).
Herramienta nueva: 29 tests offline y --check reales; --apply integral en ambos
sentidos pendiente. No reutilizar el HOME histórico como postura actual.



**15-10-2026 — RETURN-CLAMP-20261015: perfil base CARGADO; arranque/HOME VERIFICADOS.**
Usuario solicita retirar dependencia v4 tras desmontar manos. Compose Motion y
selector CC/metafile Vision vuelven al perfil de abrazaderas; DB Motion ya base,
conservada. Lectura confirma que controlador base no carga dexterous_hand_controller.
Actualización: operador confirma paro pulsado/brazos asegurados; nueve Motion
y CC recreados con mismas imágenes, Cmd/montajes y resto del entorno. Archivos
personalizados restaurados/hash verificados; hw/app base running/restart0. Guard
CC Motion3/3/cámaras2/2, liberación confirmada por operador; SelfCheck y
StartMotion succ→JoystickMode. HOME20D medido, velocidad0, sin fallos de
actuadores y delta máximo0,002972rad. Muñecas vacías; no reinicio físico necesario.
No volver a usar PICO v4 hasta reinstalar manos y recuperar perfil SPS. Recetas nuevas restore_clamp_environment.py y
activate_clamp_profile.py; respaldos privados en 20261015_RETURN_CLAMP.
[Aplicación, límites, evidencia y reversión](../../docs/incidents/2026-10-15_ARRANQUE_SIN_MANOS.md).


**15-10-2026 — HANDS-REMOVED-BOOT-20261015: manos retiradas, arranque fallido.**
Operador informa muñecas sin efectores para embalaje. Bus OP/hand cnt=0,
pero HW y CC conservan SPS y carga de dexterous_hand_controller falla por
get_version ausente. StartMotion→Fault, app reinicia; no inferir sensor averiado.
Perfil compatible sin efectores y recuperación pendientes. Solo lectura.
[Informe](../../docs/incidents/2026-10-15_ARRANQUE_SIN_MANOS.md).


**15-10-2026 — BOOT-CC-SPS-20261015 / selector CC:** HW_TYPE SPS instalado y
sólo CC recreado con mismaimagen/orden/montajes. Guard de arranque actualizado
para reconocer identificadorSPS conservando gates yvoz;18tests pasan.
Principal1 ybrazos asegurados confirmados; Motion no reiniciado, sinHOME/START.
Consignas latentes siguen pendientes: apagado supervisado en preparación,
paro mantenido. Detalle/rollback/evidencia en PICO_MANOS_V4_20261015.


**Ampliación 15-10 — postura PICO incompleta:** logs HW confirman rechazo
`send a jump command` (>0,087rad) en cuatro ejes, no contacto según operador.
Cancelación a auto_task deja consignas latentes~1,57rad; HOME/reset/rearme
bloqueados por guía de recuperación. Sin nuevos movimientos/restart.
Selector CC preparado offline en prepare_pico_v4_cc_env.py (sólo CC, no global),
NO instalado. Recuperación documentada y corrección/ensayo todavía pendientes.
Detalle/evidencia en PICO_MANOS_V4_20261015 y20261015_PICO_V4_PROFILE.


**15-10-2026 — PICO-V4-CC-SELECTION-20261015: PICO aún NO habilitado.**
CC con HW_TYPE antiguo seleccionó tarea clamp al entrar en teleop; Motion síSPS.
Inicialización de brazos incompleta/asimétrica, medida/consigna difieren~1,57rad.
Se cancela pasando a auto_task; velocidad medida0/sinfallos, consigna antigua aún
no coincide. Sin START PC ni HOME; no declarar postura lista ni teleop v4 probada.
Selector CC, recuperación a HOME y ensayo v4 pendientes. Detalle en ficha PICO v4.
Evidencia20261015_PICO_V4_PROFILE fueraGit; no restart/cambioenvCC en esta fase.


**15-10-2026 — PICO-V4-PROFILE-20261015: SPS CARGADO; HOME y estados v4 VERIFICADOS.**
[Estado, receta, respaldos y reversión de manos v4](../../docs/teleoperation/PICO_MANOS_V4_20261015.md).
YAML v4 sólo brazos instalado, no cargado; HW_TYPE SPS aplicado y Motion recreado.
Selector PC y comprobación de siete articulaciones preparados,19 tests pasan.
HOME medido antes del paro; operador confirma paro principal pulsado para migración.
Respaldos Motion/Vision externos y hashes verificados. Ethernet eno1 confirmado.
Mismas imágenes,3+59 archivos restaurados/verificados; operador libera paro.
CC termina StartMotion y JoystickMode; HOME20D máximo0,002493rad/velocidad0/sinfallos.
Ambos controladores v4 cargados; estados frescos7ejes/mano pasan checker ROS2.
Sin START PICO: tarea TeleopMode v4, ensayo de gatillos y replay aún pendientes.
No se requiere otro reinicio; seguimiento posterior sólo lectura.
Evidencia privada ../Humanoide-vla-evidence/20261015_PICO_V4_PROFILE/.


**15-10-2026 — HANDS-V4-BUS-IDENTITY-20261015: INSTALADO y CARGADO; arranque verificado.**
Actualiza el estado offline anterior. Operador confirma manos vacías, trayectoria
libre, otros mandos detenidos y persona junto al paro. Aclara finalmente paro
principal liberado. Antes de recarga: lecturas nuevas principal0/servo0,
cargador0 (antes se observó carga2; no se omitió el bloqueo), baterías84,1/71,7%.
Las consultas iniciales de paros con timeout corto expiraron; tipo UInt8 explícito,
RELIABLE/VOLATILE y timeout10 recibieron0/0. No se fingieron estados.

Aplicación reproducible desde PC, sin activar por este instalador:
`python scripts/hands/install_v4_bus_profile.py --check --evidence /RUTA`
y `--install` en lugar de `--check`. Instalador verifica hash original y PID1
esperando arranque, conserva propietario/permisos y sustituye atómicamente.
Acepta un perfil ya corregido como comprobación sin cambio. Destino Motion,
walker-motion.hw-1, /opt/walker/ubt_ethercat_master/bin/eni_cruzr_kw_unified_noimu.xml.
Original SHA1b0c9323a7dc1fa627aa4bfddae216374cea2f68157b7a0e8739176f42843d1d;
instalado SHA678c7d6bae1608709400383d85c6e0e5edae7032b365d11977cb56bc984250e8.
Backup remoto: /etc/walker/customizations/hands-v4-bus-20261015/
eni_cruzr_kw_unified_noimu.xml.before y receipt.json. Original externo también
en evidencia. Sólo dos valores XML cambiados, todas las comprobaciones conservadas.

Activación autorizada: un único `docker restart --time 5
walker-system.control_center-1` en Vision (rc0); no restart de hw, no start ROS
forzado ni HOME adicional. Guard pasa y CC recorre Recover/SelfCheck/StartMotion.
El maestro selecciona automáticamente el ENI corregido y actualiza por sí mismo
/opt/walker/ubt_ethercat_master/share/ubt_ethercat_master/config/dynamic_config.yaml:
last_eni pasa de eni_cruzr_kw_noimu.xml a eni_cruzr_kw_unified_noimu.xml.
Este cambio persistente es efecto del arranque; no restaurar el valor antiguo
como configuración vigente de manos. Tiempos PC/robot difieren alrededor de52s;
no comparar sus marcas directamente. Logs Docker del nuevo ciclo:
07:51:52Z selecciona perfil; versión4 obtenida de ambas manos;
07:51:56Z maestro SAFEOP→OP. No repite el fallo de selección/IMU observado antes.

Controladores manipulation, fuerza/par y estados en running, servicio responde.
Muestras nuevas /ecat/left_hand/state y right_hand/state: palm_connect=True,
servo_cnt=7, velocidades0 y servo_status publicados0 (no se interpreta ese0
como diagnóstico universal). Dos errores de SDO en direcciones antiguas18001/2
y objeto2004:7 ausente en8001 aparecen durante inicialización; no impidieron
OP/HOME/telemetría. Causa/impacto de esos avisos aún PENDIENTES, no borrados.
/mc/left_hand/joint_states y /mc/right_hand/joint_states aún no figuran en el
listado tras carga; el checker actual depende de ellos y no queda certificado
CHECK_OK. No forzar su gate; adaptación del control v4 es fase siguiente.

CC registra LimbMotion/StartMotion succ y JoystickMode. Muestra posterior de22
actuadores:20 ejes de cuerpo cerca de HOME, máximo0,00278034rad,
velocidad máxima0 y error_code0; dedos no incluidos en HOME20D.
Paso1 resuelto para inicialización del bus y recepción de estados v4; teleoperación,
movimientos de dedos, grabación/replay v4 y arranque en frío posterior PENDIENTES.
No se envió START PICO ni tarea de demostración de manos.

Reversión: sólo con control detenido/esperando, estado físico preparado y sin
otros mandos, comprobar hash instalado, comprobar SHA original del .before y
restaurar únicamente ese XML conservando permisos. Recargar mediante arranque
supervisado; no copiar dynamic_config antiguo sobre la selección actual ni
retirar sensores para sortear el fallo. Antes de recrear contenedor/actualizar,
conservar copia externa y reaplicar selectivamente según ficha. Persistencia en
recreación Docker no verificada. No se ejecutó rollback.

Fuentes/scripts, recetas, metadata, validación offline, install.json, postcheck,
logs antes/después, estados de manos y body-final-classification.json en
../Humanoide-vla-evidence/20261015_HANDS_V4_BUS_DIAG/.
Documentación before-install-docs/ y after/, SHA256SUMS. No commit/push.


**15-10-2026 — HANDS-V4-BUS-IDENTITY-20261015. VERIFICADO offline; no instalado.**
Ampliación/corrección del diagnóstico HANDS-V4-PREFLIGHT: no atribuir el fallo a
una IMU averiada. `dynamic_config.yaml` recuerda `eni_cruzr_kw_noimu.xml`, perfil
sin IMU EtherCAT que ya se utilizaba con abrazaderas. El escaneo del arranque
fallido contiene 27 dispositivos, incluidos ambos sensores Kunwei y dos
`hand unified`. El candidato vendor `eni_cruzr_kw_unified_noimu.xml` coincide
en número, orden de vendor/product y tipos salvo el puente 18000: vendor ENI
0xffffffff frente a vendor físico 0xe0000002. Su InitCmd también exige literalmente
ffffffff. La comparación no prueba por sí sola el algoritmo interno de selección
ni la causa única del fallo; el mensaje de IMU es insuficiente para diagnosticar
hardware y la activación del derivado sigue PENDIENTE.

Receta reproducible exclusivamente offline:
`python scripts/hands/prepare_v4_bus_profile.py --input ORIGINAL --output DERIVADO`.
Sólo acepta SHA256 original
1b0c9323a7dc1fa627aa4bfddae216374cea2f68157b7a0e8739176f42843d1d.
Cambia sólo VendorId del puente a 3758096386 y Validate/Data de su check vendor
a 020000e0 (mismo valor y comprobación que el perfil anterior de esta unidad).
No suprime comprobaciones, no altera PDO, sensores, límites ni watchdogs.
SHA256 derivado: 678c7d6bae1608709400383d85c6e0e5edae7032b365d11977cb56bc984250e8.
Verificación: exactamente dos hojas XML distintas, 27 identidades vendor/product
coinciden con el escaneo, fuentes alteradas rechazadas. Direcciones físicas
actuales de manos 18001/18002 difieren de las direcciones de configuración
8001/8002; su asignación por maestro aún no verificada. No inferir publicación
fresca ni manos operativas de este ensayo offline.

Destino previsto, NO aplicado: Motion, contenedor walker-motion.hw-1,
/opt/walker/ubt_ethercat_master/bin/eni_cruzr_kw_unified_noimu.xml.
Antes de aplicar: copia externa original ya conservada; respaldo remoto y
comprobación hash inmediata. No modificar dynamic_config ni forzar start como
supuesto arreglo. Cargar mediante secuencia de arranque revisada sólo después
de confirmar estado físico, paros, zona y exclusión de otros mandos: puede
iniciar homing. Después verificar bus, controladores y estados frescos de manos.
Reversión prevista: restaurar exactamente el XML original respaldado y verificar
su SHA; cualquier recarga vuelve a requerir comprobar estado físico.

Evidencia: ../Humanoide-vla-evidence/20261015_HANDS_V4_BUS_DIAG/ (logs,
inventario, perfiles originales/derivado y offline-validation.json).
Cambios de esta intervención sólo en PC: receta y documentación; robot sólo
consultado. Backup documental before/, estado after/ y SHA256SUMS en evidencia.
Revertir sólo esta ficha y la receta si se descarta; conservar cambios ajenos.
Pendientes: instalación, carga, validación física y adaptación PICO v4.
No commit/push.


**15-10-2026 — HANDS-V4-PREFLIGHT-20261015. OBSERVADO; activación PENDIENTE.**
Operador informa instalación de manos v4 con el robot apagado. Diagnóstico sólo
lectura: el escaneo EtherCAT reconoce dispositivos 18001 y 18002 como
`hand unified`, pero el intento de inicialización de las 07:34:45–50 UTC falla
por dispositivo 10000 no encontrado (mensaje vendor: IMU de movimiento, primer
dispositivo del puerto 2 del switch de cintura). No demuestra avería de IMU ni
modelo v4 por sí solo. El contenedor hw se reinicia una vez; la instancia actual
queda esperando `/mc/rosa_control/start`, sin proceso EtherCAT en `ps`.
La aplicación espera ListControllers y la consulta de ese servicio agota timeout;
los topics `/mc/left_hand/joint_states` y `/mc/right_hand/joint_states` faltan.
Los topics `/ecat/*_hand/state` por sí solos no prueban publicación fresca.
`check_hands.sh --model auto` rechaza correctamente la detección.

Existe tarea instalada `teleoperation/cruzr_v4_pico_teleoperation` y YAML
`cruzr_v4_pico_tele.yaml` con hand_type=v4, waist_mode=1 y leg_mode=2.
El lanzador PC actual sigue fijado a clamp y bloquea gatillos; no reutilizarlo
para v4 sin adaptación deliberada de tarea, cliente, controles y validaciones.
Para grabar/reproducir manos se requiere el perfil `utars_with_v4_hand`;
el inspector local de motion actual sólo admite Utars de abrazaderas.
Primero resolver arranque/topología, después configurar y comprobar v4 con
cintura/elevador bloqueados si se mantiene alcance sólo brazos. No sustituir ENI
por una variante noimu ni cambiar HW_TYPE como supuesto arreglo.

Evidencia privada: `../Humanoide-vla-evidence/20261015_HANDS_V4_PREFLIGHT/`
(metadata de tarea/YAML, listado de servicios/topics, logs, StartedAt/reinicios,
procesos y respuesta de controladores). Rutas remotas consultadas:
Motion, contenedores `walker-motion.hw-1` y
`walker-motion.manipulation_robot_app-1`; `/opt/walker/`.
No movimiento, HOME, reinicio, START ni modificación de robot/PC de control.
Cambios únicamente documentales PC en esta ficha y fuentes especializadas;
respaldo selectivo before/, copia after/ y SHA256SUMS en evidencia.
Reversión: retirar sólo el bloque HANDS-V4-PREFLIGHT-20261015; conservar cambios
anteriores del usuario. Configuración instalada v4 observada, carga y prueba
física PENDIENTES. Reanudar con diagnóstico del fallo de inicialización del bus.
No commit/push.


Estos scripts orquestan exclusivamente tareas de fábrica ya instaladas en el
robot. No instalan XML, no activan GR00T/VLA y no convierten las secuencias en
manipulación autónoma. Antes de cualquier movimiento identifican las manos por
sus topics ROS 2, leen batería, cargador y paros y verifican los XML contra
`factory_tasks.sha256`. Las primitivas referenciadas por los gestos y el mando
se verifican además contra `factory_meta.sha256`.

## Orden obligatorio

1. Instalar físicamente las manos siguiendo el SOP de UBTECH.
2. Completar homing sin errores.
3. Dejar ambas manos vacías y el robot en `home`.
4. Mantener 1,5 m libres alrededor y sobre los brazos.
5. Preparar una segunda persona junto al paro físico.
6. Ejecutar primero el diagnóstico:

```bash
./scripts/hands/check_hands.sh --model auto
```

Si no detecta inequívocamente v3 o v4, no se debe forzar el modelo.

Los XML pueden auditarse antes de instalar las manos, también sin movimiento:

```bash
./scripts/hands/check_factory_tasks.sh
```

## Demostraciones en vacío

Todos los comandos se pueden comprobar sin movimiento sustituyendo `--run`
por `--check`.

```bash
# Movimiento secuencial de dedos y apertura/cierre bimanual.
./scripts/hands/demo_dexterity.sh --run --model auto

# Pinzas pulgar-índice, pulgar-medio y pulgar-anular; sólo v4.
./scripts/hands/demo_precision_v4.sh --run

# Gesto con brazo derecho y retorno a cero.
./scripts/hands/demo_expressive.sh --run --model auto

# Coreografía compacta recomendada para el vídeo del CEO, sin objetos.
./scripts/hands/demo_ceo.sh --run --model auto
```

`--yes` omite la confirmación inicial únicamente en las demostraciones sin
objetos. No omite ninguna comprobación técnica.

## Demostraciones con objetos

Estas tareas contienen trayectorias fijas de fábrica: no localizan la bandeja
ni el mando con la cámara. Primero deben ensayarse en vacío y después con un
objeto ligero, sin personas dentro del alcance.

```bash
./scripts/hands/demo_functional.sh --check --demo plate --model auto
./scripts/hands/demo_functional.sh --run   --demo plate --model auto

# Sólo manos v4.
./scripts/hands/demo_functional.sh --check --demo remote
./scripts/hands/demo_functional.sh --run   --demo remote
```

El script siempre se detiene para que un operador apoye el objeto antes de
abrir las manos. Si se cancela en ese punto, no ejecuta automáticamente `home`.

## Recuperación con manos vacías

Si una demostración en vacío termina entre tareas, retirar primero cualquier
objeto, despejar completamente los brazos y ejecutar:

```bash
./scripts/hands/recover_hands_home.sh --check --model auto
./scripts/hands/recover_hands_home.sh --run --model auto
```

No debe usarse mientras otra acción siga activa ni con un objeto agarrado.

## Qué se puede afirmar en el vídeo

- `Factory hand dexterity`: movimientos de dedos y pinzas preprogramados.
- `Factory fixed-pose manipulation`: bandeja o mando en pose preparada.
- No anunciar `autonomous object manipulation`: estas tareas no ejecutan un
  detector, grasp planner ni política VLA.


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
