# Acceso desde postura medida a READY — revisión offline

No instala ni ejecuta. Conserva el READY que requiere ENTRY410; mide el inicio
en lugar de asumir todos los valores numéricos de HOME.

Desde la raíz del repositorio, con un directorio nuevo:

```bash
OUT=../Humanoide-vla-evidence/NUEVO_ACCESO_READY
python3 scripts/vla/capture_named_entry_state.py --output-dir "$OUT/capture"
.venv/general-home/bin/python scripts/vla/prepare_home_ready_access.py \
 --reference ../Humanoide-vla-evidence/20260914T124504Z_ENTRY410-GAP220/route-review.json \
 --named-capture "$OUT/capture/capture.json" \
 --output-dir "$OUT/access"
```

La referencia contiene la escena histórica GAP220. Mover robot, mesa o caja
invalida su aplicación a la escena actual: este comando no registra de nuevo
los obstáculos. Los tiempos usan el perfil conservador del generador existente
y requieren comprobar límites efectivos antes de instalar. La inversión sólo
cubre los mismos segmentos desde sus extremos; no es recuperación desde una
interrupción arbitraria.

## 2026-09-14 — VLA-01: acceso medido a READY calculado por grupos

OBSERVADO: captura pasiva posterior al arranque, 14:07:23–14:07:33 UTC,
347 muestras articulares, ambos paros0, sin incidencias del analizador.
VERIFICADO OFFLINE: `scripts/vla/prepare_home_ready_access.py` genera cinco
tramos desde la última postura medida hasta el READY exacto del informe410.
Comprueba identidad de traza, ausencia de movimiento/fallos en toda la traza,
variación articular≤0,002rad, identidad del modelo y fuentes inmutables durante
el cálculo. Genera diez XML DRAFT para ambos sentidos; no instala ni publica.

Resultado bajo las hipótesis del informe GAP220:1018 pares con intervalos
geométricos certificados,54 con violación del margen del modelo,0 pendientes
y sin timeout. Los54 pares son exactamente los mismos del informe de etapas
ENTRY410; no se convierten en aprobados ni se eliminan del resultado. La
correspondencia de pares no transfiere automáticamente pruebas de otro tramo.
Duración propuesta136s: cabeza20, cintura1, elevador1, brazo izquierdo57 y
derecho57. Son tiempos de propuesta, no una medición ni una ejecución aprobada.

PENDIENTE: comprobar límites dinámicos/configuración efectiva, correspondencia
runtime de grupos, identidad cargada y protocolo del ensayo. Los XML de acceso
NO están instalados, el wrapper activo permanece bloqueado y no se ha emitido
habilitación física. No hubo reinicios ni movimientos. No es aún una ruta
HOME→ENTRY ejecutable.

Evidencia externa: `../Humanoide-vla-evidence/20260914_HOME_READY_ACCESS/`
(traza, análisis, access/review.json, diez borradores, comparación y fuentes).
Tests: cinco casos de admisión de postura pasan, incluidos movimiento anterior,
deriva con velocidad cero, fallo y dato no finito; los tres tests existentes
de construcción por grupos también pasan. No cubren movimiento real.
Receta reproducible: `docs/vla/ACCESO_HOME_READY_20260914.md`. Reversión local:
retirar selectivamente las dos fuentes nuevas y restaurar documentos desde
`before/` de la evidencia, preservando otros cambios. Ningún cambio persistente
en el robot.

## 2026-09-14 — contraste vivo de configuración HOME→READY

VERIFICADO: consultas de lectura a Motion recuperaron YAML y URDF, con hashes
idénticos al contrato archivado. Tipo, lado y dimensión de los cinco grupos
coinciden. Las20 articulaciones cumplen límites de posición (incluido el error
del informe) y velocidad para el perfil cúbico propuesto. Los seis ejes de
cabeza/cuerpo cumplen además la aceleración configurada. No se localizaron
fuentes MetaMove en los dos paquetes consultados; esto no demuestra su ausencia
en todo el sistema. El orden articular efectivo dentro de MetaMove y su
interpolador no quedan demostrados por tipo/lado/dimensión.

PENDIENTE concreto: las14 articulaciones de brazo no tienen aceleración en
estos archivos. No se infiere un límite ni se marca la ejecución como aprobada.
No hubo cambios, instalaciones, reinicios ni movimientos del robot.
Evidencia: `../Humanoide-vla-evidence/20260914_HOME_READY_CONTRAST/`. La primera
lectura normalizó saltos de línea y falló la comprobación hash; se conservó y
se repitió con bytes exactos en base64 (`runtime-bytes.json`), cuyos hashes
pasan. `limits-comparison.json` conserva cada eje y sus resultados.

Reproducción local:
```bash
.venv/general-home/bin/python scripts/vla/contrast_home_ready_limits.py \
 --review ../Humanoide-vla-evidence/20260914_HOME_READY_ACCESS/access/review.json \
 --snapshot ../Humanoide-vla-evidence/20260914_HOME_READY_CONTRAST/runtime-bytes.json \
 --output /tmp/contraste-ready-nuevo.json
```

Cambio persistente sólo PC: nuevo comparador offline y este registro VLA-01.
Reversión: retirar el comparador y restaurar documentos desde before/ de la
evidencia, preservando cambios ajenos. No habilita el wrapper de movimiento.

## 2026-09-14 — VLA-01: contraste de bibliotecas internas Motion

VERIFICADO: se copiaron al PC mediante lectura las bibliotecas actuales
libmeta_move.so, libinterpolation_path_planner.so y libs2_arm_kinematics.so.
Hashes en binary-hashes.json. La biblioteca de interpolación tiene SHA256
1267e370614d5350706caa061a24c162e3333248b9b1af74b8ea319a3d5ee329.
El emulador existente verifica1312 casos de su rutina numérica: error máximo
2,6645352591003757e-15 frente a Hermite cúbica; con velocidad cero en extremos
q=q0+(q1-q0)*(3u²−2u³). Este resultado NO verifica el despacho de MetaMove,
sincronización, configuración de velocidades extremas ni control físico.

Búsqueda en YAML de cinco paquetes instalados: los perfiles CruzrS2 examinados
no declaran aceleración de brazos. Hay valores en perfiles WalkerS2/S3, pero
no son límites acreditados para esta unidad y no se reutilizan. No se encontró
una tabla explícita joint_names/joint_order en esa búsqueda. Los símbolos
exponen SetJointLimits; su existencia no demuestra los valores cargados.

PENDIENTE: demostrar el orden efectivo y la llamada completa de MetaMove, y
obtener límites efectivos de brazos. El análisis numérico del interpolador
queda cerrado en su alcance limitado. No se habilitó ejecución ni se enviaron
movimientos, instalaciones, reinicios o cambios de protecciones.
Evidencia: ../Humanoide-vla-evidence/20260914_MOTION_INTERNAL_CONTRAST/.
Las bibliotecas privadas quedan fuera de Git. Sólo cambios documentales enPC;
respaldo en before/. Revertir únicamente esta adición documental si se necesita.

Reproducción offline:
```bash
.venv/general-home/bin/python scripts/teleoperation/audit_motion_interpolation.py \
 --binary ../Humanoide-vla-evidence/20260914_MOTION_INTERNAL_CONTRAST/libinterpolation_path_planner.so \
 --output /tmp/interpolacion-contraste-nuevo.json
```

## 2026-09-14 — VLA-01: límites compilados y decisión de habilitación

VERIFICADO: se extrajo sin cargar código vendor la tabla de7 registros de48
bytes en VA0x2fe20 de libs2_arm_kinematics.so (SHA2562a41cf55…ad251c).
Las ramas izquierda/derecha del constructor copian esa tabla y llaman a
SetJointLimits; los primeros dos doubles son límites de posición. Se mantienen
sin calificar los nombres de los cuatro campos escalares restantes. Los
límites compilados NO se presentan como lectura efectiva de la memoria del
controlador: pueden existir sustituciones posteriores. Tres tests locales
verifican extracción por segmento ELF, rechazo de hash distinto y datos mutables.

HALLAZGO: todos los extremos nominales del acceso quedan dentro de estos
límites bajo la correspondencia propuesta. Sin embargo, el error independiente
±1° produce máximos0,01639868/0,01841203rad en codoL/R frente a0,01rad compilado.
El error positivo que cabe desde los máximos nominales es0,63338°/0,51803°.
Esto es una incompatibilidad del dominio de error revisado con esos defaults,
no una colisión física observada ni prueba de que la trayectoria nominal falle.
No se redujo el error para conseguir un resultado favorable. El contraste
anterior con URDF/YAML era incompleto frente a estos defaults compilados.

Consulta viva: bibliotecas MetaMove, interpolación y cinemáticaS2 mapeadas
en PID66. No se adjuntó depurador ni se suspendió el proceso. Los topics
individuales de brazo/cintura/elevador no devolvieron estado; rosa puede
terminar con código0 y mensaje de error en stderr, por lo que no se tomó ese
código como éxito. /mc/whole_joint_states y /mc/joint_states sí dieron estados
con nombres, pero en órdenes diferentes. Esto confirma la necesidad de
mapear por nombre y no prueba el orden interno de MetaMove.

DECISIÓN: no habilitar todavía. No se fabricó una habilitación ni se cambiaron
protecciones. Siguen sin demostrarse orden/despacho efectivo de MetaMove,
límites efectivos frente a defaults y seguimiento/parada para el ensayo.
No hubo objetivos de movimiento, instalación o recarga del robot. Los borradores
de acceso permanecen sólo en PC. Evidencia y decisión explícita:
`../Humanoide-vla-evidence/20260914_MOTION_INTERNAL_CONTRAST/enablement-decision.json`.

Nuevo extractor reproducible:
```bash
.venv/general-home/bin/python scripts/vla/extract_s2_compiled_limits.py \
 --binary ../Humanoide-vla-evidence/20260914_MOTION_INTERNAL_CONTRAST/libs2_arm_kinematics.so \
 --review ../Humanoide-vla-evidence/20260914_HOME_READY_ACCESS/access/review.json \
 --output /tmp/limites-compilados-nuevo.json
```

Registro global VLA-01: cambios persistentes sólo PC (extractor, tests y docs).
Respaldo de esta adición en before-final/ de la evidencia, copia de fuentes
y hashes. Reversión: retirar selectivamente las dos fuentes nuevas y restaurar
esta adición documental desde el respaldo, preservando el trabajo previo.

## 2026-09-14 — corrección del criterio de banda de error (VLA-01)

CORRECCIÓN de la conclusión anterior: el desbordamiento de la banda±1°
respecto a los límites compilados NO es por sí solo un incumplimiento de
consignas ni invalida una envolvente geométrica calculada sobre esa banda
más amplia. No se debe exigir sin distinguir que toda la banda geométrica
sea una consigna admisible. Tampoco se puede deducir seguimiento o parada
seguros del límite configurado. Se conservan los resultados previos como
historia, pero se retira ese desbordamiento como motivo suficiente de bloqueo.

VERIFICADO: las consignas nominales de los14 ejes de brazo siguen dentro
de los límites de posición compilados, bajo la correspondencia propuesta.
Las20 articulaciones pasan posición/velocidad nominal con YAML/URDF y perfil
cúbico. No se modifican límites, trayectorias, tiempos ni la banda±1°; no se
recorta esa banda a los límites. El análisis geométrico anterior no se repite
porque sus entradas geométricas y su dominio de error no han cambiado.

Cambios locales: extract_s2_compiled_limits.py distingue nominal_inside y
uncertainty_inside mediante position_domains; contrast_home_ready_limits.py
añade el resultado nominal sin cambiar la semántica de su campo previo.
Seis tests pasan: extracción ELF, hash, datos mutables, desbordamiento de banda
sin incumplimiento nominal, incumplimiento nominal real y errores no válidos.
Nuevos informes en ../Humanoide-vla-evidence/20260914_LIMIT_DOMAIN_CORRECTION/.

La habilitación física sigue sin emitirse por los pendientes independientes:
orden/despacho efectivo de MetaMove y contrato de seguimiento/parada del
ensayo, identidad/configuración efectiva frente a defaults y revisión de
los campos dinámicos de brazo. No se modifica ningún gate ni se presenta
una corrección lógica como ensayo físico completado. No hubo comandos al robot.

Registro global: sóloPC; backups anteriores en before/ de la evidencia.
Reversión: restaurar selectivamente estas fuentes/documentos desde before/
preservando otras modificaciones. Las fuentes de reproducción son los mismos
comandos de contraste y extracción documentados arriba, con directorio de
salida nuevo. Evidencia de decisión actual: decision.json.

## 2026-09-14 — VLA-01: ensayo físico de cabeza MetaMove y fallo de admisión

AUTORIZACIÓN: usuario confirmó HOME, abrazaderas vacías, cabeza/cuello libres,
ruedas bloqueadas, cargador desconectado, ningún mando y persona junto al paro.
Se verificó preflight vivo y XML oficial fijo cruzr/move_head_lower, SHA256
f3a73626…ea46c1, cabeza [yaw=0,pitch=−0,43]rad en2s. Revisión geométrica desde
estado nominal por nombre:1018 pares certificados,54 solapamientos del modelo
ya conservados,0 pendientes. No se reutilizó etapa1 ENTRY410 desde HOME.

EJECUTADO: una sola petición de acción, aceptada. La cabeza pasó de−0,00297209
a−0,42817239rad. Giro constante0,00057524rad; cambio observado máximo de otros
18 ejes0rad.312 muestras de motor; separación máxima entre muestras globales
0,03178306s. Velocidad máxima observada de pitch0,339292rad/s y discrepancia
máxima cmd_pos/posición0,364709°. cmd_pos es solicitado SIN LIMITAR, no la
consigna efectiva del servo: estos valores no califican el seguimiento futuro.
El usuario confirmó posteriormente suavidad y ausencia de contacto.

RESULTADO DEL EJECUTOR: FAILED_NO_RETRY, NO éxito validado. A1,97046s desde
dispatch, se detectó que la última muestra del paro principal tenía más de3s
y se solicitó cancelación. Se recibió respuesta, pero el registro de esta
versión no incluía código/lista de goals de la cancelación ni resultado final
de la acción. No se puede atribuir la detención a cancelación ni afirmar que
el E-stop se ejercitó. No hubo reintento ni HOME automático.

VERIFICACIÓN POSTERIOR: captura pasiva10s/348 muestras, sin incidencias, ambos
paros0 y velocidad máxima0 en todos los ejes. Estado al cierre: brazos/cuerpo
en su postura previa y cabeza baja estable, NO HOME completo. El E-stop físico
no fue accionado durante este ensayo según lo observado en los topics.

CORRECCIÓN PC: el monitor inicial admitía una sola muestra fresca de paro sin
comprobar su cadencia; eso permitió iniciar aunque su canal no sostenía el
umbral de3s. Ahora exige al menos dos muestras y comprueba intervalos antes
de dispatch. El intervalo posterior observado4,495s se rechaza antes de mover
en la regresión offline. Se mantiene el umbral3s: no se aceleran republicaciones
de valores cacheados ni se cambia el robot. Se registrarán además UUID del
goal, respuesta completa de cancelación y resultado tardío si está disponible.
Seis tests de envolvente/cadencia pasan. No se probó físicamente esa nueva
versión, no se volvió a ejecutar. Resolver la disponibilidad/semántica del
canal de paro sigue pendiente para este monitor.

Alcance cerrado: ejecución física del segundo componente de MetaMove/head y
detención posterior observada en este ensayo. NO califica cancelación, E-stop,
seguimiento/parada de brazos/elevador ni habilita ENTRY410.

Evidencias: ../Humanoide-vla-evidence/20260914_METAMOVE_TRIAL_PREP/;
../Humanoide-vla-evidence/20260914_METAMOVE_HEAD_CHECK/;
../Humanoide-vla-evidence/20260914_METAMOVE_HEAD_RUN/ (incluye fuentes EXACTAS
del ensayo antes de corregirlas, intent/result/trace/analysis);
../Humanoide-vla-evidence/20260914_METAMOVE_HEAD_AFTER/ (captura y regresión).
Fuente reproducible: docs/vla/ENSAYO_METAMOVE_CABEZA_20260914.md.

Registro global: robot sólo recibió la tarea citada y solicitud de cancelación;
ninguna instalación, recarga, cambio de fichero/firmware/protección. PC: nuevos
revisor, ejecutor de cabeza, monitor, analizador y tests. Reversión de código:
retirar selectivamente estos archivos nuevos y restaurar docs desde before-docs/
de la evidencia, preservando cambios ajenos. La postura física no se revierte
restaurando archivos: cualquier retorno requiere su propia orden comprobada.

## 2026-09-14 — VLA-01: acceso desde estado articular por nombre

VERIFICADO: captura nueva sólo lectura,98 pares de estados en5s, nombres
articulares completos, marcas de fuente crecientes y salud de actuadores.
Cabeza pitch−0,428268rad; cuerpo/brazos próximos a cero, inmóviles. El preparador
usa ahora /mc/whole_joint_states por nombre para geometría; los actuadores se
usan para salud/velocidad y no para inferir signo o posición articular.
El monitor ENTRY se corrigió con la misma separación y exige ambas fuentes
frescas, nombres completos/únicos, datos finitos y actuadores habilitados.
No confundir esta correspondencia del estado con el orden interno MetaMove.

Acceso medido→READY:1018 pares certificados,54 avisos internos conocidos,
0UNRESOLVED, sin timeout, duración nominal123s. Los54 avisos se conservan.
Contraste offline con snapshots archivados: posición/velocidad nominal20D
correctas; brazos nominales dentro de defaults compilados. No es lectura actual
de límites efectivos ni verifica aceleración de brazos, despacho o parada.
Veinte tests pasan, incluyendo orden permutado, nombres ausentes/duplicados,
no finitos y desacoplamiento entre posiciones motor y posiciones articulares.

Cambio PC: capture_named_entry_state.py, prepare_home_ready_access.py,
runtime/entry410_single_stage_remote.py y test_entry_named_state.py. Sin
instalación/reinicio ni movimiento remoto; no se generó habilitación física.
XML de acceso nuevos siguen siendo borradores locales, NO instalados.
La CLI del preparador exige ahora --named-capture; el antiguo --trace no se
usa para geometría. measured_start se conserva sólo como helper histórico.

Reproducción:
```bash
python3 scripts/vla/capture_named_entry_state.py --output-dir /ruta/captura-nueva
.venv/general-home/bin/python scripts/vla/prepare_home_ready_access.py \
 --reference ../Humanoide-vla-evidence/20260914T124504Z_ENTRY410-GAP220/route-review.json \
 --named-capture /ruta/captura-nueva/capture.json --output-dir /ruta/acceso-nuevo
```

Evidencia: ../Humanoide-vla-evidence/20260914_ENTRY_NAMED_STATE/ con captura,
access/review.json, límites, fuentes y hashes. Los backups están en before/.
Reversión sóloPC: restaurar selectivamente fuentes propias desde before/ y
retirar fuentes nuevas; no restaurar el monitor antiguo para habilitar movimiento.
Después de una actualización, contrastar ambos schemas/nombres y rehacer
captura/revisión; no transportar un contrato de otro robot/firmware.

PENDIENTE: semántica temporal y prueba de notificación física del paro,
despacho/carga efectivos de los grupos y contrato del ensayo. No hay GOAL
HOME/READY/ENTRY enviado. No se reclama retorno seguro desde cualquier postura.


## 2026-09-14 — VLA-01: acceso READY renovado tras ensayo de cabeza

Captura nueva de98 muestras por nombre en5s, postura inmóvil tras bajar cabeza.
Revisión medida→READY:1018 pares CERTIFIED_AFFINE_INTERVALS,54 avisos internos
retenidos,0 UNRESOLVED, sin timeout; cinco etapas/123s nominales. Se generaron
diez XML locales, ambos sentidos desde extremos exactos.
Lectura nueva de los dos archivos de configuración de Motion y contraste:
tipo/lado/dimensión coinciden; posiciones (incluida banda de error) y velocidades
calculadas cumplen los límites de esos archivos. Sigue sin aceleración para
los14 ejes de brazo; la lectura de configuración no demuestra el orden
efectivo MetaMove ni la configuración cargada en memoria. No se instalaron
tareas, reinició Motion ni enviaron movimientos. Confirmación física del
operador recibida; no falta autorización, falta completar integración.

Se corrige la receta inicial de este acceso para usar --named-capture; la
CLI antigua --trace no es vigente para geometría. No se vuelve al mapeo
de posiciones de motor para producir posiciones articulares.
Evidencia: ../Humanoide-vla-evidence/20260914_READY_AFTER_HEAD/
(capture/, access/, runtime-read.json, runtime-bytes.json, limits.json,
next-stage-summary.json, SHA256SUMS). Backups documentales en before-docs/.
Cambio persistente sólo documental en PC; ninguna habilitación física emitida.


## 2026-09-14 — VLA-01: orden de controladores y aceleración identificados

VERIFICADO en configuración/bibliotecas: orden explícito de los cinco grupos
coincide; manipulation_controller running. Decodificador YAML y constructor
identifican el campo compilado de aceleración de brazos:31,4rad/s² (velocidad
3,14rad/s), sin afirmar valores efectivos en memoria ni aumentar velocidades.
Hashes de las tres bibliotecas contrastados de nuevo en Motion.
Nuevo contraste con transmissions.yaml detecta head_pitch objetivo
−0,651079rad fuera del mínimo de hardware−0,65rad. El contraste anterior con
YAML/URDF de planificación no incluía ese archivo. No se recortó ni ejecutó.
Se añade auditor reproducible y tres tests pasan. Sin cambios remotos ni
habilitación física; la cadena efectiva MetaMove de brazos sigue pendiente.
Detalles, backups, receta, alcance y punto de reanudación:
[Orden y límites de controladores](ORDEN_Y_LIMITES_CONTROLADORES_20260914.md).


## 2026-09-14 — VLA-01: corrección READY de cabeza calculada y revisada

**VERIFICADO OFFLINE, NO INSTALADO.** Retomada la prueba solicitada tras la
consulta al proveedor. Captura de97 muestras en5s, estado por nombres/velocidad
y salud; no se envió movimiento. La referencia separada usa READY head_pitch
−0,63rad en acceso y recuperación, frente a−0,65107897rad. Se conserva±1°:
el extremo inferior de la banda es−0,6474533rad, dentro del mínimo de
hardware−0,65rad. ENTRY final y demás articulaciones no se modifican.

Se recalcularon ambos recorridos de la referencia y las etapas:1018 pares
certificados,54 avisos internos retenidos,0 UNRESOLVED, sin timeout en cada
revisión. Acceso desde postura medida→READY122s; READY→ENTRY74s nominales,
no tiempos de ejecución medidos. Diez XML de acceso y diez de ENTRY generados.
Contraste con controladores/transmisiones: orden configurado coincidente,
cero objetivos nominales fuera de hardware. No cambia la configuración
instalada ni se afirma aprobación física o lectura efectiva de límites.

Fuente reproducible nueva: scripts/vla/prepare_ready_head_hardware_limit.py,
selector hacia dentro de límites sin reducir incertidumbre; tres tests en
test_ready_head_hardware_limit.py ya pasaron. Ejecutar ese generador con
--reference (referencia previa), --hardware-snapshot (hardware-configs.json)
y --output NUEVO.json; después prepare_home_ready_access.py con captura
por nombre y prepare_entry410_stages.py con contrato/hashes registrados.
Las rutas, hashes y resultados quedan en
../Humanoide-vla-evidence/20260914_READY_HEAD_CORRECTED/
(reference.json, capture/, access/, stages410/, limits.json, SHA256SUMS).
Los hashes del contrato/runtime de ENTRY se reutilizaron de la revisión
anterior; requieren contraste vivo antes de instalar o habilitar.

PENDIENTE: el acceso nuevo no tiene aún instalación/ejecutor calificado;
la generación local de XML no lo convierte en tarea disponible. No instalar
o ejecutar el paquete anterior con head_pitch−0,651079rad. La cadena
efectiva de despacho/parada de brazos sigue fuera del alcance del ensayo de
cabeza. No solicitar otro paro/reinicio hasta disponer del paquete y del
procedimiento concreto completos. No se envió ningún movimiento adicional.

Cambio persistente sóloPC: generador, tests y registros; no instalados en
robot. Backup documental en before-docs/; las referencias anteriores se
conservan intactas. Reversión selectiva de estos nuevos archivos; no volver a
la referencia anterior para ejecutar un objetivo fuera del límite hardware.


## 2026-09-14 — VLA-01: paquete READY −0,63 / ENTRY410 preparado

VERIFICADO PC/LECTURA VIVA; NO INSTALADO NI PROBADO FÍSICAMENTE. Preparador,
contrato, instalador de 20 tareas aditivas y ejecutor de una etapa implementados.
42 tests pasan. Acceso medido→READY 122 s y READY→ENTRY 74 s nominales;
98 muestras actuales inmóviles. Cada revisión conserva 1018 pares certificados,
54 avisos internos, cero UNRESOLVED y sin timeout. La configuración hardware y
runtime conserva sus hashes revisados. Preflight actual PASS, baterías45,3/46,8%,
paros liberados, cargador desconectado, VLA parado y comandosSDK sin publicadores.

Plan remoto de lectura comprobado: registro82ac1bc8…2e434e → previsto9d40ede9…5440fa;
20 nombres nuevos sin sobrescritura. No se ejecutó instalación, recarga o movimiento.
Se mantiene la distinción entre archivo preparado, instalado, cargado y ensayo
físico. Falta instalación con paro comprobado, activación supervisada, evidencia
de carga y protocolo/validación de despacho, seguimiento y parada de brazos.
No se emite habilitación a partir de un booleano ni de la prueba anterior de cabeza.

Receta versionada, archivos afectados, dependencias, backups/reversión, comandos
y punto de reanudación: [Paquete READY410 corregido](PAQUETE_READY410_CORREGIDO.md). Evidencia privada completa:
../Humanoide-vla-evidence/20260914_READY410_EXECUTOR/.
