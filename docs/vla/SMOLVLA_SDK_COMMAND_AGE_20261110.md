# SmolVLA: antigüedad de comandos SDK — 10-11-2026

**Estado: análisis estático OBSERVADO; control físico y parada PENDIENTES.**
El usuario solicitó continuar la ejecución del modelo y confirmó manos vacías,
pelota en el aro, despeje, ruedas bloqueadas, cargador fuera, paros accesibles
con persona presente y ausencia de otros mandos. No se enviaron órdenes al
brazo o mano, ni se cambió controlador. La confirmación física no se traslada
automáticamente a una actuación posterior.

## Control de brazo

El último shadow con la cabeza bajada produjo cuatro propuestas, sin órdenes;
la máxima diferencia propuesta−estado fue 1,146906 rad. La red ya funciona,
pero un objetivo del modelo no es una trayectoria validada. La vía SDK previa
está acoplada a otro VLA, otra postura y abrazaderas; el cambio a SDK quedó
históricamente sin acuse. La consulta actual ROSA muestra `manipulation_controller`
en `running` y `vla_sdk_controller` en `initialized`, clase
`sdk_controller::StandardSdkController`. Un topic con suscriptores no demuestra
que el controlador tenga autoridad.

En Motion, la biblioteca instalada
`/opt/walker/sdk_controller/lib/libsdk_controller.so`, SHA256
`e77cc237226e08f5c833d6f2db5a3ccda88598acadcfa63e741a1c7b80932c96`, aparece
mapeada por `rosa_control_node` en `walker-motion.hw-1`. El mapeo y el hash del
archivo no garantizan por sí solos que los bytes en memoria sean idénticos.
Análisis estático de esa versión:

* El valor double en `.rodata` `0x51c38` es 0,01 segundos. En `update`, cuando
  la comprobación de fecha de comando está habilitada, se compara por junta
  la edad con ese umbral. Si es mayor, la rama analizada omite la escritura de
  comando de esa junta; no se observó en esa rama una orden de mantener la
  posición medida ni de poner velocidad cero.
* `starting` activa una bandera de comprobación. Existe un callback para
  desactivarla, pero no se llamó ni se ha verificado el valor de la bandera en
  runtime. No desactivar esa comprobación para hacer funcionar el puente.
* La rama inspeccionada **no demuestra qué hace el servo con la última
  consigna** ni una parada física. Destruir el publicador tampoco demuestra
  cancelación. Las rutas de vuelta a manipulación no están cualificadas como
  parada.

La inferencia Ada observada tardó 0,168–0,595 s por propuesta. Si la
comprobación de 10 ms está activa, esas propuestas no bastan por sí solas como
flujo directo de comandos: hace falta un ejecutor local que produzca y supervise
el flujo dentro del plazo, además de una estrategia de parada y recuperación
comprobada. Un período teórico de 10 ms no proporciona margen frente a jitter.
El análisis estático no demuestra que el watchdog esté activo ni que ese
transporte sea seguro.

Se examinó también una posible vía de alto nivel. El componente instalado
`libmeta_move.so`, SHA256
`bfeab1c7a295b58cd96fddd20916fc3f7fe16bd8c8ad1e77720f48aad34ccc69`,
contiene lectura de `task_json_args` con claves `component_names` y `goals`;
el desensamblado trata `goals` como una matriz de números. Esto sugiere una
forma de suministrar objetivos variables sin usar directamente el topic SDK.
Sin embargo, el catálogo consultado no registró `move_right_arm_planning`
como tarea individual. La tarea disponible
`move_dual_arms_parallel_planning` lanza objetivos de ambos brazos. No se
ha demostrado qué llamada alimenta esos argumentos para una tarea aislada
derecha, ni sus efectos, límites o parada desde PICO/v4. No se ejecutaron
esas tareas ni se instaló una nueva.

Como posible punto de investigación, el servicio anunciado
`/mc/manipulation/service` usa `mc_task_msgs/srv/WalkerMotion`, con campos
`motion_id`, `json_args` y `cmd` para inicio/parada. El nombre del campo
`stop` no demuestra su efecto físico. El `robot_app` instalado escribe
`task_json_args` en un blackboard y MetaMove lee `component_names`, `goals`
y `durations`, pero no se ha demostrado el enlace completo para una tarea
individual derecha. El XML bilateral disponible tiene SHA256
`cb369902b1e139eb8949ced9bc8fa5f6816fdf6606b76f3d3022f3713b8ae27a`; el YAML
derecho aislado en disco, no registrado como tarea individual, tiene SHA256
`676a608daee33eb250589622f01181bfcf329fca64baf423cfb05ae326671578`.
No se llamó al servicio ni a su orden de parada.

El manual SDK §5.1.2 incluye un ejemplo de publicación a 500 Hz, pero no
especifica una orden de cancelación o frenado del setpoint SDK. El §2.6
describe recuperar autoridad mediante `cc.api.sdk.switch_mc_mode` en modo
`normal`; no demuestra equivalencia con el servicio `motion_sdk` instalado ni
que eso frene una consigna en curso. El comportamiento documentado para un
fallo de comunicación de servo no debe extrapolarse a la pérdida del publicador
ROS; no se provocó ningún fallo para probarlo.

## Mano derecha

La biblioteca PICO instalada `libmeta_teleoperation.so`, SHA256
`05187431f27915bb2c869ca566ade88ca9adc302087a4fe9e20e658ce28a45c8`,
contiene una rama v4 que lee el estado de dedos, mantiene banderas de
sobrecorriente por dedo y envía el comando de mano. Pertenece al objeto C++
`Teleoperation`: no se ha encontrado una API documentada para reutilizar sólo
la derecha conservando esa lógica. La configuración PICO declara
`init_reset=true`; volver a cargarla podría afectar brazos y manos.

Las tareas de fábrica individuales de apertura/cierre usan posiciones fijas;
no se ha demostrado que preserven el control por corriente y sobrecorriente
del gatillo PICO ni que sean adecuadas para agarrar esta pelota. El escalar de
SmolVLA no está calibrado como orden o probabilidad de cierre; no convertirlo
directamente a un comando de dedos.

Una búsqueda acotada en los XML instalados encontró 13 archivos con alguna
acción de efector derecho de siete valores y `controller_mode="2"`; ninguno
contenía únicamente esas acciones: incluían también brazos, otra mano o torso.
La tarea aislada hallada con nombre de cierre por corriente es de v3 y seis
ejes. La biblioteca MetaMove lee el atributo como entero; en otra biblioteca
el enum interno 2 se identifica como `kTorque`. Estas piezas no demuestran la
conversión completa XML→hardware, unidades, protección PICO ni parada. No se
ejecutó ninguna de esas tareas.

## Reproducción de la lectura estática

Redescubrir primero los contenedores y PID; no asumir que nombres o PID
persisten tras reinicio o actualización. La siguiente consulta sólo lee la
biblioteca instalada y no invoca servicios de control:

```bash
python3 -B - <<'PY'
import sys
sys.path.insert(0, 'scripts')
from collect_estop_available_readonly import execute
lib = '/opt/walker/sdk_controller/lib/libsdk_controller.so'
for args in (
    ['sha256sum', lib],
    ['objdump', '-s', '--start-address=0x51c38', '--stop-address=0x51c40', lib],
    ['objdump', '-dC', '--start-address=0x4cfc2', '--stop-address=0x4d0e6', lib],
    ['objdump', '-dC', '--start-address=0x4d323', '--stop-address=0x4d3c4', lib],
    ['objdump', '-dC', '--start-address=0x2a500', '--stop-address=0x2a670', lib],
):
    result = execute('motion', ['docker', 'exec', 'walker-motion.hw-1', *args])
    if result.get('returncode') != 0:
        raise RuntimeError('lectura incompleta')
    print(result.get('stdout', ''))
PY
```

El inventario ROSA es `rosa service call --no-daemon
/mc/controller_manager/list_controllers rosa_control_msgs/srv/ListControllers
'{}'` dentro del contenedor de aplicación Motion, con
`ROS2CLI_DISABLE_DAEMON=1` y timeout. La evidencia privada de esta revisión es
`../Humanoide-vla-evidence/20261110T095147Z_SMOLVLA_SDK_AGE_READONLY/sdk-age-readonly.json`,
SHA256 `cc62374fbb20edf8ecda7948837b85f1a643a3650cfb9d00834f765c40cb008c`.
Incluye descubrimiento, hash, fragmentos de disassembly, proceso/mapeo y
catálogo de controladores; no contiene órdenes o cambios de modo.
