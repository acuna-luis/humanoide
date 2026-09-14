# Observación física de ENTRY: cabeza y escena actual

2026-09-14, Europe/Madrid. MOT-04/VLA-01. **VERIFICADO: movimiento de cabeza
terminado, lecturas posteriores inmóviles. OBSERVADO: caja y tablero visibles.
PENDIENTE: aprobación ENTRY, escena completa con error acotado y VLA físico.**

El usuario respondió «adelante» a la preparación de bajar sólo la cabeza,
tras pedir confirmación de ruedas bloqueadas, cabeza/cuello libres, ningún
mando y operador junto al paro. No se extendió esa autorización a ENTRY,
agarre, movimientos de brazos/base o instalación de tareas.

## Acción realizada y estado final

Preflight canónico `cruzr_blue_workbin_cycle.sh --check` correcto; también se
leyeron articulaciones, RobotCommand, locks y estado de acción. Inicialmente:
HOME numérico, máximo absoluto0,002780340178rad, velocidades0; writers0,
locks libres y última acción status4. Baterías≈83%, paros0/0, cargador libre,
actuadores habilitados y efector `cruzr_s2_v1`. El ejecutor volvió a comprobar
estos gates antes de actuar (baterías82,8/82,0%).

Una ejecución de:

```bash
./scripts/cruzr_blue_workbin_cycle.sh --prepare-vision --yes
```

Envió únicamente `cruzr/move_head_lower` al servidor
`/mc/manipulation/action`, tipo `mc_task_msgs/action/ArmTask`.
Goal: `9c5b17c1-7fc6-407b-8bdb-7636873eea9e`.
Motion: `SUCCEED`, status4. Sin reintento automático. XML existente verificado
por hash `f3a73626f97b471d4a0a03c98c24de32243651116c497328e69b5ddc57ea46c1`;
objetivo histórico verificado yaw0/pitch−0,43rad en2s. No install/reload/restart.

Lectura final: `head_pitch_joint=-0.43066510619889375rad`,
`head_yaw_joint=-0.0003834951969714103rad`, velocidades0. Diferencia máxima
entre extremos de los restantes ángulos: **0rad**. No se enviaron comandos de
brazos, torso o chasis. La comparación de extremos no es una traza continua.

**Estado dejado: brazos/cuerpo en HOME numérico, cabeza en observación;
no es HOME20D completo.** No se envió HOME para deshacerlo con la mesa delante.
No hay confirmación verbal posterior de suavidad; sí resultado Motion y lectura
inmóvil. El VLA no se inició ni se enviaron chunks físicos.

## Nueva percepción

Captura pasiva mediante ROS2 en Vision, contenedor redescubierto
`walker-ros.ros2-1`, setup `/opt/ros/humble/setup.bash`:
RGB BGR8 960×576, nube original10231puntos, frame
`stereo_left_rectified_optical_frame`. Se conservan datos binarios completos,
layout y campos de la nube, intrínsecos y PNG. Ahora se ven la caja completa y
el borde cercano del tablero. No se afirma que el volumen completo, patas,
soportes u objetos ocluidos estén medidos.

Lectura TF posterior `base_link ← stereo_left_rectified_optical_frame`:
traslación `[0.1572981833,0.0365280625,1.5067698788]m`, cuaternión xyzw
`[0.6001256758,-0.5907260807,0.3835948837,-0.3791395996]`.
Se conserva stamp de TF. RGB/nube/joints/TF son lecturas sucesivas en postura
inmóvil, no captura sincronizada por hardware ni registro con incertidumbre
certificada.

Inspección exploratoria por regiones de píxeles, proyectando XYZ con K y TF:

| Región visible | Puntos | Mediana X de base | Mediana Z de base |
|---|---:|---:|---:|
| Franja expuesta frontal del tablero |51|0,61556m|0,66631m|
| Cara frontal visible de la caja |115|0,65872m|0,77059m|
| Zona del borde posterior de la caja |47|1,03491m|0,87596m|

No son distancias desde el parachoques ni órdenes de avance del chasis. Tampoco
son extremos conservadores de colisión: cuantiles no garantizan contención,
las regiones pueden incluir bordes y la profundidad tiene error no acotado.
Un ajuste PCA de la franja del tablero da normal
`[-0.22059,0.04159,0.97448]` y residual95%4,149mm; ese ajuste regional no demuestra
inclinación real de la mesa ni calibración de2mm. No se sustituye la escena
canónica por esos pocos puntos. La altura de80cm sigue siendo declaración
física del usuario; Z de base no es directamente altura sobre el suelo.

## Evidencia, reproducción y continuidad

Evidencia privada:
`../Humanoide-vla-evidence/20260914T083005Z_ENTRY-HEAD-OBSERVATION/`.
Incluye antes/después, comandos, fuente exacta del ejecutor y hash, goal/log,
script/captura pasiva, TF, inspección por regiones, resultados, backups
anteriores de documentos, fuentes finales y `evidence.sha256`.

La receta física ya versionada es la rama `--prepare-vision`, precedida de
`--check` y comprobación física actual; no ejecutar por copiar esta nota si
cambió el estado. La receta de captura pasiva y análisis de evidencia queda en
`capture-dense.py`, `capture-tf.py` y `measure-visible-surfaces.py` del paquete
privado de evidencia, identificados por checksum. Para conservar después de
firmware no hace falta restaurar una postura transitoria: recuperar únicamente
la tarea compatible y el script descritos en MOT-04, comprobar hashes y estado.
No se cambió firmware, archivo remoto, paquete, servicio o configuración.

Prueba de esta intervención: ejecución física limitada a cabeza exitosa,
postestado inmóvil y lectura/captura útiles. No se modificó código del ejecutor;
no hacen falta tests nuevos que imiten la acción. Documentación verificada con
`git diff --check`. Sin commit/push. Se preservó todo el trabajo previo.

Siguiente trabajo: completar el registro de superficies y contornos visibles
con incertidumbre y oclusiones explícitas antes de recalcular ENTRY. La mejora
de encuadre no resuelve por sí misma los avisos de interfaces ni la evidencia
de seguimiento/parada. Mesa, caja y base se dejan como estaban.
