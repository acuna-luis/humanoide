# PICO por Wi-Fi, con Ethernet entre PC y robot

16-10-2026, Europe/Madrid. Adaptación `PICO-WIFI-MIGRATION-20261016`.

La conexión inalámbrica del visor es independiente del enlace PC → robot.
Mantener Ethernet `eno1` para Motion/Vision. Las gafas y el adaptador Wi-Fi
del PC deben estar en la misma red local.

## Direcciones verificadas en esta sesión

| Uso | Dirección |
| --- | --- |
| Red Wi-Fi del visor y PC | Cruzr S2-0669 |
| PC para «PC service IP» en XRoboToolkit | 192.168.42.215 |
| PICO por Wi-Fi | 192.168.42.211 |
| PC → robot por Ethernet eno1 | 192.168.11.250 |
| Motion / Vision | 192.168.11.2 / 192.168.11.3 |

Las IP Wi-Fi son concesiones DHCP observadas, no valores fijos. Descubrirlas
de nuevo al cambiar de red o sesión. `127.0.0.1` corresponde al túnel USB y no
sirve como destino del servicio PC al retirar ese cable.

## 1. Preparar seguimiento sin movimiento

Con la sesión de control en STOP, conectar las gafas a Cruzr S2-0669. En
XRoboToolkit, introducir `192.168.42.215`, Connect, Head + Controllers y Send
data. Mantener el visor puesto. Dejar Hands óptico desmarcado y los mandos
libres; no pulsar Y. Remote Vision puede permanecer cerrado durante esta fase.

Desde el PC, comprobar:

```bash
ip -4 route get 192.168.11.2
ip -4 route get 192.168.42.211
ss -Htn 'sport = :63901'

PICO_EFFECTOR=v4 PICO_TELEOP_CAMERA=off PICO_PC_IP=192.168.42.215 \
CRUZR_IFACE=eno1 CRUZR_PC_IP=192.168.11.250 \
bash scripts/teleoperation/cruzr_pico_teleop_pc.sh --check
```

Este `--check` es pasivo, no START. Usa cámara off sólo para comprobar XR
cuando aún no hay ADB inalámbrico. Exige identidad del visor en el backend,
peer TCP, tracking `vr_status=1` y STOP. No demuestra disponibilidad de vídeo
ni autoriza un movimiento posterior.

El descubrimiento ignora sockets USB que siguen ESTAB en el kernel aunque su
dirección local ya no esté asignada. También respeta `PICO_PC_IP` y `PICO_IP`
al buscar entre todos los peers, conservando identidad y tracking exigidos.

## Prueba elegida: sin cámara y sin USB

El operador ha elegido esta variante y confirma haber cerrado la sesión previa
con STOP. No necesita ADB ni volver a conectar USB. Mantener el visor puesto:
una conexión TCP y la pantalla Working no sustituyen tracking `vr_status=1`.
La comprobación posterior encontró `vr_status=0`; reactivar Head + Controllers
y Send data antes de continuar.

Primero, comprobación sin movimiento:

```bash
PICO_TELEOP_CAMERA=off PICO_PC_IP=192.168.42.215 \
CRUZR_IFACE=eno1 CRUZR_PC_IP=192.168.11.250 \
bash scripts/teleoperation/probar_pico_v4.sh --check
```

Cuando el check pase y con las condiciones físicas actuales comprobadas,
el operador puede iniciar desde su terminal:

```bash
PICO_TELEOP_CAMERA=off PICO_PC_IP=192.168.42.215 \
CRUZR_IFACE=eno1 CRUZR_PC_IP=192.168.11.250 \
bash scripts/teleoperation/probar_pico_v4.sh --teleoperate
```

El lanzador conserva identidad del visor, tracking, perfil v4 y condiciones
físicas. Pulsar Y únicamente al aviso del script y observar directamente el
robot durante esta prueba sin imagen remota. No se inició movimiento desde
el agente. Los pasos de ADB/cámara siguientes son opcionales para otra prueba.

## 2. Preparar ADB Wi-Fi para el lanzador con cámara

El lanzador habitual mantiene ADB obligatorio cuando se solicita cámara. Para
configurarlo, puede ser necesario conectar USB brevemente y retirarlo después.
No cambiar la dirección del servicio XR ni activar control durante este paso.

```bash
adb devices -l
adb -s PA94Y0MGKB070822G shell getprop ro.serialno
adb -s PA94Y0MGKB070822G shell ip -4 address show wlan0
```

Verificar el serial físico esperado y la IP actual. Con backend en STOP:

```bash
adb -s PA94Y0MGKB070822G tcpip 5555
adb connect 192.168.42.211:5555
adb -s 192.168.42.211:5555 shell getprop ro.serialno
```

Esto reinicia sólo el transporte ADB, no el robot ni sus controladores. Después
retirar USB y repetir la consulta de serial por `IP:5555`; debe seguir dando
`PA94Y0MGKB070822G`. Una conexión válida antes de retirar el cable no demuestra
que vaya a persistir después. Si el puerto se cierra, el vídeo integrado sigue
bloqueado: no omitir ADB ni confundir tracking Wi-Fi con ADB disponible.

## 3. Comprobar y probar vídeo inalámbrico

Con ADB Wi-Fi válido, el siguiente check consulta el perfil cargado y los
estados requeridos sin activar movimiento:

```bash
PICO_TELEOP_CAMERA=main PICO_ADB_TARGET=192.168.42.211:5555 \
PICO_PC_IP=192.168.42.215 PICO_CAMERA_PICO_IP=192.168.42.211 \
CRUZR_PICO_CAMERA_LAYOUT=mono-sbs-zed \
CRUZR_IFACE=eno1 CRUZR_PC_IP=192.168.11.250 \
bash scripts/teleoperation/probar_pico_v4.sh --check
```

Prueba únicamente de vídeo, sin movimiento:

```bash
PICO_ADB_TARGET=192.168.42.211:5555 \
bash scripts/teleoperation/cruzr_pico_camera.sh --run \
  --camera main --pico-ip 192.168.42.211 --layout mono-sbs-zed
```

En Remote Vision seleccionar ZEDMINI y abrir Listen una sola vez, confirmando
la IP **Wi-Fi del PC: 192.168.42.215**. Si la ventana ya está preparada,
mantenerla abierta; no alternar Listen repetidamente. No pulsar Y en esta
prueba. Comparar también retraso y cortes, porque Wi-Fi puede cambiar la
latencia respecto a USB. El relay realiza la única conexión a 12345; no usar
netcat/curl ni un sondeo TCP de ese puerto para comprobarlo.

Terminar la prueba independiente con Ctrl+C en su terminal propietaria antes
de abrir teleoperación. No mantener dos relays de vídeo simultáneos.

## 4. Teleoperación posterior con vídeo

Sólo después de comprobar las condiciones físicas actuales mediante el
procedimiento habitual y con el perfil v4 adecuado cargado:

```bash
PICO_TELEOP_CAMERA=main PICO_ADB_TARGET=192.168.42.211:5555 \
PICO_PC_IP=192.168.42.215 PICO_CAMERA_PICO_IP=192.168.42.211 \
CRUZR_PICO_CAMERA_LAYOUT=mono-sbs-zed \
CRUZR_IFACE=eno1 CRUZR_PC_IP=192.168.11.250 \
bash scripts/teleoperation/probar_pico_v4.sh --teleoperate
```

Este comando puede activar movimiento tras las confirmaciones y Y. La prueba
de transporte no sustituye sus gates. El perfil y los límites no se cambian
al pasar de USB a Wi-Fi. No se ha ejecutado este comando en la migración.

## Reversión y evidencia

### Retorno USB sin cámara, verificado el 16-10-2026

El operador volvió a USB y reconectó Ethernet al robot. Se verificaron túnel
ADB63901, seguimiento loopback127.0.0.1/vr_status1 y check v4 completo rc0,
sin START. Para este modo, usar `127.0.0.1` en PC service IP de XRoboToolkit,
visor puesto, Head+Controllers/Send y USB conectado. La dirección Wi-Fi .42.215
de la receta anterior no se usa como destino XR en este modo.

Comprobación sin movimiento:

```bash
PICO_TELEOP_CAMERA=off PICO_PC_IP=127.0.0.1 \
CRUZR_IFACE=eno1 CRUZR_PC_IP=192.168.11.250 \
bash scripts/teleoperation/probar_pico_v4.sh --check
```

Lanzamiento por el operador, con las confirmaciones físicas del script:

```bash
PICO_TELEOP_CAMERA=off PICO_PC_IP=127.0.0.1 \
CRUZR_IFACE=eno1 CRUZR_PC_IP=192.168.11.250 \
bash scripts/teleoperation/probar_pico_v4.sh --teleoperate
```

Pulsar Y sólo al aviso. No se ejecutó --teleoperate durante la configuración.
Evidencia `../Humanoide-vla-evidence/20261016T102402Z_PICO_USB_RETURN/`.

### Cambiar el transporte de nuevo

Para volver a USB, confirmar STOP, reconectar el cable y seguir
`configure_pico_xr_usb.sh --configure`, restableciendo `127.0.0.1` en la
aplicación. La cámara USB necesita además su forward según la guía PICO.
No restaurar una sesión transitoria de control. Para deshabilitar ADB TCP,
con USB conectado y autorizado:

```bash
adb -s 192.168.42.211:5555 usb
adb disconnect 192.168.42.211:5555
```

Si ADB Wi-Fi ya no existe, seleccionar el dispositivo USB real para `adb usb`.
Reversión del código PC: restaurar selectivamente `discover_pico_stream` desde
el respaldo, preservando cambios posteriores; los sockets obsoletos no se
eliminan ni se usan como prueba de seguimiento.

Evidencia privada: `../Humanoide-vla-evidence/20261016T100303Z_PICO_WIFI_MIGRATION/`.
Seguimiento Wi-Fi y ruta Ethernet VERIFICADOS; ADB inalámbrico/vídeo/ensayo
físico PENDIENTES al preparar esta receta. Última lectura: backend STOP, tracking
inactivo y ADB ausente; ponerse el visor y reactivar envío antes del siguiente
check. No se modificó la red del PC o robot.
