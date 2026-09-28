# Selección de caja del fondo y flexión inesperada durante el agarre

28-09-2026, Europe/Madrid. **BOX-01-EXEC-IMPROVED — incidente reconstruido.**
Actualización posterior: operador informa recuperación a HOME tras recolocar
brazos y liberar E-stop. Esta es su observación, no medición ni movimiento del
agente. Por petición posterior se corrigió selección y rechazo SPS; instalado
paquete `bf145fa17e1116fc`, con ensayo físico PENDIENTE.
[Corrección, pruebas y estado](../box_handling/FRONT_BOX_DEPTH_GATE_20260928.md).

**Historial de diagnóstico:** recuperación entonces PENDIENTE; operador apagó
y volvió a encender con E-stop. Diagnóstico solicitado por el operador, sólo
lectura de Motion/Vision y archivos locales. No se enviaron movimientos, HOME,
rearme, reinicio, cambios de configuración ni apagado.

## Resultado

**VERIFICADO:** el selector entregó la caja baja del fondo, aunque había otra
caja baja delante. El objetivo elegido estaba a X≈1,192 m en `base_link`; la
candidata cercana estaba a X≈0,794 m. Motion calculó X≈1,195 m, registró que
superaba su intervalo configurado de 0,40–0,80 m y continuó con comprobación IK
y ejecución de la trayectoria. Los objetivos de manos descendían de Z≈1 m a
Z≈0,11 m y avanzaban hacia ese objetivo lejano. La cadena selección → pose
aceptada → trayectoria explica el intento de alcanzar hacia delante y abajo.

**OBSERVADO por operador:** movimiento inesperado al intentar recoger la última
caja; pulsó E-stop, retiró las cajas implicadas y aportó fotografías de postura
con torso flexionado. Después confirmó robot y brazos inmóviles/estables,
abrazaderas vacías y ausencia aparente de contacto, ruido o calentamiento.
Las fotos no cuantifican fuerzas, daños ni el estado mecánico actual.

No atribuir el incidente sólo a altura baja: otro ciclo de ese día terminó con
un objetivo bajo y cercano. Tampoco atribuirlo a los mensajes de consola ni a
la precisión de get1: la llegada medida pasó (≈17,55 mm / 0,431°) y el fallo
ocurrió en `grasp`.

## Evidencia conservada antes del apagado

Directorio externo:
`../Humanoide-vla-evidence/20260928T145208Z_LOWEST_BOX_ESTOP/`.

- `pc-sessions/`: copia del intento fallido
  `20260928T144311Z_IMPROVED_SCENARIO1_1409920` y tres ciclos anteriores,
  incluidos `events.jsonl`, checkpoints, contexto y hashes de fuentes.
- `cruzr-scenario1-15lanme6/`: sesión remota fallida, selección original,
  checkpoint y logs del adaptador. Tres sesiones remotas anteriores preservadas.
- Logs Docker de manipulación, hardware, Control Center y detector; inventario
  nuevo de contenedores, estado/reinicios y XML/YAML vivos del agarre.
- `vision-2243.tar.gz` y `camera-2243/`: imágenes RGB, profundidad, estéreo,
  intrínsecos y anotaciones guardadas por el detector durante el intento.
  No son fotografías obtenidas después de retirar las cajas.
- `selection-comparison.json`: poses, candidatos, TF, reproducción local de
  las selecciones, referencias a líneas y hashes de archivos originales.
- Recetas `*-readonly.py` de las consultas realizadas y copia de las fuentes
  PC pertinentes. La evidencia cruda permanece fuera de Git.

La captura correspondiente a la selección es
`camera-2243/1790606603.318445000_action_grasp.jpg`, junto al RGB y profundidad
con el mismo sello. Muestra una pila lateral y dos cajas bajas alineadas en
profundidad. La anotación de la caja posterior tiene coordenadas de cámara
≈(−0,085; 0,844; 1,528), coincidentes con la pose que recibió Motion.

## Por qué ganó la caja posterior

En la segunda captura aceptada, el selector produjo:

| Candidata | Índice de esa captura | X en base_link | Y | Z | Ángulo horizontal |
| --- | ---: | ---: | ---: | ---: | ---: |
| Caja cercana | 4 | 0,794421 m | 0,106427 m | 0,099530 m | 7,630349° |
| Caja posterior, elegida | 5 | 1,191834 m | 0,112126 m | 0,100239 m | 5,374508° |

La separación longitudinal era 0,397413 m. El
[selector](../../scripts/box_handling/select_front_box.py) agrupa pilas por XY
y elige el menor ángulo horizontal absoluto, no la caja más cercana. Estas
cajas pertenecieron a grupos distintos. La posterior quedaba más centrada:
la diferencia de 2,255841° superó el umbral de ambigüedad de 2°, por lo que
no se rechazó la selección. Reproducir ambas capturas offline devuelve la misma
elección registrada; no se necesita inferirla de la foto posterior al paro.

La comprobación de dos capturas encontró sólo 3,09 mm y 0,97° de diferencia:
verificó estabilidad de esa detección, pero no que fuese la caja deseada ni que
pudiera alcanzarse con un recorrido libre. El informe declara
`reachability_checked:false`. El selector tampoco mantiene la identidad de la
pila entre ciclos ni comprueba que una caja detectada tenga otra debajo antes
de ejecutar una tarea de separación.

Estas Z pertenecen a marcos del robot y a poses del detector. **No son medidas
de la base de la caja sobre el suelo.** El `X_BaseBox` interno de Motion difiere
unos milímetros del `base_link` de la selección; ambas lecturas coinciden en el
objetivo lejano y bajo. No aplicar un offset de suelo a partir de este informe.

## Trayectoria y parada

Los tiempos siguientes son UTC **del reloj del robot**, tomados de los logs
Docker. El texto interno usa UTC+08. La captura de diagnóstico muestra un desfase
aproximado de 40 s con el PC; no mezclar directamente esos tiempos con el nombre
del directorio PC. Los tiempos entre Motion y Vision no certifican un orden
físico con precisión de milisegundos.

| Hora del log | Suceso |
| --- | --- |
| 14:43:22–24 | Detección de cajas y entrega de la pose posterior al cliente de manipulación. |
| 14:43:24,437 | `X_BaseBox out of limits`: X=1,19508 m; límites X=[0,4; 0,8]. |
| Misma secuencia | `while PositionAndRotationLimit failed, continue Iksolve check`; después `GetVisionBox successfully`. |
| 14:43:24–25 | Objetivos VISION: mano izquierda (0,9186; 0,2036; 0,1074) m; derecha (1,1866; −0,2492; 0,1095) m. |
| 14:43:25,932 | Comprobación IK declarada correcta; continuación de la trayectoria. |
| 14:43:32,271 | Motion registra exceso FT derecho, componentes −545,784 / 596,297 / 313,083 N. |
| 14:43:32,296 | Control Center registra E-stop pulsado y deshabilita capacidad de movimiento. |
| 14:43:34,910–35,101 | Error de seguimiento articular; resultado `ClampJointTrackingError`, 7101108, status=6. |

El aviso FT y el registro de E-stop están separados unos 25 ms en orden de log,
en hosts diferentes. No demuestra que el exceso FT precediese físicamente a la
pulsación ni identifica qué superficie recibió fuerza. El error de seguimiento
aparece unos 2,6–2,8 s después del registro de paro; es compatible con consignas
que dejan de ser seguidas tras detener el robot. **No demuestra movimiento físico
durante todo ese intervalo ni permite calcular la distancia de parada.**

Hardware y manipulación reiniciaron automáticamente después de la interrupción:
`hw` StartedAt 14:43:32,810; manipulación 14:43:37,576, RestartCount=1 en ambos.
No fueron reinicios enviados por el agente. El reinicio no acredita recuperación
de controladores ni postura HOME. Los errores posteriores de lease/cierre de
workers son posteriores al resultado fallido, no evidencia de que causasen la
selección o el movimiento inicial.

El checkpoint conserva sólo `navigate_get1` y `enable_vision` completadas;
`grasp` falló y el estado de caja quedó `unknown`. El operador declaró después
que las abrazaderas estaban vacías; esto no reescribe el checkpoint. No hubo
`retreat`, depósito ni HOME del ejecutor después del fallo.

## Límites del diagnóstico y siguientes medidas

**VERIFICADO:** selección del fondo, objetivos utilizados, aviso de distancia
y continuación, error terminal y registro de E-stop. **PENDIENTE:** reconstrucción
completa de articulaciones/barrido, punto exacto de contacto o esfuerzo, daño
mecánico y comportamiento de frenado. No se afirma que toda la flexión observada
quede validada por un cálculo IK exitoso.

El YAML vivo conserva configuración del proveedor y la adaptación local de
SPS; este diagnóstico no modificó límites ni protecciones. Su aviso de posición
no actuó como rechazo definitivo. Antes de repetir, hacen falta rechazo previo
efectivo de objetivos fuera de la región validada y selección vinculada a la
pila/posición deseada, considerando cajas de fondo y fin de pila. Cambiar sólo
la preferencia a «más cercana», ampliar ambigüedad o bajar velocidad no demuestra
por sí mismo una trayectoria apta. Implementación y ensayo de corrección pendientes.

**Contención operativa:** no repetir el ciclo ni reanudar el agarre fallido;
no ordenar HOME, rearmar ni liberar E-stop para corregir esta postura.
No se impuso un bloqueo nuevo ni se cambió software de control, porque la petición
autoriza diagnóstico de lectura. Los scripts existentes siguen disponibles;
este informe no autoriza ejecutarlos.

Para apagar, ya no hace falta conservar alimentación por los registros: están
copiados en el PC. Mantener paro y verificar presencialmente soporte/estabilidad
de brazos y torso contra caída o golpe al perder potencia, además de abrazaderas
vacías y zona despejada. No asumir descenso controlado ni sostener articulaciones
a mano. Seguir el [procedimiento de esta unidad](../support/UBTECH_SHUTDOWN_PROCEDURE_MISMATCH_V020.md):
apagado lógico, confirmación visual de pantalla/luces apagadas, después KEY1 y
chasis. No reiniciar desde esta postura para probar el HOME interno.

La consulta posterior de paros no pudo completarse: SSH devolvió
`No route to host`. Pérdida de conexión no confirma apagado ni el estado actual
de los paros. Después, el operador confirmó apagado y nuevo encendido con E-stop aún pulsado.
Confirmó que conserva la postura inclinada de las fotos. No liberar el paro ni
activar HOME interno desde esa postura; revisión presencial y recuperación
específica pendientes. La lectura del nuevo arranque se registra por separado,
sin reutilizar los estados técnicos anteriores. El intento de lectura en ese
nuevo arranque agotó SSH en Motion y Vision: no se verificaron controladores,
paros por telemetría ni postura articular después de encender.

## HOME instalado después del nuevo encendido

La conectividad volvió a estar disponible para una lectura posterior. Motion
presentó boot nuevo `cd0b8a7b-94d6-4fa2-a56b-561d13a603f2`. Se leyó directamente
`/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/cruzr/home.xml`:
SHA256 `d9e9462792b41300d352604b53ea2a4890a9382e942321990708f6ded2e26ccb`,
idéntico al [XML v8](../../scripts/teleoperation/tasks/cruzr_home_v8_early_roll_CANDIDATE.xml).
La lectura posterior `*-postboot-final.json` verifica paro principal=1 y
servo=0 en ambos hosts; Motion sigue esperando ListControllers y HW espera
`/mc/rosa_control/start`. Es evidencia de espera bajo paro, no de disposición
para mover ni de postura HOME. Control Center registra `WaitEStopRelease`
en el nuevo arranque. Sus logs también conservan la terminación lógica del
apagado anterior. No se llamó a esos servicios ni se liberó el paro.
Evidencia: `home-postboot.json`, lectura de archivo sin ejecutar la tarea.

| Fase nominal | Secuencia real |
| --- | --- |
| 3,75 s | Cabeza/elevador/cintura hacia cero **en paralelo** con ambos brazos: hombro −0,05 rad y codo −0,03 rad durante1 s; después otro −0,15 rad de hombro durante1,8 s. |
| 7 s | Bajada de ambos brazos hacia postura articular abierta. |
| 2,7 s | Cierre de ambos brazos hacia cero articular. |

Por tanto, la premisa «primero levanta torso con brazos quietos» no corresponde
al HOME instalado. Cambia el cuerpo y los brazos simultáneamente; no conserva
manos fijas en el mundo ni garantiza que suban desde el primer instante. No
incluye comprobación de distancia al suelo. La validación histórica de v8 no
certifica esta postura inclinada ni los obstáculos actuales.

El operador aporta fotos nuevas tras encender: abrazaderas muy próximas al
suelo y torso flexionado, con cajas retiradas del espacio inmediato. No usar
la imagen para declarar ausencia de contacto, soporte o libertad del barrido.
Se indica mantener E-stop, sin orden HOME ni liberación para probar. Preparar
una recuperación requiere postura articular fresca, revisión física del apoyo
y recorrido específico; no se ejecutó ni autorizó esa maniobra.

Cambios persistentes de esta intervención: documentación local únicamente.
Backup documental en `before/`; manifiestos de hashes/evidencia al cierre.
Para revertir documentación, restaurar selectivamente preservando cambios
posteriores; no hay rollback remoto. Sin commit ni push del agente.


## Apoyo en el suelo confirmado y límite de recuperación remota

28-09-2026, lectura PC17:11 CEST. El operador confirma que **alguna abrazadera
está apoyada en el suelo** tras el nuevo encendido y remite a las dos últimas
fotografías. Este contacto ya no es sólo una inferencia visual. Se indica no
liberar E-stop ni llamar HOME; la primera fase mueve brazos y cuerpo a la vez
y podría cargar/arrastrar el apoyo. No se indica tirar de brazos ni levantarlos
a mano. La salida requiere intervención presencial cualificada, aseguramiento
y procedimiento de servicio UBTECH adecuado a la postura y sus apoyos.

Consulta pasiva nueva, con contenedores identificados: principal1/servo0;
`/mc/actuator_state` tipo reconocido pero Writer count0 y lectura agotada,
`/mc/whole_joint_states` sin tipo/mensaje disponible. No hay veinte ángulos
nuevos para reconstruir el estado. La ausencia de datos no se resuelve liberando
el paro como prueba. El preparador local de recuperación rechaza E-stop activo
y no es un ejecutor validado para esta postura/contacto; no se invocó.

Evidencia adicional:
`../Humanoide-vla-evidence/20260928T151006Z_RECOVERY_POSTURE_READONLY/`.
`results.json` guarda comandos, salidas y tiempos; consultas únicamente, cero
servicios, objetivos o cambios remotos. La primera selección de nombres se
paró por coincidencia ambigua con ros2-export antes de leer topics; el segundo
intento utilizó roles con coincidencia completa. No se interpretó un código0
sin mensaje articular como lectura válida.

**Punto de reanudación:** robot bajo paro, contacto con suelo confirmado,
recuperación física pendiente de intervención presencial. Informe y evidencia
listos para soporte; no se enviaron a terceros. Mantener zona despejada y no
alterar apoyos, frenos o paros sin el procedimiento presencial correspondiente.
