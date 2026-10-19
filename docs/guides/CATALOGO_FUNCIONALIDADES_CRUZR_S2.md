# Catálogo operativo de funcionalidades del Cruzr S2

## CAR-PART-VISION-20261019 — propuesta de detector de referencia de pieza

**APP2-SERVER-INSTALL-20261019 — flujo local instalado y comprobado.**
[Acceso, versiones y verificaciones](../app2/SERVIDOR_LOCAL_INSTALACION.md).
CVAT2.79.0 y RF-DETR1.11.2 en servidor RTX6000 Ada; anotación/exportación COCO,
inferencia GPU,1 paso de entrenamiento sintético y ONNX/ORTCPU pasan. Entrenador
sin red, datos en volúmenes propios; servicios Ollama previos conservados.
No dataset/modelo app2 real entrenado ni despliegue/cambio del robot.

**APP2-LOCAL-20261019 — decisión vigente:** CVAT Community y entrenamiento
RF-DETR Seg Nano en servidor propio, inferencia final en Vision. Servidor
ofrecido comprobado por SSH: RTX6000 Ada48GB,503,51GiB RAM,32 núcleos;
SSD Docker con1,65TiB libres. [Plan local, recursos y tiempos](../app2/PLAN_LOCAL_RECURSOS_Y_TIEMPOS.md).
El estado posterior instalado se indica arriba; compatibilidad ONNX/TRT8.6 y
rendimiento del modelo final pendientes. La propuesta cloud queda histórica.

**APP2-VISION-RUNTIME-20261019 — unidad real comprobada.**
[Hardware, runtime, cámaras y decisión de despliegue](../app2/VERIFICACION_ROBOT_Y_ELECCION_VISION.md).
Vision AGX Orin64GB/aarch64 con L4T36.3/CUDA12.2/TRT8.6.2.3 y mensajes de
cámara SHM; cuatro canales con recepción pasiva verificada. La propuesta inicial
usaba entrenamiento en nube; el plan local posterior conserva ONNX/motor propio
compatible en Vision. No instala el
contenedor actual Roboflow Jetson6.2 suponiendo compatibilidad ni modifica el
detector de cajas vendor. Modelo app2, identificación y benchmark pendientes.

**APP2-PLAN-20261019 — documentación canónica de esta aplicación.**
El usuario la denomina **app2**. [Plan, hitos y preguntas pendientes](../app2/PLAN_Y_PREGUNTAS.md),
[requisitos](../app2/REQUISITOS_CLIENTE.md) e [imágenes originales](../app2/FOTOS_Y_FUENTES.md).
Se conserva la lámina exacta de fábrica2189×630 y cinco capturas del robot,
con hashes y paquete privado. Primer hito: detectar/separar instancias visibles;
identificar material ID y manipular requieren validaciones posteriores.
No se ha entrenado ni instalado un detector app2. La aclaración ITR/OTR
siguiente actualiza la interpretación inicial del título como discrepancia.

**Requisito aportado — ITR-IDENTITY-REQ-20261019.** La captura del documento
del usuario se titula *ITR Material Feed and Empty Container Handling*. Exige
confirmar el **material ID esperado frente al real antes de cargar** el
transportador o dispositivo de presentación, y registrar resultado de lectura,
no-read/misread, número de reintentos y estado de excepción en la interfaz de
desarrollo de la sección7. Esa sección, protocolo, documento original y versión
no se han aportado. El usuario aclara ITR como Inner Tie Rod y OTR como Outer
Tie Rod, terminología contrastada en la fuente primaria enlazada en app2.
El título OTR puede iniciar el apartado siguiente; su posición no demuestra
que las fotos sean OTR ni que exista una discrepancia. La identidad de las
piezas concretas sigue siendo una inferencia pendiente de cliente. ITR no es,
por sí solo, un código de referencia suficiente para etiquetar el detector.

También se describe comprobar material correcto y destino preparado, retirar
una pieza o cantidad aprobada, conservar orientación y superficies funcionales,
colocar con orientación/espaciado requeridos, comprobar bloqueo/llenado/
desalineación, gestionar cartón vacío y registrar ciclo/anomalías. El apoyo
manual sólo se permite en evaluación de desarrollo si se documenta como
condición de apoyo o excepción. Son **requisitos aportados, no prestaciones
verificadas en el robot**.

Implicación propuesta para percepción: recibir ID esperado de una fuente
definida de estación/orden, localizar cada pieza, identificar referencia y
compararla antes de entregar una selección válida al ejecutor. Si hay marcado
legible, evaluar lectura de código/texto; la lámina no exige una tecnología
concreta. Geometría, detalles de pieza y etiqueta de caja pueden aportar
comprobaciones cruzadas, pero el ID de la caja no demuestra por sí solo que
cada pieza interior sea correcta. Una referencia no distinguible visualmente
desde la vista disponible necesita otra vista/marcado/trazabilidad validada;
no se convierte una confianza del detector en identificación cierta. Debe
existir resultado desconocido/no leído/no coincidente y registro, con límites
de reintento acordados; esquema/API de sección7 PENDIENTE, sin inventar endpoints.
Faltan códigos de las referencias objetivo/confundibles y disponibilidad de
marcajes. No se ha entrenado, instalado ni conectado a movimiento este flujo.
Fuente registrada en evidencia privada:
`../Humanoide-vla-evidence/20261019T085657Z_ITR_REQUIREMENTS_SCREENSHOT/`.

**Actualización CAR-PART-VISIBLE-20261019:** nuevas capturas tras aviso del
operador muestran las piezas completas en la cámara de cabeza: bandeja de
cartón sobre contenedor azul, varias piezas metálicas alargadas próximas entre
sí y manos fuera del interior. Rectificada960×576, región aproximada de trabajo
x380–640/y320–505 en esa imagen concreta; no son coordenadas métricas ni un
recorte que deba copiarse a otro encuadre. También se conserva raw1920×1536,
con más detalle para estudiar rasgos distintivos; tiene distorsión óptica y
no se intercambian sus píxeles con profundidad/imagen rectificada. Cintura
640×360 sigue cortando la bandeja. No se identifica nombre, código, referencia
o punto de agarre a partir de la apariencia; se solicita al operador código
objetivo y posición dentro de la bandeja. Distinguir referencias parecidas
requiere sus etiquetas/ejemplos, no sólo un contorno de objeto alargado.
Sin detector, inferencia, entrenamiento ni movimiento del agente. Evidencia:
`../Humanoide-vla-evidence/20261019T084059Z_CAR_PART_VISIBLE_READONLY/`.
La observación anterior de espuma parcialmente visible se conserva debajo como
historia de la primera captura, no como encuadre vigente.

19-10-2026 Europe/Madrid. **OBSERVACIÓN DE CÁMARAS; DETECTOR PROPUESTO,
NO IMPLEMENTADO.** El operador necesita distinguir la pieza objetivo de otras
piezas de coche parecidas, no sólo detectar un objeto sobre la espuma.

Captura pasiva en Vision192.168.11.3, contenedor redescubierto
walker-ros.ros2-1: cabeza RGB rectificada960×576/bgr8, cintura y chasis640×360/rgb8;
dos timestamps crecientes por cada canal. Cabeza izquierda raw1920×1536/yuv422
decodificada UYVY en una segunda consulta. Espuma sobre caja azul parcialmente
visible en bordes de cabeza/cintura, sin pieza objetivo completa identificable.
No se conoce todavía referencia, dimensiones, material, CAD ni rasgos distintivos.
No inferir identidad a partir de la descripción del operador o del soporte.
Los campos age_ms del capturador incluyen procesamiento secuencial; no son una
medición de latencia completa ni de precisión del sensor.

PC: RTX4070 Laptop,8188MiB, driver580.178.04; acceso a Vision por eno1/.11.250.
No se ha medido inferencia ni capacidad disponible bajo carga de teleoperación.

Estrategia propuesta, pendiente de comprobar con imágenes útiles:

1. Obtener encuadre completo y detalle suficiente para distinguir referencias;
   elegir cámara por cobertura y calidad, antes de elegir resolución/modelo.
2. Entrenar un segmentador pequeño, comparando variantes n/s de YOLO26-seg
   como candidatos actuales; COCO genérico no identifica por sí solo esta
   referencia industrial. Incluir piezas confundibles, espuma vacía y distractores;
   etiquetar referencias separadas y contornos. Contraste/forma de espuma sólo
   ayudan a localizar la zona de trabajo, no certifican identidad de la pieza.
3. Empezar con unos cientos de imágenes diversas para un prototipo, ampliar
   según errores. Reservar sesiones/unidades para prueba; no dividir imágenes
   consecutivas casi idénticas entre entrenamiento y prueba. Evaluar confusión
   entre referencias y falsa aceptación, además de máscara/localización.
4. Si las referencias casi idénticas se confunden, probar verificación con
   clasificador ligero sobre el recorte o puntos distintivos. Si el detalle no
   es visible, cambiar vista/resolución o identificación física; más entrenamiento
   no recupera información ausente.
5. Probar primero en PC aislado; recortar zona de trabajo conservando detalle,
   batch1, cola de última imagen, sin acumular vídeo ni procesar frames antiguos.
   Tras validar precisión, comparar TensorRT con menor precisión numérica y
   conservar sólo optimizaciones que mantengan la calidad. Medir latencia p50/p95
   imagen→resultado, falsa aceptación/rechazo y consumo bajo carga. No extrapolar
   benchmarks de GPU T4 a este PC ni garantizar FPS antes de medir.
6. Para agarrarla, añadir pose métrica/orientación con profundidad registrada,
   intrínsecos/TF y, si hace falta, CAD o puntos clave. Máscara 2D no equivale a
   pose de agarre. En piezas brillantes, verificar profundidad antes de usarla.

Fuentes primarias consultadas:
[segmentación Ultralytics](https://docs.ultralytics.com/tasks/segment/),
[exportación TensorRT](https://docs.ultralytics.com/integrations/tensorrt/).
El motor TensorRT se construye para el hardware/runtime de destino; no se
traslada sin validación un engine del PC a Vision. No se ha instalado ningún
modelo ni modificado el detector workbin del proveedor, sus límites o endpoints.

Evidencia privada externa:
`../Humanoide-vla-evidence/20261019T080612Z_CAR_PART_VISION_READONLY/`.
Capturadores exactos ejecutados vía stdin, PNG sin anotación, timestamps/tipos,
hashes, hallazgos y respaldo documental. Sólo suscripciones de imagen; cero
servicios, publicadores de mando, movimientos, reinicios o instalaciones.

**15-10-2026 — BOTELLA-VISION-GRASP-20261015. PLAN; percepción/agarre pendientes.**
[Plan operativo y ramas de decisión](../plan_botella.md).
[Resumen del proceso](../plan_botella_resumen.md), también en [PDF](../plan_botella_resumen.pdf). El detector instalado de
cajas no demuestra reconocimiento de botellas; se propone evaluar primero un
segmentador preentrenado COCO en PC, después RGB-D y calibración, y finalmente
integración IK/agarre. Cámara de cintura observada: SHM Image1m, RGB rgb8 y depth
16UC1, 640×360; CameraInfo requiere QoS compatible reliable/transient_local.
No están verificadas escala, correspondencia RGB-D ni pose de agarre. Se incluyen
prototipos de captura e inferencia, con sintaxis revisada y conversión SHM probada
offline; no se han ejecutado end-to-end ni instalado en el robot. Sin movimiento.
Evidencia: `../Humanoide-vla-evidence/20261015_BOTTLE_PLAN/` fuera de Git.


**05-10-2026 — MAP-HEAD-RELOCALIZE-20261005. OBSERVADO, sólo lectura.**
Tras nuevo guardado, cabeza movida por vnav_head_processor/navigation durante
relocation_start fusion. Navegador termina barrido con stop_rotate y centro0/0;
Motion confirma IsReached, cabezaREADY. Relocalización exteriorstatus4/READY/
FSM_WaitNavigate, mientras VSLAM aúnLOCATION_LOST: no demuestra recuperación
visual ni precisión física. Mapa nuevo2471puntos/56poses; lectura4443/38 anterior
ya histórica. Sin acciones, movimientos o cambios remotos del agente.
[Secuencia, UUID, límites y evidencia](../incidents/2026-10-05_UTARS_NAV_MAP_LOCALIZATION.md#actualización-posterior--cabeza-y-relocalización-del-mapa-nuevo).

**05-10-2026 — VOICE-MAPPING-08. OBSERVADO; traducción no integrada.**
Cartografía emite TTS chino: «cerrando bucle; reduzca velocidad/espere» y «bucle
completado; continúe mapeando o guarde». Literales en libmapping2d_lidar.so,
fuera de adaptadores de workers/Control Center/freno; estas últimas bibliotecas
sí están cargadas. Cartografía del operador posteriormente guarda2D/visual y
FSM_Mapping SUCCEEDED; calidad/localización posterior no comprobadas.
Sin audio nuevo, movimiento, reinicio o cambios remotos del agente.
[Textos, origen, evidencia y continuación](../voice/AVISOS_MAPEO_CHINO_20261005.md).

**05-10-2026 — MAP-QUALITY-20261005. OBSERVADO, sólo lectura.**
Última relocalización utars_nav_map falla; VSLAM=LOCATION_LOST y pose visual
no fiable. Mapa visual presente4443puntos/38poses, pero candidatos no superan
consistencia de solver (ejemplo17<20). Cobertura/calibración/causa PENDIENTES.
API y archivos actuales no contienen destinos: get1/put1 ausentes; escenario1
bloqueado por Require one unique get1. No copiar coordenadas de un marco antiguo.
Sin relocalización/movimiento, reinicio ni edición del mapa por el agente.
[Hallazgos, límites, evidencia y continuación](../incidents/2026-10-05_UTARS_NAV_MAP_LOCALIZATION.md).

**05-10-2026 — VOICE-VOLUME-READONLY. OBSERVADO, sin cambios.**
cruzr_say_english.sh envía volume=100; PulseAudio en Vision y dentro de
walker-voice.speech_service-1 muestra salida predeterminada100%, mute=no.
Salida analógica activa: alsa_output.platform-sound.analog-stereo. Consulta sólo
lectura; sin audio ni cambio de volumen. Amplificación adicional no ensayada.
Receta manual tras acceso SSH a walker@192.168.11.3:
`pactl set-sink-volume alsa_output.platform-sound.analog-stereo 110%`;
reversión al valor observado: mismo comando con100%. Puede distorsionar.
Evidencia y respaldo documental: ../Humanoide-vla-evidence/20261005_VOICE_VOLUME_READONLY/.


**05-10-2026 — VOICE-TTS-HELLO-MATEO. VERIFICADO técnico; escucha PENDIENTE.**
Petición explícita: decir «Hello Mateo». Vision192.168.11.3: docker ps descubre
walker-voice.speech_service-1; --check confirma sys_task_msgs/action/Tts y un
servidor. Comando versionado: ./scripts/cruzr_say_english.sh "Hello Mateo";
objetivo0cbb2742-6939-4e17-a1f6-743c2177c220 aceptado, desc=Success, status=4.
Wrapper sale27 por exigir texto SUCCEED; no se repite la reproducción. Revisión
de esa validación PENDIENTE. Fuente SHA256442760e137480abb38e232396aa79d9f84c34b1f4b359d2565c1028b797a58c7.
Sólo audio transitorio; sin movimiento, instalación, reinicio ni configuración
remota modificada. Escucha humana no confirmada; estado físico no inferido.
Evidencia/resultado y respaldo documental before/after:
../Humanoide-vla-evidence/20261005_HELLO_MATEO/.
Reversión documental selectiva desde before/; no hay configuración que restaurar.


**22-09-2026 — VOICE-ES-01: inventario para todos los avisos en español.**
Localizados textos TtsClient, WAV y aviso de arranque propio en inglés.
Conversión no instalada; soporte TTS español pendiente. Primera lectura SSH
correcta; consulta posterior de voces bloqueada por timeout de conexión.
Sin audio, micrófonos, reinicios ni cambios remotos. [Inventario y pendientes](CRUZR_S2_VOZ_ESPANOL.md).

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

**19-10-2026 — HEAD-OBSERVE-20261019.** El wrapper admite ahora los perfiles
`cruzr_s2_v1` y `cruzr_s2_v1_sps` exclusivamente en sus modos de cabeza.
Los modos de cajas/brazos conservan su requisito de abrazaderas. No cambia el
perfil del robot ni la tarea instalada; XML actual contrastado con SHA256
`f3a73626f97b471d4a0a03c98c24de32243651116c497328e69b5ddc57ea46c1`.

Primero, diagnóstico **sin movimiento**:

```bash
./scripts/cruzr_blue_workbin_cycle.sh --check-head
```

Si termina con `HEAD_CHECK_OK`, con control exclusivo y condiciones físicas
actuales comprobadas, **MOVIMIENTO DE CABEZA**:

```bash
./scripts/cruzr_blue_workbin_cycle.sh --prepare-vision
```

Pide escribir `BAJAR CABEZA`. Centra yaw0 e inclina pitch−0,43rad (unos24,6°)
en2s. No mueve brazos ni chasis ni inicia agarre, inferencia o cambio de modo.
Ambos modos rechazan --fast y conservan hashes, salud20D, paros, batería,
cargador y exclusión de acción activa. El diagnóstico técnico no certifica
el entorno físico ni el encuadre resultante. PICO/web/otros mandos deben estar
detenidos. Si hay ACTION_BUSY, fault o consignas latentes, no repetir con --yes
ni cambiar a auto_task/HOME como atajo; resolver el estado según la guía de
recuperación. Esta adaptación no es una recuperación del incidente de HOME.

Verificación inicial: bash-n y36tests offline pasan. Check real --check-head acepta SPS,
valida salud20D (velocidad0, delta consigna máximo0,003039rad), pero termina27
por ACTION_BUSY=motion_goal_active. No alcanza las lecturas de paros/batería/
cargador. No se cancela la acción ni se cambia modo para superar el gate.
En esa comprobación inicial no se ejecutó movimiento. Evidencia externa:
`../Humanoide-vla-evidence/20261019T082535Z_HEAD_ONLY_SCRIPT/`.

**Prueba posterior — APP2-REAL-PIECES-PILOT-20261019:** tras confirmar las
condiciones físicas y desconectar el cargador, el preflight completo pasó con
paros `0/0`, cargador desconectado y baterías `94,6/95,0 %`.
`--prepare-vision --yes` ejecutó únicamente `cruzr/move_head_lower`: goal
`b34d2b9e-7a03-435d-9118-93ed2f0c3546`, `status=4`, `SUCCEED`, estado nativo
`1101001`. Las capturas posteriores muestran la bandeja completa y contornos
distinguibles; identidad de las piezas aún provisional. Sin cambios de modo,
HOME, configuración o modelo. El resultado es una prueba fechada, no una
comprobación de seguridad válida para una sesión futura. [Resultado y punto de
reanudación](../app2/PILOTO_PIEZAS_REALES.md), [fotografías](../app2/FOTOS_Y_FUENTES.md#4-capturas-posteriores-al-encuadre-de-cabeza).
Evidencia: `../Humanoide-vla-evidence/20261019T114329Z_APP2_REAL_PIECES_PILOT/`.

**Historia del bloqueo inicial — HEAD-ACTION-BUSY-20261019:** el UUID observado
27318de6-c1a6-4d86-a9c5-6f8b127df3da pertenecía a la tarea nativa PICO v4,
iniciada09:22 CEST. Seguía en ejecución aunque el PC estuviera STOP. El log
consultado confirmaba Head tracking1: para encuadrar dentro de una sesión PICO preparada,
la cabeza puede seguir la inclinación del visor, con grips/gatillos libres.
No equivale a autorizar una sesión nueva sin sus comprobaciones; aquella consulta
del PC mostraba tracking0. El script independiente requiere la tarea Motion libre;
no se cancela ni se cambia a auto_task/HOME automáticamente para conseguirlo.
[Detalle de seguimiento y límites](../teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md).
Evidencia: ../Humanoide-vla-evidence/20261019T083626Z_HEAD_ACTION_BUSY_READONLY/.

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
