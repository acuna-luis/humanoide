# Comprobación posterior del SSD de datos — sólo lectura

**Cierre verificado 20-10-2026: helper corregido a482e7d0…b5bd0f instalado y
probado en la recuperación; después se restauraron montaje, Docker y CVAT.**
El RO de las11:17 UTC completó cinco pasadas sin marcadores; la fase separada
posterior recuperó20 contenedores y los datos/acceso del piloto. No repetir fsck,
desmontaje o montaje para reproducir una comprobación histórica.
[Resultado completo y secuencia](OFFLINE_RECOVERY.md#montaje-servicios-y-piloto-recuperados--comprobación-final),
[incidente vigente](../../../docs/incidents/2026-10-20_APP2_SSD_DOCKER_NO_RESPONDE.md).
La fiabilidad prolongada del SSD sigue pendiente de observación.

Receta específica de `aisrv`, 20-10-2026. Requiere `storage_postcheck.py` junto a
`storage_rescue.py` SHA256
`ec8e727b23d2288ac46be24d4c0ab8867f46100a38a9578ec83a781cebffcee8`.
No instala herramientas. Necesita `nvme`, `blkid`, `journalctl`, `systemctl`,
`lsblk` y, para la opción adicional, `e2fsck` ya disponibles.

El SSD de datos se identifica por UUID y serie `S7DRNJ0X107187F`, con firmware
`8B2QJXD7`; el SSD del SO debe seguir siendo `S7DRNJ0X107095A`, `4B2QJXD7`.
Se exigen las cinco máscaras/inactividad, fstab de mantenimiento y datos sin
montar. No se utiliza un nombre NVMe histórico como identidad.

Los comandos siguientes documentan el postcheck offline ya realizado, con
datos entonces desmontados. **No son la forma de retomar CVAT ahora**, ya
montado y activo; no cambiar su estado sólo para satisfacer las guardas antiguas.
Desde el servidor, durante aquella fase y con las versiones revisadas:

```bash
python3 /home/luisacuna/app2/maintenance/storage_postcheck.py --help

umask 077
postcheck_report=$(mktemp /home/luisacuna/app2/maintenance/postfirmware-check.XXXXXXXX.json)
if sudo python3 /home/luisacuna/app2/maintenance/storage_postcheck.py \
  --filesystem-check > "$postcheck_report"; then
  postcheck_rc=0
else
  postcheck_rc=$?
fi
printf 'INFORME=%s\nCODIGO=%s\n' "$postcheck_report" "$postcheck_rc"
```

Omitir `--filesystem-check` obtiene sólo identidades, SMART, error-log y kernel.
Con la opción se ejecuta **únicamente `e2fsck -f -n`**, con un máximo de 300 s,
antes y después de comprobar que el origen sigue desmontado. `-n` abre el sistema
de archivos en lectura y responde no a reparaciones. No monta ni reproduce el
journal, repara, cambia máscaras/fstab, arranca Docker o actualiza firmware.
La opción se **omite antes de leer el sistema de archivos** si una consulta
SMART/error-log/kernel falla, se trunca o no devuelve JSON NVMe interpretable;
también si `critical_warning` o `media_errors` del SSD de datos faltan, no son
enteros interpretables o no valen cero. Se conserva el informe completo, motivo
de omisión y código 2. Pasar ese gate no demuestra salud del dispositivo.

El código del helper es 0 si completó consultas sin los marcadores de revisión,
1 si e2fsck devuelve 4 o su salida indica journal omitido/recuperación pendiente,
contadores incorrectos o problemas sin corregir **aunque e2fsck devuelva 0**;
y 2 ante bloqueo, error o timeout. El JSON conserva
argv, rc exacto, salida y duración; un rc diferente de cero no autoriza reparación.
Un informe terminado o SMART sin critical warning tampoco demuestra ausencia de
un fallo intermitente. Revisar antes de decidir si procede reparar o restaurar.
Guardar el informe privado y su SHA fuera del SSD afectado. Ninguna ejecución
remota queda autorizada por esta receta por sí sola.

Referencia de `-n` y códigos de e2fsck:
[manual de e2fsprogs](https://www.man7.org/linux/man-pages/man8/e2fsck.8.html).

## Despliegue inicial histórico — 20-10-2026

`APP2-POSTCHECK-20261020`: a las 10:22:24 UTC / 12:22:24 Europe/Madrid quedó
instalado `/home/luisacuna/app2/maintenance/storage_postcheck.py`, propietario
`luisacuna` (uid1001), modo0600, 10.171 bytes, SHA256
`9e030a05bcdc3fff750ea25f6d5990d3931720f3545b4583c34da8bf1f2e8a33`.
Origen reproducible: este directorio del repositorio, helper y dependencia
fijada arriba. Validación local: 13 tests, incluido ext4 temporal cuyo SHA no
cambia tras e2fsck -f -n; `--help` remoto sin root termina0. En ese momento no se
había ejecutado la recolección con sudo ni e2fsck real. Resultado posterior debajo.

Antes de publicar se confirmó hostname/usuario, destino en SSD del SO, padres
sin enlaces, dependencia exacta y ambos destinos inexistentes. Instalación con
temporal exclusivo0600, `fsync`, enlace duro atómico sin clobber al nombre final
y retirada del temporal; nunca se sustituyó un destino diferente. Se verificó
SHA/uid/modo posterior. Esta misma receta se conserva junto al helper como
`POSTFIRMWARE_CHECK.md`. Para reproducir, verificar las versiones, transferir a
temporales nuevos y aplicar ese mismo procedimiento sin sobrescritura; si un
destino ya existe y su hash difiere, detenerse y preparar un respaldo/revisión.

Guardas anteriores al despliegue: boot `e719f517-0709-417a-b521-7bc8c0212bf6`,
EFI presente, datos187F live8B/SO095A live4B, cinco unidades masked/inactive y
`CHECK_OK_NO_MOUNT`. La presencia de EFI no prueba por sí sola el valor de CSM;
su reversión corresponde a la comprobación separada de BIOS de esta intervención.

Evidencia privada: `../Humanoide-vla-evidence/20261020T061422Z_APP2_RESUME_READONLY/`,
archivos `post-csm-rollback-ssh-readonly.json`, `postcheck-deployment-before.json`,
`postcheck-deployment-helper.json` y `postcheck-deployment-final.json`.
Reversión: retirar sólo estos dos archivos nuevos si coinciden sus hashes con
el recibo y ya no se necesitan; no retirar `storage_rescue.py`, máscaras o fstab,
ni deshacer firmware o activar servicios como parte de esa retirada.

### Corrección posterior de interpretación — desplegada y comprobada

La primera consulta real del operador, informe
`maintenance/postfirmware-check-20261020T1023Z.json` (10:30:42 UTC), devolvió
e2fsck rc0 y el helper instalado informó código0. Sin embargo, la salida decía
`skipping journal recovery` y mostraba diferencias en contadores de bloques e
inodos con respuestas `Fix? no`. **Ese rc0 no demuestra un ext4 limpio.** El
journal seguía sin aplicarse y exigía revisar el estado antes de decidir la
recuperación. Esa lectura por sí sola no autorizaba reparar o montar.

Se corrige la fuente versionada para conservar rc/stdout/stderr exactos y marcar
esos resultados `FILESYSTEM_REVIEW_REQUIRED` con código1. La prueba de regresión
incluye literalmente la salida real. La etiqueta antigua
`NO_ERRORS_REPORTED_READ_ONLY` deja de utilizarse. Un rc0 sin esos marcadores se
describe sólo como consulta terminada, nunca como prueba de salud o limpieza.

**Instalado histórico:** helper `9e030a05…f2e8a33`. La corrección se desplegó a
las10:42:09 UTC con respaldo exacto previo en
`/home/luisacuna/app2/maintenance/postcheck-review-fix-20261020T104209Z-p5_ao905`.
**Instalado y probado real:**
`a482e7d08eee61777add951b6a1c7de0d9e91600b4082e787d2a282e87b5bd0f`,
15 pruebas locales correctas y --help remoto correcto. La consulta posterior a
la recuperación real, informe received-offline-recovery-20261020T1054Z.json,
conserva rc0, cinco pasadas y `COMPLETED_WITHOUT_REVIEW_MARKERS_READ_ONLY`.
No se repite ninguna consulta o reparación al documentarlo.
Respaldo privado previo: `before-postcheck-fsck-interpretation-fix/` dentro de la
evidencia de esta intervención; conserva helper, tests, receta y manifiesto SHA.
## Cierre posterior: servicios y datos verificados

La secuencia separada restoreconfig → mount → checker de sólo lectura →
containerd/Docker terminó correctamente. Se verificaron el montaje real del SSD
de datos y los20 volúmenes antes de arrancar Docker; después coinciden los20 IDs,
imágenes, servicios, políticas y layouts de mounts con el baseline archivado.
Los20 contenedores (18 CVAT+2 Ollama) están running, sin reinicios observados.

API CVAT conserva4 tareas/4 trabajos/9 formas; task5/job5/shape10/frame1 y ambos
PNG originales con SHA exactos. Túnel `localhost:18080` restaurado/HTTP200.
Estos resultados están documentados con sus evidencias en
[OFFLINE_RECOVERY.md](OFFLINE_RECOVERY.md#montaje-servicios-y-piloto-recuperados--comprobación-final)
y el incidente vigente. No se repitió ninguna reparación al documentarlos.

Conservar informes y backups. El postcheck favorable y la actualización de
firmware no garantizan que un fallo intermitente no reaparezca; la observación
a largo plazo sigue pendiente. No ejecutar otra pasada ni desmontar/remontar
el volumen como rutina para volver a trabajar en el piloto.
