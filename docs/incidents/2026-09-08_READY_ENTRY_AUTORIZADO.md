# HOME→READY→ENTRY autorizado y ejecutado

**08-09, observación posterior del propietario:** señala inclinación del torso
muy pronunciada y aporta fotografía. OBSERVADO: postura visual inclinada;
no confirma aceptación física de ENTRY ni estabilidad/ausencia de contacto.
La ejecución y el gate articular siguen verificados, pero la idoneidad de esta
postura queda PENDIENTE de revisión antes de avanzar con fixture/shadow.
El XML solicita lifter_pitch_1 = −0,834773 rad (−47,83°) y lifter_pitch_3 =
0,291265 rad (16,69°): son ángulos articulares, no medición del torso respecto
al suelo. La fotografía no demuestra el estado físico actual ni las holguras.
No se ha enviado movimiento ni modificado el objetivo por esta observación.

Fecha: 2026-09-08. Estado: VERIFICADO por Motion y telemetría; confirmación
visual posterior del operador PENDIENTE. Última postura medida: ENTRY.

## Autorización y preflight

El propietario pidió «ejecuta READY y ENTRY» y confirmó las condiciones físicas
para ambas etapas: abrazaderas vacías, estabilidad/sin contacto, zona libre,
cargador desconectado, ruedas bloqueadas, ambos paros liberados, ningún otro
mando y persona junto al paro. Se advirtió que ENTRY aún no se había ensayado y
que las cotas offline no garantizan holgura/dinámica reales. La revocación previa
del bloqueo por el propietario se aplicó a estas órdenes concretas.

Preflight de lectura PASS: contenedores/endpoints redescubiertos, HW clamp v1,
ambos paros 0, cargador 0, baterías 61,7 % y aproximadamente 84,1–84,3 %,
actuadores habilitados, un servidor ArmTask, VLA detenido y writers 0.
HOME inicial 20D máximo 0,002684 rad y velocidad 0. ENTRY instalado cotejado
exactamente con el XML local revisado; tareas/hashes comprobados.

## Ejecuciones únicas y resultados

- HOME→READY: `s2_bio_vla/s2_vla_pick_large_teleop_ready`, goal
  `2d93c73a-f9d7-4f2d-98f1-0544e54f7deb`, SUCCEED/status=4, state=1101001.
  Gate intermedio READY PASS: error brazos 0,001938 rad, cuerpo en referencia,
  velocidad 0 y actuadores sin fallos.
- READY→ENTRY: `s2_bio_vla/s2_vla_e6_1c_ready_to_entry`, goal
  `b288893a-86cc-45b9-a74b-6103ac147f11`, SUCCEED/status=4, state=1101001.
  XML de 12 s comanda seis ejes de cabeza/elevador/cintura, sin objetivos nuevos
  para brazos. Error máximo 20D respecto a episode_000040/frame 0:
  **0,003834951 rad**, inferior a 0,01; velocidad final **0**.
  Veinte actuadores habilitados/sin fallos; delta máximo consigna 0,003835 rad.

Captura pasiva iniciada antes de ENTRY: 13.756 mensajes, 27,509961 s, hueco
máximo 0,002095 s; primer estado READY y último ENTRY. Pico de velocidad
reportada 20D **0,107861348 rad/s**, inferior al límite provisional de 0,15.
Variación máxima de brazos desde primera muestra **0,000766990 rad**.
Aceleración, frenado y equivalencia con ley quintic no validados. No es
certificación de dinámica/geometría ni prueba general de ausencia de contacto.
El servicio de cancelación se descubrió; no se invocó. Captura pasiva sin
cancelación automática; ningún monitor persistente queda activo. Timeout 30 s
de la captura devuelve 124 intencionadamente; ambas acciones devuelven 0.

## Estado, cambios y reanudación

VERIFICADO: robot en ENTRY inmóvil según muestra final; VLA control/inference
exited/restart=no, RobotCommand writers 0/readers 2. Sin nuevas modificaciones
de software/configuración remota, sin desactivar protecciones, sin reintentos,
sin retorno automático. Los wrappers antiguos conservan sus restricciones.
No se envió movimiento del checkpoint ni se colocó el fixture.

PENDIENTE: confirmación visual posterior; ENTRY→READY físico; escena actual
SUPPORTED_LOW y cinco shadow task 0/P14 (0/5). La ida y su gate 20D dejan de
ser bloqueantes técnicos pendientes de ejecución. Antes de colocar el fixture,
asegurar robot inmóvil y verificar escena conforme al plan. No inferir permiso
para VLA físico del éxito de estas dos tareas.

Evidencia externa: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260908T071800Z_OWNER-READY-ENTRY/`.
Incluye preflight, hashes/XML, claims de ejecución única, logs de acción,
estados inicial/intermedio/final y captura con resumen. Scripts auxiliares
locales de esta ejecución archivados allí; sin commit/push.
