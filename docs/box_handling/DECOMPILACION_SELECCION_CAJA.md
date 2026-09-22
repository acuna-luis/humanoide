# Decompilación de la selección de cajas

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
