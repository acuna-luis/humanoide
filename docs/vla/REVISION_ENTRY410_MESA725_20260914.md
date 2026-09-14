# ENTRY410 con mesa de 72,5 cm: recálculo y preparación

2026-09-14, Europe/Madrid. Ficha VLA-01. Estado: **cálculos offline completados con hipótesis; ejecución física PENDIENTE**.

## Resultados actuales

- Captura pasiva Motion: 355 muestras, 12:04:24–12:04:35 UTC, sin errores observados, velocidad medida cero y ambos paros liberados durante la lectura. No hubo transición de paro ni ensayo de frenado.
- Nueva imagen, nube y TF coinciden temporalmente. CameraInfo tiene marca cero: no acredita calibración reciente. Se conservaron los datos originales.
- Mesa declarada por el operador: 0,725 m suelo–tablero. Ajuste RGB del centro del borde delantero en `base_link`: [0,569817; −0,063282; 0,573479] m. Caja, centro del borde delantero superior: [0,648247; −0,032792; 0,812530] m. Son estimaciones basadas en dimensiones y anotaciones, no metrología certificada.
- Contraste independiente con 165 puntos del tablero: discrepancia mediana de 25,70 mm respecto al plano RGB, percentil 95 absoluto de 34,39 mm, máximo observado 43,86 mm; normales separadas 6,08°. El plano de la nube tiene residuo propio P95 de 5,24 mm. Un buen ajuste interno no elimina el error entre modelos.
- Acceso desde postura medida → READY → ENTRY410 y retorno vacío inverso → HOME: cada revisión da **1018 intervalos certificados, 54 infracciones del margen del modelo y cero intervalos sin resolver**. De los certificados, 90 corresponden a escena y 928 al robot. No significa cero solapamientos.
- Se conservaron las hipótesis de ±1° independientes, margen geométrico de 2 mm y expansión de escena de 50 mm por cara. Los 50 mm no son un límite de error total demostrado. Escena modelada: tablero y caja; no todo el taller, patas o apoyos de madera.
- Las 54 interfaces se clasifican en 30 invariantes y 24 móviles; ninguna corresponde a abrazaderas. Once móviles tienen separación continua de superficies CAD demostrada para el dominio actual: nueve pruebas reutilizadas mediante inclusión exacta de intervalos y dos recalculadas. Las otras 13 presentan intersecciones CAD y siguen pendientes de justificar mecánicamente. La separación de superficies no certifica separación de volúmenes ni tolerancias del montaje.
- Configuración YAML, URDF y biblioteca cúbica en Motion conservan los hashes de la revisión de contrato. Los archivos coincidentes no demuestran todos los parámetros cargados ni el comportamiento temporal del controlador.

## Secuencia preparada

`prepare_entry410_stages.py` conserva exactamente los 20 valores originales de episode_000410 y genera cinco XML de ida y cinco inversos, todos **DRAFT**, sin transporte al robot:

| Grupo | Duración nominal |
|---|---:|
| Cabeza | 7 s |
| Cintura | 1 s |
| Elevador | 65 s |
| Brazo izquierdo | 1 s |
| Brazo derecho | 1 s |

Total READY→ENTRY: 75 s, sin esperas de comprobación y sin HOME→READY. El retorno invierte el orden. Esta velocidad es de preparación del ensayo, no una optimización de producción. La revisión geométrica de la secuencia también da 1018/54. Los límites configurados de cuerpo/cabeza se contrastaron incluyendo el intervalo de error. La ordenación articular efectiva por grupo, estabilización, seguimiento y parada siguen sin validación física. No utilizar estos borradores tras agarrar una caja ni desde una postura divergente.

## Qué permanece abierto y por qué

1. Registro físico y cobertura de escena: la comparación RGB/profundidad muestra un desacuerdo real; no permite afirmar que el error total esté acotado en 50 mm.
2. Las 13 interfaces móviles con intersecciones CAD necesitan una representación mecánica válida para todo el dominio. La aceptación de falsos positivos en la postura inicial no prueba todo el recorrido.
3. Ejecución efectiva y parada: la lectura inmóvil no mide sobrepaso, latencia ni frenado. Una función cúbica revisada offline tampoco lo demuestra.

No quedan intervalos numéricos agotados en esta revisión. Estos pendientes no se resuelven repitiendo el mismo cálculo ni marcando `physical_approval=true`. ENTRY410 sigue seleccionada; el VLA permanece sin publicador físico. Tampoco se certifica el flujo posterior de agarrar, vaciar y depositar.

## Fuentes, reproducción y recuperación

Evidencia privada: `../Humanoide-vla-evidence/20260914T120351Z_ENTRY410-725-REVIEW/`, con capturas, anotaciones, ajustes, estados, informes, XML, copia de fuentes y manifiesto `evidence.sha256`.

Herramientas locales: `fit_entry_fixture_pose.py`, `review_entry_fixture_hypotheses.py`, `audit_entry_route_interfaces.py`, `reuse_entry_boundary_proofs.py`, `prove_entry_interface_boundaries.py`, `compare_entry_scene_registration.py`, `prepare_entry410_stages.py`. Sus CLI exigen entradas explícitas y salidas nuevas. Usar Python de `.venv/general-home`; todas estas revisiones son offline. La receta exacta del cálculo queda en `reproduce-offline.sh` dentro de la evidencia y se conserva junto a las fuentes.

Cambios PC: nuevo generador ENTRY410 y reutilizador de pruebas; generador360 parametrizado con candidato explícito, manteniendo su valor por defecto360; perfil offline actualizado con evidencia actual. Validación: 16 tests de inclusión de dominios, etapas, límites, superficies y captura/planos; no hubo movimiento, instalación, recarga ni cambio de protecciones. Las consultas remotas terminaron.

Respaldo previo: `before/` en la evidencia. Reversión local: recuperar selectivamente esos archivos y retirar únicamente los archivos nuevos de esta intervención; no revertir otros cambios del usuario. No hay adaptación nueva que instalar o revertir en Motion/Vision. Después de firmware, volver a comparar modelos, configuración y contrato antes de reutilizar estos resultados.

### Receta versionada del recálculo

Ejecutar desde la raíz del repositorio; las evidencias privadas y modelos deben conservarse. Las pruebas de interfaces reutilizadas están vinculadas por hashes a sus informes originales.

```bash
#!/usr/bin/env bash
# Offline only. First argument: preserved evidence directory. Second: NEW output directory.
set -euo pipefail
src=${1:?evidence directory}; out=${2:?new output directory}
mkdir "$out"
py=.venv/general-home/bin/python
"$py" scripts/vla/fit_entry_fixture_pose.py --capture "$src/scene-capture.json" --camera-to-base "$src/camera-to-base.json" --annotations "$src/fixture-annotations.json" --output "$out/fixture-fit.json"
"$py" scripts/vla/review_entry_fixture_hypotheses.py --fixture-fit "$out/fixture-fit.json" --access-review "$src/entry410-route-input.json" --measured-joints "$src/measured-joints.json" --scene-uncertainty-profile config/vla/offline/entry_scene_uncertainty_review.json --directional-bounds --uncertainty-partition-nodes 512 --output "$out/entry410-route-review.json"
"$py" scripts/vla/audit_entry_route_interfaces.py --review "$out/entry410-route-review.json" --output "$out/interfaces410.json" --steps 9
"$py" scripts/vla/compare_entry_scene_registration.py --points "$src/current-points.npz" --annotations "$src/cloud-annotations.json" --fit "$out/fixture-fit.json" --output "$out/cloud-rgb-comparison.json"
"$py" scripts/vla/prepare_entry410_stages.py --reference "$out/entry410-route-review.json" --runtime-contract ../Humanoide-vla-evidence/20260910T142312Z_HOME-GEOMETRY-MOTION-QUALIFICATION/runtime-contract-audit.json --runtime-hashes "$src/runtime-current.sha256" --output-dir "$out/stages410"
```

## Diagnóstico posterior: el desacuerdo no identifica la extrínseca

2026-09-14, 14:22 Europe/Madrid. **Corrección de interpretación:** los 25,70 mm
son una diferencia entre el ajuste rectangular RGB y una porción de la nube;
no demuestran un error en la transformación cámara–robot. Ambas estimaciones
usan la misma transformación rígida. El desacuerdo se conserva al expresarlo
en coordenadas ópticas (diferencia numérica máxima 1,43e−16 m). Modificar esa
transformación para eliminar este residuo sería una corrección injustificada.
K y el bloque intrínseco de P coinciden en esta captura, por lo que tampoco
se observa aquí una diferencia K/P que explique el resultado.

Se repitió el ajuste por regiones, manteniendo las anotaciones y sin cambiar
la calibración. Intersectar los rayos de las esquinas con cada plano produce:

| Región de profundidad | Puntos del plano | Fondo inferido por un lateral |
|---|---:|---:|
| Completa | 165 | 72,46 cm |
| Izquierda | 84 | 67,03 cm |
| Derecha | 87 | 80,02 cm |
| Inferior | 137 | 65,53 cm |
| Superior | Sin plano dominante | No estimable |

La dimensión asumida es 84 cm. Estos resultados muestran sensibilidad a la
región y a la extrapolación del plano; no constituyen nuevas medidas del tablero.
No se puede decidir con esta única comparación si predomina error de profundidad,
anotación de esquinas, dimensiones asumidas o una combinación. No se sustituyó
la mesa modelada por ninguno de estos planos, ni se aumentaron tolerancias.

### Localización de las interfaces pendientes

Diez pares están conectados directamente por una articulación en el URDF:
lifter2–lifter3, lifter3–cintura y, por cada brazo, hombro pitch–roll,
codo roll–yaw, codo yaw–muñeca pitch y muñeca pitch–roll.
Los otros tres son lifter2–cintura, lifter3–torso y torso–cabeza pitch.
No hay abrazaderas en esos 13 pares. La adyacencia mecánica explica dónde
investigar una simplificación CAD, pero **no demuestra una exención para todo
el dominio ni autoriza a retirar sus superficies**. No se encontraron archivos
SRDF o configuraciones de colisión por nombre en los dos paquetes de descripción
consultados; esta búsqueda no demuestra ausencia en todo el software del proveedor.

### Reproducción, pruebas y cambios

Herramienta nueva: `scripts/vla/diagnose_entry_plane_disagreement.py`, offline.
Ejecutar desde la raíz con salida nueva:

```bash
.venv/general-home/bin/python scripts/vla/diagnose_entry_plane_disagreement.py \
 --capture ../Humanoide-vla-evidence/20260914T120351Z_ENTRY410-725-REVIEW/scene-capture.json \
 --annotations ../Humanoide-vla-evidence/20260914T120351Z_ENTRY410-725-REVIEW/cloud-annotations.json \
 --fit ../Humanoide-vla-evidence/20260914T120351Z_ENTRY410-725-REVIEW/fixture-fit.json \
 --output /tmp/entry410-plane-diagnosis-new.json
PYTHONPATH=scripts/vla .venv/general-home/bin/python -m unittest \
 test_diagnose_entry_plane_disagreement test_check_entry_scene_planes \
 test_compare_entry_scene_registration
```

Siete tests pasan, incluyendo intersección conocida, invariancia rígida y rechazo
de rayos paralelos o hacia atrás. Evidencia:
`../Humanoide-vla-evidence/20260914T122227Z_ENTRY410-DIAGNOSIS/`, informes,
fuentes y hashes; respaldo documental en `before/`. Cambios persistentes sólo en
herramientas/documentación del PC. Sin consultas nuevas al robot, instalación,
movimiento o modificación de modelos/protecciones. Reversión: retirar las dos
fuentes nuevas y recuperar selectivamente las copias documentales; preservar
el resto del trabajo. VLA-01 continúa sin aprobación física.

## Medida del propietario: separación chasis–mesa de 160 mm

2026-09-14, Europe/Madrid. El operador informa 16 cm entre punta del chasis y
proyección de la mesa sobre el suelo, y autoriza usar orientaciones de cámara.
Se interpreta como separación longitudinal +X hasta la proyección del borde
frontal en y=0. Error de medida y correspondencia exacta de la punta física con
la malla: no aportados. La medida no se confunde con distancia desde las ruedas.

La malla `base_link.STL`, origen de colisión cero y escala unitaria en el URDF,
tiene punta x=0,354041517 m. La medida ancla el borde a x=0,514041517 m; el ajuste
RGB lo situaba a x=0,573747159 m en y=0. Se traslada la hipótesis mesa+caja
−59,705642 mm en X, conservando sus orientaciones, coordenadas laterales y pose
relativa. Esto es un anclaje parcial, no una calibración completa. Los residuos
RGB anteriores quedan archivados como tales, no como ajuste de la pose nueva.

La exclusión solicitada por el propietario se registra en
`config/vla/offline/entry410_owner_interface_exclusions.json`: únicamente los
13 pares internos identificados, vinculados a hashes del modelo. Se omiten en
la valoración offline solicitada, pero los informes brutos se conservan y no se
afirma que se haya probado que son falsos positivos. No se modifican filtros,
anticolisión, paros ni otros controles de Motion. Ningún par de abrazadera o
entorno se incorpora a esa lista.

**Resultado nuevo:** acceso y retorno dan 1017 pares certificados, las 54 marcas
internas históricas y un par sin cota suficiente: `R_hand_link#0` frente a
`scene:tabletop_fit`. La búsqueda encontró y una segunda evaluación reprodujo
una intersección con el tablero expandido 50 mm por cara, al 99,9683% del tramo
READY→ENTRY, con error articular máximo 0,956158° y límites articulares válidos.
Distancia de sólidos cero, FCL confirma intersección. Es un contraejemplo dentro
de las hipótesis ±1°/+50 mm, **no contacto observado con la mesa real**. No se
puede eliminar usando la exclusión de interfaces internas. ENTRY no queda
aprobada con esta configuración; pendiente adaptar separación/recorrido o
acotar la incertidumbre con evidencia. El ensayo de ejecución/parada sigue
posterior a resolver este margen externo.

### Receta del anclaje y revisión

```bash
.venv/general-home/bin/python scripts/vla/anchor_entry_scene_to_chassis_gap.py \
 --fit ../Humanoide-vla-evidence/20260914T120351Z_ENTRY410-725-REVIEW/fixture-fit.json \
 --measurement config/vla/offline/entry410_gap160_measurement.json \
 --urdf cruzr_s2_description_splint/cruzr_s2_description/urdf/cruzr_s2_v1/cruzr_s2_v1.urdf \
 --chassis-mesh cruzr_s2_description_splint/cruzr_s2_description/meshes/cruzr_s2_v1/base_link.STL \
 --output /tmp/entry410-gap160-fit-new.json
```

Usar esa salida como `--fixture-fit` en la receta de revisión anterior y una
salida nueva. Para reproducir el contraejemplo, con el informe nuevo:

```bash
.venv/general-home/bin/python scripts/vla/search_entry_fixture_witness.py \
 --review /tmp/entry410-gap160-review-new.json \
 --output /tmp/entry410-gap160-witness-new.json \
 --pair 'R_hand_link#0' scene:tabletop_fit --segment 1 \
 --fraction-range 0.95 1 --iterations 60
```

Fuentes nuevas: anclaje y tests; perfiles de medida y exclusión. Perfil de
selección actualizado. Seis tests pasan (anclaje girado, borde fuera del eje,
orientación longitudinal y expansión de escena). Evidencia privada
`../Humanoide-vla-evidence/20260914T123149Z_ENTRY410-GAP160/`, respaldo `before/`,
fuentes y manifiesto. Reversión local selectiva desde ese respaldo; retirar sólo
las nuevas fuentes/perfiles de esta intervención. Sin conexión nueva, movimiento,
instalación o cambio remoto. VLA-01 conserva `physical_approval=false`.

## Retroceso confirmado: separación aproximada de 220 mm

2026-09-14, Europe/Madrid. El operador confirma unos 22 cm, orientación sin
cambios, robot y mando detenidos. Perfil nuevo
`config/vla/offline/entry410_gap220_measurement.json`; el de 160 mm se conserva
como histórico. Misma receta de anclaje con ese perfil y salidas nuevas.
Borde frontal en y=0: x=0,574041517 m; diferencia respecto al ajuste RGB original
+0,294358 mm. Se mantienen las orientaciones y pose relativa caja–mesa estimadas.
No se exige convertirlas en medidas manuales en cada ciclo; tampoco se cambia
su carácter estimado por una garantía de precisión.

**Verificado offline:** acceso y retorno con escena220 dan 1018 pares certificados,
54 marcas internas y cero pendientes; pasan todos los 90 pares robot–escena,
incluido abrazadera derecha–tablero, bajo las hipótesis ±1°/+50 mm y margen2 mm.
Las exclusiones del propietario siguen limitadas a los 13 pares internos
identificados. No se altera la anticolisión del robot.

Nueva captura pasiva Motion 12:45:43–12:45:54 UTC:361 muestras, velocidad cero,
paros0/0 y sin errores observados. Diferencia máxima de postura respecto a la
lectura anterior0,000671117 rad. Se recalculó también desde esta lectura nueva,
con el mismo resultado1018/54, sin pendientes ni agotamiento de tiempo.
La secuencia READY→ENTRY por cinco grupos y sus inversas vuelve a pasar la
revisión del modelo:75 s nominales por sentido, más comprobaciones intermedias.
Son borradores; no se instalaron ni ejecutaron. El certificado del modelo no
resuelve por sí solo incertidumbre física total, contrato de ejecución o parada.

Evidencia `../Humanoide-vla-evidence/20260914T124504Z_ENTRY410-GAP220/`:
`anchored-fit.json`, `route-review.json`, `route-current-start-review.json`,
`passive/`, `passive-analysis.json`, `measured-joints.json`, `stages410/`.
Fuentes y respaldo previo en `sources/` y `before/`; hashes en `evidence.sha256`.
Sin cambios remotos persistentes; el lector terminó. Cambios locales: perfil
nuevo, selección y documentación. Reversión selectiva desde el respaldo,
conservando todos los otros cambios del usuario. VLA-01.
