# ENTRY410 seleccionada como base para adaptar al escenario

## Actualización: mesa confirmada a 72,5 cm

El operador confirma «72,5, hecho». La altura vigente es **0,725 m desde suelo
hasta la superficie**, declarada por el operador; no se le asigna una precisión
que no haya aportado. Sustituye los 80 cm de la comparación histórica siguiente.
Se actualizan los dos perfiles offline y se repite la selección: continúa 410.
La proximidad al valor inferido de entrenamiento no acredita por sí sola un
agarre válido ni una coincidencia metrológica de milímetros.

Se redescubre Vision `192.168.11.3` y el contenedor `walker-ros.ros2-1`.
`scripts/vla/capture_entry_scene_readonly.py` se ejecuta por stdin, con timeout,
ROS2CLI_DISABLE_DAEMON=1 y `/opt/ros/humble/setup.bash`. No se instala. RGB y
nube comparten marca `1789386829376517000 ns`, TF de ese instante; CameraInfo
marca0. Imagen960×576 y9179 puntos; la imagen permite ver la caja completa y
el tablero. No se infiere de ella control exclusivo, contacto o inmovilidad.
El lector temporal terminó; no se enviaron consignas, servicios de actuación,
reinicios, recargas o cambios de configuración del robot.

**La geometría de la nueva escena aún no se ha validado.** La bajada no se modela
como una traslación vertical exacta sin comprobar los demás desplazamientos.
Los recuentos del comparador proceden de las rutas históricas de 80 cm y no se
recalcularon para la nueva mesa. El perfil vigente lo señala con
`scene_changed_since_geometry_review=true` y `current_scene_geometry_qualified=false`.
La decisión conserva el vector original 410 y `execution_enabled=false`.

Evidencia: `../Humanoide-vla-evidence/20260914T115352Z_ENTRY410-TABLE725/`:
confirmación, discovery, receta SSH/código por hash, captura, imagen y
`comparison725/comparison.json`. `before/` respalda los perfiles/fichas previos;
`final-sources/` y `evidence.sha256` conservan la versión posterior. Para repetir
el ranking usar la receta siguiente con las anotaciones vigentes (objetivo 0,725)
y una salida nueva. La captura se reproduce con el script y el argv archivados;
la lectura no sustituye una comprobación previa a movimiento.

Reversión de configuración PC: perfiles anteriores en `before/`; sólo volver a
80 cm como estado vigente si el operador confirma físicamente ese cambio.
No hay cambio remoto que revertir ni paquetes nuevos. Se verifican JSON, hashes,
selección 410 y diferencias del vector20D original (sin cambios). Sin commit/push.

## Comparación histórica con la mesa a 80 cm

2026-09-14, Europe/Madrid. VLA-01. **Selección offline realizada; ninguna
trayectoria instalada o ejecutada.** Se compara con la última altura de mesa
confirmada: **80 cm**. Proponer 72 cm no fue confirmar que se hubiese cambiado.

## Decisión

Se adopta **el episodio410 como base de adaptación**. Entre los tres candidatos
con revisión completa de acceso/retorno disponible, es el que tiene una altura
de apoyo inferida de su escena original más próxima a 80 cm. Sus ventajas son
de correspondencia con la escena de entrenamiento; no tiene una postura inicial
materialmente diferente de 360/380 ni elimina los requisitos físicos pendientes.

| Episodio | Altura de apoyo inferida del original | Sensibilidad sólo a ±4 píxeles | Mayor diferencia de origen de muñeca respecto a360 |
|---|---:|---:|---:|
| 360 | 64,18 cm | 62,25–66,03 cm | Referencia |
| 380 | 64,17 cm | 62,25–66,00 cm | 0,142 mm |
| **410** | **72,65 cm** | **71,23–74,02 cm** | **0,701 mm** |

La discrepancia nominal de altura es **7,35 cm para 410**, frente a 15,82/15,83 cm
para 360/380. Estas son inferencias bajo las mismas hipótesis de dimensiones de
caja, cámara y origen del suelo, no mediciones certificadas. La preferencia por
410 se conserva dentro de la variación de píxeles analizada; eso no acota los
sesgos de calibración o dimensiones distintas entre episodios.

## Qué representan esos números de ENTRY

360, 380 y 410 identifican **episodios del dataset**. No equivalen necesariamente
a tres poses de aproximación distintas. Se releen sus parquets y primeros
fotogramas originales; task0, frame0, timestamp0 y vectores20D coinciden con los
usados en los análisis. Las imágenes360/380 muestran una colocación muy parecida;
en410 cambia la posición/orientación de la caja en la imagen.

La mayor diferencia articular entre360 y 410 es **0,06043°**. Los tres torsos
resultan prácticamente verticales (menos de 0,017° de inclinación en el modelo).
Cambiar de número no sube de forma apreciable los brazos ni acerca el robot.

Los tres conservan 1018 pares certificados y 54 avisos internos, sin pendientes
por presupuesto, tanto en acceso como en recuperación; 90/90 contra la escena
modelada ampliada 50 mm. La menor separación nominal calculada con esa escena
es 55,21 / 55,11 / 55,10 mm: la diferencia no justifica preferir uno por seguridad.
Los 50 mm siguen siendo una hipótesis de escena y se mantiene ±1° articular.
Estos tres son los revisados en las rutas disponibles: **no se afirma haber
demostrado todas las rutas de los 150 episodios**.

## Estado que queda registrado

- `config/vla/offline/selected_entry_adaptation.json` selecciona 410, conserva
  el vector original y su procedencia. `execution_enabled=false` y
  `physical_approval=false`; no es un contrato runtime.
- `config/vla/offline/entry360_380_410_rim_annotations.json` conserva marcas,
  unidades, altura objetivo e hipótesis comunes.
- `scripts/vla/compare_entry_candidates.py` reproduce la comparación leyendo
  las fuentes originales; no contiene transporte al robot ni modifica tareas.
- Se conserva el trabajo de 360. Sus once pruebas de fronteras y sus borradores
  por etapas no se renombran a 410 ni se consideran automáticamente válidos para
  otro dominio articular, aunque la diferencia de postura sea pequeña.

El siguiente trabajo parte de 410: ajustar la relación cuerpo/brazos/caja a la
escena registrada y comprobar compatibilidad de observación y VLA shadow. Los
7,35 cm **no se convierten directamente en una consigna** de elevador ni en una
orden de bajar la mesa. La adaptación debe conservar alcance, márgenes y un
retorno revisado. Todavía no se ha modificado el vector original de 410.

## Evidencia y reproducción

Evidencia privada:
`../Humanoide-vla-evidence/20260914T113907Z_ENTRY-SELECTION/`.
`comparison/comparison.json` conserva estados, geometría relativa, alturas,
revisiones y hashes de fuentes; las tres imágenes originales se guardan junto
al informe. `checks.json` verifica hashes, reproducción de la altura 360 anterior,
consistencia de selección y estabilidad de preferencia bajo variación de píxeles.

Con los entornos existentes, sin instalar paquetes:

```bash
ENTRY_COMPARE_OUT="$(mktemp -d /tmp/cruzr-entry-comparison.XXXXXXXX)"
PYTHONPATH=.venv/general-home/lib/python3.12/site-packages \
  .venv/vla-scene/bin/python scripts/vla/compare_entry_candidates.py \
  --alternatives ../Humanoide-vla-evidence/20260914T101305Z_ENTRY50-PROOF/alternative-entries.json \
  --dataset cruzrss2_vla_pack-002/data/utars_clamp_and_place_large_box_full_data_bio_lerobot_0319 \
  --registration ../Humanoide-vla-evidence/20260911T114330Z_VLA-ENTRY-SCENE/recentered/metric-scene.json \
  --camera-info ../Humanoide-vla-evidence/20260901T084855_E4.1/artifacts/camera_info.json \
  --annotations config/vla/offline/entry360_380_410_rim_annotations.json \
  --output-dir "$ENTRY_COMPARE_OUT/comparison"
```

Cambios PC bajo VLA-01: las tres fuentes nuevas anteriores y esta decisión en
las fichas global/VLA/plan. `before/` conserva las fichas previas;
`final-sources/` y `evidence.sha256` fijan el resultado reproducible, incluidos
archivos aún sin commit. Reversión: retirar la selección offline y volver a la
referencia 360; no hay cambios remotos que deshacer. Sin conexión al robot,
movimiento, instalación, cambio de checkpoint, commit o push.
