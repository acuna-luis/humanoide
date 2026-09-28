# Ejecutor mejorado del escenario 1

28-09-2026, Europe/Madrid. **BOX-01-EXEC-IMPROVED — implementado en el PC.**
La supervisión optimizada y la corrección del lector de pose están verificadas
en lectura; el ciclo físico posterior sigue PENDIENTE. Los resultados históricos inferiores corresponden a sus
respectivas versiones, incluido un ciclo anterior ejecutado por el usuario.
[Corrección vigente y resultados](#corrección-de-pose-con-dos-publicadores--28-09-2026).
El preflight de lectura de la
versión anterior se verificó en robot a las09:06CEST. La lectura posterior de
autochecked también obtuvo una ventana válida de FT y articulaciones; devolvió55
por cualificación pendiente. Estas consultas no prueban el ciclo físico ni la
clasificación de caja. [Resultado de sensores](#lectura-real-de-sensores--28-09-2026).

**Corrección09:06 CEST:** descubrimiento de contenedores y lectura de estado
reparados. --check completa los gates técnicos y devuelve55 por mapa sin cargar
(`FSM_WAITSETMAP`); es preparación pendiente, no otro error de contenedores.
106 pruebas offline pasan. [Diagnóstico y evidencia](#corrección-de-descubrimiento-y-estado--28-09-2026).

El usuario solicita un ejecutor nuevo y pide explícitamente asumir la geometría
actual de `force_escenario1.sh`. Se conserva esta secuencia y sus parámetros:
get1 → habilitar visión → `local_front_box/separate_right_cruzr` →
`cruzr/mobot_back_20` → put1 → `wrc_cruzr/put_cruzr_wrc_low` → `cruzr/home`.
No se sustituyen XML/YAML, límites, tamaños internos ni distancias del proveedor.
El perfil registra `operator_assumed_existing`, no una validación física nueva.

Hay tres entradas con política fija. Todas conservan los controles técnicos y
el modo de lectura por defecto; únicamente cambia cómo se obtiene la evidencia
de caja. No se puede cambiar de política mediante un argumento del ejecutor.

| Entrada | Política | Evidencia de sujeción/liberación |
| --- | --- | --- |
| [`ask_improved_scenario1.sh`](../../scripts/ask_improved_scenario1.sh) | `ask` | Confirmación presencial; requiere terminal y pregunta en las transiciones |
| [`force_improved_scenario1.sh`](../../scripts/force_improved_scenario1.sh) | `assume` | Sin preguntas; estado de caja **asumido** después del éxito técnico de la etapa |
| [`force_improved_scenario1_autochecked.sh`](../../scripts/force_improved_scenario1_autochecked.sh) | `sensors` | Sin preguntas; exige ventanas frescas de FT y postura dentro de un perfil cualificado |

**El perfil de sensores distribuido está `pending`.** La entrada autochecked
permite recoger telemetría con `--check`, pero rechaza `--run` y `--resume` antes
de conectarse al robot mientras no se proporcione una cualificación válida.

## Uso

Desde la raíz del repositorio:

```bash
# Sólo plan local, sin conexión:
./scripts/force_improved_scenario1.sh --plan

# Sin argumentos equivale a --check: comprobaciones, sin movimiento:
./scripts/force_improved_scenario1.sh --check

# Ejecución con preguntas presenciales:
./scripts/ask_improved_scenario1.sh --run

# Ejecución sin preguntas; sujeción/liberación asumidas:
./scripts/force_improved_scenario1.sh --run

# Lectura de FT/postura; con el perfil distribuido informa PENDIENTE/código55:
./scripts/force_improved_scenario1_autochecked.sh --check

# Sólo tras cualificar el perfil para la unidad, abrazaderas y posturas reales:
./scripts/force_improved_scenario1_autochecked.sh --run \
  --sensor-profile /ruta/al/perfil-cualificado.json

# Pausa después de la etapa de verificación de agarre, antes del retroceso:
./scripts/force_improved_scenario1.sh --run --stop-after grasp

# Continuación de una pausa limpia, siempre mediante la misma entrada/política:
./scripts/force_improved_scenario1.sh --resume /ruta/de/evidencia/checkpoint.json
```

`--wifi` añade el salto SSH conocido. Reutiliza el ASKPASS existente y exige la
clave SSH del host conocida; no incorpora credenciales. `--evidence-dir` admite
un directorio nuevo. `--profile` acepta sólo el esquema, tamaño y tareas revisados;
no es un mecanismo para inyectar otras tareas o trayectorias.
Sin argumentos ninguna entrada inicia el ciclo: hace `--check`. El movimiento
requiere `--run` o una continuación explícita `--resume`.

`--check` descubre contenedores, valida imagen/HW_TYPE, dependencias SPS y WRC,
variante HOME/biblioteca, controlador, acción libre, dos paros, dos baterías≥20%,
cargador, dos muestras articulares frescas e inmóviles y HOME inicial20D.
Consulta mapa y get1/put1 sin cargar ni relocalizar. Si mapa/localización ya están
preparados, exige también dos poses nuevas válidas en `map`; esta lectura no
certifica llegada a un destino. Código55 indica preparación
necesaria. Todas las políticas inician procesos temporales de consulta de salud
y navegación, y crean una sesión de evidencia en `/tmp/cruzr-scenario1-*` en
Motion. No inicia adaptadores SPS, instala tareas ni ejecuta percepción. La
variante autochecked inicia además su colector FT de sólo lectura y archiva
la telemetría; con referencias pendientes informa código55. Requiere
el paquete SPS del ejecutor anterior ya instalado y coincidente; si falta,
rechaza con diagnóstico y no lo instala automáticamente.

Sólo `ask` exige terminal y `CONTINUAR` después del preflight. Tras el agarre pide
`SUJETA`; antes del depósito, `DEPOSITAR`; antes de HOME, `LIBRE`. Son
comprobaciones presenciales del estado físico y del montaje.

`force` no pide respuestas por stdin ni exige esas confirmaciones: registra
`source: assumed`. Conserva comprobaciones técnicas, estados de acción, límites,
bloqueos, plazos y HOME medido. Su éxito técnico **no se presenta como una
medición de caja**. La entrada autochecked sustituye las confirmaciones por el
contrato de sensores descrito abajo; no convierte una medición desconocida en
una suposición.

La preparación de mapa se hace dentro de la etapa autorizada.
La tarea WRC original incluye abrir las abrazaderas dentro de su XML; este
ejecutor no introduce una parada entre el descenso y esa apertura.

## Supervisión y recuperación

- Intención y resultado de cada etapa se guardan atómicamente, con fsync, en PC
  y Motion. Un fallo/interrupción deja estado indeterminado y bloquea continuidad.
- Los checkpoints nuevos usan versión2 y guardan `policy` y `confirmations`.
  Cada verificación de caja registra `box_state`, `source` (`operator`, `assumed`
  o `sensors`) y, cuando corresponde, `sensor_evidence`. Un checkpoint antiguo
  versión1 sólo puede continuar con `ask`; no se convierte en evidencia de sensores.
- El cliente nativo, reutilizado por endpoint durante la sesión, emite UUID,
  aceptación real, feedback, estados y resultado.
  Ante plazo, señal o pérdida del heartbeat solicita cancelar sólo su UUID y
  observa el resultado terminal durante un plazo acotado. No hay reintentos de
  acciones físicas ni apertura/HOME automáticos después de fallar.
- El supervisor renueva un lease comprobado por el cliente. EOF, heartbeat
  perdido o fallo del watchdog revocan la renovación. La sesión SPS dura como
  máximo900s; es un límite técnico, no una estimación de duración del ciclo.
- Se mantiene el lock local compartido con workbin y el lock remoto SPS durante
  la sesión. Se vuelven a comprobar controladores y acción libre antes de cada
  etapa física y al verificar HOME. En `assume`, `verify_held` y
  `verify_released` sólo registran la suposición y su checkpoint; la etapa física
  siguiente conserva su comprobación completa y fresca.
  Los locks no arbitran todos los posibles mandos externos: el operador debe
  mantener PICO/UI/mando manual fuera del control simultáneo.
- HOME final requiere dos muestras20D recientes con velocidad/consigna dentro
  del contrato existente y posición absoluta<0,02rad. Un resultado exitoso de
  `cruzr/home` por sí solo no completa el ciclo.
- Se puede reanudar únicamente desde un checkpoint limpio cuya última etapa sea
  `verify_held` o `verify_released`, con estado reconfirmado según la misma política
  y mismo perfil, arranque,
  contenedores, dependencias y puntos del mapa. El origen se marca consumido antes
  de armar la continuación; no se publica otra copia limpia antes de reclamarlo.
  Un intento fallido después de reclamarlo exige revisión de la evidencia nueva;
  no se reutiliza el origen ni se borra el marcador para repetir el movimiento.

Una cancelación aceptada o terminar SSH **no demuestra parada física**. Cuando el
resultado queda indeterminado se conserva la evidencia y no se envía otra etapa.
El nuevo cliente usa una adaptación local de la API Python ROSA revisada: corrige
la aceptación inferida del handle y copia el UUID al cancelar, sin modificar el
SDK. Comprueba antes de enviar el AST de las clases nativas y las interfaces
generadas; una versión distinta requiere revisión. Las consultas nativas se
verificaron en la corrección posterior; ArmTask y cancelación física siguen
pendientes de ensayo con este ejecutor.

## Verificación de sensores sin preguntas

El colector ROS2 persistente se suscribe, sin publicar órdenes, a
`/mc/ft_states/L_hand_ft` y `/mc/ft_states/R_hand_ft` (`WrenchStamped`), y a
`/mc/whole_joint_states` (`JointState`). Son sensores de **fuerza y par de muñeca**;
no se ha demostrado disponer de sensores de presión o contacto en las superficies
de las abrazaderas.

Se conserva la trama `frame_id`, la marca de origen y la de recepción de cada
muestra. El colector recibe durante los movimientos, retiene dos segundos de
recepción con límite de100Hz por señal y escribe instantáneas aproximadamente
a10Hz. Las verificaciones breves leen esa caché. `sensors.ready` indica únicamente
que han llegado las tres señales, no que una caja esté sujeta ni que exista una
calibración válida. Un fallo del colector o la pérdida de telemetría durante la
sesión revoca el lease y bloquea nuevas etapas; la acción activa sigue el
protocolo de cancelación acotada, sin afirmar que eso demuestre parada física.

El contrato exige una ventana de0,5s con al menos cinco muestras y0,2s de
extensión temporal por señal, sin huecos mayores de0,1s. Las marcas de origen
deben crecer estrictamente y ser coherentes con recepción; el desfase entre las
últimas muestras de muñecas debe ser≤0,1s. El colector rechaza marcas de origen
duplicadas o regresivas antes de reducir la frecuencia de muestras. Se rechazan
valores no finitos y tramas distintas de las del perfil. También se exige el
conjunto exacto de articulaciones esperado, una postura calibrada y velocidad
absoluta≤0,02rad/s. Son condiciones del contrato de observación, compatibles con
la ventana estática real descrita abajo; su comportamiento durante el ciclo sigue
pendiente de ensayo. Los intervalos admisibles de fuerza/par son
propios de cada muñeca y postura; no se deducen de `SUCCEED` ni de un único valor.

La postura calibrada excluye **sólo las posiciones** de
`driving_wheel_left_joint` y `driving_wheel_right_joint`: son rotaciones integradas
que cambian después de trasladar la base. En esta unidad se calibran por tanto
las otras20 articulaciones observadas; sus nombres deben coincidir exactamente.
Las dos ruedas siguen presentes en la evidencia y su velocidad debe cumplir
el mismo límite≤0,02rad/s. No se admiten exclusiones arbitrarias. El informe
explicita `posture_excluded_joint_names` y `excluded_wheel_positions_rad`.

Se vuelve a leer evidencia fresca antes del retroceso, del transporte a put1,
del depósito y de HOME. Los informes y las muestras utilizadas se archivan junto
con el perfil de sensores y su identidad. No se añaden reintentos de agarre,
movimientos de prueba ni umbrales físicos inventados.
Después de una acción, el supervisor puede esperar hasta0,7s únicamente para
reunir muestras nuevas de la ventana exigida; una carga o postura contradictoria
no se reintenta ni se descarta esperando a que otra lectura la oculte.

La plantilla [`scenario1_sensor_profile.json`](../../scripts/box_handling/scenario1_sensor_profile.json)
es deliberadamente pendiente. `--sensor-profile` acepta un JSON externo del
esquema estricto de [`scenario1_sensors.py`](../../scripts/box_handling/scenario1_sensors.py):

| Nivel | Campos exactos |
| --- | --- |
| Perfil versión1 | `version`, `id`, `geometry_id`, `qualification`, `evidence_reference`, `stages` |
| `stages` | `held` y `released`; ambos `null` cuando `qualification` es `pending` |
| Cada etapa cualificada | `pose`, `max_pose_error_rad`, `left`, `right` |
| `pose` | `joint_names` y `position_rad`, diccionario con exactamente esos nombres |
| Cada muñeca | `frame_id`, `force_min`, `force_max`, `torque_min`, `torque_max`, `max_force_span_n`, `max_torque_span_nm` |

Los cuatro límites de fuerza/par son vectores XYZ de tres valores finitos en
N/Nm; los máximos de variación son positivos y limitan el rango pico a pico de
cada componente XYZ, no la variación de la norma. La tolerancia articular explícita
debe cumplir `0 < tolerancia ≤ 0,03 rad`. `geometry_id` debe coincidir con el perfil
geométrico (`scenario1_current_geometry_v1` en la plantilla actual). `qualified` exige ambas etapas y
una referencia de evidencia no vacía; se rechazan envolventes indistinguibles
de carga/vacío cuando sus regiones de postura se solapan.

La cualificación debe identificar unidad, efector/configuración de abrazaderas,
tramas y posturas, y enlazar mediciones etiquetadas de éxito, vacío y agarre
fallido representativos en las posturas pertinentes. El validador comprueba el
esquema y la presencia de esa referencia, **no la autenticidad ni el contenido
del ensayo referenciado**. Cambiar `qualification` o inventar límites no
constituye una cualificación; esta intervención no genera esos datos.

No se resta a ciegas una lectura en HOME de otra con brazos orientados de forma
distinta: la gravedad y la transformación del sensor cambian. Tampoco se usa
`/mc/manipulation/payload_state` como detector de caja. **INFERENCIA histórica**:
el `librobot.so` archivado el14-09 (SHA256
`7322b075badd43ad6f20f87fe9ff6b4b1cd6fc95bcd44d8c5048df26486432de`)
publica `with_payload`/`no_payload` aproximadamente a1Hz; en la rama de robot cuyo
nombre no contiene `avatar` decide por postura articular (`abs(q)>0,2`) y estado
del ayudante de brazos, no por presencia independiente de caja. Se analizó la
función en0x18b300 del binario local; esto no verifica el binario cargado hoy.
El topic `debug_msg` sólo tiene tipo `JointState` demostrado en los inventarios
consultados, sin muestras ni semántica de contacto cualificadas.

Los registros reales de Singapore y su bodyback también indican identificación
de carga desactivada y masa fijada a cero. `Clamp box succeed`/`NoneException`
aparecen tanto en agarre como en apertura. Ninguna de esas cadenas demuestra
sujeción, liberación o apoyo por sí misma. Evidencia:
`../Humanoide-vla-evidence/20260922T064454Z_FRONT_SPS_ICEORYX/successful-reference-motion.log`
y `../Humanoide-vla-evidence/20260914_MOTION_INTERNAL_CONTRAST/librobot.so`.

FT y postura pueden contrastar una condición mecánica calibrada, pero **no prueban
identidad de caja, separación de todas las cajas encajadas ni apoyo completo**.
La doble captura con TF descrita abajo sólo corresponde a percepción de agarre;
no se implementó un clasificador visual autónomo posterior al agarre o al
depósito. La cualificación y la validación física de esta variante siguen
PENDIENTES; el perfil distribuido mantiene bloqueado su movimiento.

## Percepción y geometría

En el punto donde Singapore solicita percepción, después de sus preparaciones
de cabeza/brazos, el adaptador temporal obtiene dos capturas consecutivas. Cada
una pasa el contrato existente de frescura y TF exacta. Exige coherencia≤2cm/3°
y timestamps crecientes; entrega la segunda pose original de cámara, sin promedio.
El plazo nativo existente sigue vigente: una captura lenta o incoherente falla.
Se guardan ambas detecciones y el diagnóstico de estabilidad.

Esto no certifica alcance, IK, identidad de objeto ni sujeción. Se conserva el
selector frontal actual y su paso vertical0,22±0,04m; el modelo para encajes de
menor paso sigue pendiente de medidas. Tampoco se convierte la trayectoria WRC
en un depósito a100cm: se mantiene la geometría indicada por el usuario. No se
integra el avance corto no cualificado ni se amplían límites.

## Fuentes, verificación y reversión

- [Entrada con preguntas](../../scripts/ask_improved_scenario1.sh),
  [entrada sin preguntas](../../scripts/force_improved_scenario1.sh),
  [entrada de sensores](../../scripts/force_improved_scenario1_autochecked.sh)
  y [CLI](../../scripts/box_handling/scenario1_cli.py).
- [Supervisor](../../scripts/box_handling/scenario1_runtime.py), [cliente nativo](../../scripts/box_handling/scenario1_action_client.py).
- [Lector persistente de salud](../../scripts/box_handling/scenario1_health_worker.py)
  y [comprobación agrupada de dependencias](../../scripts/box_handling/scenario1_dependencies.py).
- [Contrato de etapas](../../scripts/box_handling/scenario1_contract.py), [comprobaciones](../../scripts/box_handling/scenario1_checks.py), [percepción](../../scripts/box_handling/scenario1_perception.py).
- [Perfil con geometría actual](../../scripts/box_handling/scenario1_current_geometry.json).
- [Colector de sensores](../../scripts/box_handling/scenario1_sensor_worker.py),
  [validador](../../scripts/box_handling/scenario1_sensors.py) y
  [plantilla pendiente](../../scripts/box_handling/scenario1_sensor_profile.json).

Receta de validación local, sin robot:

```bash
bash -n scripts/ask_improved_scenario1.sh scripts/force_improved_scenario1.sh \
  scripts/force_improved_scenario1_autochecked.sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover \
  -s scripts/box_handling -p 'test_scenario1_*.py'
./scripts/force_improved_scenario1.sh --plan
git diff --check
```

Verificación inicial de construcción:99 pruebas offline de contratos, API nativa simulada, cancelación,
estado indeterminado, rechazo de acción, percepción, locks/lease, HOME incompleto
y reanudación de un solo uso. Sintaxis Bash/Python3.10, ayuda y plan local pasan.
En esa construcción no se ejecutaron --check/--run contra el robot. Tampoco hubo instalación, reinicio,
nueva captura real ni modificación de mapas, tareas, SDK o servicios.

Instalado: sólo fuentes PC y permiso ejecutable de las entradas. Sin instalación
persistente en robot; la corrección posterior ejecuta código de consulta en memoria.
Probado físicamente: no. Al ejecutarse con --run, transmite código en memoria y crea
evidencia/adaptadores temporales en Motion; los adaptadores usan los archivos SPS
existentes verificados por hash. No cambia su autoarranque ni sus archivos.

Evidencia de construcción, hashes y backups documentales:
`../Humanoide-vla-evidence/20260928_IMPROVED_SCENARIO1_BUILD/`.
Se verificó que el script original y las fuentes SPS revisadas mantienen sus
hashes. Cada uso genera evidencia PC fuera de Git. Con la optimización vigente,
también `--check` de cualquiera de las políticas crea una carpeta
`/tmp/cruzr-scenario1-*` en Motion; sus rutas se registran en events.jsonl.
Reversión de esta intervención: retirar los archivos nuevos `scenario1_*`, sus
tests y la entrada, y revertir selectivamente las notas desde `before/`.
No hay cambios remotos que revertir en esta intervención; preservar evidencia de
cualquier ejecución posterior y reconciliar primero acciones/caja indeterminadas.

Punto de reanudación tras la construcción inicial: comprobar el ejecutor en lectura contra la instalación
actual; después, ensayo supervisado por etapas con condiciones físicas nuevas.

Ampliación de políticas del28-09: respaldo de esta guía anterior, fuentes y
verificación en `../Humanoide-vla-evidence/20260928T072132Z_SCENARIO1_POLICIES/`.
Las fuentes nuevas y el perfil pendiente son locales; no se cualificaron sensores
ni se ejecutaron movimientos para construir esta ampliación. Para revertirla,
restaurar selectivamente las fuentes y esta guía desde `before/`, conservando
checkpoints/evidencias y cambios ajenos. No reutilizar un checkpoint de otra
política. Punto pendiente: cualificar las envolventes de sensores y comprobar su
correspondencia con la unidad antes de habilitar `autochecked --run`.

## Corrección de descubrimiento y estado — 28-09-2026

OBSERVADO09:03 CEST: ambos contenedores estaban activos, pero sus servicios
Compose reales eran `motion.manipulation_robot_app` y `ros.ros2`; el detector
sólo admitía los nombres cortos `manipulation_robot_app` y `ros2`. Como sí había
etiquetas, tampoco aplicaba el fallback por nombre. El fallo era del detector,
no evidencia de contenedores detenidos.

Corregido en `scenario1_checks.py`: aliases exactos verificados en inventario,
manteniendo unicidad, imagen/HW_TYPE y rechazo de conflictos. `ros.ros2-export`
y los demás servicios Motion quedan fuera. Pruebas cubren el inventario vendor,
alias duplicados y contradicciones nombre/rol.

La primera repetición superó contenedores y hashes pero agotó la lectura de
`/mc/manipulation/action/_action/status`. El runtime forzaba VOLATILE en todos
los topics. El publisher de estado anuncia RELIABLE/TRANSIENT_LOCAL/KEEP_LAST1;
la consulta canónica sin sobrescribir QoS devolvió status4. Se usa esa consulta
para el estado de acciones y se conserva VOLATILE para telemetría, incluido
BEST_EFFORT en actuadores. La prueba explícita TRANSIENT_LOCAL también agotó su
plazo; no se deduce que fijar sólo ese campo baste para reproducir el CLI.
Los fallos de lectura ahora identifican topic y código de retorno.

`scenario1_cli.py` distingue errores de --check/--plan (CHECK_FALLIDO, sin órdenes
de movimiento) de interrupciones de --run/--resume. Un fallo de descubrimiento
no se presenta ya como necesidad de recuperación física.

VERIFICADO09:06 CEST con `./scripts/force_improved_scenario1.sh --check`:

- Contenedores descubiertos: `walker-motion.manipulation_robot_app-1` y
  `walker-ros.ros2-1`; arranque de contenedores05:55:18–19Z.
- Paquete SPS74f5507e44addd71 y dependencias coincidentes. HOME coincide con
  variantev8 d9e9462792b41300d352604b53ea2a4890a9382e942321990708f6ded2e26ccb.
- Controladores y estado de acción admitidos; paros0/0, cargador desconectado,
  baterías86,6%/88,6%. Dos muestras20D con posición máxima0,002780rad,
  velocidad máxima0 y MEASURED_HOME=1. Estado volátil de esa consulta.
- Puntos get1/put1 válidos. API ROSA revisada coincide; las consultas nativas
  `get_map_name` y `check_state` devuelven aceptación real y resultado4.
- Mapa activo vacío y `FSM_WAITSETMAP`: retorno55/PREPARACION_REQUERIDA, según
  contrato. No se ejecutó map_set, relocalización, percepción, ArmTask ni navegación.

Sólo cambios de fuentes/documentación PC y consultas remotas. Sin instalación,
restart, cancelación, modificación de mapas, SDK, tareas o movimiento. La
aceptación/resultado de consultas nativas se ha probado; el ciclo físico y la
cancelación de un movimiento siguen PENDIENTES. No se iniciaron adaptadores SPS.

106 pruebas offline pasan, incluidas regresiones del descubrimiento, QoS y mensajes.
Respaldo previo, inventario saneado, receta de consultas y hashes:
`../Humanoide-vla-evidence/20260928T070318Z_SCENARIO1_DISCOVERY_FIX/`.
Repetición intermedia: `../Humanoide-vla-evidence/20260928T070423Z_IMPROVED_SCENARIO1_281928/`.
Resultado final: `../Humanoide-vla-evidence/20260928T070628Z_IMPROVED_SCENARIO1_287182/`.
Reversión: restaurar selectivamente checks/runtime/CLI y tests desde before,
preservando cambios posteriores; no hay configuración remota que restaurar.
Punto de reanudación: preparar mapa dentro de una ejecución expresamente autorizada
y supervisada; mantener la comprobación física actual antes de mover.

## Lectura real de sensores — 28-09-2026

**VERIFICADO, sólo lectura:**
`./scripts/force_improved_scenario1_autochecked.sh --check` terminó con código55
exclusivamente porque el perfil FT seguía `pending`. La adquisición de sensores
y los controles técnicos completaron sus verificaciones; no se envió movimiento.

- Se descubrieron `walker-motion.manipulation_robot_app-1` y
  `walker-ros.ros2-1` mediante los aliases corregidos.
- Paros0/0, cargador0 y baterías83%/84,6%. Dos muestras de HOME20D dieron
  posición absoluta máxima0,002684rad y velocidad máxima0.
- En esta consulta el mapa ya era `utars_nav_map` y el estado
  `FSM_WAITNAVIGATE`. Se registra el estado observado; esta intervención no
  ejecutó un cambio de mapa ni explica su diferencia con la lectura anterior.
- Cada muñeca aportó16 muestras durante0,300001s; el desfase entre sus últimas
  marcas fue0. Ambas publicaron `frame_id: force_torque_sensor_controller`.
- Se observaron27 muestras de articulaciones, con22 nombres:20 del cuerpo y
  las dos ruedas. Velocidad máxima0, incluidas las ruedas. Sus posiciones
  acumuladas motivaron excluirlas del perfil de postura, conservando la
  comprobación de velocidad y la evidencia completa.
- `sensor_check` informó `box_state_evaluated: false`: estos datos **no tienen
  etiqueta física de caja sujeta, vacía o liberada** y no son una calibración.

Evidencia y fuentes exactas transmitidas:
`../Humanoide-vla-evidence/20260928T073255Z_IMPROVED_SCENARIO1_355885/`.
El colector de sólo lectura se ejecutó temporalmente y creó evidencia en
`/tmp`; no se instalaron servicios persistentes ni se iniciaron adaptadores SPS.
No se enviaron ArmTask, navegación, relocalización ni cancelación de movimientos.

Después de esta captura se reforzó el rechazo de marcas duplicadas, la espera
acotada de adquisición posterior a una acción y la exclusión de posiciones de
ruedas del perfil. La captura conserva el hash de las fuentes que usó; no prueba
en robot los cambios posteriores. La comprobación de referencias cualificadas,
el ciclo y su cancelación física siguen **PENDIENTES**.

Verificación final offline de esta ampliación: **173 pruebas correctas**, incluidas
ejecuciones simuladas completas sin terminal/preguntas, rechazo de resultados
fallidos y datos falsos, pérdida de sensores, ventanas nuevas y posiciones de
ruedas. Sintaxis Bash, ayuda/plan de las tres entradas y diffcheck correctos.
Shellcheck no está instalado. Las pruebas de software no sustituyen la
cualificación mecánica ni autorizan movimiento.

## Latencia entre etapas observada — 28-09-2026

**HISTÓRICO: versión previa a la optimización de supervisión descrita al final.**
Se conservan sus mediciones y diagnóstico; no representan los tiempos de la
versión optimizada.

OBSERVADO en la ejecución iniciada por el usuario, evidencia
`../Humanoide-vla-evidence/20260928T074311Z_IMPROVED_SCENARIO1_382679/`:
las diez etapas finalizaron, las acciones devolvieron los resultados exigidos y
HOME final se midió en20D (máximo absoluto0,002780rad, velocidad0). El checkpoint
mantiene `policy: assume`: sujeción y liberación **asumidas**, sin evidencia FT;
no demuestra separación de una única caja ni apoyo correcto. Es evidencia de
ejecución de este ciclo, no cualificación física general del montaje.

Los intervalos siguientes se calculan entre `result.time_ns` de una acción y
`accepted.time_ns` de la siguiente, ambos del reloj Motion:

| Intervalo | Tiempo observado |
| --- | ---: |
| Habilitar visión → comenzar agarre | 9,162s |
| Terminar agarre → comenzar retroceso | 18,317s |
| Terminar depósito → comenzar HOME | 20,988s |

Hay tres etapas explícitas `verify_held`, `verify_released`, `verify_home`.
Además, `Runtime.stage()` ejecuta `discover()`, `hashes()` y `health()` **en las
diez etapas**, incluso las de verificación. El diario confirma11 repeticiones
de cada grupo contando el preflight. `health()` abre consultas separadas para
controladores, estado de acción, cuatro señales de seguridad (éstas en paralelo)
y dos muestras articulares consecutivas. Cada consulta implica crear procesos
Docker/ROS/ROSA y descubrir comunicaciones. Los resultados no permiten atribuir
un tiempo exacto a cada subconsulta, pues esos eventos no llevan timestamp.

En `assume`, `verify_held` y `verify_released` sólo registran una suposición de
caja después de ese chequeo técnico completo; no hacen una medición de carga.
La etapa de movimiento siguiente repite el mismo grupo. Esto explica la
duplicación de espera observada. `verify_home` sí exige posición HOME medida.
El script original hacía preflight técnico inicial, verificaba resultados y
llegadas, pero no repetía este grupo completo entre todas las etapas.

También se crean21 clientes de acción nativos en este ciclo: consultas de mapa,
estado y movimientos. `prepare_map()` consulta de nuevo el mismo mapa/estado al
final incluso cuando no tuvo que cambiar nada. Entre la primera consulta
aceptada y el resultado HOME transcurrieron212,167s; los intervalos de acciones
distintas de consultas suman94,786s. El resto incluye comprobaciones y coordinación;
no es una medida aislada del coste de `health()`. No se mezclan marcas Motion
con el nombre/mtime de la carpeta PC para estimar duración.

Propuesta en el momento del diagnóstico (implementación vigente al final): evitar el chequeo completo duplicado en verificaciones
asumidas, conservar evidencia/checkpoints, reutilizar clientes y suscripciones
para obtener muestras frescas, y comprobar dependencias al inicio con invalidación
si cambia la instancia/configuración. Mantener paros, cargador, salud, exclusión
de clientes, resultado terminal, llegada y HOME medido. No se cambia el ejecutor,
ni se envía movimiento o consulta remota para este diagnóstico.

Receta reproducible de los tres intervalos (sólo lee el diario):

```bash
python3 -B - <<'PY'
import json
from pathlib import Path
path = Path('../Humanoide-vla-evidence/20260928T074311Z_IMPROVED_SCENARIO1_382679/events.jsonl')
stage, accepted, results = 'preflight', {}, {}
for line in path.read_text().splitlines():
    event = json.loads(line)
    if event['event'] == 'checkpoint' and event['checkpoint']['in_flight']:
        stage = event['checkpoint']['in_flight']
    if event['event'] == 'action' and event['kind'] == 'motion':
        detail = event['detail']
        if detail['event'] == 'accepted': accepted[stage] = detail['time_ns']
        if detail['event'] == 'result': results[stage] = detail['time_ns']
for before, after in [('enable_vision', 'grasp'), ('grasp', 'retreat'), ('deposit', 'home')]:
    print(before, '->', after, round((accepted[after]-results[before])/1e9, 3), 's')
PY
```

Respaldo documental previo, informe y hashes:
`../Humanoide-vla-evidence/20260928T074936Z_SCENARIO1_LATENCY_REVIEW/`.

## Optimización de supervisión — 28-09-2026

**IMPLEMENTADO en fuentes PC; VERIFICADO offline y en consultas reales de
lectura. Ciclo físico optimizado PENDIENTE.** No se ha ejecutado movimiento
por el agente para esta optimización. Las trayectorias y políticas de caja se
conservan; el perfil de sensores continúa `pending` y esta intervención no añade
captura de calibración ni clasificación visual posterior a la manipulación.

El cambio reduce la creación repetida de procesos y las comprobaciones técnicas
duplicadas en las dos transiciones que sólo registran una suposición:

| Componente | Comportamiento vigente |
| --- | --- |
| `assume`: `verify_held` / `verify_released` | Guardan intención y resultado duraderos, con `source: assumed`, sin repetir descubrimiento, hashes y salud. Conservan orden, lease y bloqueo tras fallo; no representan una medición de caja. |
| Etapas físicas y `verify_home` | Conservan descubrimiento de contenedores, comprobación completa de dependencias y salud fresca. HOME final conserva dos muestras20D y el umbral de posición establecido. |
| Dependencias | Dos `docker exec` en paralelo, uno por contenedor. Cada llamada relee todos los bytes de todos los archivos exigidos; no hay caché por mtime ni sustitución por una comprobación sólo inicial. |
| Salud y llegada | Un proceso/nodo ROSA mantiene siete suscripciones y el cliente de `ListControllers`; cada petición recoge las muestras nuevas requeridas. La llegada utiliza dos poses nuevas del mismo lector. |
| Acciones | Un proceso/nodo cliente por endpoint se reutiliza en la sesión. Cada petición conserva identificador propio, UUID del goal, aceptación y resultado terminal, sin reenvío automático de objetivos. |
| Preparación de mapa | Se omite la segunda pareja redundante de consultas únicamente si la primera lectura fresca ya devuelve mapa y localización preparados y no se cambia nada. |

La agrupación de dependencias mantiene todos los hashes SPS, tareas, YAML y
bibliotecas, las variantes HOME admitidas y la biblioteca MetaMove cuando HOME
la requiere. La tarea de visión sigue exigiendo una única acción con los atributos
`ID=MetaLook` y `start_vision_mode=transport_vision`; el XML se entrega junto al
hash de los mismos bytes leídos. La identidad se compara también con la ya fijada
en la sesión. Los metadatos del archivo sólo detectan una modificación durante
esa lectura completa; nunca permiten omitirla. El contenedor se redescubre antes
de cada etapa física y un cambio de instancia sigue impidiendo continuar.

El lector persistente se suscribe a los cuatro topics de paros/cargador/baterías,
actuadores, estado de la acción y pose de navegación. Las cuatro señales de
seguridad deben recibirse después de la petición; las dos muestras articulares
deben tener marcas de origen posteriores a ella, estrictamente crecientes y
antigüedad máxima de2s. Se conserva el clasificador20D de fallos, habilitación,
velocidad y diferencia con consigna. El estado DDS de la acción se acepta
expresamente retenido porque puede no republicarse mientras está libre; esto
no habilita reutilizar telemetría antigua de salud o llegada. `ListControllers`
se vuelve a consultar en cada petición de salud.

Después de cargar mapa o relocalizar se conserva la comprobación posterior
independiente. Después de navegar se mantienen la consulta de mapa/estado y dos
poses frescas, crecientes, en `map`, con llegada dentro de5cm/3°. No se suprime
ninguna de esas comprobaciones por reutilizar el proceso lector.

Los procesos persistentes obedecen los leases de sesión. Un error de protocolo,
una petición fallida o la pérdida de un proceso bloquean la continuación; no se
reinicia el cliente para ocultar el fallo ni se repite el objetivo. La cancelación
conserva el UUID propio, el plazo acotado y la distinción entre petición aceptada,
resultado terminal y parada física. Las fuentes y suscripciones se cargan en
procesos temporales; no se modifica el SDK ni se crean servicios de autoarranque.

Los eventos del supervisor incorporan marcas temporales y eventos `timing` con
`elapsed_s` para descubrimiento, dependencias y salud. `stage_complete` incluye
duración y distingue las transiciones lógicas asumidas. La consola muestra la
etapa y los tiempos disponibles, de modo que la siguiente evaluación pueda
separar el coste de consultas, preparación y acciones. **No se promete una
duración nueva del ciclo:** una comparación de salud en lectura no mide el
agarre, transporte, depósito ni HOME.

VERIFICADO: **242 pruebas offline correctas**, sintaxis Python/Bash, ayuda y plan
de las tres entradas, y `git diff --check`. Cubren sesiones reutilizadas,
correlación de resultados, cancelación, frescura, pérdida de procesos, hashes
completos y bloqueo antes de movimiento tras fallo técnico. Shellcheck no está
instalado. La medida reproducible adicional se solicita así:

```bash
./scripts/force_improved_scenario1.sh --check --benchmark-checks 3
```

Acepta de 1 a 5 rondas extra; se rechaza con `--run`, `--resume` o `--plan`
antes de conectar. Cada ronda vuelve a descubrir contenedores, releer hashes,
consultar salud y pedir `get_map_name`/`check_state` con los clientes ya abiertos.
La corrección posterior descrita al final añade la lectura de pose a esas rondas
cuando mapa/localización están preparados; la tabla histórica siguiente aún no
incluía esa consulta.
No llama a preparación de mapa, relocalización ni navegación. Un fallo impide
continuar; las rondas adicionales no son reintentos de una comprobación fallida.

OBSERVADO a las 10:05 CEST, retorno 0, mapa `utars_nav_map` y
`FSM_WAITNAVIGATE`, HOME medido:

| Ronda adicional | Contenedores | Dependencias | Salud fresca | Mapa/estado | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 0,090 s | 0,126 s | 2,616 s | 0,113 s | 2,945 s |
| 2 | 0,074 s | 0,153 s | 4,152 s | 0,106 s | 4,485 s |
| 3 | 0,067 s | 0,135 s | 4,187 s | 0,106 s | 4,495 s |

Evidencia: `../Humanoide-vla-evidence/20260928T080528Z_IMPROVED_SCENARIO1_442692/`.
El lector de salud y el cliente de navegación permanecieron abiertos entre
peticiones; ocho consultas de navegación obtuvieron sus ocho resultados. La
lectura sigue esperando datos nuevos: la optimización no elimina esa espera.
El arranque y descubrimiento SPS iniciales quedan fuera de esta tabla.
Estos totales no equivalen a los intervalos entre movimientos de la versión
anterior: falta ejecutar y medir un nuevo ciclo físico.

Primer `--check` integrado falló sin movimiento porque ROSA exige completar
`wait_service(0)` antes de `call_async`, aunque el servicio ya esté descubierto.
Se corrigió con espera explícitamente acotada y nueva comprobación de lease/plazo;
el segundo `--check` devolvió 0. Evidencias respectivas:
`20260928T075850Z_IMPROVED_SCENARIO1_423527/` y
`20260928T080205Z_IMPROVED_SCENARIO1_432098/`, bajo el mismo directorio externo.
El `--check` autochecked posterior también recibe FT/articulaciones y devuelve
55 exclusivamente por el perfil `pending`:
`20260928T080634Z_IMPROVED_SCENARIO1_446664/`. No se cualificó la carga.

Los helpers finalizan al revocar los leases. Sus eventos de cierre pueden
registrar `Lease expired` con códigos 2/78 sin petición activa, después de
`request_complete: 0`; el retorno global de la comprobación distingue ese cierre
de un fallo durante una petición. Se conservan también los eventos tardíos de
cancelación/resultado recibidos durante el cierre, sin habilitar otra acción.

Respaldo previo de fuentes y documentos, e inventario de la API nativa consultada:
`../Humanoide-vla-evidence/20260928T075234Z_SCENARIO1_OPTIMIZATION/`.
Fuentes finales en `after/`, inventarios `before-sha256.json`/
`after-sha256.json`, diferencias en `changed-files.json` y resultados en
`verification.json`. Reversión: restaurar selectivamente desde `before/` los archivos
modificados, retirar las fuentes nuevas de esta optimización según su inventario
y conservar los checkpoints y evidencias existentes. No restaurar estados
transitorios de control ni iniciar procesos remotos antiguos. Punto de reanudación:
medir el siguiente ciclo físico autorizado en `events.jsonl`; cualquier nuevo
ciclo requiere las condiciones y autorización vigentes del proyecto.

## Corrección de pose con dos publicadores — 28-09-2026

**VERIFICADO en lectura; ciclo físico posterior PENDIENTE.** Los intentos del
usuario `20260928T080916Z_IMPROVED_SCENARIO1_455129/` y
`20260928T081031Z_IMPROVED_SCENARIO1_458945/` fallaron en `navigate_get1`, al pedir
las poses después de navegar. Ambos obtuvieron `status: 4`,
`navigation_start SUCCEEDED` y mapa/estado esperados, pero la petición de pose
agotó 12 s. No enviaron acciones Motion: habilitar visión, agarre, retroceso,
depósito y HOME quedaron sin ejecutar. Los checkpoints conservan el fallo y
`box_state: unknown`; no son pausas limpias para `--resume`.

La regresión estaba en `NativeReader.acquire`: exigía exactamente un publicador
también para pose. Descubrimiento actual tanto ROSA como ROS2 muestra **dos**
publicadores `geometry_msgs/PoseStamped`, los mismos GIDs, Reliable/TransientLocal,
profundidades 10 y 1. Capturas VOLATILE paralelas recibieron 63 y 64 muestras en
6 s, en `map`, con marcas estrictamente crecientes y edades de 0,00077–0,00638 s.
El lector podía recibir datos válidos y aun así nunca devolver su resultado por
ese conteo. No se pudo atribuir cada mensaje a un GID mediante el rclpy instalado;
no se afirma que el segundo publicador sea sólo una copia retenida.

Se restaura el contrato que usaba la lectura ROS2 anterior: la pose puede tener
uno o más publicadores. Se mantienen VOLATILE, dos muestras posteriores a la
petición, marcas estrictamente crecientes, edad máxima de 2 s y rechazo de
marcas repetidas/futuras. Los endpoints de salud conservan exactamente un
publicador. La llegada sigue requiriendo geometría finita, cuaternión válido,
marco `map` y distancia/orientación dentro de **5 cm/3°**. No se modifica la
validación del resultado de navegación ni la localización del robot.

`validate_pose_sample` separa la validez de la telemetría de la llegada a un
destino. `--check` y las rondas de benchmark leen ahora dos poses si el mapa está
listo; cada navegación también verifica el canal antes de enviar el objetivo.
Tras navegar vuelven a pedirse dos muestras nuevas y se aplican las tolerancias
de llegada. `pose_check` registra `arrival_verified: false`: recibir posición
no certifica haber llegado. Un timeout incorpora conteos de publicadores y de
muestras para evitar el diagnóstico genérico anterior.

El aviso auxiliar `VSLAM_LOCATION_LOST` también figura en el ciclo anterior
`20260928T074311Z_IMPROVED_SCENARIO1_382679/`, que sí midió llegada. Su presencia
no basta para explicar este timeout y tampoco demuestra localización visual
recuperada. La corrección no lo oculta ni sustituye la comprobación de llegada
por `SUCCEEDED`.

VERIFICADO: **250 pruebas offline**, incluyendo dos publicadores con poses
frescas, rechazo de datos antiguos/ausentes, bloqueo antes de navegar y
distinción entre telemetría válida y llegada. Consulta real de la versión final:

```bash
./scripts/force_improved_scenario1.sh --check --benchmark-checks 3
```

Retorno 0 / `CHECK_OK`, evidencia
`../Humanoide-vla-evidence/20260928T081557Z_IMPROVED_SCENARIO1_475758/`:
cuatro peticiones de pose correctas, todas con dos publicadores y dos muestras
nuevas, 0,14–0,20 s por petición. Las rondas completas adicionales, incluida pose,
tardaron 3,04 / 4,48 / 4,52 s. El agente no envió movimientos, cambios de mapa,
relocalización, reinicios ni modificaciones persistentes al robot. Los procesos
de lectura terminaron; el siguiente ciclo físico sigue sin probar.

Descubrimiento y capturas:
`../Humanoide-vla-evidence/20260928T081314Z_POSE_DISCOVERY/`.
Backup previo y estado final reproducible:
`../Humanoide-vla-evidence/20260928T081354Z_SCENARIO1_POSE_FIX/`
(`before/`, `after/`, hashes, `changed-files.json`, tests y `verification.json`).
Reversión: restaurar selectivamente los archivos modificados desde `before/`
y retirar sólo la nueva prueba `test_scenario1_pose_preflight.py`; conservar
trabajo posterior, checkpoints y evidencia. Eso reinstala el defecto de
unicidad, no una configuración remota anterior. Punto de reanudación: ensayo
físico autorizado con el lector ya comprobado; no convertir el checkpoint
fallido en una reanudación limpia ni asumir estado físico a partir de estos logs.

## Adaptación a mesa de 73 cm revertida — 28-09-2026

El usuario pidió volver atrás antes de probar otra cosa. Se restauraron
`scenario1_cli.py`, `scenario1_contract.py` y `scenario1_runtime.py` desde el
respaldo anterior a la adaptación, verificando igualdad SHA256. Se retiraron
`config/box_handling/scenario1_put1.json`, el generador `scenario1_deposit.py`,
su prueba y el instalador incompleto `scenario1_deposit_install.py`. Esos archivos
están archivados fuera del repositorio; no se borró trabajo anterior del usuario.

Estado vigente: geometría original, depósito `wrc_cruzr/put_cruzr_wrc_low`,
clientes persistentes y corrección de los dos publicadores de pose. La altura de
73 cm **no está aplicada**. Preparación previa: sólo lecturas técnicas y TF;
no se instaló la variante en el robot ni se ejecutó movimiento. La confirmación
presencial recibida para ese ensayo no se reutiliza después de cancelarlo.

VERIFICADO al revertir: 250 pruebas offline, `--plan` con el perfil y tarea
originales, y `git diff --check`. No se ejecuta `--check` remoto ni `--run` para
esta reversión. Backup fuente:
`../Humanoide-vla-evidence/20260928T090113Z_SCENARIO1_TABLE73_BUILD/before/`.
Trabajo descartado, hashes y resultado:
`../Humanoide-vla-evidence/20260928T090823Z_SCENARIO1_TABLE73_ROLLBACK/`.
La investigación geométrica queda histórica, sin adaptación activa.
