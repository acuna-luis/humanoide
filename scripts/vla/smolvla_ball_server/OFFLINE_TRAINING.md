# Entrenamiento experimental SmolVLA sin robot

`run_offline.sh` sólo admite una imagen local de entorno ya revisada y un
dataset experimental con manifiesto de `convert_ball_candidates_to_lerobot.py`.
Los datos y modelos se montan sólo lectura; la salida debe ser un directorio
nuevo. El contenedor usa `--network none`, no monta servicios ni rutas ROS o
del robot, desactiva Hub y telemetría, limita recursos, reserva margen de VRAM
para servicios compartidos y no ejecuta rollout ni publicación física.

El modelo base y el modelo/tokenizador SmolVLM2 deben existir localmente en el
volumen propio de modelos, en `smolvla_base/` y `smolvlm2_500m_video/`, sin
enlaces que escapen del directorio montado. El volumen se monta sólo lectura. El
runner usa ambos mediante rutas locales y conserva el modelo base sin cambios.
El preprocesador del modelo base se carga con sus configuraciones originales,
con overrides para normalización del dataset y ruta local del tokenizador.
El config vivo explicita estado27, acción8, una cámara y chunk 1–8. A 2 Hz un
chunk de 8 representa 4 segundos; no es un parámetro validado para control.

```bash
bash run_offline.sh --help
bash run_offline.sh /ruta/dataset_bundle cruzr-smolvla-ball-public-models-20261109 \
  /ruta/salida_nueva 100 4 8
```

Los números sólo describen una primera prueba: 100 pasos, batch4, chunk8.
Los límites aceptados son 1–20.000 pasos, batch1–64 y chunk1–8. El runner
registra hashes de entradas, dimensión, hardware y resultado en su salida;
verificar que guarda checkpoint, estadísticas y que la evaluación offline los
puede volver a cargar. El tiempo observado sólo se obtiene al ejecutar.

El modelo resultante sigue siendo un **experimento sin cualificar**. La acción
de brazo es una hipótesis basada en transmisiones históricas y la etiqueta de
mano no es gatillo medido. Los dos episodios provienen de la misma toma, HOME y
20 cm no están demostrados, y no hay test independiente exitoso. No enviarlo al
robot ni publicarlo. El09-11 se completaron offline una prueba GPU de1 paso y
otra de100 pasos; el checkpoint inicial fue auditado con dimensiones27/8,
estadísticas del dataset-v2 y tensores finitos. El piloto de1.000 pasos terminó
en390,12s y se evaluó sobre los mismos datos:58/60 etiquetas provisionales de
mano, dos falsos cierres y error medio de brazo0,05501rad. Esto no es un test
independiente ni se extrapola a control físico.
