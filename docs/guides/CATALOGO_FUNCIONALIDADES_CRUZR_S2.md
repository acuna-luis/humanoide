# Catálogo operativo de funcionalidades del Cruzr S2

Fecha de verificación: 25 de agosto de 2026<br>
Unidad: Cruzr S2, `HW_TYPE=cruzr_s2_v1`<br>
Motion: `utars-integration:zs2_motion-v0.2.0`

Este documento enumera las funcionalidades que están disponibles actualmente en
esta unidad, con un ejemplo inmediato de uso. Se basa en los contenedores,
acciones, servicios y tópicos observados en el robot y en las pruebas físicas ya
realizadas.

No es un catálogo comercial de capacidades posibles. Una interfaz declarada en
un mensaje ROS 2 no se considera una función operativa hasta confirmar también
el servidor, su configuración y un resultado real.

## 1. Convenciones y acceso

Los ejemplos se clasifican así:

- **LECTURA:** no ordena movimientos.
- **CAMBIO DE ESTADO:** activa o desactiva un proceso, pero no debería mover el robot.
- **MOVIMIENTO:** puede mover base, cabeza, cintura, elevador o brazos.

Para ejecutar los scripts locales:

```bash
cd /home/lacuna/proyectos/Robots/Humanoide
```

Acceso al PC `vision` por el hotspot del robot:

```bash
ssh walker@192.168.42.2
```

Con Ethernet también se puede acceder directamente a:

```bash
ssh walker@192.168.11.3    # vision
ssh walker@192.168.11.2    # motion
```

Shell ROS 2 de diagnóstico en `vision`:

```bash
docker exec -it walker-ros.ros2-1 bash
source /opt/ros/humble/setup.bash
```

Shell ROSA de navegación en `vision`:

```bash
docker exec -it walker-nav.nav_taskmanager-1 bash
source /opt/walker/setup.bash
```

Shell ROSA de manipulación en `motion`:

```bash
docker exec -it walker-motion.manipulation_robot_app-1 bash
source /opt/walker/setup.bash
```

Para inventariar las interfaces activas sin ordenar movimientos:

```bash
rosa action list
ros2 service list -t
ros2 topic list -t
```

En v0.2.0 se desactiva el daemon mediante la variable de entorno, porque esta
versión del CLI no acepta `--no-daemon` de forma consistente:

```bash
export ROS2CLI_DISABLE_DAEMON=1
ros2 topic list -t
ros2 topic info -v /emb/battery_state
ros2 topic echo --once /emb/battery_state
```

## 2. Resumen de lo utilizable ahora

| Función | Estado actual | ¿Mueve el robot? |
|---|---|---:|
| Estado de baterías, cargador y paros | Probada | No |
| Cámaras RGB/RGBD, profundidad y estéreo | Activas | No |
| Nube de puntos estéreo | Activa | No |
| Lidar delantero y trasero | Activos | No |
| Detector especializado de contenedor `workbin` | Probado | No |
| Estimación de pose 6D de la caja | Probada | No |
| Perfiles 6D alternativos para cajas y bandejas | Configuraciones y modelos presentes; no activos | No |
| Detector AprilTag | Servidor activo; prueba física pendiente | No |
| Profundidad de una ROI estéreo | Servidor activo; prueba física pendiente | No |
| ASR, reconocimiento de voz | Probado en inglés | No |
| TTS, síntesis de voz | Probada en inglés | No |
| Mapas, localización y waypoints | Probados | Sí |
| Navegación con evitación de obstáculos | Probada | Sí |
| Movimientos predefinidos de brazos sin manos | Uno probado; otro instalado | Sí |
| Agarre, elevación y depósito de la caja azul | Probados | Sí |
| Transporte corto de una caja con la base | Probado por partes/en desarrollo | Sí |
| Ruta interna `test_route_01` | Navegación probada; ciclo cargado en validación | Sí |
| Recuperación automática a `home` | Implementada y usada | Sí |

## 3. Diagnóstico de alimentación y seguridad

### 3.1 Baterías

**LECTURA** — dentro de `walker-ros.ros2-1`:

```bash
timeout 10 ros2 topic echo --once /emb/battery_state
```

El campo `batsoc` es el porcentaje de carga de cada pack. Deben revisarse ambos;
no se debe usar la media para ocultar una diferencia importante entre packs.

Lectura compacta:

```bash
timeout 10 ros2 topic echo --once /emb/battery_state |
  grep -E 'charge_status|voltage:|current:|temperature:|batsoc:|sn:'
```

### 3.2 Cargador y paros

**LECTURA**:

```bash
timeout 10 ros2 topic echo --once /emb/chrg_input_status
timeout 10 ros2 topic echo --once /emb/estop_key_state
timeout 10 ros2 topic echo --once /emb/servo_estop_key_state
```

Los scripts de movimiento bloquean la ejecución si detectan cargador conectado o
un paro activo. La ausencia de fallo ROS no sustituye al paro físico preparado.

## 4. Cámaras, profundidad y nube de puntos

Están activos los controladores de cámara de chasis, cintura, estéreo, RGB y
fisheye. Las fuentes más relevantes son:

- cámara RGBD frontal del chasis;
- cámara RGBD frontal de la cintura;
- cámara estéreo de la cabeza;
- profundidad estéreo y nube de puntos;
- cámaras fisheye usadas por navegación/localización.

### 4.1 Comprobar que una imagen RGB llega

**LECTURA** — dentro de `walker-ros.ros2-1`:

```bash
timeout 8 ros2 topic hz /sensor/camera/stereo/color/raw
```

`timeout` terminará el comando automáticamente; el código 124 sólo significa que
agotó esos ocho segundos. Debe mostrarse una frecuencia mayor que cero.

Para localizar los nombres exactos de las demás cámaras de esta versión:

```bash
ros2 topic list -t | grep -E '/sensor/camera/.*(color|rgb|image)'
```

### 4.2 Comprobar profundidad

**LECTURA**:

```bash
timeout 8 ros2 topic hz /sensor/camera/stereo/depth/raw
```

### 4.3 Comprobar la nube de puntos

**LECTURA**:

```bash
timeout 8 ros2 topic hz /sensor/camera/stereo/pointcloud/raw
ros2 topic info -v /sensor/camera/stereo/pointcloud/raw
```

Esto confirma el flujo; no guarda un fichero PCD. Para una aplicación propia se
debe suscribir al tópico `sensor_msgs/msg/PointCloud2` y conservar también su
`frame_id` y sello temporal.

### 4.4 Consultar la calibración de cámara

**LECTURA**:

```bash
ros2 topic list -t | grep -E '/sensor/camera/.*(info|camera_info)'
```

Después se consulta el tópico encontrado:

```bash
timeout 10 ros2 topic echo --once NOMBRE_DEL_TOPICO
```

No se deben copiar intrínsecos de otra unidad; hay que usar los publicados por
este robot.

## 5. Lidar y percepción de obstáculos

Los lidar delantero y trasero están activos y alimentan la navegación.

### 5.1 Verificar ambos lidar

**LECTURA**:

```bash
timeout 8 ros2 topic hz /sensor/lidar/front
timeout 8 ros2 topic hz /sensor/lidar/back
ros2 topic info -v /sensor/lidar/front
ros2 topic info -v /sensor/lidar/back
```

### 5.2 Evitación de obstáculos

No se inicia con una orden independiente: forma parte del stack de navegación.
Ya se observó que el robot modifica el recorrido ante obstáculos durante una
navegación a waypoint.

Ejemplo operativo: navegar a un punto con el procedimiento de la sección 10 y
colocar únicamente un obstáculo ligero y visible, bajo supervisión y con paro
preparado. No utilizar personas para probar el frenado.

## 6. Detector especializado de caja azul `workbin`

Ésta es la función de percepción de objetos confirmada. No es un detector
general: está configurado para un contenedor tipo BYD de aproximadamente
`0.60 × 0.40 × 0.22 m` y devuelve el objeto `workbin` y su pose.

El contenedor debe estar visible, estable, con el lado largo aproximadamente
paralelo a los hombros y sin oclusiones importantes.

### 6.1 Medición rápida sin mover el robot

**LECTURA** — desde el PC Ubuntu:

```bash
cd /home/lacuna/proyectos/Robots/Humanoide
./scripts/cruzr_blue_workbin_cycle.sh --measure-box-fast
```

Salida esperada:

```text
BOX_POSE_CAMERA=x y z yaw
```

`x` representa el error lateral en la cámara, `z` la distancia aproximada y
`yaw` el giro de la caja. Si no aparece `workbin`, el script rechaza la medida.

### 6.2 Llamada directa al detector

**LECTURA** — dentro de
`walker-motion.manipulation_robot_app-1` en `motion`:

```bash
rosa action send_goal /cv/task/transport_action \
  cv_task_msgs/action/VisionActionTask \
  '{"task_type":"transport","trans_inputs":{"camera_name":"head","task_stage":"grasp","box_size":{"x":0.60,"y":0.40,"z":0.22}}}'
```

Un resultado válido debe terminar con `status=4`, `ok: True`,
`object_name: workbin` y al menos una pose en `box_pose`.

### 6.3 Preparar únicamente la visión

**MOVIMIENTO DE CABEZA**:

```bash
./scripts/cruzr_blue_workbin_cycle.sh --prepare-vision
```

Esta orden baja la cabeza; no mueve brazos ni chasis.

### 6.4 Otros perfiles especializados instalados

La imagen del contenedor de percepción contiene más configuraciones y modelos
especializados. No son detectores generales ni están ejecutándose a la vez. El
contenedor activo se inicia concretamente con:

```text
rosa run pose_6d_estimate box_pose_estimator_node -- \
  -c pose_6d_estimation_640_400_byd.json
```

Por tanto, sólo el perfil `byd` produce actualmente la detección `workbin` que
hemos conectado al agarre. Los demás perfiles encontrados son:

| Perfil | Objeto o variante prevista | Geometría principal configurada | Estado en esta unidad |
|---|---|---:|---|
| `byd` | Contenedor BYD/`workbin` | 60,3 × 39,7 × 21,7 cm | **Activo y probado** |
| `foxconn_tray` | Bandeja Foxconn | 38 × 36 × 22 cm | Modelo y configuración presentes; no activo |
| `jiepu_tray` | Bandeja Jiepu/FSK | 41 × 26 × 24 cm | Modelo y configuración presentes; no activo |
| `putbox` | Cajas y contenedores | 60,3 × 39,7 × 21,7 cm y tres tamaños auxiliares | Modelo y configuración presentes; no activo |
| `putcarton` | Caja de cartón grande | 60 × 43 × 41 cm y tres tamaños auxiliares | Modelo y configuración presentes; no activo |
| `om` | Variante de cajas para el pipeline `box_task` | Los cuatro tamaños del perfil BYD | Configuración presente; no activa |
| `thor` | Variante de cajas para cámaras estéreo | Los cuatro tamaños del perfil BYD | Configuración presente; no activa |

Los tamaños auxiliares compartidos por varios perfiles son aproximadamente
`41 × 30,8 × 14 cm`, `40 × 30 × 16 cm` y `60 × 40 × 25 cm`. Que un tamaño
aparezca en el JSON no demuestra que cualquier caja de esas dimensiones vaya a
ser reconocida: también intervienen las clases aprendidas, la apariencia, la
cámara, la iluminación y los filtros de profundidad.

No debe cambiarse en producción el perfil `byd` ni conectar un perfil alternativo
a los brazos sin seguir esta secuencia:

1. Registrar configuración, imagen y salida actuales del perfil BYD.
2. Activar el perfil alternativo de forma aislada o en modo de diagnóstico.
3. Validar únicamente segmentación, clase, pose, frame y estabilidad temporal.
4. Restaurar y confirmar `byd` antes de volver a utilizar los scripts actuales.
5. Sólo después de una prueba física supervisada crear tareas de manipulación
   específicas para el nuevo objeto.

La acción `/cv/waist_front/task/transport_action` ofrece la misma familia de
percepción desde la cámara de cintura; no constituye por sí sola otro detector
de objetos.

## 7. Detector AprilTag

El contenedor `walker-drivers.apriltag_detector-1` y los servicios de inicio
están activos. Hace falta una etiqueta física, conocer su ID y medir su lado
impreso en metros.

### 7.1 Detectar una etiqueta

**CAMBIO DE ESTADO**, sin movimiento — dentro de `walker-ros.ros2-1`:

```bash
ros2 service call /apriltag/start_detecting \
  sensor_task_msgs/srv/AprilTagStartDetecting \
  "{start_detecting: true, img_topic_name: '/sensor/camera/stereo/color/raw', tag_id: 0, tag_size: 0.16, tag_frame: 'apriltag_0'}"
```

En otro terminal ROS 2:

```bash
ros2 topic echo /sensor/camera/stereo/april_tag/results
```

El ejemplo supone ID 0 y lado impreso de 0,16 m. Hay que sustituir ambos datos
por los de la etiqueta real; un tamaño incorrecto produce una distancia 3D
incorrecta.

### 7.2 Detener la detección

**CAMBIO DE ESTADO**:

```bash
ros2 service call /apriltag/start_detecting \
  sensor_task_msgs/srv/AprilTagStartDetecting \
  "{start_detecting: false, img_topic_name: '/sensor/camera/stereo/color/raw', tag_id: 0, tag_size: 0.16, tag_frame: 'apriltag_0'}"
```

La detección de bundles también está instalada mediante
`/apriltag/start_bundle_detecting`, pero requiere un YAML de bundle compatible;
no se proporciona una orden de ejecución hasta definir ese fichero.

## 8. Profundidad estéreo de una región de interés

La acción `/cv/task/stereo_depth_roi_action` está activa. Permite pedir RGB y
profundidad sólo para un rectángulo de la imagen.

### 8.1 Verificar resolución antes de elegir la ROI

**LECTURA**:

```bash
ros2 topic list -t | grep '/sensor/camera/stereo/.*info'
timeout 10 ros2 topic echo --once TOPICO_CAMERA_INFO
```

### 8.2 Solicitar una ROI de prueba

**LECTURA** — dentro de un contenedor con `/opt/walker/setup.bash` y `rosa`:

```bash
rosa action send_goal /cv/task/stereo_depth_roi_action \
  cv_task_msgs/action/StereoDepthRoi \
  '{"input_roi":{"x_offset":100,"y_offset":100,"height":100,"width":100,"do_rectify":false}}'
```

La ROI debe quedar dentro de la resolución publicada. Un resultado correcto
contiene `success: true`, la ROI confirmada y los mapas RGB/profundidad.

## 9. Voz

### 9.1 Hacer que el robot hable en inglés

**AUDIO, sin movimiento** — desde el PC Ubuntu y con acceso directo a
`192.168.11.3`:

```bash
./scripts/cruzr_say_english.sh --check
./scripts/cruzr_say_english.sh "Welcome. The system is ready."
```

`--check` comprueba la acción TTS sin reproducir audio.

Para listar las voces instaladas, dentro de `walker-ros.ros2-1`:

```bash
ros2 service call /sys/speech/get_speaker_list \
  sys_task_msgs/srv/GetSpeakerList "{}"
```

### 9.2 Reconocer voz en inglés

**CAMBIO DE ESTADO**, sin movimiento — dentro de `walker-ros.ros2-1`:

```bash
ros2 service call /sys/asr/enable std_srvs/srv/SetBool "{data: true}"
ros2 service call /sys/run_record/enable std_srvs/srv/SetBool "{data: true}"
ros2 topic echo /sys/speech/asr
```

Al hablar se espera una salida como:

```text
text: 'please wave. '
language: <|en|>
```

Para terminar la captura:

```bash
ros2 service call /sys/run_record/enable std_srvs/srv/SetBool "{data: false}"
```

`run_record` activa el flujo de micrófono/ASR; no implica que se cree y conserve
un archivo de audio. El ASR puede clasificar erróneamente una frase inglesa como
china, por lo que una orden de movimiento debe exigir coincidencia explícita y
timeout.

## 10. Mapas, localización y navegación autónoma

El mapa confirmado es `test_route_01`, con los puntos:

```text
START, PASO1, PASO2, PASO 3, PASO4, FINISH
```

La navegación usa localización, lidar, mapas de coste y evitación de obstáculos.

### 10.1 Comprobar mapa y localización sin mover

**LECTURA** — desde el PC Ubuntu:

```bash
./scripts/cruzr_blue_workbin_map_route_short.sh --check --fast
```

Dentro de `walker-nav.nav_taskmanager-1` también se puede consultar el mapa:

```bash
rosa action send_goal /vnav/task/command \
  unav_task_msgs/action/Task \
  '{"command":"get_map_name","arg_json":"{}"}'
```

La pose actual se observa dentro de `walker-ros.ros2-1`:

```bash
timeout 10 ros2 topic echo --once /nav/robot_pose
```

### 10.2 Navegar a un waypoint

**MOVIMIENTO DE BASE** — dentro de `walker-nav.nav_taskmanager-1`:

```bash
rosa action send_goal /vnav/task/command \
  unav_task_msgs/action/Task \
  '{"command":"navigation_start","arg_json":"{\"target_point\":{\"map_name\":\"test_route_01\",\"mode\":\"logo_nav\",\"id\":\"PASO1\"}}"}'
```

Antes de ejecutarlo: cargador y Ethernet desconectados, robot correctamente
localizado, pasillo despejado para toda su anchura y paro preparado.

### 10.3 Parar una navegación por software

En otro terminal del mismo contenedor:

```bash
rosa action send_goal /vnav/task/command \
  unav_task_msgs/action/Task \
  '{"command":"navigation_stop","arg_json":"{}"}'
```

`Ctrl+C` sólo puede cortar el cliente; no debe suponerse que cancela la misión
interna. Para una emergencia se utiliza el paro físico, no esta acción ROSA.

### 10.4 Crear o editar mapas y puntos

La interfaz web ya se ha utilizado en:

```text
http://192.168.11.3/map/navigation
```

Permite crear el mapa con lidar, localizar el robot y crear waypoints. Para una
segunda mesa conviene crear un waypoint de aproximación despejado delante de la
mesa, no un punto debajo ni pegado a ella. La aproximación final a la caja o al
apoyo debe hacerse con percepción/odometría local.

## 11. Movimientos predefinidos de brazos sin manos

La lista blanca actual contiene:

- `fist_up_s2`: brazo derecho; probado físicamente en esta unidad.
- `cruzr/wave_arm`: saludo de brazo derecho y retorno a cero; tarea oficial
  instalada, pendiente de primera validación física controlada.

### 11.1 Listar y comprobar

**LECTURA**:

```bash
./scripts/cruzr_brazos_sin_manos.sh --list
./scripts/cruzr_brazos_sin_manos.sh --check
```

### 11.2 Ejecutar el movimiento ya probado

**MOVIMIENTO DE BRAZO**:

```bash
./scripts/cruzr_brazos_sin_manos.sh --run fist_up_s2
```

### 11.3 Ejecutar el saludo oficial

**MOVIMIENTO DE BRAZO**:

```bash
./scripts/cruzr_brazos_sin_manos.sh --run cruzr/wave_arm
```

Se exige zona completa de brazos despejada, robot estable, cargador desconectado
y paro preparado. No usar `--run-all` como primera prueba de una rutina nueva.

## 12. Agarre, elevación y depósito del contenedor azul

El flujo determinista validado combina el detector `workbin` con tareas de
manipulación. No utiliza GR00T/VLA.

### 12.1 Comprobar el sistema

**LECTURA**:

```bash
./scripts/cruzr_blue_workbin_cycle.sh --check
```

### 12.2 Ciclo sin mover la base

**MOVIMIENTO DE CABEZA Y BRAZOS**:

```bash
./scripts/cruzr_blue_workbin_cycle.sh --run --hold 3 --yes --fast
```

Secuencia: baja cabeza, prepara brazos, detecta, sujeta, eleva, mantiene tres
segundos, baja hasta contacto y abre. No mueve el chasis y no vuelve a `home`
porque la mesa sigue dentro de la trayectoria de los brazos.

### 12.3 Agarrar y dejar la caja suspendida

**MOVIMIENTO DE BRAZOS**:

```bash
./scripts/cruzr_blue_workbin_cycle.sh --grasp --yes
```

### 12.4 Depositar una caja ya sujeta

**MOVIMIENTO DE BRAZOS**:

```bash
./scripts/cruzr_blue_workbin_cycle.sh --deposit-held --yes
```

Estas dos órdenes sólo deben usarse si el registro del script corresponde al
agarre vigente y nadie ha modificado físicamente caja, mesa o brazos.

## 13. Aproximación visual y transporte corto de la caja

### 13.1 Centrar el robot sin agarrar

**MOVIMIENTO DE CABEZA Y BASE**:

```bash
./scripts/cruzr_blue_workbin_carry_back.sh --align-only --yes --fast
```

La función mide centro, profundidad y orientación, corrige el chasis y termina
antes de mover los brazos.

### 13.2 Agarrar después de centrarse

**MOVIMIENTO DE BASE, CABEZA Y BRAZOS**:

```bash
./scripts/cruzr_blue_workbin_carry_back.sh --grasp-only --yes --fast
```

### 13.3 Ciclo corto completo

**MOVIMIENTO DE BASE, CABEZA Y BRAZOS**:

```bash
./scripts/cruzr_blue_workbin_carry_back.sh --run --yes --fast
```

Secuencia prevista: centra, agarra, retrocede 0,50 m, vuelve a la pose de agarre,
deposita, se separa de la mesa y termina en `home`.

Este ciclo integra funciones que se han validado por partes y continúa en ajuste.
Debe permanecer supervisado; no equivale todavía a una misión industrial
homologada.

## 14. Recorridos del mapa transportando la caja

### 14.1 Ruta corta actual

**MOVIMIENTO COMPLETO**:

```bash
./scripts/cruzr_blue_workbin_map_route_short.sh --run --yes --fast
```

Ruta configurada:

```text
caja -> START -> PASO1 -> mesa -> depósito -> home
```

Desde `PASO1` vuelve directamente a la pose de aproximación de la mesa.

### 14.2 Ruta larga

**MOVIMIENTO COMPLETO**:

```bash
./scripts/cruzr_blue_workbin_map_route.sh --run --yes --fast
```

Ruta configurada:

```text
START -> PASO1 -> PASO2 -> PASO 3 -> PASO4 -> FINISH
       -> PASO4 -> PASO 3 -> PASO2 -> PASO1 -> START
       -> mesa -> depósito -> home
```

La ruta larga requiere pasillos y giros despejados para la anchura total de la
caja, supervisión continua y batería suficiente en ambos packs. Sigue siendo una
prueba de integración, no una función de producción desatendida.

## 15. Recuperación automática a `home`

### 15.1 Diagnóstico sin movimiento

**LECTURA**:

```bash
./scripts/cruzr_recover_to_home.sh --check
```

### 15.2 Recuperar postura

**MOVIMIENTO DE BASE Y CUERPO**:

```bash
./scripts/cruzr_recover_to_home.sh --run --yes --fast
```

Si detecta brazos junto a la mesa, retrocede hasta 0,50 m antes de ejecutar la
tarea oficial `cruzr/home`. Nunca avanza hacia la mesa. Debe haber al menos
1,50 m libres detrás del robot.

## 16. Interfaces presentes que aún no deben anunciarse como funciones operativas

Las siguientes señales existen, pero todavía no hay una prueba completa que
permita presentarlas como funcionalidades listas para usar:

| Interfaz o módulo | Evidencia presente | Qué falta |
|---|---|---|
| Perfiles `foxconn_tray`, `jiepu_tray`, `putbox`, `putcarton`, `om` y `thor` | JSON y modelos presentes dentro de `pose_6d_estimate` | Activación aislada, significado oficial de clases, objetos físicos y validación de precisión |
| Detector de caja con cámara de cintura | `/cv/waist_front/task/transport_action` tiene servidor | Confirmar `camera_name`, frames y resultado con caja real |
| Guardado de imagen estéreo | `/cv/task/stereo_image_save_action` tiene servidor | Contrato validado de `task_type`, ruta y permisos |
| Tracking pose 6D | servicios `/cv/task/pose_6d_track_request` y variante de cintura | Valores oficiales de `track_type` y prueba de estabilidad |
| Imagen semántica de navegación | `/vnav/perception/chassis_front_rgbd/semantic_image` | Confirmar clases, codificación y publicación durante misión |
| OCR 3D | `/vnav/perception/ocr_3d_markers` | Confirmar modelo, idiomas, activación y resultado real |
| Reconocimiento de persona/cara | `VisionStartTask` contiene campos y resultados genéricos | No se confirmó contenedor, acción o modelo específico ni salida anotada; `/sys/expression/face_control` controla la expresión del robot, no reconoce caras |
| QR y SPS | Campos en `VisionActionTask`/`VisionStartTask` | No se confirmó configuración, modelo ni valores operativos de `task_type` |
| Bundle AprilTag | Servicio activo | Crear y validar YAML de bundle |
| Recarga autónoma | Acción `/vnav/action/recharge` activa | Base compatible, mapa, tolerancias e interlocks validados |
| Comandos LLM | Acciones `/sys/speech/llm` presentes | Servicio conversacional fiable e integración segura con tareas |
| Aplicación móvil | No confirmada | APK oficial, compatibilidad y credenciales de UBTECH |

Se puede comprobar la existencia de una interfaz sin ejecutarla:

```bash
rosa action info NOMBRE_DE_LA_ACCION
rosa action type NOMBRE_DE_LA_ACCION
ros2 service type NOMBRE_DEL_SERVICIO
ros2 interface show TIPO_DEL_SERVICIO
ros2 topic info -v NOMBRE_DEL_TOPICO
```

## 17. VLA/GR00T: disponible como paquete, no operativo ahora

El paquete compartido contiene dataset, código, imágenes Docker y el checkpoint
`checkpoint-40000` de GR00T N1.5. Sin embargo, en el robot no aparecen actualmente
los contenedores VLA ni las interfaces `/gr00t/trigger_inference` y
`/vla_inference_result` activas.

Por tanto:

- el reconocimiento y agarre actuales de la caja no los realiza GR00T;
- los realiza el perfil activo `byd/workbin` del estimador de pose 6D más tareas
  deterministas de visión, manipulación y navegación;
- los perfiles alternativos de cajas y bandejas tampoco son GR00T: son
  configuraciones/modelos especializados del mismo paquete `pose_6d_estimate`;
- no existe todavía una orden VLA que pueda incluirse honestamente como ejemplo
  “usable ahora”;
- instalar el VLA requiere una validación separada de versiones, CUDA, límites
  articulares, parada, colisión y comportamiento sin publicar movimiento.

## 18. Regla práctica para nuevas funciones

Una nueva capacidad se añadirá a la parte operativa del catálogo sólo después de
superar estas cuatro comprobaciones:

1. El contenedor correspondiente está activo.
2. La acción, servicio o tópico tiene servidor/publicador real.
3. Una llamada sin movimiento devuelve datos coherentes y con frames conocidos.
4. Si mueve el robot, supera una prueba física supervisada y dispone de una
   recuperación segura.

Esta regla evita confundir “el mensaje contiene un campo” con “el robot ya sabe
hacer la tarea”.
