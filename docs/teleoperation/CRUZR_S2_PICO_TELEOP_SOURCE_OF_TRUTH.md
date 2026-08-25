# Cruzr S2 + PICO: fuente de verdad de teleoperación

**Última actualización:** 25 de agosto de 2026<br>
**Estado del documento:** operativo y en evolución<br>
**Plataforma:** Cruzr S2 con abrazaderas, PICO 4 Ultra Enterprise y PC Ubuntu<br>
**Responsable de actualización:** registrar aquí cada cambio antes de reanudar una prueba física

Este documento conserva el estado real de la integración de teleoperación. Su
objetivo es que el trabajo pueda detenerse y reanudarse sin repetir pruebas,
perder hallazgos ni confundir una capa que funciona con el sistema completo.
Es la fuente de verdad para la conexión **PICO → PC → robot**. La guía de
captura, dataset y VLA sigue estando en
[`../vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md`](../vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md).

> **Relevo vigente (25-08-2026):** la prueba física PICO movió el brazo y el
> STOP dejó el backend desarmado. Para abandonar `TeleopMode` fue necesario
> seleccionar `auto_task` explícitamente; después `cruzr/home` terminó, pero
> el operador observó que las abrazaderas orientadas hacia abajo pasaron casi
> rozando durante la interpolación directa. Desde este hallazgo los scripts
> usan la tarea v0.2.0 `cruzr/open_arm_before_home`, que separa primero los
> brazos y luego completa home. Esta nueva secuencia está validada sólo de
> forma estructural y todavía requiere una prueba física supervisada. El backend y
> `RoboticsServiceProcess` están activos y la UI permanece cerrada. El último
> snapshot de las 11:53 fue seguro: `vr_status=1`, `operation_type=1` y
> `enable_control=0`; HEAD+CONTROLLERS usa TCP directo por la WLAN local
> `Cruzr S2-0669`, sin ADB reverse. Motion quedó en `CoreMode 0` /
> `NotTele`; no se releyó el selector web. La unidad systemd sigue habilitada. El
> último preflight físico anterior detectó el cargador conectado; el estado
> físico actual debe
> verificarse de nuevo y nunca inferirse de este texto. El 25 de agosto el
> propietario autorizó explícitamente ampliar sólo el timeout del watchdog de
> heartbeat del backend de 10 a 300 s para una ventana diagnóstica. No se
> fabrica ni se da por recibido el heartbeat y el STOP al vencer permanece.
> El binario está cargado en el backend. En runtime sostuvo unos 46,1 s de
> enable sin el trip anterior de 10 s; no se ensayó el vencimiento de 300 s ni
> se completó la ventana de 60 s porque pulsaciones repetidas deshabilitaron la
> sesión. Para
> el historial anterior, véase
> [`CRUZR_S2_PICO_TELEOP_HANDOFF_2026-08-24.md`](CRUZR_S2_PICO_TELEOP_HANDOFF_2026-08-24.md).

## 1. Convenciones de evidencia

Cada afirmación importante usa una de estas categorías:

- **VERIFICADO:** comprobado directamente mediante archivos, procesos, red,
  topics, logs o hashes.
- **OBSERVADO:** visto durante una prueba, aunque no se conozca aún toda la
  causa interna.
- **INFERENCIA:** explicación que encaja con la evidencia, pero requiere
  confirmación del proveedor o una prueba adicional.
- **PENDIENTE:** no probado o no documentado por DSA.
- **DESCARTADO:** una hipótesis o workaround que la evidencia ya contradice.

Una pantalla verde `Working`, un proceso activo o un topic existente sólo
certifican su propia capa. No equivalen a “teleoperación lista para mover”.

## 2. Resumen ejecutivo del estado actual

| Capa | Estado | Evidencia resumida |
|---|---|---|
| PICO físico y red | **VERIFICADO EN WLAN LOCAL** | PICO `192.168.42.211` y PC secundario `192.168.42.215` en `Cruzr S2-0669`; IP por DHCP, redescubrir |
| Aplicación XR del PICO | **CONECTADA; `vr_status=1`** | HEAD+CONTROLLERS/Working y TCP directo a `192.168.42.215:63901` |
| Servicio XR del PC | **ACTIVO** | `RoboticsServiceProcess` y listener TCP 63901; peer directo `192.168.42.211`; reverse vacío |
| Backend UBT del PC | **ACTIVO Y DESARMADO; TIMEOUT 300 S** | SHA-256 `5083e9f0…`; TCP 8082; `operation_type=1`, `enable_control=0`; UI inactiva |
| Wi-Fi PC ↔ robot | **VERIFICADO Y CANÓNICO** | `Cruzr S2-0669`, PC `.42.215`, gateway `.42.2` y ruta persistente hacia `.11.0/24`; Motion `.2` y Vision `.3` accesibles sin Ethernet |
| Configuración de efector | **VERIFICADO EN ROBOT Y PC** | `HW_TYPE=cruzr_s2_v1`; backend PC fijado a `arm=clamp` |
| Configuración PICO del robot | **VERIFICADO** | `TELE_DEVICE=pico`, `transmit=local` |
| Tarea Cruzr/PICO correcta | **VERIFICADO** | `teleoperation/cruzr_clamp_pico_teleoperation` |
| Modo robot/web | **MOTION `NotTele`; SELECTOR WEB PENDIENTE** | tras STOP quedó `CoreMode 0`; durante la prueba sí entró en `CoreMode 7`, pero no se releyó el selector web |
| Señalización y DataChannel | **VERIFICADO** | DataChannel llegó a estado abierto durante diagnóstico |
| Flujo XR hacia el robot | **VERIFICADO** | El robot registró recepción de tele-data y habilitación temporal |
| Botón de habilitación | **FLANCO AISLADO VALIDADO; E2E PENDIENTE** | el backend anterior de nivel repetía Y cada ~0,5 s; el activo emite sólo el flanco ascendente y pasó el test aislado |
| Heartbeat de aplicación robot → PC | **FALLA REPRODUCIDA; TIMEOUT 300 S VALIDADO PARCIALMENTE EN RUNTIME** | sostuvo enable ~46,1 s sin trip de 10 s; no corrige el origen ni se probó el vencimiento a 300 s |
| Teleoperación sostenida | **PARCIAL: ~46 S; GATE DE 60 S INCOMPLETO** | terminó por tres pulsaciones adicionales, no por heartbeat |
| Movimiento físico mediante PICO | **VERIFICADO EN PRUEBA MÍNIMA** | el brazo siguió el PICO; grip exclusivo y STOP al soltar/fallar; no extrapolar a recorridos mayores |
| Grabación de episodios con `B` | **PENDIENTE** | No existe aún exportación auditada extremo a extremo |
| PICO directo al robot sin PC | **NO IMPLEMENTADO EN EL MATERIAL INSPECCIONADO** | la web viva sólo cambia el modo; no contiene discovery, tracking ni transporte PICO |

Estado consolidado tras las sesiones del 24 y 25 de agosto:

- PICO, PC Service, backend, señalización y DataChannel llegaron a enlazarse;
- no se obtuvo una teleoperación física sostenida por el fallo de heartbeat;
- por autorización explícita del propietario se instaló en el PC un timeout
  temporal de 300 s, conservando la misma ruta STOP; sostuvo enable unos
  46,1 s sin el trip anterior, pero no se validó su vencimiento;
- la primera recuperación usó `127.0.0.1:63901` y ADB reverse; después PC y
  PICO se asociaron a `Cruzr S2-0669` y XRoboToolkit descubrió
  `192.168.42.215`, abrió TCP directo y permitió retirar el reverse;
- el selector web `遥操模式` se verificó, pero no crea la conexión PICO;
- la prueba mínima produjo movimiento físico; después el STOP del PC no sacó
  por sí solo al robot de `TeleopMode`, por lo que se seleccionó `auto_task`;
- `cruzr/home` terminó, pero la vuelta directa casi hizo rozar las abrazaderas
  bajas; el flujo queda corregido para usar `cruzr/open_arm_before_home` y su
  apertura previa, aún pendiente de validación física;
- la web se devolvió manualmente a `JoystickMode`;
- el cliente de teleoperación del PC se detuvo por completo para evitar dos
  clientes sobre el mismo canal;
- el robot conserva `HW_TYPE=cruzr_s2_v1`, `TELE_DEVICE=pico` y
  `transmit=local`;
- no se renombraron topics, colas, `walker28` ni servicios de teleoperación;
  el perfil independiente de tránsito con caja sí redirige temporalmente tres
  entradas de nube de puntos del costmap y después restaura el original;
- los scripts locales se migraron a las imágenes y hashes de v0.2.0 sin
  instalar tareas nuevas ni mover el robot durante esa migración.

## 3. Arquitectura que se ha verificado

```text
PICO 4 Ultra Enterprise
  Android 14 / XRoboToolkit-PICO 1.1.1
  Wi-Fi Cruzr S2-0669: 192.168.42.211/24 en la sesión verificada
                 │
                 │ TCP directo por Wi-Fi local a 192.168.42.215:63901
                 ▼
PC Ubuntu 24.04.4 LTS
  wlo1 / DSA CORPORATE: 192.168.40.120 (Internet; conservar)
  wlx80afcad40bd6 / Cruzr S2-0669: 192.168.42.215 (PICO + robot)
  ruta 192.168.11.0/24 vía 192.168.42.2 (Motion/Vision; persistente)
  perfil Cruzr: never-default + sin DNS (Internet nunca sale por aquí)
  ├─ RoboticsServiceProcess 1.0.0.0  (TCP 63901)
  ├─ ubt_controller 5.3.0             (WebSocket local TCP 8082)
  └─ ubt-remote-control 4.1.0          (UI; no está abierta ahora)
                 │
                 │ señalización local ws://192.168.11.3:4000
                 │ + DataChannel
                 ▼
Cruzr S2 v0.2.0
  ├─ Vision 192.168.11.3: señalización/web/percepción
  └─ Motion 192.168.11.2: rtm_receiver + control/manipulación
       └─ teleoperation/cruzr_clamp_pico_teleoperation
```

La señalización y el DataChannel no son el mismo canal. Tampoco debe
confundirse el heartbeat de señalización con el heartbeat de seguridad de la
aplicación de teleoperación; esta distinción explica el bloqueo actual.

**Política de rutas canónica desde el 25-08-2026:** todo dispositivo o servicio
concerniente al robot debe usar `Cruzr S2-0669`: la subred interna completa
`192.168.11.0/24` se enruta por `192.168.42.2` y la subred PICO/AP
`192.168.42.0/24` es directa por `wlx80afcad40bd6`. El perfil NetworkManager
`Cruzr S2-0669 1` tiene esa ruta persistente, `ipv4.never-default=yes` e
`ipv4.ignore-auto-dns=yes`. Sólo destinos externos/Internet usan
`wlo1`/`DSA CORPORATE`. Las subredes PICO USB `.67` y Wi-Fi histórica `.106`
no están activas. El rollback administrativo, si el propietario revoca esta
política, consiste en retirar la ruta del perfil y devolver ambos booleanos a
`no`; no debe ejecutarse como recuperación automática.

### 3.1 Qué hace realmente la web viva del robot

Se inspeccionaron, sin modificarlos, los recursos JavaScript servidos por el
propio robot en `http://192.168.11.3`. El selector superior ofrece estos modos:

| Etiqueta | Valor interno |
|---|---|
| 遥控模式 | `joystick` |
| 开发者模式 | `develop` |
| 示教模式 | `teach` |
| 遥操模式 | `teleop` |
| 维修模式 | `maintain` |
| 自动任务模式 | `auto_task` |

Al elegir uno, la web invoca `work_mode.switch` con el campo `workMode`. Ese
componente no descubre el PICO, no lee cabeza/controladores, no abre el canal
XR y no ejecuta la tarea de manipulación. Por tanto:

```text
seleccionar 遥操模式 = prerrequisito de estado del robot
seleccionar 遥操模式 ≠ conectar PICO ni iniciar una sesión completa
```

La ruta `/vr` de esa misma web reproduce la cámara del robot mediante un flujo
WebRTC (`.../live/rtmpstream/head_front_rgbd`). Es un visor de vídeo del robot,
no un cliente de entrada PICO. La presencia de librerías WebRTC/DataChannel en
el frontend tampoco demuestra teleoperación directa.

No se encontraron en el frontend vivo ni en el subfrontend `/utars/`
implementaciones o referencias operativas a `pico_control`,
`cruzr_clamp_pico_teleoperation`, `walker28_web`, tracking PICO o conexión
directa al visor. Esto no prueba que DSA no disponga de otro APK o módulo; sí
prueba que **no está expuesto por la web actualmente instalada**.

### 3.2 Web del robot y HMI del PC no son la misma interfaz

La frase del SDK “pulsar iniciar teleoperación en la web” es ambigua. La web
viva del robot sólo contiene el cambio de `workMode`, mientras la HMI Electron
del PC (`ubt-remote-control`) contiene el control de sesión asociado al backend
5.3.0. Hasta que DSA identifique otra página o APK, no debe interpretarse el
selector de `192.168.11.3` como sustituto del PC.

## 4. Inventario y versiones

### 4.1 Robot

| Elemento | Valor | Estado |
|---|---|---|
| Modelo | Cruzr S2 | **VERIFICADO** |
| Efector actual | abrazaderas laterales | **VERIFICADO** |
| Host Motion | Ubuntu 22.04, `192.168.11.2` | **VERIFICADO** |
| Host Vision | `192.168.11.3` | **VERIFICADO** |
| Versión corta | `v0.2.0` | **VERIFICADO** en Motion y Vision |
| Imagen de integración Motion | `zs2_motion-v0.2.0` | **VERIFICADO** |
| `HW_TYPE` | `cruzr_s2_v1` | **VERIFICADO** |
| `TELE_DEVICE` | `pico` | **VERIFICADO** |
| `transmit` | `local` | **VERIFICADO** |
| `MC_SCENE` | vacío en contenedores inspeccionados | **VERIFICADO; difiere del `DAC` indicado por el SDK** |
| Canal configurado en el PC | `walker28` | **VERIFICADO**, no modificar sin DSA |
| Build exacta DAC | `v0.2.0-dac-beta.2` | **NO DEMOSTRADA** |
| Ejecutable `pico_control` | no encontrado en hosts/contenedores relevantes | **PENDIENTE DSA** |

El SOP entregado exige específicamente:

```text
utars-udoke-config-v0.2.0-dac-beta.2.tar.gz
```

El robot fue actualizado con el paquete genérico `v0.2.0`. El archivo de
versión sólo contiene `SOFT_VERSION=v0.2.0`, y las imágenes activas tampoco
incluyen `dac-beta.2` en el tag. Por tanto, **el nombre corto no demuestra
equivalencia con la build de adquisición de datos**.

Paquetes de actualización ya inspeccionados:

| Paquete | SHA-256 | Conclusión |
|---|---|---|
| archivo offline completo `v0.2.0_offline-001` | `d66372c9f233580a6ebfa7d3ec5f11045fc2bedf61c12562eb2bf4b3c05445d9` | genérico v0.2.0 |
| configuración `utars-udoke-config-v0.2.0.tar.gz` | `0f3d5a988eebb3b4aaacdbaa776c44708b3544afe522edba475fa09a7639aa3b` | genérica v0.2.0 |
| `utars-udoke-config-v0.2.0-dac-beta.2.tar.gz` | no disponible localmente | **PENDIENTE DSA** |

El SOP indica un tamaño aproximado de 39,38 MB para el paquete online DAC y
un `CR_BASE_URL` de `acr.rd.ubtrobot.com/glcr` para ese flujo. El robot tiene
actualmente `CR_BASE_URL=glcr.rd.ubtrobot.com`. No se cambiará el registry ni
se ejecutará una actualización online sin paquete, backup y aprobación.

La sección 7.1 del SDK recibido indica para v0.2.0 `MC_SCENE=DAC`,
`TELE_DEVICE=pico`, el arranque de `signal_server` en Vision, `rtm_receiver` en
Motion y la tarea `teleoperation/cruzr_clamp_pico_teleoperation`. También
menciona el comando `pico_control --arm_type clamp/hand/gripper`. En el robot
real están activos `signal_server` y `rtm_receiver`, pero `MC_SCENE` aparece
vacío y `pico_control` no se encontró. Estas dos diferencias deben resolverse
con DSA; no se inventará ni instalará un ejecutable homónimo.

### 4.2 PC de teleoperación

| Elemento | Valor | Estado |
|---|---|---|
| Sistema | Ubuntu 24.04.4 LTS, amd64 | **VERIFICADO** |
| Ethernet al robot | `192.168.11.250/24` | **VERIFICADO**, coincide con SOP |
| Interfaz USB PICO | `192.168.67.183/24` en una sesión; subred variable | **HISTÓRICAMENTE VERIFICADO** |
| ADB | `1:34.0.4-1build3` | **VERIFICADO** |
| XRoboToolkit PC Service | `roboticsservice 1.0.0.0` para Ubuntu 24.04 | **VERIFICADO** |
| Backend | `ubt-controller 5.3.0` | **VERIFICADO** |
| UI | `ubt-remote-control 4.1.0` | **VERIFICADO** |
| Servicio | `/etc/systemd/system/ubt-controller.service` | instalado, habilitado y **activo** desde 10:26:50 |
| Backend local | TCP 8082 | listener activo; operación STOP |
| Servicio XR | TCP 63901 | proceso/listener activos; PICO/stream offline en el snapshot de las 12:40 |

La instalación del 21 de agosto usó deliberadamente el paquete
`XRoboToolkit_PC_Service_1.0.0_ubuntu_24.04_amd64.deb`; el controlador 5.3.0
sólo fue entregado con nombre `ubuntu22.04`, aunque su binario funciona en el
PC 24.04. Esta combinación necesita confirmación formal de DSA.

El binario original entregado se conserva como backup con este SHA-256:

```text
3a094a007842d859ce95974d74fddf74714e1a49a9a75ca32e82fd6ce7b789fa
```

El ejecutable activo fue reconstruido de forma reproducible a partir de ese
backup, modificando tres objetos de código en dos módulos Python embebidos;
SHA-256 activo al
cierre:

```text
5083e9f0bef9142bfa6ad1b849c767cb9e5ab22e2edd99b981d6061decd7aec2
```

Los cambios son `GRIPPER → CLAMP` en la selección del efector, el mapeo del
flanco ascendente del gatillo izquierdo al booleano que el proveedor asigna a
Y, y el operando del comparador del heartbeat, fijado temporalmente en 300 s.
No se modifica el
robot, no se fuerza `enable_control` y no se fabrica heartbeat; el watchdog y
su ruta STOP siguen presentes. La versión anterior de 10 s está respaldada en
`/opt/ubt/ubt_controller/ubt_controller.clamp-trigger-heartbeat-10s-0f0d3414.bak`
con SHA-256
`0f0d341424f30042cc9189ff215d09007de91f443e4b9b0debaeffa81cda28eb`.
La variante anterior de nivel/300 s está respaldada en
`/opt/ubt/ubt_controller/ubt_controller.clamp-trigger-level-heartbeat-300s-40b440f4.bak`
con SHA-256
`40b440f4a991160e07aeabd168b212854fad2d7b4efbe6bb4874520b48038b4c`.
El activo quedó modo `0755`, propietario `lacuna:lacuna`; el directorio ya era
escribible por ese usuario antes del cambio. El backup de 10 s conserva
`root:root`.
Véase la sección 8.

### 4.3 PICO

| Elemento | Valor | Estado |
|---|---|---|
| Modelo reportado por ADB | `A9210` | **VERIFICADO** |
| Familia comercial | PICO 4 Ultra Enterprise | **VERIFICADO por hardware/proveedor** |
| Android | 14 | **VERIFICADO** |
| Aplicación | `com.xrobotoolkit.client` | **VERIFICADO** |
| XRoboToolkit | 1.1.1 | **VERIFICADO** |
| IP Wi-Fi local observada | `192.168.42.211/24` en `Cruzr S2-0669` | **VERIFICADO POR DHCP**, no fijar en scripts |
| IP USB compartida | varias subredes `192.168.67.x` y `192.168.106.x` | **HISTÓRICO**, no fijar en scripts |
| Estado de aplicación | llegó a `Working` en varias sesiones; estado físico actual no asumido | **OBSERVADO** |
| Modo de envío | `Head + Controllers` | **OBSERVADO antes del reinicio** |
| Controladores | poses enviadas; neutros antes de pruebas | **OBSERVADO** |
| `QuestTool_v3.5.3.apk` | recibido, no identificado como componente activo | **NO UTILIZADO** |

`Working` significa que el PICO está unido al servicio XR del PC. No confirma
heartbeat del robot, tarea de manipulación activa ni autorización para mover.

Después de reiniciar el visor, el USB volvió como MTP/ADB o
MTP/accessory/ADB, sin recrear la interfaz Ethernet USB anterior. El PICO no
tenía una Wi-Fi asociada y XRoboToolkit quedó sin ruta hacia el PC. Los intentos
de forzar RNDIS mediante `svc usb setFunctions` no produjeron una interfaz de
red y no deben usarse como procedimiento de reconexión.

**VERIFICADO después:** `wlo1` permanece en `DSA CORPORATE` para Internet y el
adaptador secundario `wlx80afcad40bd6` usa `Cruzr S2-0669`. Al asociar PICO a
esa misma WLAN, XRoboToolkit recibió por discovery la IP PC
`192.168.42.215` y conectó directamente a TCP 63901 desde `192.168.42.211`.
No requiere red USB ni reverse; ambas IP son concesiones observadas, no una
configuración estática garantizada.

### 4.4 Hashes de los instaladores recibidos

Los binarios grandes se mantienen fuera de Git; estos hashes permiten volver
a identificar exactamente el material utilizado.

| Archivo | SHA-256 |
|---|---|
| `XRoboToolkit-PICO-1.1.1.apk` | `6b2bb282405673d24abcb1980e3478b8f1052e90f7207b1f24cc56a59f8d8261` |
| `XRoboToolkit_PC_Service_1.0.0_ubuntu_24.04_amd64.deb` | `bce661f0be0b8a246ceecb2e5f1675a81c26b834648dc7fdf23f8c0bfe2a5d19` |
| `ubt_controller_5.3.0_ubuntu22.04_amd64.deb` | `18300c8e16c5cfc9e88214ddce772d8be6b1d03129e953b9d1cb3ae2d2d34144` |
| `ubt-remote-control_4.1.0_amd64.deb` | `2663545f83fa00946443a60f493e4f3db2b14a7e12b6980b5cdece76f2f5d279` |
| SOP UTARS/PICO recibido | `2b786be5391cd93feb3750e4e2786377b1a0799537310d527bca9ce75d22a258` |

## 5. Configuración activa conocida

### 5.1 Backend del PC

Archivo: `/opt/ubt/ubt_controller/config/config.json`.

```json
{
  "transmit": "local",
  "signal_server_url": "ws://192.168.11.3:4000",
  "channel_name": "walker28",
  "push_rate": 90,
  "control_device": "pico",
  "foot_switch_path": "/dev/input/by-id/usb-PCsensor_FootSwitch-event-kbd",
  "enable_foot_switch": 0,
  "send_joint_name": 0,
  "enable_adb_reverse": 1
}
```

Observaciones:

- `push_rate=90` es la tasa configurada del flujo XR, no una garantía de 90 FPS
  del dataset final.
- `enable_foot_switch=0` permite trabajar sin el pedal que no está instalado.
- `enable_adb_reverse=1` está configurado. El snapshot de las 10:29 muestra
  `UsbFfs tcp:63901 tcp:63901`; la sesión actual usa ese reverse porque el PICO
  sólo expone `mtp,adb` y no recreó una interfaz Ethernet USB. El flag por sí
  solo no crea a tiempo el túnel durante la espera inicial del wrapper.
- No se deben versionar certificados, tokens, contraseñas ni identificadores
  privados presentes en paquetes cerrados.

### 5.2 Tarea correcta del robot

La tarea específica de este robot y efector es:

```text
teleoperation/cruzr_clamp_pico_teleoperation
```

Usa el meta-task:

```text
meta_teleoperation/cruzr_clamp_pico_tele.yaml
```

Valores relevantes verificados:

| Campo | Valor |
|---|---|
| `robot_type` | `cruzr` |
| `hand_type` | `clamp` |
| `frequency` | `500` |
| `init_time` | `12.0` s |
| `collision_detection` | `true` |
| `web_comm_service` | `true` |
| `head_tracking` | `true` |
| `waist_tracking` | `false` |
| `tele_device` | `7` (`kPico`) |
| modo de brazos | mapeo de efector (`limb_mode=2`) |
| protección de fuerza configurada | 120 N por eje en cada brazo |

La presencia de `collision_detection=true` y umbrales de 120 N no equivale a
seguridad funcional certificada. DSA debe confirmar unidades, significado,
tiempo de reacción y límites adecuados para este efector.

También existen tareas `s2_*`, pero **no son la elección correcta para Cruzr**.
Aunque el SOP sea compartido con Walker S2, el robot contiene una variante
específica `cruzr_clamp_pico_teleoperation` con parámetros geométricos Cruzr.

### 5.3 Interfaces ROS observadas

| Topic | Tipo | Publicador/suscriptor presentes |
|---|---|---|
| `/pico_vr/hand_data` | `sensor_msgs/msg/JointState` | sí |
| `/pico_vr/joy_data` | `quest_msgs/msg/Joysticks` | sí |
| `/pico_vr/pose_data` | `sensor_msgs/msg/JointState` | sí |
| `/pico_vr/tele_data` | `sensor_msgs/msg/JointState` | 1 / 1 |
| `/mc/teleoperation/enable` | `std_msgs/msg/Bool` | 1 / 1 |
| `/mc/teleoperation/mode_status` | `sensor_msgs/msg/JointState` | 1 / 1 |
| `/teleop/enable` | `std_msgs/msg/Bool` | 1 / 1 |

La existencia de endpoints DDS no demuestra que estén publicando muestras
válidas en este instante. En el último snapshot, los `echo --once` no
recibieron muestra durante cinco segundos.

### 5.4 Controles documentados y nivel de validación

| Control PICO | Función indicada por SOP | Validación actual |
|---|---|---|
| `Y` | iniciar/detener teleoperación | contacto capacitivo observado; clic mecánico `key.b_y` no fiable |
| `X` | alternar modo en sitio/móvil | clic aislado no reproducible; no está reasignado en el backend activo |
| `A` | reset del tren superior en modo en sitio | pulsado; no corrige el enlace; efecto físico no caracterizado |
| `B` | iniciar/detener captura de episodio | **PENDIENTE** |
| grip izquierdo/derecho | seguimiento de ese brazo y cintura | **PENDIENTE**, no usar antes del gate |
| gatillo izquierdo | cierre/apertura de mano activa según SOP | con abrazaderas pasivas se mapea a un solo flanco de Y; comportamiento aislado verificado, E2E físico pendiente |
| gatillo derecho | cierre/apertura de mano activa según SOP | sin cambios; no usar con abrazaderas para habilitar |
| joysticks en sitio | cintura y elevador | **PENDIENTE** |
| joysticks en modo móvil | traslación y giro del chasis | **PENDIENTE** |
| clics de joystick | alternar protección de fuerza por brazo | **NO PROBAR** hasta confirmar estado/indicación |

La UI PICO no muestra por sí sola toda la cadena de armado. Mientras no se
conozca el heartbeat, ningún cambio de color o estado del visor debe sustituir
la lectura del backend y del robot.

### 5.5 Estado interno y semántica observada en v0.2.0

La última recuperación dejó evidencia de un cierre limpio de la tarea:

- `teleoperation/cruzr_clamp_pico_teleoperation` fue destruida antes de
  ejecutar `cruzr/home`;
- `/sys/state/module_lock_info` devolvió `locked=false` y `module_name` vacío;
- `cruzr/home` terminó con `SUCCEED/status=4`;
- la última muestra conocida del status de acción era terminal, no activa.

En v0.2.0 hay dos diferencias importantes respecto a scripts antiguos:

1. `/sys/task/remote_command` puede anunciar un cliente pero ningún servidor y
   no ofrecer `DO_RESET=9`. Si la máquina de tareas está libre, no hace falta
   enviar ese reset; si está bloqueada y `DO_RESET` no existe, se debe parar y
   diagnosticar, no enviar una orden inventada.
2. `/mc/manipulation/action` conserva un cliente persistente incluso en reposo.
   `Action client count: 1` ya no significa que haya una tarea ejecutándose.
   Para decidir si está ocupado se consultan estados activos de action status
   (`1`, `2` o `3`), además del lock y del resultado de la tarea.

El último log de la tarea PICO confirmó los parámetros reales: abrazaderas,
`PicoVRJoystick`, frecuencia 500 Hz, inicialización 12 s, detección de
colisiones activa, seguimiento de cabeza activo, cintura desactivada y
`TimeRatio=0.5`. Son evidencia de configuración, no de una sesión PICO válida.

## 6. Qué se ha probado extremo a extremo

### 6.1 Enlace PICO → PC

**VERIFICADO:**

1. El PICO aparece como dispositivo ADB autorizado.
2. XRoboToolkit entra en `Working` y envía `Head + Controller`.
3. Históricamente apareció red IP USB en subredes variables; la sesión actual
   usa la WLAN `Cruzr S2-0669` con DHCP.
4. Se establece TCP directo desde el PICO hacia
   `192.168.42.215:63901` (`RoboticsServiceProcess`).
5. El servicio detecta el dispositivo y `ubt_controller` consume el SDK.
6. En una prueba diagnóstica se observaron datos PICO próximos a la tasa
   configurada de 90 Hz.

**REGRESIÓN HISTÓRICA Y RECUPERACIÓN ACTUAL:** después de reiniciar el PICO,
ADB volvió pero no reapareció la interfaz de red USB. El 25 de agosto a las
10:29 se verificó que XRoboToolkit intenta `127.0.0.1:63901`; se restauró
`adb reverse tcp:63901 tcp:63901`, se reinició sólo la app y reaparecieron TCP
establecido y `vr_status=1`. No se forzó RNDIS.

### 6.2 PC → robot

**VERIFICADO:**

1. El backend local acepta un cliente WebSocket en TCP 8082.
2. Al iniciar recopilación desde un cliente diagnóstico, el PC establece
   señalización y abre el DataChannel con el robot.
3. El log de transporte confirma repetidamente `datachannel is open`.
4. El robot recibe tele-data y registra habilitación temporal de
   teleoperación.
5. El robot devuelve eventos `tele_operation` al PC; se observaron estados
   `enable=1` y posteriormente `enable=0`.

La prueba diagnóstica utilizó el protocolo local descubierto en el paquete:

```json
{"type":"collect","content":{"operation_type":2,"enable_hand_pose":0}}
```

`operation_type=2` inicia y `operation_type=1` detiene. Esta interfaz se usó
solamente para aislar capas; **no es el procedimiento normal de operación**.
El cliente diagnóstico fue cerrado y se envió STOP. No debe quedar conectado
en paralelo con la interfaz oficial.

### 6.3 Robot → PC: punto de fallo

**FALLA REPRODUCIDA:** el backend espera recibir periódicamente:

```json
{"type":"heartbeat"}
```

No se observó ningún mensaje de ese tipo. El watchdog del controlador compara
la hora actual con `last_heartbeat_time`; si transcurren más de 10 segundos,
registra:

```text
No heartbeat for 10 seconds, stoping operation
```

y envía STOP. El callback posterior muestra:

```json
{"content":{"enable":0},"type":"tele_operation"}
```

Ese valor de 10 s describe el binario vendor y las reproducciones históricas.
El ejecutable actualmente instalado conserva el mismo bloque pero compara con
300 s por la autorización diagnóstica registrada en 8.10; todavía no se ha
ejecutado ni validado en runtime.

El watchdog puede seguir emitiendo STOP de forma periódica mientras no haya
heartbeat. En el binario histórico, si START ocurría cuando el temporizador ya
estaba vencido, la parada podía aparecer antes de diez segundos desde la
pulsación de `Y`; los diez segundos se medían desde el último heartbeat válido,
no necesariamente desde el último START. La misma semántica se conserva con el
umbral temporal de 300 s.

La reproducción inicial se hizo sin haber confirmado el selector web
obligatorio `遥操模式`. Después se repitió la cadena con modo remoto,
`vr_status=1` y `arm=clamp`; el robot siguió devolviendo `enable=0` y no se
observó el heartbeat esperado. En la sesión analizada, estos callbacks
aparecieron aproximadamente cada 11,1 segundos, mientras el watchdog del PC
vence a los 10 segundos. Esto confirma una incompatibilidad temporal o de
protocolo pendiente de DSA; no demuestra por sí solo cuál componente tiene la
versión incorrecta.

**REVALIDADO el 25 de agosto sobre los binarios instalados:** el bytecode de
`Publisher.callback` documenta el flujo «robot SDK → RTM → Sender → callback».
La rama `type=heartbeat` llama a `update_last_heartbeat_time`; START sólo
inicializa esa misma marca una vez. El source map de la UI PC 4.1.0 no contiene
un emisor de heartbeat y sus únicos mensajes operativos son START/STOP. Por
tanto, mantener abierto el WebSocket de la UI o del lanzador no proporciona el
heartbeat que falta.

### 6.4 Los dos “heartbeats” no son equivalentes

El robot registra cada diez segundos:

```text
AnswerSession: sent heartbeat
```

El análisis de `libwebrtc_sdk.so` confirma que esa rutina envía al servidor de
señalización un mensaje equivalente a:

```json
{"event":"ping","server_id":"..."}
```

Su función es mantener registrada la sesión de señalización. **No es** el
heartbeat JSON de la aplicación que espera `ubt-controller` por el callback
del DataChannel.

El ejecutable `rtm_receiver` y la biblioteca `librtm_sdk.so` inspeccionados no
mostraron una rutina evidente que publique el heartbeat de aplicación. Esto es
coherente con que la build genérica `v0.2.0` carezca de una pieza incluida en
`v0.2.0-dac-beta.2`.

### 6.5 Resultado de las pruebas de botones

- Android/Stationservice reporta por separado contacto capacitivo y clic.
- En una prueba aislada anterior, X mantenido llegó a producir
  `key.a_x=1`, pero el resultado no fue reproducible.
- Al pulsar Y durante dos segundos apareció contacto `touch.b_y=1`, pero
  `key.b_y` permaneció en cero. Por tanto se estaba tocando el botón correcto,
  pero su clic no llegó a la aplicación.
- En las pruebas posteriores, Stationservice mantuvo `key.a_x=0` también al
  pulsar X. Una escucha directa de `get_X_button()`, `get_Y_button()`,
  `get_A_button()` y `get_B_button()` en el SDK del PC terminó con
  `BUTTONS_SEEN=NONE`, mientras el tracking de poses seguía disponible.
- Durante esa misma ventana Android registró una transición temporal a
  `HandTrackingActive` y después a `ControllerActive`. Esto sitúa el fallo
  actual antes del backend del robot: estado/modo de entrada de XRoboToolkit,
  controlador PICO o transporte de botones PICO → XRoboToolkit PC Service.
- El backend vendor usa `get_Y_button()` para `left_joystick.b_button`, y ese
  campo llama a `enable_operation_switch()`.
- Se sustituyó el workaround X/Y por un mapping del gatillo izquierdo al
  booleano Y, manteniendo intacto el mando derecho. Una prueba de ocho segundos
  no observó `b_button=true`; el robot permaneció con `enable=0`.
- Dos escuchas directas posteriores del SDK devolvieron pico de gatillo
  izquierdo `0.000` y ningún botón. Una primera prueba pudo haberse hecho sin
  accionar correctamente el gatillo; la repetición explícita también quedó en
  cero.
- Aún no se ha obtenido una teleoperación física continua y validada.

## 7. Diagnóstico de causa

### 7.1 Hechos que descartan un fallo básico de conexión

No encaja con un fallo simple de USB, ADB, PICO, Ethernet o DataChannel porque:

- ADB ve el visor;
- el PICO mantiene TCP con el servicio XR;
- el PC recibe datos XR;
- el DataChannel se abre;
- el robot recibe tele-data;
- el robot devuelve mensajes `tele_operation`;
- el watchdog específico de heartbeat es quien ordena STOP.

### 7.2 Causas compatibles con la evidencia

La respuesta posterior de DSA añadió un prerrequisito que no estaba reflejado
en las pruebas iniciales: seleccionar `遥操模式` en la web del robot. Ese modo
se seleccionó y Control Center confirmó `TeleopMode`; no resolvió por sí solo
la habilitación ni el heartbeat.

La segunda causa posible sigue siendo una incompatibilidad entre el robot
genérico `v0.2.0` y el conjunto de PC exigido para adquisición de datos. El SOP
define una matriz exacta:

| Componente | Versión exigida por SOP |
|---|---|
| Robot | `utars-udoke-config-v0.2.0-dac-beta.2.tar.gz` |
| Backend PC | `ubt_controller_5.3.0_ubuntu22.04_amd64` |
| UI PC | `ubt-remote-control_4.1.0_amd64` |

Los dos componentes del PC coinciden. La build exacta del robot no está
instalada o, como mínimo, no puede demostrarse con el material actual. La
ausencia del heartbeat de aplicación es consistente con esa diferencia, pero
no demuestra por sí sola la build causante. También existe un desfase
observado entre callbacks del robot (~11,1 s) y el watchdog del PC (10 s) que
DSA debe explicar.

### 7.3 Qué debe confirmar DSA

DSA debe proporcionar una de estas dos respuestas verificables:

1. el archivo exacto `utars-udoke-config-v0.2.0-dac-beta.2.tar.gz`, su hash y
   procedimiento de actualización/rollback; o
2. una declaración de que el paquete genérico instalado contiene exactamente
   los mismos componentes DAC, acompañada por versiones/hashes y una corrección
   concreta para el heartbeat que falta.

Hasta entonces no se considerará resuelto.

## 8. Workarounds y cambios locales aplicados

Todos son reversibles. El binario original de `ubt_controller` permanece
respaldado; los dos cambios de bytecode del PC se generan mediante un script
versionado y validan estructura, runtime y orden de lecturas antes de instalar.

### 8.1 Regla udev para PICO

Se instaló y versionó
[`../../config/udev/51-pico-ubt.rules`](../../config/udev/51-pico-ubt.rules)
para dar acceso al vendor USB `2d40` mediante `plugdev`/`uaccess`. El usuario
operador pertenece a `plugdev`.

**Resultado:** ADB funciona sin ejecutar un daemon ADB como root.

### 8.2 Locale numérico neutral

Se añadieron `LANG=C.UTF-8`, `LC_ALL=C.UTF-8` y `LC_NUMERIC=C` a la unidad
systemd y al wrapper `run.sh`.

**Motivo:** XRoboToolkit serializa arrays como texto separado por comas. Un
locale español también usa coma decimal y puede corromper la separación de
coordenadas.

**Resultado:** el servicio XR entrega poses interpretables. Esto corrige el
formato local, pero no el heartbeat robot → PC.

### 8.3 Espera de conexión PICO antes del backend

El wrapper espera hasta 60 segundos a que exista una conexión establecida en
TCP 63901 antes de lanzar `ubt_controller`.

**Motivo:** el SDK XR enumera dispositivos existentes al inicializarse. Si el
backend arranca antes de que el PICO conecte, el proceso puede quedar vivo sin
publicar poses después de una reconexión.

**Resultado:** tras el reinicio más reciente, el wrapper detectó el stream a
los 21 segundos y después arrancó el controlador.

**Limitación:** si el PICO se desconecta o duerme después, puede ser necesario
reiniciar `ubt-controller.service` una vez restablecido `Working`.

### 8.4 Operación sin pedal

Se cambió únicamente:

```json
"enable_foot_switch": 0
```

**Motivo:** no hay pedal físico conectado. El paquete contempla el flag.

**Resultado:** el backend no espera el dispositivo de pedal. Aún falta que DSA
confirme el comportamiento oficial de deadman sin pedal y la relación exacta
entre `Y`, grips y habilitación.

### 8.5 IP Ethernet del PC

Se configuró `192.168.11.250/24`, que es la IP indicada por el SOP. Sustituye
la dirección de diagnóstico anterior `192.168.11.99`.

**Resultado:** acceso correcto a Motion `.2` y Vision `.3` sin usar la ruta por
defecto del PC.

### 8.6 Cliente WebSocket diagnóstico

Se usó temporalmente un cliente local para separar UI, backend, señalización y
robot.

**Resultado:** demostró que el transporte XR/DataChannel llega al robot y que
la parada procede del watchdog de heartbeat.

**Estado final:** cerrado; STOP enviado; no debe ejecutarse junto a la UI
oficial ni convertirse en una herramienta de producción.

### 8.7 Perfil de abrazaderas en el backend del PC

Se instaló el drop-in versionado
[`../../config/systemd/system/ubt-controller.service.d/20-cruzr-clamp.conf`](../../config/systemd/system/ubt-controller.service.d/20-cruzr-clamp.conf),
que fija:

```ini
Environment=arm=clamp
```

**Motivo:** la interfaz recibió del canal del robot la etiqueta genérica
`gripper` y el backend cargó `ubt_gripper.json`, aunque el hardware real son
abrazaderas laterales. El controlador distingue explícitamente `clamp` de
`gripper`.

**Resultado:** el valor por defecto del backend coincide ahora con el efector
físico. El lanzador exige además `arm_type=clamp` y aborta si el log vuelve a
seleccionar `gripper`.

### 8.8 UI bajo demanda y preflight del PC

Se añadió la unidad de usuario bajo demanda
[`../../config/systemd/user/ubt-remote-control.service`](../../config/systemd/user/ubt-remote-control.service)
y el lanzador
[`../../scripts/teleoperation/cruzr_pico_teleop_pc.sh`](../../scripts/teleoperation/cruzr_pico_teleop_pc.sh).

La UI no se habilita al arrancar Ubuntu. El lanzador comprueba ADB, rutas,
Motion/Vision, TCP 63901, WebSocket 8082, `vr_status`, estado de operación y
`arm=clamp`; exige una confirmación física antes de publicar y detiene/cierra
si aparece el watchdog.

La inspección del source map de `ubt-remote-control 4.1.0` mostró dos detalles:

- la UI no genera el heartbeat de aplicación; éste debe llegar desde el lado
  del robot;
- usa `reconnectLimit: -1` como si significara infinito, pero la versión
  incluida de la librería no reconecta con ese valor. Por eso el orden seguro
  es backend + PICO primero y UI después.

**MEJORADO el 25 de agosto a las 10:35:** `check_pc` era silencioso hasta
terminar, por lo que una consulta lenta parecía un cuelgue. Ahora imprime siete
etapas con timestamp antes de ejecutarlas, limita ADB, systemd, journal y
WebSocket a 5 s y termina con `CHECK COMPLETADO`. El gate muestra además cuándo
envía START y cuándo espera `arm=clamp`; un fallo Bash inesperado informa
línea/comando antes de solicitar STOP. Para traza completa sin cambiar la
operación se puede usar:

```bash
CRUZR_TELEOP_DEBUG=1 \
  ./scripts/teleoperation/cruzr_pico_teleop_pc.sh --check
```

Se verificó el flujo normal completo y un fallo ADB simulado; ambos dejaron
`operation_type=1`, `enable_control=0`, `vr_status=1`. No se ejecutó el gate.

### 8.9 Recuperación de socket XR del PICO

Después de reiniciar `RoboticsServiceProcess`, XRoboToolkit puede conservar una
pantalla activa con un socket ya muerto. Se reprodujo que reiniciar sólo la app
`com.xrobotoolkit.client` por ADB recupera TCP 63901. Ese reinicio desarma el
envío: hay que volver a seleccionar `Head + Controllers`, pulsar `Send data` y
verificar `Working`; TCP establecido por sí solo no equivale a `vr_status=1`.

**REVALIDADO el 25 de agosto a las 10:29:** el servicio estaba activo y
escuchaba 63901, pero no había red USB ni entrada en `adb reverse --list`.
XRoboToolkit registraba fallos repetidos contra `127.0.0.1:63901`. Tras crear
el reverse, la app conservó el socket fallido; `am force-stop` seguido de un
nuevo lanzamiento produjo TCP establecido, `ControllerActive` y
`vr_status=1`. El backend permaneció en `operation_type=1`,
`enable_control=0`; no se envió `collect`/START ni hubo prueba física. El
`--check` canónico pasó red, ADB, stream, tracking, clamp, hash `40b440…` y
watchdog configurado a 300 s.

**REVALIDADO el 25 de agosto a las 11:53:** PC y PICO quedaron en
`Cruzr S2-0669` con `192.168.42.215` y `192.168.42.211`, respectivamente,
sin desconectar `wlo1` de `DSA CORPORATE`. Tras `Head + Controllers` y
`Send data`, el log Unity confirmó conexión a `192.168.42.215:63901` y `ss`
mostró el peer directo. Se eliminó `adb reverse --remove-all`; TCP,
`vr_status=1` y STOP permanecieron. El lanzador identifica ahora el visor por
`ro.serialno` con serial USB o destino ADB `IP:puerto`. `bash -n` y `--check`
pasaron; `shellcheck` no está instalado. No se envió START ni hubo movimiento.

**REVALIDADO el 25 de agosto a las 12:16:** una caída transitoria de la WLAN y
la recuperación ADB dejaron dos sockets XR simultáneos. Aunque la app estaba
visible en `Working` y el tracking PICO local mostraba cabeza y controladores,
el backend registró `device missing` a las 12:13:21 y devolvió `vr_status=0`.
Se reinició únicamente `com.xrobotoolkit.client`; después de volver a elegir
`Head + Controllers` y `Send data`, `vr_status` cambió `0→1` manteniendo
`operation_type=1`, `enable_control=0`. El `--check` canónico volvió a pasar
7/7 por TCP directo `.211→.215:63901`. No hubo START ni movimiento.

### 8.10 Corrección del efector y workaround de entrada

El script
[`../../scripts/teleoperation/patch_ubt_controller_clamp.py`](../../scripts/teleoperation/patch_ubt_controller_clamp.py)
reconstruye el archivo PYZ de PyInstaller con Python 3.10 y aplica:

1. `WebsocketServer.collect`: cambia la selección automática
   `ARM_TYPE.GRIPPER` por `ARM_TYPE.CLAMP`.
2. Con `--pico-enable-left-trigger`, `PicoPublisher.publish_joysticks`:
   conserva el empaquetado de ambos mandos, lee una vez el gatillo izquierdo
   y publica `left_joystick.b_button=true` sólo durante su flanco ascendente.
   Mantenerlo apretado ya no repite el conmutador Y del proveedor.
3. Con `--heartbeat-timeout-seconds 300`,
   `WebsocketServer._broadcast_publisher_states`: sustituye únicamente el
   operando `release_timeout` de la comparación de heartbeat por el literal
   `300`; no toca las demás aplicaciones de `release_timeout`.

Este modo se eligió porque X/Y no entregaron un clic reproducible y las
abrazaderas pasivas no tienen dedos que accionar con el gatillo. El gatillo
debe seguir siendo pulsado físicamente; no se sintetiza un clic, no se llama
directamente a `enable_operation_switch()`. El workaround de entrada no altera
heartbeat, STOP ni control de colisiones. El cambio de timeout es independiente:
no crea mensajes, conserva el mismo bloque STOP y sólo retrasa su vencimiento.
El mando derecho permanece intacto.

**VERIFICADO el 25 de agosto:** el gatillo izquierdo produjo
`b_button=true`, el robot respondió `enable=1` y Motion entró en `CoreMode 7`.
La segunda prueba mantuvo físicamente el gatillo: la entrada cruda permaneció
estable en `trigger_value=1.0` y `b_button=true`, mientras las respuestas del
robot alternaron `enable=1/0` cada aproximadamente 0,51 segundos. Esto demuestra
que el Y del proveedor es un **conmutador con repetición**, no un *deadman*.
Mantenerlo pulsado provoca entradas/salidas repetidas de `CoreMode 7`.

**VERIFICADO a las 10:38 PC / 16:37–16:38 Motion:** el DataChannel abrió a
las 10:38:02.094, antes del primer `enable=1` a las 10:38:03.670. Motion
recibió tele-data, entró en `CoreMode 7`, terminó el retardo de tres segundos,
habilitó protección de fuerza en ambos brazos y arrancó correctamente ambos
chequeos. La habilitación se sostuvo unos 46,1 s sin el watchdog de 10 s. El
operador movió los mandos y confirmó cero movimiento físico. En 4.530 muestras
de cada mando, `squeeze`/grip permaneció siempre `false` y `0.0`; el SOP exige
mantener el grip correspondiente para que ese brazo siga al operador. Por
tanto, la ausencia de movimiento es coherente con este gate deliberadamente
sin maniobra y no demuestra un fallo de tracking. Al final, tres pulsaciones
adicionales produjeron `enable=0`, `1`, `0` a intervalos de 0,5 s; el script
detectó la pérdida y envió STOP. Motion registró `CoreMode 7→0` y
`Teleoperation disabled`; el backend quedó en `operation_type=1`,
`enable_control=0`.

**VERIFICADO a las 12:27–12:28:** hubo un solo flanco físico, pero la lectura
cruda permaneció alta 0,567 s (12:27:59.412–12:27:59.979). El backend de nivel
habilitó a las 12:27:59.685 y volvió a deshabilitar a las 12:28:00.019; el
script observó la pérdida a las 12:28:01.157 y envió STOP. No actuó el
watchdog. Exigir manualmente un toque menor de 0,5 s no era robusto: una sola
pulsación podía repetirse mientras permaneciera alta.

A las 12:31, durante el diagnóstico, se observó además otra sesión activa no
esperada (`operation_type=2`, `enable_control=1`) y ambos grips altos. Se envió
inmediatamente el STOP canónico y se confirmó `operation_type=1`,
`enable_control=0`. No se ordenó movimiento desde las herramientas de
diagnóstico.

La corrección instalada convierte el gatillo en un pulso de un frame sólo en
el flanco ascendente. Los tres flujos físicos comprueban además que todos los
controles estén neutros antes de START y que aparezca una lectura nueva de
gatillo liberado en menos de tres segundos después de habilitar; de lo
contrario envían STOP. El test aislado con niveles `[0,1,1,1,0,1]` produjo
`b_button=[false,true,false,false,false,true]`, exactamente dos llamadas al
conmutador. La prueba física extremo a extremo del nuevo flanco queda
**PENDIENTE** hasta recuperar ADB/stream PICO y repetir el preflight.

El lanzador se corrigió para pedir ese toque único y enviar STOP
automáticamente al completar los 60 segundos. El modo recomendado
`--gate-local` exige un TTY del PC y emite localmente una campana y el texto
`TOQUE AHORA` después de armar el publicador; el chat o una coordinación remota
no forman parte de la ventana de 8 segundos. `--run` queda como alias. El gate
local se ejecutó posteriormente y falló de nuevo por ausencia de heartbeat;
por tanto, la estabilidad sostenida continúa bloqueada. Para revertir el parche
de timeout sin perder las correcciones de clamp/gatillo, usar el backup de 10 s
documentado abajo con el robot en STOP.

**VERIFICADO EN DISCO Y PARCIALMENTE EN RUNTIME el 25 de agosto:** el propietario del
proyecto autorizó explícitamente ampliar el timeout de heartbeat de 10 a 300 s
para probar teleoperación. Se envió STOP y se confirmó
`operation_type=1`/`enable_control=0`; después se detuvo el servicio, se
instaló el SHA-256 activo `40b440f4a991160e07aeabd168b212854fad2d7b4efbe6bb4874520b48038b4c`
y se dejó `inactive/dead`, sin procesos ni listeners 8082/63901. La unidad
permanece habilitada al boot. La validación estática confirmó exactamente un
comparador a 300 s y que, sin la opción nueva, el script reproduce byte a byte
el binario anterior `0f0d3414…`. No se arrancó el backend, no se publicó al
robot y no hubo movimiento durante el cambio.

**ACTUALIZADO a las 12:39–12:40:** se envió STOP, se confirmó
`operation_type=1`/`enable_control=0`, se detuvo el servicio mediante su
lifecycle de 15 s y se instaló la variante de flanco ascendente con SHA-256
`5083e9f0bef9142bfa6ad1b849c767cb9e5ab22e2edd99b981d6061decd7aec2`.
La variante anterior de nivel/300 s quedó respaldada en
`/opt/ubt/ubt_controller/ubt_controller.clamp-trigger-level-heartbeat-300s-40b440f4.bak`
con SHA-256 `40b440f4a991160e07aeabd168b212854fad2d7b4efbe6bb4874520b48038b4c`.
El servicio y listeners 8082/63901 arrancaron; el snapshot final fue
`vr_status=0`, `operation_type=1`, `enable_control=0`, UI inactiva. La ausencia
de `vr_status` se debe a que el PICO no estaba alcanzable por ADB/stream en ese
instante. No hubo START ni movimiento durante la instalación.

**REVALIDADO a las 12:44 sin START:** el preflight canónico recuperó ADB en
`192.168.42.211:5555`, confirmó el stream directo `.211→.215:63901`,
`vr_status=1`, Motion/Vision por la Wi-Fi Cruzr, `arm=clamp`, hash activo y
watchdog 300 s. Terminó 7/7 con `operation_type=1`, `enable_control=0` y UI
inactiva. No se publicó movimiento.

Después se arrancó el backend para la ventana autorizada: mantuvo enable unos
46,1 s, superando el límite anterior de 10 s sin activar el watchdog. Esto
valida que el comparador de 300 s está activo, pero no demuestra heartbeat ni
el STOP por vencimiento a los 300 s.

`probar_pico.sh --gate-only` conserva el STOP automático a los 60 s y describe
esa ejecución como **ventana diagnóstica**, no como gate de heartbeat: 60 s
son menos que el timeout temporal de 300 s. Una ejecución sin STOP durante esa
ventana no demuestra que llegue `{"type":"heartbeat"}`. También se cambió la
detección del log a un patrón independiente del número de segundos.

Rollback del timeout, siempre con el robot desarmado, UI cerrada y servicio
detenido:

```bash
./scripts/teleoperation/cruzr_pico_teleop_pc.sh --stop
systemctl stop ubt-controller.service
install -m 0755 \
  /opt/ubt/ubt_controller/ubt_controller.clamp-trigger-heartbeat-10s-0f0d3414.bak \
  /opt/ubt/ubt_controller/ubt_controller
sha256sum /opt/ubt/ubt_controller/ubt_controller
```

El hash esperado tras rollback es `0f0d341424f30042cc9189ff215d09007de91f443e4b9b0debaeffa81cda28eb`.
No arrancar el servicio hasta repetir el preflight físico y lógico.

Para el operador se añadió `scripts/teleoperation/probar_pico.sh`. Tras la
autorización explícita del propietario para movimiento real, su ejecución sin
argumentos delega una prueba mínima del brazo derecho; `--move-left-arm`
selecciona el izquierdo y `--gate-only` conserva el flujo sin maniobra. El
modo físico realiza preflight PC y Motion (paros, batería, cargador,
`HW_TYPE`, tarea PICO, única acción activa y velocidad articular), exige
confirmación visual de home/abrazaderas/zona/ruedas, mantiene 60 s estables sin
grips y abre después sólo 5 s para un gesto de 2–3 cm con un único grip. Soltar
el grip, usar Ctrl+C, perder enable o tocar el grip opuesto envía STOP. El
primer handler de señal sólo hacía STOP y podía reanudar el `read`; se corrigió
para que `Ctrl+C`/`TERM` envíen STOP y terminen con 130/143.

**PENDIENTE DE EJECUCIÓN FÍSICA — MODO INTEGRAL:** el propietario amplió
explícitamente la autorización para probar todos los comandos documentados del
headset durante al menos dos minutos. El modo versionado es
`./scripts/teleoperation/probar_pico.sh --all-controls`. Conserva el preflight
PC/Motion y exige 60 s iniciales completamente neutros; después abre 120 s de
control por defecto. `PICO_ALL_CONTROLS_SECONDS` sólo admite 120–180 s para
mantener margen frente al watchdog temporal de 300 s. Permite cabeza, ambos
grips/brazos, joysticks de cintura/elevador/chasis, `X`, `A`, `B`, gatillo
derecho y clicks de joystick. `X` y `B` deben usarse por pares, y cualquier
click que conmute protección de fuerza debe repetirse para intentar restaurar
el estado inicial. El gatillo izquierdo sigue reasignado a `Y`/enable: no está
disponible como cierre de mano izquierda; sólo su flanco ascendente se publica,
pero el operador no debe repetirlo durante la sesión. En los
últimos 30 s se exige volver al modo en sitio y cerrar captura; en los últimos
10 s, dejar toda entrada neutra. Al vencer, perder enable, actuar el watchdog,
recibir una señal o fallar cualquier comprobación, el script solicita STOP.
El resumen final demuestra entradas vistas en el log, no el efecto físico ni
el modo/protección final; éstos se verifican visualmente. Antes de editar se
comprobó el backend desarmado (`vr_status=0`, `operation_type=1`,
`enable_control=0`). La sintaxis, ayudas, rango y rechazo no-TTY quedaron
validados sin START ni movimiento. El preflight intenta además recuperar ADB
TCP a partir del peer XR directo y sólo lo acepta si `ro.serialno` coincide;
no fija la IP DHCP en el repositorio.

**VERIFICADO SIN START a las 10:51:** XR quedó otra vez en `vr_status=1`; el
preflight exacto del modo físico devolvió paros `0,0`, baterías 77,2/77,8 %,
cargador desconectado, articulaciones inmóviles, `HW_TYPE=cruzr_s2_v1`,
`TELE_DEVICE=pico`, `transmit=local` y tarea activa
`teleoperation/cruzr_clamp_pico_teleoperation`. Se validaron sintaxis, ayuda,
rechazo no-TTY, cancelación interactiva antes de START, `git diff --check` y
estado final `operation_type=1`, `enable_control=0`. La micromaniobra física
continúa pendiente de que el operador ejecute el lanzador local.

**DECISIÓN ANTERIOR SUPERADA SÓLO PARA ESTE DIAGNÓSTICO:** seguía descartado
ampliar el timeout hasta que el propietario lo autorizó explícitamente. La
excepción instalada es 300 s y conserva STOP; siguen descartados eliminar la
ruta, devolver un heartbeat ficticio o declarar resuelta la incompatibilidad.
La solución de producción continúa siendo un backend PC oficialmente
compatible o el componente oficial que genere el heartbeat real.

### 8.11 Parada rápida y limpia del servicio del PC

El drop-in
[`../../config/systemd/system/ubt-controller.service.d/30-service-lifecycle.conf`](../../config/systemd/system/ubt-controller.service.d/30-service-lifecycle.conf)
configura `SIGTERM`, `KillMode=mixed` y `TimeoutStopSec=15s`. Corrige una parada
vendor que consumía el timeout completo de 90 segundos. Está pendiente de una
validación final y todavía no debe considerarse instalación estable.

**OBSERVADO el 25 de agosto:** el drop-in `30-service-lifecycle.conf` no estaba
instalado; `systemctl cat` sólo mostró `20-cruzr-clamp.conf`. Al detener el
backend para instalar el timeout de heartbeat, systemd agotó los 90 s y mató
`RoboticsServiceProcess`, dejando temporalmente la unidad en `failed`. No
quedaron procesos ni listeners y `systemctl reset-failed` la devolvió a
`inactive/dead`. No confundir este fallo de lifecycle con una ejecución del
backend de 300 s.

### 8.12 Compatibilidad de los scripts locales con v0.2.0

Los scripts de movimiento y recuperación del repositorio ya no esperan la
imagen anterior `zs2_motion-v0.26.10`. Se migraron a
`utars-integration:zs2_motion-v0.2.0` y a los hashes oficiales observados en el
robot actual.

Cambios relevantes:

- metas de caja v0.2.0 validadas por hash:
  - clamp: `531f02cd9b3922142d66944633d35f717f50b6bd5a9a17c9ac7d770edd010b8f`;
  - depósito: `88179f36bfa17aa1e161792680ece2cd716ca0c7cc457ee5c9135e0dd5172f11`;
  - apertura: `02df67780fd37ee45d287a1e8a103f5e299c653481137b9e94895130d01f7a3d`;
- `cruzr/wave_arm.xml` cambió en v0.2.0 y ya no retorna a cero; los scripts
  envían `cruzr/home` después de esa demostración;
- la plantilla bilateral local se reconstruyó a partir de las poses v0.2.0 y
  termina explícitamente en cero, pero **no se instaló en el robot** durante la
  migración;
- se eliminó el argumento incompatible `--no-daemon` y se usa
  `ROS2CLI_DISABLE_DAEMON=1`;
- las comprobaciones de “acción ocupada” usan estados activos y no el número
  persistente de clientes;
- la recuperación trata `DO_RESET` como opcional cuando el task manager está
  libre y falla de forma segura si está bloqueado sin reset disponible;
- los hashes de las 26 tareas y tres metas de manos existentes continuaron
  coincidiendo con v0.2.0.

Se validaron sintaxis Bash, XML, hashes y modos `--check`. Durante esta
migración no se instaló ninguna tarea, no se alteró configuración del robot y
no se produjo movimiento. Un preflight posterior llegó correctamente al gate
de cargador y se detuvo al detectar `CHARGER_CONNECTED=1`.

### 8.13 Límite exacto entre cambios del robot y cambios del PC

Cambios relevantes **dentro del robot**:

- actualización desde la build anterior al paquete genérico v0.2.0;
- configuración actual de abrazaderas `HW_TYPE=cruzr_s2_v1`;
- `TELE_DEVICE=pico` y `transmit=local` en los componentes inspeccionados;
- mapas, waypoints y nombres ROS conservados según las comprobaciones
  realizadas.

Cambios que existen **sólo en el PC**:

- IP Ethernet `192.168.11.250/24`;
- regla udev, locale neutral y orden de arranque;
- `enable_foot_switch=0`;
- perfil `arm=clamp`;
- parche reversible de selección de efector y gatillo izquierdo;
- unidad de UI bajo demanda, preflight y lifecycle de systemd.

No se cambió en el robot ningún nombre a `walker28_web`; ese texto no aparece
en el sistema inspeccionado. `walker28` sigue siendo únicamente el
`channel_name` del backend PC. Tampoco se renombraron `/pico_vr/*`,
`/mc/teleoperation/*`, `signal_server` ni `rtm_receiver`.

Sí existió otro cambio de referencias a topics, ajeno a PICO: para navegar con
el workbin sujeto, `cruzr_cargo_perception_profile.sh` redirige temporalmente
las entradas de nube de puntos del costmap:

```text
/upub_od_waistpc  -> /cruzr/cargo_transit/waistpc_suppressed
/upub_od_bottompc -> /cruzr/cargo_transit/bottompc_suppressed
/upub_od_headpc   -> /cruzr/cargo_transit/headpc_suppressed
```

El objetivo era evitar que las cámaras registrasen la propia caja transportada
como obstáculo dinámico. LiDAR frontal, mapa, localización, odometría, bumpers
y paros permanecían activos. El orquestador guarda el archivo original, usa un
trap de salida y lo restaura byte a byte incluso ante una interrupción. El
último preflight registrado devolvió `CARGO_PERCEPTION_PROFILE=disabled`, es
decir, las tres entradas originales estaban restauradas. Este perfil no cambia
el canal `walker28` ni los topics de teleoperación.

## 9. Acciones intentadas que no solucionan el problema

| Acción | Resultado | Decisión |
|---|---|---|
| Pulsar `Y` una vez | sólo contacto capacitivo; no hay clic mecánico | **DESCARTADO** en este mando |
| Mantener `Y` pulsado | `key.b_y` sigue en cero | **DESCARTADO** en este mando |
| Pulsar `X` dos segundos | un evento `key.a_x=1` aislado; después `key.a_x=0` y `BUTTONS_SEEN=NONE` | no considerar resuelto; recuperar modo `ControllerActive` y repetir escucha directa |
| Configurar operación sin pedal | backend acepta `enable_foot_switch=0` | soporte de configuración verificado; prueba física pendiente |
| Reiniciar servicio del PC | restaura detección PICO | útil para discovery, no corrige build |
| Ver `Working` en PICO | confirma sólo PICO ↔ PC | no usar como autorización de movimiento |
| Pulsar `A` | no resuelve heartbeat | `A` es reset de tren superior, no reparación de enlace |
| Cerrar UI y usar cliente diagnóstico | aísla transporte | diagnóstico válido, no solución final |
| Confiar en `AnswerSession: sent heartbeat` | heartbeat equivocado | **DESCARTADO** |
| Usar tarea `s2_clamp_pico_teleoperation` | parámetros de otro robot | **DESCARTADO** |
| Desactivar o fabricar heartbeat | ocultaría pérdida de enlace | **PROHIBIDO; no realizado** |
| Ampliar timeout a 300 s | ventana diagnóstica solicitada por el propietario | **INSTALADO; STOP conservado; runtime pendiente** |

## 10. Tabla rápida de fallos y recuperación

| Síntoma | Comprobación | Causa probable | Acción segura |
|---|---|---|---|
| PICO queda en `Connecting` | WLAN/IP, `adb devices`; TCP 63901 | app/red/servicio XR no unidos | misma WLAN, `Head + Controllers` → `Send data`; después reiniciar sólo lo necesario |
| `Working`, pero backend no detecta visor | logs `device found/missing` | backend arrancó antes del stream | reiniciar servicio con PICO ya conectado |
| TCP 63901 existe, pero `vr_status=0` | consulta local `detect` | app reconectada pero tracking no rearmado | `Head + Controllers` → `Send data` → `Working` |
| Heartbeat ausente con red correcta | selector superior derecho de `192.168.11.3` | robot fuera de `遥操模式` | seleccionar Remote control mode antes de START |
| Backend indica `Arm type is: gripper` | log del PC | tipo genérico incorrecto para abrazaderas | mantener `arm=clamp`; abortar la sesión |
| ADB no autorizado | `adb devices -l` | autorización, cable o udev | aceptar diálogo; revisar cable/regla; no usar root ADB |
| Datos con números inválidos | locale del servicio | coma decimal española | mantener `LC_NUMERIC=C` |
| No conecta con robot | ping `.2/.3`, config WS | IP/ruta/cable/config | restaurar `192.168.11.250/24`; no tocar ROS |
| DataChannel no abre | logs de señalización/RTM | canal, servidor o cliente duplicado | una sola UI; revisar `.3:4000` y `channel_name` |
| `Y` no habilita | comparar `touch.b_y`/`key.b_y` | pulsador mecánico Y no registrado | el gatillo izquierdo sólo es un workaround diagnóstico no validado; pedir revisión/flujo oficial a DSA |
| PC recibe `enable=0` repetidamente | log backend | watchdog sin heartbeat | no confundir con E-stop físico |
| Topic existe pero `echo` no devuelve | `ros2 topic info/echo` | endpoints sin muestras activas | no considerar listo sólo por discovery DDS |
| PICO se duerme/desconecta | ADB/TCP desaparecen | suspensión/USB | neutralizar, parar, reconectar y reiniciar servicio |
| UI oficial y cliente diagnóstico abiertos | `ss`/procesos | dos clientes compitiendo | cerrar diagnóstico; conservar una sola UI |
| Se desea probar PICO directo | revisar procesos/listeners del PC y peers de `.3:4000` | el servicio PC puede arrancar automáticamente | detener backend, UI y PC Service; demostrar un único peer antes de cualquier movimiento |

## 11. Procedimiento seguro para reanudar otro día

### 11.1 Antes de tocar software

1. Confirmar abrazaderas vacías y correctamente instaladas.
2. Robot en `home`, cargador desconectado y chasis detenido.
3. Envolvente completa de brazos/cabeza despejada.
4. Controladores PICO neutros; triggers y grips libres.
5. Nadie tocando el robot y una persona con el paro físico preparado.
6. No pulsar X ni Y durante diagnóstico de sólo lectura.

### 11.2 Snapshot de sólo lectura

En el PC:

```bash
ip -br -4 address
ping -c 2 192.168.11.2
ping -c 2 192.168.11.3
adb devices -l
systemctl status ubt-controller.service --no-pager
ss -tnp | grep -E '192\.168\.67\.|192\.168\.11\.3:4000'
```

En el PICO:

1. `Shared network (connect USB first)`.
2. Esperar `Working`.
3. Seleccionar `Head + Controller`.
4. Activar `Send`.
5. Mantener controladores neutros.

### 11.3 Corrección de versión antes de una nueva prueba

1. Obtener `v0.2.0-dac-beta.2`, hash y release notes de DSA.
2. Comparar manifiestos/imágenes con el `v0.2.0` instalado.
3. Respaldar Motion, Vision, mapas, puntos, configuración uDoke, calibración y
   `HW_TYPE`.
4. Confirmar procedimiento de rollback.
5. Actualizar sólo con el robot inmóvil y la envolvente despejada.
6. Verificar que continúan:
   - `HW_TYPE=cruzr_s2_v1`;
   - `TELE_DEVICE=pico`;
   - `transmit=local`;
   - mapas y waypoints intactos;
   - tarea Cruzr/PICO presente;
   - paros, batería y cargador en estado correcto.

### 11.4 Gate de heartbeat sin movimiento útil

La ventana de 60 s de `probar_pico.sh --gate-only` con timeout temporal de 300 s **no
cumple este gate**. Para validarlo deben observarse heartbeats reales; la mera
ausencia de un STOP dentro de 60 s ya no sirve como evidencia.

Antes de permitir una trayectoria:

1. Abrir una única instancia de la UI oficial.
2. Con operador neutro y paro listo, habilitar la sesión según el SOP.
3. Observar durante al menos 60 segundos:
   - mensajes app `heartbeat` continuos;
   - ausencia de cualquier `No heartbeat for ... seconds`;
   - `tele_operation enable=1` estable;
   - DataChannel abierto sin reconexiones;
   - PICO `Working`;
   - ninguna orden inesperada.
4. Detener desde la UI y confirmar `enable=0`.
5. Repetir una vez para probar inicio/parada limpios.

El propietario autorizó el 25 de agosto una excepción explícita con el timeout
de 300 s: primero para una micromaniobra de un brazo y, después de comprobar
movimiento físico, para una ventana integral supervisada de 120–180 s mediante
`--all-controls`. No es una aprobación de producción ni una validación del
heartbeat. Ambos modos mantienen estabilidad previa de 60 s, preflight fresco
y STOP automático según lo implementado en el lanzador.

Si este gate falla, no se pasa a movimiento.

### 11.5 Primera prueba de movimiento, sólo después del gate

1. Confirmación física completa de seguridad.
2. Ejecutar únicamente la tarea Cruzr/abrazaderas/PICO.
3. Mantener controladores en la postura de referencia durante `init_time=12 s`.
4. Habilitar sólo un intervalo corto y un desplazamiento pequeño.
5. No cerrar grips, no mover chasis y no grabar todavía.
6. Parar, verificar estado y revisar logs antes de ampliar recorrido.
7. Validar después brazos por separado, ambos brazos, cabeza y finalmente base.

## 12. Teleoperación directa sin pasar por el PC

### 12.1 Estado actual

**NO IMPLEMENTADA/NO VERIFICADA CON EL MATERIAL RECIBIDO.** El paquete
inspeccionado implementa explícitamente:

```text
PICO → XRoboToolkit PC Service → ubt_controller → robot
```

El PICO no se conecta directamente al controlador del robot en el flujo
suministrado. La dirección `192.168.11.3:4000` es un servidor de señalización,
no una API directa suficiente para controlar el robot. `signal_server` sigue
activo en Vision y `rtm_receiver` en Motion, pero eso sólo prepara el extremo
robot de la cadena.

La inspección de la web viva cerró una ambigüedad importante: seleccionar
`遥操模式` sólo llama a `work_mode.switch`. La web no aporta tracking,
controladores, calibración, deadman, heartbeat ni el cliente DataChannel PICO.
La página `/vr` sólo recibe vídeo de la cámara del robot. Por tanto, cambiar el
modo y ver una pantalla “online” no demuestra un camino directo.

Si DSA afirma que existe conexión directa, debe proporcionar al menos uno de
estos elementos concretos:

- APK PICO diferente y su pantalla exacta de configuración del robot;
- nombre/versión de un servicio embarcado adicional;
- endpoint, autenticación, canal y protocolo soportados;
- procedimiento oficial de START/STOP y heartbeat;
- matriz compatible con este Cruzr S2 v0.2.0 y abrazaderas.

### 12.2 Qué sí puede hacerse sin usar una shell cada vez

Una vez corregida la compatibilidad, el PC puede quedar como appliance:

- servicio `ubt-controller.service` automático;
- PICO conectado por USB/red compartida;
- UI oficial como único control de sesión;
- sin SSH, comandos manuales ni terminal durante la operación.

Eso elimina la dependencia operativa de la shell, pero **no elimina el PC**.

### 12.3 Qué exigiría eliminar realmente el PC

Sería un desarrollo nuevo y debería cubrir, como mínimo:

- SDK nativo PICO/OpenXR y permisos Enterprise;
- adquisición de cabeza/controladores/trackers;
- transformación de frames, calibración y retargeting Cruzr;
- cliente de señalización y DataChannel compatible;
- esquema exacto de tele-data;
- heartbeat de aplicación y deadman;
- estado de paros, colisiones, fuerza y modo del robot;
- autenticación, certificados y reconexión segura;
- UI de armado/desarmado y STOP;
- grabación sincronizada y trazabilidad;
- validación de latencia, pérdida de paquetes y parada segura.

No es aceptable copiar el protocolo parcialmente ni simular heartbeat para
“hacerlo funcionar”. Primero debe pedirse a DSA si existe una APK directa,
servicio embarcado o SDK oficialmente soportado.

### 12.4 Prueba decisiva sin movimiento para un supuesto modo directo

1. Detener por completo backend, UI y PC Service; comprobar que no quedan
   procesos ni listeners 8082/63901.
2. Dejar el robot en `home`, abrazaderas vacías y seleccionar `遥操模式`.
3. Abrir en el PICO únicamente la aplicación/procedimiento directo indicado
   por DSA.
4. Sin armar movimiento, observar en Vision las conexiones a TCP 4000 y en
   Motion las tasas/muestras de `/pico_vr/*`.
5. Exigir que aparezca un peer nuevo atribuible al PICO y datos frescos. Las
   conexiones internas `.2 ↔ .3` no cuentan.
6. Verificar heartbeat, STOP y estado de habilitación durante 60 s antes de
   permitir cualquier movimiento.

Con la aplicación XRoboToolkit suministrada no se encontró un menú documentado
para introducir directamente la IP del robot. Si no aparece el peer/dato
nuevo, la prueba termina ahí y se restaura `JoystickMode`.

## 13. Pendientes priorizados

### P0 — bloquean cualquier movimiento PICO

- [ ] Seleccionar y verificar `遥操模式 / Remote control mode` en
  `http://192.168.11.3`.
- [ ] Reactivar `Head + Controllers / Send data / Working` y confirmar
  `vr_status=1`.
- [ ] Ejecutar el preflight PC y comprobar `arm=clamp`.
- [ ] Obtener `utars-udoke-config-v0.2.0-dac-beta.2.tar.gz` y SHA-256.
- [ ] Obtener matriz de compatibilidad firmada: robot, PICO APK, XR PC Service,
  controller, UI, efector y Ubuntu.
- [ ] Confirmar origen, frecuencia y payload del heartbeat de aplicación.
- [ ] Aplicar/validar la build correcta con backup y rollback.
- [ ] Superar heartbeat estable durante al menos 60 segundos.
- [ ] Confirmar que STOP por pérdida de heartbeat sigue funcionando.
- [ ] Verificar que la tarea oficial es
  `teleoperation/cruzr_clamp_pico_teleoperation`.

### P1 — necesarios antes de grabar demostraciones

- [ ] Validar inicio/parada desde una sola UI oficial.
- [ ] Confirmar el modo sin pedal o adquirir el deadman recomendado.
- [ ] Medir latencia y jitter PICO → PC → robot.
- [ ] Probar desconexión USB, suspensión PICO, caída Ethernet y recuperación.
- [ ] Confirmar los umbrales de fuerza y la protección de colisión.
- [ ] Validar `B`: inicio, parada, ubicación y formato del episodio.
- [ ] Identificar la acción teleoperada 20D anterior a la respuesta mecánica.
- [ ] Auditar sincronización RGB/estado/acción/fuerza/timestamps.
- [ ] Documentar calibración y postura neutral reproducible.
- [ ] Confirmar que `channel_name=walker28` es el identificador correcto.

### P2 — robustez industrial y evolución

- [ ] Convertir el PC en appliance con healthchecks y panel de estado.
- [ ] Versionar copias sanitizadas de configuración/wrapper/systemd.
- [ ] Añadir un preflight automático que no pueda mover el robot.
- [ ] Rotar y archivar logs por sesión con timestamps sincronizados.
- [ ] Estudiar soporte oficial de PICO directo sin PC.
- [ ] Definir procedimiento de actualización que preserve mapas, calibración y
  `HW_TYPE`.
- [ ] Ejecutar campaña de datos sólo después de auditar un episodio piloto.

## 14. Preguntas exactas pendientes para DSA

1. Please provide the exact
   `utars-udoke-config-v0.2.0-dac-beta.2.tar.gz` package, SHA-256 checksum,
   release notes and rollback procedure.
2. Does the generic `utars-udoke-config-v0.2.0` package contain the same DAC
   teleoperation components? If so, please provide component versions/hashes.
3. Which robot component must send `{"type":"heartbeat"}` to
   `ubt_controller 5.3.0`, at what frequency and over which channel?
4. Is Ubuntu 24.04 + XRoboToolkit PC Service 1.0.0 for 24.04 +
   `ubt_controller 5.3.0_ubuntu22.04` an approved combination?
5. Is no-pedal operation with `enable_foot_switch=0` officially supported, and
   what is the required deadman behavior?
6. Please confirm the official task for Cruzr S2 with clamps and PICO:
   `teleoperation/cruzr_clamp_pico_teleoperation`.
7. Please define the meaning and safe values of the 120 N wrench thresholds.
8. Is there an officially supported direct PICO-to-robot mode without the PC?
9. Which component exports a synchronized LeRobot episode when `B` is used?
10. Which observable states constitute “ready for physical teleoperation”?
11. The SDK requires `MC_SCENE=DAC`, but the inspected containers expose an
    empty `MC_SCENE`. Is this expected for our v0.2.0 build?
12. Where should the documented `pico_control` executable be installed, and
    which package/version provides it?
13. Does “start teleoperation on the web” refer to the PC Electron HMI or to a
    robot webpage different from the `work_mode.switch` selector at
    `192.168.11.3`?

## 15. Evidencia reproducible y comandos de diagnóstico

Estos comandos son de sólo lectura. No iniciar tareas ROSA ni pulsar `Y` para
recoger un snapshot.

### PC

```bash
dpkg-query -W -f='${binary:Package}\t${Version}\t${Architecture}\n' \
  roboticsservice ubt-controller ubt-remote-control adb

systemctl show ubt-controller.service \
  -p UnitFileState -p ActiveState -p SubState -p ActiveEnterTimestamp -p MainPID

systemctl --user is-active ubt-remote-control.service || true
pgrep -af 'ubt_controller|RoboticsServiceProcess|ubt-remote-control' || true
ss -Hlntp | grep -E ':(8082|63901)\b' || true

adb devices -l
adb shell getprop ro.product.model
adb shell getprop ro.build.version.release
adb shell dumpsys package com.xrobotoolkit.client | \
  grep -E 'versionName|versionCode'

ip -br -4 address
ss -ltnp | grep -E ':63901|:8082'
ss -tnp | grep -E '192\.168\.67\.|192\.168\.11\.3:4000'
```

### Robot Motion

```bash
cat /etc/walker/system/soft_version

for c in \
  walker-motion.hw-1 \
  walker-motion.t800_mc_server-1 \
  walker-motion.manipulation_robot_app-1 \
  walker-motion.rtm_receiver-1
do
  docker inspect --format \
    '{{.Config.Image}} {{range .Config.Env}}{{println .}}{{end}}' "$c" |
    grep -E '(^glcr|HW_TYPE=|TELE_DEVICE=|transmit=)'
done
```

Para ROS 2 en esta plataforma, desactivar el daemon evita los fallos de
`rclpy`/XML-RPC ya observados:

```bash
export ROS2CLI_DISABLE_DAEMON=1
ros2 topic info /pico_vr/tele_data
ros2 topic info /mc/teleoperation/enable
```

En Vision, una prueba de supuesto PICO directo debe distinguir conexiones
internas de un peer externo:

```bash
ss -Hntp | grep ':4000' || true
```

No considerar “PICO conectado” si sólo aparecen peers `192.168.11.2` y
`192.168.11.3`.

### Logs relevantes

```text
PC:
  /opt/ubt/ubt_controller/logs/ubt_controller.log*
  /opt/ubt/ubt_controller/logs/rtm_pybind.log

Robot Motion:
  /etc/walker/log/motion/
```

Patrones útiles:

```text
No heartbeat for 10 seconds
tele_operation
datachannel is open
Teleoperation enabled
Teleoperation disabled
AnswerSession: sent heartbeat
```

## 16. Archivos relacionados del repositorio

- Paquete externo e instalación:
  [`../../utats/README.md`](../../utats/README.md)
- Guía de teleoperación, captura y VLA:
  [`../vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md`](../vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md)
- Checklist de sesión:
  [`../vla/templates/TELEOP_SESSION_CHECKLIST.md`](../vla/templates/TELEOP_SESSION_CHECKLIST.md)
- Activación segura del VLA:
  [`../guides/CRUZR_S2_VLA_SAFE_ENABLEMENT.md`](../guides/CRUZR_S2_VLA_SAFE_ENABLEMENT.md)
- Catálogo verificado de capacidades y tareas instaladas:
  [`../guides/CATALOGO_FUNCIONALIDADES_CRUZR_S2.md`](../guides/CATALOGO_FUNCIONALIDADES_CRUZR_S2.md)
- Arranque y recuperación específicos de v0.2.0:
  [`../guides/CRUZR_V020_BOOT_GUARD.md`](../guides/CRUZR_V020_BOOT_GUARD.md)
- Preguntas y estado de soporte con DSA:
  [`../support/UBTECH_SUPPORT_TRACKER.md`](../support/UBTECH_SUPPORT_TRACKER.md)
- Informe de actualización base:
  [`../../upgrade.txt`](../../upgrade.txt)
- Resumen enviable de la actualización:
  [`../../upgrade_summary.txt`](../../upgrade_summary.txt)
- Regla udev PICO:
  [`../../config/udev/51-pico-ubt.rules`](../../config/udev/51-pico-ubt.rules)

El SOP PDF suministrado se conserva localmente dentro de `utats/` y está
ignorado por Git debido a su tamaño/origen externo.

## 17. Registro de cambios y pruebas futuras

Añadir cada sesión al principio de esta tabla. No borrar resultados fallidos:
son parte de la evidencia.

| Fecha/hora | Cambio o prueba | Resultado | Evidencia | Próxima decisión |
|---|---|---|---|---|
| 2026-08-25 12:27–12:44 PC/PICO | primer `--all-controls` llegó a enable pero abortó; corrección de gatillo por flanco | una sola pulsación cruda duró 0,567 s y el backend de nivel alternó `enable 0→1→0`; el script detectó la pérdida y envió STOP, sin trip de heartbeat. A las 12:31 se detectó otra sesión inesperadamente activa con ambos grips altos y se envió STOP inmediato. Se sustituyó el mapeo por pulso sólo en flanco ascendente, más gates de neutralidad y liberación; activo `5083e9f0…`, backup de nivel/300 s `40b440f4…`. A las 12:44 `--check` recuperó ADB/stream y pasó 7/7; final `vr_status=1`, `operation_type=1`, `enable_control=0`, UI inactiva; sin START ni movimiento durante la corrección | timestamps y estados del log backend, STOP WS, test aislado `[0,1,1,1,0,1]`, build Python 3.10 reproducible, hashes, `bash -n`, systemd, listeners y preflight 7/7 | repetir una sola vez `--all-controls` con preflight físico fresco; el operador aprieta y suelta una vez cuando aparezca TOQUE AHORA |
| 2026-08-25 12:20–12:25 PC/PICO/Motion/Vision | propietario ordena usar Wi-Fi del robot para todos los dispositivos concernientes al robot, salvo Internet | perfil `Cruzr S2-0669 1` conserva DHCP y recibe ruta persistente `192.168.11.0/24 via 192.168.42.2`, `ipv4.never-default=yes` e `ignore-auto-dns=yes`; toda `.11.0/24` y `.42.0/24` robot pasan por `wlx80afcad40bd6`; la única ruta por defecto/Internet sigue en `wlo1`/`DSA CORPORATE`. El lanzador PICO descubre ruta/IP, exige ese SSID y ya no requiere `eno1`; se migraron los dos scripts heredados que bloqueaban por Ethernet. `--check-motion-ready` pasó en 16 s con paros 0/0, baterías 64,8/66,1 %, cargador fuera, joints inmóviles y tarea PICO. Los checks generales alcanzaron Vision/topics y Motion por Wi-Fi; `install_wave_both_arms.sh --check` pasó. Sin START ni movimiento | NetworkManager persistente/runtime, rutas kernel, inventario IP versionado, ping/TCP Motion/Vision/Internet, ADB/63901, `--check` 7/7, `--check-motion-ready`, checks generales y `bash -n` | repetir `--all-controls` desde cero sólo con confirmación física fresca; conservar `DSA CORPORATE` como default y no reintroducir dependencia Ethernet |
| 2026-08-25 12:17–12:20 PC | primer intento de `--all-controls`, abortado antes de START | tras la confirmación, el preflight Motion agotó 35 s y no envió START. Diagnóstico: `eno1` perdió físicamente portadora e IP (`NO-CARRIER`, `carrier=0`); la ruta a `.2/.3` cayó por `DSA CORPORATE` y SSH/ICMP fallaron. Ambas Wi-Fi del PC y PICO permanecieron conectadas. El preflight revalida ahora carrier, IP, ruta, ping y TCP 22 inmediatamente antes de consultar paros; el mismo caso falla en menos de un segundo con causa explícita | salida del operador, `ip`, sysfs, NetworkManager, ping/TCP/SSH, `bash -n`, `--check-motion-ready`, `git diff --check`; backend seguía STOP | **SUPERADO:** el propietario eligió Wi-Fi Cruzr para todos los dispositivos del robot; no reconectar ni volver a exigir Ethernet |
| 2026-08-25 12:08–12:16 PC/PICO | propietario autoriza probar todos los comandos del headset por ≥2 min | añadido `probar_pico.sh --all-controls`: preflight completo, 60 s neutros, ventana activa predeterminada de 120 s y configurable 120–180 s, mapa de controles, avisos de retorno a modo en sitio/cierre de captura/restauración por pares, resumen de entradas y STOP automático; gatillo izquierdo permanece reservado a enable/Y; backend estaba desarmado; no se envió START ni hubo movimiento durante el cambio. Una caída transitoria dejó ADB offline y dos sockets XR; el backend pasó a `device missing`/`vr_status=0` pese a la pantalla Working. Reiniciar sólo XRoboToolkit y reseleccionar Head+Controllers/Send data recuperó `vr_status=1`; el `--check` final pasó con stream directo, clamp/300 s y backend desarmado | `bash -n`, compilación del parser, ayudas de ambos scripts, límites 119/181 rechazados, modo válido bloqueado sin TTY, `git diff --check`, `adb`, ARP, `nmap`, `nmcli`, logcat, journal, WS 8082 y `--check` 7/7 | ejecutar una sola vez y localmente `./scripts/teleoperation/probar_pico.sh --all-controls` tras confirmar de nuevo la zona física; verificar visualmente modo en sitio e inmovilidad antes de recuperación |
| 2026-08-25 11:46–11:53 PC/PICO | migración a WLAN local sin túnel XR | `wlo1` conservó `DSA CORPORATE`; `wlx80afcad40bd6` y PICO usaron `Cruzr S2-0669` (`.215`/`.211`); XR conectó directo a TCP 63901, reverse quedó vacío, `vr_status=1`, `operation_type=1`, `enable_control=0`; lanzador acepta ADB USB o Wi-Fi por serial físico; sin movimiento | NetworkManager/IP/ping bidireccional, log Unity, `ss`, WS 8082, reverse vacío, `bash -n`, `--check` completo | retirar USB; tras reinicio redescubrir DHCP y ADB TCP; conservar `DSA CORPORATE`; repetir sólo `--check` antes de cualquier gate físico |
| 2026-08-25 17:14–17:20 Motion | recuperación a home después de movimiento PICO | el STOP del PC dejó `operation_type=1`, `enable_control=0`, pero la tarea TeleopMode siguió activa; el operador seleccionó `auto_task` y home terminó; reportó paso casi rozando con abrazaderas bajas. Corrección local: `--home` usa ahora la tarea v0.2.0 `cruzr/open_arm_before_home` (SHA `ec2c187c…`), que abre primero ambos brazos y luego hace cero; el detector reconoce postura teleoperada y esta nueva tarea como home | WebSocket Control Center `workMode=teleop`, acción activa, logs Motion, XML/hash de fábrica, reporte del operador; `bash -n`, ayudas, `git diff --check` y `cruzr_blue_workbin_cycle.sh --check` sin movimiento | validar físicamente la secuencia nueva sólo desde una postura PICO mínima, abrazaderas vacías, envolvente libre y persona en el paro; no volver a usar `cruzr/home` directo tras teleoperación |
| 2026-08-25 10:50–10:52 PC/Motion | propietario autoriza teleoperación física real; lanzador de micromovimiento | `probar_pico.sh` sin argumentos selecciona brazo derecho; `--move-left-arm` el izquierdo; 60 s estables, grip exclusivo, 2–3 cm/5 s máximo, STOP al soltar/fallar; XR recuperado a `vr_status=1`; preflight Motion exacto OK (paros 0,0; batería 77,2/77,8 %; cargador fuera; joints inmóviles; task Cruzr/PICO); cancelación seca dejó STOP; no se envió START físico | scripts, `bash -n`, ayuda, no-TTY, cancelación TTY, WS 8082, ADB, ROS 2 y log Motion | ejecutar localmente primero brazo derecho sólo con confirmación física fresca; reportar postura/recorrido/alarmas antes de probar el izquierdo |
| 2026-08-25 10:38 PC / 16:37–16:38 Motion | primera ventana runtime con timeout 300 s | DataChannel abrió antes de enable; `enable=1` y `CoreMode 7` sostenidos ~46,1 s; protección y chequeos de fuerza de ambos brazos activos; cero movimiento con 4.530 muestras por mando y grips siempre `false/0.0`; tres pulsaciones finales alternaron `0→1→0`, el script envió STOP; final `operation_type=1`, `enable_control=0`, Motion `NotTele`; a las 10:43 `vr_status=0` | `ubt_controller.log`, `rtm_pybind.log`, `robot_app`, traza del lanzador y confirmación del operador | no repetir `probar_pico.sh` como prueba de movimiento; rearmar XR y completar primero el gate de 60 s con un solo toque; diseñar aparte una micromaniobra supervisada de un brazo usando grip y nuevo preflight físico |
| 2026-08-25 10:35 PC | observabilidad del lanzador | `--check` muestra 7 etapas con timestamp; timeouts de 5 s para ADB/systemd/journal/WS; `CRUZR_TELEOP_DEBUG=1` da línea/comando; fallo simulado explícito; estado final STOP y `vr_status=1` | salida normal, traza con serial inexistente, `bash -n`, `git diff --check`, WS 8082 | el operador puede repetir `--check`; no ejecutar gate hasta completar confirmación física |
| 2026-08-25 10:29 PC/PICO | recuperación de reconexión VR | causa: app dirigida a `127.0.0.1:63901`, reverse ausente y socket viejo; restaurado `adb reverse`, reiniciada sólo XRoboToolkit; TCP establecido, `vr_status=1`, `ControllerActive`; backend `operation_type=1`, `enable_control=0`, UI inactiva; `--check` completo OK | ADB, `sys.usb.config=mtp,adb`, `ss`, log Unity, WS 8082 y lanzador canónico | no pulsar gatillo ni ejecutar ventana hasta confirmar preflight físico actual y `遥操模式` |
| 2026-08-25 10:20 PC | timeout heartbeat 10→300 s autorizado por el propietario | parche reproducible instalado; sólo cambia el operando del comparador, conserva STOP; activo `40b440…`, backup 10 s `0f0d3414…`; backend/UI/XR detenidos, unidad `inactive/dead` y habilitada; sin runtime ni movimiento | validación bytecode Python 3.10, SHA-256, estado systemd, procesos y listeners | repetir preflight físico/lógico; arrancar sólo localmente; `probar_pico.sh` es ventana diagnóstica de 60 s y no valida heartbeat |
| 2026-08-25 durante inspección 10:13 PC | incidencia de inspección local | una heredoc mal formada ejecutó fugazmente el backup vendor fuera de su directorio; abortó antes de inicializar por ausencia de `pem/vr_key.pem`; no sustituyó archivos, no abrió listeners, no cambió el servicio y no hubo movimiento | excepción local `FileNotFoundError`, hashes y snapshot posterior de procesos/systemd | usar sólo lectura binaria mediante `Path.read_bytes`; ya corregido en la sesión |
| 2026-08-25 después del gate 09:53 | origen del heartbeat y opción de omitir watchdog | UI 4.1.0 revalidada sin emisor; `Publisher.callback` recibe el tipo `heartbeat` por el canal inverso RTM del robot; desactivar/puentear watchdog descartado | source maps de `app.asar`, bytecode instalado de `publisher.py` | pedir backend PC compatible o componente oficial si el robot debe permanecer inmutable |
| 2026-08-25 09:53 PC | primer gate con lanzador local y toque único | START 09:53:46.142; `enable=1` 09:53:49.845; watchdog 09:53:56.718 (`10,576 s` desde START, `6,873 s` desde enable); `enable=0` 09:53:57.224; final `operation_type=1`, `enable_control=0`, UI inactiva; sin movimiento físico y con voz del robot | salida del operador, `ubt_controller.log`, consulta WS y systemd | no repetir; resolver con proveedor el heartbeat de aplicación |
| 2026-08-25 después del gate 09:53 | corrección de aborto local | se observó que `Ctrl+C` durante la confirmación enviaba STOP pero el `read` podía continuar; handler cambiado a STOP + salida 130/143; sin prueba física durante el cambio | salida del operador, `bash -n`, prueba aislada del handler y `git diff --check` | conservar el aborto duro; no usar el gate hasta resolver heartbeat |
| 2026-08-25 después del gate 09:44 | lanzador local solicitado por el operador | añadido `scripts/teleoperation/probar_pico.sh`; briefing, orden local y progreso cada 5 s, ejecución delegada al gate canónico; sin prueba física | `bash -n`, bloqueo no-TTY y `git diff --check` | el operador lo ejecuta manualmente desde el terminal local; no coordinar el toque por chat |
| 2026-08-25 después del gate 09:44 | eliminación de latencia del chat en el procedimiento | añadido `--gate-local`: TTY obligatorio, señal local posterior al armado, monitor 60 s y STOP automático; sin ejecución física durante el cambio | `bash -n`, `--help`, `git diff --check` | ejecutar desde terminal local con dos personas; conservar el chat sólo para revisar logs |
| 2026-08-25 09:44 PC / 15:44 robot | segundo gate, gatillo mantenido | entrada cruda fija en `trigger_value=1.0`/`b_button=true`, pero `enable` alternó cada ~0,51 s por repetición del conmutador Y; STOP automático; movimiento físico pendiente de confirmación explícita del operador | log PC `ubt_controller.log`, estado final WS | confirmar resultado físico; corregir a un toque menor de 0,5 s; no repetir hasta validar script y preflight |
| 2026-08-25 09:39 PC / 15:39 robot | primer gate actual con PICO por ADB reverse | gatillo→`b_button=true`→`enable=1`→Motion `CoreMode 7`; las pulsaciones repetidas alternaron `enable`; STOP automático, sin movimiento físico; TTS de activación oído | log PC `ubt_controller.log`, log Motion `robot_app`, confirmación visual del operador | aislar semántica de Y antes del gate de 60 s |
| 2026-08-25 | migración de scripts locales al runtime v0.2.0 | sintaxis/XML/hashes y `--check` válidos; sin instalación ni movimiento; gate de cargador bloqueó como debía | scripts y hashes del robot | conservar cambios; desconectar cargador sólo antes de una prueba física autorizada |
| 2026-08-25 | inspección de la web viva del robot | el selector sólo ejecuta `work_mode.switch`; `/vr` sólo recibe cámara; no hay cliente PICO directo visible | assets servidos por `192.168.11.3` | pedir a DSA APK/módulo/procedimiento directo exacto |
| 2026-08-25 | recuperación tras teleoperación y separación de clientes | `cruzr/home` terminó `SUCCEED/status=4`; `JoystickMode` restaurado; stack PC detenido sin procesos/listeners | log de Motion, ROSA, systemd, `pgrep`, `ss` | nuevo preflight desde estado conocido; no arrancar dos clientes |
| 2026-08-25 | auditoría de v0.2.0 | `signal_server` y `rtm_receiver` activos; `MC_SCENE` vacío; `pico_control` ausente; nombres ROS/canal no renombrados | contenedores/env/procesos/búsqueda local | aclarar diferencias del SDK con DSA |
| 2026-08-24 12:28 | reinicio ordenado del stack PC y rearme del PICO | preflight completo aprobado: red, ADB, TCP 63901, tracking `vr_status=1`, backend 5.3.0 y `arm=clamp`; UI inactiva | lanzador local, systemd, WebSocket 8082 | obtener gate físico fresco y validar heartbeat durante 60 s |
| 2026-08-24 12:25 | selección manual del modo web exigido por DSA | selector superior muestra `遥操模式`; el PICO aún devuelve `vr_status=0` | captura web y preflight local | rearmar `Head + Controllers / Send data / Working` y repetir gate |
| 2026-08-24 12:08–12:15 | perfil PC `arm=clamp`, UI bajo demanda y preflight reproducible | red/ADB/TCP/backend válidos; tras reiniciar app falta rearmar tracking (`vr_status=0`) | systemd, WebSocket 8082, ADB, TCP 63901 | activar tracking y `遥操模式`; ejecutar gate único |
| 2026-08-24 12:13 | DSA responde al diagnóstico | exige cambiar la web del robot a `遥操模式` | chat de soporte | probar ese prerrequisito antes de atribuir fallo a build |
| 2026-08-24 11:04 | reinicio de `ubt-controller.service` con PICO conectado | XR detectado tras 21 s; servicio activo | systemd, ADB, TCP 63901 | no pulsar `Y`; resolver build |
| 2026-08-24 10:45–11:07 | pruebas repetidas de START/`Y` y diagnóstico WS | DataChannel abre; `enable=1` temporal; watchdog envía STOP | logs PC/robot | falta heartbeat app |
| 2026-08-24 | inspección de binarios cerrados | watchdog 10 s y tipo `heartbeat` confirmados; ping de señalización diferenciado | bytecode/bibliotecas locales | solicitar DAC beta.2 |
| 2026-08-21 | instalación stack PC/PICO | paquetes instalados; PICO Working | apt/dpkg/ADB | mejorar orden de arranque |
| 2026-08-21 | locale C + espera TCP 63901 + udev | poses legibles y discovery reproducible | diffs systemd/run.sh; regla udev | conservar y validar tras upgrade |

Plantilla para una nueva entrada:

```text
Fecha/hora:
Objetivo:
Estado físico y preflight:
Versiones/hashes:
Cambio exacto:
Comandos o UI utilizados:
Resultado esperado:
Resultado observado:
Logs/timestamps:
Movimiento físico ocurrido: sí/no
Rollback realizado:
Decisión y siguiente gate:
```

## 18. Criterio para declarar la teleoperación resuelta

No basta con que el brazo se mueva una vez. El problema se considerará resuelto
sólo cuando se cumpla todo lo siguiente:

- build exacta y matriz de versiones verificadas;
- PICO y PC reconectan de forma reproducible;
- heartbeat de aplicación estable;
- START/STOP funcionan desde una única UI;
- pérdida de PICO, PC o Ethernet provoca parada segura;
- no hay clientes diagnósticos ni bypasses activos;
- tarea Cruzr/abrazaderas correcta;
- primera prueba limitada sin movimientos inesperados;
- logs y timestamps permiten explicar cada transición;
- un episodio piloto se graba, detiene, exporta y audita;
- DSA confirma los parámetros de seguridad pendientes.

## 19. Relevo mínimo para una nueva sesión de Codex

No reconstruir el diagnóstico desde cero ni reinstalar paquetes. La nueva
sesión debe leer primero este archivo completo y respetar los cambios sin
commit que pueda mostrar `git status`.

### 19.1 Hechos que ya no deben volver a investigarse

- La web de `192.168.11.3` cambia el modo, pero no implementa el cliente PICO.
- `/vr` es recepción de vídeo, no teleoperación de entrada.
- `signal_server` y `rtm_receiver` existen y están activos en el robot.
- El camino PICO → PC → robot llegó hasta DataChannel y datos; falla el
  heartbeat de aplicación esperado por el PC.
- `Working` en PICO, `TeleopMode` en web y topics existentes son condiciones
  parciales, no autorización de movimiento.
- No se renombraron topics, colas ni canales de teleoperación. El perfil de
  carga redirigió temporalmente tres entradas del costmap y el último
  preflight las mostró restauradas (`CARGO_PERCEPTION_PROFILE=disabled`).
- El último estado de movimiento verificado es `home`; no asumir que el
  cargador o la conexión física siguen igual.
- El stack PC está activo para el flujo suministrado: XR y backend activos, UI
  inactiva, `vr_status=1`, `operation_type=1`, `enable_control=0`. No iniciar
  un cliente directo en paralelo.

### 19.2 Primer snapshot, sin movimiento

```bash
cd /home/lacuna/proyectos/Robots/Humanoide
git status --short

systemctl is-active ubt-controller.service || true
systemctl is-enabled ubt-controller.service || true
systemctl --user is-active ubt-remote-control.service || true
pgrep -af 'ubt_controller|RoboticsServiceProcess|ubt-remote-control' || true
ss -Hlntp | grep -E ':(8082|63901)\b' || true

ip -br -4 address
ping -c 2 192.168.11.2
ping -c 2 192.168.11.3
adb devices -l
```

Si se pretende probar PICO directo, el resultado esperado antes de empezar es
que no haya backend/UI/PC Service ni listeners 8082/63901. Si se pretende usar
el flujo suministrado con PC, arrancarlos mediante el preflight versionado y
usar una sola UI.

### 19.3 Próxima decisión técnica

La prioridad no es mover el robot, sino resolver una de estas rutas:

1. **Ruta soportada con PC:** obtener/confirmar DAC beta.2, origen del
   heartbeat y `pico_control`; superar el gate de 60 s.
2. **Ruta directa:** recibir de DSA el APK/módulo/procedimiento exacto y
   demostrar peer/datos/heartbeat sin movimiento según 12.4.

No cambiar `MC_SCENE`, no instalar un paquete DAC supuesto, no simular
heartbeat y no ejecutar teleoperación física hasta que una de esas rutas quede
demostrada.

### 19.4 Texto para iniciar un chat nuevo

```text
Lee completamente docs/teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md
antes de actuar. Es la fuente de verdad del Cruzr S2 real. Conserva el
worktree existente y no reinicies el diagnóstico. Empieza con el snapshot de
la sección 19.2, sin mover el robot, y continúa únicamente desde la decisión
pendiente de la sección 19.3.
```
