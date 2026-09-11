# Planificador HOME desde una postura general

**11-09-2026 — Preparación directa desde robot, sin teleoperación:**
[`../cruzr_prepare_recovery.py`](../cruzr_prepare_recovery.py) integra captura
pasiva, salud/exclusividad, dos JointState canónicos y este planificador.
No usar posiciones crudas de motores como coordenadas URDF: algunos signos
son distintos. Diez pruebas pasan; en H03 permanece START_GEOMETRY_REJECTED.
No contiene ejecución, ni --run, ni cambia las restricciones de este paquete.
[Uso y alcance](../../../docs/teleoperation/CRUZR_RECUPERACION_SIN_TELEOPERACION.md).

**Actualización 11-09-2026: el cierre del modelo de interfaces sigue pendiente.**
El auditor reconstruye ahora puntos de contacto sobre ambos triángulos originales:
`contact.pos` de FCL por sí solo puede quedar fuera de la intersección.
Nuevos `audit_home_interface_sweeps.py` y `audit_native_collision_policy.py`:
el primero busca contraejemplos a exclusiones completas y el segundo traza sólo
un bucle de grupos sintéticos de una biblioteca fijada por hash. Ninguno autoriza
excepciones o ejecución. Barridos finales: 8 parejas con testigo nuevo en dominio
URDF, 4 en ±0,5 rad; no equivalen a contactos físicos. Los 54 rechazos de las
referencias siguen activos. Pasan 64 pruebas sin omitidas. Fuentes, comandos,
resultados descartados y dato mecánico pendiente en
[la guía de interfaces](../../../docs/teleoperation/CRUZR_HOME_GEOMETRIA_Y_MOTION.md#resultado-de-la-revisión-de-interfaces-11-09-2026).
No hay nuevas dependencias, instalaciones ni cambios de trayectoria del robot.

**2026-09-11, Europe/Madrid — planificador probado offline y lector pasivo probado
bajo E-stop. Integración física pendiente.**

[`../cruzr_plan_home.py`](../cruzr_plan_home.py) calcula propuestas desde veinte
posiciones articulares archivadas, con abrazaderas vacías. Conserva el estado
de cada brazo; no exige ni inventa una postura PICO. Comprueba el robot completo
y los obstáculos de la escena proporcionada. No contiene transporte al robot,
exportador XML, `--run`, instalación ni recarga.

## Preparar el PC

Desde la raíz del repositorio, con Python 3.12:

```bash
python3 -m venv .venv/general-home
.venv/general-home/bin/python -m pip install --only-binary=:all: -r scripts/teleoperation/general_home/requirements.txt
```

Las versiones probadas están fijadas en `requirements.txt`. Este entorno queda
ignorado por Git y no cambia Python del sistema. Se necesita una copia local
del paquete original `cruzr_s2_description_splint/cruzr_s2_description`, también
excluido de Git. No instalar estos paquetes Python en Motion ni Vision.

## Auditar el modelo sin postura del robot

```bash
.venv/general-home/bin/python scripts/teleoperation/cruzr_plan_home.py \
  --audit-model --output /tmp/cruzr-home-model-audit.json
```

El archivo de salida debe ser nuevo. Este modo utiliza HOME y las dos
referencias PICO **sintéticas**, sin escena. No consulta ni describe la postura
actual del robot. El JSON identifica por nombre los pares rechazados y la
representación geométrica utilizada.

Resultado con el paquete suministrado el 10-09: 45 geometrías, 982 pares internos
comprobados y ocho pares internos de conjuntos rígidos omitidos. Hay 54 pares
con solapamiento o separación menor/igual a 2 mm en cada referencia. No son
54 contactos físicos: algunas mallas representan interfaces de montaje y
11 mallas aún abiertas se sustituyen por envolventes completas que pueden rellenar
huecos. Se recuperaron siete de las 18 originales mediante separación de sólidos
cerrados y unión de grietas numéricas de hasta 10 nm, conservando los triángulos y
descontando el error medido de las distancias. De los 54 pares, 30 son invariantes
con base/ruedas fijas y 24 cambian con los ejes controlados. Todos siguen comprobados.
Es necesario terminar de resolver esa representación antes de aceptar un retorno
general en este modelo. No se excluyen automáticamente articulaciones vecinas.

Vista autónoma para revisar cada par, girar las piezas y alternar CAD original
con sólidos del cálculo:

```bash
.venv/general-home/bin/python scripts/teleoperation/render_home_geometry_review.py \
  --output /tmp/cruzr-home-geometry-review.html
```

Contiene CAD del proveedor; conservar el HTML fuera de Git. No mide la escena
real ni permite controlar el robot.

## Planificar con archivos de estado y escena

```bash
.venv/general-home/bin/python scripts/teleoperation/cruzr_plan_home.py \
  --plan --state /ruta/estado.json --scene /ruta/escena.json \
  --timeout 30 --output /tmp/cruzr-home-plan.json
```

Los ejemplos de formato son
[`cruzr_general_home_state.example.json`](../../../config/examples/cruzr_general_home_state.example.json)
y [`cruzr_general_home_scene.example.json`](../../../config/examples/cruzr_general_home_scene.example.json).
Son datos inventados para ilustrar el formato, no medidas del taller ni una
autorización. El ejemplo PICO con esa escena se rechaza en el modelo suministrado
(`START_GEOMETRY_REJECTED`, 73 pares contando los obstáculos sintéticos).

| Archivo/campo | Contenido y unidades |
|---|---|
| Estado: `schema` | `cruzr-general-home-state-v1` |
| Ambos: `captured_at`, `source` | Fecha ISO 8601 con zona y procedencia de los datos. Se informa su antigüedad; no se convierten en lecturas vivas. |
| Estado: `joint_state.name` | Exactamente los veinte nombres del ejemplo, una vez cada uno. Pueden venir en otro orden. |
| Estado: `position`, `velocity` | Veinte números JSON con punto decimal, respectivamente radianes y radianes/segundo, en el orden de `name`. No escribir grados ni unidades dentro del número. |
| Estado: `empty_clamps`, `actuators_healthy`, `controller_idle` | Deben ser `true` para analizar un retorno vacío y estacionario. Son afirmaciones del archivo, no comprobaciones independientes del robot. |
| Estado: `auxiliary_joint_positions` | Diccionario opcional de articulaciones no controladas del URDF y sus ángulos en radianes. Los ausentes se fijan a cero sólo para análisis y se señalan como impedimento para activar. |
| Escena: `schema`, `frame_id` | `cruzr-general-home-scene-v1`, `base_link`. No usar coordenadas de foto, cámara o mapa sin transformarlas al marco correcto. |
| Escena: `complete` | `true` declara que se ha incluido la escena relevante; el programa no puede comprobarlo a partir del archivo. |
| Escena: `objects` | Lista de cajas con `id` único y `type: "box"`. Incluir suelo, tablero, patas y otros obstáculos relevantes. No hay una exención automática para el contacto rueda–suelo. |
| Cada caja: `size_m`, `center_m` | Tres dimensiones positivas y centro `[x,y,z]`, en metros. Deben encerrar la pieza real. |
| Cada caja: `rpy_rad` | `[roll,pitch,yaw]` en radianes; rotación `Rz(yaw) · Ry(pitch) · Rx(roll)` que lleva la caja local a `base_link`. |

Se rechazan datos ausentes/duplicados/no finitos, nombres desconocidos, escena
sin marco, articulaciones fuera de límites y velocidades mayores de 0,002 rad/s.
No se completa una articulación controlada ausente con cero. `--timeout` limita
la búsqueda después de cargar el modelo; los análisis de incertidumbre y de
progreso independiente pueden emplear otro presupuesto igual cada uno. No es un límite total de proceso ni de
respuesta para un sistema físico.

## Cómo busca y qué significa el resultado

1. Valida entrada y HOME. Si cualquiera falla, informa el par o límite.
2. Prueba camino directo y corredores con apertura necesaria por lado, bajada
   simultánea o por brazo. Cada punto parte del estado recibido.
3. Si no encuentra corredor, usa RRT-Connect con semilla reproducible en las
   veinte articulaciones. El chasis permanece fijo en este análisis.
4. Comprueba cada tramo mediante distancias 3D y cotas del desplazamiento
   articular. Subdivide si la cota no basta; rechaza al agotar la resolución.
   No acepta un segmento sólo porque algunos puntos muestreados estén libres.
5. Elimina desvíos únicamente tras volver a comprobar el atajo. Ajusta tiempos
   a una ley quintic común `s(u)=10u³−15u⁴+6u⁵`, `q=q0+s·(q1−q0)` por tramo,
   con velocidad y aceleración cero en los puntos de paso. Revalida el camino.

Con `--timing-law cubic-rest` calcula alternativamente `s(u)=3u²−2u³`, la fórmula
numérica identificada y emulada en la biblioteca actual de Motion. Recalcula
velocidad/aceleración y declara sin cota el jerk global por los saltos de
aceleración en reposo. El certificado geométrico afín requiere el mismo progreso
en todos los ejes. Se añade un segundo certificado de la caja completa de
intervalos articulares, `independent_joint_progress`: si pasa, demuestra
separación incluso con desfase independiente entre ejes dentro de esos extremos,
con los márgenes declarados. Si falla o agota presupuesto, queda señalado;
una candidata afín no equivale a ejecución admitida. No acredita sobrepasos,
seguimiento o parada del controlador. La opción predeterminada sigue siendo `quintic`.

Las mallas cerradas usan distancias/intersecciones FCL y comprobación adicional
de contención de sólidos; las abiertas se encierran con un sólido convexo o
una caja completa. Las partes unidas por articulaciones fijas se mantienen
íntegras frente al resto del robot. Estos métodos siguen dependiendo de que
el modelo corresponda a la geometría física.

La ley temporal usa límites de diseño de 0,3 rad/s, 0,35 rad/s² y 1,5 rad/s³.
**No son límites dinámicos certificados del Cruzr ni una velocidad recomendada
para ejecutar.** Los tiempos publicados corresponden al cálculo nominal.
No se afirma optimización global ni un retorno en 20 s desde cualquier postura.
Una candidata se comprueba además con el escenario conservado de 5° por eje,
40 mm de desplazamiento axial por abrazadera y 2 mm de error por cada pieza
(4 mm combinados), más los 2 mm de separación nominal. Esta suma es una
hipótesis explícita conservadora; no una medición del error ni de la parada.

| Estado | Interpretación | Salida del proceso |
|---|---|---|
| `MODEL_AUDIT` | Auditoría terminada; puede contener conflictos | 0 |
| `GEOMETRIC_CANDIDATE` | Camino comprobado para el modelo nominal y la curva declarada | 0 |
| `ALREADY_HOME_NUMERIC` | Entrada exactamente cero y geométricamente válida; no verifica HOME físico | 0 |
| `START/HOME_GEOMETRY_REJECTED`, `START/HOME_OUTSIDE_LIMITS` | Entrada u objetivo rechazado | 3 |
| `SEARCH_TIMEOUT`, `SEARCH_EXHAUSTED`, `FINAL_CURVE_REJECTED` | No se obtuvo un camino comprobado; no demuestra imposibilidad matemática | 3 |
| Error de archivo/formato/modelo/dependencias | No hay informe utilizable | 2 |

Todos los informes llevan `physical_approval=false`, `installable=false` y
`movement_commands=0`, además de hashes de entradas, URDF, mallas y código, y
versiones de dependencias. Una candidata no debe copiarse a una secuencia
MetaMove: aún no se ha demostrado que Motion respete el dominio, los márgenes
de error y el contrato de ejecución/parada comprobados.

## Captura pasiva y análisis

`../capture_home_motion_trace.py` escucha actuadores y ambos paros, con
contenedores descubiertos y límites de tiempo también dentro del robot.
`../analyze_home_motion_trace.py` revisa veinte ejes, marcas temporales y
recorrido observado tras un evento de paro. Ninguno ordena movimientos ni
sirve de watchdog/parada. Funcionan con Python stdlib y la conexión privada
existente; no instalan paquetes en el robot.

La captura bajo E-stop leyó principal `1` y servo `0`, sin actuadores, y se
rechazó correctamente como evidencia de movimiento. Tras completar el arranque,
la salida nativa `--print-compact` resultó no ser JSON: se corrigió a objetos
JSON completos de la salida por defecto. Captura real en HOME:252muestras válidas,
paros0/0, sin errores. Las pruebas de seguimiento dinámico
y parada físicos no se han realizado. Comandos, campos, códigos de salida y
límites en [la guía de captura](../../../docs/teleoperation/CRUZR_HOME_CAPTURA_Y_PROGRESO_INDEPENDIENTE.md).

## Pendientes para mover el robot

**Actualización de interfaces, 11-09-2026:** `prism_enclosure.py` reconoce cinco
paredes prismáticas completas del tercer tramo del elevador y conserva los huecos
entre piezas mediante cierres locales. Ya está integrado en `geometry.py`;
envolventes generales11→10, sin recortar originales ni cambiar pares/márgenes.
`../audit_home_interfaces.py` diagnostica cada rechazo con las superficies
originales y testigos, sin convertirlos en excepciones. Las tres referencias
siguen con54avisos. Pasan52pruebas; no hay ensayo físico ni velocidad mejorada
acreditada. [Comandos, límites y resultados](../../../docs/teleoperation/CRUZR_HOME_GEOMETRIA_Y_MOTION.md#refinamiento-del-elevador-y-diagnóstico-de-interfaces-11-09-2026).

La auditoría `../audit_native_collision_geometry.py` extrae defaults compilados
de S2 mediante emulación aislada y compara la S2Clamp aislada con el CAD. Cinco
pruebas nuevas pasan, incluida extracción de tres bibliotecas archivadas.
Resultado aislado: hasta44,4mm de exceso bajo marcos URDF/anclaje supuesto.
La ampliación `../audit_wrist_clamp_union.py` contrasta anclajes por configuración
y emulación del código nativo: la unión con WristRoll reduce el exceso observado
en vértices a8,64mm, pero no cubre todo el CAD. `union_coverage.py` construye un
complemento local y certifica frontera/volumen del conjunto rígido de ambos lados.
Ocho pruebas nuevas pasan; `../render_wrist_clamp_review.py` genera un visor 3D
autónomo de CAD/formas nativas/complemento. No se ha integrado esa representación
en `RobotGeometry`: es amplia, no demuestra menor tiempo y no cambia pares o
márgenes. Calibración activa y montaje físico siguen pendientes; `s2_leg` no es
el elevador de Cruzr. [Recetas y alcance](../../../docs/teleoperation/CRUZR_HOME_GEOMETRIA_Y_MOTION.md#unión-muñeca-y-abrazadera-11-09-2026).

- Resolver el modelo de colisiones derivado: uniones móviles, mallas abiertas,
  cobertura, montaje real de abrazaderas y discrepancia de cabeza con runtime.
  Conservar originales y justificar cada zona de montaje por geometría;
  no convertir todos los solapamientos iniciales en pares ignorados.
- Comprobar el contrato real de trayectoria de Motion y construir su adaptador,
  con lecturas frescas, control exclusivo, seguimiento y parada local.
  Los XML actuales separan brazos/cabeza/elevador/cintura; no demuestran un
  reloj común de veinte ejes. Se ha contrastado el código numérico cúbico en
  1.312 casos mediante emulación, con error máximo de 2,67e-15 rad; no se ha
  ejecutado ni validado el despacho/seguimiento/parada real.
- Acotar dinámica, estabilidad, errores de escena/seguimiento y parada por
  dominio. Los límites de velocidad de elevador/cintura aparecen como cero en
  este URDF. Ya se han localizado límites positivos en las configuraciones
  runtime, con valores distintos entre YAML y URDF; se registran como datos de
  configuración y no como acreditación dinámica.
- Resolver también el HOME que lanza el arranque de Control Center. Este
  planificador PC no intercepta ni sustituye ese camino interno.

El perfil operativo PICO/HOME de 20 s conserva sus archivos. No se ejecutó ni
instaló una trayectoria general en esta intervención.

## Verificación y reversión

```bash
.venv/general-home/bin/python -m unittest discover -s scripts/teleoperation -p test_general_home.py -v
python3 -m unittest discover -s scripts/teleoperation -p test_home_motion_trace.py -v
```

41 pruebas del planificador y 15 de captura/análisis (94 contando 38 regresiones
operativas): desfase independiente que colisiona aunque la diagonal quede libre,
streams incompletos/estancados y datos ausentes, además de sólidos contenidos,
mallas abiertas, reparación acotada de grietas,
emulación rechazada para un binario desconocido, leyes temporales y límites,
obstáculo entre extremos libres,
obstáculo delgado fuera del punto medio, subdivisión, límites/presupuesto,
búsqueda alrededor de obstáculo, temporización, asimetría 20D, pares rígidos,
entradas incompletas y CLI sin ejecución ni sobrescritura.

Evidencia y respaldo documental anterior:
`../../../../Humanoide-vla-evidence/20260910T134348Z_GENERAL-HOME-IMPLEMENTATION/`
(ruta relativa a este directorio). Contiene `model-audit-final.json` y
`pico-example-plan.json`. Las fuentes reproducibles están en este repositorio;
el modelo del proveedor y los informes privados deben respaldarse aparte.

La ampliación de geometría y auditoría de Motion tiene su evidencia en
`../../../../Humanoide-vla-evidence/20260910T142312Z_HOME-GEOMETRY-MOTION-QUALIFICATION/`.
Incluye copias runtime, hashes, emulación, comparación de marcos/límites y HTML.
[Resultados, comandos de auditoría y alcance físico](../../../docs/teleoperation/CRUZR_HOME_GEOMETRIA_Y_MOTION.md).
Añade `unicorn==2.1.4` al entorno PC; no usa bibliotecas nativas mediante `dlopen`.

Para retirar esta herramienta, eliminar selectivamente sus fuentes/ejemplos
nuevos y `.venv/general-home`, conservando cambios posteriores. Restaurar sólo
sus entradas documentales desde el respaldo si corresponde. No necesita
rollback, recarga ni reinicio en el robot. Registro: ANL-01 en
[`SYSTEM_CUSTOMIZATIONS.md`](../../../docs/SYSTEM_CUSTOMIZATIONS.md).
