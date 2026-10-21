# app2 — instalación del servidor local

**20-10-2026 — datos rescatados, firmware datos8B verificado; rollback CSM/EFI verificado; APP2/CVAT operativo; datos y acceso local verificados.**
Se verificaron 22 TAR (47.034.378.240 bytes) de los 20 volúmenes persistentes,
recetas y definiciones Docker en el SSD sano del SO. De ellos, 13 TAR no Ollama
(1.373.347.840 bytes) y el recibo están también en el PC con los 13 SHA coincidentes.
Ollama permanece respaldado en el SSD del SO; no tiene tercera copia en el PC.

**PostgreSQL: PASS** en una copia aislada del PC: recuperación física y dump
restaurado en otra DB vacía; 4 tareas, 4 trabajos y 9 formas globales, con
tarea 5 / trabajo 5 / shape 10 del frame 1 presentes. No significa 9 piezas reales.
**Medios de tarea 5: PASS**: ambos PNG originales, CRC, decodificación completa,
dimensiones, hashes originales y manifiesto coinciden. Esto no es una prueba
completa de la UI/API de CVAT; Docker/CVAT del servidor siguen detenidos.

Las capas escribibles de 20 contenedores y metadatos ya están respaldadas:
200.683.520 bytes, compare PASS y copia en PC con SHA coincidente. Origen desmontado,
cinco protecciones conservadas. No incluye capas inmutables ni imagen completa.
**Estado actual: APP2/CVAT operativo y verificado.** Configuración, montaje y
servicios restaurados; veinte contenedores conservados y running. CVAT `2.79.0`,
API/UI HTTP 200. API autenticada confirma 4 tareas, 4 trabajos y 9 formas globales;
tarea 5 / trabajo 5, shape 10 del frame 1 presente. Originales PNG con hashes
exactos y chunk del editor con 2 JPEG/CRC correcto.

Túnel del PC activo en `localhost:18080`, PID `1042428`; API local y trabajo 5
HTTP 200. [Retomar anotación/revisión humana](http://localhost:18080/tasks/5/jobs/5).
No sudo pendiente ni recuperación que repetir. No se modificaron anotaciones,
no se entrenó un modelo real y no se conectó o movió el robot en esta recuperación.
Conservar backups/undo; fiabilidad a largo plazo pendiente de observación.
[Incidente y punto de reanudación](../incidents/2026-10-20_APP2_SSD_DOCKER_NO_RESPONDE.md).
No reinstalar ni reimportar sobre el origen para resolver la incidencia.

**ID:** APP2-SERVER-INSTALL-20261019.
**Fecha/zona:**19-10-2026, Europe/Madrid.
**Estado:** INSTALADO Y VERIFICADO en servidor. CVAT, inferencia GPU, un paso
de entrenamiento sintético sin red y exportación ONNX pasan. No se ha entrenado
un detector de piezas reales ni desplegado app2 en el robot.

**Uso diario y relevo:** [retomar desde otro PC/agente](RETOMAR_APP2.md),
[datos y entrenamiento](DATOS_Y_ENTRENAMIENTO.md),
[copias y migración](BACKUP_Y_MIGRACION.md). No reinstalar para retomar.

**Ampliación posterior:** [APP2-REV001-WORKFLOW-20261019](VALIDACION_FLUJO_LOCAL.md)
completa el recorrido sintético con conversor, checkpoint/recarga, ZXing,
trazabilidad y demo. Conserva esta imagen base y sus servicios. Las limitaciones
de este informe describen la instalación inicial; el informe nuevo recoge los
pasos ahora cerrados.

## Destino y alcance

Usuario autoriza instalar lo necesario para el [plan local](PLAN_LOCAL_RECURSOS_Y_TIEMPOS.md)
en `ssh -p 2649 luisacuna@192.168.1.43`. Directorio de recetas y estado pequeño:
`/home/luisacuna/app2`; almacenamiento voluminoso mediante Docker en su SSD
dedicado. No hay cambios de robot, driver del host, red, cuentas cloud o datos
reales enviados a servicios externos. Los dos contenedores Ollama previos se
conservan; el entrenamiento debe convivir con su uso de GPU.

Inventario previo: Ubuntu24.04.5, x86_64, Threadripper PRO5975WX32 núcleos,
RAM503,51GiB, RTX6000 Ada49140MiB/5500MiB usados, driver580.178.04;
Docker29.8.1/Compose5.5.1 y runtime nvidia disponibles. El directorio app2 no
existía y el puerto18080 estaba libre. Raíz/home con77,71GiB libres; Docker
en NVMe separado con1,65TiB libres. Estos valores son instantáneos.

## Componentes y reproducción

Fuente reproducible: [scripts/app2/server](../../scripts/app2/server/README.md).
El instalador se ejecuta en el servidor y permite `--check`, `--install` y
`--status`; no publica comandos físicos ni toca servicios de Motion/Vision.

| Componente | Fuente/versión y destino | Estado de validación |
|---|---|---|
| CVAT Community | v2.79.0, commit9176834830e2e931a8d3a6857dcf43c6cc0ee927; `~/app2/cvat/upstream` | API, anotación y COCO VERIFICADOS |
| Imágenes CVAT | Diez imágenes únicas fijadas en `~/app2/cvat/images.lock.yml` y [lock versionado](../../scripts/app2/server/cvat/images.lock.yml) | Descargadas;18 contenedores finales running, sin bucle de reinicio |
| API/UI CVAT | Proyecto app2-cvat,18 servicios,7 volúmenes; sólo127.0.0.1:18080 | UI/API200, OPA bundle200; login y exportación pasan |
| Cuenta local | app2_admin; contraseña aleatoria en `~/app2/secrets/cvat-admin.json`,0600 | Creada y login comprobado; no reproducida aquí |
| Entrenador | RF-DETR1.11.2, PyTorch2.10.0/torchvision0.25.0, CUDA12.8/cuDNN9 | Construido; GPU y backward RF-DETR VERIFICADOS |
| Base del entrenador | Imagen oficial PyTorch, digestb85566342b86d13a67712e9315d40cdc2dad7f8d86df1aff3831f80835edbcca | Descargada y fijada; driver580 del host intacto |
| Pesos | RF-DETR Seg Nano público,134545398 bytes; MD5 validado y SHA256a44613a4…35fb99b | Precache CPU e inferencia GPU pasan; manifiesto en caché/evidencia |
| Dataset de piezas | Ninguno importado en esta instalación | Captura/etiquetado y entrenamiento app2 reales pendientes |

El entorno GPU usa un proceso efímero,8CPU/32GiB RAM, usuario10001 y volúmenes
`app2_training_cache`, `app2_datasets`, `app2_checkpoints`. Los comandos de
inferencia/entrenamiento usan `network_mode: none`; la descarga explícita de
pesos públicos es un comando separado sin acceso al dataset. No se instala
TensorRT en este servidor ni se genera un engine RTX para copiarlo a Orin.

Imagen propia instalada: `app2-rfdetr:1.11.2-torch2.10.0-cu128`, ID
`sha256:af168d95cd04b99fc107652ec11834d69f5dfdf75f98e5bf568cf758eb928ba0`,
9732275036 bytes (~9,06GiB). Dependencias resueltas y artefactos de pip en
`environment.freeze.txt`/`install-report.json` dentro de la imagen y en evidencia.
Transformers5.17.0, Hub1.16.0, PEFT0.21.2 y Click8.3.1 fijados en la receta.

## Acceso del operador

En una terminal del PC, mantener abierto:

```bash
ssh -p 2649 -N -L 18080:127.0.0.1:18080 luisacuna@192.168.1.43
```

Abrir `http://localhost:18080`, usuario `app2_admin`. La contraseña se consulta
privadamente en el archivo indicado del servidor. La interfaz no se publica
directamente en todas sus interfaces. Cerrar el túnel no detiene CVAT.

Para consultar las credenciales en otra terminal privada del PC:

```bash
ssh -p 2649 luisacuna@192.168.1.43 'cat "$HOME/app2/secrets/cvat-admin.json"'
```

No pegar su contenido en Git, chats o incidencias. El túnel del comando anterior
se comprobó desde este PC con API200/versión2.79.0 y se cerró al terminar la
prueba; no se dejó un proceso de acceso permanente ni se cambió la red.

## Incidencias de instalación resueltas en la receta

1. **Permisos de configuraciones públicas:** la extracción no privilegiada con
   umask077 dejaba archivos600/directorios700. Vector/Grafana no podían leer
   sus bind mounts y reiniciaban. La receta usa ahora `tar --same-permissions`
   para el archivo vendor previamente verificado por SHA256. En esta primera
   extracción se restauró lectura/traversal sólo en fuentes públicas montadas
   desde el árbol upstream; no en secretos ni directorios del usuario. Se
   reiniciaron exclusivamente esos dos contenedores nuevos de app2.
2. **Negociación API:** CVAT2.79 responde406 a `Accept: application/json` en
   estos endpoints. El verificador usa `application/vnd.cvat+json`, y `*/*`
   para descargar el ZIP. No era una contraseña incorrecta.
3. **Autorización interna:** limitar ALLOWED_HOSTS sólo a localhost bloqueaba
   la descarga de políticas OPA desde `cvat-server:8080`, causando500 en API
   autenticada. El override incluye también los aliases internos `cvat-server`
   y `cvat_server`; no se desactiva la autorización. Los aliases de red ya
   estaban en upstream: los avisos iniciales no demuestran pérdida de aliases.
4. **Python de la imagen PyTorch:** la base usa Python de sistema con PEP668.
   Se crea `/opt/app2/venv` con acceso a los paquetes base para reutilizar Torch,
   y se instalan las dependencias nuevas allí. No se fuerza pip sobre Python
   del host ni se usa `--break-system-packages`.
5. **Dependencias transitivas:** Spin heredado exige Click<8.4; Hub moderno
   requiere Click>=8.4.2. Se fijan Transformers5.17.0, Hub1.16.0 y Click8.3.1
   dentro de los rangos de RF-DETR, manteniendo `pip check` y sin borrar Spin.
6. **Caché de kernels:** `/cache/xdg` provenía del build con propietario root.
   La inferencia funcionaba pero no podía crear su caché JIT. El helper
   `training/init_cache.sh` inicializa únicamente ese subárbol del volumen
   público app2_training_cache para UID10001, en contenedor CPU temporal sin
   red ni montajes de dataset/host. Prueba GPU posterior sin ese aviso.

Se conservan fallos y correcciones en evidencia. No omitir estos contratos al
recrear la instalación ni repetir pruebas fallidas sin resolver su causa.

## Verificación de aceptación

| Prueba | Resultado observado |
|---|---|
| UI/API y autorización | HTTP200 para UI/about; versión2.79.0, cuenta autenticada y OPA bundles200 |
| Anotación y exportación | PNG128×96, guardar/releer polígono, exportar COCO;1 instancia/3072px de máscara exacta; tarea propia eliminada |
| CUDA/inferencia | Backward tensor CUDA, NMS torchvision e inferencia de segmentación con salidas finitas; máscara100×312×312; sin red |
| Entrenamiento | RF-DETR real,1 optimizer step,543 parámetros con gradientes finitos/no nulos; BF16 mixed; COCO exclusivamente sintético; sin red |
| ONNX | Opset17/IR8, entrada1×3×312×312; checker y ejecución ONNX Runtime CPU pasan sin red; grafo122825723 bytes |
| Aislamiento | Sólo127.0.0.1:18080;18 servicios app2 running; ningún entrenador queda ejecutándose |
| Acceso desde PC | Túnel SSH temporal y API200/versión2.79.0 comprobados; túnel de prueba cerrado |
| Servicios anteriores | IDs de ambos Ollama conservados y arranque anterior a la intervención; GPU final5500MiB/0%, igual a lectura inicial |

ONNX público de prueba en el volumen app2_checkpoints:
`smoke/20261019T104005.285654Z_export/onnx/app2_seg_nano_312_public_smoke.onnx`,
SHA256 `156ecce6b816f89e586362a7d9a0c725b03263b0bf0251fe166439f22512c804`.
Es un grafo estático de prueba. Su ejecución CPU no demuestra paridad numérica,
precisión o compatibilidad con TensorRT8.6; esas verificaciones siguen pendientes.

El entrenamiento sintético reservó ~718MiB de CUDA según Torch. No representa
batch automático, escenas con muchas instancias o consumo total de la GPU.
Los tiempos de una sola inferencia/paso no son un benchmark ni una estimación
de épocas completas. Medir el piloto real de2–5 épocas antes de presupuestarlo.

Al cerrar:~1,64TiB disponibles en SSD Docker y~77,56GiB en raíz/home. La variación
observada de Docker durante la intervención fue~14,14GiB, incluyendo imágenes
y cachés; raíz creció~153MiB. Aún no hay dataset real o retención de checkpoints
de entrenamiento.200GiB sigue siendo presupuesto de crecimiento, no una cuota.

Estos checks verifican software. No demuestran identificación de piezas reales,
precisión, latencia en robot o compatibilidad del modelo final con TRT8.6.

## Respaldo, reversión y evidencia

Antes: inventario/estado de contenedores/imágenes/volúmenes/redes y copias de
documentación/cambios locales previos. No había instalación app2 que respaldar.
Después: recetas, locks, versiones reales, resultados, estados y hashes se
conservan en evidencia junto con este informe. Archivos privados y contraseñas
fuera de Git. La imagen propia no se ha publicado en un registro externo.

Evidencia PC:
`../Humanoide-vla-evidence/20261019T101640Z_APP2_SERVER_INSTALL/`.
Evidencia de pruebas en servidor: `~/app2/receipts/` y volumen
`app2_checkpoints`. Los originales de fábrica/cámaras permanecen en su archivo
privado previo; no se han usado en los smokes sintéticos.

Para detener sólo el servicio nuevo, conservando datos:

```bash
# En el servidor:
bash "$HOME/app2/setup/cvat/cvat.sh" --down
```

El entrenador termina al salir su comando. No usar limpiezas globales ni
`down -v`. Para retirar definitivamente datos/modelos, revisar y respaldar
antes cada volumen propio. No hay configuración de robot que revertir.

**Punto de reanudación:** abrir CVAT y preparar un piloto de30–50 escenas diversas, polígonos y
referencias verificadas; separar train/valid antes del primer entrenamiento real.
