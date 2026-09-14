# Ejecutor de ensayo ENTRY410 por etapas

**Actualización vigente — 2026-09-14: READY→ENTRY410 probado físicamente,
5/5 etapas con éxito según el operador y sus cinco resultados Motion SUCCEED.**
HOME→READY nuevo y READY→ENTRY410 quedan completados para los ensayos comunicados.
Se conserva `force_entry.sh` del operador. Siguiente: lectura fresca y propuestas
VLA task 0 en shadow desde ENTRY; el agarre VLA aún no se ha probado.
[Registro del ensayo, Goal ID y evidencia](ENSAYO_READY_ENTRY410_20260914.md).


2026-09-14, Europe/Madrid. VLA-01. **Implementado y comprobado localmente;
no instalado, no probado en movimiento y sin habilitación física emitida.**

## Archivos y alcance

- `scripts/vla/run_entry410_stage.py`: ejecutor de una sola etapa.
- `scripts/vla/entry410_stage_contract.py`: identidad del informe, fuentes,
  XML, extremos, tiempos y habilitación específica del ensayo.
- `scripts/vla/runtime/entry410_installed_task_admission.py`: comprobación
  de archivos/registro y proceso dentro de Motion, sólo lectura.
- `scripts/vla/runtime/entry410_single_stage_remote.py`: cliente de acciones
  y monitor de articulaciones/paros dentro de `walker-ros.ros2-1`.

No sustituye el ejecutor antiguo E6.1C/ENTRY040, que sigue retirado. No activa
el checkpoint VLA ni publica consignas articulares. Una invocación solicita
una tarea Motion concreta y termina: no encadena etapas, no reintenta, no
recupera automáticamente. `reverse` exige el extremo correspondiente de esa
etapa, no admite una postura arbitraria tras interrupción.

Los cinco tramos comienzan en **READY**, no en HOME. La preparación HOME→READY
y el final READY→HOME quedan fuera de este ejecutor. No usar etapa1 desde HOME.

## Comprobación local utilizable ahora

Desde la raíz del repositorio:

```bash
ENTRY410_REVIEW=../Humanoide-vla-evidence/20260914T124504Z_ENTRY410-GAP220/stages410/review.json
.venv/general-home/bin/python scripts/vla/run_entry410_stage.py \
  --check --review "$ENTRY410_REVIEW" --step 1 --direction forward
```

`--check` no accede a la red. Comprueba identidad410, fuentes y modelos mediante
hash, cinco etapas exactas, extremos, duración y XML generado; rechaza escena
pendiente o sin certificar y límites configurados no contrastados. No etiqueta
el informe como aprobación de movimiento.

Para preparar una carpeta nueva con los diez XML y el fragmento **aditivo**
del registro, también sólo en el PC:

```bash
.venv/general-home/bin/python scripts/vla/run_entry410_stage.py \
  --prepare-installation /tmp/entry410-install-review-new \
  --review "$ENTRY410_REVIEW" --step 1 --direction forward
```

Se conserva el comentario DRAFT de los XML. El fragmento no sustituye
`task_list.yaml`. **No hay instalación o recarga automática.** La primera
carpeta preparada está en la evidencia indicada al final. Los nombres son
`s2_bio_vla/entry410_stage_01_forward` … `05_forward` y sus cinco `reverse`.

## Requisitos antes de usar `--run`

Se requiere un archivo de habilitación **revisado y respaldado por evidencias**,
schema `cruzr-entry410-stage-commissioning-release-v1`, para propósito
`supervised_empty_single_stage_trial`. El programa no lo genera. No crear un
JSON con banderas verdaderas para saltarse los pendientes.

El contrato exige:

- `review_sha256`, `authorized`, `reviewer` y hashes de las cuatro fuentes del
  ejecutor en `executor_sha256` (rutas absolutas).
- `evidence_sha256` y `evidence_roles`: `group_mapping`,
  `loaded_task_identity`, `scene_and_interfaces`,
  `commissioning_motion_and_stop_protocol`. Cada rol referencia una evidencia
  existente con hash verificado. El hash asegura identidad, no veracidad;
  el contenido necesita revisión técnica independiente del script.
- `task_list_sha256`, `boot_id`, `pid1_start_ticks` de Motion y `loaded_tasks`
  con tarea→hash XML; deben representar las tareas realmente cargadas. Copiar
  archivos o que el proceso sea reciente no basta para emitir esa evidencia.
- Tolerancias justificadas `position_tolerance_rad`,
  `velocity_tolerance_rad_s`, `stationary_joint_tolerance_rad`, positivas y
  como máximo0,02 en sus respectivas unidades. El máximo del programa no
  constituye una recomendación ni calificación física de esos valores.

La exclusión offline de13 pares del propietario permanece separada de la
evidencia de montaje/escena y no altera las protecciones de Motion.

Cuando exista ese contrato revisado, los comandos son:

```bash
.venv/general-home/bin/python scripts/vla/run_entry410_stage.py \
  --preflight --review "$ENTRY410_REVIEW" --step 1 --direction forward \
  --qualification /ruta/habilitacion-revisada.json \
  --evidence-dir /ruta/evidencia-preflight-nueva

.venv/general-home/bin/python scripts/vla/run_entry410_stage.py \
  --run --review "$ENTRY410_REVIEW" --step 1 --direction forward \
  --qualification /ruta/habilitacion-revisada.json \
  --evidence-dir /ruta/evidencia-etapa-nueva
```

`--preflight` comprueba el contrato y el auditor vivo existente; la admisión
remota de tarea/estado se repite inmediatamente antes de movimiento en `--run`.
La confirmación interactiva es específica de una etapa; la herramienta está
concebida para un operador en terminal, no para ejecución desatendida.

## Qué hace durante una etapa

Mantiene un bloqueo local de concurrencia; verifica el preflight canónico,
ausencia de otros publicadores y vuelve a consultarlo tras la confirmación.
Contrasta fuentes/contrato de nuevo. Dentro de Motion verifica XML, registro e
identidad del proceso; después usa el puente ROS. Exige20 articulaciones
finitas, sin errores, muestra recibida hace como máximo0,5 s y marca fuente de
edad0–0,5 s; ambos paros cero con lectura de como máximo3 s. Estos requisitos
de frecuencia todavía deben comprobarse en integración sostenida; una señal
lenta impide el ensayo, no se elimina el requisito para hacerlo pasar.

Exige extremo inicial estable durante0,5 s, envía una sola acción y observa
que las articulaciones permanezcan dentro de la envolvente de esa etapa con
las tolerancias revisadas. No verifica sincronía de una curva común ni es un
controlador de seguimiento certificado. Exige estado de acción4, resultado
Motion `SUCCEED` y extremo final estable durante0,5 s.

Ante error, paro o pérdida de telemetría solicita cancelación si dispone del
goal aceptado. **Cancelar una acción no demuestra detención física.** Si se
pierde la conexión o no se conoce la aceptación, el resultado puede ser
incierto; no se reintenta y se conserva un registro específico. El operador
debe intervenir con el E-stop ante movimiento/contacto inesperado. No usar un
timeout del PC como garantía de parada. El protocolo de ensayo debe resolver
estas condiciones antes de habilitarlo.

## Instalación y carga: todavía pendientes

Se ha preparado el contenido concreto para revisión, no un instalador remoto.
No usar el instalador E6.1C antiguo, ni recargar Motion con el paro liberado.
La instalación cualificada deberá respaldar registro/XML previos, añadir
únicamente estas entradas y verificar hashes; la activación debe seguir la
[guía de arranque](../guides/CRUZR_V020_BOOT_GUARD.md), teniendo en cuenta el
HOME interno. Registrar y verificar después la correspondencia de grupos y
la identidad efectiva de las tareas. No se ha completado ese procedimiento
en esta intervención ni se ha emitido el contrato requerido.

## Verificación y evidencia

Once tests locales pasan; cubren diez sentidos de etapa, inversión exacta de
extremos, rechazo de ENTRY040, archivos alterados incluso con hash actualizado,
cambios de fuentes, duración inconsistente, escena pendiente y autorización
booleana sin evidencia. Los diez XML reales pasan `--check`; `--run` sin
habilitación termina antes de la red. Sintaxis Python comprobada.

Consulta viva **sin enviar goal**: Motion contiene interfaces SWIG nativas y
no tiene `rclpy`/`rosidl_runtime_py`; el contenedor ROS sí tiene los tipos ROS2,
`ArmTask.Goal` contiene `task_name`/`yaml_args`, el resultado contiene
`state.desc` y el servidor `/mc/manipulation/action` responde al descubrimiento.
Se corrigió el destino del cliente a ROS manteniendo admisión de archivos en
Motion. No se probaron aún goal/cancelación/monitor en movimiento ni se atribuye
esa cobertura a los tests locales.

Evidencia: `../Humanoide-vla-evidence/20260914T125923Z_ENTRY410-EXECUTOR/`.
Incluye paquete local, consultas fallidas y corregidas, comprobaciones,
fuentes, respaldo documental `before/` y manifiesto. Cambio persistente sólo
en PC: cuatro fuentes del ejecutor, tests y documentación. Reversión: retirar
selectivamente esos archivos nuevos y restaurar documentos desde el respaldo,
conservando todos los cambios ajenos. No hubo instalación, recarga, cambio de
protecciones o movimiento del robot.

## Ampliación: instalador en disco preparado y plan vivo contrastado

2026-09-14, Europe/Madrid. El apartado anterior sobre ausencia de instalador
queda como estado histórico: ahora existen `install_entry410_stages.py` y
`runtime/entry410_install_disk.py`. **Aún no se han instalado las tareas.**

`--plan` consulta el registro actual y verifica que las diez claves y destinos
sean nuevos; sólo escribe el plan en el PC. `--install-on-disk` exige preflight
canónico con E-stop activo y específicamente `ESTOP_KEY=1` (paro principal),
cargador0, contenedores/modos requeridos y ausencia de otros publicadores.
El operador debe mantener el paro pulsado. No instala con el estado anterior
de paros liberados y no permite una recarga implícita.

El instalador vincula plan, informe, diez XML y fuentes mediante hashes; vuelve
a contrastar el registro justo antes de sustituirlo. Respalda el registro y
el paquete dentro de Motion en `/var/tmp/cruzr-entry410-backups/entry410-<tiempo>/`.
Crea únicamente XML nuevos con apertura exclusiva y añade entradas sin
reescribir el YAML previo. Conserva permisos/propietario del registro y lo
sustituye atómicamente. Ante fallo normal revierte si no detecta un cambio
concurrente ajeno; conserva evidencia para recuperación manual si lo detecta.
Un corte de conexión/energía puede dejar resultado incierto: inspeccionar
registro y backup, no repetir ni recargar automáticamente. Copiar fuera del
robot el backup y recibo antes de actualizaciones/recreación del contenedor.

Plan vivo calculado sobre registro SHA256 `c4873861…78c84f1`; registro resultante
previsto `82ac1bc8…d2e434e`. Diez destinos ausentes, sin conflictos. Una modificación
posterior del registro invalida el plan y exige regenerarlo.

```bash
ENTRY410_REVIEW=../Humanoide-vla-evidence/20260914T124504Z_ENTRY410-GAP220/stages410/review.json
.venv/general-home/bin/python scripts/vla/install_entry410_stages.py \
 --plan --review "$ENTRY410_REVIEW" --plan-file /ruta/plan-nuevo.json

# Sólo con paro principal pulsado y mantenido; NO recarga ni ejecuta.
.venv/general-home/bin/python scripts/vla/install_entry410_stages.py \
 --install-on-disk --review "$ENTRY410_REVIEW" \
 --plan-file /ruta/plan-nuevo.json --evidence-dir /ruta/instalacion-nueva
```

El plan concreto preparado está en
`../Humanoide-vla-evidence/20260914T132031Z_ENTRY410-INSTALL-PREP/install-plan.json`.
La carga posterior requiere el procedimiento de arranque y una nueva identidad
verificada; no reutilizar un contrato de otro arranque. Esta instalación tampoco
emite la habilitación para ensayo ni convierte el cliente ROS no ensayado en
validación física. La solicitud del operador cubre continuar; la comprobación
pendiente es **paro principal realmente pulsado**, no otra autorización genérica.

Quince tests pasan: siete del instalador y ocho del contrato de etapas. Incluyen
fallo de escritura inyectado, conservación literal del registro, backup, nombres
ajenos, hashes alterados y claves duplicadas. Sintaxis verificada. No hubo
instalación, movimiento o recarga en esta intervención; sólo consultas de lectura
a Motion y cambios de herramientas/documentación en PC. Respaldo local `before/`,
fuentes y manifiesto en esa evidencia. Reversión local: retirar sólo las tres
fuentes nuevas (instalador, helper, tests) y restaurar selectivamente documentos;
no existe aún una instalación remota de esta intervención que revertir.

## Instalación real y recarga realizadas

2026-09-14, Europe/Madrid. Operador confirma paro principal pulsado después de
confirmar HOME, abrazaderas vacías, zona libre, ruedas bloqueadas y ausencia de
otros mandos. Preflight vivo verifica principal1 y cargador0.

**INSTALADO EN DISCO:** diez XML en Motion, contenedor
`walker-motion.manipulation_robot_app-1`, bajo
`/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/s2_bio_vla/entry410_stage_*.xml`.
Registro `task_list.yaml` actualizado c4873861…78c84f1 →82ac1bc8…d2e434e.
Recibo con los diez SHA completos en
`../Humanoide-vla-evidence/20260914_ENTRY410_INSTALL_ACTUAL/receipt.json`.
Segunda lectura confirma todos los hashes. Backup remoto:
`/var/tmp/cruzr-entry410-backups/entry410-1789392478474447360/`.
Copia externa verificada en `backup-from-robot/` de la evidencia de instalación.

**RECARGADO UNA VEZ:** nuevo script `scripts/vla/reload_entry410_tasks.py`
verifica informe, recibo, copia externa y todos los hashes, consulta paro
principal activo y reinicia únicamente ese contenedor. Instancia antes
2026-09-14T13:26:42.399802944Z; después2026-09-14T13:32:04.614854174Z.
Hashes conservados tras reinicio. No llama tareas, servo enable, StartMotion,
HOME, ni libera el paro. Sintaxis comprobada y esta rama ejecutada una vez;
no representa un ensayo de movimientos. La carga efectiva por el gestor aún
no se acredita sólo con el reinicio y los archivos.

```bash
.venv/general-home/bin/python scripts/vla/reload_entry410_tasks.py --reload \
 --review ../Humanoide-vla-evidence/20260914T124504Z_ENTRY410-GAP220/stages410/review.json \
 --receipt ../Humanoide-vla-evidence/20260914_ENTRY410_INSTALL_ACTUAL/receipt.json \
 --evidence-dir /ruta/recarga-nueva
```

Receta de reproducción, **no una instrucción para repetir la recarga actual**.
El script exige backup externo y paro; no deduce recuperación por un reinicio.

Comprobación posterior: el guard devuelve `not_initial_boot_release`, sin
intento de recuperación. La instancia actual de Control Center conserva
secuencia TmpState→WaitEStopRelease→EnterWorkMode→SelfChecking→JoystickMode→
**WaitStartMotion**. Por tanto **no se indica liberar E-stop**. El boot guard
antiguo tiene su ejecución retirada y no corresponde aplicar una recuperación
para Fault a este estado. No se reinició CC ni hw ni se forzó StartMotion.
Continuación: procedimiento supervisado de apagado/arranque documentado,
conservando el paro, seguido de comprobación de carga y habilitación del ensayo.

Evidencia de recarga y estado:
`../Humanoide-vla-evidence/20260914_ENTRY410_RELOAD_ACTUAL/`.
Reversión de la instalación, sólo con paro principal y tras verificar que el
registro sigue siendo el SHA posterior: restaurar el registro respaldado y
retirar exclusivamente los diez XML cuyos hashes coincidan con el recibo;
si el registro ha cambiado, conservar entradas posteriores y preparar una
reversión selectiva. La vuelta de archivos a disco no descarga tareas del
proceso: activación posterior por procedimiento de arranque, sin recarga
ciega. Conservar backup externo antes de actualizar firmware o contenedores.
La instalación está realizada, la prueba física de ENTRY410 no.

## 2026-09-14 — VLA-01: comprobación posterior al arranque completo

VERIFICADO: el preflight vivo con paros liberados termina correctamente;
20 articulaciones, velocidad máxima cero, baterías75,5/77,1%, cargador
desconectado, ambos paros0, servidor de manipulación disponible, sin otros
publicadores de control y contenedores VLA detenidos. Los diez XML instalados
y el registro conservan los hashes del recibo después del reinicio. Esto
verifica archivos persistentes, no la identidad efectiva de tareas cargadas.
HOME es la postura comunicada ahora por el usuario; este preflight no demuestra
por sí solo coincidencia de las20 posiciones con el extremo HOME.

PENDIENTE: el ejecutor de cinco etapas comienza en READY. El wrapper
`scripts/vla/cruzr_vla_ready_pose.sh` mantiene bloqueado HOME→READY y exige
validación independiente. No ejecutar etapa1 desde HOME. También sigue sin
emitirse la habilitación de ensayo documentada en el ejecutor ENTRY410.
No se enviaron movimientos, no se reinició ningún servicio y no se modificó
el robot en esta comprobación. El arranque correcto no elimina estos pendientes.
Evidencia: `../Humanoide-vla-evidence/20260914T135826Z_ENTRY410-POSTBOOT/`,
con preflight, hashes posteriores al arranque y respaldo documental.
Punto de reanudación: resolver el acceso HOME→READY y la habilitación del
ensayo, conservando el robot en su estado actual; no repetir el ciclo de
encendido para resolver un requisito del ejecutor.

## 2026-09-14 — VLA-01: acceso medido a READY calculado por grupos

OBSERVADO: captura pasiva posterior al arranque, 14:07:23–14:07:33 UTC,
347 muestras articulares, ambos paros0, sin incidencias del analizador.
VERIFICADO OFFLINE: `scripts/vla/prepare_home_ready_access.py` genera cinco
tramos desde la última postura medida hasta el READY exacto del informe410.
Comprueba identidad de traza, ausencia de movimiento/fallos en toda la traza,
variación articular≤0,002rad, identidad del modelo y fuentes inmutables durante
el cálculo. Genera diez XML DRAFT para ambos sentidos; no instala ni publica.

Resultado bajo las hipótesis del informe GAP220:1018 pares con intervalos
geométricos certificados,54 con violación del margen del modelo,0 pendientes
y sin timeout. Los54 pares son exactamente los mismos del informe de etapas
ENTRY410; no se convierten en aprobados ni se eliminan del resultado. La
correspondencia de pares no transfiere automáticamente pruebas de otro tramo.
Duración propuesta136s: cabeza20, cintura1, elevador1, brazo izquierdo57 y
derecho57. Son tiempos de propuesta, no una medición ni una ejecución aprobada.

PENDIENTE: comprobar límites dinámicos/configuración efectiva, correspondencia
runtime de grupos, identidad cargada y protocolo del ensayo. Los XML de acceso
NO están instalados, el wrapper activo permanece bloqueado y no se ha emitido
habilitación física. No hubo reinicios ni movimientos. No es aún una ruta
HOME→ENTRY ejecutable.

Evidencia externa: `../Humanoide-vla-evidence/20260914_HOME_READY_ACCESS/`
(traza, análisis, access/review.json, diez borradores, comparación y fuentes).
Tests: cinco casos de admisión de postura pasan, incluidos movimiento anterior,
deriva con velocidad cero, fallo y dato no finito; los tres tests existentes
de construcción por grupos también pasan. No cubren movimiento real.
Receta reproducible: `docs/vla/ACCESO_HOME_READY_20260914.md`. Reversión local:
retirar selectivamente las dos fuentes nuevas y restaurar documentos desde
`before/` de la evidencia, preservando otros cambios. Ningún cambio persistente
en el robot.

## 2026-09-14 — VLA-01: límites compilados y decisión de habilitación

VERIFICADO: se extrajo sin cargar código vendor la tabla de7 registros de48
bytes en VA0x2fe20 de libs2_arm_kinematics.so (SHA2562a41cf55…ad251c).
Las ramas izquierda/derecha del constructor copian esa tabla y llaman a
SetJointLimits; los primeros dos doubles son límites de posición. Se mantienen
sin calificar los nombres de los cuatro campos escalares restantes. Los
límites compilados NO se presentan como lectura efectiva de la memoria del
controlador: pueden existir sustituciones posteriores. Tres tests locales
verifican extracción por segmento ELF, rechazo de hash distinto y datos mutables.

HALLAZGO: todos los extremos nominales del acceso quedan dentro de estos
límites bajo la correspondencia propuesta. Sin embargo, el error independiente
±1° produce máximos0,01639868/0,01841203rad en codoL/R frente a0,01rad compilado.
El error positivo que cabe desde los máximos nominales es0,63338°/0,51803°.
Esto es una incompatibilidad del dominio de error revisado con esos defaults,
no una colisión física observada ni prueba de que la trayectoria nominal falle.
No se redujo el error para conseguir un resultado favorable. El contraste
anterior con URDF/YAML era incompleto frente a estos defaults compilados.

Consulta viva: bibliotecas MetaMove, interpolación y cinemáticaS2 mapeadas
en PID66. No se adjuntó depurador ni se suspendió el proceso. Los topics
individuales de brazo/cintura/elevador no devolvieron estado; rosa puede
terminar con código0 y mensaje de error en stderr, por lo que no se tomó ese
código como éxito. /mc/whole_joint_states y /mc/joint_states sí dieron estados
con nombres, pero en órdenes diferentes. Esto confirma la necesidad de
mapear por nombre y no prueba el orden interno de MetaMove.

DECISIÓN: no habilitar todavía. No se fabricó una habilitación ni se cambiaron
protecciones. Siguen sin demostrarse orden/despacho efectivo de MetaMove,
límites efectivos frente a defaults y seguimiento/parada para el ensayo.
No hubo objetivos de movimiento, instalación o recarga del robot. Los borradores
de acceso permanecen sólo en PC. Evidencia y decisión explícita:
`../Humanoide-vla-evidence/20260914_MOTION_INTERNAL_CONTRAST/enablement-decision.json`.

Nuevo extractor reproducible:
```bash
.venv/general-home/bin/python scripts/vla/extract_s2_compiled_limits.py \
 --binary ../Humanoide-vla-evidence/20260914_MOTION_INTERNAL_CONTRAST/libs2_arm_kinematics.so \
 --review ../Humanoide-vla-evidence/20260914_HOME_READY_ACCESS/access/review.json \
 --output /tmp/limites-compilados-nuevo.json
```

Registro global VLA-01: cambios persistentes sólo PC (extractor, tests y docs).
Respaldo de esta adición en before-final/ de la evidencia, copia de fuentes
y hashes. Reversión: retirar selectivamente las dos fuentes nuevas y restaurar
esta adición documental desde el respaldo, preservando el trabajo previo.

## 2026-09-14 — VLA-01: ensayo físico de cabeza MetaMove y fallo de admisión

AUTORIZACIÓN: usuario confirmó HOME, abrazaderas vacías, cabeza/cuello libres,
ruedas bloqueadas, cargador desconectado, ningún mando y persona junto al paro.
Se verificó preflight vivo y XML oficial fijo cruzr/move_head_lower, SHA256
f3a73626…ea46c1, cabeza [yaw=0,pitch=−0,43]rad en2s. Revisión geométrica desde
estado nominal por nombre:1018 pares certificados,54 solapamientos del modelo
ya conservados,0 pendientes. No se reutilizó etapa1 ENTRY410 desde HOME.

EJECUTADO: una sola petición de acción, aceptada. La cabeza pasó de−0,00297209
a−0,42817239rad. Giro constante0,00057524rad; cambio observado máximo de otros
18 ejes0rad.312 muestras de motor; separación máxima entre muestras globales
0,03178306s. Velocidad máxima observada de pitch0,339292rad/s y discrepancia
máxima cmd_pos/posición0,364709°. cmd_pos es solicitado SIN LIMITAR, no la
consigna efectiva del servo: estos valores no califican el seguimiento futuro.
El usuario confirmó posteriormente suavidad y ausencia de contacto.

RESULTADO DEL EJECUTOR: FAILED_NO_RETRY, NO éxito validado. A1,97046s desde
dispatch, se detectó que la última muestra del paro principal tenía más de3s
y se solicitó cancelación. Se recibió respuesta, pero el registro de esta
versión no incluía código/lista de goals de la cancelación ni resultado final
de la acción. No se puede atribuir la detención a cancelación ni afirmar que
el E-stop se ejercitó. No hubo reintento ni HOME automático.

VERIFICACIÓN POSTERIOR: captura pasiva10s/348 muestras, sin incidencias, ambos
paros0 y velocidad máxima0 en todos los ejes. Estado al cierre: brazos/cuerpo
en su postura previa y cabeza baja estable, NO HOME completo. El E-stop físico
no fue accionado durante este ensayo según lo observado en los topics.

CORRECCIÓN PC: el monitor inicial admitía una sola muestra fresca de paro sin
comprobar su cadencia; eso permitió iniciar aunque su canal no sostenía el
umbral de3s. Ahora exige al menos dos muestras y comprueba intervalos antes
de dispatch. El intervalo posterior observado4,495s se rechaza antes de mover
en la regresión offline. Se mantiene el umbral3s: no se aceleran republicaciones
de valores cacheados ni se cambia el robot. Se registrarán además UUID del
goal, respuesta completa de cancelación y resultado tardío si está disponible.
Seis tests de envolvente/cadencia pasan. No se probó físicamente esa nueva
versión, no se volvió a ejecutar. Resolver la disponibilidad/semántica del
canal de paro sigue pendiente para este monitor.

Alcance cerrado: ejecución física del segundo componente de MetaMove/head y
detención posterior observada en este ensayo. NO califica cancelación, E-stop,
seguimiento/parada de brazos/elevador ni habilita ENTRY410.

Evidencias: ../Humanoide-vla-evidence/20260914_METAMOVE_TRIAL_PREP/;
../Humanoide-vla-evidence/20260914_METAMOVE_HEAD_CHECK/;
../Humanoide-vla-evidence/20260914_METAMOVE_HEAD_RUN/ (incluye fuentes EXACTAS
del ensayo antes de corregirlas, intent/result/trace/analysis);
../Humanoide-vla-evidence/20260914_METAMOVE_HEAD_AFTER/ (captura y regresión).
Fuente reproducible: docs/vla/ENSAYO_METAMOVE_CABEZA_20260914.md.

Registro global: robot sólo recibió la tarea citada y solicitud de cancelación;
ninguna instalación, recarga, cambio de fichero/firmware/protección. PC: nuevos
revisor, ejecutor de cabeza, monitor, analizador y tests. Reversión de código:
retirar selectivamente estos archivos nuevos y restaurar docs desde before-docs/
de la evidencia, preservando cambios ajenos. La postura física no se revierte
restaurando archivos: cualquier retorno requiere su propia orden comprobada.

## 2026-09-14 — VLA-01: semántica del topic de paro identificada

VERIFICADO estáticamente en unova_power/server13cea0b9…e1a6d: la rama CAN0x5b
publica cambios de ambos paros y suprime duplicados hasta reiniciar un contador
cada11 tramas. La cadencia4,5s no demuestra avería del paro; el monitor local
lo había tratado incorrectamente como heartbeat continuo3s. No se aumentaTTL
ni se cambia firmware/reporte/protección; notificación física y parada no quedan
probadas por análisis estático. ENTRY comprueba ahora cadencia antes de dispatch,
como el ensayo de cabeza, para evitar iniciar y fallar después. Doce tests pasan.
Sin HOME, READY, ENTRY, instalaciones o reinicios remotos. Auditor y dependencias
Capstone5.0.6/pyelftools0.32 sólo enPC/evidencia privada, sin SDK modificado.
Ver `docs/vla/ESTADO_PARO_Y_CADENCIA_20260914.md` para receta, hashes, evidencia,
respaldo/reversión y pendientes. Observación de pulsación estática solicitada;
no confundir solicitud con pulsación realizada ni liberar automáticamente.

## 2026-09-14 — VLA-01: acceso desde estado articular por nombre

VERIFICADO: captura nueva sólo lectura,98 pares de estados en5s, nombres
articulares completos, marcas de fuente crecientes y salud de actuadores.
Cabeza pitch−0,428268rad; cuerpo/brazos próximos a cero, inmóviles. El preparador
usa ahora /mc/whole_joint_states por nombre para geometría; los actuadores se
usan para salud/velocidad y no para inferir signo o posición articular.
El monitor ENTRY se corrigió con la misma separación y exige ambas fuentes
frescas, nombres completos/únicos, datos finitos y actuadores habilitados.
No confundir esta correspondencia del estado con el orden interno MetaMove.

Acceso medido→READY:1018 pares certificados,54 avisos internos conocidos,
0UNRESOLVED, sin timeout, duración nominal123s. Los54 avisos se conservan.
Contraste offline con snapshots archivados: posición/velocidad nominal20D
correctas; brazos nominales dentro de defaults compilados. No es lectura actual
de límites efectivos ni verifica aceleración de brazos, despacho o parada.
Veinte tests pasan, incluyendo orden permutado, nombres ausentes/duplicados,
no finitos y desacoplamiento entre posiciones motor y posiciones articulares.

Cambio PC: capture_named_entry_state.py, prepare_home_ready_access.py,
runtime/entry410_single_stage_remote.py y test_entry_named_state.py. Sin
instalación/reinicio ni movimiento remoto; no se generó habilitación física.
XML de acceso nuevos siguen siendo borradores locales, NO instalados.
La CLI del preparador exige ahora --named-capture; el antiguo --trace no se
usa para geometría. measured_start se conserva sólo como helper histórico.

Reproducción:
```bash
python3 scripts/vla/capture_named_entry_state.py --output-dir /ruta/captura-nueva
.venv/general-home/bin/python scripts/vla/prepare_home_ready_access.py \
 --reference ../Humanoide-vla-evidence/20260914T124504Z_ENTRY410-GAP220/route-review.json \
 --named-capture /ruta/captura-nueva/capture.json --output-dir /ruta/acceso-nuevo
```

Evidencia: ../Humanoide-vla-evidence/20260914_ENTRY_NAMED_STATE/ con captura,
access/review.json, límites, fuentes y hashes. Los backups están en before/.
Reversión sóloPC: restaurar selectivamente fuentes propias desde before/ y
retirar fuentes nuevas; no restaurar el monitor antiguo para habilitar movimiento.
Después de una actualización, contrastar ambos schemas/nombres y rehacer
captura/revisión; no transportar un contrato de otro robot/firmware.

PENDIENTE: semántica temporal y prueba de notificación física del paro,
despacho/carga efectivos de los grupos y contrato del ensayo. No hay GOAL
HOME/READY/ENTRY enviado. No se reclama retorno seguro desde cualquier postura.


## 2026-09-14 — VLA-01: revisión del bloqueo y corrección del monitor READY

VERIFICADO LOCAL/LECTURA. Autorización del dueño conservada. UBTECH respondió al
incidente completo indicando reinicio tras E-stop; no se usa ese comportamiento
como exigencia genérica de reparación previa. Se separa ensayo vacío supervisado
de validación general. Evidencia PICO→HOME del11-09 incorporada como observación
(2103 muestras, error máximo0,007568924rad), no como cota futura de READY.

Dos defectos concretos corregidos: el monitor exige progreso común de todos los
ejes dentro del segmento revisado, no sólo cajas articulares independientes;
las tolerancias de posición del contrato no pueden superar la banda geométrica
del informe (±1° en este caso), aunque sean menores que el techo genérico0,02.
31 tests pasan. Nuevas revisiones mantienen1018 pares certificados,54 avisos
internos retenidos y cero UNRESOLVED. 20 XML regenerados idénticos al receipt de
instalación: no hace falta reinstalar ni reiniciar por este cambio sóloPC.
No se envió movimiento ni se emitió habilitación ficticia.

Paquete vigente para revisión local:
../Humanoide-vla-evidence/20260914_READY_COMMISSIONING_REVIEW/package/access.json
El paquete anterior de READY410_EXECUTOR contiene hashes de fuentes anteriores;
no usarlo con el monitor modificado ni editar manualmente sus hashes.
Protocolo propuesto, evidencia y alcance pendientes en
[Revisión de habilitación](REVISION_HABILITACION_READY_20260914.md).
Fuentes cambiadas: runtime/entry410_single_stage_remote.py, entry410_stage_contract.py,
ready410_trial_contract.py y test_entry410_corridor.py, bajo scripts/vla/.
Backups before/, evidencia, fuentes y SHA256SUMS en el directorio citado.
Reversión selectiva de fuentes desde backup; no se recomienda volver al monitor
que admite combinaciones fuera del segmento. Estado físico sólo leído: cabeza
bajada alrededor−0,430665rad, resto próximo a HOME, inmóvil. No VLA físico ni
READY ejecutado. La parada y la ejecución efectiva nuevas no se declaran probadas.
