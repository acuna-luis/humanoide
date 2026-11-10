# Paso de brazo derecho para SmolVLA mediante MetaMove — 10-11-2026

## Revisión del lanzador — 10-11-2026

El `--check` del lanzador llama ahora a la comprobación pasiva integrada PC→
Motion→guardia y cliente nativo de lectura. Con las fuentes actualizadas pasó
sin crear meta ni movimiento; el proceso y `/tmp` temporal no se observaron
tras terminar. Evidencia privada
`../Humanoide-vla-evidence/PICO_FULL_PASSIVE_CHECK/check-5377068e140c41adb7d978c292ef327a/`:
`stdout.jsonl` SHA256 `bd2777d7ecc6eed971d23b1f1f3d3c6b57f9b0fb9f4408eb8e2af80c1af8f92a`,
`sources-sha256.json` `fe925978f51d41ec10ae88dbfa549fdbc548ea3103f139c1b5d1655c21023a37`.

Se corrigieron dos fallos observados al revisar la rama futura: si se bloquea
el journal, el progreso del coordinador deja de renovar el lease; si la entrega
de código o payload al proceso hijo puede haber sido parcial, se conserva su
handle y resultado incierto, sin asumir que matarlo frene el robot. Una espera
de guardia de hasta26 s respeta el TTL independiente de preflight30 s. La
prueba local de disco bloqueado fue corregida para esperar el rechazo o
expiración efectiva del archivo, sin confundir una bandera en memoria con una
escritura ya terminada. Son pruebas con procesos simulados, no medidas de
frenado o certificados de latencia.

La copia vinculada `../Humanoide-vla-evidence/PICO_WRIST_REVIEW_BINDING_FINAL_20261110/`
tiene binding SHA256 `734032a629b8fb5a16cd22118e879652b3f2acc3ebe8ace778d941045ad043b1`;
una comparación local observó coincidencia de fuentes controladas y de los
bytes del manifiesto, URDF y SPS. El texto vinculado es una instantánea de
esta guía, no una aprobación ni una revisión integral del runtime. Una copia
anterior queda histórica tras los cambios. El lanzador exige esa comprobación
de integridad, pero `physical_release_gate` y la atestación técnica siguen
bloqueados: no se ha instalado ni enviado la tarea, ni validado físicamente la
trayectoria, mano v4, parada o aplicación de SmolVLA.

112 tests locales de las familias wrist, guardia, lease y comprobación pasan;
el código y el check pasivo no acreditan que la política alcance la pelota.

## Comprobación integrada pasiva — 10-11-2026

Se ejecutó una única comprobación PC→host Motion con desafío y latido,
guardia ROS2, lease en `/tmp` compartido y proceso de solo lectura en el
contenedor nativo. Este último contrastó las huellas de las clases ROSA
instaladas y validó el formato de la meta; un UUID sintético se comunicó
únicamente al guardia. Resultado `PASS_PC_HOST_GUARD_READONLY_NATIVE`, sin
crear ni enviar un goal. El guardia creó clientes ROS efímeros para descubrir
interfaces, pero no llamó a envío ni cancelación. Los procesos y el directorio
temporal se observaron retirados al finalizar.

Evidencia privada `../Humanoide-vla-evidence/PICO_FULL_PASSIVE_CHECK/check-daed9efa9c0641e0ba656fc2cd077e5a/`:
`stdout.jsonl` SHA256 `87de0fd70ad37e96ff0753546a85d94a75204a3bc4754fd5bed63b140313b8fd`,
`sources-sha256.json` `c0eef07d763eea02a45afdacf0bc7bd21acb6f23668b902fba18489f2cbb8a0a`.
Seis tests locales del comprobador pasan. Su receta es:

```bash
python3 -B scripts/vla/check_pico_wrist_full_passive.py --check \
  --manifest ../Humanoide-vla-evidence/PICO_WRIST_PREP_20261110T103237Z_078897/candidate/manifest.json \
  --urdf ../Humanoide-vla-evidence/PICO_WRIST_PREP_20261110T103237Z_078897/runtime.urdf \
  --transmissions ../Humanoide-vla-evidence/PICO_WRIST_PREP_20261110T103237Z_078897/transmissions.yaml
```

También se conectó una comprobación de integridad al lanzador: compara los
bytes de fuentes/bundles controlados y las tres entradas con una copia local
vinculada a la guía técnica. Binding privado
`../Humanoide-vla-evidence/PICO_WRIST_REVIEW_BINDING_INTEGRATED_20261110/`,
SHA256 `5c61f48fa838a96df3a4009fa21a0dcc4dfffe6fb29e581162fd0ec83f9b7ce0`.
Seis tests del binding y ocho del lanzador pasan; la comparación puntual
actual devolvió coincidencia. El texto vinculado es la guía existente, no una
aprobación ni una revisión independiente; no demuestra identidad del revisor,
runtime en memoria o firmware. La copia anterior es histórica y no coincide
con el lanzador modificado.

El cliente ROSA aún no ha ejecutado una meta de esta prueba y no se han probado
ni staging ni cancelación física. Siguen cerrados el gate físico y la
atestación de revisión técnica del lanzador; la geometría/montaje de la mano
v4 y la trayectoria real siguen sin cualificar. Los resultados pasivos no
habilitan el VLA, no garantizan frenado y no justifican modificar protecciones.

## Lanzador candidato — 10-11-2026

**Revisión posterior de fuentes:** el lanzador prepara la conservación de
bytes y hashes de ocho fuentes PC controladas, además de bundles y entradas.
Se corrigió la ruta del lector de E-stop y se comprueba que esas fuentes se
puedan leer. Esto no acredita los módulos ya cargados, Python, ROSA, SDK ni
todo el entorno. No se ha generado una aprobación externa ni se requiere
inferirla de un hash; la vinculación a la revisión técnica real sigue pendiente.

Se preparó un lanzador que combina la tarea nativa local de muñeca, el cliente
ROSA de cajas, un monitor de cuerpo/manos/paros, lease y un latido de desafío
PC–Motion. La instalación propuesta es aditiva y conserva recibo; una marca
global impide repetir automáticamente un intento incierto. El monitor verifica
los seis objetivos que se esperan quietos contra la postura y avisos SPS
actuales, además de la meta de muñeca. Una cancelación independiente del UUID
propio puede solicitarse ante fallo; si se recibe posteriormente estado activo,
se permite una segunda solicitud al mismo UUID sin reenviar el movimiento.
El estado posterior puede ser antiguo; ninguna respuesta certifica frenado.

Pasan 94 tests locales en total, con procesos o ROS simulados (incluidos
preparador y plan). La guardia final y su intercambio de UUID sintético/lease
pasaron una prueba pasiva en Motion: cero metas y movimientos. Evidencia
`../Humanoide-vla-evidence/ARM_NATIVE_BRIDGE_CHECK/check-fe7cb1c412de437b9ddbd783337b3623/`,
`stdout.log` SHA256 `d8a9590b0b81a302d9c481f2b1b20bc595c968e53688ad6f8490507a3391d243`,
`sources-sha256.json` `a952464f7130fd0eaf5e91acd77ee5075840321860618ab2032df16c2c6e5f9b`.
La prueba pasiva no ejecutó el lanzador físico, staging, cliente ROSA real ni
cancelación de una trayectoria.

**No está listo para mover:** `physical_release_gate` y la atestación de
bundles revisados siguen cerrados. La tarea no está instalada; falta verificar
el lanzador integrado, atestar el código efectivamente revisado, revisar la
geometría y el recorrido v4, y establecer un procedimiento frente a pérdida
de cliente/guardia y parada física. El canal de estado no demuestra exclusividad
distribuida y un latido no prueba que el operador vea alertas. No se ha hecho
staging ni se ha mandado ningún movimiento; no habilita SmolVLA físico.

## Puente de supervisión y cliente nativo — 10-11-2026

`arm_native_lease_bridge.py` prepara un lease de duración experimental 0,5 s,
renovado sólo con telemetría válida, y una asociación del UUID al guardia antes
de devolver la petición al cliente ROSA. La fuente archivada del SDK muestra que
`create_goal_request` termina antes de `call_async`; se conserva el cotejo de
huellas del cliente de cajas. El puente pide ACK del UUID exacto antes del
envío, y si falla el intercambio retira la referencia local y no envía.

El monitor funciona ahora como proceso pasivo continuo, acepta un UUID exacto
antes de la comunicación de una meta y continúa rechazando otras acciones.
Un comprobador ejecutó monitor y coordinador en Motion, usando el mismo reloj
monotónico: un UUID sintético obtuvo ACK y, al terminar el monitor, se observó
la revocación del lease. No se creó ni envió una meta, ni se instaló tarea.
Procesos y directorio temporal terminaron. Evidencia privada
`../Humanoide-vla-evidence/ARM_NATIVE_BRIDGE_CHECK/check-83127cadbf8e4e579c29d1931cebc92d/`:
`stdout.log` SHA256 `3df383804eb9f97ffd6ff66b8f9399996dcf741abf52ef11de21642f4960100f`,
`sources-sha256.json` `f3a9a8266fe32adfa5dd7b1d79e3885bd9b23efc1b4a0dfceaad550c5f2416eb`.
Pasan 14 tests de monitor, 17 de puente y cinco de comprobador con procesos o
ROS simulados. `physical_release_gate` sigue bloqueando el acceso físico.
La prueba no usa el cliente ROSA real ni comprueba un lease entre contenedores,
la trayectoria, cancelación o frenado de un objetivo físico.

Una comprobación separada creó un marcador privado temporal en `/tmp` de Motion:
los contenedores ROS2 y de manipulación lo leyeron correctamente, sus namespaces
de reloj monotónico coincidieron con el host y la lectura de cada reloj quedó
entre las dos lecturas locales que acotaban su consulta. El marcador se retiró.
Es una observación puntual de ruta y reloj, no una prueba del lease o cliente
ROSA entre contenedores. Receta: `python3 -B scripts/vla/check_motion_lease_shared.py --check`.
Evidencia `shared-tmp-clock.json`, SHA256
`4feec448cbe6faf4149bc1742a02ee5c6a111feaea9b19078064728e46148f38`, en
el mismo directorio de evidencia.

Receta de la comprobación pasiva, con la muestra archivada; una repetición debe
volver a verificar la postura actual y no convierte esa muestra en permiso:

```bash
python3 -B scripts/vla/check_arm_native_bridge_live.py --check \
  --manifest ../Humanoide-vla-evidence/PICO_WRIST_PREP_20261110T103237Z_078897/candidate/manifest.json \
  --urdf ../Humanoide-vla-evidence/PICO_WRIST_PREP_20261110T103237Z_078897/runtime.urdf \
  --transmissions ../Humanoide-vla-evidence/PICO_WRIST_PREP_20261110T103237Z_078897/transmissions.yaml
```

La comprobación mantiene guardia y coordinador en un contenedor; se observó
por separado ruta temporal y reloj compartidos con el contenedor nativo, pero
el lease todavía no se ha probado entre los dos. La
detección 0,5 s, ACK 0,4 s y expiración
son valores experimentales, no límites de parada. `GuardPipe.exchange` limita
la escritura al pipe y la espera del ACK, con prueba simulada de pipe lleno;
la interfaz genérica acepta otros callbacks y no puede imponerles ese plazo.
Si muere el cliente ROSA, un
lease que éste deja de leer no cancela por sí solo una consigna aceptada. La
cancelación y la respuesta del servidor no certifican frenado; continuar
requiere supervisión física y tratamiento de resultado incierto.

## Preparación nativa de muñeca — 10-11-2026

Con el patrón del ensayo de brazo de cajas se preparó una sola acción
`MetaMove` derecha: la referencia procede de una muestra 20D; el objetivo
varía únicamente `R_wrist_roll_joint` +0,01 rad en 4 s. No es una propuesta
SmolVLA ni se programó un retorno automático. El preparador rechaza extremos
fuera del URDF o las transmisiones SPS; la comprobación de velocidad es de
promedio necesario y no acredita picos, trayectoria o colisión.

La muestra tenía los dos codos dentro de sus límites nominales y márgenes
aproximados0,000622 y0,001293 rad. El valor0,002 rad del informe es una banda
diagnóstica, no un límite oficial ni una decisión automática de admisión. No
se ha establecido incertidumbre total, comportamiento del planificador o
distancia de parada. El monitor independiente alerta si un eje inmóvil se
aproxima a la mitad de su margen nominal; no garantiza que el servo se detenga.

Paquete privado en `../Humanoide-vla-evidence/PICO_WRIST_PREP_20261110T103237Z_078897/`:
`candidate/task.xml` SHA256 `70544f68d66f77ea7d4be163f6d517fba9a572127dcaa71e0c7dfe8f0e2abdca`,
`candidate/manifest.json` `adcffeafa262dbb8a07e736fb8fadd295885e0a9f9dd6525eaf73a8f759ad576`,
`stage-plan-v2.json` `07d690dacbc38010e7de51e2bfd99cf70526458e6135964eb1ca0303adc1eca1`.
El plan v2 usa `/tmp` y exige comprobar que host y contenedor comparten la
ruta; `stage-plan.json` anterior se conserva como evidencia obsoleta.
No se instaló ni ejecutó; el plan es solo local. La muestra no acredita las
condiciones físicas al intentar mover. Once tests del preparador/plan pasan.

Validación reproducible del paquete existente:

```bash
python3 -B scripts/vla/prepare_pico_wrist_native_probe.py --check \
  ../Humanoide-vla-evidence/PICO_WRIST_PREP_20261110T103237Z_078897/candidate/manifest.json \
  --urdf ../Humanoide-vla-evidence/PICO_WRIST_PREP_20261110T103237Z_078897/runtime.urdf \
  --transmissions ../Humanoide-vla-evidence/PICO_WRIST_PREP_20261110T103237Z_078897/transmissions.yaml
```

El cliente de cajas y el monitor de corredor aún no se han probado juntos con
una meta real; falta ese lanzador, así como revisar despeje real de mano v4,
trayectoria y parada. Ningún parámetro `--run` de
estas piezas habilita el movimiento. La preparación no cumple por sí sola los
gates del VLA físico.

## Referencia del ciclo de cajas — 10-11-2026

Por indicación del usuario se consultó el ciclo de cajas ya probado. El
[registro de mesa74](../guides/TRANSFERENCIA_CAJA_ENTRE_MESAS_CON_APRILTAG.md)
describe un ciclo físico completo de 323,879 s con depósito, HOME y confirmación
del operador. La prueba usaba abrazaderas y tareas concretas para cajas. El
catálogo atribuye el agarre operativo a percepción 6D y tareas nativas; el
proveedor afirma un VLA integrado en otro flujo, pero el XML examinado no
identifica checkpoint ni demuestra que fuera el ejecutado en ese ciclo.

Además, el [diagnóstico nativo de brazos](../box_handling/EMPTY_ARM_DIAGNOSTIC_20261022.md#preparación-nativa-completa-de-un-brazo)
probó físicamente el brazo derecho por separado mediante dos `MetaMove` y
retorno. Motion informó status 4, `SUCCEED`, código 1101001, y el operador
observó movimiento normal. En la traza conservada hay 1.299 muestras 20D;
el menor error máximo de los siete ejes respecto al objetivo fijo fue
0,002095673 rad en una muestra. Esto respalda el orden y seguimiento de ese
XML fijo en aquella postura con abrazaderas, no acredita objetivos dinámicos,
parada ni la geometría de manos v4. Las tareas temporales del ensayo se
retiraron: no ejecutar sus rutas históricas.

La comparación lee `candidate.joint_order` y `candidate.outbound_joint_target_rad`
del manifiesto `../Humanoide-vla-evidence/20261022T093744Z_EMPTY_ARM_CONTROL_DIAGNOSTIC/native-right-final/manifest.json`
(SHA256 `8d2c823193c8e3bd7e0d83ee83740142e841ee97a452f750a66227c2465d329c`),
busca cada muestra `/mc/whole_joint_states` por nombre en `native-right-trace.jsonl`
(SHA256 `37d2a12618eb512f8f115759b56ccd210542d023c42565953f38e015ee7f0c48`),
calcula el máximo error absoluto de los siete ejes por muestra y toma el mínimo.
El resultado es una observación puntual, no una cota de seguimiento futuro.

El cliente de cajas `scripts/box_handling/scenario1_action_client.py` usa la
misma acción `/mc/manipulation/action` con `task_name` y `yaml_args`; comprueba
aceptación, UUID, tiempo y cancelación, y declara que cancelar no certifica
parada física. Su criterio de éxito exige status 4, `SUCCEED` y código
1101001. El candidato de brazo ahora adopta ese criterio. Una prueba pasa su
orden hipotética por `validate_goal` del cliente de cajas y compara criterios
de resultado, además de las simulaciones anteriores: nueve tests de brazo y
37 del cliente de cajas pasan. La aceptación del formato por ese validador
no prueba que Motion acepte o ejecute la tarea dinámica.

No se ejecutó movimiento ni se modificó el cliente de cajas. El candidato
SmolVLA usa rclpy, no el cliente ROSA de cajas, por lo que sólo se reutilizó
el contrato, no se afirma una validación física de su transporte. Permanecen
abiertos geometría y trayectoria con mano v4, paso de argumentos al nodo,
parada efectiva y gates de VLA; la salida física sigue bloqueada.

## Candidato de ejecución y cancelación — 10-11-2026

Se amplió el runtime pasivo con una rama candidata: genera una meta desde
el estado medido para `right_arm` con una variación de 0,01 rad en muñeca,
envía como máximo una acción con UUID asignado, supervisa articulaciones y
solicita cancelación de ese UUID ante anomalías. La recepción desconocida,
fallo de enlace o respuesta de cancelación no demuestran parada; no reintentar
ni ordenar HOME automáticamente. El valor, duración y corredor son
experimentales, no límites certificados ni una trayectoria revisada.

La ejecución real permanece bloqueada al entrar en el runtime mediante
`physical_release_gate`, y el comprobador local rechaza `--run`. En tests se
sustituye esta función únicamente dentro del proceso simulado, sin ROS real:
una acción simulada llegó al objetivo y una activación de paro mientras se
esperaba aceptación provocó solicitud de cancelación del UUID exacto. Siete
tests locales pasan. **No se ejecutó el candidato en el robot.**

Siguen pendientes: comportamiento real de `yaml_args`, planificación y
movimiento con manos v4, cobertura geométrica y escena, y parada; tampoco
existe un lanzador físico habilitado para este candidato. Este ensayo no
conecta SmolVLA ni demuestra ejecución física de la política.

## Monitor pasivo de brazo — 10-11-2026

El operador confirmó manos v4 vacías, postura PICO con cabeza bajada, zona
libre, ruedas bloqueadas, cargador desconectado, ambos paros accesibles y
persona junto al paro, sin otro control activo. La batería observada en la
lectura puntual era 68,6/71,1 %. Esa confirmación y lectura no acreditan
condiciones posteriores.

Se adaptó el monitor de cabeza a esta referencia y se preparó un comprobador
pasivo. Éste valida controladores y ausencia de publicador SDK, hash de la
tarea dinámica, estado de articulaciones, salud de actuadores, manos, ambos
paros y comunicación de supervisión. Un único `--check` en Motion pasó y
terminó sin comandos. No quedó proceso de monitor observado. Cuatro tests
locales pasan; comprueban además el rechazo de movimientos excesivos en una
función de corredor, pero el check en vivo no mueve el eje ni prueba esa
función durante una trayectoria. El paso de muñeca de 0,01 rad y umbrales del
código son hipótesis experimentales, no límites certificados.

En la revisión inicial el código no incluía envío. La rama candidata posterior
incluye envío y cancelación sólo comprobados en simulación; `--run` y
`dry_run=False` están bloqueados. La recepción de
argumentos de `move_components_json`, planificador y parada física siguen
pendientes. La autorización del usuario existe, pero esta observación no
cumple los gates de ejecución del VLA ni valida geometría de manos o escena.
Receta pasiva: `python3 -B scripts/vla/check_arm_from_pico_supervised.py --check`.
No repetirla para suplantar la verificación necesaria antes de un movimiento.

## Tarea dinámica nativa encontrada — 10-11-2026

La consulta de catálogo de Motion devolvió `move_components_json` como
disponible para mano v4. Su XML instalado, SHA256
`bfcfc097dfefb3e81fcb2acc913d7db55545b3ea3b853b345b9ba1836c01b797`,
contiene una sola acción `MetaMove json_args="true"`. El `libmeta_move.so`
instalado, SHA256 `bfeab1c7a295b58cd96fddd20916fc3f7fe16bd8c8ad1e77720f48aad34ccc69`,
coincide con la copia analizada. En ésta, `GetRequestFromXmlNode` lee ese
booleano y llama a `UpdateRequestFromBlackboard`, que consulta `task_json_args`,
lee `component_names` como lista de nombres y `goals` como matriz de números;
también contiene lecturas de `mode` y `durations`. El archivo de descripción
de Cruzr leído en Motion declara un componente `right_arm`. El componente
configurado y la carga efectiva del proceso no quedan demostrados por el archivo.

El conversor genera ahora `candidate_dynamic_task`: nombre de tarea y una
hipótesis de argumentos para un solo brazo, con una fila de siete objetivos,
modo 0 y duración experimental. Es un **borrador**, no un ejecutor: faltan
demostrar el paso de `ArmTask.yaml_args` al blackboard en esta ruta, la
identidad/carga efectiva de la tarea, la semántica y trayectorias del
planificador, límites, control exclusivo y parada. No se envía la tarea, no se
instala ni recarga nada, y `--run` continúa bloqueado. El catálogo por sí solo
no prueba carga o efecto físico. La consulta del catálogo se reproduce con la
receta de la guía del puente, cambiando el filtro por `move_components_json`.
Se conservaron la sesión shadow previa y se probaron siete tests locales; no
se repitió entrenamiento, captura ni movimiento.

**Estado: conversión en vivo verificada sin control físico; ejecución PENDIENTE.** El
usuario solicitó acortar la prueba y reutilizar lo ya disponible. Las tareas
de fábrica y `scripts/custom_tasks/heart_v4_fingers.xml` muestran el formato
`MetaMove`, `type="arm"`, `location="right"` y `joint_angles` de siete valores.
Esto abre una vía para estudiar objetivos sucesivos con el controlador de
manipulación, sin asumir que haya que alimentar el SDK directo a 100 Hz.

[`prepare_ball_native_arm_step.py`](../../scripts/vla/prepare_ball_native_arm_step.py)
lee un resultado shadow JSONL completo mediante el auditor existente. Verifica
el checkpoint y la estructura, deriva el estado de los siete ejes de brazo a
partir de la predicción y su diferencia registrada, y limita cada diferencia
al valor solicitado por quien ejecuta el análisis. Emite por stdout un JSON con
los valores originales y limitados, el orden hipotético y un único XML candidato
`MetaMove type="arm" location="right"`. No instala archivos en Motion, no
crea clientes ROS, no envía órdenes y `--run` devuelve 2 sin conectar.

La opción `--stream` procesa el flujo real de `run_ball_live_shadow.py` por
stdin y produce un borrador por cada predicción, tras verificar checkpoint,
secuencia, sellos, estructura y cierre del flujo. Conserva el escalar de mano
sin interpretarlo como orden. No instala tareas ni publica a actuadores. Si el
flujo termina incompleto o contiene datos incompatibles, devuelve error; ya
puede haber impreso borradores anteriores, que tampoco habilitan movimiento.

Este es un **borrador para revisar, no una tarea habilitada**:

* El orden de siete ejes y el significado de las metas del modelo aún no se
  han cualificado para esa ruta `MetaMove` en esta unidad.
* El parámetro de salto y la duración son experimentales; no son límites de
  seguridad ni comprueban velocidad, aceleración, colisión o parada. Recortar
  una propuesta altera la política y puede impedir completar la tarea.
* Una grabación no acredita estado actual; el flujo en vivo tampoco acredita
  latencia física completa o sincronía. No contiene control de dedos ni
  detección de agarre o apoyo.
* La ejecución de `MetaMove` en esta postura, la aceptación del formato y su
  cancelación/retorno siguen sin verificarse; no instalar ni ejecutar este XML
  como resultado del diagnóstico.

Reproducción con el shadow ya existente, sin repetir captura o inferencia:

```bash
python3 -B scripts/vla/prepare_ball_native_arm_step.py \
  --check ../Humanoide-vla-evidence/20261109_SMOLVLA_LIVE_SHADOW/live-run.jsonl \
  --sample 0 --max-step-rad 0.05 --duration-s 4
python3 -B -m unittest discover -s scripts/vla -p 'test_prepare_ball_native_arm_step.py' -v
```

El ejemplo de 0,05 rad y 4 s es sólo para revisar el formato, no una elección
validada para mover el brazo. Con esa primera muestra se produjeron siete
diferencias candidatas limitadas a 0,05 rad; `physical_control_qualified=false`
y `physical_commands_sent=0`. Los cuatro tests locales pasan. La muestra es
del 09-11, anterior al movimiento de cabeza; no describe la escena actual.
Entrada SHA256 `5be819ea4a7941c3b136c40aa66494bbda42c5b6b116fbe431686cf2b85e8131`.

## Observaciones actuales — prueba integrada sin movimiento

Con el checkpoint ya entrenado y la cámara del robot se ejecutó un único flujo
de 5 s a 1 Hz. La inferencia en Ada entregó cuatro predicciones y la conversión
generó cuatro borradores de una acción derecha cada uno; no se enviaron órdenes.
La mayor diferencia original propuesta−estado fue 1,157168 rad; cada diferencia
del borrador se recortó al parámetro experimental 0,05 rad y la duración se
fijó experimentalmente en 4 s. Estos valores no son límites certificados. La
inferencia tardó 0,168–0,564 s; adaptador PC a predicción 0,271–0,687 s, sin
incluir transporte Vision→PC. No se guardaron imágenes ni se verificó que el
modelo identifique la pelota. El modelo vio las imágenes recibidas; eso no
demuestra un ciclo cerrado ni un agarre.

Se comprobaron localmente 7 tests. El colector de Vision y el contenedor
temporal de Ada habían terminado al concluir. Evidencia privada en
`../Humanoide-vla-evidence/20261110_NATIVE_LIVE_3ndpJ8/`: `shadow.jsonl`
SHA256 `ed178695efa640def802d854a9cc8738d33374191351f3563b4ff72333087fc1`,
`native-preview.jsonl` `a9eba4fe6a756ce9d91688570e709058993656cab32f59acc28ae6089c2514bd`,
`source.py` `37a057432ab181e399613451f2c8d38472254e88212e146dc8b8f965d3f7478f`
y `shadow-stderr.log` `f788aef7b645aba82d1ac2ed3bf547ed17d0a1dfd05ee5c0aea681a7fefd6e4b`.

La cadena ROS `R_shoulder_pitch→roll→yaw→elbow_roll→elbow_yaw→wrist_pitch→roll`
del URDF de Motion leído coincide con el orden de salida del modelo; el URDF
leído en texto normalizado a LF tenía SHA256
`a4bf032f2c8314c8d0f320357bbc7da8b75b846c1d44fb05b37ed0cb3bb0acfc`.
**Corrección 10-11:** el hash de los bytes reales en Motion es
`c01acb400366ec154a852e75853bc2b5cf4807d5bd217a89578b8f4cd8ae1760`;
contiene 721 finales CRLF. `execute()` normalizó los finales al devolver texto;
el hash anterior no identifica los bytes exactos en disco. Verificado mediante
`sha256sum` y normalización explícita dentro del contenedor.
Es una consistencia estática de la cadena cinemática, no demuestra que el
parser de `MetaMove` aplique ese mismo orden o que el archivo sea el usado por
el controlador en ejecución.

Para reproducir la conexión en observación, comprobar antes las fuentes fijadas
según [la receta shadow](../../scripts/vla/SMOLVLA_BALL_LIVE_SHADOW.md) y,
desde la raíz, usar sus argumentos de servidor existentes con `--seconds 5
--fps 1` y canalizar stdout a:

```bash
python3 -B scripts/vla/prepare_ball_native_arm_step.py --stream --max-step-rad 0.05 --duration-s 4
```

El paso limita cada articulación individual, cambia la salida del modelo y
no garantiza una trayectoria real, colisiones, agarre, parada o éxito físico.

Para pasar a un ciclo físico sigue faltando conectar los pasos al control del
robot, comprobar el orden y la parada de la tarea de brazo, y disponer
de una orden de mano con límites/confirmación de agarre y suelta. Ver la
[auditoría del SDK y mano](SMOLVLA_SDK_COMMAND_AGE_20261110.md).
