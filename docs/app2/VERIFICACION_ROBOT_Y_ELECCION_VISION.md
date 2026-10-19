# app2 — verificación real de Vision y elección de plataforma

**ID:** APP2-VISION-RUNTIME-20261019. Fecha: 19-10-2026, Europe/Madrid.
**Estado:** hardware, runtime y recepción de imágenes VERIFICADOS por lectura.
Modelo app2, inferencia, rendimiento e identificación de referencia PENDIENTES.

## Decisión propuesta

Para el equipo actual, mantener **Roboflow como primera candidata de preparación
de datos y entrenamiento en nube**, descargar un modelo de segmentación y
ejecutarlo mediante **TensorRT 8.6 en Vision**, en un contenedor app2 separado.
Esta elección prioriza facilidad de trabajo con imágenes y exportación; no es
una clasificación de precisión o velocidad entre proveedores.

Primera prueba técnica propuesta: **YOLO11n-seg** exportado a ONNX. Su tamaño
pequeño motiva el punto de partida, pero no demuestra que sea el modelo óptimo.
Comparar RF-DETR de segmentación pequeño si interesa su licencia Apache 2.0 o
si las confusiones/máscaras del primer modelo son insuficientes. La licencia
para desplegar YOLO en un producto cerrado debe resolverse antes de adoptarlo;
pagar entrenamiento en nube no concede por sí solo esa licencia.

Ultralytics Platform es una alternativa válida de entrenamiento/exportación si
se decide trabajar exclusivamente con YOLO. No hay una dependencia de hardware
que obligue a utilizar Roboflow; el artefacto y su ejecutor son lo que debe
validarse contra el robot. El modelo ganador sólo se podrá elegir midiendo
precisión, máscara, latencia y recursos con los datos app2.

## Lo leído en el robot real

Conexión PC → Vision192.168.11.3 por **eno1**, origen192.168.11.250.
No se consultó Motion ni se enviaron órdenes de control.

| Elemento | Lectura real | Alcance de la comprobación |
|---|---|---|
| Placa | NVIDIA Jetson AGX Orin Developer Kit | Device tree: p3737-0000+p3701-0005, tegra234 |
| Arquitectura / CPU | aarch64; 12 CPU lógicas | `uname -m`, `getconf` |
| Sistema | Ubuntu22.04.4; kernel5.15.136-rt-tegra | Host real |
| L4T | 36.3.0 | `/etc/nv_tegra_release` y paquete l4t-core |
| Correspondencia de stack | JetPack6.0 producción | Deducción contrastada con notas NVIDIA de L4T36.3; metapaquete nvidia-jetpack ausente |
| RAM total | 64351128KiB, 61,37GiB; clase64GB | Memoria unificada, no VRAM dedicada libre |
| MemAvailable | ~11,4GiB en dos capturas | Instantánea con servicios activos, no reserva para app2 |
| CUDA runtime | cuda-cudart-12-2,12.2.140-1 | Host y contenedores GPU consultados |
| TensorRT | libnvinfer8,8.6.2.3-1+cuda12.2 | Paquetes reales; import Python devuelve8.6.2 |
| Parser ONNX | libnvonnxparsers8,8.6.2.3 | Presente; ningún grafo nuevo compilado |
| cuDNN | 8.9.4.25-1+cuda12.2 | Contenedores box/stereo |
| Python / PyTorch vendor | 3.10.12 / 2.4.0a0+07cecf4168.nv24.5 | Metadatos de paquetes, no ejecución de un modelo |
| Ultralytics vendor | 8.0.120 | Existencia de paquete; no implica soporte YOLO11/26 ni reconocimiento app2 |
| Disco disponible | ~348,6GB en volumen NVMe | No se descargó ni instaló ningún modelo |
| Modo de potencia | MAXN | `nvpmodel -q`, sin cambiar modo |

No se necesita actualizar JetPack/CUDA/TensorRT para realizar la primera
prueba de compatibilidad de un ONNX. La compilación del grafo exacto sigue
pendiente; estas lecturas no certifican cualquier modelo exportado.

## Contenedores y separación de entornos

Se redescubrieron nombres/estado mediante `docker ps -a` antes de consultar:

| Contenedor | Imagen / entorno observado | Consecuencia |
|---|---|---|
| walker-box_pose_estimation.box_pose_estimation-1 | utars-integration:zs2_vision-v0.2.0; runtime nvidia; TensorRT/CUDA presentes | No modificar el detector del proveedor para instalar app2 |
| walker-stereo.stereo_depth_estimation-1 | Misma imagen GPU y versiones consultadas | Comparte la GPU; no detenerlo ni sustituirlo |
| walker-ros.ros2-1 | ros2_ws:humble-dyn-v0.0.114; runtime runc | Tiene ROS2/rclpy/shm_msgs tras preparar su entorno; no TensorRT en la consulta |

La imagen GPU leída tiene ID
`sha256:302d2d6a012f3bef89d126dfe8aa1dee5b5c419043f01192284dac1bb1e798dd`.
La ROS2 leída tiene ID
`sha256:974d1466729d580c21e35ffcc1aef5d98d6ad812cf12186eff0f21e5c02edd44`.
IDs completos de contenedores y resultados se conservan en evidencia privada.

Un contenedor app2 necesitará tanto acceso de lectura a imágenes como un
runtime GPU compatible. No se demostró que los contenedores existentes ya
reúnan ambas interfaces Python. No instalar dependencias dentro de ellos como
atajo; preparar posteriormente una imagen propia con versiones fijadas.

## Cámaras comprobadas mediante recepción pasiva

Nodo temporal rclpy, sólo suscripciones BEST_EFFORT/volatile/depth1. Se
recibieron **dos timestamps distintos por canal**, sin imágenes enviadas a nube
ni capturas nuevas guardadas. No demuestra FPS sostenidos, latencia total,
calibración o precisión de profundidad.

| Canal | Tipo real | Imagen recibida |
|---|---|---|
| /sensor/camera/stereo/color/raw | shm_msgs/msg/Image2m | 960×576, bgr8, step2880 |
| /sensor/camera/stereo_left/image/raw | shm_msgs/msg/Image6m | 1920×1536, yuv422, step3840 |
| /sensor/camera/waist_front_rgbd/color/raw | shm_msgs/msg/Image1m | 640×360, rgb8, step1920 |
| /sensor/camera/waist_front_rgbd/depth/raw | shm_msgs/msg/Image1m | 640×360,16UC1, step1280 |

Un publicador descubierto por canal. Frame de cabeza rectificada:
`stereo_left_rectified_optical_frame`; la imagen sin rectificar usa
`stereo_left_link`. No intercambiar sus coordenadas. El tipo es un mensaje SHM
del proveedor, no `sensor_msgs/Image`; el adaptador app2 debe respetarlo o
convertirlo explícitamente manteniendo el timestamp y el frame.

La cabeza rectificada es una candidata de entrada inicial por el encuadre
previamente conservado. La imagen1920×1536 puede aportar detalle para distinguir
referencias, pero tiene otro modelo óptico. No se volvió a valorar visualmente
la disposición de piezas durante esta consulta de metadatos.

### Consultas fallidas y corrección comprobada

La primera consulta de grafo intentó `/opt/walker/setup.bash` en el contenedor
ROS2 y falló: ese archivo no existe allí. Una consulta posterior desde la
imagen vendor, tras su setup walker, no encontró rclpy. Ninguno de esos errores
demostró fallo de cámara.

Se descubrieron los archivos de entorno y la lectura definitiva funcionó en
`walker-ros.ros2-1` con `/opt/ros/humble/setup.bash` y
`/opt/ubt_3rdparty/setup.bash`. Allí rclpy, shm_msgs y cv_bridge se encuentran
bajo `/opt/ros/humble/local/lib/python3.10/dist-packages/`.
No asumir ausencia de un módulo a partir de un intérprete sin preparar el entorno.

## Recursos compartidos: qué limita la recomendación

Se observaron ~45560MB reportados como RAM en uso por tegrastats y MemAvailable
~11,4GiB. Ambas medidas tienen semánticas distintas; no se suman ni se
interpretan como memoria GPU dedicada. La instantánea de procesos incluye
percepción, estéreo, navegación, voz, web y LLM activos; VLA permanece detenido.
No se cambió el estado de ninguno.

La ventana posterior de tegrastats produjo11 muestras, con GR3D entre0 y99%.
Hay picos y variación; no demuestra margen sostenido ni saturación continua.
Carga media del host alrededor de24 en la primera captura no equivale a un
porcentaje de GPU. Tampoco un100% de CPU en docker stats representa el100% de
las12 CPU. No se ejecutó benchmark, compilación o estrés adicional de GPU.

Esto aconseja empezar con modelo pequeño, batch1, cola de última imagen y
frecuencia de inferencia limitada según las mediciones. Aumentar resolución
sólo cuando mejore la distinción de referencias. El presupuesto de memoria,
CPU/GPU y la coexistencia con navegación deben validarse antes de aceptar app2.

## Diferencia frente a instalar Roboflow Inference actual

El Dockerfile oficial Jetson6.2.0 consultado, fijado en commit
`c5917ecbd59a13ec8857c8bfc0394c41751cb413`, declara CUDA>=12.6 y prepara
TensorRT10.7. No coincide con CUDA12.2/TensorRT8.6 del robot real. No se
instaló ni se presume compatible esa imagen. Esto afecta al ejecutor
preparado por el proveedor, no a la utilidad de su plataforma de entrenamiento.

La ruta propuesta descarga pesos/ONNX y usa un ejecutor propio compatible.
RF-DETR1.11.2 declara TensorRT>=8.6.1 en sus dependencias opcionales; eso no
garantiza que un ONNX concreto compile, que su postprocesado sea correcto o
que sea rápido en esta unidad. Tampoco la tabla de rendimiento sobre una GPU
L4 publicada por Roboflow es un benchmark del Orin de este robot.

## Siguiente comprobación concreta

1. Conseguir un artefacto pequeño exportable y conservar versión/hash/licencia.
2. Preparar una imagen app2 ARM64 independiente compatible con el runtime leído.
3. Validar ONNX de entrada estática/batch1, inicialmente en FP32, contra sus
   resultados de referencia; después evaluar FP16 y comparar máscaras/clases.
4. Medir latencia imagen→resultado p50/p95, memoria y coexistencia con servicios
   del robot; repetir con escenas reservadas de referencias parecidas.
5. Validar arranque y funcionamiento sin Internet ni PC para inferencia.

Estas acciones no se han ejecutado en esta inspección. No hay todavía modelo
app2 entrenado, prueba de identificación ni permiso implícito para movimiento.

## Evidencia y fuentes

Archivo privado:
`../Humanoide-vla-evidence/20261019T094304Z_APP2_VISION_RUNTIME_READONLY/`.
Contiene inventarios host/contenedores, muestras de recursos, recepción de
imágenes, errores y correcciones, scripts exactos de lectura, fuentes públicas
fijadas, before/after y checksums. Los tiempos del host remoto y los nombres de
evidencia no se usan para medir latencia de cámara; no se verificó sincronización.

Para repetir las consultas, usar esos scripts de lectura conservados y
redescubrir primero contenedores/entornos. Ninguno envía START, HOME, acciones,
cambios de modo, instalaciones o reinicios. Las suscripciones ya terminaron.

Fuentes primarias consultadas:

- [NVIDIA JetPack6.0/L4T36.3](https://docs.nvidia.com/jetson/archives/jetpack-archived/jetpack-60/release-notes/index.html).
- [Roboflow: modelos entrenables/exportables](https://docs.roboflow.com/models/supported-models).
- [Roboflow: descarga de pesos y condiciones](https://docs.roboflow.com/models/model-weights/download-roboflow-model-weights).
- [Dockerfile Jetson6.2.0 fijado](https://github.com/roboflow/inference/blob/c5917ecbd59a13ec8857c8bfc0394c41751cb413/docker/dockerfiles/Dockerfile.onnx.jetson.6.2.0).
- [RF-DETR1.11.2, dependencias](https://github.com/roboflow/rf-detr/blob/1.11.2/pyproject.toml).
- [Ultralytics: entrenamiento/exportación](https://docs.ultralytics.com/platform/train/models).
- [NVIDIA: compatibilidad de motores](https://docs.nvidia.com/deeplearning/tensorrt/latest/inference-library/engine-compatibility.html).

Cambio persistente de esta intervención: sólo documentación/evidencia del PC.
No se modificó la configuración de robot, PC de control o PICO. Restauración de sistema no necesaria;
para descartar la decisión, editar selectivamente estos documentos conservando
las lecturas originales. Cambios ya staged por el usuario se preservan.
