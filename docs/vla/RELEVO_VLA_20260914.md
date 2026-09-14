# Relevo VLA — 14 de septiembre de 2026

Fecha: 2026-09-14, Europe/Madrid. Este documento resume el punto de reanudación;
AGENTS.md, PROJECT_SOURCE_OF_TRUTH.md y la guía VLA siguen siendo las fuentes
normativas. Los estados físicos aquí descritos son históricos: leer el resultado
más reciente antes de enviar una orden. No repetir por defecto HOME→READY→ENTRY.

## Objetivo y punto de reanudación

Objetivo completo: recoger una caja cargada desde una posición baja, transportarla,
volcar su contenido en otro lugar, llevar la caja vacía a una tercera posición,
depositarla y volver para repetir. Objetivo inmediato: ejecutar una propuesta VLA
desde ENTRY410 y progresar hasta un agarre real en la escena fija preparada.

**No hay todavía un agarre VLA demostrado.** Sí están probados físicamente
HOME→READY nuevo y READY→ENTRY410, y funciona la inferencia shadow desde ENTRY.
El siguiente paso preparado es un prefijo pequeño de una propuesta grabada:
25 % del puente hacia su primer punto, 4 segundos, máximo 1,396° articular.
No es el primer punto completo, un chunk completo ni el agarre.

**Último resultado: TRIAL_02 falló durante el cambio de controlador.**
El operador lo inició durante la redacción. result.json: success=false,
returncode=1. trace.jsonl: `controller_handoff_requested`, después
`Controller handoff outcome uncertain; inspect controller state, no retry`.
**Cero frames publicados por el ejecutor y ninguna confirmación del servicio.**
Esto no demuestra que el servicio no actuase: pudo completarse después del timeout.
**El controlador activo final es DESCONOCIDO; comprobarlo antes de otra orden.**
No hubo `controller_handoff_acknowledged` ni éxito de llegada. Esta intervención
sólo documentó el resultado local; no cambió controladores ni diagnosticó en vivo
el estado posterior. Este es el punto exacto de reanudación para mañana.

## Avances que no deben volver a tratarse como pendientes

| Hito | Evidencia y alcance |
| --- | --- |
| HOME→READY nuevo | Operador: cinco etapas `s2_bio_vla/ready410_h63_access_01…05_forward`, todas SUCCEED, state 1101001, status 4; recorrido comunicado como exitoso. |
| READY→ENTRY410 | Operador: cinco etapas `s2_bio_vla/ready410_h63_entry_01…05_forward`, todas SUCCEED; confirmó resultado correcto. |
| Postura ENTRY | Captura por nombre de 20 ejes, 98 muestras; error respecto a referencia hasta 0,1593°; velocidades cero en esa captura. |
| VLA task 0 shadow | Checkpoint-40000 produjo seis chunks, los seis aceptados por el filtro shadow de brazos. Sin publicación física del modelo. |
| Preparación del prefijo | Geometría recalculada: 1018 pares certificados por el modelo, 54 avisos internos históricos conservados, cero fallos nuevos/de escena. |
| Correcciones del ejecutor | Directorios únicos; diagnóstico de admisión; deriva de ruedas acotada; cambio explícito a controlador VLA SDK; errores finales muestran causa y trace. |
| Verificación del código vigente | 17 tests, --check y --observe en vivo pasaron. --observe no activó controlador ni creó publicador. |

Detalles de ensayos e IDs de objetivos:
[HOME→READY](ENSAYO_HOME_READY_NUEVO_20260914.md),
[READY→ENTRY y shadow](ENSAYO_READY_ENTRY410_20260914.md),
[ensayo mínimo y correcciones](ENSAYO_MINIMO_PUNTO_VLA_ENTRY410.md).
La aceptación shadow no certifica una trayectoria física; el ensayo exitoso de
acceso no demuestra todas las posturas ni la parada de cualquier movimiento.

## Última escena y estado conocidos antes de TRIAL_02

- Robot Cruzr S2 WAE001UBT60000669, v0.2.0, abrazaderas, HW_TYPE=cruzr_s2_v1.
- Escena de referencia usada por este plan: mesa de 725 mm, caja azul
  603 × 397 × 217 mm, vacía y apoyada; geometría registrada en reference.json.
  La mesa de 800 mm pertenece a una configuración anterior, no a este plan.
  La referencia conserva separación frontal registrada de 220 mm; no convertirla
  en una medición nueva ni aplicar el plan a otra colocación sin comprobarla.
- Última captura posterior al intento fallido: ENTRY, mismo inicio del plan,
  diferencia máxima 0 rad entre los vectores de inicio extraídos.
- Último preflight del intento fallido: baterías 41,5/42,3 %, paros 0/0,
  cargador desconectado. Estas cifras no son el estado de mañana.
- Último inventario nativo anterior a TRIAL_02: manipulation_controller y
  chassis_controller running; sdk_controller y vla_sdk_controller initialized.
- Modelo/inferencia y control VLA estaban detenidos tras shadow. El replay
  preparado no necesita arrancarlos; usa una propuesta ya guardada.
- Motion: 192.168.11.2; Vision: 192.168.11.3. Contenedores contrastados:
  walker-motion.manipulation_robot_app-1 y walker-ros.ros2-1.
- No se ha ordenado apagado, HOME ni cambio de controlador por el agente en el
  último diagnóstico. No afirmar que el robot quedó apagado o en HOME.

## Qué falló y qué se corrigió

1. TRIAL_01 original abortó antes de publicar por la admisión de estado. La
   repetición dio FileExistsError. El ejecutor conserva cada intento y crea un
   hermano con sufijo si la ruta existe.
2. La admisión rechazaba pequeñas variaciones de encoder de ruedas. Ahora
   limita simultáneamente velocidad a 0,01 rad/s y deriva a 0,002 rad; no ignora
   el chasis. El seguimiento durante el movimiento no se relajó.
3. TRIAL_01-6l8y73xw publicó 134 frames en 1,33 s con posiciones medidas
   constantes. Terminó por `Tracking error: R_shoulder_pitch_joint`.
   **Faltaba cambiar de manipulation_controller a vla_sdk_controller**: fue
   una omisión del ejecutor. Suscriptores SDK presentes no implicaban control activo.
4. El ejecutor corregido lee inventario con ROSA nativo (ROS2 carece del tipo
   rosa_control_msgs en su contenedor). Sólo --run llama una vez a
   `/mc/motion_sdk/switch_to_vla` (std_srvs/srv/Trigger), exige respuesta positiva,
   postura conservada y feedback SDK 20D fresco antes de crear el publicador.
   Conserva chasis y envía 14 ejes de brazos más seis consignas fijas explícitas.
5. Si el cambio se realiza, **SDK queda activo**, incluso si falla después;
   no hay cambio automático de vuelta, HOME ni reintento. El intento corregido
   TRIAL_02 abortó por timeout de 3 s del cambio; sin frames ni acuse. Comprobar
   servicio/controlador/logs antes de atribuirlo a un timeout insuficiente o repetir.

La configuración instalada switch_controllers.yaml y vla_sdk_controller.yaml
confirma el cambio de los 20 ejes superiores sin detener chassis_controller.
No se reinstaló firmware, XML ni contenedor para esta corrección. El servicio
no debe confundirse con arrancar el modelo VLA ni con ordenar una postura.

## Consulta inicial para resolver el último fallo

Dentro de una shell de Motion, esta consulta es de lectura; no cambia de modo:

```bash
docker exec walker-motion.manipulation_robot_app-1 bash -lc '
source /opt/walker/setup.bash
export ROS2CLI_DISABLE_DAEMON=1
timeout 7 rosa service call /mc/controller_manager/list_controllers rosa_control_msgs/srv/ListControllers "{}"
'
```

Usar contenedor redescubierto si hubo actualización/reinicio. Si VLA SDK aparece
running, no repetir el cambio ni forzar manipulación para hacer pasar el preflight.
Si sigue initialized, consultar los logs para saber por qué el servicio no dio
respuesta. En ambos casos, medir postura y velocidades. El ejecutor actual sólo
admite partir de manipulación running con SDK initialized; no es un recuperador
de una transición interrumpida. Continuar el desarrollo a partir de este hecho.

## Archivos y plan vigentes

Ejecutor PC: `scripts/vla/run_entry410_vla_point.py`.
Preparador: `scripts/vla/prepare_entry410_vla_point.py`.
Runtime enviado por stdin: `scripts/vla/runtime/entry410_vla_point_remote.py`.
Tests: `scripts/vla/test_entry410_vla_point.py` y `test_entry410_corridor.py`.

Plan vigente, relativo a la raíz del repositorio:
`../Humanoide-vla-evidence/ENTRY410_ONE_POINT_PREPARATION/controller-fixed-plan/review.json`.
Los planes executable-plan y admission-fixed-plan son anteriores; no utilizarlos
con el ejecutor nuevo. El plan vincula 184 fuentes por SHA-256, todas presentes
al redactar el relevo. Cambiar código invalida sus hashes: regenerar con el
preparador, nunca parchear hashes para que pase. Conservar evidencias fuera de Git.

Comprobación local, sin robot:

```bash
.venv/general-home/bin/python scripts/vla/run_entry410_vla_point.py \
  --check \
  --review ../Humanoide-vla-evidence/ENTRY410_ONE_POINT_PREPARATION/controller-fixed-plan/review.json
```

Comprobación en vivo sin cambiar controlador ni publicar:

```bash
.venv/general-home/bin/python scripts/vla/run_entry410_vla_point.py \
  --observe \
  --review ../Humanoide-vla-evidence/ENTRY410_ONE_POINT_PREPARATION/controller-fixed-plan/review.json \
  --evidence-dir ../Humanoide-vla-evidence/ENTRY410_OBSERVATION_RESUME
```

El comando físico está en [la receta vigente](ENSAYO_MINIMO_PUNTO_VLA_ENTRY410.md).
No ejecutarlo automáticamente al leer este relevo: primero resolver TRIAL_02 y
comprobar postura/controlador actuales. Si ya avanzó, el inicio revisado deja de
ser válido. --physical-confirmed no es una confirmación permanente del entorno.

## Secuencia mínima para mañana

1. Leer AGENTS.md, fuente global, este relevo y guía VLA; git status. Mantener
   los cambios del usuario. Revisar TRIAL_02 y cualquier intento más reciente,
   result.json, trace.jsonl y el último status/error; comprobar si sigue ejecutándose.
2. Si hay éxito `ONE_POINT_PREFIX_SUCCEEDED_AND_SETTLED`, registrar mediciones
   y observación del operador. No repetir desde ENTRY ni afirmar agarre.
   Si hay fallo, distinguir antes/después del cambio de controlador y frames
   emitidos; diagnosticar esa causa antes de otra orden. No volver a HOME a ciegas.
3. Recuperar estado actual en lectura: postura 20D y velocidades, salud,
   controlador activo, paros/cargador/batería, otros mandos y escena. Tras un
   reinicio no reutilizar el estado de ayer; redescubrir contenedores/endpoints.
4. Si TRIAL_02 no llegó a ensayarse y conserva el inicio/escena, usar el ejecutor
   corregido para el prefijo supervisado. No repetir cálculos geométricos si las
   fuentes/escena siguen iguales y --check pasa. Si algo cambió, regenerar.
5. Tras demostrar seguimiento SDK del prefijo, preparar la continuación desde
   la postura real hacia el primer punto completo, resolver su margen con mesa,
   y después los siguientes puntos. Todavía no existe un bucle físico VLA de
   agarre cualificado para esta escena. No encadenar chunks sólo porque shadow acepta.
6. Completar agarre, transporte, vaciado y depósito como etapas separadas con
   evidencias. El proveedor dice que el vaciado no viene incluido: desarrollarlo;
   no volver a preguntar si existe ni dar por entrenada esa operación.

## Pendientes concretos y tiempos

- Resolver el timeout del cambio a SDK de TRIAL_02: comprobar controlador
  activo, respuesta tardía y logs del servicio; no ampliar el timeout por
  suposición ni reintentar un cambio cuyo efecto aún es desconocido.
- Ejecución del prefijo corregido: TRIAL_02 emitió cero frames y no lo probó.
- Seguimiento y comportamiento real al interrumpir SDK; cesar publicación no
  equivale a E-stop ni mide una distancia de parada.
- Primer punto completo: quedó un par mano derecha/mesa sin resolver, cota
  44,4 mm frente a margen calculado 82,7 mm. Esto no se resolvió con el prefijo.
  Los 54 avisos internos CAD conservados no deben convertirse en colisiones
  reales confirmadas ni en certificados generales.
- Ejecución física de siguientes propuestas, agarre y estabilización con caja;
  después integración del transporte, vaciado propio y depósito de caja vacía.
- Optimización pendiente de tiempos de READY/ENTRY; no cambiar duraciones sin
  distinguir la versión probada físicamente de una versión acelerada.

Tiempos observados/preparados: READY 122 s nominales; ENTRY 74 s nominales.
En shadow: primera inferencia 1,598 s, caliente mediana 0,436 s, iteración caliente
0,479 s; arranque exterior 79,394 s incluyó contenedores/importaciones (no es
latencia de cada inferencia). Propuestas separadas 5 s por el benchmark.
Prefijo físico programado: 4 s, más preflight/admisión. No atribuir el tiempo de
cálculos geométricos offline, arranque o posturas lentas a la inferencia VLA.

## Evidencias y conservación del trabajo

Todo bajo `../Humanoide-vla-evidence/`:

- READY_ACCESS_OPERATOR_SUCCESS_20260914T212712+0200: acceso probado.
- ENTRY_OPERATOR_SUCCESS_20260914T213548+0200: ENTRY, captura y shadow-benchmark.
- ENTRY410_ONE_POINT_PREPARATION: planes anteriores y controller-fixed-plan.
- ENTRY410_ONE_POINT_TRIAL_01, ENTRY410_ONE_POINT_TRIAL_01-6l8y73xw: fallos preservados.
- ENTRY410_ONE_POINT_TRIAL_02: fallo del cambio de controlador, cero frames;
  resultado del servicio incierto. Prioridad de diagnóstico al retomar.
- ENTRY_POINT_SDK_NOT_FOLLOWING: diagnóstico, capture-after, observe-fixed,
  before-fix/after-fix, fuentes y SHA256SUMS; reversión en la receta del ensayo.

Rama main, un commit por delante de origin/main al inicio del relevo; muchos
archivos modificados/no seguidos. **No se ha hecho commit ni push de este relevo.**
Los cuatro Python del ensayo y numerosos documentos aún están sin seguimiento:
un checkout limpio no reproduce el estado actual. Preservar el directorio de
trabajo y la carpeta hermana de evidencias. No ejecutar git clean/reset/stash
indiscriminadamente. No sobrescribir force_ready.sh/force_entry.sh del operador.
No modificar el SDK original del proveedor ni versionar sus paquetes/checkpoints.

La política de cambios persistentes está en SYSTEM_CUSTOMIZATIONS.md, ficha
VLA-01. Para firmware, seguir la guía de reaplicación; no copiar configuraciones
antiguas completas sobre una nueva instalación. Este relevo no autoriza un reinicio.

Copia externa de este relevo: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/HANDOFF_20260914T221428+0200`. Conserva estado Git, parche documental,
versiones anteriores/finales, copia de TRIAL_02 y los 184 archivos vinculados al
plan (4,5 MB) por hash, con mapa a sus rutas originales. Las mallas del robot y
el checkpoint siguen en sus ubicaciones existentes; esta copia no sustituye
el respaldo completo previo a firmware. SHA256SUMS permite comprobar la copia.
