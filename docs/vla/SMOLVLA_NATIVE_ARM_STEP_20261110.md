# Paso de brazo derecho para SmolVLA mediante MetaMove — 10-11-2026

**Estado: conversión offline preparada; ejecución física PENDIENTE.** El
usuario solicitó acortar la prueba y reutilizar lo ya disponible. Las tareas
de fábrica y `scripts/custom_tasks/heart_v4_fingers.xml` muestran el formato
`MetaMove`, `type="arm"`, `location="right"` y `joint_angles` de siete valores.
Esto abre una vía para estudiar objetivos sucesivos con el controlador de
manipulación, sin asumir que haya que alimentar el SDK directo a 100 Hz.

[`prepare_ball_native_arm_step.py`](../../scripts/vla/prepare_ball_native_arm_step.py)
lee un resultado shadow JSONL completo mediante el auditor existente. Verifica
el checkpoint y la estructura, deriva el estado de los siete ejes de brazo a
partir de la predicción y su diferencia registrada, y limita cada diferencia
al valor solicitado por quien ejecuta el análisis. Emite por stdout un JSON con
los valores originales y limitados, el orden hipotético y un único XML candidato
`MetaMove type="arm" location="right"`. No instala archivos en Motion, no
crea clientes ROS, no envía órdenes y `--run` devuelve 2 sin conectar.

Este es un **borrador para revisar, no una tarea habilitada**:

* El orden de siete ejes y el significado de las metas del modelo aún no se
  han cualificado para esa ruta `MetaMove` en esta unidad.
* El parámetro de salto y la duración son experimentales; no son límites de
  seguridad ni comprueban velocidad, aceleración, colisión o parada. Recortar
  una propuesta altera la política y puede impedir completar la tarea.
* La entrada es una grabación: no acredita el estado actual, frescura o
  sincronía. No contiene control de dedos ni detección de agarre o apoyo.
* La ejecución de `MetaMove` en esta postura, la aceptación del formato y su
  cancelación/retorno siguen sin verificarse; no instalar ni ejecutar este XML
  como resultado del diagnóstico.

Reproducción con el shadow ya existente, sin repetir captura o inferencia:

```bash
python3 -B scripts/vla/prepare_ball_native_arm_step.py \
  --check ../Humanoide-vla-evidence/20261109_SMOLVLA_LIVE_SHADOW/live-run.jsonl \
  --sample 0 --max-step-rad 0.05 --duration-s 4
python3 -B -m unittest discover -s scripts/vla -p 'test_prepare_ball_native_arm_step.py' -v
```

El ejemplo de 0,05 rad y 4 s es sólo para revisar el formato, no una elección
validada para mover el brazo. Con esa primera muestra se produjeron siete
diferencias candidatas limitadas a 0,05 rad; `physical_control_qualified=false`
y `physical_commands_sent=0`. Los cuatro tests locales pasan. La muestra es
del 09-11, anterior al movimiento de cabeza; no describe la escena actual.
Entrada SHA256 `5be819ea4a7941c3b136c40aa66494bbda42c5b6b116fbe431686cf2b85e8131`.

Para pasar a un ciclo físico sigue faltando conectar observaciones y acciones
en tiempo real, comprobar el orden y la parada de la tarea de brazo, y disponer
de una orden de mano con límites/confirmación de agarre y suelta. Ver la
[auditoría del SDK y mano](SMOLVLA_SDK_COMMAND_AGE_20261110.md).
