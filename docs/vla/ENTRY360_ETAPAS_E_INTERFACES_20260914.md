# ENTRY360: etapas, fronteras de las uniones y contraste de escena

2026-09-14, Europe/Madrid. VLA-01. **VERIFICADO en el alcance offline descrito;
ensayo físico todavía no habilitado.** Se avanza sobre los tres puntos de la
[revisión anterior](REVISION_PRUEBA_ENTRY360_20260914.md). Esta intervención no
mueve el robot, no instala tareas, no reinicia y no cambia límites o exclusiones.
Las consultas remotas se limitan a contenedores y hashes de archivos.

## Resultado concreto

| Punto | Resultado nuevo | Límite del resultado |
|---|---|---|
| Uniones sin cruce de superficies en las muestras | 11/11 con separación continua de fronteras CAD en el dominio de ENTRY360 | No acredita volumen material, error de montaje ni separación física de 2 mm |
| Otras uniones móviles | Permanecen 13 con cruces de superficies en el CAD | Falta definir las regiones mecánicas admisibles, no otra medida de la almohadilla |
| Secuencia específica de 360 | Cinco etapas independientes, ida y retorno preparados; 75 s nominales por sentido | Borradores offline, sin instalador ni ejecutor |
| Geometría de la secuencia por etapas | 1018 pares certificados, 54 avisos, sin timeout; incluye 90/90 contra mesa/caja del modelo | Conserva las hipótesis de escena+50 mm y ±1°; no describe toda la sala |
| Límites de cabeza/cuerpo | Intervalos con ±1° dentro de los seis límites configurados | Hashes actuales de archivos, no verificación de parámetros cargados o seguimiento real |
| Suelo frente a mesa en una captura | Alturas inferidas 75,47 / 80,85 / 82,11 cm según parche | Dispersión de 66,40 mm; no establece una cota de error total |

No se presenta la ausencia de una prueba como una colisión física. Tampoco se
presenta la separación entre superficies trianguladas como la validación de
toda una unión mecánica. Los 54 avisos originales se conservan en los informes.

## Separación continua: qué cambió en el cálculo

El cálculo anterior aplicaba un radio de desplazamiento grande a todo el torso.
La distancia pequeña cerca del rodamiento obligaba a dividir el dominio en
muchísimas cajas angulares. Para ENTRY360, la primera pasada prueba ocho pares;
la ampliación del presupuesto resuelve ambos hombros, pero sigue sin resolver
`lifter_pitch_2_link#0` / `torso_link#0` con ese método.

El nuevo método trabaja en el marco del eje `lifter_pitch_3_joint`. Cada
triángulo se encierra mediante radio mínimo/máximo, altura axial y sector
angular. El giro de ese eje sólo desplaza el sector angular; conserva radio y
altura. El segundo eje, `waist_yaw_joint`, se acota por el desplazamiento de
cada triángulo respecto a su propio eje, no por el radio del torso completo.

Una jerarquía de cajas descarta parejas separadas. Para cajas próximas se
subdividen los triángulos, conservando ambos hijos. Una prueba sólo pasa si
se cubre todo el dominio. Agotar presupuesto o solapar las cajas devuelve
inconcluso, nunca una exención de colisión. Las superficies fuente se conservan.

La unión del elevador queda cubierta en ocho intervalos de cintura, con todo
el intervalo del tercer tramo del elevador en cada uno:

```text
lifter_pitch_3_joint: [-0.7591330206, 0.0174532925] rad
waist_yaw_joint:      [-0.0178367877, 0.0174532925] rad
```

Quince nodos del árbol angular (ocho hojas aprobadas), unos 24 s de cálculo.
La cota mínima resultante es 0,000174732 mm después de los resguardos numéricos.
Es una **cota inferior floja del cálculo**, no una medida de la holgura real ni
una tolerancia física utilizable. El resguardo numérico es 0,0001 mm; no se
sustituyen por él los errores mecánicos. La primera versión sin subdivisión
de triángulos no resolvía el caso; su código y resultado se conservan.

## Qué falta de las trece interfaces

Las trece relaciones pendientes son:

- Segundo/tercer tramo del elevador; segundo tramo/cintura.
- Tercer tramo/cintura; tercer tramo/torso.
- Torso/cabeza pitch.
- Hombro pitch/roll de cada brazo.
- Codo roll/yaw de cada brazo.
- Codo yaw/muñeca pitch de cada brazo.
- Muñeca pitch/roll de cada brazo.

Se necesitan regiones de interfaz y dominios articulares cuya correspondencia
con el mecanismo real esté establecida, o un modelo equivalente de colisión
validado para esas uniones. El auditor ya conserva nombres y dominios exactos
en `current-interfaces360.json`. No basta declarar toda la pareja exenta:
los barridos previos encontraron cruces nuevos en algunos dominios. La
observación anterior del técnico sobre falsos positivos en reposo no demuestra
que cualquier cruce durante el recorrido pertenezca al mismo espacio admitido.
Véase [la revisión mecánica previa](../teleoperation/CRUZR_HOME_GEOMETRIA_Y_MOTION.md).

## Escena: contraste independiente de la traslación de cámara

Se reutiliza la captura pasiva de las 10:42:01 UTC, marca de imagen/nube
`1789382521092207000 ns`. No se toma otra foto ni se cambia la mesa. Las marcas
de nube, imagen y TF deben coincidir exactamente para este comparador.

Se ajustan tres parches visibles del suelo y el parche visible del tablero.
La diferencia de planos cancela una traslación común de cámara. Respeta los
pasos de fila/punto y endianness de PointCloud2, rechaza marcos inconsistentes
y sólo admite la proyección rectificada usada por esta captura.

Las alturas extrapoladas a la posición del parche de mesa son:

| Parche de suelo | Altura en Z de base | Diferencia respecto a 80 cm declarados |
|---|---:|---:|
| Izquierdo | 808,47 mm | +8,47 mm |
| Derecho | 754,73 mm | −45,27 mm |
| Delantero | 821,13 mm | +21,13 mm |

La proyección de la mesa queda fuera de los tres parches de suelo observados;
la extrapolación se señala en el JSON. Estas cifras no identifican por sí solas
si el origen de la discrepancia es profundidad, ajuste, o geometría real del
suelo. No se corrige la calibración ni se transforma el máximo observado en una
cota garantizada. **No procede ordenar bajar la mesa a 72 cm basándose en esto.**

Para quitar este requisito de un primer ensayo de postura vacía, la alternativa
es retirar físicamente mesa/caja de todo el alcance y verificar la zona actual.
Eso no resuelve las interfaces mecánicas, seguimiento o parada, ni valida después
un agarre VLA con la mesa recolocada.

## Propuesta por etapas y límites actuales

En lugar del XML histórico de otro episodio, se generan diez borradores nuevos:
cinco de ida y sus cinco inversos. Cada XML contiene una única acción de grupo.

| Etapa de ida desde READY | Duración nominal |
|---|---:|
| Cabeza | 7 s |
| Cintura | 1 s |
| Elevador, sus tres ejes | 65 s |
| Brazo izquierdo, ajuste pequeño al vector original | 1 s |
| Brazo derecho, ajuste pequeño al vector original | 1 s |

El extremo coincide exactamente con el vector20D original360. El retorno usa
las etapas en orden inverso y los mismos segmentos geométricos al revés. Los
75 s no incluyen HOME→READY, READY→HOME, las comprobaciones entre etapas, ni el
agarre VLA. Cada paso requiere comparar estado20D medido, inmovilidad y control
exclusivo antes del siguiente; no se suministra una secuencia automática que
omita esas comprobaciones. El orden de los ejes en el despacho real todavía
debe verificarse. Los tres ejes del elevador siguen compartiendo un grupo.

Se redescubre Motion y se leen los hashes de YAML, URDF nativo y biblioteca
cúbica. Coinciden con las copias auditadas previamente. Se comprueban los seis
límites de cabeza/cuerpo contra los extremos y todo ±1°; la interpolación afín
permanece dentro por convexidad. Los caps analíticos de 0,05 rad/s y 0,05 rad/s²
quedan por debajo de los configurados. No se ha verificado que el proceso tenga
esos archivos cargados, el seguimiento real, la estabilidad ni el frenado.

## Reproducción, pruebas y registro VLA-01

Fuentes nuevas en PC:

- `scripts/vla/check_entry_scene_planes.py`: comparación métrica por parches.
- `scripts/vla/entry_orbit_bounds.py` y `prove_entry_lifter_orbits.py`: cotas de
  órbitas y prueba específica de la unión del elevador.
- `scripts/vla/prepare_entry360_stages.py`: genera borradores y revisa geometría
  y límites. No contiene SSH, ROS, instalación o ejecución.
- Tests correspondientes: planos, cotas frente a puntos interiores/giro,
  subdivisión, marcos contrastados con FK completa, mapeo de grupos, inversión
  del recorrido, límites e inconsistencias de hashes.

**Verificación: 18 tests pasan, sin fallos, errores ni pruebas omitidas.**

Evidencia privada: `../Humanoide-vla-evidence/20260914T110514Z_ENTRY360-CLOSURE/`.
Resultados finales: `scene-plane-comparison.json`, `boundaries360.json`,
`boundaries360-remaining.json`, `lifter-orbits-refined.json`,
`stages360-final/review.json`, `runtime-current.sha256`, `tests.log`.
Los borradores están exclusivamente en `stages360-final/DRAFT_*.xml`, fuera
de la carpeta de tareas instalables. Sus hashes constan en el informe.

Repetir offline con salidas nuevas desde la raíz del repositorio:

```bash
ENTRY360_PREV=../Humanoide-vla-evidence/20260914T104001Z_ENTRY360-QUALIFICATION
ENTRY360_EVIDENCE=../Humanoide-vla-evidence/20260914T110514Z_ENTRY360-CLOSURE
ENTRY360_OUT="$(mktemp -d /tmp/cruzr-entry360-offline.XXXXXXXX)"

.venv/general-home/bin/python scripts/vla/check_entry_scene_planes.py \
  --capture "$ENTRY360_PREV/scene-capture.json" \
  --annotations "$ENTRY360_EVIDENCE/plane-annotations.json" \
  --output "$ENTRY360_OUT/planes.json"

.venv/general-home/bin/python scripts/vla/prove_entry_lifter_orbits.py \
  --interfaces "$ENTRY360_PREV/current-interfaces360.json" \
  --output "$ENTRY360_OUT/orbits.json" --max-boxes 31

.venv/general-home/bin/python scripts/vla/prepare_entry360_stages.py \
  --reference "$ENTRY360_PREV/current-route-review.json" \
  --runtime-contract ../Humanoide-vla-evidence/20260910T142312Z_HOME-GEOMETRY-MOTION-QUALIFICATION/runtime-contract-audit.json \
  --runtime-hashes "$ENTRY360_EVIDENCE/runtime-current.sha256" \
  --output-dir "$ENTRY360_OUT/stages"
```

El último comando reproduce la lectura de hashes archivada; no la refresca.
Conexión verificada: Motion `192.168.11.2`, contenedor
`walker-motion.manipulation_robot_app-1`, imagen motion-v0.2.0. Las consultas
fueron `docker ps` y `docker exec … sha256sum` sobre los tres archivos; los
lectores SSH finalizaron. No se modificó el robot ni sus servicios.

`before/` conserva documentos y versiones intermedias de herramientas nuevas;
`final-sources/` y `evidence.sha256` fijan código, documentación y resultados.
Dependencias: entorno ANL-01 `.venv/general-home` existente, sin instalaciones.
Reversión: retirar únicamente estas herramientas nuevas y restaurar las fichas
desde el backup de esta intervención si se desea deshacer el análisis; no hay
rollback remoto. No se hace commit ni push.
