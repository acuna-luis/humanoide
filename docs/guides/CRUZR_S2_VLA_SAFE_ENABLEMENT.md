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
