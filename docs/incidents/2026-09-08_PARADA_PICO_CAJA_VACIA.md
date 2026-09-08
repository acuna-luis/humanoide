# Detención PICO al manipular caja vacía

**08-09, recuperación solicitada tras disparo FT:** el operador confirma caja
retirada, abrazaderas vacías, estabilidad/sin contacto, zona libre y otros mandos
detenidos. El --check de recuperación rechaza ACTION_BUSY (rc27). Se canceló
únicamente la tarea PICO `ac314729-ec21-4ea5-9439-4d4d8f179824` por CancelGoal;
respuesta aceptada y status final 5 (CANCELED). ROSA falló en conversión local
del UUID antes de llamar; la llamada ROS2 estándar sí fue aceptada.
Muestra posterior sana e inmóvil, delta máximo 0,001900 rad, NO HOME.
No se envió trayectoria ni rearme. Recuperación HOME pendiente: postura PICO
tras fuerza no cubierta por READY→HOME ni por el ciclo de caja del wrapper.
No hubo cambio persistente de configuración ni reinicio; sin monitor activo.

2026-09-08. Sólo diagnóstico, cero movimientos/servicios/rearmes/reinicios.
Operador reporta caja vacía desechable manipulada mediante teleoperación y
posteriormente soltada; ningún paro accionado. No equivale a caja retirada de
trayectoria ni a ausencia de contacto/daño confirmada.

VERIFICADO en Motion: protección de fuerza bilateral, primero izquierda y
0,200 s después derecha. Log local Motion 15:44:22.988/15:44:23.188 (relojes
con desfase; no interpretar como hora Madrid). Izquierda pasa a kTerminated,
después derecha; mensajes explícitos `force protection triggered!`.

Wrench registrada [Fx,Fy,Fz,Mx,My,Mz], unidades/compensación deben contrastarse
con configuración del controlador antes de derivar cargas físicas:
- izquierda inicial [-12.1019,1.71507,-1.22408,0.436419,3.96022,4.36346];
  disparo [5.34205,123.287,-4.11798,52.2784,-1.1948,55.5776].
- derecha inicial [-14.44,3.97321,-5.7081,2.79058,6.26413,-3.10361];
  disparo [-25.8225,-120.294,-14.6216,-48.5371,16.4354,-52.3608].

INFERENCIA: fuerzas bilaterales durante agarre compatibles con apriete/contacto;
no se demuestra punto de contacto ni se atribuye al peso de la caja. Tampoco
se declara falla del sensor o tara incorrecta. Disparo explícito demostrado;
causa mecánica y umbral/comparación exactos pendientes.

Muestra posterior: paros 0/0, veinte actuadores habilitados/sin error,
velocidad cero, delta máximo consigna 0,001900 rad, máximo posición 1,660630 rad:
NO HOME. Servidor de manipulación disponible, RobotCommand writers 0/readers 2,
VLA detenido. Writers 0 sólo cubre ese topic: no prueba STOP del transporte PICO.
Motion conserva CoreMode 7 en registros posteriores. No se conectó WebSocket
PC por riesgo documentado de auto-START; consulta pasiva del log no cambia modo.

PENDIENTE antes de recuperación: estado físico estable/sin contacto, caja fuera
de trayectoria, control PICO cesado, inspección y ruta específica desde esta
postura. HOME↔READY previamente probado no cubre esta postura teleoperada.
No rearmar ni HOME automático. Última postura vigente teleoperada detenida,
sustituye HOME del ensayo anterior. Sin monitor persistente.

Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260908T074634Z_ESTOP-AVAILABLE/results.json` y extracto force-trip-excerpt.txt.
