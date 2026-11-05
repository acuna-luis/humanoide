# App2: RF-DETR Seg Nano local

Receta para el servidor x86_64; no se instala en Vision ni cambia el driver del
host. Los contenedores de trabajo son efímeros y no publican puertos. Las pruebas
usan rectángulos sintéticos y pesos públicos, sin fotografías privadas.

## Versiones y fuentes

- RF-DETR **1.11.2**, tag oficial en commit
  `7433d5919d0f7e72cc6cb78663e0a731afd499e0`:
  [API y extras versionados](https://github.com/roboflow/rf-detr/tree/7433d5919d0f7e72cc6cb78663e0a731afd499e0).
  [Wheel PyPI](https://pypi.org/project/rfdetr/1.11.2/) de 788908 bytes,
  SHA256 `2f23589567123b59302f1cfa9d14d23630f9f583ee6f3468c5891e33fb103b2a`.
- Base oficial **pytorch/pytorch:2.10.0-cuda12.8-cudnn9-runtime**, digest linux/amd64
  `sha256:b85566342b86d13a67712e9315d40cdc2dad7f8d86df1aff3831f80835edbcca`.
  Capas comprimidas del manifiesto consultado: **4432776135 bytes (4,13 GiB)**;
  el disco descomprimido y el tamaño final se miden tras el build.
  [Pareja oficial](https://pytorch.org/get-started/previous-versions/):
  PyTorch 2.10.0 + torchvision 0.25.0, CUDA 12.8. El driver580 observado admite
  runtimes CUDA12 mediante
  [compatibilidad de NVIDIA](https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html).
- `requirements.txt` fija las dependencias principales; los extras son
  `train,onnx`. No se instala TensorRT. El build conserva el informe de pip y
  **todas** las versiones resueltas en `/opt/app2/`. El digest final de la imagen
  debe registrarse al instalar: las dependencias transitivas/apt no están fijadas
  por este archivo y pueden cambiar en otro build.
- La imagen base usa Python de Ubuntu con protección PEP668. El Dockerfile crea
  `/opt/app2/venv` con `--system-site-packages` para reutilizar sus ruedas CUDA y
  PyTorch, e instala las dependencias adicionales dentro del entorno virtual.
  No se modifica Python del host ni se usa `--break-system-packages`. Apt/venv y
  pip están en capas separadas; BuildKit conserva las descargas pip en una caché
  de build propia `app2_training_pip`, sin copiarlas a la imagen final.
- Peso público `rf-detr-seg-nano.pt`, URL oficial y MD5 en
  [registro versionado](https://github.com/roboflow/rf-detr/blob/7433d5919d0f7e72cc6cb78663e0a731afd499e0/src/rfdetr/assets/model_weights.py).
  `precache` valida el MD5 y guarda también SHA256/tamaño/URL.

Las versiones fijadas cumplen los rangos publicados por RF-DETR. La combinación
se considera operativa cuando pasan las pruebas reales descritas debajo; una
resolución correcta de pip por sí sola no demuestra inferencia/entrenamiento.

La primera instalación detectó un conflicto con `spin0.16`, incluido en la base:
necesita Click<8.4, mientras que Hugging Face Hub>=1.17 necesita Click>=8.4.2.
Se fija Transformers5.17.0 + Hub1.16.0 + Click8.3.1, conservando PEFT0.21.2 y
sin eliminar herramientas de la base ni ignorar `pip check`. No actualizar
estas versiones por separado sin reconstruir y repetir los smokes.

## Preparación y comprobación

Ejecutar desde esta carpeta en el servidor autorizado:

```bash
docker compose build --pull
docker compose --profile online run --rm --no-deps precache
bash init_cache.sh
docker compose run --rm --no-deps training python smoke.py gpu
docker compose run --rm --no-deps training python smoke.py train
# Opcional: exportación ONNX opset17 y ejecución CPU con tensor sintético.
docker compose run --rm --no-deps training python smoke.py export
```

El servicio `training` usa `network_mode: none`. Sus pruebas pasan sin red tras
el precache. `precache` es el único servicio con red y no monta el dataset ni
reserva GPU. No requiere cuenta/API key y sólo descarga pesos públicos.
El build necesita acceso a índices de paquetes e imágenes públicas.
Los ajustes de entorno desactivan telemetría HF y loggers; la separación de red
es la garantía efectiva de que una ejecución de entrenamiento no envía datos.

Límites iniciales: una GPU seleccionada por `APP2_GPU_DEVICE` (0 por defecto),
8 CPU, 32 GiB RAM, 2 GiB shm, 512 procesos. No hay límite de VRAM en Docker:
la GPU sigue compartida con otros procesos. No se detienen cargas ajenas.
Para otra GPU: `APP2_GPU_DEVICE=1 docker compose run ...`.
El ID de GPU expuesto se convierte en `cuda:0` dentro del contenedor.

Tres volúmenes con nombre quedan en el DockerRootDir del host:

`init_cache.sh` prepara la caché JIT después del precache: la imagen base/build
puede dejar `/cache/xdg` propiedad de root. El helper monta sólo el volumen
público etiquetado `app2_training_cache`, sin GPU, red o directorios del host,
y cambia ese subárbol a UID10001. El entrenador sigue siendo usuario10001 con
capabilities vacías. No se alteran dataset, checkpoints o permisos del servidor.

| Volumen | Destino | Uso |
|---|---|---|
| `app2_training_cache` | `/cache` | Pesos/cachés públicos, Triton y HF |
| `app2_datasets` | `/datasets` | COCO privado, montado sólo lectura al entrenar |
| `app2_checkpoints` | `/checkpoints` | Modelos, CSV, configuración y evidencia |

El proceso usa UID/GID10001, raíz de contenedor sólo lectura, sin capacidades
Linux y con `no-new-privileges`. No se monta Docker socket, directorio del
usuario ni red del host. Los volúmenes nuevos toman el propietario10001 del
directorio de la imagen; si ya existen, inspeccionar permisos antes de cambiar
propietarios. No usar `down -v` ni limpiezas globales.

Cada smoke crea un directorio UTC nuevo y conserva `runtime.json`, freeze y
`result.json`. La prueba GPU ejecuta backward CUDA, NMS torchvision e inferencia
del segmentador sobre una imagen generada. La prueba `train` ejecuta exactamente
un paso de optimizador RF-DETR y una validación sobre COCO sintético; exige
gradientes finitos y no nulos. Sus métricas no dicen nada sobre las piezas reales.
La exportación opcional comprueba ONNX y sus salidas con ONNX Runtime CPU;
paridad numérica, exportación del modelo final y TensorRT8.6 en Orin quedan
pendientes. No producir/copiar un engine RTX como artefacto portable a Orin.

## Dataset y primer piloto

El formato `dataset_file="roboflow"` es el lector **local COCO**, no un servicio
remoto: `train/_annotations.coco.json`, `valid/_annotations.coco.json` e imágenes
en esas mismas carpetas; `test` es opcional. Los IDs y nombres de categorías
deben coincidir entre particiones, con segmentación por instancia. Un export
COCO único de CVAT necesita preparar esas particiones antes de entrenar.
Conservar imágenes originales y reservar sesiones/unidades diferentes.

Tras importar el dataset revisado en el volumen `app2_datasets`, por ejemplo en
`/datasets/pilot_v001`, validar sin arrancar entrenamiento:

```bash
docker compose run --rm --no-deps training python train_local.py --dataset /datasets/pilot_v001 --check
# Cuando exista el dataset revisado y se decida iniciar el piloto:
docker compose run --rm --no-deps training python train_local.py --dataset /datasets/pilot_v001 --epochs 3 --run
```

`--check` rechaza imágenes idénticas en splits distintos, rutas inexistentes,
categorías incompatibles y anotaciones sin segmentación. La revisión humana de
fugas entre sesiones, contornos e identidad de las clases sigue siendo necesaria.
No hay dataset real incluido ni entrenamiento real iniciado por esta receta.

Piloto: Seg Nano312 fijo, `multi_scale="off"`, `amp_dtype="auto"`, batch automático,
4 workers, seed42, CSV local y ningún logger cloud. RF-DETR guarda el batch y
acumulación efectivos en `training_config.json`. Si se necesita comparar con
otra GPU, fijar `--batch-size` explícito. `--epochs 3` mide un primer lote; conservar
duración por época de CSV, máximos de memoria, anotaciones/hashes y checkpoints
del directorio nuevo. No equivale a un entrenamiento validado para producción.
El resumen RSS de Python excluye sus workers y las medidas CUDA excluyen otros
procesos: completar con monitorización del host cuando se mida el piloto.

El peso original nunca se sobrescribe. Cada ejecución crea un destino nuevo;
interrumpir el contenedor detiene sólo ese proceso. La reversión del entorno
consiste en dejar de usar/eliminar la imagen propia y los contenedores efímeros;
conservar los tres volúmenes y sus backups hasta revisar su contenido.
