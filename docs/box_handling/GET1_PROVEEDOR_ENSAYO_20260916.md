# get1 del proveedor: ensayo exitoso con disposición corregida

2026-09-16, Europe/Madrid. **PROBADO FÍSICAMENTE según el operador**, con
resultados Motion aportados. Sustituye el estado pendiente/suspendido de get1
para este montaje. Conserva el incidente anterior y no acredita el resto del ciclo.

## Montaje y resultados

- Base de caja objetivo: **780 mm desde el suelo**, antes570 mm.
- Centro de rueda derecha a frente de caja: **590 mm** longitudinales.
- Lado derecho de rueda a lado derecho de caja: **160 mm hacia fuera**;
  rueda situada a la derecha de la caja, no hacia su centro.
- Caja603×397×217 mm; YAML del proveedor603×397×220 mm.
- Hay una caja/pila baja a la derecha. El operador indica que reproduce la
  demostración y que el espacio a la altura de extracción está libre.
  Su mera presencia en una foto no demuestra interferencia.

| Acción del operador | Goal ID | Resultado |
| --- | --- | --- |
| `vision/enable_transport_vision_switch` | `7c29cf8d-4c6c-4075-aff1-071f92a00dd2` | SUCCEED /1101001 /status4 |
| `Singapore/separate_right_cruzr` | `cf10d446-d7cc-49e7-85fd-6c8329920adc` | SUCCEED /1101001 /status4 |

El operador comunica que funciona perfectamente. El XML incluye preparación
de cabeza/brazos, `wrc/separate_right_cruzr` y `wrc/separate_bodyback_cruzr`.
No se capturaron aquí fuerzas ni postura posterior al éxito. No confundir el
último HOME anterior con el estado después de agarrar.

La disposición cambió y el nuevo ensayo fue exitoso. No se ha aislado la
contribución de altura, lateralidad y otras variables a la causa inicial.
Las opciones de colisión y la libertad de torso describen la configuración;
no prueban por sí solas que la tarea sea incorrecta en su escenario previsto.

## Orden restante del escenario1

### Mapa y puntos

En el original, `NavigationLocation` de
`subtrees/Navigation/navigation.xml` fija `map_name="utars_nav_map"` tanto en
`MappingNameGain command="get_map_name"` como en `MappingOperations command="map_set"`.
No es el nombre obligatorio de cualquier mapa del robot: es la referencia del
flujo original. Para usar MESAS2 u otro nombre hay que adaptar esa referencia en
una copia del flujo/dependencias, manteniendo el original; exportar
`CRUZR_MAP_NAME` en PC no modifica ese XML del proveedor. No se ha aplicado cambio.

Los puntos del primer ciclo son `get1` y `put1` en el mismo mapa seleccionado;
el escenario completo requiere además `get2`, `put2`, `get3`, `put3`, respetando
los nombres en minúsculas. Guardar X/Y y orientación de la base. `get1` debe
reproducir la posición de base del agarre exitoso antes del retroceso20cm; usar
la pose actual sólo si el chasis no se ha desplazado desde entonces. No guarda
ángulos de brazos, altura de caja ni un punto de contacto sobre la caja.

Registrar `put1` es situar el robot donde debe comenzar el depósito frente a la
estantería; guardar sus coordenadas no adapta alturas/pendiente del MetaClamp.
La lectura de este XML no demuestra cuál es el mapa activo actualmente.
El arranque completo llama `cruzr/open_arm_before_home` dentro de
`NavigationLocation`, en paralelo con la preparación del mapa: no utilizarlo
como una continuación con caja ya sujeta.

### Tareas después del agarre

Fuente: [árbol original](../../vendor/ubtech/cruzr_s2/snapshot_20260916/vision/cruzr_s2/utars_task_canada_wrc_20250930_start.xml).

1. `cruzr/mobot_back_20`: `MetaCruzrMove delta_pose=-0.2;0;0`, retroceso200mm.
2. `logo_nav_put1`: navegar al punto `put1` del mapa.
3. `wrc_cruzr/put_cruzr_wrc_low`: depósito inferior y después
   `wrc/open_arm_cruzr`; la apertura está incluida.
4. `cruzr/home`.
5. `logo_nav_get2` → `Singapore/clamp_cruzr`: recoger caja superior izquierda.
6. `cruzr/mobot_back_20` → `logo_nav_put2` →
   `wrc_cruzr/put_cruzr_wrc_low` → `cruzr/home`.
7. `logo_nav_get3` → `wrc_cruzr/clamp_cruzr_wrc_high`: recoger del nivel superior.
8. `logo_nav_put3` → `wrc_cruzr/put_cruzr_wrc_chitu` → `cruzr/home`.

Los `logo_nav_*` son subárboles de Vision: `navigation_start`, modo `logo_nav`,
nombre de punto como `target_id`. No son tareas ArmTask de Motion.
La recogida alta incluye retroceso−0,1m/s durante5s; el depósito en mesa incluye
apertura y retroceso−0,1m/s durante4s. Son órdenes nominales, no distancias medidas.

El árbol original reintenta get1 hasta10 veces, get2/get3 hasta5 y navegación
hasta5. Arrancarlo desde el inicio no equivale a continuar después de get1.
No se ha seleccionado/iniciado aquí. put1 y demás fases siguen sin ensayo
comunicado en el montaje nuevo. El destino local1000→830mm sin rodillos difiere
del ejemplo del proveedor. Este flujo utiliza detector/MetaClamp, no VLA ni dumping.

## Acciones del agente, cambios y evidencia

Antes del ensayo del operador: preflight canónico correcto, y
`scripts/cruzr_blue_workbin_cycle.sh --prepare-vision --yes`, sólo cabeza−0,43rad
en2s; goal `0e6916b3-2247-46b7-9f36-12cd247d04f3`, SUCCEED. Posterior pitch
−0,430665rad, otros ejes corporales sin variación y velocidades0.
El agente habilitó transport vision mediante el XML comprobado con una sola
acción MetaLook, goal `f5d04ee3-353a-43e2-a77c-3af0b7fa57ee`, SUCCEED.
Dos detecciones de `/cv/task/transport_action`, tipo
`cv_task_msgs/action/VisionActionTask`, transport/head/grasp/caja0.603,0.397,0.22:
cinco poses en ambas respuestas, variación de la primera2,07mm.

No ejecutó separate_right, navegación, depósito ni HOME. Sin instalación/recarga
de XML/YAML o cambio de límites. Transport vision quedó habilitada para continuar;
no se restablece automáticamente la postura mientras pueda haber una caja sujeta.

Evidencia privada, capturas RGB/nube, respuestas, configuración y reproducción:
`../Humanoide-vla-evidence/20260916T091030Z_GET1_LAYOUT_780_OUTSIDE/`.
Resultado aportado y backups en `provider-success-record/`; copias `after/`
y SHA256SUMS. El script fue cambiado por el usuario, commit `fffe749`, SHA256
`b0e0be6877656f0c466baf2919a6994728f6f99c8600be5b54e1ee3026fcdd86`;
ya no contiene el bloqueo inicial. Se conserva su trabajo.
El perfil offline cambia a780mm y se regenera mediante
`python3 scripts/box_handling/prepare_single_box.py`; sigue sin ejecutar.
Reversión documental: copias before/ de esta intervención. No restaurar
automáticamente estados físicos ni la configuración anterior. Sin commit/push
por el agente. No se emitieron nuevas órdenes tras recibir el ensayo exitoso.

## Continuación: punto get1 y ejecutor ampliado

El 16-09 se guardó `get1` con orientación actual en `utars_nav_map`. El script
incorpora ahora el primer ciclo hasta HOME, pero `put1` sigue por registrar y
la ampliación no se ejecutó físicamente. [Registro y receta](GET1_PUT1_MAPA_Y_EJECUTOR.md).
