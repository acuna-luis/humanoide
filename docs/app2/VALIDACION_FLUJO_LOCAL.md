# app2 — recorrido local reproducible y resultados

**ID:** APP2-REV001-WORKFLOW-20261019. **Fecha/zona:** 19-10-2026, Europe/Madrid.
**Estado:** infraestructura local VERIFICADA con datos sintéticos. Modelo de
piezas reales, identificación industrial, calibración y operación física PENDIENTES.

**Ampliación posterior del mismo día:** se ha preparado la
[primera tarea de imágenes reales](PILOTO_PIEZAS_REALES.md) en el proyecto 1.
El estado «vacío» que figura más abajo corresponde al cierre de esta prueba
sintética; consultar ese informe para la anotación real aún pendiente.

El usuario aporta la especificación completa, confirma completar el recorrido
local y permite consultas técnicas sin movimiento. Se conserva la
[matriz rev001](ESPECIFICACION_REV001.md). **APP2 es nuestro nombre para la segunda
operación, ITR**; el Word también contiene Harness Box y OTR. No se implementan
esas otras operaciones en esta intervención.

## 1. Qué se añadió a lo ya instalado

Se reutilizan CVAT 2.79.0, GPU, Docker y la imagen inicial RF-DETR. Las
[recetas nuevas](../../scripts/app2/workflow/README.md) están en
`scripts/app2/workflow/` del repositorio y `~/app2/workflow/` del servidor.
No se reinstalan CVAT, el sistema, CUDA del host o los drivers.

| Componente | Estado / versión |
|---|---|
| GPU real | Una NVIDIA RTX 6000 Ada, 49140 MiB; no memoria agregada de varias GPUs |
| Sistema servidor | Ubuntu 24.04.5 x86_64, Threadripper PRO 5975WX, unos 503 GiB RAM |
| Driver | 580.178.04 conservado; la capacidad que anuncia nvidia-smi no es la versión de toolkit instalada |
| Runtime de entrenamiento | Torch 2.10.0 + CUDA 12.8 de la imagen, RF-DETR 1.11.2; ejecución real cuda:0/BF16 |
| Imagen base conservada | `app2-rfdetr:1.11.2-torch2.10.0-cu128`, ID `af168d95…928ba0` |
| Imagen derivada | `app2-workflow:1.0-rfdetr1.11.2`; dependencias y fuentes propias, sin sustituir la base |
| Anotación | CVAT 2.79.0 existente; proyecto provisional y demo sintética persistentes |
| OpenCV | headless 5.0.0.93 ya presente en base, conservado |
| Lectura | ZXing-C++ 3.1.1; QR real generado/leído para probar infraestructura |
| Experimentos | TensorBoard 2.20.0, eventos locales escritos y releídos; sin visor permanente |
| CVAT SDK | 2.79.0 en venv aislado `/opt/app2/cvat-sdk-venv`; login/consulta real comprobados |
| Trazabilidad | JSON/JSONL local; no MES, base de datos ni PLC externos conectados |

Imagen final: `sha256:fb2c1b830588d81634af285a6886519b5c201492fb265b71d3a01fc33d43704c`.
[Lock de runtime y versiones](../../scripts/app2/workflow/runtime.lock.json).
La imagen final añade el helper SDK y su documentación; el código de inferencia,
conversor y entrenamiento coincide con el ejecutado en los recibos.

GPU al terminar: 5500 MiB ocupados/0%, igual al inventario inicial de esta
sesión. Ollama y los 18 servicios CVAT mantienen IDs/arranques anteriores;
ningún entrenador queda permanente. El contenedor GPU sólo ve la GPU seleccionada,
por defecto la 0; límites 8 CPU/32 GiB RAM/2 GiB shm, sin cuota de VRAM.
Raíz/home y SSD Docker siguen separados; datos grandes en volúmenes Docker.
Las cifras libres son instantáneas; consultar antes de una campaña.

El runtime de inferencia del robot sigue siendo el de la
[inspección anterior](VERIFICACION_ROBOT_Y_ELECCION_VISION.md); no se conecta
ni modifica Motion/Vision en esta ampliación. No copiar el runtime CUDA 12.8
del servidor sobre la Orin con CUDA 12.2/TRT 8.6.

## 2. CVAT y ontología de inicio

Acceso desde el PC, mantener la terminal abierta:

```bash
ssh -p 2649 -N -o ExitOnForwardFailure=yes \
  -L 127.0.0.1:18080:127.0.0.1:18080 luisacuna@192.168.1.43
```

Abrir **http://localhost:18080**. Cuenta/contraseña privadas existentes según
[la guía de acceso](RETOMAR_APP2.md). No hay contraseña en estos documentos.

| Recurso creado | Uso y estado |
|---|---|
| Proyecto 1, `app2-itr-v0` | Para datos reales posteriores; vacío, sin referencias inventadas |
| Etiqueta `itr_candidate` | Polígono provisional; atributos `visibility` visible/partial/indeterminate e `identity_status` provisional/confirmed |
| Proyecto 2, `app2-infrastructure-demo-v0` | Aisla completamente las imágenes sintéticas del dataset real |
| Tarea 2 | Cuatro rectángulos PNG sintéticos con polígonos conocidos, conservada |
| Tarea 3 | Reimportación COCO de la anterior; contornos/máscaras comparados, conservada |

No usar la etiqueta `confirmed` sin ground truth documentado. No mezclar
rectángulos sintéticos con ITR reales. Cabeza/extremo, caja/separadores, región
de etiqueta y alojamientos del destino se añadirán sólo si ayudan a un contrato
de orientación, lectura o presentación confirmado; no anotar por rellenar clases.

La foto de fábrica muestra organización en cartón/separadores. Es una pista
para ROI y estrategia de selección, no confirma dimensiones, número fijo de
posiciones o que todas las cajas de trabajo sean iguales.

## 3. Repetir el recorrido completo

En el PC:

```bash
ssh -p 2649 luisacuna@192.168.1.43
```

En el servidor existente, empezar por lectura:

```bash
bash "$HOME/app2/workflow/run_local.sh" --check
```

Para repetir las pruebas CPU y códigos, o todo el recorrido sintético:

```bash
bash "$HOME/app2/workflow/run_local.sh" --test
bash "$HOME/app2/workflow/run_local.sh" --verify
```

`--test` crea una nueva evidencia pequeña. `--verify` **crea nuevas tareas
sintéticas** en el proyecto de demo, una versión COCO nueva, un checkpoint y
resultados; requiere CVAT operativo y GPU disponible. No es una consulta de
estado ni necesita ejecutarse antes de cada sesión. Su recorrido es:

1. CVAT: carga cuatro PNG distintos, guarda polígonos, exporta COCO con imágenes,
   reimporta a otra tarea y comprueba las máscaras.
2. Copia sólo ese ZIP/manifiesto a resultados; convierte a train/valid con
   grupos explícitos y valida formato, imágenes, dimensiones y máscaras.
3. Hace un paso real de RF-DETR, comprueba gradientes y cambio de un parámetro,
   guarda el checkpoint, lo recarga y coteja todos los tensores.
4. Genera QR conocidos/imagen sin código/dos códigos, ejecuta inferencia del
   checkpoint sobre esos archivos y escribe PNG, JSON y JSONL.

Las ejecuciones son contenedores `--rm`, sin red y sin dispositivos del robot.
El cliente CVAT usa únicamente localhost en el host; no envía fotos a servicios
externos. Las descargas públicas se hicieron en el build, separadas de los datos.

El entrenador inicial `smoke.py train` no guardaba pesos. No se presenta como
checkpoint recuperable: la prueba nueva es `checkpoint_smoke.py`, que sí guarda
y recarga y verifica cambio efectivo, además de gradientes.

## 4. Resultados realmente observados

Ejecución de datos:
`infra-20261019T112733Z-297050`.
Resultados finales dentro del volumen `app2_checkpoints`:

```text
/checkpoints/infra-20261019T112733Z-297050/verification-background-fix/
  codes/inputs/                     # known.png, blank.png, ambiguous.png
  codes/result.json
  training/20261019T112933.284949Z_checkpoint_roundtrip/
    synthetic_step1.pth
    synthetic_step1.manifest.json
    result.json
    runtime.json
    tensorboard/
  demo/                             # Tres PNG, JSON y events.jsonl
  result.json                       # PASS del recorrido GPU/códigos/demo
```

| Prueba | Resultado observado |
|---|---|
| CVAT exportación/reimportación | Cuatro imágenes/cuatro instancias; máscaras exactas 3072/3072/2560/1792 píxeles; PNG y contornos conservados |
| Conversión | ZIP real de CVAT → dos train/dos valid, clases/IDs/bytes y manifiesto; sin fuga entre grupos declarados |
| Pruebas automáticas | 33 tests de conversor/material + 3 de mapping/background + 2 de errores de registro; todos pasan en el entorno servidor |
| ZXing | MATCH, MISMATCH, NO_READ, AMBIGUOUS, PROCESSING_ERROR y dos casos UNKNOWN pasan con datos sintéticos |
| GPU/entrenamiento | Un optimizer step, una llamada backward, 543 parámetros con gradientes finitos/no nulos; BF16 mixed |
| Actualización | Delta máximo medido `6.98436051607132e-05` en `model.transformer.decoder.layers.0.self_attn.in_proj_weight` |
| Checkpoint | Guardado, SHA256 `77f128367c8a82fa41870ee51b13fe716d1f318544d6ef7908374b2f1801f737`; recarga con todos los tensores iguales |
| Inferencia recargada | Cajas/confianza/máscaras finitas; 100 salidas raw, 100 background, **0 foreground** en esa comprobación sintética |
| Memoria/duración | Máximo Torch reservado 752877568 bytes, asignado 683905024; ~3,00 s para paso/guardado/recarga de esta prueba, no entrenamiento real |
| Demo integrada | Tres imágenes procesadas con inferencia real: AMBIGUOUS, NO_READ y MATCH; cero errores de procesamiento; PNG+JSONL |
| TensorBoard | Releídos eventos de optimizer_steps=1 y delta medido; no servicio web permanente |
| SDK | CVAT SDK 2.79.0 consulta servidor 2.79.0 y ambos proyectos; no altera proyectos |

**Cero foreground es una limitación explícita de esta prueba.** Un solo paso
no entrena un detector útil. PASS significa que el recorrido de software,
datos y checkpoint funciona; no significa precisión ITR o que detecte estos
rectángulos. No ajustar umbrales para fabricar una detección positiva.

Se conservó un fallo inicial de validación: RF-DETR 1.11.2 puede devolver el
canal background `N` en modelos ajustados con `N` clases. Se comprobó contra
la fuente instalada y la salida real. El wrapper excluye sólo ese canal,
registra su recuento y mapea índices contiguos a IDs COCO explícitos; no modifica
el postprocesador vendor ni convierte background en pieza. Las cabezas públicas
COCO tienen otro catálogo y no reciben ese filtro por suposición.

La inferencia medida sigue sin optimizar. No se utiliza esta prueba para
prometer FPS, precisión, tiempo industrial de ciclo o compatibilidad TRT 8.6.

## 5. Ejecutar sólo la demo ya preparada

En el servidor, usa estos archivos sintéticos que ya existen:

```bash
APP2_BASE=/checkpoints/infra-20261019T112733Z-297050/verification-background-fix
APP2_WEIGHTS="$APP2_BASE/training/20261019T112933.284949Z_checkpoint_roundtrip/synthetic_step1.pth"
bash "$HOME/app2/workflow/run_local.sh" --demo \
  --image "$APP2_BASE/codes/inputs/known.png" \
  --output-root "/checkpoints/demo-$(date -u +%Y%m%dT%H%M%SZ)-$$" \
  --model checkpoint --checkpoint "$APP2_WEIGHTS" \
  --identity-scope box --expected-material APP2-SYNTHETIC-MATERIAL-A \
  --synthetic-input
```

Para una secuencia, sustituir `--image ...` por `--sequence .../inputs`.
La entrada real posterior será otro archivo/colección local con su procedencia;
no marcarlo como sintético y no atribuir precisión de piezas al checkpoint
sintético. La interfaz `LocalPerception.predict(PIL.Image)` permite adaptar en
otra fase una cámara integrada, sin acoplar la percepción a movimiento.

Cada salida usa un directorio nuevo y rechaza sobrescritura. Ejecución GPU sólo
durante el comando. No hace falta habilitar modo automático/PICO, ROS, MoveIt
o PLC para esta demo. Interrumpir el proceso propio no envía HOME ni otra acción.

## 6. Identidad de caja, contrato y registro

**Aclaración del operador:** el ID estará en la caja. El ámbito de comparación
es `box`, no serial individual de cada pieza. Falta confirmar referencia/lote,
simbología, ejemplos y reglas del payload; el operador confirma que aún no
se sabe qué contiene. El parser actual es UTF-8 exacto o
un campo JSON configurado explícitamente; no presupone GS1, normalización,
eliminación de espacios o formato del cliente. QR es sólo el caso de prueba.

Lectura → interpretación → comparación son etapas distintas. Una caja bien
identificada no demuestra que no haya mezcla de piezas. La vinculación entre
caja activa y piezas, condiciones de invalidación y cambio de caja requiere
su contrato antes de integrar el ciclo. No hay lógica de control físico para ello.

| Resultado local | Significado / código propuesto |
|---|---|
| MATCH | Un ID interpretable coincide en el ámbito declarado; no valida pieza por forma |
| MISMATCH | ID interpretable distinto; `APP2_WRONG_MATERIAL`, no prueba por sí solo un misread |
| NO_READ | Ningún código válido; `APP2_NO_READ` |
| AMBIGUOUS | Varios IDs distintos; `APP2_AMBIGUOUS` |
| PROCESSING_ERROR | Datos/parser/decodificación/inferencia no procesables; se conserva componente/error |
| UNKNOWN | Falta ID esperado o ámbito confirmado; `APP2_IDENTITY_UNCONFIRMED` |

JSONL conserva aplicación/tarea/UTC/ubicación, esperado/reconocido, resultado y
pass/fail de comparación, no-read, reintentos, excepciones, intervención/paros,
tiempo, versiones y finalización. Añade hashes de fuente/imagen/modelo/dataset.
Los códigos son **propuesta local**, no catálogo aprobado del cliente.
Verificar el diccionario exacto en `demo.py`; un fallo de procesamiento no es
equivalente a material incorrecto.

`misread`, estados físicos de paros/intervención, ubicación y versiones de
robot desconocidas quedan nulos. `cycle_time_s=null`: sólo se mide procesamiento
offline. La calidad de lectura queda nula si ZXing no proporciona confianza;
no sustituirla por la confianza del segmentador. Completion es procesamiento
offline completado/fallido, nunca ciclo físico completado. Caja vacía y destino
preparado quedan UNKNOWN; pose/agarre 3D devuelven CALIBRATION_REQUIRED.

Persistencia inicial: archivos JSONL en SSD, sin daemon de base de datos nuevo.
Retención, buffer/exportación industrial, diccionario definitivo y códigos de
camino bloqueado, paro, recuperación fallida y demás eventos físicos quedan
pendientes. No se inventan tags de PLC ni llamadas de SDK para representar esos
eventos. [Requisitos mínimos de §7](ESPECIFICACION_REV001.md#4-contrato-mínimo-de-datos-descrito-en-7).

## 7. Fuentes, versiones y reversión

Código, recetas y licencias están descritos en el
[README técnico](../../scripts/app2/workflow/README.md). RF-DETR código y Seg Nano
según las fuentes del editor son Apache 2.0; SDK/ZXing/TensorBoard se verifican
por separado. El empaquetado OpenCV y FFmpeg incluye obligaciones propias;
no resumir toda la imagen como si tuviera una sola licencia. Datos reales y
permiso de uso siguen siendo responsabilidad a confirmar con el cliente.

Las versiones resueltas/informes pip de main y SDK se conservan dentro de la
imagen y en evidencia; la derivada no actualiza Torch, NumPy, RF-DETR o drivers.
Sin SAM: no aporta un desbloqueo necesario a esta prueba. No se añaden servicios
pesados ni suscripciones. Los smokes, inferencia y entrenamiento son sin red.

Antes: fuentes/estado Git y recibos del servidor inicial conservados. Después:
fuentes ejecutadas, pruebas, versiones, IDs, exportaciones, resultado y checkpoint
sintético en evidencia privada externa:

```text
../Humanoide-vla-evidence/20261019T112209Z_APP2_REV001_LOCAL_WORKFLOW/
../Humanoide-vla-evidence/app2/specifications/2026-10-19/
```

Los proyectos/tareas demo permanecen deliberadamente en CVAT; no se borran para
dejar un PASS. Para revertir la ampliación, terminar sólo sus contenedores
efímeros, conservar fuentes/recibos/modelos y dejar de usar la imagen derivada.
No borrar datos de CVAT ni volúmenes, ni tocar Ollama o la imagen base. No hay
servicio añadido con autoarranque ni configuración del robot que revertir.
Los paquetes privados anteriores de relevo son instantáneas anteriores a esta
ampliación. Se conserva un overlay actual de fuentes/documentos/especificación
con checksum y otra copia del checkpoint sintético; procedimiento de traslado
en [BACKUP_Y_MIGRACION.md](BACKUP_Y_MIGRACION.md). No asumir que el paquete base
anterior incluye estos scripts o el DOCX nuevo.

## 8. Continuación acordada

La [lista única del plan](PLAN_Y_PREGUNTAS.md#4-lista-principal-de-trabajo)
recoge estados y dependencias. Próximas tres tareas:

1. Obtener etiquetas reales, referencias/confundibles y reglas de asociación
   caja→piezas; confirmar vigencia/criterios MQ1 13-11/MQ2 18-12-2026.
2. Capturar y etiquetar piloto real por sesión/caja/lote, revisar máscaras y
   reservar condiciones independientes para evaluación.
3. Entrenar/evaluar con esos datos y medir lectura e identidad, luego validar
   exportación/paridad/latencia en Orin antes de geometría o manipulación.

El documento exige entrega mínima en inglés y revisión de normas SD; la
documentación operativa del laboratorio en español y estas pruebas sintéticas
no cierran esa aceptación ni certifican seguridad o capacidad de producción.
