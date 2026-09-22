# Seleccionar la caja frontal independientemente de la altura

**22-09-2026 10:58 CEST — Corregido empate entre caja frontal y soporte.**
El nuevo fallo38371422…/NoneException procedía del selector: dos detecciones de
la misma pila tenían ángulo casi igual. Operador confirma la caja abierta
superior de la pila frontal. Selector ahora agrupa columnas coherentes de
workbin22cm y elige la superior dentro de la pila frontal, sin priorizar la
altura de pilas laterales ni ampliar controles físicos. Paquete
`74f5507e44addd71` instalado de forma aditiva; percepción directa y recepción
nativa SUCCEED verificadas, sin trayectoria. Pose nueva X≈0,780/Y≈0,134/Z≈0,794m;
no reutilizar la pose baja del fallo anterior. Usuario confirma inmóvil y sin
contacto; tras preparación del ensayo no asumir HOME. Agarre aún PENDIENTE.
[Causa, fuentes, pruebas, instalación y reversión](../incidents/2026-09-22_FRONTAL_PILA_AMBIGUA.md).

**VIGENTE — integración SPS instalada, enlace perceptivo nativo probado:** ambos ejecutores usan la variante frontal. Tres pruebas MetaLook SUCCEED y coincidencia de pose en el log C++; agarre físico pendiente. [Uso, estado exacto y reversión](INTEGRACION_CAJA_FRONTAL_SPS.md). Los registros inferiores describen las etapas previas de diagnóstico y bloqueo.

**Actualización 21-09 13:40 Europe/Madrid:** decompilación completada de las funciones de selección; identificada rama configurable SPS mediante `special_box_name`. Se sustituye el requisito anterior de obtener necesariamente fuentes/build. Es una vía por verificar, todavía sin adaptador ni agarre integrado. [Hallazgos, pseudocódigo y receta](DECOMPILACION_SELECCION_CAJA.md).

Estado histórico previo a la integración, 2026-09-21. BOX-01-FRONT. **Selector implementado; comprobación
--check-front probada con percepción real y TF sincronizado. Agarre NO integrado
ni probado físicamente. El ciclo sin argumentos se detiene antes de mover.**

## Requisito confirmado

El operador quiere recoger la caja delante del robot aunque haya cajas más
altas a ambos lados. Apartar la pila fue una prueba diagnóstica; no es la
solución funcional solicitada. No priorizar altura ni índice devuelto por visión.
Seleccionar y comprobar alcance son operaciones diferentes: si la caja frontal
no es alcanzable, detenerse; no elegir en su lugar una lateral.

## Hallazgo de la ruta actual

En la biblioteca instalada libmeta_clamp.so, rama GetVisionBox(Request,...),
la llamada en0x120bc0 a PerceptionActionClient::GetBoxVisionPose pasa índice0
(xor r9d,r9d en0x120b50). La biblioteca de percepción verifica rango del índice
y convierte esa entrada de box_pose. Esto concuerda con el goal58946ad3,
que usó la primera de tres poses, correspondiente a la caja superior izquierda.
La lectura está acotada a esa rama/binarios; no implica que todas las tareas
usen índice0. No se ha parcheado ningún binario.

Un selector directo select_by_xyzCam ya fue rechazado por el servidor Vision
instalado; su presencia en Motion no equivale a soporte extremo a extremo.
Los ejemplos vision_aligned con id pertenecen a otra ruta y no autorizan
cambiar el tipo de tarea separate_box ni fijar índice1: los índices cambian.

## Componente preparado

Fuente: [select_front_box.py](../../scripts/box_handling/select_front_box.py).
Consume un único conjunto de poses coherente transformado a base_link.
Criterio: mínimo valor absoluto de atan2(Y,X), con X positivo; la altura Z
no interviene en la clasificación. Sector diagnóstico inicial ±20°, ambigüedad
≤2° entre mejores candidatas: rechazar. Son parámetros provisionales del
selector, no límites físicos ni precisión validada. Dos cajas apiladas igualmente
centradas quedan ambiguas: el criterio frontal por sí solo no distingue alturas.

Devuelve la pose original seleccionada sin modificar coordenadas, orientación
ni límites. No descarta una caja frontal por alcance para escoger otra. No
crea clientes ROS, publicadores o acciones; no acepta --run. No certifica
frescura, TF, tamaño, alcance, IK, contactos o trayectoria. Estos controles
siguen siendo requisitos del adaptador y de Motion.

Verificación:

```bash
python3 -m unittest scripts.box_handling.test_select_front_box
python3 scripts/box_handling/select_front_box.py detecciones_en_base_link.json
```

Ocho tests correctos: caja frontal más baja, todas las permutaciones,
altura independiente, frontal inalcanzable sin sustitución, ambigüedad,
marco incorrecto, poses inválidas y política inválida.
Reproducción aproximada de captura de tres cajas del21-09 elige índice1,
la baja derecha, bearing7.04°. Usa transformación histórica redondeada y
supuesto de postura igual, únicamente para probar clasificación; no es nueva
medida ni validación geométrica. No publicar ese resultado en el robot.

## Integración que falta

El selector debe consumir las candidatas de la MISMA consulta que utilizará
MetaClamp, con transformación temporal válida. Una medición previa seguida de
la tarea original puede volver a seleccionar otra caja. Conservar detección
original y trazabilidad de candidata elegida, verificar estabilidad/ambigüedad
sin reutilizar índices, después ejecutar los controles originales de alcance,
IK y fuerza. Ante cualquier fallo, terminar sin sustitución de objetivo.

Preferencia: extensión del cliente nativo de percepción con selección explícita
por tarea, o adaptador aislado con conexión demostrada únicamente a esta tarea.
No remapear globalmente el detector, reemplazar poses ni modificar la biblioteca
a ciegas. El código fuente nativo no se encontró entre los archivos instalados
inspeccionados. PENDIENTE: implementación verificable de ese enlace y prueba
sin movimiento antes de instalación/ensayo físico autorizado.

Cambiar únicamente force_escenario1*.sh no introduce ese enlace. Ambos scripts
del operador permanecen intactos en esta intervención.

## Ensayo perceptivo con cajas laterales 2026-09-21 13:11

Europe/Madrid. **OBSERVADO:** operador vuelve a colocar cajas laterales.
Contenedores redescubiertos en Motion/Vision, sin reinicios ni configuración.
Una consulta `/cv/task/transport_action` `cv_task_msgs/action/VisionActionTask`,
transport/head/grasp, box_size0.603/0.397/0.22, termina okTrue/status4;
goal `5a5062f1-4062-48f1-a72e-85a40effea2f`. Devuelve dos poses:

- índice0: caja superior izquierda; cámara[-0.672804,0.464934,0.909906]m;
- índice1: caja baja frontal; cámara[-0.077572,0.750330,1.051937]m.

Imagen segment.png coincide con esa disposición; su stamp0 no permite
certificar sincronización. TF cámara→base_link corresponde a RGB9,840s
posterior a la detección. Última muestra articular tiene velocidades0 y
head_pitch−0.430473rad; no demuestra inmovilidad durante todo el intervalo.
**INFERENCIA:** clasificación aproximada elige índice1 con bearing7,524°.
Posición base_link aproximada[0.798609,0.105484,0.384597]m. No equivale a
X_BaseBox interno ni certifica margen, IK o trayectoria de agarre.

**VERIFICADO offline:** select_front_box aplicado a estas poses transformadas
selecciona la caja baja frontal. No integrado ni instalado en MetaClamp.
force_escenario1.sh conserva la selección nativa; no usar este resultado
como autorización para ejecutar el ciclo. Cero órdenes de movimiento/HOME.
La consulta puede crear las imágenes diagnósticas automáticas del proveedor.
No se cambió configuración persistente; no hay rollback remoto.

Evidencia privada: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260921T111050Z_BOX_SELECTION_CAPTURE`; vision.json, capture.json,
capture-metadata.json, segment.png, raw.png, selection-input-approximate.json,
selection-result.json y SHA256SUMS. Reproducción offline:
`python3 scripts/box_handling/select_front_box.py <evidencia>/selection-input-approximate.json`.
Pendiente: TF temporal coherente en integración, selección consumida realmente
por MetaClamp, validación de alcance/IK y prueba física autorizada.

## Ejecutor con comprobacion frontal

2026-09-21 13:18 Europe/Madrid. **VERIFICADO:** modificación local de
`scripts/force_escenario1.sh` y nuevo `scripts/box_handling/probe_front_box.py`.

```bash
./scripts/force_escenario1.sh --check-front
# Si se necesita el salto Wi-Fi ya existente:
./scripts/force_escenario1.sh --wifi --check-front
```

Envía únicamente transport/head/grasp al servidor perceptivo existente. No
habilita visión, cambia modos, prepara cabeza, navega ni ejecuta MetaClamp.
El script transmite los dos módulos Python por stdin al contenedor ROS2 de
Motion; no instala archivos, parámetros o servicios remotos. Dependencias
comprobadas: rclpy, tf2_ros, cv_task_msgs y rosidl_runtime_py ya instalados.
Contenedores y acción redescubiertos; robot sin actualización ni recarga.
Vision puede guardar sus imágenes diagnósticas habituales como efecto de consulta.

Exige status4/okTrue, cámara head/workbin y marco óptico conocido; detección
≤2s y no anterior a la petición por más de0,5s. Buffer TF iniciado antes
de consultar, lookup en el stamp exacto; no recurre a TF latest. Selección
geométrica conserva posiciones/orientaciones y rechaza ambigüedad. Devuelve
resultado completo, TF, candidatas, índice seleccionado y movimiento0. No
certifica IK, alcance, colisiones ni trayectoria. Timeout solicita cancelar
sólo el goal propio cuando conoce su handle; no afirma cierre por timeout.

**Cambio deliberado del comportamiento sin argumentos:** sale78 con
INTEGRACION_FRONTAL_PENDIENTE antes de SSH y de cualquier movimiento.
--check conserva su consulta anterior de mapa; --check-front no llama al ciclo.
La secuencia histórica se conserva en el archivo pero no queda accesible
desde el modo run actual. No se añade un bypass. No se modifica
force_escenario1_first_part.sh; ese archivo conserva su comportamiento anterior
y NO dispone de selección frontal.

Prueba real del diagnóstico: goal2c9d1d54-3409-4912-8711-6a78e59c4c28,
status4/okTrue. Detecta dos cajas; elige índice1, bearing7,684802°,
base_link[0,799609;0,107895;0,383578]m. Resultado y TF comparten exactamente
stamp1789989425.799668000. Esto sustituye sólo la aproximación temporal de
la consulta anterior; NO demuestra equivalencia con X_BaseBox interno ni
margen robusto al límite X0,8m. Sin órdenes mecánicas.

Validación local:13 pruebas pasan (8 selector,5 probe/frescura/TF/bloqueo
antes de SSH), bash -n y git diff --check correctos. Shellcheck no instalado.

```bash
python3 -m unittest scripts.box_handling.test_select_front_box scripts.box_handling.test_probe_front_box
bash -n scripts/force_escenario1.sh
```

**Bloqueo técnico pendiente:** la rama nativa GetVisionBox pasa índice0;
use_box_target_pos/select_by_xyzCam no tiene soporte extremo a extremo
demostrado y la consulta directa fue rechazada. Los ejecutables instalados
inspeccionados no incluyen el código fuente necesario para modificar esa
rama. No se parchean binarios ni se altera globalmente percepción. Hace falta
una integración por tarea comprobable con MetaClamp que seleccione dentro
de su propia consulta; una comprobación previa seguida del agarre original
NO garantiza que vaya a coger la misma caja.

Destino y fuente reproducible: los scripts versionados enlazados arriba,
Python3 estándar en PC y dependencias ROS2 existentes en robot. Activación:
--check-front carga el código en un proceso temporal que termina; nada
instalado/cargado persistentemente en robot. Agarre físico: PENDIENTE.
Evidencia, copia de archivos anteriores y hashes:
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260921T111708Z_FRONT_SCRIPT`. Reversión local: restaurar únicamente
force_escenario1.sh desde before/scripts/force_escenario1.sh y retirar el probe
y su test; esa reversión recupera la selección original, NO el agarre frontal.
No requiere reinicio ni rollback remoto. Preservar los cambios posteriores
del operador si los hubiera; no sustituir por git checkout.

## Auditoría de integración nativa — 2026-09-21 13:28 Europe/Madrid

**HISTÓRICO; conclusión sobre necesidad de fuentes sustituida por la decompilación posterior.** El operador pide integrar todo. Se
inspeccionaron en lectura la interfaz ROSA Python y NodeOptions, la configuración
textual de /opt/walker y /etc/walker en Motion y las bibliotecas previamente
identificadas. No se encontró una opción de remapeo de la acción de transporte
ni un parámetro por tarea para cambiar el índice en esta rama. Esto es una
conclusión limitada a los archivos/API inspeccionados, no prueba de que todas
las versiones UBTECH carezcan de esa capacidad.

`/opt/walker/pose_6d_estimate/lib/pose_6d_estimate/box_pose_estimator_node`
expone las cadenas grasp y select_by_height, y no select_by_xyzCam; concuerda
con el rechazo registrado de esa etapa. `VisionUpdateConfig` sólo incluye
save_flag, save_path y boxes_sizes; StereoDepthRoi devuelve RGB/profundidad
de una ROI y no demuestra que cambie el filtro del agarre.
Los directorios include inspeccionados de manipulation_perception y
manipulation_meta_tasks no aportan headers de implementación utilizables.

El SDK original se mantuvo intacto. Se enumeraron en lectura los tres
archivos ubt_api_tiny_colcon.0624.tar.xz, ubt_api_tiny_python.0624.tar.xz y
Cruzer_S2-low-level-demo0624.tar.xz: no contienen rutas de implementación
con los nombres clamp/perception/vision/transport. Tampoco se encontraron
clamp_vision.* / perception_action_client.* / box_pose_estimator.* fuente
entre los archivos de /home/lacuna/proyectos/Robots inspeccionados.

Se descartó desplegar un adaptador suelto como solución terminada: sin un
cambio verificable del consumidor, MetaClamp seguiría usando su endpoint
y su índice original. No se aplicaron parches binarios, LD_PRELOAD, remapeos
globales, cambios de configuración, reinicios ni órdenes de movimiento.
El bloqueo rc78 del ejecutor se conserva. No se añadieron nuevas rutas de
agarre ni se declaró completa la integración. Se solicita al operador la
ruta de fuentes nativas o una build UBTECH con selección por tarea.

Requisito concreto para esa extensión:

1. Opt-in por tarea de selección frontal en GetVisionBox/GetBoxVisionPose.
2. Aplicar select_front_box sobre TODAS las poses de la misma respuesta
   que consumirá el agarre, transformadas con TF en el stamp exacto.
3. Entregar al planificador la pose medida original seleccionada, con
   trazabilidad de goal/candidatas/índice y sin inventar coordenadas.
4. Mantener comprobaciones de alcance, IK, fuerza y límites; si la frontal
   falla, no sustituirla por una lateral. Rechazar datos obsoletos/ambiguos.
5. Exponer comprobación sin ejecutar trayectorias y validar igualdad entre
   selección diagnosticada y pose realmente consumida por MetaClamp.

La prueba de introspección de NodeOptions en un proceso Python temporal
terminó por segmentation fault al salir sin inicializar el contexto ROSA;
no era el proceso de Motion. Puede haber generado core dump (ubicación
PENDIENTE); no se borró. El inventario posterior conserva manipulación,
hardware y servicios Motion Up3hours, sin reinicios de contenedores. No
interpretar ese inventario como verificación física de inmovilidad.

Evidencia privada de consultas y copias documentales previas:
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260921T112801Z_FRONT_NATIVE_INTEGRATION_AUDIT`; SHA256SUMS. Sin cambios persistentes
intencionados en robot, por lo que no hay configuración que revertir.
Punto de reanudación: localizar fuente/build compatible y conectar el
consumidor; los tests del selector y --check-front ya estaban superados.
