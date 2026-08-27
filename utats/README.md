# Paquete local UTATS para teleoperación

Este directorio contiene el material suministrado para preparar la
teleoperación del Cruzr S2 con PICO 4 Ultra Enterprise. Los instaladores y el
PDF no se versionan por su tamaño; este índice permite saber qué debe estar
presente y para qué sirve cada elemento.

## Inventario esperado

| Archivo | Versión | Uso |
|---|---:|---|
| `XRoboToolkit-PICO-1.1.1.apk` | 1.1.1 | Aplicación XR del PICO |
| `QuestTool_v3.5.3.apk` | 3.5.3 | Utilidad auxiliar del visor |
| `XRoboToolkit_PC_Service_1.0.0_ubuntu_22.04_amd64.deb` | 1.0.0 | Servicio XR para Ubuntu 22.04 |
| `XRoboToolkit_PC_Service_1.0.0_ubuntu_24.04_amd64.deb` | 1.0.0 | Servicio XR para Ubuntu 24.04 |
| `ubt_controller_4.7.0_ubuntu22.04_amd64.deb` | 4.7.0 | Controller entregado por UBTECH para robot v0.2.0 |
| `ubt_controller_5.3.0_ubuntu22.04_amd64.deb` | 5.3.0 | Puente de datos/control del robot |
| `ubt-remote-control_4.1.0_amd64.deb` | 4.1.0 | Interfaz de teleoperación del PC |
| `usb_driver.zip` | suministrado | Recurso auxiliar USB |
| `Utars…SOP-2.pdf` | julio de 2026 | SOP de teleoperación suministrado |

Use exclusivamente el paquete que corresponda a la versión real de Ubuntu.
No instale a la vez los servicios XR para 22.04 y 24.04.

## Orden de instalación resumido

1. Confirmar que el robot usa la configuración v0.2.0 compatible y realizar
   una copia de seguridad de mapas, puntos, configuración y `HW_TYPE`.
2. Preparar un PC de datos con Ubuntu 22.04 o posterior, Chrome actualizado,
   ADB y Ethernet directa al robot.
3. Instalar en el PICO 4 Ultra Enterprise `XRoboToolkit-PICO-1.1.1.apk`.
4. Instalar en el PC una sola variante de `XRoboToolkit_PC_Service`.
5. Emparejar versiones antes de instalar: para el robot genérico v0.2.0
   UBTECH indicó `ubt_controller` 4.7.0 + `ubt-remote-control` 4.1.0. No usar
   5.3.0 sin el robot/plataforma DAC compatible.
6. Configurar el robot con `TELE_DEVICE=pico` y el transporte adecuado.
7. Verificar primero conectividad y teleoperación sin grabar; después hacer
   una grabación piloto y auditar su exportación.

La secuencia completa, la configuración y los criterios de calidad están en
[`docs/vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md`](../docs/vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md).

## Configuración observada del controlador

Los paquetes 4.7.0 y 5.3.0 instalan `ubt-controller.service`, descrito como
backend para datos de VR, exoesqueleto y guantes. El 26-08 quedó instalado
4.7.0: DEB SHA-256 `4f2b728b689175867ff345bec3e30f319fe7d8567d9e08985aa48a2b67bad61c`
y ejecutable vendor
`e88b83b7936a13f5fb71b99416e0d6bcc844b9361524ef709f87fd04ed449d16`.
La configuración suministrada usa, entre otros, estos campos:

```json
{
  "transmit": "local",
  "signal_server_url": "ws://192.168.11.3:4000",
  "push_rate": 90,
  "control_device": "pico",
  "enable_adb_reverse": 1
}
```

`push_rate=90` describe el envío del controlador XR. No demuestra que el
dataset final tenga 90 FPS ni debe sustituir la inspección de timestamps,
imágenes y acciones exportadas.

La matriz del proveedor etiqueta v0.2.0 + 4.7.0 como `只支持遥操作` (“sólo
teleoperación”), mientras que en la reunión del 26-08 UBTECH afirmó que 4.7.0
sí recopilará datos del robot. Se mantiene como PENDIENTE determinar si esto
significa captura local de episodios sin la plataforma central de 5.3.0 y
auditar una exportación real.

## Seguridad y trazabilidad

- No guarde contraseñas en este directorio ni en Git.
- Conserve el hash SHA-256 y el origen de cada instalador en el registro de la
  sesión.
- No ejecute aplicaciones o servicios manualmente si el SOP indica que deben
  ser administrados por systemd o por la interfaz del proveedor.
- Estos binarios son dependencias externas; deben recuperarse del canal
  autorizado del proveedor si se clona el repositorio en otro equipo.
