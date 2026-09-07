# HOME observado el 07-09, 12:33 Madrid

## Hechos y alcance

**OBSERVADO por operador:** «hecho, se fue a home sin problemas».
No convertir este reporte en inspección de daños ni aprobación de otras rutas.

**VERIFICADO en registros:** Motion, archivo
`/etc/walker/log/motion/robot_app.20260907-132646.65.log`:

- Inicio cruzr/home: 18:33:35.654659, reloj del host.
- Órdenes lifter, left_arm, right_arm, waist, head a cero, duración 6 s.
- Ambos brazos y los otros tres grupos registran éxito.
- BTree tick succeeded: 18:33:42.733877.
- Consulta date del host devuelve +08:00; conversión a Madrid +02:00:
  inicio 12:33:35.654659 y fin 12:33:42.733877, suponiendo reloj host correcto.
- 184 avisos ValidateCmdWithLimit en la ventana examinada, de cabeza índice
  literal 2. Primer valor −0.696331 frente a límite inferior −0.688727 rad.
- Búsqueda de Excessive force/ft sensor en esa ventana no produjo alarmas.
  No equivale a fuerza cero ni a telemetría continua de los sensores FT.

Primera consulta al host: 18:34:19 +08:00, posterior al fin. No se realizó
vigilancia preventiva durante este movimiento; fue lectura retrospectiva.
Última lectura 18:35:52 +08:00 conservaba fin de tarea como última entrada.
No se enviaron movimientos, servicios ROS, rearme ni cambios de configuración.

## Pendientes

Determinar el tratamiento del aviso de cabeza y la consigna inicial; no ampliar
límites para silenciarlo. El éxito y reporte del operador describen este retorno
particular, no validan VLA, apertura lateral, teleoperación o montajes/recorridos
distintos. No atribuir causa del incidente anterior sólo a asimetría por este
resultado. Estado físico actual, paros y holguras no medidos por el agente.
