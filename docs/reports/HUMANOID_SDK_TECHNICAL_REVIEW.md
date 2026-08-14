# Auditoría técnica exhaustiva — UBTECH Cruzr S2

Fecha: 2026-08-06<br>
Workspace: `/home/lacuna/proyectos/Robots/Humanoide`<br>
Caso de referencia: ciclo pallet → caja llena → cinta/vaciado → pallet de vacíos en La Palma; extensiones posteriores de carga/descarga de máquinas en EE. UU. y Polonia.

## Criterio y límites de la auditoría

Esta revisión es exclusivamente estática y local. No se instalaron DEB/wheels, no se ejecutaron scripts, firmware, binarios, nodos o contenedores, no se descomprimieron imágenes grandes a disco y no se hizo tráfico de red. Se inspeccionaron índices de archivos, texto/documentos, fuentes, mensajes, configuraciones, metadatos de dataset/checkpoint y manifests/configuración de imágenes Docker. Por ello se confirma **presencia e intención técnica**, no funcionamiento en un robot real.

Las conclusiones usan tres niveles:

- **[A] Confirmado:** existe evidencia directa en archivo/interfaz/código.
- **[B] Inferido:** consecuencia técnica razonable, aún no validada físicamente.
- **[C] No encontrado/por confirmar:** el material no permite afirmarlo.

La solicitud denomina al paquete VLA `cruzrs2_vla_pack-002`; la carpeta presente es `cruzrss2_vla_pack-002`. No se modificó ninguna de las tres carpetas originales.

## 1. Resumen ejecutivo

1. **[A] Los paquetes sí permiten iniciar un desarrollo serio sobre Cruzr S2:** hay interfaces ROS 2 para joints, ruedas, estado, F/T, cámaras, lidar y pinza; API de aplicación para navegación/mapas/skills; modelos URDF/USD; teleoperación; runtime offline; y un demo VLA con dataset y pesos. Evidencias: `Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/Cruzr S2 优必选SDK二次开发文档【对外】6.24.pdf`, `Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/demo/Cruzer_S2-low-level-demo0624.tar.xz`, `cruzrss2_vla_pack-002`, `utars-udoke-config-v0.2.0_offline-001`.
2. **[A] No hay evidencia suficiente para afirmar que el ciclo completo de La Palma esté implementado o sea viable industrialmente.** El demo cubre cuatro conductas de pick/place de estante con una caja de 60 × 40 × 22 cm a 1 m; no incluye navegación, accionamiento del efector, pallet, transporte con base, cinta ni volcado. Evidencias: manual SDK sección 7.3; `cruzrss2_vla_pack-002/data/utars_clamp_and_place_large_box_full_data_bio_lerobot_0319/meta/tasks.jsonl:1-4`; `meta/info.json:86-112`.
3. **[A] El payload publicado es sólo 15 kg máximo bimanual.** No aparece payload por brazo, curva por alcance/CoG/aceleración, peso del efector ni masa usada en el demo. Evidencia: manual SDK, especificación general, `Cruzr S2 优必选SDK二次开发文档【对外】6.24.pdf`.
4. **[A] La pinza PGC ofrece apertura de 0–50 mm y fuerza mandada de 0–100 N; una caja de 600 mm sin asas no puede deducirse como agarrable con esa geometría.** El VLA se denomina `utars_clamp`, pero su acción no contiene pinza/mano: probablemente usa placas/clamp y compresión bimanual, algo que UBTECH debe describir. Evidencias: manual SDK 5.10 y 7.3; `meta/info.json:86-112`; `codes-S2/motion/s2_vla_scripts/s2_bio_vla/s2_vla_pick_large_teleop_ready.xml:5-16`.
5. **[A] El VLA es un prototipo ROS 2 local de un solo RGB + estado articular → GR00T N1.5 → chunks articulares.** Aunque el dataset contiene 12 canales F/T, el runtime de inferencia no los usa; tampoco usa profundidad, pose 6D o estado de pinza. Evidencias: `meta/info.json:16-112`; `codes-S2/vision/rosa_vla_additional/vla-onboard/src/gr00t_control/model_interface_general_ros2.py:187-286`.
6. **[A] Hay defectos/inconsistencias que impiden probar el VLA sin corrección:** IDs de tarea contradictorios, resultado ROS Action marcado `succeed` tras fallo, pérdida de acciones lifter al convertir 20→17 y límite de velocidad global superior al máximo documentado de brazos. Evidencias: `codes-S2/vision/rosa_vla_additional/vla-onboard/src/mc_task_msgs/action/InferenceTask.action:1-7`; `.../configs/utars_clamp_and_place_large_bio_box_lock_lifter.yaml:6-10`; `.../gr00t_inference.py:240-251`; `codes-S2/motion/rosa_vla_additional/vla-motionx86/src/vla_executor/vla_executor/executor_node_sdk.py:37-43,88-166,272-295`.
7. **[A] Navegación, localización, mapping, recarga y pose de caja 6D aparecen en la plataforma offline, pero no están integrados en el demo VLA.** El estimador 6D usa configuración `byd` y project ID `walker_s2`, sin contrato de topics ni métricas. Evidencias: `utars-udoke-config-v0.2.0_offline-001/vision/.metafiles/nav.metafile.yml:1-91`; `box_pose_estimation.metafile.yml:1-12`.
8. **[A] No se encontró un planificador de colisiones/MoveIt, control cartesiano, controlador de compliance, recovery de misión ni safety supervisor VLA.** El ejecutor sólo verifica velocidad y publica posición con velocidad/esfuerzo cero. Evidencia: `executor_node_sdk.py:88-166,210-248,342-376` y ausencia de esos componentes en los árboles inspeccionados.
9. **[A] Existen riesgos de compatibilidad y supply chain:** runtime base Orin CUDA 12.2/cuDNN 8.9 frente a VLA CUDA 12.6.3/cuDNN 9.3/PyTorch 2.6; Isaac-GR00T fue clonado sin commit visible y se relajaron versiones. Evidencias: configuración interna de `utars-udoke-config-v0.2.0_offline-001/images/vision.tar` e historial interno de `cruzrss2_vla_pack-002/docker_images/vla_inference_node_sdk.tar`.
10. **[A] El material no constituye una solución de seguridad industrial.** Confirma E-stop físico y fallos de servo, pero no safety PLC, zonas, escáneres, PL/SIL, control seguro de velocidad/fuerza o interfaces de máquina. Evidencias: manual SDK secciones 2.1–2.5; ausencia en los tres paquetes; `executor_node_sdk.py:135-166`.

**Dictamen:** viabilidad del ciclo completo de La Palma **todavía indeterminable**. Es razonable inferir que hay base técnica para un prototipo de navegación + pick/place bimanual condicionado, pero peso real, efector, precisión, transporte cargado, volcado, seguridad y fiabilidad no están demostrados.

## 2. Descripción de los tres paquetes

### 2.1 SDK y documentación

`Cruzr S2-20260803T070710Z-1-003` ocupa 298.15 MB y contiene 12 archivos: manual v2.1 PDF/DOCX, SOP de mapping, ejemplos ROS 2 C++, cliente ControlCenter C++/Python, URDF/USD y paquete/SOP de actualización. El manual identifica Ubuntu 22.04, ROS 2 Humble y ROSA 2.0 en dos ordenadores del robot. Evidencias: `Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK`; manual SDK secciones 3.1–3.4.

El tar de bajo nivel contiene definiciones de `RobotState`, `RobotCommand`, `JointCmd`, `GripCmd`, `GripStatus`, mensajes de cámara de memoria compartida, batería y TTS, además de fuentes de ejemplo. El cliente de alto nivel contiene bibliotecas estáticas aarch64/x86_64 y wheels CPython 3.10 `ubt_robot` 1.0.9 para ambas arquitecturas. Evidencias: `SDK/demo/Cruzer_S2-low-level-demo0624.tar.xz`; `SDK/c++/ubt_api_tiny_colcon.0624.tar.xz`; `SDK/python/ubt_api_tiny_python.0624.tar.xz`.

### 2.2 VLA

`cruzrss2_vla_pack-002` ocupa 74.02 GB: 52 GiB de imágenes Docker, 16 GiB de checkpoint, 1.9 GiB de datos y dos árboles de código casi duplicados. Incluye entrenamiento/fine-tuning y ejecución, no sólo inferencia. Evidencias: `cruzrss2_vla_pack-002/gr00t_finetune.py:36-135,194-267,344-459`; `cruzrss2_vla_pack-002/weight/checkpoint-40000`; `cruzrss2_vla_pack-002/data`.

El dataset contiene 500 episodios/105,207 frames/500 vídeos a 120 fps y únicamente un split `train`. Hay 150/150 episodios pick/place de nivel inferior y 100/100 de nivel medio; no hay evaluación física o split separado. Evidencias: `data/utars_clamp_and_place_large_box_full_data_bio_lerobot_0319/meta/info.json:2-14`; `meta/episodes.jsonl`; `meta/tasks.jsonl:1-4`.

El checkpoint es GR00T N1.5 con acción 20-D, horizonte 10, bfloat16 y Transformers 4.51.3. Sus dos shards suman aproximadamente 7.58 GB y el optimizador 8.53 GB; llegó a 40,000 pasos, pero no registra best metric/checkpoint. Evidencias: `weight/checkpoint-40000/config.json:2-63`; `weight/checkpoint-40000/trainer_state.json`; archivos de `weight/checkpoint-40000`.

### 2.3 uDoke offline

`utars-udoke-config-v0.2.0_offline-001` ocupa 35.69 GB y contiene uDoke 0.8.7 para amd64/arm64, seis imágenes motion, veinte vision, 22 YAML, 14 scripts y manifests de despliegue. Las imágenes de integración son `zs2_motion-v0.2.0` amd64 y `zs2_vision-v0.2.0` arm64, ambas creadas el 2026-06-19. Evidencias: `utars-udoke-config-v0.2.0_offline-001/debs/upgrade.json:1-9`; `motion/metafile.yml:1-24`; `vision/metafile.yml:1-23`; manifests internos de `images/motion.tar` e `images/vision.tar`.

La imagen motion contiene controladores, EtherCAT, manipulation y SDK. La de vision contiene sensores, navegación/localización/mapping, ControlCenter, pose 6D, voz/LLM, web y observabilidad. Evidencias: etiquetas internas de `images/{motion,vision}.tar`; `motion/.metafiles/motion.metafile.yml:1-52`; `vision/.metafiles/{drivers,nav,system,box_pose_estimation}.metafile.yml`.

### 2.4 Cómo encajan

- La plataforma uDoke es el sistema base desplegable en las dos placas.
- El SDK documenta y expone las interfaces que usan aplicaciones propias.
- El VLA añade dos contenedores manuales: inferencia en Orin y ejecución articular en x86.
- No se encontró un metafile uDoke que gestione los contenedores VLA ni un BOM que declare la combinación homologada. Evidencias: manual SDK 7.3.3–7.3.4; `utars-udoke-config-v0.2.0_offline-001`; ausencia de VLA en sus metafiles.

El inventario ampliado está en `SDK_FILE_INVENTORY.md`.

## 3. Arquitectura reconstruida

### 3.1 Hardware y reparto

**[A] PC1 motion:** x86, dirección de fábrica `192.168.11.2`, control en tiempo real, EtherCAT, `t800_mc_server`, joints, IMU/F-T y `sdk_controller`. **[A] PC2 vision:** NVIDIA Jetson Orin arm64, `192.168.11.3`, cámaras, IA, navegación, ControlCenter y VLA. Comparten ROS domain mediante un switch. Evidencia: manual SDK secciones 3.1.1–3.1.3; `motion/metafile.yml:8-24`; `vision/metafile.yml:7-23`.

**[A] Robot:** 22 DoF sin manos — cabeza 2, brazos 7+7, waist 1, lifter 3, ruedas 2 — 176 cm, 188 kg, Orin declarado a 275 TOPS, profundidad/F-T/IMU/fisheye y payload bimanual máximo 15 kg. Evidencia: manual SDK, secciones 1.0–1.2.

### 3.2 Flujo de componentes y datos

```text
                           PC/PLC/aplicación externa
                        TCP 51000 (ubt_robot JSON-RPC)
                                      │
                           ┌──────────▼──────────┐
                           │ Orin / vision arm64 │
                           │ Ubuntu 22.04/Humble │
                           │ ControlCenter/skills│
                           │ maps/nav/localize   │
 RGB/RGBD/stereo/lidar ───►│ pose6D, TF, web    │
                           │                     │
 /sensor/camera/stereo/    │ GR00T inference     │
 color/raw +               │ RGB + joint state   │
 /mc/sdk/robot_state ─────►│ → 10×20 joint chunk │
                           └──────────┬──────────┘
                    ROS 2/CycloneDDS │ /vla_inference_result
                           ┌──────────▼──────────┐
                           │ x86 / motion amd64  │
                           │ Ubuntu 22.04/Humble │
                           │ VLA executor 200 Hz │
                           │ 20→17, interpola    │
                           │ sdk_controller      │
                           │ t800_mc_server      │
                           └──────────┬──────────┘
                                      │ EtherCAT/CAN
        /mc/sdk/robot_command ───────► joints, lifter, wheels, brazos
                                      │
                  GripCmd separado ──► PGC/manos (no usado por VLA)
```

Evidencias del flujo VLA: `codes-S2/vision/rosa_vla_additional/vla-onboard/src/gr00t_control/gr00t_inference.py:22-120,393-429,597-633`; `codes-S2/vision/rosa_vla_additional/vla-onboard/src/gr00t_control/model_interface_general_ros2.py:187-312`; `codes-S2/motion/rosa_vla_additional/vla-motionx86/src/vla_executor/vla_executor/executor_node_sdk.py:37-43,112-133,272-376`.

### 3.3 Interfaces principales

| Dominio | Interfaz confirmada | Evidencia |
|---|---|---|
| Estado robot | topic `/mc/sdk/robot_state`: joints, IMU[], F/T[] | manual SDK 5.1.1; `demo/...tar.xz::mc_state_msgs/msg/RobotState.msg` |
| Control joints | topic `/mc/sdk/robot_command`, `RobotCommand/JointCmd`, posición/velocidad/esfuerzo/PVT | manual SDK 5.1.2; `demo/...tar.xz::mc_task_msgs/msg/RobotCommand.msg` |
| Ruedas | velocidad por joints; API `cc.api.motion.cmd_vel` con timeout de 2 s | manual SDK 6.2.6.1; `demo/...tar.xz::pub_wheel_command_velocity.cpp:1-42` |
| Pinzas PGC | `/ecat/{left,right}_grip/{cmd,state}` | manual SDK 5.10.1–5.10.2 |
| Navegación | skill `A000002 NavTo`; `pose` o `targetId`; track nav opcional | manual SDK 6.2.1.5 |
| Mapas/localización | `cc.api.map.*`, `A000012 SetMap`, `A000013 Relocation` | manual SDK 6.2.1.5 y 6.2.5 |
| RGBD | color/depth/CameraInfo en cámaras chasis/cintura | manual SDK 5.3 |
| Estéreo | left/right, depth info y `/sensor/camera/stereo/pointcloud/raw` | manual SDK 5.4 |
| Lidar | `/sensor/lidar/front`, `/sensor/lidar/back` | manual SDK 5.8 |
| Alto nivel | `ubt_robot` C++/Python ↔ ControlCenter TCP 51000 | manual SDK 6.1 |
| VLA | action `/gr00t/trigger_inference`; topic `/vla_inference_result` | `gr00t_inference.py:103-120` |
| Faults | `cc.api.fault.current.get/subscribe/update` | manual SDK 6.1.2 |

### 3.4 Navegación, percepción y manipulación

La navegación offline configura FreePNC, task manager, recharge, percepción 2D, localización 3D, mapping 2D y VSLAM, con mapas persistidos en `/etc/walker/map`. Esto confirma componentes instalables, no precisión o readiness sin configuración por planta. Evidencia: `vision/.metafiles/nav.metafile.yml:3-91`.

La visión configura cámaras RGB, Orbbec waist/chassis, lidars, AprilTag, calibración, RealSense opcional y un `box_pose_estimator_node` GPU. No se encontró el contrato de salida del estimador 6D ni una conexión desde éste al VLA. Evidencias: `vision/.metafiles/drivers.metafile.yml:15-75`; `box_pose_estimation.metafile.yml:1-12`; `gr00t_inference.py:24-120`.

El SDK proporciona FK e IK por brazo mediante `CalcEndPose` y `CalcJointAnglesForEndPose`, pero no se encontró control cartesiano, planning scene o planificador con colisiones. El URDF tiene geometrías de colisión, aunque carece de transmission/ros2_control y algunos límites no son utilizables como safety limits. Evidencias: manual SDK 5.11; `SDK/URDF/cruzr_s2_description.zip::cruzr_s2_description/urdf/cruzr_s2_v1/cruzr_s2_v1.urdf`.

### 3.5 Despliegue, logs y diagnóstico

uDoke usa `network_mode: host`, CycloneDDS y volúmenes comunes entre placas; los servicios relevantes suelen tener `restart: always`. Hay ROSA log directories, Loglect/log-agent, Loki, Netdata y self-check. Evidencias: `motion/metafile.yml:1-24`; `vision/metafile.yml:1-23`; `motion/.metafiles/monitor.metafile.yml:1-23`; `vision/.metafiles/system.metafile.yml:92-120`.

El tutorial VLA no usa esa gestión: carga dos imágenes, monta código/pesos y requiere varios shells para iniciar motion controller, cambiar a `sdk_controller`, arrancar ejecutor e inferencia. Evidencia: manual SDK sección 7.3.3–7.3.4.

## 4. Compatibilidad y requisitos

### 4.1 Matriz técnica observada

| Componente | Plataforma / versiones observadas | Estado |
|---|---|---|
| Sistema robot | Ubuntu 22.04; ROS 2 Humble; ROSA 2.0 | Documentado para x86 y Orin |
| SDK Python | CPython 3.10; `ubt_robot` 1.0.9; aarch64 y x86_64 | Entregado; el manual muestra por error 1.0.0 |
| SDK C++ | C++17/colcon; bibliotecas estáticas aarch64 y x86_64 | Entregado; manual contradice disponibilidad x86 |
| motion base | amd64, integración v0.2.0; ROSA 22.04-v2.2.7 | Imagen offline incluida |
| vision base | arm64, CUDA 12.2.12, cuDNN 8.9.4.25, TensorRT 8.6.2.3 | Imagen offline incluida |
| VLA control | amd64, Ubuntu 22.04, usuario `ubt` | Docker save incluido |
| VLA inferencia | arm64, Ubuntu 22.04, CUDA 12.6.3, cuDNN 9.3.0, Python 3.10, PyTorch 2.6.0 | Docker save incluido |
| Modelo | NVIDIA GR00T N1.5, 20-D, horizonte 10, bfloat16 | Pesos incluidos |

Evidencias: manual SDK secciones 3.3–3.4; `SDK/python/ubt_api_tiny_python.0624.tar.xz`; `SDK/c++/ubt_api_tiny_colcon.0624.tar.xz`; configuraciones internas de `images/{motion,vision}.tar` y `docker_images/*.tar`; `weight/checkpoint-40000/config.json:2-63`.

### 4.2 Riesgos de reproducción

- **CUDA/JetPack:** el host/integración vision declara CUDA 12.2, mientras el contenedor VLA fue construido con CUDA 12.6.3. La compatibilidad depende del driver/JetPack host y no está declarada. Evidencias: config interna de `images/vision.tar`; historial interno de `docker_images/vla_inference_node_sdk.tar`.
- **Entorno no fijado:** el historial VLA clona `NVIDIA/Isaac-GR00T`, relaja `==` a `>=` e instala dependencias; no se encontró Dockerfile, commit o lockfile entregado. Evidencia: historial interno de `docker_images/vla_inference_node_sdk.tar`.
- **Base externa de entrenamiento:** `gr00t_finetune.py` usa por defecto `nvidia/GR00T-N1.5-3B`; el checkpoint entrenado sí está, pero reentrenar desde base limpia puede requerir recursos externos no incluidos. Evidencia: `gr00t_finetune.py:69-83,260-267`.
- **GPU de entrenamiento:** se exige CUDA y se admite `torchrun`, pero no se especifican GPU, VRAM o tiempo. Evidencia: `gr00t_finetune.py:344-459`.
- **Artefactos mezclados:** `codes`/`codes-S2` incorporan source/build/install/log, objetos, `.so`, `.pyc` y vendor `vision_opencv`, sin receta de build limpia o CI propio. Evidencia: árboles `cruzrss2_vla_pack-002/codes*`.
- **Offline parcial:** el paquete grande contiene imágenes, pero SOP/historiales también referencian registries, URLs y recursos externos; debe probarse con red desconectada. Evidencias: `SDK/Upgrade package/离线包升级SOP.pdf`; `vision/.metafiles/system.metafile.yml:47-70`; historiales de contenedor.
- **Integridad:** no se encontraron hashes, firmas o SBOM. Evidencia: ausencia de archivos checksum/signature en las tres carpetas.

### 4.3 Red y variables

El robot usa una red interna `192.168.11.0/24`, SSH alternativo y ControlCenter 51000; motion y vision limitan ROSA a interfaces concretas y se descubren mutuamente con CycloneDDS. Se requieren al menos `HW_TYPE`, `MC_SCENE`, `TELE_DEVICE`, `CR_BASE_URL` y opciones de transmisión. Evidencias: manual SDK 3.1/3.3; `motion/metafile.yml:8-20`; `motion/.metafiles/motion.metafile.yml:5-12`; `vision/metafile.yml:7-19`; `vision/.metafiles/system.metafile.yml:71-83`.

## 5. Matriz de capacidades

La matriz exhaustiva y procesable está en `SDK_CAPABILITY_MATRIX.csv`. Los puntos decisivos son:

| Área | Disponible o configurable | Parcial / por desarrollar | No demostrado |
|---|---|---|---|
| Base | velocidad, maps, NavTo, relocation, stacks de mapping/nav/recharge | precisión, obstacle avoidance cuantificado, docking API, parada segura | transporte cargado integrado con brazos |
| Brazos | joints, estado, FK/IK, control bimanual articular | interpolación, límites, F/T | cartesiano, compliance, collision planning, payload por brazo |
| Efector | PGC command/status/fuerza; manos v3/v4 | detección grip/drop sin integrar | clamp del VLA y agarre de caja sin asas |
| Visión | RGB, depth, pointcloud, CameraInfo, extrínsecos, TF | pose 6D cerrada/configurable | grasp point, segmentación y tracking integrados |
| Manipulación | demo VLA pick/place de estante | levantar/agarrar bimanual bajo condiciones del demo | pallet, transporte, volcado, recovery, repetibilidad |
| Aprendizaje | teleop documentada, record/play/edit, dataset, checkpoint, fine-tune | pipeline de demostración incompleto | GPU/VRAM y evaluación oficial |
| Industrial | TCP API y rosbridge | REST genérico/map HTTP | PLC, I/O, OPC UA, Modbus, safety cell |
| Operación | containers, logs, monitor, diagnostics, update | autoarranque VLA/recovery | rollback, firmas/SBOM y licencias globales |

Evidencias detalladas, por fila, se encuentran en `SDK_CAPABILITY_MATRIX.csv`.

## 6. Análisis del ciclo de cajas de La Palma

### 6.1 Descomposición paso a paso

| Paso | Interfaz/evidencia | Proveedor | Estado | Dependencias, carencias y hardware | Riesgos y prueba necesaria |
|---|---|---|---|---|---|
| 1. Ir al palé | `A000002 NavTo`, targetId/pose; FreePNC/nav/localize | SDK + uDoke | Configurable | mapa, waypoint, lidar/cámaras; falta precisión con carga | FAT de 100 llegadas XY/yaw, obstáculos y relocalización; manual SDK 6.2.1.5, `nav.metafile.yml:3-58` |
| 2. Detectar/localizar caja | RGBD/pointcloud; `box_pose_estimator_node` | SDK + uDoke | Parcial | modelo/config correcto, iluminación, pallet/oclusiones; salida no documentada | medir pose 6D vs metrología; `box_pose_estimation.metafile.yml:1-12`, manual SDK 5.3–5.4 |
| 3. Calcular pregrasp | FK/IK por brazo | SDK | Desarrollo propio | TCP/hand-eye, grasp planner y collision scene | probar workspace/singularidades/colisión; manual SDK 5.11 |
| 4. Agarrar bimanualmente | joints ambos brazos; PGC topics separados; dataset VLA | SDK + VLA | Parcial | efector exacto, geometría caja/asa, sincronía y control de fuerza | medir fuerza/reparto/slip; `meta/info.json:86-112`, manual SDK 5.10 |
| 5. Levantar | tareas VLA pick lower/middle | VLA | Parcial | peso/CoG desconocidos; lifter descartado por ejecutor S2 | ensayo incremental con lastre y fixture; `meta/tasks.jsonl:1-4`, `executor_node_sdk.py:288-295` |
| 6. Transportar sosteniendo | NavTo existe, VLA no manda ruedas | SDK/uDoke | Desarrollo propio | safety scanner, límites base con carga, supervisor base-brazos | estabilidad/frenado/obstáculo/deslizamiento; `meta/info.json:86-112` |
| 7. Alinear con cinta | NavTo + visión general | SDK/uDoke | Desarrollo propio | pose exacta de cinta, posiblemente marcador/fixture | error de deposición, contacto; probar tolerancias y recuperación |
| 8. Inclinar/vaciar | control articular/F-T disponibles | SDK | No implementado | trayectoria, caja/efector, CoG variable, contención de producto | cálculo dinámico y ensayos de derrame/atasco; no hay tarea equivalente en `tasks.jsonl:1-4` |
| 9. Depositar caja vacía en otro palé | VLA place sólo estante; NavTo | VLA/SDK | Desarrollo propio | pallet detection, patrón de stacking, caja deformada | precisión y estabilidad de pila; no hay pallet model/task |
| 10. Verificar/repetir/recuperar | GripStatus tiene `dropped`; faults/self-check | SDK/uDoke | Parcial | state machine, cycle handshake, retries y safe stop | inyectar fallos; el action VLA puede reportar éxito falso `gr00t_inference.py:240-251,345-380` |

### 6.2 Caja, payload y efector

**Dimensiones demostradas:** el tutorial sólo alinea el demo con una caja de **60 × 40 × 22 cm**, situada sobre plataforma de **1 m**. Esto no es un máximo geométrico ni una especificación de rango. Evidencia: manual SDK sección 7.3.1.

**Peso:** el único dato es **15 kg máximo con ambos brazos**; el peso del demo y el payload por brazo no aparecen. Antes de un go/no-go hacen falta masa máxima/mínima, distribución, CoG, rigidez, coeficiente de fricción, contenido y dinámica del cliente. Evidencia: manual SDK especificaciones; ausencia en dataset/config.

**Uno o dos brazos:** para una caja de 600 mm y el demo `clamp`, la evidencia apunta a bimanual, pero no prueba cómo se genera la fuerza de cierre. La PGC de 50 mm podría agarrar un asa o adaptador, no la anchura total; agarrar una caja sin asas requerirá placas opuestas, dedos a medida, vacío u otro tooling. Evidencias: manual SDK 5.10/7.1/7.3; `s2_vla_pick_large_teleop_ready.xml:5-16`; `meta/info.json:86-112`.

**Volcado:** es técnicamente concebible con 7 DoF por brazo, waist y F/T, pero no hay evidencia de trayectoria, control de fuerza, payload dinámico o estabilidad. Debe tratarse como función nueva y de alto riesgo, no extensión menor. Evidencias disponibles: manual SDK 1.2, 5.1 y 5.11; ausencia de tareas de volcado en `meta/tasks.jsonl:1-4`.

### 6.3 Precisión, estabilidad y coordinación

No hay especificación de precisión de navegación, repetibilidad articular/cartesiana, error de pose 6D ni precisión de deposición. Sin una cadena de tolerancias base → cámara/TF → pose → IK → TCP no puede juzgarse el pick autónomo. Evidencias: manual SDK aporta interfaces/extrínsecos, no métricas; `box_pose_estimation.metafile.yml:1-12`.

El robot es una base móvil de 188 kg con pendiente máxima documentada de 5°; no hay diagrama de estabilidad, límite de aceleración con brazos extendidos ni envelope de carga. No debe moverse cargado hasta recibir límites UBTECH y validarlos con un safety rig. Evidencia: manual SDK especificación general y tabla de joints.

La coordinación existente es sólo comunicación ROS 2 entre módulos. No se encontró un controlador coordinado base+brazos, interlock de estabilidad o planificación whole-body. El VLA controla brazos y bloquea head/waist en el ejecutor; descarta lifter y nunca manda ruedas. Evidencias: `executor_node_sdk.py:37-65,210-248,288-295`; `meta/info.json:86-112`.

### 6.4 Ejemplos encontrados

- **VLA box pick/place:** sí, tutorial, 500 episodios y checkpoint. Evidencias: manual SDK 7.3; `meta/tasks.jsonl:1-4`; `weight/checkpoint-40000`.
- **Lifting box / box lifting:** relacionado por la tarea “Pick up”, pero no existe un test formal llamado así ni métricas de lifting. Evidencia: nombres del dataset y tareas.
- **Bimanual:** implícito/confirmado en acciones simultáneas de dos brazos; no se encontró skill nominal `bimanual`. Evidencia: `meta/info.json:91-105`.
- **Pallet:** no encontrado como modelo, task o pipeline.
- **Grasp:** estado de pinza y compresión articular disponibles, pero no grasp planner/localizador de punto de agarre.

### 6.5 Dictamen específico

El paquete reduce significativamente el trabajo para un **proof of concept de pick/place bimanual en una escena similar al demo**, condicionado a recibir el clamp correcto y resolver defectos del runtime. No demuestra el ciclo pallet–cinta–pallet, sobre todo transporte cargado, vaciado, seguridad y fiabilidad. La viabilidad comercial sólo puede decidirse tras respuestas P0, inspección del robot y una prueba “lifting box process testing” con caja/contenido reales.

## 7. Métodos de programación y entrenamiento

1. **¿Se programa mediante posiciones y trayectorias? Sí.** Hay `RobotCommand/JointCmd`, IK y record/player/editor; el VLA genera posiciones por chunks e interpola. Evidencias: manual SDK 5.1, 5.11, 7.1.2; `executor_node_sdk.py:168-248,272-376`.
2. **¿Existe teaching o guiado manual? Parcial.** Hay teaching de puntos de mapa y reproducción de motions, pero no se encontró hand-guiding/gravity compensation de brazos. Evidencias: `SDK/SOP Mapping on Web.docx`; manual SDK 7.1.
3. **¿Existe teleoperación? Sí, requiere configuración/hardware.** El manual soporta Pico/VR, Xsens y exoesqueleto en combinaciones de efector; uDoke configura VRPN y `rtm_receiver`. Evidencias: manual SDK 7.1; `motion/.metafiles/motion.metafile.yml:31-45`.
4. **¿Existe aprendizaje por demostración? Parcial.** Hay grabación/reproducción/edición, dataset LeRobot y fine-tune, pero no se entrega el conversor `.motion`→LeRobot ni pipeline de etiquetado/sincronización. Evidencias: manual SDK 7.1.2; `data/.../meta/info.json`; `gr00t_finetune.py`.
5. **¿Chaleco/exoesqueleto/guantes/mocap?** Se mencionan VR/Pico/Xsens/exoskeleton; no se encontró soporte nominal de guantes ni hardware/licencias entregados. Evidencia: manual SDK 7.1.2.
6. **¿Qué es exactamente `cruzrss2_vla_pack`?** Un kit de laboratorio para fine-tuning/inferencia GR00T N1.5 aplicado a pick/place de caja: dataset, checkpoint, código ROS 2, mensajes, poses preparatorias y dos imágenes de runtime. Evidencia: árbol `cruzrss2_vla_pack-002`.
7. **¿Incluye modelos entrenados? Sí.** Checkpoint 40000 con dos shards Safetensors y configuración GR00T. Evidencia: `weight/checkpoint-40000`.
8. **¿Incluye datasets? Sí.** 500 episodios LeRobot/500 vídeos; sólo train. Evidencia: `meta/info.json:2-44`.
9. **¿Entrena o sólo infiere? Ambos.** `gr00t_finetune.py` crea `TrainRunner`; `model_interface_general_ros2.py` carga `Gr00tPolicy`. Evidencias: `gr00t_finetune.py:194-267,357-404`; `model_interface_general_ros2.py:36-68`.
10. **¿Qué GPU requiere?** Inferencia: Orin con CUDA, arch 8.7, imagen arm64. Entrenamiento: CUDA, una o varias GPU; modelo/VRAM exactos no documentados. Evidencias: historial de `docker_images/vla_inference_node_sdk.tar`; `gr00t_finetune.py:419-459`.
11. **¿Robot o servidor externo?** Inferencia prevista en Orin y ejecución en x86 del robot. Fine-tune razonablemente requiere servidor GPU externo, aunque el script no lo impone. El API de ControlCenter puede ejecutarse en robot o PC externo. Evidencias: manual SDK 3.1/6.1/7.3.4; `model_interface_general_ros2.py:61-68`.
12. **¿Documentado o experimental?** Topics/API base, teleop y pasos manuales están documentados. VLA parece experimental: contenedores `latest`, arranque manual, variantes duplicadas, semántica de error defectuosa, configs contradictorias y ausencia de pruebas. Evidencias: manual SDK 7.3; `codes` vs `codes-S2`; `gr00t_inference.py:240-251,345-380`.

## 8. Integración industrial

### 8.1 Disponibilidad

ControlCenter ofrece TCP bidireccional en 51000 con SDK C++/Python y skills; rosbridge websocket está configurado; existe map HTTP/MQTT interno en la plataforma. Evidencias: manual SDK 6.1; `vision/.metafiles/system.metafile.yml:47-89`; `vision/.metafiles/web.metafile.yml:18-29`.

No se encontraron entradas/salidas digitales de usuario, PLC, OPC UA, Modbus, Profinet, EtherNet/IP o state machine de célula. EtherCAT es interno del robot y no sustituye una interfaz de máquina. Por tanto los casos de nidos semiautomáticos requieren un gateway/PLC externo y desarrollo de handshake. Evidencias: `motion/.metafiles/motion.metafile.yml:13-29`; ausencia de protocolos industriales en los tres paquetes.

### 8.2 Propuesta de integración

```text
PLC/safety PLC de célula
  ├─ señales seguras: E-stop, puertas, scanners, STO/safe stop
  ├─ señales de proceso: ready, request, clamp, cycle_start, done, fault
  └─ gateway no-safety TCP/ROS 2 ↔ orquestador Cruzr
                              ├─ NavTo / map / faults
                              ├─ percepción y manipulación
                              └─ trazabilidad/OEE/logs
```

El accionamiento físico de un pulsador sólo debería evaluarse si la máquina no ofrece interfaz eléctrica, con tooling y evaluación de riesgo propios. No hay ejemplo suministrado. Para nidos, además se necesitan pose del nest, inserción cartesiana/compliance, force limits, handshake y recuperación; esas capacidades no están listas en el material.

## 9. Seguridad y operación

### 9.1 Seguridad funcional y movimiento

El manual exige zona libre, no tocar durante movimiento y E-stop posterior. En developer/SDK mode advierte que el control interno sale y el desarrollador asume todos los joints; desaconseja real-time desde Orin/PC externo. Evidencia: manual SDK secciones 2.1–2.5 y 3.1.2.

El ejecutor VLA comprueba sólo una velocidad global de 6.28 rad/s. No valida posición, aceleración, jerk, esfuerzo, F/T, payload o colisión; tampoco observa E-stop/fault topics. Además calcula seguridad sobre 9 s/900 puntos, pero publica 900 puntos a 200 Hz, aproximadamente 4.5 s, por lo que la velocidad real inferida puede ser el doble de la usada en el check. Evidencia: `executor_node_sdk.py:42,88-100,135-166,296-376`. Esta discrepancia debe corregirse antes de mover el robot.

La parada/cancelación del action sólo solicita terminar después de la inferencia actual; no es una función de seguridad. Evidencia: `gr00t_inference.py:190-194,312-380`. La célula requerirá análisis de riesgos, safety PLC, E-stops accesibles, scanners/fencing/interlocks, límites seguros y validación conforme a normativa aplicable; nada de ello puede sustituirse por ROS 2 o VLA.

### 9.2 Ciberseguridad

- Hay credenciales estáticas en el manual SDK, en `SDK/SOP Mapping on Web.docx` y en `SDK/Upgrade package/离线包升级SOP.pdf`. No se reproducen sus valores; deben rotarse antes de conectar el robot.
- El ControlCenter permite actualmente token vacío y `api_id` arbitrario; un segundo cliente con igual ID expulsa al primero. Evidencia: manual SDK sección 6.1.1.2–6.1.1.3.
- ControlCenter/rosbridge/web usan host network/puertos; el web backend y `backend_service` montan `/root/.ssh`. Evidencias: `vision/.metafiles/system.metafile.yml:28-33,71-86`; `vision/.metafiles/web.metafile.yml:1-29`.
- Self-check y Netdata montan Docker socket; Netdata obtiene `SYS_ADMIN`, `SYS_PTRACE`, apparmor unconfined y visibilidad read-only del host. Evidencias: `motion/.metafiles/monitor.metafile.yml:1-23`; `vision/.metafiles/system.metafile.yml:92-120`.
- `shells/cmd_proxy.sh` instala como root un daemon que ejecuta mediante `eval` lo escrito en un FIFO. Aunque no aparece en `replace.json`, debe bloquearse o eliminarse salvo justificación formal. Evidencia: `utars-udoke-config-v0.2.0_offline-001/shells/cmd_proxy.sh:1-183`, especialmente `:63-74`.
- La imagen VLA contiene variables de entorno de publicación/credenciales; los valores se han redactado y deben revocarse si son reales. Evidencia: configuración interna de `docker_images/vla_inference_node_sdk.tar`.
- No se encontraron claves privadas visibles por nombre/contenido en los árboles no comprimidos, pero eso no sustituye un secret scan completo de layers/SBOM.

### 9.3 Scripts y actualización

`replace.json` ordena scripts que modifican servicios, kernel RT/GRUB, NTP, GPU, IRQ, CAN, Wi-Fi y TF. `trim_service.sh` enmascara servicios de actualización y mantenimiento; `auto_load_vla_scripts_new.sh` puede borrar una carpeta de configuración de manipulation tras confirmación. Ninguno fue ejecutado. Evidencias: `utars-udoke-config-v0.2.0_offline-001/replace.json:2-37`; `shells/trim_service.sh:147-244`; `cruzrss2_vla_pack-002/codes-S2/motion/s2_vla_scripts/auto_load_vla_scripts_new.sh:86-134`.

Existe proceso de actualización uDoke y OTA declarado, pero no rollback, firma o restore. Antes de instalar debe clonarse el almacenamiento o seguir un procedimiento oficial UBTECH probado. Evidencias: manual SDK especificación/SOP; `debs/upgrade.json:1-9`; ausencia de rollback/checksums.

### 9.4 Licencias

Los scripts NVIDIA/GR00T y paquetes de mensajes declaran Apache-2.0; `vision_opencv` aporta Apache/BSD. No se encontró licencia global para SDK propietario, librerías estáticas/wheels, dataset, checkpoint, imágenes, modelos nav/pose o USD/URDF. Evidencias: `cruzrss2_vla_pack-002/gr00t_finetune.py:1-14`; `codes-S2/vision/rosa_vla_additional/vla-onboard/src/*/package.xml`; ausencia de `LICENSE` superior. Se requieren derechos escritos antes de una entrega comercial.

## 10. Limitaciones de lo recibido

1. Sin robot no se validaron ABI, topics reales, QoS, latencias, calibración ni movimiento.
2. Los binarios cerrados de las imágenes sólo permiten inferir capacidad por manifests/configuración.
3. No hay BOM homologado, hashes, firmas, SBOM ni CVE report.
4. No hay requisitos de caja real: peso, material, asas, CoG, contenido o caudal de vaciado.
5. No hay performance de navegación, percepción, IK, joints, pinza o VLA.
6. El dataset carece de val/test y contiene al menos un episodio de longitud atípica.
7. No hay safety manual/certificados/circuito de célula.
8. No hay especificación de integración PLC/I/O.
9. No hay simulation stack completo ni CI/test de misión.
10. No hay licencia comercial global.

Evidencias: `SDK_FILE_INVENTORY.md`; `SDK_CAPABILITY_MATRIX.csv`; paths citados en cada sección anterior.

## 11. Riesgos priorizados

| Riesgo | Probabilidad preliminar | Impacto | Mitigación obligatoria |
|---|---|---|---|
| Efector/clamp no coincidente con demo | Alta | Crítico | Confirmar BOM/CAD/TCP y prueba con caja real |
| Payload dinámico/CoG insuficiente | Desconocida | Crítico | Curvas UBTECH + ensayo incremental |
| Colisión/daño por ejecutor VLA | Alta sin cambios | Crítico | Corregir límites/tiempo; collision/safety supervisor |
| Action ejecuta tarea equivocada o éxito falso | Alta | Alto | Corregir IDs y semántica; tests automatizados |
| Navegación/pose sin precisión suficiente | Desconocida | Alto | Cadena de tolerancias y FAT estadístico |
| Transporte/volcado inestable | Desconocida | Crítico | Diseño dinámico, fixture y validación safety |
| Incompatibilidad CUDA/JetPack | Media | Alto | Matriz homologada y smoke test offline |
| Ciberseguridad/credenciales/privilegios | Alta en baseline | Alto | Rotación, segmentación, hardening, eliminar proxy |
| Actualización sin rollback/integridad | Media | Alto | Imagen de recuperación, firmas, ensayo en clon |
| Licencias insuficientes | Alta hasta contrato | Alto | Grant escrito y lista de entitlements |

Las probabilidades son inferencias [B] basadas en el contenido; deben recalibrarse tras respuestas UBTECH y pruebas.

## 12. Pruebas recomendadas cuando llegue el robot

### Fase 0 — recepción, sin movimiento

1. Fotografiar/registrar número de serie, efector, placas, versiones, `HW_TYPE`, firmware, imagen, driver/JetPack y hashes.
2. Rotar credenciales; aislar la red; inventariar puertos/servicios y deshabilitar componentes no autorizados.
3. Verificar E-stop, liberación, corte/retención de energía, recuperación y estados de fault con brazos soportados.
4. Comparar lista/tipo/QoS/frecuencia de topics/services/actions con documentación.

### Fase 1 — banco seguro, sin carga

5. Validar signos/cero/límites por joint a baja velocidad; nunca iniciar con el ejecutor VLA.
6. Medir latencia y pérdida entre Orin/x86 para `/mc/sdk/robot_state`, imágenes, chunks y commands.
7. Validar URDF↔robot, FK↔medición, IK, singularidades, self-collision y TCP.
8. Calibrar CameraInfo, extrínsecos, hand-eye, TCP y F/T; registrar incertidumbre.
9. Probar PGC/mano/clamp: homing, fuerza real, estado grip/drop, pérdida de energía y objetos patrón.

### Fase 2 — base y percepción

10. Crear mapa; ejecutar ≥100 NavTo por estación con error XY/yaw, obstáculos dinámicos, relocalización y docking.
11. Medir pose 6D con cajas reales por distancia, orientación, apilado, oclusión, deformación e iluminación.
12. Construir cadena de tolerancias para comprobar que error total deja margen de grasp.

### Fase 3 — manipulación controlada

13. Implementar primero una secuencia explícita IK/trajectory/gripper, con speed/acceleration/effort/F-T limits, collision checking y safe stop.
14. Probar bimanual con caja vacía y lastre incremental, célula vallada, soporte anti-caída y medición F/T/CoG.
15. Validar lift/place sin base; después base con carga a velocidades crecientes y frenadas/obstáculos controlados.
16. Prototipar volcado con caja/contenido inerte, contención y cálculo dinámico; medir residuo/derrames/slip.

### Fase 4 — VLA y misión

17. Corregir IDs, action results, lifter, timing y safety limits; añadir unit/integration tests antes de conectar commands.
18. Ejecutar VLA primero sobre datos grabados, luego shadow mode sin publicar, después robot sin carga y finalmente carga incremental.
19. Añadir supervisor determinista que valide salida VLA y controle pinza, faults, timeout, cancel y recovery.
20. FAT de ≥100 ciclos por variante con success rate, cycle time, precisión, recoveries, incidentes, vídeo/rosbag/logs y configuración/hash.

Evidencias que motivan la secuencia: `gr00t_inference.py:164-380`; `executor_node_sdk.py:88-376`; manual SDK advertencias de developer mode.

## 13. Conclusión de viabilidad

### Caso La Palma

**Valoración: todavía indeterminable.**

- **A favor [A]:** plataforma móvil/navegación, sensores, dos brazos, F/T, IK, API de pinza, teleop, dataset/checkpoint y demo VLA de caja están presentes.
- **En contra [A]:** no hay peso de demo/payload por brazo, efector exacto, precisión, planificación de colisión, control de fuerza integrado, transporte cargado, pallet, volcado, recovery, safety cell ni métricas de éxito.
- **Inferencia [B]:** un PoC de pick/place bimanual en condiciones controladas parece alcanzable con soporte UBTECH y desarrollo propio sustancial. La operación industrial autónoma completa no puede aprobarse con la evidencia actual.

### Casos EE. UU./Polonia

La recogida/deposición de piezas es conceptualmente programable, pero la inserción en nidos exige más precisión, control cartesiano/compliance y calibración que el caso de caja. El accionamiento y handshake de máquinas requiere PLC/I/O/gateway no suministrado; la seguridad y normativa deben diseñarse por célula. Viabilidad igualmente indeterminable hasta conocer pieza, tolerancia, máquina e interfaz.

## 14. Próximos pasos priorizados

1. **P0 — Enviar las 15 preguntas prioritarias** de `UBTECH_OPEN_QUESTIONS.md` y exigir respuestas documentadas.
2. **P0 — Solicitar “lifting box process testing” presenciado** con caja/contenido reales, transporte y volcado; no aceptar sólo el demo de estante.
3. **P0 — Congelar BOM/software homologado** por número de serie, con hashes, licencias, JetPack/driver y árbol VLA canónico.
4. **P0 — Cerrar requisitos físicos:** dimensiones, masa, CoG, rigidez, asas, contenido, caudal, palés, cinta, ciclo, disponibilidad y entorno.
5. **P0 — Seleccionar efector** tras CAD/payload/pruebas: clamp/placas, PGC con asas, vacío o tooling a medida.
6. **P0 — Realizar risk assessment y arquitectura safety/OT** antes de cualquier demo con movimiento autónomo.
7. **P1 — Corregir/hardening del VLA:** IDs, resultados, lifter, límites por joint, timing, F/T, colisión, watchdog y tests.
8. **P1 — Diseñar baseline determinista** de navegación + pose + IK/planning + grip + supervisor; usar VLA sólo donde aporte valor medible.
9. **P1 — Construir test cell/simulador**, cadena de calibración y sistema de captura de datos/val/test.
10. **P1 — Definir integración industrial** mediante PLC/gateway, handshakes y logging, separando control funcional de seguridad.
11. **P2 — Industrializar despliegue:** imagen inmutable, arranque uDoke, healthchecks, backup/rollback, observabilidad y gestión de modelos.
12. **P2 — FAT/SAT contractual** con métricas, configuración firmada y criterios go/no-go.

## Entregables relacionados

- Inventario resumido: `SDK_FILE_INVENTORY.md`
- Matriz exhaustiva: `SDK_CAPABILITY_MATRIX.csv`
- Preguntas concretas a UBTECH: `UBTECH_OPEN_QUESTIONS.md`
