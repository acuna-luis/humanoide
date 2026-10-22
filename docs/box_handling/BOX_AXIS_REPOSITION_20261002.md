# Corrección visual de posición antes de recoger

## Contacto del brazo izquierdo durante la entrada — 22-10-2026

### Prueba limitada de yaw izquierdo+2° y retorno — 22-10-2026

**BOX-LEFT-SHOULDER-YAW-2DEG-20261022. PROBADO FÍSICAMENTE en alcance acotado;
staging REVERTIDO.** El operador confirma preparación y después «hecho» a HOME
visual estable/libre/sin ruido y ruedas inmovilizadas. La única ejecución SDK
completa+2°/retorno en vacío y el operador confirma «Todo normal, sin contacto
ni ruidos». No valida rango completo, carga, postura del agarre ni depósito695;
la causa de la divergencia original permanece PENDIENTE.

**Plan revisado.** Fuente canónica por nombre, cinco grupos head/left_arm/
right_arm/lifter/waist,20D sin ruedas. Sólo `L_shoulder_yaw_joint` varía+2°
(0,034906585 rad) respecto al inicio; los otros19 ejes permanecen fijados a la
muestra medida. Inicio=final:22 s, hold inicial2, rampa quíntica8, hold máximo2,
retorno8 y hold final2. No se infiere el signo desde posiciones crudas de motor.
Límites de posición URDF y FK nominales pasan; origen de manoizquierda recorre
≈3,279 mm y codo-roll≈0,698 mm. Son orígenes del modelo, no certificación del
volumen de brazo/clamp, la calibración, la colisión global o la parada física.

**Contrato y admisión.** Player nativo y orden articular se contrastan por hash:
`8744a30ecce20c414dcf67b60d9aa7ac486bab752d5eee3de08a7336d65ddf0d` y
`7f9d7975ebd27774e5248afa666a71ecaeb24bad30a234c9af2b81abc321f39c`.
Preflight pasivo PASS: delta inicial0,20D habilitados/sin fault/velocidad0,
SDK libre, manipulación terminal4, paros0/0, cargador0 y baterías52/52,5%.
`run_native_diagnostic.py` repite los requisitos justo antes del envío; todos
pasan. Staging/preflight anteriores no son autorización reutilizable. Fuerza,
watchdogs, límites y configuración no cambian. La captura pasiva conserva
usable=false por el INFO no JSON; los mensajes completos se analizan de forma
informativa, sin falsear el flag o certificar toda la traza.

**Artefacto y receta concreta.** En
`../Humanoide-vla-evidence/20261022T071028Z_LEFT_SHOULDER_CONTROL_DIAG/yaw-left-candidate/`
se conservan constructor, muestra inicial, revisión FK/URDF, comprobador SDK y
archivo candidato original. SHA256 de sus bytes:
`b533dd93540a5bb604660d8a257aad80bac6a6da332751653d83ed66f13e6610`.
Se copió a una ruta nueva del contenedor Motion, con hash idéntico; archivo y
directorio se retiraron tras el cierre, conservando los bytes originales privados:
`/tmp/left_shoulder_yaw_diag_20261022T071028Z/left_shoulder_yaw_plus2deg_22s.motion`.
El primer auxiliar de staging falla de sintaxis antes de ejecutar; v2 confirma
copia/hash sin sobrescribir originales. La receta nativa que usa el runner,
después de sus gates y dentro del contenedor redescubierto, es:

```bash
source /opt/walker/setup.bash
export ROS2CLI_DISABLE_DAEMON=1
rosa run manipulation_outline_sdk player -- --robot utars \
  --input /tmp/left_shoulder_yaw_diag_20261022T071028Z/left_shoulder_yaw_plus2deg_22s.motion
```

Es registro de esta ejecución autorizada, no instrucción para repetirla.
Se omite `--loop` por el defecto conocido del parser. El SDK original no se
modifica. El inspector versionado `scripts/teleoperation/inspect_pico_motion.py`
y los archivos exactos del constructor/runner permiten revisar la preparación;
una reproducción futura necesitaría su propia admisión y orden explícitas.

**Resultado y estado final.** Una ejecución nativa sin `--loop`: preflight
inmediato completo PASS, inicio remoto07:24:38,818705 UTC y fin07:25:01,962784,
23,144 s de runtime para22 s solicitados. Player rc0 y texto
`is_finished=true ... bag has been played successfully`. No reintento ni
HOME después.3102 mensajes de actuadores y14 de cada paro, todos0:

| Medida del ensayo en vacío | Resultado |
| --- | --- |
| Excursión yaw real | 1,9775390625° frente a2° solicitados |
| Máximo error yaw consigna/posición | 0,000822637820 rad =0,047133675° |
| Mayor rango de los otros19 ejes | 0,00124636 rad |
| Postflight20D | Habilitados, sin fault, velocidad0 |
| Máximo delta corporal consigna/posición final | 0,001246359 rad |
| Máxima posición canónica corporal final | 0,004122573 rad, headpitch |
| Cliente SDK / writers de comando SDK | 0 /0 |

El servidor SDK permanece1; controlador de manipulación running,
`sdk_controller` y `vla_sdk_controller` initialized, módulos sin locks y
paros0/0/cargador0. Esto no significa arrancar el modelo VLA. Logs HW de la
ventana consultada sin patrones jump/fault/SAFEOP/Excessive; no se afirma
que no exista otro aviso. Operador: «Todo normal, sin contacto ni ruidos».
La observación y estos datos demuestran seguimiento de este movimiento pequeño,
lento y sin carga cerca de HOME; no el seguimiento en la postura del incidente.

**Hallazgo independiente de arranque.** `startup-limit-observations.json`
conserva102 avisos de cabeza: cmd−0,694701 frente a mínimo−0,688727 rad,
y315 de segunda articulación derecha: cmd0,133264 frente a máximo0,0987266 rad.
Ocurren durante HOME de arranque15:06:33/34, hora nativa, antes de esta prueba;
BTree termina correctamente15:06:48 y después se mide postura próxima a HOME.
No ampliar límites ni atribuir estos avisos al fallo previo de yaw izquierdo.

El log HW también conserva `servo cmd timeout, diff5 ms` a15:26:14 hora nativa,
posterior al fin del ensayo15:25:01. No es ausencia total de avisos ni causa
demostrada de la divergencia anterior. Muestra final con sello de fuente
07:29:53,473967 UTC:20 actuadores, velocidad0, delta máximo0,001246359 rad,
sin error o eje deshabilitado (`final-lowload-actuator-summary.json`).

**Reversión temporal completada y evidencia.** Player terminado y postflight
comprobado; `motion-diagnostic-cleanup.json` confirma eliminación del único
archivo nuevo y de su directorio vacío, cod0, con hash verificado antes de borrar.
Se conservan candidato original, constructor/SDK/contrato con hashes, runner y
receta exactos privados en esta evidencia. No hay persistencia nueva de SDK,
servicios o configuración. `physical-test-summary.json`,
`yaw-test-informative-tracking-analysis.json`, `motion-native-diagnostic-run.jsonl`
y `motion-test-postflight.json` contienen resultados; `yaw-test-passive-trace/`
conserva los datos y su usable=false original. Backups documentales en
`before-yaw-test-documentation/` y manifiesto. El cierre no incluye más pruebas u objetivos. Queda pendiente revisar la
postura de agarre y posibles limitaciones por carga antes de otro ensayo. `scope-close.json` confirma un goal SDK, cero HOME independientes,
resets, modos, reinicios o configuración cambiados. Sin commit/push.

### Reposo actual y semántica del aviso hardware — 22-10-2026

**BOX-LEFT-SHOULDER-CONTROL-DIAG-20261022. VERIFICADO por lectura pasiva;
causa bajo carga PENDIENTE.** El usuario ofrece liberar el paro para pruebas;
se indicó mantenerlo durante el diagnóstico y confirmar el estado físico.
Las consultas posteriores muestran que el paro ya fue liberado: CC registra
liberación a15:06:09,986 (hora nativa UTC+8), self-check y StartMotion correcto
a15:06:48, después JoystickMode. Son eventos observados, no comandos del agente.
En este corte pasivo estaban pendientes ruedas y HOME visual. El operador
los confirmó posteriormente para la prueba acotada cerrada arriba; aquella
lectura aislada no autorizaba por sí sola una prueba física.

**Lecturas actuales, no reconstrucción del incidente:** entre07:09 y07:11 UTC,
ambos paros0, cargador0, baterías52/52,5%, estado canónico20D próximo a cero
y velocidad máxima0. Servicio nativo de controlador disponible, cero writers
de `/mc/sdk/robot_command` y status de acción4 retenido: éste no es un latido
periódico ni una prueba adicional del movimiento histórico. ActuatorState con
BEST_EFFORT da20 ejes corporales habilitados, sin error ni fault, velocidad0 y
delta máximo consigna/posición0,0028762139773 rad. Yaw izquierdo medido
−0,0002876214 rad, consigna0; effort0,33 y current0,09 son valores reportados,
sin unidades/calibración validadas para diagnosticar carga o fuerza de contacto.
Este reposo posterior al arranque no demuestra que el motor esté globalmente
sano ni que el problema al agarrar haya desaparecido.

**Corrección de interpretación de `jump command`, limitada al binario verificado.**
La biblioteca viva `/opt/walker/ecat_hardware/lib/libecat_hardware.so`, SHA256
`d2594d81ac62376d2357529b2aa8a60008abd6f32ac08e0b29684eb4d9597957`,
coincide con el análisis estático offline. La rama compara
`abs(q_command-q_actual) >= 0.087 rad`; no calcula salto entre consignas
consecutivas. El log está limitado a intervalos mayores de1 s: siete mensajes
no demuestran siete saltos discretos. Esa rama no rechaza, recorta ni retorna
tras avisar; continúa con la consigna hacia CSP/mode8, `ServoCmdArray` y
`setServoCmdArray`. Hay `enforceLimits` antes y el comportamiento posterior del
master/servo no queda probado por esta rama. No generalizar la conclusión a
otra biblioteca o versión, ni interpretar el aviso como prueba de aceptación
física de cada orden. Las notas históricas que equiparaban «jump» con «rechazo»
no deben usarse para explicar este binario coincidente.

Una captura pasiva de6 s conserva148 muestras de actuadores y una de cada paro,
pero el analizador estricto mantiene **`usable_capture=false`** por una línea
INFO `Shared memory mode is turned off` no JSON. Se conservan datos y error
originales: no se modifica el flag ni se presenta la captura como plenamente
válida o como prueba física de parada. Sólo mide reposo en esa ventana.

**Evidencia y continuación:**
`../Humanoide-vla-evidence/20261022T071028Z_LEFT_SHOULDER_CONTROL_DIAG/`,
lecturas Motion/Vision, `fresh-actuator-summary.json`, `stationary-passive-trace/`
y scripts `collect*`/`remote*`; `before/` respalda esta documentación.
El análisis estático y su disassembly están en la evidencia anterior
`20261022T065229Z_LEFT_ELBOW_READONLY_DIAG/jump-command-semantics-readonly.json`
y `binary-semantics/`; su hash vivo se verifica en `motion-supplement-readonly.json`
del directorio nuevo. Diagnóstico en reposo; contacto/carga, control o límites
siguen por discriminar. No se ejecutan optimistic, agarre, HOME, reset, cambios
de servicio, configuración o umbrales. Sin commit/push. Las observaciones
previas siguientes conservan su fecha y no describen el estado actual.

### Diagnóstico nativo de seguimiento izquierdo — 22-10-2026

**BOX-LEFT-ELBOW-HW-TRACKING-20261022. VERIFICADO en registros recuperados;
causa física/control PENDIENTE.** El usuario autoriza diagnóstico con el robot
en paro. Se redescubren Motion, hardware y ROS activos tras el nuevo arranque,
`HW_TYPE=cruzr_s2_v1`. Una lectura fresca de `/emb/estop_key_state` devuelve
`data:1` a07:00:03 UTC (09:00:03 CEST); la app nativa espera ListControllers. No se demuestra
HOME ni estado seguro de caja/brazos. Todas las consultas son de lectura;
no se envían movimiento, reset, rearme, reinicios o cambios de configuración.

Los logs Docker de la app contienen corrupción/NUL y se cortan antes del goal.
Se recuperan sin repararlos los logs persistidos de `/etc/walker/log/motion/`,
con copia y SHA256. `robot_app.20261022-143452.65.log` identifica el UUID
`d48c4ef5-a880-4cab-ad21-a01b17de7889` del intento220593. En horario nativo
UTC+8, HW registra siete avisos `L_shoulder_yaw_motor send a jump command`
entre14:39:17,366 y14:39:23,371; registra E-stop después, a14:39:24,426772.
Posición reportada≈−1,03342→−1,03227 rad; consigna−0,946269→−0,125697 rad.
La separación crece hasta0,906573 rad (≈51,94°), frente a la advertencia0,087 rad
(≈4,98°). El hardware **advierte**: el log no demuestra si transmite o rechaza
esas consignas. La divergencia importante precede al registro del paro en el
mismo log HW; no es una falsa alarma causada sólo por detener el robot.

El vector articular nativo presenta elemento6 hasta−0,912253 rad, compatible
con esa divergencia, sin certificar el mapeo de índices sólo por su orden.
La mano izquierda registra errores de posición de hasta≈30 mm antes del último
fallo. `CheckPoseTrackingError` imprime a14:39:24,266854 los vectores de posición
`[-0.152945,-0.180321,0.0221676]` y rotación`[0.461929,-0.171935,-0.0869033]`;
termina `ClampPoseTrackingError`7101107. No se infiere su criterio interno exacto
de norma/eje sólo de esos textos. La separación aborta antes de completar su
trayectoria y **bodyback no comienza**. En149970/196799 no se observan aquellos
avisos HW previos; sus errores grandes crecen después de registrarse el paro.
No agrupar esos resultados como un mismo fallo de seguimiento anterior al paro.

**Objetivos y configuración leídos, no trayectoria física reconstruida.** El
log nativo entrega caja`[.7610,-.0608,.9057]`, entrada izquierda VISION
`[.4809,.0407,.9057]` y valor original clamp`[.7659,.2407,.9057]`.
El objetivo izquierdo nominal t14→16 pasa de`[.480856,.0407036,.905712]` a
`[.761026,.3015,.90566]`; son objetivos impresos, no posiciones3D reales del codo.
El stack instalado SHA256`bd8f5c38ac97c2a9ff19097b2bae43b0ab59827e377fd601ddfcfc1709da0e33`
coincide con la referencia histórica: manos, CoM, límites shoulder-roll y
manipulabilidad. No declara tareas explícitas de codo, torso o distancia a caja;
esa ausencia en este stack no demuestra ausencia de otras protecciones.

Contacto/carga, límites o funcionamiento del control y configuración requieren
discriminación; no hay motor averiado, singularidad o rama IK demostrados.
Faltan ángulos canónicos completos en el instante del contacto y fuerza calibrada:
no reconstruir FK del codo rellenando ejes con cero o confundiendo motor con
articulación, ni mezclar marcos de mano/base. El vínculo exacto vídeo↔goal sigue
sin confirmarse. Mantener la recuperación específica: no HOME, rearme o repetición
automática; no ampliar advertencias, fuerza o trayectoria para forzar un ensayo.

**Evidencia y reversión documental:**
`../Humanoide-vla-evidence/20261022T065229Z_LEFT_ELBOW_READONLY_DIAG/`,
`native-ik-hw-comparison.json`, `installed-config-structural-review.json`,
`kinematic-inputs/`, `motion-fresh-estop.json` y capturas/código `collect_*` y
`remote_*_readonly.py`. `before/` conserva estos dos documentos previos.
Sólo lectura remota y documentación local, sin cambios de código/sistema,
tests nuevos, commit o push. Historia de las observaciones anteriores a continuación.

### Vídeo WhatsApp: plegado del codo izquierdo — 22-10-2026

**Actualización del relato, OBSERVADO por el operador.** Sobre el nuevo vídeo
indica que la caja apenas se separa y que el izquierdo se fue hacia dentro;
aclara que pulsó el paro por ese movimiento y precisa: **«El codo se plegó
hacia el torso»**. No reducir el diagnóstico a que la muñeca necesite más
desplazamiento lateral. Debe revisarse la postura articular del brazo y la
envolvente del codo: una muñeca próxima a su objetivo no demostraría por sí sola
un recorrido adecuado del codo. En este caso tampoco hay seguimiento medido de
muñeca. No se ha demostrado singularidad, selección de solución IK, autocolisión
o una causa física concreta; el plegado reportado no acredita contacto con el torso.

**Qué aporta el vídeo.** Original
`/home/lacuna/Descargas/WhatsApp Video 2026-10-22 at 08.42.46.mp4`,21,373792 s,
478×850 a12,5 fps; SHA256
`3555cd77987ae51e450f5e633951bc49da3287c739eff9e5c6ddcdac7466643e`.
Se conserva copia,43 frames a2 fps y hoja de contacto. Se ve apertura/separación
vertical parcial entre cajas, pero no hay referencia métrica
para convertirla en altura o holgura lateral suficiente para entrar. El ángulo
cambia y no identifica inequívocamente el lado exacto de cada brazo. No concluir
que la caja se retiró ni que el codo siguió una determinada trayectoria 3D.

**Diario nuevo, distinto de las cancelaciones anteriores.** En
`20261022T063829Z_OPTIMISTIC_SCENARIO1_220593`, las fuentes de recuperación
capturadas coinciden con la revisión actual. El agarre nativo
`d48c4ef5-a880-4cab-ad21-a01b17de7889` devuelve a21,783 s de su aceptación
**ABORTED/status6, `ClampPoseTrackingError`,7101107**. En la misma ventana se
registra `LIVE_HEALTH_FAILED: estop not confirmed clear`. No hay
`cancel_requested` ni acuse de cancelación0 en ese objetivo: no presentarlo
como el terminal cancelado5 de los intentos196799 o149970. El resultado nativo
indica fallo de seguimiento de pose, pero no identifica articulación ni demuestra
su causa, y la proximidad de ambos eventos no fija por sí sola su orden físico.
El relato sitúa el paro como respuesta protectora al movimiento observado.

El manifiesto de ese diario corresponde al perfil695; no completa agarre,
retirada, put1, depósito o HOME. El vínculo entre este objetivo y el clip
WhatsApp continúa PENDIENTE de confirmación. El diario local sólo conserva
feedback global de ejecución, detección y resultado: no hay series de estados
articulares/actuadores, trayectorias cartesianas medidas/objetivo de muñeca,
residuales HQP ni FT durante el agarre. Los ceros de seguridad anteriores no
reconstruyen el mensaje que provocó el fallo. No deducir una postura o causa
mediante FK con datos de otra fase ni extrapolar un ensayo de llegada de base.

**Estado actual y siguiente paso.** El usuario comunica que se está encendiendo
con el paro todavía sin liberar. Es estado reportado, sin lectura nueva ni HOME
comprobado; caja sujeta/apoyada/retirada, estabilidad y contacto actuales siguen
PENDIENTES. No enviar HOME, rearmar, liberar para probar o repetir el agarre.
Primero confirmar el estado presencial y el arranque; después contrastar la
postura/objetivo izquierdos y percepción/TF de la ejecución correcta antes de
proponer cambios. Más fuerza, un objetivo de muñeca más exterior o más reintentos
no resuelven por sí solos el plegado del codo. El gate XYZ sigue siendo sólo un
filtro de posición de caja, no verificación de alcance, codo o barrido sin colisión.

**Evidencia y alcance:**
`../Humanoide-vla-evidence/20261022T064428Z_WHATSAPP_BOX_LEFT_ARM_VIDEO/`:
`source.json` conserva hash/receta de frames; `optimistic-latest-runs-review.json`
y `in-flight-telemetry-availability.json` conservan fuentes y límites del análisis.
`before/` respalda estos dos documentos antes de esta actualización. Sólo
documentación y consultas de archivos locales, sin SSH, movimiento, código,
fuerza, instalación o reinicio del agente. Sin nuevos tests por tratarse de
documentación; no commit/push. Historia anterior conservada a continuación.

**BOX-VIDEO-DESAPILADO-20261022. OBSERVADO por el operador y revisión local;
causa geométrica PENDIENTE.** El operador precisa: «yo presioné el paro porque
el brazo izquierdo golpeó la caja en vez de ponerse por el lado izquierdo».
Esta aclaración fija el orden comunicado: contacto primero, paro protector
después. El error de paro de una ejecución que corresponda a ese hecho sería
una consecuencia de la intervención, no la explicación inicial del golpe.
No tratarlo como una alarma falsa ni reducir la supervisión del paro.

Antes del paro, el operador indica que la maniobra continúa pero no consigue
retirar la caja; confirma que son las mismas cajas de la demo. El vídeo de
19,167 s muestra contacto de la abrazadera visible e inclinación/separación
parcial de la caja superior, sin retirada completa. La cámara se mueve y no
permite medir desplazamiento real, demostrar deslizamiento ni reconstruir el
recorrido del brazo izquierdo oculto por la caja. El contacto izquierdo queda
acreditado por el relato presencial; su instante y geometría exactos siguen
pendientes. Usar las mismas cajas no demuestra que su pose, altura de apoyo
y postura inicial del robot coincidan con las del ensayo que funcionó.

**Qué se ha contrastado sin mover.** El
[árbol nativo](../../vendor/ubtech/cruzr_s2/snapshot_20260916/motion/tasks/Singapore/separate_right_cruzr.xml)
prepara ambos brazos durante 3 s y después ejecuta separación y bodyback,
con duraciones nominales de 18 y 6 s. La
[trayectoria izquierda](../../vendor/ubtech/cruzr_s2/snapshot_20260916/motion/meta_clamp/wrc/separate_right_cruzr.yaml)
incluye un punto `ABSOLUTE [0.3, 0.4, 1.0]` en t=2 s y otro
`VISION [-0.285, -0.2, 0]` en t=8 s. No aparece un waypoint intermedio
explícito que rodee la cara de la caja entre esos puntos. El
[adaptador frontal](../../scripts/box_handling/front_box_integration.py)
conserva esa trayectoria. El
[contrato SPS](../../scripts/box_handling/front_sps_contract.py)
entrega la pose óptica original y comprueba el rango XYZ en `base_link`,
declarando `reachability_checked=False`. Cumplir el rango de posición de la
caja no demuestra que el camino del brazo esté libre de colisiones.

**Aclaración: hueco creado por la derecha y segunda entrada izquierda.** El
usuario pregunta si falta desplazamiento de la caja hacia la derecha o
recorrido del brazo izquierdo. La secuencia tiene otra entrada izquierda
posterior a la aproximación inicial t2→8. Estos tiempos pertenecen al
MetaClamp de separación; no están sincronizados con los segundos del vídeo:

| Tiempo nominal | Objetivo derecho | Objetivo izquierdo |
| --- | --- | --- |
| t14 | `SEPARATE_ABSOLUTE [0, -0.07, +0.06]` | `RELATIVE [0, 0, 0]` |
| t16 | `RELATIVE [0, 0, 0]` | `SEPARATE_ABSOLUTE [0, 0, 0]` |
| t17 | `RELATIVE [0, 0, 0]` | Cierre `RELATIVE [0, -0.07, 0]` |
| t18 | `RELATIVE [0, -0.005, 0]` | `RELATIVE [0, +0.005, +0.06]` |

La configuración fija una temporización; no contiene una condición explícita
que mida el hueco creado y sólo entonces autorice esa entrada izquierda. Esto
no permite afirmar qué comprobaciones internas adicionales realiza el binario.
Los offsets derechos no demuestran que la caja se traslade 7 cm lateralmente
o suba 6 cm: falta comprobar el movimiento efectivo de caja y abrazadera.
Si el contacto ocurre en t14→16, tanto una separación efectiva insuficiente
como un objetivo/recorrido izquierdo incorrecto son hipótesis compatibles;
pueden coexistir. Hay que comparar la holgura real en ese instante, la pose
de caja y los objetivos/posiciones reales del izquierdo antes de decidir qué
movimiento modificar. No aumentar recorridos a ciegas ni confundir esta fase
con un error del ajuste de base. No hay nueva prueba o cambio de trayectoria.

**Hipótesis a distinguir, no causas demostradas:**

- La pose/orientación detectada o su interpretación por Motion coloca mal el
  objetivo lateral izquierdo. Es necesario reconstruir la pose original, el
  quaternion y la TF correspondiente al instante de detección.
- El destino lateral es correcto, pero el recorrido desde la preparación
  articular o desde el punto absoluto cruza la caja. Hay que identificar la
  fase del golpe y comparar objetivos y posiciones reales del brazo.

Los offsets `VISION` no pueden interpretarse como coordenadas directas del
robot ni corregirse invirtiendo un signo por intuición. Tampoco basta con
aumentar alcance, altura, fuerza o número de intentos. La hipótesis anterior
sobre pérdida de sujeción en bodyback queda relegada frente al contacto
comunicado durante la entrada. La diferencia local de consignas laterales
nominales entre separación y bodyback, ±20 y ±5 N, no demuestra fuerzas
medidas ni explica por sí sola este choque. Los movimientos relativos de
6 cm tampoco equivalen a una elevación vertical garantizada de la caja.

**Relación con los reintentos y el diario.** La recuperación acotada descrita
más abajo actúa antes del agarre nativo y sólo ante falta de progreso de la
aproximación del chasis. No recupera contacto, paro ni agarre interrumpido.
El diario `20261022T061026Z_OPTIMISTIC_SCENARIO1_149970` registra éxito del
ajuste de base solicitado de 17,845 mm y cancelación durante el agarre unos
22 s después de aceptarlo. El worker termina con `estop not confirmed clear`;
acuse0/status5 no acreditan parada física, retirada ni sujeción. No está
demostrado que sea la ejecución del vídeo. El mensaje de seguridad que
provocó aquel fallo no se conservó; los valores cero anteriores no prueban
que el paro permaneciera liberado después. No usar ese diario para invertir
el orden contacto→paro que comunica el operador.

**Estado y punto de reanudación.** El usuario informa después «estamos
reiniciando». Sólo se registra el reinicio comunicado; no se ha verificado
que haya finalizado ni que el robot alcance HOME. Estado actual de la caja
(apoyada, sujeta o retirada), estabilidad de brazos, ambos paros y recorrido
PENDIENTES. No se ordenan HOME, rearme, liberación del paro, reinicio de
servicios ni repetición del agarre. Antes de cualquier nueva prueba debe
comprobarse la recuperación física y revisarse la entrada izquierda conforme
a la [guía de recuperación tras contacto](../guides/CRUZR_S2_RECUPERACION_TRAS_CONTACTO_TELEOP.md).
Un arranque correcto no valida la trayectoria que produjo el golpe.

**Evidencia y alcance documental.** Original:
`/home/lacuna/Descargas/MicrosoftTeams-video.mp4`, SHA256
`e0a0488377efc0e7837d54b787da92aa35a523af3509ca597cdb326bf84515ed`.
Copia, 19 frames, hoja de contacto, receta de extracción, relato actualizado
del operador, fuentes revisadas y análisis del diario en
`../Humanoide-vla-evidence/20261022T062519Z_BOX_MOTION_VIDEO_DIAG/`.
`incident-contact-report.md` conserva la aclaración; `source.json`,
`operator-confirmations.json` y `latest-optimistic-journal-review.json`
permiten contrastarla. `before-rewrite/` y `before-rewrite-sha256.json`
respaldan estos dos documentos antes de reescribirlos en `feriabarcelona`,
tras el cambio temporal de rama comunicado por el usuario. Se conservan las
notas y verificaciones anteriores; no se copian archivos completos de otra
rama. Reversión documental selectiva desde el respaldo, sin tocar controles.
Esta intervención sólo analiza archivos locales y actualiza documentación:
sin conexión al robot, cambios de código/configuración, instalación, pruebas
físicas, commit o push. La integración documental no valida el depósito695.

## Presupuesto vigente de ajustes visuales — 22-10-2026

**BOX-01-VISUAL-ALIGN-RETRY-BUDGET-20261022. Implementado y VERIFICADO localmente
en PC; prueba física PENDIENTE.** Las secciones de octubre2–7
que siguen conservan el alcance y los valores históricos de aquellas revisiones.
Esta sección fija el presupuesto vigente de la fase de aproximación visual.

El usuario solicita más intentos tras `BOX_ALIGNMENT_LIMIT`. El diario local
`20261022T052858Z_OPTIMISTIC_SCENARIO1_40744` muestra un primer desplazamiento
solicitado de29,828969950998596 mm y llegada9,2 mm/0,44°. La caja se vuelve a
medir en X=0,7805179438290441 m (78,051794 cm), Y≈−4,441 cm y Z≈79,055 cm
en `base_link`; Z no es altura al suelo. X cumple el gate exterior nativo de
0,79 m, pero excede el máximo interior0,77 m. La corrección necesaria10,517944 mm
se amplía por la tolerancia de llegada12 mm y el progreso mínimo2 mm, dando
24,51794382904414 mm. Sumada a la primera,54,34691378004274 mm, superaba los
50 mm acumulados: se detenía tras **un ajuste**, aunque el contador ya permitía
siete. Los errores de lease posteriores son consecuencias del cierre.
Son datos del intento archivado, no un estado actual ni una prueba de agarre.

| Límite de aproximación visual | Valor vigente |
| --- | --- |
| Correcciones máximas de caja | 7, conservadas |
| Solicitud máxima por objetivo, norma del vector X/Y | 50 mm, conservada |
| Suma de longitudes solicitadas | 100 mm, antes50 mm |
| Presupuesto global de esta fase | 120 s, antes70 s |
| Llegada terminal antes de volver a observar | 12 mm /2°, conservada |
| Margen interior del gate X/Y | 20 mm, conservado |
| Mejora visual mínima si persiste incumplimiento | 2 mm, conservada |
| Vigilancia de falta de progreso durante una acción | 4 s, conservada |

No significa que se ejecuten siete ajustes siempre: la primera medida que
cumple el margen termina la fase. Salud, percepción, asociación, localización
y navegación conservan sus rechazos. Sólo la falta de progreso tipada admite
la recuperación única descrita a continuación; los demás fallos interrumpen.
El guard conserva30 s por acción, excursión80 mm y recorrido120 mm por acción,
además de velocidades, giro, frescura, frames, heartbeat, lease y cancelación
del UUID propio.100 mm solicitados acumulados no son una cota de recorrido real
ni de distancia de frenado. El ajuste de llegada al waypoint `get1` conserva
dos intentos y su presupuesto anterior; el contador de siete se comparte sólo
entre el planificador de caja y la validación del mensaje `box_pickup`.

El error mantiene `BOX_ALIGNMENT_LIMIT` e incorpora motivo `attempts` o
`distance`, contador/máximo, acumulado solicitado, siguiente paso y máximo
acumulado. También se registra un evento `box_alignment`, `phase=limit`, con
estos valores. Así se distingue falta de intentos de falta de distancia sin
inventar movimiento ni ocultar el cierre posterior.

**Fuentes y activación.** `scripts/box_handling/scenario1_box_alignment.py`
define el presupuesto; `scenario1_nav_correction.py` comparte el máximo de
`box_pickup` sin modificar el de `get1`; `scenario1_runtime.py` aplica los
límites y el diagnóstico. La presentación de consola/CLI usa la política vigente.
Se cargan en memoria por el mismo wrapper en la siguiente ejecución autorizada,
sin instalación o recarga de paquetes del robot. Se conservan los gates XYZ
nativos, SPS, tareas, perfiles de depósito y SDK originales. Esta intervención
es sólo local: sin SSH, comandos de movimiento, cambio de modo o reinicio.

Antes de otra ejecución, comprobar la situación física tras la interrupción y
recuperar HOME mediante la ruta apropiada, con abrazaderas vacías y trayectoria
libre. No reiniciar el ciclo automáticamente. Para la mesa69,5 cm sigue vigente
el ensayo acotado con `--stop-after deposit --deposit-trial`; este cambio no
declara cualificado el depósito ni autoriza HOME posterior sin caja liberada.

```bash
# Plan local; no conecta al robot:
./scripts/optimistic_scenario1.sh --table-height-cm 69.5 --plan
# Sólo con condiciones físicas actuales y HOME comprobados:
./scripts/optimistic_scenario1.sh --table-height-cm 69.5 \
  --run --stop-after deposit --deposit-trial
```

**Verificación y reversión.** PASS: 238 pruebas distintas,135 de componentes
de alineación/navegación y103 de integración runtime/políticas/consola/sesión/
mesa695. La ejecución de componentes consta como informe del agente revisor
en `verification.json`, sin inventar un log bruto; la integración conserva
`integration-tests-command.json` e `integration-tests.log`. Sintaxis y planes
locales45/69.5/90 pasan (`offline-validation.json`). Revisión del bootstrap real
de20 módulos, sin `main` ni clientes ROS: el guard embebido admite caja/intentos3
y7, rechaza8 y get1/intento3. Estas pruebas validan código, no movimiento real.
`changed-code-sha256.json` conserva los seis hashes finales de fuentes y tests,
incluido el planificador SHA256
`0fcbd6fdad16dfad532951c0f1f176b1cd8f60624c4c61b08089dcf3dd1091e7`.
Backup/evidencia: `../Humanoide-vla-evidence/20261022T053302Z_BOX_ALIGNMENT_RETRY_BUDGET/`,
`before/` conserva las fuentes y documentación previas con sus cambios locales.
Revertir sólo los fragmentos de este cambio desde la copia cotejada, con el
ejecutor detenido y preservando cambios del usuario y del perfil695. No hay
configuración remota persistente que restaurar. Ensayo físico PENDIENTE;
sin commit o push.

### Recuperación acotada antes del agarre — 22-10-2026

**BOX-01-VISUAL-ALIGN-RECOVERY-20261022. Implementado sólo en PC; prueba física
PENDIENTE.** Esta revisión permite una única recuperación de falta de progreso
dentro de una sesión nueva de alineación visual, antes del agarre nativo.
Sustituye exclusivamente el aborto definitivo por esa causa en la versión usada
por el intento117383, descrita a continuación. No reabre ni reanuda el checkpoint
ya abortado. No se ha conectado al robot ni solicitado movimiento en este cambio.

La recuperación exige todas estas condiciones, en este orden:

1. El guard de `box_pickup` identifica falta de progreso mediante excepción
   tipada. No basta con buscar un texto de error ni con recibir un código genérico.
   El supervisor debe haber optado expresamente por esta ruta; get1 y agarre
   nativo no la usan. Se conserva el watchdog de4 s.
2. Cancelación aceptada del único UUID propio y resultado terminal cancelado5,
   sin otra causa, identidad ambigua o evento de fallo. El contrato puro valida
   orden, tipo y pertenencia de la evidencia. Su retorno interno4 significa
   `recovery_required`, nunca navegación exitosa ni parada física verificada.
3. El worker antiguo queda vivo sólo para retirarse y rechaza nuevos goals.
   El supervisor exige salud actual, brazos/torso HOME y cabeza de observación,
   muestras de actuadores con sello posterior al terminal, dos muestras nuevas
   de reposo odométrico y dos poses nuevas de mapa posteriores a la cancelación.
   Contenedores, dependencias y hashes deben seguir siendo los mismos.
4. Sólo después se cierra el worker anterior y se exige salida0, EOF final y
   cola nativa sin salida opaca, errores o terminales tardíos. El worker hace un
   último spin/drain antes del EOF; el validador sólo admite status enteros
   1/2/3/5. No se borra el fallo ni se reutiliza su cliente ROSA cancelado. Un cliente nuevo confirma
   mapa `utars_nav_map`, estado `FSM_WAITNAVIGATE` y puntos originales.
5. Se adquieren dos detecciones nuevas con TF exacta, frescura/coherencia y
   asociación a la caja ancla original. Si ya cumplen el margen interior,
   termina la alineación y el agarre nativo conserva sus comprobaciones propias.
   Si siguen fuera, se exige mejora visual≥2 mm respecto a la observación previa
   y se calcula un nuevo objetivo de longitud vectorial mínima25 mm y máxima
   50 mm, escalando sólo los ejes afectados y manteniendo la proyección dentro
   del margen interior.
   No es una repetición del objetivo cancelado ni una nueva selección de caja.

Fallar cualquier comprobación termina el escenario. Una segunda falta de
progreso tampoco permite otra recuperación. Fallos de salud, percepción,
asociación, localización, cancelación desconocida u otras violaciones siguen
abortando; no se reintenta un agarre nativo fallido ni se envía HOME automático.
La cancelación sola nunca equivale a comprobar reposo: éste se mide de nuevo
después, sin convertir una observación de inmovilidad en certificación de frenado.

**Presupuestos y activación.** Cada solicitud reserva su longitud y consume un
intento **antes del envío**, aunque acabe cancelada. Se conservan siete objetivos,
100 mm solicitados acumulados y el plazo único120 s desde el inicio de la fase;
la recuperación no reinicia ninguno. Siguen50 mm por objetivo y los demás
límites de llegada, asociación, excursión, recorrido, velocidad y frescura.
El mínimo25 mm se aplica sólo a objetivos recalculados tras esta recuperación;
la alineación ordinaria conserva su mínimo anterior. El mismo comando de ensayo
695 ya documentado usa esta revisión en la próxima sesión nueva autorizada,
con HOME inicial y estado físico actual comprobados. No concede cualificación
física al depósito695 ni autoriza reanudar una caja de estado desconocido.

**Fuentes, verificación y reversión.** Helper puro nuevo
`scenario1_correction_recovery.py`, guard tipado, cliente/worker de acción,
sesión, supervisor, planificador y consola/CLI en `scripts/box_handling/`;
tests del contrato, cancelación y orquestación. Se transmiten en memoria, sin
instalación persistente, cambio de SDK o modificación de tareas del proveedor.
354 pruebas de11 módulos PASS en6,387 s: `final-tests-command.json` y
`final-tests.log`. AST, planes45/69.5/90 y bootstrap real autocontenido de21
módulos PASS en `offline-checks.json`, sin ejecutar main ni clientes ROS.
`changed-code-sha256.json`, `verification.json`, `intervention-only.patch` y
`after/` conservan hashes y fuentes reproducibles. Es comprobación de código,
no ensayo físico de recuperación.
Backup/evidencia `../Humanoide-vla-evidence/20261022T061103Z_BOX_ALIGNMENT_RECOVERY/`
con `before/` de15 archivos, fuentes, recibos y tests. Revertir selectivamente
esta revisión con ejecutor detenido, retirar sólo helper/tests nuevos si
procede y conservar presupuesto7/100/120 y cambios695 anteriores. Sin SSH,
movimiento, instalación, reinicio, commit o push en esta intervención.

### Diagnóstico de progreso del intento117383 — 22-10-2026

Nota histórica: describe la versión ejecutada antes de la recuperación acotada
anterior. El aborto del intento se conserva y no se transforma en éxito.

**BOX-01-VISUAL-ALIGN-NO-PROGRESS-DIAG-20261022. OBSERVADO offline; sin cambio
de código ni consulta al robot.** El usuario indica que no reintenta. Se revisa
`20261022T055833Z_OPTIMISTIC_SCENARIO1_117383` y se contrastan sus hashes:
alineación, navegación, runtime y CLI coincidían con los cuatro módulos vigentes
en ese corte, anterior a la recuperación acotada.
El presupuesto nuevo de7 ajustes,100 mm y120 s estaba cargado; no es una
ejecución de las fuentes antiguas ni un nuevo agotamiento de50 mm.

El primer objetivo solicita15,414475 mm. A7,728032 s del armado el guard
interrumpe `Correction made no significant progress`, tras4,008352 s sin otra
mejora aceptada. La odometría relativa al objetivo se acercó hasta0,832094 mm,
pero el residual final fue5,830833 mm tras volver a alejarse. En mapa, residual
final15,089369 mm y yaw1,367060°; distancia fuera de llegada12 mm, también
fuera de5 mm. No explicar el rechazo como diferencia entre esos dos umbrales.
Los recorridos registrados fueron43,941741 mm en mapa y67,054137 mm en odometría;
excursiones30,525577/35,795459 mm. Hubo variación de pose medida, pero no nueva
convergencia suficiente durante la ventana. Estos registros no permiten decidir
si el origen es movimiento físico, localización, control o una combinación.

Los7 ajustes permiten nuevos objetivos después de que el anterior termine bien
y se vuelva a observar la caja. No autorizan repetir una navegación fallida ni
eludir el guard de4 s. Cancelación ack0/status5 no demuestra parada física;
no se inicia el agarre nativo, retirada, put1, depósito o HOME. El perfil695
sigue sin cualificación física. Se conservan7/100 mm/120 s y todos los demás
límites; no ampliar watchdog ni ignorar localización para forzar otra pasada.

La continuación requiere revisar navegación y mediciones del intento y confirmar
la situación física actual antes de recuperar o repetir. No ejecutar otro ciclo
ni HOME automáticamente. Evidencia y copia documental previa:
`../Humanoide-vla-evidence/20261022T060229Z_BOX_ALIGNMENT_NO_PROGRESS_DIAG/`.
`diagnosis.json` conserva las métricas y los SHA256 del diario, checkpoint y
manifiesto de fuentes originales. No hay modificación de implementación o
configuración remota que revertir; reversión documental selectiva desde el
respaldo, preservando los cambios del presupuesto. Sin nuevos tests, por tratarse
de lectura y documentación; las238 pruebas anteriores validan el código local,
no este resultado físico. Sin SSH, comandos de movimiento, commit o push.

**07-10-2026 — BOX-MARGIN-CONSOLE-20261007. VERIFICADO offline; instaladoPC.**
Usuario pide cambiar20mm. Margen real actual editado porusuario inside_margin_m
0,002(2mm) se conserva; antes CLI/ready mostraban20mm fijo. CLI leePOLICY y
supervisor incorpora inside_margin_m enevento ready; consola muestra margen
real delevento, sininventar20mm enlogs antiguos (fallbackmargenconfigurado).
Cambios sólo presentacióneventos, sin alterar planificación/gates/valoresusuario.
Fuentes: scenario1_cli.py,scenario1_runtime.py,scenario1_console.py ytestconsola.
35testsconsola pasan y --plan localcorrecto; sin ejecución/consulta robot.
El runtime se transmite en próxima ejecución normal, carga/prueba remotaPENDIENTES.
Evidencia before/after, tests.log,plan.log,SHA256SUMS:
../Humanoide-vla-evidence/20261007_BOX_MARGIN_CONSOLE/. Reversión selectiva de
fuentes desdesu before/, conservando cambiosusuario posteriores. No commit/push.

**07-10-2026 — BOX-BASE-UNSTABLE-DIAG. OBSERVADO offline.**
Intento112123_977522 tras llegadaajuste8,1mm falla durantecapturavisual.
Historialmapa de request30 aúltima request39 cambia10,435197mm, giro0,052642°;
última pareja39 cambia≈10,439mm en~90,528ms. stable_base admite5mm/1°,
porloque rechazo esdesplazamiento aparente, no toleranciaarrival. No se distingue
movimientoreal desaltoSLAM; no debaja delcontrol de estabilidad oautorreintento.
Configuraciónactual observada editada poroperador: inside_margin_m0,002 y
max_arrival_distance_m0,018; nocambiada porelagente, pruebas físicas deestas
relajacionesno certificadas. Sólolectura diario/código ydocumentaciónPC.
Evidencia yrespaldo documental selectivo: ../Humanoide-vla-evidence/20261007_BOX_ALIGNMENT_BASE_UNSTABLE_DIAG/.
No ROS/movimiento/configuraciónremota. Estadofísicoactual pendiente.

**06-10-2026 — BOX-GET1-DISTANCE-DIAG. OBSERVADO offline.**
Diario134210_433140: llegada get1 reporta9,7mm/0,33°. Tras dos ajustes,
última pose archivada queda15,304mm del get1 de ESTA ejecución
(X−0,166060932/Y0,800009887/yaw−3,113288720); no son coordenadas de mapas
anteriores ni una lectura física actual. Caja X0,804998160→0,776323314→
0,779033661m base_link. Primer objetivo34,998mm mejora28,675mm; segundo
6,323mm (<ventana terminal12mm) termina con residual8,476mm y nueva caja
2,710mm más lejos. NO_IMPROVEMENT aborta antes del agarre: exteriorXYZ
admite últimaX, pero margen interior exigeX≤0,77m. Sin cambios de ejecutor,
órdenes o conexión al robot. Mejora de planificación de objetivos pequeños
sigue PENDIENTE; no se aplica el mínimo20mm propuesto anteriormente en el chat.
Evidencia/backups documentales selectivos:
../Humanoide-vla-evidence/20261006_BOX_GET1_DISTANCE_DIAG/.

**06-10-2026 — BOX-01-VISUAL-ALIGN-ENVELOPE-DIAG. OBSERVADO offline.**
Diario132500_391413: caja X0,837857869/Y0,086008026/Z0,926560129m base_link.
Preparación exige X≤0,77m: solicitud X+67,857869mm>50mm por objetivo;
aborta antes de navegación correctiva/agarre. Es límite de un objetivo,
distinto del presupuesto acumulado del intento131056. Llegada get1 válida
no demuestra alcance de caja. Sin órdenes/conexión ni modificación de límites;
estado físico actual PENDIENTE. Evidencia y respaldo documental selectivo:
../Humanoide-vla-evidence/20261006_BOX_ALIGNMENT_ENVELOPE_DIAG/.

**06-10-2026 — BOX-01-VISUAL-ALIGN-LIMIT-DIAG. OBSERVADO offline.**
Diario131056_357497: X inicial0,808542620m solicita+38,542620mm;
llegada residual10,197mm/0,438°. Nueva X0,783235489m cumple gate exterior,
pero queda13,235489mm fuera del margen interior (Xmáx0,77m). Segundo objetivo
llevaría el total solicitado a51,778109mm>50mm; aborta después de UN ajuste
por presupuesto acumulado, no por agotar dos intentos. Mejora visual25,307130mm.
No se alcanzó agarre. Lectura de diario local, sin conexión/comandos al robot;
postura/parada/caja actuales PENDIENTES. No se cambian límites ni planificador.
Evidencia/backups/hashes: ../Humanoide-vla-evidence/20261006_BOX_ALIGNMENT_LIMIT_DIAG/.
Reversión sólo documental selectiva desde before/, preservando cambios ajenos.

## BOX-01-VISUAL-ALIGN-INSIDE-MARGIN — 06-10-2026

**VERIFICADO offline; instalado PC; carga remota y ensayo físico PENDIENTES.**
Fecha Europe/Madrid. Petición: solucionar el rechazo de posición después de que
la preparación declarara la caja dentro del rango. El operador dice haber
llevado el robot a HOME antes de ejecutar; esto no demuestra HOME después del
nuevo fallo. No se consultó ni movió el robot en esta intervención.

Diario local20261006T090347Z_OPTIMISTIC_SCENARIO1_389599/events.jsonl:
preparación phase=ready, attempts=0, X0,7862544401792924m,
Y0,1085135373474658m, Z0,7235547702272845m. Sólo quedaban3,745560mm hasta
Xmáx0,79m. La detección posterior del agarre fue X0,7906630007712482m,
Y0,10856005879087316m, Z0,7229042095552463m: diferenciaX4,408561mm y
exceso0,663001mm. Variación de estimación/postura/objeto OBSERVADA; causa física
no identificada. El intento090212 también muestra aceptación0,787905m y
rechazo0,790360m; no se atribuye exclusivamente a ruido visual.

**Cambio:** `displacement()` ahora aplica el margen20mm también a valores
que aún cumplen el gate nativo. Preparación: X[0,43;0,77], Y[−0,37;0,37]m.
El caso real solicita X+0,0162544401792924m/Y0, con el mismo cálculo del objetivo
en mapa desde la pose fresca y yaw final conservado. `violation()` mide el
exceso sobre ese intervalo interior: el segundo ajuste exige mejora visual≥2mm
incluso si ambas medidas cumplen el gate exterior. Sin margen después de dos
ajustes, aborto antes de iniciar el agarre. Sin cambio de selector, referencia
original, XYZ SPS (X[0,41;0,79],Y[−0,39;0,39],Z[0,01;1,49]m), Z/elevador,
TF exacta, salud/HOME, percepción/coherencia, asociación, llegada, watchdog,
velocidad, trayectoria ni presupuestos2 objetivos/50mm/70s. Tolerancia aritmética
1e−12m sólo en el margen añadido, para sus límites representables; el gate nativo
no cambia. Tras navegación se vuelve a medir, y el agarre obtiene sus propias
capturas y validaciones. No se reintenta ni se navega después de un fallo nativo.
Los20mm reducen sensibilidad al borde; no garantizan precisión física ni éxito.

Consola informa el margen interior y muestra `ajustes visuales: 0`; antes
`clean(value or '')` convertía ese0 a texto vacío. Sólo se cambia la presentación
del contador de esta fase; diario original y decisiones independientes.

**Destino/fuentes reproducibles:** PC, archivos relativos al repositorio:
[planificador](../../scripts/box_handling/scenario1_box_alignment.py),
[CLI](../../scripts/box_handling/scenario1_cli.py),
[consola](../../scripts/box_handling/scenario1_console.py),
[tests de ajuste](../../scripts/box_handling/test_scenario1_box_alignment.py),
[tests de consola](../../scripts/box_handling/test_scenario1_console.py),
[fixture histórica](../../scripts/box_handling/fixtures/box_alignment_inside_margin_20261006.json).
La fixture conserva valores originales y SHA256 del diario; no es pose actual
ni se importa por un ejecutor físico. Misma dependencia del worker SPS/modelo/
tareas y pines existentes. El wrapper transmite estas fuentes en memoria al
supervisor transitorio de Motion en la próxima ejecución; no requiere instalar
ni reiniciar paquetes remotos. No se ha activado allí esta revisión.

**Verificación:** 725 pruebas pasan; módulos/argumentos exactos en
test_command.json y salida tests.log. Exclusión legacy
`test_scenario1_deposit_install`, con errores preexistentes ya documentados.
Regresiones: caso exacto aceptado→rechazado sin alterar poses, límites interiores,
ambos signos/ejes, una corrección antes del único agarre, necesidad de segundo
ajuste aunque la primera medida esté dentro del gate exterior, falta de progreso,
agotamiento de dos ajustes, abortos previos y contador0. La aritmética de replay
llevaría la segunda X a0,774409m, dentro del gate exterior; no se simula como una
nueva observación real. Sintaxis Python/shell, plan local y git diff --check
correctos. No pruebas físicas, consultas remotas, instalaciones o reinicios.

**Activación y continuación:** tras recuperación presencial específica y
HOME fresco, abrazaderas vacías y condiciones físicas actuales comprobadas,
usar el mismo entrypoint. `--check` sólo valida dependencias/estado, no prueba
la trayectoria ni la incertidumbre visual:

```bash
./scripts/optimistic_scenario1.sh --check
./scripts/optimistic_scenario1.sh --run --stop-after grasp
```

No ejecutar automáticamente esos comandos tras el rechazo: la tarea nativa
prepara brazos antes de consultar SPS. Este fallo no demuestra que sigan en
HOME; verificar caja sujeta/apoyada/retirada y trayectoria antes de recuperarlos.
Sigue vigente el requisito de persona junto al paro y control exclusivo.

**Respaldo/evidencia/reversión:**
../Humanoide-vla-evidence/20261006_BOX_ALIGNMENT_INSIDE_MARGIN/ contiene before/
con todos los cambios locales previos conservados, baseline.json (HEAD+hashes),
incident.json, test_command.json/tests.log, plan.log/static_checks.json,
after/ y SHA256SUMS. Reversión selectiva de los archivos de esta intervención
desde before/, conservando cualquier cambio posterior ajeno; retirar la fixture
nueva si se revierte. No restaurar todo el checkout ni coordenadas antiguas.
Sin configuración persistente remota modificada. El historial anterior queda
conservado; este criterio sustituye continuar inmediatamente por cumplir sólo
el gate exterior.

**02-10-2026 — revisión BOX-01-VISUAL-ALIGN-ASSOCIATION.** Asociación entre
posturas mediante media de cada pareja coherente en odometría local; mantiene
20mm/3° y última pose original para SPS. Sustituye asociación de últimas
capturas en mapa citada en revisiones históricas. Replay real19,290mm/2,120°;
715 pruebas pertinentes pasan. Instalado PC; nueva carga/ensayo PENDIENTES.

**02-10-2026 — revisión BOX-01-VISUAL-ALIGN-ARRIVAL.** Llegada terminal12mm/2°
para volver a observar la caja tras éxito/reposo nativo; sustituye el criterio
PC de5mm citado en revisiones históricas. Ventana5mm del guard para giro rápido
intacta. Sólo nueva visión/gateXYZ permite recoger o usar el segundo ajuste
presupuestado. 708 pruebas pertinentes pasan; nueva carga/ensayo PENDIENTES.

**02-10-2026 — revisión BOX-01-VISUAL-ALIGN-FRESH.** Reposo visual desde el
worker persistente, con el mismo validador y dos muestras nuevas de odometría.
Evita caducar la imagen durante arranque/cierre ROSA de otro proceso. Edad
máxima2s conservada, diagnóstico de edad antes de decidir. 700 pruebas offline
pertinentes pasan; revisión instalada PC, carga/ensayo PENDIENTES. Detalle al final.

**02-10-2026 — revisión BOX-01-VISUAL-ALIGN-PROGRESS.** El intento084706
confirma emparejamiento temporal y envía ajusteX+22,774mm, cancelado a4,009s.
Se reconoce una única recuperación inicial medible antes de mejorar la distancia
de entrada; el watchdog sigue siendo4s y no se renueva con oscilaciones repetidas.
VERIFICADO offline; nuevo ensayo PENDIENTE. Detalle al final.

**02-10-2026 — revisión BOX-01-VISUAL-ALIGN-TIME.** Corregido el rechazo
`BOX_ALIGNMENT_POSE_TIME_MISMATCH` del intento083606: las poses se adquieren
durante la detección y se emparejan con la imagen, en vez de exigir proximidad
con una consulta posterior al procesamiento. Se conserva el límite0,5s y se
comprueba estabilidad de todas las muestras intermedias. La detección y sus
parejas quedan registradas antes de decidir continuar. VERIFICADO offline;
carga/ensayo de esta revisión PENDIENTES. Detalle y reversión al final.

**02-10-2026, Europe/Madrid — BOX-01-VISUAL-ALIGN. IMPLEMENTADO en PC;
VERIFICADO offline; carga remota y ensayo físico PENDIENTES.**

La entrada `scripts/optimistic_scenario1.sh --run` incorpora esta comprobación
dentro de `grasp`, antes de iniciar `local_front_box/separate_right_cruzr`.
Se activa automáticamente en `optimistic_v1`; las entradas standard conservan
su flujo. No añade preguntas ni etapas nuevas al checkpoint.

## Motivo y evidencia

El intento `20261002T081640Z_OPTIMISTIC_SCENARIO1_102007` llegó a get1 con
3,970 mm / 0,426°, dentro de 20 mm / 2°. La percepción posterior rechazó
X=0,7909284808515973 m, Y=0,09943778448581805 m, Z=0,31117874288896163 m:
X excedía 0,79 m por 0,928 mm. Llegar al waypoint del mapa no demuestra que
la caja esté dentro del intervalo visual de recogida. Los errores de lease
posteriores son del cierre tras el fallo, no el motivo original del rechazo.

Estos datos son históricos; no describen la postura actual. El XML nativo
prepara ambos brazos antes de consultar SPS, de modo que aquel rechazo no
demuestra HOME ni permite reiniciar automáticamente desde esa postura.

El replay numérico solicita X=+20,928 mm, Y=0 en base_link, para situar la
caja a X=0,77 m según esa medición. La componente positiva X corresponde a
acercarse a una caja demasiado distante; negativa, a alejarse de una demasiado
cercana. El objetivo se transforma al mapa con el yaw fresco del chasis.
La [fixture saneada](../../scripts/box_handling/fixtures/box_alignment_20261002.json)
incluye el SHA256 del diario original y el objetivo histórico, sólo para tests.
Nunca se usa esa pose archivada como objetivo físico.

## Secuencia y límites

1. Comprobar salud completa, reposo, consignas y brazos/torso medidos en HOME.
   El estado de entrada debe declarar abrazaderas vacías. El script no mide
   directamente presencia de caja en ellas; persiste la preparación presencial.
2. Verificar el hash de `cruzr/move_head_lower` y ejecutar esa tarea existente.
   Objetivo de cabeza 0/−0,43 rad; nueva salud exige esa postura, manteniendo
   brazos/torso en HOME. No se prepara todavía el agarre nativo.
3. Comprobar contenedores, dependencias, acción libre, mapa utars listo,
   puntos sin cambios, dos lecturas odométricas nuevas en reposo y pose estable.
4. Solicitar dos detecciones nuevas al socket del worker SPS instalado, usando
   cabeza/grasp/workbin y TF del instante exacto. Se usa el mismo selector frontal
   del paquete, con coherencia ≤20 mm / 3° y sellos crecientes. La observación
   puede estar fuera del intervalo; nunca se entrega a Motion como éxito SPS.
   Durante cada captura se solicitan pares de poses nuevas al lector existente,
   mientras otro hilo espera al worker perceptivo independiente. Sólo el hilo
   principal usa el protocolo secuencial de salud. Para cada imagen se eligen
   las dos poses de sello más cercano, ambas a ≤0,5 s; no se exige que una
   consulta posterior al procesamiento sea contemporánea de la exposición.
   Toda la serie, incluidos extremos e intermedios, debe mantenerse dentro de
   5 mm / 1° respecto de la entrada. La referencia final del objetivo se obtiene
   de una consulta nueva y el guard vuelve a comprobar su correspondencia con
   poses frescas antes de mover. No se transforma una pose histórica en permiso
   de llegada. Cada captura tiene límite12s y la serie ≤256 muestras; después
   del reposo final se exige edad de la segunda detección ≤2s. Los límites de
   frescura del lector ordinario, percepción/SPS y guard permanecen vigentes.
5. Si X/Y cumplen el margen interior de 20 mm, continuar sin mover el chasis.
   En caso contrario, corregir únicamente los ejes que incumplen ese margen:
   X en [.43,.77] / Y en [−.37,.37] m. El gate nativo de recogida conserva
   X[.41,.79] / Y[−.39,.39] m. Z fuera de [.01,1.49] m aborta;
   no hay ajuste de elevador para compensarlo. Z en base_link no es altura al suelo.
6. Enviar `navigation_start/free_nav` al objetivo medido, conservar yaw final
   y vigilar con el guard existente mapa/odom, velocidad, recorrido, progreso,
   frescura, frames, salud, heartbeat, lease y cancelación por UUID propio.
   Solicitud de velocidad 0,05/0,01 m/s y 0,15 rad/s, sin asumir que el controlador
   las respete. Monitor ≤0,10 m/s, giro ≤0,60 rad/s al aproximar y ≤1,20 rad/s
   únicamente dentro de **5 mm** del objetivo, con traslación ≤0,02 m/s.
   get1 conserva su umbral anterior de 20 mm. La trayectoria nativa puede
   describir un arco; los ejes se refieren al desplazamiento del objetivo final.
7. Exigir resultado exitoso, dos muestras nuevas de reposo y llegada terminal
   ≤12 mm / 2° en dos poses nuevas estables; después repetir toda la medición visual.
   Este criterio de precisión del mapa no autoriza el agarre. Comparar la media
   geométrica de cada pareja coherente usando odometría local con la referencia
   inicial, ≤20 mm / 3°, para impedir que el
   cambio de chasis se confunda con cambio de caja. Es asociación geométrica,
   no prueba de identidad física si otra caja ocupa una pose indistinguible.
8. Permitir como máximo dos correcciones, con mejora del exceso respecto del
   margen interior ≥2 mm cuando siga incumpliéndolo, ≤50 mm por objetivo y **≤50 mm de desplazamiento
   solicitado acumulado**. Presupuesto global 70 s y por navegación ≤30 s.
   El guard conserva además excursión ≤80 mm y recorrido ≤120 mm **por acción**;
   50 mm solicitados no son una cota de recorrido real ni distancia de frenado.
9. Cuando una nueva medida cumpla el margen interior, guardar una referencia de comparación
   y ejecutar el agarre nativo una vez. Su adaptador conserva las dos capturas,
   el gate XYZ original y comparación con esa referencia antes de entregar la
   selección. Una nueva desviación o cualquier fallo nativo detiene el ciclo.

No se reintenta un agarre fallido, navegación rechazada, pérdida de salud/datos,
ambigüedad, cambio de mapa/geometría de caja ni violación de vigilancia. No se amplían
los límites XYZ/de movimiento, recortan coordenadas, cambia de caja para pasar el gate, relocaliza
durante el ajuste ni envía HOME automáticamente al fallar.

## Fuentes y activación

Fuentes PC: [planificador](../../scripts/box_handling/scenario1_box_alignment.py),
[supervisor](../../scripts/box_handling/scenario1_runtime.py),
[guard de navegación](../../scripts/box_handling/scenario1_nav_correction.py),
[CLI](../../scripts/box_handling/scenario1_cli.py),
[consola](../../scripts/box_handling/scenario1_console.py) y
[entrada](../../scripts/optimistic_scenario1.sh). Se transmiten en memoria en
la siguiente sesión, al host Motion y cliente nativo del contenedor redescubierto.
El socket de percepción conserva 0600/root: el supervisor lo consulta desde
su contenedor, sin cambiar permisos. Biblioteca vendor, SDK, XML/YAML y seis
fuentes del paquete SPS permanecen intactos; ID **bf145fa17e1116fc** verificado
localmente. No necesita instalación SPS, recarga ni reinicio.

Nueva dependencia de cabeza, leída en `--check` cuando hay agarre pendiente y
de nuevo inmediatamente antes de usarla:
`/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/cruzr/move_head_lower.xml`,
SHA256 `f3a73626f97b471d4a0a03c98c24de32243651116c497328e69b5ddc57ea46c1`.
La lectura histórica `held-check` del 01-10 confirma el signo de posición
del actuador1002 (−0,431336 rad) usado en este gate; no es estado físico actual.
Evidencia saneada: `head-actuator-contract-readonly.json`.
No se agrega a la identidad persistida de dependencias: las reanudaciones de
cajas ya sujetas/liberadas conservan sus contextos anteriores y no usan esta
preparación. Se mantienen todas las comprobaciones de contexto originales.

Evidencia de sesión: `box_alignment` en `events.jsonl`, estado de intención
`box-alignment.json` antes de mover y resultado medido después, referencia
`box-alignment-reference.json`, además del checkpoint original `grasp` en curso.
Los archivos viven en la carpeta temporal privada de la sesión Motion; las
observaciones y objetivos también quedan en el diario PC. No representan una
autorización reutilizable ni éxito de recogida.

Uso reproducible:

```bash
# Sólo plan local:
./scripts/optimistic_scenario1.sh --plan
# Lectura técnica actual, sin adaptadores, detección ni movimiento:
./scripts/optimistic_scenario1.sh --check
# Nueva ejecución, sólo con entrada física preparada y comprobada:
./scripts/optimistic_scenario1.sh --run --stop-after grasp
```

Para un fallo anterior, conservar el checkpoint y revisar la recuperación
específica: la postura preparatoria de brazos no pasa este nuevo requisito de
HOME. No usar un ciclo desde cero para recuperarla. La guía de
[reanudación por etapa](FORCE_IMPROVED_SCENARIO1.md#reanudación-por-etapa--28-09-2026)
continúa vigente; una entrada `grasp` explícita exige brazos/torso HOME medidos.

## Verificación, respaldo y reversión

Pruebas reproducibles, sin robot:

```bash
python3 -B -m unittest scripts.box_handling.test_scenario1_box_alignment \
  scripts.box_handling.test_scenario1_navigation_correction \
  scripts.box_handling.test_scenario1_perception \
  scripts.box_handling.test_scenario1_optimistic
bash -n scripts/optimistic_scenario1.sh
git diff --check
```

La suite de `scripts/box_handling/test_*.py` excluye sólo
`test_scenario1_deposit_install`, con fallos legacy documentados previamente.
**675 pruebas correctas, cero fallos/errores**, incluidas 27 específicas del
ajuste. Sintaxis Python/shell, planes y diff-check correctos. Resultado y módulos exactos: `tests.json` / `tests.log` en la evidencia
externa `../Humanoide-vla-evidence/20261002_BOX_AXIS_REPOSITION/`.
`replay.json` verifica el caso original exacto; `before-manifest.json`,
`before/`, `after-manifest.json` y `after/` conservan fuentes/hashes de esta
intervención, incluidos archivos locales nuevos sin commit.

Cambios persistentes: sólo fuentes/pruebas/documentación PC. Instalado en PC:
sí; cargado en Motion/cliente nativo: **PENDIENTE**; probado físicamente:
**PENDIENTE**. Esta intervención no conectó al robot, envió detecciones,
movimientos, HOME, reinicios ni cambios de mapa. La prueba de depósito90 del
01-10 no cualifica esta nueva maniobra visual. Falta ensayar dirección, giro,
seguimiento, parada y retorno de percepción con zona y persona junto al paro.

Rollback de software sin sesiones consumidoras: restaurar selectivamente los
archivos modificados desde `before/`, retirar el planificador/test/fixture nuevos
y revertir estas notas, preservando cambios posteriores. No restaurar contexto,
checkpoints, cachés o archivos remotos. Vuelve el rechazo sin ajuste automático;
el gate SPS instalado sigue vigente. Sin commit/push.

## Revisión temporal del intento083606

**OBSERVADO en evidencia histórica**, no estado actual: llegada get1
2,071mm/0,365°; preparación `cruzr/move_head_lower` SUCCEED. Última salud previa
al fallo: cabeza1002 −0,430665rad; brazos máximo0,000959rad y velocidad0.
El diario no envió agarre nativo ni ajuste de chasis después de preparar cabeza.
Las consultas de pose antes/después de las capturas difieren3,140683s, con deriva
entre extremos0,003904mm / 0,009393°. Esto no prueba inmovilidad durante todo el
intervalo; por eso la revisión vigila también las posiciones intermedias.

**VERIFICADO en código:** la versión anterior comparaba el sello de la segunda
imagen con el último sello de la consulta posterior. El procesamiento de visión
puede romper esa coincidencia aunque los datos sean válidos. El sello exacto
de imagen no se archivó antes de ese fallo: delta real y desglose de la latencia
PENDIENTES; no se atribuye el fallo a congelación de pose o reloj del robot.

Fuentes de esta revisión: supervisor, planificador temporal y su suite de tests,
todos enlazados arriba. No cambia worker SPS/health, contenedores, parámetros,
límites de movimiento ni el protocolo de reanudación. Los eventos
`box_alignment_capture` archivan cada observación recibida antes de la
comparación; `box_alignment_time_pair` conserva sellos, delta y poses elegidas,
además de la referencia actual. Los fallos de emparejamiento incluyen imagen,
delta al sello más cercano y número de muestras.

Respaldo exacto del árbol local anterior, incluidos cambios sin commit de la
primera intervención: `../Humanoide-vla-evidence/20261002_BOX_ALIGNMENT_TIME_PAIR/`.
`incident-summary.json` conserva el diagnóstico saneado y hash del diario;
`before/`, `after/` y manifiestosSHA256 reproducen esta revisión. Pruebas/resultados
en `tests.json`/`tests.log`: **680 pruebas correctas**, incluidas32 específicas
del ajuste; misma exclusión legacy de la primera intervención. Sintaxis, plan
local y diff-check correctos; misma receta offline anterior. Reversión únicamente
de esta revisión: restaurar selectivamente supervisor, planificador y test desde
ese `before/`, y sus notas documentales, preservando cambios posteriores. Mantiene
el ajuste visual anterior con su defecto de adquisición; no restaura estados
remotos ni permite reiniciar un ciclo interrumpido. Sin conexiones ni movimientos
del agente; el ensayo con detección real y posterior ajuste sigue PENDIENTE.

## Revisión de progreso del intento084706

**02-10-2026, Europe/Madrid — OBSERVADO histórico:**
`20261002T084706Z_OPTIMISTIC_SCENARIO1_181758` pasa get1, visión y cabeza.
La revisión temporal anterior queda cargada y observada:38 poses; parejas de
imágenes con delta máximo62.036.696/62.324.032ns, dentro de0,5s.
Solicita X+22,774352mm, sin Y, y el navegador acepta el objetivo.
El error de distancia en mapa parte de22,774352mm, alcanza29,500645mm a1,632s
y vuelve a26,466501mm a2,900s. Cancela a4,009s con22,301181mm restantes:
mejora neta0,473171mm, menor que2mm, y fuera de llegada5mm.
La vigilancia anterior comparaba sólo con su referencia de mejor progreso,
por lo que esa recuperación del alejamiento permitido no renovaba el contador.

Odómetro: recorrido acumulado43,448mm, excursión máxima25,600mm; mapa:
recorrido14,368mm, excursión6,730mm. Son métricas en frames separados, no
posiciones restables ni confirmación de llegada. Velocidades máximas0,028452m/s
y0,018908rad/s; avisos LOCATION_LOST recibidos. **INFERENCIA:** maniobra inicial
nativa y/o estimación de localización pueden explicar el alejamiento/retorno;
causa y discrepancia mapa/odom **PENDIENTES**, porque el guard anterior no
archivaba poses individuales. La revisión las añade sin autorizar llegada por
odometría ni restaurar localización durante movimiento.

Cancelación del UUID propio aceptada con return_code0, resultado terminal5 y
`FSM_Navigating onCancel and stop`. Esto no verifica parada física. No se
envió agarre nativo, reintento ni HOME después. Los errores de lease son
posteriores al fallo primario. El checkpoint conserva box_state=unknown y
grasp fallido; no autoriza reiniciar el ciclo desde un estado físico inferido.

**Cambio local:** el guard reconoce una única recuperación inicial en
`box_pickup`, si el pico se alejó≥2mm de la entrada y después la distancia
disminuye≥2mm desde ese pico. Sólo antes de progreso neto y de fase final.
Esta recuperación renueva una vez el mismo contador de4s; no eleva umbrales
de tiempo/velocidad/distancia ni añade reintentos. Un chasis inmóvil o que sólo
se aleja sigue abortando a4s; retrocesos y retornos posteriores no renuevan
esa recuperación. Mejoras netas posteriores de2mm conservan la regla existente.
get1 conserva su comportamiento. Se mantienen presupuesto30s/70s, empeoramiento
máximo15mm respecto al mejor error, excursión80mm, recorrido120mm, frescura,
salud, velocidades, llegada5mm/2°, reposo, nueva visión y gate XYZ original.

Fuentes exactas: [guard](../../scripts/box_handling/scenario1_nav_correction.py),
[consola](../../scripts/box_handling/scenario1_console.py),
[tests de vigilancia](../../scripts/box_handling/test_scenario1_nav_correction.py),
[tests de consola](../../scripts/box_handling/test_scenario1_console.py) y
[fixture saneada](../../scripts/box_handling/fixtures/box_alignment_progress_20261002.json).
La fixture conserva tiempos/distancias del diario y su SHA256. Los tests
proyectan esas distancias en un eje sintético, con yaw/odom sintéticos: no son
replay de poses originales ni demuestran que el navegador termine la maniobra.
La regresión comprueba que desaparece este aborto prematuro, y que un bloqueo
posterior, oscilación, exceso físico o datos obsoletos todavía abortan.
Resumen nuevo: last_pose por frame, progress_ns/progress_distance_m y
pickup_recovery con distancia inicial/pico/sello del único uso. La consola
muestra «código0» sin convertirlo en confirmación de parada física.

Verificación reproducible sin robot:

```bash
python3 -B -m unittest scripts.box_handling.test_scenario1_nav_correction \
  scripts.box_handling.test_scenario1_console \
  scripts.box_handling.test_scenario1_correction_transport
./scripts/optimistic_scenario1.sh --plan
bash -n scripts/optimistic_scenario1.sh
git diff --check
```

**690 pruebas correctas**, misma suite/exclusión legacy ya documentada,
incluidas9 nuevas de vigilancia y1 de consola; sintaxis/plan/diff-check correctos.
`tests.json` registra módulos y resultados exactos. Backup del árbol local
previo sin perder cambios sin commit, manifiestos SHA256 antes/después,
diagnóstico con hash del diario y checks:
`../Humanoide-vla-evidence/20261002_BOX_ALIGNMENT_PROGRESS/`.
Destinos: sólo fuentes PC, transmitidas en memoria al cliente nativo Motion
en la próxima sesión autorizada. Dependencias/SDK/paquete SPS intactos; no
requiere instalación/reinicio. Instalado en PC: sí; cargado en robot/probado
físicamente **de esta revisión: PENDIENTES**. El ensayo anterior sólo demuestra
activación hasta el objetivo correctivo, no éxito de corrección/agarre.

Reversión selectiva: restaurar guard/consola y sus tests desde `before/`, retirar
fixture nueva y restaurar notas correspondientes; preservar cambios posteriores
y no restaurar checkpoints ni estados remotos. Devuelve el cálculo anterior
de progreso, manteniendo la revisión temporal. Reanudación: conservar evidencia
y aplicar recuperación específica con postura/caja/parada comprobadas; no
reintentar automáticamente la acción cancelada. Sin conexiones, movimientos,
cambios remotos, commit ni push por el agente.

## Revisión de frescura del intento085958

**02-10-2026, Europe/Madrid — OBSERVADO histórico:**
`20261002T085958Z_OPTIMISTIC_SCENARIO1_215101` pasa get1 (5mm/0,43°), visión
y cabeza. Capturas coherentes, emparejadas con poses a67,320/52,869ms. La segunda
imagen tiene sello1790931604911903000ns; pose seleccionada base_link:
X0,787601691/Y0,114263272/Z0,311893826m, dentro del gate original en ese instante.
No se llegó a enviar ajuste de chasis ni agarre nativo. La prueba de recuperación
de progreso anterior no se ejercitó en este intento.

Edad de imagen al registrar recepción:1,135722s; tras adquirir las poses
posteriores:1,315706s. Consulta final de reposo:0,903138s desde ese registro
hasta su devolución, desglosados0,772748s hasta comenzar adquisición de odometría,
0,051459s para dos muestras y0,078930s hasta devolver/registrar el resultado.
Imagen≥2,218844s tras reposo y2,223167s al registrar el error. El guard anterior
no guardaba su instante exacto de comprobación; esos extremos demuestran que
el límite2s ya se había superado. Salud/lease fallan después durante cierre;
no son la causa primaria de `BOX_ALIGNMENT_DETECTION_STALE_BEFORE_DISPATCH`.

**VERIFICADO en código:** el gate ejecutaba un proceso nuevo con ROSA para
cada lectura de reposo. El coste de lanzamiento/retorno posterior a las capturas
agotaba su frescura. Se sustituye el transporte de esa lectura por una petición
`base` al worker de salud ya abierto. La primera petición crea una suscripción
read-only /mc/odom, nav_msgs/msg/Odometry, QoS SensorData/bestEffort/volatile/
keepLast5; las siguientes reutilizan el lector, sin reutilizar sus muestras.

Cada petición crea la misma `scenario1_resume_worker.Acquisition` original,
importada en memoria sin iniciar ROSA. Conserva dos sellos/recepciones posteriores
a la petición, avance temporal, tratamiento de duplicados, frames, cuaternión,
edad máxima0,5s, único publicador, velocidades≤0,003m/s/0,01rad/s y estabilidad
≤5mm/1°. Plazo máximo5s. Datos viejos, movimiento, leases, falta/ambigüedad de
publicadores y errores siguen bloqueando. Odómetro no entra en la caché live
de salud; se conserva el único hilo de peticiones de telemetría durante capturas.
Los flujos health/pose y el worker standalone de reanudación no cambian.
La imagen sigue limitada a2s: un procesado lento todavía aborta. El nuevo evento
`box_alignment_freshness` registra sello/edad/límite antes de comprobarlo;
el error incluye age_ns. No se reintenta una captura o acción fallida.

Fuentes PC: [runtime](../../scripts/box_handling/scenario1_runtime.py),
[worker persistente](../../scripts/box_handling/scenario1_health_worker.py),
[payload](../../scripts/box_handling/scenario1_cli.py),
[tests de integración visual](../../scripts/box_handling/test_scenario1_box_alignment.py) y
[tests de telemetría](../../scripts/box_handling/test_scenario1_health_worker.py).
Dependencia adicional embebida: [validador original sin cambios](../../scripts/box_handling/scenario1_resume_worker.py).
SDK, tareas/XML/YAML, SPSbf145fa17e1116fc y parámetros nativos intactos.
Destinos: estas fuentes PC; próxima sesión transmite health worker al cliente
Motion/contenedor redescubierto. Lector se activa al primer gate base; --check
no lo crea. No requiere instalar archivos persistentes ni reiniciar contenedores.

Verificación reproducible sin robot:

```bash
python3 -B -m unittest scripts.box_handling.test_scenario1_health_worker \
  scripts.box_handling.test_scenario1_box_alignment \
  scripts.box_handling.test_scenario1_optimistic
./scripts/optimistic_scenario1.sh --plan
bash -n scripts/optimistic_scenario1.sh
git diff --check
```

**700 pruebas pertinentes correctas**, cero fallos/errores, con la misma
exclusión legacy test_scenario1_deposit_install documentada anteriormente.
Diez nuevas comprueban transporte persistente, dos muestras nuevas por petición,
datos previos/duplicados/movimiento/frescura/publicadores/lease, creación única
del lector, caché live intacta y payload importable sin ROSA. La prueba de latencia
simula imagen1,14s + poses0,18s: reposo0,05s permite continuar; reposo0,91s
todavía aborta sin movimiento. Es regresión sintética, no medición de latencia
de esta revisión instalada en robot. Sintaxis/plan/diff-check correctos.

Respaldo íntegro anterior/final de fuentes modificadas y notas, SHA256, estado
Git, tests.json/tests.log, plan.json y incident-summary.json con hash del diario:
`../Humanoide-vla-evidence/20261002_BOX_ALIGNMENT_FRESH_DISPATCH/`.
Instalado PC: sí; cargado en Motion y probado físicamente **de esta revisión:
PENDIENTES**. Esta intervención no conecta al robot, cambia configuración remota
ni envía detecciones, comandos físicos o HOME. El ensayo histórico demuestra
adquisición temporal, no éxito de ajuste/agarre ni estado físico actual.

Rollback selectivo desde before/ de runtime/health worker/CLI, sus tests y estas
notas, preservando cambios posteriores. Vuelve la consulta standalone de reposo;
mantiene correcciones temporal/de progreso anteriores. No restaura checkpoints,
sesiones, permisos ni estados remotos. Reanudar sólo tras verificar físicamente
parada/postura/caja según el modo de recuperación correspondiente. Sin commit/push.

## Revisión de llegada del intento091156

**02-10-2026, Europe/Madrid — OBSERVADO histórico:**
`20261002T091156Z_OPTIMISTIC_SCENARIO1_244792` llega get1 a10,7mm/0,41°,
prepara cabeza y mide cajaX0,792649615m. Edad de segunda imagen0,993809s:
la revisión de frescura anterior está cargada y se observa en este intento.
Solicitud de correcciónX+22,649615mm en base_link, Y0. Objetivo mapa:
X1,674653343/Y0,290748126m, yaw1,606405957rad. Navegación status4/SUCCEEDED.
La recuperación inicial de progreso se usa una vez; distancia máxima inicial
30,759mm y distancia al resultado2,039mm. Reposo confirmado por el guard, dos
muestras posteriores al terminal; después del asentamiento la distancia de
mapa es9,630466mm. Las dos poses solicitadas por el supervisor confirman
9,629522/9,629890mm y0,451711/0,452175°. Ese error explica el rechazo5mm PC.

Odómetro: recorrido87,220mm y excursión máxima68,271mm, dentro de120/80mm.
En asentamiento la pose de mapa cambia mientras odometría queda en reposo;
no atribuir esa diferencia sólo a frenado/desplazamiento real. **INFERENCIA:**
precisión del controlador y/o actualización de localización explican el error
residual; el diario por sí solo no separa sus causas. El análisis histórico
[ArcPrecise](ARC_PRECISE_ARRANQUE_20260922.md) documenta tolerancia0,012m e
histéresis0,005m. No se consultó hoy la configuración remota ni se modificó.
No se capturó la caja después del ajuste; su posición final/gate son **PENDIENTES**.
No se envió agarre nativo, segunda corrección ni HOME.

**Cambio local:** criterio terminal de precisión5→12mm, yaw2° conservado,
dos poses nuevas y estabilidad5mm/1°; sólo después de acción exitosa y reposo
medido por el guard. Un resultado fuera de12mm/2° sigue abortando antes de
capturar/recoger. Este cambio no se aplica a `distance_tolerance` del guard:
la ventana que permite giro final rápido conserva5mm; vigilancia física,
frescura, empeoramiento15mm, excursión80mm, recorrido120mm, velocidades,
watchdogs, paros y cancelación permanecen intactos. get1 tampoco cambia.

Pasar ese criterio terminal sólo habilita nueva doble detección con salud,
postura, reposo, asociación geométrica de caja en mapa≤20mm/3°, TF exacta y
frescura originales. Si caja cumple XYZ, prepara referencia comparativa y el
agarre nativo vuelve a detectar/validar sin recibir una pose archivada como
autorización. Si sigue fuera, exige mejora≥2mm y permite únicamente el segundo
objetivo ya previsto, con límite50mm solicitado acumulado/70s. Fallos nativos,
de salud, identidad, datos, presupuesto o mejora siguen deteniendo el ciclo.
La consola muestra distancia/yaw terminales y «Se vuelve a medir la caja».

Fuentes modificadas: [planificador/gate terminal](../../scripts/box_handling/scenario1_box_alignment.py),
[runtime](../../scripts/box_handling/scenario1_runtime.py),
[consola](../../scripts/box_handling/scenario1_console.py),
[tests](../../scripts/box_handling/test_scenario1_box_alignment.py) y
[fixture histórica](../../scripts/box_handling/fixtures/box_alignment_arrival_20261002.json).
Policy congelada explicita max_arrival_distance_m0,012 y max_arrival_yaw_deg2.
Plan local expone esos valores; caller no puede inyectar una policy más amplia.
Fixture conserva objetivo/poses reales, métricas y SHA256 del diario, saneados.
Las posiciones de caja posteriores en tests son sintéticas, no resultados
físicos del ensayo. Nueva revisión instalada en PC; carga Motion/cliente nativo
y validación física **PENDIENTES**. Revisiones anteriores sí observadas hasta
navegación/reposo; éxito de ajuste visual completo/agarre no demostrado.

Receta offline:

```bash
python3 -B -m unittest scripts.box_handling.test_scenario1_box_alignment \
  scripts.box_handling.test_scenario1_nav_correction \
  scripts.box_handling.test_scenario1_optimistic
./scripts/optimistic_scenario1.sh --plan
bash -n scripts/optimistic_scenario1.sh
git diff --check
```

**708 pruebas pertinentes pasan**, cero errores/fallos; misma suite/exclusión
legacy test_scenario1_deposit_install. Ocho nuevas cubren replay exacto de
poses9,63mm, límites inclusivos12mm/2°, no finitos/cantidad/estabilidad/yaw,
ventana de giro5mm intacta, nueva visión antes de agarre, segundo ajuste visual
(47,2mm solicitados totales), fallos de identidad/yaw/mejora y residual visible.
Sintaxis, plan local y diff-check correctos. Evidencia, módulos/resultados,
respaldo anterior/final y manifiestosSHA256:
`../Humanoide-vla-evidence/20261002_BOX_ALIGNMENT_VISUAL_ARRIVAL/`.

Activación: próxima sesión optimista autorizada transmite helpers en memoria
a Motion/cliente en contenedor redescubierto, sin instalación remota/reinicio.
Dependencias/SDK/vendor/SPSbf145fa17e1116fc/XML/YAML/mapa intactos. Esta intervención
no conecta al robot ni envía detecciones, comandos físicos o HOME.
Rollback: restaurar selectivamente los tres scripts/test/notas desde before/,
retirar fixture nueva y conservar cambios posteriores; vuelve llegada5mm PC,
manteniendo revisiones anteriores. No restaura estados remotos/checkpoints.
Punto de reanudación: conservar diario/checkpoint y comprobar físicamente
parada/postura/caja para recuperación específica, sin inferir estado actual
del ensayo ni reiniciar automáticamente un ciclo fallido. Sin commit/push.

## Revisión de asociación del intento092429

**02-10-2026, Europe/Madrid — OBSERVADO histórico:**
`20261002T092429Z_OPTIMISTIC_SCENARIO1_275930` solicitaX+23,953mm, termina
navegación exitosa/reposo y pasa llegada6,8mm/0,45°. Capturas iniciales:
X0,792248/0,793953m; posterioresX0,746606/0,743580m. Cada pareja pasa20mm/3°
con chasis quieto, TF exacta, sellos crecientes y edad0,719/0,739s tras reposo.
La última caja observada cumpleXYZ. Fallo posterior: comparar únicamente las
últimas selecciones transformadas al mapa da29,625624mm. No se envió agarre,
segunda corrección ni HOME; errores de lease son del cierre después del rechazo.

Mapa y odometría dan desplazamientos distintos. Cambiar sólo al último par
odométrico da21,957063mm y tampoco pasa20mm; no se omite ese resultado.
**INFERENCIA:** ruido de detección entre vistas y actualización del mapa pueden
contribuir a la discrepancia. No es una calibración de VSLAM/odometría ni prueba
de identidad de caja. Los índices2 de las capturas no constituyen identidad.
La media de las dos posiciones coherentes de cada postura, con orientación
promediada tras normalizar/alinear el signo de cuaterniones, da en odometría
local **19,289749mm/2,120403°**, dentro de los mismos20mm/3°.

**Cambio local:** sólo la asociación entre posturas usa esas medias diagnósticas
y odometría local. La comparación fija el ancla inicial para todos los ajustes;
no la mueve incrementalmente para tolerar deriva acumulada. Usa los informes
de reposo ya existentes antes/después de cada pareja; no añade detecciones,
consultas ROS, reinicios ni publicadores. Revalida forma/sellos/frame/velocidades
de las muestras y edad en su instante de finalización registrado; las recepciones
reales/lease fueron validadas en el worker original y no se inventan sellos nuevos.
Exige odom→base_link/base_footprint, frames iguales dentro de los informes y
entre posturas, dos muestras posteriores a cada petición y frescura0,5s,
reposo0,003m/s/0,01rad/s, estabilidad5mm/1° dentro de cada postura. Las comprobaciones
de odometría deben encerrar temporalmente las dos imágenes. Sigue verificando
mapa estable y asociación temporal de las imágenes con las poses durante captura.

Son coordenadas de comparación: XY/yaw en odometría planar y Z relativo a
base_link con cuerpo en HOME; no una pose absoluta3D para Motion. La diferencia
vertical fija base_link/base_footprint se cancela entre posturas. La consulta
histórica [21-09](GET1_PUT1_MAPA_Y_EJECUTOR.md#2026-09-21-1303-europemadrid--box-01-select-pila-apartada-objetivo-primero)
observó mismoXY y diferenciaZ0,13m; no es comprobación de TF actual de esta
intervención. Se mantienen torso/brazos HOME y el uso exclusivamente diagnóstico.
Un cambio/reset de frame o desplazamiento incompatible sigue rechazando.

La media lleva comparison_only=True y nunca sustituye selection.selected_pose
del último resultado original. Correcciones siguen calculadas con esa medición
original, en X/Y, y mapa fresco. La referencia de agarre sigue exactamente la
segunda captura original; adaptador nativo vuelve a detectar y conserva el gate
XYZ/TF/frescura/consistencia de sus capturas antes de entregar una pose a Motion.
No cambia2cm/3°, gateXYZ, llegada12mm/2°, ventana5mm para giro, guard físico,
salud, watchdogs, cancelación, dos objetivos/50mm solicitados/70s o criterios
de mejora. Medias no pueden esconder una pareja incoherente: se valida antes
de promediar. Una asociación geométrica válida no demuestra identidad física.

Fuentes/destinos PC: [planificador](../../scripts/box_handling/scenario1_box_alignment.py),
[runtime](../../scripts/box_handling/scenario1_runtime.py),
[payload](../../scripts/box_handling/scenario1_cli.py),
[tests](../../scripts/box_handling/test_scenario1_box_alignment.py) y
[fixture saneada](../../scripts/box_handling/fixtures/box_alignment_association_20261002.json).
Dependencia pura [scenario1_resume_worker](../../scripts/box_handling/scenario1_resume_worker.py)
sin cambios, cargada ahora también en supervisor antes del planificador; ROSA
sigue importándose sólo al ejecutar lectores. El runtime borra asociación previa
al empezar una medición y registra geometría/frame/base usados. Evento
box_alignment_association archiva resultado o causa con ambos extremos al fallar.
No se reutiliza como permiso persistido ni de una sesión anterior.

Receta offline:

```bash
python3 -B -m unittest scripts.box_handling.test_scenario1_box_alignment \
  scripts.box_handling.test_scenario1_optimistic \
  scripts.box_handling.test_scenario1_resume_runtime
./scripts/optimistic_scenario1.sh --plan
bash -n scripts/optimistic_scenario1.sh
git diff --check
```

**715 pruebas pertinentes correctas**, cero errores/fallos; misma exclusión
legacy test_scenario1_deposit_install. Siete nuevas cubren replay con cuatro
capturas/informes reales, medias y signos de cuaterniones sin mutar originales,
frames/relojes/muestras/reposo/frescura/bracketing, límites20mm/3°, caja cambiada,
pareja incoherente y flujo hasta agarre simulado con última poseX0,743580m intacta.
No se reproduce un éxito físico: la prueba usa acciones Mock. Sintaxis, plan y
diff-check correctos. Fuentes, hashes antes/después, diario saneado con SHA256,
association-replay.json, tests.json/tests.log y plan.json:
`../Humanoide-vla-evidence/20261002_BOX_ALIGNMENT_ODOM_ASSOCIATION/`.

Instalado PC: sí; carga Motion/cliente nativo y prueba física de esta revisión
**PENDIENTES**. Activación en próxima sesión optimista autorizada, transmisión
en memoria a contenedor redescubierto; sin instalación persistente/reinicio.
SDK/vendor/tareas/XML/YAML/SPSbf145fa17e1116fc/guard/percepción base intactos.
La discrepancia mapa/odom/cámara y su calibración siguen PENDIENTES; este cambio
no la corrige ni convierte un dato histórico en estado físico actual.
Rollback: restaurar selectivamente tres fuentes/test/notas desde before/ y
retirar fixture nueva, preservando cambios posteriores; vuelve asociación de
última captura en mapa. No restaurar checkpoint/leases/estados remotos. Reanudar
con recuperación específica y comprobación física de parada/postura/caja.
Sin conexión, movimientos, comandos HOME, commit ni push por el agente.

## Diagnóstico HOME del intento093621

**02-10-2026, Europe/Madrid — BOX-01-HOME-DIAGNOSTIC. OBSERVADO histórico;
IMPLEMENTADO PC; VERIFICADO offline con719 pruebas pertinentes y5 del clasificador.**

El diario `../Humanoide-vla-evidence/20261002T093621Z_OPTIMISTIC_SCENARIO1_305053/events.jsonl`
contiene dos muestras de actuadores con sellos1790933761.632769913 y
1790933761.652784627. Ambas pasan validación de cobertura, habilitación/fault,
velocidad y consigna del clasificador original, pero dan MEASURED_HOME=0.
Único eje fuera de HOME: head_pitch1002=−0,4307609799981366rad (−24,680°).
Cabeza yaw1001=−0,0002876214rad; máximo absoluto sin cabeza0,000958738rad,
velocidad corporal0 y máxima diferencia consigna/posición0,000958738rad.
HOME exige valor absoluto estrictamente menor de0,02rad en los20ejes, cabeza
incluida. El registro no contiene etapas ni acciones físicas de ese intento.
Checkpoint: completed=[], in_flight=null. No acredita que la caja esté libre
actualmente ni que siga siendo seguro cualquier movimiento de recuperación.

INFERENCIA: inclinación compatible con la preparación visual0/−0,43rad de
los intentos anteriores. Esto no es una medición actual ni un permiso para
iniciar el ciclo o ejecutar HOME. Los errores de lease son posteriores al
rechazo original durante el cierre del lector; no justifican alargar la lease.

El supervisor ahora informa head_pitch(1002)=−0.430761rad, límite |posición|<0.02rad
(y cualquier otro eje rechazado), con recuperación presencial antes de repetir.
Antes de generar ese detalle aplica el clasificador completo original: no
oculta faults, duplicados, ejes ausentes, movimiento ni consignas latentes.
Registra `home_not_measured`, sello de la muestra, clasificación y ejes fuera
de HOME antes de abortar. No amplía tolerancia ni acepta una cabeza de observación
como HOME, no envía objetivos de recuperación y conserva el requisito para las
dos muestras frescas. Las ruedas no forman parte de20D y sus posiciones no se
incluyen en el diagnóstico. Un control de salud sin exigir HOME sigue admitiendo
la postura observacional sólo cuando la etapa correspondiente lo permite.

### Continuación física

Antes de iniciar otra sesión, el operador debe comprobar efector/abrazaderas,
caja libre/sujeta/apoyada, contacto y obstáculos, paros, cargador/batería, ruedas,
modo y mando exclusivo, con una persona junto al paro. Si la postura nueva sigue
siendo sólo cabeza de observación con cuerpo HOME, recuperar la cabeza a0rad
con el control supervisado vigente y despejado; no sustituirlo por una trayectoria
completa de brazos/cuerpo. Esta intervención no descubre ni autoriza una nueva
orden remota para esa recuperación. No repetir HOME ni cambiar de modo como
prueba. Una recuperación distinta requiere determinar antes el estado real.

Después de la recuperación, comprobar con lecturas nuevas:

```bash
./scripts/optimistic_scenario1.sh --check
```

Sólo un check satisfactorio con HOME20D nuevo permite plantear el siguiente
`--run` desde abrazaderas vacías y recorrido preparado. Una reanudación de grasp
sigue exigiendo HOME20D y llegada get1; --recovery-confirmed no los omite.
El script general cruzr_recover_to_home.sh --check puede clasificar la ruta
histórica, pero su --run no es recuperación específica de cabeza: podría
retroceder el chasis y mover brazos en una ruta de caja reconocida. No se indica
como solución automática a este registro.

### Fuente, aplicación y reversión

Destino PC: scripts/box_handling/scenario1_runtime.py y su test_scenario1_runtime.py.
El CLI vigente transmite el supervisor y el clasificador en memoria a Motion
redescubierto durante la siguiente sesión autorizada. No se instala archivo,
reinicia contenedor ni se cambia XML/YAML/SDK en el robot. Instalado PC;
carga remota y verificación física del mensaje PENDIENTES.

- SHA256 scripts/box_handling/scenario1_runtime.py: `a7dde5b773039c1bb6a6ba484363b3fea55b65531b76b6318779cd02bc802902`.
- SHA256 scripts/box_handling/test_scenario1_runtime.py: `a81f8af351d32616083fd97d9cf404f33edd11833dd5665e34b10e30c4bce29a`.

Backup exacto previo y posterior, manifest SHA256, estado Git, incident-summary.json
y resultados en ../Humanoide-vla-evidence/20261002_BOX_HOME_DIAGNOSTIC/.
El backup previo preserva la revisión de asociación aún sin commit. Reversión:
restaurar selectivamente runtime/test/notas desde before/ comparando con el
árbol vigente, sin perder cambios posteriores; no restaurar HEAD completo,
checkpoints, estados de control ni revisiones anteriores de asociación.

Verificación reproducible local, sin ROS/red/robot:

```bash
python3 -m unittest scripts.box_handling.test_scenario1_runtime
python3 scripts/test_home_posture_gate.py
bash -n scripts/optimistic_scenario1.sh
./scripts/optimistic_scenario1.sh --plan
```

Nuevas regresiones de seguridad: cabeza observacional bloqueada sin comandos,
borde exacto0,02rad y alias de torso, fault prioritario, rechazo de la segunda
muestra fuera de HOME y controles sin HOME inalterados. El conjunto pertinente
excluye el test_scenario1_deposit_install legacy con errores ya documentados;
el listado exacto y resultados están en tests.json. Estado físico y éxito de
recogida tras las correcciones anteriores siguen PENDIENTES.

Resultado:719/719 pruebas pertinentes y5/5 del clasificador correctas; AST, bash -n,
plan local y git diff --check correctos. La primera ejecución de las cuatro
pruebas nuevas falló por sellos sintéticos anteriores a su consulta; corregidos
sólo los sellos del test, sin relajar frescura en producción. Registro conservado
en tests-initial-failed.txt. Sin conexión, movimiento, commit ni push del agente.

## Revisión de progreso odométrico del intento094521

**02-10-2026, Europe/Madrid — BOX-01-VISUAL-ALIGN-ODOM-PROGRESS.**
OBSERVADO histórico, IMPLEMENTADO PC, VERIFICADO offline; nueva carga/ensayo
físico PENDIENTES. No conexión ni movimiento del agente.

El intento `20261002T094521Z_OPTIMISTIC_SCENARIO1_327808` supera HOME inicial,
get1 (3,6mm/0,46°), visión y preparación de cabeza. Caja seleccionada original
X0,791200231m, Y0,107340655m, Z0,310717357m: se solicita X+21,200231mm;
el objetivo permanece en mapa. En la vigilancia el error de mapa sube desde
21,200mm hasta pico28,863mm y después baja sólo a27,095mm, sin mejorar2mm
respecto del pico. No se consume la concesión de recuperación inicial anterior.

A4,007992979s desde armado el guard cancela por no significant progress.
Recorrido acumulado: mapa9,757mm, odometría42,601mm; desplazamiento neto en
odometría25,800mm. La posición local relativa al objetivo pedido tiene error
4,599724mm. Máximos registrados0,026206119m/s y0,011344640rad/s; frames odom
y base_footprint. El mapa recibe sellos nuevos pero su XY permanece casi fijo
tras el primer retroceso mientras odometría avanza. Esto demuestra discrepancia
de estimaciones; no prueba por sí solo movimiento físico, causa, calibración o
parada. Pregunta al operador sobre retroceso/avance pendiente de respuesta al
cerrar esta intervención. No se usa odometría para afirmar llegada física.

Cancelación del UUID propio aceptada return_code0; resultado terminalstatus5,
FSM_Navigating onCancel and stop. Parada física no confirmada, sin agarre/reintento
ni HOME después. Errores de lease posteriores pertenecen al cierre. La postura
actual, estado de la caja y recuperación siguen PENDIENTES: no reiniciar el ciclo
a partir de este diario sin recuperación específica/comprobación presencial.

### Cambio de supervisión

En arm(), con los dos streams frescos y estacionarios existentes, el guard
calcula el desplazamiento objetivo dentro del frame mapa: objetivo−origen_mapa.
Rota ese vector por yaw_origen_odom−yaw_origen_mapa y lo ancla a origen_odom.
Eso expresa la misma solicitud relativa en odometría; nunca resta coordenadas
mapa/odom, modifica el objetivo físico ni publica un TF. Requiere box_pickup y
frames odom→base_link/base_footprint; get1 y frames desconocidos conservan el
comportamiento anterior. La correspondencia planar/yaw de la postura inicial
es una hipótesis del seguimiento local, no una calibración global demostrada.

Cada pose odométrica validada puede renovar el contador existente sólo si mejora
al menos2mm respecto del mejor error local que ya contó como progreso. No basta
moverse ni recorrer distancia: una dirección equivocada, volver al mismo mínimo,
oscilar o continuar más allá del objetivo no renuevan ese progreso. El crédito
es finito al aproximarse al objetivo; no hay renovación por entrar/salir de una
ventana de llegada local. Durante settling no se renueva por odometría.

El watchdog conserva4s desde la última mejora, tiempo de acción30s, total70s,
recorrido120mm y excursión80mm en ambos frames; empeoramiento de mapa≤15mm,
límites de velocidad/giro, sellos/frescura, frames estables, salud, lease y
cancelación quedan activos. Si el mapa no converge, se sigue cancelando después
de4s sin mejora nueva. La llegada terminal requiere éxito nativo, reposo y
nuevas poses de mapa≤12mm/2°, después nueva visión/coherencia/gateXYZ. La
ventana5mm de mapa del guard para giro rápido no cambia: cercanía odométrica
no habilita giro1,20rad/s ni autoriza llegada/agarre. No se intenta relocalizar
durante movimiento, alargar lease ni repetir una acción cancelada.

Logs nuevos: progress_source indica mapa u odom_relative_goal; pickup_odometry
incluye objetivo diagnóstico local, distancia actual, mejor error acreditado,
sello de progreso y arrival_authorized=false. progress_distance_m sigue siendo
el valor anterior en mapa; no se mezcla numéricamente con el error odométrico.

### Verificación, aplicación y reversión

La fixture versionada `scripts/box_handling/fixtures/box_alignment_odom_progress_20261002.json`
conserva spec, snapshots archivados y SHA256 del diario original. Replay de las
poses muestreadas reconoce progreso antes del punto de cancelación original,
con mapa todavía27,095mm y odometría local4,600mm, sin afirmar llegada/reposo.
No es replay completo DDS: la primera muestra estacionaria se reconstruye,
los snapshots sólo contienen últimas poses y los twists instantáneos del test
son sintéticos (reposo); los límites de velocidad se prueban separadamente.
No demuestra que la navegación nativa vaya a terminar o que la caja sea alcanzable.

Ocho regresiones nuevas: traza archivada, rotación entre frames/origen exacto,
reposo/dirección equivocada/subumbral, oscilaciones, sobrepaso/giro rápido,
gates de mapa/velocidad/excursión/frescura/frames, get1/frames desconocidos y
persistencia del aborto cuando el mapa no converge. Suite pertinente727/727
correcta; módulos exactos/exclusión del legacy test_scenario1_deposit_install
con errores previos constan en tests.json. AST, bash -n, plan local y diff-check
correctos. Las dos primeras pruebas nuevas fallaron por geometría sintética de
yaw fuera del gate y recorrido de oscilaciones>120mm; corregidos sólo los tests,
sin relajar gates de producción.

```bash
python3 -m unittest scripts.box_handling.test_scenario1_nav_correction \
  scripts.box_handling.test_scenario1_correction_transport \
  scripts.box_handling.test_scenario1_action_session
bash -n scripts/optimistic_scenario1.sh
./scripts/optimistic_scenario1.sh --plan
git diff --check
```

Destinos PC: guard/test/fixture y notas enlazadas. Activación: la próxima sesión
autorizada transmite el helper vigente en memoria al cliente Motion descubierto,
sin instalación ni reinicio. Instalado PC, carga remota y validación física de
esta revisión PENDIENTES; el ensayo anterior ya demuestra que la preparación y
el objetivo correctivo se enviaron, no éxito de agarre ni HOME final.

- SHA256 scripts/box_handling/scenario1_nav_correction.py: `68dcdf2cb8a91b673a5ee948c7f35c0fd2405800c99db93cc2ea3eecff15f131`.

- SHA256 scripts/box_handling/test_scenario1_nav_correction.py: `195945e422bbbb75aa09826e17750c238cfc4e65206d83e815a5404745458180`.

- SHA256 scripts/box_handling/fixtures/box_alignment_odom_progress_20261002.json: `75a4983128bc5cffb4555721722067c22f936dda42eb2a51fbc2e38fe23a4f18`.

Backup exacto before/ y after/, manifiestos previos/finales, estado Git,
incident-summary.json, tests.json/tests.txt y plan en
`../Humanoide-vla-evidence/20261002_BOX_ALIGNMENT_ODOM_PROGRESS/`.
Reversión selectiva de guard/test/notas desde before/ y retirada de la fixture
nueva; conservar las revisiones anteriores de asociación/HOME y cambios
posteriores. No restaurar checkpoint ni estado remoto. Sin commit ni push.

15-10-2026 — preparación de publicación: se conserva POLICYmax_corrections7
editado en copia local; CLI ahora muestra el valor vigente, sin fijarlo en2.
Prueba de escenario con25mm iniciales +24mm solicitados después espera49mm;
permanece presupuesto total50mm. Ajuste de mensaje/prueba, sin ejecución física.
