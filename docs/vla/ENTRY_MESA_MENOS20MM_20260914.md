# Simulación de ENTRY con mesa y caja 20 mm más bajas

2026-09-14, Europe/Madrid. VLA-01. **VERIFICADO sólo en modelo; ENTRY física
sigue PENDIENTE.** Petición autorizada: simular primero la modificación. No se
consultó ni modificó el robot, no se movió mesa/caja y no se instalaron paquetes.

## Resultado

Se conserva HOME → READY → ENTRY372, las mismas20articulaciones y segmentos,
±1° por articulación, margen2mm, sólidos y1072pares. Se desplazan **ambos**
obstáculos archivados (`tabletop_inferred`, `box_inferred`) −0,020m en Z de
`base_link`. No se altera el robot, X/Y, tamaños ni posición relativa caja–mesa.
Es un escenario hipotético de desplazamiento, no una recalibración que demuestre
78cm respecto al suelo: los límites archivados están inferidos en `base_link`
y no son una medición completa y actual del tablero.

| Escenario de la ruta completa | Certificados afines del modelo | Avisos nominales | Pendientes |
|---|---:|---:|---:|
| Escena original |1016|54|2|
| Mesa y caja −20mm |1016|54|2|

La revisión nueva termina sin timeout:5,891s con distancias rápidas y6,043s
con afinado de sólidos. El afinado mejora32consultas, hasta33,057mm, pero no
cambia la clasificación. Los54avisos y los2pendientes conservan exactamente
sus identidades; no hay exclusiones. Pendientes: ambas abrazaderas frente al
tablero, por cota de incertidumbre no demostrada. No son contactos observados.

Además se reevaluaron **las mismas posturas concretas**, encontradas anteriormente
dentro de±1°; no se buscaron nuevos mínimos globales:

| Distancia entre sólidos del modelo en la misma postura | Antes | Con −20mm |
|---|---:|---:|
| Abrazadera izquierda–tablero |32,527mm|32,527mm|
| Abrazadera derecha–tablero |2,107mm|3,408mm|

La mejora del ejemplo derecho es **1,301mm**, no20mm. El cálculo mide separación
mínima entre sólidos tridimensionales, no sólo una altura respecto a la cara
superior. No se puede sumar directamente el descenso del tablero a esa distancia.
Esta comparación puntual tampoco prueba el mínimo de toda la ruta o caja de error.
Con esta evidencia no se recomienda bajar físicamente la mesa como solución
suficiente ni se aprueba ENTRY. Las interfaces del modelo, escena real completa,
seguimiento/interpolación/parada y compatibilidad VLA conservan su estado previo.

## Cambio reproducible del PC

Destino: `scripts/vla/review_vla_entry_error_bound.py`. Opción nueva
`--scene-z-offset-mm`, predeterminada0, expresada enmm y aplicada a **todos los
obstáculos listados**. No es una opción del ejecutor ni toca configuración runtime.
La escena original y sus hashes se conservan; el informe añade desplazamiento,
marca de hipótesis y objetos realmente evaluados. No se falsifica el hash de una
escena modificada como si hubiese sido medida.

Antes de afinar desde otro informe, se exige el mismo desplazamiento. Los
informes antiguos sin ese campo sólo corresponden a0mm. Un informe de0mm no
puede seleccionar pendientes para−20mm; primero se calcula el escenario nuevo.
Entradas vacías/malformadas, dimensiones degeneradas y desplazamientos no finitos
se rechazan. Las comprobaciones originales de candidato, ruta, modelo y fuentes
permanecen. Test nuevo: `scripts/vla/test_review_vla_entry_error_bound.py`.

Verificación: **20tests pasan** en esta intervención (4nuevos,5de afinado y11del
certificador). Sintaxis y `git diff --check` correctos. Dependencias existentes:
`.venv/general-home`; sin nuevos paquetes. Datos privados fuera de Git.

```bash
VLA_EVIDENCE_ROOT=/home/lacuna/proyectos/Robots/Humanoide-vla-evidence
.venv/general-home/bin/python scripts/vla/review_vla_entry_error_bound.py \
  --access-review "$VLA_EVIDENCE_ROOT/20260914T055526Z_VLA-ENTRY80-OFFLINE/review-filtered/access-review.json" \
  --selection "$VLA_EVIDENCE_ROOT/20260914T055526Z_VLA-ENTRY80-OFFLINE/review-filtered/selection.json" \
  --obstacles "$VLA_EVIDENCE_ROOT/20260911T114330Z_VLA-ENTRY-SCENE/recentered/obstacles.json" \
  --error-degrees 1 --subdivision-depth 10 --budget-seconds 90 \
  --local-radius-bounds --scene-z-offset-mm -20 \
  --output /tmp/entry-lower20-base-new.json
```

Para afinar, repetir los mismos argumentos con otra salida nueva y añadir
`--refine-unresolved-from /tmp/entry-lower20-base-new.json`. No reutilizar la
salida de la escena0mm. Ambas revisiones son sólo offline.

Evidencia privada: `../Humanoide-vla-evidence/20260914T080700Z_ENTRY-TABLE-MINUS20MM/`.
Incluye comandos exactos, dos informes completos, logs, script/resultado de
comparación de posturas fijas, `before/`, `final-sources/`, `verification.json`
y `evidence.sha256`. Los20D de cada ejemplo quedan conservados. Los hashes
identifican fuentes locales sin depender de un commit que omita cambios pendientes.

Aplicación tras actualización: recuperar el revisor y su test; ejecutar la receta
con las mismas fuentes privadas. No hay instalación/recarga remota. Rollback:
restaurar el revisor desde `before/`, retirar sólo el test nuevo y actualizar
estas entradas documentales, preservando cambios ajenos y las mejoras anteriores.
Sin commit/push. Ante un cambio físico posterior, medir/registrar escena nueva;
este escenario hipotético no sustituye esa medición.
