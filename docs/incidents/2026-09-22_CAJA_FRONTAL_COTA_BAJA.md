# Caja frontal a cota baja: selección recibida, agarre rechazado

22-09-2026, Europe/Madrid. **VERIFICADO por sesión SPS, Motion y fotografía
original del intento. Sin nuevas órdenes de movimiento del agente.**

El operador aporta otra ejecución de `force_escenario1.sh`:
MetaClamp UUID `52efbb3b-4963-4a86-add2-87a3ce6e7fa0`, 09:17:35 UTC,
`ClampBoxOutOfReach`/7101100/status6. Llegada get1 medida16,6/16,7mm y
0,310/0,319°. Este rechazo es posterior a la selección; no es el empate que
produjo NoneException en el intento anterior.

## Pose realmente enviada

Sesión `/tmp/cruzr-front-sps-l6uotv1u`, stamp1790068660.701830000.
El selector instalado devuelve índice3, pila[3], bearing8,3945°.
Pose de cámara original:
[-0,0929194724;0,9467645246;1,1446559011]m,
cuaternión XYZW[0,8500248083;−0,0082301468;−0,0065586746;0,5266375164].
SPS selección UUID `b9aaccf5-8799-4f6c-b2b4-0a84ade5b25c`.
Motion `GetSelectedVisionPose` y `X_CameraBox` registran la misma pose redondeada.
Reproducción offline con la captura y TF exacta conservadas produce idéntica
selección e idéntica pose de cámara. No hubo elección de una lateral por altura.

| Detección | X base_link (m) | Y base_link (m) | Z base_link (m) |
| --- | --- | --- | --- |
|0, lateral |0,761811|0,726632|0,901427|
|1, lateral |0,768259|0,735041|0,696203|
|2, lateral |0,770140|0,728523|0,476642|
|**3, frontal elegida** |**0,800556**|**0,118137**|**0,167063**|

Fotografía exacta guardada por Vision:
`/etc/walker/bag/vision/pose_6d_head_front/2026-09-22/17-17/1790068660.701830000_action_grasp.jpg`.
La etiqueta correspondiente aparece sobre la caja baja frontal derecha de la
pila lateral. Esta imagen histórica identifica la detección; no verifica
estado físico actual, despeje de recorrido ni ausencia de contacto.

**La escena/pose no equivale a la consulta anterior:** en el ensayo perceptivo
final previo, la caja superior frontal tenía Z≈0,7936m y X≈0,7835m. En este
intento tiene Z≈0,1671m y X≈0,8006m por TF. No presentar la prueba anterior
como validación de un agarre a esta cota. Z es la coordenada del punto que
define percepción en base_link; no es una medida manual de la base/soporte.

## Rechazo de trayectoria

Motion transforma por su propia cinemática y obtiene
`X_BaseBox=[0,803920;0,119211;0,174068]m`.
Su intervalo X admitido es[0,4;0,8]m: exceso3,920mm. El log permite continuar
con IK tras ese chequeo fallido; no aborta sólo por los milímetros.

Puntos VISION con offsets registrados:

- Mano izquierda: [0,5239;0,2206;0,1699]m.
- Mano derecha: [0,7989;−0,2322;0,1782]m.

La búsqueda `GetTorsoFromEef` prueba candidatos y registra cinco
`Cannot find matched IK011`, después `Query exceeds maximum count`,
`IK failed for eef poses in Cartesian` y
`both PositionAndRotationLimit and IkSolved checking failed, exit`.
El MetaClamp termina FAILURE tras≈1,206s. No se ejecutó su trayectoria de agarre;
los tres MetaMove de cabeza y brazos previos sí habían terminado SUCCESS.
No suponer HOME ni reiniciar el ciclo desde el principio por este informe.

**Conclusión acotada:** selección frontal y entrega a Motion verificadas;
la trayectoria/búsqueda de postura de separate_right_cruzr no encontró solución
para este caso bajo. No demuestra imposibilidad absoluta del robot ni una
altura mínima universal. No demuestra que avanzar4mm resuelva IK, ni justifica
ampliar límites, quitar controles o escoger una caja lateral. La tarea actual
es una secuencia de separación específica, no una recogida baja genérica.
No se encontró en los documentos consultados una receta ya validada para esta
cota que se pueda intercambiar automáticamente.

## Estado y siguiente trabajo

Prioridad del operador conservada: recoger la caja frontal incluso si es más
baja que las laterales. No se le pide medir de nuevo ni se prescribe elevarla
como solución definitiva. Para seguir hace falta validar una trayectoria y
postura adecuadas a esta cota (con modelo/IK y recorrido de ambos efectores),
o determinar con el proveedor la rutina admitida. No parchear signos,
orientaciones, offsets o límites para probar a ciegas.

No se envió nueva percepción, navegación, HOME ni agarre durante este diagnóstico.
Sólo lectura de logs/archivos y replay offline. El estado físico tras **este**
fallo no se infiere de la confirmación que dio el operador en el intento anterior.
Consulta posterior `cruzr_blue_workbin_cycle.sh --check`: rc0, 20 actuadores
habilitados/sin fallo reportado, velocidades0, delta máximo consigna0,002330rad,
paros0/0, cargador desconectado, batería45,8/48,2%, acciones libres. Es evidencia
instrumental de quietud/salud en esa consulta; no prueba HOME ni ausencia de
contacto/caja sujeta. No se envió orden de recuperación.

## Evidencia y registro BOX-01-FRONT-SPS

`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260922T091930Z_FRONT_STACK_REACH`.

Incluye original del operador, inventario redescubierto, logs Motion/HW/RouDi,
sesión íntegra y selección, TF y candidatos reconstruidos, imagen original con
ruta, replay, consultas/versiones y backups documentales antes/después.
RouDi no registra entradas en el intervalo consultado; esto no certifica toda
la comunicación del robot. No se atribuye el fallo a Iceoryx.

Cambios persistentes de esta intervención: documentación PC exclusivamente.
Selector/paquete74f5507e44addd71, trayectorias, límites, mapas y servicios no
modificados por el agente. Cambios locales del operador en los wrappers
preservados. Reversión documental selectiva desde before/, sin rollback remoto,
sin restauración de postura ni estado transitorio. `SHA256SUMS` fija evidencias.
Punto de reanudación: recogida a cota baja con selección correcta; agarre sigue
FALLIDO, ninguna nueva trayectoria probada.


## Repetición confirmada — 22-09-2026 11:31 CEST

Otro intento del operador, goal `e2b1c122-b3a1-41e9-8ea0-730466f946ff`,
09:27:37 UTC. Navegación651a290d… y llegada get1 verificadas por el script con
15,7/15,3mm, 0,306/0,287°. Visión habilitada SUCCESS. MetaClamp vuelve a
ClampBoxOutOfReach7101100/status6. El agente no repitió el movimiento.

Sesión `/tmp/cruzr-front-sps-uu3_s5cy`, pose/TF exactas conservadas,
stamp1790069262.628097000. Selección índice2, pila[2], bearing8,166°; original
cámara[-0,0894386;0,9434448;1,1417394]m y base_link
[0,799323;0,114699;0,171341]m. Motion registra la misma pose de cámara y
transforma a **X0,802563/Y0,115734/Z0,178277m**: exceso X2,563mm sobre0,8m.
Cinco `Cannot find matched IK011`, agotamiento de búsqueda y fallo conjunto
PositionAndRotationLimit/IkSolved. Es la misma clase de fallo del intento
anterior, con variación milimétrica; el selector no eligió una caja lateral.
El cambio de índice3→2 es orden/cantidad de detecciones, no prueba de otro
objeto. El replay del selector/contrato reproduce exactamente la entrega.

No dar por válido alcance sólo porque TF estime X0,7993m: Motion usa su propia
cinemática y el agarre también depende de una postura que su búsqueda rechaza.
No se afirma que la transformación esté mal calibrada sólo por unos milímetros.
Tampoco que repetir la navegación, ampliar límiteX o aumentar iteracionesIK
vaya a resolver la recogida baja.

Se revisaron herramientas offline locales: existen FK y análisis geométrico
URDF para abrazaderas, pero no se localizó un ejecutor de IK offline ya
validado que reproduzca esta rutina de MetaClamp. Esto acota el próximo trabajo:
reproducir los objetivos y validar una recogida baja antes de modificar la
trayectoria. No se generó ni aprobó una trayectoria nueva en esta revisión.

Diagnóstico de lectura, sin consulta perceptiva nueva, reinicio, cambio de
script ni orden física. No se reutiliza la lectura de salud del intento
anterior como estado actual. Evidencia y backups:
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260922T092921Z_FRONT_REACH_REPEAT`; incluye logs, sesión y replay. Reversión documental selectiva desde
before/. Agarres de este montaje siguen fallidos; no reanudar ciclo completo
por rutina.


## Repetición 55965b96 y comparación con selección original — 22-09-2026

**BOX-01-FRONT-SPS; VERIFICADO por lectura y replay offline.** Goal
`55965b96-a276-419b-a8d0-75312e1796f4`, 09:44:51 UTC; sesión
`/tmp/cruzr-front-sps-zxblb9ti`. Motion registra X_BaseBox
[0,803550;0,106654;0,181595]m, exceso X3,550mm y cinco fallos IK011,
seguidos de fallo conjunto de límites/IK y ClampBoxOutOfReach. El aviso
Shared memory OFF no es el rechazo. No se enviaron nuevas acciones.

Captura stamp1790070295.998716000: la candidata2 frontal está en
base_link[0,800605;0,105735;0,174821]m; candidata0 lateral en
[0,767838;0,716028;0,698010]m y candidata1 lateral en
[0,765401;0,717586;0,468999]m. El replay reproduce exactamente selección y
pose de cámara; posición y cuaternión enviados son los originales del índice2.
Motion registra la misma posición de cámara redondeada.

**INFERENCIA acotada:** aplicando la regla original índice0 a ESTA captura,
el objetivo sería una lateral, no la frontal. No se ejecutó la tarea original
ni una nueva consulta del detector; otra captura puede cambiar de orden.
Restaurar simplemente el nombre Singapore con las laterales presentes no
constituye una comparación controlada de ambas vías para el mismo objetivo.

Revisión local del constructor del paquete74f5507e44addd71: YAML igual al
snapshot salvo `request.special_box_name: box`; XML estructuralmente igual
tras retirar MetaLook sps_vision y restaurar el nombre de MetaClamp. Conserva
preparación, offsets, tiempos y límites. Sin embargo, la rama perceptiva sí
cambió: no se ha demostrado equivalencia funcional completa para una misma
caja/pose. El éxito histórico conservado no se ha identificado como el ensayo
concreto que recuerda el operador. **Corrección del punto de reanudación:**
antes de prescribir otra trayectoria, contrastar el contrato de ambas vías y
la pose del mismo objetivo. No atribuir el problema definitivamente a la cota
ni dar por descartada una regresión de integración.

Evidencia privada: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260922T094620Z_FRONT_REPEAT_55965`. Incluye inventario de contenedores, script
reproducible de lectura, logs, sesión y offline-comparison.json. Cambio de esta
intervención: documentación PC exclusivamente; sin modificación de scripts,
paquete, límites ni robot. Estado físico actual no comprobado. Backups before/
y copia after/ con SHA256SUMS; reversión documental selectiva. Comparación
nativa con el mismo objetivo y agarre físico satisfactorio PENDIENTES.


## Revisión de la corrección: IK alternativa y apoyo confirmado — 22-09-2026

El operador confirma ahora que la caja objetivo está **sobre una caja**.
No trasladar la confirmación histórica de dos apoyos al montaje actual. Imagen
exacta del intento55965b96, stamp1790070295.998716000, recuperada de Vision:
`/etc/walker/bag/vision/pose_6d_head_front/2026-09-22/17-44/1790070295.998716000_action_grasp.jpg`.
La superposición de la candidata2 aparece sobre la caja abierta frontal;
la imagen recortada no permite certificar toda su base ni el estado actual.
La coordenada Z interna no se equipara a altura del apoyo sobre el suelo.

**VERIFICADO estáticamente:** CheckPositionAndRotationLimit escribe100 en
Request+0x9bc (ELF0x12063b). HandleVisionOrientation compara ese campo con100
(0x10c2de), salta a la rama alternativa y llama CheckIkSolved (0x10c545).
El pseudocódigo confirma que esa llamada está condicionada por ese estado,
con ambos objetivos de mano disponibles. No son dos pruebas independientes
que siempre deban pasar: aquí se rechaza el intervalo y falla la alternativa.
El exceso X3,55mm puede ser relevante para activar esa rama; la búsqueda IK
fallida no prueba por sí sola que el agarre original sea inviable a esta cota.
No ampliar el intervalo ni falsificar X para eludir esa comprobación.

**Auditoría de percepción:** el éxito original archivado solicita literalmente
transport/head/grasp y tamaño[0,603;0,397;0,22], igual que el adaptador.
GetBoxVisionPose y GetSelectedVisionPose llaman ambas a
ConvertPoseMsgToRigidTransformd y SetObjectInfo; ClampVision converge después
en la transformación cámara/cuerpo común. Esto reduce la sospecha de una
conversión diferente introducida por SPS; no sustituye un ensayo nativo
controlado de equivalencia completa y no certifica calibración/percepción.

**INFERENCIA / siguiente validación:** comprobar colocación real con margen
respecto al intervalo original antes de rediseñar la trayectoria. La llegada
al waypoint admite5cm/3° en el script; no certifica margen de agarre.
Acercarse una distancia arbitraria no asegura éxito ni recorrido libre.
No integrar front_nudge: su prueba anterior retrocedió, RUN_QUALIFIED=False.
El punto exacto, método de ajuste y ensayo de recogida siguen PENDIENTES.
No se ha identificado ni instalado un parche que garantice recoger esta caja.

Sólo lectura remota de imagen/inventario y análisis estático de copia local
libmeta_clamp.so d6bc61a493f7d790150fdbd673108121f46589fef56620de4a9023dcc2ba520a.
Sin percepción nueva, movimiento, modificación de scripts, SDK, límites o robot.
Cambio persistente: documentación PC. Evidencia y backup/reversión selectiva:
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260922_GRASP_LIMIT_BRANCH` (before/, after/, SHA256SUMS).
Receta estática reproducible, desde la raíz del repositorio:

```bash
python3 scripts/box_handling/decompile_box_selection.py \
  --tool-dir ../Humanoide-vla-evidence/tools \
  --binary ../Humanoide-vla-evidence/20260921T110500Z_FRONT_BOX_SELECTION/libmeta_clamp.so \
  --output-dir ../Humanoide-vla-evidence/GRASP_LIMIT_BRANCH_NUEVO \
  --filter HandleVisionOrientation --filter CheckIkSolved
```

Las dos extracciones objdump acotadas se conservan junto al pseudocódigo y
manifest de Ghidra; offsets ELF originales, Ghidra añade base0x100000.


## Intento en posición actual c1c6c537 — 22-09-2026

**OBSERVADO en logs Motion recuperados, sin nueva orden física.**
Goal c1c6c537-f3fc-412c-a26d-2419bd439c4d, sesión
/tmp/cruzr-front-sps-xcnimkuz. X_BaseBox=[0,800690;0,109031;0,175936]m:
el exceso X es ahora **0,690mm**, no reutilizar3,55mm del anterior intento.
Cinco fallosIK011 y fallo conjunto del intervalo/alternativa de postura.
Sigue cerca del mismo umbral; no demuestra que sea ruido, descalibración,
incapacidad absoluta ni que avanzar0,69mm garantice un agarre correcto.

El código actual siempre navega a get1 en ambos wrappers; el fragmento del
operador comienza después y no permite establecer si en este intento hubo
navegación previa o una ejecución directa. No atribuir el fallo a esa navegación
sin evidencia. Cambiar sólo tolerancia de llegada podría bloquear más ensayos,
pero no corregiría por sí mismo la posición relativa. No se hizo ese cambio,
ni se falseó la pose ni amplió el límite. No se identifica un parche de software
validado para conseguir el agarre desde esta posición. Pendiente colocación
real con margen y validación del movimiento/agarre; no ensayar el avance corto
anterior, que retrocedió. Estado físico actual no verificado por esta lectura.

Evidencia privada reproducible y backups: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260922_FRONT_C1C6`.
Sólo lectura de logs/sesión y documentación; sin cambios de scripts ni robot.
Reversión documental selectiva desde before/; SHA256SUMS fija la evidencia.
