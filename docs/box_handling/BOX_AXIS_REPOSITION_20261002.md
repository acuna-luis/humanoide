# Corrección visual de posición antes de recoger

**02-10-2026 — revisión BOX-01-VISUAL-ALIGN-ASSOCIATION.** Asociación entre
posturas mediante media de cada pareja coherente en odometría local; mantiene
20mm/3° y última pose original para SPS. Sustituye asociación de últimas
capturas en mapa citada en revisiones históricas. Replay real19,290mm/2,120°;
715 pruebas pertinentes pasan. Instalado PC; nueva carga/ensayo PENDIENTES.

**02-10-2026 — revisión BOX-01-VISUAL-ALIGN-ARRIVAL.** Llegada terminal12mm/2°
para volver a observar la caja tras éxito/reposo nativo; sustituye el criterio
PC de5mm citado en revisiones históricas. Ventana5mm del guard para giro rápido
intacta. Sólo nueva visión/gateXYZ permite recoger o usar el segundo ajuste
presupuestado. 708 pruebas pertinentes pasan; nueva carga/ensayo PENDIENTES.

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
7. Exigir resultado exitoso, dos muestras nuevas de reposo y llegada terminal
   ≤12 mm / 2° en dos poses nuevas estables; después repetir toda la medición visual.
   Este criterio de precisión del mapa no autoriza el agarre. Comparar la media
   geométrica de cada pareja coherente usando odometría local con la referencia
   inicial, ≤20 mm / 3°, para impedir que el
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
los límites XYZ/de movimiento, recortan coordenadas, cambia de caja para pasar el gate, relocaliza
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

## Revisión de llegada del intento091156

**02-10-2026, Europe/Madrid — OBSERVADO histórico:**
`20261002T091156Z_OPTIMISTIC_SCENARIO1_244792` llega get1 a10,7mm/0,41°,
prepara cabeza y mide cajaX0,792649615m. Edad de segunda imagen0,993809s:
la revisión de frescura anterior está cargada y se observa en este intento.
Solicitud de correcciónX+22,649615mm en base_link, Y0. Objetivo mapa:
X1,674653343/Y0,290748126m, yaw1,606405957rad. Navegación status4/SUCCEEDED.
La recuperación inicial de progreso se usa una vez; distancia máxima inicial
30,759mm y distancia al resultado2,039mm. Reposo confirmado por el guard, dos
muestras posteriores al terminal; después del asentamiento la distancia de
mapa es9,630466mm. Las dos poses solicitadas por el supervisor confirman
9,629522/9,629890mm y0,451711/0,452175°. Ese error explica el rechazo5mm PC.

Odómetro: recorrido87,220mm y excursión máxima68,271mm, dentro de120/80mm.
En asentamiento la pose de mapa cambia mientras odometría queda en reposo;
no atribuir esa diferencia sólo a frenado/desplazamiento real. **INFERENCIA:**
precisión del controlador y/o actualización de localización explican el error
residual; el diario por sí solo no separa sus causas. El análisis histórico
[ArcPrecise](ARC_PRECISE_ARRANQUE_20260922.md) documenta tolerancia0,012m e
histéresis0,005m. No se consultó hoy la configuración remota ni se modificó.
No se capturó la caja después del ajuste; su posición final/gate son **PENDIENTES**.
No se envió agarre nativo, segunda corrección ni HOME.

**Cambio local:** criterio terminal de precisión5→12mm, yaw2° conservado,
dos poses nuevas y estabilidad5mm/1°; sólo después de acción exitosa y reposo
medido por el guard. Un resultado fuera de12mm/2° sigue abortando antes de
capturar/recoger. Este cambio no se aplica a `distance_tolerance` del guard:
la ventana que permite giro final rápido conserva5mm; vigilancia física,
frescura, empeoramiento15mm, excursión80mm, recorrido120mm, velocidades,
watchdogs, paros y cancelación permanecen intactos. get1 tampoco cambia.

Pasar ese criterio terminal sólo habilita nueva doble detección con salud,
postura, reposo, asociación geométrica de caja en mapa≤20mm/3°, TF exacta y
frescura originales. Si caja cumple XYZ, prepara referencia comparativa y el
agarre nativo vuelve a detectar/validar sin recibir una pose archivada como
autorización. Si sigue fuera, exige mejora≥2mm y permite únicamente el segundo
objetivo ya previsto, con límite50mm solicitado acumulado/70s. Fallos nativos,
de salud, identidad, datos, presupuesto o mejora siguen deteniendo el ciclo.
La consola muestra distancia/yaw terminales y «Se vuelve a medir la caja».

Fuentes modificadas: [planificador/gate terminal](../../scripts/box_handling/scenario1_box_alignment.py),
[runtime](../../scripts/box_handling/scenario1_runtime.py),
[consola](../../scripts/box_handling/scenario1_console.py),
[tests](../../scripts/box_handling/test_scenario1_box_alignment.py) y
[fixture histórica](../../scripts/box_handling/fixtures/box_alignment_arrival_20261002.json).
Policy congelada explicita max_arrival_distance_m0,012 y max_arrival_yaw_deg2.
Plan local expone esos valores; caller no puede inyectar una policy más amplia.
Fixture conserva objetivo/poses reales, métricas y SHA256 del diario, saneados.
Las posiciones de caja posteriores en tests son sintéticas, no resultados
físicos del ensayo. Nueva revisión instalada en PC; carga Motion/cliente nativo
y validación física **PENDIENTES**. Revisiones anteriores sí observadas hasta
navegación/reposo; éxito de ajuste visual completo/agarre no demostrado.

Receta offline:

```bash
python3 -B -m unittest scripts.box_handling.test_scenario1_box_alignment \
  scripts.box_handling.test_scenario1_nav_correction \
  scripts.box_handling.test_scenario1_optimistic
./scripts/optimistic_scenario1.sh --plan
bash -n scripts/optimistic_scenario1.sh
git diff --check
```

**708 pruebas pertinentes pasan**, cero errores/fallos; misma suite/exclusión
legacy test_scenario1_deposit_install. Ocho nuevas cubren replay exacto de
poses9,63mm, límites inclusivos12mm/2°, no finitos/cantidad/estabilidad/yaw,
ventana de giro5mm intacta, nueva visión antes de agarre, segundo ajuste visual
(47,2mm solicitados totales), fallos de identidad/yaw/mejora y residual visible.
Sintaxis, plan local y diff-check correctos. Evidencia, módulos/resultados,
respaldo anterior/final y manifiestosSHA256:
`../Humanoide-vla-evidence/20261002_BOX_ALIGNMENT_VISUAL_ARRIVAL/`.

Activación: próxima sesión optimista autorizada transmite helpers en memoria
a Motion/cliente en contenedor redescubierto, sin instalación remota/reinicio.
Dependencias/SDK/vendor/SPSbf145fa17e1116fc/XML/YAML/mapa intactos. Esta intervención
no conecta al robot ni envía detecciones, comandos físicos o HOME.
Rollback: restaurar selectivamente los tres scripts/test/notas desde before/,
retirar fixture nueva y conservar cambios posteriores; vuelve llegada5mm PC,
manteniendo revisiones anteriores. No restaura estados remotos/checkpoints.
Punto de reanudación: conservar diario/checkpoint y comprobar físicamente
parada/postura/caja para recuperación específica, sin inferir estado actual
del ensayo ni reiniciar automáticamente un ciclo fallido. Sin commit/push.

## Revisión de asociación del intento092429

**02-10-2026, Europe/Madrid — OBSERVADO histórico:**
`20261002T092429Z_OPTIMISTIC_SCENARIO1_275930` solicitaX+23,953mm, termina
navegación exitosa/reposo y pasa llegada6,8mm/0,45°. Capturas iniciales:
X0,792248/0,793953m; posterioresX0,746606/0,743580m. Cada pareja pasa20mm/3°
con chasis quieto, TF exacta, sellos crecientes y edad0,719/0,739s tras reposo.
La última caja observada cumpleXYZ. Fallo posterior: comparar únicamente las
últimas selecciones transformadas al mapa da29,625624mm. No se envió agarre,
segunda corrección ni HOME; errores de lease son del cierre después del rechazo.

Mapa y odometría dan desplazamientos distintos. Cambiar sólo al último par
odométrico da21,957063mm y tampoco pasa20mm; no se omite ese resultado.
**INFERENCIA:** ruido de detección entre vistas y actualización del mapa pueden
contribuir a la discrepancia. No es una calibración de VSLAM/odometría ni prueba
de identidad de caja. Los índices2 de las capturas no constituyen identidad.
La media de las dos posiciones coherentes de cada postura, con orientación
promediada tras normalizar/alinear el signo de cuaterniones, da en odometría
local **19,289749mm/2,120403°**, dentro de los mismos20mm/3°.

**Cambio local:** sólo la asociación entre posturas usa esas medias diagnósticas
y odometría local. La comparación fija el ancla inicial para todos los ajustes;
no la mueve incrementalmente para tolerar deriva acumulada. Usa los informes
de reposo ya existentes antes/después de cada pareja; no añade detecciones,
consultas ROS, reinicios ni publicadores. Revalida forma/sellos/frame/velocidades
de las muestras y edad en su instante de finalización registrado; las recepciones
reales/lease fueron validadas en el worker original y no se inventan sellos nuevos.
Exige odom→base_link/base_footprint, frames iguales dentro de los informes y
entre posturas, dos muestras posteriores a cada petición y frescura0,5s,
reposo0,003m/s/0,01rad/s, estabilidad5mm/1° dentro de cada postura. Las comprobaciones
de odometría deben encerrar temporalmente las dos imágenes. Sigue verificando
mapa estable y asociación temporal de las imágenes con las poses durante captura.

Son coordenadas de comparación: XY/yaw en odometría planar y Z relativo a
base_link con cuerpo en HOME; no una pose absoluta3D para Motion. La diferencia
vertical fija base_link/base_footprint se cancela entre posturas. La consulta
histórica [21-09](GET1_PUT1_MAPA_Y_EJECUTOR.md#2026-09-21-1303-europemadrid--box-01-select-pila-apartada-objetivo-primero)
observó mismoXY y diferenciaZ0,13m; no es comprobación de TF actual de esta
intervención. Se mantienen torso/brazos HOME y el uso exclusivamente diagnóstico.
Un cambio/reset de frame o desplazamiento incompatible sigue rechazando.

La media lleva comparison_only=True y nunca sustituye selection.selected_pose
del último resultado original. Correcciones siguen calculadas con esa medición
original, en X/Y, y mapa fresco. La referencia de agarre sigue exactamente la
segunda captura original; adaptador nativo vuelve a detectar y conserva el gate
XYZ/TF/frescura/consistencia de sus capturas antes de entregar una pose a Motion.
No cambia2cm/3°, gateXYZ, llegada12mm/2°, ventana5mm para giro, guard físico,
salud, watchdogs, cancelación, dos objetivos/50mm solicitados/70s o criterios
de mejora. Medias no pueden esconder una pareja incoherente: se valida antes
de promediar. Una asociación geométrica válida no demuestra identidad física.

Fuentes/destinos PC: [planificador](../../scripts/box_handling/scenario1_box_alignment.py),
[runtime](../../scripts/box_handling/scenario1_runtime.py),
[payload](../../scripts/box_handling/scenario1_cli.py),
[tests](../../scripts/box_handling/test_scenario1_box_alignment.py) y
[fixture saneada](../../scripts/box_handling/fixtures/box_alignment_association_20261002.json).
Dependencia pura [scenario1_resume_worker](../../scripts/box_handling/scenario1_resume_worker.py)
sin cambios, cargada ahora también en supervisor antes del planificador; ROSA
sigue importándose sólo al ejecutar lectores. El runtime borra asociación previa
al empezar una medición y registra geometría/frame/base usados. Evento
box_alignment_association archiva resultado o causa con ambos extremos al fallar.
No se reutiliza como permiso persistido ni de una sesión anterior.

Receta offline:

```bash
python3 -B -m unittest scripts.box_handling.test_scenario1_box_alignment \
  scripts.box_handling.test_scenario1_optimistic \
  scripts.box_handling.test_scenario1_resume_runtime
./scripts/optimistic_scenario1.sh --plan
bash -n scripts/optimistic_scenario1.sh
git diff --check
```

**715 pruebas pertinentes correctas**, cero errores/fallos; misma exclusión
legacy test_scenario1_deposit_install. Siete nuevas cubren replay con cuatro
capturas/informes reales, medias y signos de cuaterniones sin mutar originales,
frames/relojes/muestras/reposo/frescura/bracketing, límites20mm/3°, caja cambiada,
pareja incoherente y flujo hasta agarre simulado con última poseX0,743580m intacta.
No se reproduce un éxito físico: la prueba usa acciones Mock. Sintaxis, plan y
diff-check correctos. Fuentes, hashes antes/después, diario saneado con SHA256,
association-replay.json, tests.json/tests.log y plan.json:
`../Humanoide-vla-evidence/20261002_BOX_ALIGNMENT_ODOM_ASSOCIATION/`.

Instalado PC: sí; carga Motion/cliente nativo y prueba física de esta revisión
**PENDIENTES**. Activación en próxima sesión optimista autorizada, transmisión
en memoria a contenedor redescubierto; sin instalación persistente/reinicio.
SDK/vendor/tareas/XML/YAML/SPSbf145fa17e1116fc/guard/percepción base intactos.
La discrepancia mapa/odom/cámara y su calibración siguen PENDIENTES; este cambio
no la corrige ni convierte un dato histórico en estado físico actual.
Rollback: restaurar selectivamente tres fuentes/test/notas desde before/ y
retirar fixture nueva, preservando cambios posteriores; vuelve asociación de
última captura en mapa. No restaurar checkpoint/leases/estados remotos. Reanudar
con recuperación específica y comprobación física de parada/postura/caja.
Sin conexión, movimientos, comandos HOME, commit ni push por el agente.

## Diagnóstico HOME del intento093621

**02-10-2026, Europe/Madrid — BOX-01-HOME-DIAGNOSTIC. OBSERVADO histórico;
IMPLEMENTADO PC; VERIFICADO offline con719 pruebas pertinentes y5 del clasificador.**

El diario `../Humanoide-vla-evidence/20261002T093621Z_OPTIMISTIC_SCENARIO1_305053/events.jsonl`
contiene dos muestras de actuadores con sellos1790933761.632769913 y
1790933761.652784627. Ambas pasan validación de cobertura, habilitación/fault,
velocidad y consigna del clasificador original, pero dan MEASURED_HOME=0.
Único eje fuera de HOME: head_pitch1002=−0,4307609799981366rad (−24,680°).
Cabeza yaw1001=−0,0002876214rad; máximo absoluto sin cabeza0,000958738rad,
velocidad corporal0 y máxima diferencia consigna/posición0,000958738rad.
HOME exige valor absoluto estrictamente menor de0,02rad en los20ejes, cabeza
incluida. El registro no contiene etapas ni acciones físicas de ese intento.
Checkpoint: completed=[], in_flight=null. No acredita que la caja esté libre
actualmente ni que siga siendo seguro cualquier movimiento de recuperación.

INFERENCIA: inclinación compatible con la preparación visual0/−0,43rad de
los intentos anteriores. Esto no es una medición actual ni un permiso para
iniciar el ciclo o ejecutar HOME. Los errores de lease son posteriores al
rechazo original durante el cierre del lector; no justifican alargar la lease.

El supervisor ahora informa head_pitch(1002)=−0.430761rad, límite |posición|<0.02rad
(y cualquier otro eje rechazado), con recuperación presencial antes de repetir.
Antes de generar ese detalle aplica el clasificador completo original: no
oculta faults, duplicados, ejes ausentes, movimiento ni consignas latentes.
Registra `home_not_measured`, sello de la muestra, clasificación y ejes fuera
de HOME antes de abortar. No amplía tolerancia ni acepta una cabeza de observación
como HOME, no envía objetivos de recuperación y conserva el requisito para las
dos muestras frescas. Las ruedas no forman parte de20D y sus posiciones no se
incluyen en el diagnóstico. Un control de salud sin exigir HOME sigue admitiendo
la postura observacional sólo cuando la etapa correspondiente lo permite.

### Continuación física

Antes de iniciar otra sesión, el operador debe comprobar efector/abrazaderas,
caja libre/sujeta/apoyada, contacto y obstáculos, paros, cargador/batería, ruedas,
modo y mando exclusivo, con una persona junto al paro. Si la postura nueva sigue
siendo sólo cabeza de observación con cuerpo HOME, recuperar la cabeza a0rad
con el control supervisado vigente y despejado; no sustituirlo por una trayectoria
completa de brazos/cuerpo. Esta intervención no descubre ni autoriza una nueva
orden remota para esa recuperación. No repetir HOME ni cambiar de modo como
prueba. Una recuperación distinta requiere determinar antes el estado real.

Después de la recuperación, comprobar con lecturas nuevas:

```bash
./scripts/optimistic_scenario1.sh --check
```

Sólo un check satisfactorio con HOME20D nuevo permite plantear el siguiente
`--run` desde abrazaderas vacías y recorrido preparado. Una reanudación de grasp
sigue exigiendo HOME20D y llegada get1; --recovery-confirmed no los omite.
El script general cruzr_recover_to_home.sh --check puede clasificar la ruta
histórica, pero su --run no es recuperación específica de cabeza: podría
retroceder el chasis y mover brazos en una ruta de caja reconocida. No se indica
como solución automática a este registro.

### Fuente, aplicación y reversión

Destino PC: scripts/box_handling/scenario1_runtime.py y su test_scenario1_runtime.py.
El CLI vigente transmite el supervisor y el clasificador en memoria a Motion
redescubierto durante la siguiente sesión autorizada. No se instala archivo,
reinicia contenedor ni se cambia XML/YAML/SDK en el robot. Instalado PC;
carga remota y verificación física del mensaje PENDIENTES.

- SHA256 scripts/box_handling/scenario1_runtime.py: `a7dde5b773039c1bb6a6ba484363b3fea55b65531b76b6318779cd02bc802902`.
- SHA256 scripts/box_handling/test_scenario1_runtime.py: `a81f8af351d32616083fd97d9cf404f33edd11833dd5665e34b10e30c4bce29a`.

Backup exacto previo y posterior, manifest SHA256, estado Git, incident-summary.json
y resultados en ../Humanoide-vla-evidence/20261002_BOX_HOME_DIAGNOSTIC/.
El backup previo preserva la revisión de asociación aún sin commit. Reversión:
restaurar selectivamente runtime/test/notas desde before/ comparando con el
árbol vigente, sin perder cambios posteriores; no restaurar HEAD completo,
checkpoints, estados de control ni revisiones anteriores de asociación.

Verificación reproducible local, sin ROS/red/robot:

```bash
python3 -m unittest scripts.box_handling.test_scenario1_runtime
python3 scripts/test_home_posture_gate.py
bash -n scripts/optimistic_scenario1.sh
./scripts/optimistic_scenario1.sh --plan
```

Nuevas regresiones de seguridad: cabeza observacional bloqueada sin comandos,
borde exacto0,02rad y alias de torso, fault prioritario, rechazo de la segunda
muestra fuera de HOME y controles sin HOME inalterados. El conjunto pertinente
excluye el test_scenario1_deposit_install legacy con errores ya documentados;
el listado exacto y resultados están en tests.json. Estado físico y éxito de
recogida tras las correcciones anteriores siguen PENDIENTES.

Resultado:719/719 pruebas pertinentes y5/5 del clasificador correctas; AST, bash -n,
plan local y git diff --check correctos. La primera ejecución de las cuatro
pruebas nuevas falló por sellos sintéticos anteriores a su consulta; corregidos
sólo los sellos del test, sin relajar frescura en producción. Registro conservado
en tests-initial-failed.txt. Sin conexión, movimiento, commit ni push del agente.

## Revisión de progreso odométrico del intento094521

**02-10-2026, Europe/Madrid — BOX-01-VISUAL-ALIGN-ODOM-PROGRESS.**
OBSERVADO histórico, IMPLEMENTADO PC, VERIFICADO offline; nueva carga/ensayo
físico PENDIENTES. No conexión ni movimiento del agente.

El intento `20261002T094521Z_OPTIMISTIC_SCENARIO1_327808` supera HOME inicial,
get1 (3,6mm/0,46°), visión y preparación de cabeza. Caja seleccionada original
X0,791200231m, Y0,107340655m, Z0,310717357m: se solicita X+21,200231mm;
el objetivo permanece en mapa. En la vigilancia el error de mapa sube desde
21,200mm hasta pico28,863mm y después baja sólo a27,095mm, sin mejorar2mm
respecto del pico. No se consume la concesión de recuperación inicial anterior.

A4,007992979s desde armado el guard cancela por no significant progress.
Recorrido acumulado: mapa9,757mm, odometría42,601mm; desplazamiento neto en
odometría25,800mm. La posición local relativa al objetivo pedido tiene error
4,599724mm. Máximos registrados0,026206119m/s y0,011344640rad/s; frames odom
y base_footprint. El mapa recibe sellos nuevos pero su XY permanece casi fijo
tras el primer retroceso mientras odometría avanza. Esto demuestra discrepancia
de estimaciones; no prueba por sí solo movimiento físico, causa, calibración o
parada. Pregunta al operador sobre retroceso/avance pendiente de respuesta al
cerrar esta intervención. No se usa odometría para afirmar llegada física.

Cancelación del UUID propio aceptada return_code0; resultado terminalstatus5,
FSM_Navigating onCancel and stop. Parada física no confirmada, sin agarre/reintento
ni HOME después. Errores de lease posteriores pertenecen al cierre. La postura
actual, estado de la caja y recuperación siguen PENDIENTES: no reiniciar el ciclo
a partir de este diario sin recuperación específica/comprobación presencial.

### Cambio de supervisión

En arm(), con los dos streams frescos y estacionarios existentes, el guard
calcula el desplazamiento objetivo dentro del frame mapa: objetivo−origen_mapa.
Rota ese vector por yaw_origen_odom−yaw_origen_mapa y lo ancla a origen_odom.
Eso expresa la misma solicitud relativa en odometría; nunca resta coordenadas
mapa/odom, modifica el objetivo físico ni publica un TF. Requiere box_pickup y
frames odom→base_link/base_footprint; get1 y frames desconocidos conservan el
comportamiento anterior. La correspondencia planar/yaw de la postura inicial
es una hipótesis del seguimiento local, no una calibración global demostrada.

Cada pose odométrica validada puede renovar el contador existente sólo si mejora
al menos2mm respecto del mejor error local que ya contó como progreso. No basta
moverse ni recorrer distancia: una dirección equivocada, volver al mismo mínimo,
oscilar o continuar más allá del objetivo no renuevan ese progreso. El crédito
es finito al aproximarse al objetivo; no hay renovación por entrar/salir de una
ventana de llegada local. Durante settling no se renueva por odometría.

El watchdog conserva4s desde la última mejora, tiempo de acción30s, total70s,
recorrido120mm y excursión80mm en ambos frames; empeoramiento de mapa≤15mm,
límites de velocidad/giro, sellos/frescura, frames estables, salud, lease y
cancelación quedan activos. Si el mapa no converge, se sigue cancelando después
de4s sin mejora nueva. La llegada terminal requiere éxito nativo, reposo y
nuevas poses de mapa≤12mm/2°, después nueva visión/coherencia/gateXYZ. La
ventana5mm de mapa del guard para giro rápido no cambia: cercanía odométrica
no habilita giro1,20rad/s ni autoriza llegada/agarre. No se intenta relocalizar
durante movimiento, alargar lease ni repetir una acción cancelada.

Logs nuevos: progress_source indica mapa u odom_relative_goal; pickup_odometry
incluye objetivo diagnóstico local, distancia actual, mejor error acreditado,
sello de progreso y arrival_authorized=false. progress_distance_m sigue siendo
el valor anterior en mapa; no se mezcla numéricamente con el error odométrico.

### Verificación, aplicación y reversión

La fixture versionada `scripts/box_handling/fixtures/box_alignment_odom_progress_20261002.json`
conserva spec, snapshots archivados y SHA256 del diario original. Replay de las
poses muestreadas reconoce progreso antes del punto de cancelación original,
con mapa todavía27,095mm y odometría local4,600mm, sin afirmar llegada/reposo.
No es replay completo DDS: la primera muestra estacionaria se reconstruye,
los snapshots sólo contienen últimas poses y los twists instantáneos del test
son sintéticos (reposo); los límites de velocidad se prueban separadamente.
No demuestra que la navegación nativa vaya a terminar o que la caja sea alcanzable.

Ocho regresiones nuevas: traza archivada, rotación entre frames/origen exacto,
reposo/dirección equivocada/subumbral, oscilaciones, sobrepaso/giro rápido,
gates de mapa/velocidad/excursión/frescura/frames, get1/frames desconocidos y
persistencia del aborto cuando el mapa no converge. Suite pertinente727/727
correcta; módulos exactos/exclusión del legacy test_scenario1_deposit_install
con errores previos constan en tests.json. AST, bash -n, plan local y diff-check
correctos. Las dos primeras pruebas nuevas fallaron por geometría sintética de
yaw fuera del gate y recorrido de oscilaciones>120mm; corregidos sólo los tests,
sin relajar gates de producción.

```bash
python3 -m unittest scripts.box_handling.test_scenario1_nav_correction \
  scripts.box_handling.test_scenario1_correction_transport \
  scripts.box_handling.test_scenario1_action_session
bash -n scripts/optimistic_scenario1.sh
./scripts/optimistic_scenario1.sh --plan
git diff --check
```

Destinos PC: guard/test/fixture y notas enlazadas. Activación: la próxima sesión
autorizada transmite el helper vigente en memoria al cliente Motion descubierto,
sin instalación ni reinicio. Instalado PC, carga remota y validación física de
esta revisión PENDIENTES; el ensayo anterior ya demuestra que la preparación y
el objetivo correctivo se enviaron, no éxito de agarre ni HOME final.

- SHA256 scripts/box_handling/scenario1_nav_correction.py: `68dcdf2cb8a91b673a5ee948c7f35c0fd2405800c99db93cc2ea3eecff15f131`.

- SHA256 scripts/box_handling/test_scenario1_nav_correction.py: `195945e422bbbb75aa09826e17750c238cfc4e65206d83e815a5404745458180`.

- SHA256 scripts/box_handling/fixtures/box_alignment_odom_progress_20261002.json: `75a4983128bc5cffb4555721722067c22f936dda42eb2a51fbc2e38fe23a4f18`.

Backup exacto before/ y after/, manifiestos previos/finales, estado Git,
incident-summary.json, tests.json/tests.txt y plan en
`../Humanoide-vla-evidence/20261002_BOX_ALIGNMENT_ODOM_PROGRESS/`.
Reversión selectiva de guard/test/notas desde before/ y retirada de la fixture
nueva; conservar las revisiones anteriores de asociación/HOME y cambios
posteriores. No restaurar checkpoint ni estado remoto. Sin commit ni push.
