# APP2 — preparar la actualización del Samsung 990 PRO

**ID:** APP2-FIRMWARE-PREP-20261020. **Fecha/zona:** 20-10-2026, Europe/Madrid.
**Estado:** **8B2QJXD7 verificado en Linux sólo en S7DRNJ0X107187F**,
live; el SSD del SO095A conserva4B2QJXD7/live. Lectura10:08:59 UTC en
`post-firmware-ssh-readonly.json`, Boot ID
`97828070-b077-4777-9ce6-3ed952d66bb2`, guarda `CHECK_OK_NO_MOUNT`.
BootNext se observó ausente después del arranque. **Restauración CSM guardada:**
UEFI vivo mostró Enabled; se cambió a Disabled, Primary Display se leyó
Discrete graphics card sin editarlo, y F10 mostró sólo CSM Enabled → Disabled.
Se confirmó Enter a las10:17:26 UTC. **Arranque posterior PASS10:20:03 UTC**,
boot `e719f517-0709-417a-b521-7bc8c0212bf6`, UEFI,187F8B/095A4B/live y cinco
máscaras/inactividad/check correctos. Lectura EFI10:20:43 UTC: BootCurrent0001,
BootOrder sólo0001 Ubuntu, sin BootNext ni entradas BBS; SecureBoot disabled.
Restauración y arranque normal verificados. **Recuperación offline ejecutada por
el operador11:17:31 UTC:** preen0, recuperación del journal y resumen clean;
undo4.345.856bytes. La comprobación posterior `-f -n` completó cinco pasadas0,
sin omitir journal, diferencias de contadores ni marcadores de revisión. SMART
de ambos SSD conserva critical_warning/media_errors/error-log0; guardas finales
correctas. **Activación final verificada11:35 UTC:** configuración restaurada,
datos montados ext4/rw en el SSD187F, checker de veinte volúmenes PASS y
Docker/containerd activos. Los veinte contenedores originales están running,
restart_count0 y definiciones coincidentes. CVAT2.79.0/API/UI200; cuatro tareas,
cuatro jobs y nueve formas; job5 conserva shape10/frame1 y dos PNG coinciden
exactamente con sus originales. Túnel localhost18080 restaurado. Ver sección15.
**Reanudación:** continuar la anotación humana de APP2 y vigilar la fiabilidad del
almacenamiento conservando backups/undo/evidencia. No hay sudo pendiente ni
recuperación, restauración, montaje o START que repetir. Los comandos siguientes
son registro histórico de esta intervención, no instrucciones actuales. La
comprobación puntual no demuestra estabilidad prolongada del SSD.
Informes privados: `received-offline-preflight-20261020T1054Z.json` y
`received-offline-recovery-20261020T1054Z.json`.
El medio virtual fue retirado y el Chrome aislado propio cerrado; perfil privado
retenido. El intento previo de Sign out agotó su espera: **logout BMC no comprobado**.
El SSD095A se excluyó respondiendo N a continuar con el siguiente dispositivo.
Después del bloqueo de imagen/teclado en UEFI, el
apagado ACPI y encendido controlado recuperaron Ubuntu/SSH: Boot ID
`97a5c584-ff68-4e18-b6b1-c479951083be`, check `CHECK_OK_NO_MOUNT`.
La [receta BMC](BMC_RECUPERACION_KVM.md) conserva esa recuperación, sin reset
forzado. Después del gate de vídeo120s/Enter vacío y SHA virtual coincidente,
se volvió a UEFI. **CSM temporal guardado:** el resumen F10 mostró únicamente
`Launch CSM: Disabled → Enabled`; se confirmó OK/Enter y se observó POST.
**Ubuntu volvió a arrancar** a las09:59:28 UTC, Boot ID
`1c617aab-a3c3-4665-83b7-d6d90477a187`. BootCurrent0001 sigue siendo Ubuntu EFI;
el firmware añadió entradas BBS0002/0003 y dejó BootOrder0001,0002,0003.
No se editó explícitamente ese orden; su cambio automático queda registrado.
**BootNext0003 y reinicio ejecutados por el operador a las10:03:15 UTC**,
con guarda correcta y selección temporal confirmada. A las10:05:01 UTC la KVM
muestra **ISOLINUX6.03**, arranque del CD verificado. Después se confirmó dos
veces Y para Drive1/serie187F y se observó finalización correcta. Se declinó el
siguiente dispositivo con N y se pulsó Enter para salir a las10:07:25 UTC;
el wrapper de la ISO condujo después al reinicio. La lectura Linux posterior
confirma8B en187F y4B en095A. Después el operador confirmó guarda y otro
`sudo systemctl reboot --firmware-setup`, aproximadamente10:10 UTC, para revertir
CSM. La KVM mostraba una imagen Linux antigua y reconexión; no se da por
confirmada la llegada a UEFI ni se envían teclas de reversión sin imagen actual.
La restauración CSM/Primary Display ya se comprobó y guardó en UEFI, como se
detalla en sección11; el arranque normal/EFI posterior ya pasan. Falta salud/datos.

Esta receta acompaña al [incidente de almacenamiento](../../../docs/incidents/2026-10-20_APP2_SSD_DOCKER_NO_RESPONDE.md).
Consultar allí el estado vigente de las copias y servicios antes de actuar.
La actualización se prepara después de rescatar y verificar los datos que se
quieran conservar; no demuestra ni repara por sí sola la integridad de EXT4/CVAT.

**Gate posterior verificado, 20-10-2026:**
`bmc-kvm-120s-stability.json` conserva12/12 muestras de WebSocket OPEN durante
120s, running=true, sin reconexión y edades de recepción1–160ms. El Enter vacío
produjo cambio de imagen en la consola de login, sin escribir usuario ni comando;
captura `bmc-kvm-empty-enter-after.png`. La ventana de muestras termina a las
09:44:39 UTC. Esto verifica esa sesión en Ubuntu, no su estabilidad durante POST.
El operador ejecutó `sudo sha256sum /dev/sr0`: hash completo coincidente otra
vez con la ISO de la sección2, según
`virtual-cdrom-second-attachment-sha256-operator-result.json` de09:42:17 UTC.
El CD observado es AMI Virtual CDROM0 de52.428.800bytes, sin montar; no se deduce
su integridad del widget KB. En ese instante no se había arrancado la segunda
conexión; el arranque y resultado posteriores figuran en las secciones9–10.

Snapshot privado del PC previo al siguiente intento:
`pre-fw-local-source-20261020T094356Z`, TAR SHA256
`1ce1f4522592ed955ca5cc33dc552c2c244770544f8ee70db05fae3822076f37`.
Conserva el estado local previo; no sustituye los backups del servidor.

## 1. Identificar el destino

Datos contrastados con las lecturas conservadas del servidor, no con nombres de
dispositivo supuestos:

| Recurso | Identidad | Tratamiento previsto |
|---|---|---|
| SSD de datos Docker | Samsung 990 PRO with Heatsink 2TB; serie `S7DRNJ0X107187F`; UUID de la partición `b819b286-2006-4474-b2d5-13982b0f1536` | Único candidato de esta intervención; firmware observado `4B2QJXD7` |
| SSD del sistema operativo | Mismo modelo; serie `S7DRNJ0X107095A` | Excluido de esta actualización; puede contener la única copia de los datos rescatados |
| Placa | ASUS Pro WS WRX80E-SAGE SE WIFI II, BIOS observado `1602` | No se prepara una actualización de BIOS |

Los nombres `nvme0`/`nvme1` cambiaron entre arranques. Volver a contrastar modelo,
capacidad y **serie completa** cuando se elija el SSD. Si la utilidad no permite
identificar inequívocamente el destino, detenerse antes de confirmar escritura.
No aprobar automáticamente todos los Samsung detectados.

## 2. Fuente y archivo preparados

La [página oficial Samsung](https://semiconductor.samsung.com/consumer-storage/support/tools/)
enlaza el firmware **8B2QJXD7** para la serie 990 PRO. Sus notas citan estabilidad
de lectura para 8B y falta de reconocimiento intermitente para 7B. Son motivos
para evaluar la actualización, sin confirmar la causa del fallo de esta unidad.

| Dato | Valor comprobado en el PC |
|---|---|
| URL final HTTPS | `https://download.semiconductor.samsung.com/resources/software-resources/Samsung_SSD_990_PRO_8B2QJXD7.iso` |
| Respuesta | HTTP 200 |
| Tamaño | 52.428.800 bytes, 50 MiB |
| SHA256 local | `f05508f3228960fc1501fe5a27d3a826377332afc8c021aac44487c8fd1c93d5` |

El hash se calculó sobre la descarga conservada; no es un checksum publicado
por Samsung ni una firma del fabricante. URL, cabeceras HTTP, fecha UTC, tamaño
y hashes de ISO/manuales están en la evidencia privada:

```text
../Humanoide-vla-evidence/20261020T061422Z_APP2_RESUME_READONLY/firmware-preparation/
  download-manifest.json
  inspection-manifest.json
  README-preparation.md
  Samsung_SSD_990_PRO_8B2QJXD7.iso
```

No añadir la ISO ni los binarios extraídos a Git. Para descargar otra copia en
una carpeta **nueva del PC**, sin ejecutar su contenido:

```bash
mkdir -m 700 samsung-990-pro-preparacion
cd samsung-990-pro-preparacion
curl --fail --location --proto '=https' --proto-redir '=https' \
  --connect-timeout 15 --max-time 120 \
  --dump-header Samsung_SSD_990_PRO_8B2QJXD7.iso.headers \
  --output Samsung_SSD_990_PRO_8B2QJXD7.iso \
  https://download.semiconductor.samsung.com/resources/software-resources/Samsung_SSD_990_PRO_8B2QJXD7.iso
stat --format='%s bytes' Samsung_SSD_990_PRO_8B2QJXD7.iso
sha256sum Samsung_SSD_990_PRO_8B2QJXD7.iso
```

Si tamaño/hash difieren de esta instantánea, conservar ambos y verificar qué ha
cambiado en la fuente; no asumir que otro archivo es el mismo firmware preparado.

## 3. Qué se comprobó sin arrancar la ISO

`file`, `xorriso`, `sbverify --list` y lectura gzip/newc, disponibles en el PC,
permitieron obtener lo siguiente sin ejecutar sus archivos:

- Imagen ISO9660 con MBR isohybrid y una entrada El Torito **BIOS**; no se
  enumeró una entrada El Torito EFI ni una partición ESP.
- Contiene `EFI/boot/bootx64.efi`, `grubx64.efi`, configuración GRUB y módulos
  x86_64-efi. Su presencia no garantiza arranque UEFI al copiar la ISO en bruto.
- `sbverify --list` enumera firmas Microsoft/Canonical en los cargadores; el
  kernel `bzImage` 5.15.39 no presenta tabla de firma. No se ha verificado la
  cadena de confianza, su revocación ni compatibilidad con Secure Boot de ASUS.
- El initrd contiene `8B2QJXD7.enc`; sus scripts arrancan automáticamente el
  actualizador interactivo. No se encontró un README interno separado. Se
  conservaron inventario y hashes de 901 entradas, sin ejecutar el actualizador.

**Lectura posterior del SO, 20-10-2026 a las 08:24:51 UTC:**
`firmware-boot-mode-readonly.json` confirma plataforma UEFI de 64 bits y
`mokutil --sb-state` con código0, `SecureBoot disabled`, sin modificar BIOS.
Esto no verifica que la ISO preparada arranque en UEFI ni su cadena de confianza.
**El arranque legacy se verificó después, en las secciones9–10; arranque UEFI
de esta ISO sigue sin validar.** No extraer el actualizador
para ejecutarlo por SSH, parchearlo, instalarlo en Ubuntu o cargar el `.enc` con
`nvme fw-download` a partir de esta inspección. Tampoco usar `dd` suponiendo que
la estructura híbrida resuelve todos los modos de arranque.

## 4. Método del fabricante y requisitos para la aplicación posterior

El [manual Samsung enlazado actualmente](https://semiconductor.samsung.com/resources/user-manual/Firmware_Update_Utility_UserManual.pdf)
es de mayo de 2019, con portada rev3.2 y páginas rev3.1. Describe crear USB con
**UNetbootin → Diskimage → ISO → USB identificado**, reiniciar desde él y seguir
la utilidad interactiva. Pide copia previa y alimentación estable; no define
compatibilidad UEFI/Secure Boot. No se creó un USB; el medio virtual observado
posteriormente se describe en la sección6, todavía sin validar su arranque.

Para la sesión de aplicación faltan:

1. Copia verificada de los datos esenciales y plan de recuperación. Un hash
   correcto de la ISO no sustituye una copia del contenido de CVAT.
2. Consola visible y operable durante el reinicio: monitor/teclado o BMC con
   consola y, si se usa, medio virtual ya comprobados. SSH de Ubuntu no controla
   los diálogos de la utilidad una vez se abandona ese sistema.
3. USB prescindible identificado por modelo/capacidad/serie, cuyo contenido se
   pueda borrar, o un medio virtual compatible validado. No se asume `/dev/sdX`.
4. Comprobar el método de arranque sin modificar a ciegas BIOS, RAID ni claves
   Secure Boot. Anotar cualquier cambio autorizado y su restauración.

El [manual ASUS de esta placa](https://dlcdnets.asus.com/pub/ASUS/mb/Socket%20sTRX4/PRO_WS_WRX80E-SAGE_SE_WIFI_II/PRO_WS_WRX80E-SAGE_SE_WIFI_II_BIOS_MANUAL_EN.pdf)
documenta F8 durante el logo para elegir arranque (p72). Advierte que activar
CSM cambia la salida primaria al VGA de placa (p69). La configuración real de
BIOS1602 se capturó después en la sección8; el gate sigue siendo consola probada.

El agente principal comprobó después el BMC por IPMI local y su canal LAN1:
IP estática `192.168.1.34/24`. Su web HTTPS responde con HTTP200, sin intentos de
login. La herramienta IPMI se desplegó aislada, sin instalar paquetes ni un
daemon o modificar el BMC. Evidencias: `ipmi-readonly-stage.json`,
`ipmi-readonly-check.json`, `ipmi-channel1-query.json` y `bmc-web-readonly.json`
en la carpeta de intervención. Se conservan los avisos de la consulta IPMI en
[su receta](IPMI_CONSOLA_REMOTA.md). Tras la consulta de la
[FAQ oficial ASUS para esta placa](https://servers.asus.com/support/faq/detail/1047906)
y el único intento manual solicitado, el operador confirmó KVM con tecla Enter
operativa y medio virtual cuyo control muestra `Stop Media`. No se registran
credenciales de la unidad; no hubo intentos automatizados, resets o cuentas nuevas.
El guest detectó el CD virtual y su hash privilegiado coincidió con la ISO
preparada. En esa fase faltaba arrancarla; el resultado posterior está en sección9.

Con sólo SSH **sí se puede continuar el rescate y la validación de los datos**.
La aplicación posterior utilizó consola y selección inequívoca187F, como consta
en sección9; Linux ya verificó8B en187F y4B en095A. La restauración CSM se
guardó después, sección11, y falta comprobar el arranque final.
Los reinicios se conservan explícitamente en las secciones7/10 como historia;
no se programan por escribir esta documentación.

## 5. Verificación posterior prevista

Una vez aplicado de forma controlada, guardar el resultado de la utilidad y
releer serie, firmware, SMART, error-log y kernel después de arrancar Ubuntu.
Comparar especialmente el SSD187F y comprobar que el SO095A sigue como estaba.
Restaurar sólo las opciones de arranque que se hubieran cambiado y conservar
las protecciones de Docker hasta validar copias y sistema de archivos. Registrar
por separado firmware instalado, arranque probado, datos restaurables y
estabilidad observada; ninguna de esas verificaciones sustituye las otras.

## 6. CD virtual verificado y primer reinicio ejecutado

**EJECUTADO por el operador y verificado después.** Se mantiene la descripción
del procedimiento utilizado como historia, no como orden para repetirlo.
El operador mantiene abierta la KVM y confirma que Enter responde; el medio virtual permanece conectado
(`Stop Media`). La lectura `firmware-virtual-cdrom-preflight.json`, de las
08:31:23 UTC del20-10-2026, observa `/dev/sr0`, modelo `Virtual CDROM0`, con
102.400 sectores de512 bytes: **52.428.800 bytes/50 MiB**. La lectura del medio
sin privilegios fue denegada; su tamaño no sustituye al checksum.

En esa misma comprobación, `storage_rescue.py --check` terminó con código0 y
`CHECK_OK_NO_MOUNT`, SSD de datos serie187F y SO095A correctos. No se modificaron
BMC, red o BIOS. El usuario ya autorizó el reinicio y la actualización; esta
línea sólo pretende verificar el medio y reiniciar hacia el menú, sin confirmar
la escritura de firmware.

En la terminal SSH del servidor, el operador ejecutó esta línea:

```bash
(umask 077 && python3 /home/luisacuna/app2/maintenance/storage_rescue.py --check && sudo sha256sum /dev/sr0 > /home/luisacuna/app2/maintenance/virtual-cdrom-20261020T0832Z.sha256 && test "$(cut -d ' ' -f 1 /home/luisacuna/app2/maintenance/virtual-cdrom-20261020T0832Z.sha256)" = 'f05508f3228960fc1501fe5a27d3a826377332afc8c021aac44487c8fd1c93d5' && echo ISO_VERIFICADA && sudo systemctl reboot)
```

La redirección guarda el checksum con el usuario de la sesión y `umask077`.
Los `&&` impiden llegar al reinicio si falla el check, la lectura o la comparación.
Mantener la KVM abierta: cuando aparezca el logo ASUS, pulsar **F8** para abrir
el menú de arranque. Detenerse en ese menú y comunicar el resultado; **no elegir
todavía un SSD ni confirmar el actualizador Samsung**. Si el medio no coincide,
conservar el fichero y la salida para diagnóstico, sin probar otro dispositivo
o forzar el reinicio. No hay cambio de orden persistente de arranque en esta línea.

**Resultado comprobado:** `firmware-reboot-progress-second.json`, de las
08:36:50 UTC, registra boot nuevo `93957c9b-5c54-490a-ba45-ea8e85b4fcb0` y el
fichero `virtual-cdrom-20261020T0832Z.sha256` con el SHA exacto
`f05508f3228960fc1501fe5a27d3a826377332afc8c021aac44487c8fd1c93d5` de `/dev/sr0`.
No se retuvo el menú de arranque; Ubuntu volvió a iniciar.
`firmware-post-reboot-capability-readonly.json`, de las08:38:05 UTC, vuelve a
observar ambos NVMe `live`, firmware `4B2QJXD7`, guard/check correcto y systemd255.4.
No se ha actualizado ninguno de los SSD.

## 7. Antecedente: configuración ASUS abierta y bloqueo posterior

**EJECUTADO por el operador:** confirma la configuración ASUS/UEFI abierta en
KVM tras la orden siguiente. Se conserva como historia, no para repetirla:

```bash
sudo systemctl reboot --firmware-setup
```

El [manual oficial de systemctl](https://www.freedesktop.org/software/systemd/man/latest/systemctl.html#--firmware-setup)
define la opción para solicitar configuración de firmware en el siguiente
arranque. La lectura D-Bus previa devolvió `CanRebootToFirmwareSetup="challenge"`
y `RebootToFirmwareSetup=false`: soportado pero requiere autorización; todavía
no había solicitud activada. No fue necesario instalar `bootctl`.

Esta orden solicita el siguiente arranque en la interfaz ASUS mediante el bit
`EFI_OS_INDICATIONS_BOOT_TO_FW_UI` de `OsIndications`. No cambia BootOrder, CSM,
Secure Boot ni programa una escritura del SSD. Según la
[especificación UEFI §8.5.4](https://uefi.org/specs/UEFI/2.10/08_Services_Runtime_Services.html#exchanging-information-between-the-os-and-firmware),
el firmware debería limpiar ese bit al consumir la solicitud y mostrar su
interfaz, para que no se repita en arranques siguientes. Es el comportamiento
esperado; su consumo debe verificarse, no darse por realizado al enviar la orden.

**Antecedente, captura del operador a las08:44 UTC/10:44 Madrid:** la pantalla
está en **Arrancar → Configuración de arranque**, no en una lista Boot Menu.
Se ven salida primaria `Discrete graphics card`, Fast Boot desactivado y POST
de3s. CSM no se ha abierto ni modificado en esta etapa.

En la barra superior de **esa ventana KVM** aparece `CD Image (0 KB)` y
`Start Media`: no hay una ISO seleccionada en esa ventana. No se infiere de ese
indicador el estado global del CD virtual o de otra sesión; la verificación
histórica de la sección6 tampoco confirma que esta ventana esté sirviendo el
medio en este momento.

**Instrucciones solicitadas entonces, conservadas como antecedente; no repetir
desde este punto tras recuperar Ubuntu:**

1. En la KVM, usar `Browse File` para seleccionar en Descargas
   `Samsung_SSD_990_PRO_8B2QJXD7.iso`. Pulsar `Start Media` y observar
   `Stop Media`. El número KB de ese widget no es una verificación de tamaño
   o integridad: no exigir que alcance50MiB. El SHA del dispositivo leído en
   el guest es la comprobación directa que se usó en la sección6.
2. Sin reiniciar ni modificar ajustes, pulsar **Esc una vez** para volver a
   la pantalla principal **Arrancar** y mostrar sus opciones de Boot Override
   o prioridades. Listarlas para revisión; no editar las prioridades ni elegir
   todavía el CD virtual o un SSD.

**Conservar BootOrder, CSM y Secure Boot como están; no confirmar ningún
flasheo.** No se ha validado el arranque UEFI de la ISO ni seleccionado un
destino de actualización.

La apertura de UEFI es una confirmación del operador. El consumo y limpieza del
bit `OsIndications` quedaban **PENDIENTES de lectura** entonces; la comprobación
posterior09:13:07 UTC devolvió `b false`, conservada en
`post-acpi-ubuntu-protection-check.json`. Como antecedente separado, el broadcast pegado
por el operador sitúa el primer reinicio de la sección6 a las08:34:59 UTC,
congruente con el nuevo boot `93957c9b-5c54-490a-ba45-ea8e85b4fcb0`. No se
atribuye esa hora al segundo reinicio a configuración.

**Reversión condicional, no ejecutada:** si una solicitud se hubiera activado
pero quedara pendiente y se cancelara el plan desde Ubuntu, se puede desactivar
por la API documentada de [systemd-logind](https://www.freedesktop.org/software/systemd/man/latest/org.freedesktop.login1.html):

```bash
sudo busctl --system call org.freedesktop.login1 /org/freedesktop/login1 org.freedesktop.login1.Manager SetRebootToFirmwareSetup b false
busctl --system get-property org.freedesktop.login1 /org/freedesktop/login1 org.freedesktop.login1.Manager RebootToFirmwareSetup
```

Usar esa reversión sólo ante una solicitud pendiente que se quiera cancelar y
registrar el resultado. No escribir variables EFI en bruto. Al volver normalmente
a Ubuntu, la propiedad debería ser `b false`; si no lo es, revisar antes de
otro reinicio. No cargar valores BIOS por defecto ni tocar otras opciones como
parte de la reversión de esta única solicitud.

La imagen/teclado quedaron posteriormente sin responder pese a reabrir el
visor, Resume/Refresh Video y Ctrl+Alt+Del. No se pudo distinguir entonces un
host bloqueado de una imagen KVM obsoleta; reanexar el medio en UEFI coincidió
con el problema, sin demostrar causalidad. La recuperación ACPI/encendido de
la portada devolvió SSH. CSM no fue aplicado durante esa secuencia.

## 8. CSM temporal aplicado y restauración verificada con arranque normal

**Antecedente del cambio temporal:** tras capturar el preestado y no aparecer una
opción UEFI válida del CD, se revisó F10 a las09:52:47 UTC. El resumen contiene
únicamente `Launch CSM: Disabled → Enabled`; el agente principal confirmó
OK/Enter y observó el POST posterior. Fuentes `uefi-csm-save-reset-review.json`,
`bmc-csm-save-reset-review.png`, `bmc-csm-save-confirmed-reset.png` y
`documentation-csm-save-confirmed-reset-review.json`.
En ese recibo seguían pendientes la lectura efectiva tras el reinicio y la
enumeración de arranque. **Resultado posterior:** Ubuntu/SSH
regresó a las09:59:28 UTC, boot `1c617aab-a3c3-4665-83b7-d6d90477a187`.
La lectura EFI de la sección10 observa Ubuntu EFI activo y CD virtual legacy
enumerado. La lectura directa posterior mostró CSM Habilitada antes de
restaurarlo a Disabled; sección11. El arranque posterior verifica UEFI, orden
Ubuntu y eliminación automática de BBS; guardar no sustituye esa comprobación.

`Boot Device Control` ya mostraba `UEFI and Legacy OPROM`: **no fue editado**.
Los controles Network/Storage/PCIe mostraban `Legacy only` como valores latentes
preexistentes; tampoco se editaron. `Primary Display` quedó oculto al habilitar
CSM, sin un cambio explícito de ese campo en el resumen. Boot Option1 Ubuntu
se conservó antes de guardar; la lectura EFI posterior de sección10 confirma
Ubuntu activo. El firmware se aplicó después a187F según la utilidad, sección9;
Linux posterior confirma8B en187F/4B en095A. El resto conserva el criterio
de selección y reversión; no es una orden de repetir el cambio ya guardado.

La lectura posterior EFI confirma BootCurrent0001 Ubuntu y BootOrder0001,0002,0003:
CSM añadió automáticamente entradas BBS de discos y CD. Esto es un efecto de
configuración observado, aunque sólo se editara Launch CSM. El plan siguiente
usa BootNext sin reordenar esas entradas; restaurar y verificar el estado final
de arranque al revertir CSM, sin asumir que desaparezcan automáticamente.

La alternativa se preparó al no aparecer un arranque UEFI válido de la ISO.
La inspección de la ISO enumera una entrada El Torito BIOS y ninguna EFI. La
presencia de `EFI/boot/bootx64.efi` no prueba arranque UEFI como CD virtual.
No se extraen ejecutables Samsung a Ubuntu ni se improvisan cadenas GRUB.

**OBSERVADO, 20-10-2026 a las09:31:58 UTC:** lectura SSH del agente principal,
conservada en `server-aspeed-console-readonly-observation.json`, dentro de
`20261020T061422Z_APP2_RESUME_READONLY`:

- framebuffer `fb0.name=astdrmfb`, asociado a PCI `2a:00.0`;
- ASPEED `1a03:2000`, controlador `ast`, `card0-VGA-1=connected`;
- NVIDIA Ada `10de:26b1`, controlador `nvidia`; cuatro DP desconectados.

La consola Linux está sobre ASPEED integrada. Esto apoya la viabilidad del
cambio de salida previsto por ASUS, **sin verificar una transición UEFI/CSM ni
la estabilidad del siguiente POST**. Una captura anterior, el HTTPS del BMC o
SSH de Ubuntu no sustituyen una KVM actual que renueve imagen y acepte teclado.

El [manual ASUS, pp.68–69](https://dlcdnets.asus.com/pub/ASUS/mb/Socket%20sTRX4/PRO_WS_WRX80E-SAGE_SE_WIFI_II/PRO_WS_WRX80E-SAGE_SE_WIFI_II_BIOS_MANUAL_EN.pdf#page=68)
documenta `Launch CSM`, cambio automático de salida primaria a VGA integrada y
`Boot Device Control = UEFI and Legacy OPROM`, que admite dispositivos de ambos
modos. No obliga a convertir Ubuntu a legacy. Los controles separados de red,
almacenamiento y PCIe pueden limitar modos; el manual no garantiza la aparición
de este CD virtual ni el arranque de Ubuntu con cualquier combinación.

### Preparación y valores anteriores obligatorios

Antes de guardar un cambio, conservar capturas legibles de los valores **reales
de esa sesión**, no copiar valores de otra captura o del manual:

| Valor | Qué conservar y restaurar |
|---|---|
| `Launch CSM` | Original Disabled; único campo cuyo cambio se guardó |
| `Primary Display` | Original Discrete graphics card; verificar y restaurar al terminar |
| `Boot Device Control` | Al aparecer ya UEFI and Legacy OPROM; no editado |
| `Boot from Storage Devices`, Network y PCI-E/PCI Expansion | Valores latentes Legacy only observados; no editados |
| Boot Option Priorities / entrada Ubuntu EFI | Boot Option1 ubuntu (M.2_2: Samsung SSD990PROwithHeatsink2TB), única opción de Boot Override previa; no editar orden |
| Secure Boot / OS Type | UI Other OS / estado User; última lectura del SO SecureBoot disabled. User no significa Secure Boot activado |
| AMI Native NVMe Driver, Fast Boot, POST Delay | Enabled / Disabled / 3s originales; no editados |

Preestado en `uefi-csm-temporary-plan-and-prestate.json` y sus capturas referidas,
conservados en la misma evidencia privada. Restaurar desde esos valores, no
desde valores predeterminados del manual.

El medio debe adjuntarse **con Ubuntu aún operativo y KVM viva**, antes del
reinicio. Reidentificar el CD virtual y contrastar su SHA con el de la sección2;
mantener el mismo visor y medio durante el POST. No usar el contador KB como
prueba ni reanexar el medio dentro de UEFI en esta prueba propuesta.

### Secuencia revisada y siguiente arranque único

Los pasos de preparación y guardado siguientes conservan el método utilizado.
En esta intervención ya se capturó/revisó el preestado y se confirmó F10/POST;
**no repetir esos pasos**. El único cambio guardado fue Launch CSM; no se
reescribió Boot Device Control porque ya admitía ambos modos.

1. **Gate:** KVM con imagen actual y teclado probado, respaldo anterior guardado,
   copias verificadas y guardas de almacenamiento conservadas. Si falla la
   consola, no cambiar CSM a distancia.
2. Sólo si no hay opción UEFI válida para el CD, proponer `Launch CSM = Enabled`
   y comprobar `Boot Device Control = UEFI and Legacy OPROM`. No elegir
   `Legacy OPROM only`, no convertir el SSD del SO y no cambiar el orden de
   arranque. Registrar los campos que aparecen al habilitar CSM; no extender
   esta receta con cambios de Storage/PCIe/Network a ciegas.
3. Revisar el resumen de `Save Changes & Reset`: sólo los cambios previstos,
   incluido el cambio de salida que ASUS vincula a CSM. Guardar/reiniciar sólo
   después de esa revisión; CSM puede necesitar el nuevo POST para enumerar
   opciones legacy. No confundir una imagen vieja con un POST correcto.
4. **Siguiente paso pendiente:** confirmar de nuevo vídeo/teclado y leer CSM
   efectivo y la lista de dispositivos. Usar F8/Boot Override para **un arranque**
   del CD virtual legacy identificado, preservando la entrada Ubuntu EFI.
   ASUS describe ambos mecanismos en [p.72](https://dlcdnets.asus.com/pub/ASUS/mb/Socket%20sTRX4/PRO_WS_WRX80E-SAGE_SE_WIFI_II/PRO_WS_WRX80E-SAGE_SE_WIFI_II_BIOS_MANUAL_EN.pdf#page=72).
   Si falta el CD, la entrada Ubuntu o el control de consola, detener la prueba;
   no hacer más cambios de compatibilidad ni confirmar firmware para probar.
5. Si llega la utilidad Samsung, verificar antes de escritura la serie completa
   **S7DRNJ0X107187F**, excluyendo **S7DRNJ0X107095A**. La presencia del menú o
   de la utilidad no equivale a actualización aplicada.

### Reversión y regreso al arranque normal de Ubuntu

Si se cancela antes de guardar, usar `Discard Changes & Exit`. Si se guardó,
cuando la utilidad haya terminado y permita volver a configuración, **antes
del siguiente arranque normal de Ubuntu** restaurar `Launch CSM`,
`Primary Display` y cualquier otro campo efectivamente cambiado a sus valores
capturados. Contrastar prioridades/entrada Ubuntu EFI y Secure Boot con el
preestado; no cargar valores por defecto. ASUS documenta guardar/descartar en
[p.78](https://dlcdnets.asus.com/pub/ASUS/mb/Socket%20sTRX4/PRO_WS_WRX80E-SAGE_SE_WIFI_II/PRO_WS_WRX80E-SAGE_SE_WIFI_II_BIOS_MANUAL_EN.pdf#page=78).

Nunca interrumpir una escritura de firmware para ejecutar la reversión. Si se
pierde la consola, no enviar secuencias de teclas a ciegas ni resets repetidos:
registrar el estado y recuperar el acceso antes de otro cambio. El hecho de que
ASPEED esté conectado no elimina ese límite.

Tras regresar a Ubuntu, comprobar arranque UEFI mediante `/sys/firmware/efi`,
Boot ID nuevo, SSD por serie/firmware, SMART/kernel y `storage_rescue.py --check`.
Mantener las cinco máscaras y origen sin montar; el firmware no autoriza por sí
solo restaurar Docker o CVAT. Guardar capturas anteriores/posteriores, resultado
real de CSM, arranque de la ISO, firmware y reversión como hechos separados.

## 9. SSD187F confirmado y actualización completada según la utilidad

**EJECUTADO:** `samsung-updater-device-confirmation.png` muestra Drive1, serie
**S7DRNJ0X107187F**, modelo Samsung SSD990PRO with Heatsink2TB y firmware previo
4B2QJXD7. Tras comprobar esa identidad, el agente principal envió **Y y Y** a la
confirmación inicial y advertencia. `samsung-drive1-flash-progress.png` muestra
ambas respuestas y **Firmware Update Completed**. Se respondió **N** a continuar
con el siguiente dispositivo; `samsung-next-device-declined.png` muestra salida
de la utilidad. Enter para salir se envió a las10:07:25 UTC. **095A excluido**;
su firmware posterior se leyó por separado:4B2QJXD7/live en095A y8B2QJXD7/live
en187F,10:08:59 UTC. Esa lectura, no sólo el mensaje de finalización, verifica
la versión efectiva tras arrancar Linux.

`vendor-187F-completed-documentation-observation.json` conserva hashes de esas
capturas inspeccionadas y el reporte de entradas. El resultado Linux posterior
consta en `post-firmware-ssh-readonly.json`; la restauración CSM ya se guardó
según sección11, pendiente de comprobar su arranque posterior.
No repetir el flash al volver a Ubuntu. El criterio siguiente se
conserva como método utilizado y para futuras intervenciones autorizadas.

El [manual Samsung, pp.6–7](https://semiconductor.samsung.com/resources/user-manual/Firmware_Update_Utility_UserManual.pdf#page=6)
describe escaneo y lista de discos con modelo, serie y firmware; después muestra
confirmación para un dispositivo concreto y otra advertencia antes de escribir.
Tras completar un disco pregunta si se quiere continuar con el siguiente.
El manual no documenta elegir arbitrariamente un número de disco ni garantiza
que responder `N` a la primera confirmación salte al siguiente dispositivo.

Al llegar a la utilidad, detenerse para capturar la lista y el dispositivo
propuesto **antes del primer `Y`**. Confirmar únicamente si la pantalla muestra
de forma inequívoca **S7DRNJ0X107187F** y el modelo correcto. **S7DRNJ0X107095A
queda excluido**, aunque la utilidad también lo considere actualizable.
No usar posición de la lista o nombre NVMe del arranque anterior como identidad.

Si aparece primero095A y no hay una opción explícita, comprobable y anterior a
escritura para elegir187F, detener el plan sin confirmar. No asumir `N=skip`,
no responder `Y` para alcanzar otra pantalla y no aprobar una opción de todos
los discos. Si falta la serie o sólo aparece el modelo común a ambos SSD,
la identidad no está confirmada. No cambiar el binario ni los scripts para
forzar selección. Guardar el resultado y revisar la alternativa de acceso.

Si187F termina correctamente, conservar la pantalla de finalización y responder
**`N`** a continuar con el **siguiente dispositivo**; no extender la operación
a095A. El resultado y la relectura posterior por serie serán las pruebas de
aplicación, separadas de la simple aceptación de una confirmación.

### Qué demuestra la inspección estática de la ISO actual

`firmware-preparation/fumagician-selection-static-strings.json` conserva lectura
de bytes gzip/newc y cadenas imprimibles de `root/fumagician/fumagician`,
2.960.416bytes, SHA256
`c130cf7c7bcafd019d4c023a2d85a198dba2e19b908e9c6f97efdb537b0c7c5b`.
Se encontraron mensajes de lista de series, confirmación de actualización,
siguiente dispositivo y finalización; no se identificó un mensaje explícito de
selección/salto. Esto corrobora el manual, **sin probar todo el flujo de control**.
El binario del fabricante no se ejecutó para esta inspección.

El script real `root__fumagician__fumagician.sh.source.txt` llama a la utilidad
y, cuando ésta termina, espera una tecla durante10s; por defecto ejecuta
`/sbin/reboot -f`. No asumir que queda esperando indefinidamente para revisión.
Mantener KVM y atención al POST después de finalizar, para interceptar la vuelta
a configuración y restaurar CSM/Primary Display según la sección8 antes del
arranque normal de Ubuntu. No entrar en el modo de depuración ni modificar ese
wrapper. Nunca interrumpir una escritura en curso para efectuar la reversión.

## 10. BootNext ejecutado y CD arrancado; consumo posterior por verificar

**EJECUTADO por el operador a las10:03:15 UTC:** guarda `CHECK_OK_NO_MOUNT`,
escritura de BootNext0003 confirmada y reinicio. A las10:05:01 UTC,
`bootnext-first-check.png` muestra **ISOLINUX6.03**, con la ISO Samsung adjunta.
Ese recibo verifica el arranque del CD; la selección187F y finalización de la
utilidad se observaron después y constan en la sección9.
`bootnext-executed-documentation-observation.json` conserva el reporte recibido
del operador y hash de la captura inspeccionada, separando esas fuentes.
BootNext se observó ausente al volver a Ubuntu; se conserva la observación
comunicada por el agente principal en
`post-fw-linux-and-rollback-reboot-documentation-observation.json`.

Con Ubuntu de nuevo accesible antes de esa acción, no hizo falta repetir
la carrera de F8 ni reanexar la ISO dentro de UEFI. La lectura de las10:00:20 UTC,
`post-csm-ubuntu-efi-bootnext-cd-baseline.json`, conserva el preestado, variables
EFI crudas, decodificación de entradas y check de almacenamiento:

| Variable / entrada | Observación de esta sesión |
|---|---|
| Boot ID | `1c617aab-a3c3-4665-83b7-d6d90477a187` |
| BootCurrent | `0001`, Ubuntu por `\\EFI\\UBUNTU\\SHIMX64.EFI` |
| BootOrder | `0001,0002,0003`; Ubuntu sigue primero |
| BootNext | Ausente antes de la acción propuesta |
| Boot0002 | BBS Hard Drive; no seleccionar para esta prueba |
| Boot0003 | BBS CDROM tipo3; sus datos incluyen AMI Virtual CDROM0, único dispositivo CD de esa entrada |
| Guarda | `CHECK_OK_NO_MOUNT`, origen187F y destino095A correctos |

El tamaño y SHA completo del medio ya se verificaron con el operador como
describe la portada. La captura `bmc-no-signal-after-refresh-video.png`, pese a
su nombre, muestra Ubuntu TTY. Hubo Refresh Video a las09:58:17 UTC; se registra
la secuencia sin atribuirle causalmente la recuperación del arranque o del vídeo.

`efibootmgr` instalado es versión18. Su ayuda real confirma `--bootnext XXXX`
y `--delete-bootnext`; no se instala otra herramienta. El
[README del proyecto](https://github.com/rhboot/efibootmgr/blob/main/README.md)
documenta que BootNext sustituye el orden normal para un arranque y el gestor
lo elimina tras usarlo. El borrado real debe comprobarse al volver a Ubuntu.

**La cifra0003 sólo es válida para este preestado comprobado.** En otro arranque
o tras cambiar medios/efectos de CSM, descubrir y decodificar otra vez la entrada;
no copiar el número por su antigüedad en el chat. Si hay otro BootNext, no
sobrescribirlo: podría pertenecer al operador o a otra tarea. Conservar primero
variables/orden y la identidad inequívoca del CD, como se hizo en el recibo.

### Orden concreta ejecutada por el operador en esta sesión

Se conservaron KVM, teclado y medio comprobados. El operador ejecutó la línea
siguiente después de revisar ese preestado y con autorización vigente.
Se conserva para reproducibilidad, **no para repetirla ahora desde ISOLINUX**:

```bash
python3 /home/luisacuna/app2/maintenance/storage_rescue.py --check && \
sudo efibootmgr --bootnext 0003 && \
sudo systemctl reboot
```

Los `&&` evitan pasar al paso siguiente si falla la guarda o la escritura EFI.
`--bootnext` escribe la selección temporal; no se utiliza `--bootorder`,
`--create` ni `--delete-bootnum`. Ubuntu permanece primero en el orden normal
capturado, y no se solicita otra entrada a firmware-setup en esta línea.
Conservar la salida que muestra BootNext0003 y el recibo del reinicio.
Si falla el último paso, BootNext puede quedar pendiente: no reiniciar de nuevo
a ciegas. Volver a consultar y decidir si mantener o cancelar la solicitud.

El banner ISOLINUX verifica que se alcanzó el cargador del CD una vez sin F8;
el arranque completo de la utilidad aún debe verse en KVM. Al llegar, aplicar las
condiciones de la sección9: **sólo187F**, nunca095A ni actualización de todos.

### Cancelar únicamente el BootNext creado por esta prueba

Si se escribió BootNext pero se cancela **antes de que el firmware lo consuma**,
el preestado prueba que estaba ausente y que fue esta intervención quien puso
0003. Sólo en ese caso y si la lectura actual sigue siendo0003:

```bash
if test "$(efibootmgr | awk '/^BootNext:/ { print $2 }')" = '0003'; then
  sudo efibootmgr --delete-bootnext
fi
efibootmgr
```

No borrar un BootNext distinto ni las entradas0001/0002/0003; no restaurar en
bruto variables EFI antiguas. Si no está BootNext, no hace falta borrar nada.
Esta cancelación tampoco revierte CSM. Después se guardó la restauración CSM
y se leyó Primary Display Discrete, sección11. Quedan pendientes el arranque,
la lectura de BootOrder final y los checks del SO/SSD; conservar Ubuntu EFI y documentar
cualquier cambio automático adicional. Firmware y reversión sólo se marcarán
realizados con sus respectivos resultados.

## 11. Firmware, restauración CSM y arranque normal verificados; salud pendiente

**POSTROLLBACK PASS10:20:03 UTC:**
`post-csm-rollback-ssh-readonly.json` verifica regreso de SSH, nuevo Boot ID
`e719f517-0709-417a-b521-7bc8c0212bf6`, UEFI,187F8B2QJXD7/live y095A4B2QJXD7/live.
Las cinco máscaras apuntan a/dev/null y permanecen inactivas; check
`CHECK_OK_NO_MOUNT`. `post-csm-rollback-efi-readonly.json`,10:20:43 UTC, verifica
BootCurrent0001, BootOrder sólo0001, única entrada Ubuntu, BootNext ausente y
SecureBoot disabled. Las entradas BBS añadidas por CSM desaparecieron
automáticamente: **no se borraron ni se reordenó manualmente**. Arranque normal
y restauración verificados; SMART/EXT4/CVAT todavía no comprobados.

**VERIFICADO10:08:59 UTC:** regreso de SSH, Boot ID
`97828070-b077-4777-9ce6-3ed952d66bb2`,187F8B2QJXD7/live,095A4B2QJXD7/live y
check de almacenamiento PASS. `post-firmware-ssh-readonly.json` conserva esas
lecturas; no contiene por sí solo SMART, kernel completo ni integridad CVAT.
El bloque siguiente conserva las consultas seguras para completar lo que falte;
no implica que se hayan ejecutado todas ni autoriza montar/iniciar servicios.

La finalización del proveedor no demuestra el arranque del SO ni la salud del
SSD. Esperar a que termine la utilidad y su reinicio; no interrumpir una escritura
ni arrancar otra actualización. Estas consultas de Ubuntu son **sólo lectura**,
preparadas aquí sin ejecutarlas. Guardar las salidas en evidencia privada:

```bash
cat /proc/sys/kernel/random/boot_id
uptime
test -d /sys/firmware/efi && echo ARRANQUE_UEFI
for nvme_controller in /sys/class/nvme/nvme[0-9]*; do
  test -d "$nvme_controller" || continue
  printf '%s\n' "$nvme_controller"
  cat "$nvme_controller/serial" "$nvme_controller/model" \
      "$nvme_controller/firmware_rev" "$nvme_controller/state"
done
python3 /home/luisacuna/app2/maintenance/storage_rescue.py --check
systemctl show docker.service docker.socket containerd.service \
  var-lib-docker.mount var-lib-docker.automount \
  -p Id -p LoadState -p ActiveState -p UnitFileState
findmnt --json --output SOURCE,TARGET,FSTYPE,OPTIONS
efibootmgr --verbose
mokutil --sb-state
```

Comparar **por serie**, no por nvme0/1:187F debe mostrar el firmware nuevo y
estado live;095A debe conservar4B2QJXD7. Si una lectura falla o falta un SSD,
registrarlo y mantener el origen sin montar y Docker bloqueado. El check debe
confirmar identidades/guardas, las cinco unidades deben seguir masked/inactive,
y `findmnt` no debe mostrar montada la partición de datos Docker. En EFI comprobar
Ubuntu activo y si BootNext desapareció; no borrar otro BootNext ni reconstruir
el orden por números antiguos. La lectura sysfs no sustituye SMART ni error-log.

SMART, log NVMe y kernel completo siguen pendientes de comprobación si su acceso
requiere privilegios. No marcarlos sanos por ausencia de lectura ni ejecutar
reparación EXT4, montar datos o iniciar Docker para probar la actualización.

### Reversión de los ajustes temporales en la KVM

**EJECUTADO después del reinicio a configuración:** se recuperó una UEFI viva
cerrando normalmente el medio y visor propios, sin reset adicional del BMC:

| Hora UTC | Acción y observación |
|---|---|
| 10:14:17.823 | Stop Media en la interfaz normal; CD virtual dejado de servir |
| 10:14:46.390 | Stop KVM; el visor propio cerró su pestaña |
| 10:15:21.122 | Launch H5Viewer desde MAIN; un visor nuevo recuperó UEFI viva |
| Posterior | `post-fw-rollback-csm-loaded.png`: Launch CSM Habilitada, lectura efectiva del estado temporal |
| Posterior | Selección Disabled y aviso aceptado; `post-fw-csm-disabled-after-warning.png` |
| Posterior | `post-fw-rollback-primary-read.png`: Primary Display ya Discrete graphics card, sin editar |
| Antes de confirmar | `post-fw-csm-rollback-save-review.png`: F10 enumera únicamente Launch CSM Enabled → Disabled |
| 10:17:26 | Enter de confirmación y reinicio; lectura/arranque final pendientes |

No se repitió Reset KVM Service ni se reinició el BMC para esta recuperación de
visor. El cambio ya está guardado; no repetir las teclas de restauración del
método siguiente. El siguiente resultado necesario es el arranque posterior y
verificación de las guardas/EFI/SSD. La secuencia previa fue:

El operador confirmó guarda y
`sudo systemctl reboot --firmware-setup` después de volver Ubuntu, hacia10:10 UTC.
La marca exacta del reinicio queda pendiente; no se repite aquí. KVM posterior
en reconexión/imagen antigua no confirma llegada a UEFI. Esperar imagen nueva
y teclado operable antes de aplicar la secuencia de restauración siguiente.

Si el wrapper devuelve Ubuntu antes de poder entrar
en configuración, registrar que CSM sigue temporalmente habilitado y preparar
otro acceso autorizado a firmware-setup; no repetir BootNext ni flash. Con la
utilidad terminada y una KVM nueva que renueve imagen y acepte teclado:

1. Entrar en Arrancar → CSM y leer el valor efectivo. Restaurar
   **Launch CSM Disabled**, el valor capturado antes de la prueba.
2. Volver a Configuración de arranque. Cuando el campo sea visible, comprobar
   **Primary Display = Discrete graphics card** y restaurarlo si quedó distinto.
   Mantener Fast Boot Disabled, POST3s, AMI Native NVMe Enabled y Secure Boot/
   Other OS originales; no modificar las claves ni usar F5/Load Defaults.
3. Revisar Boot Option1 Ubuntu EFI y las entradas/orden reales. Las entradas BBS
   fueron un efecto automático de CSM; no borrarlas por suponer sus números ni
   reordenar sin contrastar el preestado y el resultado tras deshabilitar CSM.
4. Revisar el resumen F10: sólo las restauraciones previstas. Guardar/confirmar
   una vez y observar el POST. Si aparecen cambios no previstos, no confirmarlos.
5. Tras volver a Ubuntu, repetir las lecturas pertinentes del bloque anterior:
   firmware187F/095A, UEFI, BootNext/BootOrder y guardas. Registrar la reversión
   efectiva y el arranque normal por separado de la actualización del SSD.

No afirmar reversión sólo por enviar teclas o guardar una opción: conservar
capturas y comprobar los valores efectivos y el resultado del reinicio.

### Helper y receta desplegados; informe sudo recibido

La [receta POSTFIRMWARE_CHECK.md](POSTFIRMWARE_CHECK.md) y `storage_postcheck.py`
preparan identidades, SMART, error-log y kernel, con la opción explícita de
`e2fsck -f -n` sobre origen desmontado. **13 pruebas locales correctas** y revisión
independiente sin bloqueo material para esa consulta condicionada. El agente
encargado instaló el helper10:22:24 UTC en
`/home/luisacuna/app2/maintenance/storage_postcheck.py`, UID1001/modo0600,
SHA256 `9e030a05bcdc3fff750ea25f6d5990d3931720f3545b4583c34da8bf1f2e8a33`,
con dependencia baseec8e727b…cee8. `--help` sin root terminó0; después el
operador ejecutó la consulta sudo de salud/FS, recibida10:30:42 UTC. Fuente inicial `postcheck-deployment-helper.json`,
con preestado en `postcheck-deployment-before.json`. El recibo final
`postcheck-deployment-final.json`,10:23:01 UTC, verifica además la receta
`/home/luisacuna/app2/maintenance/POSTFIRMWARE_CHECK.md`, SHA256
`2ff2efb788cf9a5b73d4ad46406b25d91ded341fbb13edd8282ccb7b7f3f56e0`, junto al
helper sin sobreescritura; propietarios/permisos contrastados. No reinstalar.

Límite de la revisión: sin `--filesystem-check`, rc0 significa consultas
completadas, **no salud PASS**; el JSON conserva gate y resultados. Con esa
opción, errores/truncación/JSON NVMe no interpretable o SMART de datos con
critical_warning/media_errors no cero impiden e2fsck. Revisar rc y salida;
una comprobación de lectura no repara ni autoriza montar datos.

**EJECUTADO por el operador:** `--filesystem-check` produjo el informe
`/home/luisacuna/app2/maintenance/postfirmware-check-20261020T1023Z.json`,
marca10:30:42.097783 UTC. La ausencia observada10:25:34 UTC fue anterior a esa
consulta; no es el estado vigente. Se conserva copia privada independiente,
SHA256 `324c3b3bdc4d56a657c09d0b5c71a81d3c9188b5967c117444ba95028a3bf5f5`.
El proceso terminó0, pero su etiqueta `NO_ERRORS_REPORTED_READ_ONLY` no resume
correctamente las advertencias de e2fsck. La sección12 registra los límites y
el siguiente paso propuesto. Ninguna reparación, montaje o inicio Docker se
ha efectuado por esa revisión.

### Cierre de la consola y de la sesión propia del PC

El medio ya se había retirado por Stop Media antes del rollback. El agente
principal cerró únicamente el Chrome aislado PID665887, comprobando su
propiedad; el perfil privado se conserva como evidencia. El intento anterior de
Sign out por CDP agotó la espera: **no se verificó logout ni revocación de la
sesión BMC**. Cerrar el navegador no demuestra esa revocación. El recibo
`bmc-session-cleanup-and-sudo-report-pending.json` registra el cierre, perfil,
deuda de logout y ausencia del informe. Sin cambios de alimentación/servicios
durante esta limpieza; no iniciar otro visor ni cerrar sesiones ajenas para probar.

### Diagnóstico BMC de lectura durante la espera de la reversión

**EJECUTADO10:13:36 UTC:** reutilizando sólo la sesión MAIN existente,
GET `/api/chassis-status` y GET `/api/sensors` respondieron HTTP200. Power1,
55 sensores; CPU49°C, DIMM40–46°C, LAN59°C; CPU_FAN700rpm,
CHA_FAN1/2 700rpm, CHA_FAN6 1000rpm, SOC2500rpm y CHIPSET1200rpm.
Las lecturas numéricas citadas quedan por debajo de sus umbrales altos mostrados;
no se interpretan códigos discretos como prueba de entrenamiento o fallo.
Esto confirma respuesta de esa API autenticada y alimentación, **no POST,
UEFI operativo ni SO vivo**. Recibo privado
`post-fw-rollback-bmc-chassis-sensors-readonly.json`. Sin teclas, alimentación,
reset, logout, visor nuevo ni cambio de ISO; se cerró sólo el socket CDP propio.


## 12. Informe real de lectura: journal pendiente y contadores globales

**OBSERVADO20-10-2026,10:30:42 UTC:** consulta sudo del operador terminada0,
`READ_ONLY_CHECKS_COMPLETED`. SMART de187F y095A: critical_warning0,
media_errors0 y num_err_log_entries0; temperaturas308K/311K. El extracto kernel
contiene el arranque y no muestra I/O timeout ni reset fallido. Esto no excluye
fallos anteriores ni garantiza estabilidad futura del SSD.

La ejecución `e2fsck -f -n` también terminó0 y mostró las cinco pasadas, pero
advirtió que omitía recuperación del journal por ser una consulta de lectura:

```text
Warning: skipping journal recovery because doing a read-only filesystem check.
Free blocks count wrong (463783574, counted=463807698).
Fix? no
Free inodes count wrong (121891505, counted=121917075).
Fix? no
```

**Interpretación:** no hay prueba de EXT4 limpio. Estos son contadores globales;
las diferencias no son un recuento de archivos perdidos. La fuente upstream
v1.47.0 explica que pueden quedar desactualizados tras un desmontaje no limpio.
Además, esos dos problemas tienen `PR_NO_OK`, por lo que rechazarlos no marca
por sí solo el sistema como inválido y puede mantenerse rc0. No concluir
corrupción estructural definitiva antes de considerar el journal pendiente.
Fuentes: [unix.c](https://github.com/tytso/e2fsprogs/blob/v1.47.0/e2fsck/unix.c),
[problem.c](https://github.com/tytso/e2fsprogs/blob/v1.47.0/e2fsck/problem.c) y
[manual1.47.0](https://github.com/tytso/e2fsprogs/blob/v1.47.0/e2fsck/e2fsck.8.in).

**DISEÑO ANTERIOR, DESCARTADO sin ejecutarlo:** mantener origen desmontado, las cinco máscaras y Docker
inactivo; revalidar serie187F/UUID frente al SSD095A del SO, backups externos,
espacio, SMART/kernel y alimentación estable. El siguiente paso mínimo a valorar
es `e2fsck -p -E journal_only,nodiscard -z <undo>` offline, diseño elegido por
el agente principal después de revisar la exigencia TTY. **Escribe** transacciones
del journal y permite arreglos automáticos de su comprobación previa; no describirlo
como una operación sin reparaciones. Después, una nueva comprobación completa
`-f -n` y revisión de toda su salida. No añadir `-f` al replay, porque fuerza
la comprobación completa. Si persisten avisos tras replay correcto, evaluar
separadamente otra reparación; no ampliar a `-p` general o `-y`, ni reactivar
Docker por rc0. El helper/argv exactos siguen pendientes de revisión/despliegue.

**Gate de implementación:** con1.47.0, journal_only sin `-p/-n/-y` requiere TTY.
Un subproceso con stdinDEVNULL/stdout capturado aborta antes del replay: no es
un método de recuperación válido. No forzar interactividad mediante una variable
con stdin vacío: EOF puede tomar la respuesta predeterminada de un prompt.
Se descartó forzar interactividad y usar PTY; el diseño elegido añade `-p`
expresamente para admitir la ejecución no interactiva. `nodiscard` deshabilita
discard; `-p` permite autoarreglos y amplía las decisiones aceptadas, aunque
journal_only salte las pasadas normales. Hay un límite adicional en1.47.0:
`check_if_skip` retorna antes de comprobar JOURNAL_ONLY si existe
PROBLEMS_FIXED. Un arreglo previo puede marcarlo y hacer que se ejecuten más
pasadas; por tanto esa combinación no excluye técnicamente toda reparación
adicional en un journal anómalo. Exigir lectura previa completa sin anomalías
del journal, validar salida y documentar ese alcance antes de actuar. Detectar
Pass1 después de comenzar no garantiza que no haya escrituras anteriores.
Conservar stdout/stderr completos: un error de
checksum/corrupción del journal puede aparecer antes de un reinicio interno
del programa y no debe aceptarse por un código final0/1.

**Undo opcional, alcance limitado:** la revisión de la fuente1.47.0 demuestra que
`-z` instala undo_io antes de abrir el FS/replay y guarda los bloques originales
antes de escribir mediante fs->io. Para un journal interno esa ruta incluye el
replay; un journal externo abre un canal distinto, por lo que hay que verificar
su ausencia antes de atribuir cobertura completa. No equivale a una imagen
íntegra ni garantiza reversión tras caída de energía/sistema; el manual lo
advierte. No ejecutar e2undo automáticamente ni prometer rollback. Fuentes:
[journal.c](https://github.com/tytso/e2fsprogs/blob/v1.47.0/e2fsck/journal.c),
[undo_io.c](https://github.com/tytso/e2fsprogs/blob/v1.47.0/lib/ext2fs/undo_io.c) y
[util.c](https://github.com/tytso/e2fsprogs/blob/v1.47.0/e2fsck/util.c).

Evidencia privada: `ext4-postfirmware-independent-review/`, con copia del informe,
fuentes versionadas/hash y análisis de secuencia. Esta etapa sólo leyó el informe
por SSH y fuentes oficiales; no ejecutó reparación, montaje ni órdenes BMC/robot.


## 13. Recuperación offline estándar: diseño revisado y ya ejecutado

Tras revisar el alcance real de1.47.0, se descartó presentar journal_only como
barrera absoluta a reparaciones. El agente principal eligió preparar:

```text
e2fsck -p -E nodiscard,fixes_only,no_optimize_extents -z <undo-privado-en-SO> <partición-datos-validada>
```

**EJECUTADO por el operador,11:17:31 UTC; resultado en sección14.** El helper
`storage_offline_recovery.py --recover` y la receta `OFFLINE_RECOVERY.md`
conservan el diseño revisado. No repetir por volver a leer esta receta. No copiar este esquema con un /dev/nvme antiguo: resolver
serie187F/UUID, excluir095A/SO, comprobar desmontaje, máscaras/inactividad,
backups y salud nueva antes de la escritura. No `-y`, `-f`, `-c`, conversión,
montaje, reparación automática posterior ni arranque de Docker.

Según el manual1.47.0, `nodiscard` evita TRIM de bloques libres; `fixes_only`
limita a corregir metadatos dañados y excluye optimizaciones htree/extent y
conversiones bmap2extent; `no_optimize_extents` refuerza esa exclusión. Son
restricciones, no una modalidad de sólo lectura. `-p` aplica los arreglos que
preen considera automáticos y se detiene ante problemas que requieren intervención.
Puede haber escrito arreglos antes de detenerse: no es una transacción todo o nada.
Sin `-f` no se fuerza un recorrido completo si tras el replay el FS se considera
limpio; la consulta posterior completa `-f -n` seguirá siendo necesaria.
Fuente: [manual e2fsck1.47.0](https://github.com/tytso/e2fsprogs/blob/v1.47.0/e2fsck/e2fsck.8.in).

La salida completa debe acompañar al código. Sólo0/1 permiten evaluar el paso
siguiente, sin constituir por sí solos un gate limpio; cualquier otro bit, error
journal/checksum/I/O, salida truncada, fallo de guarda o desaparición del SSD
impide continuar y exige revisión. Mantener Docker apagado y sin reintentos.
Después, comprobar FS completo de lectura, SMART/kernel y guardas; la validez de
CVAT/DB sigue siendo una fase separada aunque e2fsck resulte limpio.

El undo se conserva en el SSD del SO, fuera del origen, con identidad/espacio y
permisos controlados. La reserva basada sólo en tamaño del journal no es una
cota válida para una reparación general de metadatos; se debe documentar el
margen como estimación y no prometer capacidad ni rollback garantizados.
No sustituye los backups ya verificados ni protege contra caída de alimentación.


## 14. Recuperación real verificada y próximo gate antes de Docker

**VERIFICADO20-10-2026:** el informe de preflight,11:17:25.898196 UTC, terminó
CHECK_READY_NO_WRITES; diagnóstico sin incidentes nuevos, identidad, backups,
journal interno y espacio comprobados. El informe de recuperación empieza a las
11:17:28.677850 UTC; su carpeta fsync se creó a las11:17:31 UTC:
`/root/app2-offline-recovery/20261020T111731Z-7r0y7atv`.

Se ejecutó una vez el argv de la sección13. Código0; salida recovering journal
y después clean,184553/122101760 files,24570022/488378368 blocks. Undo regular
`recovery.e2undo`,4.345.856bytes. La consulta posterior completa `e2fsck -f -n`
realizó las cinco pasadas con0, sin warning de journal omitido, sin diferencias
ni review_reasons. Guardas de origen desmontado/cinco máscaras/inactividad al
final PASS; SMART de ambos SSD con critical_warning0/media_errors0/
num_err_log_entries0 y sin errores nuevos observados en el extracto kernel.
Esto autoriza técnicamente valorar el siguiente montaje controlado, **no declara
Docker/CVAT comprobados ni elimina la vigilancia de estabilidad del SSD**.

Fuentes privadas leídas, no se repitieron consultas de salud:

| Informe | SHA256 |
| --- | --- |
| received-offline-preflight-20261020T1054Z.json | 890ad4d0328415e819146084a77a25d80f1d218cda74338ee44d32c7bd9e5fda |
| received-offline-recovery-20261020T1054Z.json | 35620e71eab15a2ef805a5ed3682a9b36e9ecc79dd96b265c56788629d611ade |

**SECUENCIA HISTÓRICA YA EJECUTADA, NO REPETIR:** se restauró el fstab original y sólo las máscaras
registradas usando `storage_maintenance.py --restore-config`. Ese helper verifica
hashes del fstab actual/preparado y original; si algo cambió, se detiene. No
borrar máscaras a mano ni sobrescribir otro fstab para evitar su rechazo.
No monta ni arranca servicios. Después, iniciar únicamente la unidad de montaje
y ejecutar el [checker de montaje](storage_mount_check.py), que no cambia nada.
Debe comprobar el destino exacto `/var/lib/docker`, UUID conocido, ancestry de
serie187F y SO095A, ext4/rw y dispositivo distinto del sistema raíz. Exige root
y valida además containers/overlay2/volumes y los veinte `_data` del recibo de
backup pinned3e497d85…7c4b3, sin symlinks ni otro filesystem. No crea datos ni
hashea los TAR grandes; `--help` no necesita root. Cuatro pruebas locales PASS
cubren montaje incorrecto/raíz/RO, volumen ausente, recibo alterado/symlink y
ayuda sin consultas/root requerido.

El checker y su dependencia base pinned se desplegaron y revisaron antes de
la ejecución del operador. La línea siguiente conserva la secuencia histórica,
ya completada; no ejecutarla de nuevo:

```bash
# HISTÓRICO: ya ejecutado y verificado; no repetir ahora.
sudo sh -c 'python3 /home/luisacuna/app2/maintenance/storage_maintenance.py --restore-config /root/app2-storage-maintenance/aisrv-7epmpnej && systemctl start var-lib-docker.mount && python3 /home/luisacuna/app2/maintenance/storage_mount_check.py --check && systemctl start containerd.service docker.service'
```

La cadena se detiene ante un fallo y sólo inicia containerd/Docker si el checker
termina correctamente. El agente principal autorizó este gate en la misma línea;
no requirió otra confirmación humana entre montaje y daemon. **EJECUTADA y
verificada:** montaje, checker20 y START pasaron; API, contenedores y CVAT se
comprobaron después, como registra la sección15. Docker inició los contenedores
por sus políticas existentes; no se activaron otros proyectos para esta validación.
La retirada de máscaras, montaje RW y START son cambios persistentes/operativos
que deben registrarse con resultado. No se consideran reversibles sin más si ya
se montó RW; si falla, conservar salida y revisar antes de repetir. No ejecutar
comandos Docker entre restaurar configuración y verificar el montaje, para evitar
una activación accidental sobre un directorio del SSD raíz. Fuente restauradora
local/servidor contrastada por el agente principal:
`storage_maintenance.py` SHA256
`f0b7c15750d088996f9e0c0a927dadee63ca485f2b5c7320731f3b058679dabf`.
La comprobación de montaje sólo lee y nunca emite START por sí misma.


## 15. Estado final: Docker/CVAT recuperados, retomar las anotaciones

**VERIFICADO20-10-2026,11:35–11:36 UTC:** el operador ejecutó la secuencia de
restauración de configuración, montaje, checker20 PASS y START. La consulta de
sistema11:35:02 UTC muestra Docker, docker.socket y containerd activos; montaje
exacto `/var/lib/docker` ext4/rw y cero unidades fallidas. Los veinte IDs
originales están presentes, sin faltantes/adicionales ni diferencias de
configuración; running y restart_count0. Son18 contenedores APP2/CVAT y2 Ollama.
No convertir running en una garantía de salud prolongada o de todos los endpoints.

La API y UI CVAT responden200, versión2.79.0. La comprobación11:35:56 UTC encuentra
cuatro tareas, cuatro jobs, nueve formas globales y el objeto shape10/frame1 en
job5. `head_raw.png` y `head_rgb.png` conservan dimensiones y SHA256 exactos de
los originales; no se trata sólo de que cargue la portada. A las11:36:53 UTC se
restauró el túnel SSH propio del PC a localhost18080 y se verificaron about y
la UI de job5 con200. La anotación humana puede retomarse en
`http://localhost:18080/tasks/5/jobs/5`.

Evidencia privada consultada localmente, sin nuevas acciones remotas en esta
actualización documental:

| Recibo | SHA256 |
| --- | --- |
| docker-activation-system-readonly.json | 4cf732ec977574fa3280d46f79cf755a93f8b57823f53225639e55c9469e6733 |
| docker-post-start-compare-20261020T113508Z.json | 2ed036af14d9223b10c11cb958f3f4dd756e9785b6ceceb94b629b694bbf6fd0 |
| cvat-post-recovery-api-media.json | 198173a091bd89c50addc509e7ab3b3cd8dcaa6dddbc1bc1dfa820d00085f780 |
| pc-cvat-tunnel-restored.json | 7242b5b6093e497dae07687bf25abd3cacde203d9846b9a1897b7827466383ec |

**Punto de reanudación:** anotación/revisión humana de las piezas de APP2 y
vigilancia de fiabilidad del almacenamiento. Conservar backups de datos/capas,
undo y evidencia externa; no borrar el rescate por haber recuperado la aplicación.
No hay sudo pendiente, ni debe repetirse firmware, CSM, BootNext, e2fsck,
restore-config, montaje o START por leer las recetas históricas. Una consulta
puntual correcta no demuestra que el SSD no vuelva a fallar. Si aparecen nuevos
errores, registrar el contexto y revisar el incidente sin lanzar reparaciones
sobre un filesystem activo.
