# Procedimiento de cajas recibido de UBTECH — 14-09-2026

**Archivo en el repositorio — 2026-09-16:** ya no es necesario depender de
Descargas o del chat para consultar estos materiales. Ambos escenarios, otros
XML de Cruzr S2 y las dependencias seleccionadas están en el
[catálogo local](../../vendor/ubtech/cruzr_s2/README.md). Los DOCX español/chino,
con credenciales omitidas, figuras y extracción de texto están en
[docs/vendor/ubtech/box_handling](../vendor/ubtech/box_handling/README.md).
Las copias no activan tareas ni sustituyen la comprobación de parámetros.


Estado: AFIRMACIÓN DEL PROVEEDOR, no ensayo en nuestra unidad. Se revisaron
el texto y las ocho imágenes del DOCX. No indica versión de firmware,
checkpoint, algoritmo, script ni configuración exacta. No demuestra que sea
el VLA suministrado. No se ejecutaron instrucciones de botones ni movimientos.
Las credenciales del documento no se transcriben ni versionan.

## Lo que aporta

- Mapeo y registro de puntos por la web. Dos escenarios diferentes.
- Escenario con rack de rodillos: cajas60×40×23cm, palés80×60×26cm,
  mesa91,5cm; cotas de rack y puntos get1/put1/get2/put2/get3/put3.
  La referencia de varias cotas es el centro de la rueda derecha.
- Escenario con dos estanterías: cajas40×30×23cm; niveles bajos70/90cm
  y altos125cm. Distancias de puntos desde el centro del saliente/bumper
  frontal hacia el rack: get1=12,5cm, put1=33,5cm, get2=12cm, put2=31cm;
  exige alineación perpendicular centrada. No son distancias desde rueda.
- Secuencia del segundo escenario: get1→put2 para caja cargada, después
  get2→put1 para otra caja vacía. No describe volcar/vaciar una caja.
- Según proveedor: G a derecha y volver inicia selección/localización y tarea;
  E abajo y volver al centro, después G, repite tras recolocar cajas.
  A termina después de navegar al siguiente punto, no se describe como paro
  inmediato. Dice reiniciar para volver a ejecutar tras esa interrupción.
  No aplicar estas acciones sin identificar el paquete instalado y su escena.

## Preguntas históricas antes de la respuesta y del XML

Superadas parcialmente: no reenviar esta lista. Las preguntas vigentes están al final.

1. ¿Qué algoritmo usa cada escenario (VLA, detector o combinado), qué versión,
   checkpoint/paquete y efectores requieren? ¿Está ya instalado en nuestra unidad?
2. ¿Qué archivo/servicio/comando lanza G y cómo seleccionar los dos flujos desde
   un script? Facilitar configuración funcional mínima y mapa de etapas/puntos.
3. ¿Dónde editar dimensiones, alturas, poses y tolerancias, para detector y VLA?
   ¿Mesa72,5cm y nuestra caja/abrazaderas necesitan otro perfil o entrenamiento?
4. ¿Existe rutina oficial recoger abajo→vaciar contenido en otro lugar→depositar
   esa misma caja vacía en un tercero? Este documento no incluye el vaciado.
5. ¿Cómo reanudar desde caja sujeta/ya depositada sin repetir agarre ni reiniciar?
   Precisar el alcance de A y la diferencia frente a E-stop; el fallo SIGABRT
   ya documentado se conserva como incidencia separada.
6. ¿Pueden enviar plano acotado con orientaciones y correspondencia de puntos?
   El primer flujo dice depósito inferior derecho para put1 y put2; confirmar
   si la segunda referencia es una errata.

## Relación histórica con el trabajo pendiente

No cambia por sí solo los límites de hardware ni valida nuestro ENTRY. La
adaptación de cabeza READY a−0,63rad sigue pendiente de ejecución de los
cálculos/validación: se añadieron prepare_ready_head_hardware_limit.py y tres
tests que pasan, pero NO se generó referencia revisada, instaló ni movió.
Antes de instalar una adaptación conviene identificar si este SOP permite
usar la secuencia oficial suministrada para nuestro escenario.

Fuente privada: /home/lacuna/Descargas/Cruzr S2 搬箱子操作流程.docx.
SHA256: f43f8b6ea12db16fe322bb2fe0ad9d04d1150486927a47e057e5b4fac08662bc.
Evidencia externa: ../Humanoide-vla-evidence/20260914_UBTECH_BOX_SOP/.
No cambios remotos. Reversión documental: restauración selectiva desde
before-docs/ y retirada de este resumen, conservando trabajo previo.


## XML recibido posteriormente: configuración concreta del flujo

2026-09-14, VERIFICADO EN ARCHIVO, no instalado ni ejecutado. Fuente:
`/home/lacuna/Descargas/utars_task_zhucheng_env_20260428_start.xml`.
SHA256 `98d12aafcedfc5d08f064574e0714eb88ebcfeff70cd25515a919a5ca7fea5bf`.
XML bien formado, formato BTCPP4, árbol principal `test`. Esto no demuestra que
los nodos personalizados estén disponibles ni que el árbol pueda ejecutarse.
Copia privada y extracción estructurada: evidencia
`../Humanoide-vla-evidence/20260914_READY410_BOOT_AND_VENDOR/`.

El proveedor había afirmado que el manejo de cajas utiliza su VLA integrado,
que enviaría un flujo preconfigurado, que el vaciado debe desarrollarse y que
la recuperación predeterminada libera el agarre. Son afirmaciones del proveedor;
no se ha comprobado que este archivo corresponda a checkpoint-40000.

### Secuencia literal

1. Inicialización y voz; `RemoteControlNode` y `TaskSequenceNode` coordinan
   `taskControl`. `flysky:=1` apunta al mando; la relación con G no se define aquí.
2. `NUM_TIMES_ENV` fija el número de repeticiones; selección de navegación
   mediante `NavigationModelSelect`.
3. Navegar a `get1`; ejecutar `cruzr/half_back_sit`; agarrar con
   `ManipulationSubTreeGrabBoxByTargetPos`, `TaskName="zhucheng/clamp_cruzr"`,
   `boxSize="[0.4,0.3,0.22]"`, `targetPos="[0,0.0,0.7]"`.
4. `cruzr/back_sit`; navegar a `put2`; llamar primero al subárbol de depósito
   con `cruzr_clamp/cruzr_series_put/move_up_cruzr_json_xx_high_dual_link_clamping_box`
   y después con `zhucheng/put_cruzr_low`, ambos con `putHeight="0.7"`;
   finalizar con `cruzr/home`.
5. Navegar a `get2`; mismo subárbol/tarea de agarre con
   `targetPos="[0,0.0,1.2]"`; ejecutar `cruzr/back_sit`.
6. Navegar a `put1`; mismo primer subárbol de depósito y después
   `zhucheng/put_cruzr_high`, ambos con `putHeight="1.2"`; `cruzr/home`.

Todos los seis usos de `boxSize` contienen el mismo vector: el flujo no cambia
realmente el tamaño entre las secuencias aunque sus descripciones digan caja
grande/pequeña. Las magnitudes sugieren metros (400×300×220 mm), pero el XML no
especifica unidades ni el marco/origen de `targetPos` o `putHeight`. No asumir
que el último componente es directamente la altura del tablero ni modificarlo
por la altura de nuestra mesa sin leer el subárbol.

No aparecen posiciones numéricas de navegación: usa puntos guardados por nombre.
No contiene vaciado, control de inclinación de la caja, tercer destino para
la misma caja ni recuperación específica con carga. La rutina nueva de ENTRY
instalada por nosotros no se invoca: el archivo usa tareas de proveedor distintas,
incluyendo nuestro `cruzr/home` instalado si se resuelve en esta misma unidad.
No mezclar ambos flujos automáticamente.

### Dependencias que todavía faltan

Incluye `subtrees/Navigation/navigationCollection.xml` y
`subtrees/Manipulation/manipulation.xml`, no adjuntos al archivo recibido ni
localizados por nombre en la copia local/repositorio/evidencia revisados.
No se hizo una búsqueda remota de esos subárboles durante el arranque.
También se necesitan las tareas Motion referenciadas, sus nodos registrados,
el archivo de selección del árbol y el lanzamiento/entorno de `NUM_TIMES_ENV`.

El XML no menciona VLA, checkpoint, inferencia ni tareas VLA0–3. El agarre tiene
la descripción china `运控泛化动作` (acción generalizada de control de movimiento).
Eso no demuestra detector ni descarta un VLA dentro del subárbol. Hay que resolver
la aparente diferencia con la explicación del proveedor leyendo las dependencias.

### Preguntas vigentes, sin repetir lo ya respondido

1. Facilitar ambos includes y las tareas Motion referenciadas, junto con ruta de
   instalación, comando de lanzamiento y configuración de `NUM_TIMES_ENV` para
   nuestra v0.2.0. Confirmar qué paquete/versiones necesitan esos nombres.
2. Aclarar si `ManipulationSubTreeGrabBoxByTargetPos` → `zhucheng/clamp_cruzr`
   usa el VLA integrado mencionado o una primitiva generalizada de Motion; si
   usa VLA, identificar relación con checkpoint-40000. Es una pregunta sobre
   este archivo concreto, no repetir la consulta genérica detector/VLA.
3. Precisar unidades, orden y referencia de `boxSize`, `targetPos`, `putHeight`:
   centro/base de caja, tablero o referencia interna; y qué valores editar para
   nuestra caja603×397×217mm y tablero725mm. El SOP indica23cm y alturas70/90/125cm;
   este archivo muestra0.22 y0.7/1.2: confirmar qué disposición corresponde.

No volver a preguntar si existe dumping: ya contestaron que debe desarrollarse.
No pedir de nuevo dónde se escribe el tamaño a nivel del árbol: ahora conocemos
`boxSize`; falta su semántica y alcance en el subárbol/backend.


## Actualización: archivos encontrados en la unidad, 2026-09-14

La búsqueda remota posterior localizó el XML recibido y ambos includes bajo
`/opt/walker/task_manager/share/task_manager/config/cruzr_s2/` en Vision.
El XML principal tiene exactamente el mismo hash que el adjunto. También se
localizaron las cuatro tareas citadas en el directorio config de Motion.
Por tanto, ya no hace falta solicitar esos archivos; sí falta confirmar el
lanzamiento/selección del flujo y semántica de sus parámetros.

El subárbol de agarre envía `"boxInfo":{"size":... ,"targetPos":...}` como
yaml_args; el de depósito envía `"boxInfo":{"size":...},"height":...`.
Contiene reintentos (hasta5 adicionales) para errores de visión7101100/7101003.
No es un simple movimiento de brazos: clamp_cruzr incorpora movimiento inicial,
visión transport_vision/pointclouds_vision, control MetaClamp y retroceso de
chasis de0,5 en delta_pose. El depósito bajo abre brazos y retrocede0,4.
No se ha ejecutado este flujo ni validado su escena.

`manipulation_meta_tasks/config/meta_clamp/zhucheng/clamp_cruzr_zc.yaml` expone
el control de movimiento: duración6s/frecuencia500, puntos VISION/RELATIVE,
box_size[0.4,0.3,0.22], control bimanual y offset de efector±0,095 en Z.
request.enable_self_collision_check está false en el archivo existente;
no se cambió ni se trasladó ese ajuste a nuestros ensayos. Las opciones de fuerza
no equivalen a límites de carga admisible. No aparece una llamada explícita al
checkpoint-40000 en la cadena XML/YAML revisada.

Pregunta de arquitectura ahora concreta: «Our installed XML is identical to
your sample and calls MetaLook + MetaClamp with clamp_cruzr_zc.yaml. Where does
the supplied VLA/checkpoint-40000 enter this particular workflow, or is this
the vision-based motion-control example?» Mantener las preguntas de lanzamiento
y referencias geométricas. No reenviar la solicitud de archivos ya encontrados.

Copias y hashes: ../Humanoide-vla-evidence/20260914_READY410_HEAD_PREP/
(vendor-files/, vendor-dependencies.json, vendor-motion-tasks.json,
metaclamp-configs.json). Sólo lectura; ningún despliegue del ejemplo.

## Escenario 1 localizado en robot, pero no seleccionado — 2026-09-16

VERIFICADO EN LECTURA, 08:17 Europe/Madrid. La revisión local anterior no incluía
este XML: ahora se encontró en Vision, contenedor walker-system.task_manager-1:
`/opt/walker/task_manager/share/task_manager/config/cruzr_s2/utars_task_canada_wrc_20250930_start.xml`.
Su secuencia coincide con el escenario 1 del SOP:

- get1 → Singapore/separate_right_cruzr → cruzr/mobot_back_20 → put1 →
  wrc_cruzr/put_cruzr_wrc_low → cruzr/home.
- get2 → Singapore/clamp_cruzr → cruzr/mobot_back_20 → put2 →
  wrc_cruzr/put_cruzr_wrc_low → cruzr/home.
- get3 → wrc_cruzr/clamp_cruzr_wrc_high → put3 →
  wrc_cruzr/put_cruzr_wrc_chitu → cruzr/home.

Incluye NavigationLocation, RemoteControlNode y TaskSequenceNode; no basta
con tener puntos en el mapa. Contiene reintentos de agarre (10/5/5), por lo que
no debe confundirse con un ensayo de un solo movimiento. Las seis tareas
específicas y de retroceso consultadas existen como XML en Motion; eso no prueba
su registro/carga ni que las cotas internas coincidan con nuestra instalación.

**Selección efectiva actual: NO es este escenario.**
`/etc/walker/system/task_manager/config/task_config.yaml` contiene
`config_file: default_task_config.xml`. El log del arranque actual confirma la
carga desde `/opt/walker/task_manager/share/task_manager/config/cruzr_s2/default_task_config.xml`.
Ese árbol sólo anuncia en chino: «No se ha especificado una tarea; selecciónela
en la web y reinicie el gestor de tareas». El log conserva esa llamada TTS;
no se afirma que se oyera ni que completara bien. Las fechas de los logs del
robot usan otro reloj/zona; la consulta se realizó el 16-09 a las 08:17 local.

Por tanto: flujo compatible presente, pero no seleccionado/activado. No se
inspeccionaron los seis puntos del mapa ni la disposición física en esta consulta.
Falta seleccionar el árbol, verificar parámetros/dependencias y mapa/escena antes
de ejecutar. No se cambió ningún archivo remoto, no se reinició ningún servicio,
no se accionaron botones ni se enviaron objetivos o movimientos.

Evidencia: ../Humanoide-vla-evidence/20260916_SCENARIO1_DISCOVERY/:
scenario-candidates.json, active-config.json, log-config.json, motion-tasks.json,
copia del XML y SHA256SUMS. Esto sustituye únicamente la ausencia del XML en las
copias locales: el hallazgo remoto no demuestra que el flujo se haya probado.
