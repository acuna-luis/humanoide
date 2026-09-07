# Cruzr S2 — recuperación tras contacto, paro y fault durante teleoperación

**07-09, cálculo STL corregido:** rutina de distancia entre triángulos omitía
algunos cruces arista–cara. Históricos dependientes no utilizables como prueba
de separación sin regenerar. Nuevos tres testigos iniciales hombro–torso
separados en superficies STL, sin recorrido completo ni tolerancias físicas.
Detalle y tests en SALIDA_MUNECA_FIJA; ninguna autorización de movimiento.

**07-09, ampliación de candidato:** filtro AABB de salida/vuelta encuentra
tres pares hombro–torso inconclusos, no contacto físico demostrado. Geometría
shoulder_pitch incompleta y entorno/frenado sin evaluar. No usar como autorización
de movimiento. Informe SALIDA_MUNECA_FIJA, tres tests nuevos correctos.

**07-09, candidato de muñeca fija:** invariancia relativa sensor/muñeca
comprobada numéricamente en salida sintética de hombro, no holgura inicial
ni seguridad física. Diagonales L174/R178 mm no son separación mínima.
Ver `docs/incidents/2026-09-07_SALIDA_MUNECA_FIJA.md` antes de continuar.

**07-09, precisión del bloqueo geométrico:** no está limitado a staging↔A;
los 30 tramos revisados tienen testigos de solapamiento conservador bilateral
con propio brazo. No interpretar las separaciones negativas como penetración
real. Aumentar radios o serializar no habilita la ruta. Ver auditoría por tramo
en BARRIDO_PESIMISTA_RECORRIDO; sin movimiento ni cambios de protecciones.

**07-09, desarrollo offline:** salida histórica temporizada y límites de posición
evaluados, no autorización de salida/retorno. El solapamiento útil–wrist_pitch
permanece inconcluso. Emparejador temporal implementado sin recolector vivo;
no usarlo como monitor de seguridad. Diez tests locales pasan entre ambos módulos.

**07-09 ~12:54 Madrid:** imagen estéreo disponible por suscripción pasiva,
pero par concurrente imagen/joints separado 1,288 s; no sincronización validada
ni protección de movimiento. Véase TELEMETRIA_ESTACIONARIA en incidents.

**07-09 ~12:49 Madrid:** lectura puntual de joints y FT disponible; brazos
próximos a cero, velocidades reportadas cero. No demuestra ausencia de contacto,
tara FT ni vigilancia preventiva. No se enviaron movimientos ni cambios de modo.
Alcance y pendientes: `docs/incidents/2026-09-07_TELEMETRIA_ESTACIONARIA.md`.

**07-09 ~12:33 Madrid:** operador reporta HOME sin problemas tras rearme.
Log muestra éxito pero 184 avisos de cabeza fuera de rango; sin alarmas FT
explícitas en ventana consultada retrospectivamente. No fue ensayo monitorizado
antes del contacto ni aprobación de recuperación general. No ampliar límites.
Evidencia y alcance en `docs/incidents/2026-09-07_HOME_OBSERVADO_1233.md`.

**07-09, peor caso geométrico:** la esfera nominal 119,411 mm ya invade la malla
de muñeca en el testigo conservado (centro hipotético a 40,639 mm). No demuestra
contacto real; sí impide aprobar mediante esa envolvente. Reservas mayores no
lo resuelven. No excluir la muñeca ni elegir giro favorable para obtener PASS.

**07-09, referencia de útil pendiente:** revisión de fotos y cotas no permite
reducir el registro a otra longitud. Hace falta identificar físicamente origen,
ejes y cara de fijación del sensor sixforce_link (croquis de referencia o
registro cualificado). No exigir repetir A–F/T ni más fotos genéricas; no
desmontar/mover para resolverlo. No hay nueva aprobación de recuperación.

**07-09, alcance adicional offline:** candidato histórico pasa límites de
posición URDF para 14 ejes; continuidad monotónica garantiza que no sale del
intervalo de sus extremos. No equivale a límites activos ni comprobación de
colisiones. Generador exige --urdf y conserva JSON no ejecutable. V2 externa;
geometría de útil/muñeca y HOME interno siguen pendientes.

**07-09, candidato temporal local:** generador build_home_offline_candidate.py
calcula tiempos para retorno histórico P14, no una recuperación autorizada.
35,389 s totales con curva quíntica y límites provisionales; no trasladar sus
duraciones a MetaMove suponiendo la misma interpolación. No valida colisiones,
postura actual, estado de otros ejes ni arranque. JSON no ejecutable, sin ROS.

**07-09, interfaz de planificación examinada:** ArmTask no expone un plan
articular previo; GetMnpActionList sólo catálogo. PickPlanner/WalkPlanner son
interfaces de punto/pose, no retorno articular. No usar MetaMove/ArmTask como
consulta sin ejecución ni confiar en un yaml_args dry-run no documentado.
Planificación desacoplada aún no demostrada; informe RUTA_HOME_ALTERNATIVAS.

**07-09, alternativa HOME estudiada sin ejecutar:** existe tarea instalada
move_dual_arms_home_ompl con planificación solicitada para 14 ejes. No es un
reemplazo aprobado: no demostrados plan-only, geometría activa, recorrido ni
intercepción del HOME interno. No reutilizar variantes genéricas cintura/base
con dimensiones distintas. No llamar MetaMove para obtener un plan de prueba.
Hallazgos, hashes y dependencias en
`docs/incidents/2026-09-07_RUTA_HOME_ALTERNATIVAS.md`. Sin cambios en robot.

**07-09 ~09:44 UTC, autoarranque del guard contenido:** con autorización expresa,
Vision guard pasa a disabled sin --now/stop/restart. Archivos y marcas de última
ejecución intactos; copias antes/después y manifiesto verificados. Se retiró sólo
el enlace de arranque, reversible bajo nueva revisión. No cubre HOME interno
ni ejecución manual del guard, no habilita movimiento o rearme. Ver diagnóstico
de arranque; no confundir con las consultas previas que no cambiaron el robot.

**07-09 09:38 UTC, lectura conectada:** guard Vision enabled/active-exited y copia
instalada sin bloqueo del repositorio, ahora contrastado con archivos remotos.
No ejecutado ni cambiado. Deshabilitar sólo autoarranque queda propuesto pendiente
de aprobación; no resuelve HOME interno ni habilita rearme. VLA control/inference
detenidos según inventario; no implica estado físico seguro. Evidencia y alcance
en diagnóstico de arranque sólo lectura. Cero ROS/movimiento/recargas.

**07-09, muñeca refinada con STL:** en dos testigos, distancia centro supuesto
a superficie ~40,6 mm frente a radio mínimo 139,4 mm: la esfera sigue alcanzando
muñeca. No es evidencia de contacto de la herramienta real ni motivo para
excluir el par. No se aprueba retorno/HOME con esa aproximación. Hace falta
acotar montaje y comportamiento, no incrementar márgenes. Ver cierre de bloqueos
de aprobación; sin conexión al robot, desbloqueo ni comandos.

**07-09, recorrido sintético histórico muestreado:** cuatro envolventes y tres
órdenes de brazos; 6.030 muestras en resolución mayor. Separación condicional
respecto a cuerpo/brazo contrario/otra abrazadera, pero solapamiento con propio
brazo; no se elimina ese par para producir PASS. No reproduce HOME interno ni
su postura inicial/tiempos/ley Motion. Falta geometría propia shoulder_pitch y
resto de coberturas descritas en el informe de barrido pesimista. Suite v5 pasa;
sin modificación ni autorización de movimiento o rearme.

**07-09, cotas pesimistas sólo en sensibilidad offline:** para postura URDF
cero, cuatro radios hipotéticos 139,411–204,411 mm quedan separados de 26 AABB
de cuerpo. Mínimo del caso mayor: 15,550 mm, no distancia física observada.
No incluye brazos/entorno/recorrido ni demuestra tolerancias reales. No usar
este resultado para rearmar o enviar HOME; no cambió el robot. Informe externo
`20260907_clamp_pessimistic_screen.json`, tres tests nuevos correctos.

**07-09, cota sin resolver el giro (sólo estudio):** radio nominal 119,411 mm
alrededor del origen descriptivo cubre la caja para toda rotación si las
referencias son ortonormales y la contención reportada es válida. Centro en
sensor y errores siguen sin registrar; no es un radio de seguridad. Una esfera
que intersecta torso es inconclusa, no evidencia de colisión del útil. Tres
tests nuevos/suite v4 pasan, sin cálculos sobre trayectorias ni cambios físicos.

**07-09, envolvente nominal recibida:** operador indica T=130 mm, sin salientes
fuera de otros márgenes. Modelo propio nominal 82×100×130 mm, profundidad
−35/+95 respecto al eje descriptivo. No volver a pedir T o un CAD inexistente.
Ocho tests del generador pasan; no incluye incertidumbre validada ni montaje
registrado, y no protege el HOME interno. No libera paros ni habilita movimiento.

**07-09, integridad del auditor y siguiente dato:** límites calculados sólo
se incluyen para lados con evidencia validada; rechazo de overflow y prueba
contra uso del modelo parcial como contrato. Suite v3 local ampliada, sin
modificar protección instalada. Ficha de cotas del soporte en
`docs/incidents/2026-09-07_COTAS_PENDIENTES_SOPORTE.md`: T desde almohadillas,
contención y salientes; aún pendientes. No medir con acceso inseguro ni
rearmar/mover para identificar geometría. HOME interno sigue sin interceptar.

**07-09, alternativa al plano de fabricante:** un modelo propio de volúmenes
envolventes puede sustituir al CAD inexistente de la abrazadera, siempre que
contención, montaje e incertidumbre estén verificados. El generador local
`build_clamp_simplified_model.py` sólo representa la placa y una reserva lateral
condicionada para las patitas; soporte completo y R/t siguen pendientes.
Cuatro tests pasan, sin aprobación física. No pedir nuevas fotos genéricas ni
liberar el E-stop para resolver el registro. El HOME interno continúa sin
interceptar; este modelo no modifica esa situación.

**07-09, cierre de la vía de tornillos sin referencia adicional:** los diez
centros CAD usados son invariantes bajo reflexión lateral; las dos hipótesis
2D restantes no son dos configuraciones físicas demostradas. No resolver el
empate mediante movimiento ni otra repetición de foto. Falta referencia de
cara/normal/plano físico y soporte completo, no más tests de esos mismos
puntos. Seis tests pasan, informe exterior v2; sin desbloquear ni mover.

**07-09, correspondencias exteriores candidatas:** cuatro fijaciones exteriores
de las fotos permiten destacar dos de las seis hipótesis del patrón central,
sin calificar ninguna como transformación física. Análisis sólo 2D: alturas
de cabezas, identidad y perspectiva no resueltas. No cambia bloqueo de HOME,
rearme ni movimiento; cero órdenes/despliegues. Evidencia en contraste de fotos.

**07-09, fotos suficientes para documentar, no para cualificar:** se retira
la solicitud genérica de otra vista/conector no identificado. La auditoría
`audit_clamp_sensor_asymmetry.py` demuestra asimetría de la malla completa,
no correspondencia con la herramienta real. Tres tests correctos. Falta
registro geométrico y protección de recorridos/arranque; conservar E-stop,
sin ensayo HOME ni rearme. Ver contraste fotográfico para evidencia y límites.

**07-09, rutas heredadas:** instalación E6.0N, recarga E6.0O y apply/restore
de READY E6.0P bloqueadas localmente antes de conexión. Suite v2: 18 variantes
rechazadas, sin cambios en tareas instaladas ni protección del HOME interno.
No usar un restore-vendor o un reinicio como ensayo de recuperación.

**07-09, entradas estrictas y suite local:** gate HOME exige posición,
velocidad, cmd_pos, status y error, sin valores por defecto. Clasificar HOME
no demuestra frescura, geometría ni salud más allá de los campos inspeccionados.
E6.1C instalación/recarga bloqueadas antes de conexión. La suite
`scripts/run_contact_requalification_offline.py` terminó
`OFFLINE_REGRESSIONS_OK_PHYSICAL_BLOCKED`; 14 variantes de lanzamiento rechazadas.
No se modificaron las tareas instaladas ni el HOME interno.

**07-09, desfases HOME verificados en logs:** órdenes de grupos escalonadas
~0,2 s; dispersión total ~0,805–0,806 s en ambos arranques del 04-09.
Primer HOME: consignas avisadas fuera de rango en ambos brazos y cabeza
antes de FT. No ampliar límites ni asumir que una interpolación sincronizada
reproduce Motion. Véase [temporización](../incidents/2026-09-07_HOME_TEMPORIZACION.md).
Esto no prueba la causa única, trayectoria física ni ausencia de contacto.

**07-09, E6.1C offline retirado como vía de aprobación:** wrapper --check/--run
y analizador directo devuelven bloqueo/salida 78. No regeneran PASS basados
en el proxy antiguo. Informes previos preservados, no rehabilitados. Este
cierre documental no protege HOME interno de arranque ni modifica el robot.

**07-09, contraste numérico de fotos:** ajuste 2D reproducible confirma varias
correspondencias indistinguibles del patrón central (RMS L~0,852 px y R~1,022 px).
No demuestra orientación absoluta, plano, distancias de colisión ni protección
de HOME. Se conserva bloqueo; falta referencia no simétrica física/CAD, no
repetir las dimensiones de placa ni las mismas fotografías.

**07-09, referencia de fijación pendiente:** el STL del sensor se auditó
offline; z=0 es candidato, no plano real confirmado. Vistas inferiores
recibidas (primera L, segunda R), originales `Imágenes/1.jpeg` y `2.jpeg`
inspeccionados y hashes registrados; pendientes de correspondencia contra CAD. El patrón
de seis contornos de ~4,2 mm es simétrico cada 120°; no identifica por sí solo
el montaje ni demuestra equivalencia con los seis tornillos visibles.
No sustituir esa correspondencia por
offset PGC ni reutilizar los PASS históricos para HOME.

**07-09, geometría parcial actualizada:** F=36 mm en ambos clamps confirmado;
volumen de placa calculado offline, cinco tests aprobados. No incluye aún
soporte completo ni transformación al sensor: no autoriza HOME/rearme.

**07-09, patillas hacia interior:** confirmado por operador en postura actual;
ancho de placa 70 mm centrado, extremo de patillas a 47 mm del centro lateral.
No equivale a holgura respecto al torso ni a orientación fija del frame ROS.
Contorno frontal implementado offline; sin desbloqueo de trayectorias.

**07-09, cotas recibidas:** A=95 mm, B/C=45/55 mm reportados bilateralmente;
altura remedida=100 mm; patillas=12 mm. B/C aclaradas desde unión real,
centro daría 50/50; [detalle y cotas restantes](../incidents/2026-09-07_CONTRASTE_FOTOS_CLAMPS.md).
No modifican la cuarentena ni validan HOME; sólo completan entradas manuales.

**Actualización 07-09:** [seis fotos corregidas contrastadas con URDF](../incidents/2026-09-07_CONTRASTE_FOTOS_CLAMPS.md).
Se conocen las referencias externas del soporte; faltan sus cotas respecto
al sensor, no otra confirmación de la inspección ni las mismas fotografías.
No usar el offset de la pinza PGC como offset de estas placas.

> **07-09 — contención local implementada:** [estado de recalificación](../incidents/2026-09-07_REQUALIFICACION_CLAMPS.md).
> Doce variantes de lanzamiento rechazadas en tests sin conexión; no cubre
> HOME interno del arranque, UI/PICO ni el guard instalado en Vision.
> E-stop mantenido; no liberar ni reiniciar para probar. Inspección reportada:
> daño sólo en carcasa; clamps restauradas. Geometría bilateral y barrido
> pendientes; E6.0K retirado para nuevos PASS. No hubo despliegue ni movimiento.

**Última actualización:** 7 de septiembre de 2026
**Unidad observada:** Cruzr S2 `WAE001UBT60000669`  
**Baseline:** robot v0.2.0, abrazaderas, `HW_TYPE=cruzr_s2_v1`, PC controller 4.7.0  
**Ámbito:** contacto contra mobiliario, objeto posiblemente sujeto, postura no
`home`, paro de emergencia, fault de servo y consignas latentes.

Este documento describe incidentes reales y el procedimiento conservador que
permitió recuperar el robot en los casos cerrados. No convierte un apagado abrupto ni un reset de
servo en procedimientos aprobados por UBTECH. El estado físico y lógico debe
comprobarse de nuevo en cada incidente.

## 1. Resultado ejecutivo del incidente

**Restricción vigente:** la [auditoría del 07-09](../incidents/2026-09-07_AUDITORIA_CONTACTOS_HOME.md)
demuestra que el arranque v0.2.0 envía internamente `cruzr/home`. Un ciclo de
apagado/arranque **no es una retirada segura universal** desde contacto,
READY o postura asimétrica. Los casos históricos siguientes no autorizan
repetirlo: primero inspección de daño, geometría real y trayectoria cualificada.
El wrapper PC no intercepta ese HOME interno. No hay bloqueo técnico central
desplegado por esta auditoría; no confundir restricción documental con protección.

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

### 2.7 Tercer incidente: home vendor incompatible con postura cruzada

El 28-08, después de una sesión PICO, el script clasificó
`teleoperated_pose` y ejecutó por primera vez físicamente la tarea vendor
`cruzr/open_arm_before_home`, goal `54f7beb2-ffd2-45bd-86e6-07559fae709b`.
El XML no calcula una retirada condicionada por la postura: en su primera fase
manda en paralelo el brazo derecho a
`[0,-0.332024,0,0,0,0,0]`, el izquierdo a
`[0,-0.348983,0,0,0,0,0]`, y cintura/elevador a cero.

El final de PICO ya había registrado autocolisión entre torso y codo/muñeca
izquierdos, con distancias de aproximadamente 17–25 mm, rechazando comandos.
Durante el recovery, 1,76 s después del inicio del goal, la protección midió:

```text
Excessive force detected ... left ft sensor: -370.944 [Force-X]
```

El brazo derecho y la cintura informaron éxito; el brazo izquierdo no alcanzó
el objetivo —incluido un error de codo de `-1,30408 rad`— y el elevador quedó
abortado. El resultado global fue `MoveToGoalFailed`, state `7104050`,
`status=6`. Inmediatamente después, los servos izquierdos 4004 (codo roll),
4003 (hombro yaw) y 4002 (hombro roll) registraron `error_code=0x1003` y
`Operation disabled unexpected:0x123f`.

El operador accionó el paro. `hw` y `manipulation_robot_app` reiniciaron una
vez; el nuevo rosa_control quedó esperando `/mc/rosa_control/start`,
`/mc/actuator_state` sin publicador y `/mc/manipulation/action` sin servidor.
Los checks versionados terminaron con código 25. El diagnóstico mantuvo el
paro y no rearmó, reinició, cambió modo ni envió otra trayectoria.

**DESCARTADO:** considerar `open_arm_before_home` una retirada segura universal
desde cualquier postura PICO. Hasta diseñar y validar una recuperación por
regiones de postura, el script no debe ejecutarse de nuevo después de PICO.

### 2.8 Cuarto incidente: rearmado `StartMotion` desde READY con clamp contra torso

El 04-09 el goal E6.1C READY→ENTRY no llegó a enviarse: el preflight abortó
porque Motion seguía en `WaitStartMotion`. Tras un ciclo completo, el operador
liberó el E-stop desde la postura READY. El self-check terminó
`passed=true`, pero la acción interna `StartMotion` falló trece segundos
después con `reason:19 Limb motion failed`. La clamp izquierda quedó
visiblemente contra el torso. A continuación 4003/4004 registraron `0x1003`,
4004 pasó a `0x2006` y EtherCAT cayó globalmente a `SAFEOP ERROR`.

No se había arrancado el checkpoint, el publicador ni ENTRY. Se accionó el
E-stop y se hizo un segundo apagado completo; al retirar potencia el contacto
se alivió y los brazos descendieron. El segundo arranque, ya sin contacto,
terminó en `JoystickMode`. El preflight canónico aprobó y una muestra fresca
midió HOME en los 20 ejes, con brazos ≤`0,000479 rad`, velocidad cero y deltas
posición–consigna ≤`0,002397 rad`; no se envió otra trayectoria HOME desde el PC.
**Corrección 07-09:** los logs originales demuestran `cruzr/home` interno en
ambos arranques (19:58:01 y 20:20:14 +08); el primero registró FT −317,787 y
abortó. El segundo ejecutó HOME y terminó. No fue sólo reenergización.

El propietario confirmó posteriormente que las abrazaderas estaban montadas
deliberadamente en orientación invertida para mejorar la manipulación de
cajas. Ese cambio amplió o desplazó la envolvente física hacia el torso, pero
no se representó en el URDF, en una malla de colisión ni en un perfil distinto
de herramienta; tampoco existe un parámetro de orientación en el contrato VLA
inspeccionado. Por ello los checks articulares podían aprobar sin detectar las
patillas salientes. La coincidencia geométrica y temporal hace de esta
envolvente no modelada una hipótesis contribuyente fuerte, no una causa única
demostrada de cada daño. La distribución exacta de fuerzas y el alcance material
requieren inspección. No repetir HOME→READY hasta registrar orientación de fábrica y
holgura física bilateral, y sustituir la transición rápida por una validación
escalonada.

Las fotografías posteriores muestran rayado y una marca/orificio aparente en
la cubierta. No se ha demostrado todavía si el daño es sólo cosmético o si
afecta una pieza estructural, cableado o sensor. Debe conservarse evidencia
fotográfica y realizarse una inspección técnica antes de calificarlo.

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
| **DESCARTADO** | el boot guard debía tratar como error un arranque detenido en `WaitEStopRelease` | el reinicio supervisado del 03-09 demostró que éste es el estado correcto mientras el paro físico sigue accionado; el guard ahora lo reconoce y sale sin reiniciar ni mover |
| **VERIFICADO** | la primera fase de `open_arm_before_home` puede aumentar el contacto desde una postura PICO cruzada | el XML mueve ambos brazos, cintura y elevador en paralelo; produjo `Force-X=-370,944 N`, fallo del brazo izquierdo y faults 4002/4003/4004 |

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
- postura PICO cruzada o con codo/muñeca dentro del margen de autocolisión: la
  tarea `open_arm_before_home` no es una retirada segura demostrada;
- falta una persona con acceso inmediato al paro.

`--force-held-home` queda **RETIRADO**. El incidente demostró que aceptar la
caída de una caja no vuelve geométricamente segura la trayectoria: desde la
postura PICO real aumentó el contacto contra el torso antes de abortar.

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
3. Leer el boot guard. Con el paro accionado debe reconocer
   `WaitEStopRelease` y salir con
   `NO_ACTION=waiting_for_physical_estop_release`; no reiniciarlo
   automáticamente si una recuperación pudiera mover cabeza o brazos.
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

El script canónico aplica ahora esta decisión de forma automática:

- muestra 20D sana y `abs(position)<0,02`: declara `home_measured` y envía
  **cero objetivos**;
- último estado demostrado de depósito/apertura del ciclo de caja: permite
  retirada del chasis y la tarea vendor, con un segundo gate antes y una
  medición 20D después;
- postura PICO, estado desconocido, caja posiblemente sujeta, intento de home
  no confirmado o evento posterior de fuerza/autocolisión/fault: bloquea antes
  de publicar un goal.

En la imagen v0.2.0 observada, `/mc/actuator_state` identifica elevador y
cintura como `11004/11003/11002/11001`. El gate acepta esos IDs como aliases
de los históricos `2001/2002/2003/3001`, exige una única muestra por eje lógico
y sigue requiriendo los 14 IDs de brazos. No relaja límites ni permite omitir
un eje.

`--fast` se conserva sólo por compatibilidad con los flujos exteriores, pero
ya no omite ninguna auditoría de seguridad de return-to-home. Sin argumentos,
el script equivale a `--check`; el movimiento requiere `--run` explícito.

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
abs(velocity) > 0.02 rad/s
```

Además, `cruzr_recover_to_home.sh`:

- exige una muestra fresca de los 20 ejes de cuerpo y no confunde el inicio de
  una tarea con un home completado;
- busca eventos posteriores de exceso de fuerza, autocolisión,
  `MoveToGoalFailed`, fault de servo y EtherCAT `SAFEOP`;
- prohíbe `open_arm_before_home` desde `teleoperated_pose`, `unknown` o un
  intento anterior no confirmado;
- restringe la primitiva vendor a estados conocidos del ciclo de caja;
- revalida después del retroceso/reset y confirma el home final por posición,
  velocidad y consigna, no sólo por `status=4`;
- centraliza también `cruzr_blue_workbin_cycle.sh --home`, que ya no puede
  invocar directamente la trayectoria;
- retira `--force-held-home` y hace que `--fast` no salte gates.

Las regresiones locales se ejecutan con:

```bash
./scripts/cruzr_recover_to_home.sh --self-test
```

El 28-08 pasaron los casos home, non-home, consigna latente, eje en movimiento,
fault 4003, eje ausente, PICO bloqueado, intento de home fallido, fuerza
bloqueada y estado conocido de workbin. Esta validación fue exclusivamente
local con el robot completamente apagado; la nueva ruta de caja aún requiere
una prueba física controlada posterior y no autoriza el arranque actual.

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

### Punto de reanudación vigente tras el incidente del 28-08

El punto anterior queda histórico. El estado vigente es:

- apagado lógico aceptado por `/emb/pm_shutdown` con `success=True`;
- Motion y Vision sin respuesta; pantalla y luces confirmadas apagadas;
- `KEY1` pulsado únicamente después de esa confirmación;
- chasis apagado e indicador verde apagado;
- postura no `home`, con brazo izquierdo apoyado contra el torso sin presión
  apreciable antes del apagado; robot y brazos estables al final;
- abrazaderas vacías, cargador desconectado y zona de descenso despejada por
  confirmación del operador;
- FT izquierdo disparado a `-370,944 N` durante la apertura previa;
- faults 4002/4003/4004 observados antes del reinicio automático;
- no se rearmó ningún servo ni se envió otra trayectoria.

No encender para “probar”. El siguiente arranque debe comenzar con paro
accionado, abrazaderas vacías, cargador fuera, zona completa despejada y una
persona junto al paro. Después hay que descubrir contenedores desde cero y,
antes de liberar el paro o seleccionar modo, demostrar EtherCAT/controladores,
errores, status, velocidad y deltas posición–consigna. No ejecutar `home` ni
teleoperación hasta resolver una retirada segura específica para esta región
de postura.

### Punto de reanudación vigente tras el arranque del 03-09

El punto del 28-08 queda histórico. Se completó un shutdown lógico y un ciclo
de alimentación supervisado con el E-stop principal accionado. Control Center
pasó `WaitEStopRelease→SelfChecking→JoystickMode`; al liberar el paro, el
operador confirmó estabilidad y ausencia de movimiento inesperado. Self-check
y `StartMotion` terminaron con éxito.

La comprobación viva final, sin objetivos, registró:

```text
ACTUATORS_OPERATION_ENABLED=1
ESTOPS=0,0
CHARGER=disconnected
ACTIONS=ready
ACTUATOR_BODY_COUNT=20
ACTUATOR_ARM_COUNT=14
BODY_MAX_ABS_POSITION=0.002684
ARMS_MAX_ABS_POSITION=0.000959
BODY_MAX_ABS_VELOCITY=0.000000
BODY_MAX_ABS_COMMAND_DELTA=0.002684
MEASURED_HOME=1
RECOVERY_ROUTE=already-home,no-motion
```

El guard de arranque se corrigió e instaló en Vision con hash
`6c3cbe48…9287b`; backup
`/home/walker/cruzr-v020-boot-guard-backups/20260903T113735`. Su `--check`
confirmó x86 3/3, cámaras 2/2, `JoystickMode`, seguridad `0 0 0` y
`movement=none restart=none`. Antes de cualquier movimiento debe repetirse el
preflight físico; esta evidencia no valida una trayectoria de recuperación
desde una postura distinta de home.
