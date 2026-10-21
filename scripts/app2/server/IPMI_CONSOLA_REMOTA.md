# APP2 — consultar el BMC con herramientas IPMI aisladas

**ID:** APP2-IPMI-PREP-20261020. **Fecha/zona:** 20-10-2026, Europe/Madrid.
**Estado:** paquete aislado **desplegado y comprobado** después del backup;
`--check`, información de canal 1 y lectura LAN1 verificadas. No se instalaron
paquetes, servicios, firmware ni configuración BMC.
El objetivo es consultar si ya existe una vía de consola remota; tener una IP
no demuestra acceso, credenciales, KVM ni medio virtual funcionales.

**Actualización 20-10-2026:** el agente principal conservó la transferencia y los
hashes del paquete en `ipmi-readonly-stage.json`; `ipmi-readonly-check.json`
confirma `CHECK_OK_NO_BMC_CALL`. La consulta del operador en
`ipmi-channel1-query.json` devuelve canal 1 `802.3 LAN`, IP estática
`192.168.1.34/24` y gateway `192.168.1.251`, sin modificar esos parámetros.
Se conservan avisos de registro IANA ausente, `Get Device ID` fallido con `0x53`
y respuesta con ID inesperado 0 frente a 1; el informe LAN llegó completo. No dar por
validada la ausencia de errores del protocolo a partir de esa lectura.

`bmc-web-readonly.json` verifica puerto 443 accesible, TLS 1.3 y HTTP 200 en
`https://192.168.1.34/`, sin intentos de autenticación; puerto 80 agotó su espera.
Credenciales, inicio de sesión, KVM y Virtual Media siguen **PENDIENTES**.
Estas cuatro evidencias están en la carpeta de intervención
`20261020T061422Z_APP2_RESUME_READONLY`, junto a `ipmi-preparation`.

**Actualización de arranque y acceso:** `firmware-boot-mode-readonly.json`
(08:24:51 UTC) confirma UEFI de 64 bits y `SecureBoot disabled` mediante lectura
del SO, sin cambiar BIOS; no prueba el arranque UEFI de la ISO Samsung.
El operador no conoce las credenciales actuales. La
[FAQ oficial ASUS de esta placa](https://servers.asus.com/support/faq/detail/1047906)
documenta credencial inicial `admin`/`admin`, no comprobada en esta unidad.
Se ha pedido al operador **un único intento manual en el navegador**; su resultado
sigue pendiente. No se han hecho intentos automatizados, resets ni cuentas nuevas.

## 1. Por qué no se instala el paquete con APT

La simulación del servidor propone tres paquetes nuevos, sin actualizaciones:

| Paquete | Versión preparada |
|---|---|
| ipmitool | `1.8.19-7ubuntu0.24.04.3` |
| libfreeipmi17 | `1.6.13-3ubuntu0.2` |
| freeipmi-common | `1.6.13-3ubuntu0.2` |

Se descargaron los `.deb` oficiales de `https://archive.ubuntu.com/ubuntu/` en el
PC; tamaños y SHA256 coinciden con `apt-cache show` del servidor. La inspección
de `postinst` descubre una llamada a **iniciar `ipmievd.service`**. Su unidad
ejecuta un daemon de eventos y no comprueba `/etc/default/ipmievd`.
Por tanto, `--no-install-recommends` no basta para evitar ese arranque.
Aquí se descarta la instalación, sin crear máscaras o políticas nuevas.

La alternativa preparada contiene sólo el ejecutable `ipmitool`, su biblioteca
`libfreeipmi.so.17`, licencias, procedencia y el wrapper
[`ipmi_readonly.py`](ipmi_readonly.py). No contiene `ipmievd`, unidades, scripts de
inicio ni scripts de mantenimiento de paquetes. La biblioteca se guarda como
archivo regular bajo su SONAME para evitar enlaces a ubicaciones externas.

La evidencia privada está en:

```text
../Humanoide-vla-evidence/20261020T061422Z_APP2_RESUME_READONLY/ipmi-preparation/
```

Incluye los `.deb` originales, metadatos/cabeceras/checksums, scripts inspeccionados,
inventario ELF, lecturas del host y el paquete mínimo. No añadir binarios a Git.

## 2. Qué está comprobado y qué falta

Por lectura: servidor `aisrv`, Ubuntu24.04/x86_64, glibc2.39; cargador
`/lib64/ld-linux-x86-64.so.2` y dependencias de host requeridas presentes.
`ldconfig -p` sólo se utilizó para consultar su caché, sin modificarla.
Los hashes de esas bibliotecas se conservan como observación fechada.
En la preparación previa no se ejecutaron `ldd` ni el ejecutable en el servidor.
Después del despliegue se realizaron las consultas del wrapper descritas arriba;
no se ha ejecutado `ldd` sobre el paquete.

`/dev/ipmi0`, sysfs y módulos IPMI existen. El BMC informó IPMI2.0/firmware1.32
en la consulta del agente principal. `ipmievd.service` e `ipmi.service` aparecen
`not-found`/`inactive` en la lectura previa. Ningún resultado garantiza todavía
consola, conexión de su interfaz de red o disponibilidad de credenciales.

## 3. Preparación reproducible del contenido mínimo

En una carpeta nueva y privada del PC, verificar primero tamaño/hash de los
`.deb` contra `download-manifest.json`. Estos comandos extraen bytes sin ejecutar
sus scripts; requieren los paquetes exactos de la tabla:

```bash
set -o pipefail
umask 077
mkdir -m 700 ipmi-readonly-tools
mkdir -m 700 ipmi-readonly-tools/bin ipmi-readonly-tools/lib
dpkg-deb --fsys-tarfile ipmitool_1.8.19-7ubuntu0.24.04.3_amd64.deb \
  | tar --extract --to-stdout --file=- ./usr/bin/ipmitool \
  > ipmi-readonly-tools/bin/ipmitool
dpkg-deb --fsys-tarfile libfreeipmi17_1.6.13-3ubuntu0.2_amd64.deb \
  | tar --extract --to-stdout --file=- ./usr/lib/x86_64-linux-gnu/libfreeipmi.so.17.2.12 \
  > ipmi-readonly-tools/lib/libfreeipmi.so.17
sha256sum ipmi-readonly-tools/bin/ipmitool ipmi-readonly-tools/lib/libfreeipmi.so.17
```

Hashes esperados:

```text
37910be2ba09a7effcfac016e601d54f69396b925584f871a475ae41b814fd61  bin/ipmitool
57db493603d605a684006438177d5630176d86dfa7775d3ba605736527fbfe08  lib/libfreeipmi.so.17
```

Incluir también el wrapper versionado, licencias y manifiestos del paquete
preparado; revisar su hash de fuente antes de usar `sudo`. El agente principal
ya revisó y transfirió esta instantánea, con hash y permisos contrastados.
Destino comprobado, en el disco del SO sano y sin enlaces simbólicos:
`/home/luisacuna/app2/maintenance/ipmi-readonly-tools`.
Directorios0700 y archivos0600; no añadir esa biblioteca a `ldconfig` ni al sistema.
El README del paquete conserva la instantánea de preparación anterior al
despliegue; este documento incorpora los resultados posteriores sin cambiar
el paquete ya verificado.

## 4. Consultas posteriores permitidas

El check y las consultas de canal1/LAN1 ya se realizaron. Las órdenes siguientes
se conservan como receta de repetición controlada; `--mc-info` y canal8 permanecen
**PENDIENTES**, sin necesidad de ejecutarlos si no aportan un dato necesario:

```bash
python3 /home/luisacuna/app2/maintenance/ipmi-readonly-tools/ipmi_readonly.py --check
sudo python3 /home/luisacuna/app2/maintenance/ipmi-readonly-tools/ipmi_readonly.py --mc-info
sudo python3 /home/luisacuna/app2/maintenance/ipmi-readonly-tools/ipmi_readonly.py --channel-info 1
sudo python3 /home/luisacuna/app2/maintenance/ipmi-readonly-tools/ipmi_readonly.py --channel-info 8
```

Consultar LAN sólo para un canal que informe medio `802.3 LAN`:

```bash
sudo python3 /home/luisacuna/app2/maintenance/ipmi-readonly-tools/ipmi_readonly.py --lan-print 1
# Alternativa únicamente si el canal 8 resulta LAN:
sudo python3 /home/luisacuna/app2/maintenance/ipmi-readonly-tools/ipmi_readonly.py --lan-print 8
```

El wrapper valida host, ruta privada, hashes y argumentos de lista cerrada.
Invoca el cargador absoluto con `--library-path` privado, entorno limpio y
timeout15s; fija `-I open -d 0`, sin conexión IPMI por red ni contraseña.
`--check` sólo comprueba archivos/host y no llama al BMC.
Redacta la comunidad SNMP que puede aparecer en `lan print`.

Estos subcomandos muestran información del controlador, canal y configuración
LAN según el [manual de ipmitool](https://manpages.ubuntu.com/manpages/jammy/man1/ipmitool.1.html).
Las opciones de escritura, usuarios, resets, alimentación y `raw` no están
expuestas. Si no hay información suficiente, se conserva el resultado; no hay
comando de escritura de recuperación ni pruebas de credenciales en el wrapper.
El intento manual inicial documentado arriba es una etapa separada y acotada,
sin autorizar ensayos masivos o recuperación de acceso por cambios del BMC.

Guardar la salida en evidencia privada. Una vez conocida una IP, comprobar
acceso/consola con las credenciales autorizadas en una etapa separada. No cambiar
LAN o usuarios, iniciar KVM/medio virtual, reiniciar BMC/servidor ni actualizar
firmware desde esta receta. Las copias de datos continúan siendo la prioridad.
