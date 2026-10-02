# Corrección visual de posición antes de recoger

**02-10-2026 — revisión BOX-01-VISUAL-ALIGN-FRESH.** Reposo visual desde el
worker persistente, con el mismo validador y dos muestras nuevas de odometría.
Evita caducar la imagen durante arranque/cierre ROSA de otro proceso. Edad
máxima2s conservada, diagnóstico de edad antes de decidir. 700 pruebas offline
pertinentes pasan; revisión instalada PC, carga/ensayo PENDIENTES. Detalle al final.

**02-10-2026 — revisión BOX-01-VISUAL-ALIGN-PROGRESS.** El intento084706
confirma emparejamiento temporal y envía ajusteX+22,774mm, cancelado a4,009s.
Se reconoce una única recuperación inicial medible antes de mejorar la distancia
de entrada; el watchdog sigue siendo4s y no se renueva con oscilaciones repetidas.
VERIFICADO offline; nuevo ensayo PENDIENTE. Detalle al final.

**02-10-2026 — revisión BOX-01-VISUAL-ALIGN-TIME.** Corregido el rechazo
`BOX_ALIGNMENT_POSE_TIME_MISMATCH` del intento083606: las poses se adquieren
durante la detección y se emparejan con la imagen, en vez de exigir proximidad
con una consulta posterior al procesamiento. Se conserva el límite0,5s y se
comprueba estabilidad de todas las muestras intermedias. La detección y sus
parejas quedan registradas antes de decidir continuar. VERIFICADO offline;
carga/ensayo de esta revisión PENDIENTES. Detalle y reversión al final.

**02-10-2026, Europe/Madrid — BOX-01-VISUAL-ALIGN. IMPLEMENTADO en PC;
VERIFICADO offline; carga remota y ensayo físico PENDIENTES.**

La entrada `scripts/optimistic_scenario1.sh --run` incorpora esta comprobación
dentro de `grasp`, antes de iniciar `local_front_box/separate_right_cruzr`.
Se activa automáticamente en `optimistic_v1`; las entradas standard conservan
su flujo. No añade preguntas ni etapas nuevas al checkpoint.

## Motivo y evidencia

El intento `20261002T081640Z_OPTIMISTIC_SCENARIO1_102007` llegó a get1 con
3,970 mm / 0,426°, dentro de 20 mm / 2°. La percepción posterior rechazó
X=0,7909284808515973 m, Y=0,09943778448581805 m, Z=0,31117874288896163 m:
X excedía 0,79 m por 0,928 mm. Llegar al waypoint del mapa no demuestra que
la caja esté dentro del intervalo visual de recogida. Los errores de lease
posteriores son del cierre tras el fallo, no el motivo original del rechazo.

Estos datos son históricos; no describen la postura actual. El XML nativo
prepara ambos brazos antes de consultar SPS, de modo que aquel rechazo no
demuestra HOME ni permite reiniciar automáticamente desde esa postura.

El replay numérico solicita X=+20,928 mm, Y=0 en base_link, para situar la
caja a X=0,77 m según esa medición. La componente positiva X corresponde a
acercarse a una caja demasiado distante; negativa, a alejarse de una demasiado
cercana. El objetivo se transforma al mapa con el yaw fresco del chasis.
La [fixture saneada](../../scripts/box_handling/fixtures/box_alignment_20261002.json)
incluye el SHA256 del diario original y el objetivo histórico, sólo para tests.
Nunca se usa esa pose archivada como objetivo físico.

## Secuencia y límites

1. Comprobar salud completa, reposo, consignas y brazos/torso medidos en HOME.
   El estado de entrada debe declarar abrazaderas vacías. El script no mide
   directamente presencia de caja en ellas; persiste la preparación presencial.
2. Verificar el hash de `cruzr/move_head_lower` y ejecutar esa tarea existente.
   Objetivo de cabeza 0/−0,43 rad; nueva salud exige esa postura, manteniendo
   brazos/torso en HOME. No se prepara todavía el agarre nativo.
3. Comprobar contenedores, dependencias, acción libre, mapa utars listo,
   puntos sin cambios, dos lecturas odométricas nuevas en reposo y pose estable.
4. Solicitar dos detecciones nuevas al socket del worker SPS instalado, usando
   cabeza/grasp/workbin y TF del instante exacto. Se usa el mismo selector frontal
   del paquete, con coherencia ≤20 mm / 3° y sellos crecientes. La observación
   puede estar fuera del intervalo; nunca se entrega a Motion como éxito SPS.
   Durante cada captura se solicitan pares de poses nuevas al lector existente,
   mientras otro hilo espera al worker perceptivo independiente. Sólo el hilo
   principal usa el protocolo secuencial de salud. Para cada imagen se eligen
   las dos poses de sello más cercano, ambas a ≤0,5 s; no se exige que una
   consulta posterior al procesamiento sea contemporánea de la exposición.
   Toda la serie, incluidos extremos e intermedios, debe mantenerse dentro de
   5 mm / 1° respecto de la entrada. La referencia final del objetivo se obtiene
   de una consulta nueva y el guard vuelve a comprobar su correspondencia con
   poses frescas antes de mover. No se transforma una pose histórica en permiso
   de llegada. Cada captura tiene límite12s y la serie ≤256 muestras; después
   del reposo final se exige edad de la segunda detección ≤2s. Los límites de
   frescura del lector ordinario, percepción/SPS y guard permanecen vigentes.
5. Si X/Y cumplen el gate, continuar sin mover el chasis. Si alguno lo supera,
   corregir únicamente los ejes incumplidos: objetivo 20 mm dentro de la cara
   correspondiente de [.41,.79] / [−.39,.39] m. Z fuera de [.01,1.49] m aborta;
   no hay ajuste de elevador para compensarlo. Z en base_link no es altura al suelo.
6. Enviar `navigation_start/free_nav` al objetivo medido, conservar yaw final
   y vigilar con el guard existente mapa/odom, velocidad, recorrido, progreso,
   frescura, frames, salud, heartbeat, lease y cancelación por UUID propio.
   Solicitud de velocidad 0,05/0,01 m/s y 0,15 rad/s, sin asumir que el controlador
   las respete. Monitor ≤0,10 m/s, giro ≤0,60 rad/s al aproximar y ≤1,20 rad/s
   únicamente dentro de **5 mm** del objetivo, con traslación ≤0,02 m/s.
   get1 conserva su umbral anterior de 20 mm. La trayectoria nativa puede
   describir un arco; los ejes se refieren al desplazamiento del objetivo final.
7. Exigir resultado exitoso, dos muestras nuevas de reposo y llegada medida
   ≤5 mm / 2°, después repetir toda la medición visual. Comparar geometría de
   caja en el mapa con la referencia inicial, ≤20 mm / 3°, para impedir que el
   cambio de chasis se confunda con cambio de caja. Es asociación geométrica,
   no prueba de identidad física si otra caja ocupa una pose indistinguible.
8. Permitir como máximo dos correcciones, con mejora del exceso ≥2 mm cuando
   siga fuera del gate, ≤50 mm por objetivo y **≤50 mm de desplazamiento
   solicitado acumulado**. Presupuesto global 70 s y por navegación ≤30 s.
   El guard conserva además excursión ≤80 mm y recorrido ≤120 mm **por acción**;
   50 mm solicitados no son una cota de recorrido real ni distancia de frenado.
9. Cuando una nueva medida cumpla el gate, guardar una referencia de comparación
   y ejecutar el agarre nativo una vez. Su adaptador conserva las dos capturas,
   el gate XYZ original y comparación con esa referencia antes de entregar la
   selección. Una nueva desviación o cualquier fallo nativo detiene el ciclo.

No se reintenta un agarre fallido, navegación rechazada, pérdida de salud/datos,
ambigüedad, cambio de mapa/geometría de caja ni violación de vigilancia. No se amplían
los límites, recortan coordenadas, cambia de caja para pasar el gate, relocaliza
durante el ajuste ni envía HOME automáticamente al fallar.

## Fuentes y activación

Fuentes PC: [planificador](../../scripts/box_handling/scenario1_box_alignment.py),
[supervisor](../../scripts/box_handling/scenario1_runtime.py),
[guard de navegación](../../scripts/box_handling/scenario1_nav_correction.py),
[CLI](../../scripts/box_handling/scenario1_cli.py),
[consola](../../scripts/box_handling/scenario1_console.py) y
[entrada](../../scripts/optimistic_scenario1.sh). Se transmiten en memoria en
la siguiente sesión, al host Motion y cliente nativo del contenedor redescubierto.
El socket de percepción conserva 0600/root: el supervisor lo consulta desde
su contenedor, sin cambiar permisos. Biblioteca vendor, SDK, XML/YAML y seis
fuentes del paquete SPS permanecen intactos; ID **bf145fa17e1116fc** verificado
localmente. No necesita instalación SPS, recarga ni reinicio.

Nueva dependencia de cabeza, leída en `--check` cuando hay agarre pendiente y
de nuevo inmediatamente antes de usarla:
`/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/cruzr/move_head_lower.xml`,
SHA256 `f3a73626f97b471d4a0a03c98c24de32243651116c497328e69b5ddc57ea46c1`.
La lectura histórica `held-check` del 01-10 confirma el signo de posición
del actuador1002 (−0,431336 rad) usado en este gate; no es estado físico actual.
Evidencia saneada: `head-actuator-contract-readonly.json`.
No se agrega a la identidad persistida de dependencias: las reanudaciones de
cajas ya sujetas/liberadas conservan sus contextos anteriores y no usan esta
preparación. Se mantienen todas las comprobaciones de contexto originales.

Evidencia de sesión: `box_alignment` en `events.jsonl`, estado de intención
`box-alignment.json` antes de mover y resultado medido después, referencia
`box-alignment-reference.json`, además del checkpoint original `grasp` en curso.
Los archivos viven en la carpeta temporal privada de la sesión Motion; las
observaciones y objetivos también quedan en el diario PC. No representan una
autorización reutilizable ni éxito de recogida.

Uso reproducible:

```bash
# Sólo plan local:
./scripts/optimistic_scenario1.sh --plan
# Lectura técnica actual, sin adaptadores, detección ni movimiento:
./scripts/optimistic_scenario1.sh --check
# Nueva ejecución, sólo con entrada física preparada y comprobada:
./scripts/optimistic_scenario1.sh --run --stop-after grasp
```

Para un fallo anterior, conservar el checkpoint y revisar la recuperación
específica: la postura preparatoria de brazos no pasa este nuevo requisito de
HOME. No usar un ciclo desde cero para recuperarla. La guía de
[reanudación por etapa](FORCE_IMPROVED_SCENARIO1.md#reanudación-por-etapa--28-09-2026)
continúa vigente; una entrada `grasp` explícita exige brazos/torso HOME medidos.

## Verificación, respaldo y reversión

Pruebas reproducibles, sin robot:

```bash
python3 -B -m unittest scripts.box_handling.test_scenario1_box_alignment \
  scripts.box_handling.test_scenario1_navigation_correction \
  scripts.box_handling.test_scenario1_perception \
  scripts.box_handling.test_scenario1_optimistic
bash -n scripts/optimistic_scenario1.sh
git diff --check
```

La suite de `scripts/box_handling/test_*.py` excluye sólo
`test_scenario1_deposit_install`, con fallos legacy documentados previamente.
**675 pruebas correctas, cero fallos/errores**, incluidas 27 específicas del
ajuste. Sintaxis Python/shell, planes y diff-check correctos. Resultado y módulos exactos: `tests.json` / `tests.log` en la evidencia
externa `../Humanoide-vla-evidence/20261002_BOX_AXIS_REPOSITION/`.
`replay.json` verifica el caso original exacto; `before-manifest.json`,
`before/`, `after-manifest.json` y `after/` conservan fuentes/hashes de esta
intervención, incluidos archivos locales nuevos sin commit.

Cambios persistentes: sólo fuentes/pruebas/documentación PC. Instalado en PC:
sí; cargado en Motion/cliente nativo: **PENDIENTE**; probado físicamente:
**PENDIENTE**. Esta intervención no conectó al robot, envió detecciones,
movimientos, HOME, reinicios ni cambios de mapa. La prueba de depósito90 del
01-10 no cualifica esta nueva maniobra visual. Falta ensayar dirección, giro,
seguimiento, parada y retorno de percepción con zona y persona junto al paro.

Rollback de software sin sesiones consumidoras: restaurar selectivamente los
archivos modificados desde `before/`, retirar el planificador/test/fixture nuevos
y revertir estas notas, preservando cambios posteriores. No restaurar contexto,
checkpoints, cachés o archivos remotos. Vuelve el rechazo sin ajuste automático;
el gate SPS instalado sigue vigente. Sin commit/push.

## Revisión temporal del intento083606

**OBSERVADO en evidencia histórica**, no estado actual: llegada get1
2,071mm/0,365°; preparación `cruzr/move_head_lower` SUCCEED. Última salud previa
al fallo: cabeza1002 −0,430665rad; brazos máximo0,000959rad y velocidad0.
El diario no envió agarre nativo ni ajuste de chasis después de preparar cabeza.
Las consultas de pose antes/después de las capturas difieren3,140683s, con deriva
entre extremos0,003904mm / 0,009393°. Esto no prueba inmovilidad durante todo el
intervalo; por eso la revisión vigila también las posiciones intermedias.

**VERIFICADO en código:** la versión anterior comparaba el sello de la segunda
imagen con el último sello de la consulta posterior. El procesamiento de visión
puede romper esa coincidencia aunque los datos sean válidos. El sello exacto
de imagen no se archivó antes de ese fallo: delta real y desglose de la latencia
PENDIENTES; no se atribuye el fallo a congelación de pose o reloj del robot.

Fuentes de esta revisión: supervisor, planificador temporal y su suite de tests,
todos enlazados arriba. No cambia worker SPS/health, contenedores, parámetros,
límites de movimiento ni el protocolo de reanudación. Los eventos
`box_alignment_capture` archivan cada observación recibida antes de la
comparación; `box_alignment_time_pair` conserva sellos, delta y poses elegidas,
además de la referencia actual. Los fallos de emparejamiento incluyen imagen,
delta al sello más cercano y número de muestras.

Respaldo exacto del árbol local anterior, incluidos cambios sin commit de la
primera intervención: `../Humanoide-vla-evidence/20261002_BOX_ALIGNMENT_TIME_PAIR/`.
`incident-summary.json` conserva el diagnóstico saneado y hash del diario;
`before/`, `after/` y manifiestosSHA256 reproducen esta revisión. Pruebas/resultados
en `tests.json`/`tests.log`: **680 pruebas correctas**, incluidas32 específicas
del ajuste; misma exclusión legacy de la primera intervención. Sintaxis, plan
local y diff-check correctos; misma receta offline anterior. Reversión únicamente
de esta revisión: restaurar selectivamente supervisor, planificador y test desde
ese `before/`, y sus notas documentales, preservando cambios posteriores. Mantiene
el ajuste visual anterior con su defecto de adquisición; no restaura estados
remotos ni permite reiniciar un ciclo interrumpido. Sin conexiones ni movimientos
del agente; el ensayo con detección real y posterior ajuste sigue PENDIENTE.

## Revisión de progreso del intento084706

**02-10-2026, Europe/Madrid — OBSERVADO histórico:**
`20261002T084706Z_OPTIMISTIC_SCENARIO1_181758` pasa get1, visión y cabeza.
La revisión temporal anterior queda cargada y observada:38 poses; parejas de
imágenes con delta máximo62.036.696/62.324.032ns, dentro de0,5s.
Solicita X+22,774352mm, sin Y, y el navegador acepta el objetivo.
El error de distancia en mapa parte de22,774352mm, alcanza29,500645mm a1,632s
y vuelve a26,466501mm a2,900s. Cancela a4,009s con22,301181mm restantes:
mejora neta0,473171mm, menor que2mm, y fuera de llegada5mm.
La vigilancia anterior comparaba sólo con su referencia de mejor progreso,
por lo que esa recuperación del alejamiento permitido no renovaba el contador.

Odómetro: recorrido acumulado43,448mm, excursión máxima25,600mm; mapa:
recorrido14,368mm, excursión6,730mm. Son métricas en frames separados, no
posiciones restables ni confirmación de llegada. Velocidades máximas0,028452m/s
y0,018908rad/s; avisos LOCATION_LOST recibidos. **INFERENCIA:** maniobra inicial
nativa y/o estimación de localización pueden explicar el alejamiento/retorno;
causa y discrepancia mapa/odom **PENDIENTES**, porque el guard anterior no
archivaba poses individuales. La revisión las añade sin autorizar llegada por
odometría ni restaurar localización durante movimiento.

Cancelación del UUID propio aceptada con return_code0, resultado terminal5 y
`FSM_Navigating onCancel and stop`. Esto no verifica parada física. No se
envió agarre nativo, reintento ni HOME después. Los errores de lease son
posteriores al fallo primario. El checkpoint conserva box_state=unknown y
grasp fallido; no autoriza reiniciar el ciclo desde un estado físico inferido.

**Cambio local:** el guard reconoce una única recuperación inicial en
`box_pickup`, si el pico se alejó≥2mm de la entrada y después la distancia
disminuye≥2mm desde ese pico. Sólo antes de progreso neto y de fase final.
Esta recuperación renueva una vez el mismo contador de4s; no eleva umbrales
de tiempo/velocidad/distancia ni añade reintentos. Un chasis inmóvil o que sólo
se aleja sigue abortando a4s; retrocesos y retornos posteriores no renuevan
esa recuperación. Mejoras netas posteriores de2mm conservan la regla existente.
get1 conserva su comportamiento. Se mantienen presupuesto30s/70s, empeoramiento
máximo15mm respecto al mejor error, excursión80mm, recorrido120mm, frescura,
salud, velocidades, llegada5mm/2°, reposo, nueva visión y gate XYZ original.

Fuentes exactas: [guard](../../scripts/box_handling/scenario1_nav_correction.py),
[consola](../../scripts/box_handling/scenario1_console.py),
[tests de vigilancia](../../scripts/box_handling/test_scenario1_nav_correction.py),
[tests de consola](../../scripts/box_handling/test_scenario1_console.py) y
[fixture saneada](../../scripts/box_handling/fixtures/box_alignment_progress_20261002.json).
La fixture conserva tiempos/distancias del diario y su SHA256. Los tests
proyectan esas distancias en un eje sintético, con yaw/odom sintéticos: no son
replay de poses originales ni demuestran que el navegador termine la maniobra.
La regresión comprueba que desaparece este aborto prematuro, y que un bloqueo
posterior, oscilación, exceso físico o datos obsoletos todavía abortan.
Resumen nuevo: last_pose por frame, progress_ns/progress_distance_m y
pickup_recovery con distancia inicial/pico/sello del único uso. La consola
muestra «código0» sin convertirlo en confirmación de parada física.

Verificación reproducible sin robot:

```bash
python3 -B -m unittest scripts.box_handling.test_scenario1_nav_correction \
  scripts.box_handling.test_scenario1_console \
  scripts.box_handling.test_scenario1_correction_transport
./scripts/optimistic_scenario1.sh --plan
bash -n scripts/optimistic_scenario1.sh
git diff --check
```

**690 pruebas correctas**, misma suite/exclusión legacy ya documentada,
incluidas9 nuevas de vigilancia y1 de consola; sintaxis/plan/diff-check correctos.
`tests.json` registra módulos y resultados exactos. Backup del árbol local
previo sin perder cambios sin commit, manifiestos SHA256 antes/después,
diagnóstico con hash del diario y checks:
`../Humanoide-vla-evidence/20261002_BOX_ALIGNMENT_PROGRESS/`.
Destinos: sólo fuentes PC, transmitidas en memoria al cliente nativo Motion
en la próxima sesión autorizada. Dependencias/SDK/paquete SPS intactos; no
requiere instalación/reinicio. Instalado en PC: sí; cargado en robot/probado
físicamente **de esta revisión: PENDIENTES**. El ensayo anterior sólo demuestra
activación hasta el objetivo correctivo, no éxito de corrección/agarre.

Reversión selectiva: restaurar guard/consola y sus tests desde `before/`, retirar
fixture nueva y restaurar notas correspondientes; preservar cambios posteriores
y no restaurar checkpoints ni estados remotos. Devuelve el cálculo anterior
de progreso, manteniendo la revisión temporal. Reanudación: conservar evidencia
y aplicar recuperación específica con postura/caja/parada comprobadas; no
reintentar automáticamente la acción cancelada. Sin conexiones, movimientos,
cambios remotos, commit ni push por el agente.

## Revisión de frescura del intento085958

**02-10-2026, Europe/Madrid — OBSERVADO histórico:**
`20261002T085958Z_OPTIMISTIC_SCENARIO1_215101` pasa get1 (5mm/0,43°), visión
y cabeza. Capturas coherentes, emparejadas con poses a67,320/52,869ms. La segunda
imagen tiene sello1790931604911903000ns; pose seleccionada base_link:
X0,787601691/Y0,114263272/Z0,311893826m, dentro del gate original en ese instante.
No se llegó a enviar ajuste de chasis ni agarre nativo. La prueba de recuperación
de progreso anterior no se ejercitó en este intento.

Edad de imagen al registrar recepción:1,135722s; tras adquirir las poses
posteriores:1,315706s. Consulta final de reposo:0,903138s desde ese registro
hasta su devolución, desglosados0,772748s hasta comenzar adquisición de odometría,
0,051459s para dos muestras y0,078930s hasta devolver/registrar el resultado.
Imagen≥2,218844s tras reposo y2,223167s al registrar el error. El guard anterior
no guardaba su instante exacto de comprobación; esos extremos demuestran que
el límite2s ya se había superado. Salud/lease fallan después durante cierre;
no son la causa primaria de `BOX_ALIGNMENT_DETECTION_STALE_BEFORE_DISPATCH`.

**VERIFICADO en código:** el gate ejecutaba un proceso nuevo con ROSA para
cada lectura de reposo. El coste de lanzamiento/retorno posterior a las capturas
agotaba su frescura. Se sustituye el transporte de esa lectura por una petición
`base` al worker de salud ya abierto. La primera petición crea una suscripción
read-only /mc/odom, nav_msgs/msg/Odometry, QoS SensorData/bestEffort/volatile/
keepLast5; las siguientes reutilizan el lector, sin reutilizar sus muestras.

Cada petición crea la misma `scenario1_resume_worker.Acquisition` original,
importada en memoria sin iniciar ROSA. Conserva dos sellos/recepciones posteriores
a la petición, avance temporal, tratamiento de duplicados, frames, cuaternión,
edad máxima0,5s, único publicador, velocidades≤0,003m/s/0,01rad/s y estabilidad
≤5mm/1°. Plazo máximo5s. Datos viejos, movimiento, leases, falta/ambigüedad de
publicadores y errores siguen bloqueando. Odómetro no entra en la caché live
de salud; se conserva el único hilo de peticiones de telemetría durante capturas.
Los flujos health/pose y el worker standalone de reanudación no cambian.
La imagen sigue limitada a2s: un procesado lento todavía aborta. El nuevo evento
`box_alignment_freshness` registra sello/edad/límite antes de comprobarlo;
el error incluye age_ns. No se reintenta una captura o acción fallida.

Fuentes PC: [runtime](../../scripts/box_handling/scenario1_runtime.py),
[worker persistente](../../scripts/box_handling/scenario1_health_worker.py),
[payload](../../scripts/box_handling/scenario1_cli.py),
[tests de integración visual](../../scripts/box_handling/test_scenario1_box_alignment.py) y
[tests de telemetría](../../scripts/box_handling/test_scenario1_health_worker.py).
Dependencia adicional embebida: [validador original sin cambios](../../scripts/box_handling/scenario1_resume_worker.py).
SDK, tareas/XML/YAML, SPSbf145fa17e1116fc y parámetros nativos intactos.
Destinos: estas fuentes PC; próxima sesión transmite health worker al cliente
Motion/contenedor redescubierto. Lector se activa al primer gate base; --check
no lo crea. No requiere instalar archivos persistentes ni reiniciar contenedores.

Verificación reproducible sin robot:

```bash
python3 -B -m unittest scripts.box_handling.test_scenario1_health_worker \
  scripts.box_handling.test_scenario1_box_alignment \
  scripts.box_handling.test_scenario1_optimistic
./scripts/optimistic_scenario1.sh --plan
bash -n scripts/optimistic_scenario1.sh
git diff --check
```

**700 pruebas pertinentes correctas**, cero fallos/errores, con la misma
exclusión legacy test_scenario1_deposit_install documentada anteriormente.
Diez nuevas comprueban transporte persistente, dos muestras nuevas por petición,
datos previos/duplicados/movimiento/frescura/publicadores/lease, creación única
del lector, caché live intacta y payload importable sin ROSA. La prueba de latencia
simula imagen1,14s + poses0,18s: reposo0,05s permite continuar; reposo0,91s
todavía aborta sin movimiento. Es regresión sintética, no medición de latencia
de esta revisión instalada en robot. Sintaxis/plan/diff-check correctos.

Respaldo íntegro anterior/final de fuentes modificadas y notas, SHA256, estado
Git, tests.json/tests.log, plan.json y incident-summary.json con hash del diario:
`../Humanoide-vla-evidence/20261002_BOX_ALIGNMENT_FRESH_DISPATCH/`.
Instalado PC: sí; cargado en Motion y probado físicamente **de esta revisión:
PENDIENTES**. Esta intervención no conecta al robot, cambia configuración remota
ni envía detecciones, comandos físicos o HOME. El ensayo histórico demuestra
adquisición temporal, no éxito de ajuste/agarre ni estado físico actual.

Rollback selectivo desde before/ de runtime/health worker/CLI, sus tests y estas
notas, preservando cambios posteriores. Vuelve la consulta standalone de reposo;
mantiene correcciones temporal/de progreso anteriores. No restaura checkpoints,
sesiones, permisos ni estados remotos. Reanudar sólo tras verificar físicamente
parada/postura/caja según el modo de recuperación correspondiente. Sin commit/push.
