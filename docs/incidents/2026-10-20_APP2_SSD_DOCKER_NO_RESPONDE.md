# app2 — SSD de Docker no responde al retomar la anotación

**ID:** APP2-STORAGE-20261020.\
**Fecha/zona:** 20-10-2026, Europe/Madrid.\
**Estado:** SSD Docker vuelve a detectarse y protecciones de mantenimiento VERIFICADAS tras arranque nuevo; SMART/error-log/kernel recibidos del operador; integridad de datos/DB y copia de rescate PENDIENTES.

## Resultado y alcance actual

**El SSD de Docker vuelve a detectarse tras la retirada/reconexión de AC reportada
por el operador.** SSH está operativo y el arranque es nuevo:
`cebc2464-2073-4f1e-82fc-17ee30941a22`. La consulta
`booting-review-initial.json`,07:25:35UTC/09:25:35Europe/Madrid, uptime40,92s,
y `cold-boot-system-review.json`,07:26:14UTC/09:26:14Madrid, uptime78,62s,
verifican dos controladores NVMe en estado **live**.

| Identidad | Observación actual tras este arranque |
|---|---|
| SSD Docker/datos | Samsung990PRO2TB, serialS7DRNJ0X107187F,2.000.398.934.016bytes; actualmente nvme0n1 y partición nvme0n1p1 |
| UUID Docker | b819b286-2006-4474-b2d5-13982b0f1536, presente; partición sin montar |
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

**Reaparición no significa datos íntegros ni CVAT recuperado.** No se ha montado
el SSD, ejecutado fsck, copiado datos, restaurado configuración o arrancado Docker.
Las cargas Docker, incluido CVAT/Ollama, permanecen detenidas por las protecciones.
La raíz sana no tiene espacio para una imagen completa de2TB y el operador
confirma que **no dispone de otro almacenamiento**. No hay destino disponible
para la imagen completa; se valora como PLAN una copia selectiva de datos CVAT
al SSD sano del SO, primero comprobando tamaños, capacidad y permisos. No se ha
montado el origen ni iniciado esa copia. La ausencia de otro disco no implica que
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
incidente. Backup e integridad de datos siguen pendientes; no se han montado,
copiado o reparado datos ni arrancado Docker o actualizado firmware.

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

## Autorización de rescate y corrección — preestado registrado

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
leyó su configuración. ipmitool no está instalado. No confundir sóloSSH
actualmente disponible con inexistencia de BMC o acceso remoto ya resuelto.
GNUtar1.35,rsync,dumpe2fs ydebugfs ya existen; raíz libre82.682.929.152bytes en
esa consulta. No se instaló ni cambió ningún paquete o configuración. Mantener el SSD del SO095A como destino sano
si conserva la única copia; no actualizar ambos dispositivos a la vez.

`authorized-maintenance-before.json`,07:43:52UTC/09:43:52Europe/Madrid,
bootcebc2464-2073-4f1e-82fc-17ee30941a22 y uptime1136,79s, verifica de nuevo
SSD/UUID presentes, ambos NVMe live, cinco máscaras y unidadesinactive,
fstabnoauto,ro,noload0,0 y ausencia de montaje. Éste es el preestado de esta fase.

Preparación técnica en curso: helper storage_rescue.py para check de lectura,
inventario privilegiado con montaje temporalro,noload y cleanup, y copia
selectiva del origen de sólo lectura al SO sano. Receta oficial de firmware/ISO
se prepara por separado. Todavía no están desplegados/verificados, no se ha
montado temporalmente el origen ni copiado datos, creado USB o actualizado
firmware en esta fase. Los avances se registrarán sólo al disponer de logs:
fuente/hash, ubicación exacta, ejecución, limpieza y estado final. No se solicita
una nueva aprobación de cada paso reversible ya incluido en esta autorización.

## Hoja de ruta correctiva — AUTORIZADA, ejecución técnica pendiente

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

## Cronología anterior — observaciones de cada fase, no estado actual

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

## Evidencia directa anterior al reinicio

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

## Registro de kernel aportado por el operador

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

## Fallo del controlador confirmado en el filtro específico

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

## Resultado comprobado del reinicio por software

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

## Datos conservados y límites de la copia

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

## Mantenimiento autorizado y aplicado por el administrador

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

## Receta preparada para el administrador

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

## Plan anterior tras reconexión de AC — histórico, superado por el arranque actual

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

## Receta presencial anterior — no repetir ahora; dispositivo ya reaparecido

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

## Punto de reanudación vigente tras reaparecer el SSD

1. Mantener las cinco máscaras/fstab y el SSD sin montar. No repetir ciclos de
   energía, resets ni --restore-config para probar.
2. SMART/error-log/kernel ya recibidos como salida sudo del operador. Conservar
   esa procedencia y no confundir los contadores favorables actuales con
   integridad del filesystem/base de datos o una causa demostrada.
3. El operador no tiene otro almacenamiento. La imagen completa exige al menos
   2.000.398.934.016bytes más margen; no hay destino para ella. Valorar copia
   selectiva CVAT al SO sano sólo tras comprobar tamaño real, espacio y permisos,
   conservando margen del SO. No usar el volumen ajenoSPM. Esa alternativa es un
   PLAN pendiente, sin montaje ni copia ejecutados; no equivale a un clon completo.
4. Preservar primero la copia; revisar y recuperar sobre copia antes de reparar,
   actualizar firmware, restaurar configuración o arrancar Docker. Aún no hay
   integridad de datos ni DB comprobada. La posibilidad de copia selectiva debe
   valorarse expresamente si no hay destino para imagen completa.
5. Sólo tras el rescate y validación, revisar tareas/anotaciones de CVAT y cambios
   posteriores al snapshot19-10 antes de cualquier reimportación o entrenamiento.

## Evidencia y reanudación de app2

Carpeta privada: `../Humanoide-vla-evidence/20261020T061422Z_APP2_RESUME_READONLY/`.
Incluye consultas exactas, errores, respuestas HTTP, inventario de discos/montaje,
snapshot previo conservado, resumen, before/after y checksums. Los extractos de diagnóstico no contienen contraseñas; el backup privado del
SO descrito arriba sí contiene credenciales y no debe publicarse. No hay una
reparación del SSD ejecutada.

Tras recuperar el acceso: verificar tarea5/job5 y sus contornos actuales antes de
editar o reimportar; conservar cualquier trabajo posterior al snapshot. Completar
el frame1 y su revisión, y reunir escenas independientes antes del entrenamiento.
