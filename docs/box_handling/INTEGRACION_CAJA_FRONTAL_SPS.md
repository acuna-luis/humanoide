# Integración frontal mediante percepción SPS

**22-09-2026 11:22 CEST — Nueva recogida baja rechazada; selección correcta.**
Goal52efbb3b… devuelve ClampBoxOutOfReach. Sesión/TF/imagen y Motion confirman
candidata3 frontal, no laterales. Pose nueva base_link≈[0,8006;0,1181;0,1671]m;
Motion≈[0,8039;0,1192;0,1741]m. Distinta de la caja aZ≈0,794m de la prueba
perceptiva anterior. Excede X3,92mm y falla IK011/búsqueda de postura; no basta
quitar el límite ni interpretar llegada get1 como alcance de agarre. Preparó
cabeza/brazos; no asumir HOME. Agente sólo diagnóstico, sin nuevas trayectorias
ni cambios de controles; recoger a esta cota sigue pendiente de validación.
[Informe y evidencia](../incidents/2026-09-22_CAJA_FRONTAL_COTA_BAJA.md).

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

**22-09 — Paquete vigente `a9eaf948512d2eb4`, instalado.** Añade OFF/cyclone a
clientes nativos, adaptador y flujo; parser admite el aviso INFO exacto de OFF.
`--check-runtime` real correcto, sin arrancar adaptadores ni ejecutar tareas.
Setup Motion/HW preparado, procesos principales todavía SIN RECARGAR.
Gates físicos intactos; alcance/IK y agarre pendientes. [Ficha COMM-01](../support/CRUZR_CYCLONE_SIN_SHM_20260922.md).

**22-09 — Ensayo frontal FALLIDO; diagnóstico de lectura VERIFICADO.** MetaClamp
sí recibió la caja frontal elegida, pero rechazó alcance/IK (X0,803542m).
RouDi retiró runtimes por heartbeat y abortaron cliente ROSA/adaptador; comunicación
sigue degradada. Robot inmóvil en postura preparatoria, **fuera de HOME**;
actuator_state sin muestra. No repetir ciclo ni reiniciar a ciegas. Usuario
confirma recogidas previas sin laterales y caja sobre otras dos; no pedir nuevas
medidas. Sin cambios remotos del agente. [Informe y reanudación](../incidents/2026-09-22_FRONTAL_SPS_ALCANCE_ICEORYX.md).

2026-09-21, Europe/Madrid. **BOX-01-FRONT-SPS — INSTALADO; enlace perceptivo
nativo VERIFICADO. Agarre físico y ciclo con esta variante PENDIENTES.**

Los dos ejecutores `force_escenario1.sh` y `force_escenario1_first_part.sh`
llaman ahora a `local_front_box/separate_right_cruzr`. La variante usa
`special_box_name: box`, con un adaptador temporal que selecciona por mínimo
ángulo horizontal respecto a `base_link`. No prioriza altura ni el orden del
detector; si la frontal es ambigua, obsoleta o inalcanzable, no se sustituye
por una lateral. La comprobación de alcance/IK continúa en Motion.

Ambos scripts conservan su secuencia previa completa get1→recogida→retroceso
20cm→put1→depósito→HOME, incluido el HOME que ya figuraba en el archivo del
operador al comenzar esta intervención. El nombre `first_part` NO lo convierte
en una prueba de recogida aislada. No reiniciar el ciclo si hay una caja sujeta.

## Uso y límites de la comprobación

Desde la raíz del repositorio, con abrazaderas vacías:

```bash
./scripts/force_escenario1.sh --check-sps
```

Ejecuta sólo el XML `local_front_box/detect_only`: habilita el cliente SPS,
detecta y selecciona mediante `MetaLook`. **Actualiza la caché perceptiva
`box/0` de Motion**; no es una consulta sin efectos en su memoria. No envía
trayectorias de cabeza, brazos, elevador o chasis. No usar con una caja sujeta
ni durante otro control. Rechaza objetivos de manipulación activos y exige
`manipulation_controller=running`, SDK/VLA inicializados e inactivos; no cambia
controladores. `--check-front` conserva el diagnóstico ROS2 anterior, sin
actualizar esa caché nativa; `--check` conserva la consulta del mapa.

Para el ciclo completo, sólo tras revisar la disposición física actual:

```bash
./scripts/force_escenario1.sh
```

Exige terminal y confirmación `CONTINUAR` sobre efector, caja libre, postura,
recorridos de brazos/caja/chasis, destino, modo de ruedas, paros, cargador,
control exclusivo y persona junto al paro, conforme a AGENTS.md. Ejecuta
además el preflight técnico existente `cruzr_blue_workbin_cycle.sh --check`:
salud articular20D, inmovilidad/consigna, paros, baterías, cargador y acción libre.
Después valida hashes del paquete/tareas/bibliotecas y arranca los adaptadores
sólo durante esa sesión. No hay autoarranque ni instalación al ejecutar.

Identificar correctamente la caja NO certifica el espacio para abrazaderas,
el barrido junto a las cajas laterales, la postura del torso, el alcance ni
el depósito. Los límites, fuerzas y trayectorias originales se conservan byte
a byte en el YAML salvo la adición `special_box_name`. No se han habilitado
comprobaciones geométricas que el proveedor tuviera desactivadas ni se afirma
que esa trayectoria sea apta para cualquier pila. La X medida sigue cerca
de0,8m y `base_link` no se ha demostrado idéntico al `X_BaseBox` interno.

## Enlace demostrado

1. `MetaLook`/la rama especial de `ClampVision` consultan detección aproximada
   en `/cv/task/sps_select_action` y después pose final en
   `/cv/task/sps_pose_action`. Los nombres son contraintuitivos: se verificaron
   en el constructor nativo, offsets0x9adbe–0x9adfc, y mediante ejecución.
2. El servidor ROSA propio pide una captura al proceso ROS2 mediante socket
   Unix privado. Ese proceso consulta el detector original
   `/cv/task/transport_action`, transport/head/grasp, tamaño0,603/0,397/0,22.
3. Exige status4/ok, marco óptico conocido, antigüedad≤2s y relación temporal
   con la petición. Obtiene TF en el stamp exacto; no acepta TF latest.
4. Clasifica todas las poses en `base_link` y conserva la pose original de
   cámara de la elegida. Detección SPS devuelve sólo esa candidata; selección
   SPS consume la misma transacción una vez. Datos ambiguos, petición sin
   detección, caducidad, cancelación o fallo invalidan la sesión.
5. El cliente C++ recibe y guarda la pose como `box/0`, la clave utilizada
   por `GetVisionBoxHistory`. No se devuelve la pose transformada de base
   haciéndola pasar por una medida de cámara.

El servidor acepta sólo SPS/box/0, sin tracking, máscara, nube o tamaños
alternativos. Antes de arrancar exige cero servidores SPS existentes; los
clientes persistentes de Motion son normales. No redirige el endpoint de
transporte ni otros objetos SPS. El supervisor impide dos sesiones propias
simultáneas; el operador sigue siendo responsable de excluir otros mandos.

La clase Python `ActionServer` del proveedor devolvía estado EXECUTING al
GetResult del cliente C++ antes de acabar la captura. Se usa una subclase
local que espera un resultado terminal hasta9s. No se modifica ROSA instalado.
La captura está acotada a7s; no hay éxito con vector de poses vacío. Al salir
se cierran los procesos; una concesión temporal máxima de900s limita su vida
si se pierde el supervisor. El flujo comprueba esa sesión antes de cada
etapa; al interrumpir el supervisor, solicita terminar sólo su shell y bloquea
nuevas órdenes mediante la marca stop. No es un watchdog físico ni demuestra parada
del robot al perder SSH. El flujo conserva sus abortos y parada solicitada
de navegación, sin reintento, apertura o HOME después de un fallo.

## Evidencia en esta unidad

**Éxito1:** tarea `local_front_box/detect_only`, goal
`fb548cf0-b984-4bc9-b2c8-fba840aa73b1`, SUCCEED/state1101001/status4.
Elige índice1 de2, frontal baja, bearing7,463°.
Pose cámara[-0,0768054;0,7516101;1,0532552]m;
base_link[0,7992784;0,1047018;0,3828935]m.
Detección y TF stamp1789991732.146605000.
Motion registra `Success to detect box with precision pose` con
XYZ[-0,0768;0,7516;1,0533], coincidente con el redondeo de la pose seleccionada.

**Éxito2, desde el wrapper definitivo `--check-sps`:** goal
`755685a3-56ae-4894-afe7-a0ef3d3f6207`, SUCCEED/state1101001/status4.
Índice1 de2, bearing7,368°;
base_link[0,7977887;0,1031655;0,3832363]m.
Pose cámara[-0,0752764;0,7518881;1,0517850]m; Motion registra
[-0,0753;0,7519;1,0518]. Detección/TF stamp1789991872.867667000.
Esto prueba recepción por **PerceptionActionClient mediante MetaLook**.
La conexión de MetaClamp se verifica por configuración/ensamblador; no se
ejecutó su trayectoria para afirmar una prueba física que no ha ocurrido.

**Éxito3, paquete final1fbe634748083afe tras añadir control de interrupción:**
goal `aed5add0-2fab-4c73-b904-c0c45f4d48a2`, SUCCEED/state1101001/status4.
Índice1 de2, bearing7,634°; base_link[0,7984858;0,1070280;0,3833352]m.
Pose cámara[-0,0791306;0,7513946;1,0524153]m. Detección y TF comparten
stamp1789992222.072397000. Sesión `/tmp/cruzr-front-sps-9b_5x59u` cerrada.

El preflight técnico independiente pasó:20D,14 brazos, velocidades0,
máxima diferencia de consigna0,000959rad, baterías73,8/72,7%, paros0/0,
cargador desconectado y acción libre. No sustituye la revisión presencial.

Dos intentos perceptivos iniciales fallaron antes de corregir orden de
endpoints y respuesta GetResult. El resultado externo arrastró la descripción
ClampBoxOutOfReach, pero los logs de estas tareas puramente MetaLook indican
fallo perceptivo; no hubo un nuevo ensayo de alcance ni trayectoria. Los
fallos y su corrección se conservan como evidencia, sin ocultarlos.

Pruebas locales:49 casos verificados (12 contrato/paquete,8 selector,5 probe,
24 flujo). La expectativa antigua de un test omitía el HOME presente en el
script del operador: se actualizó. La suite completa final terminó49/49 OK. Sintaxis
Bash/Python y diff check correctos. No commit ni push.

## Fuentes, instalación y estado persistente

Fuente reproducible: [front_box_integration.py](../../scripts/box_handling/front_box_integration.py),
[contrato](../../scripts/box_handling/front_sps_contract.py),
[servidor ROSA](../../scripts/box_handling/front_sps_native.py),
[worker ROS2](../../scripts/box_handling/front_sps_worker.py),
[supervisor](../../scripts/box_handling/front_sps_session.py),
[instalador remoto](../../scripts/box_handling/front_sps_install_remote.py),
[tests](../../scripts/box_handling/test_front_sps.py).
Reutilizan selector/probe existentes; stdlib PC, ROSA y ROS2 ya instalados.

```bash
# Paquete revisable fuera del robot; directorio nuevo:
python3 scripts/box_handling/front_box_integration.py --build /ruta/nueva
# Instalación aditiva, sin reinicio ni ejecución de trayectoria:
python3 scripts/box_handling/front_box_integration.py --install
```

Ambos modos de conexión admiten `--wifi`. El paquete identifica sus fuentes
por SHA256; ID vigente `a66aa93932ef9bdb`. El instalador rechaza divergencias
en originales/dependencias y conflictos en destinos; no sobrescribe originales.
No cambia `task_list.yaml`: carga de los XML nuevos comprobada sin reinicio.

Destinos exactos en Motion192.168.11.2:

- Host: `/var/tmp/cruzr-front-box/a66aa93932ef9bdb/`, manifiesto y recibo.
- Contenedores `walker-motion.manipulation_robot_app-1` y `walker-ros.ros2-1`:
  `/opt/cruzr-front-box/a66aa93932ef9bdb/`, seis módulos Python.
- Contenedor Motion, raíz
  `/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/`:
  `local_front_box/detect_only.xml` y `local_front_box/separate_right_cruzr.xml`.
- Contenedor Motion, raíz
  `/opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config/meta_clamp/`:
  `local_front_box/separate_right_cruzr.yaml`.

Los hashes exactos de cada fuente/tarea y las tres bibliotecas vinculadas
están en manifest.json y en bundle.json de la copia externa. Paquetes anteriores
de esta intervención (inactivos, no reinstalar):5ad181e9b79e17f4,
d25df81839d15d10,539e162b626c0a5d,f0663faa0e1e2dd7,d0024477b566018e,
54dd8f56f6bb2f56,1fbe634748083afe (sustituido el22-09).
El primero quedó parcialmente copiado por permisos de escritura en `/opt`
del contenedor ROS2; se corrigió usando root sólo para crear el directorio.
Se conservaron estos paquetes como historial, sin apuntadores de autoarranque.

Estado al finalizar el21-09 (histórico): archivos instalados; diagnóstico cargado y probado;
sesiones auxiliares cerradas, SPS sin servidores. Motion conserva clientes
SPS inicializados y la última pose de diagnóstico en caché. No restaurar una
pose antigua: toda recogida frontal debe adquirir una detección nueva.
Vision puede conservar sus imágenes diagnósticas habituales. No se modificaron
SDK original, bibliotecas, servicios, límites, mapa ni configuración del detector.

## Respaldo y reversión

Evidencia externa:
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260921T114523Z_FRONT_SPS_INTEGRATION`.
Incluye before/ de scripts/documentos, paquetes completos, inventario, logs,
consultas, copia de sesiones y SHA256SUMS. Sesiones robot conservadas:
`/tmp/cruzr-front-sps-c9akqxlf` y `...-wf1y_qkc` (fallos),
`...-tm_2y7vl`, `...-8f0jn6cj` y `...-9b_5x59u` (éxitos). No depender de /tmp para reinstalar.

Reversión sin mover: con acciones terminadas y cero servidores SPS, comparar
primero SHA256 de los tres archivos `local_front_box` con el manifiesto.
Retirar sólo esos archivos nuevos si siguen coincidiendo; no tocar los XML/YAML
`Singapore`/`wrc` originales ni task_list.yaml. Retirar los directorios propios
del paquete en ambos contenedores y host cuando no haya procesos que los usen.
Restaurar selectivamente los wrappers desde before/, conservando cambios
posteriores. Esa reversión recuperaría la selección ordinaria por índice0.
No requiere reiniciar Motion ni enviar HOME. La caché/percepción inicializada
es estado transitorio y no se convierte en una trayectoria de recuperación.

Punto de reanudación: revisión física del montaje y ensayo supervisado del
agarre frontal; recogida, retirada y depósito de esta variante aún no probados.

## Correccion del descubrimiento SPS 2026-09-22

**BOX-01-FRONT-SPS, Europe/Madrid — INSTALADO; preflight de lectura VERIFICADO;
agarre físico PENDIENTE.** El intento del operador terminó rc78 antes de
arrancar adaptadores o enviar la navegación, pese a superar el preflight20D.
La lectura actual de ambos endpoints SPS devolvió rc0, stdout `\n`, stderr
vacío. El listado nativo completo contiene Motion/transporte y ningún endpoint
SPS. Se confirma ausencia en esas consultas, no un servidor en conflicto.
Puede ocurrir antes de inicializar los clientes SPS; no se presupone un reinicio.

La comprobación anterior exigía literalmente `Action server count: 0`, texto
que ROSA sólo había devuelto en las pruebas del21-09 con clientes inicializados.
Ahora el supervisor consulta primero `rosa action list --no-daemon -t`, exige
formato válido y acciones Motion/transporte con sus tipos esperados; luego
consulta ambos endpoints con timeout. Acepta salida vacía sólo si la acción
estaba ausente del listado válido. Los clientes con cero servidores siguen
admitidos. Rechaza servidores presentes, tipo incorrecto, salida contradictoria,
timeout, errores de CLI y grafo vacío/incompleto; muestra la causa y salida
acotada cuando falla una consulta. No se inicia SPS para ocultar la ausencia.

El modo adicional ejecuta hashes, descubrimiento, inactividad de la acción y
controladores, y sale antes de crear la sesión, adaptadores o tareas perceptivas:

```bash
python3 scripts/box_handling/front_box_integration.py --check-runtime
```

**Resultado real: rc0 / CHECK_SPS_RUNTIME_OK**, ambos endpoints `absent`.
No es el chequeo de batería/paros/postura ni el diagnóstico de selección;
el ciclo conserva el preflight físico/técnico completo del wrapper.
Los dos wrappers consumen automáticamente el supervisor corregido mediante
el ID del paquete; no se modificaron sus etapas en esta intervención.

Paquete vigente `a66aa93932ef9bdb`, anterior `1fbe634748083afe` preservado.
Instalado con el instalador versionado: seis módulos por contenedor y paquete
del host en los destinos indicados arriba; `created_tasks=[]`, cero originales
sobrescritos, reinicios o comandos de movimiento. XML/YAML y bibliotecas siguen
idénticos. Cargado y probado: supervisor en modo de lectura; worker/servidor de
percepción y agarre NO ejecutados en esta intervención. No se actualizó box/0.

Validación local:21 tests de contrato/paquete/supervisor pasan, incluidos nueve
nuevos de descubrimiento y salida anticipada de `--check-runtime`; AST Python
y `git diff --check` correctos. Los49 tests completos del21-09 quedan como
histórico; no se afirma una nueva ejecución de toda aquella suite.

Respaldo externo de archivos locales anteriores, paquete anterior del robot,
fuentes finales, bundle/manifiesto nuevo, recibo de instalación, lecturas y hashes:
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260922T063716Z_FRONT_SPS_DISCOVERY`.
Los SHA256 de fuentes/tareas/bibliotecas están en `package/bundle.json`;
`SHA256SUMS` inventaría evidencia y backups sin depender de Git o /tmp.
Reproducir con `--build /ruta/nueva`, `--install`, `--check-runtime` del
integrador; no requiere reiniciar contenedores ni activar controladores.

Reversión de esta corrección: con el ciclo terminado, restaurar selectivamente
los cambios de `front_sps_session.py` y `front_box_integration.py` comparando con
`before/`, conservando cambios posteriores; volverá a calcularse el ID anterior
si sus seis fuentes coinciden. Ese paquete está preservado en Motion y en
`robot-package-before.tar.gz`. El paquete nuevo puede permanecer inactivo;
no borrar los tres XML/YAML compartidos con la versión anterior. La versión
anterior recuperaría también el falso rechazo con SPS ausente.
Punto de reanudación: revisar las condiciones físicas actuales y ejecutar el
ciclo supervisado; esta corrección no demuestra alcance ni éxito del agarre.
