# Ensayo frontal SPS: rechazo de agarre y pérdida de comunicación

**22-09-2026 10:10 CEST — Prioridad del operador: resolver el agarre frontal.**
No se necesita anular protecciones; el candidato de navegación queda sin instalar
ni activar y su investigación se aparca. Revisión de la tarea y del rechazo:
[alcance y trayectoria de agarre](#revision-centrada-en-el-agarre-22-09-2026).
El diagnóstico de la primera orden de retroceso queda documentado aparte en
[ArcPrecise](../box_handling/ARC_PRECISE_ARRANQUE_20260922.md).


**2026-09-22 09:55 CEST — Ensayo5cm interrumpido por retroceso; robot detenido en HOME.**
Operador confirmó espacio frontal/apoyos libres, ruedas en navegación y persona
junto al paro. Se cargó utars_nav_map y relocalizó: NAVIGATION_READY; durante
esta preparación la cabeza volvió cerca de HOME, observado antes de navegar.
Un único objetivo5cm al frente (27028c333b0c450ea296ff577d3c38bc) generó retroceso.
El monitor solicitó navigation_stop al medir−5,11mm; petición aceptada status4.
Postlectura: desplazamiento−7,503mm, velocidad0, HOME20D sin faults, máximo
0,000959rad. No avance5cm, agarre, reintento ni segundo movimiento de cabeza.
Log del proveedor: MPPI tolerancia0,3m→ArcPreciseController, allow_backward=true;
objetivo delante5cm, x_tilt−0,05 y salida x−0,04m/s. Causa completa/contrato del
controlador PENDIENTE; no invertir signos ni forzar parámetros a ciegas.
Herramienta nueva front_nudge.py queda bloqueada para --run; --check sólo lectura.
Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260922T073932Z_FRONT_REACH_RECHECK`.

**2026-09-22 09:46 CEST — Caja frontal confirmada; cabeza preparada, sin agarre.**
Tras «adelante» y condiciones físicas confirmadas en el arranque, se ejecuta
únicamente `--prepare-vision --yes`: cabeza0/−0,43rad en2s,
goalc68f5d5e-45b9-4ff6-9ac7-a3c9d01ac807 SUCCEED/status4. Preflight correcto.
Postlectura20D sana, inmóvil; pitch−0,430473rad y brazos próximos a HOME.
Dos detecciones con TF exacta eligen índice1, la caja frontal baja, frente a
la lateral alta: X0,800744/0,798246m; Y0,105542/0,106856m;
Z0,383803/0,382768m. Selección correcta y estable≈3mm; X en el borde0,8m
del proveedor. Esto no valida IK ni espacio entre cajas.
Mapa vacío/FSM_WAITSETMAP tras encendido; no hay pose de navegación actual.
Propuesta de ensayo: avance recto5cm y nueva medición, conservando límites;
requiere preparar localización/control y confirmar espacio de chasis/apoyos y
ruedas en navegación. Confirmación solicitada y PENDIENTE. Sin avance ni agarre.
Cabeza queda bajada; no HOME automático.
Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260922T073932Z_FRONT_REACH_RECHECK`.

2026-09-22, Europe/Madrid. **VERIFICADO por logs; recuperación de comunicación
y agarre PENDIENTES.** Diagnóstico del agente sólo lectura remota, sin nuevas
tareas, movimiento, instalación, reinicio o cambios de límites/prioridades.

## Resultado y secuencia

El operador ejecutó `force_escenario1.sh`, paquete `a66aa93932ef9bdb`.
El descubrimiento SPS corregido pasó con ambos endpoints ausentes. Preparó
mapa/localización y llegó a get1: dos muestras de5,3mm y0,351°. Esto verifica
llegada al waypoint, no alcance físico de la caja.

La tarea `local_front_box/separate_right_cruzr` **sí llegó a Motion**, aunque
el cliente no imprimió Goal accepted ni resultado antes de abortar. Goal UUID
reconstruido del estado ROS2: `7b5767c6-7319-425d-9ae8-e8ea78b0882c`, status6.
Los MetaMove preparatorios de cabeza/brazos precedieron a MetaClamp. No debe
interpretarse el fallo del cliente como ausencia de movimiento durante el ensayo.

Tiempos UTC de Docker (el texto interior Motion muestra UTC+8):

| UTC | Hecho verificado |
| --- | --- |
|06:42:31.140|Empieza el árbol frontal en Motion.|
|06:42:35.690|Empieza MetaClamp tras preparar cabeza y brazos.|
|06:42:36.795–36.825|Adaptador selecciona candidata1 de4; Motion recibe esa pose por SPS.|
|06:42:36.836|X_BaseBox excede X máximo; continúa comprobación IK del proveedor.|
|06:42:38.333|IK falla; no encuentra postura de las manos.|
|06:42:38.334–38.336|RouDi retira cuatro runtimes por heartbeats ausentes1612–1755ms.|
|06:42:38.413|MetaClamp termina `ClampBoxOutOfReach`; árbol FAILURE.|
|06:42:38.530|Cliente ROSA Python PID2441 aborta con `POPO__CHUNK_LOCKING_ERROR`.|
|06:42:44.555|Adaptador SPS PID2039 aborta al cerrar un suscriptor, mismo error Iceoryx.|

El aborto de transporte ocultó en la terminal el rechazo de agarre que sí
consta en Motion. No fue un timeout de45s ni un fallo del descubrimiento SPS.
No se ejecutaron retirada, navegación put1, depósito o HOME tras el rechazo.

## Selección y pose consumida

`selection.jsonl` contiene detección y selección de la misma captura
stamp1790059356.372785000; índice1 de4, bearing7,670°.
Pose original cámara[-0,079699224;0,750455715;1,055247894]m,
cuaternión XYZW[0,848783703;−0,004980253;−0,007105500;0,528669021].
El log `GetSelectedVisionPose` y `X_CameraBox` coincide con esa pose y
orientación redondeadas: XYZ[-0,0797;0,7505;1,0552], RPY[2,0274;0,0068;−0,0160].
**Queda demostrado el consumo SPS por MetaClamp en esta ejecución**, ampliando
las pruebas MetaLook previas. No implica que el agarre haya funcionado.

El selector estima base_link[0,801366;0,107923;0,382920]m con TF del instante.
Motion usa su propia cinemática y obtiene
`X_BaseBox=[0,803542;0,104953;0,389692]m`, frente a X permitido[0,4;0,8].
Exceso3,542mm en X, junto a fallo IK (`IK001/IK101`, `IK failed for eef poses`).
No convertir ese exceso en una orden de avanzar4mm ni ampliar el límite:
ambos chequeos fallaron. Z es coordenada estimada del objeto, no una medición
presencial de la altura del soporte ni prueba de que esa caja sea inalcanzable
bajo cualquier trayectoria.

La imagen guardada **de esa captura**, `current-grasp.jpg`, sitúa la etiqueta
[-0,080;0,750;1,055] sobre la caja frontal baja a la derecha de la pila alta.
La selección ya no usa la primera caja lateral alta del detector. La imagen
histórica no certifica espacio libre, ausencia de contacto o estado presente.

## Comparación solicitada con el éxito anterior

El operador confirma que esta caja ya se recogió sin laterales, está apoyada
sobre otras dos cajas y pide no repetir mediciones. Se conserva esa información;
no se le prescribe cambiar alturas ni retirar laterales como solución definitiva.

El éxito archivado localizado del21-09 a18:26 (hora interna Motion) registra
`Singapore/separate_right_cruzr` y `separate_bodyback_cruzr` SUCCESS.
Su `X_BaseBox=[0,7876;0,1016;0,5997]m`, cámara[-0,0770;0,5660;0,9537]m.
Frente a ese registro: ahora X+15,942mm, Y+3,353mm y Z−210,008mm.
`X_WCamera` es prácticamente el mismo en ambos registros. Las imágenes guardadas
muestran disposiciones de escena distintas. **No está establecido que sea el
ensayo concreto al que se refiere el operador ni el mismo montaje**; no usar
esa diferencia para negar su experiencia o afirmar que ahora deba elevar la caja.

La revisión estática existente muestra conversión pose→RigidTransform en la
ruta ordinaria y convergencia de ambas rutas en la conversión cámara/cuerpo.
En esta ejecución la pose del detector sí coincide con la entregada a Motion;
no se encontró una pose base enviada por error como cámara. No se ha demostrado
la causa completa de la diferencia de alcance/detección entre ensayos.

## Estado posterior e Iceoryx

El usuario confirma robot inmóvil, caja apoyada, abrazaderas vacías y sin
contacto. JointStates ROS2 posterior stamp1790059606.382006726:22 velocidades0;
brazos en postura preparatoria (hombro yaw≈±1,908rad), cabeza pitch−0,430665rad,
torso próximo a0. **Fuera de HOME**. Ambos paros leídos0/0; acción status6.
`/mc/actuator_state` nativo agotó8s (rc124, sin muestra): no queda verificado
estado completo de servos, faults ni discrepancia posición/consigna.

Motion/ROSA/IMU/RouDi permanecen running, RestartCount0, OOMKilledfalse;
no repetir la interpretación del incidente del16-09, donde sí reiniciaron.
Procesos del adaptador y shell de ciclo ya no aparecen en el inventario Motion;
la sesión conserva `stop`. RouDi sigue recibiendo Keepalive de dos runtimes
retirados del PID65. **Que robot_app siga vivo no demuestra comunicación sana.**
RAM disponible4181MiB, /dev/shm64%, swap0: lectura posterior, no exclusión de
presión puntual. Hilos de trabajo Motion SCHED_FIFO70 y KeepAlive SCHED_OTHER
observados después; falta demostrar por qué perdieron heartbeat. Coincide
con el cálculo IK, pero no se atribuye causalidad a CPU, GIL o SPS sin medición.

No repetir ciclo, HOME o reinicio a ciegas desde esta postura. Primero recuperar
comunicación con procedimiento compatible con robot fuera de HOME y verificar
salud/consignas. No borrar /dev/shm, desactivar watchdogs, elevar prioridades ni
ampliar timeouts como supuesto arreglo. Después contrastar una detección actual
con el ensayo físico pertinente y validar alcance de la recogida frontal.

## Evidencia, cambios y reanudación

Evidencia externa con SHA256SUMS, original del operador, logs completos, sesiones,
consultas, imágenes originales con rutas de procedencia y backups documentales:
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260922T064454Z_FRONT_SPS_ICEORYX`.
Referencia exitosa: `../Humanoide-vla-evidence/20260921T104034Z_SEPARATE_NEIGHBOR_DIAG/motion.log`;
se conserva copia y extracto para no depender de rotación remota.

Sólo se modifican documentos PC: este informe y enlaces/estado de las fuentes
global, especializada, integración, mapa y ficha BOX-01-FRONT-SPS. Paquete,
wrappers, fuentes Python, configuraciones, servicios y parámetros intactos.
Reversión documental selectiva con `before/`; no hay rollback remoto de esta
intervención. Verificación: correlación de logs, UUID/status, pose de selección,
lecturas de sólo consulta y `git diff --check`; no se ejecutan pruebas físicas.
Punto de reanudación: salud de comunicación y comparación de detección/alcance;
**selección consumida por MetaClamp verificada, agarre frontal fallido**.


## Continuación: mensaje UBTECH y ensayo sin SHM

El proveedor recomienda CycloneDDS sobre los logs del18-09 aportados por el
usuario. Nueva lectura demuestra que Motion ya usa cyclone; se identifica y
prueba `ROSA_USE_SHM=OFF` sólo en cliente temporal. Descubrimiento correcto,
actuator_state sigue rc124. No se ha aplicado a servicios ni recuperado Motion.
Se preparó la interfaz de apagado sin llamarla; usuario dispone de medios de
aseguramiento, no confirma todavía brazos asegurados/apagado.
[Informe, receta, evidencia y pendientes](../support/CRUZR_CYCLONE_SIN_SHM_20260922.md).


## Revisión centrada en el agarre — 22-09-2026

Petición actual: centrarse en coger la caja, sin anular controles. Se aparca la
modificación de navegación y no se envía ninguna tarea ni movimiento nuevo.
Se revisan el log original de 06:42 UTC y el YAML/XML de la tarea que ejecutó
la variante frontal, cuyos hashes son dependencias de la integración SPS.
No se han obtenido poses nuevas en esta revisión; se conservan las dos
mediciones anteriores y la pose que consumió Motion durante el fallo.

**VERIFICADO:** la caja frontal correcta llegó a MetaClamp. El rechazo ocurre
al construir/comprobar la trayectoria, antes de ejecutar su agarre. Los MetaMove
preparatorios sí habían ocurrido. El log no atribuye este rechazo a contacto
con cajas laterales. Eso no certifica que la trayectoria esté libre de ellas.

- Pose consumida: X0,803542/Y0,104953/Z0,389692 m; X supera el intervalo
  configurado por 3,542 mm. El proveedor registra explícitamente que continúa
  con el chequeo IK después de ese primer rechazo. El error final indica que
  fallaron **ambas** comprobaciones; no diagnosticar sólo un límite rectangular.
- Mano izquierda, punto VISION con offset: [0,52525;0,20636;0,386347] m.
  Punto original de pinzado izquierdo: [0,8102;0,4064;0,3863] m.
- Mano derecha, punto VISION con offset: [0,7968;−0,2465;0,3930] m.
- La búsqueda de postura registra diez candidatos de torso y errores
  `Cannot find matched IK001/IK101`, terminando en `CheckIkSolved` fallido.
  Es evidencia de fallo de esa búsqueda, no demostración matemática de que
  cualquier agarre de la caja sea imposible. Tampoco valida acercarse 4 mm.

**Trayectoria revisada:** `wrc/separate_right_cruzr.yaml` usa `task_type:
separate_box`; no es una recogida simétrica genérica. Introduce distintos
puntos VISION para cada mano, una traslación de módulo 6 cm y un giro de 20°
para la derecha en `CURRENT_RELATIVE`, etapas `SEPARATE_ABSOLUTE` y cierre
posterior de la izquierda. No interpretar esos 6 cm como una bajada vertical
en el mundo sin resolver la convención de transformación. El fallo ocurrió
antes de ejecutar esa secuencia de agarre.

Siguiente trabajo de agarre: contrastar las poses de ambos efectores y la
búsqueda de postura con el perfil de separación para esta caja baja y apoyada,
conservando selección frontal, límites y controles de fuerza. La alternativa
clamp genérica existente tiene otra trayectoria; **no se ha demostrado** que
pueda entrar entre las cajas laterales ni se ha intercambiado por la tarea
actual. Antes de un nuevo ensayo hará falta pose reciente y espacio real de
entrada; no pedir al operador repetir medidas manuales ya descartadas.
No marcar el agarre corregido ni repetir `force_escenario1.sh` por este análisis.

Evidencia adicional de esta revisión y backup documental:
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260922T080049Z_ARC_PRECISE_DIAG`.
Fuentes originales del rechazo conservadas en la evidencia06:44 citada arriba.
Sin cambios de YAML/XML instalados, scripts de ciclo, parámetros ni runtime.
