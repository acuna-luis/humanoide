# Cruzr S2 + PICO: fuente de verdad de teleoperación

**Última actualización:** 24 de agosto de 2026  
**Estado del documento:** operativo y en evolución  
**Plataforma:** Cruzr S2 con abrazaderas, PICO 4 Ultra Enterprise y PC Ubuntu  
**Responsable de actualización:** registrar aquí cada cambio antes de reanudar una prueba física

Este documento conserva el estado real de la integración de teleoperación. Su
objetivo es que el trabajo pueda detenerse y reanudarse sin repetir pruebas,
perder hallazgos ni confundir una capa que funciona con el sistema completo.
Es la fuente de verdad para la conexión **PICO → PC → robot**. La guía de
captura, dataset y VLA sigue estando en
[`../vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md`](../vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md).

> **Bloqueo vigente:** no iniciar movimiento con `Y` ni arrancar una tarea de
> teleoperación física hasta recibir y validar la compilación exacta
> `utars-udoke-config-v0.2.0-dac-beta.2`, o una confirmación escrita de DSA con
> hashes/componentes equivalentes, y superar una prueba de heartbeat estable.
> No se debe eliminar ni ampliar el watchdog de 10 segundos.

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
| PICO físico y USB | **VERIFICADO** | ADB autorizado y enlace TCP XR activo |
| Aplicación XR del PICO | **VERIFICADO** | XRoboToolkit 1.1.1, `Head + Controller` enviando |
| Servicio XR del PC | **VERIFICADO** | `RoboticsServiceProcess` activo, PICO conectado a TCP 63901 |
| Backend UBT del PC | **VERIFICADO** | `ubt-controller` 5.3.0 activo y escuchando en TCP 8082 |
| Ethernet PC ↔ robot | **VERIFICADO** | PC `192.168.11.250/24`; Motion `.2`; Vision/señalización `.3` |
| Configuración de efector | **VERIFICADO** | `HW_TYPE=cruzr_s2_v1`, abrazaderas |
| Configuración PICO del robot | **VERIFICADO** | `TELE_DEVICE=pico`, `transmit=local` |
| Tarea Cruzr/PICO correcta | **VERIFICADO** | `teleoperation/cruzr_clamp_pico_teleoperation` |
| Señalización y DataChannel | **VERIFICADO** | DataChannel llegó a estado abierto durante diagnóstico |
| Flujo XR hacia el robot | **VERIFICADO** | El robot registró recepción de tele-data y habilitación temporal |
| Heartbeat de aplicación robot → PC | **FALLA REPRODUCIDA** | El PC no recibe `{"type":"heartbeat"}` |
| Teleoperación sostenida | **NO VALIDADA** | El watchdog envía STOP por ausencia de heartbeat |
| Movimiento físico mediante PICO | **BLOQUEADO** | No se autoriza hasta corregir heartbeat/build |
| Grabación de episodios con `B` | **PENDIENTE** | No existe aún exportación auditada extremo a extremo |
| PICO directo al robot sin PC | **NO SOPORTADO/NO VERIFICADO** | El material recibido requiere el PC intermedio |

Tras el último reinicio del servicio del PC:

- `ubt-controller.service` está activo;
- el PICO permanece autorizado por ADB;
- existe una sesión TCP XR estable entre `192.168.67.197` y
  `192.168.67.183:63901`;
- `RoboticsServiceProcess` y `ubt_controller` están activos;
- no está abierta la interfaz Electron `ubt-remote-control`;
- no hay un cliente diagnóstico WebSocket persistente;
- no se ha enviado una nueva orden de movimiento.

## 3. Arquitectura que se ha verificado

```text
PICO 4 Ultra Enterprise
  Android 14 / XRoboToolkit-PICO 1.1.1
  IP USB compartida observada: 192.168.67.197
                 │
                 │ USB + red compartida + ADB
                 ▼
PC Ubuntu 24.04.4 LTS
  IP PICO: 192.168.67.183
  IP Ethernet robot: 192.168.11.250
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
| Canal configurado en el PC | `walker28` | **VERIFICADO**, no modificar sin DSA |
| Build exacta DAC | `v0.2.0-dac-beta.2` | **NO DEMOSTRADA** |

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

### 4.2 PC de teleoperación

| Elemento | Valor | Estado |
|---|---|---|
| Sistema | Ubuntu 24.04.4 LTS, amd64 | **VERIFICADO** |
| Ethernet al robot | `192.168.11.250/24` | **VERIFICADO**, coincide con SOP |
| Interfaz USB PICO | `192.168.67.183/24` | **VERIFICADO** |
| ADB | `1:34.0.4-1build3` | **VERIFICADO** |
| XRoboToolkit PC Service | `roboticsservice 1.0.0.0` para Ubuntu 24.04 | **VERIFICADO** |
| Backend | `ubt-controller 5.3.0` | **VERIFICADO** |
| UI | `ubt-remote-control 4.1.0` | **VERIFICADO** |
| Servicio | `/etc/systemd/system/ubt-controller.service` | activo y habilitado |
| Backend local | TCP 8082 | escuchando |
| Servicio XR | TCP 63901 | escuchando y con PICO conectado |

La instalación del 21 de agosto usó deliberadamente el paquete
`XRoboToolkit_PC_Service_1.0.0_ubuntu_24.04_amd64.deb`; el controlador 5.3.0
sólo fue entregado con nombre `ubuntu22.04`, aunque su binario funciona en el
PC 24.04. Esta combinación necesita confirmación formal de DSA.

El binario ejecutable instalado de `ubt_controller` coincide byte por byte con
el `.deb` entregado:

```text
3a094a007842d859ce95974d74fddf74714e1a49a9a75ca32e82fd6ce7b789fa
```

No se ha parcheado el binario cerrado. Sí se han ajustado de forma reversible
su configuración, wrapper y unidad systemd; se documentan en la sección 8.

### 4.3 PICO

| Elemento | Valor | Estado |
|---|---|---|
| Modelo reportado por ADB | `A9210` | **VERIFICADO** |
| Familia comercial | PICO 4 Ultra Enterprise | **VERIFICADO por hardware/proveedor** |
| Android | 14 | **VERIFICADO** |
| Aplicación | `com.xrobotoolkit.client` | **VERIFICADO** |
| XRoboToolkit | 1.1.1 | **VERIFICADO** |
| IP compartida observada | `192.168.67.197` | **VERIFICADO** en la sesión actual |
| Estado de aplicación | `Working` | **OBSERVADO** |
| Modo de envío | `Head + Controller` | **OBSERVADO** |
| Controladores | poses enviadas; neutros antes de pruebas | **OBSERVADO** |
| `QuestTool_v3.5.3.apk` | recibido, no identificado como componente activo | **NO UTILIZADO** |

`Working` significa que el PICO está unido al servicio XR del PC. No confirma
heartbeat del robot, tarea de manipulación activa ni autorización para mover.

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
- `enable_adb_reverse=1` está configurado, pero el snapshot actual de
  `adb reverse --list` está vacío. La sesión XR funciona mediante la red USB
  compartida; el flag por sí solo no prueba que exista un reverse activo.
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
| `Y` | iniciar/detener teleoperación | intentado; el heartbeat impide mantenerla |
| `X` | alternar modo en sitio/móvil | **PENDIENTE** |
| `A` | reset del tren superior en modo en sitio | pulsado; no corrige el enlace; efecto físico no caracterizado |
| `B` | iniciar/detener captura de episodio | **PENDIENTE** |
| grip izquierdo/derecho | seguimiento de ese brazo y cintura | **PENDIENTE**, no usar antes del gate |
| triggers | cerrar/abrir manos activas | no aplicable a abrazaderas pasivas; confirmar con DSA |
| joysticks en sitio | cintura y elevador | **PENDIENTE** |
| joysticks en modo móvil | traslación y giro del chasis | **PENDIENTE** |
| clics de joystick | alternar protección de fuerza por brazo | **NO PROBAR** hasta confirmar estado/indicación |

La UI PICO no muestra por sí sola toda la cadena de armado. Mientras no se
conozca el heartbeat, ningún cambio de color o estado del visor debe sustituir
la lectura del backend y del robot.

## 6. Qué se ha probado extremo a extremo

### 6.1 Enlace PICO → PC

**VERIFICADO:**

1. El PICO aparece como dispositivo ADB autorizado.
2. XRoboToolkit entra en `Working` y envía `Head + Controller`.
3. La red USB asigna `192.168.67.183` al PC y `192.168.67.197` al PICO.
4. Se establece TCP desde el PICO hacia `RoboticsServiceProcess:63901`.
5. El servicio detecta el dispositivo y `ubt_controller` consume el SDK.
6. En una prueba diagnóstica se observaron datos PICO próximos a la tasa
   configurada de 90 Hz.

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

El watchdog puede seguir emitiendo STOP de forma periódica mientras no haya
heartbeat. Si START ocurre cuando el temporizador ya está vencido, la parada
puede aparecer antes de diez segundos desde la pulsación de `Y`; los diez
segundos se miden desde el último heartbeat válido, no necesariamente desde el
último START.

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

### 6.5 Resultado de la prueba física

- Se pulsó y mantuvo `Y` en diferentes intentos con controladores neutros,
  grips y gatillos libres, abrazaderas vacías, zona despejada y paro listo.
- Se comprobó que el PICO permanecía `Working`.
- El enlace llegó al robot, pero no se sostuvo la habilitación.
- No se obtuvo una teleoperación física continua y validada.
- Repetir `Y` no corrige la ausencia de heartbeat y no debe usarse como método
  de diagnóstico.

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

### 7.2 Causa más probable

**INFERENCIA FUERTE:** incompatibilidad entre el robot genérico `v0.2.0` y el
conjunto de PC exigido para adquisición de datos. El SOP define una matriz
exacta:

| Componente | Versión exigida por SOP |
|---|---|
| Robot | `utars-udoke-config-v0.2.0-dac-beta.2.tar.gz` |
| Backend PC | `ubt_controller_5.3.0_ubuntu22.04_amd64` |
| UI PC | `ubt-remote-control_4.1.0_amd64` |

Los dos componentes del PC coinciden. La build exacta del robot no está
instalada o, como mínimo, no puede demostrarse con el material actual. La
ausencia del heartbeat de aplicación es consistente con esa diferencia.

### 7.3 Qué debe confirmar DSA

DSA debe proporcionar una de estas dos respuestas verificables:

1. el archivo exacto `utars-udoke-config-v0.2.0-dac-beta.2.tar.gz`, su hash y
   procedimiento de actualización/rollback; o
2. una declaración de que el paquete genérico instalado contiene exactamente
   los mismos componentes DAC, acompañada por versiones/hashes y una corrección
   concreta para el heartbeat que falta.

Hasta entonces no se considerará resuelto.

## 8. Workarounds y cambios locales aplicados

Todos son reversibles. Ninguno modifica el binario cerrado de
`ubt_controller`.

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

## 9. Acciones intentadas que no solucionan el problema

| Acción | Resultado | Decisión |
|---|---|---|
| Pulsar `Y` una vez | no mantiene teleoperación | no repetir hasta corregir build |
| Mantener `Y` pulsado | no aporta heartbeat | **DESCARTADO** como solución |
| Pulsar `Y` sin pedal | backend intenta habilitar, luego STOP | configuración aceptada, heartbeat sigue ausente |
| Reiniciar servicio del PC | restaura detección PICO | útil para discovery, no corrige build |
| Ver `Working` en PICO | confirma sólo PICO ↔ PC | no usar como autorización de movimiento |
| Pulsar `A` | no resuelve heartbeat | `A` es reset de tren superior, no reparación de enlace |
| Cerrar UI y usar cliente diagnóstico | aísla transporte | diagnóstico válido, no solución final |
| Confiar en `AnswerSession: sent heartbeat` | heartbeat equivocado | **DESCARTADO** |
| Usar tarea `s2_clamp_pico_teleoperation` | parámetros de otro robot | **DESCARTADO** |
| Desactivar o ampliar watchdog | ocultaría pérdida de enlace | **PROHIBIDO por seguridad** |

## 10. Tabla rápida de fallos y recuperación

| Síntoma | Comprobación | Causa probable | Acción segura |
|---|---|---|---|
| PICO queda en `Connecting` | `adb devices`; TCP 63901 | app/USB/servicio XR no unidos | recuperar `Working`, después reiniciar servicio una vez |
| `Working`, pero backend no detecta visor | logs `device found/missing` | backend arrancó antes del stream | reiniciar servicio con PICO ya conectado |
| ADB no autorizado | `adb devices -l` | autorización, cable o udev | aceptar diálogo; revisar cable/regla; no usar root ADB |
| Datos con números inválidos | locale del servicio | coma decimal española | mantener `LC_NUMERIC=C` |
| No conecta con robot | ping `.2/.3`, config WS | IP/ruta/cable/config | restaurar `192.168.11.250/24`; no tocar ROS |
| DataChannel no abre | logs de señalización/RTM | canal, servidor o cliente duplicado | una sola UI; revisar `.3:4000` y `channel_name` |
| `Y` parece activar y se corta | log `No heartbeat...` | heartbeat app ausente | STOP, no repetir; corregir build DAC |
| PC recibe `enable=0` repetidamente | log backend | watchdog sin heartbeat | no confundir con E-stop físico |
| Topic existe pero `echo` no devuelve | `ros2 topic info/echo` | endpoints sin muestras activas | no considerar listo sólo por discovery DDS |
| PICO se duerme/desconecta | ADB/TCP desaparecen | suspensión/USB | neutralizar, parar, reconectar y reiniciar servicio |
| UI oficial y cliente diagnóstico abiertos | `ss`/procesos | dos clientes compitiendo | cerrar diagnóstico; conservar una sola UI |

## 11. Procedimiento seguro para reanudar otro día

### 11.1 Antes de tocar software

1. Confirmar abrazaderas vacías y correctamente instaladas.
2. Robot en `home`, cargador desconectado y chasis detenido.
3. Envolvente completa de brazos/cabeza despejada.
4. Controladores PICO neutros; triggers y grips libres.
5. Nadie tocando el robot y una persona con el paro físico preparado.
6. No pulsar `Y` durante diagnóstico de sólo lectura.

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

Antes de permitir una trayectoria:

1. Abrir una única instancia de la UI oficial.
2. Con operador neutro y paro listo, habilitar la sesión según el SOP.
3. Observar durante al menos 60 segundos:
   - mensajes app `heartbeat` continuos;
   - ausencia de `No heartbeat for 10 seconds`;
   - `tele_operation enable=1` estable;
   - DataChannel abierto sin reconexiones;
   - PICO `Working`;
   - ninguna orden inesperada.
4. Detener desde la UI y confirmar `enable=0`.
5. Repetir una vez para probar inicio/parada limpios.

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

**NO SOPORTADA/NO VERIFICADA.** El paquete recibido implementa explícitamente:

```text
PICO → XRoboToolkit PC Service → ubt_controller → robot
```

El PICO no se conecta directamente al controlador del robot en el flujo
suministrado. La dirección `192.168.11.3:4000` es un servidor de señalización,
no una API directa suficiente para controlar el robot.

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

## 13. Pendientes priorizados

### P0 — bloquean cualquier movimiento PICO

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

## 15. Evidencia reproducible y comandos de diagnóstico

Estos comandos son de sólo lectura. No iniciar tareas ROSA ni pulsar `Y` para
recoger un snapshot.

### PC

```bash
dpkg-query -W -f='${binary:Package}\t${Version}\t${Architecture}\n' \
  roboticsservice ubt-controller ubt-remote-control adb

systemctl show ubt-controller.service \
  -p ActiveState -p SubState -p ActiveEnterTimestamp -p MainPID

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
- Informe de actualización base:
  [`../../upgrade.txt`](../../upgrade.txt)
- Regla udev PICO:
  [`../../config/udev/51-pico-ubt.rules`](../../config/udev/51-pico-ubt.rules)

El SOP PDF suministrado se conserva localmente dentro de `utats/` y está
ignorado por Git debido a su tamaño/origen externo.

## 17. Registro de cambios y pruebas futuras

Añadir cada sesión al principio de esta tabla. No borrar resultados fallidos:
son parte de la evidencia.

| Fecha/hora | Cambio o prueba | Resultado | Evidencia | Próxima decisión |
|---|---|---|---|---|
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
