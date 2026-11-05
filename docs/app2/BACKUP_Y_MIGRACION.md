# app2 — copias, traslado de PC y recuperación

**ID:** APP2-HANDOFF-20261019. **Fecha/zona:** 19-10-2026, Europe/Madrid.
El traslado documental no cambia servicios. El backup completo de volúmenes
y una restauración de servidor **siguen PENDIENTES**; las recetas de la sección 3
no se han ejecutado. No confundir persistencia en Docker con copia externa.

## 1. Paquete privado preparado para cambiar de PC o agente

**Publicación posterior:** tras el commit/push solicitado, el código y la
documentación actuales se recuperan desde la rama `vision-reconoce` según
[RETOMAR_APP2.md](RETOMAR_APP2.md#recuperar-el-código-y-las-fotografías).
Los paquetes siguientes conservan instantáneas anteriores: no aplicar sus
parches u overlays encima del clon actual por rutina. Git no respalda las
fotos, evidencias, modelos, base de datos CVAT ni credenciales privadas.

**Ampliación posterior del 19-10-2026:** el paquete original sigue siendo una
instantánea válida anterior al DOCX y al nuevo flujo. Para recuperar el estado
de la intervención `APP2-REV001-WORKFLOW-20261019`, conservar además estos dos
archivos privados:

```text
../Humanoide-vla-evidence/20261019T112209Z_APP2_REV001_LOCAL_WORKFLOW/app2_workflow1_fuentes_y_especificacion.tar.gz
../Humanoide-vla-evidence/20261019T112209Z_APP2_REV001_LOCAL_WORKFLOW/app2_workflow1_fuentes_y_especificacion.tar.gz.sha256
```

Contienen el overlay de documentación/fuentes de aquella intervención y el Word
original con sus imágenes ITR, sin contraseñas ni DB. No incluyen el helper de
importación real, las guías posteriores ni las capturas y recibos del trabajo 5.
Esos originales y recibos están en las rutas privadas del
[piloto real](PILOTO_PIEZAS_REALES.md); requieren una copia separada. Tras
restaurar el paquete base como
se explica abajo, en ese **destino nuevo de recuperación**, aplicar el overlay:

```bash
set -euo pipefail
sha256sum -c app2_workflow1_fuentes_y_especificacion.tar.gz.sha256
mkdir overlay_app2_extraido
tar -xzf app2_workflow1_fuentes_y_especificacion.tar.gz -C overlay_app2_extraido
# APP2_DEST es el directorio nuevo creado en la sección 2; no un checkout con trabajo ajeno.
test -d "$APP2_DEST/Humanoide/.git"
cp -a overlay_app2_extraido/workspace/. "$APP2_DEST/Humanoide/"
cp -a overlay_app2_extraido/private/Humanoide-vla-evidence/. "$APP2_DEST/Humanoide-vla-evidence/"
```

Leer entonces [VALIDACION_FLUJO_LOCAL.md](VALIDACION_FLUJO_LOCAL.md). El
checkpoint sintético y sus resultados tienen otra copia privada en
`app2-final-run.tar.gz` dentro de esa misma evidencia; no vienen en el overlay.
No se ha migrado el servidor ni validado una recuperación de su DB.

Desde la raíz del repositorio actual:

```text
../Humanoide-vla-evidence/app2/handoff/app2_relevo_20261019T105234Z.tar.gz
../Humanoide-vla-evidence/app2/handoff/app2_relevo_20261019T105234Z.tar.gz.sha256
```

Se conserva fuera de Git, con acceso privado. Incluye:

- Base Git de la rama `vision-reconoce`, commit
  `06250fb93f47e5a48c93c129819e2b7327b70ca7`, mediante bundle.
- Parche binario del árbol de trabajo respecto a esa base, recetas y documentos
  nuevos de app2. No depende de que estén ya en GitHub.
- Estado Git, manifiesto de archivos/hashes y comandos de restauración.
- Seis fotos originales con manifiesto, incluida la lámina de fábrica.
- Evidencias de inspección de Vision, planificación e instalación del servidor,
  con fuentes, versiones y resultados; huellas públicas de host SSH.

No incluye claves privadas, contraseña CVAT, bases de datos vivas, volúmenes,
imagen Docker del entrenador, pesos ni el ONNX binario. Los recibos de pruebas
no son una copia de los modelos. Tampoco incluye todo el SDK ni todos los datos
históricos del proyecto: el alcance es el relevo de app2. Dos locks locales
preexistentes y ajenos a app2 no se incluyen ni se modifican.

El paquete aún está en este PC. Copiarlo junto con su checksum a otro equipo
o almacenamiento privado autorizado y verificar allí el hash antes de depender
de él. No subirlo a un repositorio público o a servicios cloud de etiquetado.

**Verificación real:** restaurado en una carpeta temporal nueva, sin red ni
servidor: bundle, parche, archivos nuevos y evidencia recuperados; los 31 hashes
de código/documentación y el manifiesto de fotografías pasan. Recibo:
`../Humanoide-vla-evidence/20261019T105234Z_APP2_HANDOFF_DOCS/restore-validation.json`.
Esto verifica el relevo documental; no es una restauración de la base de datos.

## 2. Restaurar en un PC nuevo, manteniendo el mismo servidor

Para el estado actual, preferir el clon de la rama publicada y recuperar aparte
los archivos privados. Lo siguiente restaura exclusivamente la instantánea
histórica del paquete base, con sus cambios locales de aquel momento; el overlay
de la sección 1 amplía esa instantánea hasta el cierre del flujo sintético.
No reinstalar el servidor. El paquete incluye `README_RESTAURAR.md`; procedimiento:

```bash
set -euo pipefail
umask 077
# En la carpeta que contiene ambos archivos transferidos:
sha256sum -c app2_relevo_20261019T105234Z.tar.gz.sha256
tar -tzf app2_relevo_20261019T105234Z.tar.gz
mkdir relevo_app2_extraido
tar -xzf app2_relevo_20261019T105234Z.tar.gz -C relevo_app2_extraido
```

Entrar en la carpeta `app2_relevo_20261019T105234Z` extraída y seguir su README.
La restauración se hace en un directorio **nuevo**, con esta estructura:

```bash
set -euo pipefail
APP2_PACKAGE="$PWD"
APP2_DEST="$HOME/trabajo_app2_recuperado"
test -f "$APP2_PACKAGE/baseline.bundle"
test ! -e "$APP2_DEST"
sha256sum -c SHA256SUMS
mkdir -m 700 "$APP2_DEST"
git clone -b vision-reconoce "$APP2_PACKAGE/baseline.bundle" "$APP2_DEST/Humanoide"
cd "$APP2_DEST/Humanoide"
git bundle verify "$APP2_PACKAGE/baseline.bundle"
git apply --check "$APP2_PACKAGE/tracked-working-tree.patch"
git apply --binary "$APP2_PACKAGE/tracked-working-tree.patch"
tar -xzf "$APP2_PACKAGE/new-files.tar.gz" -C "$APP2_DEST/Humanoide"
cp -a "$APP2_PACKAGE/private/Humanoide-vla-evidence" "$APP2_DEST/"
sha256sum -c "$APP2_PACKAGE/workspace-files.sha256"
git remote set-url origin git@github.com:acuna-luis/humanoide.git
git status --short --branch
(cd ../Humanoide-vla-evidence/app2/reference/2026-10-19 && sha256sum -c SHA256SUMS)
```

Estos comandos no hacen commit ni push y no conectan al robot. El estado
recuperado conserva cambios locales; no usar reset/clean para dejarlo limpio.
El índice Git se documenta en el paquete; el parche recupera los bytes finales
del árbol de trabajo sin volver a preparar cambios staged automáticamente.
No copiar claves privadas SSH: el nuevo PC necesita su propio acceso autorizado.

Una restauración en carpeta temporal permite cotejar código y fotografías.
No demuestra acceso de red desde otro PC ni restaura el servidor. Tras recuperarlo,
seguir [RETOMAR_APP2.md](RETOMAR_APP2.md) para acceso SSH y túnel al CVAT existente.

## 3. Backup completo del servidor: receta para una intervención futura

**No realizado en este relevo.** Requiere una ventana sin edición CVAT ni
entrenamiento escribiendo. Detiene sólo app2-cvat y conserva sus volúmenes.
No detener Ollama, Docker global o el servidor. Leer todo antes de ejecutar;
las transferencias siguientes se lanzan desde un PC con espacio suficiente en
otro almacenamiento privado, nunca dentro del `/home` pequeño del servidor.

La copia completa debe conservar:

| Grupo | Elementos |
|---|---|
| Fuente/configuración | `~/app2/setup`, `~/app2/cvat` y `~/app2/receipts`, locks, freeze y hashes |
| Credenciales | `~/app2/secrets`, en respaldo privado con permisos restrictivos; no publicarlo |
| CVAT, 7 volúmenes | `app2-cvat_cvat_cache_db`, `app2-cvat_cvat_data`, `app2-cvat_cvat_db`, `app2-cvat_cvat_events_db`, `app2-cvat_cvat_inmem_db`, `app2-cvat_cvat_keys`, `app2-cvat_cvat_logs` |
| Entrenamiento, 3 volúmenes | `app2_training_cache`, `app2_datasets`, `app2_checkpoints` |
| Imágenes | Imagen propia `app2-rfdetr:1.11.2-torch2.10.0-cu128`; imágenes CVAT por digest o su exportación para recuperación sin Internet |
| Datos externos | Fotos originales, ZIP COCO, manifiestos de sesiones/clases, backups de tareas/proyectos y resultados copiados al PC |

Las bases de datos se copian **en frío**, con todos los servicios app2-cvat
detenidos; no copiar archivos de Postgres en ejecución. Los entrenadores son
efímeros y no se detienen con `cvat.sh --down`: comprobar aparte que no escriban.
`docker ps` ayuda a identificar procesos, no prueba que nadie abra otro editor.

### 3.1 Inventario y parada del proyecto propio

En el servidor, primero consultar:

```bash
bash "$HOME/app2/setup/install_server.sh" --status
docker ps -a --filter label=com.docker.compose.project=app2-training
docker ps -a --filter label=com.docker.compose.project=app2-cvat
docker volume ls --filter name=app2
docker image inspect app2-rfdetr:1.11.2-torch2.10.0-cu128 --format '{{.Id}}'
df -h /home /var/lib/docker
```

Después de cerrar edición y terminar los trabajos propios de forma controlada:

```bash
bash "$HOME/app2/setup/cvat/cvat.sh" --down
docker ps --filter label=com.docker.compose.project=app2-cvat
docker ps --filter label=com.docker.compose.project=app2-training
```

No continuar si quedan escritores. Registrar la parada y avisar a otros usuarios.

### 3.2 Exportación privada desde el PC

Las siguientes órdenes son **plantillas pendientes de ensayo**. Sustituir el
destino, verificar su capacidad y no ejecutar sobre un directorio existente.
Se usa la imagen ya instalada como herramienta tar, sin GPU ni red dentro del
contenedor. El acceso root temporal es sólo para leer propietarios/archivos de
estos volúmenes, montados como sólo lectura; no monta el host ni cambia permisos.

```bash
set -euo pipefail
umask 077
APP2_BACKUP=/ruta/privada/externa/app2_servidor_fecha
mkdir -m 700 "$APP2_BACKUP"
ssh -p 2649 luisacuna@192.168.1.43 \
  'tar --numeric-owner -C "$HOME" -czf - app2/setup app2/cvat app2/receipts app2/secrets' \
  > "$APP2_BACKUP/server-files.tar.gz"
ssh -p 2649 luisacuna@192.168.1.43 \
  'docker image save app2-rfdetr:1.11.2-torch2.10.0-cu128' \
  > "$APP2_BACKUP/training-image.tar"
for APP2_VOLUME in \
  app2-cvat_cvat_cache_db app2-cvat_cvat_data app2-cvat_cvat_db \
  app2-cvat_cvat_events_db app2-cvat_cvat_inmem_db app2-cvat_cvat_keys \
  app2-cvat_cvat_logs app2_training_cache app2_datasets app2_checkpoints
do
  ssh -p 2649 luisacuna@192.168.1.43 \
    "docker volume inspect '$APP2_VOLUME' >/dev/null && docker run --rm --network none --read-only --user 0:0 --cap-drop ALL --cap-add DAC_OVERRIDE --security-opt no-new-privileges --mount type=volume,source='$APP2_VOLUME',target=/data,readonly --entrypoint tar app2-rfdetr:1.11.2-torch2.10.0-cu128 --numeric-owner -C /data -cf - ." \
    > "$APP2_BACKUP/$APP2_VOLUME.tar"
done
(cd "$APP2_BACKUP" && sha256sum server-files.tar.gz training-image.tar app2*.tar > SHA256SUMS)
```

Guardar además inventario, estado de parada y fecha. Para una copia sin Internet,
exportar también las diez imágenes CVAT fijadas por `images.lock.yml`; el digest
por sí solo no contiene sus bytes. Los modelos y el ONNX quedan dentro de
`app2_checkpoints.tar`; comprobar que están realmente presentes y cotejar sus
hashes. Conservar modos/UID/GID al restaurar. Los tars pueden ser grandes.

Comprobar códigos de salida, checksums y listado legible de cada tar, y hacer una
prueba de recuperación aparte. Un fichero creado por una transferencia fallida
puede estar truncado. Esta receta no es una validación de restauración.
Al acabar la ventana, si se pretende reabrir el editor, en el servidor original:

```bash
bash "$HOME/app2/setup/cvat/cvat.sh" --up
bash "$HOME/app2/setup/cvat/cvat.sh" --status
```

### 3.3 Nuevo servidor o recuperación tras pérdida

1. Inventariar Ubuntu/arquitectura, Docker/Compose, GPU/driver/runtime NVIDIA,
   discos y acceso. No instalar encima de otra aplicación ni cambiar drivers
   por rutina. La imagen del entrenador es x86_64, no es una imagen para Orin.
2. Verificar hashes externos; cargar la imagen propia con `docker image load`
   desde su tar y comprobar ID. Recuperar la fuente/configuración exactas y
   las imágenes CVAT del lock. No ejecutar el instalador ni arrancar una versión
   nueva contra una base de datos recuperada.
3. Crear los diez volúmenes con sus nombres/etiquetas originales sólo si no
   existen. Recuperar cada tar en un volumen vacío, preservando UID/GID/modos
   con un contenedor temporal y permisos limitados de restauración. **Rechazar
   un destino existente o no vacío**: nunca sobrescribir la única copia buena.
4. Recuperar `~/app2` con sus permisos. Mantener la contraseña privada en 0600
   y revisar los bind mounts públicos; no aplicar modos 0700/0600 a toda la
   fuente vendor que leen los contenedores.
5. Comprobar composición, nombres de volúmenes y versiones antes del primer
   `--up`. Si todo coincide, activar sólo app2-cvat; luego verificar UI/API,
   autorización, login y acceso a tareas/etiquetas recuperadas.
6. Ejecutar una prueba sintética independiente y una reimportación COCO, revisar
   máscaras de un lote real recuperado y verificar lectura de checkpoints.
   Comprobar GPU sin reentrenar ni sobrescribir modelos. Documentar resultado.

No se ofrece una orden automática de restauración que sobrescriba volúmenes.
Este paso necesita su propia receta verificada al ensayarlo en destino vacío.
Hasta entonces, el estado del backup completo y su recuperación es PENDIENTE.

## 4. Qué registrar en cada relevo posterior

- Commit/base y cambios locales incluidos; receta/imagen/lock/freeze utilizados.
- Versiones de dataset, catálogo, sesiones/splits y hashes; tareas CVAT y exportaciones.
- Rutas de ejecución/modelos, resultados, fallos y métricas realmente medidas.
- Ubicación de copias externas, checksum, fecha y última restauración ensayada.
- Servicios detenidos/activos, comandos ejecutados, reversión y siguiente paso.

Volver a crear el paquete si cambian código o documentos. La copia del
19-10-2026 es una instantánea, no sincronización continua ni un respaldo
automático de etiquetas o modelos futuros.
