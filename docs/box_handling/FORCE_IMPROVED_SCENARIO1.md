# Ejecutor mejorado del escenario 1

28-09-2026, Europe/Madrid. **BOX-01-EXEC-IMPROVED — implementado en el PC.**
Consola vigente: etapas legibles, feedback normal repetido limitado a una vez
por segundo, avisos inmediatos y registro técnico íntegro; `--verbose` muestra
los eventos completos. [Uso](#consola-resumida--28-09-2026).
Reanudación vigente: `--resume CHECKPOINT --from-stage ETAPA`, con `--plan`
y `--check` de sólo lectura. Admite las diez etapas; una entrada tras fallo,
interrupción o salto exige estado de caja y recuperación declarados explícitamente,
además de comprobar técnicamente la entrada. El origen se conserva y la nueva
ejecución registra sólo su segmento real.
[Uso y condiciones](#reanudación-por-etapa--28-09-2026).
Incidencia anterior: interrupción en salud antes de `retreat`, sin enviarlo;
caja sujeta y separada según confirmación del usuario. El lector diferencia
duplicados idénticos de regresiones/conflictos; fallo original no reproducido
en lectura. Checkpoint fallido conservado; su entrada en retreat ya pasa
`--resume --check`, pero la continuación física sigue PENDIENTE.
[Estado y evidencia](#sello-articular-repetido-o-regresivo-antes-de-retreat--28-09-2026).
La prueba exclusiva `--stop-after get1` está verificada: una navegación con
lectura posterior de **3,92 mm/0,28°** respecto al punto guardado, sin agarre.
[Resultado y receta](#prueba-de-navegación-exclusiva-a-get1--28-09-2026).
La comprobación vigente de llegada exige **2 cm/2° en get1** y **5 cm/3° en
put1**. **Ajuste automático reactivado por autorización del operador:**
hasta dos maniobras nativas supervisadas, con nuevos límites para la curva de
aproximación y el giro final. Se vuelve a medir antes de ajustar y sólo continúa
al confirmar las dos poses dentro de 2 cm/2° y reposo. La velocidad JSON no se
considera un techo efectivo del proveedor. Si ya cumple, conserva las mismas
lecturas sin ajustes ni esperas adicionales. Nuevo perfil comprobado offline;
convergencia y frenado físicos PENDIENTES.
[Comportamiento vigente y límites](#reactivación-supervisada-del-ajuste-get1--28-09-2026).
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

# Sólo navegación a get1 y medición de llegada, sin recogida:
./scripts/force_improved_scenario1.sh --run --stop-after get1

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

# Revisar una recuperación desde retreat, sin conectar ni mover:
./scripts/force_improved_scenario1.sh --resume /ruta/de/evidencia/checkpoint.json \
  --from-stage retreat --box-state held --recovery-confirmed --plan

# Comprobar esa entrada en lectura; no consume el origen:
./scripts/force_improved_scenario1.sh --resume /ruta/de/evidencia/checkpoint.json \
  --from-stage retreat --box-state held --recovery-confirmed --check
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
- Los ciclos desde el inicio usan versión2; las reanudaciones usan versión3
  con etapa de entrada, procedencia y segmento realmente ejecutado. Guardan
  `policy` y `confirmations`.
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
- Se puede seleccionar cualquiera de las diez etapas, con el estado físico
  requerido y comprobaciones nuevas. Un origen fallido, interrumpido o un salto
  requiere `--box-state` y `--recovery-confirmed`; no se infiere su resultado.
  Se conserva la misma política, perfil, arranque,
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


## Tolerancia de get1 de 2 cm y 2° — 28-09-2026

Esta sección registra el cambio inicial. La corrección automática posterior
se rige por el [perfil supervisado vigente](#reactivación-supervisada-del-ajuste-get1--28-09-2026);
el umbral de aceptación y los fallos de telemetría se conservan.

Petición: exigir una llegada más estricta usando las comprobaciones actuales,
sin una nueva fase de alineación. Instalado en fuentes PC; activación en robot
y ensayo físico PENDIENTES. No se ha conectado ni movido el robot al aplicar
este cambio.

La configuración está en `ARRIVAL_TOLERANCES` de
[`scenario1_checks.py`](../../scripts/box_handling/scenario1_checks.py):

```python
ARRIVAL_TOLERANCES = {'get1': (0.02, 2.0), 'put1': (0.05, 3.0)}
```

Cada pareja contiene **distancia planar en metros** y **giro en grados**. La
misma función se utiliza desde `Runtime.navigate` con el destino explícito;
no se acepta un destino desconocido ni se selecciona un umbral por omisión.
La distancia es radial `hypot(dx, dy)`, no 2 cm por eje. El giro usa el menor
ángulo entre orientación medida y objetivo. Se incluyen los límites exactos,
con margen numérico de 1e-12 exclusivamente para redondeo de coma flotante.

Ambas muestras deben cumplir el umbral. Conservan marco `map`, frescura,
marcas crecientes y cuaternión válido. Cada evento `arrival` archiva el error
medido y las tolerancias aplicadas; el error por rechazo incluye destino,
medición y límite. Una llegada a 2,2 cm se rechaza en `get1`, aunque antes se
aceptase; el mismo error sigue siendo admisible en `put1`.

Las tres entradas mejoradas (`ask_improved_scenario1.sh`,
`force_improved_scenario1.sh`, `force_improved_scenario1_autochecked.sh`) cargan
este módulo automáticamente en su siguiente invocación. No requiere instalar
XML/YAML ni reiniciar servicios. `--plan` permite revisar la secuencia local;
`--check` comprueba telemetría y preparación sin certificar llegada a get1.
Los ejecutores anteriores, incluido `force_escenario1.sh`, no cambian.

El fallo queda en `navigate_get1`: no se habilita visión ni se envía agarre,
HOME o reintento automático. Mantiene el tratamiento de checkpoint fallido y
la recuperación existente. La comprobación más estricta no modifica el
controlador de navegación, velocidades, mapa ni posición guardada; no ordena
una corrección. No añade lecturas, pausas ni etapas. La duración física y la
repetibilidad con esta exigencia están PENDIENTES de ensayo.

Respaldo previo, fuentes finales, hashes, pruebas e inventario:
`../Humanoide-vla-evidence/20260928T101004Z_SCENARIO1_GET1_TOLERANCE/`.
VERIFICADO: 259 pruebas de regresión del ejecutor pasan, incluidas 35 pruebas
de comprobaciones y navegación. Cubren límites inclusivos, distancia radial,
ángulos positivos/negativos, selección por destino, frescura, fallo de cualquiera
de las dos muestras y bloqueo de visión/agarre sin reintento. Sintaxis, `--help`,
`--plan` y `git diff --check` correctos. Las pruebas no acceden al robot;
los tests no versionados del trabajo de depósito pendiente quedan fuera de
esta suite y no se han modificado.
Receta de comprobación offline de los límites y la interrupción antes del
agarre:

```bash
python3 -B -m unittest scripts.box_handling.test_scenario1_checks \
  scripts.box_handling.test_scenario1_pose_preflight
./scripts/force_improved_scenario1.sh --plan
```

Reversión: restaurar selectivamente los archivos enumerados en
`before-sha256.json` desde `before/`, conservando cambios posteriores y ajenos.
Eso devuelve el criterio previo de 5 cm/3°; no hay configuración remota ni
estado físico que restaurar. La evidencia identifica también los archivos
locales pendientes ajenos a este cambio; no se han integrado ni retirado.


## Prueba de navegación exclusiva a get1 — 28-09-2026

Petición autorizada: ir una vez a `get1` y medir su distancia respecto al robot.
El operador confirmó de nuevo HOME, abrazaderas instaladas/vacías, cargador
fuera, ambos paros liberados, ruedas habilitadas, automático, recorrido libre,
sin otros mandos y persona junto al paro. La confirmación es de este ensayo;
no constituye autorización física permanente para otro estado del robot.

Añadido `--stop-after get1` a la CLI y `navigate_get1` a las paradas del contrato.
El supervisor mantiene todos sus preflight, leases, bloqueos, estados y dos
muestras de llegada, pero no inicia los adaptadores SPS para este modo. Sólo
puede completar `navigate_get1`; el checkpoint termina vacío y no permite
reanudar hacia visión/agarre. Las otras paradas conservan su secuencia y SPS.
El mensaje final es `GET1_ALCANZADO`, sin afirmar que se ejecutó un ciclo de caja.

Receta versionada, desde la raíz del repositorio:

```bash
./scripts/force_improved_scenario1.sh --plan --stop-after get1
./scripts/force_improved_scenario1.sh --check --stop-after get1
# Sólo con autorización y estado físico actual comprobado:
./scripts/force_improved_scenario1.sh --run --stop-after get1
# Lectura posterior, sin movimiento:
./scripts/force_improved_scenario1.sh --check --stop-after get1
```

VERIFICADO: 269 tests del ejecutor pasan (suite versionada y nueva prueba
`test_scenario1_navigation_only.py`); plan de una etapa y diffcheck correctos.
Los archivos locales de depósito pendiente no se integran ni se modifican en
este ensayo. Sus tests siguen fuera de esta suite: una ejecución ampliada del
agente informó 17 errores en el instalador pendiente, ajenos al modo de navegación.

Ensayo real, 12:19 CEST, goal `3e98a8d1-9908-42b5-b308-c1bd22acf457`:

| Lectura | Distancia a get1 | Diferencia de giro |
| --- | ---: | ---: |
| Llegada, primera muestra | 3,882 mm | 0,439° |
| Llegada, segunda muestra | 3,883 mm | 0,440° |
| Postcheck, dos muestras coincidentes | 3,923 mm | 0,284° |

Ambas lecturas de llegada cumplen 20 mm/2°. En el último postcheck, el punto
queda aproximadamente 3,67 mm delante y 1,38 mm a la izquierda del origen de
la pose del robot. Son coordenadas calculadas de `/nav/robot_pose` y del punto
guardado en `map`; no miden externamente el chasis ni la caja. La diferencia
entre llegada y postcheck no permite atribuir deriva al robot o al estimador.
Una sola prueba no demuestra repetibilidad ni que endurecer el filtro mejore
el controlador: no se ha cambiado ese controlador.

Aceptación→resultado de navegación: **12,086 s**. Etapa completa, incluidos
chequeos y lectura: **15,832 s**. Estos son tiempos del ensayo, no el coste
incremental de la tolerancia más estricta. El resultado contiene
`navigation_start SUCCEEDED` y aviso auxiliar `VSLAM_LOCATION_LOST`, conservado
en evidencia. La llegada se acepta por las poses frescas y el contrato vigente;
no se declara reparada la localización visual ni certificada precisión absoluta.

Precheck y postcheck retornaron 0. Lectura final: HOME20D, velocidades articulares
cero, paros0/0, cargador0, baterías61,0/62,1%. No se envió ninguna acción Motion,
agarre, apertura, HOME, reintento, edición de mapa ni relocalización explícita.
Los procesos temporales de lectura y supervisión terminaron. El chasis queda
junto al punto `get1`; cualquier tarea posterior requiere revalidar su estado.

Evidencia y backup:
`../Humanoide-vla-evidence/20260928T101642Z_SCENARIO1_GET1_TRIAL/`.
Incluye `authorization.json`, `check/`, `run/`, `postcheck/`,
`arrival-report.json`, pruebas, fuentes y SHA256 antes/después. La comprobación
inicial anterior al nuevo modo está en
`../Humanoide-vla-evidence/20260928T101642Z_IMPROVED_SCENARIO1_803752/`.
Las consultas generan sesiones temporales `/tmp/cruzr-scenario1-*` en Motion;
no hay instalación persistente en contenedores ni cambios del SDK.

Reversión de software: restaurar selectivamente CLI, contrato, runtime y tests
modificados desde `before/` y retirar sólo `test_scenario1_navigation_only.py`;
conservar cambios posteriores y los límites 2 cm/2° respaldados previamente.

## Ajuste automático acotado de get1 — 28-09-2026

**Registro histórico: límites iniciales sustituidos.**
Los límites y el algoritmo siguientes se conservan para análisis y pruebas
offline; no representan una capacidad física habilitada. Consultar el
[perfil vigente](#reactivación-supervisada-del-ajuste-get1--28-09-2026).

**BOX-01-EXEC-IMPROVED, 12:35 CEST, Europe/Madrid.** Petición: corregir el
posicionamiento cuando no cumpla 2 cm/2° y seguir con el flujo. Instalado en
fuentes PC, cargado temporalmente para comprobaciones de lectura; prueba de
movimiento correctivo **PENDIENTE**. El ensayo físico de las 12:19 sólo probó
la llegada normal, que ya cumplía; no valida estas nuevas maniobras.

El comportamiento se aplica automáticamente a las tres entradas mejoradas,
incluido `force_improved_scenario1.sh --run`. No añade preguntas a `force` ni a
`autochecked`; esta última conserva la exigencia de referencias FT cualificadas.

1. La navegación inicial y sus dos muestras de llegada se mantienen.
   Ambas deben tener datos frescos, marcas crecientes y marco `map` válido.
   Si ambas cumplen 2 cm/2°, continúa sin nuevas consultas ni esperas.
2. Sólo un resultado de navegación exitoso con residual geométrico puede
   entrar en corrección. Error máximo admisible de entrada: **5 cm y 5°**.
   Los fallos de navegación, localización/telemetría, mapa o contenedores
   interrumpen el ciclo; no se transforman en un ajuste.
3. Antes de cada ajuste redescubre contenedores y verifica hashes, salud,
   HOME20D, mapa/FSM y que los puntos guardados no hayan cambiado. Lee otra
   pareja de poses: si ya cumple, evita enviar un movimiento. Si no, exige
   estabilidad ≤5 mm/1° entre ambas y prepara dos muestras nativas nuevas de
   mapa y odometría, con chasis estacionario.
4. Solicita `navigation_start` al **mismo x/y/yaw guardado de get1**, como
   `free_nav` explícito. Conserva el navegador y sus controles de obstáculos;
   no publica `/cmd_vel`, no cambia parámetros, no relocaliza durante el ajuste
   y no utiliza `front_nudge.py`, cuya prueba de retroceso sigue descalificada.
5. Después del resultado exige reposo del chasis con datos nuevos y las dos
   poses de llegada dentro de **2 cm/2°** antes de habilitar visión y agarre.
   Hay como máximo **dos ajustes adicionales**. El segundo requiere reducción
   de al menos 0,1 en `max(error_m/0,02, error_deg/2)`; la falta de progreso,
   un timeout o cualquier fallo detienen el flujo sin otro intento ni HOME.

La configuración de aceptación permanece en `ARRIVAL_TOLERANCES` de
[`scenario1_checks.py`](../../scripts/box_handling/scenario1_checks.py).
Los límites de vigilancia están en `POLICY` de
[`scenario1_nav_correction.py`](../../scripts/box_handling/scenario1_nav_correction.py):

| Límite | Valor |
| --- | --- |
| Ajustes adicionales / entrada máxima | 2 / 5 cm y 5° |
| Plazo por acción, incluida preparación | 15 s |
| Presupuesto global para admitir ajustes y fijar sus plazos | 40 s |
| Excursión / recorrido por intento, en cada marco | 8 cm / 12 cm |
| Empeoramiento respecto a la mejor distancia medida | 5 mm |
| Velocidad real lineal / angular máxima | 0,10 m/s / 0,25 rad/s |
| Excursión angular máxima por intento | 10° |
| Edad máxima de fuente y recepción de telemetría | 0,5 s |
| Sin mejora significativa mientras sigue fuera de tolerancia | 4 s |
| Estacionario al preparar y terminar | ≤0,003 m/s y ≤0,01 rad/s |
| Observación de reposo después del resultado, dentro de los 15 s | Hasta 1,5 s |

Se solicita velocidad lineal X 0,05 m/s y yaw 0,15 rad/s. No se presupone que
el controlador Arc respete esos campos en todas sus fases: se vigila velocidad
real y desviación. Mapa y odometría se comparan sólo contra sus propias
referencias, sin restar coordenadas de marcos diferentes. Los límites anteriores
son umbrales de detección/aborto, no una garantía de distancia física de frenado.
La petición de cancelación se dirige exclusivamente al UUID activo y se observa
su resultado hasta 8 s; incluso un éxito tardío mantiene la interrupción.
Los 40 s no son un plazo garantizado hasta quedar físicamente detenido:
las consultas y la observación final de cancelación pueden acabar después.
Tiempo añadido por corrección y repetibilidad: PENDIENTES de ensayo.

`navigate_get1` permanece en curso en el checkpoint durante todos los ajustes.
Antes de enviarlos persiste `get1-correction.json`; el diario añade
`get1_correction` y `correction_guard`, con intento, UUID, errores y medidas.
`arrival` sólo se emite cuando ambas muestras finales cumplen. Un checkpoint
fallido no permite reanudar hacia visión/agarre ni repetir automáticamente el
ciclo. `--stop-after get1` mantiene su terminación antes de SPS/recogida, también
si necesitó corregir. `put1` no incorpora ajustes y conserva 5 cm/3°.
En `--plan`, `automatic_retries: 0` se refiere a fallos de acción; el bloque
`get1_correction` describe por separado estos ajustes tras éxito técnico.

Fuentes de ejecución bajo `scripts/box_handling/`: `scenario1_checks.py`,
`scenario1_runtime.py`, `scenario1_action_client.py`, `scenario1_cli.py` y nuevo
`scenario1_nav_correction.py`. El CLI incorpora el módulo de vigilancia tanto
en el supervisor como en el proceso nativo de acciones. Activación automática
en la próxima invocación, sin instalación persistente ni reinicio del robot.
Dependencias nuevas de lectura: `/mc/odom` (`nav_msgs/msg/Odometry`); se conserva
`/nav/robot_pose` (`geometry_msgs/msg/PoseStamped`) y la API ROSA ya comprobada.

Comprobación local reproducible, sin conexión:

```bash
python3 -B -m unittest \
  scripts.box_handling.test_scenario1_nav_correction \
  scripts.box_handling.test_scenario1_correction_transport \
  scripts.box_handling.test_scenario1_navigation_correction \
  scripts.box_handling.test_scenario1_pose_preflight \
  scripts.box_handling.test_scenario1_navigation_only
./scripts/force_improved_scenario1.sh --plan
```

Comprobación técnica de lectura: `./scripts/force_improved_scenario1.sh --check`.
El ensayo correctivo requiere una nueva prueba autorizada y comprobar el
estado físico actual; no se reutiliza la confirmación del ensayo de las 12:19.

**Evidencia:**
`../Humanoide-vla-evidence/20260928T102716Z_SCENARIO1_GET1_CORRECTION/`.
`check/` y `check-final/` contienen --check real rc0, mapa/FSM preparados y dos poses nuevas.
`probe.stdout` recoge una prueba nativa del vigilante sin enviar objetivos:
2 publicadores de pose y 1 de odometría, marcos `map` y
`odom→base_footprint`, 12/86 muestras, velocidades y recorrido cero. El monitor
se armó sólo para leer; armar este objeto no envía comandos. La posición estaba
a 3,776 mm/0,293° de get1, por lo que no había corrección que ejecutar.
`probe-final.stdout` verifica además el modo de observación de reposo: 14/101
muestras de mapa/odometría, `settled=true` tras 0,165 s, recorrido y velocidades
cero, sin objetivo ni resultado físico de acción. Es validación del lector y
sus condiciones, no una prueba de desaceleración real. Distancia final medida
4,164 mm/0,294°; no se movió deliberadamente al robot para forzar una corrección.
**355 pruebas offline pasan**, incluida la carga del módulo en el proceso
nativo embebido, cancelación por UUID, reposo posterior y bloqueo del agarre
ante cualquier fallo. Sintaxis, los tres planes y `git diff --check` correctos.
`unit-tests.txt` y `verification.json` documentan las pruebas finales y alcance;
quedan fuera los tests no versionados del trabajo de depósito pendiente.

Backup previo en `before/` conserva los cambios de tolerancia y navegación
exclusiva anteriores; `before-sha256.json`, `after-sha256.json` y
`changed-files.json` identifican versiones exactas sin depender de un commit.
Reversión: restaurar selectivamente los archivos cambiados desde `before/` y
retirar sólo los tres tests nuevos de corrección y `scenario1_nav_correction.py`,
preservando cualquier trabajo posterior. No usar `git reset` ni restaurar todo
desde v0.0.1: se perderían los cambios anteriores. Los procesos de lectura se
terminaron; no hay configuración operativa remota que revertir. Tag v0.0.1,
altura de depósito pendiente y trabajo ajeno conservados; sin commit ni push.

## Sello articular repetido o regresivo antes de retreat — 28-09-2026

Esta sección conserva la situación anterior a implementar reanudación por
etapa. La recuperación explícita disponible ahora se describe
[más abajo](#reanudación-por-etapa--28-09-2026); el fallo original permanece archivado.

**BOX-01-EXEC-IMPROVED, 12:50 CEST, Europe/Madrid.** El ciclo del usuario
`20260928T104306Z_IMPROVED_SCENARIO1_886744` termina el agarre `c0654cd5…`
con `SUCCEED` y completa `verify_held` bajo política `assume`. Entra en
`retreat`, descubre contenedores y comprueba dependencias; falla la petición 8
de salud con `Nonadvancing actuator source timestamp` después de 2,05 s.
El diario no contiene un despacho de retroceso, depósito ni HOME posterior.
El tiempo mostrado para `health` es duración de la consulta hasta fallar,
no confirmación de salud correcta. La llegada a get1 cumplió 14,11 mm/0,29°;
no se activó ninguna corrección automática.

El usuario confirma **caja sujeta y completamente separada de la pila**.
Es confirmación presencial, no conclusión extraída de la foto o del éxito
técnico del agarre. El archivo final conserva `failure: retreat` y
`box_state: unknown` conforme al contrato de interrupción. No se ha editado
ni sustituido por el checkpoint limpio anterior. `--resume` no admite este
estado y `--run` iniciaría de nuevo el ciclo; la recuperación física debe
prepararse específicamente desde caja sujeta, sin repetir agarre ni HOME.
En esta intervención no se enviaron movimientos.

El error antiguo usa una única condición `stamp <= last_stamp` y no registra
el sello anterior/actual: **no se puede determinar si el incidente fue una
duplicación o un retroceso**. Una captura posterior de 10 s recibió 500 mensajes
con un único publicador y ningún duplicado/regresión. Cinco peticiones
posteriores de salud también finalizaron correctamente; no demuestran que
el incidente original esté resuelto. No se declara fallo mecánico ni avería
permanente del sensor a partir de ese mensaje.

Se endurece y precisa el tratamiento en
[`scenario1_health_worker.py`](../../scripts/box_handling/scenario1_health_worker.py):

- Sólo para `actuator`, mismo sello y contenido completo idéntico en JSON
  canónico se descarta sin añadir muestra, cambiar `last_stamp` ni renovar
  recepción/edad. El informe registra `actuator_duplicates_ignored`.
- Mismo sello con contenido distinto, cualquier retroceso y sellos inválidos,
  futuros o caducados siguen rechazados. Los errores incluyen ambos sellos,
  diferencia temporal y hashes del contenido para distinguir causas.
- Datos anteriores al inicio sólo se ignoran antes de recibir la primera
  muestra nueva; una regresión posterior ya no se oculta como cola antigua.
- Siguen siendo necesarias dos muestras distintas posteriores a la petición,
  ambas con edad ≤2 s, salud completa y publicadores únicos. Esperar al controlador
  no permite mantener válidas muestras congeladas. El timeout máximo sigue 12 s.
  La política de marcas repetidas de `pose` no se relaja.

Cambios sólo en fuentes PC: módulo anterior y
[`test_scenario1_health_worker.py`](../../scripts/box_handling/test_scenario1_health_worker.py),
más registro global y guías. Las tres entradas incorporan el módulo en memoria
en su próxima invocación; no requieren instalación, reinicio ni modificar SDK,
mapa, sensores o tareas del robot. Comprobación offline reproducible:

```bash
python3 -B -m unittest scripts.box_handling.test_scenario1_health_worker
./scripts/force_improved_scenario1.sh --plan
```

VERIFICADO: 31 pruebas del lector, incluidos duplicados sin renovación, contenido
conflictivo, regresión previa al inicio, congelación durante espera del
controlador y timeout de 12 s con reloj simulado. Regresión completa: **364 pruebas pasan**. Detalle
en `unit-tests.txt`/`verification.json` de la evidencia.
Lectura real del módulo nuevo: cinco consultas `health(require_home=False)`,
3,42–4,94 s, dos sellos nuevos por consulta y cero duplicados ignorados.
Paros 0/0 y cargador 0, baterías 56,5% y 57,5–57,8%, velocidad articular 0,
`MEASURED_HOME=0`; controlador/acción libre verificados por el lector.
No se usó `--check` inicial, que exige HOME, ni se ordenó HOME para satisfacerlo.
Esto comprueba la lectura desde la postura actual, no autoriza retirada ni
demuestra la sujeción por fuerza. La confirmación de caja corresponde al usuario.

Evidencia:
`../Humanoide-vla-evidence/20260928T104807Z_SCENARIO1_ACTUATOR_TIMESTAMP/`.
Incluye `incident-reference.json` (rutas/hashes del incidente original),
`incident-checkpoint.json`, `incident-events-summary.json`, `stamp-probe.json`,
`health-qualification.json`, fuentes exactas de los colectores y sus hashes,
`before/`, `after/`, `before-sha256.json`, `after-sha256.json`,
`changed-files.json`, `verification.json` y `unit-tests.txt`.
Los procesos nativos de lectura en Motion 192.168.11.2 se terminaron; ningún
publicador/cliente de acciones ni cambio persistente remoto. Roles redescubiertos
en ambas consultas; no se asumen nombres de contenedor a partir del histórico.

Reversión: restaurar selectivamente módulo/test desde `before/`, preservando
los cambios previos de get1 y cualquier trabajo posterior; actualizar estas
notas al revertir. Sin rollback de configuración remota. Causa exacta y ensayo
de ciclo posterior PENDIENTES; recuperación física desde la caja sujeta también
PENDIENTE. Checkpoint, tag v0.0.1 y trabajo de altura ajeno conservados; sin commit/push.

## Reanudación por etapa — 28-09-2026

**BOX-01-EXEC-IMPROVED, 13:12 CEST, Europe/Madrid.** Implementado por petición
del usuario. `--resume` acepta checkpoints v1/v2/v3 y puede entrar por cualquiera
de las diez etapas. El perfil, política, arranque, contenedores, dependencias y
puntos del mapa deben coincidir con el contexto del origen. Un cambio de contexto
exige otra preparación; seleccionar una etapa no lo omite.

```bash
# Caso actual: revisar la recuperación, sin mover ni consumir el checkpoint:
./scripts/force_improved_scenario1.sh \
  --resume ../Humanoide-vla-evidence/20260928T104306Z_IMPROVED_SCENARIO1_886744/checkpoint.json \
  --from-stage retreat --box-state held --recovery-confirmed --check
```

`--plan` muestra la entrada, etapas pendientes y requisitos sin conexión.
`--check` comprueba el estado actual sin armar, consumir el origen ni crear un
checkpoint ejecutable nuevo. **Quitar `--check` ejecuta la continuación**;
no requiere añadir `--run`. La declaración `held` significa caja completamente
separada, sujeta y estable; `released`, caja apoyada y liberada; `empty`,
abrazaderas vacías. No son mediciones sensoriales.

Sin `--from-stage`, selecciona la siguiente etapa del origen, incluso al acabar
una parada en get1/agarre. Un ciclo ya completo requiere selección explícita.
Una frontera limpia con caja conocida permite inferir ese estado bajo la misma
política; fallo, etapa en curso, caja indeterminada, salto o repetición requieren
**`--box-state` y `--recovery-confirmed`**. Esta última declara que el operador
ha resuelto el estado físico y que la etapa/recorrido elegidos son adecuados.
No desactiva ningún control ni autoriza por sí sola a mover durante un check.
Antes de ejecutar deben estar comprobadas las condiciones físicas actuales
del proyecto: efector, carga, postura, batería/cargador, paros, ruedas, modo,
zona libre, mando exclusivo y persona junto al paro. `force` no añade preguntas;
`ask` conserva sus confirmaciones presenciales.

| Etapa | Caja requerida | Condición adicional de entrada |
| --- | --- | --- |
| `navigate_get1` | `empty` | HOME20D |
| `enable_vision` | `empty` | HOME20D y get1 ≤2 cm/2° |
| `grasp` | `empty` | HOME20D y get1; prepara visión y SPS nuevo antes de agarrar |
| `verify_held` | `held` | get1; verifica sujeción sin repetir agarre |
| `retreat` | `held` | get1 y espacio trasero libre |
| `navigate_put1` | `held` | Caja libre para navegar hacia put1 |
| `deposit` | `held` | put1 ≤5 cm/3° y apoyo compatible |
| `verify_released` | `released` | Verifica liberación sin repetir depósito |
| `home` | `released` | Trayectoria HOME libre |
| `verify_home` | `released` | HOME20D medido, sin nueva orden HOME |

Todas las entradas comprueban salud articular, acción libre, mapa/FSM listos y
**chasis detenido**. El helper nativo nuevo lee dos muestras de `/mc/odom`
posteriores a la petición: un publicador, marcos estables, edad ≤0,5 s,
velocidad ≤0,003 m/s y 0,01 rad/s, variación ≤5 mm/1°. Plazo máximo 5 s y lease vigente;
sin servicios ni publicadores de mando. El waypoint usa dos poses frescas y no
intenta corregir automáticamente una entrada de recuperación mal situada.
Se vuelve a comprobar la entrada justo al iniciar la primera etapa, después
de persistir su intención y antes de cualquier acción, aunque las confirmaciones
anteriores se hayan demorado. También exige el handshake de resume antes de arm.

**Retreat sigue ordenando 20 cm completos relativos hacia atrás.** No calcula
el recorrido pendiente de una retirada parcial. Estar otra vez dentro de la
tolerancia de get1 no demuestra que nunca retrocedió unos milímetros. Tras una
acción incierta, el operador debe resolver esa situación antes de elegir
`retreat`; puede seleccionar `navigate_put1` cuando la caja y el espacio ya
permitan esa navegación. No se deduce “no enviado” de la mera ausencia de un
evento de despacho. El incidente 104306 sí tiene fallo documentado durante salud,
antes de la llamada de movimiento; su elección actual no repite un agarre.

`autochecked` mantiene perfil cualificado y medidas FT/articulares para entradas
`held/released`. Una postura sin referencias compatibles sigue bloqueada; la
declaración de caja nunca se convierte en evidencia de sensores. Esto puede
impedir alguna entrada hasta disponer de calibración para esa postura.

El checkpoint versión3 comienza con `completed: []`, `entry_stage`,
`entry_box_state` y `origin`. No inventa éxitos de etapas omitidas. Cada etapa
completada se añade al segmento real; fallos nuevos quedan en la nueva evidencia.
`origin` conserva hash del checkpoint de origen, fallo/etapa en curso, selección,
declaraciones y etapas saltadas/repetidas. El CLI archiva el origen dentro de un
contenedor JSON `resume_source_snapshot` **no ejecutable como checkpoint**,
el plan y su contexto. Recalcula el plan en Motion y relee el origen antes de
consumirlo; cualquier cambio aborta antes de arm. El marcador
`checkpoint.json.consumed.json` se crea sólo al ejecutar, antes de armar.
Una prueba o cancelación previa no fabrica otra copia limpia reutilizable.
SPS sólo se inicia si el segmento pendiente incluye agarre.

Fuentes bajo `scripts/box_handling/`: `scenario1_cli.py`,
`scenario1_contract.py`, `scenario1_runtime.py`, nuevos `scenario1_resume.py`
y `scenario1_resume_worker.py`. Se cargan desde PC en la siguiente invocación;
no hay instalación persistente, modificación del SDK/XML/YAML ni reinicio.
Pruebas reproducibles sin conexión:

```bash
python3 -B -m unittest \
  scripts.box_handling.test_scenario1_resume \
  scripts.box_handling.test_scenario1_resume_worker \
  scripts.box_handling.test_scenario1_resume_runtime
```

**418 pruebas offline pasan**, incluidas compatibilidad previa, diez entradas,
fallos de salud/pose/odometría, ausencia de comandos en check, procedencia,
consumo y revalidación antes de actuar. Sintaxis, ayudas, planes y diff correctos.

Lectura real `--resume ... --from-stage retreat ... --check`: **rc0**, base
quieta y dos poses a 11,240 mm/0,156° de get1, dentro del criterio. No hubo arm,
etapas, SPS ni objetivos físicos; el origen sigue sin consumir. Es prueba de
preparación técnica, no de continuación física. La autorización para programar
la función no se utilizó como autorización para mover al robot.

Evidencia y versiones exactas:
`../Humanoide-vla-evidence/20260928T110310Z_SCENARIO1_RESUME_STAGES/`
(`before/`, `after/`, `before-sha256.json`, `after-sha256.json`,
`changed-files.json`, `unit-tests.txt`, `verification.json`, `check-retreat/`, `check-final/`).
El respaldo conserva las modificaciones anteriores de get1 y sellos articulares.
Reversión selectiva de CLI/contrato/runtime desde `before/`, retirar únicamente
los dos módulos y tres tests nuevos de resume; conservar trabajo posterior.
Sin rollback operativo remoto. No consumir/borrar marcadores como forma de
repetir acciones. Continuación física PENDIENTE; tag v0.0.1 y trabajo de altura
ajeno conservados, sin commit/push.
Reversión física: no automática; no se ordenó volver al punto de salida ni HOME.


## Bloqueo de corrección free_nav por velocidad — 28-09-2026

**Registro histórico: bloqueo sustituido por la
[reactivación supervisada](#reactivación-supervisada-del-ajuste-get1--28-09-2026).**
La mitigación descrita aquí bloqueaba la corrección física automática. Sustituyó la disponibilidad de hasta dos ajustes descrita en la
sección histórica de las 12:35. La navegación inicial y llegada exigida siguen
siendo 2 cm/2° en get1 y 5 cm/3° en put1. No se cambian velocidades originales
del recorrido, XML/YAML, mapa, abrazaderas ni altura de depósito.

### Causa observada y límites del diagnóstico

El intento del usuario `20260928T112349Z_IMPROVED_SCENARIO1_1010309` llegó a
get1 con residual de 27,32 mm/0,385°. La primera corrección `free_nav` pidió
0,05 m/s lineal y 0,15 rad/s angular, pero el guard midió **0,261430929 rad/s**,
por encima de 0,25 rad/s. Velocidad lineal máxima 0,007283259 m/s, inferior al
límite de 0,10. El guard estaba activo, no preparando ni comprobando reposo.

El evento 243 de `events.jsonl` registra el error; 244 contiene los máximos;
245 solicita cancelar UUID `7a0f4969-80ba-4262-bd56-57544cc204b6`; 252 devuelve
status 5/cancelado. `LOCATION_LOST` aparece después de solicitar cancelar:
no fue la condición que disparó esta cancelación. No se ha reparado ni dado
por válido el subsistema visual. Ningún objetivo Motion de agarre se envió en
este intento. Una respuesta cancelada no prueba por sí sola reposo físico.

El máximo angular es la norma XYZ del twist. La muestra causante no se guardó
completa en aquella versión: eje/signo exacto y subfase nativa, PENDIENTES.
El [análisis local del proveedor](ARC_PRECISE_ARRANQUE_20260922.md) demuestra que
ArcPrecise no aplica `setNaviSpeed`/`level` y tiene un límite angular interno
propio; el giro final usa otro límite en el árbol. Por tanto, bajar sólo el
campo `speed` no es una solución demostrada. No se han vuelto a consultar
configuraciones remotas en esta intervención ni se atribuye una subfase
concreta sin sus registros internos.

### Comportamiento actual

- Una llegada ya dentro de tolerancia conserva exactamente sus consultas y
  continúa el flujo. No se añaden preguntas.
- Dentro de la antigua envolvente correctiva, se conserva el preflight y una
  nueva pareja de poses: si se estabilizan dentro, continúa sin otro objetivo.
- Si siguen fuera, registra `get1_correction/blocked_before_dispatch`, muestra
  distancia y ángulo medidos y falla con `GET1_CORRECTION_UNQUALIFIED` antes de
  escribir una intención correctiva o enviar una segunda navegación. No abre
  abrazaderas ni ejecuta agarre, HOME o reintentos por este fallo.
- Hay bloqueo adicional en `Runtime.action` y en el cliente nativo antes de
  armar/enviar una corrección. No hay flag CLI, JSON o variable de entorno para
  saltarlo. `--plan` publica `motion_enabled:false`; las tres entradas avisan
  del estado al iniciar. `--check` correcto verifica infraestructura, no
  cualifica automáticamente el ajuste fino.
- Se mantienen todos los límites del monitor, incluida velocidad angular
  0,25 rad/s. Si se usa en simulación, el error de velocidad ahora distingue
  preparación/actividad/reposo final y guarda magnitudes, límites, sellos y
  copia de la muestra causante en `velocity_violation`.

### Reproducir y revertir

```bash
./scripts/force_improved_scenario1.sh --plan
python3 -B -m unittest \
  scripts.box_handling.test_scenario1_nav_correction \
  scripts.box_handling.test_scenario1_navigation_correction \
  scripts.box_handling.test_scenario1_correction_transport
```

Las pruebas del algoritmo retirado sólo lo habilitan con mocks explícitos
locales, sin ROS ni transporte físico. Las regresiones operativas ejercitan el
bloqueo real sin esos mocks y verifican ausencia de segundo objetivo, intención
correctiva y continuación hacia agarre. La inyección de la velocidad observada
sigue causando fallo; no se amplió el umbral para ocultarlo.

Respaldo anterior, fuentes posteriores, hashes y resultados en
`../Humanoide-vla-evidence/20260928T112641Z_SCENARIO1_CORRECTION_VELOCITY/`
(`before/`, `after/`, `before-sha256.json`, `after-sha256.json`,
`changed-files.json`, `incident-summary.json`, `unit-tests.txt`, `verification.json`).
La reversión técnica es selectiva desde `before/`, preservando otros cambios,
pero reactivaría una maniobra cuya incompatibilidad ya fue observada; no es la
solución de la incidencia. Ningún cambio o rollback operativo remoto.

**Punto pendiente:** preparar y validar un controlador/árbol de ajuste cuyo
límite efectivo cubra todas las fases, con comprobación de frenado y llegada.
La mitigación evita relanzar la maniobra incompatible, no recupera todavía la
capacidad de corregir automáticamente todos los residuales. No se ha movido el
robot ni probado físicamente esta versión. VERIFICADO: 428 pruebas offline
sin fallos, AST/bash y --help/--plan de las tres entradas; detalle en
`verification.json`. Estado físico actual PENDIENTE.


## Reactivación supervisada del ajuste get1 — 28-09-2026

**Estado: habilitado en fuentes PC por petición explícita del operador de
relajar límites cuando ayude a posicionarse. Validación física PENDIENTE.**
Sustituye el bloqueo total anterior. La política de confirmación de caja no
cambia y no se añaden preguntas. Se aplica con el siguiente inicio de cualquiera
de las tres entradas mejoradas; no modifica el script antiguo.

### Motivo y decisión

El intento `20260928T114539Z_IMPROVED_SCENARIO1_1076787` llegó a 28,966 mm y
0,352°; no se envió corrección. Respecto al robot: destino 16,656 mm delante y
23,698 mm a la izquierda, dirección ≈54,898°. Elevar sólo 0,25 a 0,35 rad/s
seguiría cortando una maniobra que ArcPrecise permite hasta 0,5 rad/s y cuyo
orientador final tiene un límite separado de 1,1 rad/s.

El [análisis del binario capturado](ARC_PRECISE_ARRANQUE_20260922.md) muestra
`R=abs(distancia/(2*sin(alpha)))`, limitado a [0,01;5] m, y giro angular
recortado a ±0,5 rad/s. Una curva circular ideal hasta el destino cambia el
rumbo en **2×alpha**, no sólo alpha: para el residual observado, radio ≈17,70 mm,
arco ≈109,80° y longitud ≈33,92 mm. Es un cálculo geométrico, no simulación
física ni demostración del recorrido que elegirá el robot. El control discreto,
retroceso inicial, saturación y tolerancia de salida pueden cambiarlo.

### Límites del supervisor

Configuración versionada en
[`scenario1_nav_correction.py`](../../scripts/box_handling/scenario1_nav_correction.py),
`POLICY`, `yaw_limits()` y `Guard.angular_limit()`. Son límites de detección y
cancelación sobre datos medidos, no consignas ni garantía de distancia de frenado.
La orden conserva 0,05 m/s lineal y 0,15 rad/s angular solicitados al navegador.

| Condición | Límite vigente |
| --- | --- |
| Entrada a corrección | Residual máximo 5 cm y 5°, HOME fresco y chasis quieto |
| Llegada aceptada | Dos poses nuevas en get1 dentro de 2 cm y 2° |
| Velocidad lineal medida | 0,10 m/s, conservada |
| Velocidad angular al aproximar | 0,60 rad/s |
| Velocidad angular junto al destino | 1,20 rad/s sólo con las dos últimas poses frescas a ≤2 cm y velocidad lineal medida ≤0,02 m/s; en otro caso vuelve a 0,60 |
| Excursión angular | `2×bearing cercano + error yaw final +15°`, mínimo10°, máximo195° |
| Giro acumulado absoluto | `2×excursión permitida +10°`, máximo400° |
| Excursión del centro / recorrido acumulado | 8 cm / 12 cm por intento, conservados e independientes para mapa y odometría |
| Empeoramiento transitorio de distancia | Hasta15 mm respecto a la mejor distancia registrada |
| Tiempo | Hasta30 s por acción, hasta70 s de presupuesto de correcciones; máximo2 intentos |
| Telemetría / progreso / reposo final | Edad0,5 s;4 s sin progreso;1,5 s para confirmar reposo final, conservados |

La cota angular depende de cada geometría, considerando la dirección más cercana
con avance o retroceso: el caso114539 permite ≈125,15° de excursión y260,30°
acumulados. Se integra giro firmado entre muestras para medir excursión sin
perder vueltas al cruzar ±180°; acumular sólo `wrap(yaw−origen)` haría ineficaz
un umbral195°. El acumulado absoluto limita oscilaciones de ida y vuelta.
El cuerpo y los brazos barren espacio al girar:8 cm limita el centro, no el
volumen del robot. Sigue siendo necesario un recorrido libre para el giro,
abrazaderas vacías y HOME; no trasladar estos límites a transporte con caja.

El margen15 mm permite el arranque inverso conocido de Arc (ensayo anterior
7,503 mm; cálculo de primeras consignas ≈10 mm). No se ignora un alejamiento
indefinido: siguen el límite respecto al mejor valor, excursión, camino,
progreso y tiempo. 30 s no garantiza agotar todos los plazos máximos del proveedor
(25 s de control preciso más20 s del orientador); es un presupuesto menor
intencionado para un ajuste local.

El permiso de1,20rad/s exige además dos poses compatibles con el sello fuente
de la velocidad; posiciones posteriores no autorizan retroactivamente un giro
anterior. Un historial acotado permite asociar los streams aunque DDS entregue
odometría con retraso. Cada avance real de2mm reancla la referencia angular
para que el regreso lento tras la curva cuente como progreso.

El watchdog cuenta progreso geométrico: antes de entrar a2 cm, orientarse hacia
el desplazamiento más cercano y reducir distancia; al entrar, orientarse al yaw
final. La entrada a esa fase sólo reinicia su referencia una vez; oscilar sobre
el umbral no renueva indefinidamente el plazo. No se fuerza una trayectoria
«giro, recta, giro»: el navegador conserva su planificador y anticolisión.

### Qué se ha verificado

VERIFICADO: **446 pruebas offline**, sin fallos ni omisiones; AST/bash y
--help/--plan de las tres entradas.

Pruebas offline del residual observado y arco ideal, giro previo, orientación
final y reposo. La antigua velocidad0,261430929 se admite; superar0,60 lejos,
1,20 cerca o el límite lineal cancela. Regresiones de mapas caducados, una sola
pose cercana, traslación excesiva, cambio de marcos, watchdog, lease, oscilación,
plazos y cancelación por UUID siguen obligatorias. Se conservan llegada2cm/2°
y fallo duradero; no se reintenta un fallo técnico ni se ordena HOME por error.

`qualification_report()` distingue `motion_enabled:true` y
`physical_validation:pending`: habilitar el perfil por petición del operador
no equivale a certificarlo físicamente. Los simuladores recorren ahora la vía
habilitada real; las pruebas del bloqueo utilizan una indisponibilidad inyectada.
Una llegada inicial ya válida no añade consultas ni maniobras.

```bash
./scripts/force_improved_scenario1.sh --plan
python3 -B -m unittest \
  scripts.box_handling.test_scenario1_nav_correction \
  scripts.box_handling.test_scenario1_navigation_correction \
  scripts.box_handling.test_scenario1_correction_transport \
  scripts.box_handling.test_scenario1_policies
```

La prueba física acotada utiliza primero `--check` y después
`--run --stop-after get1`, con estado físico actualizado y zona libre también
para girar. Ese modo no inicia agarre. El ciclo normal emplea el mismo ajuste y
continúa únicamente tras la llegada confirmada. No se ha ejecutado ninguna de
esas órdenes de movimiento en esta intervención; no asumir el estado físico de
los registros anteriores. Convergencia, duración real y frenado PENDIENTES.

### Evidencia y reversión

Destino: fuentes PC del ejecutor, sin cambios persistentes de robot, SDK,
configuración nativa, mapas ni XML/YAML. Backup incluye los cambios locales
previos sin commit. Fuentes/hashes antes y después, cálculo del residual y
resultados en
`../Humanoide-vla-evidence/20260928T115136Z_SCENARIO1_CORRECTION_REENABLE/`
(`before/`, `after/`, `before-sha256.json`, `after-sha256.json`,
`incident-summary.json`, `changed-files.json`, `unit-tests.txt`, `verification.json`).
Reversión selectiva desde `before/` devuelve el bloqueo total y los límites
anteriores, preservando trabajo ajeno; actualizar estado en guías/índice. No
rollback remoto ni reproducción de estados transitorios. Sin commit/push.


## Consola resumida — 28-09-2026

**BOX-01-EXEC-IMPROVED, 14:43 CEST, Europe/Madrid.** Cambio de presentación
solicitado por el usuario para eliminar el JSON repetido del terminal. Afecta a
`ask_improved_scenario1.sh`, `force_improved_scenario1.sh` y
`force_improved_scenario1_autochecked.sh`, que comparten el cliente PC.

Ejemplo ilustrativo, sin constituir evidencia de una prueba física:

```text
Etapa 3/10: Recoger y separar la caja
  Comprobación de estado técnico: 2,1 s
  En curso — 12,8 s
  Resultado recibido: SUCCEED
  Etapa completada: 34,5 s
Etapa 4/10: Registrar sujeción
  Etapa completada: 0,0 s; estado de caja asumido
```

- Tiempos con un decimal; residual de posición en mm y grados. El redondeo sólo
  afecta al texto: las comparaciones mantienen los datos originales.
- Feedback normal repetido como máximo una vez por segundo, por objetivo y
  tipo de acción, mediante reloj monotónico PC. El primer mensaje y los cambios
  de estado se muestran inmediatamente; no se añaden esperas al flujo.
- Errores, obstáculos, pérdida de localización, rechazos y cancelaciones sin
  limitación de frecuencia. El lector sigue mostrándolos durante el cierre,
  aunque la espera principal ya haya fallado. Una respuesta de cancelación no
  se presenta como prueba de parada física.
- `FINISH`, `SUCCEED` y `status=4` se presentan como feedback/respuesta; sólo el
  evento `stage_complete` anuncia la etapa completada. El tiempo de una consulta
  de salud no afirma éxito; las confirmaciones `assumed` siguen identificadas.
- `events.jsonl` guarda cada línea original antes de resumirla. Checkpoints,
  validaciones, objetivos y mecanismos de cancelación conservan su protocolo.
  Una excepción del formateador no consume el evento ni suprime un fallo técnico.

El formato se activa al siguiente inicio, sin argumentos nuevos. Para diagnóstico
completo en consola, añadir `--verbose` a cualquiera de las tres entradas:

```bash
./scripts/force_improved_scenario1.sh --help
./scripts/force_improved_scenario1.sh --check --verbose
```

La segunda orden conecta y consulta sin iniciar movimientos; no se ejecutó en
esta intervención. `--plan` conserva su JSON de planificación. `--verbose` no
cambia el detalle de `events.jsonl`, que ya es completo por defecto.

Fuente reproducible: `scripts/box_handling/scenario1_console.py` y su integración
en `scenario1_cli.py`; Python estándar, sólo en el PC. El formateador no se envía
al robot y su hash se incorpora a `source-sha256.json` en cada ejecución.

Verificación **VERIFICADO offline**: 462 pruebas correctas, incluidas 16 de
presentación, más regresiones del supervisor; sintaxis Python/bash, `--help` y `--plan` de las tres entradas. Conteo
y resultados exactos en `verification.json`. Registro íntegro, checkpoints,
limitación de feedback, estados asumidos, avisos y cierre tardío cubiertos por
`test_scenario1_console.py`. Prueba física con este formato: **PENDIENTE**;
no se ha conectado al robot ni enviado movimiento.

Backup, hashes antes/después, fuentes finales, pruebas y muestra de consola:
`../Humanoide-vla-evidence/20260928T123214Z_SCENARIO1_CONSOLE/`.
Para revertir, restaurar selectivamente los archivos de `changed-files.json`
desde `before/`, preservando cambios posteriores; los dos archivos nuevos
(formateador y su test) pueden retirarse después de restaurar el cliente.
No requiere restaurar robot, mapas, tareas, estados transitorios ni checkpoints.
Actualizar este estado y el índice al revertir. Sin commit ni push.
