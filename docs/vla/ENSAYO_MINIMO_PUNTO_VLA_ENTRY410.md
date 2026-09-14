# Ensayo mínimo desde ENTRY410 hacia un punto VLA

**Último resultado, 2026-09-14, durante el relevo:** TRIAL_02 del operador
terminó success=false por `Controller handoff outcome uncertain; inspect
controller state, no retry`. Cero frames, solicitud de cambio emitida pero sin
acuse antes del timeout de 3 s. No se sabe qué controlador quedó activo:
consultarlo antes de reutilizar los comandos de esta receta. El plan corregido
no está probado físicamente. [Punto exacto de reanudación](RELEVO_VLA_20260914.md).


2026-09-14, Europe/Madrid. VLA-01. **Intento del operador interrumpido por falta
de seguimiento; corrección del controlador preparada, prueba física pendiente.** No confundir con los ensayos de acceso
HOME→READY→ENTRY que el operador ya completó y con los seis chunks shadow aceptados.

## Qué se ha preparado

Se conserva el primer punto original del chunk 2 de la sesión shadow task 0
registrada en ENTRY_OPERATOR_SUCCESS_20260914T213548+0200. Fue la propuesta
aceptada cuyo primer punto tenía menor desplazamiento máximo entre las seis.
Cambio completo máximo medido respecto al inicio: 0,0974421 rad (5,583°).
No se recortan articulaciones por separado ni se mezclan propuestas.

El recorrido al primer punto completo dejó una separación sin resolver entre
R_hand_link#0 y scene:tabletop_fit: cota observada 44,4 mm, inferior al margen
calculado con incertidumbre. Se conserva ese informe en plan/review.json;
no se declara colisión real ni se reduce su margen para hacerlo pasar.

El ensayo mínimo es **el primer 25 % de la transición hacia ese punto**, no el
chunk completo ni siquiera su primer punto completo: máximo 0,02436052 rad
(**1,396°**), ambos brazos; los otros seis ejes conservan la postura medida.
Transición quintica de 4 s, 401 consignas a 100 Hz; posición y velocidad iniciales
compatibles con reposo, velocidad final cero. El destino físico parcial se
etiqueta separado del punto del modelo. Es un replay de una propuesta grabada,
no política VLA en bucle ni inferencia fresca durante movimiento. No agarre,
no siguiente chunk, no HOME automático.

Límites propios del ensayo: cambio completo original ≤0,1 rad; prefijo ≤0,025 rad;
velocidad programada ≤0,05 rad/s, aceleración ≤0,1 rad/s². Son límites de ensayo
del proyecto, no certificación del fabricante. El cálculo parcial conserva la
banda geométrica original ±1° y margen base 2 mm: 1018 pares certificados por el
modelo y los mismos 54 avisos internos del informe de referencia, sin otros
avisos, sin pares de escena pendientes y sin timeout. Los avisos se conservan;
no se convierten en certificados ni se usa esto como aprobación general.

## Ejecución de una sola prueba

Desde la raíz del repositorio:

```bash
.venv/general-home/bin/python scripts/vla/run_entry410_vla_point.py \
  --check \
  --review ../Humanoide-vla-evidence/ENTRY410_ONE_POINT_PREPARATION/controller-fixed-plan/review.json
```

La comprobación anterior se ha ejecutado y pasó. Para el ensayo físico:

```bash
.venv/general-home/bin/python scripts/vla/run_entry410_vla_point.py \
  --run --physical-confirmed \
  --review ../Humanoide-vla-evidence/ENTRY410_ONE_POINT_PREPARATION/controller-fixed-plan/review.json \
  --evidence-dir ../Humanoide-vla-evidence/ENTRY410_ONE_POINT_TRIAL_01
```

Si el directorio de ejecución ya existe, se conserva intacto y se crea otro
con sufijo único; el script imprime su ruta en EVIDENCE_DIR. `--physical-confirmed` declara que
la escena no ha cambiado, las abrazaderas están vacías, ruedas bloqueadas,
ningún otro mando activo y una persona junto al E-stop. No crea una autorización
general ni evita el preflight o la lectura articular. No ejecutar este ensayo
si mesa/caja/base han cambiado respecto al escenario revisado. El comando envía
movimiento real; sólo se admite una ejecución desde el inicio revisado.

El monitor exige salud de los 20 actuadores, estado por nombre con recepción y
marca de origen de ≤0,1 s, ambos paros y cargador desconectados, chasis inmóvil,
control SDK exclusivo y coincidencia inicial ≤0,002 rad durante 1 s. Antes de
publicar observa repetición de paros; su timeout de comunicación sigue en 6 s.
Durante la transición comprueba error con la consigna ≤0,005 rad, velocidad
medida ≤0,05 rad/s, corredor conjunto, plazos de envío (sin recuperar retrasos)
y llegada inmóvil. La telemetría viene de /mc/whole_joint_states y
/mc/actuator_state. Publica 20 consignas en /mc/sdk/robot_command: los 14 brazos del prefijo y
los seis ejes restantes fijos en la postura inicial medida.

Ante error cesa la publicación, sin reintento, sin comando de recuperación ni
retorno automático. Destruir el publicador no equivale al E-stop ni demuestra
una distancia de parada; ante movimiento inesperado el operador acciona el
paro, y después sigue la recuperación UBTECH. La prueba todavía no demuestra
el comportamiento real del transporte SDK, seguimiento o parada de este tramo.

## Qué se verificó y qué se conserva

- Captura nueva de 98 muestras; preflight de lectura correcto: batería44/44,8%,
  ambos paros0, cargador0, sin publicadores SDK y VLA detenido. Son observaciones
  de esta preparación, no un permiso perpetuo; el ejecutor las vuelve a leer.
- Endpoint SDK descubierto: mc_task_msgs/msg/RobotCommand, cero publicadores,
  dos suscripciones BEST_EFFORT/KEEP_LAST5. La consulta adicional al servicio
  list_controllers falló por tipo no disponible en ese entorno ROS; no se
  afirma conocer su estado a partir de esa consulta.
- 13 tests locales pasan: selección sin clipping, rechazo de propuesta excesiva,
  ejes retenidos, no finitos, plazos y seguimiento, extremos de la transición y
  regresiones del corredor conjunto. El --check del plan real también pasa.
- Fuentes: prepare_entry410_vla_point.py, run_entry410_vla_point.py,
  runtime/entry410_vla_point_remote.py y test_entry410_vla_point.py.
  El backend SDK y monitor de corredor existentes se reutilizan sin modificarlos.
- Evidencia: ../Humanoide-vla-evidence/ENTRY410_ONE_POINT_PREPARATION/,
  con captura, plan completo no resuelto, plan parcial ejecutable, preflight,
  descubrimiento SDK, copias de fuentes y backups documentales.

## Reproducción, instalación y reversión

No necesita XML nuevo, instalación en robot, recarga ni reinicio. En `--run`
realiza un cambio temporal de controlador mediante el servicio instalado
`/mc/motion_sdk/switch_to_vla` (std_srvs/srv/Trigger); `--observe` no lo llama. El ejecutor
se envía en memoria por stdin al contenedor walker-ros.ros2-1 de Motion; el
modelo VLA permanece detenido. Dependencias PC: entorno .venv/general-home,
modelos splint y scripts geométricos existentes. Dependencias robot: ROS2,
mensajes mc_task_msgs, estado y SDK del firmware contrastado v0.2.0.

Para regenerar el plan tras cambiar fuentes, usar nueva captura y directorio:

```bash
.venv/general-home/bin/python scripts/vla/prepare_entry410_vla_point.py \
 --capture ../Humanoide-vla-evidence/ENTRY410_ONE_POINT_PREPARATION/capture/capture.json \
 --shadow-log ../Humanoide-vla-evidence/ENTRY_OPERATOR_SUCCESS_20260914T213548+0200/shadow-benchmark/results/shadow.jsonl \
 --reference ../Humanoide-vla-evidence/20260914_READY_COMMISSIONING_REVIEW/reference.json \
 --fraction 0.25 --output-dir DIRECTORIO_NUEVO
```

El ejemplo reproduce el cálculo archivado; antes de un ensayo nuevo hay que
capturar el estado vigente y conservar la identidad de escena. Los planes atan
fuentes/modelo/datos: no editar hashes manualmente. Tras firmware comprobar la
compatibilidad del SDK, mensajes, QoS, modelo y efectores antes de reaplicar.

Reversión: retirar los cuatro archivos nuevos del PC y restaurar selectivamente
las notas desde before/ si procede; no restaurar ni tocar scripts del usuario
force_ready.sh/force_entry.sh. No hay adaptación persistente del robot que
revertir. Esta preparación no genera un grant para el lanzador NO_BOX_READY
retirado. Sin commit ni push.

## Corrección de admisión y evidencias — 2026-09-14

El intento ENTRY410_ONE_POINT_TRIAL_01 ya existía con preflight correcto y
FAILED_NO_RETRY antes de crear el publicador, sin frames registrados. El segundo
intento del operador falló en mkdir, por reutilizar la ruta. Se preservan ambos
hallazgos; no se atribuye movimiento a ninguno de estos errores.

El ejecutor ahora crea un directorio hermano único si el solicitado ya existe,
sin borrar ni sobrescribir el anterior. --observe recorre la admisión en vivo
y retorna antes de construir el backend/publicador SDK. Los errores muestran
el topic o articulación responsable; ya no se oculta la causa tras un fallo
genérico de ENTRY estable.

La observación inicial identificó rechazos por velocidad instantánea de ruedas
y algunos ejes. Captura posterior de 98 muestras: cuerpo/brazos con velocidad0,
variación articular máxima observada0,000095874rad; ruedas con velocidad máxima
0,007330383rad/s y rango angular máximo0,001533981rad. Son lecturas compatibles
con pequeñas fluctuaciones de encoder; no se afirma medir movimiento de chasis
por la fotografía. El umbral anterior0,001rad/s rechazaba esas lecturas.

Admisión: velocidad articular máxima0,01rad/s y coincidencia de posición con el
inicio≤0,002rad durante1s. Ruedas: velocidad≤0,01rad/s **y** desplazamiento desde
su primera lectura≤0,002rad durante toda la sesión; no se ignoran las ruedas.
Las comprobaciones de fuente/recepción0,1s, paros, cargador, corredor, errores
de seguimiento, límites de envío y trayectoria física siguen iguales. No se
altera firmware ni sus protecciones. Quince tests locales pasan, incluidos
preservación de evidencia y rechazo de deriva/velocidad de ruedas excesivas.

Plan regenerado con la captura nueva y las fuentes actuales en
ENTRY410_ONE_POINT_PREPARATION/controller-fixed-plan/review.json. Mantiene chunk2,
prefijo25%, 4s, máximo1,396°, 1018 pares certificados por el modelo y54 avisos
internos históricos; no se editan hashes manualmente. Los planes anteriores
permanecen archivados y no son válidos con el ejecutor modificado.

**VERIFICADO en vivo tras la corrección:** --observe terminó con
ENTRY_POINT_ADMISSION_OBSERVED_NO_PUBLISHER, publishers_created=0. El preflight
canónico pasó y los 20 ejes finales registran velocidad0. No se ha ejecutado
el tramo físico ni se han cambiado los scripts force_ready/force_entry.
Evidencia, fuentes y backup: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/ENTRY_POINT_ADMISSION_FIX_20260914T215603`.
Reversión selectiva de los tres Python modificados y las notas desde before/;
los planes atados a la versión anterior dejan de ser válidos. No se modificó
la instalación del robot y no requiere reinstalación, recarga ni reinicio.

## Incidente de controlador y corrección — 2026-09-14

**OBSERVADO:** `ENTRY410_ONE_POINT_TRIAL_01-6l8y73xw` envió 134 frames,
0–133, durante 1,330000755 s. Las posiciones leídas permanecieron constantes;
el error final fue `Tracking error: R_shoulder_pitch_joint`, al separarse su
consigna más de 0,005 rad de la posición. La captura posterior volvió a medir
el mismo inicio. No demuestra una colisión ni un fallo del modelo VLA.

ROSA nativo sí permite consultar ListControllers: manipulación y chasis estaban
`running`; `sdk_controller` (22 ejes) y `vla_sdk_controller` (20) `initialized`.
La consulta ROS2 anterior fallaba por ausencia del tipo rosa_control_msgs en ese
contenedor. Tener suscripciones al topic SDK no demostraba que controlara ejes.
La omisión del cambio de controlador era un defecto de nuestro ejecutor.

Configuración contrastada, sin modificarla, en Motion,
`walker-motion.manipulation_robot_app-1`:

- `/opt/walker/config_mc_cruzr_s2_v1/share/config_mc_cruzr_s2_v1/config/switch_controllers.yaml`:
  inicia vla_sdk_controller y detiene manipulation_controller; chasis excluido.
- `.../config/controllers/vla_sdk_controller.yaml`: los 20 ejes del modelo.
- `/mc/motion_sdk/switch_to_vla`, std_srvs/srv/Trigger, anunciado; el ejecutable
  robot_app contiene los mensajes de cambio específico a vla_sdk_controller.
- `/mc/sdk/robot_state`, mc_state_msgs/msg/RobotState, contiene joint_states.

Corrección PC, sin instalar ficheros en robot:

1. Inventario nativo antes de continuar: manipulación y chasis activos, SDK
   inactivos, recursos VLA exactamente 20 ejes, sin otro controlador articular.
2. `--observe` sólo observa; comunica que el cambio está pendiente y no crea
   publicador ni llama servicios de cambio de modo.
3. `--run` espera admisión y llama una vez a switch_to_vla, manteniendo el
   monitor. Exige respuesta positiva, postura conservada y feedback SDK fresco
   durante 0,5 s antes de crear el publicador. Ausencia/error/timeout aborta.
4. Envía los 14 brazos más seis consignas constantes explícitas; no controla
   ruedas. Conserva el prefijo de 4 s y todos los límites anteriores.
5. Comprueba feedback SDK 20D durante el envío y la llegada. Error final imprime
   causa concreta y ruta del trace, conservando cada intento separado.

**Estado final previsto:** queda vla_sdk_controller activo, también ante fallo
posterior al cambio; no vuelve automáticamente a manipulación, no ejecuta HOME
ni repite consignas. Un timeout de cambio deja su resultado incierto y exige
leer el controlador antes de otra orden. No usar el script como recuperación.

**VERIFICADO:** 17 tests offline (inventario/conflictos, respuesta negativa,
feedback SDK ausente/obsoleto/incorrecto, seguimiento, ruedas, selección,
calendario y corredor). **PENDIENTE:** cambio efectivo de controlador y ensayo
corregido sobre hardware; el agente no los ejecutó en esta intervención.

Evidencia y respaldo previo completo de los siete archivos editados:
`../Humanoide-vla-evidence/ENTRY_POINT_SDK_NOT_FOLLOWING/`, con `before-fix/`,
`diagnosis.json`, consultas de configuración/controladores, captura posterior,
fuentes finales y SHA256SUMS. No se cambiaron firmware, XML ni contenedores.
Para revertir, recuperar los tres Python desde before-fix y regenerar un plan;
la versión anterior conserva el defecto y no debe utilizarse para movimiento.
Reproducción: preparar con capture-after/capture.json, el mismo shadow.jsonl y
reference.json de la receta anterior, `--fraction .25`, directorio nuevo.
No modificar manualmente hashes de review.json.

Verificación final de esta corrección: `--check` de controller-fixed-plan pasó;
`--observe` en vivo también pasó, con `controller_handoff_pending=true`,
`service_calls=0` y `publishers_created=0` (observe-fixed/result.json y trace).
La geometría recalculada conserva 1018 pares certificados y 54 avisos internos,
sin fallos nuevos. No se hizo el cambio de controlador ni se envió movimiento.
