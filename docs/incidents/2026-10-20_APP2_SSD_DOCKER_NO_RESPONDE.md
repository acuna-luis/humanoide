# APP2 — fallo del SSD de Docker y recuperación de datos

**ID:** APP2-STORAGE-20261020. **Fecha/zona:** 20-10-2026, Europe/Madrid.

## Estado actual verificado

**APP2/CVAT operativo y verificado. Se puede continuar la anotación del piloto.**
A las 11:37:55 UTC, el servidor tiene 20 contenedores ejecutándose, ninguno parado
o pausado, `DockerRootDir=/var/lib/docker`, driver `overlay2` y sin avisos Docker.
Datos `S7DRNJ0X107187F` activo en `8B2QJXD7`; SO `S7DRNJ0X107095A` conservado en
`4B2QJXD7`; ambos NVMe `live`. Boot `e719f517-0709-417a-b521-7bc8c0212bf6`.

La configuración original quedó restaurada: UUID de datos
`b819b286-2006-4474-b2d5-13982b0f1536`, EXT4 `rw,relatime` en `/var/lib/docker`,
fstab `defaults 0 2`. Docker, socket y containerd activos/running/enabled; mount
generado activo y ninguna unidad systemd fallida. El checker confirmó los 20
volúmenes antes de arrancar. Comparación de los 20 contenedores a las 11:35:08 UTC:
mismos IDs, imágenes, políticas y montajes; todos running, `RestartCount=0` y
`Error` vacío. Redis con healthcheck healthy; los demás no tienen HEALTHCHECK.
Ambos Ollama arrancaron mediante su política existente, sin recrearlos.

**Datos y acceso comprobados, no sólo HTTP 200:**

- API autenticada de CVAT, sólo lectura, a las 11:35:56 UTC: 4 tareas, 4 trabajos
  y 9 formas globales; tarea 5 / trabajo 5, `shape 10` del frame 1 presente.
- Originales de tarea 5 servidos por CVAT con los mismos hashes, tamaños y
  dimensiones que los PNG conservados: `head_raw.png`, 1920 × 1536,
  4.845.034 bytes, SHA `8c3c3106f46e86d508eb8c7655e3bf7c29f1dbf78313096e91f722213ab7f864`;
  `head_rgb.png`, 960 × 576, 991.124 bytes,
  SHA `3764c2ca78af1e51da2e273a3d00344c9d8baa48459113efc79cc7e149e798cc`.
- Chunk comprimido usado por el editor: ZIP con 2 JPEG legibles y CRC sin error,
  verificado a las 11:37:55 UTC.
- API about y UI HTTP 200, CVAT `2.79.0`. Túnel del PC restaurado a las
  11:36:53 UTC, API local HTTP 200 y página del trabajo 5 HTTP 200.

**Retomar:** abrir [el trabajo 5](http://localhost:18080/tasks/5/jobs/5) en este PC
con la cuenta existente y continuar anotación/revisión humana. No se escribió una
anotación de prueba, no se entrenó un modelo real y no se conectó ni movió el robot
en esta recuperación. **Ningún sudo queda pendiente para reanudar APP2.** No repetir
firmware, recuperación, montaje o arranque. La fiabilidad a largo plazo sigue
pendiente de observación; estos resultados no prueban que el fallo intermitente
no volverá a ocurrir. Backups, undo e informes se conservan.

### Túnel del PC: estado y reversión

PID `1042428`; listener sólo en `127.0.0.1:18080`; socket privado
`/tmp/app2-cvat-tunnel-58rqjz4k/ssh.sock`. Comando de esta sesión, **ya ejecutado**
(no duplicarlo mientras siga abierto):

```bash
ssh -f -N -M -S /tmp/app2-cvat-tunnel-58rqjz4k/ssh.sock \
  -o BatchMode=yes -o ExitOnForwardFailure=yes -o ConnectTimeout=8 \
  -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
  -p 2649 -L 127.0.0.1:18080:127.0.0.1:18080 luisacuna@192.168.1.43
```

Para cerrar sólo este túnel, sin detener CVAT:

```bash
ssh -S /tmp/app2-cvat-tunnel-58rqjz4k/ssh.sock -O exit \
  -p 2649 luisacuna@192.168.1.43
```

El socket es de esta sesión y puede desaparecer al reiniciar el PC. Para otro PC
o una sesión nueva, usar la [receta SSH estable](../app2/RETOMAR_APP2.md#3-retomar-hoy-con-el-servidor-existente),
sin copiar credenciales o perfiles de navegador. El intento inicial con socket de
ruta demasiado larga no creó listener; sólo el túnel corto descrito quedó activo.

### Recuperación y evidencia que se conserva

La recuperación offline real terminó a las 11:17:31 UTC (13:17:31 Madrid),
código 0: journal recuperado y cinco pasadas posteriores de lectura, código 0
en 2,384 s, sin avisos. La alerta pre-replay quedó resuelta en esa muestra. SMART
de ambos SSD sin avisos críticos, errores de medios o entradas de error; kernel
muestreado normal. Rollback CSM/EFI verificado: sólo `Boot0001 ubuntu`, BootNext
ausente; Primary Display leído Discrete antes de guardar. Sin borrado EFI manual.
Backup/undo en `/root/app2-offline-recovery/20261020T111731Z-7r0y7atv`, undo de
4.345.856 bytes. Checker instalado en
`/home/luisacuna/app2/maintenance/storage_mount_check.py`, 4.715 bytes,
UID 1001 / `0600`, SHA `03fa9b8a29d07a4ca8520c7cdc5d61bc8a36faf58a5e37af8fde060c79fa3f06`.

Recibos privados finales:

| Archivo | SHA256 |
|---|---|
| `docker-post-start-compare-20261020T113508Z.json` | `2ed036af14d9223b10c11cb958f3f4dd756e9785b6ceceb94b629b694bbf6fd0` |
| `cvat-post-recovery-api-media.json` | `198173a091bd89c50addc509e7ab3b3cd8dcaa6dddbc1bc1dfa820d00085f780` |
| `pc-cvat-tunnel-restored.json` | `7242b5b6093e497dae07687bf25abd3cacde203d9846b9a1897b7827466383ec` |
| `cvat-storage-final-readonly.json` | `f54d341c0ce9482ff2d985f7d3141c07e4d0d9c9da3fbdb73ddeae9248cc9114` |

También se conservan `docker-activation-system-readonly.json`,
`docker-mount-layout-compare.json`, los informes de recuperación y sus hashes.
No se publican credenciales, cookies, TAR, imágenes originales o dumps en Git.

### Última sincronización documental del servidor

A las 11:39:43 UTC se sincronizaron sólo dos recetas en
`/home/luisacuna/app2/maintenance/`, ambas UID 1001 / `0600`:

- `POSTFIRMWARE_CHECK.md`: 8.629 bytes, SHA `82ce58c94c7d95618ffbf9d5918755a020ef1ee5d2a6365896309e8092cdf355`.
- `OFFLINE_RECOVERY.md`: 13.688 bytes, SHA `abc0e210d3e9057cdfa534c55abfbbfb3172e5fdd718f96f7b92c6b66acff9b6`.

Versiones anteriores y recibo conservados en `docs-final-state-7uwtkxyv/`, junto
a las recetas. Recibo local `maintenance-docs-final-state-deployment.json`,
SHA `3a7344b072472626c75c88fc7b0baf19d0043054fa14b19ba6ae1fb7bca8f6f5`. No se cambiaron servicios, helpers,
firmware o datos durante esta sincronización. APP2/CVAT sigue operativo y verificado.

### Antecedentes comprobados y preparación anterior a la recuperación

**Baseline verificado antes de la recuperación: SSD de datos activo en 8B2QJXD7.**
post-firmware-ssh-readonly.json, 10:08:59 UTC: Ubuntu boot
97828070-b077-4777-9ce6-3ed952d66bb2. Datos serie S7DRNJ0X107187F en /dev/nvme0:
8B2QJXD7, live. SO serie S7DRNJ0X107095A: 4B2QJXD7, live. Coinciden el dispositivo
objetivo del actualizador y la lectura posterior; el SSD del SO no se flasheó.
Guardas PASS, cinco unidades masked/inactive, origen sin montar; Docker/CVAT no
arrancados. No se han ejecutado SMART privilegiado post-flash ni fsck.

**Verificación postrollback anterior a la recuperación, 10:20:03 UTC:** Ubuntu boot
e719f517-0709-417a-b521-7bc8c0212bf6; EFI presente, datos187F8B2QJXD7/live y
SO095A4B2QJXD7/live. Cinco unidades masked/inactive, origen sin montar, guardas PASS
(post-csm-rollback-ssh-readonly.json). EFI fresco, rc0 en
post-csm-rollback-efi-readonly.json: BootCurrent0001, BootOrder[0001], **sólo
Boot0001 ubuntu**, BootNext ausente y Secure Boot disabled. BBS0002/0003 se
eliminaron automáticamente tras CSM Disabled; no se borraron manualmente.
CSMDisabled se había guardado con F10 y PrimaryDisplay Discrete se leyó sin editar
antes de guardar. Arranque UEFI y orden/entradas originales restaurados, con evidencia
posterior; no se da por terminada aún la revisión de salud/integridad/CVAT.

**Helper vigente, corrección aplicada 10:42:09 UTC:** storage_postcheck.py
SHA256 a482e7d08eee61777add951b6a1c7de0d9e91600b4082e787d2a282e87b5bd0f y receta POSTFIRMWARE_CHECK.md
SHA256 64efc32bffaea72194c0ec5e8103661e0f42da70bac4787bccd86c89965657b5. Ambos en
/home/luisacuna/app2/maintenance/, propiedad del usuario/mode0600; sólo se
sustituyeron esos dos archivos, sin diagnósticos, montajes o servicios durante
este despliegue. 15 tests locales PASS. Previamente se respaldaron los archivos
instalados9e030a05…8a33/2ff2efb7…f56e0 en
/home/luisacuna/app2/maintenance/postcheck-review-fix-20261020T104209Z-p5_ao905.
Recibo postcheck-review-fix-deployment.json. La primera instalación y el resultado
de10:30:42UTC pertenecen a la versión anterior; la salida original se conserva.
Reversión del código sólo desde ese backup cotejado, sin montar ni reparar datos.
[Receta de revisión](../../scripts/app2/server/POSTFIRMWARE_CHECK.md).

**Resultado anterior de sólo lectura, 10:30:42 UTC:** el operador obtuvo CODIGO=0
y el JSON /home/luisacuna/app2/maintenance/postfirmware-check-20261020T1023Z.json,
boot e719f517…2bf6. Ambos NVMe live, datos187F8B y SO095A4B. SMART de ambos:
critical_warning=0, media_errors=0, num_err_log_entries=0; kernel recogido sólo
muestra arranque, sin reset o I/O error visible en esa muestra. No demuestra que
el fallo intermitente esté resuelto definitivamente. Cinco máscaras/inactividad
y origen sin montar siguen PASS.

**EXT4 no se declara limpio:** e2fsck -f -n devolvió rc0 en2,387s, pero indicó
«skipping journal recovery», diferencias de contadores y «Fix? no»:

| Contador | Valor almacenado | Contado por e2fsck |
|---|---:|---:|
| Bloques libres | 463783574 | 463807698 |
| Inodos libres | 121891505 | 121917075 |

La comprobación no reprodujo el journal y no reparó. Son diferencias observadas
antes de replay; no prueban por sí solas corrupción definitiva, ni un rc0 las
convierte en consistencia verificada. El resumen del helper
NO_ERRORS_REPORTED… era demasiado fuerte para esta salida y ya se corrigió en helper/receta;
no se ejecutó otro diagnóstico durante ese despliegue. Se debe conservar JSON y salida originales, usar esas advertencias como el estado vigente en aquella fase, antes de la recuperación posterior.
Archivo privado de evidencia previsto: postfirmware-check-20261020T103042Z.json.

**Plan aprobado antes de ejecutar la recuperación — historial de preparación:** preen estándar
limitado a autocorrecciones de journal y metadatos, sobre el volumen identificado
por serie/UUID187F y desmontado:

```text
e2fsck -p -E nodiscard,fixes_only,no_optimize_extents -z <undo-en-SSD-SO> <volumen187F-identificado>
```

No se promete «sólo journal»: la investigación de e2fsprogs1.47 halló que incluso
-p/journal_only puede ampliar pasadas por flags previos. Se revisó y se desplegó storage_offline_recovery.py --check/--recover; receta
OFFLINE_RECOVERY.md también instalada, con guardas,
recibos de backups, SMART fresco, undo y copia inicial de2MiB en SO, reserva,
logs y comprobación posterior de lectura. **Helper INSTALADO; preflight/recovery NO ejecutados todavía.** Undo/copia2MiB no son una imagen completa del volumen.
Sin -y, -c, -f, montaje, arranque, reintento automático o timeout que mate e2fsck.
No se ha reparado ni reproducido el journal; Docker/CVAT siguen detenidos.

**Despliegue real del helper offline10:54:07UTC/12:54:07 Europe/Madrid:**
/home/luisacuna/app2/maintenance/storage_offline_recovery.py,
20.560 bytes/UID1001/mode0600, SHA256 0f016474bdae29cce095dc31c2261661b951cff7c88a050851df7b0f0406ce6b.
Destino anterior ausente, publicación atómica sin clobber. Dependencias baseec8
ypostchecka482 verificadas; sólo --help remoto rc0. Revisión root e independiente
aprobadas; 13 tests locales PASS, incluidos preen real sobre EXT4 temporal,
undo/lectura posterior y lock heredado. **Eso no es recuperación del volumen real.**
[OFFLINE_RECOVERY.md](../../scripts/app2/server/OFFLINE_RECOVERY.md). Reversión del despliegue: retirar sólo
ese archivo nuevo con hash cotejado, conservar fuentes/recibos y no tocar datos.

Se pidió al operador la línea sudo --check && sudo --recover, con informes
/home/luisacuna/app2/maintenance/offline-preflight-20261020T1054Z.json y
offline-recovery-20261020T1054Z.json en esa misma carpeta. **Ejecución y resultados
PENDIENTES**: aún no sudo/check/recover, replay, reparación, montaje o Docker.
No inferir resultado por tests/instalación/help. Revisar los recibos reales y la
comprobación posterior antes de cualquier activación.

**Preparación concreta completa entonces, antes de ejecutar — historial:** la receta
/home/luisacuna/app2/maintenance/OFFLINE_RECOVERY.md está instalada nueva,
8.356 bytes/UID1001/0600, SHA256 aecfd1cc66156c6155d62c4d0679cbe8c286dc733c91ecf31eff89941f148390.
Recibo offline-recovery-deployment-final.json, SHA256
a9e6cc022ad6de8e133e581e054bfbd6d0aa2712e172232555f192b0f075ab02.
A las **10:56:38 UTC** ambos informes offline-preflight-20261020T1054Z.json y
offline-recovery-20261020T1054Z.json seguían **AUSENTES**. No se ejecutaron sudo
check/recover ni montaje/arranque. La sesión SSH del agente no dispone de sudo
sin contraseña; el operador debe ejecutar la línea ya preparada en su terminal.
No hay que repetir permisos, despliegue o tests. Retomar recibiendo ambos JSON,
revisar estado/rc/salidas y sólo entonces decidir restaurar configuración,
montar o activar Docker. Mantener guardas y origen sin montar mientras tanto.
Revisar el resultado real de la futura operación antes de decidir activación.

**Cierre de las herramientas de esta fase:** el medio virtual fue retirado por
UI normal antes del rollback CSM. El agente intentó Sign out sólo de su sesión
BMC, pero CDP agotó tiempo: **logout no confirmado**. Después cerró únicamente
su Chrome aislado PID665887 con comprobación de propiedad; KVM ya no queda activo.
Se retiene el perfil privado en la evidencia/profile-spki-clean, con posibles
datos de sesión privados; no se añade a Git. No hubo energía o cambios de servicios
del host durante esta limpieza. Recibo bmc-session-cleanup-and-sudo-report-pending.json.
No hace falta reabrir KVM para la consulta sudo de salud/FS.

Secuencia de escritura ya completada: Samsung v3.1 mostró Drive1/seriecompleta187F,
firmware previo4B; Y/Y sólo ese SSD, Firmware Update Completed, N al siguiente,
salida/ENTER10:07:25UTC. El objetivo se verificó después en Linux8B; no son sólo
resultados del proveedor. Capturas samsung-updater-device-confirmation.png,
samsung-drive1-flash-progress.png y samsung-next-device-declined.png conservadas.
No repetir flash o arrancar Docker/CVAT para probar; la causa original sigue sin
demostración concluyente. Firmware del SO permanece en4B, con los backups conservados.

La recuperación previa ACPI off/on, sesión BMC y restablecimiento KVM se conservan
abajo como antecedentes. No hubo hard reset o force-off. La receta versionada es
[BMC_RECUPERACION_KVM.md](../../scripts/app2/server/BMC_RECUPERACION_KVM.md).
Credenciales/cookies/CSRF sólo privadas, sin cambios de confianza global o paquetes.

**Gates comprobados antes del flash — antecedente:** el navegador limpio aislado
con excepción SPKI sólo del BMC (PID 665887, puerto local 46821) mantiene KVM OPEN,
sin reconnect, en 12/12 muestras durante 120 s; último paquete 1–160 ms. Un Enter
vacío cambió efectivamente la consola aisrv login, sin comando o login. Captura
bmc-kvm-empty-enter-after.png y bmc-kvm-120s-stability.json. El estado transitorio
anterior de bmc-clean-kvm-recovery-result se conserva como historial, no vigente.

La ISO se adjuntó con file input normal y Start Media. /dev/sr0 AMI Virtual CDROM0
muestra 102.400 sectores / 52.428.800 bytes. El operador confirmó otra lectura sudo
SHA f05508f3228960fc1501fe5a27d3a826377332afc8c021aac44487c8fd1c93d5,
coincidente con la ISO oficial local (virtual-cdrom-second-attachment-sha256-operator-result.json).
No depender del contador de KB del visor para juzgar la integridad del archivo.

**Secuencia UEFI anterior al flash, 09:47–09:52 UTC:** el operador confirmó ejecutado el comando
único de guardas y sudo reboot--firmware-setup (second-reboot-to-firmware-operator-confirmation.json).
UEFI está vivo, teclado de navegación funciona y reloj avanza de 09:47 a 09:51.
BIOS muestra versión 1602 x64 y fecha de build literal «09/04/2024», sin interpretar
el formato de fecha (bmc-second-uefi-live-full.png).

El Boot inicial sólo mostraba Ubuntu / M2_2, sin CD. Antes de tocar, se respaldaron
pantallas y uefi-csm-temporary-plan-and-prestate.json: Launch CSM Disabled,
Primary Display Discrete graphics card, Fast Boot Disabled, POST3s, OS Type Other OS,
Secure Boot UI User (mokutil previo Disabled), Boot1 Ubuntu y AMI Native NVMe Enabled.
**Único cambio de BIOS confirmado, temporal:** la revisión F10 mostró sólo
Launch CSM Disabled → Enabled (bmc-csm-save-reset-review.png,
uefi-csm-save-reset-review.json). El agente confirmó OK/Enter y observó reset/POST
(bmc-csm-save-confirmed-reset.png). **Confirmación de guardado enviada y reset
observado; readback de CSM activo todavía pendiente** al volver a setup/Boot Menu.
No seguir describiéndolo como sin guardar; tampoco afirmar persistencia comprobada
hasta leer el valor después del reset.

No se editaron UEFI+Legacy OPROM ni red/storage/PCIe Legacy Only: eran defaults
mostrados. El campo Primary Display quedó oculto con CSM; no demuestra cambio
persistente a Onboard. No se cambió Boot Order ni se escribieron SSD.
**Reversión obligatoria tras la prueba:** Launch CSM → Disabled y verificar también
Primary Display Discrete graphics card con el preestado respaldado. Registrar la
reversión y comprobarla después de guardar; no modificar campos ocultos por suposición.

En esa fase se observaba POST y se intentó F8 para leer dispositivos
(csm-post-f8-monitor095343, resultados parciales); el host ya volvió a Ubuntu
como se registra en el estado actual. No se ha seleccionado un SSD o iniciado el actualizador.
**Firmware SSD sigue con cero escrituras.** Sólo el cambio de configuración BIOS
Launch CSM fue confirmado tras revisión; los demás campos se conservan.

La recuperación previa incluyó PUT /api/ResetKVM sin cuerpo, 09:23:18,525 UTC,
HTTP 200; sólo servicio KVM. SSH posterior mantuvo boot 97a5c584…83be, sin nuevo
reinicio de host o reset completo BMC. Hubo rechazo TLS del popup, resuelto para
esta sesión mediante perfil limpio/SPKI, sin confianza global del SO o paquetes
cambiados. Perfiles/helpers y sesiones permanecen privados, sin secretos en Git.

Respaldo local previo al firmware: pre-fw-local-source-20261020T094356Z/
project-working-files.tar.gz, 39.855.239 bytes, SHA256
1ce1f4522592ed955ca5cc33dc552c2c244770544f8ee70db05fae3822076f37.
Incluye los cambios del repositorio a esa hora; git-head/status, manifest y patch
conservados junto al TAR, rc 0. No reemplaza los backups de datos ya verificados.

Se creó una sesión BMC autenticada en ejecución y se cambió el estado de energía
del host. Credenciales, cookies y CSRF sólo en material privado. Redfish devolvió
401 sin token; la Web UI sí autenticó. Estado/configuración/capacidades previos
preservados. La receta versionada es
[BMC_RECUPERACION_KVM.md](../../scripts/app2/server/BMC_RECUPERACION_KVM.md).
Evidencias: bmc-web-session-login-result.json, bmc-web-auth-readonly-prestate.json,
bmc-web-auth-capability-prestate.json, bmc-acpi-shutdown-result.json y
bmc-power-on-after-acpi.json. No repetir apagado/encendido ni restaurar guardas
para probar; comprobar primero el estado nuevo.

**Captura anterior del operador (~10:44 Europe/Madrid; reloj UEFI 08:44):**
ASUS está en Arrancar → Configuración de arranque, no en una lista de dispositivos.
El visor KVM de esa ventana muestra CD Image / Browse File (0 KB) / Start Media;
no vemos una ISO seleccionada allí. Esto no prueba por separado que el medio
haya quedado desconectado globalmente; no hay lectura del SO mientras está en UEFI.
Los ensayos previos de adjunto y SHA siguen registrados como comprobaciones previas.
Siguiente: volver a seleccionar la misma ISO de Descargas y Start Media; después,
Esc una vez para volver a Arrancar y leer Boot Override, antes de elegir dispositivo.
La captura muestra pantalla primaria Discrete graphics card, Fast Boot deshabilitado
y POST 3 s. Son valores observados: no se han editado ajustes, incluido CSM.
No arrancó el actualizador ni se aplicó firmware.

| Elemento | Resultado vigente | Límite |
|---|---|---|
| Persistencia Docker | **PASS:** 20 volúmenes, recetas y definiciones en 22 TAR, 47.034.378.240 bytes; compare y SHA por archivo | No es una imagen del SSD ni incluye capas escribibles |
| Copia fuera del servidor | **PASS:** 13 TAR no Ollama + recibo, 1.373.347.840 bytes; 13 SHA coincidentes en el PC | Ollama sigue respaldado en el SSD del SO, sin tercera copia PC |
| PostgreSQL | **PASS:** recuperación física de copia y dump restaurado en otra DB vacía | No valida toda la aplicación CVAT |
| Datos de CVAT recuperados | 4 tareas, 4 trabajos y 9 formas globales; tarea5/job5/shape10 del frame1 presentes | No son 9 piezas reales de job5 |
| Medios de tarea5 | **PASS:** head_raw.png1920×1536 y head_rgb.png960×576; CRC, decodificación, hashes originales y manifiesto coinciden | No había ZIP de chunks ni image_meta en este snapshot; UI/API CVAT sin prueba completa |
| Servidor de origen | SSD identificado montado EXT4 RW; Docker/socket/containerd activos y enabled; sin unidades fallidas | Verificación de API de datos y túnel del PC en curso |
| Capas escribibles | **PASS:** diff de 20 contenedores y metadatos; TAR de 200.683.520 bytes, compare y SHA coincidentes también en PC | Sin capas inmutables ni restauración Docker completa |
| BMC y host | CSMDisabled guardado y arranque UEFI confirmado; sólo Boot0001ubuntu, Order[0001], Nextausente; BBS eliminadas automáticamente | PrimaryDisplay Discrete leído antes de guardar; sin eliminación EFI manual |
| Firmware | Datos8B/SO4B, rollback y recuperación verificados; CVAT API/UI HTTP200 | Anotaciones/medios en ejecución y acceso local todavía no cerrados |

No hay una restauración PostgreSQL pendiente: **la prueba física y lógica ya pasó**.
Lo que falta es arrancar el medio oficial y aplicar firmware de forma controlada,
y comprobar CVAT completo después. La auditoría del TAR pasó y la copia extra ya terminó
en servidor y PC con hashes coincidentes. No se han movido ni
consultado controles del robot durante esta intervención del servidor.

## Copias y prueba de restauración

El backup está en:

```text
/home/luisacuna/app2/recovery/rescue-20261020T075927Z-boa8lm5f
```

storage-rescue-backup-complete.json confirma los 22 TAR, todos los 20 volúmenes
incluidos y ninguno excluido, compare PASS/SHA por archivo, 0600/UID1001 y origen
sin montar tras terminar. El SO conservaba35.648.344.064 bytes libres. El montaje
RO temporal terminó desmontado; no arrancó Docker. El recibo no equivale a imagen
completa ni a una validación del sistema de archivos.

offserver-copy-receipt.json confirma 13 TAR no Ollama + recibo bajo
recovered-offserver/ en la evidencia del PC, con todos sus SHA coincidentes.
Los otros volúmenes Ollama permanecen en el backup del SSD sano del SO.
No actualizar ese SSD mientras sea su única copia adicional.

pg-restore-test-20261020T080940Z/result.json registra
PASS_PHYSICAL_RECOVERY_AND_LOGICAL_ROUNDTRIP: se recuperó una copia nueva de
PostgreSQL15 y se restauró su dump en otra DB vacía con los mismos recuentos.
El dump privado cvat-recovered.dump tiene 260.183 bytes y SHA256:

```text
20a573774561d6e026db34554086590001811fa949e22dbbb9a24d2b4f407997
```

La receta reproducible es [verify_pg_rescue.py](../../scripts/app2/server/verify_pg_rescue.py),
SHAa6504b82d8f5e6e732b97c1045b529ad2cf97f55870e641f789a67b5825f0c17.
Se usó la imagen oficial fijada postgres:15-alpine@sha256:
f7d23353e1b15400d22ebe31189f4d314b87a4c129cc400c8c2d8d4ca127bf81,
contenedor temporal sin red/puertos y una copia privada. Se eliminó el contenedor,
los TAR originales permanecen intactos y los 23 IDs previos siguen presentes.
Loki ya estaba en crashloop: su StartedAt cambió sin comandos dirigidos a él.
26 tests de mantenimiento/rescate/PG pasan; no es una prueba física del robot.

cvat-task5-media-audit.json(SHAb188e7ebca072bc5fe48f0c9c21c01d3f47f5644737321d81bdb720cfffe3dd9)
verifica los dos PNG originales de tarea5: todos los CRC, decodificación completa,
dimensiones, hashes originales y dos registros de imagen del manifiesto. Existen
los directorios de tarea5/job5; no ZIP de chunks ni image_meta en ese snapshot.
Es validación de los originales, no una prueba end-to-end de CVAT.

## Identidad, protecciones y causa todavía sin demostrar

Servidor: luisacuna@192.168.1.43:2649; boot actual
e719f517-0709-417a-b521-7bc8c0212bf6, tras rollback CSM y arranque UEFI comprobado. SSD de datos:
S7DRNJ0X107187F, 2.000.398.934.016 bytes, UUID b819b286-2006-4474-b2d5-13982b0f1536.
SSD del SO: S7DRNJ0X107095A. Los nombres nvme0/nvme1 cambiaron entre arranques;
identificar siempre por serie/UUID. Datos187F está en 8B2QJXD7 y SO095A conserva 4B2QJXD7, lectura post-flash verificada.

Se conservan docker.service, docker.socket, containerd.service,
var-lib-docker.mount y var-lib-docker.automount enmascarados/inactivos, con
fstab noauto,ro,noload/pass0. Backup original de configuración:
/root/app2-storage-maintenance/aisrv-7epmpnej. No ejecutar --restore-config ni
arrancar Docker sólo para probar mientras falten las comprobaciones previstas.
La reversión del helper de guardas no arranca servicios por sí misma.

El controlador dejó de responder y el reset del driver falló(-19/ENODEV), con
CSTSffffffff/PCI_STATUSffff y posterior EIO. El reboot por software no recuperó
el SSD; tras retirada/reconexión de AC reportada volvió a detectarse. No se
confirmó que el apagado ordenado previo hubiera terminado antes de retirar AC.
Esto no demuestra daño NAND, causa APST o firmware concreto.

SMART/error-log anteriores al flash, aportados mediante sudo por el operador, no lectura independiente
del agente: critical_warning0,307K/33,85°C,spare100%,percent_used0,media_errors0,
num_err_log_entries0; ocho entradas de error a cero. unsafe_shutdowns35,
power_cycles36,power_on_hours48 son históricos; no atribuir35al último apagado
ni deducir corrupción EXT4. El extracto del nuevo kernel enumera ambos NVMe sin
reset fallido/EIO visible. Los avisos _OSC[AER LTR DPC] son de capacidades,
no prueba de error de bus. SMART favorable no excluye fallo del controlador.
Kernel observado tras arrancar6.8.0-147-generic; previo6.8.0-142. No se instaló
un kernel durante esta intervención.

**Lectura adicional 09:33:19 UTC, sin cambios:** enlaces PCIe de ambos NVMe
(2c/2d) a 16 GT/s ×4, power/control=on y runtime_status=active. Totales AER del
arranque actual a cero. nvme_core.default_ps_max_latency_us=100000 y política
ASPM [default]; no se aplicó mitigación APST/ASPM. Esto no determina el estado
APST real del dispositivo, pendiente de Get Features NVMe con privilegios, ni
descarta una causa de energía/enlace: los contadores AER corresponden al nuevo
arranque. Evidencia nvme-power-and-link-readonly-post-recovery.json.

## Herramientas aplicadas y estado de ejecución

| Fuente | Estado | Evidencia |
|---|---|---|
| [storage_maintenance.py](../../scripts/app2/server/storage_maintenance.py) | Preparación de guardas aplicada y verificada | Backup fstab/unidades conservado; cronología abajo |
| [storage_rescue.py](../../scripts/app2/server/storage_rescue.py) | Versiónec8e727b…cee8,20.378B/0600; 22tests ychecks reales PASS; inventario/backup de todos los volúmenes ejecutados | storage-rescue-all-volumes-deploy/check.json, inventory y backup-complete |
| [verify_pg_rescue.py](../../scripts/app2/server/verify_pg_rescue.py) | Prueba de restauración en PC PASS, contenedor temporal eliminado | pg-restore-test-20261020T080940Z/ |
| [ipmi_readonly.py](../../scripts/app2/server/ipmi_readonly.py) | Herramienta aislada desplegada; check y consulta de canal1 ejecutados | ipmi-readonly-stage/check.json,ipmi-channel1-query.json |
| [storage_writable_rescue.py](../../scripts/app2/server/storage_writable_rescue.py) | Desplegado; 6 tests PASS; backup real comparado y copiado al PC con SHA coincidente | writable-rescue-backup-complete.json y writable-rescue-offserver-copy.json |

Helper de capas en/home/luisacuna/app2/maintenance/storage_writable_rescue.py,
10.322B/0600/UID1001,SHA0e9765027351ade0ec7275d84918e4ea7392172609448a0cfaf45887c34a89ed.
No se sobrescribió la baseec8e…; FITS real yreserva16GiB preceden a crearTAR.
Backup confirmado en /home/luisacuna/app2/recovery/writable-20261020T082144Z-oeuj8a7l:
20 contenedores, diff de overlay2 y metadatos, writable-layers.tar de 200.683.520 bytes,
compare PASS y SHA256 bf4f0821c36de479841ae123cfbe8f334b52ad65f712a979b91211e0263a5699.
El mismo archivo está en recovered-offserver/ del PC con SHA coincidente
(writable-rescue-offserver-copy.json, 08:23:17 UTC). La fuente quedó desmontada,
las cinco máscaras siguen activas y el SO conserva 35.441.082.368 bytes libres.
No incluye capas inmutables, logs ni todo Docker; restauración Docker completa
pendiente. La auditoría del TAR en PC, sin extracción, verifica 20 raíces,
1.019 entradas y 11 configuraciones de imagen con SHA correctos; conserva
78 enlaces simbólicos y 114 atributos overlay. No equivale a restaurar Docker.
Evidencia writable-layers-offline-audit.json, SHA
f389cc786dcb5cfbd7c99e1e9191183158ace0b487b1966535919efd6607ce2d.
Los estados «pending external copy» de los recibos iniciales describen
su momento de creación, anterior al recibo de transferencia ya verificado.

Las herramientas IPMI están en~/app2/maintenance/ipmi-readonly-tools,nuevo700/files600,
bundleSHA63eb350f26bbb8519c26b7cac9c886a96e8d717491311ea66ba7cc6d2c6865b4,
wrapperb7a7a79bee6563f967de73479249fa4da765214b4956151b024443dc92a8c5e2.
Se extrajeron payloads verificados sin instalar paquetes, ejecutar postinst o
iniciar ipmievd; configuración BMC intacta. Se añadieron después del backup
server-app2, con fuentes/paquete/manifiestos preservados en PC y recetas.
La reversión es dejar de invocar y retirar selectivamente sólo los archivos nuevos,
conservando fuentes/recibos; no hay una configuración BMC modificada que restaurar.

## Secuencia previa de BMC, CD virtual y reinicio — antecedente al ACPI off/on

La consulta del operador identifica canal1LAN, IP estática192.168.1.34/24 y
gateway192.168.1.251. Los avisos stderr se conservaron; stdout aporta los valores.
La web https://192.168.1.34/ respondió HTTP200/TLS1.3 en443 sin autenticación;
80 agotó tiempo. El operador confirmó después un único login manual correcto;
la captura muestra ASMB9-iKVM 1.32.0, Host Online y menús Remote Control / Image
Redirection. Hasta esa fase manual no hubo autenticación automatizada ni reset o cambios de cuentas,
contraseñas o configuración BMC. La [FAQ oficial ASUS ASMB9](https://servers.asus.com/support/faq/detail/1047906)
fundamentó la consulta del valor inicial, que no se publica aquí. Ver el menú no
demostró por sí solo una consola funcional. Después, el operador y la captura
confirmaron vídeo KVM de Ubuntu 24.04.5, aisrv tty1. Después, el operador confirmó
teclado Enter y adjunto de la ISO mediante Start Media / Stop Media. Ese adjunto
es un cambio de estado temporal del medio virtual, sin cambios de cuentas o red.
/dev/sr0 se presenta como Virtual CDROM de 102.400 sectores / 50 MiB. La lectura
inicial sin root fue denegada por permisos, no por una ISO inválida. La lectura sudo
posterior coincidió con SHA f05508…93d5; guardfile 0832Z conservado.

La orden del operador verificó el hash y ejecutó el primer reinicio ordenado.
08:36:50 UTC: Ubuntu arrancado, boot 93957c9b-5c54-490a-ba45-ea8e85b4fcb0,
uptime 37,70 s. A las 08:38:05 UTC, ambos NVMe siguen live con firmware 4B2QJXD7;
check de guardas PASS, origen sin montar y Docker detenido. No se alcanzó el
actualizador. Se ha pedido al operador `sudo systemctl reboot --firmware-setup`
para entrar en configuración ASUS, sin depender del tiempo de F8; **ejecutado y pantalla ASUS/UEFI confirmada por el operador**. La solicitud UEFI de una sola vez fue ejecutada por el operador; no se modificaron
ajustes Boot Order, CSM o Secure Boot. La consulta previa de systemd 255.4 confirmó soporte
CanRebootToFirmwareSetup=challenge / estado false. Si se ejecuta, solicita una
entrada UEFI de una sola vez mediante OSIndications; no es un cambio de firmware
SSD ni de parámetros BIOS. [Contrato systemctl](https://www.freedesktop.org/software/systemd/man/latest/systemctl.html#--firmware-setup).

La actualización necesaria está autorizada con cautela, pero ahora sólo se
trabaja por SSH, sin monitor/teclado/USB. La
[receta Samsung](../../scripts/app2/server/FIRMWARE_SAMSUNG_990_PRO.md) conserva ISO8B
oficial preparada/inspeccionada en PC:52.428.800bytes,
SHAf05508f3228960fc1501fe5a27d3a826377332afc8c021aac44487c8fd1c93d5.
Es hash local, no firma/checksum publicado del fabricante. También se copió la ISO
al PC en /home/lacuna/Descargas/Samsung_SSD_990_PRO_8B2QJXD7.iso (0600, 50 MiB),
con el mismo SHA verificado; firmware-iso-downloads-copy.json, 08:28:46 UTC.
Reversión: retirar sólo ese archivo si sigue coincidiendo su hash. El operador
confirmó Browse File → ISO → Start Media y hash del CD virtual; primer reinicio
ordenado completado en Ubuntu como se registra arriba. No se escribió USB físico,
ejecutó el actualizador o aplicó firmware/BIOS. La consulta de sólo lectura confirma
UEFI de 64 bits y Secure Boot desactivado; el arranque real de esta ISO en ASUS
sigue sin validar, aunque el medio virtual y su hash sí están comprobados
(firmware-boot-mode-readonly.json y firmware-reboot-progress-second.json).
No ejecutar el binario extraído por SSH como sustituto del método oficial.

[Samsung](https://semiconductor.samsung.com/consumer-storage/support/tools/) publica
notas7B sobre reconocimiento intermitente y8B sobre lectura. Son una pista para
corregir después de preservar datos, no una causa o solución garantizada.
El manual de2019 enlazado es genérico, no prueba de esta combinación de990PRO/ASUS.

## Punto de reanudación

1. Conservar las copias y los recibos ya verificados, sin restaurar sobre el
   origen. No repetir backups, transferencias o pruebas PostgreSQL ya verificados.
2. Continuar anotación y revisión humana del piloto en tarea 5 / trabajo 5.
   API, anotaciones, originales, chunk y túnel ya se verificaron; no repetir
   recuperación o pruebas para retomar.
3. Conservar backups/undo y observar fiabilidad del almacenamiento durante el uso.
   No hay sudo pendiente, entrenamiento real o movimiento del robot en esta fase.
4. Tras la corrección, registrar versión/SMART/logs, comprobar integridad offline
   cuando corresponda y recuperar CVAT antes de retirar guardas. Validar carga,
   reposo y reinicios controlados;24–48 h es una primera ventana orientativa, no garantía.
5. Si recae, aislar un cambio cada vez(APST/PCIe/ranura/alimentación/temperatura)
   y valorar diagnóstico/RMA. No cambiar GRUB/ASPM/BIOS indiscriminadamente.

## Evidencia y conservación

Carpeta privada:
../Humanoide-vla-evidence/20261020T061422Z_APP2_RESUME_READONLY/.
Los TAR,dumps,ISO,paquetes ycredenciales permanecen fuera de Git. Los recibos
incluyen procedencia de las salidas sudo del operador; fotos originales intactas.
Antes de esta consolidación se conservaron los siete documentos en
before-current-state-consolidation/. Las observaciones anteriores se mantienen
abajo como historial, sin sustituir este único estado vigente.

## Historial anterior — no usar como estado actual

<details>
<summary>Registro histórico conservado de las fases previas; sus pendientes fueron resueltos o actualizados arriba</summary>

### HISTÓRICO — Resultado y alcance actual

**Backup terminado y verificado a nivel de archivos:**
storage-rescue-backup-complete.json,08:02:30UTC/10:02:30Europe/Madrid, confirma
22 TAR que suman47.034.378.240 bytes(20 volúmenes,server-app2 ydocker-definitions)
en /home/luisacuna/app2/recovery/rescue-20261020T075927Z-boa8lm5f sobreSO 095A.
Todos los 20 volúmenes archivados/comparados,excluded []; cada tar concompare PASS y
SHA256,0600 / UID 1001. No quedan montajes de origen/rescate; raíz libre35.648.344.064B.
El recibo final dice ARCHIVES_VERIFIED_PENDING_EXTERNAL_COPY_AND_RESTORE_TEST.

No es una imagen completa de 2 TB ni auditoría/respaldo de capas escribibles; aún no hay
restauración PostgreSQL probada, integridad de EXT4 o CVAT funcional. El gate continúa
NOT_CLEARED_WRITABLE_LAYERS_EXTERNAL_COPY_RESTORE_TEST_PENDING.

offserver-copy-receipt.json,08:06:17UTC/10:06:17Madrid, confirma13 TAR no Ollama
(1.373.347.840B)+recibo en recovered-offserver/ de la evidenciaPC: **transferencia
VERIFICADA,13 SHA coincidentes**,all_copied_hashes_matchtrue. No hay tercera copia
deOllama en PC; sus respaldos permanecen en el SSD sano delSO. Las copias mayores permanecen en el
SO sano; no actualizar eseSSD ni ambos a la vez. El siguiente paso previsto es
probar restauración aislada en PC, todavía sin resultado, sin arrancar el
Docker del origen.

El backup ha terminado y el origen está desmontado; ya puede prepararse la
herramienta IPMI aislada sin alterarAPP2mientras se estaba archivando. La herramienta
ya fue desplegada y comprobada sin llamadas BMC, como se registra abajo; no hay
paquetes instalados, servicios iniciados o configuración BMC cambiada. Firmware
sigue sin aplicar.

### Evolución del backup — observaciones previas al resultado final

**Backup iniciado y todavía sin resultado final:** backup-progress-second.json,
07:59:52UTC/09:59:52Europe/Madrid, confirma el destino
/home/luisacuna/app2/recovery/rescue-20261020T075927Z-boa8lm5f. La fuente es
/dev/nvme0n1p1, major:minor259:5, montada temporalmente en
/root/app2-rescue-pz2a5jgn con ext4ro,norecovery,nodev,nosuid,noexec. No hay
arranque de Docker. El log sólo contiene BACKUP=..., aún sin JSONfinal/recibo
completo: no declarar copia validada ni desmontaje final realizado.

La raíz conserva65.409.859.584bytes libres, unos17,27GB menos que al empezar;
esto muestra escritura en curso, no integridad de los archivos. Temperaturas
observadas: SSDdatos37,85°C/SO36,85°C. No instalar o preparar herramientasIPMI
bajoAPP2 hasta terminar, para no alterar los ficheros fuente que se respaldan.

Los checks de no montaje y tamaños de las secciones siguientes son previos a
esta copia; el cleanup del inventario sí se verificó, el del backup sigue pendiente.

**El SSD de Docker vuelve a detectarse tras la retirada/reconexión de AC reportada
por el operador.** SSH está operativo y el arranque es nuevo:
`cebc2464-2073-4f1e-82fc-17ee30941a22`. La consulta
`booting-review-initial.json`,07:25:35UTC/09:25:35Europe/Madrid, uptime40,92s,
y `cold-boot-system-review.json`,07:26:14UTC/09:26:14Madrid, uptime78,62s,
verifican dos controladores NVMe en estado **live**.

| Identidad | Observación actual tras este arranque |
|---|---|
| SSD Docker/datos | Samsung990PRO2TB, serialS7DRNJ0X107187F,2.000.398.934.016bytes; actualmente nvme0n1 y partición nvme0n1p1 |
| UUID Docker | b819b286-2006-4474-b2d5-13982b0f1536, presente; montaje del backup ya terminado y desmontado |
| SSD del SO | serialS7DRNJ0X107095A, actualmente nvme1n1; EFI en nvme1n1p1 |
| Firmware observado por sysfs | 4B2QJXD7 en ambos SSD |
| Protecciones | cinco máscaras /dev/null/unidades inactive/masked; fstab defaults,noauto,ro,noload0,0; /var/lib/docker sin montar |
| Estado del SO | systemd running, cero unidades fallidas y ningún job pendiente |
| Recursos en reposo | RAM~503GiB; RTX6000Ada49140MiB,2MiB usados,32°C/0%; raíz82.683.002.880bytes libres |

Una lectura adicional, `cold-boot-hardware-readonly.json`, a184,11s del mismo
boot, mantiene ambos NVMe live, UUID correcto y ausencia de montaje. Hwmon informa
temperatura composite Docker33,85°C/SO36,85°C y alarmas0; ambos enlacesPCIe están
a16GT/s x4. nvme-cli2.8/libnvme1.8 están presentes. Son observaciones de hardware,
no un informe SMART ni una prueba de ausencia de errores del medio. La salida
de smartctl identifica el kernel ahora activo como6.8.0-147-generic; antes del
mantenimiento se observó6.8.0-142-generic. No se instaló un kernel en esta
intervención ni se atribuye aquí quién instaló esa versión.

**Reaparición no significa datos íntegros ni CVAT recuperado.** Sólo se ha
montado temporalmente el origenro,noload para inventario y desmontado al terminar,
como se registra abajo. No se ha ejecutado fsck, copiado datos, restaurado
configuración o arrancado Docker.
Las cargas Docker, incluido CVAT/Ollama, permanecen detenidas por las protecciones.
La raíz sana no tiene espacio para una imagen completa de2TB y el operador
confirma que **no dispone de otro almacenamiento**. No hay destino disponible
para la imagen completa; se valora como PLAN una copia selectiva de datos CVAT
al SSD sano del SO, primero comprobando tamaños, capacidad y permisos. El origen ya se inventarió mediante montaje temporalRO y cleanup verificado;
la copia todavía no se ha iniciado. La ausencia de otro disco no implica que
sea imposible conservar datos selectivos; su viabilidad sigue pendiente.
Conservar primero datos antes de reparar o reanudar escrituras sobre el origen.

**SMART/error-log/kernel recibidos correctamente del operador:** fuente sudo
pegada en el chat, no lectura independiente del agente. Archivos
`cold-boot-smart-user.json`, `cold-boot-error-log-user.json`,
`cold-boot-kernel-user.txt` y recibo `cold-boot-smart-user-receipt.json`,
07:30:29UTC/09:30:29Madrid, conservan salida e interpretación.

- critical_warning0; temperatura307K/33,85°C; reserva100%; percent_used0.
- media_errors0 y num_err_log_entries0; las8entradas consultadas de error-log
  tienen todos sus campos a cero.
- unsafe_shutdowns35, power_cycles36 y power_on_hours48 son contadores históricos.
  No atribuir35al último apagado, a esta intervención o a un daño de EXT4.
- El extracto del kernel del nuevo boot enumera ambos NVMe y no muestra
  reset fallido, controllerdown o EIO. Es un extracto, no una validación completa.
  Los avisos _OSC sobre capacidades[AER LTR DPC] no acreditan un error de bus.

El primer pegado sin separadores produjo un error de argumentos de la CLI; ese
intento no fue un resultado de salud. La línea corregida con && sí produjo los
resultados anteriores. La ausencia de avisos críticos/errores reportados ahora
no garantiza integridad de EXT4 ni de PostgreSQL y no demuestra la causa del
incidente. Backup e integridad de datos siguen pendientes; sólo el montaje
temporalRO/inventario/desmontaje posterior están acreditados. Sin copia, reparación,
arranque de Docker o actualización de firmware.

**Pista de firmware, causa no demostrada:** la
[página oficial de herramientas Samsung](https://semiconductor.samsung.com/consumer-storage/support/tools/)
publica para990PRO7B2QJXD7(septiembre2025), con una corrección de
no-reconocimiento intermitente, y8B2QJXD7(diciembre2025), con mejora de estabilidad
de lectura. Ambos SSD instalados muestran4B2QJXD7. Es una pista para revisar
tras preservar los datos, no prueba de que esa fuera la causa. No se ha aplicado
ninguna actualización y no debe hacerse antes del rescate.

Backup de configuración conservado en
`/root/app2-storage-maintenance/aisrv-7epmpnej`; cinco máscaras y fstab protegido
se mantienen. Sin conexión ni movimiento del robot, cambios de anotaciones o
instalación de alternativa PC; esa alternativa sigue aplazada.

### HISTÓRICO — Autorización de rescate y corrección — preestado registrado

El operador comunica: **«me han dado autorización para actualizar lo que sea
necesario, pero por favor se cauteloso»**. Queda autorizada la secuencia de
preservar selectivamente datos y preparar la corrección; primero SSD de datos
serialS7DRNJ0X107187F tras respaldo y comprobaciones. La autorización no acredita
que se haya instalado/aplicado nada. El operador aclara que **ahora sólo se puede
trabajar por SSH**, sin monitor, teclado o USB disponibles. Preparar la ISO y
rescatar selectivamente por SSH sigue autorizado; aplicar firmware queda
PENDIENTE de consola y método oficial compatible. No se aplicará un binario
extraído por SSH como sustituto de ese método. La consulta
rescue-tools-readonly.json detecta /dev/ipmi0 y sysfsipmi0, con driversipmi_si,
ipmi_devintf,ipmi_msghandler eipmi_ssif cargados. Hay interfaz IPMI local, pero
la consola BMC sigue PENDIENTE de acceso/configuración/credenciales; aún no se
leyó su configuración. ipmitool no está instalado. No confundir sólo SSH
actualmente disponible con inexistencia de BMC o acceso remoto ya resuelto.
GNUtar1.35,rsync,dumpe2fs ydebugfs ya existen; raíz libre82.682.929.152bytes en
esa consulta. No se instaló ni cambió ningún paquete o configuración. Mantener el SSD del SO 095A como destino sano
si conserva la única copia; no actualizar ambos dispositivos a la vez.

`authorized-maintenance-before.json`,07:43:52UTC/09:43:52Europe/Madrid,
bootcebc2464-2073-4f1e-82fc-17ee30941a22 y uptime1136,79s, verifica de nuevo
SSD/UUID presentes, ambos NVMe live, cinco máscaras y unidadesinactive,
fstabnoauto,ro,noload0,0 y ausencia de montaje. Éste es el preestado de esta fase.

Preparación técnica en curso: helper storage_rescue.py para check de lectura,
inventario privilegiado con montaje temporalro,noload y cleanup, y copia
selectiva del origen de sólo lectura al SO sano. Receta oficial de firmware/ISO
se prepara por separado. Las fuentes locales ya existen:
[storage_rescue.py](../../scripts/app2/server/storage_rescue.py) y
[receta de firmware](../../scripts/app2/server/FIRMWARE_SAMSUNG_990_PRO.md).
El helper ya está instalado y --check real verificado, como se registra abajo.
El inventario privilegiado y su desmontaje ya están acreditados, como se
registra abajo; no se ha realizado backup ni creado USB/actualizado firmware. Los avances se registrarán sólo al disponer de logs:
fuente/hash, ubicación exacta, ejecución, limpieza y estado final. No se solicita
una nueva aprobación de cada paso reversible ya incluido en esta autorización.

### Preparación local de fuentes e ISO — no despliegue/flash

La receta APP2-FIRMWARE-PREP-20261020 registra la ISO oficial 8B2QJXD7 descargada
por HTTPS e inspeccionada estáticamente en el PC;52.428.800bytes y SHA256 local
f05508f3228960fc1501fe5a27d3a826377332afc8c021aac44487c8fd1c93d5, recontrastados
con el archivo privado. Fuentes y manifiestos bajo firmware-preparation/ en la
evidencia; no son firma/checksum publicado por Samsung. No se ejecutó software
de la ISO ni se escribió USB/firmware/BIOS/BMC. La inspección no prueba arranque
UEFI/SecureBoot/ASUS y sólo SSH no controla la utilidad tras abandonar Ubuntu.

El helper de rescate local separa check sin montaje, inventario privilegiado
ro,noload temporal y backup selectivo al SO. Comprueba identidad serial/UUID,
máscaras/fstab y que el destino sea el SO sano; reserva16GiB. Copia CVAT y
app2_datasets/checkpoints; caché entreno sólo si cabe. El resto de volúmenes queda
fuera de esa selección y el recibo no libera su gate de firmware. Tar compara
bytes/metadatos con origen y guarda hash, pero la recuperación PostgreSQL sobre
copia sigue pendiente. --check sin montaje e inventario privilegiado con montaje temporalRO/cleanup
se ejecutaron en el servidor; --backup todavía no está realizado.

### Despliegue real del helper y primer check sin montaje

`storage-rescue-deploy.json`,07:52:22UTC/09:52:22Madrid, confirma creación nueva
con O_EXCL en /home/luisacuna/app2/maintenance/storage_rescue.py,18669bytes,
permisos0600 / UID 1001; no existía archivo previo que sobrescribir. SHA256 local y
remoto coinciden:935ec1875f9ffabb1b6f08083cf60c9d0f075b4ba28c058c9aaed72cc4dcf74b.
Las20pruebas offline pasan(1,108s); no son ensayos del montaje real.
`storage-rescue-check.json`,07:52:23UTC/09:52:23Madrid, rc0/CHECK_OK_NO_MOUNT,
confirma origen/dev/nvme0n1p1/serial187F y destinoOS095A, sin montar ni copiar.
Reversión del despliegue: dejar de invocar el helper y conservar su fuente/recibos;
no exige restaurar fstab o retirar máscaras, que deben mantenerse.

El operador recibió una línea sudo --inventory que conserva salida privada en
/home/luisacuna/app2/maintenance/rescue-inventory-20261020T075223Z.json.
El resultado posterior se recibió y se registra a continuación; la copia aún no
se ha ejecutado. Sudo se introduce en su terminal,
sin revelar contraseña ni añadirla a las recetas.

`ipmi-sysfs-readonly.json` identifica firmwareBMC 1.32/IPMI 2.0 eIDs; acceso,
configuración, credenciales y consola siguen pendientes. La simulación
`ipmitool-install-plan-readonly.json` propone3paquetes nuevos(freeipmi-common,
libfreeipmi17,ipmitool),0actualizaciones/0borrados. No hay instalación real ni
configuración/acción BMC ejecutada.

### Inventario real y limpieza verificados; copia todavía pendiente

El operador comunica INVENTARIO_LISTO. storage-rescue-inventory.json,
07:54:10UTC/09:54:10Europe/Madrid, rc0, registra20 volúmenes legibles y
source_unmounted true. El helper instalado ejecutó su montaje temporal con
ro,noload,nodev,nosuid,noexec para medir y terminó con desmontaje normal. La
comprobación posterior/proc mountinfo no encuentra montajes Docker o de rescate.
No hubo desmontaje forzado/lazy, reparación o arranque de Docker. Ese inventario
fue aplicado y su cleanup verificado; la copia iniciada después es otra fase.

- Plan sólo APP2:2.467.282.944bytes estimados, cabe.
- Todos los 20 volúmenes:46.832.386.226bytes lógicos; estimación conservadora que
  incluye ficheros/definiciones y margen:51.843.033.088bytes.
- Libres del SO:82.682.867.712bytes, reserva mínima17.179.869.184bytes(16GiB).
  También cabe el plan de todos los persistentes, sin excluir los de Ollama.

Bajo la autorización vigente se elige **respaldar todos los20 volúmenes** y
conservar recetas/definiciones, en vez de limitarse aAPP2. El helperv2con
--all-volumes ya está desplegado y su check verificado, como se registra abajo.
El inventario anterior se ejecutó con v1935ec…f74b, conservada como respaldo.
Todavía no se realizó backup ni se probó restauración PostgreSQL; no se ha
retirado ninguna protección ni aplicado firmware.

La inspección estática delDEB deipmitool revela postinst que puede iniciar
ipmievd. No se instalarán esos paquetes/servicios como método de lectura; se
prepara extracción aislada de los3DEB verificados, sin postinst/daemon. Aún no
hay ejecución de esa herramienta ni configuración BMC cambiada.

### Despliegue v2 para todos los volúmenes — backup aún pendiente

storage-rescue-all-volumes-deploy.json,07:57:32UTC/09:57:32Madrid, registra
20378bytes/0600 y SHA256ec8e727b23d2288ac46be24d4c0ab8867f46100a38a9578ec83a781cebffcee8
en /home/luisacuna/app2/maintenance/storage_rescue.py. Antes del cambio atómico,
se contrastó el hash de v1 y se respaldó en
/home/luisacuna/app2/maintenance/storage_rescue.before-all-volumes.935ec1875f9f.py.
22 tests offline pasan(1,103s). storage-rescue-all-volumes-check.json,
07:57:33UTC/09:57:33Madrid, rc0/CHECK_OK_NO_MOUNT, confirma origen187F/destino095A
sin montaje. Este check no acredita una copia.

La opción --all-volumes exige tamaños legibles y capacidad para todos los
volúmenes; no descarta ninguno para caber. Conserva reserva16GiB y verifica cada
archivo contra el origen. No es una imagen de SSD ni respalda sus capas
escribibles. El recibo mantiene un gate pendiente de capas importantes,
copia externa y prueba de restauración; tar/compare no demuestra PostgreSQL sano.

El operador recibió una línea sudo --backup --all-volumes con salida privada en
/home/luisacuna/app2/maintenance/rescue-backup-20261020T075733Z.log. El backup ya se inició, como confirma la actualización actual. Todavía no hay
resultado final ni recibo completo; no afirmar datos completamente respaldados
o cleanup final de esa ejecución. El desmontaje del inventario previo sí se
verificó; las protecciones siguen aplicadas.

### Copia externa verificada e IPMI aislado desplegado

13 TAR no Ollama,1.373.347.840 bytes yreceipt.json llegaron alPC/recovered-offserver;
los13 SHA256 coinciden con el recibo del backup. Sólo esos13 archivos se copiaron
fuera: Ollama permanece respaldado en elSSD delSO, no en una tercera copia.
La restauración PostgreSQL aislada en PC está en preparación; no tiene resultado
válido todavía y no se ha iniciado el Docker del servidor.

ipmi-readonly-stage.json,08:05:30UTC/10:05:30Madrid, acredita creación nueva de
/home/luisacuna/app2/maintenance/ipmi-readonly-tools,carpeta700/files600.
BundleSHA25663eb350f26bbb8519c26b7cac9c886a96e8d717491311ea66ba7cc6d2c6865b4;
wrapperipmi_readonly.py SHA256b7a7a79bee6563f967de73479249fa4da765214b4956151b024443dc92a8c5e2.
Payloads extraídos de3DEB verificados; no se ejecutan postinst/daemon ni se
instalan paquetes. ipmi-readonly-check.json,08:05:31UTC/10:05:31Madrid,rc0,
CHECK_OK_NO_BMC_CALL: sin llamada/configuración BMC, no hay consola probada.

El operador recibió la consulta privilegiada dechannel1 ylanprint si el canal
es802.3LAN, con salida privada
/home/luisacuna/app2/maintenance/ipmi-channel1-20261020T0806Z.txt. Informe ya recibido: IP ywebHTTPS verificadas abajo; autenticación/consola/medio
virtual siguen pendientes. Este añadido aAPP2 se hizo
después del backup server-app2; su código/paquete privado/manifiestos se conservan
en PC y la receta para reproducirlo. Reversión: dejar de invocar el wrapper y
retirar selectivamente sólo su directorio privado si se decide; no hay paquetes,
servicios o configuración BMC modificados que revertir.

### Restauración PostgreSQL física y lógica verificada en elPC

Prueba pg-restore-test-20261020T080940Z/result.json:
PASS_PHYSICAL_RECOVERY_AND_LOGICAL_ROUNDTRIP. Desde losTARexternos verificados,
se extrajo una copia nueva privada y recuperó PostgreSQL15; pg_dump produjo
cvat-recovered.dump,260.183bytes,SHA256
20a573774561d6e026db34554086590001811fa949e22dbbb9a24d2b4f407997.
Ese dump se restauró enotraDBvacía y los recuentos coinciden:4tareas,4jobs y
9polígonos globales. Existen tarea5,job5 asociado yshape10frame1; se conserva el
primer contorno histórico. No confundir9formas globales con9piezas reales dejob5.
No se ha validado todavía la aplicaciónCVAT completa ni su acceso a imágenes.

Fuente reproducible [verify_pg_rescue.py](../../scripts/app2/server/verify_pg_rescue.py),
SHA256a6504b82d8f5e6e732b97c1045b529ad2cf97f55870e641f789a67b5825f0c17,
26tests mantenimiento/rescate/PG pasan. Docker oficial fijado:
postgres:15-alpine@sha256:f7d23353e1b15400d22ebe31189f4d314b87a4c129cc400c8c2d8d4ca127bf81.
Imagen descargada alPC, copia nueva sin enlaces externos y contenedor temporal
sin red/puertos, con rootfsRO,capdrop y límites. No se montó el SSD del servidor
ni se arrancó su Docker. WAL/recovery llegó aready; revisar postgres.log para
la secuencia, no interpretar un probe inicial previo already como fallo final.

El contenedor temporal se eliminó, archivosTARoriginales intactos y23IDs previos
conservados. review.json registra StartedAtcambiado de/fullstack-loki-1,ya en
crashloop antes de la prueba; no hubo comandos dirigidos aese contenedor.
Resultado,review,postgres.log,receta ydump privados permanecen en la evidencia;
no añadir datos/credenciales aGit. La prueba no aplicó firmware o restauróCVAT.

### BMC localizado y webHTTPS accesible — autenticación/consola pendientes

ipmi-channel1-query.json recoge la consulta privilegiada del operador:
channel1 es802.3LAN,IPestática192.168.1.34/24 ygateway192.168.1.251. Los avisos
stderr(IANA/deviceID/respuestaID) se conservan; stdout ofrece los parámetros
válidos. No se modificó red, usuario, credencial o configuraciónBMC.

bmc-web-readonly.json,08:09:44UTC/10:09:44Madrid, verifica443accesible,
HTTP200/TLS1.3 enhttps://192.168.1.34/ sin intento de autenticación; puerto80
agota tiempo. Esto demuestra webHTTPS disponible, **no accesoKVM/VirtualMedia**.
Credenciales autorizadas se han solicitado sin pedir que se publiquen en elchat;
acceso yfunciones de consola siguen pendientes. No se ha reiniciado BMC ni
aplicado firmware, BIOS o parámetros de energía.

### Rescate de capas escribibles — helper nuevo, aún sin ejecutar

Para cubrir datos que no estaban en los volúmenes, se prepara
[storage_writable_rescue.py](../../scripts/app2/server/storage_writable_rescue.py).
El preflight de lectura writable-rescue-preflight.json,08:14:14UTC, confirma
baseec8e… intacta, cinco máscaras, origen sin montar y35.641.851.904bytes libres.

writable-rescue-stage.json,08:15:01UTC/10:15:01Europe/Madrid, acredita creación
nueva en/home/luisacuna/app2/maintenance/storage_writable_rescue.py,
10.322bytes,0600/UID1001,SHA256
0e9765027351ade0ec7275d84918e4ea7392172609448a0cfaf45887c34a89ed.
No existía versión anterior; no se sobrescribió el helper base. Su propósito es
respaldar overlay2 escribible y metadatos Docker, no capas inmutables ni imagen
del disco completo. **Backup todavía sin resultado**:6tests fixture versionados pasan, como acredita
writable-rescue-tests.json; --backup solicitado al operador, salida pendiente.
La comprobación FITS real precede a crearTAR y mantiene reserva16GiB.
No declarar esas capas respaldadas ni liberar firmware por haber colocado el
archivo. Reversión del despliegue: dejar de invocarlo y retirar selectivamente
sólo el archivo nuevo si procede, manteniendo fuente yrecibo.

Credenciales deBMC,KVM/VirtualMedia, validaciónCVAT completa/imágenes y aplicación
de firmware siguen pendientes; este despliegue no cambió esos estados.

### HISTÓRICO — Hoja de ruta correctiva — AUTORIZADA, ejecución técnica pendiente

SMART sin avisos actuales no excluye un fallo del controlador. La recuperación
de acceso tras retirar alimentación tampoco demuestra una causa única. La
siguiente ruta busca preservar datos y probar una corrección concreta por etapas;
la autorización ya está recibida, pero su ejecución y resultados siguen
pendientes. No es una garantía de solución.

1. **Preservar y probar restauración.** Conservar los datos importantes de
   Docker/CVAT y del SO, según qué SSD vaya a actualizarse. La copia selectiva de
   esenciales en el SO sano es sólo una opción pendiente de tamaños/capacidad:
   hay82.683.002.880bytes libres, no espacio para un clon de2TB. No se ha realizado
   esa copia ni probado su restauración. Si queda como única copia en el SSD del
   SO, no actualizar ese SSD ni ambos a la vez; también necesita respaldo antes
   de cualquier futura intervención sobre él.
2. **Primera corrección razonable tras el respaldo: firmware del SSD de datos.**
   Verificar modelo/serialS7DRNJ0X107187F y compatibilidad oficial antes de pasar
   de4B2QJXD7 a la versión8B2QJXD7 publicada actualmente por Samsung. Las notas
   de7B describen reconocimiento intermitente y las de8B mejoras de lectura;
   son una pista, no causa demostrada ni garantía. Usar el método oficial ISO/USB
   de arranque, con reinicio y acceso físico/consola. La arrancabilidad en esta
   ASUS sigue PENDIENTE; no se ha preparado o probado el USB. El manual
   Firmware_Update_Utility_UserManual.pdf enlazado en la
   [página oficial Samsung](https://semiconductor.samsung.com/consumer-storage/support/tools/)
   es genérico de2019, no una demostración de990PRO funcionando en esta placa.
   No actualizar ambos SSD simultáneamente ni el SO que conserve la única copia.
3. **Integridad y observación tras la copia.** Revisar EXT4/DB offline y sobre
   copia cuando corresponda, conservando el origen. Tras la corrección y una
   restauración comprobada, validar carga habitual, reposo y reinicios
   controlados con registro.24–48horas es una primera ventana orientativa de
   observación, no prueba de fiabilidad definitiva. No se ha ejecutado esta fase.
4. **Si reaparece el fallo, aislar variables.** Revisar por un técnico fijación
   M.2, ranura, alimentación/PSU y temperaturas. Investigar APST/PCIe mediante
   un único cambio controlado por vez, con estado previo, registro y reversión;
   no cambiar GRUB/ASPM/BIOS indiscriminadamente. Según si el fallo sigue al SSD
   o a la ranura/plataforma, tramitar diagnóstico/RMA del componente pertinente.

Estado aplicado actual sin cambios: cinco máscaras y fstab protegido, SSD sin
montar, Docker detenido. No hay copia, reparación, firmware, GRUB/ASPM/BIOS,
prueba de carga o nuevo reinicio ejecutado como parte de esta hoja de ruta.

### HISTÓRICO — Cronología anterior — observaciones de cada fase, no estado actual

Los estados ausente/dead, espera de apagado y encendido pendiente que siguen
corresponden a instantes anteriores. El estado vigente es el resultado posterior
al nuevo arranque descrito arriba; no repetir las órdenes históricas.

**Actualización posterior:** el operador REPORTA retirada de AC durante un minuto
y reconexión. No quedó confirmado que antes hubiera concluido el apagado
ordenado o se hubieran detenido los ventiladores; tampoco se confirma aún que
se pulsara encendido, un nuevo boot o el retorno del SSD. Se indicó que, si no
arranca automáticamente, pulse brevemente encendido una sola vez y no repita si
ya arranca. Estado de encendido y reaparición de datos PENDIENTES; la consulta
posterior se conservará en `after-ac-reconnect-readonly.json`. Las protecciones
son las últimas verificadas antes del apagado, no una comprobación fresca tras
reconectar. Sin datos copiados ni recuperación demostrada.

**Fase anterior, conservada como historia:**

**Actualización de apagado:** el operador indica que han pasado entre2y5minutos
desde la orden y los ventiladores siguen activos; no hay monitor conectado.
La consulta `shutdown-delay-readonly.json`,20-10-2026 07:18:37UTC/09:18:37Madrid,
termina rc255, «No route to host». Esa pérdida de acceso NO demuestra que el
apagado haya terminado ni identifica el SSD como causa de la demora. Se mantiene
AC conectado, sin force, Reset ni corte forzado. Si persiste, hace falta observar
la consola con un monitor antes de decidir cómo continuar. No se ha completado
el ciclo frío, no hay datos copiados ni evidencia de recuperación del SSD.

Las comprobaciones de SSH/protecciones descritas a continuación son anteriores
a esta orden; la finalización del apagado queda pendiente de comprobar.

El servidor vuelve a estar accesible por SSH tras el único reinicio ordenado
aplicado por el administrador. Las cinco máscaras y el fstab de mantenimiento
están verificados; `/var/lib/docker` permanece sin montar. El UUID del SSD de
Docker sigue ausente, por lo que CVAT y las demás cargas de Docker permanecen
detenidos. El reinicio no ha recuperado acceso al dispositivo de datos.

El operador confirma ahora: **«tenemos acceso físico ahora»**. El ciclo frío está
preparado. La orden de apagado ya se solicitó, pero TODAVÍA NO se ha confirmado
su finalización ni retirado alimentación.
La consulta de llegada `physical-arrival-readonly.json`,07:13:00UTC/
09:13:00Europe/Madrid, verifica el mismo boot94f200a2…3f55, uptime2249,63s,
las cinco máscaras/unidades inactive, fstab protegido, ningún montaje de Docker
y UUID de datos ausente. Próximo paso coordinado: el operador solicita el apagado
ordenado en su terminal, espera a que termine y sólo entonces retira AC; tras
encender, se comprueba UUID/serie y se prioriza copia si reaparece el SSD.

Antes sólo se disponía de SSH, sin presencia ni BMC/gestión de energía; esa fase
se conserva como historia más abajo. Mantener máscaras/fstab protegido; no resets,
reparaciones, restauración de configuración ni arranque de Docker para probar.
El backup sigue en `/root/app2-storage-maintenance/aisrv-7epmpnej`. El agente no
ha enviado apagado, reinicio ni órdenes al dispositivo en esta actualización.

No se ha conectado ni movido el robot, ni modificado anotaciones. La alternativa
de continuar la anotación en el PC queda aplazada por decisión del operador; no
se instaló ni se prometió su disponibilidad. La copia local del19-10 no
sustituye la base actual de CVAT ni permite asumir qué trabajo se guardó después.

La fase inicial de esta incidencia fue sólo de lectura: CVAT ya fallaba por
loopback y el túnel local anterior estaba cerrado; no se abrió uno nuevo. Después
se aplicó la preparación y un único reinicio, como recoge la secuencia siguiente.

### HISTÓRICO — Evidencia directa anterior al reinicio

| Comprobación | Observación |
|---|---|
| CVAT por `localhost:18080` del servidor | Portada y `/api/server/about`: HTTP 404 |
| Contenedores app2 | 18 procesos mostrados como Up 20 hours; kvrocks/redis_ondisk unhealthy |
| `docker inspect` de Traefik | `overlay2/.../lower: input/output error` |
| Montaje de Docker | `/dev/nvme0n1p1`, ext4, `/var/lib/docker`; figura `rw` |
| `lsblk` del dispositivo de Docker | Samsung SSD 990 PRO with Heatsink 2TB, `nvme0n1`, **0 B**, estado **dead** |
| Segundo NVMe | Mismo modelo, `nvme1n1`, 1,8 T, estado live |
| `df` de Docker | Informa 1,7 T libres; no demuestra acceso sano al dispositivo |
| Backend directo descubierto por API Docker | `172.19.0.15:8080/api/server/about`, Host localhost: HTTP 500 |
| UI directa descubierta | `172.19.0.18:8080`: connection refused |
| Registro de kernel sin privilegios | Sin acceso a los mensajes del sistema |
| `sudo -n journalctl` | Requiere contraseña; no se intentó introducirla desde el agente |

La API de listado de Docker sigue respondiendo y permitió descubrir IPs sin
inspeccionar capas. Se usaron sólo para consultas HTTP; no se cambiaron redes,
puertos o rutas. Las IPs anteriores son observaciones transitorias, no una receta
fija para sesiones futuras.

**Interpretación:** el sistema ha perdido acceso efectivo al dispositivo que
almacena Docker, lo que impide el funcionamiento normal de CVAT. `dead` y 0 B no
prueban que el disco esté vacío ni que los datos se hayan perdido definitivamente.
No se ha determinado si la causa es controlador, enlace PCIe, alimentación,
firmware, medio físico u otra. No atribuir el problema sólo al modelo de SSD.

Fuentes primarias para interpretar el estado, separadas de las lecturas reales:
[estados del controlador NVMe en Linux](https://raw.githubusercontent.com/torvalds/linux/v6.8/drivers/nvme/host/nvme.h),
[retirada de namespaces y capacidad expuesta](https://raw.githubusercontent.com/torvalds/linux/v6.8/drivers/nvme/host/core.c).
No se ha supuesto que esa versión de kernel sea la instalada en el servidor.

### HISTÓRICO — Registro de kernel aportado por el operador

El 20-10 el operador ejecuta la consulta con sudo en su terminal y aporta una
salida dominada por avisos EXT4 de `nvme0n1p1`: `htree_dirblock_to_tree` y
`dx_probe`, con **`error -5 reading directory block`** en varios procesos,
incluidos uvicorn y grafana. Se conserva un extracto representativo, marcado como
incompleto, en `kernel-user-excerpt.txt` de la evidencia privada. Marcas visibles
06:18:10–06:19:13 del servidor, sin zona confirmada; no son el instante de inicio.

Esto confirma errores de entrada/salida al leer directorios del mismo volumen.
No prueba que una corrupción lógica de EXT4 sea la causa ni que haya daño NAND.
El filtro inicial incluía `EXT4-fs`, por lo que el aluvión de avisos desplaza
los mensajes del controlador NVMe fuera del límite de 100 coincidencias.
En la salida aportada no aparece el evento inicial del controlador.

### HISTÓRICO — Fallo del controlador confirmado en el filtro específico

El operador aporta después los mensajes de `nvme0` del 20-10 a las **06:10:38
(hora del servidor, zona sin confirmar)**. El controlador corresponde al PCI
`0000:2c:00.0`, enumerado el 30-09 en ese arranque. La secuencia registrada es:

1. `controller is down; will reset: CSTS=0xffffffff, PCI_STATUS=0xffff`.
2. Aviso sobre posible ahorro energético y sugerencia de parámetros de arranque.
3. `Disabling device after reset failure: -19`.

**Conclusión comprobable:** el controlador dejó de responder, el intento de
reinicio del driver falló y Linux deshabilitó el dispositivo. `-19` corresponde
a ENODEV. Explica el estado dead/0B y los errores posteriores de directorios.
El origen de esa pérdida de comunicación y el estado de los datos siguen sin
confirmar. No se necesitan más registros para preparar la fase de mantenimiento.

**Ahorro energético: hipótesis, no diagnóstico.** El código Linux imprime la
sugerencia al leer CSTS con todos los bits a uno; no ha demostrado que APST/ASPM,
firmware o un componente físico concreto causaran este fallo. [Fuente primaria:
función nvme_warn_reset y tratamiento del reset fallido](https://raw.githubusercontent.com/torvalds/linux/v6.8/drivers/nvme/host/pci.c).
El texto exacto aportado añade `pcie_port_pm=off`; se conserva tal cual en
`kernel-controller-user.txt`. La referencia Linux enlazada sirve para interpretar
el aviso, no para atribuir una versión al kernel instalado.

### HISTÓRICO — Resultado comprobado del reinicio por software

**SSH vuelve y se comprueba el arranque:** bootID
`94f200a2-b021-4f20-8bba-b50c2e8b3f55`, uptime34,11s en la primera consulta
completa. Antes se observaron conexión rechazada/timeouts y después pam_nologin
«System is booting up»; no se enviaron más reinicios. El primer periodo acotado
no obtuvo acceso; el segundo sí. No convertir aquellos timeouts en una conclusión
de pérdida permanente de acceso.

**Protecciones verificadas por lectura tras arrancar:** cinco máscaras apuntan
a `/dev/null` y las cinco unidades están inactive/masked; fstab contiene
`defaults,noauto,ro,noload 0 0` para el UUID de Docker; `/var/lib/docker` no está
montado. La preparación está aplicada y comprobada, no sólo anunciada por el
operador. Docker/CVAT y las otras cargas de Docker permanecen detenidas.

**El SSD de Docker no se ha recuperado en esta prueba:** no existe
`/dev/disk/by-uuid/b819b286-2006-4474-b2d5-13982b0f1536`. A los71,79s del arranque
se vuelve a comprobar esa ausencia; a159,90s sigue sin aparecer. Sólo aparece un NVMe2TB live con el sistema
operativo, `/boot` y EFI: serial `S7DRNJ0X107095A`. El NVMe live actual no demuestra
que haya vuelto el dispositivo de datos. El otro dispositivo sda sigue siendo el
almacenamiento de `/srv/tenants/SPM`; no se utiliza ni modifica para el rescate.

**No reutilizar nombres anteriores:** el `nvme0n1p1` actual es EFI (`/boot/efi`,
UUID4B3D-6252), no la partición ext4 de Docker. El PCI `0000:2c:00.0` aparece ahora
vinculado al controlador del disco del SO; tampoco basta ese dato para identificar
el volumen buscado. La comprobación decisiva aquí es la ausencia del UUID exacto
de Docker y del segundo NVMe en lsblk. No se debe montar ni reparar el dispositivo
sólo por llamarse nvme0n1p1.

No se montó ningún dispositivo, no se ejecutó fsck, no se restauró configuración
ni se arrancó Docker. Falta acceso al SSD para copiar su base de datos. En la fase posterior a esa
consulta, el operador confirmó que sólo tenía SSH, sin acceso físico ni BMC/IPMI
disponible: el ciclo completo quedó entonces pendiente de presencia. Después
confirma la llegada física, registrada arriba; el ciclo aún no se ha ejecutado.
Las protecciones se mantienen y no se solicitan más reinicios o resets. La pérdida definitiva de datos continúa sin demostrar.

### HISTÓRICO — Datos conservados y límites de la copia

- Diez PNG de referencia del PC (seis iniciales y cuatro del encuadre posterior),
  junto a fuentes/metadatos, verificados contra sus SHA256SUMS. No se han cambiado.
- Snapshot local de CVAT de **ayer 19-10-2026**, tarea5/job5: una anotación manual,
  shape10, frame1, `itr_candidate`, 26 vértices. Se conserva otra copia privada en
  la evidencia de este incidente, junto al recibo de su revisión.
- Ese snapshot **no es una copia completa ni actual de la base CVAT**. No se puede
  afirmar que incluya trabajo que el usuario hiciera después. La consulta de hoy
  no logró leer las anotaciones actuales.
- Fuentes, recetas y documentación están versionadas en `vision-reconoce`.
  Modelos/DB/volúmenes del SSD no han podido respaldarse de nuevo desde este fallo.

### HISTÓRICO — Mantenimiento autorizado y aplicado por el administrador

**Actualización:** el operador ejecuta la orden de preparación y reinicio. El
helper confirma `CONFIG_PREPARED_NO_SHUTDOWN=1` y conserva el respaldo real
`/root/app2-storage-maintenance/aisrv-7epmpnej`. El servidor anuncia el reinicio a
las **06:32:27 UTC / 08:32:27 Europe/Madrid** del20-10-2026. El cliente pierde SSH
con Broken pipe, compatible con el cierre de la sesión, sin demostrar por sí solo
que el arranque haya terminado. Se comprobó disponibilidad de forma
acotada; no se enviaron más reinicios o resets. Primero se recibió Connection
refused; después volvió SSH. Resultado arriba: arranque operativo y protecciones
activas, SSD de Docker no detectado.

La preparación está **APLICADA Y VERIFICADA por lectura tras el arranque**:
cinco máscaras, fstab protegido y volumen sin montar. La receta no arrancó Docker ni montó/reparó el SSD. Las descripciones
siguientes conservan la evolución previa y las opciones preparadas.

El operador había confirmado acceso físico/admin y autorizó detener todo el
servidor; después aclara que **no tiene acceso físico por ahora** y que **no ha
ejecutado** la orden previa. Consulta SSH fresca confirma servidor accesible,
cinco máscaras ausentes y fstab original `defaults 0 2`; nvme0 sigue dead y nvme1
live. En aquella consulta previa aún no se había aplicado la preparación ni
enviado apagado/reinicio; el administrador lo hizo después, como consta arriba.

**Plan histórico que se aplicó:** una sola prueba de preparación verificada seguida de
**reinicio ordenado por software**, sin cortar corriente. La parada de todos
los servicios sigue autorizada; no hace falta repetir esa confirmación.
La orden anterior con `poweroff` queda retirada mientras no haya una forma de
volver a encender el servidor. Un reinicio puede recuperar acceso al enumerar de
nuevo el controlador, pero no equivale a un ciclo completo de alimentación ni
garantiza recuperar el SSD. Si el firmware/arranque/SSH no vuelve, será necesario
esperar acceso presencial o disponer de consola remota/BMC. No hay garantía de
acceso remoto continuo durante esta prueba.

Lectura previa de mantenimiento: kernel `6.8.0-142-generic`; `docker.service`,
`docker.socket` y `containerd.service` están active/running y enabled. `/etc/fstab`
monta `/var/lib/docker` por `UUID=b819b286-2006-4474-b2d5-13982b0f1536`, ext4,
opciones defaults. Un arranque normal volvería a intentar montar el SSD y arrancar
Docker: la parada debe incluir una estrategia de arranque de mantenimiento.
Estado original guardado en `maintenance-before-units.json`, sin cambiar unidades
o fstab. No confiar sólo en que nvme0 conserve ese nombre tras el encendido.

Secuencia prevista antes de la actuación, conservada como historia (pasos1–4
completados; el SSD no reapareció y se aplica la rama presencial del paso5):

1. Conservar fuera del SSD las copias y evidencia accesibles. La base CVAT actual
   continúa sin backup completo; no asumir que sólo hay datos de app2 en Docker.
2. Confirmar que se pueden interrumpir **todos los servicios del servidor**,
   incluidos Ollama y otras cargas, y preparar el arranque de mantenimiento para
   que Docker no reanude escrituras sobre el SSD antes de comprobarlo.
3. Con el administrador conectado, ejecutar la preparación y sólo tras éxito
   realizar un reinicio ordenado por software. No se envía poweroff, no se
   requiere retirar corriente y no se repite el reinicio automáticamente.
4. Comprobar si el dispositivo reaparece con su capacidad y estado normales,
   identificándolo por serial/UUID/PCI; los nombres nvme0/nvme1 pueden cambiar.
5. Si reaparece, priorizar copia/clon y respaldo de datos/DB en otro soporte sano
   antes de reanudar trabajos o reparar. Revisar sobre copia/offline si procede.
   Si no reaparece, escalar a diagnóstico físico/recuperación con el administrador.
6. Volver a CVAT sólo tras comprobar almacenamiento y datos; verificar tarea5
   y conservar posibles anotaciones posteriores al snapshot antes de importar.

**Autorización recibida:** el operador confirma «Sí, podemos hacer la parada
ahora», incluyendo Ollama y cualquier otra carga del servidor. La autorización
no es una afirmación de que ya se haya apagado o restaurado el almacenamiento.

No se han aplicado los parámetros de energía sugeridos, cambios de GRUB/firmware,
resets adicionales, recreación de contenedores ni limpieza de volúmenes. Esas
modificaciones requieren una decisión y un registro separados si se justifican.
Una reparación ext4 sobre el volumen montado no forma parte de este diagnóstico;
[el manual de e2fsck desaconseja comprobar sistemas montados](https://raw.githubusercontent.com/tytso/e2fsprogs/master/e2fsck/e2fsck.8.in).

### HISTÓRICO — Receta preparada para el administrador

Fuente versionada: [storage_maintenance.py](../../scripts/app2/server/storage_maintenance.py).
Destino copiado, en el disco sano: `/home/luisacuna/app2/maintenance/storage_maintenance.py`,
permisos0600. SHA256 común local/remoto:
`f0b7c15750d088996f9e0c0a927dadee63ca485f2b5c7320731f3b058679dabf`.
**Estado:** COPIADO y `--check` VERIFICADO; `--prepare` ejecutado con éxito según
salida del operador, backup real `/root/app2-storage-maintenance/aisrv-7epmpnej`.
Reinicio por software aceptado a06:32:27UTC; arranque y protecciones comprobados.
Recuperación pendiente: el UUID del SSD de Docker no está presente. No se ha introducido una contraseña
de sudo desde el agente.

La comprobación previa a --prepare confirmó hostnameaisrv, entrada fstab
esperada y ausencia de archivos/máscaras locales para las cinco unidades. Ocho tests offline pasan:
entrada UUID/tipo/destino exactos, preservación del resto de fstab, opciones de
sólo lectura/noauto/noload, unicidad de montaje y guardas de restauración.
Los tests por sí solos no prueban recuperación del SSD; la aplicación real de
fstab/máscaras se verificó después mediante las lecturas posteriores al reinicio.

**Orden histórica ya ejecutada por el operador; no repetirla en el estado actual:**

```bash
sudo python3 /home/luisacuna/app2/maintenance/storage_maintenance.py --prepare && sudo systemctl reboot
```

El helper, ejecutado como root, primero conserva `/etc/fstab`, sus bytes,
propietario/permisos/hashes y estados de unidades en una carpeta exclusiva
`/root/app2-storage-maintenance/aisrv-...`, que imprime como `BACKUP=...`.
Rechaza un hostname/UUID/tipo/destino distintos, múltiples entradas, backup en el
volumen afectado o un archivo/máscara local preexistente que pudiera sobrescribir.
Modifica atómicamente **sólo** la entrada del SSD a `noauto,ro,noload`, fsckpass0;
crea máscaras persistentes de Docker/socket/containerd y mount/automount.
No usa `--now`, no desmonta el volumen actual ni envía órdenes de reparación.
Verifica el resultado antes de `CONFIG_PREPARED_NO_SHUTDOWN=1`. La segunda orden,
fuera del helper, solicita el reinicio ordenado; `&&` impide ejecutarla si la
preparación falla. Un error conserva recibo/backup y requiere revisión, sin
repetir a ciegas ni cortar alimentación.

La conexión SSH se cortará durante el reinicio. Tras dar tiempo al arranque,
comprobar disponibilidad de forma acotada. Una demora o timeout no autoriza
`--force`, otro reinicio, reset NVMe o corte de alimentación. Si no vuelve,
comunicar el resultado y usar acceso físico/consola remota cuando esté disponible.

El apagado completo y posterior retirada de alimentación durante unos30segundos
queda como una alternativa de mantenimiento **futura**, sólo con acceso físico
y coordinación del administrador. No es el paso actual.

El arranque ya comprobado conserva SSH en el sistema operativo sano, con
Docker/containerd y mount/automount del SSD bloqueados. Mantener esa protección
antes de cualquier futuro montaje, reparación o reanudación de CVAT. Identificar
el dispositivo por UUID/serie y revisar capacidad/estado, no por su nombre antiguo.

### Conservación adicional antes de la parada

Se ha copiado al PC, desde el volumen sano del SO, `setup`, `workflow`, recibos,
secretos del proyecto y locks CVAT: archivo privado
`healthy-host-app2-before-maintenance.tar.gz` bajo la evidencia actual,
11.903.996bytes, permisos0600 y carpeta0700, checksum en
`healthy-host-backup.json`. Contiene credenciales privadas: no añadirlo a Git,
publicarlo ni mostrar su contenido en el chat. No incluye los volúmenes de datos
del SSD fallido y **no sustituye un backup de la base CVAT**.

### Reversión de configuración, sólo después de valorar el rescate

La ruta BACKUP real de esta ejecución es
`/root/app2-storage-maintenance/aisrv-7epmpnej`. Conservarla. La restauración de
configuración sigue pendiente de valorar el rescate; receta en el servidor:

```bash
# No ejecutar antes de valorar/completar el rescate de datos.
sudo python3 /home/luisacuna/app2/maintenance/storage_maintenance.py --restore-config /root/app2-storage-maintenance/aisrv-7epmpnej
```

Comprueba los hashes del original y del fstab preparado, se niega a sobrescribir
cambios posteriores y retira sólo las máscaras creadas y aún intactas. Permite
revertir una preparación parcial registrada. No monta ni arranca Docker; su
reactivación requiere revisar primero disco, UUID/montaje y copias recuperadas.
No borrar las máscaras a mano ni ejecutar `--restore-config` como primer paso
tras encender: se perdería la protección preparada para el rescate.

### HISTÓRICO — Plan anterior tras reconexión de AC — histórico, superado por el arranque actual

Retirada de AC un minuto y reconexión reportadas por el operador. Comprobar si
arranca; si no, pulsación breve única de encendido, sin repetir si ya hay arranque.
Esperar nueva disponibilidad y verificar bootID, UUID de datos, dispositivos y
protecciones antes de montar, restaurar configuración o arrancar Docker. No dar
por confirmado el apagado ordenado previo ni la recuperación del SSD. Los pasos
siguientes conservan el plan anterior y no acreditan su ejecución completa.

1. Mantener AC conectado mientras no se confirme el final del apagado; no usar
   force, Reset ni corte forzado. Espera acotada y, si persiste, observar consola
   con un monitor. Las cinco máscaras/fstab siguen como última configuración
   verificada antes de la orden; no enviar
   reinicios extra, resets NVMe, fsck, --restore-config ni START de Docker.
2. Presencia física confirmada: coordinar el apagado ordenado por el operador y
   retirar AC sólo cuando el sistema esté apagado. La orden de apagado ya se
   solicitó; su finalización sigue sin confirmar y el ciclo frío NO se completó. Tras encender, comprobar el dispositivo por UUID/serie, sin
   reutilizar el nombre nvme0n1p1 anterior.
3. Si reaparece, conservar primero datos/DB en otro soporte sano y comprobar la
   recuperación sobre copia antes de reparar o reanudar servicios. Si no reaparece,
   el administrador deberá continuar el diagnóstico físico/recuperación.
4. La continuidad de anotación en el PC queda aplazada: el operador prioriza
   recuperar primero el servidor. No se ha instalado otra instancia ni se ha
   prometido recuperar allí el estado actual. Si se retoma esa alternativa,
   conservar cualquier trabajo local separado hasta reconciliarlo con la base
   original, evitando sobrescribir anotaciones aún no rescatadas.

### HISTÓRICO — Receta presencial anterior — no repetir ahora; dispositivo ya reaparecido

El operador confirma ahora que **ya hay acceso físico al servidor**. La consulta
de llegada conserva las protecciones y UUID ausente; el apagado/ciclo frío aún no
se ha completado. El operador ya solicitó el apagado; persisten ventiladores
sin monitor, como recoge la actualización actual. Se prioriza recuperar este almacenamiento; la alternativa de
anotación en el PC queda aplazada. Apagado solicitado, finalización sin confirmar.

Nueva consulta de lectura, mismo bootID y uptime524,51s: UUID de Docker ausente,
cinco unidades inactive/masked y volumen sin montar. DMI identifica placa ASUS
Pro WS WRX80E-SAGE SE WIFI II, BIOS1602. Evidencia exacta:
`physical-preparation-readonly.py/json` en la carpeta privada del incidente.

**Con la presencia ya confirmada, secuencia coordinada todavía pendiente de ejecución:**

1. Comprobar que las protecciones anteriores siguen aplicadas. No repetir
   `--prepare`, ya ejecutado. El administrador solicita un apagado ordenado desde
   su terminal; la contraseña, si se pide, se introduce allí:

   ```bash
   ssh -t -p 2649 luisacuna@192.168.1.43 'sudo systemctl poweroff'
   ```

2. Esperar a que termine el apagado del SO y se detengan los ventiladores.
   Después desconectar de la máquina todos sus cables de alimentación eléctrica,
   incluso si vienen de un SAI/UPS. Esperar a que desaparezcan los indicadores de
   alimentación residual; unos60segundos son una espera operativa prudencial,
   no una especificación de ASUS ni una garantía de recuperación. Reconectar y
   encender normalmente. No usar Reset ni manipular los M.2 en este primer intento.
   El [manual oficial de la placa, apartados1.1 y1.2/power button](https://dlcdnets.asus.com/pub/ASUS/mb/Socket%20sTRX4/PRO_WS_WRX80E-SAGE_SE_WIFI_II/E21365_Pro_WS_WRX80E-SAGE_SE_WIFI_II_UM_WEB.pdf)
   distingue apagado lógico de alimentación conectada y exige desconectarla antes
   de manipular componentes.
3. Al volver SSH, verificar un bootID nuevo, las cinco máscaras, fstab y ausencia
   de montaje. Descubrir de nuevo dispositivos por UUID/serie/modelo/capacidad:

   ```bash
   ssh -p 2649 luisacuna@192.168.1.43 'cat /proc/sys/kernel/random/boot_id; lsblk -b -o NAME,MODEL,SIZE,STATE,UUID,MOUNTPOINTS,SERIAL'
   ssh -p 2649 luisacuna@192.168.1.43 'ls -l /dev/disk/by-uuid/b819b286-2006-4474-b2d5-13982b0f1536'
   ssh -p 2649 luisacuna@192.168.1.43 'systemctl show docker.service docker.socket containerd.service var-lib-docker.mount var-lib-docker.automount -p Id -p ActiveState -p UnitFileState'
   ```

   Si aparece un segundo NVMe pero no su UUID, no formatear ni concluir que esté
   vacío: primero revisar identidad y estado. **nvme0n1p1 es ahora EFI**, por lo
   que ningún comando de recuperación se debe construir con ese nombre histórico.
4. Si reaparece el SSD, prioridad a copia/imagen en un soporte sano antes de
   montar, reparar o arrancar Docker. Confirmar destino y capacidad libre exactos:
   una imagen completa necesita al menos los bytes reales del disco más margen;
   un soporte externo de4TB es una opción práctica para el origen de2TB. Ni el
   espacio disponible en raíz ni el almacenamiento ajeno `/srv/tenants/SPM` son
   destinos de rescate preparados. Herramienta, mapfile y orden de copia quedan
   pendientes de verificar; no se ha instalado ni iniciado un clonador.
5. Si no reaparece tras este ciclo frío, detener nuevos intentos de encendido y
   pasar con el administrador al diagnóstico físico del SSD/ranura o recuperación
   especializada. No actualizar firmware ni reparar EXT4 para intentar que un
   dispositivo que no se detecta vuelva a aparecer.

### HISTÓRICO — Punto de reanudación vigente tras reaparecer el SSD

Backup de todoslos20volúmenes actualmente EN CURSO. Esperar resultado/recibo,
verificar archivos/hashes y desmontaje; no instalar herramientasIPMI ni modificar
APP2fuente mientras tanto. Los pasos de selección y preparación que siguen ya
precedieron el inicio; integridadDB/restore y copia externa siguen pendientes.

1. Mantener las cinco máscaras/fstab y el SSD sin montar entre operaciones; el
   inventario temporalRO ya terminó con cleanup verificado. No repetir ciclos de
   energía, resets ni --restore-config para probar.
2. SMART/error-log/kernel ya recibidos como salida sudo del operador. Conservar
   esa procedencia y no confundir los contadores favorables actuales con
   integridad del filesystem/base de datos o una causa demostrada.
3. Backup de todoslos20volúmenes ya terminado/comparePASS ysource desmontada.
   Los13TAR+recibo enPC ya tienen hashes verificados; probar restore
   aislado, resultado todavía pendiente. El operador no tiene otro almacenamiento para imagen completa de al menos
   2.000.398.934.016bytes más margen; no hay destino para ella. Valorar copia
   de todoslos20volúmenes al SO sano: el inventario demuestra que la estimación
   cabe reservando16GiB. Helperv2--all-volumes ya desplegado y --check verificado;
   resultado del backup entregado al operador aún pendiente. No usar el volumen ajenoSPM. La copia sigue pendiente; el
   inventario temporalRO ya se ejecutó y no equivale a un clon completo.
4. Preservar primero la copia; revisar y recuperar sobre copia antes de reparar,
   actualizar firmware, restaurar configuración o arrancar Docker. Aún no hay
   integridad de datos ni DB comprobada. La posibilidad de copia selectiva debe
   valorarse expresamente si no hay destino para imagen completa.
5. Sólo tras el rescate y validación, revisar tareas/anotaciones de CVAT y cambios
   posteriores al snapshot19-10 antes de cualquier reimportación o entrenamiento.

### HISTÓRICO — Evidencia y reanudación de app2

Carpeta privada: `../Humanoide-vla-evidence/20261020T061422Z_APP2_RESUME_READONLY/`.
Incluye consultas exactas, errores, respuestas HTTP, inventario de discos/montaje,
snapshot previo conservado, resumen, before/after y checksums. Los extractos de diagnóstico no contienen contraseñas; el backup privado del
SO descrito arriba sí contiene credenciales y no debe publicarse. No hay una
reparación del SSD ejecutada.

Tras recuperar el acceso: verificar tarea5/job5 y sus contornos actuales antes de
editar o reimportar; conservar cualquier trabajo posterior al snapshot. Completar
el frame1 y su revisión, y reunir escenas independientes antes del entrenamiento.


</details>
