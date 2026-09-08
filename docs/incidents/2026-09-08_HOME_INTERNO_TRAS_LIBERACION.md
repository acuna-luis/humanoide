# HOME interno tras liberación del paro — 08-09-2026

## OBSERVADO

El usuario comunicó haber liberado el E-stop. Se hizo lectura retrospectiva y
puntual con `collect_estop_available_readonly.py`, sin enviar goals, READY,
START, cambios de modo o servicios. No fue una maniobra monitorizada antes
de la liberación ni un ensayo HOME→READY.

Tiempos del log robot (+08:00; restar seis horas para Madrid, con el desfase
PC–robot previo ~25 s aún sin corregir):

- 14:00:10,197: CC pasa WaitEStopRelease→EnterWorkMode.
- 14:00:22,384: comienza StartMotion interno.
- 14:00:33,118: manipulación registra `cruzr/home` iniciado.
- 14:00:40,197: BTree tick succeeded.
- 14:00:40,211: StartMotion succ; después JoystickMode.

Lecturas posteriores:

- Principal/chasis 0/0; entrada de cargador 0.
- 20 actuadores no rueda presentes, IDs distintos, error_code=0 y status=0x1237.
- Máximo |posición| 0,003067962 rad; máxima velocidad reportada 0;
  máximo |consigna−posición| 0,003067962 rad.
- `/mc/whole_joint_states` vuelve a responder, sello 1788847270.602614907;
  las 22 velocidades reportadas son cero. No mezclar signos crudos de motor
  con coordenadas ROS; el resumen de actuadores usa magnitudes.
- Action server count 1, último goal status 4. `/mc/sdk/robot_command` writers 0.
- VLA control/inference exited, restart=no. Baterías 66,3/98,4 %, discharging.
- Topics FT vuelven a estar anunciados; no se midió fuerza en esta captura.

Evidencia externa:
`../Humanoide-vla-evidence/20260908T060126Z_ESTOP-AVAILABLE/`.
Los logs incluyen historial; la secuencia anterior corresponde al 08-09.

## Límites y reanudación

### Confirmación visual y lectura puntual posterior

El operador confirmó después: «salió todo bien al arrancar e ir a home y ahora
todo estable». Se registra como OBSERVADO POR OPERADOR, no medición de holgura.
Solicitó READY; no se envió porque el recorrido continúa sin validar. Sólo
se hicieron tres suscripciones concurrentes de lectura, sin monitor continuo:

- FT L, sello 1788847462.723603306: fuerza [34,4585; 8,5775; −5,2321] N,
  par [0,0821; −0,9385; −0,2361] N·m.
- FT R, sello 1788847462.623641974: fuerza [27,8512; −3,5691; 35,4211] N,
  par [−0,2917; −0,8155; 0,5906] N·m.
- Joints, sello 1788847462.828640704: 22 velocidades reportadas cero;
  posiciones de brazos iguales a la captura anterior, cabeza pitch −0,00297209 rad.

Frame FT `force_torque_sensor_controller`. Tara, compensación de gravedad,
ejes físicos y umbrales activos no verificados; no calificar como fuerza de
contacto ni declarar normalidad por estos valores. Muestras no simultáneas;
resultados crudos en salida de herramientas del chat, resumen persistido aquí.
No se presentó esta captura como registro del arranque ni del recorrido READY.

Estado articular puntual compatible con HOME, no garantía de ausencia de
contacto durante el arranque. Pendiente confirmación visual del operador de
estabilidad y ausencia de roce. No se ha validado HOME→READY ni READY→HOME.
No hay monitor continuo activo ni protección de parada aportada por estas
consultas. No se movió desde el PC; la liberación física desencadenó la tarea
interna. Geometría, trayectorias y condiciones completas siguen pendientes.
