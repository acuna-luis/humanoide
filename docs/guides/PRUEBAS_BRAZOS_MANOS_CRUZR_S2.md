# Pruebas iniciales de brazos y manos — Cruzr S2

Protocolo preparado para la primera prueba en vacío. No utilizar cargas, herramientas ni objetos durante estas comprobaciones.

## 0. Instalación física de las manos — condición previa

La vía preferida es instalar las manos antes del homing y de cualquier prueba visible. El paquete documental suministrado no incluye el procedimiento mecánico de instalación, la orientación izquierda/derecha, los pares de apriete, la secuencia de conexión eléctrica ni la calibración posterior. No improvisar estos datos.

Como excepción, puede realizarse una prueba limitada de **homing de brazos sin manos** si el responsable técnico local acepta la configuración y se cumplen todas estas condiciones: conectores de ambas muñecas protegidos con sus tapas originales, cables sujetos sin posibilidad de engancharse, ningún adaptador o tornillo suelto y autodiagnóstico sin luz roja ni error de efector final. Esta excepción no autoriza acciones de manos, tareas predefinidas que requieran un tipo de mano ni control directo de articulaciones.

Antes de montar, obtener del proveedor:

- modelo y generación exactos de cada mano, identificación izquierda/derecha y compatibilidad con el robot;
- SOP de montaje con orientación, tornillos, arandelas, fijador de roscas y pares de apriete;
- secuencia segura de apagado, conexión de alimentación/comunicaciones y protección ESD;
- ruta y holgura correctas del cable para evitar pellizcos durante el giro de muñeca;
- valor de `HW_TYPE`, driver/firmware requerido y procedimiento de detección;
- calibración, homing y prueba inicial sin carga;
- confirmación de supervisión por un técnico de UBTECH.

Condiciones mínimas de instalación: robot completamente apagado, cargador retirado, alimentación del chasis desconectada según el manual, brazos apoyados de forma segura y conectores sin tensión. No encender ni realizar homing hasta que ambas manos estén fijadas, cableadas e inspeccionadas conforme al SOP.

## Uso del cable Ethernet

| Fase | Ethernet | Motivo |
|---|---:|---|
| Carga y diagnóstico estático | Conectado | SSH, batería, estados ROS2 y registros |
| Apagado e instalación física de manos | Desconectado | Evitar tropiezos, tirones y conexiones innecesarias |
| Configuración de `HW_TYPE`/drivers | Conectado | Acceso a PC1/PC2 y verificación de software |
| Identificación de temas y estado de manos, robot inmóvil | Conectado | Confirmar detección, homing y ausencia de errores |
| Homing con el mando | Desconectado por defecto | Evitar enganches; el homing no necesita Ethernet |
| Acción predefinida con el mando | Desconectado | El mando ejecuta y detiene la tarea sin red |
| Movimiento de base | Siempre desconectado | Riesgo elevado de arrastrar o enrollar el cable |
| Movimiento lanzado mediante SDK desde el portátil | Conectado y asegurado | Necesario para mandar/detener; solo con base inmovilizada, cable con alivio de tensión y técnico presente |
| Diagnóstico posterior al movimiento | Reconectar con el robot detenido | Revisar batería, estados y errores |

No desconectar Ethernet durante una orden SDK activa: se perdería el canal de supervisión/parada por software. Para la primera prueba se prefiere una acción predefinida mediante el mando, con Ethernet retirado y parada física disponible.

## Esta noche: carga

- El manual indica un tiempo de carga de hasta 3 horas.
- El cargador rojo y la luz verde intermitente del chasis indican carga en curso.
- Cuando el cargador y la luz inferior estén en verde fijo, finalizar la carga y retirar el cargador.
- No dejar el cargador conectado durante toda la noche ni mantenerlo conectado una vez completada la carga; el manual advierte que debe evitarse la sobrecarga.
- No efectuar movimientos con el cable de carga conectado.

## 1. Preparación de seguridad después de instalar las manos

- Cargador desconectado y cable retirado del área.
- Suelo nivelado, seco y despejado; área mínima 2 × 2 m.
- Mantener al menos 1,5 m entre el robot y cualquier persona u objeto.
- Manos/pinzas vacías y sin elementos sueltos alrededor.
- Una persona maneja el mando y otra permanece junto al paro de emergencia físico.
- Antena del mando extendida, batería del mando suficiente y todos los controles centrados.
- No situarse dentro del recorrido de los brazos ni sujetarlos durante el movimiento.

Detener inmediatamente ante golpes, tirones, vibración persistente, ruido mecánico anormal, luz roja, aviso de servo o trayectoria hacia una persona/objeto. Durante una tarea, la parada ordinaria documentada es **H centrado + A**. Ante riesgo inmediato, utilizar el paro de emergencia físico.

## 2. Arranque y comprobaciones previas

1. Encender el robot siguiendo el manual y esperar aproximadamente 2 minutos.
2. Confirmar que los paros de emergencia están liberados y que no hay luz roja.
3. Consultar batería y estados desde PC2:

```bash
ssh walker@192.168.11.3
docker exec -it walker-ros.ros2-1 bash
source /opt/ros/humble/setup.bash
timeout 10 ros2 topic echo --once /emb/battery_state
timeout 10 ros2 topic echo --once /emb/estop_key_state
timeout 10 ros2 topic echo --once /emb/servo_estop_key_state
timeout 10 ros2 topic echo --once /sys/sensor/errors
```

No continuar si la batería no está suficientemente cargada, existe una alarma o aparece una luz roja.

## 3. Primera prueba de brazos: homing

1. Confirmar nuevamente que el cargador está desconectado y el área despejada.
2. En el mando, colocar **F abajo** y pulsar **D** una sola vez.
3. No tocar el robot mientras realiza el homing.
4. Verificar ambos brazos: movimiento suave, sin colisiones con el torso, sin ruidos anormales y llegada estable a la posición inicial.
5. Confirmar que no aparece luz roja ni aviso de servo.

Esta es la única prueba inicial de brazos que puede ejecutarse sin conocer la acción preseleccionada en el mando. También es la única prueba prevista en este protocolo antes de instalar las manos; no continuar con las secciones 4–6 hasta completar su montaje y detección.

## 4. Identificación de las manos o pinzas instaladas

Después del homing, ejecutar:

```bash
ros2 topic list | grep -E '^/mc/(L_hand|R_hand|left_hand|right_hand)|^/ecat/(left_grip|right_grip)'
```

Interpretación:

- Mano hábil de 3.ª generación: `/mc/L_hand/joint_states` y `/mc/R_hand/joint_states`.
- Mano hábil de 4.ª generación: `/mc/left_hand/joint_states` y `/mc/right_hand/joint_states`.
- Pinza DH PGC-140-50: `/ecat/left_grip/state` y `/ecat/right_grip/state`.
- Si no aparece ninguna pareja, detener la prueba de manos y solicitar al proveedor la activación/configuración del driver correspondiente.

Consultar solamente el estado de la pareja detectada:

```bash
timeout 10 ros2 topic echo --once /mc/L_hand/joint_states
timeout 10 ros2 topic echo --once /mc/R_hand/joint_states
```

o bien:

```bash
timeout 10 ros2 topic echo --once /mc/left_hand/joint_states
timeout 10 ros2 topic echo --once /mc/right_hand/joint_states
```

o, si equipa pinzas:

```bash
timeout 10 ros2 topic echo --once /ecat/left_grip/state
timeout 10 ros2 topic echo --once /ecat/right_grip/state
```

En las pinzas, antes de mover, comprobar `init_state: 1`, `homed: 1` y `error_code: 0` en ambos lados.

## 5. Prueba visible de movimiento de brazos

Esta es la prueba en la que los brazos realizan un movimiento amplio y claramente visible. Se ejecuta **después** del homing y de identificar el tipo de mano/pinza.

Elegir una única acción según el hardware confirmado:

- Mano de 3.ª generación: `production_movie/fist_up_s2`. Levanta los brazos/manos en un gesto de ánimo y, según el SDK, vuelve automáticamente a cero. Es la primera opción recomendada para esta versión.
- Mano de 4.ª generación: `production_movie/cheer_up_s2`. Después debe ejecutarse `production_movie/cheer_down_s2` para regresar a cero.
- Pinza DH o hardware aún no identificado: no ejecutar estas acciones; pedir al proveedor una tarea de demostración compatible exclusivamente con brazos.

Antes de ejecutar:

1. Confirmar que la base no forma parte de la acción y que el nombre mostrado o anunciado coincide exactamente.
2. Colocar a todas las personas fuera del alcance de los brazos.
3. Operador preparado con **H centrado + A** y segunda persona junto al paro físico.
4. Ejecutar una sola repetición, sin objetos en las manos.
5. Verificar que ambos brazos se mueven suavemente, no golpean el torso y regresan a una postura estable.

## 6. Prueba de movimiento de manos

Usar únicamente una acción predefinida cuya identidad haya confirmado el proveedor. No mover **G a la derecha** si no se conoce la acción seleccionada, porque una tarea puede incluir brazos, cuerpo o base.

La documentación SDK enumera estas acciones candidatas, pero deben confirmarse para el hardware y firmware de esta unidad:

- Mano de 3.ª generación: `production_movie/fist_up_s2` — movimiento de ánimo y retorno automático a cero.
- Mano de 4.ª generación: `production_movie/cheer_up_s2`, seguida de `production_movie/cheer_down_s2` para volver a cero.
- `qyh/handshake` no se recomienda como primera prueba porque requiere una orden de parada y posteriormente `qyh/post_handshake` para regresar.

Secuencia del mando para una tarea confirmada:

1. Usar **E arriba/abajo** únicamente para seleccionar la acción confirmada.
2. Comprobar su nombre por pantalla o indicación de voz antes de ejecutarla.
3. Mover **G a la derecha** para ejecutar.
4. Mantener preparada la parada ordinaria **H centrado + A**.
5. Confirmar el retorno a posición segura antes de acercarse.

No utilizar todavía `/mc/sdk/robot_command`, los temas `/mc/*hand*/command` ni `/ecat/*grip/cmd`. Esos interfaces publican órdenes directas. Además, el SDK suministrado contiene una ambigüedad entre la constante de modo de posición y el valor empleado en sus demos; se requiere confirmación del proveedor antes de una primera prueba.

## 7. Criterios de aceptación

- Homing completo sin luz roja ni aviso de servo.
- Hombros, codos y muñecas se mueven suavemente y sin colisiones.
- Ambos finales de brazo publican estado y no muestran errores.
- Todos los dedos/pinzas participan en la acción correcta y vuelven a cero.
- La tarea se puede interrumpir con **H centrado + A**.
- No aparecen errores nuevos en `/sys/sensor/errors`.
- Registrar vídeo de la prueba, nivel de batería, acción utilizada y cualquier ruido o asimetría.

## Confirmaciones pendientes del proveedor

1. Tipo exacto de mano/pinza y valor `HW_TYPE` de esta unidad.
2. Nombre/posición en el mando de una acción segura en vacío para brazos y dedos.
3. Confirmación de **H centrado + A** como parada de tarea en este firmware.
4. Modo correcto para comandos de manos, debido a la discrepancia del SDK.
5. Supervisión online para la primera ejecución ampliada.
