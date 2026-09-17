# Separación derecha interrumpida: 137 y aborto Iceoryx

2026-09-16, Europe/Madrid. Diagnóstico remoto sólo lectura. Sin movimientos,
reinicios, limpieza de memoria compartida ni modificación de límites/configuración.

## Hallazgos verificados

El operador ejecutó una versión del script con `navigate_get1` añadido por él;
se conserva íntegra. Navegación a get1 y habilitación de visión terminaron bien.
La separación empezó a las 18:38:15.510 del log Motion (10:38:15Z en eventos Docker).
La visión devolvió detección exitosa en 1006 ms; no fue VisionDetectionFailure.

A las 18:38:21.803 RouDi/Iceoryx eliminó aplicaciones por falta de respuesta
1504–1528 ms. Inmediatamente después Motion informó:

```text
pthread_mutex_lock: [22] Invalid argument
ICEORYX error! POPO__CHUNK_LOCKING_ERROR
terminate called without an active exception
SIGABRT
```

Stack: `ThreadSafePolicy::lock → PublisherPortUser::sendChunk → dds_write →
RobotRosaClient::PubPayloadState`. Relación temporal consistente con recursos de
comunicación invalidados tras retirar las aplicaciones. El motivo de perder
los heartbeats (planificación/CPU, bloqueo u otro defecto) sigue PENDIENTE;
no se afirma agotamiento de memoria ni causa geométrica del aborto.

Docker registra `exec_die exitCode=137` a epoch1789555102 y reinicio automático
de `walker-motion.manipulation_robot_app-1` a 10:38:22.224Z. El contenedor IMU
reinició a 10:38:22.222Z. Ambos RestartCount1. El contenedor principal registra
`die exitCode=0`; no confundir esa salida del wrapper con el SIGABRT del proceso
interno o el 137 de docker exec. No hubo resultado ArmTask final que justificase
continuar. El aborto ocurrió ~6,3 s después de iniciar la tarea, antes de45s.
Al desaparecer el contenedor se perdió también el shell interior y sus traps;
el mensaje genérico exterior no describe adecuadamente esta causa.

No se observó evento Docker OOM en la ventana; estado actual OOMKilled=false,
RAM disponible4189MiB, swap0usada, /dev/shm64% ocupado. Estos datos posteriores
no demuestran ausencia absoluta de presión puntual. journalctl-k sin entradas.

## Hallazgo geométrico distinto

El detector usado por esta ejecución produjo `X_BaseBox`:
X0.810808m, Y0.132186m, Z0.736137m. Límite configurado de X:[0.4,0.8]m.
Exceso **10.808mm** en el eje X de la base, no distancia desde la rueda ni desde
el borde del chasis. Motion registró la advertencia y continuó al cálculo IK.
No hay evidencia de que ese exceso causara el fallo de Iceoryx. Repetir navegación
a un punto de mapa no garantiza reproducir exactamente el registro relativo
robot/caja del ensayo manual exitoso. Falta comparar pose de llegada y detección
con aquel ensayo antes de corregir get1; no se altera punto ni límite aquí.

## Estado posterior observado

Operador confirma que no pulsó E-stop: robot inmóvil y caja apoyada/sin moverse.
Lectura de ambos paros0/0. JointStates nuevo: 22 velocidades cero, torso próximo
al cero, brazos preparados y cabeza−0.430473rad; no HOME. La primera lectura de
actuator_state expiró; no inventar un diagnóstico de actuadores sin esa muestra.
Servidor de manipulación presente (1) después del reinicio; esto no prueba
salud completa. RouDi sigue avisando de Keepalive de procesos desconocidos.
Captura pasiva RGB/nube/TF con timestamps RGB/nube coincidentes; imagen muestra
las cajas superiores y la pila inferior a la derecha. No demuestra ausencia de
contacto fuera del campo visual. Foto lateral y confirmación del operador
concuerdan con postura preparatoria, sin extracción completada.

## Continuación

No repetir el ciclo completo ni emitir HOME desde esta postura a ciegas.
Antes de reanudar: recuperar salud de comunicación con procedimiento adecuado
al estado físico; verificar pose/caja y comparar llegada a get1. El arreglo
permanente requiere investigar heartbeat y ciclo de vida de memoria compartida
con UBTECH. No ampliar el timeout ni borrar /dev/shm como supuesto arreglo.
No se solicita aquí un reinicio automático, que podría activar HOME.

## Evidencia y cambios

Privada: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260916T104043Z_SEPARATE_137/`: inspección Docker, eventos, logs Motion/HW/CC,
ventana precisa de RouDi, JointStates, paros y RGB/nube/TF (`scene.json`,
`camera.png`). Logs IMU de la ventana fallaron por un NUL en el log Docker;
se conserva ese fallo de lectura y no se atribuye una causa IMU no observada.
Cambios persistentes: únicamente este informe y enlaces documentales PC.
Respaldo de documentos en `before-docs/`; reversión selectiva de esos cambios.
Script del usuario, servicios, mapa y parámetros permanecen intactos.

## Dos rechazos posteriores de alcance (16-09, 18:46 y 18:48 hora del log)

Consulta posterior sólo lectura, evidencia `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260916T104942Z_OUT_OF_REACH`. Ambos intentos retornaron
ClampBoxOutOfReach/7101100/status6, sin el aborto137 en esas ejecuciones.
Primer X_BaseBox=[0.810903,0.127635,0.736885]m; segundo
[0.803963,0.130645,0.738027]m. X excede máximo0.8m en10.903mm y3.963mm.
En ambos el código continuó a IK, que devolvió `Cannot find matched IK101`,
`IK failed for eef poses in Cartesian` y `both PositionAndRotationLimit and
IkSolved checking failed, exit`. Por tanto no es sólo un límite numérico:
también falló la solución cinemática de las poses solicitadas. No basta ampliar
el máximo ni afirmar que avanzar4mm garantiza agarre.

HOME intermedio comunicado por operador con SUCCEED; siguiente intento volvió
a fallar. Pose de base leída después: distancia a get1 7.84mm y
diferencia yaw -0.196°. No demuestra un error grande de navegación; el
punto guardado reproduce una relación robot/caja que esta ejecución rechaza.
La muestra es posterior, no telemetría exacta del instante de detección. put1
ya existe. get1 conserva X/Y/yaw guardados; otros campos auxiliares cambiaron
por edición externa. Sin sobrescribir mapa, script, límites ni mover el robot.
Siguiente: comparar con geometría/pose del ensayo exitoso, corregir aproximación
y registrar get1 sólo tras verificar alcance; causa Iceoryx previa sigue abierta.
