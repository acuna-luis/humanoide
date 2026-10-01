# Decompilación de la selección de cajas

## Material que ya tenemos — 30-09-2026

**VENDOR-SOURCE-SCOPE-01, revisión de disponibilidad local.** Sí existe código
fuente parcial. La solicitud al proveedor debe centrarse en las implementaciones
internas que faltan y en identificar sus versiones compatibles.

| Material | Disponibilidad comprobada |
|---|---|
| Ejecutor y selección propios | Fuentes completas en `scripts/box_handling/`: CLI, runtime, contratos, selector, adaptadores SPS y pruebas |
| Tareas del robot | XML/YAML archivados en `vendor/ubtech/cruzr_s2/snapshot_20260916/`; describen secuencias, trayectorias y parámetros, no la implementación C++ de los nodos |
| SDK C++ | Tar versionado: 9 ejemplos `.cpp`, 3 cabeceras `ubt_robot/{api,skill,work}.h`, 46 cabeceras JSON de terceros y 14 bibliotecas estáticas; API interna compilada |
| SDK Python | Tar versionado: 9 demos y 2 wheels; sus implementaciones vienen en `_core.so`, `libcc_api_client.so` y bibliotecas tbox |
| Demo de bajo nivel | Tar versionado: 23 ejemplos `.cpp`, 28 `.msg`, `Tts.action` y CMake/package.xml |
| Modelos y VLA | URDF/USD y código VLA/GR00T, puentes y mensajes disponibles; VLA no es el ejecutor de optimistic. Los directorios grandes extraídos están excluidos de Git |
| Ingeniería inversa | Binarios y pseudocódigo de Ghidra en evidencia externa; no equivalen al proyecto fuente original compilable |

Los tres tar del SDK se inspeccionaron incluyendo ambos wheels en memoria,
sin instalación ni ejecución. No contienen las implementaciones de
`manipulation_meta_tasks`, `manipulation_perception`, `pose_6d_estimate`,
`nav_taskmanager` o `freepnc`. El paquete de actualización de 40 archivos tiene
YAML, scripts, JSON y DEB, sin fuentes C/C++. La búsqueda de archivos desplegados
en el workspace, incluyendo carpetas ignoradas y excluyendo secretos/entornos,
tampoco encontró los archivos C++ internos identificados más abajo. Las
imágenes Docker locales se distinguen del código versionado: su presencia
no demuestra que incluyan el árbol fuente completo.

Se indexaron también las capas `COPY /opt/walker` de `images/motion.tar` y
`images/vision.tar`, sin cargar contenedores ni extraer a disco. En los paquetes
Motion `manipulation_meta_tasks`, `manipulation_task_manager` y
`manipulation_perception`, y en los paquetes Vision `pose_6d_estimate`,
`nav_taskmanager`, `freepnc_task_manager`, `freepnc_task_module`,
`arc_precise_controller`, `local_controller`, `ucostmap` y `umap_manager`, no
aparecen fuentes C/C++, cabeceras ni Python. Sí hay fuentes generadas de
mensajes/bindings en paquetes de interfaces. No se auditaron todas las capas
base: esta comprobación cubre las capas de instalación de los componentes.

Por tanto, añadir a la solicitud: «We already have the SDK examples, API
headers, task XML/YAML files and runtime images. We need the original source
implementation of the underlying modules and their reproducible build setup.»
La petición anterior de interfaces/configuraciones completas sigue sirviendo
para solicitar la versión compatible, pero no implica que no tengamos ninguna.

Índices de los tar y SHA256, respaldo previo y revisión sólo PC:
`../Humanoide-vla-evidence/20260930T080718Z_SOURCE_AVAILABILITY`.
No se modificaron SDK, código ejecutable ni robot. Reversión documental
selectiva desde `before/`; sin cambios de instalación que reaplicar.

## Fuentes a solicitar a UBTECH — 30-09-2026

**VENDOR-SOURCE-SCOPE-01 — VERIFICADO en código local y evidencia archivada.**
Solicitud preparada, no enviada. No conexión ni cambios al robot. El script
`optimistic_scenario1.sh` entra en `scenario1_cli` y `scenario1_runtime`; éstos
son nuestros, al igual que `front_sps_*`, `select_front_box.py` y la variante
`local_front_box`. Lo que falta es el árbol fuente compilable del proveedor
que atiende las acciones y ejecuta las tareas, con sus dependencias transitivas.
No se afirma disponer de un inventario exhaustivo de fuentes internas: UBTECH
debe entregar los manifiestos de compilación y relacionarlos con los binarios.

| Bloque | Proyectos/componentes confirmados que identificar en la solicitud |
|---|---|
| Motion | `manipulation_task_manager`, `manipulation_meta_tasks` y `manipulation_perception`; implementación de `MetaClamp`, `MetaMove`, `MetaLook`, `MetaCruzrMove` y dependencias de controlador, IK/HQP, trayectorias, fuerza y hardware |
| Percepción | Repositorio de compilación `pose_6d_estimation`, paquete `pose_6d_estimate`, ejecutable `box_pose_estimator_node`, implementación de `/cv/task/transport_action` y pipeline de detección/pose 6D de `workbin` |
| Navegación | Repositorios `nav_taskmanager`, `freepnc_task`, `freepnc_local`; paquetes `freepnc_task_module`, `freepnc_task_manager`, `behaviortree_interface`, `arc_precise_controller` |
| Dependencias NAV | `navi_common`, `navi_global`, `navi_local`, `navi_recovery`, `uglobal_planner`, `local_controller`, `ucostmap`, `ucostmap_converter`, `freepnc_aeb`, `umap_manager`, `bt_interface`, `nav_freepnc_config_utars`; localización LiDAR/VSLAM y gestión de mapas |
| Interfaces/plataforma | ROSA y puente ROS2, mensajes/acciones/servicios/IDL usados; controladores y drivers de actuadores, base y sensores; URDF, TF y calibraciones correspondientes a esta unidad |

Archivos C++ identificados en las rutas de compilación de los binarios
archivados (pedir también cabeceras y fuentes asociadas, no sólo estos archivos):

- `repos/manipulation/meta_tasks/src/meta_clamp/{meta_clamp,clamp,clamp_vision,clamp_traj,clamp_task_stack,clamp_admit,clamp_admit_replan,clamp_abnormality_helper,clamp_utils}.cpp`.
- `repos/manipulation/perception/src/perception_action_client.cpp`.
- `repos/nav_taskmanager/nav_taskmanager/src/{nav_taskmanager,json_parser,map_interface}.cpp` y `fsm/`.
- `repos/freepnc_task/freepnc_task_module/src/{freepnc_task_module,freepnc_task_module_node}.cpp` y `semantic_planning_manager/semantic_planning_manager.cpp`.
- `repos/freepnc_local/arc_precise_controller/src/arc_precise_controller.cpp`.

No se conoce el nombre de cada fuente de `box_pose_estimator_node`; sí su
paquete y símbolo `UBT_CV::WalkerS::Pose6dNode::execute_Trans`. La configuración
archivada arranca `pose_6d_estimation_640_400_byd.json`. Componentes auxiliares
configurados: `rgb_camera/rgb_camera_node`,
`stereo_depth_estimation/stereo_depth_node` y
`calibration_full_chain/calibration_node`; solicitar su relación de dependencias.
`locate3d_task` y `vslam` son nombres de servicios/contenedores observados,
no identificaciones completas de sus repositorios fuente.

Cadena concreta para que el proveedor determine el alcance:

- `/mc/manipulation/action` (`mc_task_msgs/action/ArmTask`):
  `vision/enable_transport_vision_switch`,
  `local_front_box/separate_right_cruzr` (derivada de
  `Singapore/separate_right_cruzr`), `cruzr/mobot_back_20`,
  `wrc_cruzr/put_cruzr_wrc_low`, `cruzr/home`.
- YAML originales de `meta_clamp/wrc/`: `separate_right_cruzr.yaml`,
  `separate_bodyback_cruzr.yaml`, `put_cruzr_wrc_low.yaml`, `open_arm_cruzr.yaml`;
  pilas `task_stack_cruzr_separate_manipulability.yaml`,
  `task_stack_cruzr_clamp_bodyback.yaml`, `task_stack_cruzr_clamp_manipulability.yaml`.
- `/cv/task/transport_action` (`cv_task_msgs/action/VisionActionTask`):
  `transport/head/grasp`, caja de 0,603 × 0,397 × 0,22 m; nuestras dos interfaces
  SPS enlazan esa detección con el consumidor nativo de Motion.
- `/vnav/task/command` (`unav_task_msgs/action/Task`), `free_nav`/`logo_nav`,
  y `/vnav/action/planning` (`vnav_task_msgs/action/VnavCommand`).

Pedir fuentes C++/Python, cabeceras, CMake/package.xml, submódulos, versiones de
dependencias, XML/YAML/launch, modelos/pesos de percepción, URDF/calibraciones,
Dockerfiles y procedimiento de compilación/despliegue. Solicitar commit/tag y
digest de imagen que correspondan a los binarios instalados: la etiqueta
`v0.2.0` sola no identifica una compilación. Los hashes de las tres bibliotecas
Motion están en `front_box_integration.py`; `libmeta_move.so` se comprueba por
`scenario1_dependencies.py`. El planificador archivado/contrastado el 29-09 tiene
SHA256 `54da620905aa6816bb29a8e5983823172b02fe1f36cae68a407de5c420b812ea`.

Evidencia de nombres: scripts citados, XML/YAML de
`vendor/ubtech/cruzr_s2/snapshot_20260916/motion`, configuración local
`utars-udoke-config-v0.2.0_offline-001/vision/.metafiles/box_pose_estimation.metafile.yml`,
y archivos externos `20260921T110500Z_FRONT_BOX_SELECTION`,
`20260922T080049Z_ARC_PRECISE_DIAG/vendor`, `20260929T123551Z_NAV_PLANNER_FIX`.
Respaldo documental/SHA: `../Humanoide-vla-evidence/vendor_source_scope_latest.txt`.
Sólo documentación PC; no adaptación instalada ni mensaje enviado. Reversión:
retirar selectivamente esta sección y las entradas de índice, conservando los
cambios anteriores. Pendiente entrega y comprobación del árbol fuente de UBTECH.

**Actualización posterior:** adaptador y variante ya instalados; dos pruebas de recepción nativa correctas. Agarre físico pendiente. [Integración SPS vigente](INTEGRACION_CAJA_FRONTAL_SPS.md). El análisis inferior conserva el estado previo a esa instalación.

2026-09-21, Europe/Madrid. **BOX-01-FRONT-DECOMPILE — VERIFICADO por análisis
estático y lectura de interfaces; integración y prueba física PENDIENTES.**

Se decompilaron copias locales de las bibliotecas Motion y del ejecutable de
percepción Vision con Ghidra. El resultado es pseudocódigo reconstruido, no
el código fuente original ni una biblioteca lista para recompilar e instalar.
Las firmas y argumentos inferidos por Ghidra se contrastan con símbolos C++
y ensamblador; algunas inferencias de tipos son incorrectas.

## Resultado y corrección de la auditoría anterior

La auditoría anterior no encontró una selección configurable. La decompilación
revela una vía adicional ya presente: `request.special_box_name`, cuyo valor
ordinario es `none`. Si tiene otro valor, `ClampVision::GetVisionBox` consulta
la percepción SPS. **Ya no se considera demostrado que sea imprescindible
obtener el código fuente de UBTECH.** Esta vía es una candidata de integración,
no una integración funcional demostrada.

| Hallazgo | Evidencia estática/lectura |
| --- | --- |
| Transporte ordinario utiliza índice cero | `libmeta_clamp.so`: llamada `GetBoxVisionPose` en `0x120bc0`, `xor r9d,r9d` en `0x120b50` |
| Rama especial obtiene detección y selección SPS | `GetApproximateVisionPoses` en `0x121200`, seguido de `GetSelectedVisionPose` en `0x1212af`; tipo literal `SPS`, nombre del request e índice cero |
| La selección SPS consume la primera pose y la guarda | `libperception_action_client.so`, `GetSelectedVisionPose` en `0xaa2d0`; conversión de `sps_outputs.poses[0]` y `SetObjectInfo(nombre,id,pose)` |
| El historial exige conservar la identidad | `GetVisionBoxHistory` en `0x1266f0` pide `GetObjectInfo("box",0,...)`; no basta inventar otro nombre |
| El proveedor ya configura esa rama en otras tareas | YAML instalado `meta_clamp/ti/clamp_head_to_spbox_s2.yaml`, `special_box_name: ti_box`; no trasladar sus trayectorias a Cruzr |
| El parser lee realmente ese campo YAML | `GetRequestFromYamlNode`, lectura `special_box_name` en `0x138261`, conversión a string y asignación en `0x138280–0x13828f` |
| Hay activación de percepción sin trayectoria en ese XML | `vision/enable_sps_vision_switch.xml` contiene sólo `MetaLook start_vision_mode="sps_vision"`; se leyó, no se ejecutó |
| SPS necesita dos servidores | `EnableSpsVision` en `0xad610` crea clientes de detección y selección y espera ambos; no aparecieron acciones SPS en el inventario ROS2 consultado |

Las direcciones anteriores son offsets ELF originales; Ghidra añadió base
`0x100000` en estos proyectos. La ausencia en ROS2 no prueba por sí sola
ausencia en todos los transportes ROSA: verificar ambos antes de instalar.

La propuesta concreta es una variante por tarea con `special_box_name: box`
que consulte un adaptador SPS de selección frontal. Usar `box` conservaría
la clave `box/0` para las etapas que leen historial. **INFERENCIA de diseño:**
esa compatibilidad debe comprobarse con el consumidor nativo, no sólo con
un cliente de prueba independiente.

El adaptador necesitaría devolver una única pose original de cámara elegida
entre todas las candidatas de una consulta fresca de transporte. La selección
se calcula en `base_link` con TF del mismo instante; la pose devuelta a Motion
permanece en el marco que espera su conversión cámara/cuerpo. No entregar
directamente una pose `base_link` como si fuese una pose de cámara.

Debe enlazar detección y selección SPS sin reutilizar resultados anteriores,
rechazar ambigüedad/caducidad y peticiones incompatibles y conservar los
controles de alcance, IK y fuerza. En la rama inspeccionada el cliente SPS
accede a la primera pose sin una comprobación visible de vector vacío:
**nunca responder éxito con cero poses.** La exclusividad de los endpoints,
el contrato ROSA/ROS2, cancelación y la pose realmente consumida siguen por
validar. No se añadió un servidor ficticio ni se devolvieron poses inventadas.

## Herramienta y reproducción

Fuentes propias, sin copiar ni alterar el SDK original:

- [decompile_box_selection.py](../../scripts/box_handling/decompile_box_selection.py)
- [ConfigureBoxAnalysis.java](../../scripts/box_handling/ConfigureBoxAnalysis.java)
- [DecompileBoxSelection.java](../../scripts/box_handling/DecompileBoxSelection.java)

Ghidra 12.1.3 se instaló aisladamente en
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/tools/ghidra_12.1.3_PUBLIC`.
Procedencia: [publicación oficial](https://github.com/NationalSecurityAgency/ghidra/releases/tag/Ghidra_12.1.3_build).
Archivo `ghidra_12.1.3_PUBLIC_20260817.zip`, SHA256
`93a5d11a9ad510622acaaf908c556a7b9b764d338e78a7567f3689bf5081fd54`.
Java21 ya estaba instalado; no se instalaron paquetes globales. Ghidra crea
también su configuración/caché habitual de usuario. No se modificó el PATH.

```bash
python3 scripts/box_handling/decompile_box_selection.py \
  --tool-dir ../Humanoide-vla-evidence/tools \
  --binary ../Humanoide-vla-evidence/20260921T110500Z_FRONT_BOX_SELECTION/libmeta_clamp.so \
  --output-dir ../Humanoide-vla-evidence/analisis_clamp_NUEVO \
  --filter GetVisionBox --filter ClampBox
```

El directorio de salida debe ser nuevo. `--setup-tool` permite reproducir la
instalación de la versión fijada con verificación del checksum. Para percepción,
usar `libperception_action_client.so` y filtros `GetBoxVisionPose`,
`GetApproximateVisionPoses`, `GetSelectedVisionPose`, `EnableSpsVision`.
El manifiesto registra entradas, hashes y comando; el binario se copia y se
analiza, nunca se ejecuta. La herramienta no conecta con el robot.

El primer análisis de Clamp propagó erróneamente un atributo no-return de
funciones de registro y truncó el pseudocódigo. Se repitió desactivando las
heurísticas indicadas en `ConfigureBoxAnalysis.java`; utilizar `clamp-refined/`,
no el primer `clamp/`. Advertencias de tipos, vtables y relocaciones limitan
el resultado: el ensamblador sigue siendo la comprobación de cada hallazgo.
La gran función `GetRequestFromYamlNode(YAML::Node&,...)` excedió los90s del
decompilador; figura como `DECOMPILE_FAILED` en `parser.c`. El parser no se
declara recuperado completo: su lectura de `special_box_name` se comprobó
con el ensamblador acotado, conservado en `native-special-name-parser.asm`.

## Estado, evidencia y reversión

Evidencia privada fuera de Git:
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260921T112932Z_FRONT_DECOMPILE`.
Contiene `clamp-refined/pseudocode.c`, `perception/pseudocode.c`,
`perception/sps.c`, `vision/pseudocode.c`, proyectos, manifiestos, logs,
ensamblador acotado, consultas SPS, respaldo `before/` y fuentes/hashes finales.

Binarios analizados y sus SHA256:

| Binario | SHA256 |
| --- | --- |
| `libmeta_clamp.so` | `d6bc61a493f7d790150fdbd673108121f46589fef56620de4a9023dcc2ba520a` |
| `libperception_action_client.so` | `8b45c88e41eb797382d5bb7d89976e1eff60b31f931c866bf8f1ab3eb0c27421` |
| `box_pose_estimator_node` | `090afff51e540c3ff499ca4dac332f01a80eb5c6c53f01e1ab9c5ad22580f9f7` |

Destinos originales leídos: Motion, contenedor
`walker-motion.manipulation_robot_app-1`, `/opt/walker/manipulation_meta_tasks/lib/`
y `/opt/walker/manipulation_perception/lib/`; Vision,
`walker-box_pose_estimation.box_pose_estimation-1`,
`/opt/walker/pose_6d_estimate/lib/pose_6d_estimate/box_pose_estimator_node`.
Interfaces leídas en Motion, `walker-ros.ros2-1`.

Cambio persistente: herramientas y documentación **sólo PC**. No se instalaron
adaptadores ni tareas en el robot, parchearon bibliotecas, habilitaron SPS,
reiniciaron servicios o enviaron movimientos. El ejecutor conserva su bloqueo
de integración; `--check-front` sigue siendo diagnóstico. Decompilación local
completada no equivale a agarre integrado ni probado.
Validación: Ghidra ejecutó los scripts Java y exportó las funciones de selección;
CLI Python comprobada,13 tests existentes selector/probe correctos,
`bash -n scripts/force_escenario1.sh` y `git diff --check` correctos.

Reversión: retirar selectivamente los tres archivos propios y la instalación
aislada si dejan de ser útiles; conservar evidencia y cambios previos del
operador. No requiere restauración remota. Los respaldos documentales están
en `before/`; no sustituir indiscriminadamente documentos con cambios nuevos.
Punto de reanudación: implementar/verificar el contrato SPS descrito y una
variante aditiva de tarea; comprobar consumo nativo sin movimiento antes de
activar el agarre. No hace falta volver a pedir fuentes para investigar esa vía.
