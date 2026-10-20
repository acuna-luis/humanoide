# APP2 — preparar la actualización del Samsung 990 PRO

**ID:** APP2-FIRMWARE-PREP-20261020. **Fecha/zona:** 20-10-2026, Europe/Madrid.
**Estado:** ISO oficial descargada e inspeccionada estáticamente en el PC;
firmware **NO APLICADO**. No se ha accedido al servidor desde esta preparación,
ejecutado software del proveedor, escrito un USB ni modificado BIOS o BMC.

Esta receta acompaña al [incidente de almacenamiento](../../../docs/incidents/2026-10-20_APP2_SSD_DOCKER_NO_RESPONDE.md).
Consultar allí el estado vigente de las copias y servicios antes de actuar.
La actualización se prepara después de rescatar y verificar los datos que se
quieran conservar; no demuestra ni repara por sí sola la integridad de EXT4/CVAT.

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

**UEFI, Secure Boot y arranque real siguen PENDIENTES.** No extraer el actualizador
para ejecutarlo por SSH, parchearlo, instalarlo en Ubuntu o cargar el `.enc` con
`nvme fw-download` a partir de esta inspección. Tampoco usar `dd` suponiendo que
la estructura híbrida resuelve todos los modos de arranque.

## 4. Método del fabricante y requisitos para la aplicación posterior

El [manual Samsung enlazado actualmente](https://semiconductor.samsung.com/resources/user-manual/Firmware_Update_Utility_UserManual.pdf)
es de mayo de 2019, con portada rev3.2 y páginas rev3.1. Describe crear USB con
**UNetbootin → Diskimage → ISO → USB identificado**, reiniciar desde él y seguir
la utilidad interactiva. Pide copia previa y alimentación estable; no define
compatibilidad UEFI/Secure Boot. No se ha creado ese medio en esta intervención.

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
CSM cambia la salida primaria al VGA de placa (p69). No se ha comprobado la
configuración real de BIOS1602; no activar CSM a distancia sin consola probada.

Hay indicios reales de BMC: `/dev/ipmi0`, sysfs y módulos IPMI presentes según
`rescue-tools-readonly.json`; `ipmitool` no está instalado. Falta verificar LAN,
acceso, credenciales, consola y medio virtual. La presencia del dispositivo no
garantiza esas funciones. No se ha instalado ni configurado BMC aquí.

Con sólo SSH **sí se puede continuar el rescate y la validación de los datos**.
La escritura de firmware queda pendiente de resolver esa consola y el arranque,
sin reiniciar automáticamente para probar.

## 5. Verificación posterior prevista

Una vez aplicado de forma controlada, guardar el resultado de la utilidad y
releer serie, firmware, SMART, error-log y kernel después de arrancar Ubuntu.
Comparar especialmente el SSD187F y comprobar que el SO095A sigue como estaba.
Restaurar sólo las opciones de arranque que se hubieran cambiado y conservar
las protecciones de Docker hasta validar copias y sistema de archivos. Registrar
por separado firmware instalado, arranque probado, datos restaurables y
estabilidad observada; ninguna de esas verificaciones sustituye las otras.
