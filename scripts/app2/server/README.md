# Instalación local de app2 en el servidor

Destino: `ssh -p 2649 luisacuna@192.168.1.43`, x86_64/RTX6000 Ada.
Esta receta no se ejecuta en Motion/Vision. No instala drivers o paquetes del
host, no altera Ollama y no contiene imágenes o contraseñas privadas.

**Para trabajar con la instalación existente**, seguir la
[guía de relevo](../../../docs/app2/RETOMAR_APP2.md) y consultar `--status`.
Cambiar de PC no requiere volver a ejecutar `--install`.
[Estado realmente instalado y probado](../../../docs/app2/SERVIDOR_LOCAL_INSTALACION.md).

## Aplicación reproducible

Desde la raíz del repositorio en el PC:

```bash
tar --exclude=__pycache__ --exclude='*.pyc' -czf /tmp/app2-server-recipes.tar.gz -C scripts/app2/server .
scp -P 2649 /tmp/app2-server-recipes.tar.gz luisacuna@192.168.1.43:app2-server-recipes.tar.gz
ssh -p 2649 luisacuna@192.168.1.43
```

En el servidor, conservar primero cualquier receta/estado anterior de app2 si
se está actualizando. Para una instalación nueva:

```bash
umask 077
mkdir -p "$HOME/app2/setup"
tar -xzf "$HOME/app2-server-recipes.tar.gz" -C "$HOME/app2/setup"
bash "$HOME/app2/setup/install_server.sh" --check
bash "$HOME/app2/setup/install_server.sh" --install
```

El instalador descarga fuentes/imágenes fijadas, crea exclusivamente recursos
app2, espera la API, prepara el administrador y comprueba anotación/exportación
COCO con una imagen sintética. Después construye el entorno RF-DETR, descarga
pesos públicos y comprueba inferencia y un paso de entrenamiento sin red.
No entrena un detector de piezas reales. No hay un entrenador permanente.
Un fallo conserva volúmenes/evidencia; no ejecuta una limpieza o rollback global.

Las imágenes CVAT quedan fijadas en `~/app2/cvat/images.lock.yml`; conservar
este archivo con el respaldo. Si existe una copia versionada junto a `cvat.sh`,
el instalador la usa en instalaciones nuevas en lugar de resolver etiquetas.
El build RF-DETR guarda todas las versiones resueltas y el informe de pip dentro
de la imagen. Su ID instalado y copias de esas versiones se registran en el
informe de la intervención; reconstruir con versiones resueltas antes de
comparar otro entorno. Los paquetes apt también deben cotejarse al actualizar.

## Abrir el editor

Desde el PC, dejar abierta esta terminal:

```bash
ssh -p 2649 -N -L 18080:127.0.0.1:18080 luisacuna@192.168.1.43
```

Abrir `http://localhost:18080` en el navegador. Usuario `app2_admin`.
La contraseña aleatoria está sólo en el archivo privado del servidor
`~/app2/secrets/cvat-admin.json`, permisos0600. Se puede consultar en una
terminal privada del propietario; no copiarla a Git ni a informes.
El servicio sólo escucha en loopback: no se publica el editor en todas las
interfaces del servidor. Cerrar el túnel no detiene CVAT.

## Estado y datos

```bash
# En el servidor:
bash "$HOME/app2/setup/install_server.sh" --status
docker ps --filter label=com.docker.compose.project=app2-cvat
docker volume ls --filter name=app2
```

CVAT mantiene siete volúmenes propios bajo el DockerRootDir del SSD grande.
El entrenador usa `app2_training_cache`, `app2_datasets` y `app2_checkpoints`;
el dataset se monta sólo lectura al entrenar. No escribir datos voluminosos en
`/home`, que pertenece al volumen pequeño, ni editar los directorios internos
de Docker manualmente.200GiB es presupuesto inicial, no una cuota ya aplicada.

Las recetas detalladas están en [cvat/README.md](cvat/README.md) y
[training/README.md](training/README.md). Para iniciar el piloto aún hacen
falta fotos variadas, polígonos por instancia, clases verificadas y particiones
COCO train/valid revisadas. No confundir pesos COCO públicos o un smoke sintético
con el reconocimiento de una referencia industrial ya entrenado.

## Detener/revertir sin perder datos

```bash
# Sólo app2; conserva base de datos, imágenes, etiquetas y modelos:
bash "$HOME/app2/setup/cvat/cvat.sh" --down
```

Los entrenadores son procesos `run --rm`: terminan al finalizar su orden.
No usar `docker system prune`, `volume prune`, `down -v` o comandos sobre los
contenedores Ollama. Conservar volúmenes, credenciales privadas, lock de imágenes
y respaldos de CVAT antes de cualquier retirada definitiva. Las copias en el
mismo SSD no sustituyen un respaldo en otro almacenamiento propio.
