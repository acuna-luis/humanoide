# app2 — recorrido local de desarrollo

**Fecha:** 19-10-2026, Europe/Madrid. Este directorio amplía el entorno existente
con conversión de datos, lectura de códigos, trazabilidad e inferencia sobre
archivos. Las comprobaciones y sus resultados observados se registran en
[VALIDACION_FLUJO_LOCAL.md](../../../docs/app2/VALIDACION_FLUJO_LOCAL.md).
La presencia de un script o una salida prevista en esta guía no significa que
una prueba haya terminado correctamente: consultar ese informe y sus recibos.

El servidor es `luisacuna@192.168.1.43`, SSH puerto `2649`. La copia operativa
de **este** directorio está en `~/app2/workflow`; las recetas del entrenador
anterior siguen en `~/app2/setup/training`. Para empezar desde otro PC, revisar
[RETOMAR_APP2.md](../../../docs/app2/RETOMAR_APP2.md), el
[informe del servidor](../../../docs/app2/SERVIDOR_LOCAL_INSTALACION.md) y las
[copias/migración](../../../docs/app2/BACKUP_Y_MIGRACION.md).

## 1. Qué ejecuta y qué conserva

La imagen nueva `app2-workflow:1.0-rfdetr1.11.2` deriva de
`app2-rfdetr:1.11.2-torch2.10.0-cu128`. El lanzador exige que el ID de la base
siga siendo `sha256:af168d95cd04b99fc107652ec11834d69f5dfdf75f98e5bf568cf758eb928ba0`.
Construir la extensión conserva esa imagen base, el driver y los servicios
anteriores. No sustituye la instalación CVAT ni detiene Ollama.

| Componente | Contrato de esta extensión |
|---|---|
| RF-DETR Seg Nano | Heredado: RF-DETR 1.11.2, resolución 312, Torch 2.10/CUDA 12.8 |
| OpenCV | `opencv-python-headless==5.0.0.93`, ya presente en la base |
| Códigos | `zxing-cpp==3.1.1`; lectura real de archivos locales |
| Experimentos | `tensorboard==2.20.0`; escritura local de eventos, sin servicio permanente |
| CVAT SDK | `cvat-sdk==2.79.0` en `/opt/app2/cvat-sdk-venv`, separado del Python de entrenamiento |
| API CVAT del recorrido | Cliente HTTP de biblioteca estándar; reutiliza credenciales privadas y API local |
| Datos/resultados | Volúmenes existentes `app2_datasets`, `app2_training_cache`, `app2_checkpoints` |

Los procesos de trabajo son efímeros, UID/GID `10001:10001`, raíz de contenedor
de sólo lectura, sin capacidades y sin red. El servicio Compose `tools` dispone
de escritura en el volumen de datasets para prepararlos; `gpu` monta esos datos
en sólo lectura. Ambos escriben resultados/caché en sus volúmenes. Hay límites
de 8 CPU, 32 GiB de RAM y 2 GiB de memoria compartida. GPU 0 es el valor inicial;
`APP2_GPU_DEVICE` selecciona el dispositivo expuesto como `cuda:0` dentro del
contenedor. No iniciar simultáneamente varios entrenamientos/inferencias sin
revisar la memoria disponible y las otras cargas.

La construcción de la imagen necesita descargar paquetes públicos. Las órdenes
de inferencia, pruebas y entrenamiento no tienen red. `--verify` realiza además
operaciones **locales** en CVAT desde el host para crear proyectos/tareas
sintéticos, exportarlos y reimportarlos; no sube fotografías productivas. No hay
clientes de control del robot, ROS, cámaras en vivo ni escrituras a PLC.

## 2. Inicio y repetición

Conectar desde el PC y ejecutar los comandos siguientes **en el servidor**:

```bash
ssh -p 2649 luisacuna@192.168.1.43
cd "$HOME/app2/workflow"
bash run_local.sh --help
bash run_local.sh --check
```

`--check` consulta imagen base/extensión, volúmenes, contenedores propios y GPU.
No instala ni arranca un entrenamiento. Si la extensión aún no existe, su
inspección terminará con error; después de transferir/revisar las fuentes, la
orden de construcción explícita es:

```bash
cd "$HOME/app2/workflow"
bash run_local.sh --install
bash run_local.sh --check
```

No reconstruir por cambiar de PC de acceso. La construcción guarda los informes
`/opt/app2/workflow-install-report.json`,
`/opt/app2/workflow-environment.freeze.txt` y los equivalentes `cvat-sdk-*` en la
imagen. Conservar su ID y esos informes: las versiones directas están fijadas,
pero las dependencias transitivas no se congelan completamente sólo con
`requirements.txt`.

Para ejecutar pruebas CPU, lectura de QR conocido/sin lectura y comparación:

```bash
cd "$HOME/app2/workflow"
bash run_local.sh --test
```

El recibo de lectura queda en el volumen de resultados bajo
`/checkpoints/code-smoke/UTC-PID/`, con entradas PNG sintéticas y `result.json`.
Un error de infraestructura devuelve código distinto de cero; consultar el
recibo antes de repetir. No interpretar `NO_READ` como un fallo de instalación
cuando corresponde a la imagen en blanco de la prueba.

El recorrido integrado se lanza con:

```bash
cd "$HOME/app2/workflow"
bash run_local.sh --verify
```

Secuencia implementada: crear/revisar proyectos CVAT → cargar cuatro escenas
sintéticas → guardar polígonos → exportar COCO → reimportar en otra tarea y
comparar → preparar `train/valid` → entrenar un paso en GPU → comprobar cambio
de parámetros → guardar checkpoint → recargar y comparar tensores → inferir
sobre archivos → generar diagnósticos y JSONL. Verificar el resultado real en
el informe de validación; una interrupción puede dejar etapas posteriores sin
ejecutar.

Cada ejecución genera un identificador `infra-UTC-PID` y muestra al terminar:

```text
WORKFLOW_RUN=infra-UTC-PID
HOST_RECEIPTS=/home/luisacuna/app2/receipts/infra-UTC-PID
VOLUME_RESULTS=/checkpoints/infra-UTC-PID
```

Conservar el identificador de **esa** ejecución. No asumir que cualquier carpeta
con fecha reciente es una prueba completa o el modelo que se desea utilizar.
Los reintentos usan nombres nuevos; no sobrescriben datasets o resultados.

## 3. Abrir CVAT y trabajar manualmente

En otra terminal del **PC**, mantener abierto:

```bash
ssh -p 2649 -N -L 18080:127.0.0.1:18080 luisacuna@192.168.1.43
```

Abrir `http://localhost:18080`. La cuenta existente es `app2_admin`; consultar
su contraseña de forma privada siguiendo el informe del servidor. No introducir
credenciales en Git, informes, comandos publicados o capturas compartidas.

El recorrido prepara dos proyectos separados:

- **`app2-itr-v0`**: catálogo inicial de trabajo con polígono `itr_candidate`,
  atributos `visibility` (`visible`, `partial`, `indeterminate`) e
  `identity_status` (`provisional`, `confirmed`). Se crea sin inventar un número
  de material ni cargar automáticamente fotos reales. La identidad de pieza se
  confirma con una fuente del cliente y su asociación documentada.
- **`app2-infrastructure-demo-v0`**: exclusivamente sintético, etiqueta
  `synthetic_app2_probe_only`. Contiene tareas `SYNTHETIC ONLY app2 demo ...` y
  `SYNTHETIC ONLY reimport ...` para inspeccionar las pruebas.

Si un proyecto ya existe, el helper comprueba propietario y catálogo; no cambia
sus etiquetas para hacer pasar la prueba. Los IDs reales y las tareas creadas
quedan en `cvat-demo-result.json`; los recursos sintéticos se conservan también
cuando una fase falla. Revisarlos antes de retirar selectivamente una prueba.

Para datos reales: crear tareas por sesión, subir copias autorizadas, dibujar un
polígono por instancia visible, revisar, guardar/reabrir y exportar **COCO 1.0 con
imágenes**. Confirmar primero las referencias y qué objetos confundibles se
etiquetarán. No mezclar los rectángulos sintéticos con el futuro dataset de ITR.
Las instrucciones de anotación y captura están en
[DATOS_Y_ENTRENAMIENTO.md](../../../docs/app2/DATOS_Y_ENTRENAMIENTO.md).

La instalación del SDK está aislada; este recorrido HTTP no necesita mezclar sus
dependencias con RF-DETR. Puede comprobarse la versión instalada, sin conexión:

```bash
cd "$HOME/app2/workflow"
docker compose --env-file /dev/null -f compose.yaml run --rm --no-deps tools \
  /opt/app2/cvat-sdk-venv/bin/python -c \
  'import cvat_sdk, importlib.metadata; print(importlib.metadata.version("cvat-sdk"))'
```

## 4. Manifiesto y conversión de datos

`coco_prepare.py` necesita un ZIP con un único JSON `annotations/*.json` y un
manifiesto explícito. Las claves de `images` son **exactamente** los
`images[].file_name` del COCO, sin añadir por intuición `images/default/`:

```json
{
  "schema_version": 1,
  "images": {
    "sesion_a/imagen_001.png": {
      "split": "train",
      "session_group": "captura_a_caja_a"
    },
    "sesion_b/imagen_001.png": {
      "split": "valid",
      "session_group": "captura_b_caja_b"
    }
  }
}
```

El manifiesto debe cubrir todas las imágenes. `train` y `valid` deben tener
imágenes; `test` es opcional para este conversor. Un `session_group` sólo puede
pertenecer a una partición. Mantener una misma ráfaga, pieza física/caja/lote y
sus derivados en el grupo que corresponda al protocolo de evaluación. Nombres
de grupo diferentes no prueban independencia física: revisar procedencia y
casi duplicados antes de entrenar.

Para repetir la preparación sobre el ZIP sintético de una ejecución anterior:

```bash
cd "$HOME/app2/workflow"
read -r -p 'Copia el valor WORKFLOW_RUN de tu ejecución: ' APP2_RUN
APP2_PREPARED="${APP2_RUN}-prepared-$(date -u +%Y%m%dT%H%M%SZ)-$$"
bash run_local.sh --prepare \
  --cvat-zip "/checkpoints/$APP2_RUN/cvat-export.zip" \
  --split-manifest "/checkpoints/$APP2_RUN/split-manifest.json" \
  --output "/datasets/$APP2_PREPARED"
```

Las rutas `/datasets` y `/checkpoints` son internas al contenedor. Para un ZIP
real, transferirlo con su manifiesto al volumen mediante la receta de datos;
no basta con pasar la ruta `/home/...` del host, que no está montada. Las
exportaciones productivas y los pesos permanecen fuera de Git.

Salida:

```text
dataset_nuevo/
  dataset_manifest.json
  train/_annotations.coco.json
  train/<file_name original>
  valid/_annotations.coco.json
  valid/<file_name original>
  test/...                         # Si se ha asignado ese split.
```

Se conservan bytes de imagen, IDs y categorías. Se comprueban dimensiones
decodificadas, referencias, cajas, polígonos/RLE, rangos y números finitos;
también rutas peligrosas, enlaces, colisiones y duplicados exactos de imagen.
El manifiesto resultante registra hashes del ZIP, JSON COCO, asignaciones,
conversor e imágenes. Publica una carpeta nueva mediante `renameat2` sin
reemplazar un destino existente; requiere Linux. El conversor limita cada
miembro a 512 MiB, el JSON a 64 MiB y el ZIP descomprimido a 64 GiB para esta
primera herramienta. No renumerar o alterar esas restricciones a ciegas para
admitir una exportación rechazada.

Interfaz reutilizable: `validate_coco_dataset(Path)` devuelve el resumen de
validación; sin `dataset_manifest.json`, marca la revisión de sesiones como
pendiente. No mide generalización ni identifica por sí sola un código de pieza.

## 5. Inferir sobre una imagen o secuencia local

Ejemplo sobre un QR sintético generado por `--verify`, con pesos públicos:

```bash
cd "$HOME/app2/workflow"
read -r -p 'Copia el valor WORKFLOW_RUN de tu ejecución: ' APP2_RUN
APP2_DEMO_RUN="demo-$(date -u +%Y%m%dT%H%M%SZ)-$$"
bash run_local.sh --demo \
  --image "/checkpoints/$APP2_RUN/verification/codes/inputs/known.png" \
  --output-root "/checkpoints/$APP2_DEMO_RUN" \
  --model public --expected-material APP2-SYNTHETIC-MATERIAL-A \
  --identity-scope box --synthetic-input
```

Para una secuencia, sustituir `--image ARCHIVO` por `--sequence DIRECTORIO`.
Procesa archivos de imagen por nombre, sin temporización de vídeo ni cámara
en vivo. El modelo público reconoce su dominio COCO; no se ha entrenado para
las referencias ITR de esta aplicación.

Para el checkpoint sintético de una prueba concreta, copiar su ruta
`checkpoint` del `result.json` de entrenamiento y mantener su
`*.manifest.json` adyacente:

```bash
cd "$HOME/app2/workflow"
read -r -p 'WORKFLOW_RUN: ' APP2_RUN
read -r -p 'Ruta checkpoint /checkpoints/.../synthetic_step1.pth: ' APP2_CHECKPOINT
APP2_DEMO_RUN="demo-checkpoint-$(date -u +%Y%m%dT%H%M%SZ)-$$"
bash run_local.sh --demo \
  --sequence "/checkpoints/$APP2_RUN/verification/codes/inputs" \
  --output-root "/checkpoints/$APP2_DEMO_RUN" \
  --model checkpoint --checkpoint "$APP2_CHECKPOINT" \
  --expected-material APP2-SYNTHETIC-MATERIAL-A \
  --identity-scope box --synthetic-input
```

Esto comprueba recarga/inferencia; un paso sobre rectángulos no entrena un lector
de QR ni un detector de piezas reales. Para una foto productiva, omitir
`--synthetic-input`, aportar su ubicación privada ya transferida al volumen y
dejar ausentes los metadatos que se desconozcan. No inventar un material esperado
para obtener `MATCH` ni declarar `piece` cuando la etiqueta corresponde a caja.

El parámetro `--threshold` tiene valor inicial `0.5`; es un umbral técnico de
salida del modelo, no un criterio de aceptación de la aplicación. La clase
`LocalPerception` consume RGB/Pillow y devuelve cajas, contornos de máscaras y
metadatos. Es la interfaz pequeña que podrá conectarse después a la cámara real;
esa conexión, los timestamps y la calibración todavía deben implementarse y
validarse por separado.

### Lectura, interpretación y comparación

`material.py` separa los bytes leídos por ZXing, el parser de contenido y la
comparación con el identificador esperado. El parser predeterminado es
`{"type":"exact_utf8"}`: compara UTF-8 exacto, sin eliminar espacios, cambiar
mayúsculas, interpretar GS1 o adivinar el formato del cliente.

Si el contrato confirmado del cliente fuera un objeto JSON con una clave de
primer nivel `material_id`, el archivo local de configuración sería:

```json
{"type":"json_field","field":"material_id"}
```

Se pasa con `--parser-config /datasets/.../parser.json`. Es una posibilidad
implementada, no una afirmación sobre las etiquetas reales. No incluye rutas
JSON anidadas ni un parser GS1 implícito. Bytes no UTF-8 y contenido mal formado
producen error de procesamiento, sin sustituir caracteres o ignorar lecturas.

| Resultado | Interpretación del contrato local |
|---|---|
| `MATCH` | Un identificador válido coincide dentro del ámbito declarado |
| `MISMATCH` | Se leyó un identificador válido distinto del esperado |
| `NO_READ` | La imagen se procesó y no se obtuvo código |
| `AMBIGUOUS` | Se obtuvieron identificadores distintos; no se elige el que conviene |
| `PROCESSING_ERROR` | Falló la lectura, la entrada o la interpretación |
| `UNKNOWN` | Hay lectura, pero faltan material esperado o ámbito confirmado |

El ámbito es `piece`, `box`, `lot`, `task` o `unconfirmed`. Un código de caja
coincidente no certifica individualmente las piezas que contiene. Incluso con
`piece`, esta utilidad registra una asociación declarada, sin demostrar que el
código está unido físicamente a la pieza detectada. Un `MATCH` nunca autoriza
movimiento ni equivale al éxito del ciclo industrial.

## 6. Checkpoint y artefactos

El smoke explícito permite repetir sólo la comprobación de entrenamiento sobre
el dataset **sintético** preparado:

```bash
cd "$HOME/app2/workflow"
read -r -p 'WORKFLOW_RUN del dataset sintético: ' APP2_RUN
bash run_local.sh --checkpoint-smoke \
  --dataset "/datasets/$APP2_RUN" \
  --output-root /checkpoints/workflow-training --synthetic-only
```

`--synthetic-only` declara el alcance; no valida que una carpeta arbitraria sea
sintética ni debe usarse para presentar un dataset real como prueba artificial.
El script genera una subcarpeta UTC nueva, mide gradientes y cambio de un
parámetro, guarda estado del modelo, comprueba igualdad de tensores al recargar e
infiere sobre una imagen de validación. No representa una época completa,
evaluación reservada ni checkpoint de reanudación con todo el estado del
optimizador. El entrenador piloto de varias épocas permanece en
`~/app2/setup/training`; revisar su guía antes de ajustar piezas reales.

| Ubicación | Contenido esperado según la fase ejecutada |
|---|---|
| `~/app2/receipts/infra-.../cvat/` | PNG sintéticos, ZIP COCO, split-manifest y recibo API con IDs |
| Volumen datasets, `infra-.../` | Dataset convertido y manifiesto con hashes |
| Resultados, `infra-.../verification/result.json` | Resultado agregado o fallo de la integración |
| `verification/training/UTC_checkpoint_roundtrip/` | `runtime.json`, validación, `result.json`, `synthetic_step1.pth`, manifiesto y eventos TensorBoard |
| `verification/codes/` | Entradas QR/blanco/ambiguo y casos de lectura |
| `verification/demo/` | PNG de diagnóstico, JSON por imagen y `events.jsonl` |

`events.jsonl` registra aplicación/tarea, timestamp UTC, ubicación, materiales,
lectura/visión, excepciones, reintentos del procesador, versiones/hash y estado
de finalización offline. Los campos físicos desconocidos quedan `null` o
`UNKNOWN`: versiones del robot, intervención/paradas físicas, disponibilidad del
destino, tiempo del ciclo industrial. `offline_processing_time_s` mide sólo el
procesamiento de archivos, no una cadencia real. Las listas vacías de eventos
pertenecen al procesador y no demuestran ausencia de incidencias en una línea.

La geometría se devuelve como `CALIBRATION_REQUIRED`, con pose y agarre `null`.
Una máscara o dos puntos en imagen no son coordenadas 3D ni un agarre validado.
El contenedor permanece `UNKNOWN` aunque no haya detecciones; falta una
verificación específica para declarar vacío y manipular el cartón.

### TensorBoard opcional, sólo bajo petición del operador

Las pruebas escriben eventos locales y no dejan un servicio escuchando. Si se
quiere verlos, abrir temporalmente en el servidor un proceso CPU independiente:

```bash
docker run --rm --name app2-tensorboard \
  --user 10001:10001 --read-only --cap-drop ALL \
  --security-opt no-new-privileges --pids-limit 128 --cpus 2 --memory 1g \
  --tmpfs /tmp:rw,nosuid,nodev,size=64m,mode=1777 \
  --publish 127.0.0.1:16006:6006 \
  --mount type=volume,source=app2_checkpoints,target=/checkpoints,readonly \
  app2-workflow:1.0-rfdetr1.11.2 \
  tensorboard --logdir /checkpoints --host 0.0.0.0 --port 6006 --load_fast=false
```

Ese comando manual publica únicamente el puerto loopback del servidor; no
configura autoarranque. En el PC, abrir un túnel aparte y visitar
`http://localhost:16006`:

```bash
ssh -p 2649 -N -L 16006:127.0.0.1:16006 luisacuna@192.168.1.43
```

Ctrl+C termina el proceso y retira su contenedor. No se inicia desde `--verify`.
El inicio manual de la interfaz y su acceso deben verificarse cuando se usen;
no se deducen de la creación de un archivo de eventos.

## 7. Licencias y procedencia

Código, pesos y datos se revisan por separado. Se conservan versiones y hashes;
una licencia de herramienta no concede permiso sobre fotografías productivas o
etiquetas del cliente. Mantener autorización/procedencia de cada dataset y los
avisos correspondientes antes de distribuir artefactos.

| Elemento | Fuente primaria y alcance |
|---|---|
| RF-DETR 1.11.2, código | [Apache 2.0 en el commit fijado](https://github.com/roboflow/rf-detr/blob/7433d5919d0f7e72cc6cb78663e0a731afd499e0/LICENSE) |
| RF-DETR Seg Nano, pesos | La [tabla oficial de licencias de modelos](https://roboflow.com/licensing) declara RF-DETR Seg, todos los tamaños, Apache 2.0. No generalizar a modelos Plus o detección XL/2XL. El peso público exacto y SHA256 están en el manifiesto de precache |
| CVAT Community/SDK | [MIT en el commit CVAT fijado](https://github.com/cvat-ai/cvat/blob/9176834830e2e931a8d3a6857dcf43c6cc0ee927/LICENSE); SDK 2.79.0 aislado |
| ZXing-C++ 3.1.1 | [Apache 2.0 de esa versión](https://github.com/zxing-cpp/zxing-cpp/blob/v3.1.1/LICENSE) |
| TensorBoard 2.20.0 | [Apache 2.0 de esa versión](https://github.com/tensorflow/tensorboard/blob/2.20.0/LICENSE) |
| OpenCV headless 5.0.0.93 | [Licencias de la distribución](https://pypi.org/project/opencv-python-headless/5.0.0.93/#licensing): empaquetado MIT, OpenCV Apache 2.0 y avisos de terceros, incluido FFmpeg LGPL 2.1 en los wheels. Conservar los textos incluidos en la imagen |
| Imágenes sintéticas | Generadas por los scripts locales; marcar su condición sintética y conservar código/hash |
| Datos productivos/públicos | Permisos y licencia de **cada** origen pendientes de registrar antes de incorporarlos; no se heredan de CVAT o del modelo |

La arquitectura funciona sin suscripciones, créditos o cuentas de entrenamiento
externas. El origen de los pesos públicos puede requerir Internet durante el
precache inicial; una ejecución offline necesita el archivo local y su hash,
no una descarga implícita. No subir datos del cliente a servicios externos.

## 8. Detener, revertir y retomar

Los comandos `run_local.sh` usan `docker compose run --rm --no-deps`: terminan
sin dejar un entrenador permanente. Para interrumpir uno, usar Ctrl+C en su
terminal; conservar recibos parciales y elegir otra salida al reintentar. Si
quedase un proceso, identificarlo con:

```bash
docker ps --filter label=com.docker.compose.project=app2-workflow
```

Detener sólo el contenedor propio identificado; no ejecutar `docker stop` sobre
todos, `prune`, limpiezas de GPU ni `down -v`. La imagen base y los servicios
previos se conservan, por lo que retirar selectivamente esta extensión no exige
reinstalar CUDA/PyTorch o reiniciar el servidor/robot. No borrar datasets,
checkpoints o tareas CVAT sin revisar su recibo y backup.

El estado de CVAT se consulta y su servicio propio se detiene/arranca con las
recetas ya instaladas, conservando sus volúmenes:

```bash
bash "$HOME/app2/setup/cvat/cvat.sh" --status
# Sólo si se pretende detener/arrancar CVAT:
bash "$HOME/app2/setup/cvat/cvat.sh" --down
bash "$HOME/app2/setup/cvat/cvat.sh" --up
```

Cerrar el túnel SSH del navegador no detiene CVAT. Exportar COCO tampoco
sustituye una copia de su base de datos y volúmenes: seguir la guía de backup.

Para retomar, leer primero la validación y su `WORKFLOW_RUN`, comprobar imagen y
volúmenes con `--check`, abrir CVAT y revisar los artefactos reales. El siguiente
resultado de aplicación es un piloto con escenas de ITR y referencias
confirmadas, anotación revisada y evaluación por sesiones independientes.
Compatibilidad TensorRT 8.6 en Vision, calibración, señales PLC, agarre, cartón,
ciclo y aceptación FAT/SAT son trabajos posteriores; este recorrido no escribe
en esos equipos ni demuestra esas capacidades.
