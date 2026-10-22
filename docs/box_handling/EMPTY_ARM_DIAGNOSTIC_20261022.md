# Diagnóstico de brazos en vacío — 22-10-2026

**Último resultado: BOX-NATIVE-ARM-PREPARATION-DIAG-20261022.** Las preparaciones
nativas completas de derecho e izquierdo, ensayadas por separado, terminan
`SUCCEED/status4/state1101001`. El operador confirma que **observó ambos
movimientos normales, sin ruidos ni contacto**. Es preparación articular en
vacío; no reproduce MetaClamp, inserción/separación, fuerza, agarre ni carga.
Postflight final correcto; ambos XML y soporte temporal RETIRADOS, originales
verificados intactos. Las rutas de prueba citadas son históricas y ya no existen:
otro check o ensayo exige **staging NUEVO**, referencias actuales y autorización
aplicable. [Receta nativa y alcance](#preparación-nativa-completa-de-un-brazo).

**BOX-EMPTY-ARM-CONTROL-DIAG-20261022. Derecho e izquierdo ejecutados una vez
cada uno; SDK/telemetría correctos, archivos temporales RETIRADOS.** Fecha/zona:
22-10-2026, Europe/Madrid. El usuario pide comprobar primero el derecho sin
caja y valorar después el izquierdo si el primero no identifica el problema.
Confirma abrazaderas vacías/libres, caja apoyada o retirada, sin contacto y
robot alejado de la caja. Son confirmaciones del operador; postura, paros y
controlador requieren consulta actual antes de movimiento.

Evidencia privada de esta intervención:
`../Humanoide-vla-evidence/20261022T093744Z_EMPTY_ARM_CONTROL_DIAGNOSTIC/`.
El primer check detectó cargador conectado y bloqueó la prueba; el general
anterior terminó55. `blocked-charger-check-receipt.json` conserva el bloqueo78
de09:49:20 UTC: **su salida raw fue sobrescrita por el check posterior**;
no se presenta como un archivo raw original conservado. Tras desconexión comunicada por el operador, el nuevo
`right-check.jsonl` pasa con `all_pass=true`, igual que el preflight repetido
antes del único run derecho. Esos rechazos iniciales no se presentan como
preflights aprobados ni se eliminan del relato.

## Resultados medidos de los dos ensayos pequeños

Una sola reproducción derecha comienza el22-10 a09:51:57,844753 UTC
(11:51:57 CEST) y termina en23,111726s con rc0 y texto SDK
`is_finished=true, bag has been played successfully`. No se pidió HOME ni
reintento. La captura retiene1.199 mensajes de actuadores y1.495 JointState,
sin errores de validación, fault o paro activo en la muestra; conserva aparte
una línea INFO no JSON. Recorrido medido de shoulder-yaw≈1,983° y
elbow-roll≈1,582°; error máximo consigna/posición de los siete ejes derechos
≈0,06501°. Son picos de las muestras retenidas, no cada actualización del servo.

El operador aclara después que **no estuvo pendiente visualmente del ensayo**.
No se registra suavidad, ausencia de contacto/ruido ni inspección visual como
confirmadas. El resultado SDK/telemetría no sustituye esa observación ni prueba
salud mecánica general, seguimiento con carga o la preparación completa.

Dentro de la petición de examinar el izquierdo si el derecho no identifica el
problema, se construye un candidato izquierdo desde `right-postflight-joints.json`,
SHA de entrada`ea49124b2dd2aa097964566183736d16e5bd3277729172d8da3f7de08039ffcf`.
El candidato tiene SHA256
`329ac9e6a9ae431daca6516ac21e93e66a4148c4463e0dd9a1ef25d588589f28`;
staging nuevo`/tmp/empty_arm_diag_20261022T093744Z_left.motion` verificado.
`left-check.jsonl` pasa. Una reproducción izquierda comienza a09:54:55,299832 UTC
(11:54:55 CEST), termina en23,109012s, rc0 y texto SDK de finalización correcta;
sin HOME ni reintento. La captura retiene1.199 mensajes de actuadores y1.494
JointState,9 de cada paro/todos0, sin errores de validación ni fault/deshabilitación
en la muestra. El yaw izquierdo recorre1,977539° y codo-roll1,582031°;
error máximo consigna/posición de los siete ejes izquierdos0,070507°.

Los postflights de ambos lados pasan las consultas de reposo, salud, control
exclusivo y paros/cargador. Máximo absoluto canónico20D:0,002972088rad tras
derecho y0,004410195rad tras izquierdo, próximos a HOME en esas consultas.
No son verificación del agarre ni del estado físico posterior a otras acciones.
Las dos capturas conservan una línea INFO no JSON y sus limitaciones; no se
fabrican flags de captura de seguridad validada. Los archivos temporales de
ambos candidatos se retiran con rc0, recibos `right-cleanup-result.json` y
`left-cleanup-result.json`; copias/reviews privadas conservadas.
Fuentes: checks/runs, `basic-tests-summary.json`, ambos `*-trace-analysis.json`,
postflights y reviews. No hay observación visual de suavidad/contacto acreditada
por estos datos; el usuario indicó que no estuvo pendiente del ensayo derecho.

## Último agarre real y distinción del diagnóstico

Para el intento524935, el operador aclara que **accionó el paro al prever que
el izquierdo iba a chocar**, sin contacto y con la caja apenas desplazada según
su relato. El diario termina con pérdida del worker, diagnóstico de paro no
confirmado libre y cancelación propia ack0/status5; no demuestra causa mecánica
ni parada física mediante el software. Se distingue de los contactos reportados
en otras ejecuciones del22Oct; no se reescribe esa historia como el mismo caso.
Antes de ese agarre hubo **una** corrección visual de chasis solicitada de
21,200095mm, llegada medida≈10,389mm/0,384° y nueva selección SPS en
X≈0,763103m. Es evidencia de ese ajuste y del gate perceptivo, no de separación
o agarre completados. El checkpoint de ese intento conserva fallo/unknown.

El usuario solicita después movimientos más representativos. Esa prueba nativa
**diferente**, completada más abajo, copia siete ejes de la preparación completa
por un brazo mediante MetaMove3s y retorno a la referencia medida6s. No es el
archivo SDK de2° ni incluye fuerza, cabeza, torso, visión, separación o agarre.
Su éxito no resuelve por sí mismo el incidente. Una prueba del MetaClamp completo
en vacío necesitaría un contrato de objetivo explícito que aún no está
determinado: continúa PENDIENTE y no se entrega una pose SPS sintética.

## Preparación nativa completa de un brazo

**BOX-NATIVE-ARM-PREPARATION-DIAG-20261022 — tareas aditivas instaladas,
cargadas y PROBADAS FÍSICAMENTE por separado.** No se reemplaza el XML original
ni se cambia `task_list`, SDK, límites o parámetros de fuerza. Cada tarea sólo
contiene dos `MetaMove` del brazo elegido: su acción original de3s, copiada
exactamente del XML nativo hash
`4ba2515ba030f7f1483eed704ce68e0d888ac29754bef1645908fb9f96345e0b`,
y un retorno nuevo de6s a los siete ángulos medidos al preparar el manifiesto.
No contiene acciones de cabeza/elevador/cintura, MetaClamp, visión o HOME global.
Al ejecutar un brazo cada vez se diferencia del `Parallel` bimanual original.

| Lado | XML aditivo / resultado |
| --- | --- |
| Derecho | `diagnostics/native_arm_preparation_right_1f1b5137f17f4730.xml`, SHA256 `1f1b5137f17f4730ef64fc86a9b9c6ae96e4685bb32423b71292510fda293ece`; UUID `d72380ba-6b8e-4ad5-abaf-a15491471afc`, `SUCCEED/status4/state1101001` |
| Izquierdo | `diagnostics/native_arm_preparation_left_0ba73acf59757767.xml`, SHA256 `0ba73acf597577678b243adbe280844ca2d6b4b51ccfb34b620b308c9d916d9c`; UUID `d3c883ea-b790-4906-b930-5805ecff466b`, `SUCCEED/status4/state1101001` |

Ambos XML se crean en
`/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/`
del contenedor Motion redescubierto, en rutas antes ausentes. Los manifiestos
`native-right-final/manifest.json` y `native-left-final/manifest.json` conservan
XML, muestra canónica completa, referencia de retorno, hashes, orden articular
y contrato. Sus flags de construcción `PREPARED_NOT_INSTALLED_OR_EXECUTED`
no se reescriben; los recibos de staging/run acreditan los pasos posteriores.
No hay reintento ni HOME después de los dos goals. La observación visual positiva
corresponde a **estos** ensayos nativos; no se atribuye retrospectivamente al
ensayo pequeño derecho que el operador no había observado.

### Construir, preparar y comprobar la tarea nativa

[prepare_native_arm_preparation.py](../../scripts/box_handling/prepare_native_arm_preparation.py)
genera `task.xml` y `manifest.json` localmente. El builder verifica el XML fuente
exacto, estado HOME20D por nombre y extremos/velocidades medias necesarias frente
al URDF. Esas comprobaciones no certifican interpolador, picos de velocidad,
geometría de abrazaderas, escena, holgura o parada; no son un barrido de colisión.

```bash
python3 scripts/box_handling/prepare_native_arm_preparation.py \
  --state /ruta/privada/nueva/estado-canonico-actual.json \
  --urdf /ruta/privada/nueva/urdf-instalado-verificado.urdf \
  --arm right --output /ruta/privada/nueva/native-right
```

Para otro lado o sesión, medir otra vez; no reutilizar el manifiesto como permiso.
El runner
[run_native_arm_preparation_remote.py](../../scripts/box_handling/run_native_arm_preparation_remote.py)
se ejecuta en el host Motion. Necesita un directorio privado de soporte con la
**misma ruta y contenido visibles desde host y contenedor**. En esta unidad se
verificó `/tmp` compartido; no asumirlo después de recrear contenedores.

Receta de staging para una sesión nueva; APP y RUNTIME_XML se sustituyen por
el contenedor descubierto y `candidate.runtime_path` del manifiesto, respectivamente:

```bash
robot=walker@192.168.11.2
candidate=/ruta/privada/nueva/native-right
support=$(ssh -T "$robot" 'mktemp -d /tmp/cruzr-native-preparation.XXXXXXXX')
scp "$candidate/manifest.json" "$robot:$support/manifest-right.json"
scp "$candidate/task.xml" "$robot:$support/task-right.xml"
scp scripts/box_handling/run_native_arm_preparation_remote.py \
  scripts/box_handling/run_empty_arm_diagnostic_remote.py \
  scripts/box_handling/scenario1_action_client.py \
  scripts/box_handling/scenario1_request_ids.py "$robot:$support/"
ssh -T "$robot" 'docker ps --format "{{.Names}}"'
ssh -T "$robot" "docker exec APP test -d '$support'"
# Tras verificar directorio compartido, contrato y destino inexistente:
ssh -T "$robot" "docker exec APP bash -lc 'umask 077; mkdir -p /opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/diagnostics; set -C; cat \"$support/task-right.xml\" > RUNTIME_XML'"
ssh -T "$robot" "docker exec APP sha256sum RUNTIME_XML"
```

No sobrescribir un XML existente ni modificar el original para hacer coincidir
el contrato. El runner valida el XML completo, referencia actual≤0,003rad,
paros/cargador y salud/control exclusivo en dos rondas, con refresco de cuerpo
y seguridad después de los hashes. Verifica `libmeta_move.so` SHA256
`bfeab1c7a295b58cd96fddd20916fc3f7fe16bd8c8ad1e77720f48aad34ccc69`,
además del contrato SDK/URDF anterior y el XML fuente. Soporte nativo requerido:

```text
scenario1_action_client.py  196b6241de0d1e624b919ab062fc391e6e8ee8837e4a496cbcdad99a57b3b607
scenario1_request_ids.py    904adfb55e621fde1bd03d8e7fd96b61bf1866e5a0b94f92b36eb53999d4092d
```

`--bundle` y `--support-dir` deben apuntar al mismo directorio privado `/tmp`.
Comprobación por defecto, sin ejecutar tarea:

```bash
ssh -T "$robot" "python3 '$support/run_native_arm_preparation_remote.py' --bundle '$support/manifest-right.json' --support-dir '$support'" \
  > /ruta/privada/nueva/native-right-check.jsonl \
  2> /ruta/privada/nueva/native-right-check.stderr
```

Sólo tras PASS nuevo y autorización/condiciones físicas actuales se puede añadir
`--run` a esa orden, con archivos de salida nuevos y captura pasiva independiente.
Envía un único goal de manipulación, cliente nativo acotado a25s y proceso45s.
Exige mismo UUID aceptado y terminal `status4/SUCCEED/1101001`; no basta rc0.
Cancelación, timeout o resultado incierto terminan sin retry ni HOME. El retorno
de6s forma parte de la tarea normal; no es recuperación garantizada si se
interrumpe la ida. La captura sigue siendo pasiva y no sustituye la parada física.

### Estado de cierre nativo y verificación

Ambos goals correctos y confirmación visual del operador registrados en
`native-right-run.jsonl` y `native-left-run.jsonl`, junto con trazas/análisis.
`native-tests-summary.json` resume las muestras retenidas a hasta32Hz:

| Métrica | Derecho | Izquierdo |
| --- | ---: | ---: |
| Recorrido shoulder-yaw |109,324951° |109,308472° |
| Mayor error consigna/posición de los siete ejes |1,263546° |1,227138° |
| Máxima velocidad muestreada del brazo |0,964469rad/s |0,955044rad/s |
| Mensajes actuadores / JointState |1045 /1299 |1047 /1304 |
| Fault/ejes deshabilitados, errores de validación o paro activo observados |0 |0 |

Son picos retenidos, no límites garantizados ni errores máximos de cada ciclo
del servo. `final-postflight-checks.json` da `all_pass=true`: estado actual
consultado sano/en reposo, seguridad libre y controles ociosos. No se deduce
de ello una causa del incidente ni salud bajo carga.

`native-all-cleanup-receipt.json`, rc0, confirma retirada de ambos XML nuevos,
directorio `diagnostics` creado aquí y ya vacío, siete archivos de soporte y
su directorio compartido `/tmp/empty_arm_nativeprep_20261022T093744Z`.
`original-contract-after-cleanup.json` verifica13 archivos nativos/SDK/SPS con
sus hashes originales. No queda archivo nativo nuevo que reaplicar ni
autoarranque de estas pruebas. Las copias/manifiestos privados se conservan.
La limpieza no envía HOME ni repite retorno o trayectoria.

Verificación final local: **42 pruebas PASS en7,687s**, incluyendo los nuevos
builder/runner y las23 previas; recibos de pruebas en la evidencia. No se
atribuye la ejecución offline a movimiento ni a validación del agarre.

Para reproducir la verificación local:

```bash
python3 -B -m unittest scripts.box_handling.test_prepare_native_arm_preparation \
  scripts.box_handling.test_run_native_arm_preparation_remote \
  scripts.box_handling.test_prepare_empty_arm_diagnostic \
  scripts.box_handling.test_run_empty_arm_diagnostic_remote
```

La reversión retira únicamente los XML aditivos listados, el directorio
`diagnostics` si se creó aquí y queda vacío, y los archivos de soporte nuevos
del recibo; comprobar hashes antes de retirarlos y conservar copias externas.
No restaurar tareas/configuración completas, no recargar servicios ni enviar
HOME para limpiar. El intento completo de MetaClamp en vacío no tiene contrato
de objetivo determinado y continúa PENDIENTE; estos resultados no declaran
resuelta una avería ni autorizan un nuevo agarre automático.

### Por qué no se ejecutó la separación completa en vacío

En los XML/YAML revisados, la separación derecha nominal en t14 y la entrada
izquierda en t16 se programan por tiempo. No aparece allí una condición
**explícita de hueco lateral medido** antes de entrar; no se concluye que todo
el código C++ carezca de otros controles. El modo `VISION` de t8 y los
`SEPARATE_ABSOLUTE` de t14 derecho/t16 izquierdo dependen de la pose visual.
Dar sóloXYZ sin orientación, o cambiar el modo para evitar visión, no conserva
el mismo objetivo6D ni reproduce la trayectoria del ensayo fallido.

Las alternativas revisadas `clamp_box` con modo `ABSOLUTE` no equivalen a
`separate_box`. `GetBoxNoVision`/FK no se identificó como una API demostrada
para suministrar una pose6D independiente. Por tanto no se ejecutó el MetaClamp
completo en vacío, no se fabricó un éxito SPS y no se cambiaron fuerzas para
forzarlo. El diagnóstico termina en la preparación articular separada.
Fuentes locales: `native-separation-local-findings.json` y
`native-empty-grasp-test-options.json` en la evidencia.

Consulta concreta pendiente al proveedor, para una prueba posterior:

- ¿Existe una interfaz oficial para suministrar una pose virtual6D de caja a
  `separate_box`, conservando el mismo cálculo y trayectoria que con visión?
- ¿Qué marco, convención de orientación, unidades, offset de caja/herramienta
  y semántica deben usarse para `VISION` y `SEPARATE_ABSOLUTE`?
- ¿Hay un modo oficial de plan/dry-run o ensayo sin caja que evite búsqueda
  de contacto/fuerza sin sustituir silenciosamente la tarea por `clamp_box`?
- ¿Qué condiciones de hueco, contacto, fuerza y abortado conserva ese modo,
  y cómo se inspeccionan objetivos articulares/cartesianos antes de ejecutarlos?

Es una solicitud técnica, no un mensaje enviado ni una autorización para
activar esa prueba. Hace falta resolver contrato, recorrido y condiciones
actuales antes de proponer otro movimiento.

## Qué prueba el candidato

[prepare_empty_arm_diagnostic.py](../../scripts/box_handling/prepare_empty_arm_diagnostic.py)
construye localmente un `.motion`, sin ROS, SDK, conexión o ejecución. Desde
un estado canónico completo próximo a HOME, desplaza los siete ejes de un
solo brazo en la dirección de su vector nativo de preparación, escalado de
modo que **ningún eje recorra más de2°**. No reproduce la preparación completa,
la separación, `bodyback`, contacto, agarre, carga ni solver de MetaClamp.

- Cinco grupos SDK/20 ejes: cabeza2, brazo izquierdo7, derecho7, elevador3,
  cintura1. Ruedas y dedos quedan fuera del archivo.
- Los otros13 ejes mantienen exactamente la referencia medida. También se
  mandan al SDK: esto no es aislamiento físico del resto del cuerpo.
-22s a500Hz,11.001 muestras por grupo: reposo2s, rampa quíntica8s,
  sostener2s, retorno8s y reposo2s; final igual al inicio.
- El builder exige todos los nombres y posiciones/velocidades finitos, sin
  duplicados ni ceros inventados: cuerpo `|q|<0,02rad`, reposo `<0,002rad/s`.
  No acredita por sí mismo la frescura del archivo de entrada.
- URDF comprobado para posición/velocidad de18 ejes de brazos/torso. Este
  modelo omite cabeza; sus dos ejes se conservan fijos y se declaran sin
  cobertura URDF. No se inventan límites ni se toma otro modelo para cubrirlos.

El candidato derecho actual usa SHA256
`41c914b2ee5365a15b20a4376c07c2f59a79954336acd0c997b02c0c22fcb2b3`,
5.299.492bytes. Pico nominal por eje, en el orden del brazo:

```text
shoulder_pitch +0,005756845 rad   shoulder_roll −0,008845438 rad
shoulder_yaw   +0,034906585 rad   elbow_roll    −0,027468376 rad
elbow_yaw     +0,012738162 rad   wrist_pitch   +0,006615803 rad
wrist_roll    +0,002595149 rad
```

La velocidad máxima analítica es0,008181231rad/s y la aceleración máxima
0,003148957rad/s². Son valores del candidato, no seguimiento medido, límites
certificados, holgura de codo o distancia de parada. La causa del incidente
izquierdo22Oct continúa sin resolver; ni el ensayo previo+2° de yaw ni este
candidato califican el agarre con carga.

## Construcción local reproducible

Usar una captura **nueva por nombre**, su URDF instalado verificado y un
directorio de salida inexistente. Estos nombres conservan la receta histórica;
para otra sesión cambiar el destino y obtener entradas actuales:

```bash
python3 scripts/box_handling/prepare_empty_arm_diagnostic.py \
  --state ../Humanoide-vla-evidence/20261022T093744Z_EMPTY_ARM_CONTROL_DIAGNOSTIC/fresh-joints.json \
  --urdf ../Humanoide-vla-evidence/20261022T093744Z_EMPTY_ARM_CONTROL_DIAGNOSTIC/installed-cruzr_s2.urdf \
  --arm right --amplitude-deg 2 \
  --output /ruta/privada/nueva/right-candidate
python3 -B -m unittest scripts.box_handling.test_prepare_empty_arm_diagnostic
```

`review.json` conserva entrada/hash, orden por grupo, referencia, vector,
muestreo, límites revisados y limitaciones; permanece
`PREPARED_NOT_EXECUTED/physical_approval=false`. No editarlo para simular una
aprobación. La auditoría local inicial del builder registra10 pruebas correctas,
archivo/cronología/amplitud/retorno verificados y cero conexiones u órdenes.
La suite actual del builder y runner suma23 pruebas correctas:

```bash
python3 -B -m unittest scripts.box_handling.test_prepare_empty_arm_diagnostic \
  scripts.box_handling.test_run_empty_arm_diagnostic_remote
```

## Staging temporal y contrato del SDK

El archivo actual se escribió como **nuevo**, dentro del contenedor Motion,
en `/tmp/empty_arm_diag_20261022T093744Z_right.motion`; lectura posterior
coincide con el SHA anterior (`right-stage-result.json`). No se instala una
tarea, no se cambia el SDK/configuración y no se recarga ningún servicio.
La siguiente receta muestra cómo preparar otra copia en un directorio nuevo;
no repetirla para sobrescribir el archivo actual:

```bash
robot=walker@192.168.11.2
candidate=/ruta/privada/nueva/right-candidate/empty_arm_right.motion
remote_dir=$(ssh -T "$robot" 'mktemp -d /tmp/cruzr-empty-arm.XXXXXXXX')
scp "$candidate" "$robot:$remote_dir/candidate.motion"
# Descubrir exactamente un contenedor de manipulación antes de continuar:
ssh -T "$robot" 'docker ps --format "{{.Names}}"'
# Sustituir APP por ese nombre recién verificado; mkdir debe crear una ruta nueva:
ssh -T "$robot" "docker exec APP mkdir -m 700 '$remote_dir'"
ssh -T "$robot" "docker cp '$remote_dir/candidate.motion' 'APP:$remote_dir/candidate.motion'"
sha256sum "$candidate"
ssh -T "$robot" "docker exec APP sha256sum '$remote_dir/candidate.motion'"
```

Detenerse ante ambigüedad, archivo existente o hash distinto; no usar nombres
de contenedor de un arranque anterior. La copia en host y contenedor son sólo
staging; registrar ambas rutas para retirarlas al cerrar.

[run_empty_arm_diagnostic_remote.py](../../scripts/box_handling/run_empty_arm_diagnostic_remote.py)
se ejecuta en el host Motion. Descubre contenedores y comprueba hashes:

| Archivo instalado | SHA256 requerido |
| --- | --- |
| `manipulation_outline_sdk/.../player` | `8744a30ecce20c414dcf67b60d9aa7ac486bab752d5eee3de08a7336d65ddf0d` |
| `motion_sdk/joint_order/utars_joints.yaml` | `7f9d7975ebd27774e5248afa666a71ecaeb24bad30a234c9af2b81abc321f39c` |
| `manipulation_platforms/.../urdf/cruzr_s2.urdf` | `c01acb400366ec154a852e75853bc2b5cf4807d5bd217a89578b8f4cd8ae1760` |

Las rutas absolutas están en `CONTRACT` del runner versionado; se comparan
también con `sdk-contract-fresh.json`. Un binario diferente requiere revisar
el contrato, no sustituir el checksum para conseguir PASS.

## Comprobar primero, ejecutar sólo de forma explícita

Sin `--run`, el runner sólo consulta y valida: ambos paros/cargador, baterías
>20%,20 actuadores habilitados/sin error, reposo, consigna/posición≤0,01rad,
HOME canónico, SDK ocioso sin otros writers/clientes, locks libres, controladores
y archivo/contrato. Tras las consultas lentas vuelve a adquirir cuerpo y paros,
exige marcas de fuente articulares crecientes, recepción reciente y diferencia
inicial≤0,003rad. No es vigilancia continua durante la reproducción.

Ejemplo de **check** de una copia recién construida y cargada mediante el staging
anterior; conservar stdout/stderr y código. Los nombres históricos ya se han
retirado y no se reutilizan como comandos actuales:

```bash
motion_sha=$(sha256sum "$candidate" | cut -d ' ' -f 1)
ssh -T "$robot" \
  "python3 - --motion '$remote_dir/candidate.motion' --sha256 '$motion_sha' --arm right" \
  < scripts/box_handling/run_empty_arm_diagnostic_remote.py \
  > /ruta/privada/nueva/right-check.jsonl \
  2> /ruta/privada/nueva/right-check.stderr
```

`all_pass=false` o código78 bloquean el player. Sólo después de PASS nuevo,
autorización presencial aplicable, brazos/clamps vacíos, zona libre, ruedas
inmovilizadas, cargador fuera, paros liberados, otros mandos detenidos y persona
junto al paro, la misma orden puede añadir `--run`, con recibos nuevos.
El runner repite el preflight y ejecuta **una sola vez** el player nativo:

```text
rosa run manipulation_outline_sdk player -- --robot utars --input ARCHIVO.motion
```

No se añade `--loop`; no hay siguiente brazo automático, retry ni HOME posterior.
Exige rc0 **y** texto `Action finished with is_finished=true, bag has been played successfully`;
salida0 sola no basta. Timeout65s deja estado físico indeterminado y no reintenta.
Cancelar SSH o matar el cliente no demuestra parada del robot: actuar conforme
a la situación física y conservar evidencia antes de decidir una recuperación.

## Captura pasiva, cierre y reversión

[collect_empty_arm_trace_readonly.py](../../scripts/box_handling/collect_empty_arm_trace_readonly.py)
versionado registra estado canónico,
actuadores y ambos paros; conserva todas las recepciones de paros y emite cuerpo
hasta32Hz. No publica órdenes, no compara para cancelar y **no es un guard de
seguridad activo**.
[analyze_empty_arm_trace.py](../../scripts/box_handling/analyze_empty_arm_trace.py)
versionado permite revisar después
seguimiento, errores, corrientes y retorno, sin presentar unidades no calibradas
como fuerza física. El runner deja la parada al operador y protecciones nativas.

Receta pasiva, en un terminal aparte antes del ensayo autorizado; sustituir
APP por el contenedor descubierto y usar archivos nuevos. No iniciar movimiento
sólo por aparecer el mensaje de inicio del recolector:

```bash
ssh -T walker@192.168.11.2 \
  'docker exec -i APP bash -lc "source /opt/walker/setup.bash; export ROS2CLI_DISABLE_DAEMON=1; exec python3 - --seconds 48"' \
  < scripts/box_handling/collect_empty_arm_trace_readonly.py \
  > /ruta/privada/nueva/right-trace.jsonl \
  2> /ruta/privada/nueva/right-trace.stderr
python3 scripts/box_handling/analyze_empty_arm_trace.py \
  /ruta/privada/nueva/right-trace.jsonl \
  --output /ruta/privada/nueva/right-trace-analysis.json
```

Los colectores privados con nombre anterior se conservan como fuentes exactas
de la captura ya realizada; los enlaces versionados permiten retomar la receta.
No se declara una captura de seguridad completa/usable a partir del análisis.
Los resultados básicos y nativos, postflights y retirada de sus archivos están
registrados arriba. La observación visual del derecho2° no está acreditada;
el operador sí confirmó ambos recorridos nativos. La causa del fallo con caja
y la prueba del MetaClamp completo siguen PENDIENTES. No construir o
ejecutar el siguiente ensayo automáticamente por un rc0; revisar qué aporta cada etapa.

Al cerrar, verificar ausencia de clientes activos, reposo/errores/consignas y
estado físico; comprobar SHA antes de retirar **sólo** el archivo temporal nuevo
y, si corresponde, su directorio vacío y copia de host. Conservar el candidato,
review, runner exacto, capturas, recibos y hashes privados. La limpieza no envía
HOME ni restaura postura. Staging y limpieza se registran por separado como
cargado/retirado; no declarar limpieza o retorno físico antes de sus recibos.
No hay firmware, parámetros, SDK o servicio nuevo que revertir.

Backup documental: `before-empty-arm-guide/manifest.json` registra esta guía
como ausente antes de crearla. Las fuentes y la receta anteriores permiten
reconstruir el candidato sin depender del chat; una nueva ejecución exige
entradas y condiciones actuales. Restaurar documentos no recupera el robot.
`before-basic-results-documentation/` conserva los cuatro documentos anteriores
a este cierre básico; `basic-test-documentation-source-hashes.json` fija por
SHA256 los cuatro scripts de construcción/runner/captura/análisis utilizados
como fuentes versionadas de la receta.
`before-native-preparation-documentation/` conserva los cuatro documentos antes
del cierre nativo; recibos/manifest de cada lado conservan fuentes y hashes.
