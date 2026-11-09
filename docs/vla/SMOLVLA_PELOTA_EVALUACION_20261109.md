# Evaluación offline de SmolVLA y revisión de cabeza — 09-11-2026

**VLA-BALL-SHADOW-20261109 — VERIFICADO sin movimiento; control físico
PENDIENTE.** El usuario solicitó instalar y ejecutar el SmolVLA de pelota en
el robot y autorizó expresamente mover sólo la cabeza para ver el aro. Confirmó
manos vacías, trayectoria de cabeza despejada, ruedas bloqueadas, cargador
desconectado, paros accesibles y persona junto al paro, y que nadie manejaba el
robot. Posteriormente confirmó que la pelota estaba sobre el aro. Estas
confirmaciones son del momento, no acreditan el estado físico posterior.

## Lectura y observación pasiva

Motion/Vision respondieron por la red; Motion anunció configuración
`HW_TYPE=cruzr_s2_v1_sps` y PICO, con mano derecha publicando siete ejes.
La telemetría puntual registró paros 0/0, cargador0 y baterías98,2/98,3 %;
no sustituye comprobación presencial ni debe extrapolarse. El modo/enable
no se identificó inequívocamente. Alrededor de 21:23 Europe/Madrid se leyó
un goal de manipulación `EXECUTING`, UUID
`753bc615-0293-441c-bc55-fb8452810533`. Su sello coincide con el inicio
histórico de `teleoperation/cruzr_v4_pico_teleoperation` en el log, pero éste
no contiene el UUID: es correlación, no identificación directa; EXECUTING no
demuestra movimiento físico. No se canceló el goal ni se cambió modo.
Lectura posterior en `head-technical-read.json` confirmó la misma acción
status2 y un cliente/servidor; la consulta directa de cabeza agotó el plazo
(rc124). SHA256 de esta lectura:
`265cc83853ae3486289c6d01f45a98fc176e9b2685fc423a4e8150a462f0d4c0`.

De 21:19:46 a 21:19:55 Europe/Madrid se ejecutó una captura pasiva de5s con
`scripts/vla/capture_passive_episode.py` dentro de `walker-ros.ros2-1` de
Vision. Terminó rc0 y el proceso de lectura terminó. Guardó23 imágenes,22
pares RGB/estado y132 estados válidos de mano derecha; QC base y mano derecha
`true`. En fotogramas revisados la cámara apunta al fondo y no se distingue
claramente el aro cercano, aunque el operador confirma que la pelota estaba
colocada. La cabeza medida en esa captura estaba próxima a yaw0 y pitch0;
datos medidos no validan la escena física posterior. Diagnóstico de
normalización en22 muestras: yaw y pitch de cabeza alcanzaron ~32,6 y ~9,2
desviaciones típicas de entrenamiento; no son límites de seguridad ni prueba
de sincronía física. Se calcularon como máximo de `abs((q−media)/(std+1e-8))`
con `training-stats.json` y las22 filas de `aligned.jsonl`; fuente y resultado
están en `normalization-diagnostic.json`. Evidencia y originales preservados bajo
`../Humanoide-vla-evidence/20261109_BALL_SHADOW_ASSESSMENT/`.

La tarea instalada `cruzr/move_head_lower` SHA256
`f3a73626f97b471d4a0a03c98c24de32243651116c497328e69b5ddc57ea46c1`
declara únicamente cabeza yaw0/pitch−0,43 rad,2 s. Su ejecutor cualificado
exige HOME20D; la postura leída era PICO, no HOME. El otro flujo disponible
exige ausencia de acción activa y perfil de abrazaderas, frente al perfil SPS.
No se saltaron esos gates, no se cambió modo, no se envió HOME ni se movió la
cabeza. El seguimiento de cabeza en PICO es histórico y no demuestra una vía
actual segura para reactivarlo aisladamente. El bloqueo es técnico, no falta
de autorización del usuario.

## Inferencias aisladas

En servidor `aisrv`, la nueva carpeta privada
`/home/luisacuna/cruzr-smolvla-ball-20261109/assessment-20261109-shadow/`
contiene observaciones, fuentes y resultados; no altera el checkpoint o dataset
previos. Ambos procesos usaron imagen y modelos verificados, GPU, entradas RO,
`--network none`, sin ROS ni conexión al robot. Cinco observaciones de la
captura actual y siete de intentos fallidos de otra captura se evaluaron de
una en una; son propuestas abiertas, no trayectoria en bucle cerrado.

| Entrada | Mayor diferencia propuesta articular − estado observado | Salida de mano |
| --- | --- | --- |
| Actual,5 muestras | `R_elbow_yaw_joint` +1,167653 rad (~66,9°), fotograma2 | 0,77048–0,94528 |
| Intentos fallidos,7 muestras | `R_elbow_roll_joint` −0,688391 rad (~−39,4°), fotograma387 | 0,39825–0,90509 |

Una revisión independiente verificó hashes y recalculó por nombre todas las84
diferencias sin discrepancia. Las salidas de mano no son probabilidades ni
comandos cualificados. Las diferencias son propuestas individuales, no
movimientos ejecutados, error frente a la trayectoria correcta ni cotas de
seguridad. El aro no era distinguible en la captura actual y la otra captura
contiene intentos fallidos: no son prueba de agarre exitoso o generalización.
La semántica de comandos, relojes y seguimiento/parada siguen sin cualificar;
ninguna de estas inferencias habilita publicación o ejecución física.

## Fuentes, verificación y reversión

Recetas versionadas:
`scripts/vla/prepare_ball_current_observations.py`,
`scripts/vla/prepare_ball_failed_observations.py` y
`scripts/vla/smolvla_ball_server/EVALUATION_HELD_OUT_AND_CURRENT.md` con sus
evaluadores y wrappers sin red ni publicador. Se verificaron causalidad nominal,
procedencia, datos, checkpoint y normalización; 17 pruebas locales pasaron.
El manifiesto `server/assessment-provenance.json` tiene SHA256
`8b493e5fd7d9b7df98e5eb36386ff7ff925333967fc2c44d32d301a6f2f5f960` y enlaza
hashes de 13 evidencias y recetas. Los informes actuales y fallidos tienen
SHA256 `febef434c3f1e100e61fe10daa07ab40e28c2b77d0f2d849850e9c9a5eaaa3c4`
y `9f7bf333fcaa42e9f87aa755e80d7d0da608238ad345e8c5b383ef8287f9ecc1`.
GPU volvió a 5.500 MiB en uso y sin contenedores propios de evaluación activos;
servicios existentes conservados. Fuentes, observaciones y resultados privados
no se añaden a Git.

Restauración: no se cambiaron archivos ni parámetros persistentes del robot.
Preservar y comparar primero cualquier trabajo posterior; retirar sólo las
fuentes y resultados nuevos de esta intervención y, si procede, la carpeta
privada propia del servidor, sin borrar dataset/checkpoint anteriores ni
servicios, imágenes, volúmenes o caché ajenos. Documentos previos en
`../Humanoide-vla-evidence/20261109_BALL_SHADOW_ASSESSMENT/before-docs/`;
índice `before-docs.sha256` SHA256
`37ef71561af90afe6a3a2685f02d0bbfb2c6153136b4c8dabe48ff6727acfd4e`.
