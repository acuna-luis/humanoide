# HOME general: captura pasiva y progreso independiente

**2026-09-11 — H02 PICO con torso recto → HOME 4×, ensayo cerrado.**
Preflight exacto y referencia `pico_body_zero` reconocida; una acción supervisada
`cruzr/pico_to_home_open_v2_4x`, XML SHA `6dd482a7…`, 20s nominales.
Motion SUCCEED/4, 2.103 muestras válidas, cero fallos/deshabilitados; velocidad
máxima observada0,243997rad/s y HOME final0,00297209rad máximo, velocidad0.
El operador confirma «resultado ok, suave y sin contacto, libres, sigamos».
Se valida este caso observado; no retorno general, cuerpo flexionado, carga,
posturas asimétricas ni frenado. No se instaló, recargó, reinició o cambió modo
ni protección. Próximo paso: captura de una postura asimétrica habitual, sin
mandar un retorno hasta revisarla. Ejecutores intactos; confirmación por chat
para esta acción supervisada, sin simular la confirmación de terminal.
ANL-01/MOT-02; evidencia `../Humanoide-vla-evidence/20260911T084247Z_H02-PICO-SUPERVISED/`.
[Resultados y receta](CRUZR_HOME_ENSAYOS_SUPERVISADOS.md).

**2026-09-11 — Ensayo H01 desde HOME ejecutado bajo supervisión.**
Con preparación física confirmada y preflight aprobado se envió una sola
acción `cruzr/home`, XML instalado open_v3_20s SHA `05174d2b…`, desde HOME
medido: apertura lateral de brazos bajos y cierre. Motion `SUCCEED/status=4`;
2.103 muestras válidas, sin fallos de servo ni deshabilitados, velocidad máxima
observada 0,247139 rad/s. Lectura final HOME máximo 0,00278034 rad y velocidad0.
Paros0/0 sin transición: no se midió frenado. El operador confirmó después «suave sin contacto»: H01 cerrado para el caso
ensayado. No se aprueba retorno general ni nuevas velocidades.
Sin instalación, recarga, reinicio, modo o protección modificados. La primera
preparación abortó por formato YAML antes del envío y se conservó; después de
corregir el lector se repitieron los controles, sin reintentar movimiento.
ANL-01; evidencia `../Humanoide-vla-evidence/20260911T082510Z_SUPERVISED-HOME-PREPARATION/`.
[Caso, receta y alcance](CRUZR_HOME_ENSAYOS_SUPERVISADOS.md).

**Ampliación posterior del mismo día: arranque hasta HOME y captura articular
real en reposo VERIFICADOS.** Después de confirmar la preparación física, el
usuario liberó el paro: CC pasó self-check/StartMotion y llegó a AutoTaskMode.
La lectura independiente confirmó veinte actuadores sanos/habilitados, HOME
máximo0,003068rad y velocidad0. Confirmación visual posterior pendiente.
La captura inicial de movimiento falló por el formato ROSA; corregida y probada
después en reposo (252 muestras, paros0/0, sin errores). No se reconstruyó el
movimiento perdido ni se midió frenado. Evidencia nueva:
`../Humanoide-vla-evidence/20260911T062619Z_BOOT-AFTER-CONFIRMATION/`.

**2026-09-11, Europe/Madrid. VERIFICADO: software local y lectura de paros.
PENDIENTE: ejecución física general.** No se instaló ni recargó una trayectoria,
no se reinició el robot y no se liberó ni rearmó ningún paro.

## Resultado y situación del arranque

Se recuperó la conexión Wi-Fi y se descubrieron los contenedores actuales de
Motion y Vision, v0.2.0. El registro de este arranque de Control Center llegó a
`WaitEStopRelease`; la captura pasiva de ocho segundos leyó paro principal `1`
y paro de servo `0`, dos mensajes de cada uno. No recibió estados de actuadores.
La lectura anterior del servidor de manipulación devolvió cero servidores.
Esto describe ese arranque bajo paro, no acredita una avería ni un estado actual
permanente. El usuario confirmó que todavía no había liberado el E-stop.

Para esta revisión de archivos/código no es necesario liberarlo. Para obtener
telemetría articular funcional y realizar después un ensayo, hay que completar
el arranque conforme a la [guía v0.2.0](../guides/CRUZR_V020_BOOT_GUARD.md).
Liberar el paro puede permitir el HOME interno: la captura pasiva no intercepta
ese HOME y no lo convierte en un retorno aprobado desde cualquier postura.
En esta intervención no quedó confirmada la postura física actual ni se preparó
un recorrido general que haya superado todos los requisitos para ensayarlo.

## Comprobación nueva del recorrido

`Validator.independent_progress(a,b)` comprueba todo el producto cartesiano
de los intervalos articulares de una etapa, incluyendo situaciones en las que
un eje se retrasa o se detiene mientras otros avanzan. Cada articulación puede
estar en cualquier posición entre sus dos extremos; no se supone un reloj o
porcentaje de avance común entre brazos, cabeza, elevador y cintura.

Usa las mismas distancias y cotas de desplazamiento por par del planificador.
Una subdivisión divide **un intervalo articular** en dos cajas, conservando el
resto de intervalos completos. Se rechaza cualquier contacto, margen insuficiente
o región sin demostrar al agotarse profundidad/tiempo. No se sustituye por una
malla de muestras. La prueba de regresión incluye una diagonal libre que colisiona
si los dos ejes progresan con desfase: el certificado anterior acepta la diagonal
y el nuevo rechaza correctamente la caja de progreso independiente.

`cruzr_plan_home.py --plan` aplica esta comprobación a las candidatas, con el
escenario de incertidumbre ya declarado: 5° por eje, hasta 40 mm axiales por
abrazadera, 2 mm por pieza y 2 mm nominales. Informa
`independent_joint_progress.separated` y sus impedimentos. Este análisis tiene
su propio presupuesto `--timeout`, además del de búsqueda y error afín.
No es una cota total de tiempo de proceso.

Una aceptación demuestra separación en esas cajas del modelo y con esos
márgenes. **No demuestra** que el controlador real permanezca en ellas, ni
acredita velocidad, sobrepaso de extremos, frenado o estabilidad. Los informes
siguen con `physical_approval=false` e `installable=false`.

La auditoría actual del CAD conserva **54 conflictos de geometría/margen por
referencia HOME/PICO**, once envolventes y todos los pares ya descritos en
[la revisión geométrica](CRUZR_HOME_GEOMETRIA_Y_MOTION.md). No se modificaron
originales, superficies ni exenciones. El nuevo comprobador no cierra por sí
solo esas interfaces internas del montaje.

## Capturar datos sin ordenar movimiento

Desde la raíz del repositorio, elegir una carpeta nueva fuera de Git:

```bash
python3 scripts/teleoperation/capture_home_motion_trace.py \
  --seconds 10 --output-dir ../Humanoide-vla-evidence/ensayo-home-01

python3 scripts/teleoperation/analyze_home_motion_trace.py \
  --input ../Humanoide-vla-evidence/ensayo-home-01/trace.jsonl \
  --output ../Humanoide-vla-evidence/ensayo-home-01/analysis.json
```

El primer comando **sólo escucha**. No inicia una trayectoria, no la detiene,
no cancela acciones y no es un watchdog. No utilizarlo como capa de parada ni
liberar el E-stop para conseguir que su resultado cambie de estado.
Un ensayo posterior requiere su preparación propia; esta receta no lo autoriza.

El PC descubre contenedores y envía el programa lector por stdin a Python del
host Motion. No instala archivos ni paquetes en el robot. Usa la credencial
privada existente de `cruzr_recover_to_home.sh`; no incorpora claves en el código.
Suscribe únicamente:

| Topic | Cliente | Datos y unidades |
|---|---|---|
| `/mc/actuator_state` | ROSA nativo en manipulación | Veinte articulaciones, posición rad, velocidad rad/s, `cmd_pos` rad, marcas temporales, status/error |
| `/emb/estop_key_state` | ROS 2 en contenedor ROS | Estado observado `0/1` del paro principal |
| `/emb/servo_estop_key_state` | ROS 2 en contenedor ROS | Estado observado `0/1` del paro de servo |

Se eligió ROS 2 para los paros porque ROSA nativo devolvía errores de lectura DDS
en esos topics. El primer intento quedó archivado como fallido; no se interpretó
su texto como una muestra. La segunda captura recibió ambos paros sin errores.
La primera captura después de liberar descubrió que `--print-compact` nativo
produce texto `act_item:[...], header:{...}`, no JSON. Se conserva como fallida.
El lector corregido usa la salida JSON multilínea por defecto, enmarca cada
objeto completo y sólo entonces lo interpreta. Se contrastó con una muestra
real de22actuadores (20de cuerpo y2ruedas) y con252muestras en reposo. El ensayo
de seguimiento durante movimiento sigue pendiente.

El lector registra el reloj monotónico del host para las tres suscripciones.
Admite entre 1 y 120 s, más un máximo de0,5s para completar un objeto en curso
al cierre; un stream que no lo complete se rechaza. Limita volumen/línea y
coloca un `timeout` **dentro de
cada contenedor**, de modo que una caída del cliente SSH no deje una suscripción
indefinida. Esos timeouts terminan únicamente lectores; no detienen Motion.
La carpeta PC se crea privada, con captura, stderr, descubrimiento, fuente
remota enviada, metadatos y SHA256. No sobrescribe carpetas existentes.

## Qué calcula y qué no permite concluir

El analizador exige veinte ejes, ID/alias único, datos finitos, marcas de origen
no nulas y progresivas, reloj de recepción monótono y stream completo. Informa
huecos, retraso entre marcas de actuadores/cabecera, errores de servo y estados
deshabilitados. Rechaza también una captura que termina con datos articulares
antiguos después de haberse silenciado el stream.

Por articulación registra velocidad máxima observada, rango de posiciones y
error respecto a `cmd_pos`. La definición del proveedor dice expresamente que
`cmd_pos` es la **última consigna solicitada sin límites aplicados**: no debe
presentarse como consigna final entregada al servo.

Si observa una transición de paro `0→1`, calcula recorrido articular muestreado
entre la muestra previa y las posteriores, y los huecos alrededor del evento.
No conoce el instante físico en que se pulsó, la latencia del topic ni movimiento
entre muestras. Ese recorrido **no es una cota superior de parada** y una prueba
no califica todos los estados/cargas/velocidades. No acredita sincronización
absoluta de relojes ni frescura absoluta de la fuente. No genera autorización.

| Resultado | Interpretación |
|---|---|
| Captura: código 0 | Stream completo con actuadores y ambos paros; falta analizar calidad y alcance |
| Análisis: código 0 | Observaciones numéricas disponibles; `physical_approval=false` |
| Código 3 | Faltan datos o el stream no satisface las comprobaciones; conservar evidencia |
| Código 2 | Error de argumentos/archivo/formato/transporte previo a la captura |

Con el E-stop pulsado se obtuvo código 3 por **cero muestras de actuadores**.
Los valores de ambos paros se conservaron correctamente. No se inventó HOME,
PICO, velocidad cero ni permiso a partir de esa ausencia.

## Contrato nativo: hallazgos que condicionan el ejecutor

Se copiaron nueve archivos de runtime y se inspeccionaron símbolos, sin cargar
bibliotecas ni invocar control:

- `json_control/joints_control_cruzr.xml` usa MetaClamp. Su perfil absoluto
  `meta_clamp/json_control/cruzr/joint_json_absolute_control.yaml` contiene
  `enable_self_collision_check: false` y
  `enable_abnormality_determination: [none]`, y deshabilita cintura/elevador.
  **No se utiliza como adaptador HOME ni se modificó.**
- `librobot.so` contiene `GeometricPrimitiveSet`, cápsulas y funciones de
  colisión de cuerpo/cabeza y grupos. Los símbolos apoyan que existe una
  representación nativa distinta del CAD triangular; no proporcionan por sí
  solos dimensiones/cobertura o una lista válida de contactos permitidos.
  La búsqueda acotada no encontró un SRDF o configuración suficiente para
  cerrar esas interfaces. No se afirma haber descartado todo archivo posible.
- `rosa action --help` ofrece list/info/type/send_goal, sin comando cancel.
  No se verificó una cancelación física ni watchdog local apropiado. Terminar
  el proceso `rosa`/SSH no equivale a frenar el robot. No se improvisó un
  rearme, StartMotion, cambio de modo o servicio de servo como sustituto.

El ejecutor general, su supervisor y la integración del HOME de arranque siguen
pendientes. Los perfiles operativos existentes de 20 s no se ampliaron a nuevas
posturas. El siguiente paso para geometría es cerrar la especificación de las
interfaces internas/cobertura; para ejecución, verificar el despacho y mecanismo
local de parada con la ruta y dominio concretos antes de un ensayo físico.

## Verificación, evidencia y reproducción

**Verificación:** se ejecutaron41pruebas del planificador y38regresiones
PICO/adaptación/optimización. Tras corregir el formato se ejecutaron15pruebas
del lector/análisis (94casos en total), incluyendo lectores simulados que
terminan después del corte y streams que se atascan. Auditoría completa CAD
terminada. Capturas reales bajo E-stop y después en HOME: la última contiene
252muestras válidas, hueco máximo22,875ms y diferencia máxima de marcas
actuador/cabecera0,127ms. No se midieron seguimiento dinámico o parada físicos.

```bash
.venv/general-home/bin/python -m unittest discover -s scripts/teleoperation -p test_general_home.py -v
python3 -m unittest discover -s scripts/teleoperation -p test_home_motion_trace.py -v
```

Evidencia y backup PC privados:
`../Humanoide-vla-evidence/20260911T054510Z_GENERAL-HOME-COMPLETION/`.
Incluye `before/`, `before.sha256.json`, `runtime-manifest-complete.json`,
`model-audit.json`, ambas capturas (fallida inicial y lectura corregida),
`passive-under-estop-v2-analysis.json` y `verification-tests.json`.
Los logs del robot muestran su hora configurada; las horas de las consultas
están registradas en UTC del PC, sin equipararlas automáticamente.
Registro reproducible y reversión selectiva: ANL-01 en
[SYSTEM_CUSTOMIZATIONS.md](../SYSTEM_CUSTOMIZATIONS.md#anl-01--comparación-y-planificación-offline-de-geometría-y-tiempos).
