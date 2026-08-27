# Cruzr S2 — recuperación tras contacto, paro y fault durante teleoperación

**Última actualización:** 27 de agosto de 2026  
**Unidad observada:** Cruzr S2 `WAE001UBT60000669`  
**Baseline:** robot v0.2.0, abrazaderas, `HW_TYPE=cruzr_s2_v1`, PC controller 4.7.0  
**Ámbito:** contacto contra mobiliario, objeto posiblemente sujeto, postura no
`home`, paro de emergencia, fault de servo y consignas latentes.

Este documento describe un incidente real y el procedimiento conservador que
permitió recuperar el robot. No convierte un apagado abrupto ni un reset de
servo en procedimientos aprobados por UBTECH. El estado físico y lógico debe
comprobarse de nuevo en cada incidente.

## 1. Resultado ejecutivo del incidente

Durante teleoperación PICO el robot ejerció fuerza contra una mesa. Se accionó
el paro y el robot quedó estable, flexionado y con una caja de cartón
prescindible posiblemente sujeta. La mesa se retiró.

La recuperación automática se bloqueó correctamente varias veces:

- el registro más nuevo no permitía demostrar la fase de manipulación;
- `/mc/manipulation/action` quedó temporalmente sin servidor;
- el hombro izquierdo yaw, servo `4003`, permaneció en FAULT;
- una tarea excepcional sólo para el brazo derecho fue abortada sin mover;
- ese aborto dejó consignas derechas distintas de las posiciones reales;
- el preflight impidió rearmar `4003` con esas consignas latentes.

El operador realizó después un apagado completo, retiró la caja y usó `KEY1`.
Los brazos descendieron sin una trayectoria controlada. En el siguiente
arranque el robot se encendió inicialmente con el paro accionado. Después de
liberarlo, Motion inicializó todos los ejes sin fault, inmóviles, con
posición/consigna coincidentes y dentro de ±0,003 rad de cero. El robot ya
estaba en `home` articular, por lo que **no se envió otra trayectoria `home` ni
se llamó al servicio de rearmado**.

`KEY1` no queda validado como método de recuperación. En esta unidad ya se
había asociado su uso aislado a un corte abrupto y corrupción de registros
Docker. Consulte
[`../support/UBTECH_SHUTDOWN_PROCEDURE_MISMATCH_V020.md`](../support/UBTECH_SHUTDOWN_PROCEDURE_MISMATCH_V020.md).

## 2. Evidencia verificable

### 2.1 Fault del hombro 4003

Tras el contacto se observaron:

```text
L_shoulder_yaw_motor
id=4003
error_code=0x1001
status=0x0238
velocity=0
```

Las lecturas SDO confirmaron:

```text
0x603F -> 0x1001   # error code
0x6041 -> 0x0238   # status word con FAULT
```

Los registros añadieron esta secuencia:

```text
servo 4003 error code:0x1001
Operation disabled unexpected
servo 4003 error code:0x2007
EnableServoSrv timeout
```

Los demás ejes mostraban `0x0237`, compatible con `Operation Enabled`. No se
dispone de la tabla oficial UBTECH que traduzca `0x1001` y `0x2007`; su nombre
y causa exacta siguen pendientes del proveedor.

### 2.2 Arranque parcial de manipulación

Después de seleccionar `auto_task`, `manipulation_robot_app` reinició porque
esperaba controladores que no estaban cargados. Se restauraron de forma
volátil mediante el `controller_manager` oficial:

```text
force_torque_sensor_controller: running
imu_sensor_controller: running
```

Después `/mc/manipulation/action` volvió a publicar un servidor. Esto resolvió
el arranque de la aplicación, pero no el fault 4003. En el arranque completo
posterior ambos controladores aparecieron `running` sin intervención manual.

### 2.3 Objetivo aceptado no equivale a movimiento ni éxito

Se preparó una tarea temporal con una única acción:

```xml
<Action ID="MetaMove" type="arm" location="right"
        delta_translation="0;-0.05;0" duration="6" />
```

El objetivo fue aceptado, pero terminó:

```text
desc=MoveToGoalFailed
state=7104050
status=6
```

Las siete posiciones derechas permanecieron iguales y todas las velocidades
fueron cero. En esta plataforma, el éxito observado de una acción es
`status=4` y `SUCCEED`; `status=6` es un resultado terminal abortado, no éxito.

### 2.4 Un aborto puede dejar consignas latentes

Aunque la tarea anterior no movió el brazo, `/mc/actuator_state` mostró después
estas diferencias `cmd_pos-position` en la cadena derecha:

```text
mínimo absoluto: 0,0166 rad
máximo absoluto: 0,1043 rad
```

Rearmar el eje fallido en ese estado podía permitir que las consignas se
aplicaran de forma brusca. La llamada dirigida a `/ecat/servo/op_enable` fue
bloqueada por el preflight **antes de ejecutarse**.

### 2.5 Estado final recuperado

Después del apagado y nuevo arranque:

```text
todos los ejes no rueda: error_code=0
status=0x1237
velocity=0
abs(cmd_pos-position)<0,003 rad
abs(position)<0,003 rad
/mc/manipulation/action: server count 1
manipulation_controller: running
force_torque_sensor_controller: running
imu_sensor_controller: running
charger: conn_status=2, current=0
baterías: 65,6 % y 74,6 %
estops: 0,0
```

El comando de sólo lectura terminó:

```text
./scripts/cruzr_blue_workbin_cycle.sh --check
ACTUATORS_OPERATION_ENABLED=1
ESTOPS=0,0
CHARGER=disconnected
ACTIONS=ready
CHECK_OK
```

### 2.6 Segundo incidente: trip FT y recuperación completa

El 27-08 una sesión arms-only bimanual tomó una caja y el robot dejó de
responder mientras PICO/PC seguían publicando a 90 Hz. Motion midió en el FT
izquierdo `Force-X=-305,6…-307,0 N` frente al umbral de 120 N, registró
`Excessive force` y detuvo la tarea. Después aparecieron faults del servo 5003,
saltos de consigna en ambos hombros y todos los esclavos EtherCAT pasaron a
`SAFEOP ERROR`. Los reinicios automáticos de contenedores no restauraron
`ListControllers` ni `/mc/manipulation/action`.

Con caja retirada, brazos/robot estables y zona despejada se completó el flujo
lógico `/emb/pm_shutdown` hasta `Shutdown→Term`; sólo después de confirmar
pantalla, luces y red apagadas se pulsó `KEY1` y finalmente se apagó el chasis.
En el arranque siguiente se mantuvo inicialmente el paro accionado. Al
liberarlo, sin movimiento inesperado, Control Center completó self-check y
`StartMotion`; EtherCAT, controladores y servidor de manipulación reaparecieron.
El check versionado verificó todos los actuadores `Operation Enabled`, sin
fault, inmóviles y con consignas dentro del límite, paros `0,0` y cargador
desconectado. No se envió `home`: el nuevo log no permitía clasificar la
postura, aunque el hardware estaba sano.

Este segundo incidente confirma que el grip PICO no determina fuerza
proporcional: es un clutch booleano. La carga FT provino de la interacción
física o de un transitorio/bias del sensor, no de cuánto se apretó el botón.
También confirma que un reinicio automático de contenedores no equivale a
recuperación cuando EtherCAT cae; debe exigirse el preflight completo.

## 3. Posibles causas

Mantener separadas las observaciones de las explicaciones evita convertir una
hipótesis en procedimiento.

| Estado | Posible causa | Evidencia y límite |
|---|---|---|
| **OBSERVADO** | contacto sostenido contra la mesa | el operador vio fuerza elevada y accionó el paro; el fault apareció en el mismo intervalo |
| **INFERENCIA** | sobrecarga o protección del hombro izquierdo yaw | `4003` fue el único eje en FAULT y no terminó de habilitar; falta la tabla de códigos UBTECH |
| **OBSERVADO** | transición EtherCAT anormal alrededor del incidente/reinicio | se registraron `WKC act/set=29/69`, `SAFEOP ERROR` y errores de sincronización; no está demostrado si fueron causa o consecuencia |
| **VERIFICADO** | arranque incompleto del stack de manipulación | faltaban los controladores FT e IMU y el servidor de acción era 0; cargarlos restauró la aplicación, no el servo |
| **VERIFICADO** | una acción abortada puede modificar consignas sin mover | `status=6`, posiciones iguales y deltas de consigna posteriores de hasta 0,1043 rad |
| **OBSERVADO** | `KEY1` puede desenergizar la parte superior de forma abrupta | los brazos descendieron sin trayectoria; un uso anterior coincidió con registros Docker corruptos |
| **OBSERVADO** | el boot guard no puede recuperar cualquier estado de arranque | con seguridad `1,0,0` leyó `CONTROL_STATE=unknown` y terminó `unexpected_control_state_unknown`; Motion se inicializó al liberar el paro |

No está demostrado que el fault implique daño mecánico permanente: desapareció
en el arranque final. Tampoco está demostrado que repetir un power cycle sea
siempre suficiente o seguro.

## 4. Árbol de decisión

```text
contacto, fuerza anormal o movimiento inesperado
                 |
                 v
        STOP / paro físico
                 |
                 v
 ¿objeto, mesa o persona en trayectoria?
       | sí                     | no
       v                        v
 no enviar home          preflight de sólo lectura
 retirar contacto sólo          |
 con estado físico seguro       v
                       ¿fault, movimiento o
                       abs(cmd-pos)>0,01?
                         | sí          | no
                         v             v
                  no home/rearmado   ¿ya está en home?
                  no tarea parcial    | sí       | no
                         |             v          v
                         v          terminar   recuperación oficial
                  apagado aprobado              con preflight fresco
                  y nuevo descubrimiento
```

## 5. Procedimiento de recuperación

### Fase A — detener y clasificar

1. Ante contacto o fuerza inesperada, detener teleoperación y usar el paro
   físico si el movimiento continúa o existe riesgo inmediato.
2. Mantener personas, pies y manos fuera de brazos, cabeza, elevador, cintura,
   caja y posibles zonas de caída.
3. Clasificar el objeto como **sujeto**, **apoyado** o **retirado**. No deducirlo
   del log.
4. No enviar `home` mientras una mesa, caja o persona pueda interceptar la
   trayectoria.
5. No combinar PICO, UI, mando y scripts como clientes simultáneos.

### Fase B — diagnóstico sin movimiento

Desde el PC:

```bash
./scripts/cruzr_recover_to_home.sh --check
./scripts/cruzr_blue_workbin_cycle.sh --check
```

El segundo script comprueba ahora, para cada articulación no rueda:

- `error_code == 0`;
- bit FAULT ausente;
- bits de `Operation Enabled` presentes;
- `abs(cmd_pos-position) <= 0.01` rad;
- servidor de manipulación, objetivos, batería, cargador y paros.

Interpretación:

```text
ACTUATOR_FAULT=...          -> no mover, no rearmar
ACTION_BUSY=...             -> no iniciar otro objetivo
ACTUATORS_OPERATION_ENABLED=1
CHECK_OK                    -> infraestructura apta; aún falta estado físico
```

Un topic anunciado no garantiza una muestra fresca. Después de reinicios hay
que redescubrir nombres de contenedor y no depender del daemon ROS 2 obsoleto.

### Fase C — condiciones que prohíben `home`

No ejecutar `home` si se cumple cualquiera:

- fault o error de cualquier articulación;
- una articulación no está `Operation Enabled`;
- `abs(cmd_pos-position)>0,01` rad con el robot inmóvil;
- acción activa o estado interno desconocido;
- objeto posiblemente sujeto sin zona de caída libre;
- cargador conectado, batería insuficiente o paros sin comprobar;
- robot, brazo o caja apoyados contra mobiliario;
- falta una persona con acceso inmediato al paro.

`--force-held-home` sólo omite la clasificación histórica de la fase de
manipulación y permite aceptar la caída de una caja prescindible. No omite los
gates anteriores y no debe combinarse con `--fast`.

### Fase D — fault o consignas latentes

1. No repetir una tarea parcial: este incidente demostró que puede abortar y
   dejar consignas latentes.
2. No escribir SDO, no publicar posiciones crudas y no reiniciar controladores
   individualmente para “probar”.
3. No rearmar un servo mientras otro eje conserve `cmd_pos` alejado de su
   posición real.
4. Si no existe un reset de tareas documentado y las consignas no se limpian,
   detenerse y usar únicamente el procedimiento de apagado completo aprobado.
5. `KEY1` aislado no es ese procedimiento. La discrepancia de apagado v0.2.0
   sigue pendiente de UBTECH.
6. Retirar un objeto con el robot apagado sólo corresponde a personal presente
   que pueda demostrar estabilidad mecánica; nadie debe quedar debajo de un
   brazo que pueda descender.

### Fase E — siguiente arranque

La secuencia usada en este incidente fue arrancar con el paro principal
accionado y la zona despejada. Es una observación, no un SOP universal aprobado.

1. Esperar el arranque completo de Motion y Vision.
2. Descubrir contenedores con `docker ps`; no reutilizar nombres históricos.
3. Leer el boot guard. Con el paro accionado puede terminar ineligible; no
   reiniciarlo automáticamente si una recuperación pudiera mover cabeza o
   brazos.
4. Antes de liberar el paro: abrazaderas vacías, brazos sin contacto, zona
   completa despejada y una persona preparada para volver a accionarlo.
5. Después de liberarlo, no seleccionar PICO, UI ni `auto_task` hasta obtener
   una muestra de `/mc/actuator_state`.
6. Exigir error cero, `Operation Enabled`, velocidad cero y consignas
   coincidentes para todos los ejes.

### Fase F — decidir si hace falta mover

Si todos los ejes ya están cerca de cero, no enviar una trayectoria redundante:

```text
abs(position)<0,02 rad para brazos, cabeza, cintura y elevador
velocity=0
abs(cmd_pos-position)<0,01 rad
```

Si están sanos pero no en `home`, repetir primero:

```bash
./scripts/cruzr_recover_to_home.sh --check
```

Sólo con comprobación física fresca ejecutar el modo apropiado. No usar
`--force-held-home` con abrazaderas vacías salvo que el estado histórico siga
siendo realmente indeterminable; nunca usarlo para ignorar un fault.

## 6. Checklist breve para la persona junto al robot

Antes de cualquier transición que pueda habilitar par:

- [ ] objeto retirado o caída aceptada y zona inferior despejada;
- [ ] brazos sin apoyar contra robot, suelo, mesa o pared;
- [ ] abrazaderas vacías;
- [ ] robot estable y cargador desconectado;
- [ ] ambas personas fuera de la envolvente;
- [ ] una persona toca o alcanza inmediatamente el paro;
- [ ] terminal visible y un único cliente de control;
- [ ] criterio acordado para volver a accionar el paro.

Después:

- [ ] no hubo tirón, ruido, olor ni calentamiento;
- [ ] velocidades cero;
- [ ] error cero y `Operation Enabled` en todos los ejes;
- [ ] consignas coinciden con posiciones;
- [ ] resultado de acción, si existió, fue `status=4`/`SUCCEED`;
- [ ] estado físico final confirmado visualmente.

## 7. Cambios preventivos implementados

`scripts/cruzr_blue_workbin_cycle.sh` bloquea ahora antes de enviar objetivos
si detecta:

```text
error_code != 0
status con bit FAULT
estado distinto de Operation Enabled
abs(cmd_pos-position) > 0.01 rad
```

El XML temporal de liberación sólo con el brazo derecho se retiró del robot y
del repositorio. No debe recrearse como workaround automático.

## 8. Pendientes para UBTECH

1. Tabla oficial de errores de servo `0x1001` y `0x2007`.
2. Procedimiento aprobado para inspeccionar y rearmar únicamente el servo 4003.
3. Significado y tratamiento de `MoveToGoalFailed`, state `7104050`.
4. Método oficial para limpiar consignas después de una acción abortada.
5. SOP de apagado y arranque aplicable a esta revisión física, incluida la
   función exacta de `KEY1` y la posición de los paros.
6. Confirmación de si un contacto/overload exige inspección mecánica antes de
   volver a teleoperar.

## 9. Punto de reanudación

Al cerrar el incidente:

- caja retirada y abrazaderas vacías por confirmación del operador;
- postura articular `home` demostrada sin una acción adicional;
- todos los actuadores sin error, `0x1237`, inmóviles y sincronizados;
- paros `0,0`, cargador desconectado, baterías suficientes;
- `/mc/manipulation/action` con un servidor y controladores requeridos running;
- boot guard `failed` por `unexpected_control_state_unknown` y Control Center
  pendiente de revalidación;
- ninguna nueva teleoperación autorizada por este documento.

Antes de otro movimiento: comprobar Control Center, repetir ambos `--check`,
inspeccionar visualmente hombro izquierdo/abrazaderas y hacer una prueba vacía
de amplitud mínima con persona en el paro.
