# Conservar y recrear las adaptaciones tras actualizar

**Política global del proyecto desde 2026-09-10.** Usar junto al
[registro vigente](../SYSTEM_CUSTOMIZATIONS.md) y
[`AGENTS.md`](../../AGENTS.md). Aplica también al cambio de imagen/recreación
de un contenedor, al SDK, al PC y al PICO, aunque no cambie el firmware.

El resultado de una recuperación debe ser una lista de fichas con decisión y
evidencia: **conservada, reaplicada y comprobada, retirada porque ya no hace
falta, o pendiente**. No hay un “restaurar todo” automático: mezclar un compose,
calibración o XML antiguos con binarios nuevos puede reproducir los incidentes
anteriores. La copia de seguridad conserva datos; no autoriza movimientos.

## 1. Antes de actualizar

1. Guardar el estado del repositorio, incluidos cambios sin commit y archivos
   no versionados necesarios. Guardar aparte paquetes oficiales, imágenes,
   checkpoints, modelos usados en cálculos y evidencia de sus hashes.
2. Respaldar **Motion y Vision**, no sólo el PC. Registrar versiones, imágenes
   y digests, contenedores, montajes, políticas de reinicio, servicios y red.
   No estar grabando un mapa ni cambiando configuración mientras se copia.
3. Copiar los respaldos fuera del robot y verificar sus checksums. La copia
   en `/home/walker` puede perderse con la actualización o con el disco.
4. Contrastar la cobertura con todas las fichas del registro. Si una adaptación
   añade una ruta que el script no respalda, ampliar la selección o copiarla
   expresamente antes de continuar. `docker diff` ayuda a detectar diferencias
   adicionales, pero no explica cuáles son modificaciones deseadas.
5. Preparar la actualización física con la guía de arranque/apagado aplicable.
   La instalación de archivos, la recarga de procesos y el primer movimiento
   son pasos distintos. Un arranque o cambio a auto puede lanzar HOME.

### Copia del trabajo local (PC)

Desde la raíz del repositorio, en una terminal Bash. El directorio creado es
privado y externo a Git. No hace commit, no instala ni controla el robot.

```bash
umask 077
CRUZR_BACKUP_STAMP="$(date -u +%Y%m%d-%H%M%S)"
CRUZR_BACKUP_LOCAL="$PWD/../Humanoide-vla-evidence/preupgrade-$CRUZR_BACKUP_STAMP"
mkdir -p "$PWD/../Humanoide-vla-evidence"
mkdir "$CRUZR_BACKUP_LOCAL"
git status --short --branch > "$CRUZR_BACKUP_LOCAL/git-status.txt"
git rev-parse HEAD > "$CRUZR_BACKUP_LOCAL/git-head.txt"
git diff --binary HEAD > "$CRUZR_BACKUP_LOCAL/working-tree.patch"
git ls-files --others --exclude-standard > "$CRUZR_BACKUP_LOCAL/untracked-files.txt"
tar -czf "$CRUZR_BACKUP_LOCAL/project-working-files.tar.gz" AGENTS.md README.md docs scripts config
```

Este tar incluye archivos de esas carpetas aunque aún no estén en un commit;
no incluye todo el repositorio ni los paquetes ignorados. Revisar la lista de
no versionados y añadir los que se necesitan. En esta unidad se deben conservar
también los modelos locales `cruzr_s2_description/` y
`cruzr_s2_description_splint/` si se usan en la validación, y la carpeta externa
`Humanoide-vla-evidence` relevante. Conservar el paquete VLA original y los
workspaces modificados de `/home/walker/cruzr-vla/additional/` por separado;
sus pesos no están incluidos en el backup ligero.

Para reinstalar el PC, añadir a una copia privada sus perfiles NetworkManager,
`/opt/ubt-controller`, `/opt/ubt-remote-control`, unidades/drop-ins systemd,
configuración de usuario de teleoperación, reglas udev y paquetes oficiales
instalados. Registrar versiones XR/APK del PICO. No copiar credenciales al
registro público. Una actualización del robot por sí sola no requiere
reinstalar estas aplicaciones del PC.

### Copia de ambos ordenadores del robot

El script [preupgrade_backup_remote.sh](../../scripts/upgrade/preupgrade_backup_remote.sh)
se ejecuta **en cada host**, mediante SSH habitual; sólo lee configuración y
escribe su carpeta de respaldo. No tiene `docker exec/start/restart`, llamadas
de control ni cambios de modo. Requiere Bash, Docker, tar, coreutils y sudo.

Con las variables del bloque anterior todavía definidas, ejecutar desde el PC:

```bash
scp scripts/upgrade/preupgrade_backup_remote.sh walker@192.168.11.2:/tmp/cruzr-preupgrade-backup.sh
ssh walker@192.168.11.2 "sudo bash /tmp/cruzr-preupgrade-backup.sh $CRUZR_BACKUP_STAMP"
scp scripts/upgrade/preupgrade_backup_remote.sh walker@192.168.11.3:/tmp/cruzr-preupgrade-backup.sh
ssh walker@192.168.11.3 "sudo bash /tmp/cruzr-preupgrade-backup.sh $CRUZR_BACKUP_STAMP"
```

Comprobar **las dos salidas y códigos de salida** antes de pasar a la copia:

- `BACKUP_STATUS=CAPTURED_REVIEW_COVERAGE`: terminó la selección conocida;
  revisar aún `host-paths.tsv`, `container-paths.tsv` y `container-diff/`.
- `PARTIAL` y código 6: falló alguna copia/diff o no se reconocieron los
  contenedores; `failures.txt` indica dónde. Conservar evidencia y completar
  el respaldo. No tratarlo como listo para actualizar.
- `IN_PROGRESS`, sin checksum final o cualquier otra salida no cero: abortó
  antes de completar. Resolver la causa y usar otra marca de tiempo; el script
  rechaza sobrescribir una copia anterior.

El prefijo `preupgrade-v0.2.0-` se mantiene por compatibilidad con las copias
anteriores; **no demuestra la versión actual**, registrada en `soft_version.txt`.
Copiar como tar preserva enlaces como datos, sin seguirlos:

```bash
ssh walker@192.168.11.2 "tar -C /home/walker -czf - preupgrade-v0.2.0-$CRUZR_BACKUP_STAMP" > "$CRUZR_BACKUP_LOCAL/motion.tar.gz"
ssh walker@192.168.11.3 "tar -C /home/walker -czf - preupgrade-v0.2.0-$CRUZR_BACKUP_STAMP" > "$CRUZR_BACKUP_LOCAL/vision.tar.gz"
mkdir "$CRUZR_BACKUP_LOCAL/motion" "$CRUZR_BACKUP_LOCAL/vision"
tar -xzf "$CRUZR_BACKUP_LOCAL/motion.tar.gz" -C "$CRUZR_BACKUP_LOCAL/motion"
tar -xzf "$CRUZR_BACKUP_LOCAL/vision.tar.gz" -C "$CRUZR_BACKUP_LOCAL/vision"
(cd "$CRUZR_BACKUP_LOCAL/motion/preupgrade-v0.2.0-$CRUZR_BACKUP_STAMP" && sha256sum -c SHA256SUMS)
(cd "$CRUZR_BACKUP_LOCAL/vision/preupgrade-v0.2.0-$CRUZR_BACKUP_STAMP" && sha256sum -c SHA256SUMS)
(cd "$CRUZR_BACKUP_LOCAL" && sha256sum *.tar.gz > ARCHIVE_SHA256SUMS)
```

Verificar cada salida; una transferencia incompleta no es un respaldo válido.
Conservar además una copia en otro disco/equipo según disponibilidad. No
extraer `configuration.tar.gz` o `container-configs.tar.gz` sobre `/` para
restaurar: se comparan y recuperan archivos seleccionados.

**Cobertura del script:** configuración uDoke, sistema, mapas/tareas/calibración,
boot y sus backups, trajectory-overlays, systemd, perfiles de red del robot,
backup arms-only, tareas del propietario, manifiestos/backups VLA y script
kiosk. Incluye configuraciones del gestor y metatareas de manipulación,
percepción/freepnc e index/JS de expresiones en contenedores reconocidos,
incluso detenidos. Guarda inventario/inspect y `docker diff` de los demás.
`INVENTORY_ONLY` significa que sus archivos internos **no** se copiaron.

No incluye automáticamente imágenes Docker, pesos, workspace VLA completo,
todos los logs ni datos del PC/PICO. La lista debe crecer con el registro.
Los archivos systemd/boot se archivan como evidencia: algunos contienen estados
transitorios o servicios retirados que **no se deben reactivar**.

## 2. Después de actualizar: decidir antes de reaplicar

Registrar firmware real, hardware/efector, imágenes y digests, montajes,
versiones del SDK, nombres/endpoints y estado de los servicios. Comparar
original nuevo, original anterior y adaptación anterior. Para cada ID:

| Resultado de comparación | Acción |
|---|---|
| La adaptación sigue presente e idéntica | Verificar carga/comportamiento; no reinstalar por rutina |
| El proveedor ya resuelve el problema | Retirar el workaround y documentar evidencia |
| Desapareció y sigue siendo compatible | Reaplicar desde fuente revisada y comprobar |
| Cambió contrato, binario, marco o geometría | Adaptar y validar primero; no relajar hashes/gates |
| Era una prueba temporal o un cambio retirado | Conservar sólo evidencia; no activar |

Antes del primer HOME, revisar **MOT-01**: una recreación de manipulación puede
haber devuelto el XML directo del proveedor. Con brazos elevados, no usar
StartMotion, modo auto o reinicio como sustituto de una recuperación.
Mantener VLA detenido/sin autoarranque y clientes de control inactivos durante
la intervención; la activación física sigue su guía específica.

## 3. Receta BOOT: espera, voz y pantalla

Ésta documenta cómo recrear BOOT-01/02/03 con la **misma versión y contratos
revisados**. No valida una nueva versión del proveedor. Leer primero las
fichas y [la guía de arranque](CRUZR_V020_BOOT_GUARD.md). El despliegue anterior
fue verificado; esta receta consolidada no se ha vuelto a ejecutar en el robot.

1. Respaldar el compose y archivos actuales. Comprobar que el guard antiguo
   está deshabilitado/inactivo. Revisar binario de CC, contenedores ROS/Motion,
   cámaras, servicios TTS, página web y disponibilidad de `inspection.mp4`.
   Los hashes/contratos esperados están en los scripts, no se omiten.
2. Preparar en Vision una carpeta privada nueva, por ejemplo
   `/home/walker/restore-reviewed/`, y copiar desde el PC estas fuentes:

   ```bash
   ssh walker@192.168.11.3 'mkdir -m 700 /home/walker/restore-reviewed'
   scp scripts/upgrade/cruzr_cc_start_when_ready.py scripts/upgrade/cruzr_boot_voice.py scripts/upgrade/cruzr_boot_visual.py scripts/upgrade/cruzr-boot-ready.js scripts/upgrade/cruzr-boot-voice.service scripts/upgrade/patch_cc_readiness_compose.py walker@192.168.11.3:/home/walker/restore-reviewed/
   ```

3. En una **terminal SSH de Vision**, con backups ya guardados y compatibilidad
   revisada, instalar los archivos. Estos comandos no reinician procesos:

   ```bash
   cd /home/walker/restore-reviewed
   sudo install -d -m 755 -o walker -g walker /etc/walker/boot
   sudo install -m 644 -o walker -g walker cruzr_cc_start_when_ready.py cruzr_boot_voice.py cruzr_boot_visual.py cruzr-boot-ready.js /etc/walker/boot/
   sudo install -m 644 -o root -g root cruzr-boot-voice.service /etc/systemd/system/cruzr-boot-voice.service
   ```

4. Aplicar sólo el comando preventivo al **compose nuevo**, no sustituirlo
   por el backup entero. El helper necesita Python con PyYAML; su salida debe
   ser un archivo nuevo. En Vision:

   ```bash
   python3 patch_cc_readiness_compose.py --input /home/walker/.config/udoke/walker/compose.yml --output compose.reviewed.yml
   diff -u /home/walker/.config/udoke/walker/compose.yml compose.reviewed.yml
   ```

   Revisar que sólo cambia el comando de `system.control_center` (o no hay
   diferencia si ya estaba aplicado). Después de esa revisión, instalarlo
   conservando propietario/permisos del original:

   ```bash
   cp --preserve=mode,ownership /home/walker/.config/udoke/walker/compose.yml compose.install.yml
   cat compose.reviewed.yml > compose.install.yml
   mv compose.install.yml /home/walker/.config/udoke/walker/compose.yml
   ```

   No modifica el proceso CC ya creado; uDoke debe consumir el compose
   actualizado en la activación planificada. No improvisar un reinicio de CC
   con brazos elevados. Registrar la activación y comando efectivo después.

5. Preparar el añadido del visor y la unidad para el próximo encendido:

   ```bash
   python3 /etc/walker/boot/cruzr_boot_voice.py --prepare-display
   sudo systemctl daemon-reload
   sudo systemctl enable cruzr-boot-voice.service
   systemctl is-enabled cruzr-boot-voice.service
   ```

   El preparador rechaza un index distinto y deja el indicador apagado.
   No copiar `cruzr-boot-ready.json`, un boot ID anterior ni habilitar el preview.
   No usar `enable --now`. El wrapper necesita que `/etc/walker` siga siendo
   visible en el contenedor CC, como en la entrega revisada.
6. Activar en el siguiente encendido **supervisado** conforme a la guía;
   registrar las comprobaciones técnicas, voz/pantalla y fases posteriores
   por separado. Desde PC, `./scripts/cruzr_boot_ready.sh --check` consulta sin
   dar órdenes de movimiento. Inspeccionar el comando efectivo y el log del
   proceso actual demuestra si uDoke consumió el cambio. Si no, revisar el
   despliegue con la guía, no repetir cambios de modo/reinicios a ciegas.

Rollback selectivo: ficha BOOT y [guía voz/pantalla](CRUZR_AVISO_VOZ_ARRANQUE.md).
Retirar la voz o el visor no requiere retirar la espera preventiva. Cerrar
LoadingScreen termina la sesión kiosk; preferir el próximo encendido para
cargar la página. No reiniciar Motion/CC para probar una pantalla.

## 4. Reaplicación de movimiento, PC y datos

| Ficha | Punto de entrada versionado | Qué no demuestra instalar |
|---|---|---|
| MOT-01 | `python3 scripts/teleoperation/cruzr_install_internal_home.py --check`, luego `--preflight` y `--install` según su guía | XML correcto no valida escena, interpolación ni parada |
| MOT-02 | `./scripts/teleoperation/cruzr_pico_to_home_owner.sh --check --speed 4`, luego `--install --speed 4` según su guía | `--reload` no recupera por sí solo Motion tras E-stop |
| MOT-03 | `./scripts/teleoperation/install_cruzr_pico_arms_only.sh --check` | Copia YAML no prueba modos cargados |
| MOT-04 | Instalador y guía de cada tarea; no restaurar `task_list.yaml` entero | Presencia de READY/ENTRY no aprueba todas las trayectorias |
| PC-01/02 | Perfiles exportados, `config/systemd`, `config/udev` y fuente PICO | UI conectada puede armar control; no autoarrancarla |
| VLA-01 | `./scripts/vla/install_ubtech_vla.sh --check` y `--verify`; etapas de instalación según guía | Inferencia correcta no autoriza publicar comandos |
| NAV-01 | Perfil, mapa y calibración guardados; guías de transferencia | Mapa cargado no demuestra mesa/caja en su posición anterior |
| NAV-02 | `./scripts/cruzr_cargo_perception_profile.sh --check` | Configuración temporal de carga no es el estado base |

La recarga, cuando es necesaria, queda como paso separado en cada guía.
No ejecutar todos estos comandos de instalación como una secuencia única:
sus condiciones físicas y de modo son diferentes.

## 5. Cierre de la actualización

Añadir una intervención en la fuente global con: versión anterior/nueva,
carpeta privada de backups, hashes, decisiones por ID, archivos realmente
cambiados, pruebas ejecutadas y pendientes. Actualizar las fichas vigentes y
la guía especializada. Conservar una copia final de fuentes/configuración
instaladas, también si todavía no tienen commit.

No cerrar con “todo restaurado” si sólo se copiaron ficheros: distinguir
**instalado**, **cargado** y **comprobado físicamente**. La revisión del
2026-09-10 amplió el respaldo y la política en el PC; no ejecutó estos comandos
de despliegue ni modificó el robot.
