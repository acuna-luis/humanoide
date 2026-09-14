# ENTRY440: contraejemplo con la hipótesis de escena de 50 mm

2026-09-14, Europe/Madrid. **VERIFICADO en el modelo; no contacto físico
observado.** Ficha VLA-01. Intervención exclusivamente en el PC, sin consultas,
movimientos, instalación, recarga o cambios en Motion/Vision.

## Resultado que sustituye el pendiente numérico

El par `R_hand_link#0`–`scene:box_fit` del
[análisis anterior](CIERRE_Y_TOLERANCIAS_ENTRY_20260914.md) ya tiene
contraejemplos concretos. Se conserva ENTRY440, su ruta archivada desde la
observación, la caja del ajuste visual ampliada **50 mm por cara**, el error
articular independiente **±1°**, los sólidos completos y los límites URDF.

| Consulta | Avance READY→ENTRY | Error articular máximo | Resultado FCL |
|---|---:|---:|---|
| Búsqueda en el segmento completo | 98,829790 % | 0,992356° | Intersección de superficies |
| Búsqueda restringida a la postura final | 100 % | 0,934363° | Intersección de superficies |

Ambos resultados se recomputaron en procesos separados desde sus vectores
articulares guardados: límites válidos, perturbación dentro del escenario,
un contacto FCL, distancia FCL −1 (indicador de intersección, **no profundidad**),
distancia conservadora 0 y errores de representación de estas dos piezas 0.
La búsqueda numérica no prueba un mínimo global; **un contraejemplo válido
basta para refutar separación en todo el dominio**. No equivale a observar una
colisión en el robot ni a verificar que su error real alcanza esos valores.

El contraejemplo existe en el extremo: cambiar únicamente los puntos
intermedios conservando ese extremo y el dominio de incertidumbre no basta.
Reducir la separación mínima de 2 mm tampoco elimina una intersección.
No se cambia la ruta de ejecución ni se elimina ningún par del análisis.

## Comprobación con caja sin ampliar

Se retira únicamente la ampliación exploratoria para esta comparación
separada, reconstruyendo las dimensiones originales del mismo ajuste visual.
**Esto no modifica el análisis de aprobación ni la escena del robot.**

En ENTRY440 nominal, la separación del par es **71,391754 mm**. Con la
perturbación del testigo final es **49,904452 mm**.

Además de la intersección con la envolvente ampliada, se construye otra escena
hipotética con la caja original trasladada en `base_link`:

```text
Δ = [−3.098989, −49.786137, +2.638506] mm
norma de Δ = 49.952226 mm
```

Está dentro de una bola traslacional de radio 50 mm y se recomputa un contacto
FCL. Por tanto, el contraejemplo no requiere el crecimiento simultáneo de las
tres dimensiones. **No se ha establecido que esa traslación conserve el apoyo
en la mesa**: pertenece a la hipótesis independiente de registro explorada,
no es una observación de la colocación real de la caja. Una futura hipótesis
acoplada a la mesa debe demostrar sus restricciones antes de sustituirla.

Los 50 mm continúan siendo provisionales; no se convierten en una cota
verificada o en un «óptimo». La separación de fronteras internas, el registro
completo de escena, el seguimiento y la parada mantienen los pendientes de
las fichas anteriores. VLA físico no aprobado.

## Hallazgo sobre los puntos próximos de FCL

En esta consulta BVH, `nearest_points` devolvió los dos puntos en orden inverso
al de los objetos solicitados. Sus distancias a la superficie correspondiente
eran 49,904 mm; al intercambiarlos pertenecen a sus superficies. La primera
traslación exploratoria, antes de corregir el orden, se alejó y **no produjo
contacto**. Se conserva como resultado descartado, sin interpretarlo como prueba.

`ordered_surface_points` verifica la pertenencia mediante distancias a todos
los triángulos transformados y corrige el orden sólo si esa comprobación pasa;
rechaza puntos que no pertenecen a ninguna asignación válida. Tres tests
cubren orden correcto, inverso y puntos inválidos.

Las cotas direccionales anteriores ensayan ambos signos de cada normal: ese
intercambio no modifica sus desigualdades de separación. Sus tests se repiten
junto con los de subdivisión: **11 tests pasan** en total.

## Alternativas examinadas para continuar

Se revisan **113 extremos task0** del informe de dataset con torso a menos de
5° de la vertical y dentro de los límites URDF. Se ordenan por separación
nominal mínima contra la misma escena ampliada 50 mm. Es una selección
geométrica, no un criterio de compatibilidad del VLA ni una nueva tolerancia.

Las tres primeras son `episode_000360`, `episode_000380` y `episode_000410`.
En las tres, acceso por READY y retorno vacío hasta HOME20D producen:

- **1018 pares certificados**, incluidos los **90 pares contra escena**.
- **54 avisos nominales**, exactamente el mismo conjunto de pares internos
  que el informe de referencia; ninguno se excluye.
- **0 pares sin demostrar y ningún timeout**, conservando ±1° y 2 mm.

`alternative-entries.json` contiene los seis análisis completos. La postura
360 se contrasta además con la primera fila del parquet original: identidad
del episodio, task0, timestamp0 y vector articular coincidente exactamente.
Se extrae y revisa su imagen original inicial; hashes en `entry360-source.json`.

**Estas alternativas no sustituyen automáticamente ENTRY440 para la mesa de
80 cm.** Por ejemplo, en ENTRY360 los orígenes sixforce quedan aproximadamente
151 mm más bajos y 201 mm más atrás que en ENTRY440, en `base_link`.
Que el torso esté vertical y la ruta separe sólidos no demuestra compatibilidad
de altura, imagen y alcance con la tarea entrenada. No se cambia ningún
contrato, candidato del ejecutor o configuración en el robot. La selección
geométrica queda preparada para el siguiente contraste de escena y shadow.

## Archivos, estado y evidencia

- PC, nuevos: `scripts/vla/search_entry_fixture_witness.py`,
  `scripts/vla/explain_entry_fixture_witness.py`, su test y
  `scripts/vla/screen_entry_fixture_candidates.py`. Herramientas offline;
  no incluyen conexión al robot ni se integran en el ejecutor.
- Dependencias existentes: `.venv/general-home`, NumPy, SciPy, trimesh y
  python-fcl. No se instala ningún paquete. Chrome headless existente se usa
  sólo para revisar el HTML local, con un perfil temporal separado.
- Evidencia privada: `../Humanoide-vla-evidence/20260914T101305Z_ENTRY50-PROOF/`.
  `search.json`, `verification.json`, `endpoint-search.json`,
  `endpoint-verification.json` y **`translation-verified.json`** son los
  resultados de cálculo; `contraejemplo-entry-verificado.html` es la vista 3D
  autocontenida, revisada mediante `visual-review.png`.
- `translation-proof.json` y `contraejemplo-entry.html` son la **primera
  exploración descartada** por orden de puntos; usar las versiones verificadas.
- `before/` conserva los documentos previos. Versiones intermedias de los
  scripts quedan en `search-source-initial.py` y `explain-source-initial.py`;
  `final-sources/` y `evidence.sha256` preservan la entrega. Los informes
  contienen hashes de modelos y entradas. No basta un commit para reproducir
  estos archivos todavía sin commit.
- Comprobaciones: dos testigos recomputados, caja trasladada recomputada,
  rechazo de un testigo fuera de límites sin crear salida, 11 tests,
  sintaxis JavaScript y renderizado local del HTML correctos.

## Reproducción

Desde la raíz del repositorio, elegir un directorio nuevo de salida. Las rutas
de entrada privadas deben conservarse junto con sus hashes; no requieren robot.

```bash
ENTRY50_OUT="$(mktemp -d /tmp/cruzr-entry50-replay.XXXXXXXX)"
ENTRY50_REVIEW="../Humanoide-vla-evidence/20260914T095214Z_ENTRY-FINAL-GATES/entry440-scene50mm.json"

.venv/general-home/bin/python scripts/vla/search_entry_fixture_witness.py \
  --review "$ENTRY50_REVIEW" --pair 'R_hand_link#0' 'scene:box_fit' \
  --fraction-range 1 1 --output "$ENTRY50_OUT/endpoint.json"

.venv/general-home/bin/python scripts/vla/search_entry_fixture_witness.py \
  --review "$ENTRY50_REVIEW" --pair 'R_hand_link#0' 'scene:box_fit' \
  --verify-witness "$ENTRY50_OUT/endpoint.json" \
  --output "$ENTRY50_OUT/verified.json"

.venv/general-home/bin/python scripts/vla/explain_entry_fixture_witness.py \
  --review "$ENTRY50_REVIEW" --witness "$ENTRY50_OUT/verified.json" \
  --output "$ENTRY50_OUT/translation.json" --html "$ENTRY50_OUT/view.html"

PYTHONPATH=scripts/vla .venv/general-home/bin/python -m unittest \
  test_explain_entry_fixture_witness test_entry_directional_bounds \
  test_entry_subdivided_scene_bounds
```

Omitir `--fraction-range 1 1` busca el segmento completo. Para repetir exactamente
un testigo sin depender de la optimización, pasar el JSON archivado a
`--verify-witness`. Los scripts rechazan sobrescribir resultados.

Para reproducir la revisión de las alternativas:

```bash
.venv/general-home/bin/python scripts/vla/screen_entry_fixture_candidates.py \
  --dataset-report ../Humanoide-vla-evidence/20260904T094803_E6.0Z/dataset-entry-states.json \
  --review "$ENTRY50_REVIEW" --output "$ENTRY50_OUT/alternatives.json"
```

Reversión: las herramientas son nuevas y no tienen activación remota. Para
retirarlas, conservar primero evidencia/fuentes y retirar sólo estos cuatro
archivos y sus referencias documentales. No restaurar configuraciones antiguas
en el robot ni revertir cambios ajenos. Punto de reanudación: corregir o acotar
con evidencia el registro de escena, o seleccionar otro extremo ENTRY y
revisar de nuevo su acceso/retorno; no seguir ampliando presupuesto para
intentar demostrar separación de este dominio ya refutado.
