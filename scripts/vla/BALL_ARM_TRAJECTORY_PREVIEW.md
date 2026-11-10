# Vista previa articular de SmolVLA pelota

`ball_arm_trajectory_preview.py` produce muestras **sólo para análisis** de
una propuesta del brazo derecho. No incluye backend, publicador ni transición
de controladores. Su resultado no es una trayectoria ejecutable ni autoriza
movimiento. Tampoco detecta colisiones ni comprueba la escena, el control, la
parada, los relojes o el montaje de las manos.

Recibe un JSON local con los campos `state`, `proposal`, `policy` y `now_ns`
descritos para el guard en [BALL_ARM_PREVIEW_REPLAY.md](BALL_ARM_PREVIEW_REPLAY.md),
además de `sample_count` (entero entre 2 y 1001) y
`locked_stationary_velocity_rad_s` (umbral positivo para cada una de las otras
13 articulaciones). Requiere los 20 nombres, posiciones y velocidades; utiliza
los nombres, no el orden recibido, y retiene los otros 13 valores. Las marcas de
recepción deben pertenecer al mismo reloj monotónico que `now_ns`: el programa
no verifica la sincronización de relojes de equipos distintos.

La política debe proporcionar límites por cada articulación del brazo, edad
máxima y duración. Son datos del usuario, **no límites certificados**. Si el
guard los rechaza, si cualquier articulación está en movimiento según esos
umbrales o si el tiempo resulta insuficiente para las cotas matemáticas, no se
generan muestras. No se recortan propuestas rechazadas. La interpolación usa
un factor mínimo-jerk común para los siete ejes y mantiene el estado del resto;
un conjunto finito de muestras no demuestra ausencia continua de colisiones.

Ejecución local, con una entrada preparada por quien analiza:

```bash
python3 -B scripts/vla/ball_arm_trajectory_preview.py --input /ruta/a/entrada.json
```

La salida JSON sólo se imprime en pantalla; código 0 indica que se generó la
vista, 1 un rechazo de los datos y 2 un error de entrada. El ejemplo sintético
reproducible del esquema y de sus límites se encuentra en `example()` de
`test_ball_arm_trajectory_preview.py`; no representa al robot físico. Pruebas:

```bash
python3 -B -m unittest discover -s scripts/vla -p 'test_ball_arm_trajectory_preview.py' -v
python3 -B -m unittest discover -s scripts/vla -p 'test_ball_arm_preview_guard.py' -v
```
