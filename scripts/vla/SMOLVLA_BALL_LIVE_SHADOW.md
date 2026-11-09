# SmolVLA pelota: inferencia con observaciones en vivo

La vía conecta lecturas pasivas RGB/20D/7 dedos de Vision con el checkpoint de
pelota en el servidor Ada. El proceso del modelo corre en Docker `--network
none`, sin ROS ni publicador; únicamente devuelve propuestas por stdout. No
controla el robot, no demuestra agarre y no cualifica acciones o parada.

## Preparación en el servidor

Desde la raíz del repositorio, preparar **una ruta privada nueva** en el
servidor (no reutilizar una ruta con datos existentes):

```bash
ssh -p 2649 -o BatchMode=yes -o StrictHostKeyChecking=yes \
  luisacuna@192.168.1.43 \
  'mkdir -m 700 /home/luisacuna/cruzr-smolvla-ball-20261109/live-shadow-NUEVO' && \
rsync --ignore-existing -e 'ssh -p 2649 -o BatchMode=yes -o StrictHostKeyChecking=yes' -- \
  scripts/vla/smolvla_ball_server/shadow_live_inference.sh \
  scripts/vla/smolvla_ball_server/shadow_live_inference.py \
  scripts/vla/smolvla_ball_server/evaluate_failed_offline.py \
  scripts/vla/smolvla_ball_server/evaluate_train_offline.py \
  scripts/vla/smolvla_ball_server/train_offline.py \
  luisacuna@192.168.1.43:/home/luisacuna/cruzr-smolvla-ball-20261109/live-shadow-NUEVO/
```

Comparar los SHA256 de **los cinco archivos** locales y remotos antes de usar
la copia. El wrapper verifica además ID de imagen, volumen, modelo,
normalización y checkpoint; usa un contenedor propio y comprueba su identidad
al limpiarlo. La copia de la intervención del 09-11-2026 está en
`/home/luisacuna/cruzr-smolvla-ball-20261109/live-shadow-20261109-2144/`.

## Ejecutar shadow

```bash
python3 -B scripts/vla/run_ball_live_shadow.py \
  --host luisacuna@192.168.1.43 --port 2649 \
  --runner /home/luisacuna/cruzr-smolvla-ball-20261109/live-shadow-20261109-2144/shadow_live_inference.sh \
  --train /home/luisacuna/cruzr-smolvla-ball-20261109/dataset-v2/lerobot-experiment \
  --volume cruzr-smolvla-ball-public-models-20261109 \
  --checkpoint /home/luisacuna/cruzr-smolvla-ball-20261109/pilot-1000step/run/checkpoints/001000/pretrained_model \
  --device cuda --seconds 20 --fps 0.5 --max-samples 100 --startup-timeout 120
```

El PC descubre el contenedor ROS de Vision y arranca un colector temporal de
sólo suscripción después de `model_ready`. Empareja por nombres y sellos
nominales la imagen y los estados: diferencia de fuente ≤80 ms, recepción de
Vision ≤500 ms. Comprueba hash y formato RGB; descarta observaciones si el
modelo no alcanza el ritmo. La cola está acotada y el tiempo de ejecución
limitado. El stdout contiene propuestas, diferencias y resumen, no imágenes;
los hashes y resultados deben tratarse como evidencia privada.

El tiempo `pc_adapter_to_prediction_seconds` empieza cuando el adaptador del
PC termina de preparar la observación: excluye el transporte Vision→PC y no
es una latencia física completa. Los relojes de los hosts no están calibrados.
Los valores de mano no son comandos validados ni probabilidades calibradas.
Una diferencia entre propuesta y estado no es un movimiento ni una cota de
seguridad. El ejecutor no inspecciona visualmente si se distingue la pelota.

Al terminar o interrumpir, comprobar por separado que no queda el colector
temporal en Vision ni contenedores propios `cruzr-ball-live-shadow-*` activos
en el servidor. La pérdida de SSH no acredita su terminación instantánea;
ambos procesos tienen límites temporales y deben verificarse. No detener
contenedores ajenos. Véase el [registro](../../docs/SYSTEM_CUSTOMIZATIONS.md#smolvla-ball-live-shadow-20261109).
