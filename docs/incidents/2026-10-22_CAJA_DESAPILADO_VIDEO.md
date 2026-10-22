# Vídeo de recogida y desapilado de caja — 22-10-2026

**Estado: OBSERVADO en vídeo y fuentes locales; explicación mecánica INFERIDA,
sin confirmación de extracción completa.** Sólo revisión del PC, sin SSH,
movimiento, cambio de código, configuración, fuerza o reintentos.

El operador confirma: **«Continúa, pero no consigue retirar la caja»** y
**«mismas cajas»**. La falta de retirada queda así reportada presencialmente,
no sólo deducida del clip. No se ha confirmado resultado técnico SUCCEED ni
remedido la altura actual del apoyo; usar las mismas cajas no mide la geometría.

## Evidencia conservada

Original: `/home/lacuna/Descargas/MicrosoftTeams-video.mp4`,19,167 s,
720×1280 a30 fps. SHA256:
`e0a0488377efc0e7837d54b787da92aa35a523af3509ca597cdb326bf84515ed`.
Copia íntegra,19 frames de1 fps, hoja de contacto cada2 s, receta de extracción
en `source.json` y respaldo documental en:
`../Humanoide-vla-evidence/20261022T062519Z_BOX_MOTION_VIDEO_DIAG/`.
El vídeo y sus imágenes permanecen fuera de Git; esta ficha conserva la referencia.

## Qué se observa y qué no demuestra

| Tiempo aproximado del clip | Observación |
| --- | --- |
| 0–10 s | Las abrazaderas se aproximan a la caja superior de la pila. |
| Hacia12 s | La placa visible llega al lateral de la caja. La imagen no mide fuerza. |
| 14–16 s | La caja superior se separa parcialmente y se inclina respecto a la inferior. |
| Hacia18 s | La caja vuelve a quedar muy próxima a la pila; no se ve una retirada completa. |

La cámara se mueve y no hay referencia métrica calibrada. No se puede obtener
altura real, holgura, recorrido vertical o fuerza desde estos frames, ni concluir
que hubo deslizamiento, extracción lograda o ayuda física de la persona visible.
La situación actual de caja/brazos tampoco se deduce del vídeo.

## Contraste con la secuencia local del proveedor

El [XML de referencia](../../vendor/ubtech/cruzr_s2/snapshot_20260916/motion/tasks/Singapore/separate_right_cruzr.xml)
prepara cabeza/brazos en3 s, llama a `wrc/separate_right_cruzr` y después a
`wrc/separate_bodyback_cruzr`. El [adaptador frontal](../../scripts/box_handling/front_box_integration.py)
conserva esa secuencia, añadiendo la visión SPS y el nombre local del agarre.
Los tiempos nominales YAML son18 s de separación y6 s de recolocación corporal;
no equivalen a tiempos medidos del clip ni permiten sincronizarlo sin más datos.

El [YAML de separación](../../vendor/ubtech/cruzr_s2/snapshot_20260916/motion/meta_clamp/wrc/separate_right_cruzr.yaml)
incluye offsets Z de±0,06 m y orientaciones de aproximadamente20° en marcos
`CURRENT_RELATIVE`, `RELATIVE` y `SEPARATE_ABSOLUTE`. No significa una elevación
garantizada de6 cm sobre el suelo. La secuencia es compatible con balancear o
inclinar la caja para desencajarla: **INFERENCIA**, no fallo demostrado de
alineación del chasis ni prueba de extracción completa.

Hay admisión de fuerza nominal Y de±20 al final de separación y±5 en
[bodyback](../../vendor/ubtech/cruzr_s2/snapshot_20260916/motion/meta_clamp/wrc/separate_bodyback_cruzr.yaml),
con admitancia activa. Son consignas configuradas, no fuerzas de contacto medidas.
Su relación con el movimiento observado queda PENDIENTE; no se propone subir
fuerza ni repetir automáticamente el agarre. También difieren las geometrías
nominales: separación `[0.603,0.397,0.22]` m y bodyback `[0.6,0.4,0.28]` m.
La compatibilidad con la caja y altura actuales debe comprobarse, sin alterar
estos valores por conjetura.

El [escenario](../../scripts/box_handling/scenario1_contract.py) realiza
`grasp → verify_held → retreat`; el [runtime](../../scripts/box_handling/scenario1_runtime.py)
manda `cruzr/mobot_back_20` sólo después del éxito del agarre y de registrar
sujeción. En optimistic ésta se asume; no es medición física de carga. El
retroceso de chasis de20 cm es posterior y distinto del balanceo de los brazos.

## Diario separado: intento149970

El archivo `latest-optimistic-journal-review.json` conserva el análisis del
diario `20261022T061026Z_OPTIMISTIC_SCENARIO1_149970`, SHA256 de eventos
`1cec46154576a4b4b540e6bd1d1bcd219df3c11dc4625b1bb7e1cea72155135f`.
**La correspondencia entre este diario y el vídeo está PENDIENTE.**

Ese otro intento se interrumpe durante agarre por pérdida de worker y
`estop not confirmed clear`; el mensaje entrante de seguridad no se conserva.
No usar ese fallo para explicar este vídeo: el operador afirma que el movimiento
continúa, y la correspondencia entre ambas ejecuciones no está probada. El foco
actual es por qué el desapilado/sujeción no logra retirar la caja. Fuerza efectiva,
deslizamiento, encaje y geometría relativa siguen siendo hipótesis por comprobar.

## Preguntas y siguiente comprobación

Confirmado que son las mismas cajas y que continúa sin retirarla. Pendientes:
altura actual exacta del apoyo y resultado técnico final de esta ejecución.
Con esas respuestas, contrastar
geometría y fase interna real antes de proponer cambios. No reiniciar desde cero
ni enviar HOME con una caja posiblemente sujeta o dentro de la trayectoria.

Reproducción de la revisión: `source.json` contiene el comando exacto de ffmpeg
usado; los frames y la hoja de contacto son derivados, el original se conserva.
Para releer las fuentes sin acceder al robot:

```bash
sed -n '1,80p' vendor/ubtech/cruzr_s2/snapshot_20260916/motion/tasks/Singapore/separate_right_cruzr.xml
rg -n 'duration:|box_size:|timestamp:|position:|tranform_mode:|desire_force:' vendor/ubtech/cruzr_s2/snapshot_20260916/motion/meta_clamp/wrc/separate_right_cruzr.yaml vendor/ubtech/cruzr_s2/snapshot_20260916/motion/meta_clamp/wrc/separate_bodyback_cruzr.yaml
```

Sólo hallazgo documental: sin tests nuevos, cambios del sistema, commit o push.
Reversión de esta ficha/notas selectiva desde el respaldo; conservar vídeo y
diario originales. No hay configuración del robot que revertir.
