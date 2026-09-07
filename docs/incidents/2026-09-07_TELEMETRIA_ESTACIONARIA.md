# Telemetría estacionaria — 07-09-2026

## Emparejador offline implementado

`scripts/audit_timestamp_pairing.py` empareja por nanosegundos enteros,
rechaza sello cero, timestamps articulares duplicados/desordenados y evita
extrapolar fuera del intervalo disponible. La aceptación exige tolerancia
explícita y reloj verificado; la CLI no certifica este último. No interpola
posiciones ni valida contenido articular. Tres tests pasan, incluido rechazo
del desfase observado de 1.288.367.921 ns. No se implementó aún recolector
continuo ni se verificó sincronización de hosts. Sólo desarrollo local.

## Alcance

Diagnóstico autorizado de sólo lectura, aproximadamente 12:48–12:51 Madrid.
No se publicaron comandos, cambiaron modos, abrieron WebSockets del PC ni
arrancaron cámaras. No constituye vigilancia preventiva ni aprobación física.

## OBSERVADO

- Motion: contenedor redescubierto `walker-motion.manipulation_robot_app-1`.
  Suscripciones `rosa topic echo --once`, timeout acotado y
  `ROS2CLI_DISABLE_DAEMON=1`. Primer intento reliable no devolvió joints;
  el segundo best_effort sí. No se concluye avería por aquel timeout.
- `/mc/whole_joint_states`: sello 1788778151.229195028
  (12:49:11 Madrid); `/mc/joint_states`: 1788778153.870173656.
  Los 14 ejes de brazos tienen |q| <= 0,000958738 rad y velocidades
  reportadas cero. Cabeza pitch -0,002780340 rad. Son muestras puntuales,
  no certificación de HOME ni prueba de ausencia de contacto.
- FT izquierdo: sello 1788778156.541187366, fuerza
  [33,9048; 9,0090; -9,5566], torque [0,0736; -0,9392; -0,2456].
- FT derecho: sello 1788778159.201173166, fuerza
  [27,7576; -2,9286; 29,4105], torque [-0,2868; -0,8096; 0,5697].
  Ambos son WrenchStamped, frame_id `force_torque_sensor_controller`.
  No se verificó tara, compensación gravitatoria, transformación física
  de ejes ni umbrales activos. No interpretar estos valores como fuerza
  de contacto ni como prueba de normalidad. Muestras secuenciales, no simultáneas.
- PC: ubt-controller active/running, UI de usuario inactive. Log pasivo
  de backend a 12:48–12:49 muestra cero clientes WebSocket.
  Esto NO demuestra publisher en STOP ni ausencia de otros mandos.
- Vision: última transición visible de Control Center:
  SelfChecking -> JoystickMode a 18:33:42.751611 +08:00.
  Log posterior hasta 18:49:21 no muestra otra transición en la ventana
  consultada. Es evidencia de log, no respuesta transaccional de modo actual.
- `/mc/teleoperation/enable` y `/mc/sdk/robot_state` no dieron muestra en
  el primer timeout. Ausencia de mensaje no significa false/inactivo.
- CameraInfo estéreo izquierda no entregó muestra en consulta desde Motion.
  No se capturó imagen ni se estableció sincronización imagen-articulaciones.

## PENDIENTE y punto de reanudación

La disponibilidad de joints y FT permite preparar un registro diagnóstico,
pero no reemplaza límites/control de fuerza en el controlador. Falta resolver
captura de imagen con sello y correspondencia temporal, estado de control
demostrable y geometría de montaje. No deducir montaje del esfuerzo estático.
No se necesita repetir las cotas A–F/T ni fotos generales ya suministradas.
No usar movimiento exploratorio ni un retorno inverso como garantía de seguridad.

Cambios persistentes: únicamente documentación local; sin cambio robot/PC.

## Continuación: cámara disponible, sincronización aún no demostrada

OBSERVADO 07-09 aproximadamente 12:53–12:54 Madrid, sólo suscripciones:

- Contenedores Vision redescubiertos. CameraInfo recibido desde
  `walker-stereo.stereo_depth_estimation-1`, topic
  `/sensor/camera/stereo/color/info`, QoS transient_local. Resolución 960×576,
  frame stereo_left_rectified_optical_frame; fx=fy=383,1236026,
  cx=476,1841125, cy=192,6788712. Sello cero: calibración retenida, no reloj
  de fotograma. Los timeouts anteriores de otro topic/QoS no prueban cámara caída.
- `/sensor/camera/stereo/color/raw`: Image2m, un writer, best_effort,
  volatile, depth 5. Mensaje completo recibido y procesado descartando píxeles
  de la salida; bgr8 (longitud explícita 4), step 2880, 960×576.
  Primer sello 1788778379.137487000. No se guardó ni inspeccionó imagen visual.
- Segundo ensayo con ambas consultas lanzadas concurrentemente: joints
  1788778413.290172079, imagen 1788778414.578540000: diferencia
  1,288367921 s. No es un par sincronizado. Los tiempos de lectura remota
  fueron 1788778413.398267 y 1788778414.8937528 respectivamente;
  las diferencias incluyen transporte/serialización, no son latencias del sensor
  ni prueba de sincronización de relojes entre hosts.
- Esta segunda muestra articular vuelve a reportar velocidades cero y las
  mismas posiciones. No habilita movimiento ni resuelve el registro del útil.

Punto siguiente: buffer temporal de muestras articulares y emparejamiento por
sello de cada imagen, con desfase explícito y rechazo si no hay correspondencia;
comprobar antes la referencia de reloj entre Motion/Vision. No usar la hora
de llegada SSH ni el sello cero de CameraInfo como sustitutos. La cámara de
cabeza tampoco garantiza que el montaje de ambas muñecas esté en su campo visual.
