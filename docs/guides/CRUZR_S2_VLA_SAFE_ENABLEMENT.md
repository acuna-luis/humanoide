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

`E6.0-CHECK` vigente (`20260903T094623_E6.0-CHECK`) separó los gates por escenario.
E4.4 y la envolvente clamp/fixture no aplican al canary sin caja cuando
plataforma y B0 están retiradas, pero siguen bloqueando E7+. E6.0A
`20260903T093145_E6.0A` confirmó ready B dentro del soporte del checkpoint y
definió hold fresco de H/L/W; el run `092935` se descarta por usar el swap de
muñecas antiguo. Para E6.0 quedan seis requisitos: ready S2
instalado/registrado, recovery validado, barrido de
autocolisión/entrada/salida, ejecutor revisado, límite de aceleración y
contrato temporal físico. La auditoría y el frontend
`run_cruzr_vla_canary.sh --check` son locales; `--one-point`, `--one-chunk`,
`--window` y `--stop` todavía se rechazan antes de acceder al robot.

E6.0B (`20260903T094547_E6.0B`) muestreó 401 estados del camino exacto
`preposición→A→B→A→preposición`. Con FK vendor y OBB/SAT sobre 46 links
obtuvo cero violaciones URDF y cero solapes entre links a distancia cinemática
mayor que tres. Los 58 pares cercanos reportados no se clasifican: falta la
SRDF/matriz de colisiones permitidas, y la geometría PGC no representa las
abrazaderas pasivas instaladas. Es un PASS parcial de broad phase, no un PASS
de autocolisión ni una autorización física.

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

## Condición pendiente para movimiento físico

Antes de conectar un ejecutor físico deben cumplirse todos estos puntos:

1. Completar la auditoría del XML suministrado
   `codes-S2/.../s2_vla_pick_large_teleop_ready.xml`, hash
   `f4025124491eba995ec824db3e3be91875f781a4b4e98928654bde9a021d8323`,
   instalando/identificando primero el task canónico, completando lifter,
   límites, swept volume y recovery. El mapping local de cintura ya quedó
   resuelto como `waist_yaw=0`. Aún no se autoriza
   probarlo físicamente.
2. La definición instalada de `clamp_s2_joints_trajectory` ya está resuelta y
   preservada por hash; demostrar que pertenece al task S2 oficial y resolver
   por qué su `back` no invierte toda la secuencia.
3. Repetir shadow desde esa postura y obtener chunks aceptados sin saltos,
   valores fuera de rango ni estado obsoleto.
4. Implementar un ejecutor S2 independiente que sólo mande los 14 ejes de los
   brazos. Cabeza, elevador y cintura permanecen bloqueados, como en el diseño
   del ejecutor SDK suministrado.
5. Añadir deadman, timeout, parada por pérdida de estado y límites conservadores
   antes de habilitar la publicación.
6. Realizar primero una prueba sin caja y a velocidad reducida, con aprobación
   física explícita en ese momento.

Hasta completar estas condiciones, el VLA está operativo únicamente para
inferencia y validación shadow; no está habilitado para mover el robot.
