# Piloto offline SmolVLA con pelota — 09-11-2026

**VLA-BALL-OFFLINE-20261109 — VERIFICADO offline; ejecución física pendiente.** El usuario
solicita experimentar con las dos grabaciones existentes; orden futura: tomar
la pelota con mano derecha, elevarla aproximadamente 20 cm, bajarla y soltarla.
La trayectoria debe empezar en HOME y depender de la posición observada. El
usuario autoriza preparar datos y servidor/entrenamiento offline; no autoriza
enviar órdenes al robot. No se ha inferido el estado físico actual.
El usuario aclaró que la pelota comenzará siempre sobre el aro fijo; la pose
del robot respecto de la mesa al iniciar desde HOME queda PENDIENTE.

## Evidencia y segmentación

Las tomas originales son `../Humanoide-vla-evidence/20261109T183246Z_EPISODE_7abf3106/`
y `../Humanoide-vla-evidence/20261109T183726Z_EPISODE_879a137d/`; ambas se
interrumpieron y tienen QC general falso y manos parciales. Se conservan sin
escrituras. La especificación versionada
`config/vla/ball_observation_segments_20261109.json` enumera 12 tramos; los
menos revisados siguen `unreviewed`. La primera toma contiene intentos
incompletos, no una prueba de éxito independiente. La segunda tiene dos
candidatos visuales revisados fotograma a fotograma:

- 579–633: cierre/elevación/depósito visibles; persona recoloca la pelota en
  575–577 antes del tramo. Inicia con la mano cerca de la pelota.
- 935–1008: aproximación, cierre, elevación y depósito visibles, sin intervención
  humana visible durante el tramo; hay oclusión parcial de la pelota.
- 1010–1075 es asistido: persona recoloca el aro en 1033–1036.

Los candidatos proceden de la misma captura, no empiezan en HOME y no hay
medida calibrada que pruebe la altura de 20 cm. Ni el éxito visual ni los
splits exploratorios demuestran éxito físico repetible o generalización.

## Recetas y alcance

```bash
python3 -B scripts/vla/prepare_ball_observations.py \
  --segments config/vla/ball_observation_segments_20261109.json \
  --output ../Humanoide-vla-evidence/20261109_VLA_BALL_OFFLINE_PREP/observations_v2
python3 -B scripts/vla/prepare_ball_candidate_targets.py \
  --observations ../Humanoide-vla-evidence/20261109_VLA_BALL_OFFLINE_PREP/observations_v2 \
  --hardware-snapshot ../Humanoide-vla-evidence/20260914_ARM_MAPPING_LIMITS/hardware-configs.json \
  --output ../Humanoide-vla-evidence/20261109_VLA_BALL_OFFLINE_PREP/candidate_targets
```

Ambos destinos ya existen: son ejemplos reproducibles para rutas nuevas; los
scripts rechazan sobrescribir. La primera salida contiene 12 segmentos/664
fotogramas verificados; la segunda selecciona sólo dos candidatos visuales,
129 fotogramas. Ambas conservan hashes y `training_ready=false`; no son un
dataset LeRobot ni habilitan control. Las etiquetas 5/7 son correlaciones de
apertura/agarre, no gatillo medido ni semántica oficial confirmada.

El snapshot histórico `hardware-configs.json` contiene `transmissions.yaml`
SHA256 `7c7e0760c274c59237ca5787bc2e75096692ee92c43bcf79f61cbad2cfa0f29c`.
Los signos históricos de los siete motores derechos coinciden empíricamente
con los datos de ambas tomas; en la segunda, la diferencia de `cmd_pos`
transformado frente a estado articular medido tiene mediana 0,00133 rad,
percentil95 0,01293 rad y máximo 0,19570 rad. Esta comparación no valida
sincronía física, comando aplicado ni configuración v4 cargada el 09-11.
`cmd_pos` es consigna de motor solicitada sin limitar. Los objetivos
transformados son hipótesis exclusivamente offline, no acciones cualificadas.

La transferencia reproducible se hace desde este PC con
`scripts/vla/smolvla_ball_server/stage_data.sh --help` y `--copy --candidates`
apuntando a `candidate_targets`, `--host luisacuna@192.168.1.43 --port 2649`
y `--remote-dir` a una ruta nueva privada; compara SHA antes y después y copia
el log bruto, el bundle y las fuentes. En `aisrv` usar el wrapper copiado
`tools/convert_on_server.sh --help`, primero `--check` y luego `--run` con
`--staging` y un `--output` nuevo. Se usaron rutas
`/home/luisacuna/cruzr-smolvla-ball-20261109/input-staged-v2/` y
`/home/luisacuna/cruzr-smolvla-ball-20261109/dataset-v2/`; ya existen y no se
deben sobrescribir. Los 60 puntos a 2 Hz tienen entrada y mano nominalmente
anteriores a la consigna, y el sidecar conserva sellos; no implica calibración
física de relojes. La etiqueta de mano emplea la última orden cruda previa,
no sólo la muestra más cercana a cada imagen.

El runner versionado `scripts/vla/smolvla_ball_server/run_offline.sh` documenta
su interfaz en `--help`: recibe bundle LeRobot, volumen de modelos público,
salida nueva, pasos, batch y chunk. Se ejecutó con `dataset-v2/lerobot-experiment`,
`cruzr-smolvla-ball-public-models-20261109` y salidas separadas `smoke-1step/`,
`benchmark-100step/` y `pilot-1000step/`; jamás reusar esos destinos como salida.
Los parámetros son respectivamente `1 1 8`, `100 4 8` y `1000 4 8`. El runner
usa `--network none`, entradas RO, seed1000 y no monta ni publica al robot.
El VLM y codificador visual permanecen congelados. Consultar
`scripts/vla/smolvla_ball_server/OFFLINE_TRAINING.md` para alcance y controles.

## Servidor y deuda abierta

El servidor de entrenamiento se identificó como `aisrv`, RTX 6000 Ada 49.140
MiB y Threadripper PRO; en lectura previa la GPU estaba compartida con Ollama
y tenía 5.500 MiB ocupados. La receta aislada de entorno está en
`scripts/vla/smolvla_ball_server/`; imagen de entorno construida y CUDA
verificada. La copia privada `input-staged/` se comprobó por SHA; conversión
real sin red, GPU ni robot generó `dataset-v1/lerobot-experiment/`, con 60
filas en dos episodios a 2 Hz. Auditoría independiente: 60/60 vectores de
estado/objetivo coinciden con la fuente convertida a float32; las 60 imágenes
conservan píxeles, los hashes y el sidecar de tiempo coinciden. Este dataset
usa objetivos explícitamente hipotéticos y no está cualificado para control;
una comparación con acumulación float64 encontró desviaciones estadísticas
incorrectas en tres ejes casi constantes; se conserva `dataset-v1` sin
sobrescribir y no debe usarse su normalizador. `dataset-v2` se
generó y auditó: 60/60 imágenes/estados/objetivos/sidecar correctos y estadísticas
globales y por episodio coinciden con recálculo float64. Un paso real GPU
completó con pérdida y gradiente finitos; auditoría de checkpoint encontró
500 tensores finitos, 122 modificados y ninguno del VLM congelado. Un ensayo
de 100 pasos/batch4 tardó 45,16 s incluyendo carga y guardado; el piloto de
1.000 pasos completó en390,12s. Evaluación sobre las mismas60 muestras:
error absoluto medio de brazo0,05501rad y58/60 etiquetas provisionales de mano
coinciden al umbral exploratorio0,5, con dos falsos cierres. La revisión
independiente encontró un error puntual máximo0,55891rad; las salidas de mano
no son probabilidades calibradas. Se usan datos de entrenamiento y etiquetas
hipotéticas, no es una cota de movimiento o eficacia. No hay prueba
independiente ni autorización de control físico. Se corrigieron dos etiquetas de suelta
contrastando la última orden cruda antes de la consigna del motor. No se
afirman relojes físicos sincronizados. El estado y reversión del servidor se
registran en la ficha de `docs/SYSTEM_CUSTOMIZATIONS.md`. No usar
`lerobot-rollout` ni conectar un publicador al robot para este piloto.

Pendiente: cualificar las acciones, relojes y modelo de mano; obtener una
evaluación independiente, conservar datos por sesión y no atribuir
generalización al conjunto; definir y validar HOME→zona de agarre y altura de
20 cm. El entrenamiento offline no autoriza movimiento.

## Reversión y respaldo

Fuentes originales y capturas se conservan; retirando exclusivamente las salidas
del piloto y sus fuentes nuevas no se revierten cambios previos del proyecto.
El respaldo previo de documentos vive en
`../Humanoide-vla-evidence/20261109_VLA_BALL_OFFLINE_PREP/before-docs/`.
El checkpoint completo de1.000 pasos y estado de entrenamiento están copiados
en `../Humanoide-vla-evidence/20261109_VLA_BALL_OFFLINE_PREP/checkpoint-backup/001000/`;
los12 archivos se contrastaron con el servidor por SHA256, índice
`checkpoint-backup.sha256` SHA256 `4ef9f58239352720726fcf5dff27f50a6017971c2715968132568752635d021f`.
Comprobar cambios posteriores antes de restaurar. La reversión selectiva del
servidor y las dependencias figuran en la ficha de sistema.
