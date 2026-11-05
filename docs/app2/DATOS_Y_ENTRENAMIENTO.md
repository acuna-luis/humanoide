# app2 — datos, etiquetado y entrenamiento local

**ID:** APP2-DATA-TRAIN-HANDOFF-20261019.

**Fecha/zona:** 19-10-2026, Europe/Madrid.

**Estado:** receta documental contrastada con los scripts actuales. CVAT y los
smokes sintéticos están VERIFICADOS según el [informe de instalación](SERVIDOR_LOCAL_INSTALACION.md).
Dataset real, ajuste de piezas y modelo final exportado: **PENDIENTES**.
**Actualización posterior:** [flujo completo de infraestructura](VALIDACION_FLUJO_LOCAL.md)
con conversión, checkpoint/recarga, códigos y JSONL ya comprobado con datos
sintéticos. El ID real estará en la caja según el operador; su payload y
asociación con las piezas todavía deben acordarse.

**Piloto real preparado:** [tarea 5/job 5 actual; tarea 4/job 4 inicial conservada](PILOTO_PIEZAS_REALES.md),
dos vistas nuevas y dos previas conservadas, grupo relacionado compartido,
sin anotaciones iniciales ni partición train/valid.
Sirve para iniciar la revisión; todavía no es un dataset de entrenamiento aceptado.

Esta guía permite preparar el siguiente lote y reconocer dónde se detiene el
flujo disponible. Los comandos de servidor se ejecutan allí cuando corresponda;
no se han ejecutado durante esta revisión documental. No necesitan conexión a
Motion/Vision ni autorizan movimiento. El objetivo final de esta fase es un
modelo de percepción evaluado offline.

## 1. Punto de partida y versiones

El editor instalado es CVAT Community **2.79.0**. Para abrirlo desde otro PC,
seguir el túnel y la cuenta privada del [informe de instalación](SERVIDOR_LOCAL_INSTALACION.md#acceso-del-operador).
No volver a instalar por cambiar de PC de acceso. Las fotos no están en Git:
recuperar primero los originales y sus hashes según [FOTOS_Y_FUENTES.md](FOTOS_Y_FUENTES.md).

El entrenamiento está en `~/app2/setup/training` del servidor
`luisacuna@192.168.1.43`, SSH por puerto 2649. Los archivos fuente correspondientes son
[`scripts/app2/server/training`](../../scripts/app2/server/training/README.md).

| Elemento | Receta vigente |
|---|---|
| Modelo | RF-DETR Seg Nano, `rfdetr==1.11.2` |
| Fuente RF-DETR | commit `7433d5919d0f7e72cc6cb78663e0a731afd499e0` |
| Torch / torchvision | `2.10.0` / `0.25.0`, CUDA 12.8/cuDNN 9 |
| Dependencias fijadas | Transformers 5.17.0, Hub 1.16.0, Lightning 2.6.6, Torchmetrics 1.8.2, PEFT 0.21.2, Supervision 0.31.0, NumPy 2.2.6, Click 8.3.1 |
| Imagen | `app2-rfdetr:1.11.2-torch2.10.0-cu128` |
| ID instalado observado | `sha256:af168d95cd04b99fc107652ec11834d69f5dfdf75f98e5bf568cf758eb928ba0` |
| Peso inicial | `/cache/rfdetr/rf-detr-seg-nano.pt`, público; no es un modelo app2 |
| Dataset / resultados | `app2_datasets` → `/datasets`; `app2_checkpoints` → `/checkpoints` |

La imagen conserva todas las versiones resueltas en
`/opt/app2/environment.freeze.txt` y el informe `/opt/app2/install-report.json`.
Las dependencias transitivas y apt no quedan completamente fijadas sólo por
`requirements.txt`; conservar la imagen instalada y esos archivos para reproducirla.
TensorRT no está instalado en este entrenador. Vision se observó con TRT 8.6.2.3;
la compatibilidad del modelo propio sigue PENDIENTE.

Antes de un trabajo nuevo, consultar en el servidor:

```bash
bash "$HOME/app2/setup/install_server.sh" --status
docker image inspect app2-rfdetr:1.11.2-torch2.10.0-cu128 --format '{{.Id}}'
docker volume inspect app2_datasets app2_checkpoints --format '{{.Name}} {{index .Labels "app2.purpose"}}'
nvidia-smi --query-gpu=index,name,memory.total,memory.used,utilization.gpu --format=csv
df -h /home /var/lib/docker
```

Esperar etiquetas `local-coco-datasets` y `local-models-and-evidence`,
respectivamente. Si faltan volúmenes, difiere la imagen o cambian las versiones,
revisar el estado antes de importar. La GPU se comparte con otras cargas; no
detenerlas. No guardar un dataset creciente en `/home` ni acceder directamente a
`/var/lib/docker/volumes`. Los 200 GiB del plan son presupuesto, no cuota aplicada.

## 2. Preparar el piloto y fijar las clases

Preparar inicialmente **30–50 escenas diversas**, como presupuesto del
[plan local](PLAN_LOCAL_RECURSOS_Y_TIEMPOS.md#6-fases-y-entregables): piezas
aisladas, bandeja llena, huecos, solapamientos, cambios de luz, vacíos y objetos
confundibles. Cientos de frames consecutivos de una escena no equivalen a
cientos de situaciones independientes. Conservar originales sin dibujar y
cualquier recorte o conversión como derivado separado.

Registrar, fuera de Git junto al dataset, una tabla por imagen con: nombre
original, SHA256, sesión/fecha, cámara y resolución, unidad física si se conoce,
condiciones, referencia verificada o provisional, procedencia y split asignado.
Guardar también una tabla de clases con `category_id`, nombre estable, significado,
referencia/material ID confirmado y quién lo confirmó. Un nombre provisional
como `pieza_provisional_a` no demuestra el código de material.

Antes de etiquetar, acordar por escrito:

- Qué constituye una instancia y qué partes visibles forman su máscara.
- Las clases confirmadas y los confundibles; no deducir referencia de la caja.
- La política para oclusión, reflejos, objetos parciales y objetos sin identificar.
- Qué escenas negativas deben quedar sin instancias y qué objetos sí deben
  etiquetarse. Una pieza conocida visible sin anotar puede convertirse en un
  falso fondo durante el entrenamiento.

Crear un proyecto CVAT con un catálogo común de etiquetas y tareas identificadas
por sesión. Mantener los nombres estables. El COCO exportado es el que determina
los `category_id`: no asumir que el ID interno de etiqueta de CVAT es el ID COCO
ni el índice de salida del modelo. La versión RF-DETR fijada deriva su mapping
de clases del COCO de entrenamiento; conservarlo con el modelo.
[Lector oficial de esta versión](https://raw.githubusercontent.com/roboflow/rf-detr/7433d5919d0f7e72cc6cb78663e0a731afd499e0/src/rfdetr/datasets/coco.py).

En todas las particiones debe quedar la **misma tabla `categories` de IDs y
nombres**, incluso cuando una categoría no tenga instancias en un split. No
renumerar cada exportación de forma independiente, añadir una clase de fondo
por intuición ni reutilizar un ID para otra referencia. Un cambio de catálogo
requiere una versión nueva del dataset y la revisión de todos sus splits.

## 3. Etiquetar, revisar y exportar desde CVAT

1. Subir copias de trabajo de las imágenes al proyecto local. Conservar la
   correspondencia inequívoca con los originales y sus sesiones.
2. En cada imagen, dibujar **un contorno por pieza visible**. Evitar unir piezas
   vecinas por contacto y no completar geometría escondida. Etiquetar cada
   instancia con su clase confirmada o la provisional acordada.
3. Guardar, cerrar y reabrir el trabajo. Revisar todas las imágenes del piloto,
   especialmente instancias pequeñas, ocluidas y confundibles. Resolver las
   discrepancias antes de congelar el lote.
4. Exportar **COCO 1.0**, incluyendo imágenes. Conservar el ZIP original intacto,
   SHA256, proyecto/tareas/jobs de origen, fecha y catálogo utilizado en una
   ubicación privada persistente.
5. Inspeccionar el JSON del ZIP: `images`, `annotations`, `categories`, nombres
   de archivo y segmentaciones por instancia. Revisar máscaras sobre imágenes
   originales. La prueba de instalación sólo comprobó un polígono sintético;
   no revisó estas imágenes reales.
6. Conservar además un backup de tareas/proyecto y otra copia de los originales
   fuera del SSD de trabajo. Exportar COCO no sustituye todos los datos de CVAT.

La exportación sintética verificada contiene JSON bajo `annotations/` e imágenes
bajo `images/`. **Ese ZIP no es todavía la carpeta que acepta `train_local.py`.**
No basta con renombrar el ZIP o un JSON ni con copiar el mismo COCO a tres carpetas.

## 4. Separar sesiones y producir el COCO local

Asignar sesiones completas a `train`, `valid` y `test` **antes de entrenar**.
Cuando haya suficientes unidades físicas, reservar también unidades diferentes.
Mantener una ráfaga, sus recortes y sus variantes en una sola partición. Usar
`valid` para decidir cambios y elegir candidato; preservar `test` para la
evaluación final. Si no hay sesiones independientes suficientes, registrarlo
como limitación y ampliar datos antes de afirmar generalización.

El formato requerido por el script es:

```text
pilot_v001/
  train/
    _annotations.coco.json
    sesion_a_0001.png
    ...
  valid/
    _annotations.coco.json
    sesion_b_0001.png
    ...
  test/                         # Opcional para el script; recomendado como reserva.
    _annotations.coco.json
    sesion_c_0001.png
    ...
```

Cada JSON incluye sólo sus imágenes y anotaciones, con la misma tabla de clases.
`image_id` y `annotation.id` deben ser únicos dentro de su split y las referencias
deben concordar. `images[].file_name` es relativo a su propia carpeta, nunca una
ruta absoluta o que salga de ella. Si se reorganizan imágenes, actualizar
`file_name`; no alterar coordenadas sin registrar y aplicar su transformación.
No redimensionar previamente a 312 por necesidad del script: el entrenamiento
tiene su procesamiento propio. Preservar el detalle del original para evaluar
si esa resolución permite distinguir las referencias.

**Conversor disponible y probado con exportación CVAT real de datos sintéticos:**
[`coco_prepare.py`](../../scripts/app2/workflow/coco_prepare.py).
[Prueba completa y comandos](VALIDACION_FLUJO_LOCAL.md). El manifiesto exige
una asignación por imagen, por ejemplo:

```json
{"schema_version":1,"images":{"sesion_a/img01.png":{"split":"train","session_group":"sesion_a"},"sesion_b/img02.png":{"split":"valid","session_group":"sesion_b"}}}
```

En el servidor, con el ZIP y manifiesto privados ya dentro del volumen de
resultados, y un nombre de dataset nuevo:

```bash
bash "$HOME/app2/workflow/run_local.sh" --prepare \
  --cvat-zip /checkpoints/lote_elegido/cvat-export.zip \
  --split-manifest /checkpoints/lote_elegido/split-manifest.json \
  --output /datasets/pilot_v001
```

El conversor conserva bytes/IDs/categorías y registra hashes. Comprueba grupos
separados, duplicados exactos, imágenes/dimensiones y geometría de cajas/máscaras;
rechaza rutas inseguras, relaciones inválidas y destinos existentes. Publica el
resultado completo de forma atómica. No elige el split automáticamente, no
confirma clases y no detecta todos los casi duplicados o errores de procedencia:
revisar el manifiesto de sesiones y las máscaras reales antes de entrenar.
El ZIP original permanece intacto. No copiar el mismo COCO a tres carpetas.

## 5. Importar al volumen sin modificar el host

La siguiente receta de transferencia usa herramientas de archivo de la imagen
instalada. Es una receta documental; **no se ha probado con un dataset real**.
Parte de `pilot_v001/` ya preparado y revisado en el PC del operador. Usar un
nombre nuevo para cada versión; los ejemplos rechazan que ese destino exista.
No incluir enlaces simbólicos o a archivos de fuera del dataset.

En el PC, ajustar la ruta al padre de la carpeta preparada. El flujo por stdin
evita una copia voluminosa en `/home` del servidor y no monta directorios del host:

```bash
set -euo pipefail
APP2_DATASET_PARENT=/ruta/privada/datasets_preparados
test -f "$APP2_DATASET_PARENT/pilot_v001/train/_annotations.coco.json"
test -f "$APP2_DATASET_PARENT/pilot_v001/valid/_annotations.coco.json"
tar -C "$APP2_DATASET_PARENT" -cf - pilot_v001 |
  ssh -p 2649 luisacuna@192.168.1.43 'docker run --rm -i --network none --read-only --user 10001:10001 --cap-drop ALL --security-opt no-new-privileges --pids-limit 64 --memory 512m --cpus 1 --mount type=volume,source=app2_datasets,target=/datasets --entrypoint /bin/sh app2-rfdetr:1.11.2-torch2.10.0-cu128 -c "umask 077 && test ! -e /datasets/pilot_v001 && tar --no-same-owner --no-same-permissions -xf - -C /datasets"'
```

Confirmar primero la existencia/etiqueta del volumen en la sección 1: Docker
puede crear un volumen ausente al montarlo. La escritura se hace con UID/GID
**10001:10001**, el mismo usuario del entrenador; no requiere `chown` ni root.
No cambiar propietarios de volúmenes existentes para resolver un error sin
inspeccionar su origen. Si falla o se interrumpe la transferencia, el destino
puede quedar parcial: no entrenarlo ni sobrescribirlo a ciegas. Conservar la
evidencia y revisar ese directorio antes de decidir su retirada o una versión nueva.

## 6. Comprobar y entrenar el piloto

En el servidor, desde las recetas instaladas:

```bash
set -euo pipefail
APP2_TRAINING_COMPOSE=(docker compose --env-file /dev/null
  --project-name app2-training
  --project-directory "$HOME/app2/setup/training"
  -f "$HOME/app2/setup/training/compose.yaml")
"${APP2_TRAINING_COMPOSE[@]}" run --rm --no-deps training python train_local.py --help
"${APP2_TRAINING_COMPOSE[@]}" run --rm --no-deps training python train_local.py --dataset /datasets/pilot_v001 --check
```

El proyecto y el archivo Compose se fijan explícitamente: `--env-file /dev/null`
por sí solo no neutraliza `COMPOSE_FILE` o `COMPOSE_PROJECT_NAME` heredados de
otra sesión. No depende del directorio actual de la terminal.

Esperar `DATASET_CHECK_PASS` y revisar los recuentos de imágenes/instancias,
categorías y hashes. El check es también el comportamiento por defecto: sin
`--run` no empieza el ajuste. Comprueba rutas locales, imágenes presentes,
IDs repetidos dentro de un split, referencias imagen/clase, segmentación no
vacía, ancho/alto positivos de bbox y bytes de imagen idénticos entre splits.
Si existe `test/_annotations.coco.json`, también lo comprueba; si falta, omite
`test`. Confirmar expresamente su presencia cuando se haya reservado un test.

**Límites del check:** no decodifica ni inspecciona visualmente las imágenes,
no rasteriza/valida completamente los polígonos o cajas, no confirma identidad
de las clases, no detecta casi duplicados ni fuga de sesión y no exige que cada
clase tenga ejemplos suficientes. Su salida mantiene
`session_split_review = PENDING` incluso si pasa; la revisión humana debe quedar
firmada en el manifiesto del lote. Un PASS no reemplaza esa revisión.

Cuando esos datos estén aceptados y se decida iniciar el piloto:

```bash
APP2_TRAINING_COMPOSE=(docker compose --env-file /dev/null
  --project-name app2-training
  --project-directory "$HOME/app2/setup/training"
  -f "$HOME/app2/setup/training/compose.yaml")
"${APP2_TRAINING_COMPOSE[@]}" run --rm --no-deps training python train_local.py --dataset /datasets/pilot_v001 --epochs 3 --run
```

Esto sí inicia trabajo GPU. El servicio carece de red y monta el dataset sólo
lectura. Usa una GPU —selección `APP2_GPU_DEVICE`, 0 por defecto—, 8 CPU/32 GiB RAM,
2 GiB shm y UID 10001; no impone un límite de VRAM. El proceso dentro ve su GPU
como `cuda:0`. Usa pesos ya cacheados; si faltan, la receta falla en vez de
descargarlos implícitamente. Preparación online/caché sólo mediante la
[receta existente](../../scripts/app2/server/training/README.md#preparación-y-comprobación).

El piloto fija resolución 312, `multi_scale="off"`, `amp_dtype="auto"`,
seed 42, 4 workers y batch automático. Para una repetición comparable se puede
fijar `--batch-size 1` u otro entero comprobado. Las opciones admitidas son
las de `--help`; no hay una opción actual de reanudar checkpoint o de seleccionar
otro peso propio. Medir las 3 épocas y registrar memoria, tiempos y fallos antes
de decidir una ejecución más larga. Los plazos del plan son estimaciones.

Cada ejecución crea `/checkpoints/runs/<UTC>_seg_nano_312/`. No sobrescribe el
peso público. Al terminar, revisar:

| Archivo | Qué conservar/comprobar |
|---|---|
| `runtime.json` | Versiones y GPU realmente expuestas |
| `dataset_manifest.json` | Recuentos/hashes del dataset utilizado |
| `requested_config.json` | Parámetros solicitados por el wrapper |
| `training_config.json` | Configuración/batch/acumulación efectivos producidos por RF-DETR |
| CSV y registros de RF-DETR | Métricas/tiempo de entrenamiento y validación; inspeccionar sus rutas reales |
| `result.json` | PASS/FAIL, duración, memoria y lista de checkpoints con SHA256 si terminó correctamente |
| Pesos `.pth`, `.ckpt` o `.pt` | Los artefactos reales encontrados; no asumir un nombre fijo |

Un fallo previo a crear el directorio o una interrupción abrupta puede no dejar
`result.json`; la ausencia no es PASS. Guardar también el código de salida/log
del proceso. El RSS del resumen excluye workers y las cifras CUDA excluyen otros
procesos: completar las mediciones del host durante el piloto.

El wrapper tiene `run_test=False`: **no evalúa automáticamente el test reservado**.
Elegir el candidato por validación y revisión de errores, conservando el test.
Existe inferencia de checkpoint con manifiesto explícito mediante
`run_local.sh --demo --model checkpoint`; guardado/recarga de un paso sintético
verificados. **PENDIENTE:** evaluación de métricas de un checkpoint de piezas
reales, catálogo/model_manifest de ese entrenamiento y errores por clase,
desconocidos y sesiones.
La pérdida o el PASS del proceso no certifican identificación industrial.

## 7. Recoger resultados y preparar el relevo

Listar en el servidor las ejecuciones propias, sin GPU ni escritura de resultados:

```bash
docker run --rm --network none --read-only --user 10001:10001 --cap-drop ALL --security-opt no-new-privileges --pids-limit 64 --memory 256m --cpus 1 --mount type=volume,source=app2_checkpoints,target=/checkpoints,readonly --entrypoint /bin/sh app2-rfdetr:1.11.2-torch2.10.0-cu128 -c '
  if [ -d /checkpoints/runs ]; then
    find /checkpoints/runs -mindepth 1 -maxdepth 1 -type d -print
  else
    printf "%s\n" "Todavía no hay entrenamientos reales."
  fi
'
```

En la instalación inicial sólo existen resultados bajo `smoke`; esta consulta
informa si falta `runs` y no crea el directorio.

Para copiar **una ejecución** al PC, sustituir la ruta `REEMPLAZAR_UTC_seg_nano_312`
por la elegida y usar un destino privado nuevo. La exportación lee el volumen
como 10001 y no monta el directorio del PC o del servidor en el contenedor:

```bash
set -euo pipefail
umask 077
APP2_RESULTS_DEST=/ruta/privada/relevo_app2_run_elegido
mkdir "$APP2_RESULTS_DEST"
ssh -p 2649 luisacuna@192.168.1.43 'docker run --rm --network none --read-only --user 10001:10001 --cap-drop ALL --security-opt no-new-privileges --pids-limit 64 --memory 256m --cpus 1 --mount type=volume,source=app2_checkpoints,target=/checkpoints,readonly --entrypoint tar app2-rfdetr:1.11.2-torch2.10.0-cu128 -C /checkpoints -cf - runs/REEMPLAZAR_UTC_seg_nano_312' > "$APP2_RESULTS_DEST/run.tar"
tar -tf "$APP2_RESULTS_DEST/run.tar"
sha256sum "$APP2_RESULTS_DEST/run.tar"
```

Comprobar que SSH terminó con código 0 y que el archivo contiene configuración,
métricas y pesos; una transferencia fallida puede dejar un tar parcial. Verificar
los hashes de los checkpoints contra `result.json` tras recuperarlos. Esta copia
externa permite el relevo; conservar también dataset congelado, ZIP CVAT,
manifiesto de sesiones/clases, imagen/locks/freeze y criterio de selección.
No añadir fotos, pesos, tars, secretos o backups privados a Git.

Registrar en el relevo: versión exacta del lote, ruta de ejecución, estado del
proceso, checkpoint candidato y SHA256, resultados medidos, fallos conocidos,
revisión de fugas, ubicación de copias y siguiente paso pendiente. Nunca usar
`down -v`, `volume prune` o `system prune` como limpieza de este flujo. Detener
un entrenador propio termina ese proceso; preservar sus resultados antes de
retirar artefactos. No modificar servicios Ollama u otros proyectos.

## 8. Exportar el modelo propio: límite actual

El comando existente:

```bash
# En el servidor. Prueba pública opcional, usa GPU.
APP2_TRAINING_COMPOSE=(docker compose --env-file /dev/null
  --project-name app2-training
  --project-directory "$HOME/app2/setup/training"
  -f "$HOME/app2/setup/training/compose.yaml")
"${APP2_TRAINING_COMPOSE[@]}" run --rm --no-deps training python smoke.py export
```

**Exporta siempre `rf-detr-seg-nano.pt` público** mediante `cached_weights()`.
No acepta el checkpoint del entrenamiento app2. Comprueba ONNX opset 17/IR 8,
entrada estática 1×3×312×312 y ejecución ONNX Runtime CPU sobre un tensor
sintético; no compara predicciones numéricamente. Repetirlo no convierte el
modelo ajustado en un ONNX propio.

**PENDIENTE — exportación del fine-tuning:** seleccionar y cargar explícitamente
el checkpoint candidato y su catálogo/configuración, conservar hash, exportar
ONNX y documentar preprocesamiento, clases, máscaras y posprocesamiento. Añadir
una receta versionada y comprobar que exporta esos pesos, con paridad contra
PyTorch en imágenes retenidas. No hay un comando funcional de ese paso en el
repositorio actual.

**PENDIENTE — Vision:** compatibilidad del ONNX final con TensorRT 8.6.2.3,
compilación para la Orin real, paridad/métricas, integración de imágenes SHM y
latencia/memoria bajo carga. No copiar un engine producido en RTX como artefacto
portable al robot. Estas tareas pertenecen a una intervención posterior de
percepción, con descubrimiento actualizado del destino; no requieren habilitar
control físico. Hasta cerrarlas, el entregable es el dataset/checkpoint y su
evidencia offline, no un detector app2 desplegado.
