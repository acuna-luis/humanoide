# Cruzr S2 — fuente de verdad global del proyecto

**Última actualización:** 4 de septiembre de 2026
**Unidad:** Cruzr S2, SN `WAE001UBT60000669`  
**Propósito:** relevo técnico y operativo entre sesiones, personas y agentes

Este documento es el índice vivo del proyecto completo. Conserva el estado
conocido del robot, las modificaciones persistentes, lo que ya funciona, los
bloqueos y el punto de reanudación. No sustituye las guías especializadas ni
certifica el estado físico actual.

`AGENTS.md` obliga a Codex a leer esta fuente al iniciar una sesión desde el
repositorio. Si se modifica aquí una condición material, debe actualizarse
también la fuente especializada enlazada.

## 1. Cómo interpretar el documento

- **VERIFICADO:** demostrado en esta unidad mediante estado, archivos, hashes,
  logs, topics, servicios o una prueba controlada.
- **OBSERVADO:** visto durante una prueba, pero sin causa interna totalmente
  demostrada.
- **INFERENCIA:** explicación compatible con la evidencia que requiere otra
  prueba o confirmación del proveedor.
- **PENDIENTE:** no probado, no resuelto o no contestado por DSA/UBTECH.
- **DESCARTADO:** hipótesis o workaround contradicho por la evidencia.

Una observación histórica no autoriza movimiento. Al retomar, comprobar de
nuevo el estado físico y lógico.

## 2. Relevo vigente

### 2.1 Último estado conocido

| Elemento | Último estado documentado | Confianza |
|---|---|---|
| Postura | tras el canary rechazado se ejecutó el recovery E6.0 READY→HOME una sola vez: `SUCCEED/status=4`; los 20 ejes quedaron a ≤`0,002780 rad` de HOME, brazos ≤`0,000959 rad`, velocidad cero y delta posición–consigna ≤`0,002780 rad`. El operador confirmó HOME visual estable, brazos/cabeza sin contacto, clamps vacíos y ningún movimiento inesperado | **HOME MEDIDO Y VISUALMENTE CONFIRMADO; ESTADO VOLÁTIL** |
| Modo robot | el reinicio completo supervisado rearmó Motion: `ACTUATORS_OPERATION_ENABLED=1`, action server presente y `ACTIONS=ready`; el task READY S2 permanece cargado con hash `c767f739…a9b2` | **OPERATIVO; REVALIDAR INMEDIATAMENTE ANTES DE OTRO GOAL** |
| Efector | abrazaderas, `HW_TYPE=cruzr_s2_v1` confirmado por el check fresco | **VERIFICADO POR SOFTWARE; VACÍO DEBE RECONFIRMARSE ANTES DE MOVIMIENTO** |
| Actuadores | muestra fresca posterior a READY→HOME: 20 ejes presentes, 14 de brazos, velocidad máxima `0`, sin fault y delta posición–consigna ≤`0,002780 rad` | **VERIFICADO; ESTADO VOLÁTIL** |
| Teleoperación PC | combinación oficial robot v0.2.0 + controller 4.7.0 + UI 4.1.0, overlay `clamp,0,0` y control bimanual. La sesión 10:25 terminó por protección FT, no por VR. Tras el reinicio el robot quedó en `AutoTaskMode`; no se ha recargado ni reanudado PICO | **BLOQUEADA HASTA NUEVO PREFLIGHT Y CAMBIO DE MODO AUTORIZADO** |
| Servicio PC/PICO | el STOP oficial tras `Ctrl+C` quedó confirmado; PC permaneció encendido durante el power cycle del robot | **STOP VERIFICADO; SIN CLIENTE FÍSICO** |
| VLA | contenedores persistentes detenidos, `restart=no`, cero publicadores. E6.0Z demostró que E6.0Y combinó task 0 con escena `NO_BOX` y una entrada 20D a `0,834773183 rad` del frame task 0 más cercano. `--ready` y `--one-point` quedaron retirados y su código activo eliminado; sólo STOP/recovery histórico permanecen | **E6.0 NO_BOX RETIRADO; SIGUIENTE: ENTRADA TASK-MATCHED + 5 SHADOW, SIN MOVIMIENTO AUTORIZADO** |
| Cargador | el último preflight móvil dio `CHARGER=0`; después el operador conectó físicamente el cargador durante E6.0Z | **CONECTADO POR CONFIRMACIÓN DEL OPERADOR; TODO MOVIMIENTO BLOQUEADO HASTA DESCONECTAR Y REVALIDAR** |
| Paros, ruedas y zona | antes del recovery el operador confirmó READY estable, sin contactos, clamps vacíos, zona 1,5 m, dos personas y mano en E-stop; software leyó `ESTOP_KEY=0`, `SERVO_ESTOP_KEY=0`. Después confirmó HOME visual estable y sin movimiento inesperado | **RECOVERY CERRADO; RECONFIRMAR TODO ANTES DE OTRO MOVIMIENTO** |
| Mapa/localización | `test_route_01` se conservó; activación y localización son volátiles | **RECOMPROBAR** |

La rama `main` estaba limpia y sincronizada con `origin/main` en el commit
`4536f8a` antes de crear esta fuente global. El estado Git actual prevalece
sobre esa referencia.

El 28-08 se endureció localmente return-to-home. El script no mueve ya sin
`--run`, mide los 20 ejes,
trata todo inicio de home como no confirmado hasta observar las posiciones,
bloquea PICO/unknown/fuerza/autocolisión/fault y restringe la tarea vendor a
estados del ciclo de caja. `--force-held-home` quedó retirado y `--fast` ya no
omite gates. El 03-09 se corrigió el mapping para aceptar los IDs reales
v0.2.0 `11004…11001`; las regresiones de ambos mappings pasaron y un `--check`
vivo demostró `home` sin ordenar movimiento. La recuperación general desde
una postura arbitraria no-home sigue sin validación física; la ruta específica
VLA READY→HOME sí quedó validada por E6.0Q.

### 2.2 Primeros pasos de la siguiente sesión

Sin mover el robot:

```bash
git status --short --branch

# Elegir sólo los diagnósticos relacionados con la tarea.
./scripts/cruzr_blue_workbin_cycle.sh --check
./scripts/cruzr_blue_workbin_table_transfer.sh --check --fast
./scripts/teleoperation/cruzr_pico_teleop_pc.sh --check
./scripts/vla/run_ubtech_vla_shadow.sh --status
```

El diagnóstico de teleoperación exige que estén presentes los enlaces que
pretende comprobar; no debe interpretarse un fallo por PICO desconectado como
un defecto nuevo del robot. Consulte siempre `--help` antes de usar modos de
movimiento o recuperación.

## 3. Inventario técnico consolidado

### 3.1 Robot y red

| Componente | Valor conocido | Estado |
|---|---|---|
| Modelo | Cruzr S2 | **VERIFICADO** |
| Número de serie | `WAE001UBT60000669` | **VERIFICADO** |
| Software | genérico `v0.2.0` en Motion y Vision | **VERIFICADO** |
| Motion | Ubuntu 22.04, `192.168.11.2` | **VERIFICADO** |
| Vision/web | `192.168.11.3` | **VERIFICADO** |
| PC Ethernet | `eno1`, perfil `cruzr-s2`, `192.168.11.250/24`, autonegociación, 1000 Mb/s full, never-default; Motion/Vision directos | **VERIFICADO; PREFERIDO PC→ROBOT** |
| PC Wi-Fi Internet | `wlo1`, `DSA CORPORATE`, `192.168.40.120/24` | **VERIFICADO; CONSERVAR** |
| PC Wi-Fi robot/PICO y fallback | `wlx80afcad40bd6`, `Cruzr S2-0669`, `192.168.42.215/24`; `.42.0/24` directa y fallback `.11.0/24` vía `.42.2`, never-default, sin DNS y `powersave=disable` | **VERIFICADO; VIGILAR RESET USB REALTEK** |
| PICO Wi-Fi local | `Cruzr S2-0669`, `.211` el 25-08 y `.212` el 26-08 | **VERIFICADO; DHCP, REDESCUBRIR** |
| Efector actual | abrazaderas | **VERIFICADO** |
| `HW_TYPE` | `cruzr_s2_v1` | **VERIFICADO** |
| `TELE_DEVICE` | `pico` | **VERIFICADO** |
| `transmit` | `local` | **VERIFICADO** |
| `MC_SCENE` | vacío en contenedores inspeccionados | **VERIFICADO; DIFERENCIA CON SOP** |

Las credenciales del robot no se versionan. Las rutas Wi-Fi pueden diferir de
las rutas Ethernet; deben descubrirse en cada sesión.

### 3.2 Efectores

- Las abrazaderas son el efector operativo actual. La configuración coherente
  es `HW_TYPE=cruzr_s2_v1`.
- Las manos v4 se instalaron físicamente, se detectaron mediante
  `/mc/left_hand/joint_states` y `/mc/right_hand/joint_states`, y se probaron
  tareas de fábrica. Después se retiraron y se restauraron las abrazaderas.
- Con manos v4 se observó `HW_TYPE=cruzr_s2_v1_sps`. No reutilizar ese valor
  con abrazaderas.
- Las demostraciones de manos son trayectorias fijas, no manipulación autónoma.
  La coreografía de corazón requirió iteración y llegó a dejar un dedo en
  contacto con el torso; no debe ejecutarse desde una postura desconocida.

Guía: [`../scripts/hands/README.md`](../scripts/hands/README.md).

### 3.3 Mapa, estaciones y referencias

- Mapa: `test_route_01`.
- Waypoints conocidos: `START`, `PASO1`, `PASO2`, `PASO 3`, `PASO4`,
  `FINISH`, `MESA2_PRE`.
- La misión mesa 1 → mesa 2 no necesita pasar por `PASO1`; el destino global
  es `MESA2_PRE`, seguido de alineación local.
- AprilTag mesa 1: ID 112, familia `tag36h11`, lado negro medido 75 mm,
  `tag_size=0.075`; uso opcional.
- AprilTag mesa 2: ID 113, familia `tag36h11`, lado negro medido 73,5 mm,
  `tag_size=0.0735`; referencia del depósito.
- El tag 113 se detectó con márgenes de decisión altos y medidas estables. Hay
  referencias separadas para robot vacío y con caja sujeta porque la postura
  de transporte cambia la transformación cámara-tag.
- Activar el mapa no equivale a estar bien localizado. Después de un arranque,
  actualización o movimiento manual hay que validar la pose contra el entorno
  LiDAR antes de navegar.

Guía y valores completos:
[`guides/TRANSFERENCIA_CAJA_ENTRE_MESAS_CON_APRILTAG.md`](guides/TRANSFERENCIA_CAJA_ENTRE_MESAS_CON_APRILTAG.md).

### 3.4 Caja de ensayo y carga

- Contenedor azul de plástico, aproximadamente `600 × 400 × 220–230 mm`.
- Las pruebas descritas se hicieron con la caja vacía o ligera.
- DSA/UBTECH indicó por chat una carga útil máxima bimanual de 20 kg y un rango
  recomendado de 10–15 kg. Es una afirmación del proveedor, no una curva de
  payload validada para cualquier alcance, centro de gravedad o aceleración.
- No extrapolar las pruebas de caja vacía a carga industrial sin commissioning
  mecánico y límites documentados.

## 4. Cambios persistentes realizados en el robot

### 4.1 Actualización v0.2.0

**VERIFICADO:** se aplicó el paquete offline genérico v0.2.0 en Motion y
Vision. Antes se respaldaron configuraciones y mapas. El flujo estándar
`udoke replace` no recibió `upload-confirm` en tres intentos, por lo que se
aplicó el fallback manual incluido en el SOP: preinstalación, sustitución de
configuración, despliegue uDoke y postinstalación.

Se preservaron:

- mapa `test_route_01` y su checksum;
- configuración de abrazaderas `HW_TYPE=cruzr_s2_v1`;
- acceso web, navegación, manipulación y visión.

Detalles y reporte al proveedor: [`../upgrade.txt`](../upgrade.txt) y
[`../upgrade_summary.txt`](../upgrade_summary.txt).

### 4.2 Servicios estabilizados tras la actualización

- `main.x86` y `main.orin`: plantillas sin comando que reiniciaban en bucle;
  se dejó su reinicio automático deshabilitado.
- Cliente MQTT cloud: se bloqueaba con `segmentation fault` en el callback de
  batería; se dejó detenido y sin reinicio automático. El MQTT local/upilot
  permaneció estable.
- Netdata Vision: contenedor activo pero health check local de `19999` no
  saludable; pendiente de corrección oficial.
- Frecuencia GPU Vision: el script oficial informó 1,224 GHz frente a objetivo
  1,122 GHz; pendiente de confirmación del proveedor.

Estos cambios son workarounds locales y deben revisarse después de cualquier
actualización oficial.

### 4.3 Guard de arranque v0.2.0

**VERIFICADO:** Vision arrancaba Control Center antes de que Motion ofreciera
servicios x86 funcionales. El self-check fallaba, la cara quedaba roja y la
cabeza baja. Se instaló en Vision un guard reversible que:

- espera versión exacta v0.2.0 y servicios Motion funcionales;
- exige respuestas reales de self-check y muestras de las seis cámaras;
- sólo recupera el patrón `Fault` conocido con paros/cargador seguros;
- reconoce `WaitEStopRelease` como espera física segura y sale sin reiniciar ni
  mover;
- reinicia Control Center una vez, exige `StartMotion` y `JoystickMode`;
- devuelve la cabeza a la tarea oficial de home.

Archivos instalados en Vision:

```text
/usr/local/sbin/cruzr-v020-boot-guard
/etc/systemd/system/cruzr-v020-boot-guard.service
/usr/local/share/doc/cruzr-v020-boot-guard.md
```

Guía, comprobación y rollback:
[`guides/CRUZR_V020_BOOT_GUARD.md`](guides/CRUZR_V020_BOOT_GUARD.md).

### 4.4 VLA suministrado

**VERIFICADO:** se instalaron las imágenes, workspaces y
`checkpoint-40000` suministrados. Los dos contenedores se mantienen detenidos
con `restart=no`.

Se añadió un overlay local para:

- usar el perfil S2 correcto de 20 ejes;
- leer `/mc/whole_joint_states` como fuente read-only, porque
  `/mc/sdk/robot_state` no entregaba muestras;
- montar la variante GR00T suministrada y los metadatos de inferencia;
- validar chunks sin importar ni publicar `RobotCommand`.

La inferencia shadow produjo chunks finitos de forma esperada y confirmó cero
publicadores en `/mc/sdk/robot_command`. Desde `home`, los chunks se rechazaron
por diferencias de hasta aproximadamente 1,35 rad en ocho articulaciones. No
se habilitó movimiento VLA.

El 2026-08-28 se ejecutó task 0 otra vez desde una postura/escena viva no
documentada, por lo que el run se clasifica `OOD_RUNTIME_SMOKE`, no prueba
nominal. Generó dos chunks y el validador rechazó ambos por siete saltos del
primer punto; el máximo fue `R_shoulder_yaw_joint=1,339886 rad` frente a
`0,35 rad`. El goal solicitado por 8 s concluyó en `10,063076 s`, al terminar
el ciclo de inferencia en curso. STOP dejó ambos contenedores `exited` y cero
publicadores. Los logs se recuperaron de los contenedores detenidos en
`Humanoide-vla-evidence/20260828T080202_E2.0_recovered/`. Estado:
`PASS_SHADOW_SAFETY_ONLY`; E1.0/E1.3 y la validación de task siguen pendientes.

El 2026-08-28 se implementó y ejecutó E2.2 para PLACE sin utilizar el robot.
`run_vla_offline_place_e2_2.sh` creó un contenedor NVIDIA transitorio en Vision
con red desactivada, sin ROS ni `RobotCommand`, y cargó el checkpoint una sola
vez. El run válido `20260828T112730_E2.2` reprodujo task 1/episodio 465 y task
3/episodio 265 desde frame 0: salidas 10×20 finitas, MAE `0,007283609` y
`0,011394879`, sin violaciones de rango ni de primer salto. El split es el
último 15 % estratificado definido por el proyecto; el dataset sólo declara
`train`, por lo que no prueba generalización ni exclusión del entrenamiento.
`meta/info.json` anuncia `frame_index`, pero los parquets inspeccionados lo
omiten; se usó índice de fila únicamente tras validar task, episodio y la línea
temporal exacta a 120 Hz. Los dos intentos previos fallaron antes de inferencia
y quedaron documentados. La limpieza de JSON root-owned se corrigió y el
residuo temporal se retiró. Hashes de evidencia válidos; estado final
`exited/exited/publishers:0`, sin leer estado ni ordenar movimiento físico.

E3.0 amplió esa ruta a tasks 0–3, cinco episodios/fases por task y cinco
ejecuciones totales del seed 0: run `20260828T114346_E3.0`, 20 muestras y 36
inferencias. Las MAE medias fueron task 0 `0,004908891`, task 1 `0,006516288`,
task 2 `0,009686776` y task 3 `0,008983554`; las repeticiones seed 0 fueron
idénticas (`max_abs_diff=0`). Dos de 20 baselines excedieron el rango del
perfil: task 2/episodio 270/frame 0 predijo `lifter_pitch_1_joint=0,051654458`
en el primer punto, y task 3/episodio 287/frame 0 llegó a `0,060465574` y
excedió el máximo `0,000336618` en 7/10 puntos. No hubo violaciones del salto
inicial. El split local fue 424/76 episodios con solapamiento cero, pero el
proveedor sólo declara `train` y no se conoce la membresía del entrenamiento
de C0; no se permite afirmar generalización. Los hashes completos del
checkpoint coincidieron antes/después. Resultado
`PASS_OFFLINE_CAMPAIGN_WITH_CONSERVATIVE_VIOLATIONS`; sólo libera E3.1 offline,
no publicación física. Cierre `exited/exited/publishers:0`, sin estado ni
movimiento del robot.

E3.1 se ejecutó offline sobre dos frames fijos de tasks 0/2. El dataset carece
de RGB-D, calibración, máscara/pose 6D de la caja y geometría métrica de repisa;
por tanto la parrilla solicitada en metros/yaw real queda explícitamente
`BLOCKED_MISSING_RGBD_CALIBRATION_MASK_AND_SCENE_GEOMETRY`. El run válido
`20260828T120228_E3.1` aplicó una sola transformación global de imagen por vez:
desplazamiento horizontal ±5/±10 %, zoom 0,9/1,1 y perspectiva trapezoidal
±5/±15 grados-proxy. Las 26 variantes fueron `ACCEPT_STRUCTURAL`, las tres
entradas nominales por task produjeron exactamente lo mismo y no hubo
violaciones conservadoras. Los máximos cambios del chunk para task 0 fueron
`0,027470/0,040258/0,030194 rad`; para task 2,
`0,036843/0,053590/0,014256 rad`, respectivamente. Esto es sensibilidad a
imagen, no OOD métrico, éxito de agarre ni generalización. Checkpoint intacto;
cierre `exited/exited/publishers:0`, sin leer ni mover el robot. Sólo libera
E3.2 en sink offline.

E3.2 implementó un sink Python local sin ROS, red, mensajes de mando ni API de
publisher/action. El run `20260828T121832_E3.2` aceptó dos chunks válidos
consecutivos y rechazó 32/32 fallos de identidad, esquema, finitud, frescura,
timeline, límites, secuencia, control y cliente. Cancel/STOP son idempotentes,
el deadman expira con STOP enclavado y los chunks inválidos no consumen el ID.
Los ocho perfiles `P14_A…P20_AHLW` tienen cobertura unitaria de máscara/hold no
nulo, pero la campaña completa se ejecutó sólo para `P20_AHLW/low`. La pose
low es un midpoint sintético del perfil, no `VLA_READY_LOW`. Antes/después:
`exited/exited/publishers:0`; no se leyó estado ni se mandó movimiento. Falta
un límite certificado de aceleración, por lo que VLA-5 y todo ejecutor físico
siguen bloqueados. Sólo queda liberado E3.3 offline.

E3.3 se ejecutó como simulación temporal Python local y auditoría estática del
runtime suministrado, run `20260828T124011_E3.3`. Pasaron 22/22 casos: diez
puntos exactos a 80 ms, no repetición durante huecos, timeout inter-chunk,
solapamiento/dispatch tardío fail-closed, IDs, cancel antes/durante/entre
chunks, STOP, pérdida de imagen/estado, timeout de sesión y política candidata
de cinco flags. Cancel/STOP/fault purgan la cola en el mismo evento lógico. El
módulo no importa ROS/red, no contiene API de publisher/action ni topic físico;
antes/después quedó `exited/exited/publishers:0`, sin leer estado ni mover.

La auditoría UBTECH no permite cerrar VLA-3: Vision declara `0,2 Hz`, chunks
10×20 a `0,08 s` (horizonte `0,72 s`) y termina con un único
`flag_pred > 0,1`, mientras el YAML declara `continuous_end_chunk_num=5` sin
que el Python lo consulte. Además, el ejecutor bajo `src/` interpola a 900
puntos/9 s y la copia bajo `install/` a 600 puntos/6 s. El contrato local de
cinco flags y timeout de hueco a 0,5 s es una propuesta fail-closed, no la
semántica física del proveedor. Resultado
`PASS_LOCAL_TEMPORAL_FAIL_CLOSED_VENDOR_SEMANTICS_UNRESOLVED`; sólo se libera
E4.0 de resolución de artefactos en lectura, nunca movimiento.

E4.0 se ejecutó en lectura local/remota, run final corregido
`20260901T075728_E4.0`. Motion sí
contiene `clamp_s2_joints_trajectory` (hash `7722b734…7f6`, 2×14,
`1,5 + 1,0 s`) y `clamp_s2_joints_trajectory_back` (hash
`ee39039c…389`, 2×14, `2,0 + 3,0 s`). El back termina en el primer waypoint
forward, pero no invierte la secuencia completa ni restaura cabeza, cintura y
elevador. El task esperado por el loader suministrado,
`s2_bio_vla/s2_vla_pick_large_teleop_ready`, no está instalado ni registrado.
Los candidatos presentes tienen distinta semántica y el task tampoco aparece
en el upgrade v0.2.0 suministrado. La revisión v2 corrigió hombro/codo, pero
asumió erróneamente que también debía intercambiar `wrist_pitch/wrist_roll`.
E6.0A rechazó después ese intercambio al compararlo con task 0/frame 0 del
dataset: el orden directo da error máximo `0,002112805 rad` y el intercambio
`0,614627484 rad`. El URDF sólo contiene `waist_yaw_joint`, el ejecutor
genérico usa `[pitch,yaw]` y el S2 conserva el índice 19, de modo que el
segundo cero resuelve `waist_yaw=0`. Los lifter quedan heredados; el ejecutor
los descarta y 500 episodios muestran múltiples configuraciones, no un ready
único. Faltan límites runtime, swept volume y recuperación completa. Resultado
`PARTIAL_RESOLUTION_BLOCKED_NOT_READY_FOR_E4_1_OR_PHYSICAL_USE`; sólo queda
autorizado E4.2 offline, no E4.1 ni movimiento. Antes/después:
`exited/exited/publishers:0`, sin leer estado ni ordenar movimiento.

E4.2 se ejecutó sin red al robot en `20260901T081210_E4.2`. El analizador
versionado cruzó los 500 episodios, perfiles no-S2 55/70/85/100/115 y FK del
URDF S2. Rechazó una altura única: tasks 0/1 tienen coincidencias 55/70/85 y
tasks 2/3 100/115 a `0,05 rad`, pero 84/95/49/58 episodios no coinciden con
ningún perfil nombrado. Los pares task 0/2 episodios 450/206 y task 1/3
443/171 comparten configuración de elevador a sólo
`0,000124356/0,000206182 rad`, de modo que lifter/FK no determina nivel ni
`platform_in_base`. Tasks 2/3 episodios 90/91 correlacionan con el perfil 100
y la plataforma SDK de 1 m, pero el XML es no-S2 y falta calibración métrica.
Estado `PARTIAL_HEIGHT_FAMILIES_RESOLVED_SINGLE_HEIGHT_MAPPING_REJECTED`; diez
frames representativos y todos los hashes validan. Inferencia, publicadores,
estado y movimiento del robot fueron cero. Sólo se permite aclaración de
semántica o calibración métrica offline; E4.0 y lo físico siguen bloqueados.

E4.1 métrico se ejecutó después, por autorización del propietario, en
`20260901T084855_E4.1`. El VLA permaneció `exited/exited/publishers:0`; no hubo
movimiento. CameraInfo vivo confirmó `960×576`, frame rectificado y
`fx=fy=383,1236026`; 20 posiciones del tag 113 validaron escala/TF. La rama
angular planar (`5,484°`) se declaró ambigua y se excluyó de la solución. Dos
rayos del borde posterior de B0, píxeles `(307,293)…(713,293)`, reconstruyeron
`0,603128627 m`, residual `+0,128627 mm`. Con origen en el centro del borde
frontal de la mesa, +X ancho/+Y fondo/+Z arriba, la candidata es
`platform_in_base=(0,261844987,-0,027738106,0,870000000,0,0,-1,545870035)`.
`D_BUMPER_PLATFORM=-0,092859226 m` revela solape de proyecciones; la
incertidumbre es ±16,84/13,30/10,00 mm y ±0,868°. Estado
`METRIC_FIXTURE_CANDIDATE_RESOLVED_PHYSICAL_GATES_OPEN`: E4.0, swept volume,
colisiones y recovery aún impiden colocar la mesa allí o mover el robot.

La continuación E4.1C se repitió completamente local en
`20260903T093408_E4.1C` después de corregir el orden de muñecas demostrado por
E6.0A. Sobre 121 muestras de
`preposition→forward_1→forward_2→back_1→back_2`, el URDF vendor y sus 46
geometrías de colisión produjeron 60 candidatos AABB contra el tablero E4.1;
32 cruces fueron confirmados a nivel de triángulos en doce links de
muñeca/sensor/efector. B0 tuvo cero candidatos y no se colocó. Resultado
`SOLID_TABLETOP_CANDIDATE_REJECTED_BY_VENDOR_URDF_SWEEP`: la mesa sólida no
debe acercarse a esa pose. El run anterior `20260901T090235_E4.1C` queda
`DESCARTADO` porque usó el mapping de muñecas incorrecto.

E4.1D se repitió después en `20260903T093440_E4.1D`. El SDK identifica los
meshes como pinza Dahuan
PGC-140-50 y exige `HW_TYPE=cruzr_s2_v1_gripper`; no son el mecanismo
instalado `cruzr_s2_v1`, compuesto por abrazaderas laterales pasivas. Sin CAD
o cotas de las abrazaderas, la equivalencia de envolventes queda
`NOT_DEMONSTRATED`. Sin embargo, la partición de los 32 cruces deja 10 en
`pgc/finger` y **22 en muñecas/sensores de fuerza**. Por ello el rechazo del
tablero sólido se mantiene aun excluyendo todo el modelo PGC. Sólo queda
autorizado diseñar offline otra pose o una plataforma rígida con huecos; la
entrada a preposición y el recovery completo continúan sin resolver. E4.1C y
E4.1D no conectaron con el robot ni iniciaron inferencia, publicadores o
movimiento, y B0 no se colocó. El intento `20260903T093412_E4.1D` quedó
incompleto y `DESCARTADO`: el wrapper aún exigía los conteos obsoletos; ahora
valida dinámicamente la partición y su suma.

E4.1E continuó ese camino offline en `20260903T093443_E4.1E`. Sobre 401
estados y tres planos verticales (`-10/0/+10 mm`) calculó un margen XY total de
55 mm para muñecas/sensores. Manteniendo B0 y su apoyo fijos, la búsqueda
alineada de mesa sólida en ±5° produjo 128.386 colocaciones con apoyo válido y
cero libres de colisión. La única referencia sólida global refinada exige
`+76,5°` y desplazar el origen `0,856 m`, fuera de la escena calibrada. Se
derivaron dos muescas frontales candidatas: izquierda
`x=-0,720…-0,470, y=0…0,200 m`; derecha
`x=0,400…0,650, y=0…0,170 m`. No solapan el apoyo B0+50 mm, pero no incluyen
la envolvente real de las abrazaderas, patas/espesor, entrada ni recovery. No
se autorizó acercar/modificar la mesa, colocar B0, inferencia, publicador o
movimiento. E4.1F sustituyó la medición manual por una auditoría exclusiva de
fuentes oficiales.

E4.1F se ejecutó localmente en `20260903T085912_E4.1F`. Verificó por hash el
manual SDK, manual de producto, USD/URDF, XML ready y metadatos VLA
suministrados. Las fuentes fijan B0 `0,60×0,40×0,22 m`, plataforma `1,00 m`,
carga máxima global bimanual `15 kg` y PGC-140-50
`0,1385×0,075×0,075 m`/carrera `0,05 m`. Esta última corresponde a
`cruzr_s2_v1_gripper` y queda excluida. El manual enumera la familia
`clamp hands`, pero ningún artefacto publica envolvente, TCP, masa, CoG o CAD
de las placas pasivas `cruzr_s2_v1`; USD/URDF sólo contienen PGC. No se
inventaron cotas ni se usaron mediciones/fotografías. El fixture físico sigue
bloqueado, pero el punto de reanudación pasa a E5.0 offline.

E5.0 se ejecutó localmente en `20260903T090355_E5.0`. La matriz completa de
ocho perfiles `P14_A…P20_AHLW` por fixtures sintéticos `low/middle` aprobó
16/16 celdas: 544 casos, 32 válidos aceptados, 512 inválidos rechazados y
16/16 probes de máscara. Los ejes habilitados copiaron el chunk y los
bloqueados conservaron el hold sintético del fixture. Se corrigió el fault
`axis_profile_mismatch` para que `P14_A` use realmente otro perfil. El sink y
la campaña no usan ROS, red, publicadores ni estado del robot; no hubo
movimiento. E5.0 completa VLA-5 sólo en alcance offline y libera únicamente
E5.1 shadow. No valida poses reales, aceleración ni un ejecutor físico.

E5.1 se completó como shadow-replay local en `20260903T091319_E5.1`. Dado que
los perfiles son máscaras posteriores y no inputs del checkpoint, las 20
inferencias C0 congeladas de E3.0 —4 tasks × seeds 0–4— se reutilizaron bajo
los ocho perfiles, generando 160 bundles comparables. Resultado: 148
`ACCEPT_STRUCTURAL`, 12 `REJECT_SAFE` y 160/160 contratos de máscara. Todos
los rechazos requieren `L`: task 1/seed 2 excede velocidad de
`lifter_pitch_3_joint`; task 2/seed 0 y task 3/seed 0 exceden rango de
`lifter_pitch_1_joint`. Los perfiles sin elevador aceptan 80/80. Los hashes de
E3.0 y del checkpoint antes/después se verificaron. No hubo red, ROS, estado
vivo, publicador o movimiento. Sólo se libera E5.2 offline; faltan fixture
vivo, GPU/VRAM, frecuencia, `flag_pred` y toda validación física.

E5.2 ejecutó la selección preliminar local en `20260903T091901_E5.2`. Exigió
5/5 aceptaciones y eligió el perfil de menor dimensión dentro de
`max(0,0001 rad, 1 %)` del mejor MAE por task. El resultado fue `P14_A` para
tasks 0–3. H no produjo mejora material (`-5,0×10⁻⁹…+1,20×10⁻⁶ rad` frente a
P14), W empeoró `+6,88×10⁻⁶…+1,16×10⁻⁵ rad` y L empeoró
`+7,83×10⁻⁴…+3,48×10⁻³ rad`, además de 12/80 rechazos en todos los perfiles
con elevador. La banda es un criterio de selección offline, no límite
mecánico. No hubo red, ROS, estado vivo, publicador o movimiento. E6.0 sigue
bloqueado.

El precheck reproducible `E6.0-CHECK` se ejecutó de nuevo localmente en
`20260903T123041_E6.0-CHECK`. Corrige el alcance del gate de fixture: E4.4 y
la geometría clamp/mesa **no aplican** al canary `NO_BOX_READY`, porque exige
retirar plataforma y B0; sí siguen siendo obligatorios para E7+. El precheck
cerró correctamente sin red, ROS, estado del robot, publicador ni movimiento,
y dejó tres bloqueos explícitos: recovery sin validar, transporte físico/STOP
ausente y límite de aceleración no certificado. La semántica del canary de un
punto ya quedó cerrada por contrato de proyecto E6.0L: consume únicamente el
índice 0 de un chunk, una vez, sin replay y sin usar el `end_flag` ambiguo del
proveedor. El gate geométrico del canary sin caja se acepta sólo bajo el proxy
documental conservador E6.0J ordenado por el propietario; no constituye CAD ni
certificación del clamp real. El
registro runtime y el preflight articular fresco ya están demostrados. El ready P14 ya no exige tres valores numéricos
de lifter: E6.0A demuestra que sus 14 ejes comandados coinciden con el frame 0
grabado y que H/L/W deben capturarse frescos y mantenerse bloqueados. El
frontend `run_cruzr_vla_canary.sh` sólo implementa `--check`; todos los modos
activos fallan antes de acceder al robot.

E6.0A autoritativo es `20260903T093145_E6.0A`. Derivó un recovery de brazos
exactamente inverso `B→A→preposición`, con segmentos dentro de la envolvente
de velocidad analítica, y confirmó que el `back` vendor no es esa inversa. No
lo instaló ni validó contra colisiones o hardware. El run anterior
`20260903T092935_E6.0A` queda `DESCARTADO`: heredó el intercambio de muñecas
equivocado de E4.0 y produjo un falso fuera de soporte. Se conserva como
evidencia, pero no debe usarse para decisiones.

E6.0B se ejecutó localmente en `20260903T094547_E6.0B`. Reconstruyó por FK
401 estados del recorrido exacto de brazos
`preposición→A→B→A→preposición` y aplicó SAT de OBB a 46 geometrías de
colisión vendor. No encontró violaciones de límites URDF ni solapes OBB entre
links alejados (distancia cinemática >3), incluso antes de excluir PGC/dedos.
Esto sólo cierra el broad phase upstream: 58 pares cercanos/estructurales no
pueden clasificarse sin SRDF/matriz de colisiones permitidas, y el URDF no
incluye la geometría de las abrazaderas pasivas instaladas. Tampoco certifica
holgura, flexión, fuerza o aceleración. Por tanto el gate de autocolisión y el
canary físico permanecen bloqueados. Cero red, ROS, estado vivo, publicador o
movimiento.

E6.0C continuó el narrow phase local en `20260903T095600_E6.0C`. Clasificó
los 58 pares cercanos de E6.0B en 40 uniones directas estructurales, 12 pares
estáticos fuera de P14, 2 pares PGC no instalados y 4 pares móviles upstream.
Estos cuatro —codo/muñeca y hombro/torso de cada lado— se comprobaron en los
401 estados mediante BVH de los STL: las AABB de triángulos descartaron todos
los candidatos y hubo cero intersecciones exactas; cuatro casos sintéticos
validaron además la rama SAT coplanar/3D. Es evidencia favorable para el modelo vendor, pero no
resuelve las abrazaderas reales, holgura mínima/tolerancias, revisión de la
política runtime ni validación física. El gate sigue cerrado; cero red, ROS,
estado vivo, publicador o movimiento.

E6.0D cuantificó la distancia exacta muestreada en
`20260903T101730_E6.0D`. Recorrió 401 estados (201 únicos y retorno simétrico)
con BVH best-first y distancia exacta triángulo-triángulo. Los mínimos fueron
`34,877144 mm` y `34,884472 mm` para codo/muñeca, y `16,378588 mm` y
`16,377700 mm` para hombro/torso; el mínimo global fue `16,377700 mm` en la
muestra 100. El kernel superó 4 casos dirigidos y 300 comparaciones aleatorias
contra una implementación escalar. Es sólo holgura de malla vendor en puntos
muestreados: no prueba continuidad, clamp pasivo, calibración, flexión ni
tolerancia física. También derivó un contrato offline fail-closed de un punto:
el delta efectivo es `min(delta_perfil, velocidad_perfil × 0,08 s)`, pero
aceleración, fuerza/corriente y margen físico permanecen `null`; no contiene
topic/publicador y `physical_execution_enabled=false`.

E6.0E implementó y probó ese guard en
`20260903T102652_E6.0E`: 35 casos de mensajes y 7 manipulaciones del contrato,
42/42 expectativas correctas, 2 previews válidos, cero autorizaciones físicas
y cero publicadores. Rechaza ejecución solicitada, segundo punto, identidad u
orden incorrectos, estados no-ready, datos no finitos/obsoletos/futuros,
rangos/deltas excedidos y cambios de H/L/W. El run `20260903T102636_E6.0E`
queda `DESCARTADO`: sólo falló el empaquetado autocontenido de evidencia por
copiar el módulo un nivel incorrecto; no llegó a ejecutar la campaña ni
accedió al robot.

E6.0F cerró el inventario exclusivamente local en
`20260903T102931_E6.0F`. Congeló el XML ready, la entrada exacta de
`task_list`, los destinos previstos y un rollback sin aplicarlos. Detectó que
el loader vendor es interactivo y puede usar `rm -rf`, `sed -i` y reemplazo de
`task_list`, por lo que queda prohibido ejecutarlo desatendido. Los seis
componentes offline están agotados con las fuentes actuales; lo pendiente
cruza necesariamente a robot vivo o entrada física/certificada. El primer
escenario será `NO_BOX_READY_EMPTY_CELL`: sin caja, mesa/plataforma ni
AprilTag, radio libre mínimo 1,5 m, clamps vacíos, ruedas bloqueadas, cargador
fuera, dos personas y un solo cliente. E6.0F no autoriza ese movimiento.

E6.0G ejecutó el primer preflight vivo de sólo lectura en
`20260903T104309_E6.0G`. Confirmó `HW_TYPE=cruzr_s2_v1`, E-stop principal
accionado (`1`) y servo E-stop liberado (`0`), cargador fuera, baterías
79,8/82,1 %, ambos contenedores VLA detenidos y cero publicadores. El task/XML
ready estaban ausentes. Con el paro activo no había servidor de acción ni
`/mc/whole_joint_states`; `/mc/actuator_state` se anunciaba pero no entregó
muestra, por lo que la inmovilidad no quedó instrumentada. No hubo instalación,
recarga, reinicio ni movimiento.

Tras liberar físicamente el E-stop principal sin movimiento inesperado, E6.0G
se repitió inicialmente en `20260903T105539_E6.0G`: ambos paros `0`, cargador
`0`, ready presente sólo en disco y VLA detenido/cero publicadores, pero
Control Center permaneció en `WaitStartMotion` sin servidor de acción ni
muestra articular. Una pulsación exterior se registró sólo como `Power click`.
Se aplicó entonces el ciclo completo prescrito por la sección 5.3.3: shutdown
lógico aceptado, apagado físico confirmado y arranque supervisado con E-stop.
Control Center pasó por `WaitEStopRelease`; al liberarlo completó self-check,
`StartMotion` y `JoystickMode`, sin movimiento inesperado.

El run E6.0G vigente `20260903T113216_E6.0G` usa ahora `rosa action info` —el
CLI `ros2 action info` había dado un falso cero bajo ROSA/DDS— y demostró un
servidor de manipulación, proceso Motion posterior al `task_list`, ready
cargado en runtime, preflight canónico aprobado, articulaciones inmóviles,
paros `0/0`, cargador fuera y VLA `exited/exited` con cero publicadores. No
envió movimiento y no autoriza el canary.

E6.0H instaló únicamente en disco el XML vendor y una entrada exacta en
`task_list.yaml` en `20260903T104552_E6.0H`, con el E-stop principal activo.
Verificó el hash XML `f4025124…d8323`, creó el backup fresco
`/home/walker/cruzr-vla/backups/20260903T104552_E6.0H`, cambió el hash del
task list de `c03ea6a…21a44` a `e4ac5e43…4def7` y volvió a comprobar VLA
detenido/cero publicadores. No recargó ni reinició el task manager; el registro
runtime y todo movimiento continúan bloqueados. El diagnóstico shadow se
corrigió para tratar un topic de mando inexistente como cero publicadores, sin
ocultar otros errores de transporte. El wrapper E6.0H quedó idempotente:
`--check` reconoce el hash postinstalación y no vuelve a escribir. El proceso
`robot_app` es anterior al cambio del task list; ni sus strings ni sus logs
demostraron recarga dinámica, y los logs repiten `ListControllers: service not
available` bajo el paro. Se exige una recarga supervisada separada.

E6.0I cerró el segmento geométrico omitido después del reinicio, sin ordenar
movimiento. El primer run `20260903T114811_E6.0I` detectó conservadoramente un
nuevo solape OBB `R_shoulder_yaw_link↔torso_link` y terminó fail-safe; queda
reemplazado por `20260903T115129_E6.0I`, que sometió también ese par a BVH,
SAT de triángulos y distancia exacta. Usó un snapshot fresco de 20 ejes en
home, 101 estados `home↔preposición` y la evidencia anterior para cubrir 601
estados compuestos. No hubo violaciones URDF, pares cercanos nuevos ni
intersecciones exactas; el mínimo vendor muestreado fue `0,011169662 m` en
hombro derecho/torso desde home. El resultado no incorpora las abrazaderas
pasivas, tolerancias, continuidad ni dinámica, y no autoriza movimiento.

E6.0J `20260903T120626_E6.0J` aplicó la decisión del propietario de continuar
sin medición manual usando especificaciones y artefactos oficiales. Sustituyó
cada clamp por la unión completa `pgc_base+finger1+finger2` del URDF vendor,
dilatada 25 mm en cada cara a partir de la carrera documentada de 50 mm. La
envolvente resultante por extremo es aproximadamente
`0,145×0,142×0,330 m`. Tras declarar únicamente la cadena de montaje propia
`sixforce/wrist_roll/wrist_pitch` como contacto permitido, auditó 1.201
estados `home→staging→A→B→A→staging→home`, con paso máximo
`0,0092978 rad`, cero pares OBB externos y cero intersecciones exactas. Es una
**suposición de ingeniería aceptada para el canary sin caja**, no demuestra la
geometría, masa, CoG, fuerza o flexión de las abrazaderas instaladas y no
autoriza movimiento por sí sola. Los runs `120340` y `120453` son intentos
fail-safe de implementación/formato y contacto proximal antes de fijar esta
política.

E6.0K `20260903T121338_E6.0K` registró las cuatro fotografías con cinta del
clamp instalado como observación manual aproximada: `120×52×105 mm` en ejes
montaje-transversal/espesor/distal y un espesor local de 33 mm. Se añadió
10 mm por cada cara, obteniendo `140×72×125 mm`. El analizador demostró por
inclusión que este paralelepípedo cabe en el proxy E6.0J para ambos lados bajo
la hipótesis de hardware igual o reflejado. Por ello el barrido de 1.201
estados del proxy mayor domina la envolvente observada; no hubo acceso al
robot, ROS, publicador ni movimiento. Las fotos no están versionadas y la
lectura conserva incertidumbre de perspectiva; no se convierte en CAD ni en
certificación de carga/fuerza.

E6.0L `20260903T122501_E6.0L` añadió el núcleo local del canary de un punto y
pasó 30 casos de estado/fallo más 6 manipulaciones del contrato. Sólo acepta
el punto fuente 0 de un único chunk ya validado por E6.0E, crea como máximo un
intent en memoria, queda enclavado en `COMPLETED` y no repite. Cancel, STOP y
fault purgan el preview antes de cualquier intent posterior. El módulo no
contiene ROS, red, action, topic ni publicador; por diseño tampoco contiene el
transporte físico o STOP físico. Resuelve la semántica temporal propia de
E6.0, no el gate del adaptador físico.

E6.0M `20260903T122502_E6.0M` empaquetó y auditó localmente la secuencia
determinista `home→staging→A→B→A→staging→home`. El tramo nombrado de retorno
usa los goals `B→A→staging` con duraciones invertidas `1,0/1,5 s`, y el tramo
final lleva brazos, cabeza y cintura a cero numérico. El frontend
`cruzr_vla_ready_pose.sh` permite sólo `--check`/`--dry-plan`; instalación,
ready, recovery y STOP fallan antes de acceder al robot. El bundle no está
instalado ni validado físicamente y no autoriza movimiento.

Al preparar la validación física de E6.0, la primera confirmación textual de
E-stop no coincidió con dos lecturas `ESTOPS=0,0`; ese intento se detuvo sin
instalar ni mover. El operador volvió a enclavar el E-stop principal y declaró
también el paro del chasis. El run fresco E6.0G
`20260903T123632_E6.0G` confirmó `ESTOP_KEY=1`, cargador fuera, VLA
`exited/exited`, `publishers:0` y ausencia esperada de estado articular/action
server con el paro activo. `SERVO_ESTOP_KEY=0` no permite afirmar por software
que el paro del chasis esté activo.

E6.0N `20260903T123940_E6.0N` instaló bajo ese E-stop los archivos previstos
para la recuperación exacta y una entrada única en `task_list.yaml`. Respaldó el
estado anterior en
`/home/walker/cruzr-vla/backups/20260903T123940_E6.0N`; el hash del task list
cambió de `e4ac5e43…4def7` a `0d24122c…64957`, XML
`45359d49…cd3c` y MetaMove `bd5f588a…e3b0`. E6.0Q demostró después que ese
check validaba una ruta incorrecta para el MetaMove: se había instalado bajo
`manipulation_task_manager/config/meta_move`, mientras el binario lo busca en
`manipulation_meta_tasks/config/meta_move`. El check posterior de E6.0N había
confirmado `installed-on-disk-not-reloaded` y las nueve evidencias pasaron
`evidence.sha256`. No se recargó/reinició Motion, no se inició VLA y no se
publicó movimiento. En ese punto la tarea todavía no existía en el runtime;
su carga se resolvió en E6.0O y la validación física supervisada sigue
pendiente.

E6.0O `20260903T124843_E6.0O` recargó exclusivamente el contenedor dedicado
`walker-motion.manipulation_robot_app-1` bajo la autorización física del
operador. El proceso pasó de `10:35:33Z` a `10:48:31Z`, posterior al mtime del
task list; persistieron el hash `0d24122c…64957`, una sola entrada y los hashes
exactos de XML/MetaMove. El E-stop principal se verificó antes y después,
`SERVO_ESTOP_KEY` siguió en `0`, el cargador permaneció fuera, VLA detenido y
`publishers:0`. No se invocó tarea ni se publicó movimiento. El arranque sólo
espera `ListControllers`, coherente con los controladores no disponibles bajo
E-stop; no registró fatal, crash o error YAML. Se corrigió después un defecto
de quoting que hacía que el recolector incluyera líneas anteriores en el log;
la lectura corregida confirmó el arranque limpio sin repetir la recarga.

Después, el operador liberó el E-stop principal y confirmó estabilidad. La
lectura aislada mostró `ESTOP_KEY=0`, `SERVO_ESTOP_KEY=0`, cargador `0` y
baterías 64,6/67,1 %, pero no `/mc/whole_joint_states` ni action server
(`count=0`). La inspección del log de Control Center descartó la inferencia
inicial de que el paro del chasis explicaba el bloqueo: no hay un evento
`onServoEstopState=1`; el E-stop principal había provocado
`JoystickMode/Ready→WaitStartMotion`, y su liberación sólo produjo
`onEstopState=0`, sin `ButtonStartMotion`. Por tanto, telemetría y log son
consistentes con ambos paros liberados y rearme pendiente. El preflight terminó
antes de cualquier goal. El auditor se corrigió para imprimir el bloqueo en
vez de salir silenciosamente. Las fotos posteriores confirman la revisión de
hardware ya documentada: blanco=`KEY1`, aro verde=Power/Start exterior,
metálico=alimentación del chasis y ningún START Motion independiente
identificable. Una pulsación verde ya produjo sólo `Power click`; no debe
repetirse. Desde `WaitStartMotion`, el único recovery comprobado es el ciclo
completo supervisado de la sección 5.3.3.

El ciclo completo posterior se completó y E6.0G
`20260903T132151_E6.0G` volvió a demostrar ambos paros `0/0`, actuadores
habilitados, un servidor de manipulación, acciones listas, cargador fuera,
task ready/recovery cargados, VLA `exited/exited` y cero publicadores. Desde
home medido se invocó por primera vez únicamente
`s2_bio_vla/s2_vla_pick_large_teleop_ready`. La acción fue aceptada, pero
terminó `MoveToGoalFailed/status=6`. El log demuestra la causa: el primer
`MetaMove` de cintura terminó `FAILURE` antes de emitir `MoveTo`; el XML vendor
entrega `joint_angles="-0.0; 0.0"`, mientras esta unidad expone una cintura
S2 de un eje. El `Parallel threshold=4` abortó después cabeza y ambos brazos,
dejando un avance parcial quieto de cuerpo `0,195870 rad` y brazos
`0,080246 rad`. No hubo fuerza excesiva, colisión ni fault. Con confirmación
física fresca se ejecutó una sola vuelta vendor `cruzr/home`, que devolvió
`SUCCEED/status=4`; la medida posterior confirmó `MEASURED_HOME=1` con cuerpo
`0,002589 rad`, brazos `0,000671 rad` y velocidad cero.

E6.0P `20260903T133300_E6.0P` creó una copia versionada del ready que cambia
exclusivamente la cintura a `joint_angles="0.0"`, validó por parseo/diff que
no cambia ningún otro atributo de acción y sustituyó atómicamente sólo el XML
vivo. Hash vendor `f4025124…d8323` → overlay S2
`c767f739…a9b2`; backup
`/home/walker/cruzr-vla/backups/20260903T133300_E6.0P`. No hubo reload,
inferencia, publicador ni movimiento durante el cambio, y home se mantuvo
medido. El auditor vivo distingue ahora explícitamente
`vendor-incompatible-waist-2d` de `s2-waist-1d-overlay`.

E6.0Q `20260903T135236_E6.0Q` cerró la validación física determinista sin
caja. El READY corregido terminó `SUCCEED/status=4` y quedó medido contra las
consignas nativas con error máximo `0,001842048 rad`, velocidad cero y sin
faults. El primer recovery no movió: el loader no encontró el MetaMove en su
ruta runtime y abortó fatalmente en `GetRequestFromYamlNode`, lo que reinició
una vez el contenedor (`OOMKilled=false`) y dejó las articulaciones exactamente
en READY. Se corrigieron dos defectos del bundle local: el YAML se instala
ahora en `manipulation_meta_tasks/config/meta_move` y la acción final de
cintura contiene un único valor. El XML nuevo es
`9e47b6ee37f83f75036c203b809e9a93284d459316764615496a872ca3b4fbcc`;
el backup remoto es
`/home/walker/cruzr-vla/backups/20260903T134947_E6.0Q`. Sin reload ni
movimiento durante el arreglo, el segundo recovery obtuvo el goal
`c183c3e0-240a-4bfe-8904-535f0b2b50eb`, `SUCCEED/status=4`. La muestra final
dio `MEASURED_HOME=1`, cuerpo `0,002589 rad`, brazos `0,000959 rad` y velocidad
cero. VLA quedó `exited/exited` con `publishers:0`. Esto cierra el gate de
ready/recovery, pero no autoriza el checkpoint: siguen pendientes el adaptador
de transporte/STOP físico y un límite de aceleración aprobado.

El E6.0-CHECK regenerado `20260903T140006_E6.0-CHECK` consume E6.0Q y reduce
el inventario vigente de bloqueos de tres a dos:
`physical_executor_implemented_and_reviewed` y
`certified_acceleration_limit`. Continúa con `E6.0_PHYSICAL_AUTHORIZED=0`.

El trabajo de cierre E6.0R/S/T avanzó esos dos gates sin mover el robot.
E6.0R `20260903T142823_E6.0R` implementó y probó offline el adaptador P14 de
un punto para `/mc/sdk/robot_command`: 43 casos funcionales y 8 tamper pasaron,
incluyendo STOP idempotente, purga, no replay y fallo de backend cerrado. El
backend ROS existe sólo como componente inyectable, sin `main`, autoarranque ni
launcher activo. E6.0T autoritativo `20260903T143529_E6.0T` verificó en vivo y
sólo lectura que el transporte correcto es `mc_task_msgs/msg/RobotCommand` en
`/mc/sdk/robot_command`, con dos suscriptores, y que
`/mc/sdk/robot_state` tiene dos publicadores; los topics alternativos directos
de brazos no existen. Ambos contenedores VLA estaban `exited` y había cero
publicadores de comando. Los runs T `142955`, `143123` y `143255` se descartan
por auditorías incompletas/corregidas y no accedieron a movimiento.

E6.0S `20260903T144344_E6.0S` validó localmente una envolvente de ingeniería
reemplazable para el canary sin caja: delta máximo `0,1 rad`, velocidad
`0,15 rad/s`, aceleración `0,5 rad/s²`, muestreo `0,01 s` y transición
minimum-jerk `0,5–2,0 s`. Pasaron 28 casos dirigidos y 2.000 aleatorios. No es
un límite certificado por el fabricante ni está todavía aceptado por el
propietario.

E6.0U `20260904T073609_E6.0U` implementó el monitor fail-closed sobre estado
medido: exige los 14 ejes de brazos y los seis ejes H/L/W bloqueados, estado y
velocidad frescos, READY inicial, `|v_arm|<=0,15 rad/s`,
`|a_arm|<=0,5 rad/s²`, deriva H/L/W `<=0,01 rad` y velocidad H/L/W
`<=0,01 rad/s`. Pasaron 152 casos y 8 tamper. E6.0V
`20260904T073852_E6.0V` seleccionó en vivo y sólo lectura
`/mc/whole_joint_states`: entregó 22 nombres/posiciones/velocidades con QoS
reliable; `/mc/sdk/robot_state` tenía dos publicadores pero no produjo payload
en 3 s. También confirmó que los dos consumidores de
`/mc/sdk/robot_command` usan BEST_EFFORT y que había cero publicadores.

E6.0W `20260904T074537_E6.0W` implementó el coordinador y proceso ROS acotado
de un punto. Pasaron 24 casos de runtime y 3 casos de activación. Sólo acepta
el punto 0 de un chunk 10x20 de task 0/P14, mantiene H/L/W con el estado fresco,
crea el publicador SDK de forma perezosa tras READY+chunk válidos y destruye el
publicador al completar, fallar o recibir STOP. La plantilla versionada exige
una escena vacía estática y conserva `owner_accepted=false`,
`active_launcher_enabled=false` y `physical_execution_authorized=false`.

E6.0X `20260904T075519_E6.0X` registra la aceptación explícita del propietario
de esa envolvente únicamente para `NO_BOX_READY`, task 0, P14 y un solo punto.
El registro referencia por SHA-256 los límites aceptados y deja expresamente
`acceptance_is_movement_authorization=false` y
`physical_execution_authorized=false`.

El consolidado histórico `20260904T075648_E6.0-CHECK` consume E6.0R–X. El gate
de ejecutor queda `PASS_CODE_OFFLINE_ACTIVATION_GATED`, la aceptación queda
`PASS` y hay cero bloqueos estáticos. El preflight anterior se clasifica
`RUN_SPECIFIC_REQUIRED` y no se reutiliza hoy. No se creó ningún publicador ni
se movió el robot. Su siguiente paso de celda vacía fue ejecutado y después
retirado por E6.0Z; no debe reutilizarse para generar otro grant. Sigue
`E6.0_PHYSICAL_AUTHORIZED=0`.

El preflight fresco de fase A `20260904T075947_E6.0G`, realizado sólo en
lectura con los paros declarados accionados, confirmó Motion/ROS en ejecución,
`HW_TYPE=cruzr_s2_v1`, cargador fuera, baterías `45,8/48,5 %`, READY S2
registrado con hash `c767f739…a9b2`, VLA `exited/exited` y cero publicadores.
Software leyó `ESTOP_KEY=1` pero `SERVO_ESTOP_KEY=0`: el principal sí quedó
corroborado; el paro físico de chasis no tiene corroboración positiva por esa
señal. Como es normal bajo E-stop, no había whole-state ni action server y no
se evaluó estacionariedad. No hubo movimiento ni autorización. Reanudación:
liberar físicamente ambos paros bajo supervisión y repetir inmediatamente el
preflight con `--expect-released`, sin pulsar Power/KEY1/Start.

Tras la confirmación física de liberación, dos lecturas mostraron
`ESTOP_KEY=0`, `SERVO_ESTOP_KEY=0` y cargador `0`, pero siguieron ausentes
`/mc/whole_joint_states` y el servidor `/mc/manipulation/action`. El preflight
canónico falló cerrado y no envió movimiento. Una primera invocación local de
`cruzr_v020_boot_guard.sh --check` desde el PC produjo
`containers_not_ready`; se descarta porque ese binario debe ejecutarse dentro
de Vision. La invocación correcta de la copia instalada en `192.168.11.3`
confirmó v0.2.0, 3/3 probes x86, 2/2 rondas de las seis cámaras y seguridad
`0 0 0`, pero `CONTROL_STATE=unknown`; fue sólo lectura. Esto confirma el
estado post-E-stop no rearmado. No pulsar Power/KEY1/Start aisladamente ni
invocar StartMotion por ROS: hace falta el ciclo completo supervisado de
apagado y arranque descrito para v0.2.0.

Ese ciclo completo se realizó el 04-09 con el E-stop principal accionado
durante el arranque. Tras liberarlo, el guard remoto de Vision mostró
`JoystickMode`, grafo/cámaras listos y seguridad `0 0 0`. El preflight
`20260904T084316_E6.0G` confirmó action server, estado 20D, actuadores
habilitados, acciones libres, cargador fuera, VLA `exited/exited` y cero
publicadores. Un gate articular posterior midió HOME con velocidad cero. La
auditoría general `cruzr_recover_to_home.sh --check` puede seguir fallando si
el log recién rotado no contiene una etiqueta histórica; para E6.0 se usa el
estado articular fresco y no esa inferencia de log.

E6.0Y añade el primer launcher activo pero cerrado por defecto. `--ready`,
`--one-point` y `--recover` son etapas separadas, cada una revalida estado y
exige una frase exacta. El grant del punto dura como máximo 180 s, queda ligado
por SHA-256 al preflight/READY/aceptación/límites y se comprueba antes de
importar ROS. El publicador se crea sólo después de READY y un chunk válido;
el ejecutor vendor no se arranca y los contenedores se detienen al terminar o
fallar. La prueba offline `20260904T085243_E6.0Y-OFFLINE` pasó; no hubo acceso
al robot ni movimiento. Un recorrido vivo sin confirmación llegó hasta HOME y
falló cerrado antes del goal.

La transición E6.0Y HOME→READY autorizada se ejecutó una sola vez en
`20260904T085921_E6.0Y-READY`: Motion devolvió `SUCCEED/status=4`. El gate
inicial produjo un falso negativo porque comparó signos de coordenadas crudas
de motor con coordenadas articulares del checkpoint. La captura independiente
nombrada `20260904T090051_E6.0V` demostró los 14 brazos a un máximo de
`0,001842 rad` del READY y velocidad cero; la comprobación cruda mantuvo salud
de actuadores y delta posición–consigna máximo `0,001842 rad`. Se corrigió
`cruzr_s2_vla_ready_state_gate.py` para consumir
`/mc/whole_joint_states` por nombre, conservando la muestra cruda como gate de
fallos/consigna. La regresión offline `20260904T090403_E6.0Y-OFFLINE` pasó.
No hubo reintento, inferencia ni publicador; el estado posterior confirmó VLA
`exited/exited` y `publishers:0`. Antes de `--one-point` falta la inspección
visual del operador de READY estable y libre de contacto.

El primer intento autorizado de `--one-point`,
`20260904T090909_E6.0Y`, no llegó al trigger. La inferencia quedó lista, los
dos preflights midieron READY y se copió un grant íntegro, pero el proceso de
Motion lo rechazó antes de importar ROS con `grant_not_current`: el PC estaba
22 s adelantado respecto a Motion, por lo que `issued_at` aún quedaba en el
futuro desde el reloj validador. El cleanup confirmó contenedores
`exited/exited` y `publishers:0`; no hubo publicador ni movimiento. El builder
y launcher toman ahora un epoch fresco de Motion, registran el desfase y
fallan si `abs(skew)>60 s`. La regresión offline
`20260904T091614_E6.0Y-OFFLINE` incluye el rechazo del desfase. Una captura
posterior volvió a dar `MEASURED_READY=1`, error máximo `0,001842 rad` y
velocidad cero. No se reintenta con la autorización ya consumida: hace falta
otra confirmación exacta de un punto.

El segundo intento autorizado `20260904T091928_E6.0Y` resolvió el reloj
usando Motion (`skew=23 s`) y llegó al checkpoint. La inferencia task 0
terminó correctamente y generó tres chunks, pero el primer punto recibido fue
rechazado por `transport:arm:target_delta:2`: el objetivo del eje 2 excedía el
límite aceptado de `0,1 rad`. `frames_published=0`, por lo que no se envió
movimiento. En esta versión del runtime el backend llegó a construir
brevemente el publicador antes de planificar, aunque lo destruyó en el rechazo;
el estado final fue `publishers:0`. Esto se endureció inmediatamente: la
trayectoria completa se valida ahora antes de construir el backend/publicador,
el error incluye delta y límite numéricos y los estados repetitivos ya no
inundan el log. E6.0R check y las regresiones E6.0W
`20260904T092245_E6.0W` y E6.0Y `20260904T092246_E6.0Y-OFFLINE` pasan. Una
muestra posterior volvió a confirmar READY a `0,001842 rad`, velocidad cero;
VLA quedó `exited/exited`, `publishers:0`. No procede relajar `0,1 rad`,
repetir el punto ni recuperar automáticamente: primero debe analizarse en
shadow la discontinuidad del checkpoint.

Con confirmación física independiente, el recovery E6.0 se ejecutó una sola
vez en `20260904T092716_E6.0Y-RECOVERY`. Revalidó READY, paros liberados,
cargador fuera, actuadores sanos y acciones libres; la tarea
`s2_bio_vla/s2_vla_e6_0_exact_recovery` terminó `SUCCEED/status=4`. La medida
final dio `MEASURED_HOME=1`, cuerpo máximo `0,002780 rad`, brazos
`0,000959 rad`, velocidad cero y delta posición–consigna `0,002780 rad`. VLA
permaneció `exited/exited` y `publishers:0`. La inspección visual posterior se
registró a continuación; no debe iniciarse otro canary desde HOME sin un nuevo
ciclo HOME→READY y nueva autorización.

La inspección post-recovery quedó confirmada por el operador: HOME visual
estable, brazos y cabeza sin contacto, clamps vacíos y sin movimiento
inesperado. E6.0 queda cerrado físicamente en HOME. El siguiente trabajo es
exclusivamente shadow/offline para conservar el punto normalizado y medir la
discontinuidad de `L_shoulder_pitch_joint`; no hay autorización vigente para
READY, checkpoint ni recovery adicionales.

E6.0Z cerró el diagnóstico offline en
`20260904T094803_E6.0Z`. La metadata del checkpoint marca los 20 grupos de
acción como `absolute=true`; la salida se desnormaliza y se copia como
posición articular, por lo que no es lícito reinterpretarla como delta. Los
500 frame 0 del dataset muestran que, para task 0 (150 episodios), el primer
target demostrado difiere del estado observado como máximo `0,003134013 rad`.
Los 14 brazos usados por E6.0Y sí estaban dentro de la familia task 0
(`0,000287628 rad` respecto del frame más próximo sólo en brazos), pero la
entrada completa 20D estaba a `0,834773183 rad` de su frame task 0 más cercano:
`lifter_pitch_1_joint=0` frente a `-0,834773183 rad`. Además se solicitó
“Pick up the large box from the lowest level of shelf” en `NO_BOX_READY`; seis
frames representativos de las familias de elevador muestran un contenedor
grande apoyado, no una celda vacía. Son dos incumplimientos confirmados de
entrada (escena y estado 20D); no puede aislarse cuánto aportó cada uno al
outlier neuronal porque el runtime antiguo no conservó los valores exactos del
chunk rechazado y sólo demostró `abs(delta)>0,1` en el eje 2.

El hueco de evidencia queda corregido para futuras ejecuciones: shadow y el
runtime guardan estado, primer punto, deltas con signo y máximo por eje antes
de crear un publicador. `check_vla_task_entry_state.py` compara tarea, escena y
los 20 ejes contra un mismo frame 0 del dataset; el contrato E6.0Z exige una
distancia Chebyshev de proyecto `<=0,01 rad` y cinco chunks shadow frescos,
todos con primer delta `<=0,1 rad`. Un PASS sólo califica shadow y nunca
autoriza movimiento. La evaluación histórica falla por
`task_scene_mismatch`, `state_outside_same_task_observed_bounds` y
`state_not_close_to_any_same_task_frame_zero`.

La ruta anterior queda retirada, no meramente advertida:
`run_vla_canary_physical_e6_0y.sh --ready` y `--one-point` abortan localmente
antes de acceder a la red, y el launcher ya no contiene trigger de inferencia,
grant ni proceso publicador. Sólo permanecen `--stop` y el recovery
READY→HOME para una postura histórica interrumpida. La regresión
`20260904T100258_E6.0Y-OFFLINE` confirma 10 checks estáticos, ruta activa
eliminada, READY retirado, recovery conservado y cero acceso al robot. No se
aumentará `0,1`, no se recortará/proyectará el target y no se reintentará
`NO_BOX/task 0`. Un
sucesor físico nuevo requerirá, en este orden, escena `SUPPORTED_LOW`, entrada
20D asociada a un frame task 0, transición y recovery deterministas validados,
cinco chunks shadow frescos aceptados y una autorización física nueva. Durante
este cierre el cargador quedó conectado; no se ordenó movimiento, los análisis
de parquet se ejecutaron en un contenedor efímero `--network none` y no se
arrancaron los contenedores VLA persistentes.

Como punto de partida exclusivamente offline se seleccionó
`episode_000040`, el frame task 0 más próximo a la entrada histórica E6.0Y.
Su H/L/W es `[-0,431336224, 0, -0,834773183, -0,000958738, 0,291264594,
0,024639565] rad` y su primer target se separa sólo `0,000326395 rad` de ese
estado. El frame RGB muestra un contenedor plástico gris grande, abierto y
vacío, apoyado sobre una superficie blanca; no demuestra equivalencia con una
caja de cartón arbitraria. Esta selección permite diseñar y auditar
HOME→ENTRY→HOME, pero no congela el fixture ni autoriza movimiento.

La evidencia VLA ya no depende de variables exportadas por un bloque anterior.
`new_vla_evidence_run.sh` crea cada run de forma exclusiva y rechaza `/` y
rutas existentes. E1.1/E1.2, los smoke E2.0/E2.1 y las repeticiones E2.3 tienen
wrappers autocontenidos; E2.3 usa sesiones independientes y STOP entre runs.
E2.2, E3.0, E3.1, E3.2, E3.3, E4.0, E4.1, E4.1C, E4.1D, E4.1E,
E4.1F, E4.2, E5.0, E5.1, E5.2, E6.0A, E6.0B, E6.0C, E6.0D, E6.0E, E6.0F,
E6.0G, E6.0H, E6.0I, E6.0J, E6.0K, E6.0L, E6.0M, E6.0N, E6.0O, E6.0P,
E6.0Q, E6.0R, E6.0S, E6.0T, E6.0U, E6.0V, E6.0W, E6.0X, E6.0Y, E6.0Z y E6.0-CHECK
disponen ahora de
evaluador/sink y wrappers autocontenidos. Los ejemplos aún no implementados de
VLA-T00…T08 inicializan su directorio
en el mismo bloque. Las herramientas de evidencia son cambios del
PC/repositorio; E2.2/E3.0/E3.1 sólo arrancaron contenedores offline transitorios
en Vision; E3.2/E3.3 fueron procesos Python locales y E3.3 sólo consultó el
estado remoto antes/después. No alteraron Motion ni los contenedores VLA
persistentes.

El paquete local sí contiene
`codes-S2/motion/s2_vla_scripts/s2_bio_vla/s2_vla_pick_large_teleop_ready.xml`,
hash `f4025124…d8323`. Preposiciona cintura, cabeza y brazos y llama a la
primitiva 14D ya localizada, pero el task S2 completo no está instalado, la
pose 20D sigue incompleta y los límites/recovery/swept volume no están
demostrados. El SDK 7.3 confirma B0 `60×40×22 cm` sobre plataforma de **1 m de
altura** y sólo pide mover el robot a una posición adecuada; no proporciona
distancia horizontal.

Se extrajeron de sólo lectura 12 frames —inicio/medio/final de los episodios 0,
1, 90 y 91— con VLC. La referencia visual es un tote rígido gris abierto de
paredes altas y borde gris, con tiras/marcas negras estrechas en algunos frames
y un pequeño elemento con lazo visible dentro, no una caja de cartón cerrada.
Por ello `B0_SAFE` vacía puede servir para canary, pero es OOD si no
reproduce esa apariencia/contenido.

El siguiente bloque de trabajo VLA está planificado al principio de
[`plan_de_trabajo.md`](plan_de_trabajo.md): auditoría offline, contrato temporal,
posturas `VLA-ready`, ejecutor sink, matriz shadow de 4 tasks × 8 perfiles
funcionales (`P14`…`P20`), canary progresivo y comparación del checkpoint
intacto frente a continuación o nuevo DataConfig. Se añadieron tarjetas
`VLA-T00…T10` con fixture, estado inicial, comandos/mensajes PC, PASS/FAIL,
evidencia y recovery: `B0_SAFE` `0,603 × 0,397 × 0,217 m`, plataforma inicial
a 1 m de altura confirmada por SDK y pose medible en `PLATFORM_FRAME`. E4.2
demostró que low/middle son familias, no alturas escalares. E4.1 resolvió una
pose métrica candidata para el episodio 90 y detectó solape firmado con el
bumper. La repetición corregida E4.1C rechazó esa candidata para un tablero
sólido al confirmar 32 cruces de mesh. E4.1D confirmó que 22 cruces pertenecen
a muñecas/sensores y
subsisten sin `pgc/finger`. E4.1E encontró cero poses sólidas libres dentro de
±5° y derivó dos huecos upstream que aún carecen de la envolvente real de las
abrazaderas; el plan no autoriza movimiento, modificar la mesa ni colocar B0.
Las tarjetas
físicas permanecen bloqueadas hasta demostrar `VLA_READY`, ejecutor canary y
primitiva de trayectoria. El manual operativo al inicio del plan ordena los
experimentos `E1.0…E8.2`: montaje medido, baseline, primera inferencia, OOD,
ready, perfiles 14–20, canary, cuatro tareas físicas y evolución C1/C2. Para
experimentos 1–3 mantiene plataforma/B0 fuera de la envolvente; el 1 m es
altura de plataforma, no separación.

Fuente: [`guides/CRUZR_S2_VLA_SAFE_ENABLEMENT.md`](guides/CRUZR_S2_VLA_SAFE_ENABLEMENT.md).

### 4.5 Teleoperación del robot

Se verificaron `TELE_DEVICE=pico`, `transmit=local`, `signal_server`,
`rtm_receiver` y la tarea
`teleoperation/cruzr_clamp_pico_teleoperation`. No se renombraron topics,
colas o servicios del robot.

`walker28` es exclusivamente el `channel_name` del backend PC. El nombre
`walker28_web` no se encontró en el frontend ni en el sistema inspeccionado.

### 4.6 Tareas auxiliares y scripts

El repositorio contiene XML auxiliares y scripts para brazos, voz, manos,
cajas, navegación, recovery, VLA y teleoperación. Algunos scripts pueden
instalar tareas versionadas en el árbol de manipulación del robot antes de
ejecutarlas; su presencia debe comprobarse mediante los modos `--check` y los
hashes incorporados. No asumir que una tarea local está instalada tras una
actualización.

Los scripts se migraron a los nombres de imágenes/tareas observados en v0.2.0.
La migración se validó sin instalar tareas nuevas ni mover el robot.

## 5. Cambios persistentes en el PC de teleoperación

### 5.1 Paquetes instalados

- XRoboToolkit PC Service `1.0.0.0` para Ubuntu 24.04.
- `ubt-controller` `4.7.0` entregado por UBTECH para el robot v0.2.0 e
  instalado el 26-08; binario oficial sin parches `e88b83b7…`.
- `ubt-remote-control` `4.1.0`.
- ADB y regla udev para PICO.
- Servicio systemd `/etc/systemd/system/ubt-controller.service`.

Instaladores grandes y SOP se mantienen fuera de Git; sus hashes están en la
fuente de teleoperación y en [`../utats/README.md`](../utats/README.md).

### 5.2 Configuración y workarounds PC

- Ruta preferida PC → Motion/Vision por Ethernet `eno1`/`.11.250`, 1 Gb/s;
  Wi-Fi Cruzr conserva PICO, `.42.0/24` y el fallback `.11.0/24` vía `.42.2`.
  Ambas son never-default; Internet continúa exclusivamente por DSA.
- Backend con `transmit=local`, señalización
  `ws://192.168.11.3:4000`, `channel_name=walker28`, dispositivo PICO y
  `enable_foot_switch=1` restaurado por 4.7.0, pendiente de aclaración.
- Los tres parches diagnósticos de 5.3.0 —`GRIPPER→CLAMP`, gatillo izquierdo
  como Y por flanco y timeout heartbeat 300 s— ya no están instalados. 4.7.0
  usa el binario exacto del DEB del proveedor y su watchdog por defecto.
- `arm=clamp` se conserva como variable systemd del PC; `LC_NUMERIC=C` evita
  diferencias locales de separador decimal sin modificar el ejecutable.
- 4.7.0 instala además el cliente oficial `/usr/local/bin/pico_control`
  (`46323392…`), cuya ayuda admite `--arm_type clamp`. No se ejecutó porque
  puede iniciar el flujo de control; el preflight sólo verifica hash y ayuda.
- La instalación 5.3.0 parcheada, configuración, units y backups quedó
  archivada en
  `/home/lacuna/Descargas/ubt-controller-5.3.0-patched-20260826.tar.gz`
  (SHA-256 `c085fc4b…`). El DEB original 5.3.0 se conserva fuera de Git.
- El preflight de teleoperación muestra ahora siete etapas con timestamp y
  timeouts de 5 s para ADB/systemd/journal/WebSocket. La variable
  `CRUZR_TELEOP_DEBUG=1` activa traza Bash con línea y comando; los fallos del
  gate informan el punto exacto antes de solicitar STOP.
- Se mejoró orden de arranque: servicio XR y PICO antes del backend; UI al
  final. Una desconexión/suspensión del visor puede exigir reinicio del
  servicio.
- El lanzador descubre ahora el mismo visor por `ro.serialno` tanto si ADB usa
  el serial USB como si usa un destino `IP:puerto`; `PICO_ADB_TARGET` permite
  fijar el transporte para diagnóstico. No se cambió ninguna ruta de mando.

El binario original permanece respaldado; los hashes original y activo están
en la fuente especializada.

### 5.3 Último estado PC

El 26-08 quedó activo `ubt-controller 4.7.0`, listener 8082 y XR Service 63901;
la UI está inactiva. PICO mantiene el flujo USB `192.168.51.220` →
`192.168.51.42:63901` y `vr_status=1`. El cliente oficial se ejecutó una vez
con timeout y `--arm_type clamp`: Y produjo `Left.b_button=true` y el callback
`tele_operation enable=1`; el grip derecho llegó al backend. Sin embargo, el
backend registró `Arm type is: gripper`. El propietario acepta temporalmente
esa diferencia sólo para cinemática de brazos y prohíbe inferir equivalencia
para mandar el efector. `pico_control` confirmó STOP/`operation_type=1`. El
rearme observado un segundo después no fue espontáneo: un segundo cliente
diagnóstico `wscat --wait 1` permaneció conectado después de enviar STOP y el
backend autoarrancó al detectar cliente + PICO online. El STOP canónico corto
lo dejó después en `operation_type=1`, cliente terminado y articulaciones
inmóviles. No mantener otro WebSocket abierto después de STOP.
La concesión Wi-Fi observada del PICO cambió a `.42.212`, como corresponde a
DHCP. Tras sustituir el cable, Ethernet negocia 1000 Mb/s full y Motion/Vision
responden directamente desde `.11.250` en 0,2–0,9 ms; Wi-Fi Cruzr queda activa
para PICO/fallback y `DSA CORPORATE` mantiene la ruta por defecto de Internet.

El estado 5.3.0 con `vr_status=1`, `enable_control=0` y el backend parcheado
`5083e9f0…` queda como evidencia histórica del 25-08, no como estado activo.

El 27-08 se verificó en Motion que la tarea
`teleoperation/cruzr_clamp_pico_teleoperation` carga `Hand type: clamp`, pero
el YAML vendor activa cuerpo completo con `waist_mode=1` y `leg_mode=2`.
Durante la sesión problemática ambos grips quedaron simultáneamente altos y
el solver registró fallos de alcance repetidos; el torso/elevador compensó en
CoreMode 7. Se instaló de forma reversible un overlay que cambia únicamente
esos dos modos a cero, SHA-256 `4e8d79a4…`, conservando clamp, brazos,
anticolisión y umbrales de fuerza. El backup vendor `5f08b30c…` y el overlay
persisten en Motion bajo `$HOME/.local/share/cruzr-pico-arms-only/`. El overlay
se recargó después y el último baseline conocido quedó
`ARMS_ONLY_LOADED=hand:clamp,waist:0,leg:0`.

El 28-08 se añadió `scripts/teleoperation/probar_pico_full.sh` como lanzador
separado, dejando `probar_pico.sh` sin cambios. Puede preparar el rollback
exacto al YAML vendor y sólo permite START full-body si demuestra hash
`5f08b30c…` más tarea viva `clamp,waist=1,leg=2`; exige Wi-Fi sin Ethernet
sujeto al robot, conserva los gates oficiales y añade STOP ante clicks de
protección, fallos IK, sobreesfuerzo, EtherCAT o pérdida del monitor Motion.
La preparación, recarga de TeleopMode y movimiento son pasos separados. El
cambio quedó validado localmente y con checks de sólo lectura: el full rechazó
correctamente el hash activo `4e8d79a4…` y el original confirmó
`ARMS_ONLY_LOADED=hand:clamp,waist:0,leg:0`. **No se restauró ni cargó el perfil
full, no hubo START ni movimiento**. El primer `--prepare-full` real del
28-08 a las 09:48 superó el preflight Motion, pero abortó antes del rollback:
el comprobador pasivo intentaba asignar temporalmente la constante shell
`readonly BACKEND_LOG`, por lo que Python no recibió la ruta. Se corrigió usando
el nombre de entorno independiente `BACKEND_LOG_PATH`. La reproducción de sólo
lectura devolvió `PASSIVE_OPERATION_TYPE=1` y el check posterior volvió a
demostrar `clamp,waist=0,leg=0`; por tanto no hubo cambio parcial.

Más tarde, tras una sesión PICO, `cruzr_recover_to_home.sh --run --yes`
clasificó correctamente `teleoperated_pose` y lanzó la tarea vendor verificada
`cruzr/open_arm_before_home`. Su primera fase no es una separación cartesiana
condicionada por postura: manda en paralelo ambos brazos a objetivos articulares
intermedios, y también cintura/elevador a cero. Desde la postura cruzada real,
Motion registró primero anticolisión torso–codo/muñeca izquierda durante el
final de teleoperación y, ya en recovery, `Force-X=-370,944 N` en el FT
izquierdo. El brazo derecho y cintura terminaron; el izquierdo falló con
errores articulares grandes y el elevador abortó. La acción acabó
`MoveToGoalFailed`, state `7104050`, `status=6`. Después 4004, 4003 y 4002
registraron `0x1003`/`Operation disabled unexpected:0x123f`; `hw` y
`manipulation_robot_app` reiniciaron. Con el paro accionado, rosa_control espera
`/mc/rosa_control/start`, `/mc/actuator_state` tiene cero publicadores y la
acción de manipulación cero servidores. **DESCARTADO** usar
`open_arm_before_home` como retorno universal desde cualquier postura PICO.
No se liberó el paro, rearmó, reinició, cambió modo ni envió otro movimiento
durante el diagnóstico; el siguiente paso requiere confirmación física fresca
y, si procede, apagado completo controlado, no otra trayectoria.

El operador confirmó después paro accionado, brazo izquierdo apoyado sin
presión apreciable, robot/brazos estables, abrazaderas vacías, cargador fuera,
zona de descenso despejada y persona junto al paro. La solicitud oficial
`/emb/pm_shutdown` con `confirm-to-shutdown` respondió `success=True`; Motion y
Vision pasaron de accesibles a no responder. Tras confirmar físicamente
pantalla y luces apagadas, el operador pulsó `KEY1` y luego apagó el chasis.
Estado final: indicador verde apagado, hosts sin respuesta, robot y brazos
estables. No se liberó el paro, rearmó ningún servo ni se envió otra
trayectoria. Los faults y consignas deben redescubrirse desde cero en el
próximo arranque controlado.

El drop-in de lifecycle de 15 s permanece instalado. Una parada anterior de
5.3.0 agotó el margen y recibió SIGKILL; durante la migración el servicio se
mantuvo enmascarado para impedir que el `postinst` del proveedor arrancara el
backend antes de completar la configuración.

Fuente completa:
[`teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md`](teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md).

## 6. Capacidades verificadas

### 6.1 Operación y diagnóstico

- Lectura de batería, cargador, paros, sensores y estado de potencia.
- Control web y cambio de modos de trabajo.
- Mando físico para elevador/chasis después de rearme correcto y desbloqueo de
  ruedas.
- TTS en inglés y ASR capaz de transcribir inglés; español funciona peor.
- Cámaras, LiDAR, RGB-D/estéreo y navegación con evitación de obstáculos.

### 6.2 Manipulación tradicional, sin VLA

- Detector especializado `workbin` de UBTECH/DSA para pose 6D de contenedores.
- Centrado visual, agarre bimanual BYD, elevación y depósito mediante tareas
  deterministas.
- Control de separación y fuerzas durante el agarre.
- Transferencia de la caja azul desde mesa 1 a mesa 2 mediante detector,
  navegación, waypoint y AprilTag; un ciclo `--resume-held` completó depósito,
  retroceso de aproximadamente 0,484 m y `home`.
- AprilTag 113 detectado y calibrado para pose vacía y pose con carga.

GR00T/VLA no intervino en esas pruebas. La adaptación procede de detección 6D,
transformaciones, realimentación de fuerza y secuencias programadas.

### 6.3 Manos

Con manos v4 instaladas se verificaron topics y tareas de fábrica para apertura,
cierre, pinzas de dedos, gestos y secuencias. Las manos ya no están instaladas.

### 6.4 VLA

- Checkpoint suministrado cargable en v0.2.0 mediante overlay.
- Inferencia y validación shadow sin publicar a control físico.
- Cuatro IDs documentados: recoger/depositar caja grande en nivel inferior y
  medio.
- No se ha demostrado una ejecución física segura del checkpoint.

Catálogo detallado:
[`guides/CATALOGO_FUNCIONALIDADES_CRUZR_S2.md`](guides/CATALOGO_FUNCIONALIDADES_CRUZR_S2.md).

## 7. Problemas conocidos y decisiones vigentes

### 7.1 PICO/teleoperación — bloqueo P0

La cadena PICO → PC → robot llegó a `Working`, señalización, DataChannel y
recepción de tele-data. El PC no recibe el heartbeat de aplicación esperado.
Con el timeout original esto deshabilitaba la sesión aproximadamente cada
11,1 s; el timeout diagnóstico de 300 s ya superó en runtime ese límite, pero
no corrige ni valida el heartbeat.

En el gate del 25 de agosto se verificó además el workaround de entrada:
gatillo izquierdo → `b_button=true` → `enable=1` → Motion `CoreMode 7`. El
Y del proveedor funciona como conmutador con repetición, no como *deadman*:
con el gatillo crudo estable en `1.0`, `enable` alternó aproximadamente cada
0,51 segundos. A las 12:27 una sola pulsación de 0,567 s volvió a alternar
`enable 0→1→0`; no fue un fallo de heartbeat. El backend activo publica ahora
sólo el flanco ascendente. Tras detectar que el primer gate reutilizaba
muestras antiguas, los scripts exigen ahora muestras Left/Right nuevas después
de START mientras `enable_control=0`, neutralidad antes de mostrar
`TOQUE AHORA` y liberación posterior del gatillo. Su test aislado pasó; el E2E
físico queda pendiente.
Los STOP automáticos dejaron el PC en `operation_type=1`, `enable_control=0`.
El operador confirmó cero movimiento físico en los intentos informados. El gate
local de 60 segundos se ejecutó el 25 de agosto: START fue a las 09:53:46.142,
el toque habilitó a las 09:53:49.845 y el watchdog cerró a las 09:53:56.718 por
`No heartbeat for 10 seconds`. No hubo movimiento físico y sí se oyó una voz
del robot. Esto confirma el bloqueo P0 de heartbeat.

En la ventana de las 10:38 con el timeout de 300 s, el DataChannel abrió antes
de habilitar y `enable_control=1` se sostuvo durante unos 46,1 s sin disparar
el watchdog anterior. Motion entró en `CoreMode 7`, habilitó la protección de
fuerza de ambos brazos y arrancó ambos chequeos de fuerza. El operador movió
los mandos, pero observó cero movimiento del robot. El log PC contiene 4.530
muestras por mando durante ese minuto y ninguna activación de
`squeeze`/grip (`false`, valor `0.0`). Según el SOP, mover el mando sólo hace
seguir al brazo mientras se mantiene el grip correspondiente; por ello este
resultado es el esperado para el gate sin maniobra y no valida ni refuta aún
el seguimiento físico. Tres pulsaciones nuevas al final produjeron
`enable=0→1→0` a intervalos de 0,5 s; el lanzador detectó la pérdida y envió
STOP. El robot quedó `CoreMode 0`/`NotTele` y el PC en
`operation_type=1`, `enable_control=0`. A las 10:43 el stream XR volvió a
`vr_status=0`, aunque TCP/ADB reverse seguían presentes.

A las 10:50–10:51 se restauró de nuevo el stream reiniciando sólo
XRoboToolkit y conservando ADB reverse. El propietario autorizó después una
prueba física real inmediata. `probar_pico.sh` sin argumentos ejecuta ahora
una micromaniobra del brazo derecho; `--move-left-arm` permite la segunda
prueba y `--gate-only` conserva el diagnóstico sin movimiento. Cada modo
físico exige un preflight fresco de paros, batería, cargador, efector, tarea
PICO y velocidad articular, mantiene 60 s sin grips, admite un solo grip y un
gesto de 2–3 cm durante un máximo de 5 s, y envía STOP al soltar o fallar. El
preflight sólo lectura pasó con baterías 77,2/77,8 %, ambos paros a cero,
cargador desconectado, robot inmóvil y tarea Cruzr/PICO correcta. No se envió
START durante la implementación ni la validación seca.

A las 11:53 el transporte XR se migró a la WLAN local `Cruzr S2-0669` sin
alterar `DSA CORPORATE`: PC `192.168.42.215`, PICO `192.168.42.211`. Tras
seleccionar `Head + Controllers` y `Send data`, XRoboToolkit abrió TCP directo
hacia el listener PC `63901`. Se borró el reverse, el flujo siguió establecido
y el preflight canónico terminó correctamente con el backend en STOP. ADB TCP
se usó sólo para administración inalámbrica; no transporta el stream XR
directo. No hubo movimiento físico.

La reinspección de los artefactos instalados descarta que el heartbeat deba
producirlo la UI PC: el source map de `ubt-remote-control 4.1.0` sólo envía
START/STOP. El bytecode de `Publisher.callback` en `ubt_controller 5.3.0`
declara que procesa mensajes inversos del robot por RTM y sólo ante
`type=heartbeat` actualiza `last_heartbeat_time`. **DESCARTADO** desactivar o
puentear este watchdog en el PC: eliminaría la detección de pérdida robot→PC.
El propietario autorizó después una excepción limitada: ampliar el timeout a
300 s para diagnóstico, conservando el STOP. Esto no resuelve ni valida el
heartbeat y una ventana local de 60 s ya no puede declararse gate de heartbeat.
Si el robot debe permanecer inmutable, UBTECH debe suministrar un backend PC
compatible con la v0.2.0 genérica o el componente oficial que complete ese
heartbeat, conservando la parada por pérdida de enlace.

La coordinación del flanco ya no debe realizarse por chat. El modo local
`cruzr_pico_teleop_pc.sh --gate-local` exige terminal interactivo, emite la
señal `TOQUE AHORA` sólo después de armar, monitoriza el gate y envía STOP al
terminar o ante cualquier fallo. `--run` es únicamente un alias compatible.
El lanzador humano `scripts/teleoperation/probar_pico.sh` presenta esas órdenes
en el terminal y delega el flujo al controlador canónico. Por defecto ejecuta
la prueba física mínima del brazo derecho; `--move-left-arm` selecciona el
izquierdo y `--gate-only` conserva el gate sin maniobra. Tras observar que
`Ctrl+C` durante un `read` enviaba STOP pero permitía continuar, el handler se
corrigió para terminar definitivamente con código 130 (143 para `TERM`)
después del STOP.

El SOP exige `utars-udoke-config-v0.2.0-dac-beta.2.tar.gz`, pero sólo está
demostrada la build genérica v0.2.0. Además, `MC_SCENE` está vacío y no se
encontró `pico_control`, aunque ambos aparecen en el SDK/SOP.

Decisiones:

- no eliminar el watchdog ni fabricar heartbeat; el timeout temporal autorizado
  es 300 s y debe tratarse como workaround diagnóstico;
- no declarar lista la teleoperación por ver sólo `Working`, `TeleopMode` o un
  topic existente;
- no ejecutar a la vez el cliente PC y un supuesto cliente PICO directo;
- exigir un gate monitorizado de 60 s antes de cualquier movimiento mínimo;
- pedir a DSA paquete DAC exacto, hashes, matriz de versiones, componente de
  heartbeat y procedimiento directo.

Fuente viva obligatoria:
[`teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md`](teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md).

### 7.2 Navegación transportando caja

La caja puede aparecer ante las cámaras RGB-D/estéreo como obstáculo propio y
bloquear el costmap dinámico. Se creó un perfil temporal de percepción de
carga que redirige únicamente tres entradas de nube de puntos; mantiene LiDAR,
odom, mapa, bumpers y paros. El último preflight registró
`CARGO_PERCEPTION_PROFILE=disabled`, es decir, restaurado.

Nunca desactivar toda la evitación ni dejar el perfil activo después del
transporte.

### 7.3 Depósito y AprilTag

- Una tolerancia demasiado estricta causaba múltiples correcciones aunque la
  caja ya estuviera razonablemente sobre la mesa.
- El perfil `--fluid` acepta hasta 50 mm en la estación validada, con límites
  duros y menos muestras/iteraciones.
- Una lectura vertical no se corrige con el chasis. La postura de cabeza y
  brazos debe coincidir con la calibración.
- La aproximación autónoma se interrumpe si la orientación o la detección es
  inestable; no debe abrir las abrazaderas al fallar.

### 7.4 Arranque y apagado

- La carrera de arranque v0.2.0 está mitigada mediante boot guard local.
- El manual oficial exige un `Servo Control Button` no identificable en esta
  revisión física.
- La máquina de estados v0.2.0 pide pulsar el paro rojo después de aceptar un
  apagado, aunque el manual no lo incluye como apagado normal.
- Usar `KEY1` aisladamente produjo un corte compatible con apagado abrupto y
  corrupción de logs Docker. No debe usarse como sustituto del apagado lógico.
- El procedimiento definitivo aplicable a este número de serie sigue
  pendiente de DSA.

Fuente:
[`support/UBTECH_SHUTDOWN_PROCEDURE_MISMATCH_V020.md`](support/UBTECH_SHUTDOWN_PROCEDURE_MISMATCH_V020.md).

### 7.5 Baterías/BMS

Históricamente se observó gran diferencia de SOC y truncamiento del segundo
número de serie. Tras la actualización se registraron SOC equilibrados y
números completos, pero la respuesta técnica del proveedor sobre el fallo
histórico sigue pendiente. La UI también llegó a mostrar “fault” sin error de
powerboard. No borrar alarmas ni asumir que son falsas sin comprobar BMS.

### 7.6 Voz

ASR transcribió frases inglesas cuando `run_record`/chatting estaban en el
estado adecuado. Los topics no siempre emitían; se llegó a recuperar texto del
log del motor ASR. El español se reconocía peor. No existe una lista completa
confirmada de órdenes industriales por voz.

### 7.7 Soporte documental y proveedor

Siguen abiertos, entre otros: build DAC exacta, heartbeat, apagado actualizado,
corrección oficial del boot race, cliente MQTT, Netdata, GPU, documentación de
payload, pipeline teleoperación → LeRobot, certificado de conformidad y reporte
de inspección de fábrica.

Seguimiento:
[`support/UBTECH_SUPPORT_TRACKER.md`](support/UBTECH_SUPPORT_TRACKER.md) y
[`support/UBTECH_OPEN_QUESTIONS.md`](support/UBTECH_OPEN_QUESTIONS.md).

## 8. Matriz de reanudación por tarea

### 8.1 Diagnóstico o recuperación de postura

1. Confirmar visualmente efector, carga y obstáculos.
2. Ejecutar `./scripts/cruzr_recover_to_home.sh --check`.
3. Leer `RECOVERY_ROUTE`: `already-home` no envía objetivos;
   `known-workbin` es la única ruta automática candidata.
4. No enviar `home` con una carga o contacto dentro de la trayectoria.
5. Tras PICO no usar `cruzr/home` ni `open_arm_before_home`: el script canónico
   bloquea toda postura no-home de PICO. Volver a home dentro de la propia
   sesión PICO antes de STOP o usar el procedimiento de recuperación por
   fault/apagado; no adivinar una trayectoria desde una postura cruzada.

### 8.2 Caja mesa 1 → mesa 2

1. Leer la guía AprilTag completa.
2. Ejecutar `--check --fast` o preparar `--check --fluid`.
3. Primera puesta en servicio: `--stage-held`; inspeccionar en `MESA2_PRE`.
4. Con caja ya sujeta, usar el modo de reanudación apropiado; no reiniciar el
   ciclo completo.
5. Confirmar visualmente tag, mesa y estabilidad antes del depósito.

Script canónico:
`scripts/cruzr_blue_workbin_table_transfer.sh`.

### 8.3 PICO

1. Leer la fuente PICO completa, incluida la checklist P0.
2. Comprobar que no hay otro cliente ni servicio reactivado.
3. Recuperar ADB/red/`Working`; verificar tracking y backend por separado.
4. Ejecutar `./scripts/teleoperation/probar_pico.sh --check` con el visor en
   Head + Controllers / Send data / Working; debe terminar 7/7 con
   `PICO_TRACKING_OK=vr_status:1`.
5. Ejecutar `./scripts/teleoperation/probar_pico.sh --check-arms-only`; debe
   demostrar el hash esperado y `hand:clamp,waist:0,leg:0`. Si informa
   `waist:1,leg:2`, no mover: salir de TeleopMode y volver a entrar sólo con
   preflight físico fresco para recargar la tarea.
6. Para brazos use únicamente `./scripts/teleoperation/probar_pico.sh
   --teleoperate`: integra `pico_control` oficial, cámara, preflight físico,
   muestras neutras, Y, gate arms-only, ventana de 300 s y STOP. Permite uno o
   ambos brazos; con ambos use recorridos pequeños y suelte ante resistencia,
   retraso o movimiento del torso. `PICO_ALLOW_BIMANUAL=0` restaura el rechazo
   de solapamiento. No autoriza chasis, elevador, joysticks, botones adicionales
   ni gatillos de efector.
7. No usar todavía `--gate-only`, `--move-*-arm` ni `--all-controls`: 4.7.0 no
   publica el campo `enable_control` usado por los gates de 5.3.0. Los scripts
   solicitan STOP y bloquean START en esos modos legados.
8. Repetir siempre el preflight físico fresco y verificar cámara PICO antes de
   cualquier movimiento. La captura de un episodio piloto
   sigue pendiente de exportación y auditoría.

### 8.4 VLA suministrado

1. Mantener contenedores detenidos salvo diagnóstico solicitado.
2. Usar `--status` y shadow, nunca un ejecutor físico implícito.
3. Registrar la postura oficial ready y repetir shadow desde ella.
4. Resolver task-ID, primitiva de trayectoria, límites y deadman antes de
   publicar a control.

### 8.5 Nuevo dataset/checkpoint

1. No iniciar una campaña grande hasta exportar y auditar un episodio piloto.
2. Capturar misión, fases, observaciones sincronizadas, acciones, estado,
   fuerza, cámaras, transformaciones, mapa/waypoints, AprilTags y resultado.
3. Separar navegación global, alineación local, pick, transporte y place.
4. Mantener variantes de caja/pose/iluminación y negativos/recovery en splits
   por escenario, no por frames.

Fuente:
[`vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md`](vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md).

### 8.6 Manos

Las manos no están instaladas. Para retomarlas: SOP físico, `HW_TYPE` correcto,
homing, `check_hands.sh`, ensayo `--check` y luego demostración vacía. No usar
scripts de manos con abrazaderas.

## 9. Qué no debe darse por hecho

- Que la postura o el modo descritos aquí siguen vigentes.
- Que mapa cargado significa localización correcta.
- Que `Working` del PICO significa teleoperación autorizada.
- Que un topic DDS anunciado está publicando muestras frescas.
- Que `status=6` con `RUNNING` es éxito; en acciones ROS 2, el éxito observado
  ha sido `status=4` con `SUCCEED`.
- Que una tarea de manos, caja o VLA sigue instalada después de actualizar.
- Que `KEY1` es el botón de apagado lógico.
- Que una caja ligera valida la carga nominal.
- Que un detector workbin generaliza a botellas u otras clases.
- Que una reproducción `.motion` es una política adaptativa.

## 10. Estructura y fuentes canónicas

| Tema | Fuente canónica |
|---|---|
| Contexto global | este documento |
| Teleoperación PICO/PC/robot | [`teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md`](teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md) |
| Handoff histórico PICO | [`teleoperation/CRUZR_S2_PICO_TELEOP_HANDOFF_2026-08-24.md`](teleoperation/CRUZR_S2_PICO_TELEOP_HANDOFF_2026-08-24.md) |
| Captura y entrenamiento VLA | [`vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md`](vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md) |
| VLA instalado y shadow | [`guides/CRUZR_S2_VLA_SAFE_ENABLEMENT.md`](guides/CRUZR_S2_VLA_SAFE_ENABLEMENT.md) |
| Cajas y AprilTags | [`guides/TRANSFERENCIA_CAJA_ENTRE_MESAS_CON_APRILTAG.md`](guides/TRANSFERENCIA_CAJA_ENTRE_MESAS_CON_APRILTAG.md) |
| Plan pick → transporte → volcado → depósito multialtura | [`plan_de_trabajo.md`](plan_de_trabajo.md) |
| Contacto/fault y recuperación post-teleop | [`guides/CRUZR_S2_RECUPERACION_TRAS_CONTACTO_TELEOP.md`](guides/CRUZR_S2_RECUPERACION_TRAS_CONTACTO_TELEOP.md) |
| Capacidades y ejemplos | [`guides/CATALOGO_FUNCIONALIDADES_CRUZR_S2.md`](guides/CATALOGO_FUNCIONALIDADES_CRUZR_S2.md) |
| Manos | [`../scripts/hands/README.md`](../scripts/hands/README.md) |
| Boot guard | [`guides/CRUZR_V020_BOOT_GUARD.md`](guides/CRUZR_V020_BOOT_GUARD.md) |
| Apagado | [`support/UBTECH_SHUTDOWN_PROCEDURE_MISMATCH_V020.md`](support/UBTECH_SHUTDOWN_PROCEDURE_MISMATCH_V020.md) |
| Soporte | [`support/UBTECH_SUPPORT_TRACKER.md`](support/UBTECH_SUPPORT_TRACKER.md) |
| SDK original | [`../Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/`](<../Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/>) |

## 11. Protocolo de actualización de esta fuente

Después de cada intervención material, añadir o corregir:

1. fecha y evidencia;
2. estado físico/lógico final **sin asumir que persistirá**;
3. cambio persistente en robot, PC o repositorio;
4. verificación realizada y resultado;
5. rollback disponible;
6. bloqueo o riesgo nuevo;
7. siguiente comando de sólo lectura y documento a consultar.

No copie logs completos aquí. Resuma y enlace la fuente detallada. Si la
evidencia contradice este documento, prevalece la evidencia actual y debe
actualizarse este archivo antes de cerrar la sesión.

## 12. Historial global

| Fecha | Hito | Resultado |
|---|---|---|
| 2026-09-04 | E6.0Z cierre del outlier de entrada | run `20260904T094803_E6.0Z`: metadata demuestra acciones absolutas; 500 entradas/4 tasks auditadas offline. Task 0 tiene 150 episodios y delta máximo frame-0 acción−estado `0,003134013 rad`. La entrada histórica E6.0Y estaba a `0,834773183 rad` del frame task 0 más próximo por `lifter_pitch_1_joint`, además de usar `NO_BOX` para una instrucción de pick con caja/repisa. Gate de tarea/escena/20D rechazó por tres causas; 3/3 tests. El valor exacto del target histórico no es recuperable del log anterior, pero la instrumentación futura ya conserva posiciones y deltas completos. `--ready`/`--one-point` E6.0Y retirados antes de red y código activo eliminado; regresión `20260904T100258_E6.0Y-OFFLINE`, sólo STOP/recovery histórico. Cargador conectado, cero ROS/publicador/movimiento durante E6.0Z |
| 2026-09-04 | E6.0Y recovery READY→HOME | run `20260904T092716_E6.0Y-RECOVERY`: preflight/READY frescos; tarea exacta terminó `SUCCEED/status=4`. HOME medido en 20 ejes: cuerpo ≤`0,002780 rad`, brazos ≤`0,000959 rad`, velocidad 0 y delta ≤`0,002780 rad`. VLA `exited/exited`, `publishers:0`. Operador confirmó HOME visual estable, sin contactos, clamps vacíos y sin movimiento inesperado; ciclo físico cerrado |
| 2026-09-04 | E6.0Y checkpoint rechazado sin movimiento | run `20260904T091928_E6.0Y`: grant ligado a Motion válido (`skew=23 s`), inferencia task 0 `SUCCEEDED`, 3 chunks; primer punto rechazado por `target_delta` del eje 2 >`0,1 rad`. Cero frames y cero movimiento; un publicador se construyó transitoriamente y fue destruido, final `exited/exited`, `publishers:0`. Runtime corregido para planificar antes de crear publicador; E6.0W `20260904T092245` y E6.0Y offline `20260904T092246` pasan. READY posterior ≤`0,001842 rad`, velocidad 0. Bloqueado nuevo punto hasta análisis shadow |
| 2026-09-04 | E6.0Y primer intento de punto abortado antes de ROS | run `20260904T090909_E6.0Y`: inferencia lista y READY fresco, pero `grant_not_current` por PC 22 s adelantado a Motion. Rechazo anterior a import ROS, publicador y trigger: cero movimiento; cleanup `exited/exited`, `publishers:0`. Grant corregido para usar epoch Motion y rechazar `abs(skew)>60 s`; regresión `20260904T091614_E6.0Y-OFFLINE` aprobada. READY posterior sigue medido a ≤`0,001842 rad`, velocidad 0. Pendiente nueva autorización |
| 2026-09-04 | E6.0Y HOME→READY físico | run `20260904T085921_E6.0Y-READY`: goal único `SUCCEED/status=4`; falso negativo inicial por mezclar coordenadas crudas de motor con joints ROS. E6.0V `20260904T090051_E6.0V` midió READY por nombre con error máximo `0,001842 rad`, velocidad 0 y delta crudo ≤`0,001842 rad`. Gate corregido y regresión `20260904T090403_E6.0Y-OFFLINE` aprobada. Sin reintento, inferencia ni publicador; VLA `exited/exited`, `publishers:0`. Pendiente confirmación visual antes del punto físico |
| 2026-09-04 | E6.0Y launcher por etapas | `20260904T085243_E6.0Y-OFFLINE`: grant válido y rechazo por E-stop, gate READY nominal/rechazo por delta y 7 checks estáticos pasan; plantilla desactivada, sin robot/ROS/publicador/movimiento. Un preflight vivo posterior sin confirmación verificó HOME, `ESTOPS=0,0`, acciones listas y `publishers:0`, y terminó antes del goal. Próximo paso: autorización física específica de `--ready` |
| 2026-09-04 | Reinicio completo rearma Motion | ciclo supervisado con E-stop activo durante arranque; después de liberarlo, guard Vision en `JoystickMode`. E6.0G `20260904T084316_E6.0G`: actuadores habilitados, estado/action disponibles, cargador fuera, VLA detenido y cero publicadores. HOME fresco: cuerpo ≤0,002780 rad, brazos ≤0,000959 rad, velocidad cero |
| 2026-09-04 | Liberación de paros no rearma Motion | señales `0/0/0`, pero sin whole-state ni action server; preflight fail-closed, cero movimiento. Guard ejecutado correctamente en Vision: v0.2.0, x86 3/3, cámaras 2/2, `CONTROL_STATE=unknown`, `RECOVERY_ELIGIBLE=0`. El `containers_not_ready` previo se descarta por haberse ejecutado localmente en PC. Siguiente paso: ciclo completo supervisado; no Power/KEY1/Start aislados |
| 2026-09-04 | E6.0 preflight fresco fase A | run `20260904T075947_E6.0G`: principal corroborado activo (`1`), servo/chasis no corroborado (`0`), cargador fuera, baterías 45,8/48,5 %, READY S2 correcto, VLA detenido y cero publicadores. Sin estado/action server bajo E-stop, sin movimiento. Pendiente liberar ambos paros y repetir `--expect-released` |
| 2026-09-04 | E6.0U/V/W/X y consolidado | U `20260904T073609_E6.0U`: monitor medido, 160/160 casos. V `20260904T073852_E6.0V`: estado vivo `/mc/whole_joint_states`, 22/22/22, command QoS BEST_EFFORT y cero publicadores. W `20260904T074537_E6.0W`: runtime/proceso ROS de un punto, 27/27 casos, publicador perezoso y activación cerrada. X `20260904T075519_E6.0X`: propietario acepta `0,1 rad / 0,15 rad/s / 0,5 rad/s²` sólo para NO_BOX y no como autorización de movimiento. CHECK `20260904T075648_E6.0-CHECK`: cero gates estáticos; preflight/grant de corrida pendientes, sin movimiento ni autorización física |
| 2026-09-03 | Cierre E6.0R/S/T | R `20260903T142823_E6.0R`: adaptador SDK/STOP offline, 51/51 casos. T autoritativo `20260903T143529_E6.0T`: `/mc/sdk/robot_command` es el transporte vivo correcto, cero publicadores, VLA detenido; runs T previos descartados. S `20260903T144344_E6.0S`: 2.028/2.028 trayectorias dentro de 0,1 rad, 0,15 rad/s y 0,5 rad/s². Falta monitor medido, launcher cerrado y aceptación del propietario; sin autorización física |
| 2026-09-03 | E6.0-CHECK posterior a Q | run `20260903T140006_E6.0-CHECK`: consume la evidencia física de READY/recovery y marca ese gate PASS. Quedan 2 bloqueos: transporte/STOP físico y aceleración; `E6.0_PHYSICAL_AUTHORIZED=0` |
| 2026-09-03 | E6.0Q READY/recovery físico sin caja | run `20260903T135236_E6.0Q`: READY S2 y segundo recovery `s2_vla_e6_0_exact_recovery` terminaron `SUCCEED/status=4`; HOME final medido en 20 ejes, velocidad cero. El primer recovery no movió y reveló YAML en la raíz de paquete errónea; el fatal reinició una vez el task manager. Se corrigieron ruta MetaMove y cintura 1D, XML `9e47b6ee…4fbcc`, backup `20260903T134947_E6.0Q`. VLA `exited/exited`, `publishers:0`. El auditor canary queda con 2 gates: transporte/STOP físico y aceleración |
| 2026-09-03 | E6.0P primer ready físico, recovery y overlay cintura S2 | desde home medido, el ready vendor fue aceptado pero falló porque enviaba dos valores a la cintura S2 de un eje; el paralelo abortó cabeza/brazos y dejó sólo un avance parcial quieto. Sin fuerza/colisión/fault, una vuelta única `cruzr/home` terminó `SUCCEED/status=4` y home quedó medido. Se aplicó después sólo el overlay `joint_angles="0.0"`, hash `c767f739…a9b2`, con backup `20260903T133300_E6.0P`; sin reload, VLA, publicador ni movimiento. Reintento supervisado pendiente |
| 2026-09-03 | E6.0 preflight tras liberar E-stop | topics `0/0`, cargador fuera, pero estado articular/action server ausentes. Log: `JoystickMode/Ready→WaitStartMotion` al accionar el principal y luego `onEstopState=0`, sin `ButtonStartMotion`; no hay evento servo E-stop activo. Bloqueo atribuido a rearme pendiente, no al paro de chasis. Cero goals/movimiento; auditor corregido para reportar el fallo |
| 2026-09-03 | E6.0-CHECK consume N/O | run vigente `20260903T125333_E6.0-CHECK`: verifica recovery instalado, registrado y con proceso posterior a la configuración bajo E-stop. Mantiene 3 gates: validación física del recovery, transporte/STOP físico y aceleración aceptada; no autoriza movimiento |
| 2026-09-03 | E6.0O recarga mínima del task manager | run `20260903T124843_E6.0O`: reinició sólo `walker-motion.manipulation_robot_app-1` bajo E-stop principal, sin llamar tareas. Proceso posterior al task list; configuración/hashes exactos, E-stop antes/después, cargador fuera, VLA detenido y cero publicadores/movimiento. `SERVO_ESTOP_KEY=0`; registro action y trayectoria aún requieren validación supervisada |
| 2026-09-03 | E6.0N recovery exacto instalado sólo en disco | run `20260903T123940_E6.0N`: tras confirmar `ESTOP_KEY=1`, cargador fuera, VLA detenido y cero publicadores, respaldó en `/home/walker/cruzr-vla/backups/20260903T123940_E6.0N`, añadió una sola entrada y los XML/YAML hash-matched; task list `e4ac5e43…4def7`→`0d24122c…64957`. Check posterior `installed-on-disk-not-reloaded`; 9/9 artefactos verifican. Sin recarga, reinicio, VLA, publicador ni movimiento; runtime y validación supervisada pendientes |
| 2026-09-03 | E-stop principal reconciliado para E6.0N | run `20260903T123632_E6.0G`: `ESTOP_KEY=1`, `SERVO_ESTOP_KEY=0`, cargador fuera, VLA `exited/exited`, `publishers:0`; estado articular/action server ausentes por el paro activo. El segundo paro declarado no quedó corroborado por software |
| 2026-09-03 | E6.0K envolvente observada de clamp | run `20260903T121338_E6.0K`: cuatro fotos con cinta dan aproximadamente `120×52×105 mm`; con 10 mm por cara se usa `140×72×125 mm`. El volumen queda contenido en E6.0J para ambos lados bajo simetría, por lo que hereda su barrido mayor de 1.201 estados. Fotos no versionadas, sin CAD/carga/fuerza certificados; cero red/ROS/estado/publicador/movimiento |
| 2026-09-03 | E6.0L núcleo temporal de un punto | run `20260903T122501_E6.0L`: 30 casos de estado/fallo y 6 tamper pasan; consume sólo punto 0 una vez, sin replay ni `end_flag`. Cero ROS/red/publicador/movimiento; transporte físico y STOP físico ausentes por diseño |
| 2026-09-03 | E6.0M bundle ready/recovery local | run `20260903T122502_E6.0M`: valida `home→staging→A→B→A→staging→home` y la inversión exacta del segmento nombrado. Modos activos bloqueados antes del robot; no instalado ni validado físicamente |
| 2026-09-03 | Preparación física E6.0 bloqueada por discrepancia de E-stop | confirmación textual decía E-stop principal accionado; auditor vivo y preflight canónico leyeron `ESTOPS=0,0`, actuadores habilitados, acciones listas, cargador fuera y baterías 67,1/70,1 %. No se instaló, recargó ni movió |
| 2026-09-03 | E6.0-CHECK incorpora contrato temporal | run vigente `20260903T123041_E6.0-CHECK`: consume E6.0L/M; quedan 3 gates —recovery física, transporte/STOP físico y aceleración certificada— y no autoriza movimiento |
| 2026-09-03 | E6.0-CHECK incorpora medida observada | run histórico `20260903T121415_E6.0-CHECK`: consumió E6.0K además de E6.0J y mantuvo 4 gates antes del contrato temporal E6.0L; no autorizó movimiento |
| 2026-09-03 | E6.0J proxy documental conservador de clamps | run vigente `20260903T120626_E6.0J`: por decisión del propietario se usó la unión PGC completa del URDF vendor y se dilató 25 mm por cara según la carrera documentada de 50 mm; proxy por extremo `0,145×0,142×0,330 m`. En 1.201 estados del recorrido completo, paso máximo `0,0092978 rad`, no hubo pares OBB externos ni intersecciones exactas. Sólo se permiten contactos de la cadena propia `sixforce/wrist_roll/wrist_pitch`. Supuesto aceptado para canary sin caja, no CAD/certificación física; cero red/ROS/estado/publicador/movimiento |
| 2026-09-03 | E6.0-CHECK actualizado con supuesto geométrico | run histórico `20260903T120716_E6.0-CHECK`: consumió E6.0J y marcó autocolisión como `PASS_WITH_DOCUMENT_PROXY_ASSUMPTION`. Dejó 4 gates antes de E6.0L/M. Local, sin red/ROS/publicador; E6.0 físico no autorizado |
| 2026-09-03 | E6.0H instalación ready sólo en disco | run `20260903T104552_E6.0H`: con E-stop principal activo se respaldó `task_list.yaml`, se instaló atómicamente el XML vendor `f4025124…d8323` y una sola entrada; hash task list `c03ea6a…21a44`→`e4ac5e43…4def7`. Backup `/home/walker/cruzr-vla/backups/20260903T104552_E6.0H`. Sin recarga/reinicio, VLA detenido, cero publicadores y cero movimiento; registro runtime pendiente |
| 2026-09-03 | E6.0G preflight vivo de sólo lectura | runs iniciales `20260903T104309`/`105539`: E-stop 1/0 y luego `WaitStartMotion`. Tras el ciclo completo supervisado, run vigente `20260903T113216_E6.0G`: `rosa action info` demuestra un servidor, ready cargado porque Motion arrancó después del task list, preflight canónico aprobado, articulaciones inmóviles, paros 0/0, cargador fuera, VLA detenido y cero publicadores. Sin movimiento ni autorización física |
| 2026-09-03 | E6.0F cierre offline y escenario físico | run `20260903T102931_E6.0F`: 6/6 componentes locales inventariados; no queda acción exclusivamente local sin nueva entrada física/certificada. Preview no aplicado del XML/entrada ready y rollback; loader vendor marcado destructivo/interactivo. Primer escenario `NO_BOX_READY_EMPTY_CELL`, sin fixture y no autorizado. Cero red/ROS/estado/publicador/movimiento |
| 2026-09-03 | E6.0E guard de un punto | run autoritativo `20260903T102652_E6.0E`: 35 mensajes + 7 tamper de contrato, 42/42 expectativas, 2 previews válidos, cero autorizaciones y publicadores. Guard local/in-memory; rechaza toda solicitud física. Run `102636` descartado por estructura de copia de evidencia, sin campaña ni acceso externo |
| 2026-09-03 | E6.0D holgura vendor y contrato de guards | run `20260903T101730_E6.0D`: distancia exacta en 401 estados, mínimo global muestreado `0,016377700 m` hombro derecho/torso en muestra 100; 4 tests dirigidos y 300 aleatorios contra referencia escalar. Contrato de un punto sólo como especificación fail-closed, sin topic/publicador, con aceleración/fuerza/margen físico nulos. No certifica continuidad, clamp ni tolerancias. Cero red/ROS/estado/publicador/movimiento |
| 2026-09-03 | E6.0C narrow phase de pares cercanos P14 | run autoritativo `20260903T095600_E6.0C`: los 58 pares E6.0B se dividieron en 40 directos, 12 estáticos fuera de P14, 2 PGC no instalados y 4 móviles upstream. BVH de STL descartó todos los pares de triángulos por AABB sobre 401 estados (cero intersecciones); 4 self-tests validaron el SAT coplanar/3D. Faltan clamp real, holgura/tolerancias, política runtime revisada y validación física; gate cerrado. Cero red/ROS/estado/publicador/movimiento |
| 2026-09-03 | E6.0B broad phase de autocolisión P14 | run `20260903T094547_E6.0B`: 401 estados `preposición→A→B→A→preposición`, 46 links vendor, cero violaciones URDF y cero solapes OBB entre links con distancia cinemática >3. Los 58 pares cercanos quedan sin clasificar por ausencia de SRDF/ACM; PGC no representa las abrazaderas pasivas. Estado parcial, gate físico cerrado. Cero red/ROS/estado/publicador/movimiento |
| 2026-09-03 | E6.0A contrato ready/recovery P14 | run autoritativo `20260903T093145_E6.0A`: task0/frame0 demuestra orden directo de muñecas (`0,002112805 rad`) y rechaza el swap E4.0 (`0,614627484 rad`); ready B queda dentro del soporte. P14 usa 14 valores y hold fresco H/L/W. Recovery exacto de brazos `B→A→preposición` derivado pero no validado físicamente/colisiones; `back` vendor no es inverso. Run `092935` descartado por el mapping antiguo. Cero red/ROS/estado/publicador/movimiento |
| 2026-09-03 | E6.0I entrada/salida home del ready | run vigente `20260903T115129_E6.0I`: snapshot fresco 20D home, 101 muestras de `home↔preposición` y cobertura compuesta de 601 estados. Un nuevo OBB hombro derecho/torso se resolvió por malla exacta; cero intersecciones, mínimo vendor `0,011169662 m`. Sin publicador/movimiento; falta geometría clamp, tolerancias, dinámica y validación física. Run `114811` es fail-safe superado por no haber probado aún ese quinto par |
| 2026-09-03 | E6.0-CHECK auditoría inicial de preparación del canary | run `20260903T115457_E6.0-CHECK`, superado por `120716`: consumió E6.0G/H/I y dejó 5 gates antes de adoptar el proxy documental E6.0J. Local, sin red/ROS/publicador; no autorizó movimiento |
| 2026-09-03 | recuperación de E-stop y guard de arranque | shutdown lógico aceptado y apagado completo confirmado; el arranque con E-stop pasó `WaitEStopRelease→SelfChecking→JoystickMode`, self-check y `StartMotion` exitosos. Se corrigió el guard para aceptar `WaitEStopRelease` sin reiniciar/mover; instalado en Vision hash `6c3cbe48…9287b`, backup `/home/walker/cruzr-v020-boot-guard-backups/20260903T113735`. `--check`: versión v0.2.0, estado JoystickMode, x86 3/3, cámaras 2/2, seguridad 0/0/0, `movement=none restart=none` |
| 2026-09-03 | gate home compatible con IDs v0.2.0 | `/mc/actuator_state` usa elevador/cintura `11004/11003/11002/11001`, no los IDs históricos `2001/2002/2003/3001`. El parser acepta ambos esquemas y rechaza duplicados. Self-test completo pasó; `cruzr_recover_to_home.sh --check` vivo midió 20 ejes, cuerpo ≤0,002684 rad, brazos ≤0,000959 rad, velocidad 0 y delta ≤0,002684 rad; `MEASURED_HOME=1`, cero objetivos |
| 2026-09-03 | E5.2 selección preliminar de perfil | run `20260903T091901_E5.2`: regla de menor dimensión dentro de `max(0,0001 rad,1 %)` del mejor MAE elegible selecciona P14 para tasks 0–3. H sin mejora material, W empeora ~`6,88e-6…1,16e-5 rad`, L empeora ~`7,83e-4…3,48e-3 rad` y presenta 12/80 rechazos. Cero red/ROS/estado vivo/publicador/movimiento. No autoriza E6.0; el desglose vigente de gates está en E6.0-CHECK |
| 2026-09-03 | E5.1 matriz shadow-replay por perfil | run `20260903T091319_E5.1`: 20 inferencias C0 E3.0 verificadas se enmascararon bajo 8 perfiles para 160 bundles comparables. 148 ACCEPT, 12 REJECT_SAFE y 160/160 máscaras; los 12 rechazos sólo habilitan L (task1/seed2 velocidad lifter3; task2/seed0 y task3/seed0 rango lifter1). Perfiles sin L: 80/80 aceptados. Sin red/ROS/estado vivo/publicador/movimiento; sólo libera E5.2 offline |
| 2026-09-03 | E5.0 matriz completa del sink | run `20260903T090355_E5.0`: 8 perfiles × `low/middle`, 16/16 celdas PASS, 544 casos; 32 válidos aceptados, 512 inválidos rechazados y 16/16 probes de máscara/hold. Corregido el falso `axis_profile_mismatch` de P14. Todo local, sin ROS/red/estado/publicador/movimiento. VLA-5 queda completo sólo offline; libera E5.1 shadow, no ejecución física |
| 2026-09-03 | E4.1F auditoría de geometría oficial | run `20260903T085912_E4.1F`: manual SDK/producto, USD/URDF, XML ready y dataset validados por hash. Oficial: B0 `0,60×0,40×0,22 m`, plataforma 1 m, carga global bimanual 15 kg y PGC `0,1385×0,075×0,075 m`/50 mm; PGC corresponde a `cruzr_s2_v1_gripper` y se excluye. Para las placas pasivas `cruzr_s2_v1` sólo se enumera la familia clamp: no hay envolvente/TCP/masa/CoG/CAD oficial. Cero mediciones manuales, red al robot, inferencia, publicadores o movimiento. Fixture físico bloqueado; E5.0 offline autorizado |
| 2026-09-03 | E4.1E diseño offline de fixture corregido | run `20260903T093443_E4.1E`: 401 estados, tres planos y margen XY de 55 mm. Manteniendo B0+50 mm fijo, 128.386 colocaciones sólidas alineadas resultaron compatibles con apoyo y cero con colisión; la referencia global `+76,5°`/`0,856 m` fue rechazada. Se derivaron muescas upstream izquierda `[-0,720,-0,470]×[0,000,0,200] m` y derecha `[0,400,0,650]×[0,000,0,170] m`, sin solape con apoyo. Faltan abrazaderas reales, estructura, entrada y recovery; no autoriza fabricar ni mover. Cero red al robot, inferencia, publicadores o movimiento |
| 2026-09-03 | E4.1D identidad de efector y dependencia de colisión corregida | run `20260903T093440_E4.1D`: el SDK asigna PGC-140-50 a `HW_TYPE=cruzr_s2_v1_gripper`, distinto de las abrazaderas pasivas `cruzr_s2_v1` instaladas. Sin CAD/cotas no se validó equivalencia geométrica. Los 32 cruces E4.1C se separaron en 10 `pgc/finger` y 22 muñeca/sensor de fuerza; el tablero sólido sigue rechazado al excluir PGC. El intento `093412` se descarta por conteos hardcoded obsoletos; el wrapper ya valida la partición dinámica. Cero red al robot, inferencia, publicadores o movimiento |
| 2026-09-03 | E4.1C barrido offline corregido del fixture | run autoritativo `20260903T093408_E4.1C`: 121 estados, 46 geometrías URDF, 60 candidatos AABB y 32 intersecciones triángulo/plano contra el tablero en doce links. B0 tuvo cero candidatos y no se colocó. El run `20260901T090235_E4.1C` queda descartado por el mapping de muñecas anterior. Estado `SOLID_TABLETOP_CANDIDATE_REJECTED_BY_VENDOR_URDF_SWEEP`; todo local, cero red al robot, inferencia, publicadores o movimiento |
| 2026-09-01 | E4.1 calibración métrica del fixture | run válido `20260901T084855_E4.1`: CameraInfo/TF vivos, 20 posiciones tag 113 y borde posterior B0 del episodio 90. Reconstrucción `0,603128627 m` frente a `0,603 m`; `platform_in_base=(0,261844987,-0,027738106,0,870000000,0,0,-1,545870035)`, incertidumbre ±16,84/13,30/10,00 mm y ±0,868°. `D_BUMPER_PLATFORM=-0,092859226 m` revela solape de proyecciones; no se colocó la mesa ni hubo inferencia/publicador/movimiento. Estado `METRIC_FIXTURE_CANDIDATE_RESOLVED_PHYSICAL_GATES_OPEN`; siguiente: geometría de mesa, colisiones/swept volume y recovery E4.0, sólo offline/lectura |
| 2026-09-01 | E4.2 familias de altura low/middle offline | run `20260901T081210_E4.2`: 500 episodios + XML no-S2 55/70/85/100/115 + FK URDF S2. Tasks 0/1 correlacionan con 55/70/85 y tasks 2/3 con 100/115, pero quedan 84/95/49/58 episodios sin perfil a 0,05 rad. Pares task 0/2 y 1/3 comparten lifter a 0,000124356/0,000206182 rad: no existe altura escalar deducible ni `platform_in_base`. Episodios 90/91 sólo correlacionan tasks 2/3 con 1 m/perfil 100 no-S2. Estado `PARTIAL_HEIGHT_FAMILIES_RESOLVED_SINGLE_HEIGHT_MAPPING_REJECTED`; 10 frames y hashes válidos, sin red al robot, inferencia, publicadores o movimiento. Siguiente: aclaración UBTECH o calibración métrica offline |
| 2026-09-01 | E4.0 resolución read-only de VLA-ready | run final corregido `20260901T075728_E4.0`: forward `7722b734…7f6` 2×14/2,5 s y back `ee39039c…389` 2×14/5 s; back no invierte la secuencia. Se corrigió el orden MetaMove→checkpoint del candidato 20D y se resolvió cintura como `waist_yaw=0`. El task no está instalado/registrado ni en el upgrade v0.2.0; lifter queda heredado y 500 episodios demuestran múltiples configuraciones. Faltan límites runtime/swept volume/recovery. Resultado `PARTIAL_RESOLUTION_BLOCKED_NOT_READY_FOR_E4_1_OR_PHYSICAL_USE`; `exited/exited/publishers:0`, sin estado ni movimiento. Siguiente: E4.2 offline |
| 2026-08-28 | E3.3 contrato temporal offline | run `20260828T124011_E3.3`: 22/22 casos locales pasan y cancel/STOP/fault purgan sin replay ni publicador. Auditoría estática: chunk 10×20 a 80 ms/horizonte 0,72 s, inferencia 0,2 Hz; `continuous_end_chunk_num=5` sólo está en YAML, mientras Vision termina con un único `flag_pred>0,1`; ejecutores suministrados discrepan entre 900/9 s (`src`) y 600/6 s (`install`). `exited/exited/publishers:0`, sin estado ni movimiento. Estado `PASS_LOCAL_TEMPORAL_FAIL_CLOSED_VENDOR_SEMANTICS_UNRESOLVED`; VLA-3 y ejecución física siguen bloqueados, sólo E4.0 read-only queda autorizado |
| 2026-08-28 | E3.2 fault injection contra sink local | run `20260828T121832_E3.2`: 2/2 chunks de control aceptados y 32/32 inválidos rechazados; cubre identidad, esquema/orden/dimensión, NaN/Inf, frescura, timeline, rango/salto/velocidad, IDs, cancel/STOP/deadman y doble cliente. AST sin ROS/red/publicador/topic físico; `exited/exited/publishers:0` antes/después, sin estado ni movimiento. Ocho máscaras tienen tests unitarios, pero sólo P20/low ejecutó la suite completa; aceleración no tiene límite certificado. Estado `PASS_LOCAL_SINK_ALL_INVALID_REJECTED`; sólo libera E3.3 offline |
| 2026-08-28 | E3.1 OOD visual offline | run válido `20260828T120228_E3.1`: 26 proxies de imagen sobre tasks 0/2, 26 `ACCEPT_STRUCTURAL`, nominales exactos y máximos cambios de chunk 0,040258/0,053590 rad bajo zoom. Checkpoint sin cambios; `exited/exited/publishers:0`, sin ROS, estado o movimiento del robot. La parrilla métrica sigue bloqueada por falta de RGB-D, calibración, segmentación/pose y geometría de repisa; sólo queda liberado E3.2 con sink offline. El intento `20260828T115905_E3.1` falló seguro tras una muestra por consumo de stdin de `ssh`; wrapper corregido y regresión cubierta por ejecución completa |
| 2026-08-28 | E2.3 piloto reducido de repetibilidad P20 | se ejecutaron dos runs independientes task 0 y dos task 2, con STOP entre ellos. Task 0: 4 chunks, todos rechazados por 7 discontinuidades, duración 10,006055–10,039981 s y máximo `R_shoulder_yaw_joint` 1,361919–1,367893 rad. Task 2: 4 chunks, todos rechazados por 7 discontinuidades, duración 10,005578–10,006689 s y máximo 1,372170–1,379845 rad en el mismo eje. Ambos manifests validan; cada run y los finales quedaron `exited/exited`, `publishers:0`, sin movimiento. Estado `PASS_PILOT_2X2_SHADOW_ONLY`: rechazo/runtime reproducibles, no éxito de PICK |
| 2026-08-28 | E1.0/E1.3 reducidos y E2.1 task 2 completado en shadow | por decisión del propietario, E1.0 cerró con medidas `1,80 × 0,80 × 1,00 m`, cuatro esquinas a 1 m, rigidez/estabilidad y separación >1,5 m; fotos/marcas se difieren a E4. E1.3 reutiliza B0 `0,603 × 0,397 × 0,217 m` y difiere masa/colocación a E4/E6, sólo para liberar shadow. E2.1 `20260828T105547_E2.1` produjo dos chunks task 2 en 10,065 s; ambos fueron rechazados por siete saltos iniciales, máximo `R_shoulder_yaw_joint=1,376502 rad` frente a 0,35. Inferencia/control terminaron `exited`, publicadores `0`, hashes válidos y ningún movimiento. Estado `PASS_SHADOW_SAFETY_ONLY`, no PICK validado |
| 2026-08-28 | reanudación VLA en E1.0 con robot encendido | el propietario informó `home`; el diagnóstico fresco confirmó Motion/Vision accesibles, `HW_TYPE=cruzr_s2_v1`, baterías 70,0/77,7 %, paros 0/0, cargador fuera, acciones listas y máquina de tareas libre. El gate de home no certificó los 20 ejes porque faltaron `2001/2002/2003/3001`, por lo que no se autorizó movimiento. VLA permaneció `exited/exited` con `publishers:0`. Se abrió `Humanoide-vla-evidence/20260828T104622_E1.0/actual_result.yaml`; E1.0 queda pendiente de cuatro alturas, ancho/fondo, estabilidad y fotografías reales de `MESA_T1` a más de 1,5 m del robot |
| 2026-08-28 | return-to-home condicionado por muestra 20D y estado | `cruzr_recover_to_home.sh` pasa a `--check` por omisión, exige 20 ejes presentes, error cero, Operation Enabled, velocidad ≤0,02 rad/s, delta consigna ≤0,01 rad y usa `<0,02 rad` para declarar home sin enviar goals. Un inicio de tarea home ya no prueba éxito. Posturas PICO/unknown/caja posiblemente sujeta/intento no confirmado y eventos posteriores de fuerza, autocolisión, `MoveToGoalFailed`, fault o SAFEOP quedan bloqueados. La primitiva vendor sólo puede ejecutarse internamente desde estados reconocidos del ciclo de caja, con gates antes/después; `cycle.sh --home` delega al recovery, `--force-held-home` se retiró y `--fast` no omite auditorías. `--self-test`, `bash -n`, compilación Python y diff aprobaron localmente con el robot apagado; ruta física revisada pendiente de validación controlada |
| 2026-08-28 | `open_arm_before_home` falla desde postura PICO cruzada; apagado controlado completado | el goal `54f7beb2…` inició ambos brazos, cintura y elevador en paralelo. El FT izquierdo llegó a `Force-X=-370,944 N`; el brazo izquierdo no alcanzó el objetivo y el elevador abortó, terminando `MoveToGoalFailed`/`7104050`/`status=6`. El final previo de PICO ya mostraba autocolisión torso–codo/muñeca izquierda a 17–25 mm. Después 4004/4003/4002 registraron `0x1003` y `0x123f`; `hw`/manipulation reiniciaron y quedaron sin publisher de actuadores ni servidor de acción. Con confirmación física completa y paro mantenido, `/emb/pm_shutdown` respondió `success=True`; Motion/Vision cayeron, pantalla/luces se confirmaron apagadas, y sólo entonces se pulsó `KEY1` y apagó el chasis. Indicador verde apagado, robot/brazos estables. Se descarta esa tarea como home universal desde postura PICO; faults/consignas pendientes de redescubrir antes de cualquier movimiento |
| 2026-08-28 | corregido aborto de `--prepare-full` antes del rollback | el primer intento superó el preflight Motion, pero la asignación de entorno `BACKEND_LOG=…` chocó con la constante shell de sólo lectura y dejó a Python sin ruta. Se cambió únicamente el nombre exportado a `BACKEND_LOG_PATH`. `bash -n` y `git diff --check` aprobaron; el mismo parser pasivo obtuvo `operation_type=1` y `--check-arms-only` confirmó hash `4e8d79a4…`, `clamp/waist=0/leg=0`. El perfil full no fue restaurado, no se recargó modo, no hubo START ni movimiento |
| 2026-08-28 | lanzador PICO full-body separado, aún no activado | se creó `probar_pico_full.sh` sin modificar `probar_pico.sh`. El nuevo flujo exige el YAML vendor exacto y la tarea viva `clamp/waist=1/leg=2`, separa restauración, recarga y START, requiere Wi-Fi sin Ethernet sujeto y conserva preflight/Y/STOP. Añade monitor de log Motion y aborta ante IK, fuerza, EtherCAT, pérdida del monitor o click que conmute protección. El gestor de perfil comprueba STOP mediante log pasivo, sin abrir el WebSocket que podía autoarrancar 4.7.0. Sintaxis, ayudas, diff y bloqueos no-TTY aprobados; `shellcheck` no disponible. Checks reales: full rechazó el hash arms-only activo y el original confirmó `clamp/0/0`. No se cambió configuración robot/PC, no se recargó TeleopMode y no hubo movimiento; el baseline sigue arms-only |
| 2026-08-28 | disciplina de evidencia VLA endurecida para todos los ejercicios | se añadió un creador exclusivo de runs que rechaza raíz/rutas existentes, wrapper completo E1.1, protección de no sobrescritura y hashes relativos en E1.2, y wrapper E2.3 con sub-runs/STOP independientes. E2.0/E2.1 usan el mismo creador. Todos los bloques actuales/futuros del plan que escriben evidencia inicializan su ruta localmente; se eliminaron dependencias de `$VLA_RUN_ID`/`$VLA_EVIDENCE_ROOT` heredadas. Validación local solamente: no se inició inferencia, no se cambió el robot y no hubo movimiento |
| 2026-08-28 | E2.0 task 0 ejecutado fuera de secuencia y recuperado | el bloque manual sí ejecutó check, inferencia shadow y STOP, pero `$VLA_RUN_DIR` estaba vacío y todos los `tee` fallaron contra `/`. La evidencia persistente se recuperó en modo read-only desde los contenedores detenidos: dos chunks, ambos rechazados por `first_point_delta_violations:7`, máximo `R_shoulder_yaw_joint=1,339886 rad` frente a 0,35; duración real `10,063076 s` ante 8 s solicitados. Estado final verificado: inferencia/control `exited`, publicadores `0`, ningún movimiento. Se añadieron `--export-evidence` y `run_vla_shadow_smoke.sh` para evidencia autocontenida y STOP en fallo. Clasificación `PASS_SHADOW_SAFETY_ONLY`; escena/postura no documentadas y E1.0/E1.3 pendientes, por lo que E2.1 no está autorizado |
| 2026-08-27 | referencia visual del dataset VLA identificada | se validó en `/tmp`, sin alterar el dataset, el muestreo automatizado de 12 frames —inicio/medio/final de episodios 0/1/90/91— mediante VLC. Muestran un tote rígido gris abierto de paredes altas y borde gris, con tiras/marcas negras estrechas en algunos frames y un pequeño elemento con lazo visible dentro. El seek puede elegir frames adyacentes entre runs, por lo que sus hashes son de integridad por run, no canónicos. El plan distingue `B0_SAFE` vacía de la referencia: cartón u otro tote es OOD aunque mida 60×40×22 cm. No hubo inferencia ni movimiento |
| 2026-08-27 | mesa candidata disponible para fixture VLA | el propietario declara disponible `MESA_T1`, nominalmente `1,85 × 0,80 × 1,00 m` (ancho × fondo × altura). Se registró como `PENDIENTE`: E1.0 debe medir tablero/cuatro esquinas y comprobar nivelación, rigidez, estabilidad, patas y travesaños. No determina la separación horizontal ni autoriza acercarla al robot |
| 2026-08-27 | inventario mínimo de superficies VLA definido | para tasks 0–3 se reutilizará `MESA_T1` a 1 m y sólo se considerará una plataforma regulable rígida después de que E4.2 resuelva las alturas low/middle; no se requieren compartimientos ni dos repisas simultáneas. `RECEPTOR_VOLCADO` y `MESA_DESTINO_VACIA` corresponden a la misión ampliada y quedan pendientes de nueva primitiva/dataset, no del checkpoint actual. No se adquirió ni movió mobiliario |
| 2026-08-27 | primer intento E1.1 técnicamente correcto pero sin evidencia | `install --check/--verify` y `shadow --check/--status/--stop` observaron hosts correctos, paquete S2/checkpoint, instalación deshabilitada, contenedores `exited`, cero publishers y sesión detenida. `VLA_RUN_DIR` estaba vacío y los cinco `tee` intentaron escribir bajo `/`, fallando por permisos; no quedaron logs. El plan inicializa/valida ahora el directorio y exige cinco logs no vacíos más hashes. Estado `INCOMPLETE_EVIDENCE_EMPTY_VLA_RUN_DIR`; repetir E1.1, sin inferencia ni movimiento |
| 2026-08-27 | E1.1 baseline PC/VLA aprobado con evidencia | run `20260827T141244_E1.1`: cinco logs no vacíos validados contra `logs.sha256`; Vision/Motion y paquete `codes-S2`/`checkpoint-40000`/abrazaderas correctos; instalación deshabilitada; inferencia/control `exited`; `verify_installation` exige `restart=no`; publicadores de movimiento `0`; STOP confirmado. Se creó `actual_result.yaml` con `PASS`. Sólo queda habilitado E1.2 de lectura; no hubo inferencia ni movimiento |
| 2026-08-27 | primer intento manual E1.2 sin directorio de evidencia | `VLA_RUN_DIR` había sido definido dentro del subshell E1.1 y dejó de existir al volver al prompt. Las redirecciones intentaron escribir tres ficheros bajo `/` y fueron rechazadas por permisos; fuentes y robot no cambiaron. Se añadió `audit_vla_experiment_e1_2.sh`, wrapper local de sólo lectura que crea/valida su directorio, comprueba XML/tasks, extrae 12 frames y deja revisión visual pendiente |
| 2026-08-27 | E1.2 auditoría local de artefactos aprobada | run `20260827T141837_E1.2`: XML S2 hash `f4025124…d8323`, preposiciones y llamada pendiente `clamp_s2_joints_trajectory`; catálogo exacto tasks 0–3; doce frames y hoja de contacto inspeccionados. Referencia: tote gris abierto de paredes altas/borde gris, tiras negras estrechas en algunos frames y pequeño elemento con lazo dentro, no cartón. Alturas low/middle, task ready instalado, trayectoria interna y pose horizontal siguen `UNRESOLVED`. Estado `PASS`, sin conexión al robot, inferencia ni movimiento |
| 2026-08-27 | repetición E1.2 del operador aprobada | run `20260827T142214_E1.2`: todos los ficheros validan contra sus hashes. Varios PNG difieren bit a bit del run anterior porque el seek temporal de VLC seleccionó frames adyacentes; la hoja de contacto revisada mantiene el mismo tote/escenario/semántica. El extractor documenta ahora que los hashes PNG prueban integridad por run, no identidad canónica. Estado `PASS`, sin conexión al robot ni inferencia |
| 2026-08-27 | corregida la interpretación geométrica del demo VLA | la sección 7.3 del SDK dice que B0 `60×40×22 cm` debe estar sobre una plataforma de **1 m de altura**; no dice que exista 1 m horizontal robot–plataforma. El plan retiró esa separación inventada y dejó `D_BUMPER_PLATFORM/platform_in_base=UNRESOLVED`. También separó las alturas 55/70/85/100/115 del árbol alternativo no-S2. Se localizó el XML S2 ready, hash `f4025124…d8323`, que aún depende de `clamp_s2_joints_trajectory`. E4 debe derivar pose horizontal/alturas con XML, FK, cámara y frames antes de movimiento. Sólo hubo lectura y documentación |
| 2026-08-27 | manual secuencial E1.0→E8.2 añadido al plan VLA | el inicio de `docs/plan_de_trabajo.md` define plataforma S2 a 1 m de altura fuera de la envolvente, pose de B0, tolerancias, orden literal de comandos, salida esperada, PASS/FAIL/BLOCKED, artefactos y formulario `actual_result.yaml`. E2 es smoke shadow OOD; E4 calcula la pose horizontal y el mapeo low/middle antes de manipular. Los experimentos físicos E4/E6/E7 continúan bloqueados; no se inició inferencia ni movimiento |
| 2026-08-27 | escenarios y runbook PC completos para validación VLA | se definieron en `docs/plan_de_trabajo.md` B0, plataforma S2 de 1 m, estados `NO_BOX/SUPPORTED/HELD`, manifiesto de evidencia y tarjetas `VLA-T00…T10`. Cada tarjeta especifica escenario, comandos o mensajes PC, PASS/FAIL, evidencia y recovery; se separan scripts existentes de herramientas aún por implementar. La revisión de `cruzr_blue_workbin_cycle.sh --help` fijó el lado de 600 mm paralelo a hombros. Es planificación documental: no se inició inferencia ni hubo movimiento; los canaries físicos siguen bloqueados por falta de ready/fixture, ejecutor y primitiva demostrados |
| 2026-08-27 | campaña VLA 14→20 priorizada | se amplió el inicio de `docs/plan_de_trabajo.md` con una campaña por gates para caracterizar exhaustivamente por grupos los 20 outputs del checkpoint: A=14 brazos, H=2 cabeza, L=3 elevador y W=1 cintura. Cubre ocho perfiles funcionales —incluidas dos combinaciones distintas de 17D—, los cuatro task IDs, 32 celdas shadow, postura baja/media, contrato temporal, end flag, OOD, ejecutor sink, canary sin caja, tareas físicas con caja vacía y decisión C0/C1/C2. Es planificación documental; no se inició VLA, no se creó publicador y no hubo movimiento |
| 2026-08-27 | plan de trabajo multialtura y multitamaño | se documentó en `docs/plan_de_trabajo.md` una misión por estados para recoger una caja a baja altura, transportarla, volcar contenido ligero en un receptor, devolverla erguida y depositarla vacía a otra altura. Incluye una caja manipulada por ensayo, perfiles de cajas/estaciones, variación OFAT de posición/orientación/altura, comparación de detector/tag/RGB-D, control determinista, replay, PICO y VLA, gates de captura 20D y recuperación por fase. Es planificación documental: no se enviaron comandos ni se autorizó movimiento |
| 2026-08-27 | arranque controlado después del trip FT restaura Motion sin mover | se encendió chasis, `KEY1` y botón trasero con el paro accionado; Control Center esperó `WaitEStopRelease`. Tras confirmación física se liberó y no hubo movimiento inesperado. La primera consulta `docker info` activó `docker.service` mediante `docker.socket`; se registró explícitamente y no envió comandos al robot. Motion inició `hw`/`manipulation_robot_app`, readiness x86 3/3 y cámaras 2/2; self-check global `passed=true` y `StartMotion` exitoso. Control Center quedó en `AutoTaskMode`. `cruzr_blue_workbin_cycle.sh --check` aprobó: actuadores Operation Enabled, errores/deltas/velocidades dentro de gates, paros 0/0, cargador fuera, baterías 51,5/63,4 % y acciones listas. `cruzr_recover_to_home.sh --check` repitió la salud pero bloqueó correctamente `home` porque el nuevo log no clasifica la postura. El boot guard terminó `failed` por `CONTROL_STATE=unknown`, aunque no ejecutó recuperación (`RECOVERY_ELIGIBLE=0`) y registró seguridad `0 0 0`; no invalida el preflight de Motion, pero debe corregirse para reconocer `AutoTaskMode` |
| 2026-08-27 | teleoperación interrumpida al sujetar una caja; protección FT, caída de Motion y apagado completo | el stream PICO/PC continuó a 90 Hz, Y/enable permaneció activo y el script sólo terminó al `Ctrl+C` del operador. Motion registró en la muñeca izquierda `Force-X=-305,6…-307,0 N` frente al umbral de 120 N, declaró `Excessive force` y detuvo la tarea a las 16:25:59. La causa física exacta —compresión de la caja/contacto externo o transitorio/bias FT— queda pendiente, pero **no fue apretar fuerte el grip del PICO**, que es un clutch booleano. Después se observaron servo 5003 `0x1001/0x2007`, saltos de consigna en ambos hombros y EtherCAT SAFEOP ERROR; los checks terminaron `exit 25` sin servidor de manipulación. Con caja retirada y robot estable, el propietario autorizó apagado completo. `/emb/pm_shutdown` respondió `success=True`; Control Center transitó `TeleopMode→WaitShutdownReady→Shutdown→Term`. Motion y Vision dejaron de responder, el operador confirmó pantalla/luces apagadas, pulsó después `KEY1` y finalmente apagó el chasis; indicador verde apagado y robot estable. No se ha arrancado ni demostrado recuperación |
| 2026-08-27 | carrera de auto-START de WebSocket 4.7.0 eliminada del preflight | el intento 10:12 encontró `operation_type=2` antes de la confirmación. Los logs demuestran que las consultas locales breves de las 10:12:28.592 y 10:12:48.961 coincidieron con `Broadcasting publisher states`; 4.7.0 ejecutó `device detected online, starting remote operation` y arrancó el publisher sin un mensaje `collect operation_type=2`. El preflight detectó el segundo caso y su cleanup lo dejó en STOP a las 10:12:54.828. Se sustituyeron la espera, CHECK 7/7 y la verificación final por reconstrucción pasiva desde transiciones `Pico connect state` y eventos `Pico publisher start/stop`, limitada al arranque vigente del servicio. El WebSocket queda reservado para el cliente oficial después de la confirmación o un STOP de emergencia. `--check` real a las 10:17 abrió **0** clientes WebSocket y produjo **0** START; bloqueó únicamente por `vr_status=0`. Sintaxis, shellcheck y diff correctos; no hubo movimiento |
| 2026-08-27 | primer intento izquierdo tras habilitar bimanual: STOP por segundo Y | arms-only y preflight aprobaron; Y produjo `enable=1` a las 10:07:06.050. Al intentar mover el brazo izquierdo, el grip permanecía activo (`squeeze=1.0`) y XR publicó otro intervalo independiente `Left.b_button=true` desde 10:07:12.312; 5 ms después el backend vendor conmutó `enable=0`. El derecho siguió neutro, no hubo fallo IK y la velocidad articular final fue cero. El script identificó la deshabilitación y confirmó STOP. Es un segundo evento Y en la entrada XR, no una limitación bimanual ni un fallo del brazo. No se modificó software: en la siguiente prueba mantener ambos grips neutros hasta `ENABLE_OFICIAL_CONFIRMADO=1` y después mantener el pulgar izquierdo alejado de Y; no ocultar este STOP sin definir antes otra parada desde el visor |
| 2026-08-27 | control bimanual habilitado por el propietario | tras confirmar el operador que el torso permaneció quieto y verificar cero fallos IK en la sesión arms-only, `--teleoperate` permite por defecto ambos grips/brazos. El gate de `clamp,waist=0,leg=0`, enlaces, tracking, watchdog, STOP y demás seguridades permanece. Se registran `BIMANUAL_GRIPS_ACTIVE=1/0`; `PICO_ALLOW_BIMANUAL=0` ofrece rollback operativo inmediato al criterio de un brazo. Cambio de código sin START ni movimiento |
| 2026-08-27 | primer START con arms-only y STOP por solapamiento mínimo de grips | preflight aprobado y sesión oficial activa durante 29 s con Motion `clamp,waist=0,leg=0`. El guard local detectó ambos grips sólo entre 09:59:26.872 y .917 (~45 ms, cinco frames derechos) y solicitó STOP. En la ventana Motion hubo cero `CalcS2*…failed`; los dos mensajes `ik_restart_time_` eran estado, no fallo. Estado final: `operation_type=1`, UI/cámara paradas y velocidad articular cero. No se ha demostrado que el robot prohíba control bimanual; el bloqueo actual es intencionalmente conservador |
| 2026-08-27 | perfil arms-only recargado y demostrado sin movimiento | con preflight físico/lógico fresco se cambió Control Center `teleop→auto_task→teleop` usando el mismo RPC de la web. En el estado intermedio hubo cero acciones y velocidad articular máxima 0. El último arranque Motion y el gate canónico demuestran ahora hash `4e8d79a4…`, `hand=clamp,waist=0,leg=0`; preflight final: paros 0/0, baterías 58,0/69,0 %, cargador fuera, única acción PICO y joints inmóviles. PC quedó STOP, UI inactiva, sin `pico_control`; prueba física de un brazo pendiente |
| 2026-08-27 | causa de oscilación aislada y perfil PICO arms-only instalado | Motion confirmó que la tarea real era clamp, pero su configuración vendor activaba cintura y elevador (`waist_mode=1`, `leg_mode=2`) en CoreMode 7. Ambos grips estuvieron simultáneamente activos casi toda la sesión y los logs mostraron fallos IK repetidos de alcance, especialmente en el brazo derecho; ésa es la causa comprobada del movimiento compensatorio del torso. Se instaló sin reinicio ni movimiento un overlay reversible que cambia sólo ambos modos a cero (`4e8d79a4…`; vendor `5f08b30c…`). La tarea viva sigue con 1/2: `--check-arms-only` falla de forma esperada y `--teleoperate` no puede enviar START hasta recargar TeleopMode y demostrar `clamp,0,0`. También se añadió STOP si ambos grips quedan apretados |
| 2026-08-27 | movimiento pronunciado del torso con controller 4.7.0 | en una sesión oficial, `pico_control` solicitó `clamp`, el backend PC etiquetó `gripper`, ambos grips estuvieron activos casi continuamente y el operador observó oscilación grande del torso. STOP quedó confirmado (`operation_type=1`, `enable=0`). El diagnóstico posterior verificó Motion `clamp` con cintura/elevador 1/2 y fallos IK: véase la entrada arms-only precedente. En un hallazgo separado, ADB TCP 5555 cerró al retirar USB aunque XR/63901 siguió activo; el preflight bloqueó antes de START |
| 2026-08-27 | recuperación tras PICO, fault 4003 y consignas latentes | la recuperación normal bloqueó `unknown`; después apareció `L_shoulder_yaw_motor` 4003 en FAULT `0x1001/0x0238`. Una tarea temporal sólo para el brazo derecho fue aceptada pero terminó `MoveToGoalFailed/status=6`, sin cambiar posiciones; dejó consignas derechas latentes de hasta 0,1043 rad. El preflight impidió correctamente llamar al rearmado 4003. Se añadió un gate para error/status y `abs(cmd_pos-position)>0,01`. El operador hizo un apagado completo, retiró la caja y usó `KEY1`; los brazos descendieron sin trayectoria. En el arranque siguiente, el boot guard quedó `failed` por `CONTROL_STATE=unknown` mientras el paro estaba accionado, pero tras liberarlo Motion inicializó correctamente: todos los ejes quedaron sin fault, `0x1237`, inmóviles, con posición/consigna dentro de ±0,003 rad de cero. **Home articular alcanzado sin enviar una trayectoria adicional ni llamar al rearmado.** `KEY1` aislado sigue sin ser un procedimiento aprobado y no debe reutilizarse como recuperación |
| 2026-08-27 | auditoría local del contrato de datos 20D suministrado | **VERIFICADO** en metadatos/configuración: estado 32D = 20 posiciones + 12 fuerza/par, acción 20D y horizonte de 10 filas. **OBSERVADO** en episodios 000000/000088/000499: `action[t]` está casi alineada con las 20 posiciones simultáneas (MAE ≈`9e-5`–`1.1e-4` rad; un frame de desfase empeora ≈20x). Parquet y MP4 exportan una timeline de 120 Hz, H.264 `960x576`, con igual número de filas/frames en las muestras. **PENDIENTE UBTECH/DSA**: origen exacto de la acción previa al actuador, reloj maestro y cadencia física real. Se documentó una vía de recolector pasivo y piloto, sin declararla contrato oficial. Sólo lectura: no se cambió PC/robot ni hubo movimiento |
| 2026-08-26 | PICO migrado de USB a Wi-Fi Cruzr | con STOP confirmado se habilitó ADB TCP y se retiró USB. PICO quedó `192.168.42.212:5555`, PC robot-Wi-Fi `.215`; tras reiniciar sólo XRoboToolkit y reactivar Head + Controllers / Working, Unity conectó directamente a `.215:63901`, `vr_status=1` y `probar_pico.sh --check` pasó 7/7. Motion/Vision siguen por Ethernet y DSA conserva Internet. Un socket `.51` obsoleto siguió visible temporalmente en el kernel, pero el preflight seleccionó y demostró el flujo Wi-Fi `.212→.215` |
| 2026-08-26 | destino de cámara PICO corregido | la primera ejecución de `--teleoperate` abrió correctamente el stream Vision pero el relay esperaba el listener en la concesión histórica `.42.211`; el PICO actual era `.42.212`, por lo que no podía llegar el keyframe y no se envió START. Se eliminó la IP predeterminada fija: el lanzador y el script de cámara descubren ahora `wlan0` por el serial ADB y usan USB sólo como fallback. Validado `.42.212` por `wlx80afcad40bd6`; sin relay residual ni movimiento |
| 2026-08-26 | primer gate oficial 4.7.0 y nuevo `--teleoperate` | `pico_control --arm_type clamp` abrió P2P, Y izquierdo produjo `Left.b_button`/`enable=1` y el grip derecho llegó al backend. El cliente oficial confirmó STOP. Un rearme posterior fue causado por un segundo `wscat --wait 1`, no por el STOP oficial; ese patrón quedó prohibido. El propietario acepta temporalmente la selección interna `gripper` sólo para cinemática de brazos. Se añadió `probar_pico.sh --teleoperate`: preflight, cámara principal, neutralidad fresca, Y, ventana inicialmente de 120 s y elevada por el propietario a 300 s, monitor de enlaces/heartbeat y STOP. Sintaxis, diff y rechazo no-TTY/duración inválida verificados; la cancelación final quedó STOP y no movió. El resultado físico del primer grip sigue pendiente de confirmación del operador |
| 2026-08-26 | cable Ethernet sustituido y enlace directo restaurado | `eno1` pasó de 10 a 1000 Mb/s full con autonegociación; se activó el perfil persistente `cruzr-s2`/`192.168.11.250`, never-default, y Motion `.2`/Vision `.3` respondieron sin pérdida en 0,2–0,9 ms. La ruta a `.11.0/24` usa Ethernet, PICO/Wi-Fi Cruzr permanecen activos y la ruta por defecto/Internet sigue por `DSA CORPORATE`. `probar_pico.sh --check` reconoció Ethernet y llegó a CHECK 5/7; falló únicamente porque el PICO aún no transmite TCP 63901. Sin START ni movimiento |
| 2026-08-26 | migración solicitada por UBTECH a controller 4.7.0 para robot v0.2.0 | se respaldó 5.3.0 parcheado (`c085fc4b…`), verificó el DEB 4.7.0 (`4f2b728b…`), purgó 5.3.0 e instaló 4.7.0 conservando el servicio parado durante los scripts del proveedor. El binario instalado coincide con el DEB (`e88b83b7…`), UI 4.1.0 permanece inactiva y el backend está STOP (`operation_type=1`); 4.7.0 no expone `enable_control`, por lo que los scripts validan el baseline pero bloquean todo START hasta observar el Y/enable oficial. XRoboToolkit está abierto por ADB, aunque el visor aún no envía TCP 63901 (`vr_status=0`). No hubo movimiento. Ethernet `eno1` negoció 10 Mb/s pero no resolvió ARP hacia `.2/.3`; el perfil quedó inactivo y Wi-Fi Cruzr sigue llevando Motion/Vision, mientras DSA conserva Internet. En la reunión UBTECH afirmó que 4.7.0 sí recopila datos del robot, contradiciendo/precisando la etiqueta china `只支持遥操作`; formatos, modalidades y exportación continúan PENDIENTES |
| 2026-08-25 | cámara principal Cruzr integrada en XRoboToolkit | `cruzr_pico_camera.sh` abre mediante `/streaming/start` la estéreo izquierda de cabeza, mantiene el heartbeat exclusivo de vídeo, convierte SRS HTTP-FLV/AVCC a H.264 Annex-B con longitud TCP y lo envía al listener 12345 del PICO; las pruebas físicas esperan `PICO_CAMERA_LIVE_BEFORE_START=1`. Fuente real validada (64 frames/3 keyframes en muestra y 36 unidades contra PICO simulado), cierre sin streams ni heartbeat residuales. No hubo START ni movimiento; la visualización en el PICO real queda PENDIENTE porque `.42.211` está fuera de línea |
| 2026-08-25 | reset USB Wi-Fi durante gate PICO | a las 12:59:43 desapareció del kernel el Realtek `0bda:b812`/`wlx80afcad40bd6`; el trigger nunca llegó (758 muestras a cero), `vr_status` cayó y nunca hubo `enable=1`; STOP final, sin movimiento. USB autosuspend ya estaba desactivado, pero Wi-Fi powersave estaba activo y existían errores LPS/tx report. Se fijó `powersave=disable` sólo para `Cruzr S2-0669 1`, se reconectó con STOP, se verificó `Power save: off`, DSA intacta y `--check` 7/7. Los bucles armados abortan ahora inmediatamente ante pérdida de interfaz/carrier/IP/ruta o tracking |
| 2026-08-25 | falso positivo de neutralidad corregido | el intento de las 12:53 abortó antes de START al reutilizar las últimas muestras del log, que eran de las 12:31:26 con ambos grips altos. Ahora START queda aún con `enable=0`, se exigen estados nuevos de ambos mandos pertenecientes a esa ejecución, se valida neutralidad y sólo después aparece `TOQUE AHORA`; ausencia o entrada activa envía STOP. Sin movimiento; final STOP/UI inactiva |
| 2026-08-25 | fallo de gatillo de nivel y corrección a flanco | `--all-controls` habilitó con una sola pulsación, pero sus 0,567 s altos repitieron Y y causaron `enable 0→1→0`; STOP automático, sin trip de heartbeat. Backend cambiado a pulso sólo en flanco ascendente, con gates de mandos neutros/liberación; activo `5083e9f0…`, rollback de nivel/300 s `40b440f4…`. A las 12:44 `--check` recuperó PICO/stream y pasó 7/7; final `vr_status=1`, `operation_type=1`, `enable_control=0`, UI inactiva; E2E físico pendiente |
| 2026-08-25 | Wi-Fi Cruzr canónica para todos los dispositivos del robot; DSA sólo Internet | toda `.11.0/24` se enruta vía `.42.2` y `.42.0/24` es directa por `wlx80afcad40bd6`; perfil Cruzr `never-default`/sin DNS. Motion, Vision, PICO y servicios robot usan `Cruzr S2-0669`; sólo Internet usa `wlo1`. Scripts dejaron de exigir `eno1`; `--check-motion-ready` pasó sin START/movimiento |
| 2026-08-25 | `--all-controls` abortó antes de START por Ethernet caído | `eno1` quedó `NO-CARRIER`/sin `192.168.11.250`; Motion/Vision no eran accesibles y no se armó teleoperación. El preflight ahora recomprueba portadora, IP, ruta, ping y SSH justo antes de los gates físicos para fallar inmediatamente y con causa concreta; ambas Wi-Fi permanecieron conectadas |
| 2026-08-25 | ventana integral PICO autorizada, aún no ejecutada | `probar_pico.sh --all-controls` permite 120 s activos tras 60 s neutros (configurable 120–180 s), cubre controles documentados y siempre solicita STOP; resumen sólo acredita entradas, no efectos finales. Tras una caída WLAN quedaron dos sockets y `vr_status=0` pese a Working; reiniciar sólo XRoboToolkit y reseleccionar Head+Controllers/Send data recuperó el enlace. El `--check` final terminó 7/7 con `vr_status=1`, clamp/300 s y backend desarmado; no hubo START ni movimiento durante el cambio |
| 2026-08-25 | PICO por Wi-Fi local sin túnel XR | `DSA CORPORATE` se conservó en `wlo1`; adaptador secundario y PICO se asociaron a `Cruzr S2-0669` (`.215`/`.211`); XR abrió TCP directo 63901, reverse vacío, `--check` OK y backend STOP; ADB por Wi-Fi soportado por discovery de serial |
| 2026-08-25 | movimiento PICO y retorno a home | el brazo se movió; STOP desarmó el PC pero TeleopMode persistió hasta seleccionar `auto_task`; home directo terminó, aunque las abrazaderas bajas pasaron casi rozando. `--home` queda cambiado a la tarea oficial `cruzr/open_arm_before_home` (apertura previa); hash y preflight sin movimiento verificados, prueba física de la corrección pendiente |
| 2026-08-25 | modo físico real PICO autorizado | `probar_pico.sh` por defecto prueba sólo brazo derecho: preflight Motion+PC, estabilidad 60 s, grip exclusivo, gesto 2–3 cm/5 s máximo y STOP al soltar/fallar; XR restaurado a `vr_status=1`; en ese preflight aún no se había ejecutado START físico |
| 2026-08-25 | ventana PICO 300 s / gate sin maniobra | DataChannel abrió antes de enable; `CoreMode 7` y protección de fuerza activos ~46 s sin trip de 10 s; cero movimiento con ambos grips siempre libres; tres pulsaciones finales alternaron `0→1→0` y provocaron STOP seguro; a las 10:43 `vr_status=0` |
| 2026-08-25 | debug lanzador PICO | añadidos progreso 1/7, timestamps, timeouts de 5 s y traza opcional; flujo normal y fallo ADB simulado verificados; backend permaneció STOP |
| 2026-08-25 | reconexión XR | restaurado ADB reverse 63901 y reiniciada sólo la app; TCP y `vr_status=1`; backend activo pero STOP (`operation_type=1`, `enable_control=0`); `--check` completo OK |
| 2026-08-25 | timeout PICO 300 s | propietario autorizó 10→300 s; binario PC `40b440…` instalado con STOP conservado y backup `0f0d3414…`; backend/UI/XR quedaron detenidos; sin runtime ni movimiento |
| 2026-08-25 | gate PICO/conmutador | gatillo y `CoreMode 7` verificados; toque único correcto habilitó, pero el gate falló por heartbeat a los 10,576 s desde START; STOP dejó `operation_type=1`, `enable_control=0`; en el último intento no hubo movimiento y sí voz |
| 2026-08-10/11 | diagnóstico inicial BMS | se observó desequilibrio SOC y SN truncado; pendiente proveedor |
| 2026-08-14 | AprilTag mesa 2 | tag 113 y referencias empty/held calibrados |
| 2026-08-17 | manos v4 | detección y demos de fábrica; luego se restauraron abrazaderas |
| 2026-08-20/21 | upgrade v0.2.0 | sistema actualizado, mapa y `HW_TYPE` preservados |
| 2026-08-21 | boot guard | recuperación controlada del race Vision→Motion validada |
| 2026-08-21 | VLA shadow | inferencia funcional; chunks rechazados desde `home`; cero mando físico |
| 2026-08-21 | apagado | discrepancia manual/hardware/software documentada |
| 2026-08-24/25 | PICO | cadena hasta DataChannel validada; heartbeat sigue bloqueando sesión estable |
| 2026-08-25 | relevo global | `AGENTS.md` y esta fuente hacen el contexto descubrible automáticamente |
