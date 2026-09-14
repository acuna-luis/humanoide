# Revisión ampliada de ENTRY: resultado y límites de aprobación

2026-09-14, Europe/Madrid. VLA-01. **VERIFICADO offline; aprobación física
PENDIENTE.** Esta intervención sólo modifica herramientas e informes del PC.
No consulta ni modifica el robot, no instala, recarga, reinicia o mueve nada.
Último estado observado: cuerpo/brazos HOME, cabeza en observación; requiere
lectura nueva antes de cualquier ejecución. No se modifica el bloqueo del VLA.

## Resultado que determina la decisión

La trayectoria original HOME→READY→ENTRY372 **no cumple el escenario ±1° con
la escena archivada**. Se encontró y recomputó una intersección de sólidos
entre `R_hand_link#0` y `scene:tabletop_inferred` al 88,171149 % del segundo
tramo. La mayor perturbación es 0,993154°, todos los valores permanecen dentro
de límites articulares. FCL devuelve un contacto, distancia bruta −1 y errores
geométricos declarados de ambos sólidos 0. No se está confundiendo una distancia
reducida por margen con una intersección. **Es un contraejemplo del modelo,
no contacto físico observado ni mínimo global calculado.**

Afinar cotas o aumentar el presupuesto no puede certificar esa misma ruta para
todo ese intervalo. Tampoco demuestra que la mesa real esté en el lugar del
proxy. Se conserva la escena original y no se recorta para obtener un aprobado.

Se preparó además **ENTRY440**, verificando tarea 0, fotograma 0, timestamp 0,
las 20 articulaciones contra el primer registro original y hashes de vídeo y
parquet. La selección visual del borde trasero `[287,319]–[692,314]` en píxeles
sirve para comparar hipótesis de altura, no es calibración del dataset.

| Recorrido y escena | Pares certificados geométricamente | Avisos nominales | Sin demostrar |
|---|---:|---:|---:|
| ENTRY372, proxy original, cotas direccionales | 1017 | 54 | 1: abrazadera derecha–mesa |
| ENTRY440 vía READY, proxy original, cotas direccionales y refinamiento | 1017 | 54 | 1: abrazadera derecha–caja |
| ENTRY372, ajuste visual experimental, acceso y retorno vacío | 1018 | 54 | 0 |
| Igual, ampliando cada sólido 20 mm por cara | 1018 | 54 | 0 |
| Igual, ampliando cada sólido 50 mm por cara | 1017 | 54 | 1 |

Los análisis direccionales terminan sin timeout; el refinamiento de ENTRY440
tarda 5,95 s. Su testigo sin demostrar aparece al 75 % del segundo tramo: cota
de separación 38,770 mm frente a una cota isotrópica requerida 88,384 mm.
**No es una colisión probada de ENTRY440.** Los preanálisis de preparación a
±5° tuvieron un presupuesto de 15 s por ruta y terminaron por timeout: sus
resultados no se presentan como aprobados ni sustituyen el análisis posterior.

## Por qué el ajuste visual no sustituye todavía al proxy

Se ajustaron rectángulos con las dimensiones ya declaradas: tablero
0,84×0,838 m, grosor 0,038 m; caja nominal 0,4×0,6×0,22 m. Dos interpretaciones
del borde de la imagen colocan el centro delantero superior del tablero en
Z=0,628339 y 0,633423 m de `base_link`. El ajuste previo a la nube situaba el
centro de su zona visible en Z=0,668189 m. Son puntos y métodos distintos;
la diferencia de varios centímetros, las inclinaciones ajustadas y los bordes
parcialmente ocluidos no permiten dar por válido un registro con error de 2 mm.

La caja ajustada tiene centro del borde delantero superior
`[0.656912,-0.045131,0.877159] m`. Se probaron 32 perturbaciones reproducibles
de píxeles ±4 px, pero esto sólo cuantifica sensibilidad a esas anotaciones:
no acota sesgos de cámara, sincronización, dimensiones, TF o elección del borde.
Las ampliaciones de 20/50 mm son hipótesis de análisis, **no errores medidos**.
Las patas, travesaños y resto del entorno tampoco quedan registrados por dos
cubos. Todas las salidas mantienen `physical_approval=false` y escena incompleta.

## Mejora matemática implementada

`entry_directional_bounds.py` añade planos separadores con una cota de Taylor
de segundo orden sobre la caja finita de articulaciones. Para cada vértice y
dirección unitaria se calcula la derivada exacta en la postura nominal. La
derivada mixta de dos articulaciones de una cadena queda acotada por el radio
global de la articulación más distal. El resto es `0.5 * h.T * M * h`.
El máximo sobre todos los vértices, con ese resto y los errores geométricos,
acota el soporte del sólido completo. Una separación positiva contra el soporte
de la escena es una cota geométrica válida para esa dirección.

Las normales de FCL sólo proponen direcciones; la validez no depende de que
representen la normal de contacto correcta. Se añaden los ejes cartesianos,
ambos signos y una reserva numérica de 1e-7 m. Se conservan los 1072 pares,
los sólidos, el margen base de 2 mm y el intervalo angular solicitado.
La opción `--directional-bounds` requiere `--local-radius-bounds` y no altera
la ejecución física ni ninguna tolerancia del controlador.

Validación: **28 tests pasan** (ajuste de pose, ampliación de hipótesis,
cotas direccionales, revisión de escena, certificador y refinamiento).
Además, 3216 comparaciones contra distancias de sólidos del modelo real pasan
en perturbaciones finitas de tres posturas. Estas muestras son regresiones;
la cota procede de la derivación anterior, no de asumir que el muestreo cubre
todo el espacio. El contraejemplo se recomputa con una herramienta separada.

## Lo que no puede cerrarse por más cálculos con estas mismas entradas

- Registro de escena y su error total: el ajuste por imagen aún no concuerda
  suficientemente con la nube, y la escena es parcial. Hace falta resolver
  esa discrepancia con una referencia/calibración contrastable antes de usar
  el ajuste como geometría física.
- Las 54 interfaces nominales siguen incluidas. Sus regiones de contacto
  permitido o su representación mecánica no están validadas para esta ruta.
  El hecho de estar presentes en HOME no prueba que todo solapamiento durante
  el movimiento sea inocuo.
- ±1° sigue siendo una hipótesis offline: las trazas existentes no ejercitan
  todos los ejes del acceso. Interpolación aplicada, seguimiento en esos ejes
  y movimiento durante la parada no quedan demostrados por este análisis.

No se ha generado una autorización física, ni conectado el publicador VLA.
Una prueba supervisada necesitaría un alcance justificable con esas condiciones
resueltas; la disponibilidad del E-stop no demuestra por sí sola la separación.

## Reproducción, conservación y reversión

Evidencia privada: `../Humanoide-vla-evidence/20260914T085515Z_ENTRY-CLOSURE-REVIEW/`.
Conserva entradas anotadas, capturas referenciadas por hash, comandos JSON,
informes, contraejemplo, regresiones, fuentes y backups previos. No se añaden
imágenes, datasets o binarios del proveedor a Git. Entornos existentes
`.venv/general-home` y `.venv/vla-scene`; no se instalaron dependencias.

Herramientas nuevas bajo `scripts/vla/`: `fit_entry_fixture_pose.py`,
`review_entry_fixture_hypotheses.py`, `entry_directional_bounds.py`,
`verify_entry_model_witness.py` y sus tests. Se amplía
`review_vla_entry_error_bound.py` con una opción offline explícita.
Los comandos exactos `*-command.json` son arrays de argumentos; se ejecutan
con `subprocess.run(json.load(...), check=True)` desde la raíz, sustituyendo
la salida por una ruta nueva. Preparación de candidatos requiere
`PYTHONPATH=.venv/general-home/lib/python3.12/site-packages` como en la receta
anterior. Los informes nunca se sobrescriben.

Recomprobación independiente del contraejemplo:

```bash
VLA_EVIDENCE_ROOT=/home/lacuna/proyectos/Robots/Humanoide-vla-evidence
VLA_REVIEW="$VLA_EVIDENCE_ROOT/20260914T085515Z_ENTRY-CLOSURE-REVIEW"
.venv/general-home/bin/python scripts/vla/verify_entry_model_witness.py \
  --witness "$VLA_REVIEW/full-segment-probe.json" \
  --review "$VLA_REVIEW/original-scene-directional.json" \
  --access-review "$VLA_EVIDENCE_ROOT/20260914T055526Z_VLA-ENTRY80-OFFLINE/review-filtered/access-review.json" \
  --obstacles "$VLA_EVIDENCE_ROOT/20260911T114330Z_VLA-ENTRY-SCENE/recentered/obstacles.json" \
  --output /tmp/entry-model-witness-new.json
```

Aplicación tras actualización: recuperar estas fuentes y entradas por hash,
verificar compatibilidad del modelo y ejecutar sólo los análisis offline.
No requiere instalación en Motion/Vision. Reversión: restaurar únicamente la
versión previa del revisor desde `before/` y retirar estas herramientas nuevas
y sus anotaciones documentales, preservando cambios anteriores del usuario.
No hay estado remoto que restaurar. Sin commit/push.
