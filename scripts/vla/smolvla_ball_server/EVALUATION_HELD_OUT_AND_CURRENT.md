# Inferencia offline con observaciones fallidas o sin revisar

Este diagnóstico procesa imágenes y estado grabados, sin objetivos ni acciones
futuras como entrada al modelo. El modelo, el normalizador y las estadísticas
son los del piloto de 1.000 pasos; tanto éstos como el VLM y su tokenizador se
contrastan contra hashes fijados. El contenedor usa `--network none`, imagen
con ID fijado y entradas sólo lectura; sólo escribe en un directorio nuevo.

Una captura diferente de las de entrenamiento no es una prueba independiente
de éxito. La primera toma contiene intentos fallidos; la captura actual no está
revisada. No son rollouts cerrados, no prueban agarre ni 20 cm y no habilitan
control físico. Los relojes no están calibrados. Una diferencia entre propuesta
articular y estado capturado no es desplazamiento real, error respecto a una
trayectoria correcta, ni límite de seguridad. La salida de mano no es una
probabilidad ni una orden validada.

Para crear un paquete de observaciones fallidas, con fuentes íntegras y un
destino nuevo en el PC:

```bash
python3 -B scripts/vla/prepare_ball_failed_observations.py \
  --observations /ruta/observations_v2 --output /ruta_nueva/failed_observations
```

El exportador rechaza fuentes ajenas o alteradas, referencias incompatibles,
estado recibido después de la imagen y estados con
edad nominal mayor de 80 ms o edad de recepción mayor de 500 ms. Sólo selecciona
los dos segmentos fallidos, sin convertirlos a ejemplos de entrenamiento.
El evaluador rechaza que el hash de la captura de prueba coincida con uno de
los usados para entrenar.
Para la captura actual, usar `prepare_ball_current_observations.py --help`;
ésta conserva su estado `unreviewed`.

En el servidor, con los scripts y un paquete privado de observaciones ya
transferidos y contrastados por SHA256, ejecutar un único comando con salida
inexistente, el dataset de entrenamiento original y checkpoint originales:

```bash
bash evaluate_failed_only.sh TEST TRAIN MODEL_VOLUME CHECKPOINT OUTPUT_NUEVO cuda SEED TEST_MANIFEST_SHA256
bash evaluate_current_only.sh OBSERVACIONES TRAIN MODEL_VOLUME CHECKPOINT OUTPUT_NUEVO cuda SEED TEST_MANIFEST_SHA256
```

`TEST_MANIFEST_SHA256` debe obtenerse en el PC antes de la transferencia y
contrastarse en el servidor. No copiar personas ni datos privados fuera del
servidor autorizado. Cada ejecución produce `predictions.jsonl` y `report.json`;
la propuesta se expresa respecto al estado capturado, por nombre de eje.
Entradas y resultados son privados. Una ejecución fallida puede dejar una salida
parcial: conservarla para diagnóstico y elegir otra ruta nueva.
