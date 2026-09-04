# Integración segura del VLA suministrado para Cruzr S2

Para preparar el PICO 4 Ultra Enterprise, diseñar sesiones, capturar episodios
y decidir entre continuar este checkpoint o crear un nuevo perfil, consulte
[Cruzr S2 v0.2.0: teleoperación, captura de datos y evolución del VLA](../vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md).

## Estado verificado

El checkpoint GR00T N1.5 suministrado está instalado y puede cargarse sobre el
sistema v0.2.0. La inferencia se ha ejecutado de forma aislada y ha generado
chunks con la estructura esperada:

- 20 dimensiones en el orden oficial del perfil S2;
- 10 puntos por chunk;
- valores finitos y dentro de los rangos del checkpoint;
- cámara estéreo activa;
- estado de los 20 ejes recibido desde `/mc/whole_joint_states`;
- cero publicadores en `/mc/sdk/robot_command` durante toda la prueba.

La prueba shadow desde `home` generó dos chunks, pero ambos fueron rechazados
antes de cualquier ejecución física. El primer punto difería de la postura real
en ocho articulaciones de brazo, con diferencias máximas próximas a 1,35 rad.
Esto demuestra que el VLA no debe activarse directamente desde `home`.

Una segunda ejecución de task 0 el 2026-08-28, desde una postura y escena que
no se documentaron, produjo dos chunks adicionales. Ambos fueron rechazados por
siete violaciones del primer punto; la máxima fue
`R_shoulder_yaw_joint=1,339886 rad` con límite `0,35 rad`. La duración real fue
`10,063076 s` para un máximo solicitado de 8 s. Se mantuvieron cero
publicadores, STOP dejó ambos contenedores detenidos y no hubo movimiento. Este
run es `PASS_SHADOW_SAFETY_ONLY`, no evidencia de que task 0 pueda hacer PICK.

Al reanudar la campaña el 2026-08-28, el propietario informó que el robot ya
estaba encendido y en `home`. Un check fresco de sólo lectura confirmó
Motion/Vision, acciones listas, paros `0/0`, cargador desconectado y
`ACTUATORS_OPERATION_ENABLED=1`, pero el gate no pudo certificar la postura 20D
porque la muestra omitió los IDs `2001/2002/2003/3001`. No se envió movimiento.
VLA permaneció con ambos contenedores `exited` y cero publicadores. El siguiente
paso sigue siendo E1.0/E1.3 de medida física fuera de la envolvente; `home`
informado no autoriza repetir shadow desde una entrada nominal ni ejecutar VLA.

Para reducir carga operativa, el propietario cerró E1.0 con las medidas
`1,80 × 0,80 × 1,00 m`, cuatro esquinas a 1 m, rigidez/estabilidad y más de
1,5 m de separación; las fotos y marcas se difieren a E4. E1.3 conserva la
geometría medida de B0 `0,603 × 0,397 × 0,217 m` y difiere masa/colocación real
a E4/E6. Esta dispensa sólo libera shadow OOD. E2.1 task 2, run
`20260828T105547_E2.1`, generó dos chunks en `10,065012 s`; ambos fueron
rechazados por siete saltos del primer punto, máximo
`R_shoulder_yaw_joint=1,376502 rad` frente a `0,35 rad`. STOP dejó ambos
contenedores `exited`, publicadores `0` y hashes válidos. Es
`PASS_SHADOW_SAFETY_ONLY`, no evidencia de PICK medio ni autorización física.

E2.3 se redujo por decisión del propietario a un piloto 2+2. Task 0, run
`20260828T110217_E2.3-task0`, produjo cuatro chunks rechazados por las mismas
siete discontinuidades; duraciones `10,006055…10,039981 s` y máximo delta
`1,361919…1,367893 rad` en `R_shoulder_yaw_joint`. Task 2, run
`20260828T110617_E2.3-task2`, produjo otros cuatro rechazos equivalentes;
duraciones `10,005578…10,006689 s` y máximo `1,372170…1,379845 rad`. Cada
repetición confirmó STOP y los parents terminaron `exited/exited/publishers:0`;
ambos manifests validan. Es `PASS_PILOT_2X2_SHADOW_ONLY`: demuestra
repetibilidad del runtime/rechazo OOD, no capacidad de PICK ni seguridad para
publicación física.

E2.2 ya cubre los tasks PLACE 1 y 3 sin crear una postura HELD en el robot. El
run `20260828T112730_E2.2` cargó `checkpoint-40000` en un contenedor transitorio
con `--network none`, sin ROS ni mensajes de mando, y reprodujo frame 0 de los
episodios 465 y 265. Produjo dos chunks 10×20: MAE `0,007283609` para task 1 y
`0,011394879` para task 3, sin violaciones conservadoras de rango o primer
salto. El holdout es una partición local del último 15 % por task; no es un
split del proveedor y puede haber formado parte del entrenamiento. El resultado
es `PASS_OFFLINE_INFERENCE_ONLY`: valida el camino de inferencia, no PLACE
físico, generalización ni seguridad de ejecución. El cierre confirmó
`exited/exited/publishers:0` y cero acceso al estado del robot.

E3.0, run `20260828T114346_E3.0`, evaluó offline cinco episodios y fases por
cada task 0–3, con 20 muestras y 36 inferencias. Las MAE medias por task fueron
`0,004908891`, `0,006516288`, `0,009686776` y `0,008983554`; las cinco
ejecuciones seed 0 de cada task fueron idénticas. Dos baselines violaron el
rango de `lifter_pitch_1_joint`: task 2/episodio 270/frame 0 en un punto y
task 3/episodio 287/frame 0 en siete puntos, hasta `0,060465574` frente al
máximo `0,000336618`. Por ello el resultado es
`PASS_OFFLINE_CAMPAIGN_WITH_CONSERVATIVE_VIOLATIONS`, no candidato ejecutable.
El split local 424/76 no se solapa, pero no demuestra episodios inéditos para
C0. Hashes completos del checkpoint sin cambios y cierre
`exited/exited/publishers:0`; sólo queda autorizado continuar con E3.1 offline.

E3.1, run `20260828T120228_E3.1`, mantuvo el mismo aislamiento y evaluó 26
variantes de imagen sobre dos frames fijos de tasks 0/2. Las tres parrillas
fueron desplazamiento horizontal del frame, zoom global y perspectiva
trapezoidal global; **no** representan x, profundidad o yaw métrico de la caja.
Las 26 salidas fueron `ACCEPT_STRUCTURAL`, sin violaciones conservadoras, y los
nominales repetidos fueron exactos. El máximo cambio del chunk fue `0,040258`
rad para task 0 y `0,053590` rad para task 2, ambos bajo zoom. El checkpoint
conservó sus hashes y el cierre fue `exited/exited/publishers:0`. La prueba
métrica permanece bloqueada porque el dataset no contiene RGB-D, calibración,
máscara/pose 6D ni geometría de repisa. Sólo se autoriza E3.2 con sink offline;
no se habilita movimiento.

E3.2, run `20260828T121832_E3.2`, añadió un sink local puro y una fault suite
reproducible. Aceptó dos chunks de control y rechazó 32/32 inválidos, incluidos
NaN/Inf, orden/dimensión, estado/imagen/chunk obsoletos, rango, primer salto,
velocidad, timeline, IDs duplicados/regresivos, cancelación, STOP, deadman y
doble cliente. La auditoría AST encontró cero imports ROS/red, símbolos de
mando o llamadas de publisher/action. Los perfiles 14–20 tienen tests de
máscara y hold no nulo, pero el run certificado sólo cubre `P20_AHLW/low` con
pose sintética, no VLA-ready física. VLA permaneció
`exited/exited/publishers:0`; no hubo estado ni movimiento. Como el perfil no
incluye un límite certificado de aceleración, el gate de ejecutor físico no
está cerrado. Sólo se permite E3.3 offline.

E3.3, run `20260828T124011_E3.3`, ejecutó 22 casos en un scheduler Python
puramente local. Demostró para el contrato candidato: 10 puntos a 80 ms,
horizonte 0,72 s, cero replay en huecos, timeout inter-chunk a 0,5 s, purge
inmediato ante cancel/STOP/pérdida de imagen o estado, rechazo de overlap y
dispatch tardío, y fin sólo tras cinco flags consecutivos. El AST no contiene
ROS, red, publisher/action ni topic de mando; el VLA quedó
`exited/exited/publishers:0` antes/después y no se leyó ni movió el robot.

Ese PASS es sólo local. La fuente Vision suministrada infiere a 0,2 Hz y
termina con un único `flag_pred > 0,1`; el YAML declara cinco flags pero el
Python no lee el parámetro. El chunk declara 0,72 s, mientras las dos copias
del ejecutor suministrado interpolan a 9 s (`src`) y 6 s (`install`). Por ello
la semántica física continúa sin resolver, Gate VLA-3 permanece abierto y el
único siguiente paso permitido es E4.0 de inspección read-only.

E4.0, run final corregido `20260901T075728_E4.0`, resolvió pasivamente la primitiva instalada
`clamp_s2_joints_trajectory`: hash `7722b734…7f6`, dos goals 14D y
`1,5 + 1,0 s`. Su `back`, hash `ee39039c…389`, usa dos goals 14D y
`2,0 + 3,0 s`, pero no es la inversa exacta de la secuencia completa. El task
S2 suministrado `s2_bio_vla/s2_vla_pick_large_teleop_ready` no está instalado
ni registrado, tampoco aparece en el upgrade v0.2.0 entregado; los ready
existentes tienen otra semántica. La revisión v2 reordenó correctamente
hombro/codo, pero su intercambio de muñecas fue descartado por E6.0A: el orden
directo coincide con task 0/frame 0 a `0,002112805 rad`, frente a
`0,614627484 rad` con swap. También resolvió el segundo valor de
cintura como `waist_yaw=0`, porque el URDF S2 sólo tiene ese eje. El XML no
fija los tres lifter: los hereda, el ejecutor S2 descarta sus índices 16–18 y
los 500 episodios abarcan múltiples configuraciones. No hay límites runtime
explícitos, swept volume ni recovery completo. Estado
`PARTIAL_RESOLUTION_BLOCKED_NOT_READY_FOR_E4_1_OR_PHYSICAL_USE`; E4.2 offline
es el siguiente análisis permitido, nunca movimiento. El VLA terminó
`exited/exited/publishers:0`, sin estado ni movimiento.

E4.2, run `20260901T081210_E4.2`, se limitó a artefactos locales y rechazó la
premisa de una altura única por task. A `0,05 rad`, los perfiles nombrados
no-S2 que aparecen en tasks 0/1 son 55/70/85 y en tasks 2/3 son 100/115, con
muchos episodios sin perfil nombrado. Además, task 0/2 y task 1/3 contienen
pares de episodios con elevadores prácticamente iguales
(`0,000124356/0,000206182 rad`), por lo que ni los tres ángulos ni su FK
resuelven el nivel del estante o `platform_in_base`. Tasks 2/3, episodios
90/91, sólo quedan correlacionados offline con la plataforma SDK de 1 m/perfil
100; el XML 100 es no-S2 y no constituye calibración. Estado
`PARTIAL_HEIGHT_FAMILIES_RESOLVED_SINGLE_HEIGHT_MAPPING_REJECTED`; no hubo red
al robot, inferencia, publicador ni comando de movimiento. Siguen bloqueados
todos los gates físicos.

Por autorización posterior del propietario se ejecutó únicamente la parte
métrica de E4.1, sin terceros ni movimiento. El run válido
`20260901T084855_E4.1` capturó CameraInfo/TF, 20 posiciones estables del tag
113 y reconstruyó el borde de B0 del episodio 90. Los rayos
`(307,293)…(713,293)` producen `0,603128627 m` frente a `0,603 m`; la pose
candidata es `platform_in_base=(0,261844987,-0,027738106,0,870000000,
0,0,-1,545870035)`. `D_BUMPER_PLATFORM=-0,092859226 m` es firmado: revela
solape de proyecciones, no autorización para poner la mesa allí. La
incertidumbre es aproximadamente ±16,84/13,30/10,00 mm y ±0,868°. E4.1 queda
`METRIC_FIXTURE_CANDIDATE_RESOLVED_PHYSICAL_GATES_OPEN`; E4.0, colisiones,
swept volume y recovery mantienen todo movimiento bloqueado.

E4.1C cerró la primera comprobación de colisiones offline y se repitió con el
orden de muñecas corregido en `20260903T093408_E4.1C`. El analizador versionado
reconstruyó 121 muestras de
`preposition→forward→back`, con elevador del episodio 90, y transformó los
meshes URDF de 46 links al fixture E4.1. De 60 candidatos AABB, 32 se
confirmaron por intersección triángulo/plano contra la superficie de un tablero
sólido; afectan doce links de muñeca, sensor y efector. B0 quedó libre en la
criba AABB y no se colocó. Resultado
`SOLID_TABLETOP_CANDIDATE_REJECTED_BY_VENDOR_URDF_SWEEP`: no hacen falta aún
medidas de patas o espesor porque el plano superior de espesor cero ya falla.
El run `20260901T090235_E4.1C` queda descartado por el mapping anterior.
E4.1D cerró la duda de identidad, pero no la falta de CAD, en
`20260903T093440_E4.1D`: el SDK asocia PGC-140-50 con
`HW_TYPE=cruzr_s2_v1_gripper`; esta unidad lleva abrazaderas laterales pasivas
con `HW_TYPE=cruzr_s2_v1`. El mecanismo no es el mismo y no existen cotas/CAD
locales que validen `pgc/finger` como envolvente sustituta. La partición de
E4.1C atribuye 10 cruces a PGC/dedos y 22 a muñecas/sensores de fuerza. Estos
22 bastan para mantener rechazado el tablero sólido sin el efector PGC. Sólo
se autoriza diseñar offline huecos u otra pose. No se conectó al robot, no
hubo inferencia/publicador/movimiento y E4.3/E4.4 siguen bloqueados.

E4.1E ejecutó el siguiente cálculo permitido en
`20260903T093443_E4.1E`, también completamente local. Muestreó 401 estados,
seccionó muñecas/sensores en `z=-10/0/+10 mm` y aplicó 55 mm de margen XY.
Con B0 y su apoyo fijos, una búsqueda de tablero sólido en ±5° obtuvo 128.386
colocaciones con apoyo y cero libres de colisión. La referencia global a
`+76,5°`/`0,856 m` queda rechazada por salir de la alineación calibrada. Las
muescas frontales candidatas son izquierda
`[-0,720,-0,470]×[0,000,0,200] m` y derecha
`[0,400,0,650]×[0,000,0,170] m`. No invaden el apoyo de B0, pero omiten la
geometría de las abrazaderas reales, patas/espesor, entrada y recovery. No se
autoriza fabricar, acercar la mesa, colocar B0 ni mover. E4.1F agotó después
las especificaciones oficiales sin exigir medición manual.

E4.1F (`20260903T085912_E4.1F`) verificó por hash manual SDK/producto,
USD/URDF, XML ready y metadatos VLA. Las fuentes publican B0
`0,60×0,40×0,22 m`, plataforma `1,00 m`, carga bimanual global `15 kg` y PGC
`0,1385×0,075×0,075 m`/carrera `0,05 m`. La PGC requiere
`cruzr_s2_v1_gripper` y no representa las placas `cruzr_s2_v1`. Aunque el
manual enumera `clamp hands`, no publica envolvente, TCP, masa, CoG ni CAD; los
modelos contienen sólo PGC. No se infieren dimensiones ni se exige medirlas.
Los gates físicos siguen cerrados y sólo se libera E5.0 offline.

E5.0 completó ese gate local en `20260903T090355_E5.0`. Pasaron las 16
combinaciones de ocho perfiles por `low/middle`: 544 casos, 32 válidos
aceptados, 512 inválidos rechazados y 16 probes de máscara/hold. Los holds son
midpoints sintéticos, no estado articular vivo. El código auditado no usa ROS,
red, publicadores ni comandos físicos y el robot no fue consultado ni movido.
Por tanto se autoriza sólo E5.1 shadow; canary y ejecutor físico siguen
bloqueados por los gates de ready, fixture, recovery, aceleración y contrato
vendor.

E5.1 se ejecutó después como shadow-replay local, run
`20260903T091319_E5.1`. Las 20 inferencias C0 ya congeladas en E3.0 se
compararon bajo los ocho perfiles, sin repetir el modelo por una variable que
sólo existe en el ejecutor: 160 bundles, 148 aceptados, 12 rechazados de forma
segura y 160/160 máscaras correctas. Los 12 rechazos habilitan elevador y se
explican por límites de `lifter_pitch_1/3_joint`; los perfiles sin `L`
aceptaron 80/80. No hubo conexión ni estado vivo del robot. Se libera sólo
E5.2 offline; esta evidencia no autoriza mover ni seleccionar definitivamente
un perfil físico.

E5.2 (`20260903T091901_E5.2`) aplicó una regla explícita de parsimonia: menor
perfil dentro de `max(0,0001 rad,1 %)` del mejor MAE con 5/5 aceptaciones.
Seleccionó `P14_A` para las cuatro tasks. H no mejoró materialmente, W empeoró
ligeramente y L empeoró claramente, además de 12/80 rechazos en perfiles que
lo habilitan. Esta selección sólo vale para replay del dataset. E6.0 permanece
bloqueado; no se deriva autorización física de P14.

`E6.0-CHECK` vigente (`20260903T123041_E6.0-CHECK`) separó los gates por escenario.
E4.4 y la envolvente clamp/fixture no aplican al canary sin caja cuando
plataforma y B0 están retiradas, pero siguen bloqueando E7+. E6.0A
`20260903T093145_E6.0A` confirmó ready B dentro del soporte del checkpoint y
definió hold fresco de H/L/W; el run `092935` se descarta por usar el swap de
muñecas antiguo. E6.0J `20260903T120626_E6.0J`, por decisión del propietario,
adopta un proxy documental por clamp de `0,145×0,142×0,330 m`: unión de las
mallas PGC vendor más 25 mm por cara derivados de su carrera de 50 mm. Pasó
1.201 estados sin contacto externo; es un supuesto para el canary sin caja,
no CAD ni certificación del clamp real. E6.0L
`20260903T122501_E6.0L` fija el contrato temporal propio del canary: sólo
punto 0, una vez, sin replay y sin `end_flag`. E6.0M
`20260903T122502_E6.0M` empaqueta la secuencia exacta de ida y retorno, pero no
la instala ni la valida físicamente. Para E6.0 quedan tres requisitos:
recovery supervisado, transporte físico/STOP revisado y límite de aceleración
certificado. La auditoría y el frontend
`run_cruzr_vla_canary.sh --check` son locales; `--one-point`, `--one-chunk`,
`--window` y `--stop` todavía se rechazan antes de acceder al robot.

E6.0B (`20260903T094547_E6.0B`) muestreó 401 estados del camino exacto
`preposición→A→B→A→preposición`. Con FK vendor y OBB/SAT sobre 46 links
obtuvo cero violaciones URDF y cero solapes entre links a distancia cinemática
mayor que tres. Los 58 pares cercanos reportados no se clasifican: falta la
SRDF/matriz de colisiones permitidas, y la geometría PGC no representa las
abrazaderas pasivas instaladas. Es un PASS parcial de broad phase, no un PASS
de autocolisión ni una autorización física.

E6.0C (`20260903T095600_E6.0C`) clasificó los 58 pares: 40 directos, 12
estáticos ajenos al mando P14, 2 PGC no instalados y 4 móviles upstream. El
narrow phase BVH/STL descartó todos los candidatos a nivel de AABB de
triángulos y produjo cero intersecciones en 401 estados; cuatro self-tests
validaron el SAT coplanar/3D. El resultado es válido sólo para las mallas
vendor upstream; falta geometría clamp, holgura con tolerancias, política
runtime revisada y validación física. El gate permanece cerrado.

E6.0D (`20260903T101730_E6.0D`) midió la holgura exacta entre esas cuatro
parejas sobre los mismos 401 estados. El mínimo vendor muestreado fue
`0,016377700 m` (hombro derecho/torso, muestra 100); los codos/muñecas
mantuvieron unos `0,03488 m`. No es un margen físico certificado: el barrido
es discreto y siguen ausentes clamp, tolerancia de modelo/calibración/flexión,
aceleración y fuerza. El contrato derivado limita el canary a un punto y
calcula delta efectivo como `min(delta, velocidad × 0,08 s)`, pero queda
`SPECIFICATION_ONLY_FAIL_CLOSED`, sin publicador y con aceleración/margen
físico nulos.

E6.0E (`20260903T102652_E6.0E`) implementó el guard de preview de un solo
punto: pasó 35 casos de mensajes y 7 de manipulación del contrato. Sólo dos
previews nominales fueron aceptados; ninguno autorizó ejecución y el módulo no
contiene ROS, red, topic ni publicador. E6.0F (`20260903T102931_E6.0F`)
congeló el preview no aplicado de instalación/rollback del task ready y agotó
el inventario local. El loader vendor no debe ejecutarse desatendido porque es
interactivo y puede reemplazar el directorio y `task_list`.

La siguiente frontera es física o requiere valores certificados. El primer
escenario es `NO_BOX_READY_EMPTY_CELL`: caja, mesa/plataforma y AprilTag fuera
de un radio de 1,5 m; clamps instalados, vacíos y firmes; robot estable y home
verificado; ruedas bloqueadas y cargador fuera; dos personas, una junto al
paro; PICO/UI/teleoperación cerrados y VLA inicialmente detenido. Preparar el
escenario no autoriza movimiento.

E6.0G (`20260903T104309_E6.0G`) confirmó en vivo y sólo en lectura un E-stop
principal accionado, servo E-stop liberado, cargador fuera, baterías >79 %, VLA
detenido y cero publicadores. El task/XML ready estaba ausente. Con el paro
activo no hubo `/mc/whole_joint_states`, servidor de acción ni muestra de
actuadores, por lo que no se demostró inmovilidad instrumental.

Tras liberar el E-stop principal sin movimiento inesperado, el run intermedio
`20260903T105539_E6.0G` confirmó que Motion seguía en `WaitStartMotion`; una
pulsación exterior produjo sólo `Power click`. Se completó después el apagado
y reinicio supervisados prescritos por el manual. El arranque pasó
`WaitEStopRelease→SelfChecking→JoystickMode`, con self-check y `StartMotion`
exitosos.

El run E6.0G vigente `20260903T113216_E6.0G` corrigió además el falso cero de
`ros2 action info` usando `rosa action info`: demostró un servidor de
manipulación, proceso Motion posterior al task list, ready cargado en runtime,
preflight canónico aprobado y robot inmóvil. Paros `0/0`, cargador fuera y VLA
`exited/exited/publishers:0`; no hubo movimiento ni autorización física.

E6.0H (`20260903T104552_E6.0H`) creó un backup fresco e instaló de forma
atómica sólo el XML ready hash-matched y una entrada en `task_list.yaml`. No
recargó ni reinició el task manager, no inició VLA y mantuvo cero publicadores.
El task quedó inicialmente sólo **en disco**; el reinicio completo posterior
inició Motion después del task list y E6.0G demostró su carga runtime. El
readiness anterior mantenía cinco gates no-preflight; E6.0J redujo el vigente
a cuatro bajo el supuesto geométrico documentado. `--check` reconoce el
estado instalado sin reescribir. Esta constatación no autoriza ejecutar la
tarea ni iniciar VLA.

E6.0I vigente (`20260903T115129_E6.0I`) añadió el tramo que faltaba en los
barridos anteriores: `home` fresco a preposición vendor y su retorno. El run
inicial `114811` paró correctamente ante un nuevo solape OBB
`R_shoulder_yaw_link↔torso_link`; el analizador se amplió para resolverlo por
malla exacta. Sobre 101 muestras de entrada y 601 estados compuestos no hubo
intersecciones ni límites URDF violados. El mínimo vendor muestreado bajó a
`0,011169662 m`. Sigue sin modelar abrazaderas pasivas, tolerancias,
continuidad o dinámica; por tanto el gate físico permanece cerrado.

E6.0J vigente `20260903T120626_E6.0J` cubrió la misma trayectoria completa con
un proxy documental deliberadamente sobredimensionado por extremo
(`0,145×0,142×0,330 m`). No encontró solapes fuera de su cadena de montaje ni
intersecciones exactas. El resultado sólo satisface el gate geométrico del
canary `NO_BOX_READY` bajo la instrucción expresa del propietario; no extiende
esa aceptación a caja, mesa, carga, fuerza o operación industrial.

E6.0K `20260903T121338_E6.0K` registró una lectura manual aproximada de las
fotos con cinta: `120×52×105 mm`; con 10 mm por cara se adoptó
`140×72×125 mm`. El volumen queda contenido en el proxy E6.0J en ambos lados
bajo la hipótesis de clamps iguales o reflejados, por lo que el barrido mayor
lo cubre. Las fotos no están versionadas y la lectura no reemplaza CAD ni
certificación mecánica.

E6.0L `20260903T122501_E6.0L` pasó 36/36 expectativas del control core. El
archivo de compatibilidad `cruzr_s2_vla_physical_executor.py` es
deliberadamente transport-neutral: produce como máximo un intent en memoria y
declara `physical_transport_implemented=false`. Esto separa la decisión
temporal —ya determinada por el proyecto— de la futura implementación ROS/STOP,
que sigue siendo gate bloqueante.

E6.0M `20260903T122502_E6.0M` verificó que el nuevo MetaMove local recorre
`B→A→staging` con los goals/duraciones inversos y que el XML termina brazos,
cabeza y cintura en home numérico. `cruzr_vla_ready_pose.sh --check` y
`--dry-plan` son locales; `--install`, `--run-ready`, `--run-recover` y
`--stop` terminan con código 3 antes de cualquier acceso al robot.

La primera preparación física posterior quedó detenida antes de instalar:
aunque la confirmación textual indicaba E-stop principal accionado, el auditor
vivo y el preflight canónico leyeron `ESTOPS=0,0`. El operador enclavó después
el pulsador de nuevo. E6.0G `20260903T123632_E6.0G` confirmó entonces
`ESTOP_KEY=1`, cargador fuera, VLA detenido y cero publicadores. El valor
`SERVO_ESTOP_KEY=0` no corroboró por software el paro de chasis también
declarado. Con el E-stop principal activo, la ausencia de estado articular y
action server fue esperada y no se interpretó como inmovilidad instrumental.

E6.0N `20260903T123940_E6.0N` instaló **sólo en disco** el recovery exacto:
XML `45359d49…cd3c`, MetaMove `bd5f588a…e3b0` y una única entrada en el task
list, cuyo hash pasó de `e4ac5e43…4def7` a `0d24122c…64957`. El backup está en
`/home/walker/cruzr-vla/backups/20260903T123940_E6.0N`; el check posterior y
las nueve entradas de `evidence.sha256` pasaron. No hubo reload/restart,
arranque VLA, publicador ni movimiento. Como Motion inició antes de esta
modificación, la tarea todavía no está cargada en runtime. El gate de recovery
no se cierra hasta cargarla mediante un procedimiento separado y validarla
físicamente de forma supervisada; los otros gates continúan iguales.

E6.0O `20260903T124843_E6.0O` recargó sólo el contenedor dedicado
`manipulation_task_manager/robot_app`, no el control Motion completo. El
E-stop principal permaneció activo antes/después y no se llamó ninguna tarea.
El nuevo proceso arrancó después del task list y conservó una entrada y todos
los hashes exactos; cargador fuera, VLA detenido, cero publicadores y cero
movimiento. `SERVO_ESTOP_KEY=0` continuó sin corroborar el paro de chasis. El
log de arranque muestra únicamente la espera de `ListControllers` esperable
bajo E-stop, sin fatal/crash/YAML. Un error posterior de quoting en la captura
de log fue corregido y revalidado por lectura, sin segunda recarga. La carga
por orden temporal está demostrada; el action server y la trayectoria todavía
deben validarse tras un levantamiento controlado del paro.

`E6.0-CHECK` vigente (`20260903T125333_E6.0-CHECK`) consume E6.0N/O y mantiene
tres gates: recovery físicamente validado, transporte/STOP físico revisado y
límite de aceleración aceptado. No autoriza movimiento.

Tras liberar el E-stop principal, los topics reportaron `0/0`, pero siguieron
ausentes el estado articular y el action server. El log de Control Center
resolvió la ambigüedad: no registra `onServoEstopState=1`; el principal causó
`JoystickMode/Ready→WaitStartMotion` y su liberación produjo
`onEstopState=0`, sin un `ButtonStartMotion` posterior. El software es por
tanto consistente con ambos paros liberados y rearme pendiente. El preflight
terminó sin goal ni movimiento. Las fotos posteriores confirmaron que esta
revisión no tiene un botón separado identificable como START Motion: blanco es
`KEY1`, aro verde es Power/Start exterior y metálico es alimentación del
chasis. La prueba histórica demuestra que una pulsación verde sólo genera
`Power click`. No se debe pulsar ninguno para improvisar el rearme; corresponde
el ciclo completo supervisado de la sección 5.3.3 y repetir después el auditor.

El reinicio completo siguiente resolvió ese estado. E6.0G
`20260903T132151_E6.0G` demostró de nuevo actuadores habilitados, action server,
acciones listas, paros `0/0`, cargador fuera y VLA detenido con cero
publicadores. El primer `ready` físico se lanzó desde home medido, pero el XML
vendor falló de forma determinista: su acción de cintura contiene dos valores
`-0.0; 0.0` y el S2 v0.2.0 sólo expone `waist_yaw`. Esa rama falló antes de
emitir `MoveTo` y el paralelo abortó cabeza/brazos tras un avance pequeño. El
robot quedó quieto, sin force/collision/fault; `cruzr/home` se usó una sola vez
para invertir ese avance conocido y terminó `SUCCEED/status=4`. La medida final
fue cuerpo `0,002589 rad`, brazos `0,000671 rad`, velocidad cero.

E6.0P `20260903T133300_E6.0P` corrigió únicamente esa dimensión en una copia
versionada: `joint_angles="0.0"`. El XML S2 tiene hash
`c767f7396a325d375752fbce2351837e7f5e0c750902e4815ddd7acb24e2a9b2`; el
vendor intacto permanece en el repositorio con hash `f4025124…d8323`. El XML
vivo se sustituyó atómicamente con backup
`/home/walker/cruzr-vla/backups/20260903T133300_E6.0P`, sin recarga, tarea,
inferencia, publicador ni movimiento.

E6.0Q `20260903T135236_E6.0Q` validó físicamente READY→HOME sin caja. READY
terminó `SUCCEED/status=4` y quedó estacionario, sin fault y a menos de
`0,001843 rad` de sus consignas nativas. El primer recovery abortó antes de
movimiento: E6.0N había puesto el YAML nombrado bajo la raíz de
`manipulation_task_manager`, pero `MetaMove` lo busca bajo
`manipulation_meta_tasks`. El fatal `GetRequestFromYamlNode` reinició una vez
el contenedor y las articulaciones siguieron en READY. Se movió el YAML a la
ruta runtime correcta y se corrigió también el último remanente 2D de cintura
en el XML recovery (`joint_angles="0.0"`); XML `9e47b6ee…4fbcc`, backup
`/home/walker/cruzr-vla/backups/20260903T134947_E6.0Q`. El arreglo no recargó,
invocó ni movió. El segundo recovery terminó `SUCCEED/status=4` y la medida
final fue HOME en 20 ejes: cuerpo `0,002589 rad`, brazos `0,000959 rad`,
velocidad cero. VLA permaneció detenido y sin publicadores. El gate
ready/recovery queda cerrado; el canary del checkpoint continúa bloqueado por
transporte/STOP físico y aceleración.

El auditor local se regeneró como `20260903T140006_E6.0-CHECK`: recovery
figura `PASS` y quedan exactamente dos gates `BLOCKED`, transporte/STOP físico
y límite de aceleración. No se habilitó ningún modo activo.

Al cierre de la jornada, E6.0R `20260903T142823_E6.0R` ya aporta el adaptador
SDK P14 de un punto y STOP fail-closed, verificados offline en 51/51 casos.
E6.0T autoritativo `20260903T143529_E6.0T` confirmó sólo en lectura que esta
unidad consume `/mc/sdk/robot_command` (`RobotCommand`) y publica estado en
`/mc/sdk/robot_state`; no existen los topics directos alternativos de brazos.
No se creó ningún publicador y los dos contenedores VLA permanecieron
detenidos. E6.0S `20260903T144344_E6.0S` verificó 2.028 trayectorias minimum-
jerk con la envolvente provisional de proyecto `delta<=0,1 rad`,
`|v|<=0,15 rad/s`, `|a|<=0,5 rad/s²`. Esta envolvente no es certificación del
fabricante y aún no tiene aceptación del propietario.

E6.0U `20260904T073609_E6.0U` completó el monitor de estado medido y pasó
152 casos más 8 alteraciones de contrato. Comprueba READY y estacionariedad,
los 14 ejes de brazo, los seis ejes H/L/W bloqueados, frescura, velocidad y
aceleración; ante cualquier fallo solicita STOP una sola vez y queda
enclavado. No es una validación dinámica del robot: fue una campaña in-memory.

E6.0V `20260904T073852_E6.0V` resolvió la fuente viva sin publicar ni mover:
`/mc/sdk/robot_state` estaba anunciado pero no entregó muestra en 3 s;
`/mc/whole_joint_states` sí entregó 22 nombres, posiciones y velocidades y
quedó seleccionado con QoS RELIABLE. Los dos consumidores de
`/mc/sdk/robot_command` anuncian BEST_EFFORT y no había publicador de comando.

E6.0W `20260904T074537_E6.0W` añadió el runtime y proceso ROS explícito de un
punto: 24 casos funcionales y 3 gates de activación pasaron. La creación del
publicador es perezosa, posterior a READY fresco y a un chunk válido; sólo se
consume el punto 0, H/L/W se mantienen en su medida fresca y STOP destruye el
publicador. La plantilla del repositorio permanece desactivada y rechaza
`--run` antes de importar ROS.

E6.0X `20260904T075519_E6.0X` registra la aceptación del propietario de la
envolvente provisional sólo para `NO_BOX_READY`, task 0/P14 y un punto. No es
una certificación ni una autorización de movimiento. Después de un rearme
completo, E6.0G `20260904T084316_E6.0G` volvió a demostrar `ESTOPS=0,0`,
cargador fuera, estado/action disponibles, HOME medido, VLA detenido y cero
publicadores.

E6.0Y implementa el launcher activo por etapas sin habilitarlo por defecto.
`--ready` exige HOME medido; `--one-point` exige READY medido y crea un grant
efímero ligado por hashes a preflight, READY, aceptación y límites;
`--recover` sólo admite READY medido. El proceso crea el publicador de comando
de forma perezosa después de recibir un chunk válido y lo destruye ante STOP o
fallo. Nunca arranca el ejecutor vendor. El auditor offline
`20260904T085243_E6.0Y-OFFLINE` pasó sin acceder al robot. El primer punto
físico sigue sin ejecutarse y necesita una confirmación actual propia.

La primera etapa física HOME→READY se completó una sola vez en
`20260904T085921_E6.0Y-READY`, con `SUCCEED/status=4`. La comprobación inicial
rechazó por error la postura porque usaba coordenadas crudas de actuador: en
esta unidad algunos signos no coinciden con los joints ROS del checkpoint. La
muestra independiente `20260904T090051_E6.0V` confirmó por nombres los 14
objetivos READY con error máximo `0,001842 rad` y velocidad cero; la muestra
cruda confirmó actuadores sanos y delta posición–consigna ≤`0,001842 rad`.
El gate ahora usa `/mc/whole_joint_states` para postura y mantiene
`/mc/actuator_state` sólo para salud, velocidad cruda y consigna latente. La
regresión offline `20260904T090403_E6.0Y-OFFLINE` pasó. No se repitió READY,
no se arrancó inferencia y no apareció publicador de comando; los contenedores
siguen `exited/exited`. Falta confirmar visualmente READY estable antes de
autorizar por separado `--one-point`.

El intento `20260904T090909_E6.0Y` arrancó sólo inferencia y completó dos
preflights READY, pero no ejecutó el punto: Motion rechazó el grant con
`grant_not_current` antes de importar ROS. El PC estaba 22 s adelantado y el
`issued_at` basado en el PC aún era futuro para Motion. No se creó publicador,
no se envió trigger ni hubo movimiento; el cleanup dejó ambos contenedores
detenidos y `publishers:0`. El launcher obtiene ahora el epoch fresco de
Motion justo antes del grant, registra el skew y aborta si supera 60 s. La
regresión `20260904T091614_E6.0Y-OFFLINE` prueba grant válido, E-stop inválido,
desfase inválido y los gates READY. La postura posterior sigue
`MEASURED_READY=1` con error máximo `0,001842 rad` y velocidad cero. El intento
no debe repetirse sin una autorización nueva.

El nuevo intento `20260904T091928_E6.0Y` superó el gate temporal
(`GRANT_CLOCK_SOURCE=motion-host-epoch`, skew 23 s), y task 0 produjo tres
chunks. El primer punto se rechazó antes de emitir comandos porque el eje 2
superaba el delta máximo aceptado de `0,1 rad`:
`transport:arm:target_delta:2`. Se publicaron cero frames y no hubo movimiento.
El backend ROS sí llegó a construirse brevemente antes de que el planificador
rechazara el punto; STOP lo destruyó y el estado final fue `publishers:0`,
`exited/exited`. El runtime se corrigió para ejecutar
`plan_minimum_jerk(...)` y validar delta/velocidad/aceleración antes de crear el
backend, y para no imprimir 500 estados iguales por segundo. E6.0R y las
regresiones E6.0W `20260904T092245_E6.0W` y E6.0Y
`20260904T092246_E6.0Y-OFFLINE` pasan. El robot siguió en READY medido a
`0,001842 rad`, velocidad cero. El siguiente trabajo es analizar en shadow el
primer punto respecto del estado fresco; no aumentar `0,1 rad`, no repetir y
no recuperar automáticamente.

Tras comprobar visualmente READY, el recovery autorizado
`20260904T092716_E6.0Y-RECOVERY` llamó una sola vez a
`s2_bio_vla/s2_vla_e6_0_exact_recovery` y obtuvo `SUCCEED/status=4`. El gate
posterior midió HOME en 20 ejes: cuerpo ≤`0,002780 rad`, brazos
≤`0,000959 rad`, velocidad cero y delta posición–consigna ≤`0,002780 rad`.
No se arrancó inferencia; VLA terminó `exited/exited`, `publishers:0`. Falta
confirmación visual final. El siguiente trabajo técnico es shadow/análisis de
la discontinuidad del eje 2, no otro movimiento.

E6.0X `20260904T075519_E6.0X` registra la aceptación del propietario sólo para
E6.0, celda vacía, task 0/P14 y un punto: delta objetivo `<=0,1 rad`, velocidad
medida `<=0,15 rad/s`, aceleración medida `<=0,5 rad/s²`, muestreo de `10 ms`,
H/L/W inmóviles. No es certificación del fabricante ni autorización de
movimiento.

El consolidado vigente `20260904T075648_E6.0-CHECK` deja el ejecutor en
`PASS_CODE_OFFLINE_ACTIVATION_GATED`, la aceptación en `PASS` y cero gates
estáticos. El preflight es `RUN_SPECIFIC_REQUIRED`: debe repetirse hoy con la
celda vacía antes de crear el grant de una sola corrida. Hasta que ambas cosas
ocurran, `--one-point` sigue cerrado, VLA debe permanecer detenido y
`E6.0_PHYSICAL_AUTHORIZED=0`.

La fase A del preflight de hoy es `20260904T075947_E6.0G`. Con los paros
declarados accionados, comprobó sólo en lectura: principal `ESTOP_KEY=1`, señal
servo/chasis `0`, cargador fuera, baterías `45,8/48,5 %`, READY S2 correcto,
VLA detenido y cero publicadores. La señal `0` no corrobora el paro físico de
chasis; se conserva la comprobación física del operador. Bajo E-stop no había
estado articular ni action server, por lo que el siguiente gate es liberar
ambos paros bajo supervisión y repetir `--expect-released`. No pulsar
Power/KEY1/Start durante esa transición.

Después de liberar físicamente ambos paros, software confirmó `0/0/0`, pero
whole-state y el servidor de manipulación continuaron ausentes. El preflight
liberado falló cerrado. El guard correcto, ejecutado en Vision y sólo en modo
`--check`, obtuvo x86 3/3, cámaras 2/2 y seguridad `0 0 0`, pero
`CONTROL_STATE=unknown`; no reinició ni movió. Se requiere el ciclo completo
supervisado v0.2.0 antes de retomar E6.0. No usar Power/KEY1/Start aisladamente.

## Incompatibilidades corregidas en el overlay

El paquete original no arrancaba tal como fue entregado:

1. El ejecutor SDK instalado estaba incompleto y cargaba un perfil de 17 ejes.
2. `/mc/sdk/robot_state` se anunciaba, pero no emitía muestras. Se usa como
   alternativa read-only `/mc/whole_joint_states`, activo a unos 500 Hz.
3. La imagen no contenía la variante GR00T que define
   `Utars_1RGBDataConfig` ni el argumento `eagle_path`. Se monta el árbol GR00T
   suministrado por UBTECH, verificado mediante hashes.
4. El staging inicial omitía `experiment_cfg/metadata.json`; ahora incluye los
   dos metadatos necesarios para inferencia, pero no los 8,5 GB del optimizador
   de entrenamiento.

Ninguna de estas correcciones modifica el firmware base. Los dos contenedores
VLA siguen con política `restart=no` y quedan detenidos al terminar.

## Uso en shadow mode

Los runs no deben construirse concatenando una variable que proceda de otro
shell. Para medidas o herramientas futuras, crear la salida en el mismo bloque:

```bash
VLA_RUN_DIR="$(./scripts/vla/new_vla_evidence_run.sh --experiment ID)"
```

E1.1 y E1.2 disponen de wrappers que crean y validan esa ruta internamente:

```bash
./scripts/vla/audit_vla_experiment_e1_1.sh
./scripts/vla/audit_vla_experiment_e1_2.sh
```

Para un smoke autocontenido de task 0 o 2, con directorio propio, STOP ante
fallo y exportación de evidencia:

```bash
./scripts/vla/run_vla_shadow_smoke.sh --task-id 0
```

Para repetir E2.2 offline con tasks PLACE 1 y 3:

```bash
./scripts/vla/run_vla_offline_place_e2_2.sh --check
./scripts/vla/run_vla_offline_place_e2_2.sh --run --seed 0
```

Esta orden no sustituye una prueba física: no usa estado vivo ni comprueba que
una caja se deposite correctamente.

Para repetir la campaña E3.0 completa:

```bash
./scripts/vla/run_vla_offline_campaign_e3_0.sh --check
./scripts/vla/run_vla_offline_campaign_e3_0.sh --run
```

Las violaciones se conservan como resultado y nunca se envían al robot.

Para repetir la auditoría E4.0 de sólo lectura:

```bash
./scripts/vla/audit_vla_ready_e4_0.sh --check
./scripts/vla/audit_vla_ready_e4_0.sh --run
```

Un resultado parcial/bloqueado no autoriza E4.1 ni instalar o ejecutar el task.

Para repetir E4.2 sin red al robot:

```bash
./scripts/vla/audit_vla_heights_e4_2.sh --check
./scripts/vla/audit_vla_heights_e4_2.sh --run
```

Su resultado actual demuestra familias y rechaza una altura escalar; tampoco
autoriza una prueba física.

Después de que E1.0, E1.3 y E2.1 liberen el gate, cinco repeticiones E2.3 se
ejecutan sin mezclar logs/chunks y con STOP entre runs:

```bash
./scripts/vla/run_vla_shadow_repetitions.sh --task-id 0 --repetitions 5
```

La secuencia manual de bajo nivel continúa disponible para diagnóstico:

```bash
./scripts/vla/run_ubtech_vla_shadow.sh --deploy
./scripts/vla/run_ubtech_vla_shadow.sh --start-shadow --shadow-duration 300
./scripts/vla/run_ubtech_vla_shadow.sh --start-inference
./scripts/vla/run_ubtech_vla_shadow.sh --status
./scripts/vla/run_ubtech_vla_shadow.sh --trigger --task-id 0 --inference-duration 8
./scripts/vla/run_ubtech_vla_shadow.sh --stop
```

Si la secuencia ya terminó pero no se conservaron los logs locales, se pueden
extraer desde los contenedores detenidos sin arrancarlos:

```bash
VLA_RUN_DIR="$(./scripts/vla/new_vla_evidence_run.sh \
  --experiment RECOVERED-SHADOW)"
./scripts/vla/run_ubtech_vla_shadow.sh --export-evidence "$VLA_RUN_DIR"
```

El script aborta si detecta un publicador en `/mc/sdk/robot_command`. El
validador no importa `RobotCommand` y no crea publicadores ROS.

Los identificadores suministrados son:

- `0`: recoger caja grande del nivel inferior;
- `1`: depositar caja grande en el nivel inferior;
- `2`: recoger caja grande del nivel medio;
- `3`: depositar caja grande en el nivel medio.

## Condición de ejecución para el primer movimiento físico

Los gates de geometría, READY/recovery, transporte, monitor y límite provisional
ya tienen evidencia. Esto no concede movimiento. Para la primera ejecución se
aplica la siguiente secuencia estricta:

1. Reconfirmar celda vacía 1,5 m, clamps vacíos, ruedas bloqueadas, cargador
   fuera, dos personas y cliente único.
2. Ejecutar `--ready` desde HOME medido con su confirmación exacta; detenerse y
   confirmar visualmente READY estable.
3. Ejecutar `--one-point` sólo desde READY medido. El grant expira en dos
   minutos y autoriza exclusivamente task 0/P14, punto fuente 0, brazos 14D,
   `delta<=0,1 rad`, `|v|<=0,15 rad/s`, `|a|<=0,5 rad/s²`.
4. Inspeccionar el resultado sin repetir ni recuperar automáticamente. Ante
   contacto, oscilación o movimiento de H/L/W, accionar el E-stop.
5. Sólo si el resultado permanece READY exacto, usar `--recover`; cualquier
   postura distinta exige diagnóstico, no un recovery improvisado.

`--one-chunk` y `--window` siguen bloqueados. E6.0Y no autoriza cajas, mesa,
AprilTag, chasis, cintura, elevador ni cabeza.
