# Diagnóstico sin robot sobre los datos de entrenamiento

`evaluate_train_only.sh` ejecuta `evaluate_train_offline.py` en contenedor sin
red, robot, ROS, rollout ni Hub. Dataset, checkpoint y volumen de modelos se
montan sólo lectura; la salida debe ser nueva. CPU o CUDA se eligen explícitamente
y CUDA limita memoria al 35 % y exige 8 GiB libres al inicio.

```bash
bash evaluate_train_only.sh /ruta/dataset-v2/lerobot-experiment \
  cruzr-smolvla-ball-public-models-20261109 \
  /ruta/pilot-1000step/run/checkpoints/001000/pretrained_model \
  /ruta/salida_nueva cuda 20261109 60
```

La evaluación carga el checkpoint local, verifica forma 27/8/cámara1, chunk8,
tokenizador local y estadísticas del preprocesador contra el dataset. Para cada
fotograma envía al modelo **sólo imagen, estado e instrucción**; los targets y
acciones futuras se excluyen de la predicción y sólo se consultan después para
comparación. Calcula primera acción, MAE/RMSE por eje, rangos, una comparación
diagnóstica de apertura/cierre con umbral 0,5, latencia y pérdida de
flow-matching estocástica. `predictions.jsonl` conserva semilla, frame e imagen
SHA y tiempos de origen; `report.json` liga sus hashes a los del dataset/modelo.

Son las mismas muestras usadas en entrenamiento: **NO es un conjunto de prueba
independiente** y ninguna métrica prueba generalización, 20 cm, HOME o seguridad.
El modelo sigue sin cualificar para órdenes físicas y el umbral no es una
decisión validada de control. El semillado no garantiza igualdad bit a bit GPU.
El procedimiento se ejecutó en Ada con las 60 muestras del entrenamiento;
véase [el piloto](../../../docs/vla/PELOTA_SMOLVLA_PILOTO_20261109.md) para
el resultado y sus límites. No es una evaluación independiente ni una prueba
de control físico.
