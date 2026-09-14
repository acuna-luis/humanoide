# Contraste del tablero observado con el volumen usado en ENTRY

2026-09-14, Europe/Madrid. VLA-01. **OBSERVADO/INFERENCIA; no calibración ni
aprobación física.** Revisión offline de la captura posterior a la bajada de
cabeza. No nuevas consultas, movimientos o cambios remotos en esta intervención.
Se mantiene como último estado observado brazos/cuerpo HOME y cabeza−0,43rad.

## Hallazgo que cambia la interpretación

El punto numérico de2,107371mm obtenido antes no representa una separación
vertical sobre una mesa medida. La consulta de puntos más próximos de los
sólidos devuelve estos dos puntos, en `base_link` y metros:

- `[0.499105906956, -0.428900400383, 0.715541292692]`, en el plano frontal
  del tablero virtual (su X mínimo).
- `[0.496998535830, -0.428900400383, 0.715541292692]`, sobre la otra superficie.

Su diferencia está **sólo en X:2,107371mm**. Es el resultado de una postura
concreta dentro de±1°, no mínimo global ni contacto físico. Explica por qué
bajar20mm el volumen no añadió20mm a la distancia. La escena inferida anterior
no debe confundirse con la geometría real medida en esta captura.

Las cotas declaradas que ya constan en la guía VLA son **83,8×84cm y grosor3,8cm**.
El proxy anterior abarca94×92cm y12cm de altura, por holguras exploratorias.
No se necesita pedir otra vez esas dimensiones por defecto; falta ubicar su
contorno actual y acotar el registro. Esas cotas tampoco autorizan recortar el
proxy manteniendo una pose desconocida.

## Nueva revisión de superficie visible

Fuente: nube de10231puntos, intrínsecos y TF de
`20260914T083005Z_ENTRY-HEAD-OBSERVATION`, con caja completa en RGB. Se proyecta
la nube no organizada mediante K; no se usan índices de nube como píxeles.
El análisis selecciona un polígono visible del tablero y excluye la caja,
con anotaciones de píxeles y hashes de imagen/captura/TF.

Un ajuste robusto de plano, con umbral de clasificación5mm y600iteraciones
reproducibles, obtiene117puntos compatibles entre158seleccionados:

| Magnitud de la zona observada | Resultado |
|---|---:|
| Punto medio del ajuste, XYZ base | `[0.613354,-0.109177,0.668189]m` |
| Rango X de puntos compatibles |0,545867–0,724699m|
| Rango Z de puntos compatibles |0,650477–0,682115m|
| Residual95% respecto al plano |4,546mm|
| Inclinación ajustada respecto al Z del modelo |8,163°|

La inclinación es una propiedad del ajuste a esa zona/nube/TF; **no demuestra
que la mesa física esté inclinada8°**. El umbral5mm es un parámetro del ajuste,
no error certificado del sensor, ni reemplazo del margen2mm del planificador.
El residual tampoco limita sesgos, calibración o superficies ocluidas.

El techo del proxy anterior está49,882mm por encima del punto medio ajustado.
Su plano frontal está46,761mm por delante del punto compatible más cercano.
Todos los117puntos compatibles quedan dentro del proxy. Esto demuestra que la
representación antigua contiene esa zona visible con holgura, **no demuestra
que sobren exactamente esas cantidades en todos los bordes reales**. No se
confunden extremos de una nube parcial con los límites de toda la mesa.

Por ello no se recomienda cambiar físicamente la altura ni la posición de la
mesa basándose en los2,11mm anteriores. El siguiente trabajo geométrico es
registrar el tablero de dimensiones conocidas con contornos/oclusión y error
explícitos y después recalcular el acceso. Las54interfaces y seguimiento/parada
siguen pendientes por separado. No se ha cambiado la escena del certificador,
no se ha recortado ningún sólido ni se ha aprobado ENTRY/VLA.

## Herramientas PC y reproducción

Nuevos archivos:
`inspect_entry_table_observation.py` y `test_inspect_entry_table_observation.py`,
bajo `scripts/vla/`. Sólo leen evidencia y escriben un informe nuevo. Validan
formas, coordenadas finitas, frame base, regiones y soporte bidimensional;
rechazan plano degenerado o sin mayoría de puntos compatible con la hipótesis.
No generan contratos de movimiento. Sus salidas llevan explícitamente
`physical_approval=false`, `collision_geometry_changed=false` y
`total_uncertainty_bounded=false`.

Tres tests pasan: selección/exclusión de regiones, plano sintético con ruido
y atípicos, y rechazo de datos insuficientes/degenerados/no finitos. Sin nuevas
dependencias; `.venv/general-home` existente. `git diff --check` correcto.

```bash
VLA_EVIDENCE_ROOT=/home/lacuna/proyectos/Robots/Humanoide-vla-evidence
.venv/general-home/bin/python scripts/vla/inspect_entry_table_observation.py \
  --points "$VLA_EVIDENCE_ROOT/20260914T083005Z_ENTRY-HEAD-OBSERVATION/projected-points.npz" \
  --annotations "$VLA_EVIDENCE_ROOT/20260914T083809Z_ENTRY-SCENE-COMPARISON/annotations.json" \
  --obstacles "$VLA_EVIDENCE_ROOT/20260911T114330Z_VLA-ENTRY-SCENE/recentered/obstacles.json" \
  --output /tmp/entry-visible-table-comparison-new.json
```

Evidencia privada nueva:
`../Humanoide-vla-evidence/20260914T083809Z_ENTRY-SCENE-COMPARISON/`.
Incluye anotaciones, comando/log, informe, diagnóstico de puntos próximos con
fuente y vectores20D, backups documentales, fuentes finales y hashes. No añade
imágenes/nubes ni paquetes del proveedor a Git. Sin commit/push.

Aplicación: recuperar las dos herramientas PC y las entradas privadas por hash;
no requiere instalación/recarga en robot. Reversión: retirar sólo esos dos
archivos nuevos y estas entradas documentales, preservando trabajo previo.
No hay rollback remoto ni movimiento de restauración. El registro actual de
cabeza en observación se conserva en MOT-04 y su evidencia anterior.
