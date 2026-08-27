# Cruzr S2 v0.2.0: teleoperación, captura de datos y evolución del VLA

> Versión documental 1.3 — 27 de agosto de 2026. Estado: guía técnica del
> proyecto basada en evidencias locales; los puntos marcados «Pendiente DSA»
> requieren confirmación del proveedor.

## 1. Propósito y alcance

Esta guía define cómo usar el Cruzr S2 real y un PICO 4 Ultra Enterprise para
recoger demostraciones reproducibles, convertirlas en un dataset auditable y
entrenar o continuar un checkpoint VLA. Integra cuatro fuentes:

- el estado observado del robot tras la actualización v0.2.0;
- el SOP de teleoperación y los instaladores suministrados;
- el paquete VLA GR00T N1.5 con `checkpoint-40000`;
- las pruebas shadow y las experiencias de manipulación realizadas en este
  robot.

No es una autorización para movimiento VLA autónomo. La activación física sigue
condicionada por los bloqueos de
[CRUZR_S2_VLA_SAFE_ENABLEMENT.md](../guides/CRUZR_S2_VLA_SAFE_ENABLEMENT.md).

La campaña prioritaria para caracterizar el checkpoint intacto, comparar las
ocho combinaciones funcionales de 14 a 20 ejes, validar los cuatro task IDs y
decidir entre continuar el checkpoint o partir de GR00T base está definida al
principio de [`../plan_de_trabajo.md`](../plan_de_trabajo.md). Sus gates son
obligatorios antes de incorporar VLA a la misión física de cajas.

Las secciones 0.17–0.21 de ese plan son además el runbook reproducible de la
campaña: definen la caja segura `B0_SAFE` de `0,603 × 0,397 × 0,217 m`, los
estados `SUPPORTED/HELD`, los comandos shadow existentes, las herramientas aún
pendientes y tarjetas `VLA-T00…T10` con PASS/FAIL/evidencia/recuperación. El
fixture inicial confirmado por el SDK es B0 sobre plataforma de **1 m de
altura**. Los niveles 0,55/1,15 pertenecen al árbol alternativo no-S2 y no se
adoptan como baseline. Ninguna tarjeta física queda autorizada al documentarlo.

El plan comienza ahora con un manual para el experimentador numerado
`E1.0…E8.2`. E1 confirma plataforma `z=1,000 ± 0,010 m`, B0 y los artefactos;
E2 ejecuta sólo smoke shadow OOD con el fixture fuera de la envolvente. El SDK
no proporciona separación horizontal. E4 debe derivar y congelar
`platform_in_base`, `D_BUMPER_PLATFORM` y el mapeo de alturas low/middle a
partir de la pose S2, cinemática, frames del dataset y proveedor antes de
cualquier canary o PICK/PLACE.

Los 12 frames inicio/medio/final inspeccionados de los episodios 0/1/90/91
muestran un tote rígido gris abierto con borde/asas negras y un objeto pequeño
visible en el interior. `B0_SAFE` vacía reduce riesgo físico, pero se etiqueta
OOD si su apariencia o contenido no coincide; la igualdad dimensional no basta.

### Convenciones de evidencia

- **Verificado**: observado en el robot o inspeccionado en los paquetes
  disponibles.
- **Suministrado**: descrito por el SOP o configuración del proveedor.
- **Recomendado**: criterio de ingeniería para este proyecto, pendiente de
  validación experimental.
- **Pendiente DSA**: requiere confirmación del proveedor antes de considerarlo
  soporte oficial.

## 2. Estado de referencia del sistema

### 2.1 Robot real

| Elemento | Estado de referencia | Evidencia |
|---|---|---|
| Plataforma | Cruzr S2 | Verificado |
| Software | imágenes `zs2_motion-v0.2.0` y `zs2_vision-v0.2.0` | Verificado |
| Efector actual | abrazaderas laterales pasivas | Verificado |
| `HW_TYPE` | `cruzr_s2_v1` | Verificado |
| Dispositivo de teleoperación | `TELE_DEVICE=pico` | Verificado |
| Transporte | `transmit=local` | Verificado |
| Motion | `192.168.11.2` | Verificado |
| Vision/web | `192.168.11.3` | Verificado |
| Checkpoint | GR00T N1.5, `checkpoint-40000` | Instalado y probado en shadow |
| Ejecución física VLA | deshabilitada | Verificado |

El SOP nombra específicamente la compilación
`utars-udoke-config-v0.2.0-dac-beta.2.tar.gz`. Las imágenes activas muestran
`v0.2.0`, pero ese nombre corto no prueba por sí solo que todos los componentes
correspondan exactamente a `dac-beta.2`. La presencia de `pico`, los servicios
y los topics demuestra compatibilidad funcional inicial, no equivalencia de
build. Esta equivalencia queda como **Pendiente DSA**.

### 2.2 Interfaces observables relevantes

Teleoperación PICO:

| Topic | Tipo |
|---|---|
| `/pico_vr/hand_data` | `sensor_msgs/msg/JointState` |
| `/pico_vr/joy_data` | `quest_msgs/msg/Joysticks` |
| `/pico_vr/pose_data` | `sensor_msgs/msg/JointState` |
| `/pico_vr/tele_data` | `sensor_msgs/msg/JointState` |
| `/mc/teleoperation/enable` | `std_msgs/msg/Bool` |
| `/mc/teleoperation/mode_status` | `sensor_msgs/msg/JointState` |
| `/teleop/enable` | `std_msgs/msg/Bool` |

Estado, observación y fuerza del robot:

| Topic | Tipo | Uso posible |
|---|---|---|
| `/sensor/camera/stereo/color/raw` | `shm_msgs/msg/Image2m` | RGB usado por el perfil VLA suministrado |
| `/mc/whole_joint_states` | `sensor_msgs/msg/JointState` | estado articular observado |
| `/mc/sdk/robot_state` | `mc_state_msgs/msg/RobotState` | interfaz prevista, pero sin muestras en pruebas previas |
| `/mc/ft_states/L_hand_ft` | `geometry_msgs/msg/WrenchStamped` | fuerza/par izquierdo para QC y seguridad |
| `/mc/ft_states/R_hand_ft` | `geometry_msgs/msg/WrenchStamped` | fuerza/par derecho para QC y seguridad |

El robot dispone además de cámaras RGB-D de chasis y cintura, estéreo,
fisheye, profundidad y nubes de puntos. Que existan no significa que el
checkpoint actual sepa utilizarlas: el perfil entregado consume una sola
imagen RGB. Añadir profundidad o más cámaras exige modificar dataset,
configuración y entrenamiento de forma coherente.

## 3. Qué hace actualmente el VLA suministrado

### 3.1 Entrada, salida y tareas

El checkpoint recibido utiliza:

- una observación RGB, redimensionada a `224 x 224` por el data config;
- una instrucción de lenguaje;
- 20 posiciones articulares como estado;
- chunks de 10 acciones, cada acción con 20 valores.

Orden exacto de estado y acción:

1. brazo izquierdo: 7 ejes;
2. brazo derecho: 7 ejes;
3. cabeza: 2 ejes;
4. elevador: 3 ejes;
5. cintura: 1 eje.

No contiene acción de chasis, dedos ni pinza eléctrica. Sus cuatro instrucciones
son recoger y depositar una caja grande en el nivel inferior o medio.

### 3.2 Dataset original inspeccionado

El dataset `utars_clamp_and_place_large_box_full_data_bio_lerobot_0319` es
LeRobot v2.1 y declara:

- 500 episodios;
- 105 207 frames;
- 500 vídeos;
- aproximadamente 1,9 GB de vídeo;
- 120 FPS declarados;
- imagen RGB `960 x 576`;
- 32 valores de estado almacenados: 20 articulaciones y 12 valores de
  fuerza/par;
- 20 valores de acción;
- task index, episodio, frame, timestamp e instrucción.

Distribución:

| Tarea | Episodios | Frames |
|---|---:|---:|
| recoger caja, nivel inferior | 150 | 34 302 |
| depositar caja, nivel inferior | 150 | 26 411 |
| recoger caja, nivel medio | 100 | 23 861 |
| depositar caja, nivel medio | 100 | 20 633 |

Hay que auditar los datos antes de reutilizarlos. Por ejemplo, existe un
episodio de sólo 9 frames y los metadatos de codec no son completamente
consistentes. Los 120 FPS declarados tampoco coinciden con la tasa RGB de unos
12,5 Hz observada en vivo: puede existir remuestreo o repetición de frames. No
se debe forzar ningún recorder a 120 FPS sin entender primero la exportación.

Aunque las fuerzas están almacenadas, `Utars_1RGBDataConfig` selecciona
únicamente las 20 articulaciones como entrada al modelo. En consecuencia, el
checkpoint actual **no está condicionado por fuerza**. Las fuerzas siguen
siendo valiosas para seguridad, detección de contacto y control de calidad.

### 3.3 Resultado shadow

El modelo se cargó y produjo chunks finitos `10 x 20`. Una prueba de tarea
generó dos chunks en aproximadamente diez segundos; la primera inferencia fue
más lenta que las siguientes. No hubo publicadores en
`/mc/sdk/robot_command`.

Desde `home`, ocho ejes de brazo excedieron el límite conservador y la
diferencia llegó a aproximadamente 1,35 rad. El validador rechazó el movimiento.
Por tanto, el modelo depende de una postura inicial de preparación que no se
debe sustituir por `home`.

## 4. VLA frente a programación tradicional

| Necesidad | Enfoque preferente |
|---|---|
| caja conocida, geometría y alturas controladas | detector `workbin` + secuencia determinista |
| pequeñas variaciones medibles de pose | detector + servo visual/AprilTag + trayectoria parametrizada |
| objetos, posiciones y escenas variables dentro de una misma familia | ajuste VLA con demostraciones variadas |
| requisito de repetibilidad, trazabilidad y validación industrial | programación tradicional siempre que sea suficiente |
| manipulación con dedos, acción distinta a 20D | nuevo perfil de datos y salida; el checkpoint actual no basta |

El detector `workbin` y las tareas BYD no son un VLA: localizan la caja y
ejecutan primitivas programadas, usando geometría y realimentación de
fuerza/contacto. Esto explica por qué el robot puede adaptarse a la posición de
una caja dentro de un rango sin aprendizaje generalista.

## 5. Matriz de compatibilidad

### 5.1 Efectores

| Efector | `HW_TYPE` | Teleoperación | Checkpoint actual |
|---|---|---|---|
| abrazaderas | `cruzr_s2_v1` | soportada | compatible por diseño |
| manos v3/v4 | `cruzr_s2_v1_sps` | soportadas por el stack, pendiente validar captura | incompatible con la salida 20D |
| pinza de dos dedos/cilindro | `cruzr_s2_v1_gripper` | descrita en SOP | incompatible sin agregar su acción |

No se deben mezclar episodios de diferentes efectores en el mismo perfil sin
registrar el efector y definir una representación de acción común. Cambiar
`HW_TYPE` requiere volver a desplegar/recrear los componentes de motion según
el SOP; no basta editar una variable dentro de un contenedor en ejecución.

### 5.2 Visores

| Visor | Estado de soporte comunicado |
|---|---|
| PICO 4 Ultra Enterprise | soportado |
| PICO 4 Ultra de consumo | no soportado oficialmente; adaptación propia |
| Meta Quest 3 | citado en el SOP |
| Oculus/Meta Quest 2 | no confirmado |

El proyecto debe utilizar el **PICO 4 Ultra Enterprise ya disponible** y no
asumir equivalencia de firmware o permisos con la versión de consumo.

## 6. Arquitectura de captura

```text
PICO 4 Ultra Enterprise
  └─ XRoboToolkit-PICO (poses, mandos y opcionalmente trackers)
       └─ USB / red compartida
            └─ PC de datos Ubuntu
                 ├─ XRoboToolkit PC Service
                 ├─ ubt-controller 5.3.0 (PICO, 90 Hz configurados)
                 ├─ ubt-remote-control 4.1.0
                 └─ centro de captura/exportación
                      ├─ observación RGB
                      ├─ estado articular
                      ├─ acción/objetivo teleoperado
                      ├─ fuerza/par y timestamps
                      └─ metadatos de tarea y episodio
                           └─ LeRobot v2.1 auditable
                                └─ entrenamiento GPU fuera del robot
                                     └─ checkpoint candidato
                                          └─ offline → shadow → físico limitado
```

El servicio XR incluye un ejemplo `RobotDataRecorder` que guarda datos XR
brutos (`head.txt`, `hand.txt`, `controller.txt`, `body.csv` y `motion.txt`) y
timestamps. Es útil para diagnóstico y archivo, pero no reemplaza la captura
sincronizada de imagen, estado y acción del robot ni produce por sí solo el
dataset LeRobot esperado por GR00T.

### 6.1 Arquitectura recomendada para cajas, waypoints y AprilTags

Para mover cajas diferentes con abrazaderas entre puestos, la arquitectura
preferente es **híbrida**:

```text
orquestador de misión
  ├─ NAV_PICK_PRE   -> LiDAR + mapa + waypoint
  ├─ ALIGN_PICK    -> workbin o AprilTag + movimiento fino del chasis
  ├─ PICK          -> VLA de manipulación 20D con abrazaderas
  ├─ RETREAT_PICK  -> trayectoria odométrica validada
  ├─ NAV_DROP_PRE  -> LiDAR + mapa + waypoint
  ├─ ALIGN_DROP    -> AprilTag + movimiento fino del chasis
  ├─ PLACE         -> VLA de manipulación 20D con abrazaderas
  └─ RETREAT_HOME  -> trayectoria y home deterministas
```

La navegación, los waypoints y el servo visual AprilTag no se introducen como
20 articulaciones falsas dentro del checkpoint actual. Se ejecutan con sus
controladores especializados y se registran como fases enlazadas de una misma
misión. Esto conserva la evitación de obstáculos y permite depurar por separado
localización, alineación y manipulación.

Sólo un proyecto posterior que quiera control end-to-end de la base debe añadir
velocidades/pose del chasis al espacio de acción y crear un nuevo perfil desde
GR00T N1.5. Ese cambio no es compatible con `checkpoint-40000` y exige una
capa de seguridad independiente.

### 6.2 Capas que deben grabarse

Una grabación completa se divide en tres productos sincronizados:

1. **dataset de aprendizaje**: imagen, estado y acción de los episodios PICK y
   PLACE;
2. **sidecar de misión**: navegación, waypoints, odometría, AprilTag, workbin,
   seguridad y cambios de fase;
3. **XR bruto**: pose y botones del PICO para auditoría de la demostración.

| Capa | Fuente verificada o prevista | Qué conservar | Uso |
|---|---|---|---|
| RGB del modelo | `/sensor/camera/stereo/color/raw` | frames, timestamps, resolución, codec y frames únicos | entrada VLA |
| estado articular | `/mc/whole_joint_states` | nombres, posiciones y timestamps; seleccionar orden 20D | entrada VLA |
| acción teleoperada | exportador oficial/cadena de teleoperación, pendiente confirmar | objetivo articular 20D realmente enviado, no el estado posterior | salida supervisada |
| fuerza/par | `/mc/ft_states/L_hand_ft`, `/mc/ft_states/R_hand_ft` | wrench completo y timestamps | QC, contacto y seguridad; no entrada del checkpoint actual |
| PICO | `/pico_vr/pose_data`, `/pico_vr/hand_data`, `/pico_vr/joy_data`, `/pico_vr/tele_data` | poses, mandos, botones, modo y timestamp | trazabilidad XR |
| teleoperación | `/mc/teleoperation/enable`, `/mc/teleoperation/mode_status`, `/teleop/enable` | enable/disable y cambios de modo | fronteras y diagnóstico |
| odometría | `/mc/odom` | pose y twist reales | movimiento local y retrocesos |
| localización | `/nav/robot_pose` | pose de mapa y, si existe, covarianza/calidad | posición global |
| comando fino de base | `/cmd_vel_navi` y salida efectiva `/mc/cmd_vel`, tras confirmar tipos | velocidad solicitada y aplicada | reproducir y auditar alineación |
| navegación | acción `/vnav/task/command` | comando, goal ID, waypoint, inicio, feedback disponible, resultado y status | sidecar de ruta |
| mapa | archivos del mapa activo | nombre, hash, waypoint ID, x, y, yaw y modo | reproducibilidad espacial |
| AprilTag | `/sensor/camera/stereo/april_tag/results` | ID, tamaño configurado, frame, pose, margen, hamming y estabilidad | alineación fina |
| detector de caja | acción `/cv/task/transport_action` | `box_size` solicitado, `object_name`, `box_pose`, resultado y status | localización de agarre |
| transformaciones | `/tf` y `/tf_static`, si están disponibles en el dominio de captura | transforms usados y frames | reconstruir relaciones geométricas |
| seguridad | `/emb/estop_key_state`, `/emb/servo_estop_key_state`, `/emb/chrg_input_status` | cambios y estado en cada frontera | rechazo/aborto |
| energía | `/emb/battery_state` | SOC de ambos packs al inicio/final y eventos | trazabilidad operativa |
| percepción de tránsito | perfil de costmap activo y sus hashes | fuentes activas/suprimidas, tiempos y restauración | explicar bloqueos por la propia carga |

El dato crítico que aún debe confirmar DSA es cuál es la salida oficial que
contiene la **acción teleoperada 20D** y cómo la sincroniza el centro de captura.
Guardar sólo `/mc/whole_joint_states` produciría observaciones, no necesariamente
los objetivos que el operador ordenó.

#### 6.2.1 Auditoría local del contrato 20D suministrado — 2026-08-27

Esta sección registra evidencia del dataset local, no una especificación
recibida del proveedor. Se inspeccionaron `meta/info.json`,
`Utars_1RGBDataConfig` y los episodios `000000`, `000088` y `000499` de
`utars_clamp_and_place_large_box_full_data_bio_lerobot_0319`.

- **VERIFICADO — esquema**: `observation.state` contiene 32 valores. Los
  primeros 20 son posiciones articulares y los 12 restantes son fuerza/par de
  ambas muñecas. `action` contiene las mismas 20 articulaciones, en este orden:
  `L_elbow_roll`, `L_elbow_yaw`, `L_shoulder_pitch`, `L_shoulder_roll`,
  `L_shoulder_yaw`, `L_wrist_pitch`, `L_wrist_roll`, los siete equivalentes
  derechos, `head_pitch`, `head_yaw`, `lifter_pitch_1`, `lifter_pitch_2`,
  `lifter_pitch_3` y `waist_yaw`, todos con sufijo `_joint` en el metadato.
- **VERIFICADO — horizonte**: `Utars_1RGBDataConfig` usa el estado del índice
  actual y forma cada objetivo con 10 filas de acción consecutivas
  (`action_indices = range(10)`); no hay un vector 200D almacenado por frame.
- **OBSERVADO — relación estado/acción**: al comparar `action[t]` con las
  primeras 20 posiciones de `observation.state[t]`, el error absoluto medio fue
  `9.8915e-5`, `9.0236e-5` y `1.08006e-4` rad en los tres episodios. El máximo
  observado fue `1.45221e-3` rad. Comparar la acción con el estado de un frame
  posterior elevó el error medio a `2.12879e-3`, `1.77495e-3` y
  `2.57668e-3` rad respectivamente. Por tanto, en estas muestras la acción está
  alineada con una trayectoria articular prácticamente simultánea; no aparece
  como un objetivo desplazado un frame completo hacia el futuro.
- **VERIFICADO — timeline exportado**: los timestamps del parquet avanzan
  exactamente `1/120 s`. Los MP4 examinados son H.264, `960x576`, 120 FPS, y
  tienen el mismo número de frames que sus parquets: 225, 251 y 157. Todos los
  frames decodificados de esas tres muestras fueron distintos por hash exacto.
- **PENDIENTE**: lo anterior no demuestra si `action` procede de la consigna
  teleoperada previa al actuador, de una lectura articular independiente o de
  una conversión/interpolación del exportador. Tampoco demuestra que el sensor
  físico entregue 120 imágenes nuevas por segundo ni identifica el reloj
  maestro. Esas semánticas y la sincronización oficial siguen pendientes de
  UBTECH/DSA.

**INFERENCIA de trabajo, no contrato oficial**: si el proveedor demora el
exportador, se puede construir un recolector pasivo compatible con la forma del
dataset grabando RGB, el estado 20D reordenado, fuerza/par, XR y fronteras de
episodio. Debe conservar en canales separados tanto la consigna teleoperada —si
se localiza— como la posición ejecutada. Sólo después de comparar un episodio
piloto extremo a extremo podrá decidirse si la trayectoria ejecutada se acepta
como `action`; hasta entonces no debe etiquetarse como comando oficial ni usarse
para una campaña grande.

`shm_msgs/msg/Image2m` usa la infraestructura de imagen compartida del robot.
Antes de confiar en `ros2 bag`, se debe demostrar con un episodio piloto que el
bag contiene píxeles decodificables y no sólo metadatos de memoria compartida.
El exportador del proveedor sigue siendo la fuente preferente para el dataset
entrenable; rosbag2 puede actuar como sidecar para topics estándar.

### 6.3 Reloj común y eventos de fase

Cada muestra o evento debe quedar asociado al menos a:

- `session_id`;
- `mission_id`;
- `phase_id` y número de secuencia;
- `episode_id` cuando la fase sea PICK o PLACE;
- timestamp de la fuente;
- timestamp monotónico del PC de captura;
- host y reloj de origen.

El orquestador debe emitir un evento al entrar y salir de cada fase, incluyendo
el objetivo, resultado y causa de fallo. No basta reconstruir las fases a
partir de la imagen. Se debe medir el offset entre los relojes de motion,
vision, PC y PICO al inicio y final, y registrar si hubo resincronización.

### 6.4 Catálogo de cajas y puestos

Cada caja necesita un `box_id` persistente y estos metadatos:

- dimensiones exteriores `L x W x H` y masa real;
- material, rigidez, color, textura y transparencia;
- estado: vacía/cargada y distribución aproximada del centro de masa;
- superficies de contacto permitidas y posibles asas/salientes;
- deformación o deslizamiento observado;
- detector/perfil usado y dimensiones configuradas;
- fuerza/par máximos observados, sin confundirlos con una fuerza comandada;
- fotografía/referencia visual y versión física.

Cada puesto de recogida o depósito necesita:

- `station_id`, altura, borde y superficie útil;
- mapa y fingerprint;
- waypoint de preaproximación con pose `x, y, yaw`;
- pose fina objetivo;
- AprilTag ID, familia, tamaño negro medido, frame y transformación relativa
  a la zona de apoyo;
- tolerancias de aceptación y envolvente libre;
- versión del layout. Si se mueve mesa, tag o waypoint, crear una versión
  nueva y no mezclarla silenciosamente con datos anteriores.

### 6.5 Estructura de datos de una misión

```text
session_id/
  session_manifest.yaml
  boxes/box_catalog.yaml
  stations/station_catalog.yaml
  missions/mission_log.csv
  missions/phase_log.csv
  episodes/pick_<episode_id>/...       # LeRobot o exportación fuente
  episodes/place_<episode_id>/...
  sidecar/navigation/...
  sidecar/apriltag/...
  sidecar/workbin/...
  sidecar/safety/...
  sidecar/xr_raw/...
  qc/...
  sha256sums.txt
```

Los logs de misión y fase enlazan el recorrido completo con los episodios VLA,
pero sólo PICK y PLACE se convierten en muestras 20D para continuar el
checkpoint actual.

## 7. Preparación del PC de datos y del PICO

### 7.1 PC de datos

Requisitos suministrados:

- Ubuntu 22.04 o posterior;
- Chrome actualizado;
- Ethernet directa al robot;
- IP estática del PC `192.168.11.250` para el enlace indicado en el SOP;
- ADB;
- una sola variante de XRoboToolkit PC Service;
- `ubt-controller` 5.3.0;
- `ubt-remote-control` 4.1.0.

Comprobaciones no destructivas recomendadas:

```bash
dpkg -l | grep -E 'ubt-controller|ubt-remote-control|xrobotoolkit'
systemctl status ubt-controller.service --no-pager
ip -br address
adb devices
```

El archivo de configuración suministrado está en:

```text
/opt/ubt/ubt_controller/config/config.json
```

Para operación local debe conservar coherencia entre:

```json
{
  "transmit": "local",
  "signal_server_url": "ws://192.168.11.3:4000",
  "push_rate": 90,
  "control_device": "pico",
  "enable_adb_reverse": 1
}
```

Después de un cambio autorizado:

```bash
sudo systemctl restart ubt-controller.service
sudo systemctl status ubt-controller.service --no-pager
```

No se deben copiar contraseñas, tokens o datos personales al manifiesto de
sesión.

### 7.2 PICO 4 Ultra Enterprise

1. Actualizar el sistema del visor.
2. Activar el modo desarrollador pulsando diez veces la versión de software,
   según el SOP.
3. Desactivar el apagado automático de pantalla y suspensión.
4. Instalar por USB:

   ```bash
   adb install -g XRoboToolkit-PICO-1.1.1.apk
   ```

5. Durante la teleoperación, mantener el Wi-Fi del PICO apagado para evitar
   interferencias, tal como indica el SOP.
6. Conectar USB y elegir `Shared network (connect USB first)` en
   XRoboToolkit.
7. Conectar al servicio del PC y comprobar estado verde `working`.
8. Elegir `Head + Controller` y `Send`.
9. Si se usan trackers, seleccionar el modo correcto y calibrarlos en **cada
   sesión**. No modificar sus variables durante una teleoperación activa.
10. Minimizar la aplicación para evitar pulsaciones accidentales.

Con trackers, el SOP contempla configuraciones de tres o cinco unidades. El
tracker de cintura se coloca detrás y no debe quedar cubierto. Registrar en el
manifiesto el número, firmware, colocación y resultado de calibración.

## 8. Controles PICO suministrados

| Control | Función |
|---|---|
| `Y` | iniciar/detener teleoperación |
| `X` | alternar modo de cuerpo completo en sitio y modo móvil |
| joystick izquierdo, en sitio | giro/inclinación de cintura |
| clic joystick izquierdo | activar/desactivar protección de fuerza del brazo izquierdo; por defecto activa |
| joystick derecho, en sitio | subir/bajar elevador |
| clic joystick derecho | activar/desactivar protección de fuerza del brazo derecho; por defecto activa |
| joystick izquierdo, móvil | avance/retroceso de base |
| joystick derecho, móvil | giro de base |
| `B` | iniciar/detener captura de un episodio |
| `A` | reset de tren superior, sólo en modo en sitio; no resetea elevador |
| trigger izquierdo/derecho | cerrar mano mientras se mantiene; abrir al soltar |
| grip izquierdo/derecho | ese brazo y cintura siguen al operador, sólo en modo en sitio |

Antes de terminar, volver siempre al modo de cuerpo completo en sitio. Si `Y`
o `B` no responde, el SOP menciona desconectar USB como recurso de emergencia,
pero sólo después de asegurar robot, carga y personas. No debe convertirse en
un procedimiento normal.

## 9. Diseño de una campaña de datos

### 9.1 Definir primero la política que se quiere aprender

Cada tarea debe tener:

- una instrucción breve, exacta y estable en inglés;
- estado inicial permitido;
- condición observable de éxito;
- condición de aborto;
- efector y carga;
- rango de alturas, offsets, yaw y tamaños;
- modalidades y acción con orden y unidades documentados.

Ejemplo para extender el checkpoint de abrazaderas:

```text
Task ID: 4
Instruction: Pick up the blue workbin from the table.
Initial state: robot at the marked pre-pick zone; arms in the official ready pose.
Success: workbin is stably suspended for 1 second without slip.
Abort: loss of detection, collision, excessive force, unstable clamp or E-stop.
```

No cambie sin necesidad entre sinónimos como `pick`, `grab` y `take`. La
consistencia lingüística reduce una fuente de variabilidad que no aporta
habilidad motora.

### 9.2 Matriz de variación

Para que el modelo se adapte, las demostraciones deben cubrir deliberadamente:

- offset lateral y distancia;
- yaw del objeto;
- altura de mesa/estante;
- tamaño, color, textura y masa dentro del rango autorizado;
- iluminación y fondo;
- presencia de distractores seguros;
- aproximación desde distintas poses válidas;
- operadores distintos, si se quiere reducir sesgo de estilo.

No varíe todo a la vez en el piloto. Empiece con una cuadrícula pequeña que
permita identificar qué condición provoca errores. La recomendación inicial es
10 episodios exitosos por celda de un piloto y, tras validar el pipeline,
50–100 demostraciones exitosas por variante de tarea. El dataset del proveedor
usa 100–150 episodios por tarea; esto sirve como referencia, no como garantía.

### 9.3 Separación train/validation/test

Dividir por **sesión, escena, objeto y condición**, no por frames aleatorios del
mismo vídeo. Si frames casi idénticos aparecen en train y test, el resultado
parecerá mejor sin medir generalización.

Una propuesta inicial:

- 70 % entrenamiento;
- 15 % validación;
- 15 % test bloqueado;
- al menos un objeto, una posición o una sesión completa no vistos en train.

### 9.4 Matriz optimizada para cajas con abrazaderas

La campaña debe variar primero aquello que afecta al contacto de las
abrazaderas. Una matriz inicial puede cruzar:

| Factor | Ejemplo de niveles | Motivo |
|---|---|---|
| anchura de agarre | estrecha, nominal, ancha dentro del alcance | cambia pose y contacto de brazos |
| altura | baja, media, alta alcanzable | cambia cinemática y visibilidad |
| offset lateral | izquierda, centro, derecha | prueba corrección visual |
| profundidad | cerca, nominal, lejos dentro del rango | prueba aproximación |
| yaw | negativo, cero, positivo | prueba orientación de contacto |
| rigidez | plástico rígido, cartón autorizado | cambia deformación y fuerza observada |
| masa | vacía, ligera, media autorizada | cambia fuerza y estabilidad |
| destino | dos o más alturas/estaciones | prueba generalización de depósito |

No usar un producto cartesiano completo desde el primer día. Elegir una caja
nominal y variar un factor por vez; después añadir combinaciones difíciles.
Mantener fuera de train al menos una caja física y una versión de layout para
test real.

El detector `workbin` actual está validado alrededor de una caja de
`0,60 x 0,40 x 0,22 m` y recibe esas dimensiones en
`/cv/task/transport_action`. No se debe asumir que detectará cajas muy
diferentes. Para ampliar la familia hay tres opciones:

1. calibrar/crear perfiles deterministas adicionales del detector;
2. usar AprilTags o geometría de puesto para la alineación y dejar que el VLA
   aprenda la variación de caja;
3. entrenar un nuevo detector de pose de caja y mantener el VLA sólo para la
   manipulación.

Para un entorno industrial estable, las opciones 1 o 3 suelen ser más
verificables. El VLA aporta más valor cuando la apariencia y pose del objeto
varían dentro de un rango que resulta costoso parametrizar.

## 10. Procedimiento de grabación de una sesión

Usar también el
[checklist imprimible](templates/TELEOP_SESSION_CHECKLIST.md).

### 10.1 Secuencia de una misión caja mesa 1 → mesa 2

El sidecar se inicia antes del primer movimiento y termina después de retirar
los brazos y volver a un estado seguro. Una misión genera dos episodios de
aprendizaje, PICK y PLACE:

1. **Crear `mission_id`** y seleccionar `box_id`, estación origen, estación
   destino, mapa y layout.
2. **Iniciar sidecar continuo**: eventos de fase, odometría, pose de mapa,
   navegación, AprilTag, workbin, seguridad, fuerza y XR.
3. **NAV_PICK_PRE**: enviar el waypoint de origen y guardar payload, goal ID,
   pose inicial/final, trayectoria/resultado y tiempos.
4. **ALIGN_PICK**: registrar pose de caja y/o tag antes de corregir, todos los
   `/cmd_vel_navi`, pose real y error residual. Con el flujo actual, `workbin`
   centra el agarre; un tag de mesa puede aportar referencia de estación.
5. **PICK**: activar `B` justo antes de la demostración de brazos, grabar RGB,
   estado 20D, acción 20D, fuerzas e instrucción. Cerrar `B` tras mantener la
   caja suspendida y estable. Enlazar `pick_episode_id` con la misión.
6. **RETREAT_PICK**: grabar el retroceso odométrico, pose antes/después y
   perfil de percepción de carga. No incluir este tramo en la acción 20D.
7. **NAV_DROP_PRE**: navegar directamente al waypoint de la mesa destino, por
   ejemplo `MESA2_PRE`, sin introducir `PASO1` si no es necesario. Registrar
   goal, ruta, pose y resultado.
8. **ALIGN_DROP**: iniciar el detector AprilTag con ID, tamaño y frame
   versionados. Guardar pose/calidad de cada muestra, error inicial, cada
   corrección de chasis y error final aceptado.
9. **PLACE**: activar `B`, teleoperar el depósito, registrar el contrato 20D y
   cerrar tras apoyo estable/liberación. Enlazar `place_episode_id`.
10. **RETREAT_HOME**: guardar apertura, retroceso, home, restauración del
    costmap/percepción y estado final.
11. **Cerrar misión**: resultado, fase fallida si existe, episodios aceptados,
    hashes e incidencias.

El botón `B` no debe permanecer activo durante toda la ruta si se va a
continuar `checkpoint-40000`: el loader interpretaría comandos de chasis y
esperas como si pertenecieran a la trayectoria articular de manipulación. El
sidecar sí permanece continuo y proporciona la visión completa de la misión.

Si se desea enseñar mediante PICO también la conducción manual, conservar ese
tramo como dataset separado `base_teleop`. Para convertirlo en política
aprendida se debe crear un nuevo DataConfig con acción de base, no agregarlo al
dataset 20D actual.

### Fase A: congelar configuración

1. Crear un ID de sesión y completar
   [`session_manifest.example.yaml`](templates/session_manifest.example.yaml).
2. Registrar versión del robot, hashes de configuración, `HW_TYPE`,
   `TELE_DEVICE`, `transmit`, efector, carga y operador.
3. Registrar mapa/fingerprint, layout, waypoints, estaciones, cajas, cámaras,
   resolución y topics.
4. Confirmar que no hay cambios de software pendientes durante la sesión.
5. Reservar espacio: el dataset suministrado equivale aproximadamente a
   7,8 GB por hora de vídeo. Mantener al menos tres veces la estimación por
   archivos temporales, XR bruto y copias de seguridad.

### Fase B: seguridad física

1. Cargador desconectado.
2. Efector fijado, cableado y correspondiente al `HW_TYPE`.
3. Teleoperador fuera del alcance del robot.
4. Observador independiente con paro físico preparado.
5. Zona completa y recorrido de base despejados.
6. Protecciones de fuerza de ambos brazos activas.
7. Carga y masa dentro del rango autorizado.
8. Regla de aborto acordada verbalmente.

### Fase C: comprobar flujos sin grabar

1. Arrancar el robot con el procedimiento validado para el hardware real.
2. Verificar estado, batería, paros y cargador.
3. Comprobar conexión Ethernet robot–PC.
4. Conectar PICO por USB, estado XR verde y Wi-Fi del visor apagado.
5. Recalibrar trackers si se usan.
6. Comprobar movimiento pequeño de cada elemento necesario sin objeto.
7. Volver a la postura inicial canónica.
8. Confirmar que imagen, estado, acción y fuerzas están llegando y que los
   timestamps avanzan.
9. Confirmar que `/mc/odom`, `/nav/robot_pose`, eventos de navegación,
   workbin/AprilTag y topics de seguridad llegan al sidecar.
10. Ejecutar un ciclo sin caja o por fases y comprobar que cada transición
    aparece en `phase_log.csv`.

### Fase D: grabar un episodio

1. Colocar el objeto según la celda de la matriz y registrar su pose real.
2. Llevar el robot a la postura inicial canónica **fuera de la grabación**.
3. Confirmar instrucción/task ID y número de episodio.
4. Esperar aproximadamente un segundo con la escena estable.
5. Pulsar `B` justo antes del primer movimiento significativo.
6. Ejecutar una demostración fluida, intencional y sin correcciones nerviosas.
7. Al alcanzar el éxito, mantener el resultado estable aproximadamente un
   segundo para que el final sea observable.
8. Pulsar `B` para cerrar el episodio.
9. Volver a postura segura y preparar el siguiente episodio fuera de captura.
10. Clasificar inmediatamente el episodio como aceptado, rechazado o pendiente
    en [`episode_log.csv`](templates/episode_log.csv).
11. Registrar `mission_id`, fase PICK/PLACE, `box_id`, estación y pose real.

Evitar pausas largas, conversaciones, reposicionamientos manuales o resets
dentro del episodio. No concatenar dos intentos bajo un mismo episodio.

### Fase E: tratar fallos y retakes

El cargador actual no dispone de un campo de éxito que el entrenamiento use de
forma explícita. Por ello:

- un intento fallido se conserva en un área de cuarentena para análisis;
- no se mezcla con las demostraciones de behavioral cloning salvo que se
  cambie conscientemente el método de entrenamiento;
- un retake obtiene un nuevo episode ID;
- nunca se sobrescribe el original sin dejar trazabilidad;
- anotar colisión, saturación, pérdida visual, acción incorrecta o error humano.

### Fase F: cierre

1. Finalizar teleoperación en modo de cuerpo completo en sitio.
2. Detener captura y verificar que no queda un episodio abierto.
3. Realizar apagado normal; el paro de emergencia no es el procedimiento
   ordinario de apagado.
4. Generar inventario y hashes SHA-256.
5. Copiar a almacenamiento secundario antes de borrar temporales.
6. Ejecutar QC automático y revisar una muestra visual el mismo día.
7. Firmar el manifiesto con incidencias y episodios aceptados/rechazados.
8. Comprobar que `mission_log.csv` referencia dos episodios válidos o explica
   por qué falta alguno.
9. Confirmar que el perfil temporal de percepción/costmap quedó restaurado.

## 11. Contrato mínimo del dataset

Para continuar el checkpoint actual sin cambiar el espacio de acción:

| Campo | Requisito |
|---|---|
| formato | LeRobot v2.1 o conversión demostrablemente equivalente |
| `video.rgb` | RGB legible y sincronizado; documentar codec real |
| estado | 20 articulaciones en el orden exacto del checkpoint |
| acción | 20 objetivos articulares, mismo orden y unidades |
| fuerza/par | 12 valores opcionales almacenados para QC; no consumidos por el perfil actual |
| timestamp | monotónico y relacionado con el reloj fuente |
| task | ID e instrucción estables |
| episodio | frontera inequívoca y un solo intento |
| metadatos | robot, versión, efector, escena, operador y resultado |

La acción de cada frame no son diez archivos independientes: el data loader
forma una ventana de 10 acciones consecutivas. La continuidad temporal es
obligatoria.

La variante `Utars_1RGB_From_TeleopDataConfig` encontrada no coincide con el
perfil 20D: usa dimensiones heredadas de 17/16 y omite elementos. No debe
usarse para este robot/checkpoint sin aclaración del proveedor o una corrección
versionada y probada.

### 11.1 Contrato del sidecar de misión

El sidecar no entra directamente en `Utars_1RGBDataConfig`, pero debe poder
reconstruir la misión:

| Campo | Requisito |
|---|---|
| misión | `mission_id`, sesión, caja, origen, destino, resultado y fase fallida |
| fases | secuencia, controlador, inicio, fin, resultado y episode ID asociado |
| mapa | nombre, fingerprint, versión de layout y pose inicial/final |
| waypoint | ID, `x`, `y`, `yaw`, modo y payload enviado |
| navegación | goal ID, status, duración, pose final y clasificación de fallo |
| base | `/mc/odom`, `/nav/robot_pose`, comando deseado y movimiento efectivo |
| AprilTag | ID, familia, tamaño, frame, pose/calidad por muestra y error pre/post |
| workbin | dimensiones solicitadas, nombre, pose, status y muestras usadas |
| seguridad | paros, cargador, bumpers/colisión disponibles e incidentes |
| percepción | perfil de costmap, fuentes activas/suprimidas y restauración |
| enlaces | `pick_episode_id`, `place_episode_id` y hashes de sus datos |

Las plantillas
[`mission_log.csv`](templates/mission_log.csv) y
[`phase_log.csv`](templates/phase_log.csv) definen una base mínima. Los
payloads completos y secuencias de alta frecuencia deben guardarse en archivos
sidecar, no dentro de una celda CSV.

## 12. Control de calidad antes de entrenar

### 12.1 Gates automáticos por episodio

- vídeo abre, decodifica y tiene duración coherente;
- no hay NaN, infinito ni arrays de dimensión incorrecta;
- nombres, orden y unidades articulares coinciden con el contrato;
- timestamps son monótonos y no tienen saltos inexplicados;
- estado, acción e imagen están alineados dentro de un frame de la línea
  temporal elegida;
- frames perdidos o repetidos se cuantifican;
- no hay saltos articulares imposibles ni velocidades fuera del límite;
- fuerzas no muestran impacto o saturación no anotados;
- task ID e instrucción existen en el catálogo;
- inicio y final cumplen la definición de la tarea;
- el episodio no tiene 0–9 frames por un error de captura.

Los umbrales finales deben derivarse de tasas reales y límites del robot. No
se deben copiar umbrales genéricos sin medir el pipeline.

### 12.2 Gates de misión híbrida

Antes de declarar una misión utilizable:

- todas las fases previstas existen y están ordenadas;
- NAV_PICK_PRE y NAV_DROP_PRE terminaron con status de éxito y pose coherente;
- mapa, fingerprint, waypoint y layout coinciden con el manifiesto;
- el error de localización no se perdió durante el recorrido;
- ALIGN_PICK/ALIGN_DROP guardan pose antes y después, y todas las correcciones;
- el AprilTag usado coincide en ID, tamaño y frame con la estación;
- workbin devuelve el objeto y una pose estable cuando esa detección es parte
  del flujo;
- PICK y PLACE enlazan episodios que superaron el QC 20D;
- la caja no se deslizó ni generó una fuerza anómala no anotada;
- ningún paro, bumper o evento de seguridad fue ignorado;
- el perfil de percepción de carga se restauró al terminar o abortar;
- un fallo de navegación no se etiqueta como fallo de VLA y viceversa.

Una misión fallida puede contener un episodio PICK válido. Se puede admitir
ese episodio en el dataset de manipulación si su frontera, resultado y datos son
correctos, manteniendo la misión global como fallida. La decisión debe quedar
explícita en ambos logs.

### 12.3 Revisión humana

Reproducir como mínimo:

- todos los episodios marcados con incidencia;
- el primero y último de cada sesión;
- una muestra aleatoria por tarea/condición;
- todos los outliers de duración, fuerza, velocidad o pérdida de frames.

Comprobar que la vista disponible para el modelo permite inferir el objeto y
el resultado. Si el teleoperador ve algo que la cámara del modelo no ve, la
demostración puede ser imposible de aprender.

### 12.4 Auditoría de frecuencia

Registrar por separado:

- tasa de envío XR (`push_rate`, actualmente 90);
- tasa real de imagen;
- tasa de estado y acción;
- FPS declarado del dataset;
- cantidad de frames RGB únicos.

No interpretar `120 FPS` como 120 imágenes nuevas por segundo hasta verificar
los archivos. Si se remuestrea, documentar algoritmo, reloj maestro y política
de interpolación/retención.

## 13. Elegir el punto de partida del VLA

### 13.1 Modelo, fine-tuning y checkpoint no son lo mismo

Un **checkpoint** es una instantánea de los pesos y la configuración de un
modelo en un momento del entrenamiento. Tanto un modelo continuado como uno
entrenado desde cero acabarán guardándose en checkpoints. Por tanto, la decisión
real no es «usar o no un checkpoint», sino elegir de qué pesos partir:

1. continuar el checkpoint de cajas entregado por DSA;
2. partir del modelo fundacional preentrenado GR00T N1.5, sin heredar el ajuste
   de cajas de DSA;
3. partir de pesos aleatorios y entrenar arquitectura, visión, lenguaje y
   acción desde cero.

La segunda opción es normalmente lo que se quiere decir en este proyecto por
«crear un VLA nuevo». No reutiliza `checkpoint-40000`, pero sí aprovecha el
conocimiento visual y lingüístico del modelo fundacional.

### 13.2 Para qué fue hecho el checkpoint actual

El `checkpoint-40000` suministrado está especializado en:

- Cruzr S2 con abrazaderas laterales pasivas;
- una sola cámara RGB;
- estado y acción articulares de 20 dimensiones;
- aproximaciones que parten de una postura VLA-ready compatible;
- recoger y depositar una caja grande;
- niveles inferior y medio de la escena de entrenamiento;
- cuatro instrucciones en inglés correspondientes a esas combinaciones.

No fue hecho para:

- controlar el chasis como parte de la salida aprendida;
- accionar manos, dedos o una pinza eléctrica;
- consumir fuerza/par como entrada, aunque esos datos existan en el dataset;
- utilizar profundidad, point cloud o varias cámaras;
- cualquier caja, estante o altura sin límite;
- tareas generales como botellas, herramientas, botones o ensamblaje.

Puede generalizar moderadamente dentro de la distribución cubierta por sus
demostraciones, pero no debe presentarse como un manipulador universal.

### 13.3 Comparación de las tres estrategias

| Estrategia | Punto de partida | Recomendada cuando | Coste y riesgo |
|---|---|---|---|
| continuar DSA | `checkpoint-40000` | misma cámara, abrazaderas, acción 20D y tareas de cajas relacionadas | menor cantidad de datos y convergencia rápida; riesgo de olvidar tareas antiguas |
| nuevo VLA de dominio | `nvidia/GR00T-N1.5-3B` | nuevo efector, nueva salida, modalidades o tareas alejadas del demo de cajas | más datos y validación; conserva conocimiento fundacional |
| desde cero real | pesos aleatorios | arquitectura incompatible, restricción legal/licencia o dominio sin un preentrenado aprovechable | dataset multimodal y cómputo enormes; mayor riesgo, casi nunca recomendado aquí |

### 13.4 A. Continuar `checkpoint-40000`

Es el camino preferente cuando se mantienen:

- abrazaderas;
- una cámara RGB;
- orden 20D de estado/acción;
- familia de tareas de cajas;
- cinemática y postura inicial compatibles.

Ejemplos adecuados:

- más tamaños o colores de cajas dentro de la capacidad mecánica;
- nuevas posiciones laterales o yaw;
- otras alturas alcanzables con las mismas abrazaderas;
- variaciones de iluminación y entorno industrial;
- transferencia de caja entre mesas una vez separada la navegación de la
  política de manipulación.

Procedimiento:

1. conservar una copia inmutable de `checkpoint-40000`;
2. grabar episodios nuevos con exactamente el mismo contrato 1 RGB/20D;
3. mezclar demostraciones antiguas y nuevas;
4. continuar el fine-tuning con tasa de aprendizaje conservadora;
5. evaluar tanto las tareas nuevas como las cuatro antiguas;
6. rechazar el candidato si mejora lo nuevo pero degrada lo anterior por debajo
   del criterio acordado.

Continuar únicamente con datos nuevos puede provocar olvido catastrófico.

### 13.5 B. Crear un VLA nuevo desde GR00T N1.5

Es la recomendación para una política que **no dependa del ajuste previo de
cajas**, pero aproveche el modelo fundacional. Debe elegirse al introducir:

- manos v4 con articulaciones de dedos;
- pinza accionada o un nuevo efector;
- otra dimensión u orden de acción;
- acciones de chasis dentro de la política;
- varias cámaras, profundidad u otras observaciones;
- fuerza/par como entrada real del modelo;
- tareas alejadas: botellas, herramientas, picking de piezas, pulsadores,
  clasificación o ensamblaje.

Procedimiento:

1. definir el nuevo contrato de observación, estado y acción antes de grabar;
2. crear un nuevo `DataConfig` con nombres, orden, unidades, normalización y
   horizonte explícitos;
3. instrumentar el recorder para exportar exactamente ese contrato;
4. grabar un piloto y validar extremo a extremo el loader;
5. ampliar un dataset equilibrado, con train/validation/test separados por
   sesión y condición;
6. inicializar desde `nvidia/GR00T-N1.5-3B`, no desde `checkpoint-40000`;
7. entrenar un nuevo directorio de experimento y no sobrescribir pesos DSA;
8. validar offline, en shadow y físicamente mediante la progresión de la
   sección 15.

Si el nuevo espacio incluye dedos, el dataset debe registrar su estado y su
comando; no es posible aprenderlos a partir de episodios 20D que nunca los
contuvieron.

### 13.6 C. Entrenar desde pesos aleatorios

Entrenar «desde cero real» implica no utilizar ni `checkpoint-40000` ni GR00T
N1.5 preentrenado. Habría que aprender representación visual, comprensión de
lenguaje y control a partir de los datos propios.

Sólo tiene sentido si:

- la arquitectura necesaria es incompatible con GR00T;
- una restricción de licencia o propiedad intelectual prohíbe pesos externos;
- se dispone de un corpus multimodal masivo y cómputo suficiente;
- existe un equipo capaz de entrenar y mantener un foundation model;
- las alternativas preentrenadas han sido evaluadas y fallan por razones
  demostrables.

No se recomienda para el Cruzr S2 actual. Las demostraciones que se pueden
recoger con un solo robot son apropiadas para fine-tuning, pero no suelen ser
suficientes para crear desde cero la capacidad visual-lingüística de un VLA.

### 13.7 Decisiones recomendadas para este proyecto

| Caso | Decisión recomendada |
|---|---|
| cajas nuevas con abrazaderas y 1 RGB | continuar `checkpoint-40000` mezclando datos antiguos |
| depositar cajas a más alturas con las mismas abrazaderas | continuar el checkpoint si la cinemática y la vista siguen siendo válidas |
| manos v4 y manipulación con dedos | nuevo DataConfig y nuevo fine-tuning desde GR00T N1.5 |
| botella con pinza de dos dedos | nuevo perfil desde GR00T N1.5; detector tradicional puede ser mejor si el entorno es fijo |
| fuerza como entrada aprendida | nuevo perfil/modelo desde GR00T N1.5 y dataset con fuerza sincronizada |
| navegación entre mesas | mantener navegación LiDAR tradicional; usar VLA sólo para la manipulación, salvo proyecto de investigación específico |
| investigación de una arquitectura completamente propia | desde cero sólo con presupuesto, datos y justificación extraordinarios |

## 14. Entrenamiento fuera del robot

El script suministrado parte de `nvidia/GR00T-N1.5-3B` y contempla ajuste de
proyector y difusión, LoRA opcional, varios datasets y checkpoints periódicos.
El checkpoint recibido alcanzó `global_step=40000`, aproximadamente 6,08
épocas, con batch 16. No registra un mejor checkpoint por evaluación;
`best_model_checkpoint` es nulo. La pérdida de entrenamiento no sustituye una
evaluación retenida.

Flujo recomendado:

1. Congelar dataset, hashes y data config.
2. Validar conversión con 2–5 episodios.
3. Ejecutar overfit controlado sobre un subconjunto para probar el pipeline.
4. Entrenar en una estación NVIDIA/CUDA, no en el robot de producción.
5. Guardar argumentos, commit, versiones, seed, logs y checkpoints.
6. Evaluar cada checkpoint sobre splits retenidos y simulación/offline.
7. Elegir por métrica de validación y pruebas de rollout, no por el número de
   step más alto.

El requisito exacto de GPU, VRAM y tiempo no está documentado en el material
inspeccionado; debe medirse o confirmarse con DSA antes de dimensionar compras.

## 15. Validación y despliegue de un candidato

Secuencia obligatoria:

1. **Offline**: formas, NaN, rangos, continuidad, latencia y replay de episodios.
2. **Dataset retenido**: éxito por tarea y por condición no vista.
3. **Shadow en robot**: inferencia con estado e imagen reales, sin publicador de
   comandos.
4. **Postura inicial oficial**: comparar primer chunk con la postura real.
5. **Ejecutor S2 seguro**: mapping explícito, límites, rate limit, timeout,
   deadman, estado fresco y paro.
6. **Movimiento sin objeto**: velocidad y amplitud reducidas.
7. **Objeto ligero/controlado**: zona cerrada y observador con paro.
8. **Variaciones progresivas**: sólo después de superar el nivel anterior.
9. **Rollback**: checkpoint anterior y servicios VLA detenidos disponibles.

Para el checkpoint suministrado sigue pendiente resolver la primitiva de
preparación `clamp_s2_joints_trajectory` y disponer de un ejecutor 20D seguro.
No activar el ejecutor SDK incompleto ni usar el perfil Walker de 30 DOF.

## 16. Capacidad esperable y límites

### Lo que sí habilita la plataforma

- teleoperación de brazos, cintura, elevador, cabeza y base según modo;
- captura de episodios mediante `B`;
- control de manos si el hardware/configuración correspondiente está activo;
- registro de XR, imagen, articulaciones y fuerza si el centro de captura los
  exporta correctamente;
- replay determinista de demostraciones;
- fine-tuning VLA para adaptación estadística a variaciones cubiertas por datos;
- inferencia GR00T N1.5 a bordo, ya demostrada en shadow.

### Lo que no debe prometerse todavía

- aprendizaje automático por una sola demostración;
- manipulación con dedos usando el checkpoint de abrazaderas;
- generalización a objetos o alturas ausentes del dataset;
- uso de fuerza por el modelo actual;
- navegación VLA del chasis con la salida 20D;
- que cualquier grabación XR sea directamente entrenable;
- movimiento físico del checkpoint antes de cerrar los gates de seguridad.

## 17. Piloto recomendado antes de una campaña completa

1. Mantener abrazaderas, `HW_TYPE=cruzr_s2_v1`, `pico` y `local`.
2. Usar una caja nominal, `MESA1_PRE`, `MESA2_PRE` y los tags versionados.
3. Ejecutar una misión sin caja y verificar todas las fases del sidecar.
4. Ejecutar una misión con caja sin entrenar: comprobar navegación directa,
   errores AprilTag pre/post y restauración del perfil de percepción.
5. Grabar 10 misiones exitosas. Cada una debe producir un PICK y un PLACE
   aceptados, además del sidecar continuo.
6. Conservar 2 misiones fallidas en cuarentena, etiquetando la fase causal.
7. Exportar y comprobar video, 20D estado, **20D acción**, fuerza, task,
   timestamps, goals de navegación, poses, workbin y AprilTag.
8. Reproducir visualmente los 20 episodios y reconstruir al menos dos misiones
   completas desde sus logs.
9. Convertir PICK/PLACE a LeRobot y ejecutar QC de episodio y misión.
10. Probar que `Utars_1RGBDataConfig` carga el lote sin usar los comandos de
    chasis como parte de la acción.
11. Hacer un overfit del subconjunto fuera del robot.
12. Ejecutar inferencia offline y luego shadow desde la pose ready correcta.
13. Sólo entonces ampliar cajas, alturas, layouts y número de episodios.

## 18. Preguntas abiertas para DSA

1. ¿El sistema instalado corresponde exactamente a
   `v0.2.0-dac-beta.2`, aunque las imágenes se llamen `v0.2.0`?
2. ¿Qué aplicación/servicio produce el dataset LeRobot y dónde lo exporta?
3. ¿Cuál es el reloj maestro y cómo se sincronizan 90 Hz XR, RGB y 120 FPS
   declarados?
4. ¿Qué topic/archivo contiene la acción teleoperada 20D previa a la
   respuesta mecánica, y cómo se relaciona con `/mc/whole_joint_states`?
5. ¿Qué significado exacto tiene cada campo 20D y en qué unidades?
6. ¿Cómo se marca oficialmente el éxito o rechazo de un episodio?
7. ¿Se puede capturar fuerza/par como entrada de entrenamiento soportada?
8. ¿Cuál es el data config oficial para manos v4 y cuál es su acción?
9. ¿Cuál es la postura oficial VLA ready y dónde se define
   `clamp_s2_joints_trajectory`?
10. ¿Qué ejecutor 20D y límites recomienda DSA para Cruzr S2?
11. ¿Qué GPU/VRAM y versión exacta de GR00T recomiendan para continuar
    `checkpoint-40000`?

## 19. Fuentes locales y trazabilidad

- Índice del paquete PICO/UTATS: [`utats/README.md`](../../utats/README.md).
- SOP suministrado: PDF local dentro de `utats/`.
- Paquete VLA local ignorado: `cruzrss2_vla_pack-002/`.
- Config de datos: `cruzrss2_vla_pack-002/data_config.py`.
- Entrenamiento: `cruzrss2_vla_pack-002/gr00t_finetune.py`.
- Dataset de referencia: `cruzrss2_vla_pack-002/data/utars_clamp_and_place_large_box_full_data_bio_lerobot_0319/`.
- Checkpoint: `cruzrss2_vla_pack-002/weight/checkpoint-40000/`.
- Scripts shadow: [`scripts/vla/`](../../scripts/vla/).

Los paquetes grandes no se versionan en Git. Toda campaña debe registrar sus
hashes y conservar una copia inmutable de dataset, data config, código y
checkpoint.
