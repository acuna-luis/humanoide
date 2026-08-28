# Integración segura del VLA suministrado para Cruzr S2

Para preparar el PICO 4 Ultra Enterprise, diseñar sesiones, capturar episodios
y decidir entre continuar este checkpoint o crear un nuevo perfil, consulte
[Cruzr S2 v0.2.0: teleoperación, captura de datos y evolución del VLA](../vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md).

## Estado verificado

El checkpoint GR00T N1.5 suministrado está instalado y puede cargarse sobre el
sistema v0.2.0. La inferencia se ha ejecutado de forma aislada y ha generado
chunks con la estructura esperada:

- 20 dimensiones en el orden oficial del perfil S2;
- 10 puntos por chunk;
- valores finitos y dentro de los rangos del checkpoint;
- cámara estéreo activa;
- estado de los 20 ejes recibido desde `/mc/whole_joint_states`;
- cero publicadores en `/mc/sdk/robot_command` durante toda la prueba.

La prueba shadow desde `home` generó dos chunks, pero ambos fueron rechazados
antes de cualquier ejecución física. El primer punto difería de la postura real
en ocho articulaciones de brazo, con diferencias máximas próximas a 1,35 rad.
Esto demuestra que el VLA no debe activarse directamente desde `home`.

Una segunda ejecución de task 0 el 2026-08-28, desde una postura y escena que
no se documentaron, produjo dos chunks adicionales. Ambos fueron rechazados por
siete violaciones del primer punto; la máxima fue
`R_shoulder_yaw_joint=1,339886 rad` con límite `0,35 rad`. La duración real fue
`10,063076 s` para un máximo solicitado de 8 s. Se mantuvieron cero
publicadores, STOP dejó ambos contenedores detenidos y no hubo movimiento. Este
run es `PASS_SHADOW_SAFETY_ONLY`, no evidencia de que task 0 pueda hacer PICK.

Al reanudar la campaña el 2026-08-28, el propietario informó que el robot ya
estaba encendido y en `home`. Un check fresco de sólo lectura confirmó
Motion/Vision, acciones listas, paros `0/0`, cargador desconectado y
`ACTUATORS_OPERATION_ENABLED=1`, pero el gate no pudo certificar la postura 20D
porque la muestra omitió los IDs `2001/2002/2003/3001`. No se envió movimiento.
VLA permaneció con ambos contenedores `exited` y cero publicadores. El siguiente
paso sigue siendo E1.0/E1.3 de medida física fuera de la envolvente; `home`
informado no autoriza repetir shadow desde una entrada nominal ni ejecutar VLA.

Para reducir carga operativa, el propietario cerró E1.0 con las medidas
`1,80 × 0,80 × 1,00 m`, cuatro esquinas a 1 m, rigidez/estabilidad y más de
1,5 m de separación; las fotos y marcas se difieren a E4. E1.3 conserva la
geometría medida de B0 `0,603 × 0,397 × 0,217 m` y difiere masa/colocación real
a E4/E6. Esta dispensa sólo libera shadow OOD. E2.1 task 2, run
`20260828T105547_E2.1`, generó dos chunks en `10,065012 s`; ambos fueron
rechazados por siete saltos del primer punto, máximo
`R_shoulder_yaw_joint=1,376502 rad` frente a `0,35 rad`. STOP dejó ambos
contenedores `exited`, publicadores `0` y hashes válidos. Es
`PASS_SHADOW_SAFETY_ONLY`, no evidencia de PICK medio ni autorización física.

E2.3 se redujo por decisión del propietario a un piloto 2+2. Task 0, run
`20260828T110217_E2.3-task0`, produjo cuatro chunks rechazados por las mismas
siete discontinuidades; duraciones `10,006055…10,039981 s` y máximo delta
`1,361919…1,367893 rad` en `R_shoulder_yaw_joint`. Task 2, run
`20260828T110617_E2.3-task2`, produjo otros cuatro rechazos equivalentes;
duraciones `10,005578…10,006689 s` y máximo `1,372170…1,379845 rad`. Cada
repetición confirmó STOP y los parents terminaron `exited/exited/publishers:0`;
ambos manifests validan. Es `PASS_PILOT_2X2_SHADOW_ONLY`: demuestra
repetibilidad del runtime/rechazo OOD, no capacidad de PICK ni seguridad para
publicación física.

E2.2 ya cubre los tasks PLACE 1 y 3 sin crear una postura HELD en el robot. El
run `20260828T112730_E2.2` cargó `checkpoint-40000` en un contenedor transitorio
con `--network none`, sin ROS ni mensajes de mando, y reprodujo frame 0 de los
episodios 465 y 265. Produjo dos chunks 10×20: MAE `0,007283609` para task 1 y
`0,011394879` para task 3, sin violaciones conservadoras de rango o primer
salto. El holdout es una partición local del último 15 % por task; no es un
split del proveedor y puede haber formado parte del entrenamiento. El resultado
es `PASS_OFFLINE_INFERENCE_ONLY`: valida el camino de inferencia, no PLACE
físico, generalización ni seguridad de ejecución. El cierre confirmó
`exited/exited/publishers:0` y cero acceso al estado del robot.

E3.0, run `20260828T114346_E3.0`, evaluó offline cinco episodios y fases por
cada task 0–3, con 20 muestras y 36 inferencias. Las MAE medias por task fueron
`0,004908891`, `0,006516288`, `0,009686776` y `0,008983554`; las cinco
ejecuciones seed 0 de cada task fueron idénticas. Dos baselines violaron el
rango de `lifter_pitch_1_joint`: task 2/episodio 270/frame 0 en un punto y
task 3/episodio 287/frame 0 en siete puntos, hasta `0,060465574` frente al
máximo `0,000336618`. Por ello el resultado es
`PASS_OFFLINE_CAMPAIGN_WITH_CONSERVATIVE_VIOLATIONS`, no candidato ejecutable.
El split local 424/76 no se solapa, pero no demuestra episodios inéditos para
C0. Hashes completos del checkpoint sin cambios y cierre
`exited/exited/publishers:0`; sólo queda autorizado continuar con E3.1 offline.

## Incompatibilidades corregidas en el overlay

El paquete original no arrancaba tal como fue entregado:

1. El ejecutor SDK instalado estaba incompleto y cargaba un perfil de 17 ejes.
2. `/mc/sdk/robot_state` se anunciaba, pero no emitía muestras. Se usa como
   alternativa read-only `/mc/whole_joint_states`, activo a unos 500 Hz.
3. La imagen no contenía la variante GR00T que define
   `Utars_1RGBDataConfig` ni el argumento `eagle_path`. Se monta el árbol GR00T
   suministrado por UBTECH, verificado mediante hashes.
4. El staging inicial omitía `experiment_cfg/metadata.json`; ahora incluye los
   dos metadatos necesarios para inferencia, pero no los 8,5 GB del optimizador
   de entrenamiento.

Ninguna de estas correcciones modifica el firmware base. Los dos contenedores
VLA siguen con política `restart=no` y quedan detenidos al terminar.

## Uso en shadow mode

Los runs no deben construirse concatenando una variable que proceda de otro
shell. Para medidas o herramientas futuras, crear la salida en el mismo bloque:

```bash
VLA_RUN_DIR="$(./scripts/vla/new_vla_evidence_run.sh --experiment ID)"
```

E1.1 y E1.2 disponen de wrappers que crean y validan esa ruta internamente:

```bash
./scripts/vla/audit_vla_experiment_e1_1.sh
./scripts/vla/audit_vla_experiment_e1_2.sh
```

Para un smoke autocontenido de task 0 o 2, con directorio propio, STOP ante
fallo y exportación de evidencia:

```bash
./scripts/vla/run_vla_shadow_smoke.sh --task-id 0
```

Para repetir E2.2 offline con tasks PLACE 1 y 3:

```bash
./scripts/vla/run_vla_offline_place_e2_2.sh --check
./scripts/vla/run_vla_offline_place_e2_2.sh --run --seed 0
```

Esta orden no sustituye una prueba física: no usa estado vivo ni comprueba que
una caja se deposite correctamente.

Para repetir la campaña E3.0 completa:

```bash
./scripts/vla/run_vla_offline_campaign_e3_0.sh --check
./scripts/vla/run_vla_offline_campaign_e3_0.sh --run
```

Las violaciones se conservan como resultado y nunca se envían al robot.

Después de que E1.0, E1.3 y E2.1 liberen el gate, cinco repeticiones E2.3 se
ejecutan sin mezclar logs/chunks y con STOP entre runs:

```bash
./scripts/vla/run_vla_shadow_repetitions.sh --task-id 0 --repetitions 5
```

La secuencia manual de bajo nivel continúa disponible para diagnóstico:

```bash
./scripts/vla/run_ubtech_vla_shadow.sh --deploy
./scripts/vla/run_ubtech_vla_shadow.sh --start-shadow --shadow-duration 300
./scripts/vla/run_ubtech_vla_shadow.sh --start-inference
./scripts/vla/run_ubtech_vla_shadow.sh --status
./scripts/vla/run_ubtech_vla_shadow.sh --trigger --task-id 0 --inference-duration 8
./scripts/vla/run_ubtech_vla_shadow.sh --stop
```

Si la secuencia ya terminó pero no se conservaron los logs locales, se pueden
extraer desde los contenedores detenidos sin arrancarlos:

```bash
VLA_RUN_DIR="$(./scripts/vla/new_vla_evidence_run.sh \
  --experiment RECOVERED-SHADOW)"
./scripts/vla/run_ubtech_vla_shadow.sh --export-evidence "$VLA_RUN_DIR"
```

El script aborta si detecta un publicador en `/mc/sdk/robot_command`. El
validador no importa `RobotCommand` y no crea publicadores ROS.

Los identificadores suministrados son:

- `0`: recoger caja grande del nivel inferior;
- `1`: depositar caja grande en el nivel inferior;
- `2`: recoger caja grande del nivel medio;
- `3`: depositar caja grande en el nivel medio.

## Condición pendiente para movimiento físico

Antes de conectar un ejecutor físico deben cumplirse todos estos puntos:

1. Auditar y probar por separado el XML suministrado
   `codes-S2/.../s2_vla_pick_large_teleop_ready.xml`, hash
   `f4025124491eba995ec824db3e3be91875f781a4b4e98928654bde9a021d8323`,
   con zona despejada y paro preparado; todavía no se ha demostrado cuál task
   equivalente está instalado en Motion.
2. Resolver con UBTECH/la instalación real `clamp_s2_joints_trajectory`: el
   XML existe, pero termina invocando esa acción sin definir allí su trayectoria.
3. Repetir shadow desde esa postura y obtener chunks aceptados sin saltos,
   valores fuera de rango ni estado obsoleto.
4. Implementar un ejecutor S2 independiente que sólo mande los 14 ejes de los
   brazos. Cabeza, elevador y cintura permanecen bloqueados, como en el diseño
   del ejecutor SDK suministrado.
5. Añadir deadman, timeout, parada por pérdida de estado y límites conservadores
   antes de habilitar la publicación.
6. Realizar primero una prueba sin caja y a velocidad reducida, con aprobación
   física explícita en ese momento.

Hasta completar estas condiciones, el VLA está operativo únicamente para
inferencia y validación shadow; no está habilitado para mover el robot.
