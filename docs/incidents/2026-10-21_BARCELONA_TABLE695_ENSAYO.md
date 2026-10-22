# Barcelona: preparación y ensayos de depósito a 69,5 cm

**ID:** BOX-01-BARCELONA-TABLE695-TRIAL. **Fecha:** 21-10-2026,
Europe/Madrid (UTC+02). **CUATRO ENSAYOS FINALIZADOS, rc78; ninguno alcanza el
depósito a 69,5 cm.** El cuarto termina durante el agarre nativo por pérdida
del worker persistente; el worker de salud registra `estop not confirmed clear`.
Se cancela el goal propio, sin prueba de parada física. El operador confirma
después caja libre, abrazaderas vacías/libres y condiciones de la zona; elige
apagar y volver a encender. **Aseguramiento contra caída y ejecución del
apagado/arranque PENDIENTES de confirmación.**
No hay verify-held, retirada, transporte, depósito ni HOME de cierre del cuarto
ciclo; no hay cualificación física de la altura. No nuevos intentos ni HOME
automático tras esta interrupción.

El operador comunica pulsación y liberación del paro, corroboradas por Control
Center; su petición intermedia de HOME con `./scripts/force_home.sh` no se
ejecuta. **No se envían HOME, reset, rearme ni reinicios software del agente.**

**Los tres ensayos anteriores finalizaron rc78; ninguno alcanza el
depósito a 69,5 cm.** El primero se interrumpe durante el agarre, el segundo
por frescura de recepción del paro antes del agarre nativo y el tercero por
falta de progreso de la segunda corrección de base. En la tercera sesión no
reaparece `estop receipt stale` después del cambio limitado de QoS de los
lectores de los dos paros; esto no demuestra una solución exhaustiva.
**En los tres primeros no hay recogida completada, depósito ni HOME de cierre
del ciclo.** Los checkpoints fallidos se conservan;
no se reanuda el primero tras el cambio de boot.

Este registro se actualizará con los resultados reales de la intervención.
El corte inicial de preflight llegó a **11:57:11 UTC / 13:57:11 Europe/Madrid**;
después se lanzó el ensayo autorizado de **11:58:05 a 12:00:10 UTC /
13:58:05 a 14:00:10 Europe/Madrid**. Esta actualización usa el resultado final,
`deposit-trial/events.jsonl`, consola y checkpoint locales para el primer
ensayo. La cancelación recibida no certifica parada física ni el estado
posterior de la caja. El segundo ensayo terminó a las **12:12:08 UTC /
14:12:08 Europe/Madrid** y el tercero a las **12:21:14 UTC / 14:21:14
Europe/Madrid**. Se conservan por separado los resultados finales de las tres
sesiones.

## Autorización y alcance

El usuario solicitó expresamente el ensayo a 69,5 cm y confirmó las condiciones
físicas requeridas: mesa a esa altura, abrazaderas vacías, HOME, cargador fuera,
recorrido libre, control exclusivo y supervisión junto al paro. La declaración
se conserva en `authorization.json` de la evidencia privada. No convierte el
cálculo de altura ni la instalación en una prueba física superada.

La secuencia preparada permite un ensayo explícito hasta depósito/apertura,
con pausa **antes de verificar liberación o ejecutar HOME**. Un retorno posterior
necesita confirmación actual de caja apoyada estable, abrazaderas descargadas y
libres, y recorrido completo de HOME despejado. No se presume esa confirmación
en este documento.

La ruta PC–robot observada usa Wi-Fi `wlx80afcad40bd6`, PC
`192.168.42.215`, red `.11.0/24` vía `192.168.42.2`. Se conserva esa conexión
existente, sin cambiar red, perfiles o rutas en esta preparación. Su disponibilidad
actual no demuestra estabilidad prolongada.

## Cronología del primer ensayo

| Paso | Estado y resultado |
|---|---|
| Autorización y copia previa | **OBSERVADO:** petición y condiciones físicas del operador archivadas; archivos locales previos conservados en `before/`. |
| Comprobación de efector | **VERIFICADO por lectura:** destino `clamp`, `loaded=true` y `files_match=true`; nueve servicios Motion y Control Center Vision coherentes con `HW_TYPE=cruzr_s2_v1`. Es verificación del perfil software; no sustituye la inspección del montaje físico. |
| Contraste del modelo nativo | **VERIFICADO por lectura:** coinciden los seis pines de HOME, descripción, URDF, task stack y bibliotecas nativas requeridos por el contrato. |
| Instalación del depósito69,5 | **INSTALADO EN DISCO:** se crean únicamente los dos archivos aditivos XML/YAML de la tarea nueva; originales no sobrescritos, cero comandos de movimiento y cero reinicios según recibo. `loaded=not_verified`, `physical_validation=pending`. |
| Primer preflight, 11:55:32–11:55:33 UTC | **BLOQUEADO ANTES DE ETAPAS**, rc78: `SPS_PACKAGE_MISSING`, paquete `bf145fa17e1116fc` incompleto en el contenedor nativo de manipulación. No se interpreta como fallo del cálculo de altura ni como intento de depósito. |
| Inspección SPS | **VERIFICADO por lectura:** faltan las seis fuentes `/opt/cruzr-front-box/bf145fa17e1116fc/` en el contenedor nativo; las copias del host y del contenedor ROS están presentes. Los tres XML/YAML `local_front_box` ya existían. |
| Restauración SPS, 11:56:27–11:56:30 UTC | **VERIFICADO por recibo**, rc0: reinstalación de la misma identidad mediante el instalador versionado. `created_tasks=[]`, `originals_overwritten=false`, `restarts=0`, `movement_commands=0`. No se cambia el rango de caja, los límites ni las tareas de recogida. |
| Nuevo preflight, 11:56:56–11:57:11 UTC | **LECTURA COMPLETADA**, rc55: salud/HOME recibidos, dependencias contrastadas y puntos presentes; `nav_state=FSM_WAITRELOCATE`. No se inicia una etapa del ciclo. |
| Inicio posterior del ensayo, 11:58:05 UTC | **EJECUTADO**, con confirmación física vigente y modo `--run --table-height-cm 69.5 --stop-after deposit --deposit-trial`. A partir de aquí sí se envían comandos físicos del ensayo. |
| Navegación a `get1` | **ETAPA COMPLETADA:** relocalización `NAVIGATION_READY`, navegación exitosa y dos poses de llegada a 10,0 mm y 0,42/0,41°. Duración de etapa 37,973 s. Son errores respecto a la localización del mapa, no medición física independiente. |
| Activación de visión | **ETAPA COMPLETADA:** resultado `SUCCEED`, duración 2,093 s. |
| Preparación de recogida | **OBSERVADO:** cabeza `SUCCEED`; dos ajustes visuales X solicitados de 29,9 y 12,1 mm, con llegadas comprobadas y nueva medición. X de caja pasa aproximadamente por 79,988→78,212→75,230 cm; el gate nativo posterior registra XYZ≈75,04/−4,69/79,28 cm en `base_link`. Son observaciones del registro, no medición independiente de la escena. |
| Agarre nativo | **INTERRUMPIDO:** tras unos 20,6 s de progreso, `WATCHDOG: PERSISTENT_WORKER_LOST: no se permiten nuevas órdenes`. Se solicita cancelar únicamente el goal de esta ejecución; respuesta de cancelación código0, resultado de acción status5 y `physical_stop_verified=false`. El ejecutor no recibe un resultado de acción SUCCEED de recogida. |
| Fin, 12:00:10 UTC | **rc78:** checkpoint fallido en `grasp`, `box_state=unknown`; no se ejecutan retirada, navegación a `put1`, depósito, liberación ni HOME. |

El preflight posterior a SPS registra dos muestras de los 20 ejes corporales:
`MEASURED_HOME=1`, posición absoluta y diferencia consigna–medida máximas
`0,001534 rad`, velocidad máxima cero. Paros principal/servo `0/0`, cargador `0`,
baterías `71,5/71,3 %`. Son muestras de este preflight, no una garantía del
estado físico después del corte.

En el preflight, el mapa leído era `utars_nav_map`, con `get1` y `put1` de tipo
`logo_nav`, y el navegador esperaba relocalización. El ensayo posterior sí
registra `NAVIGATION_READY` y la llegada a `get1`. No se publican aquí sus
coordenadas para reutilizarlas como referencias de otro montaje. El checkpoint
del preflight conservaba `completed=[]` y `box_state=empty`; el final del ensayo
registra sólo `navigate_get1` y `enable_vision` completadas, `in_flight=null`,
`box_state=unknown` y fallo en `grasp`. No interpretar `unknown` como caja
sujeta, apoyada o liberada.

La consola incluye errores de lease y del worker de salud durante el cierre.
El resultado principal conservado es rc55 con `FSM_WAITRELOCATE`; esos errores
de cierre **no acreditan por sí solos** un nuevo fallo físico de actuadores o
paros. El `NAVIGATION_READY` posterior pertenece al ensayo y sustituye aquel
pendiente técnico de localización para la navegación realizada.

## Interrupción del agarre y alcance del diagnóstico

El goal propio de agarre es `71d41002-5751-42a1-aec4-3d2b4ebe74bc`.
El diario registra primero el watchdog de worker persistente perdido y después
la cancelación de ese UUID, con `return_code=0`, lista de goals cancelándose y
resultado terminal status5. El ejecutor registra expresamente
`physical_stop_verified=false`. No se traduce ese acuse en inmovilidad física
comprobada ni en una maniobra de descarga de la caja.

El worker de salud termina con
`ValueError: LIVE_HEALTH_PUBLISHERS: lost or ambiguous controller`. El checkpoint
conserva como fallo terminal de la etapa
`WORKER_REQUEST_FAILED: Lease missing, invalid or expired`. Se preservan ambas
capas del diagnóstico: no confundir el error de cierre/lease con la primera
alarma del watchdog ni afirmar qué servidor de servicio o componente físico falló sin
contrastar los logs del robot.

Los seis pines y las dependencias habían pasado el preflight. La interrupción
ocurre antes de usar la tarea de depósito69,5; **no hay evidencia aquí de que
la altura, el modelo o las dos Z nuevas sean la causa del error**. Tampoco se
descarta un problema de control por conservar los hashes. Causa concreta y
estado de actuadores/controladores posteriores PENDIENTES de diagnóstico.

Se ha solicitado al operador describir el estado físico posterior y las
condiciones para cualquier prueba nueva. Su declaración y las limitaciones del
seguimiento se registran a continuación. No se reinicia el ciclo, reintenta
agarre, abre ni envía HOME automáticamente. La confirmación inicial de
condiciones no sustituye la inspección después de esta interrupción.

## Seguimiento posterior y apagado/encendido comunicado

**OBSERVADO por declaración del operador:** «he quitado todo apagado y vuelto a
encender sin problema». Esto comunica retirada y un ciclo de alimentación;
no acredita por sí solo HOME20D medido, postura actual, estado de la caja o de
las piezas, ni el orden exacto del apagado respecto al error registrado. Se ha
preguntado si apagó antes o después del error y por las condiciones físicas
nuevas. Sobre el orden temporal respondió después **«no lo sé, quizás antes
de eso»**: la secuencia causal sigue indeterminada. Las condiciones físicas se
confirmaron de nuevo antes del segundo ensayo, como se registra más abajo.

Lectura posterior conservada en `post-interruption-read.json`:

- La aplicación Motion conserva el mismo ID de contenedor, pero registra
  `StartedAt=11:59:17 UTC` y `RestartCount=8`. Conservar el ID no demuestra
  continuidad del proceso. No se atribuyen esos reinicios al instalador ni se
  fija su relación con el apagado manual sin la aclaración pendiente.
- El worker de salud enclava a las `11:59:11.722 UTC` una consulta de
  disponibilidad: `getServiceCount` es el **recuento de servidores del servicio**,
  cuya comprobación de unicidad falla. No significa que la respuesta RPC de
  controladores fuese inválida. La última respuesta RPC aceptada es de
  `11:59:11.421 UTC`, unos `0,301 s` antes: estaba fresca y no corresponde a
  un rechazo por antigüedad de esa última muestra.
  El `count=1` conservado es el **último valor aceptado**, no el resultado de
  la comprobación fallida; no permite inferir si ésta observó cero o dos servidores.
- El log nativo registra `Clamp box succeed` a las **11:59:14.490 UTC**, mientras
  el resultado cancelado status5 del cliente es de **11:59:12.600 UTC**: la
  diferencia es aproximadamente **1,89 s**. Se corrige la interpretación anterior
  de `14.490` como duración; es la fracción final de una hora. Este evento
  posterior no sustituye el resultado del ejecutor, no demuestra sujeción física
  o continuidad del control y no cualifica el ensayo69,5.

Posteriormente, el kernel del PC registra desautenticación de la Wi-Fi del
robot a las **12:02:12 UTC / 14:02:12 CEST**. Las consultas SSH a `.11` agotan
timeout y no había ruta Ethernet alternativa operativa. Es compatible con una
interrupción durante el apagado/encendido comunicado, pero la causa exacta no
está demostrada. No se afirma un reset USB ni que este corte posterior de red
del PC causase el fallo previo del worker/controladores del robot.

NetworkManager reconecta automáticamente el perfil Wi-Fi **`Cruzr S2-0669 1`**;
la ruta vuelve a usar `192.168.42.2`, PC `192.168.42.215`. El agente no cambió
configuración de red para recuperar esa conexión.

La nueva lectura `docker-timeline-post-reboot-read.json` muestra todos los
servicios Motion con `StartedAt≈12:04:28 UTC` y `RestartCount=0`. Es un estado
posterior al del contador8; no se combinan ambos como si fueran una instancia
continua. La consulta de eventos Docker posterior no aporta el historial previo
necesario para reconstruir por sí sola cada reinicio durante el ensayo. Los logs
de clamp conservados permiten contrastar las horas anteriores, sin inferir con
ello HOME actual.

El `post-reboot-effector-check` verifica de nuevo `clamp`, con
`loaded=true/files_match=true` en Motion y Vision. El **check nuevo de
12:06:37–12:06:48 UTC termina rc78** por
`WORKER_REQUEST_MISMATCH: no result confirmed`, antes de recibir el resultado
de salud. No inicia etapas ni acciones de movimiento y **no valida HOME**.

La recuperación posterior de snapshots identifica la causa primaria que ese
mensaje de transporte no mostraba: sesión `/tmp/cruzr-scenario1-iqhrqpju`,
`live-health.json` con `written_ns=1792584349930288974` y error exacto
**`estop not confirmed clear`**. La marca equivale a `12:05:49.930 UTC` en el
reloj de origen del snapshot; los recibos del PC y las marcas del robot se
conservan con su origen, sin tratarlos como un único reloj sincronizado.

El snapshot conserva `publishers={}` y `safety={}`: el worker falla antes de
entregar el resultado de salud, lo que explica la salida sin resultado de
petición confirmado. La conclusión documentable es **señal del paro principal
no confirmada libre**; no se afirma que el pulsador físico estuviera accionado
sin el payload original y la confirmación presencial. `WORKER_REQUEST_MISMATCH`
ocultaba esta causa primaria del check; no es una demostración de fallo de
actuadores o de la trayectoria69,5.

Este bloqueo posterior al encendido es distinto del fallo previo en el recuento
de servidores de servicio durante el agarre. No se atribuye el incidente
original al estado de paro del check posterior, al reinicio ni a la altura.
La causalidad del primer fallo sigue pendiente: el orden temporal comunicado
no permite atribuirlo a un paro previo ni a la comprobación del software.

Después de un cambio de boot o pérdida de continuidad de esta ejecución,
**no se reanuda el checkpoint anterior**. La preparación de la nueva sesión
recuperó una lectura actual y una confirmación física renovada. No se envió
HOME automático como recuperación del fallo.

## Segundo ensayo: final rc78 por frescura de recepción del paro

**OBSERVADO por declaración actual del operador:** «todo ok» para las
condiciones solicitadas de mesa a 69,5 cm, montaje clamp, caja y abrazaderas,
HOME/postura, cargador fuera, paros, recorrido libre, control exclusivo y
supervisión. Esta confirmación renueva las condiciones para la prueba nueva;
no determina retrospectivamente el orden de paro, apagado y fallo del primer
ensayo.

El `restart-ready-check`, de **12:10:13 a 12:10:26 UTC**, termina **rc55**.
La salud y HOME pasan: dos muestras de los 20 ejes, posición absoluta y
diferencia consigna–medida máximas `0,002589 rad`, máximo de brazos
`0,000959 rad`, velocidad máxima cero, paros principal/servo `0/0`, cargador `0` y
baterías `70/70 %`. El único impedimento de readiness registrado es
**mapa vacío, `FSM_WAITSETMAP`**. Este resultado nuevo sustituye el pendiente
de salud/HOME del check anterior; no convierte el primer ensayo en válido.

El segundo ensayo se lanza a las **12:10:54.847524 UTC / 14:10:54
Europe/Madrid**, con autorización renovada, en `deposit-trial-2/`. Es una
sesión nueva **sin `--resume` del checkpoint previo** y con el modo:

```text
--run --table-height-cm 69.5 --stop-after deposit --deposit-trial
```

El escenario realiza la preparación de mapa y relocalización antes de navegar
a `get1`. El resultado final de **12:12:08.663877 UTC** es **rc78**:

| Paso | Resultado observado |
|---|---|
| Navegación a `get1` | Etapa completada en `44,692 s`; dos poses de llegada alrededor de `13,0 mm / 0,39°`. Son errores del mapa, no medición independiente. |
| Activación de visión | `SUCCEED`, etapa `2,384 s`. |
| Preparación de cabeza | Acción de bajada `SUCCEED`, aproximadamente `2 s`. |
| Interrupción | `WATCHDOG: LIVE_HEALTH_STALE: estop receipt`, antes de medir la caja e iniciar el agarre nativo. Después aparecen expiración del lease y errores del worker durante el cierre. |

El checkpoint conserva `completed=[navigate_get1, enable_vision]`,
`in_flight=null`, `box_state=unknown` y fallo de etapa `grasp` por
`WORKER_REQUEST_FAILED: RuntimeError: Health worker lease expired or stop requested`.
La etapa de preparación incluye cabeza; **no se lanzó el agarre nativo de
brazos ni se ejecutaron recogida, navegación a `put1`, depósito o HOME**.
`box_state=unknown` es el estado conservador del ejecutor al fallar; no demuestra
que la caja estuviese sujeta.

**OBSERVADO por declaración posterior del operador:** «Nadie tocó los
controles» durante este segundo intento. La alarma indica frescura de recepción
no satisfecha; no acredita una pulsación del paro ni determina por sí sola la
causa del transporte. El orden temporal del primer fallo continúa desconocido.
El snapshot posterior conserva un `written` reciente, unos `0,0719 s` al ser
recogido: es posterior al watchdog y no permite asignar al último archivo la
edad exacta que activó la alarma. Debe distinguirse esa actualización posterior
del dato observado por el watchdog en su instante de decisión.

La pausa del modo de ensayo sigue siendo anterior a verificar liberación y a
HOME. Un eventual retorno exige confirmación nueva de caja apoyada estable,
abrazaderas descargadas y libres y trayectoria de HOME despejada; no queda
autorizado automáticamente por completar el depósito.

## Seguimiento de QoS y tercer ensayo final rc78

La lectura `second-interruption-safety-read.json` descubre **un publicador
único por topic**, `/emb/estop_key_state` y `/emb/servo_estop_key_state`, ambos
`RELIABLE/VOLATILE`. `safety-qos-native-api.json` confirma que la API nativa
`SensorDataQoS.reliable()` y la durabilidad volátil están disponibles. Son
observaciones del grafo y de la API, no una demostración de la causa del fallo.
El diagnóstico considera la recepción ROSA nativa y el bridge ROS2; las
capturas no constituyen una comparación simultánea con todos los colectores
en los mismos procesos.

Se modifica en el PC únicamente
[`scenario1_health_worker.py`](../../scripts/box_handling/scenario1_health_worker.py):
las ramas `estop` y `servo` solicitan `RELIABLE`, manteniendo `VOLATILE`.
Los demás lectores conservan su QoS; no cambian límites de frescura,
enclavamiento de paro, validaciones ni límites físicos. No se modifica el QoS
de los publicadores del robot. Fuente aplicada SHA256
`42d6530a729793ece6ce5a58fafc02b9758337c4347d7077ba473efa8ba0117e`.

Copia previa local en `before-safety-qos/scripts/box_handling/`, con manifiesto
`before-safety-qos-manifest.json`; el worker previo tiene SHA256
`e389c9c34628b7d035f53929ec0ec95dfc6abbc3b01b535381d530ce9fd3ab7d`.
La reversión consiste en recuperar esa fuente previa, conservar el diagnóstico
y volver a comprobar su compatibilidad antes de otra ejecución. La validación
local comunicada por el agente de pruebas es **68 tests PASS**, incluidos
tres nuevos para esta selección de QoS.

El operador comunica haber enviado HOME y solicita una prueba nueva.
`reliable-safety-check`, de **12:19:10 a 12:19:47 UTC**, termina **rc0,
`CHECK_OK`**, con salud/HOME20D, paros y mapa/puntos válidos más cinco rondas
adicionales, aproximadamente `25 s`. El check no envía movimiento. Una captura
pasiva separada de `12 s` registra dos mensajes de cada paro y 451 mensajes de
actuadores; queda `usable=false` por una línea C++ que no es JSON. Ese fallo de
parseo no acredita un fallo físico nativo ni vuelve equivalentes las capturas.

El **tercer ensayo comienza a las 12:20:11.138436 UTC / 14:20:11
Europe/Madrid**, en `deposit-trial-3/`, como sesión nueva autorizada y limitada
por `--run --table-height-cm 69.5 --stop-after deposit --deposit-trial`.
El recibo fija la fuente del worker citada. Aunque el usuario solicita ejecutar
el ciclo completo, se conserva el ensayo acotado con pausa antes de HOME:
`PHYSICAL_QUALIFICATION=None` para 69,5 cm. No se activa el ciclo completo
por defecto ni se omite ningún gate.

El tercer ensayo termina a las **12:21:14.546552 UTC**, **rc78**:

| Paso | Resultado observado |
|---|---|
| Navegación a `get1` | Etapa completada en `7,248 s`; dos poses alrededor de `9,5 mm / 0,37°`, según la localización del mapa. |
| Activación de visión | `SUCCEED`, etapa `1,467 s`. |
| Preparación de cabeza | Bajada `SUCCEED`, aproximadamente `2 s`. |
| Primera observación de caja | X≈`79,803 cm`, fuera del margen requerido para iniciar el agarre. Es una observación de visión, no medición física independiente. |
| Primera corrección | Avance solicitado `28,0 mm`; llegada registrada alrededor de `7,8 mm / 0,30°`. Nueva observación X≈`77,672 cm`. |
| Segunda corrección | Avance solicitado `20,7 mm`; se interrumpe por `Correction made no significant progress`, con varios avisos `LOCATION_LOST`. |

Se cancela únicamente el goal de navegación propio
`04a2dd55-066c-4746-97d9-3c891507c322`: acuse `return_code=0`, resultado
terminal status5 y `physical_stop_verified=false`. El acuse no certifica una
parada física medida. El checkpoint conserva sólo `navigate_get1` y
`enable_vision` completadas, `in_flight=null`, `box_state=unknown` y fallo en la
etapa `grasp` con `WORKER_REQUEST_FAILED: Correction made no significant progress`.
**No se inicia el agarre nativo ni se ejecutan recogida, retirada, navegación
a `put1`, depósito o HOME del ciclo.**

En esta tercera sesión **no se observa el fallo de frescura de recepción de
paro** de la segunda. El resultado acota la comprobación del QoS a esta sesión
y al preflight de cinco rondas; no demuestra fiabilidad exhaustiva ni resuelve
el fallo de localización/progreso. No se ensaya de nuevo hasta resolver ese
impedimento o preparar físicamente otra vez la aproximación de la caja y
comprobar las condiciones actuales. Los tres resultados preceden al depósito;
no aportan evidencia física sobre las dos Z nuevas ni cualifican 69,5 cm.

## Dos checks de lectura previos al cuarto ensayo

Tras pedir de nuevo optimistic hasta depósito, el operador confirma
abrazaderas vacías, robot inmóvil, preparación, zona y persona junto al paro.
`before-deposit-trial-4-check` termina rc78 sólo por `HOME_NOT_MEASURED`,
con `head_pitch≈−0,430569 rad`, sin movimiento.

El check versionado `bash scripts/cruzr_recover_to_home.sh --check` termina
**rc1**. La primera captura registra 20 actuadores quietos y OperationEnabled,
perfil clamp, baterías `67,5/67,3 %`, paros `0/0`, cargador fuera, acciones
listas, FSM unlocked e historial unknown sin unsafe observado. El segundo
capturador falla con **«No se obtuvo una muestra fresca de /mc/actuator_state»**.
No se clasifica ruta ni se envía movimiento; esa captura inicial no sustituye
la segunda muestra fresca requerida ni valida HOME. Se conserva
`head-home-recovery-check.log` en la evidencia privada.

Hasta ese corte no se inicia un cuarto ensayo ni una orden física de
recuperación del agente. La consulta del usuario sobre volver a HOME con su
mando habitual precede a su confirmación renovada y al lanzamiento siguiente.

## Cuarto ensayo: final rc78 durante agarre nativo

El usuario confirma **HOME de nuevo y mandos detenidos**, con las condiciones
físicas recién confirmadas de abrazaderas vacías, preparación, recorrido libre
y persona junto al paro. El lanzamiento real queda registrado a las
**12:31:03.029430 UTC / 14:31:03 Europe/Madrid** en
`deposit-trial-4-launch.json`, con evidencia independiente en `deposit-trial-4/`:

```text
--run --table-height-cm 69.5 --stop-after deposit --deposit-trial
```

Es el mismo optimistic en una sesión nueva, con alcance de recogida,
transporte, depósito/apertura y **pausa antes de verificar liberación o HOME**.
No se reutilizan los checkpoints fallidos. Los dos checks de lectura anteriores
no cuentan como ensayo físico; éste sí es el cuarto ensayo autorizado.
El resultado final es **rc78**, conservado a las **12:32:27.543990 UTC /
14:32:27 Europe/Madrid, reloj del PC**.

| Paso | Resultado observado |
|---|---|
| Llegada a `get1` | Etapa completada en `8,726 s`; dos poses aproximadamente `10,6 mm / 0,44°`, según localización del mapa. |
| Visión y cabeza | Visión `SUCCEED` en etapa de `1,603 s`; bajada de cabeza `SUCCEED`. |
| Alineación | Caja X≈`77,910 cm`; corrección solicitada `23,1 mm`, llegada alrededor de `4,9 mm / 0,42°`; nueva caja X≈`76,500 cm`. |
| Gate nativo | XYZ≈`76,31 / −3,41 / 79,25 cm`, dentro de los límites comprobados. Son datos registrados, no una medición física independiente. |
| Agarre nativo | Se inicia y progresa aproximadamente `19,4 s`; después `WATCHDOG: PERSISTENT_WORKER_LOST: no se permiten nuevas órdenes`. |

La cancelación se dirige únicamente al UUID propio
`7a2f11f7-647d-4129-82e8-4f5ca34fb9c7`, con acuse `return_code=0` y
resultado status5; `physical_stop_verified=false`. El worker de salud termina
con **`ValueError: estop not confirmed clear`**. El checkpoint conserva sólo
`navigate_get1` y `enable_vision` completadas, `box_state=unknown`,
`in_flight=null` y fallo en `grasp` por
`WORKER_REQUEST_FAILED: Lease missing, invalid or expired`.
**No se ejecutan verificación de caja sujeta, retirada, navegación a `put1`,
depósito, liberación ni HOME del cuarto ciclo.**

`fourth-interruption-read.json` conserva el snapshot de error y los últimos
valores aceptados de estop/servo `0/0`. Esos valores previos **no descartan una
señal de fallo entrante** ni demuestran que el pulsador físico estuviese libre
en el instante del error. Se documenta paro principal no confirmado libre,
sin afirmar una pulsación ni una causa de transporte concretas.

La lectura Docker del robot registra la aplicación nativa con
`RestartCount=1`, `StartedAt=12:31:33.701726265Z`; ROS conserva `RestartCount=0`.
Los logs nativos incluyen `Clamp box succeed` a las
`20:31:32.452661 UTC+08` y `HQP solve failed`. No se atribuye causalidad al
reinicio ni se interpreta ese éxito nativo como recogida física verificada,
continuidad de control o cualificación del depósito.

**Los relojes del PC y del robot difieren aproximadamente un minuto.** Por
ejemplo, hay eventos remotos a `12:30:15` frente al lanzamiento del PC a
`12:31:03`. Se conservan ambas referencias con su origen; no se ordenan como
un único reloj ni se deducen latencias entre ellas. Las duraciones de etapa
anteriores proceden de sus propios registros, sin restar relojes distintos.

La ausencia de `estop receipt stale` en la tercera sesión y su preflight no
demuestran una solución exhaustiva del QoS: la cuarta falla por una señal de
paro no confirmada libre, que requiere diagnóstico separado. **Se ha pedido
confirmación física actual de inmovilidad y de caja apoyada, sujeta o retirada;
estaba PENDIENTE en ese corte.** La confirmación recibida y la decisión posterior
se registran a continuación. No reintentar agarre, iniciar otro ensayo ni enviar HOME
automáticamente. Ninguna de las cuatro sesiones llega a la tarea de depósito695.

**Declaración posterior del operador:** «he presionado el paro de emergencia,
y lo he liberado», seguida de petición de recuperar HOME e identificación de
`./scripts/force_home.sh` como su mando habitual. Esto comunica una actuación
del operador, pero su orden respecto al fallo del cuarto ensayo sigue
**PENDIENTE**; no se le atribuye la causa del error. La petición autoriza la
recuperación solicitada, pendiente de confirmar físicamente caja apoyada o
retirada, abrazaderas vacías y libres, recorrido completo, cargador, mandos
detenidos y persona junto al paro. **No se ha enviado una recuperación ni
otro ensayo en este corte.**

## Paro real corroborado y apagado/arranque elegido, todavía pendiente

El operador confirma después **caja libre, abrazaderas vacías y libres,
recorrido, cargador fuera, mandos detenidos y persona junto al paro**.
`recovery-home-preflight-4` termina **rc78** tras aproximadamente `12,9 s`:
cero publicadores/muestras de actuadores y estado, `controller_received=false`;
sí se reciben batería, cargador y ambos paros. No clasifica una recuperación
ni envía movimiento.

Las lecturas locales conservadas en `post-stop-recovery-motion.json` y
`post-stop-recovery-vision.json` muestran:

- Hardware reiniciado a `12:31:28.848384166Z`, `RestartCount=1`, esperando
  `/mc/rosa_control/start` («Wait to running»).
- Aplicación nativa de manipulación reiniciada a `12:31:33.7017Z`,
  `RestartCount=1`, esperando `ListControllers`.
- Control Center, en su reloj **UTC+08**, registra estop1 a
  `20:31:28.367641`, `publishEstopPressed` y transición
  `Ready→WaitStartMotion(ButtonStopMotion)`. A `20:32:17.633082` registra
  estop0 y evento de liberación, **sin StartMotion posterior en el corte**.

Esto **corrobora el paro real declarado por el operador**. No se cataloga ese
evento como un fallo software o un payload inválido. Liberar el pulsador no
demuestra por sí solo que Motion haya vuelto a funcionar: las lecturas
anteriores muestran la espera de StartMotion/controladores. No se atribuye
por ello una causa a todos los reinicios ni se mezclan estos relojes con los
recibos del PC.

El usuario cambia su decisión a **«mejor apagaré todo e iniciaré todo»**.
Se explican brazos asegurados contra caída **antes de desenergizar**, apagado
lógico → pantalla y luces apagadas → KEY1 → chasis, y encendido con paro
principal mantenido. **Son indicaciones, no maniobras acreditadas:** aún no se
confirma el aseguramiento contra caída ni apagado/arranque realizados.
El agente no envía HOME, reset, rearme ni reinicios de servicios/software.
La petición HOME anterior queda sustituida por esta decisión del operador.
No hay un nuevo ensayo.

El recibo privado `post-stop-recovery-and-operator-restart-request.json`
conserva las referencias y hashes de las lecturas. Un arranque posterior
requiere redescubrir estado y procesos; no reanudar los checkpoints fallidos.

## Archivos de depósito instalados

Tarea:

```text
local_scenario1_deposit/da20110015415128cfc8d89ba7ce4f1dfa8e23498d72381d528316687545d128
```

Destino: Motion, contenedor redescubierto
`walker-motion.manipulation_robot_app-1`, imagen observada `9f7acf4b…`.

| Archivo nuevo | SHA256 |
|---|---|
| `/opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config/meta_clamp/local_scenario1_deposit/da20110015415128cfc8d89ba7ce4f1dfa8e23498d72381d528316687545d128.yaml` | `248ed8768897d2821ed3fab8f59c63f8e475d13aaaf1e523382713433a2ddc71` |
| `/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/local_scenario1_deposit/da20110015415128cfc8d89ba7ce4f1dfa8e23498d72381d528316687545d128.xml` | `39f624412602786e581eb74129a700f259b14b45a1775b53ab16f07348c54fd8` |

Recibo y reversión selectiva en Motion:
`/var/tmp/cruzr-scenario1-deposit/da20110015415128cfc8d89ba7ce4f1dfa8e23498d72381d528316687545d128/`.
El estado anterior de ambos destinos era ausente. Se verifican tres dependencias
originales y los seis pines del modelo/HOME; no se sustituyen las primitivas
vendor. La receta conserva los dos cambios de Z `0,650→0,895 m`, descenso
relativo de `0,200 m` y destino resultante `0,695 m` en coordenadas de tarea.

La restauración SPS conserva el paquete `bf145fa17e1116fc`, con archivo de
instalación en `/var/tmp/cruzr-front-box/bf145fa17e1116fc/`. El inventario previo
distingue fuentes ausentes en la aplicación de las ya presentes en ROS/host;
no se atribuye su ausencia a una causa de mantenimiento no demostrada.

## Evidencia privada y reproducción

Raíz:
`../Humanoide-vla-evidence/20261021T115405Z_BARCELONA_TABLE695_TRIAL/`.
Los JSON completos, identidades de contenedor y fuentes quedan allí, fuera de Git.

| Evidencia | SHA256 |
|---|---|
| `effector-check/plan.json` | `bcf17af28da9739f7277024bad8a827af16e1f119159453279192c8dc129dacc` |
| `native-model-compare.json` | `88ff1347807f3fffd3f864e05b411dc1bd283165ac8bd355202e334cf8c371c4` |
| `install/stdout.json` | `2bb8b5e5c588292c2ef2f135e9bc5d8f90bb72f4e7cda803f040046d7b5bb899` |
| `preflight-result.json` | `36b10306d17396620f35bd65749227676c2263d98364f3de24eabf34da1bc7ab` |
| `sps-before-read.json` | `f1270e24a7be6857f7f8cfd3a712f5209336311c855e1ec502b5fa47d57448d2` |
| `sps-install.log` | `7218cde01db7bcda32d85de83801befdeaf1d9eca632151f96e8e725ae50dcec` |
| `preflight-after-sps-result.json` | `3ca978b4939c6441f39992f0307db4bf98a92eebc3d97d6be33d6fb793104015` |
| `deposit-trial-result.json` | `1703ab554d69d13d0aa84c32a7da9f7d41049739eb31ce0f88f202d3cfae8ce3` |
| `deposit-trial/checkpoint.json` | `e4c07488ef197a93b28b875c39d48b6a16e3c70a301b3530a3d2e155b81318ba` |
| `deposit-trial/events.jsonl` | `b86c66bdc4fd10e602675175c6aac0a6e373d761c2c1c37ea17ee41e83d407d2` |
| `deposit-trial-console.log` | `d66348ea409f58e10bffba758319b4161b3040d0a49cb3721d3552a8dbf18a51` |
| `post-interruption-read.json` | `ee314292fb916896afce7043662b4b62271b1f34839348589c117588b579b7ec` |
| `docker-timeline-post-reboot-read.json` | `c2d8e51a222931633738b1905d32a2f1abba1adf386f3923af284ced7e66f97f` |
| `post-reboot-effector-check/plan.json` | `e6b8473fa3d2179f643abe2ebe9cbf64026efe67447d5a69885c71bf78361470` |
| `post-reboot-check-result.json` | `aa092c1259e4aca1a7eb151c462661c8481257ecf6c22f7d10bd639a0fab92ff` |
| `post-operator-reboot-network.json` | `14f4b90b8d55c99ba8fc54f221b6ee20b910f430dd883b2dd075368acdbeb986` |
| `post-reboot-snapshots-read.json` | `95f9dd7aec3f4aaa1895c6a94e84bb4ac7fed58af43b5c0e52cde7affd87dac3` |
| `post-reboot-check-console.log` | `93008d45d96cf8bfa80a86af7ca4998c129b7bc902cd4e11a9f430125455d017` |
| `post-reboot-check/source-sha256.json` | `1454151ee409785ff8b176d12d43d288f09cea3e7e60575fa211bb0301509511` |
| `restart-ready-check-result.json` | `76362c8df7dc6f4c48a1d600b9b8e0f179f16fe7457a50c737165050a71c906d` |
| `restart-ready-check-console.log` | `9607e9378cdf3a2375128eaefa1a5cd678a008583dd80fc3e703d76602ceb5f2` |
| `deposit-trial-2-launch.json` | `22616e7a95e45ec6df32862e1bfd3b59b7915e1c762e8ba8d7eec5db826dd593` |
| `deposit-trial-2-result.json` | `c9cb5189810c64b7e56e9e8947e568b3dbc732c3eac243b79f99970b190987df` |
| `deposit-trial-2/checkpoint.json` | `690b89ccdf17c01acf2bf6c5d21ece63bb0e69f69ff456d034b7895698757eeb` |
| `deposit-trial-2/events.jsonl` | `b5e770febe8d70f8fcb86f0eda63c1ef71fc70c7a1ab0f087637c4dc021afb23` |
| `deposit-trial-2-console.log` | `338db99be044f4ad93e1fa88ba75f3efd7699adca764743e5bf1f029e652a906` |
| `second-interruption-safety-read.json` | `de64516e3bb296a30d4e507bea048321804ca20d18a78241bf47e94e4626445f` |
| `safety-qos-native-api.json` | `15689a0ddb5dd086d8653215837146aa9add670a6ea3b99a4dd71a77d7d27e96` |
| `before-safety-qos-manifest.json` | `05d6f47e0ad9daf03b57031aaf746cd4764522bffa0618d5bd30cdc82720bec6` |
| `reliable-safety-check-result.json` | `0b535b04182eae0361395ba39f5c5c6f5e7135726b9426313e6d705c2f1b13d2` |
| `reliable-safety-check-console.log` | `7b1ec15b585817b181a197e023c5d9979a1f5c40f89fcaf6c6c4a7b1c68f0385` |
| `post-home-passive.log` | `dc74729cdd3c2c8700094f689505e87cb8743f656944a3f698301331b1383b7b` |
| `deposit-trial-3-launch.json` | `879e936b6b3e862f9b2b5c30a8de9f9d20f3c2acff26211762f2ebf6cca2adfe` |
| `deposit-trial-3-result.json` | `0abb368dae4416d8c0380b5fad409cf959aef1dacef88f45590323154404135b` |
| `deposit-trial-3/checkpoint.json` | `25ef5a2870e6fbcfe8bc89102b2a6ef44ce51869f58c58d6f2a67b94b28b8d78` |
| `deposit-trial-3/events.jsonl` | `f8eee6e6a0d7a0e30a41161d89a175da1fc0ac21d5b16ffa88cd38219fadd487` |
| `deposit-trial-3-console.log` | `7e3d25800b6efc86f048648170dde8e31730f274b95e55f8a659f1d4584f22d6` |
| `head-home-recovery-check.log` | `4139beac551b643a98d06c2d01317a80cf1e0ffb254534f39704f2749f1688fa` |
| `deposit-trial-4-launch.json` | `c9f9168e40c6f4e51a305097ca2557fe5614f5c1a890555a67f21c6273564aa9` |
| `deposit-trial-4-result.json` | `747da18b706b61a491ca919c950fc68a58321c3a613e417e2c3e603ea950594b` |
| `deposit-trial-4/checkpoint.json` | `e4c07488ef197a93b28b875c39d48b6a16e3c70a301b3530a3d2e155b81318ba` |
| `deposit-trial-4/events.jsonl` | `72c254d42903fa0a361945cd256c380145fdee5c5c1b277882bcbc234c54803c` |
| `deposit-trial-4-console.log` | `c7e6b8481825dbf59daac303e052c2658105bae3649fbc973f1e25464ad8f47d` |
| `fourth-interruption-read.json` | `7fe3d8df7a69ec1fefe957d122546215fa1f42ab0d56cf73f715f803ebc04322` |
| `recovery-home-preflight-4/events.jsonl` | `87e0432db0b2b6e205056fbac2b50fd31c69b4e0bf71a2d9190f890d51fbc923` |
| `recovery-home-preflight-4/checkpoint.json` | `b908c5b76a40b6af3c75ebd7cb698e152b42744444ac31b1f64d1b373a3ddc6b` |
| `post-stop-recovery-motion.json` | `6243d0ad6b3c24911c118869fd6f6cd71160539e75e5e043539d299025ccfb36` |
| `post-stop-recovery-vision.json` | `073ac9966c9e9392241a4417d73019ff4676abaaf7b349090a4ad1b453462fdf` |
| `post-stop-recovery-and-operator-restart-request.json` | `1ac422c04f75ee622c76b045e39e5cef86f8737dbbe530125b613f64faaf195f` |

También se conservan logs de consola, eventos, contexto, checkpoints y fuentes
exactas del preflight. `before-manifest.json` y `before/` permiten contrastar
los archivos locales previos, incluidos cambios sin commit. Los comandos exactos
de cada invocación están en los recibos privados; no se copian salidas completas
ni credenciales en esta ficha.

El lanzamiento se conserva en `deposit-trial-launch.json`; los hashes anteriores
corresponden al resultado y archivos leídos después de terminar el proceso,
sin sobrescribir el checkpoint fallido ni fabricar etapas completadas.
El segundo lanzamiento queda separado en `deposit-trial-2-launch.json` y el
tercero en `deposit-trial-3-launch.json`; resultados, eventos, consolas y
checkpoints finales de ambos están identificados en la tabla. El cuarto se
registra por separado en `deposit-trial-4-launch.json`, con su resultado,
checkpoint, consola, eventos y snapshot final identificados en la misma tabla.
No queda un ensayo en curso en este corte.

Fuentes reproducibles:
[selector de efector](../../scripts/hands/cambiar_efector.sh),
[instalador69,5](../../scripts/box_handling/scenario1_table695_install.py),
[integración SPS](../../scripts/box_handling/front_box_integration.py) y
[guía del ensayo](../box_handling/SCENARIO1_BARCELONA_695.md).
No repetir instalaciones o fases de control basándose sólo en esta cronología.

## Pendientes y punto de reanudación

1. Conservar la incertidumbre sobre el orden del apagado y el primer fallo.
   El operador no puede fijarlo; no atribuir causalidad al paro, a la red del PC,
   al guard ni a la altura sin evidencia adicional. El fallo del recuento de
   servidores durante el agarre requiere su diagnóstico separado.
2. Las confirmaciones de caja libre, abrazaderas vacías/libres, recorrido,
   cargador, mandos y persona ya se recibieron. Queda confirmar aseguramiento
   contra caída antes de desenergizar y el apagado/arranque que el operador
   ha elegido; no afirmarlos realizados. No ejecutar la petición HOME previa
   ni sustituir su decisión por rearme/reset/reinicio software.
3. Mantener intactos los cuatro checkpoints fallidos; no reanudar el primero
   tras el cambio de boot. El tercer ensayo no repite el fallo de frescura del
   paro y el cuarto falla por paro no confirmado libre, ahora corroborado como
   paro real en Control Center: no constituyen una validación exhaustiva del
   cambio de QoS. Tras un arranque confirmado, redescubrir procesos/estado y
   resolver localización/progreso o renovar preparación antes de otro ensayo;
   no reintentar automáticamente ni inferir inmovilidad del acuse software.
4. Depósito69,5, liberación, HOME posterior y cualificación física de la altura
   siguen pendientes. Tras un depósito correcto, el retorno con caja declarada
   `released` necesita confirmación actual de apoyo estable, abrazaderas libres
   y recorrido seguro. Ninguno de los cuatro ensayos alcanza ese punto;
   `PHYSICAL_QUALIFICATION=None` mantiene bloqueado el ciclo completo a 69,5 cm.

No se recargaron servicios para estas instalaciones ni se modificaron límites,
red o firmware. Las comprobaciones e instalaciones iniciales no movieron el
robot; después comenzó el ensayo físico registrado arriba. Una reversión de
archivos no restaura la postura ni el estado físico de la caja.

Reversión del depósito: sólo retirar los dos archivos aditivos si sus hashes
coinciden con el recibo y la tarea está inactiva, conservando evidencia y
originales. Para SPS, comparar primero el inventario previo: no eliminar las
tareas y copias ROS/host que ya existían. Cualquier retirada posterior debe
registrarse en la misma intervención. No se ha ejecutado reversión, commit o push.
