# Error articular observado y sensibilidad de acceso a ENTRY

**14-09-2026, Europe/Madrid — VERIFICADO offline. Ficha VLA-01.**
Se revisaron diez capturas canónicas archivadas y cuatro escenarios geométricos.
No hubo conexión al robot, movimiento, instalación, cambio de límites ni arranque
VLA. Se preserva el trabajo anterior. No se aprueba ejecución física.

## Decisión práctica

- **±0,1° queda descartado como cota uniforme de la discrepancia observada:**
  existen muestras reales superiores, incluso con la cabeza quieta.
- **±0,5° contiene todas las muestras válidas revisadas**, pero sólo deja
  0,05579° sobre el máximo observado de 0,44421° (12,6% respecto al máximo).
  No es margen demostrado frente a variación de carga, velocidad o muestreo.
- **±1° es la hipótesis prioritaria para el siguiente análisis**, aproximadamente
  2,25 veces ese máximo. No es un óptimo industrial ni un límite validado;
  el ejecutor y la configuración activa no se han cambiado.
- **±5° no describe lo observado en estos dos retornos vacíos y lentos**:
  es unas 11,26 veces el máximo de esas capturas. Se conserva como escenario
  histórico conservador y como predeterminado del revisor existente; no se
  declara inválido para situaciones distintas o fallos que aquí no se midieron.

## Qué se midió

Se recalculó `abs(cmd_pos - position)` en los veinte actuadores de cada mensaje
`/mc/actuator_state`, antes de convertir radianes a grados. Son ambos campos
en coordenadas del mismo motor: no se mezclan signos de JointState y motor,
no se desplaza una señal en el tiempo para reducir el error y no se sustrae bias.

La definición archivada de UBTECH de `cmd_pos` es la última consigna solicitada
**sin aplicar límites**. Este informe mide discrepancia respecto a esa consigna;
no acredita la consigna final del servo, alineación interna de actualización de
los campos, exactitud geométrica externa o trayectoria interpolada por Motion.
Referencia: [contrato y limitaciones](../teleoperation/CRUZR_HOME_CAPTURA_Y_PROGRESO_INDEPENDIENTE.md#qué-calcula-y-qué-no-permite-concluir).

Los hashes de las diez trazas coinciden con sus `SHA256SUMS` archivados. Seis
capturas permiten comparación numérica: dos con movimiento y cuatro en reposo.
Se excluyen tres sin estados articulares y una que terminó con errores del
colector. Una captura ausente/rechazada devuelve estadísticas `null`, no error0.
No se usan `action` del dataset VLA como si fueran consignas físicas medidas.
La captura histórica READY→ENTRY del08-09 usa `whole_joint_states`, sin
`cmd_pos`: no permite medir esta discrepancia dinámica emparejada.

| Ensayo archivado | Mensajes completos | Máximo observado | Eje del máximo | Máxima velocidad observada |
|---|---:|---:|---|---:|
| H01: HOME → apertura/cierre → HOME |2103|0,444207°|hombro izquierdo, roll|0,247139rad/s|
| H02: PICO cuerpo recto → HOME 4× |2103|0,433667°|hombro derecho, roll|0,243997rad/s|

Cada ventana contiene42,04s de estados (incluye reposo antes/después de la
maniobra nominal20s). La cadencia de origen es≈50Hz: máximo intervalo
20,054ms, máximo hueco de recepción31,703ms entre ambos ensayos. No hay
faults ni actuadores deshabilitados en esos mensajes. Cada traza incluye
42.060 diferencias articulares; ninguna supera0,5°. Los registros de paros no
contienen transiciones: **no se midieron ni se acotaron latencia o recorrido
de parada**. La frecuencia de muestreo no demuestra ausencia de picos intermedios.

El revisor separa las muestras de cada eje con velocidad reportada >0,01rad/s.
Etiqueta además como movimiento significativo un recorrido observado≥1°;
son criterios descriptivos de cobertura, no tolerancias de seguridad.
H01 mueve significativamente sólo dos ejes; H02, ocho. Los percentiles quedan
en el JSON por eje y captura, pero no sustituyen el máximo ni permiten descartar
un pico como irrelevante.

| Ejes con movimiento significativo en H02 | Pico izquierdo | Pico derecho |
|---|---:|---:|
| shoulder_roll |0,430625°|0,433667°|
| shoulder_yaw |0,271990°|0,281830°|
| elbow_roll |0,369001°|0,375143°|
| elbow_yaw |0,118245°|0,122326°|

La ruta candidata a ENTRY372 varía más de1° en18ejes. **Diez de ellos carecen
de movimiento significativo en estas capturas emparejadas:** ambos shoulder_pitch,
ambos wrist_pitch/wrist_roll, head_pitch y los tres lifter_pitch. Sus números
en reposo no justifican una cota dinámica. Tampoco se ensayaron carga, inclinación
para vaciar cajas o todos los rangos y velocidades de la misión.

## Comparación geométrica con las mismas condiciones

Ruta archivada HOME con cabeza en observación → READY → ENTRY372, misma
geometría, estados, escena parcial de tablero/caja, margen base2mm y los
1.072pares. Misma profundidad de subdivisión6 y presupuesto90s. Los cuatro
cálculos terminaron sin timeout (22,82–31,49s). Sólo cambia el escenario de
error angular simultáneo por eje; no la configuración del robot.

| Escenario por eje | Certificados en intervalos afines | Avisos nominales del modelo | Sin resolver por cota de error | Sin resolver por resolución | Total sin resolver |
|---|---:|---:|---:|---:|---:|
|±0,1°|1015|54|0|3|3|
|±0,5°|1007|54|5|6|11|
|±1°|995|54|15|8|23|
|±5°|693|54|280|45|325|

Los54avisos nominales son el conjunto conservado anteriormente; no se eliminan
ni se consideran54contactos físicos. Los casos sin resolver tampoco son
colisiones demostradas. El refinamiento puede resolver una falta de resolución;
no convierte automáticamente en válida una cota de error que no demuestra
separación. De los90pares con la escena, quedan respectivamente3,7,12y36sin
resolver. No se declara la escena real completa.

La cota acumulada por radios requiere hasta22,27/103,33/204,66/1015,31mm
para esos cuatro escenarios, incluidos los2mm. Son límites conservadores de
este método, **no desplazamientos predichos o medidos de la abrazadera**.
Reducir incertidumbre ayuda sustancialmente, pero por sí solo no cierra las
interfaces del modelo, la escena ni la ejecución.

## Reproducción y archivos

Herramienta nueva, sólo biblioteca estándar Python:
`scripts/vla/review_tracking_error_traces.py`. Reutiliza el decodificador
canónico de `general_home/trace_analysis.py`, que no se modifica. Añade
rechazo por hueco de origen y fault/deshabilitación antes de la comparación.
Salidas nuevas obligatorias, hashes de fuentes/entradas, sin interfaz física.
Cinco tests nuevos pasan (incluyen picos, ausencia de datos, relojes, campos
emparejados y capturas inválidas). No se instalaron dependencias.

Desde la raíz del repositorio, ejemplo con las dos capturas móviles:

```bash
VLA_EVIDENCE_ROOT=/home/lacuna/proyectos/Robots/Humanoide-vla-evidence
python3 scripts/vla/review_tracking_error_traces.py \
  --input "$VLA_EVIDENCE_ROOT/20260911T082510Z_SUPERVISED-HOME-PREPARATION/trial/trace.jsonl" \
  --input "$VLA_EVIDENCE_ROOT/20260911T084247Z_H02-PICO-SUPERVISED/trial/trace.jsonl" \
  --output /tmp/tracking-review-new.json

for ERROR_DEG in 0.1 0.5 1 5; do
  .venv/general-home/bin/python scripts/vla/review_vla_entry_error_bound.py \
    --access-review "$VLA_EVIDENCE_ROOT/20260914T055526Z_VLA-ENTRY80-OFFLINE/review-filtered/access-review.json" \
    --selection "$VLA_EVIDENCE_ROOT/20260914T055526Z_VLA-ENTRY80-OFFLINE/review-filtered/selection.json" \
    --obstacles "$VLA_EVIDENCE_ROOT/20260911T114330Z_VLA-ENTRY-SCENE/recentered/obstacles.json" \
    --error-degrees "$ERROR_DEG" --subdivision-depth 6 --budget-seconds 90 \
    --output "/tmp/vla-error-${ERROR_DEG}-new.json" || break
done
```

Evidencia privada:
`../Humanoide-vla-evidence/20260914T065216Z_TRACKING-SENSITIVITY/`:
`tracking-review.json`, `tracking-command.json` con las diez entradas,
`scenario-*.json`, logs, `comparison-summary.json` con integridad y causas,
`before/`, `final-sources/`, `verification.json` y `evidence.sha256`.
Las trazas originales permanecen donde indica el informe, con su hash: conservar
esas evidencias junto con el análisis al migrar de equipo.

## Siguiente paso y reversión

Estudiar primero una cota más ajustada por articulación/estado con hipótesis
explícitas, y pedir a UBTECH el campo de consigna aplicada y sus tolerancias
dinámicas. Para elevar ±1° de escenario a límite operativo faltan evidencia de
los ejes/rangos/velocidades/cargas pertinentes, incertidumbre entre muestras y
parada, además de resolver modelo/escena. No hace falta volver a analizar estas
dos trazas sin datos o preguntas nuevos. VLA shadow calificado0/5, tareas físicas0/4.

Instalado/cargado/probado: dos archivos nuevos PC (analizador/tests), ejecutados
sólo offline; nada instalado/cargado/probado físicamente en el robot. Reversión:
retirar esos dos archivos y este informe, y deshacer sólo las entradas de esta
intervención comparando con `before/`, preservando las modificaciones anteriores.
No hay cambios remotos que restaurar. Sin commit/push.


## Afinado posterior del escenario ±1°

**14-09-2026, Europe/Madrid — VERIFICADO offline, no autorización física.**
Por petición del usuario se continuó el estudio de±1°. Primero se aumentó la
profundidad a12: agotó90,066s y conservó54avisos/1018pares sin resolver. Es un
intento incompleto, no empeoramiento físico ni sustituto del resultado acabado
anterior. Su fuente exacta está en `before/` de esta intervención.

Se identificó otro conservadurismo: `RobotGeometry.distances` utiliza la
separación de cajas AABB cuando están a más de4cm, válida como cota inferior
pero potencialmente menor que la distancia entre las superficies del modelo.
Nuevo helper **sólo del revisor offline**
`scripts/vla/refine_entry_pair_distances.py`: después de colocar la geometría
en cada estado, afina con `solid_distance` los pares pendientes cuyo resultado
supera4cm. Conserva contención, geometría, correcciones numéricas, radios,
±1°, margen2mm y todos los1072pares. Una contradicción entre cotas, un valor
no finito o negativo aborta; no se transforma en separación. No se ha cambiado
`general_home/geometry.py` ni el ejecutor físico.

`review_vla_entry_error_bound.py` incorpora `--refine-unresolved-from` y valida
que ese informe completo corresponde al mismo candidato, ruta, escenario,
modelo, escena, entradas y pares sin exenciones. Verifica además que las
fuentes/entradas no cambien durante el cálculo. El predeterminado sigue5°;
±1° se solicita explícitamente y no se exporta como límite runtime.

| ±1°, profundidad6, mismo recorrido | Certificados afines | Avisos nominales | Sin resolver |
|---|---:|---:|---:|
| Antes, distancias rápidas |995|54|23|
| Después, afinado de superficies |997|54|21|

La revisión nueva terminó en54,807s sin timeout. Realizó4411consultas de
sólidos adicionales;4330mejoraron la cota puntual, hasta85,141mm. Es una
mejora de precisión del análisis, no una aceleración ni holgura física nueva.
Los dos pares adicionales certificados son `lifter_pitch_3_link#0` frente a
`R_hand_link#0` y `R_elbow_yaw_link#0` frente al tablero inferido.

Los21pendientes se separan ahora en **10por resolución** y **11por cota de
incertidumbre**. Cuatro casos antes limitados por la cota llegan ahora a
subdivisión, pero siguen sin certificado. Los54avisos nominales conservan
exactamente sus identidades. No se aprueba ENTRY ni se declaran contactos
reales a partir de estos recuentos. Tampoco se ha resuelto escena completa,
seguimiento de los ejes que no se movieron en las capturas, o parada.

Reproducción, con los archivos privados previos:

```bash
VLA_EVIDENCE_ROOT=/home/lacuna/proyectos/Robots/Humanoide-vla-evidence
.venv/general-home/bin/python scripts/vla/review_vla_entry_error_bound.py \
  --access-review "$VLA_EVIDENCE_ROOT/20260914T055526Z_VLA-ENTRY80-OFFLINE/review-filtered/access-review.json" \
  --selection "$VLA_EVIDENCE_ROOT/20260914T055526Z_VLA-ENTRY80-OFFLINE/review-filtered/selection.json" \
  --obstacles "$VLA_EVIDENCE_ROOT/20260911T114330Z_VLA-ENTRY-SCENE/recentered/obstacles.json" \
  --error-degrees 1 --subdivision-depth 6 --budget-seconds 90 \
  --refine-unresolved-from "$VLA_EVIDENCE_ROOT/20260914T065216Z_TRACKING-SENSITIVITY/scenario-1.json" \
  --output /tmp/vla-error1-refined-new.json
```

Evidencia privada nueva:
`../Humanoide-vla-evidence/20260914T070658Z_ENTRY-ERROR1-REFINEMENT/`.
Incluye intento depth12, revisión completada, comandos/logs, comparación por par,
backups, fuentes finales, verificación y hashes. Dieciséis pruebas pasan:
cinco nuevas para refinamiento/proveniencia y once de intervalos existentes.
Sin paquetes nuevos; usa `.venv/general-home`. Cero consultas o cambios remotos,
movimientos, instalación o pruebas físicas. Sin commit/push.

Reaplicación: recuperar el revisor modificado y los dos archivos nuevos
(helper y `test_refine_entry_pair_distances.py`), y ejecutar la receta con las
mismas evidencias. Rollback: restaurar el revisor desde `before/`, retirar los
dos archivos nuevos y sólo estas entradas documentales, conservando el análisis
de trazas anterior y cualquier modificación posterior. No hay rollback remoto.
El siguiente avance debe centrarse en cotas geométricas más ajustadas y evidencia
por articulación; repetir únicamente el cálculo largo sin abordar sus causas
no cierra los11casos limitados por incertidumbre.

## Continuación: cotas locales y otras entradas

La revisión posterior reduce21pendientes a2 con el mismo±1°/2mm, sin
exenciones; incluye censo69, regresiones, lecturas nuevas y límites de cierre.
Véase [ENTRY: cotas locales](ENTRY_COTAS_LOCALES_20260914.md).
