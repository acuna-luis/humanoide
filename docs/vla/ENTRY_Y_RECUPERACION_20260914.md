# ENTRY y recuperación: revisión desatendida del 14-09-2026

**Actualización posterior:** [trazas y sensibilidad ±0,1/0,5/1/5°](ERROR_ARTICULAR_TRAZAS_20260914.md).
Máximo observado0,444207° en retornos vacíos; ±1° pasa a hipótesis prioritaria
de estudio, sin cambiar límites activos ni cerrar aprobación física.

**Resultado: preparación offline completada; selección y acceso físicos NO
aprobados.** Fecha/zona: 14-09-2026, Europe/Madrid. Ficha VLA-01.
El usuario autorizó resolver los puntos 1 y 2 sin nuevas preguntas. Se revisaron
datos y geometría y se consultó el robot sólo en lectura. No se enviaron órdenes
de movimiento, instalaciones, reinicios ni cambios de modo o protecciones.

## Hallazgos que cambian la elección

Se contrastaron los 150 estados iniciales task0 del archivo E6.0Z con el modelo
completo y los dos cuboides archivados de tablero/caja. Hay **69 entradas con
inclinación del torso ≤5° sin avisos adicionales respecto a HOME ni avisos
frente a esos dos obstáculos en el extremo**. Todas mantienen los 54 avisos de
interfaces de HOME: no son 69 extremos aprobados ni 54 contactos físicos.

Se inspeccionaron imágenes de familias de entrada más bajas que 430/438. En
doce episodios se cotejaron frame0, timestamp, task, vídeo y los 20 ángulos con
los parquets originales; no se mezclaron estados de episodios diferentes.
La primera selección por altura, ENTRY46, añadió ocho avisos con el tablero
en el extremo y se descartó para esa disposición. Se corrigió el selector
para aplicar primero el filtro de escena y después la preferencia por altura.

La candidata resultante es **ENTRY372**, torso **2,845°** respecto al modelo
erguido. Su altura de soporte inferida es aproximadamente **75,3 cm**, bajo las
mismas hipótesis fotográficas, con variación de píxeles y sin incertidumbre
total acotada. No demuestra compatibilidad con la mesa real de 80 cm, ni
prescribe cambiar su altura. ENTRY40 y los contratos activos permanecen intactos.

Las nuevas anotaciones no constituyen una recalibración. Por ejemplo, repetir
la reconstrucción de ENTRY40 con el montaje/cotas/selección de borde de este
análisis da aproximadamente 79,4 cm; no sustituye la estimación histórica de
77,46 cm obtenida con otro conjunto de premisas. Esta sensibilidad impide
tratar unos centímetros de diferencia como una tolerancia física demostrada.

## Rutas revisadas y alcance exacto

El comprobador conserva **1.072 pares**: 982 internos y 90 frente a los dos
obstáculos. Divide cada tramo articular afín y usa cotas del desplazamiento
para certificar intervalos completos; no declara libre un tramo sólo porque
algunas muestras estén separadas. Una violación o subdivisión sin resolver
permanece en el informe. No existen listas de pares exentos nuevas.

| Acceso a ENTRY372 | Tiempo matemático nominal | Pares certificados en intervalos | Avisos del modelo |
|---|---:|---:|---:|
| Directo desde el estado archivado | 13,471 s | 1.018 | 54 |
| Por READY | 25,264 s | 1.018 | 54 |
| Abrir, colocar cuerpo y después brazos | 28,847 s | 1.018 | 54 |

Son tiempos de la ley quintica offline con límites de diseño del planificador,
**no tiempos instalados ni velocidades autorizadas**. Las tres alternativas
mantienen el mismo conjunto de avisos que HOME y no añaden interferencias
nominales en el modelo listado. Ninguna pasa el control completo de geometría.
La escena incluye sólo los cuboides archivados; faltan el registro completo
actual, patas, apoyos y otros objetos pertinentes. El certificado afín tampoco
demuestra sincronización real de Motion, desfase entre ejes o distancia de parada.

El escenario adicional de error articular de 5° **no quedó certificado**:
alcanzó su presupuesto de 90 s. Resultado conservador: 54 avisos nominales y
1.018 pares sin resolver, no 1.018 colisiones. No se redujo el error para pasar.

La recuperación propuesta invierte el acceso **con abrazaderas vacías y
escena sin cambios**. No sirve automáticamente tras agarrar, después de una
interrupción o desde un punto fuera del recorrido. Se corrigió además el final:
volver a la postura archivada con la cabeza a −0,43 rad no es HOME completo.
Se añadió y revisó por separado el tramo final hasta los 20 ejes HOME; conserva
1.018 pares certificados y los mismos 54 avisos. El estado actual del robot
se volvió a medir y ya era HOME; no se ejecutó este retorno.

## Lectura actual del robot

14-09, 06:14–06:18 UTC: contenedores descubiertos nuevamente en Motion y Vision;
ambos VLA detenidos. `/mc/sdk/robot_command`: tipo RobotCommand, writers0,
readers2. JointState canónico: máximo HOME **0,002876214 rad**, velocidades0.
No se infiere batería, paros, objetos sujetos, modo o disponibilidad física
para mover a partir de estas consultas.

Cámara estéreo real: BGR8, 960×576. CameraInfo recibido en
`/sensor/camera/stereo/color/info`; su matriz K coincide exactamente con la
archivada usada en el análisis. Eso verifica los intrínsecos publicados
actualmente, no el montaje ni la calibración de todos los episodios del dataset.
La nueva imagen muestra una caja azul recortada por abajo. No se ha cambiado la
orientación de la cabeza para ampliar la vista durante el trabajo desatendido.

## Fuentes, uso y reproducción

Herramientas nuevas, sólo PC:

- `scripts/vla/survey_vla_entry_scene.py`: censo de los 150 extremos y sus avisos.
- `scripts/vla/prepare_vla_entry_bundle.py`: cotejo de originales, selección,
  revisión por intervalos, rutas y final de recuperación vacío hasta HOME.
- `scripts/vla/test_prepare_vla_entry_bundle.py`: diez pruebas, incluyendo
  contacto interior entre extremos separados, falta de resolución, incertidumbre,
  identidad del dataset y distinción entre cabeza de observación y HOME.
- `config/vla/offline/entry80_rim_annotations_20260914.json`: anotaciones e
  hipótesis explícitas, fuera de los contratos runtime.

No se instalaron dependencias. Se usaron los entornos existentes de geometría y
lectura de vídeo/parquet. Las dos primeras preparaciones fallaron sólo en PC al
intentar importar OpenCV/Pillow desde un entorno que no los tenía; se eliminó
la dependencia innecesaria de OpenCV y se reutilizó Pillow del entorno existente.
Las carpetas fallidas se conservan. Pasan diez pruebas nuevas y ocho del ranking.

Desde la raíz del repositorio, con los archivos privados archivados disponibles:

```bash
VLA_EVIDENCE_ROOT=/home/lacuna/proyectos/Robots/Humanoide-vla-evidence
.venv/general-home/bin/python scripts/vla/survey_vla_entry_scene.py \
  --dataset-report "$VLA_EVIDENCE_ROOT/20260904T094803_E6.0Z/dataset-entry-states.json" \
  --obstacles "$VLA_EVIDENCE_ROOT/20260911T114330Z_VLA-ENTRY-SCENE/recentered/obstacles.json" \
  --output /tmp/vla-entry-survey-new.json

PYTHONPATH=.venv/general-home/lib/python3.12/site-packages \
.venv/vla-scene/bin/python scripts/vla/prepare_vla_entry_bundle.py \
  --dataset-report "$VLA_EVIDENCE_ROOT/20260904T094803_E6.0Z/dataset-entry-states.json" \
  --dataset cruzrss2_vla_pack-002/data/utars_clamp_and_place_large_box_full_data_bio_lerobot_0319 \
  --registration "$VLA_EVIDENCE_ROOT/20260911T114330Z_VLA-ENTRY-SCENE/recentered/metric-scene.json" \
  --camera-info "$VLA_EVIDENCE_ROOT/20260901T084855_E4.1/artifacts/camera_info.json" \
  --obstacles "$VLA_EVIDENCE_ROOT/20260911T114330Z_VLA-ENTRY-SCENE/recentered/obstacles.json" \
  --annotations config/vla/offline/entry80_rim_annotations_20260914.json \
  --output-dir /tmp/vla-entry-bundle-new --route-budget-seconds 90
```

Las salidas deben ser nuevas. `--home-tail-only`, con los mismos argumentos,
revisa únicamente el tramo final y no sustituye la revisión del acceso.
Ningún comando contiene ejecución física ni produce XML instalable.

Evidencia privada:
`../Humanoide-vla-evidence/20260914T055526Z_VLA-ENTRY80-OFFLINE/`.
`endpoint-survey.json`, `review-v3/` (candidato46 descartado),
`review-filtered/` (372), `home-tail/` (final completo), lecturas nuevas,
fuentes de captura, imágenes y hashes. `sources-filtered-run/` conserva la
versión exacta anterior a añadir el tramo final; `final-sources/` conserva la
versión final. El tramo nuevo se ensayó aparte sin repetir las tres auditorías
geométricas ya terminadas. `before/` contiene los documentos previos.

## Pendiente concreto y reversión

No están cerrados los puntos físicos 1 y 2: falta resolver las interfaces del
modelo, completar el registro de escena y demostrar compatibilidad VLA desde
la candidata, además del seguimiento y recuperación del movimiento real.
No hay que repetir el censo de 150 entradas ni las rutas nominales sin que
cambien sus entradas. Los cinco shadow calificados siguen 0/5.

No se cambiaron contratos, modelo, checkpoint, runtime, trayectorias ni servicios
del robot. Instalado/cargado/probado: herramientas PC usadas offline; **no
instaladas ni probadas físicamente en el robot**. Reversión: retirar únicamente
los cuatro archivos nuevos y este informe y deshacer sus entradas documentales,
comparando `before/` para preservar cualquier trabajo posterior. No hay cambio
remoto que restaurar. No se hizo commit ni push.

## Segunda revisión: separar tiempo, resolución e incertidumbre

**14-09-2026, Europe/Madrid — cálculo terminado; no aprobación física.**
Se corrigió una redundancia de `certify_pairs`: tras quedar un par sin resolver
para un tramo, seguía explorando los intervalos hermanos de ese mismo par.
Ahora conserva su rechazo, con causa/punto/margen, y deja de gastar cálculo en
él. No lo excluye del resultado ni permite que obtenga un certificado global.
Once pruebas del comprobador pasan, incluido un caso casi tangente que comprueba
la poda sin convertir resolución insuficiente en PASS.

Nueva herramienta PC `scripts/vla/review_vla_entry_error_bound.py`: vuelve a
examinar una ruta archivada, verificando candidato, hash de escena/modelo,
orden articular y conjunto de pares. No relee cámaras ni cambia el robot.

El primer reintento con profundidad16 agotó90,101s. Se conservó como incompleto.
Para separar las causas se ejecutó profundidad6: terminó en **26,490s**, sin
agotar tiempo, manteniendo exactamente el escenario de **±5° por eje** y el
margen geométrico de2mm. La menor profundidad es un presupuesto numérico:
toda celda no demostrada sigue rechazada, no supone relajar tolerancias físicas.

| Resultado por par en HOME archivado → READY → ENTRY372 | Número |
|---|---:|
| Certificado para los intervalos afines y el escenario de error |693|
| Aviso nominal del modelo, mismo conjunto de HOME |54|
| Cota de error insuficiente para demostrar separación |280|
| Resolución numérica insuficiente |45|

De los90pares contra los obstáculos archivados,54se certifican y36siguen sin
resolver. No son36contactos. La cota global por radios acumula el efecto del
error de todos los ejes ascendientes: para algunos pares mano/abrazadera frente
a base o escena exige aproximadamente1,01531m. Esa cota conservadora **no es
una predicción de desplazamiento físico**. Aumentar únicamente el tiempo no
resuelve los280casos con margen no demostrado; necesitan una cota geométrica
más ajustada pero válida, o evidencia que permita acotar mejor el error real.
No se cambió el valor declarado5° ni se aprobó movimiento con ese escenario.

Reproducción, desde la raíz y con las evidencias privadas disponibles:

```bash
.venv/general-home/bin/python scripts/vla/review_vla_entry_error_bound.py \
  --access-review ../Humanoide-vla-evidence/20260914T055526Z_VLA-ENTRY80-OFFLINE/review-filtered/access-review.json \
  --selection ../Humanoide-vla-evidence/20260914T055526Z_VLA-ENTRY80-OFFLINE/review-filtered/selection.json \
  --obstacles ../Humanoide-vla-evidence/20260911T114330Z_VLA-ENTRY-SCENE/recentered/obstacles.json \
  --output /tmp/vla-error5-review-new.json \
  --subdivision-depth 6 --budget-seconds 90
```

El argumento `--error-degrees` tiene valor predeterminado5. Las salidas son de
análisis y siempre `physical_approval=false`. No existe `--run` físico.
Evidencia, versiones exactas y respaldo anterior:
`../Humanoide-vla-evidence/20260914T062738Z_VLA-ERROR-BOUND-CLOSURE/`.
`sources-first-90s/` coincide con los hashes del primer intento;
`final-sources/` conserva las fuentes del resultado final y los documentos.
Sin dependencias nuevas ni consulta o mutación remota en esta segunda revisión.
Rollback: restaurar los dos archivos existentes desde `before/`, retirar sólo
`review_vla_entry_error_bound.py` y esta actualización documental, preservando
el trabajo de la primera revisión y cualquier edición posterior. Sin commit/push.
