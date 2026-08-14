# Inventario técnico de los paquetes Cruzr S2

Fecha de inspección: 2026-08-06<br>
Workspace: `/home/lacuna/proyectos/Robots/Humanoide`<br>
Método: inspección estática local. No se instalaron paquetes, no se cargaron contenedores, no se ejecutaron scripts o binarios y no se realizaron conexiones de red.

## Nota sobre el nombre del paquete VLA

La solicitud denomina al segundo paquete `cruzrs2_vla_pack-002`; la carpeta realmente presente es `cruzrss2_vla_pack-002` (doble `ss`). Todas las referencias de este inventario usan el nombre existente.

## Resumen cuantitativo

| Paquete | Tamaño aparente | Archivos | Directorios | Finalidad probable |
|---|---:|---:|---:|---|
| `Cruzr S2-20260803T070710Z-1-003` | 298.15 MB (285 MiB) | 12 | 9 | SDK externo, documentación, modelos geométricos, ejemplos, bibliotecas cliente y SOP de actualización |
| `cruzrss2_vla_pack-002` | 74.02 GB (69 GiB) | 16,167 | 3,047 | Demo de manipulación de cajas mediante NVIDIA Isaac GR00T N1.5: código ROS 2, dataset, checkpoint e imágenes de ejecución |
| `utars-udoke-config-v0.2.0_offline-001` | 35.69 GB (34 GiB) | 42 | 8 | Distribución offline del sistema Cruzr S2 v0.2.0 para las placas motion x86 y vision Orin |

Los tamaños y recuentos se obtuvieron sobre las carpetas exactas anteriores; no se cuentan los cuatro entregables creados por esta auditoría.

## 1. Paquete SDK

Ruta: `Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK`

### Estructura y archivos relevantes

| Elemento | Tamaño | Fecha encontrada | Contenido / utilidad |
|---|---:|---|---|
| `Cruzr S2 优必选SDK二次开发文档【对外】6.24.pdf` | 8.37 MB | 2026-06-24 | Manual externo v2.1; hardware, seguridad, ROS 2, topics, API, teleoperación y tutorial VLA |
| `Cruzr S2 优必选SDK二次开发文档【对外】6.24.docx` | 16.32 MB | 2026-06-24 | Fuente editable del mismo manual |
| `SOP Mapping on Web.docx` | 0.77 MB | 2026-05-08 | Flujo de creación de mapas y edición de puntos mediante web |
| `demo/Cruzer_S2-low-level-demo0624.tar.xz` | 11.95 KB | 2026-06-24 | Workspace ROS 2 C++ mínimo con mensajes y ejemplos de articulaciones, ruedas, sensores, cámaras, pinzas y audio |
| `c++/ubt_api_tiny_colcon.0624.tar.xz` | 8.47 MB | 2026-06-24 | SDK cliente C++ del ControlCenter: headers, nueve ejemplos y bibliotecas estáticas aarch64/x86_64 |
| `python/ubt_api_tiny_python.0624.tar.xz` | 7.04 MB | 2026-06-24 | Wheels CPython 3.10 `ubt_robot` 1.0.9 para aarch64/x86_64 y nueve ejemplos |
| `URDF/cruzr_s2_description.zip` | 19.23 MB | 2026-06-02 | Paquete ROS 2 de descripción: URDF, launch de visualización, RViz y mallas STL |
| `USD/Collected_cruzr_s2_v1.zip` | 184.67 MB | 2026-06-25 | USD del robot completo, sub-USDes, materiales y texturas |
| `USD/Collected_hand_v3_usd.zip` | 11.41 MB | 2026-06-25 | USD físico/visual/sensor de manos v3 izquierda y derecha |
| `Upgrade package/utars-udoke-config-v0.2.0.tar.gz` | 41.30 MB | 2026-06-19 | Configuración y paquetes uDoke, sin las imágenes offline grandes; 47 entradas |
| `Upgrade package/离线包升级SOP.pdf` | 0.56 MB | 2026-06-16 | SOP de actualización “offline” |
| `Upgrade package/images.sh` | 876 B | 2026-06-23 | Automatiza transferencia/carga de imágenes; requiere red y no fue ejecutado |

### Interfaces presentes en el demo comprimido

El archivo `demo/Cruzer_S2-low-level-demo0624.tar.xz` contiene siete paquetes de mensajes/ejemplo ROS 2 y fuentes C++ para:

- `/mc/sdk/robot_state` y `/mc/sdk/robot_command`;
- control de brazos, cabeza, lifter y ruedas;
- `GripCmd`/`GripStatus` para pinzas PGC-140-50;
- manos, batería, power board, IMU y fuerza/par;
- RGBD de chasis/cintura, estéreo/fisheye y lidar delantero/trasero;
- TTS y audio.

Evidencia concreta del control de ruedas: `Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/demo/Cruzer_S2-low-level-demo0624.tar.xz::Cruzer_S2/example/src/cruzr_s2/low_level/pub_wheel_command_velocity.cpp:1-42`.

### Modelo geométrico

`URDF/cruzr_s2_description.zip::cruzr_s2_description/urdf/cruzr_s2_v1/cruzr_s2_v1.urdf` contiene 51 joints, 52 bloques inerciales y 46 colisiones. Incluye límites para 27 joints, pinzas PGC y links de los dos sensores de seis ejes, pero no contiene `<transmission>`, `<ros2_control>` ni `<sensor>`. Los límites del lifter tienen esfuerzo y velocidad cero y los de las ruedas usan valores genéricos muy altos; por tanto no debe usarse sin depuración como configuración de seguridad o planificación.

### Versiones y contradicciones

- Manual SDK v2.1, revisión 2026-06-23; revisiones previas v1.0 y v2.0: `Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/Cruzr S2 优必选SDK二次开发文档【对外】6.24.pdf`.
- Ubuntu 22.04 y ROS 2 Humble en x86 y Orin, más ROSA 2.0: mismo PDF.
- El manual muestra instalación de wheel Python 1.0.0, pero se entregan wheels 1.0.9.
- El manual dice que la biblioteca x86_64 está “todavía no abierta”; el tar C++ sí contiene `lib/x86_64/*.a`.
- No se encontró licencia global del SDK ni condiciones de redistribución. El copyright de ejemplos no sustituye una licencia contractual.

## 2. Paquete VLA

Ruta: `cruzrss2_vla_pack-002`

### Distribución por volumen

| Subárbol | Tamaño aproximado | Contenido |
|---|---:|---|
| `docker_images/` | 52 GiB | Imágenes Docker save de inferencia arm64 y control amd64 |
| `weight/` | 16 GiB | Checkpoint 40000 completo, incluido optimizador de 8.53 GB |
| `data/` | 1.9 GiB | Dataset LeRobot con 500 Parquet y 500 MP4 |
| `codes/` | 118 MiB | Variante Cruzr del runtime y múltiples poses XML |
| `codes-S2/` | 118 MiB | Variante S2 del runtime y una pose XML de preparación |
| raíz | 56 KiB | `data_config.py` y `gr00t_finetune.py` |

### Dataset

Dataset: `data/utars_clamp_and_place_large_box_full_data_bio_lerobot_0319`

- LeRobot codebase v2.1, 500 episodios, 105,207 frames, 500 vídeos, 120 fps y sólo split `train`: `meta/info.json:2-14`.
- Una imagen RGB 576 × 960; no es mapa de profundidad: `meta/info.json:16-44`.
- Estado de 32 dimensiones: 20 joints y 12 medidas de fuerza/par de muñeca: `meta/info.json:46-84`.
- Acción de 20 dimensiones: brazos, cabeza, lifter y cintura; no incluye ruedas, manos ni pinzas: `meta/info.json:86-112`.
- Cuatro tareas: pick/place en estante inferior y medio: `meta/tasks.jsonl:1-4`.
- Distribución: 150 pick inferior, 150 place inferior, 100 pick medio y 100 place medio. Existe al menos un episodio de sólo 9 frames; requiere revisión de calidad.
- No se encontró split de validación/test ni métrica de éxito física.

### Checkpoint y entrenamiento

`weight/checkpoint-40000` contiene:

- dos shards Safetensors de 5.00 GB y 2.58 GB;
- `optimizer.pt` de 8.53 GB, scheduler y RNG para reanudar;
- GR00T N1.5, horizonte 10, estado/acción máximo 20, bfloat16 y Transformers 4.51.3: `weight/checkpoint-40000/config.json:2-63`;
- 40,000 pasos y época 6.08; `best_metric` y `best_model_checkpoint` son nulos: `weight/checkpoint-40000/trainer_state.json`.

El entrenamiento está implementado en `gr00t_finetune.py`: carga LeRobot/GR00T, admite una o varias GPU CUDA, ajuste completo o LoRA y ejecuta `TrainRunner`. El modelo base por defecto es el ID externo `nvidia/GR00T-N1.5-3B`: `gr00t_finetune.py:36-127`, `gr00t_finetune.py:194-267`, `gr00t_finetune.py:344-459`. `data_config.py:773-857` define la modalidad UBTECH RGB + joints; `data_config.py:859-939` aporta otra variante de teleoperación que omite lifter y cintura en las acciones.

### Runtime ROS 2

La ruta operativa analizada es `codes-S2`:

- inferencia Orin: `codes-S2/vision/rosa_vla_additional/vla-onboard/src/gr00t_control/gr00t_inference.py`;
- interfaz modelo CUDA: `.../model_interface_general_ros2.py`;
- mensajes ROS 2: `vla_msgs`, `mc_state_msgs`, `mc_task_msgs`, `shm_msgs`;
- ejecución x86: `codes-S2/motion/rosa_vla_additional/vla-motionx86/src/vla_executor/vla_executor/executor_node_sdk.py`;
- pose previa: `codes-S2/motion/s2_vla_scripts/s2_bio_vla/s2_vla_pick_large_teleop_ready.xml`.

Se entregan árboles `build/`, `install/`, `log/`, bytecode, objetos y bibliotecas compiladas junto a fuentes. Esto explica buena parte de los 16,167 archivos y dificulta distinguir artefactos reproducibles de caché de desarrollo. No se encontró CI del runtime propio ni suite de pruebas de seguridad/misión; los tests visibles fuera del código vendorizado son scripts manuales.

### Duplicados y variantes

`codes` y `codes-S2` son casi duplicados: la comparación estática detecta sólo tres archivos comunes diferentes y seis entradas exclusivas. Las diferencias funcionales importantes son:

- `codes/motion/cruzr_vla_scripts` tiene poses preparatorias para alturas 55/70/85/100/115, pick/place lower/upper y teleop;
- `codes-S2/motion/s2_vla_scripts` sólo tiene la pose `s2_vla_pick_large_teleop_ready.xml`;
- la variante S2 admite lifter ausente en estado sustituyéndolo silenciosamente por cero: `codes-S2/vision/rosa_vla_additional/vla-onboard/src/gr00t_control/gr00t_inference.py:437-468`;
- el ejecutor S2 convierte 20 acciones en 17 conservando índices 0–15 y 19, por lo que descarta las tres acciones de lifter: `codes-S2/motion/rosa_vla_additional/vla-motionx86/src/vla_executor/vla_executor/executor_node_sdk.py:37-43`, `:272-295`.

Debe pedirse a UBTECH cuál es el árbol canónico y qué combinación exacta está validada para el número de serie del robot.

### Imágenes de contenedor

- `docker_images/vla_control_node_sdk.tar`: 18.48 GB, Linux amd64, Ubuntu 22.04, usuario `ubt`, creada 2026-04-24.
- `docker_images/vla_inference_node_sdk.tar`: 37.22 GB, Linux arm64, Ubuntu 22.04, creada 2026-04-24; CUDA 12.6.3, cuDNN 9.3.0, Python 3.10, PyTorch 2.6.0, torchvision 0.21.0, torchaudio 2.6.0, PyTorch3D 0.7.9 y OpenCV 4.11 según su historial de construcción.
- La imagen de inferencia clonó Isaac-GR00T por red sin commit visible, sustituyó restricciones `==` por `>=` e instaló paquetes externos; no hay receta Dockerfile ni lockfile separado que garantice reconstrucción exacta.

### Licencias

Los archivos de entrenamiento y el código GR00T vendorizado declaran Apache-2.0; los paquetes de mensajes también declaran Apache 2.0, y `vision_opencv` incluye Apache/BSD. No hay una licencia de nivel superior que aclare checkpoint, dataset, imágenes Docker, código UBTECH ni derechos de redistribución/comercialización.

## 3. Paquete offline uDoke

Ruta: `utars-udoke-config-v0.2.0_offline-001`

### Archivos principales

| Elemento | Tamaño | Contenido |
|---|---:|---|
| `images/motion.tar` | 6.99 GB | 6 imágenes amd64 para motion |
| `images/vision.tar` | 28.65 GB | 20 imágenes arm64 para vision |
| `debs/udoke_0.8.7_amd64.deb` | 21.57 MB | uDoke 0.8.7 amd64; requiere libc6 >= 2.30 |
| `debs/udoke_0.8.7_arm64.deb` | 19.69 MB | uDoke 0.8.7 arm64; requiere libc6 >= 2.31 |
| `replace.json` | 1.2 KB | Selección de scripts e imágenes por placa |
| `motion/metafile.yml` + 7 `.metafiles` | 40 KB | Stack x86, ROS, control, drivers, logging y monitorización |
| `vision/metafile.yml` + 13 `.metafiles` | 68 KB | Stack Orin: cámaras, navegación, pose 6D, voz, web, sistema y observabilidad |
| `shells/` | 120 KB | 14 scripts de modificación del host |

### Imágenes motion

Las seis tags, obtenidas del `manifest.json` interno de `images/motion.tar`, son:

1. ROS export Humble v0.2.4;
2. Netdata motion v0.2.0;
3. Loglect v0.1.7;
4. ROS 2 workspace Humble dynamic v0.0.114;
5. BusyBox musl;
6. `utars-integration:zs2_motion-v0.2.0`.

La imagen de integración motion es Ubuntu 22.04, amd64, creada 2026-06-19 y etiqueta ROSA `ubuntu22.04-v2.2.7`. Entre sus versiones embebidas constan `chassis_controllers` 0.3.0, `cruzr_s2_odom_estimator` 0.3.0, `manipulation` 0.2.9.12, `sdk_controller` 0.5.1, `t800_hand_controller` 0.8.7 y `t800_mc_server` 0.11.0. Evidencia: configuración JSON interna de `utars-udoke-config-v0.2.0_offline-001/images/motion.tar`.

### Imágenes vision

Las veinte tags de `images/vision.tar` incluyen:

- ASR/TTS/CWW/SV 0.8.8;
- web, backend, calibración y expression web;
- modelo de navegación 0.4.0;
- SRS, vLLM, fakedify;
- log agent, loglect, Loki y Netdata;
- ROS export/ROS 2 Humble;
- `utars-integration:zs2_vision-v0.2.0`.

La imagen de integración vision es Ubuntu 22.04, arm64, creada 2026-06-19, CUDA 12.2.12, cuDNN 8.9.4.25 y TensorRT 8.6.2.3. Sus etiquetas enumeran, entre otros, ControlCenter 0.8.138.2, pose 6D 1.1.4, Orbbec 0.12.1 y módulos FreePNC/VSLAM. Evidencia: configuración JSON interna de `utars-udoke-config-v0.2.0_offline-001/images/vision.tar`.

### Configuraciones funcionales

- motion arranca control EtherCAT/ROSA, `t800_mc_server`, `manipulation_task_manager`, VRPN y `rtm_receiver`; es privilegiado: `motion/.metafiles/motion.metafile.yml:1-52`.
- vision configura RGB, dos Orbbec RGBD, dos lidar, AprilTag, calibración y opcional RealSense: `vision/.metafiles/drivers.metafile.yml:1-75`.
- navegación incluye localización, mapping 2D, VSLAM, percepción, task manager y recarga: `vision/.metafiles/nav.metafile.yml:1-91`.
- pose de caja 6D está configurada con un JSON específico `byd` y `WALKER_PROJECT_ID=walker_s2`: `vision/.metafiles/box_pose_estimation.metafile.yml:1-12`.
- ControlCenter publica 50000/50001/51000/48158 y convive con map manager, MQTT y autocheck: `vision/.metafiles/system.metafile.yml:47-120`.
- rosbridge websocket y web backend están configurados, ambos en red del host; el backend monta `/root/.ssh`: `vision/.metafiles/web.metafile.yml:1-40`.

### Riesgos operativos del instalador

Los scripts no fueron ejecutados. `replace.json:2-37` ordena aplicar cambios de kernel/RT, servicios, frecuencia/potencia GPU, IRQ, NTP, Wi-Fi y TF. `trim_service.sh` enmascara actualizaciones y otros servicios del host. `cmd_proxy.sh:1-183`, aunque no aparece en `replace.json`, instala un servicio root que evalúa comandos recibidos por FIFO (`eval` en la línea 73). El despliegue debe bloquearse hasta contar con procedimiento oficial, backup/rollback y revisión de ciberseguridad.

## Relación entre los tres paquetes

```text
SDK/documentación
  define hardware + topics/mensajes + ControlCenter API + SOP
                 │
                 ├── runtime VLA adicional
                 │     Orin arm64: RGB + joints → GR00T → chunk 20-D
                 │     x86 amd64: chunk → interpolación → /mc/sdk/robot_command
                 │
                 └── distribución uDoke v0.2.0
                       motion x86: drivers/control/manipulation
                       vision Orin: sensores/nav/percepción/CC/web/observabilidad
```

El paquete offline aporta la plataforma base; el SDK expone y documenta interfaces; el VLA es una superposición manual fuera del stack uDoke que se ejecuta en dos contenedores extra. No se encontró manifiesto que integre automáticamente ambos contenedores VLA en uDoke, ni una matriz oficial de compatibilidad entre el sistema v0.2.0 del 19 de junio y las imágenes VLA del 24 de abril.

## Dependencias externas o no cerradas

- robot físico y configuración exacta `HW_TYPE`/efector;
- runtime NVIDIA/driver/JetPack capaz de alojar simultáneamente CUDA 12.2 del sistema y CUDA 12.6.3 del VLA;
- Isaac-GR00T y ecosistema Python/CUDA para reentrenar;
- modelo base `nvidia/GR00T-N1.5-3B` si se parte de cero;
- dispositivo Pico, VR/Xsens/exoesqueleto y software/SOP de teleoperación no incluido;
- servicios/registries internos indicados en SOP e historiales si se intenta reconstruir;
- configuración de mapas/calibración específica de planta;
- hardware de seguridad e integración industrial no contenido en estos paquetes.

## Integridad y trazabilidad

No se encontraron manifiestos SHA-256, firmas, SBOM, CVE report, repositorio Git completo ni release notes globales que permitan verificar integridad y procedencia. Las fechas de los ficheros abarcan 2024–2026, las imágenes VLA preceden al runtime v0.2.0 más reciente y hay nombres `walker_s2`, `utars`, `cruzr`, `cruzr_s2` y `s2` mezclados. Se requiere un BOM y una combinación de versiones homologada por UBTECH.
