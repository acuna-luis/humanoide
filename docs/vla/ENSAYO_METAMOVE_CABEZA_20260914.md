# Ensayo supervisado de cabeza MetaMove — 2026-09-14

El ensayo ejecutado dejó la cabeza baja y estable. El monitor interrumpió la
comprobación por cadencia insuficiente del topic del paro. No repetir desde
la postura actual: el ejecutor exige HOME numérico completo.

El script está restringido a `cruzr/move_head_lower`, hash fijo, dos segundos.
No es un ejecutor de ENTRY ni acepta tareas arbitrarias. La versión corregida
debe rechazar la cadencia observada ANTES de mover. No se ha relajado ese gate.

Reproducción de análisis offline:
```bash
.venv/general-home/bin/python scripts/vla/analyze_metamove_probe.py \
 --trace ../Humanoide-vla-evidence/20260914_METAMOVE_HEAD_RUN/trace.jsonl \
 --after-analysis ../Humanoide-vla-evidence/20260914_METAMOVE_HEAD_AFTER/analysis.json \
 --output /tmp/analisis-cabeza-nuevo.json
```

Comprobación de integración sin movimiento, únicamente con HOME restaurado:
```bash
.venv/general-home/bin/python scripts/vla/run_metamove_head_probe.py --check \
 --review ../Humanoide-vla-evidence/20260914_METAMOVE_TRIAL_PREP/head-review.json \
 --evidence-dir /tmp/ensayo-cabeza-check-nuevo
```

El comando físico utilizado fue el mismo ejecutor con `--run --physical-confirmed`
y evidencia `../Humanoide-vla-evidence/20260914_METAMOVE_HEAD_RUN`. Se registra
para reproducción histórica, no como recomendación de repetir el ensayo.
La captura `sources/` de esa evidencia contiene la versión realmente utilizada;
`corrected-sources/` contiene la corrección posterior. Consultar el informe
ante cualquier nueva prueba. No autoriza brazos, elevador ni respuesta a E-stop.

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


## 2026-09-14 — VLA-01: ensayo físico de cabeza con monitor 6s completado

**VERIFICADO por Motion y telemetría; observación final del operador PENDIENTE.**
Usuario autoriza prueba física y confirma condiciones y supervisión junto al
paro. Revisión renovada desde HOME medido con fuentes actuales:1018 pares
certificados,54 avisos internos retenidos, sin UNRESOLVED. Preflight y --check
pasan. Una sola ejecución de `cruzr/move_head_lower` (0;−0,43rad,2s), sin
reintento, instalación, recarga ni movimiento solicitado de brazos/chasis.
Motion responde SUCCEED a2,341s del envío; comprobación de estabilidad
completada a3,342s, incluyendo1s de observación posterior. Cabeza final
pitch−0,430761rad/yaw0, velocidad final de todos los ejes0. Máxima desviación
medida en otros ejes de cuerpo/brazos0,0000959rad.

Resultado: HEAD_PROBE_SUCCEEDED_AND_SETTLED; no cancelación ni falso vencimiento
del canal de paro durante el ensayo. Ambos monitores locales usan6s; éste
sólo prueba físicamente el de cabeza, no el ejecutor ENTRY. No se accionó el
paro ni se midió distancia de frenado; no valida brazos/elevador o ENTRY.
Estado final: cuerpo/brazos conservan postura inicial y cabeza bajada; NO HOME
completo. No se envió retorno automático. VLA no se arrancó.

Receta: `.venv/general-home/bin/python scripts/vla/run_metamove_head_probe.py`
con --check primero, --run --physical-confirmed sólo con revisión nueva válida
y confirmación actual; --review y --evidence-dir requieren rutas concretas
como las conservadas en esta evidencia. El primer intento con Python del
sistema falló antes de conectar por falta de fcl; usar el entorno indicado.
Evidencia: ../Humanoide-vla-evidence/20260914_HEAD_TIMEOUT6_TRIAL/
(review.json, current-joints.json, check/, run/, summary.json, SHA256SUMS).
Copia documental previa: before-docs/. La ejecución es un cambio temporal de
postura: restaurar archivos no la revierte; cualquier retorno es otra acción.


### 2026-09-14 — confirmación física del ensayo de cabeza

El operador confirma «sí» a bajada suave, sin contacto y robot estable.
Queda completado este ensayo de cabeza con monitor local de comunicación6s:
éxito de Motion, estado final inmóvil y observación física concordante.
Se sustituye el PENDIENTE de observación del registro anterior. No extiende
la validación a ENTRY, brazos, elevador, cancelación o distancia de parada.
Robot permanece con cabeza bajada; no se envió ningún movimiento adicional.
Evidencia actualizada: ../Humanoide-vla-evidence/20260914_HEAD_TIMEOUT6_TRIAL/summary.json.


## 2026-09-14 — VLA-01: cabeza bajada y dependencias del proveedor encontradas

VERIFICADO por Motion/telemetría. Usuario autoriza «adelante con todo» tras HOME
confirmado y preparación presencial. Revisión nueva y --check pasan; se ejecuta
una vez cruzr/move_head_lower (2s). SUCCEED a2,3314s y estable a3,3322s;
head_pitch final−0,430569rad, velocidades finales cero. Sin reintento, cancelación,
recarga o movimiento solicitado de brazos/chasis. Observación visual posterior
PENDIENTE. Estado: cabeza bajada; no denominarlo HOME completo. El inicio del
acceso vuelve a ser compatible en cabeza; no se emitió habilitación de brazos.
Sigue faltando evidencia del protocolo de ensayo/seguimiento/parada de brazos.

LECTURA VIVA del proveedor: el XML enviado coincide byte a byte con
/opt/walker/task_manager/share/task_manager/config/cruzr_s2/utars_task_zhucheng_env_20260428_start.xml
(Vision, walker-system.ae_bt_master-1). Ambos includes existen allí y se copiaron
al PC. Las cuatro tareas Motion solicitadas también existen y se leyeron.
clamp_cruzr llama MetaMove, MetaLook transport_vision/pointclouds_vision,
MetaClamp force_init/clamp_cruzr_zc, MetaCruzrMove delta_pose−0.5;0;0 y
bodyback_cruzr_zc. put_cruzr_low incluye apertura y retroceso−0.4;0;0.
No se ejecutaron. Ruta visible de visión y control de movimiento; no hay enlace
visible a checkpoint-40000. No basta para certificar todos los binarios internos.
YAML MetaClamp localizado: request.duration6,frequency500,box_size[.4,.3,.22],
trayectorias VISION/RELATIVE, control de fuerza bimanual; su opción
request.enable_self_collision_check aparece false. Estado del proveedor leído,
NO modificación ni autorización para desactivar nuestras comprobaciones.
Esta configuración usa otras poses e incluye chasis; no es equivalente al
acceso READY/ENTRY ni una prueba física del VLA instalado.

Evidencia privada, fuentes XML/YAML con hashes y respaldo documental:
../Humanoide-vla-evidence/20260914_READY410_HEAD_PREP/.
Cambio remoto sólo la postura de cabeza por la tarea citada. Sin archivos remotos
modificados. Reversión de documentos no revierte la postura; requiere otra orden
revisada. No se envió HOME ni se activó inferencia/control VLA.
