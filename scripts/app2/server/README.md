# Instalación local de app2 en el servidor

Destino: `ssh -p 2649 luisacuna@192.168.1.43`, x86_64/RTX6000 Ada.
Las recetas de instalación no se ejecutan en Motion/Vision, no instalan drivers
o paquetes del host, no alteran Ollama y no contienen imágenes o contraseñas
privadas. El mantenimiento de almacenamiento descrito al final tiene su alcance
y autorización registrados por separado.

**Estado de mantenimiento del 20-10: APP2/CVAT operativo y verificado.**
Recuperación, firmware, rollback, montaje y servicios comprobados. Veinte
contenedores conservados y running; CVAT API/UI, anotaciones, medios y túnel del PC
verificados. Ningún sudo pendiente para continuar. Retomar anotación/revisión humana;
no reinstalar ni repetir recuperación. Fiabilidad a largo plazo pendiente de observación.

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

## Mantenimiento vigente — 20-10-2026

**APP2/CVAT operativo y verificado.** Firmware datos `8B2QJXD7`, SO conservado en
`4B2QJXD7`, CSM/EFI restaurados y recuperación offline/postcheck sin avisos.
Configuración original y EXT4 RW restaurados; veinte contenedores conservan IDs,
imágenes, políticas y montajes, todos running/restart 0. Docker/socket/containerd
activos/enabled, ninguna unidad fallida; ambos Ollama autoiniciados.

CVAT API/UI HTTP 200; API autenticada confirma 4 tareas, 4 trabajos y 9 formas
globales, tarea 5 / trabajo 5 / shape 10 del frame 1 presente. Dos originales PNG
con hashes exactos; chunk del editor con 2 JPEG y CRC correcto. Túnel PC activo
`localhost:18080`, PID `1042428`; API local y trabajo 5 HTTP 200.
[Continuar el piloto](http://localhost:18080/tasks/5/jobs/5),
[comando y cierre del túnel](../../../docs/incidents/2026-10-20_APP2_SSD_DOCKER_NO_RESPONDE.md#túnel-del-pc-estado-y-reversión),
[receta SSH portable](../../../docs/app2/RETOMAR_APP2.md#3-retomar-hoy-con-el-servidor-existente).

No sudo pendiente, anotaciones de prueba, entrenamiento real o movimiento del robot.
Conservar backups/undo. Fiabilidad a largo plazo pendiente; no repetir recuperación
para retomar. [Checker](storage_mount_check.py), [recuperación](OFFLINE_RECOVERY.md).

### Antecedentes de esta intervención

- **Persistencia verificada:** 22 TAR de los 20 volúmenes, recetas y definiciones,
  47.034.378.240 bytes, compare/SHA correctos y origen desmontado. 13 TAR no Ollama
  y recibo también en PC con hashes coincidentes; Ollama sin tercera copia PC.
- **PostgreSQL PASS:** [verify_pg_rescue.py](verify_pg_rescue.py) recuperó una copia
  física y restauró su dump en otra DB vacía: 4 tareas, 4 trabajos, 9 formas globales;
  tarea 5 / job 5 / shape 10 / frame 1 presentes. Tests versionados correctos,
  contenedor temporal eliminado y originales intactos.
- **Medios del piloto PASS:** ambos PNG originales de tarea 5 pasan CRC,
  decodificación, dimensiones, hashes y manifiesto. UI/API de CVAT completo pendiente.
- **Capas escribibles respaldadas:** [storage_writable_rescue.py](storage_writable_rescue.py)
  desplegado, 6 tests PASS y backup real de 20 contenedores/metadatos comparado.
  writable-layers.tar: 200.683.520 bytes, SHA bf4f0821…5699, copia PC con el mismo SHA.
  Fuente desmontada y cinco máscaras conservadas; no capas inmutables ni imagen SSD.
- **Host recuperado por BMC:** [receta BMC](BMC_RECUPERACION_KVM.md). Sesión web
  autenticada y preestado respaldado; ACPI power=5 terminó con power=0 a las
  09:06:38 UTC. Encendido power=1 a las 09:08:27,993 UTC sólo desde 0; SSH Ubuntu
  vuelve 09:12:34 UTC, boot 97a5c584-ff68-4e18-b6b1-c479951083be. Sin hard reset,
  force-off o reset BMC; credenciales/cookies sólo privadas.
- **Check postboot:** CHECK_OK_NO_MOUNT, datos 187F en /dev/nvme0n1p1 y SO 095A
  identificados. A las 09:13:07 UTC: ambas NVMe live4B2QJXD7, cinco máscaras/inactivo,
  origen sin montar y guardas PASS. Flag setup UEFI false. Consola/ISO ya verificados como se detalla abajo.
- **KVM y medio listos:** navegador limpio aislado/SPKI sólo BMC, PID665887,
  OPEN 12/12 muestras/120 s, Enter vacío efectivo en consola aisrv login. Segundo
  adjunto ISO y SHA sudo completo f05508…93d5 verificados en /dev/sr0 de 50 MiB.
  Sin confianza global del SO o paquetes cambiados. El reset previo fue sólo del
  servicio KVM y conservó el mismo boot del host.
- **Secuencia previa al flash, ahora completado según vendor:** [receta Samsung](FIRMWARE_SAMSUNG_990_PRO.md). Comando
  único guardas y sudo reboot a firmware-setup ejecutado y confirmado por el operador.
  UEFI vivo/teclado funciona; BIOS1602x64/build09/04/2024. Sólo Launch CSM Enabled
  revisado como único cambio Disabled→Enabled y confirmado con OK/Enter en F10;
  reset/POST observado; ahora Ubuntu activo, readback UI CSM aún pendiente. Rollback a CSM Disabled y
  comprobar Primary Display Discrete tras prueba obligatorio. Otros campos no
  editados; la escritura posterior sólo datos187F queda registrada en el estado actual. Snapshot local de fuentes/patch/manifest de las 09:43:56 UTC
  conservado en evidencia, sin reemplazar las copias de datos. No actualizar SO095A
  que conserva los backups de Ollama, ni ambos SSD a la vez.

[storage_maintenance.py](storage_maintenance.py) conserva las guardas y su respaldo.
[storage_rescue.py](storage_rescue.py), versión ec8e… / 20.378 bytes / 0600, hizo el
inventario RO y backup de todos los volúmenes mediante --backup --all-volumes.
No retirar máscaras o arrancar Docker para probar. El
[incidente](../../../docs/incidents/2026-10-20_APP2_SSD_DOCKER_NO_RESPONDE.md)
conserva rutas, hashes, preestado, aplicación, cleanup y reversión. Las fuentes
posteriores al backup están también preservadas en PC/recetas. Datos privados fuera
de Git. No repetir backups, transferencias o pruebas PostgreSQL ya verificados.

### Registro histórico de preparación — no es el estado vigente

<details>
<summary>Etapas previas conservadas; no ejecutar sus comandos como siguiente paso sin consultar el estado vigente</summary>

### HISTÓRICO — Mantenimiento del SSD de Docker — incidencia del 20-10-2026

Receta específica de `aisrv`/UUID comprobado, no un instalador genérico:
[storage_maintenance.py](storage_maintenance.py). [Incidente, autorización,
comandos, backup y reversión](../../../docs/incidents/2026-10-20_APP2_SSD_DOCKER_NO_RESPONDE.md).
`--check` es lectura; `--prepare` root conserva fstab/unidades y prepara un arranque
sin Docker ni automontaje del SSD. No apaga, repara, desmonta ni inicia servicios.
El apagado se solicita por separado tras éxito; `--restore-config BACKUP` exige
hashes y conserva cambios ajenos, sin arrancar Docker. No usar la restauración
antes de valorar el rescate. [Tests offline](tests/test_storage_maintenance.py).

### HISTÓRICO — Rescate selectivo y firmware — fase autorizada, aún sin ejecución

El20-10 el operador autoriza las actualizaciones necesarias con cautela. La
secuencia es preservar datos esenciales y comprobar su recuperación, preparar
firmware oficial compatible para el SSD de datos187F y mantener separado el
SSD del SO 095A si conserva la única copia. No actualizar ambos SSD a la vez.

Preestado `authorized-maintenance-before.json`: mismo bootcebc…, SSD presente,
cinco unidades inactive/masked, fstab protegido y origen sin montar. Fuentes
locales disponibles; helper ya desplegado/check verificado, ejecución privilegiada pendiente:

- [storage_rescue.py](storage_rescue.py): `--check` no monta; `--inventory`
  requiere root y monta temporalmente el UUID/serial esperado con
  `ro,noload,nodev,nosuid,noexec` para medir volúmenes; `--backup` copia
  selectivamente CVAT, datasets/checkpoints y recetas del servidor al SO sano.
  Conserva16GiB libres y añade la caché sólo si cabe en el modoAPP2. Con
  `--all-volumes`(compatible con inventory/backup) incluye todos los volúmenes
  legibles y se niega a continuar si no caben; no descarta ninguno para encajar. En ambos modos privilegiados
  verifica montaje y desmonta normalmente al terminar; un fallo de limpieza se
  comunica y no se fuerza ni se oculta. [Pruebas](tests/test_storage_rescue.py).
- El backup conserva UID/GID/ACL/xattrs, compara cada tar contra el origen y
  guarda hashes/recibo privados. Ese resultado no demuestra restauración de
  PostgreSQL ni respaldo de otros volúmenes del servidor. El gate de firmware
  permanece sin liberar para datos importantes que no cubra esa selección.
- [Preparación de firmware Samsung990PRO](FIRMWARE_SAMSUNG_990_PRO.md): ISO
  oficial 8B2QJXD7 descargada e inspeccionada en el PC,52.428.800bytes,
  SHA256f05508f3228960fc1501fe5a27d3a826377332afc8c021aac44487c8fd1c93d5.
  Es checksum local, no firma publicada del fabricante. No se ejecutó su
  actualizador, escribió USB o aplicó firmware; UEFI/SecureBoot/ASUS pendientes.

Versión actual desplegada: /home/luisacuna/app2/maintenance/storage_rescue.py,
20378bytes,0600,SHA256
ec8e727b23d2288ac46be24d4c0ab8867f46100a38a9578ec83a781cebffcee8.
v1 conservada/verificada en
storage_rescue.before-all-volumes.935ec1875f9f.py antes del cambio atómico.
22 tests offline pasan y --check real devuelve CHECK_OK_NO_MOUNT.

El inventario real anterior midió20 volúmenes y terminó con desmontaje normal y
comprobación posterior sin montaje. Todos los persistentes estiman51.843.033.088B,
caben en82.682.867.712Blibres reservando16GiB. El operador recibió
`--backup --all-volumes` con salida privadarescue-backup-20261020T075733Z.log;
backup observado EN CURSO, resultado final todavía pendiente. No equivale a imagen SSD, respaldo de capas
escribibles o restauración de PostgreSQL comprobada.
El
[incidente](../../../docs/incidents/2026-10-20_APP2_SSD_DOCKER_NO_RESPONDE.md)
conservará los logs reales, ruta/hash desplegados, recibos y cleanup antes de
pasar de «fuente disponible» a «instalado/probado».

La restricción actual es **sólo SSH**, sin monitor/teclado/USB disponibles. La
preparación de ISO y el rescate selectivo siguen autorizados. Aplicar firmware
espera consola y método oficial compatible; no se sustituye por enviar un
binario extraído mediante SSH. La lectura rescue-tools-readonly.json detecta /dev/ipmi0/sysfsipmi0 y drivers
IPMI; ipmitool ausente. La interfaz local existe, pero configuración/acceso,
credenciales y disponibilidad de consola BMC siguen pendientes, sin cambios.
GNUtar1.35,rsync,dumpe2fs ydebugfs ya están presentes; no se instalaron aquí.

IPMI sysfs identifica firmwareBMC 1.32/IPMI 2.0; no acredita consola o acceso.
Una simulación apt propone3paquetes nuevos para ipmitool y ninguna actualización
ni borrado; no hay instalación real ni cambio de configuración BMC.

La inspección delDEB deipmitool detecta postinst que puede iniciar ipmievd. No se
han instalado paquetes/servicios; se prepara extracción aislada de los3DEB para
consultas BMC, sin postinst ni daemon. Todavía no se ha ejecutado esa herramienta.

Estado07:59:52UTC: backup en/home/luisacuna/app2/recovery/
rescue-20261020T075927Z-boa8lm5f, origenRO,norecovery temporalmente montado y
Docker detenido. Log sóloBACKUP, sinJSONfinal; no declarar archivos terminados
ni cleanupfinal. Raíz65.409.859.584B libres. Esperar resultado antes de preparar
IPMI dentro deAPP2 o alterar los archivos fuente del backup.

### HISTÓRICO — Resultado de rescate20-10-2026 — archivos verificados, restore pendiente

Backup terminado en/home/luisacuna/app2/recovery/
rescue-20261020T075927Z-boa8lm5f:22 TAR,47.034.378.240B, todos los 20 volúmenes y
ninguno excluido, másserver-app2/definiciones Docker;compare PASS/hash por archivo,
0600 / UID 1001. Origen y montajes de rescate ya desmontados; raíz35.648.344.064B libres.
No es imagen SSD, respaldo de capas escribibles o prueba de PostgreSQL restaurable.

13 TAR no Ollama(1.373.347.840B)+recibo se transfieren aPC/recovered-offserver;
transferencia/hash todavía pendientes. No arrancar Dockerorigen ni actualizar
SO 095Aconúnicabackup. Firmware sigue pendiente de medios/consola y validaciones.
Tras terminar la copia ya puede prepararse la herramienta IPMI aislada, sin
instalar postinst/daemon; todavía no consta ejecutada/configurada.
Los estados «en curso» anteriores son historia previa a este resultado.

### HISTÓRICO — Copia externa e IPMI aislado — estado08:06UTC

13 TAR no Ollama,1.373.347.840B+recibo, en evidenciaPC/recovered-offserver:
13 SHA coincidentes, copia externa verificada. Ollama permanece en el backup del
SSD del SO, sin tercera copia PC. Restauración PostgreSQL aislada aún pendiente.

[ipmi_readonly.py](ipmi_readonly.py) y payloads aislados están desplegados en
/home/luisacuna/app2/maintenance/ipmi-readonly-tools,nuevo700/files600;
bundle SHA63eb350…65b4 ywrapper b7a7…c5e2. --check real confirma
CHECK_OK_NO_BMC_CALL; no paquetes instalados, postinst/daemon, llamadas o
configuración BMC. Consulta canal1/LAN entregada al operador y resultado pendiente.
Código/paquete preservados en PC/receta porque se añadieron después del backup.
Consola/credenciales/medio de firmware siguen pendientes; no se ha aplicado8B.

### HISTÓRICO — Verificación de PostgreSQL y accesoBMC — resultado posterior

[verify_pg_rescue.py](verify_pg_rescue.py) verifica en elPC una copia nueva de
losTARexternos, con PostgreSQL15 oficial fijado por digest y contenedor temporal
sin red. Recuperación física másdump→DBvacía PASS:4tareas/4jobs/9formas globales,
task5/job5/shape10frame1 conservados. Dump260.183B/SHA20a57377…7997; fuentes y
receta enpg-restore-test-20261020T080940Z/.26tests pasan. Contenedor temporal
eliminado yTARoriginales intactos;23IDs previos conservados, Loki ya reiniciaba
por su cuenta. No demuestraCVATcompleto/imágenes o firmware corregido.

Canal1BMCconsultado por operador:192.168.1.34/24,gateway192.168.1.251.
Webhttps://192.168.1.34/:443respondeHTTP200/TLS1.3 sin autenticación;80timeout.
AvisosstderrIPMI conservados constdoutválido. No configuración modificada;
credenciales,KVM/VirtualMedia yarranque deISO siguen pendientes. No se ha aplicado8B.

### HISTÓRICO — Helper para capas escribibles — desplegado, ejecución pendiente

[storage_writable_rescue.py](storage_writable_rescue.py) se añadió como archivo
nuevo en/home/luisacuna/app2/maintenance/storage_writable_rescue.py,
10.322B/0600/UID1001,SHA0e9765027351ade0ec7275d84918e4ea7392172609448a0cfaf45887c34a89ed.
La base ec8e… permanece intacta. Pretende copiar overlay2 escribible ymetadatos,
no capas inmutables oimagenSSD. [6tests fixture](tests/test_storage_writable_rescue.py) pasan; --backup solicitado
al operador, resultado todavía pendiente. FITS real antes de crearTAR y reserva
16GiB; no montaje/copia de esas capas acreditados aún.
Firmware/BMCconfig no cambiados. Ver resultado vigente en el incidente.


</details>
