# Recuperación offline de ext4 — aisrv, incidente del 20-10-2026

**CIERRE VERIFICADO 20-10-2026: recuperación offline completada, datos montados
y Docker/CVAT restaurados con los datos del piloto conservados. No repetir fsck,
la recuperación o el montaje.** La fiabilidad del SSD a largo plazo sigue
pendiente de observación; este resultado no demuestra ausencia de recurrencias.
[Incidente vigente y estado completo](../../../docs/incidents/2026-10-20_APP2_SSD_DOCKER_NO_RESPONDE.md).
Este helper queda como receta histórica de esta incidencia, no como acción
periódica. No interviene en el robot.

El informe fijado de 10:30:42 UTC muestra journal sin recuperar y dos contadores
globales incorrectos. e2fsck -f -n devolvió0; eso no demuestra limpieza. La acción
realizada fue recuperación **offline estándar de journal y metadatos con preen**:

```text
e2fsck -p -E nodiscard,fixes_only,no_optimize_extents -z <undo_en_SSD_SO> <partición_verificada>
```

`-p` permite las correcciones que e2fsprogs considera seguras; si se necesita
intervención puede terminar con bit4 después de haber corregido otras cosas.
No es todo o nada. No usa `-y`, `-f`, `-c`, montaje, servicios o reintentos.
Se descartó prometer «sólo journal»: en1.47.0 la combinación journal_only/preen
puede entrar en pasadas posteriores si ya hubo correcciones previas. Sin preen
y sin TTY, e2fsck aborta antes de abrir; no se fuerza interactividad ni se envían
respuestas automáticas a preguntas.

## Condiciones históricas exigidas antes de reparar el SSD de datos

- `aisrv`, datos serie187F / UUID `b819b286-2006-4474-b2d5-13982b0f1536`,
  firmware8B2QJXD7/live; SO serie095A / firmware4B2QJXD7/live. Los nombres
  `nvme0/nvme1` se descubren y no se usan como identidad histórica.
- Cinco unidades Docker/containerd/mount masked/inactive; fstab de mantenimiento
  y datos desmontados, mediante `storage_rescue.py` fijado por SHAec8e727b…cee8.
- `storage_postcheck.py` fijado por SHAa482e7d0…b5bd0f: SMART y error-log legibles
  de ambos SSD; critical_warning y media_errors cero también en el SO que
  recibirá undo. Contadores de error/apagados/ciclos y error-log sin cambios;
  sin nuevos reset, timeout, I/O, EXT4/AER problemáticos frente al informe fijado.
- Informe previo byteexacto SHA324c3b3b…bf5f5, mismo boot/source/guardas. RO fresco
  completo idéntico: sólo journal omitido y aquellos dos contadores incorrectos.
  Cualquier cambio bloquea y requiere nueva revisión; no se ajustan umbrales.
- Journal **interno** probado en dumpe2fs-h: inode>0, sin device/UUID externos.
- Recibos SHA fijados de los22 TAR de todos los volúmenes/definiciones y del TAR
  de capas escribibles. Identidad/compare PASS/tamaños/ubicación en SO comprobados;
  no se vuelven a leer/hash los47GB. Estos respaldos lógicos no son imagen2TB.
- Al menos32GiB libres inmediatamente antes de reparar; además16GiB+margen undo
  estimado. `4×tamaño journal+256MiB` es **estimación, no cota de reparaciones
  generales ni garantía de conservar16GiB durante la ejecución**. No se impone
  un hardlimit que aborte escrituras en curso.

## Receta ejecutada — conservar como historial, no repetir

Los comandos siguientes documentan la intervención ya terminada. El estado
actual es montado/con servicios: no desmontar, remascar unidades o repetir una
pasada para volver a cumplir las guardas antiguas. Para trabajar, continuar el
[piloto de piezas reales](../../../docs/app2/PILOTO_PIEZAS_REALES.md).

Los tres helpers deben estar juntos en `/home/luisacuna/app2/maintenance/`;
las dependencias deben coincidir con sus hashes completos en el código.

```bash
python3 /home/luisacuna/app2/maintenance/storage_offline_recovery.py --help

# Sólo lectura: no crea directorios, snapshots o lock si no existían.
sudo python3 /home/luisacuna/app2/maintenance/storage_offline_recovery.py --check

# Una sola recuperación; sólo tras revisión concreta del coordinador.
umask 077
recovery_report=$(mktemp /home/luisacuna/app2/maintenance/offline-recovery.XXXXXXXX.json)
if sudo python3 /home/luisacuna/app2/maintenance/storage_offline_recovery.py \
  --recover > "$recovery_report"; then
  recovery_rc=0
else
  recovery_rc=$?
fi
printf 'INFORME=%s\nCODIGO=%s\n' "$recovery_report" "$recovery_rc"
```

Antes de e2fsck se crea un directorio único root0700 bajo
`/root/app2-offline-recovery/` en el SO. Conserva el informe/recibos originales,
preflight, header de dumpe2fs, configuración e2fsck, primeros2MiB del dispositivo
identificado, logs y undo. Archivos0600, fsync de archivos/directorios/fases.
La copia2MiB no es respaldo del journal ni rollback completo.

Lock exclusivo en archivo root privado; e2fsck lo hereda. Si el proceso padre
se interrumpe, no se mata al hijo ni se libera su lock: no lanzar otra pasada,
apagar, montar o arrancar Docker. El hijo conserva sesión propia y logs en disco.
No hay timeout, kill, terminate ni reintento automático durante la escritura.

## Resultado y límites

Después de rc0/1 sin señales sospechosas se recoge SMART/guardas y RO completo.
Si e2fsck devuelve otro código o aparecen checksum/corrupt/error/I/O/aborto,
preguntas o recuperación repetida, se marca revisión y sólo se recoge salud;
no se inicia automáticamente otro examen largo del sistema de archivos.
Los logs originales se conservan completos aunque el resumen JSON sea limitado.
El helper de recuperación no arranca servicios, monta datos o reinicia el host.
El montaje y arranque posteriores se realizaron en la fase separada verificada
que se registra al final de esta receta.

Código0 del helper significa que terminó esta recuperación y el postcheck de
lectura; no promete salud futura. Código1 requiere revisión; código2 indica
bloqueo/error/interrupción y puede coexistir con un hijo aún escribiendo:
consultar `phases.jsonl`, PID y logs antes de actuar. No repetir el comando.

`-z` guarda originales antes de escribirlos en el undo para journal interno y
metadatos, pero **no ofrece recuperación garantizada tras corte eléctrico/crash**.
No se restaura undo automáticamente. Ante fallos, conservar directorio y backups
y revisar el estado con personal competente; no aplicar e2undo o reparaciones
manuales desde esta receta. Servicios/CVAT sólo se recuperan en una fase separada.

Pruebas locales: guardas, informe alterado, delta de errores/SMART, no escrituras
en --check, argv, rc4 sin nuevo FS largo y flock heredado; además ext4 temporal
con contador alterado, preen real, undo y RO posterior sin contadores erróneos.

Fuentes primarias: [manual e2fsck](https://www.man7.org/linux/man-pages/man8/e2fsck.8.html),
[unix.c v1.47.0](https://git.kernel.org/pub/scm/fs/ext2/e2fsprogs.git/tree/e2fsck/unix.c?h=v1.47.0),
[journal.c v1.47.0](https://git.kernel.org/pub/scm/fs/ext2/e2fsprogs.git/tree/e2fsck/journal.c?h=v1.47.0),
[undo_io.c v1.47.0](https://git.kernel.org/pub/scm/fs/ext2/e2fsprogs.git/tree/lib/ext2fs/undo_io.c?h=v1.47.0).

## Registro de instalación — APP2-OFFLINE-RECOVERY-20261020

Destino `aisrv:/home/luisacuna/app2/maintenance/storage_offline_recovery.py`,
propietario luisacuna/uid1001, modo0600, 20.560 bytes. SHA256 completo:
`0f016474bdae29cce095dc31c2261661b951cff7c88a050851df7b0f0406ce6b`.
Fuente reproducible: [helper](storage_offline_recovery.py) y
[tests](tests/test_storage_offline_recovery.py) en este mismo directorio.
Dependencias exactas verificadas en el destino: storage_rescue ec8e727b…cee8 y
storage_postcheck a482e7d0…b5bd0f, cuyos hashes completos están fijados en código.

El archivo previo no existía. Se verificaron hostname/uid, padres sin enlaces y
directorio en el SSD del SO; se transfirió a temporal exclusivo0600, fsync,
publicación por enlace atómico sin clobber, retirada del temporal y fsync del
directorio. Después se comprobaron hash/uid/modo y --help sin root terminó0.
No se ejecutó sudo, --check o --recover al instalar; no hubo cambios de montaje,
servicios, firmware, BMC, configuración o contenido del SSD de datos.
Esta receta se publica por primera vez junto al helper con el mismo modo/uid.

Evidencia privada: `../Humanoide-vla-evidence/20261020T061422Z_APP2_RESUME_READONLY/`,
`offline-recovery-deployment-helper.json`, `offline-recovery-deployment-final.json`
y snapshot previo local `offline-recovery-deployment-sources/`. Los recibos
conservan las versiones/hash reales; no dependen del historial del chat.

Reproducir el despliegue requiere esas fuentes/dependencias y publicación nueva
sin sobrescritura; si el destino existe con hash diferente, detenerse y respaldar
antes de una actualización revisada. Reversión de esta instalación: retirar sólo
helper/receta nuevos, comprobando hashes y ausencia de operación activa. No borrar
lock/undo/logs con un hijo activo, no restaurar undo automáticamente ni cambiar
firmware, fstab o máscaras como parte de esa retirada. La recuperación del
filesystem y de servicios se documenta por separado al recibir sus resultados.

## Resultado real — APP2-OFFLINE-RECOVERY-20261020

El operador ejecutó --check seguido de --recover. Preflight de las11:17:25 UTC:
`CHECK_READY_NO_WRITES`; recuperación preparada a las11:17:28 UTC y preen en el
directorio de las11:17:31 UTC, PID5531, rc0, sin stderr ni truncado. Salida:
`dockerdata: recovering journal`, seguida de
`dockerdata: clean, 184553/122101760 files, 24570022/488378368 blocks`.
Estado final del helper: `RECOVERY_AND_READONLY_POSTCHECK_COMPLETED_NO_SERVICES`.

Undo conservado, regular y de4.345.856 bytes:
`/root/app2-offline-recovery/20261020T111731Z-7r0y7atv/recovery.e2undo`.
El directorio root privado conserva también logs, snapshots, recibos y primera
región de2MiB. No se ha aplicado e2undo ni se ha repetido preen.

Postcheck real de las11:17 UTC con helper a482e7d0…b5bd0f: e2fsck -f -n rc0, las cinco pasadas
completadas en2,384s, sin `wrong`, journal omitido u otros marcadores;
`review_reasons=[]`. SMART de ambos SSD conserva critical_warning/media_errors0.
En aquel postcheck, preflight/final_guard PASS: identidad/firmware correctos,
origen todavía desmontado y cinco unidades masked/inactive. Boot
e719f517-0709-417a-b521-7bc8c0212bf6. Esa fase verificó recuperación y lectura
posterior; la validación de contenedores/CVAT se realizó después, debajo.

Informes originales copiados a la evidencia privada:

- `received-offline-preflight-20261020T1054Z.json`, SHA256
  `890ad4d0328415e819146084a77a25d80f1d218cda74338ee44d32c7bd9e5fda`.
- `received-offline-recovery-20261020T1054Z.json`, SHA256
  `35620e71eab15a2ef805a5ed3682a9b36e9ecc79dd96b265c56788629d611ade`.

La copia de esta receta instalada antes de ejecutar tenía SHAaecfd1cc…148390 y
estado histórico pendiente. Los recibos de sincronización documental conservan
backup y hash de cada versión: no usar ese hash anterior como estado vigente.

Auditoría adicional **sólo local** del TAR docker-definitions verificado:
20 definiciones (18 app2-cvat con política `always`, 2 Ollama `unless-stopped`).
El inventario privado `docker-baseline-offline-audit.json`, SHA1aab3d87…9e720b,
conserva IDs/nombres, image IDs/referencias, servicios, volúmenes y políticas;
excluye Env/credenciales. Ese baseline se utilizó en la comparación real posterior;
no se recrearon contenedores ni se descargaron imágenes para hacerlos coincidir.

## Montaje, servicios y piloto recuperados — comprobación final

Después de la recuperación, el operador ejecutó la secuencia separada revisada:
restaurar la configuración respaldada (`CONFIG_RESTORED_NO_START=1`), montar el
SSD de datos, pasar el checker de sólo lectura y arrancar containerd/Docker.
El checker confirmó ext4rw en /var/lib/docker, UUID/serie187F correctos, raíz del
SO excluida y los20 volúmenes presentes. No se arrancó Docker sobre la carpeta
vacía del SO.

Lectura de las11:35:08 UTC: Docker29.8.1 activo y **20 contenedores originales**
(18 app2-cvat y2 Ollama), todos running, sin reinicios ni Error. IDs, nombres,
image IDs/referencias, proyectos/servicios, políticas, volúmenes y distribución
Type/Name/Destination/RW de mounts coinciden con las definiciones archivadas.
Redisondisk declara healthy; los otros19 no tienen HEALTHCHECK declarado.
Ambos Ollama arrancaron automáticamente con sus IDs originales. La comparación
no afirmó igualdad byteexacta de los paths Source de bind mounts, que no se
retuvieron en ese inventario sanitizado.

La comprobación final del coordinador confirma API CVAT: **4 tareas, 4 trabajos,
9 formas**, con task5/job5/shape10/frame1 conservados. Ambas imágenes PNG
originales conservan sus SHA exactos. Túnel PC `http://localhost:18080`
restaurado y HTTP200; se puede retomar la anotación del piloto, sin volver a
instalar CVAT ni repetir reparación/montaje. Esto verifica los datos y acceso
consultados, no una prueba de estabilidad prolongada del almacenamiento.

Evidencias privadas adicionales:

- `docker-post-start-compare-20261020T113508Z.json`, SHA256
  `2ed036af14d9223b10c11cb958f3f4dd756e9785b6ceceb94b629b694bbf6fd0`.
- `docker-mount-layout-compare.json`, SHA256
  `20c6f1e85053e9961d6f75f71e18aa6abfdc038c6d7758b8b40c7b81be8b13ce`.
- Las evidencias finales de API/DB/PNG/túnel están indexadas en el
  [incidente actual](../../../docs/incidents/2026-10-20_APP2_SSD_DOCKER_NO_RESPONDE.md).

Se conservan backups lógicos, capas escribibles, snapshots y undo. No limpiar
esos respaldos ni actualizar también el SSD del SO como parte de retomar el
piloto. Ante una nueva incidencia, diagnosticar el estado nuevo con su evidencia;
esta receta deliberadamente exige el boot/informe antiguos y no es un remedio
automático reutilizable.
