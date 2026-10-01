# Depósito WRC y estantería a 100 cm

## Pausa para apagado: caja inclinada y desenganche pendiente

**BOX-01-TABLE74-PAUSE-01 — 30-09-2026, Europe/Madrid.** El operador pide
apagar y continuar mañana. **Apagado y aseguramiento confirmados después por
el operador: «Ya apagado y todo asegurado y estable».** No se confirma mediante
medición independiente del agente. **No repetir descensos**.
Estado observado por el operador: toda la base está sobre el tablero, pero
la caja está inclinada y sólo apoya una punta; la esquina más alta queda a
**2,8 cm**. Las abrazaderas siguen encajadas. La foto y el operador indican
holgura para bajar el útil, pero eso no demuestra transferencia de peso,
asentamiento ni libertad de los pines. No se instaló ni ejecutó desenganche,
apertura, HOME o apagado desde el agente.

**Support físicamente ejecutado:** evidencia
`../Humanoide-vla-evidence/20260930T182221Z_TABLE74_SUPPORT_TRIAL_2072686/`.
Única tarea `local_table74_support/649c5325a01fa93e6d989fe9c8694fb0d133dcddcc521878275897699e6655d1_support`,
goal `8a15575b-f746-4405-8a1d-c819b092d01f`, SUCCEED/status4/1101001;
acción 12,429 s, etapa 17,454 s. Cuatro comprobaciones de siete hashes
coinciden. Dos muestras posteriores 20D inmóviles, delta consigna máximo
0,004190; paros 0/0, cargador 0, batería 29,2/32,0 %, HOME=0 en ese momento.
El journal conserva `physical_support_confirmed=false`, coherente con la
observación de una sola punta apoyada. Antecesor approach consumido; no hay
checkpoint ordinario nuevo, retry, apertura ni HOME. Cierre normal con
revocación de leases posterior al resultado y al reposo.

**Hallazgo nativo:** el log de soporte muestra admisión lateral Y, manteniendo
el cierre, mientras Z sigue en control de posición. Un descenso igual de ambas
manos con orientación retenida no nivela por sí solo una caja rígidamente
sujeta; podría cargar la esquina que ya toca. `3,0 − 2,8 = 0,2 cm` sólo es una
resta nominal, no una holgura de desenganche. Parte del recorrido podría acompañar
a la caja. El open WRC original mezcla bajada, apertura y giro y no constituye
una tarea demostrada de asentamiento. No se ejecuta como atajo para apagar.

**Preparación y cierre de apagado:** primero el operador confirmó personal
formado y medios; después confirmó caja, ambos brazos y cuerpo asegurados,
estables y robot ya apagado. El agente no ordenó el apagado ni la retirada
manual y no verificó visualmente los apoyos. La secuencia exacta de botones y
la postura final medida siguen sin constar; no se declara HOME ni caja liberada.
No intentar HOME con caja/mesa en su trayectoria. Se revisa la alternativa de
apagado fuera de HOME asegurado; el precedente documentado tenía pinzas vacías
y no acredita automáticamente esta situación con carga encajada.

Durante el redescubrimiento, Docker informa hardware recién iniciado (22 s) y
manipulación (18 s); posteriormente **ambos hosts dejan de responder por SSH**.
No se ha determinado la causa del reinicio ni la secuencia seguida. La pérdida
de conexión no acreditaba apagado completo; la confirmación posterior procede
del operador. No se enviaron rearme,
reinicio, modo, paro ni `/emb/pm_shutdown`; no se pudo completar una lectura
actual de los paros ni redescubrir el contrato vivo de apagado.

Evidencia de consultas, confirmación y relevo:
`../Humanoide-vla-evidence/20260930T183000Z_TABLE74_SHUTDOWN_PREP/`, con
`handoff.json` y backups documentales anteriores;
`trial-review.json` y `native-motion-log.json` en la evidencia de soporte.

**Para mañana:** encender con paro principal pulsado y mantenerlo; no liberarlo
para probar HOME automático mientras persistan caja encajada, apoyos externos
o esta postura sin recuperación revisada. Primero comprobar presencialmente
estabilidad, carga y contactos, y redescubrir boot/contenedores/controladores/
actuadores. El reinicio invalida el contexto de los ensayos anteriores. Conservar
marcadores consumed: no reutilizar los comandos de approach/support ni iniciar
el ciclo desde caja vacía. Desenganche de 3 cm, apertura y retorno a HOME quedan
PENDIENTES de una recuperación específica y de nueva comprobación física.

## Continuación separada: descenso de apoyo de 5 cm

**BOX-01-TABLE74-SUPPORT-TRIAL-01 — 30-09-2026, Europe/Madrid:** tarea de
apoyo **instalada, cargada y ejecutada con SUCCEED; apoyo estable completo
NO demostrado**. El resultado posterior y la pausa para apagado figuran arriba.
Se prepara a partir de la aproximación exitosa descrita abajo y de la
confirmación directa del operador: quedan aproximadamente 5 cm hasta la mesa.
El objetivo nominal es bajar esos 5 cm con las abrazaderas cerradas. No incluye
desenganche de 3 cm, apertura, repetición de aproximación, navegación ni HOME.
No se incorpora al ciclo ordinario ni se modifica el depósito WRC original.

**Verificación:** 70 pruebas automáticas pasan entre generadores, instalador y
ambos ejecutores, incluido bootstrap completo en memoria. Plan local real
correcto y `--check` en la unidad a las 20:21 CEST con `SUPPORT_CHECK_OK`,
put1 a 6,4 mm / 0,04°, journal anterior sin consumir, cero tareas de movimiento.
Evidencia de ese chequeo:
`../Humanoide-vla-evidence/20260930T182123Z_TABLE74_SUPPORT_TRIAL_2070145/`.
El cierre vuelve a mostrar avisos de lease revocado/expirado después de las
comprobaciones; salida final 0. El run conserva las verificaciones vigentes
antes del despacho. Esta comprobación no carga ni prueba físicamente el apoyo.

Fuentes: `scripts/box_handling/scenario1_table74_support.py`,
`scenario1_table74_support_run.py`, sus pruebas y el instalador compartido
`scenario1_table74_trial_install.py` (selector cerrado approach_only/support_only).
Referencia reproducible en `config/box_handling/scenario1_table74/support_reference.json`;
YAML/XML, manifiesto y revisión exactos en `support_trial/`.
El generador fija mesa 0,74 m, hueco aproximado 0,05 m y el bundle/goal anterior;
cualquier otra referencia exige una revisión distinta.

Trayectoria nativa de 12 s: manos con puntos relativos `[0,0,0]` a 6 y 10 s y
`[0,0,-0.05]` a 12 s; cuaternión relativo identidad en todos los puntos. Torso:
puntos relativos cero. No programa avance, giro ni separación lateral. Los pesos
XYZ del torso siguen en cero, por lo que **no queda físicamente bloqueado**;
fuerza e IK nativos pueden ajustar postura. No se certifica inmovilidad durante
los puntos de desplazamiento cero ni la interpolación física exacta.
Se conservan byte a byte todos los controles WRC fuera de trayectoria/tamaño
de caja: ventana de colisión original `[10,10,12]`, umbral Z de 10 N por mano,
control lateral de fuerza, límites y tiempos. La medida aproximada no tiene
cota de incertidumbre: puede quedar hueco residual o producirse contacto antes
de lo nominal. SUCCEED no acredita apoyo estable ni pines libres.

Destino: Motion `192.168.11.2`, contenedor
`walker-motion.manipulation_robot_app-1`, misma identidad/imagen registrada
para la aproximación. Sólo dos archivos nuevos, con nombre base
`649c5325a01fa93e6d989fe9c8694fb0d133dcddcc521878275897699e6655d1_support`:

- XML en `/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/local_table74_support/`, SHA `b046973bd370e734077fead419a9c6bfd1afcf6ba0d8f16e1f24eae6a661876c`.
- YAML en `/opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config/meta_clamp/local_table74_support/`, SHA `28d369db6d6bb869933294d02f35978b88c1984c3ad7abb67cd004b762437ce8`.

Se reconstruyó el paquete contra XML/YAML WRC vivos y biblioteca MetaClamp
pinada antes de escribir; ninguno fue sobrescrito. Backup remoto:
`/var/tmp/cruzr-table74-trial/649c5325a01fa93e6d989fe9c8694fb0d133dcddcc521878275897699e6655d1/`.
Copia externa de originales, recibo, manifiesto y bundle; fuentes/SHA, respaldo
anterior y evidencia: `../Humanoide-vla-evidence/20260930T181234Z_TABLE74_SUPPORT_TRIAL/`.
Respaldo previo adicional del instalador/tests:
`../Humanoide-vla-evidence/20260930T181155Z_TABLE74_SUPPORT_INSTALLER_BEFORE/`.

Generar nuevamente en un directorio **nuevo**:

```bash
python3 -B scripts/box_handling/scenario1_table74_support.py \
  --reference config/box_handling/scenario1_table74/support_reference.json \
  --output /ruta/nueva/support_trial
```

Aplicar/verificar archivos mediante el instalador compartido, sustituyendo
`--check` por `--install` para instalar sólo los destinos nuevos:

```bash
python3 -B scripts/box_handling/scenario1_table74_trial_install.py \
  --bundle config/box_handling/scenario1_table74/support_trial/bundle.json --check
```

La autorización de continuación procede del **journal exitoso de aproximación**,
sus eventos y contexto; no de volver a usar el checkpoint de put1 ya consumido.
El ejecutor verifica la cadena exacta accepted/result/stage_complete, hashes,
contexto de robot y cierre anterior. Rechaza navegación desde el despacho de la
aproximación y actividad posterior a su cierre, permitiendo sólo cierres idle
conocidos. Los eventos previos de navegación no incluyen el comando completo;
no se usan como certificación retrospectiva de ausencia de movimiento.
Conserva controles de salud/leases, confirma
entrada técnica en put1 y sólo admite la tarea de apoyo pinada. Consume
`trial.json` mediante marcador durable antes de armar y escribe intención antes
de despachar; sin retry. Guarda `support.json` y contexto envuelto no ejecutable,
nunca un checkpoint ordinario que habilite otro descenso.

Comprobación y ejecución desde la raíz del repositorio:

```bash
python3 -B scripts/box_handling/scenario1_table74_support_run.py --check \
  --after ../Humanoide-vla-evidence/20260930T180539Z_TABLE74_APPROACH_TRIAL_2028660 \
  --bundle config/box_handling/scenario1_table74/support_trial/bundle.json
python3 -B scripts/box_handling/scenario1_table74_support_run.py --run \
  --after ../Humanoide-vla-evidence/20260930T180539Z_TABLE74_APPROACH_TRIAL_2028660 \
  --bundle config/box_handling/scenario1_table74/support_trial/bundle.json
```

`--plan` es el modo predeterminado local; `--check` no consume el journal.
`--run` requiere TTY y `APOYAR`: misma postura/caja, hueco actual 5 cm, caja
plenamente sobre la mesa horizontal, cinta/manos fuera del recorrido y
condiciones físicas/mando verificadas por el operador. Después se comprueba
apoyo real antes de preparar o ejecutar desenganche/apertura.

Rollback de archivos cuando ninguna tarea los use:

```bash
python3 -B scripts/box_handling/scenario1_table74_trial_install.py --rollback \
  --bundle config/box_handling/scenario1_table74/support_trial/bundle.json
```

Sólo elimina los dos archivos propios con hash e identidad de contenedor
intactos, conserva aproximación y originales, y retiene evidencias. No revierte
movimientos ni permite reutilizar journals consumidos. Reaplicación tras una
actualización sólo después de comprobar dependencia por dependencia.

## Resultado físico de la aproximación del 30-09-2026

**BOX-01-TABLE74-APPROACH-TRIAL-02 — 30-09-2026, Europe/Madrid:**
aproximación **cargada y ejecutada físicamente con éxito técnico**, por el
operador tras confirmar `APROXIMAR`. El operador confirma después **unos 5 cm
entre la mesa y la parte más baja de la caja**, con cero de cinta sobre la mesa.
Se conserva esa medición aproximada; la estimación inicial de 7–8 cm a partir
de la foto queda **DESCARTADA** frente a su lectura directa. No es una prueba
de apoyo: caja todavía sujeta y fase de liberación no ejecutada.

Evidencia local: `../Humanoide-vla-evidence/20260930T180539Z_TABLE74_APPROACH_TRIAL_2028660/`.
Una única acción de movimiento, task `local_table74_trial/9360060014e4103ce31da084426302ee4c2e06900a0f5707bf68df0d07ada9ef_approach`,
goal `7553e90f-cde1-4ca7-a488-96c86816d988`, status 4 / 1101001 / SUCCEED;
duración de acción 12,407 s, etapa completa con verificaciones 17,347 s.
Se comprobaron los cinco hashes cuatro veces. Dos muestras posteriores:
20 ejes inmóviles, diferencia máxima de consigna 0,003905; paros 0/0,
cargador 0, batería 31,8/34,7 %. Estos valores corresponden a esa prueba,
no garantizan el estado físico de una ejecución posterior.

El checkpoint limpio de `mesa74-put1-20260930T200409/checkpoint.json` quedó
consumido antes de armar. Procedía del transporte autorizado por el operador,
con retreat y navigate_put1 completados; llegada de entrada ≈5 mm / 0,4°.
El ensayo emite `trial.json` y contexto envuelto `executable=false`; **no crea
un checkpoint ordinario ni permite repetir la aproximación**. No se enviaron
descenso final, apertura, liberación ni HOME. Tras el resultado y reposo se
pidió cierre y se revocó lease; los workers cerraron con avisos de lease
(rc2/rc78), sin error de supervisor ni fallo de esta trayectoria.

Consulta posterior exclusivamente de lectura: `native-motion-log.json`
incluye inventario y logs nativos del intervalo. El último muestreo cartesiano
registrado durante la tarea deja la mano izquierda en Z=0,789853 m del marco
Motion; **no equivale por sí solo a altura física de la base de la caja**.
Movimiento en reloj Motion 18:05:33.586–18:05:45.994 UTC; PC y Motion difieren
aproximadamente 44 s, no ordenar sus timestamps como si compartieran reloj.

Próximo tramo calculado desde la medida actual: 5 cm hasta apoyo nominal;
después comprobar apoyo físico antes de bajar manos 3 cm y abrir. La propuesta
de apoyo es una tarea diferente, sin repetir aproximación, traslado ni HOME.
Backups documentales `review-before/`, fuentes originales y recibos de
instalación siguen conservados. Registrar nuevas fases por separado; rollback
de archivos no revierte una postura ni autoriza reutilizar checkpoints.

## Ensayo separado de aproximación a mesa de 74 cm

**BOX-01-TABLE74-APPROACH-TRIAL-01 — 30-09-2026, Europe/Madrid.**
Estado actualizado: **instalado, cargado y ejecutado con SUCCEED**; el operador
confirmó después unos 5 cm de hueco. Véase el resultado físico y la pausa
posterior para apagado al principio del documento.
Comprobación de reanudación de lectura a las 20:02 CEST:
`20260930T180218Z_OPTIMISTIC_SCENARIO1_2020465`, mapa utars_nav_map,
FSM_WAITNAVIGATE, entrada get1 a 4,1 mm / 0,11°, `RESUME_CHECK_OK` y salida 0.
Después de anunciar las comprobaciones completas aparecen avisos de lease al
cierre; se conservan los registros y se requiere salud vigente al ejecutar.
No se envió movimiento ni se consumió el checkpoint de recogida 173316Z.
La confirmación física actual solicitada para traslado y aproximación está
pendiente; no se reutiliza como confirmación la de la recogida anterior.
La referencia real aproximada de base a 1,10 m permite preparar un primer
descenso relativo de 31 cm hasta base nominal a 79 cm, 5 cm sobre la mesa.
Esta tarea termina allí: no contiene el descenso final de 5 cm, apertura,
desenganche de 3 cm ni HOME. No está integrada en el ciclo ordinario.

Fuentes reproducibles: `scripts/box_handling/scenario1_table74_trial.py`,
`scenario1_table74_trial_install.py`, `scenario1_table74_trial_run.py` y sus
tres módulos de pruebas. Referencia y artefactos exactos:
`config/box_handling/scenario1_table74/approach_reference.json` y
`approach_trial/{bundle,review}.json`. **44 pruebas automáticas pasan**,
incluido bootstrap en memoria, cierre de sesión, escritura parcial, rollback,
rechazo de archivos alterados y prevención de repetición desde el checkpoint.
La medida es aproximada; el margen de 5 cm no es una cota de error validada.

Motion `192.168.11.2`, contenedor `walker-motion.manipulation_robot_app-1`,
ID `3e1296b4418048fd609dbf240acd9ae9dee4ba10c54eab00296746a086c321bd`,
imagen `sha256:9f7acf4bdefde90d330f13cdc249d169865b1777bbcf31fca3642827f5be7e75`.
Sólo se añaden dos archivos con nombre inmutable:

- XML bajo `/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/local_table74_trial/`.
- YAML bajo `/opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config/meta_clamp/local_table74_trial/`.

Nombre base: `9360060014e4103ce31da084426302ee4c2e06900a0f5707bf68df0d07ada9ef_approach`.
SHA XML `28a980f9c4903df74b1b710df21940afadde00bf8d5386c554aa059cc328f56e`;
SHA YAML `1acc9b2a2e9d019329556dd46fdabf5e13cabb3e03cffd67f9fc2e91a6063df4`.
Se verifican XML/YAML WRC originales y biblioteca MetaClamp; hashes completos
en el manifiesto. Instalación aditiva, sin ROS, reinicios, cambios de modo ni
movimiento. WRC original y perfil ordinario permanecen intactos.

La tarea conserva tiempos, XY, cuaternión absoluto, movimientos de torso y
controles nativos WRC. Cambia el primer Z de manos por −0,31 m usando
`Z_REL_XYRPY_ABSOLUTE`, elimina los tres descensos finales de −0,20 m,
declara caja 0,603 × 0,397 × 0,22 m y retira la acción de apertura del XML.
**No es sólo movimiento vertical:** fija XY/orientación y luego avanza 20 cm.
Conserva la ventana de contacto original entre 10 y 12 s; ésta no demuestra
protección contra un contacto anterior. La referencia sólo sirve para la misma
caja, agarre, orientación y postura, también después del transporte.

Reproducción desde la raíz del repositorio (la salida del generador debe ser
un directorio nuevo; el artefacto actual ya existe):

```bash
python3 -B scripts/box_handling/scenario1_table74_trial.py \
  --reference config/box_handling/scenario1_table74/approach_reference.json \
  --output /ruta/nueva/approach_trial
python3 -B scripts/box_handling/scenario1_table74_trial_install.py \
  --bundle config/box_handling/scenario1_table74/approach_trial/bundle.json --check
python3 -B scripts/box_handling/scenario1_table74_trial_install.py \
  --bundle config/box_handling/scenario1_table74/approach_trial/bundle.json --install
```

El runner requiere un checkpoint **limpio, caja held, justo después de put1**.
Primero se transporta mediante `optimistic_scenario1.sh --run --resume
RUTA_CHECKPOINT_RECOGIDA --stop-after put1`, sólo con condiciones físicas
actuales confirmadas. No reanudar el depósito ordinario desde put1: ejecutaría
WRC original. Para esta aproximación, con el nuevo checkpoint de put1:

```bash
python3 -B scripts/box_handling/scenario1_table74_trial_run.py \
  --resume RUTA_CHECKPOINT_PUT1 \
  --bundle config/box_handling/scenario1_table74/approach_trial/bundle.json --plan
python3 -B scripts/box_handling/scenario1_table74_trial_run.py \
  --resume RUTA_CHECKPOINT_PUT1 \
  --bundle config/box_handling/scenario1_table74/approach_trial/bundle.json --check
python3 -B scripts/box_handling/scenario1_table74_trial_run.py \
  --resume RUTA_CHECKPOINT_PUT1 \
  --bundle config/box_handling/scenario1_table74/approach_trial/bundle.json --run
```

`--run` exige TTY y confirmación `APROXIMAR`, conserva preflight/leases/
watchdog del ejecutor, consume el checkpoint antes de armar y registra intención
antes del despacho. Sólo admite una aproximación; sin retry, apertura, navegación
ni HOME. Emite `trial.json` y contexto envuelto **no ejecutable**, nunca un
checkpoint ordinario que pudiera repetir el descenso. Éxito de acción no prueba
apoyo ni altura física; detenerse y comprobar la separación antes del tramo final.

Backup remoto y recibo:
`/var/tmp/cruzr-table74-trial/9360060014e4103ce31da084426302ee4c2e06900a0f5707bf68df0d07ada9ef/`.
Copia externa, fuentes/SHA, respaldo documental previo y evidencia de esta
intervención: `../Humanoide-vla-evidence/20260930T175607Z_TABLE74_APPROACH_TRIAL/`.
`robot-backup/originals.json` conserva bytes de fuentes originales y hash de
biblioteca; ninguno se sobrescribe. Recibo registra que ambos destinos estaban
ausentes. Rollback de **archivos**, cuando ninguna tarea los esté usando:

```bash
python3 -B scripts/box_handling/scenario1_table74_trial_install.py \
  --bundle config/box_handling/scenario1_table74/approach_trial/bundle.json --rollback
```

Retira sólo los dos archivos propios si conservan hashes e identidad de
contenedor; conserva respaldos e historial. No revierte postura, no mueve el
robot ni permite reutilizar checkpoints consumidos. No reaplicar después de
actualizar imagen/software sin verificar las dependencias. Para volver al
original no hace falta restaurar YAML WRC: nunca se modificó; su uso exige
primero resolver físicamente el estado actual de la caja.

## Mesa horizontal de 74 cm — candidato local del 30-09-2026

**30-09-2026 — BOX-01-TABLE74-MEASURED-REFERENCE-01: nueva referencia real
aproximada, ciclo de depósito NO activado.** El operador confirma que la cinta
tiene el cero en el suelo, que la cara inferior de la caja está a unos1,10m y
que el robot conserva la postura posterior al agarre de la prueba173316Z.
Las nuevas fotos muestran la abrazadera colocada; se estima visualmente6–7cm
entre borde inferior de placa y nervio inferior. Es una estimación, sin cota
de incertidumbre ni verificación del recorrido de todo el útil. Con3cm de
bajada quedarían nominalmente3–4cm de ese hueco, **si esa interpretación es
correcta**. La hipótesis previa14−10cm no sustituye esta observación directa.

Se guarda `config/box_handling/scenario1_table74/measurement_review.json` con
procedencia, supuestos y datos pendientes, sin convertirlos en flags verificados.
La medición permite calcular desplazamientos relativos sin inventar Zmano:

```text
base_actual ≈ 1,10 m; mesa = 0,74 m
cambio_de_base_nominal = 0,74 − 1,10 = −0,36 m
precontacto_nominal = 0,74 + 0,05 = 0,79 m
primer_descenso_nominal = 0,79 − 1,10 = −0,31 m
tramo_final_de_depósito = −0,05 m
desenganche_de_manos_tras_apoyo = −0,03 m
```

**VERIFICADO estático en binario archivado**, SHA MetaClamp
`d6bc61a493f7d790150fdbd673108121f46589fef56620de4a9023dcc2ba520a`:
`Z_REL_XYRPY_ABSOLUTE` suma Z al punto anterior y fija XY/orientación absolutos
(handler0xfeed0; dispatch0x111990). No conserva orientación automáticamente.
Para mantener Z/orientación al posicionar XY existe `stay_last_state_dof:
[0,0,1,1]` en ABSOLUTE, usado en el YAML proveedor
`meta_clamp/zhucheng/put_cruzr_zc_low.yaml`; después se puede bajar en RELATIVE
con cuaternión identidad. No se han probado esas variantes físicamente aquí.

**INFERENCIA condicionada:** con caja rígidamente sujeta, misma orientación
y vertical del planificador paralela al suelo, el desplazamiento de manos
traslada la base por igual. Después de navegar debe mantenerse o actualizarse
la referencia; no es una calibración para todas las recogidas. Un error de
inclinación/medición puede dejar la caja suspendida o producir contacto antes
de tiempo. Sin intervalos comprobados no existe un peor caso numérico cerrado.
No se rellenan las referencias absolutas anteriores ni se activa apertura
automática. El primer ensayo requiere separar apoyo y liberación y verificar
apoyo estable antes del desenganche. El descenso conjunto previo no garantiza
que los pines estén libres.

Respaldo previo y fuentes/revisión finales con SHA en
`../Humanoide-vla-evidence/20260930T174618Z_TABLE74_MEASURED_REFERENCE/`. Este registro no mueve ni instala tareas
ni modifica checkpoints; el original WRC conserva su geometría. Reversión:
retirar sólo measurement_review.json si conserva el SHA final, y restaurar las
entradas documentales selectivamente desde before/, preservando la historia.
No hay configuración de depósito remota que revertir.

**30-09-2026 19:33 CEST — BOX-01-TABLE74-CALIBRATION-PICKUP-01:
recogida física completada, depósito74cm NO ejecutado.** Tras confirmar el
operador robot vacío/caja en recogida y todos los requisitos físicos actuales,
se ejecutó exclusivamente `./scripts/optimistic_scenario1.sh --run --stop-after grasp`.
El modo/etapas se contrastaron previamente con `--help` y `--plan`; el
`--check --stop-after grasp` de19:31 pasó con HOME medido, paros0/0, cargador0,
baterías37,3/39,8%, mapa utars_nav_map y FSM_WAITNAVIGATE. Este chequeo generó
avisos de lease al cierre tras ready y salida final0/CHECK_OK; logs conservados.

Prueba: llegada get1=3,7mm/0,14°; visión SUCCEED y recogida
`local_front_box/separate_right_cruzr` SUCCEED/status4/1101001, goal
`bc949818-0871-4443-891f-c73381b56256`, duración de etapa31,31s.
Se completó verify_held con política **assume**, no confirmación física del
objeto. Checkpoint íntegro: cuatro etapas completadas, in_flight=null,
failure=null, box_state=held. Sesión cerrada por petición de pausa, salida0.
No se ejecutaron etapas retreat, navigate_put1, deposit, verify_released ni HOME.
El agarre incluye su retorno corporal nativo; la pausa es después de la tarea
completa. Se recargó el mismo mapa en el planificador durante la navegación,
sin editar puntos; no se instaló la variante de mesa74cm ni se cambiaron fuentes.

Lecturas posteriores: `/mc/whole_joint_states` a17:34:01UTC registra todas las
velocidades0. La última mano izquierda cartesiana del log está a
17:33:31.467UTC, Z1,09623m, aún antes de terminar la tarea17:33:32.547UTC:
**no es referencia final**. Los orígenes arm_eef/hand son diferentes.
`/mc/{left,right}_hand_pose_in_camera` anuncian geometry_msgs/Pose, writer1,
Reliable/Volatile, pero ambos echo terminan timeout7s sin muestra; el anuncio
no prueba publicación vigente. `/mc/sdk/robot_state` también da timeout.
No se reemplaza la medición por el objetivo programadoZ1,10m. La caja sujeta
horizontal con orientaciones retenidas sigue siendo requisito para el cálculo.

**PENDIENTE:** confirmación visual de sujeción estable del operador, altura
real de la base de la caja y poses finales en el marco de la tarea, además de
holgura de liberación. Se solicitó sólo medición lateral sin contacto/entrada
bajo la carga; aún sin respuesta. No reiniciar el ciclo desde vacío ni enviar
HOME con la caja sujeta. El checkpoint preserva la pausa; cualquier continuación
requiere el estado físico correspondiente y no valida por sí sola el depósito.

Evidencia: `../Humanoide-vla-evidence/20260930T173316Z_OPTIMISTIC_SCENARIO1_1944108/`
(events, contexto, fuentes/SHA, checkpoint, operator-scope y post-grasp-*.json).
Precheck: `../Humanoide-vla-evidence/20260930T173144Z_OPTIMISTIC_SCENARIO1_1940118/`.
Consultas reproducibles mediante `scripts/collect_estop_available_readonly.py`
(funciones execute/ros, contenedor redescubierto en context.json): docker logs
con --since de esta prueba y lecturas rosa topic info/echo --once de los topics
anteriores, siempre con timeout y ROS2CLI_DISABLE_DAEMON=1; comandos exactos
con resultados registrados en post-grasp-*.json. Sólo lecturas tras la pausa;
sin segunda tarea para forzar publicación de poses. Copia del colector y SHA
conservados. No hay modificación remota de depósito que revertir ni trayectoria
de rollback automática; preservar caja/estado antes de cualquier recuperación.
Backups documentales review-before/ y SHA permiten reversión selectiva, sin
borrar el registro de la prueba física ni restablecer checkpoints consumidos.

**Estado vigente — BOX-01-TABLE74-RELEASE3-01, 30-09-2026 (Europe/Madrid):
desenganche propuesto de 3 cm, guardado en PC y NO activado.** A petición
«deja en 3 cm entonces», se sustituye la propuesta de 5 cm tras el apoyo por
3 cm: cada mano baja `[0,0,-0.03]` en 2 s, después se separa lateralmente
±10 cm durante 2 s sin más bajada ni giro. El tramo final de depósito conserva
5 cm; descenso nominal acumulado desde precontacto: **8 cm**. El preparador,
YAML candidato, fórmulas, informe y pruebas quedan coherentes con estos valores.

**OBSERVADO:** el operador aporta una foto y estima 14 cm de hueco.
**INFERENCIA condicional:** si corresponde al mismo hueco vertical ocupado por
la placa documentada de 10 cm, quedan 4 cm de holgura total; no determina cómo
se reparte ni demuestra 3 cm libres hacia abajo. La foto no muestra la
abrazadera colocada. No se convierte esa resta en una calibración ni se marca
`release_clearance_verified`. Altura absoluta de manos, desenganche y apoyo
real siguen PENDIENTES; no se emite XML, instala ni ejecuta trayectoria.

Destino: `config/box_handling/scenario1_table74/` y preparador/prueba locales.
Dependencias: perfil actual y snapshot WRC del 16-09, con SHA comprobados.
Reproducción: comando de preparación indicado abajo, a un directorio nuevo.
No requiere activación ni reinicio de servicios. `optimistic_scenario1.sh`
sigue usando WRC original. Las 28 pruebas offline pasan; se comprueba también
que perfil operativo, wrapper, runtime, contrato y los tres originales WRC
conservan sus SHA previos. No hubo conexión ni movimiento en esta modificación.

Respaldo de la propuesta anterior y fuentes/documentos previos:
`../Humanoide-vla-evidence/20260930T172654Z_TABLE74_RELEASE3/`, con `before/`,
`before-sha256.json`, `after/`, `after-sha256.json` y `verification.json`.
Para revertir esta revisión local, restaurar desde `before/` sólo sus archivos
cambiados y sólo si coinciden con `after-sha256.json`; si hubo ediciones
posteriores, aplicar la diferencia selectivamente. La versión de 5 cm también
era una propuesta sin validar. No hay cambio remoto que revertir.

**30-09-2026 19:21 CEST — BOX-01-TABLE74-CHECK-01: solicitud de activación;
preflight de lectura correcto, variante NO activada.** Se vuelven a contrastar
las dimensiones documentadas: placa100×70mm, cara a95mm del eje, referencias
45/55mm y pestañas12mm. La cota12mm es proyección lateral; no demuestra la
altura del pin bajo reborde. El registro de montaje diferencia el origen
`hand_link` del centro de almohadilla y no establece la relación actual
pin/caja/suelo. La petición de usar supuestos y disponer de E-stop no aporta
esa referencia ni permite rellenar las dos Z como si fueran medidas.

Ejecutado exclusivamente `timeout 120s ./scripts/optimistic_scenario1.sh --check`:
salida0/CHECK_OK, mapa `utars_nav_map`, estado `FSM_WAITNAVIGATE`, HOME medido
en dos lecturas20D, velocidad0, máxima posición/delta0,001822rad; paros0/0,
cargador0, baterías38,5/41,3%. Contenedores redescubiertos; XML/YAML de depósito
y apertura coinciden con SHA originales. Son observaciones volátiles, no
confirmación del espacio ni autorización de movimiento. No se despacha tarea
Motion ni navegación; los objetivos NAV consultan mapa/estado. Avisos de lease
aparecen al cerrar después de `ready`; se conservan en logs, con salida final0.

Evidencia: `../Humanoide-vla-evidence/20260930T172140Z_OPTIMISTIC_SCENARIO1_1914616/`;
`events.jsonl`, `context.json`, `ssh.log`, `source-sha256.json`.
Sólo diagnóstico con procesos de lectura transitorios, sin instalación,
reinicio o cambios de control. Documentos previos en `review-before/` y SHA;
reversión documental selectiva, sin estado remoto que restaurar. Sigue pendiente
la referencia geométrica de altura y liberación antes de convertir la candidata
en una tarea ejecutable. Original y respaldos permanecen disponibles.

**Historial sustituido por RELEASE3 — BOX-01-TABLE74-RELEASE5-01: descenso de desenganche5cm
PROPUESTO por el operador, sin validación física.** Tras confirmar pines bajo
reborde, el operador propone «que baje5centímetros es suficiente creo».
Se guarda `release_under_rim.candidate.yaml` con dos objetivos por mano:
2s, desplazamiento relativo `[0,0,-0.05]`, sin giro; 4s, desplazamiento relativo
`[0,+0.10,0]` izquierda / `[0,-0.10,0]` derecha, sin giro. Duración total4s;
objetivo relativo del torso0. Las translaciones se componen: esta liberación
baja5cm en total, no10cm. Los dos segundos por tramo conservan2s para abrir
y añaden2s para bajar. Un waypoint no demuestra parada exacta ni ausencia de
mezcla de interpolación en su transición.

Son **otros5cm después del apoyo previsto**, distintos de los5cm anteriores
durante el depósito con caja sujeta: desde la aproximación al final de apertura
suman10cm nominales de descenso de manos. La liberación requiere que la caja
esté apoyada establemente; separar dos puntos temporales no lo detecta. No está
comprobado que esos5cm desenganchen los pines ni que las abrazaderas quepan sin
rozar caja/mesa. Se guarda como propuesta, manteniendo
`release_clearance_verified=false`, descenso mínimo realmente necesario `null`
y altura absoluta pendiente. No se instala/activa ni se ordena prueba física.
El original sigue intacto y disponible en su entrada actual.
Al solicitar una referencia sin otra medición manual, el operador indica
«Abrazaderas separadas o robot vacío». No se obtiene de esa postura una
referencia simultánea de manos/base de caja sujeta sobre la mesa; no se
reconstruye el agarre anterior ni se mueve el robot para volver a crearlo.

Respaldo previo y versión actual con SHA:
`../Humanoide-vla-evidence/20260930T171510Z_TABLE74_RELEASE5/` (`before/`,
`before-sha256.json`, `after/`, `after-sha256.json`, `verification.json`).
28pruebas offline pasan, con secuencia relativa, tiempos, controles conservados
y propuestas separadas de mediciones. Reversión local selectiva, preservando
ediciones posteriores; volver a una copia anterior no valida su liberación.

**Actualización posterior — BOX-01-TABLE74-PINS-01: apertura sin bajada DESCARTADA
para activación.** El operador confirma que los pines quedan **bajo un reborde**.
La petición de activar/probar era condicional a que no pudieran quedar enganchados;
esa condición no está demostrada. El descenso conjunto de caja/manos antes del
apoyo no equivale a un desenganche relativo una vez apoyada la caja. No se conoce
el descenso mínimo ni el giro necesarios, y5cm es un máximo pedido, no una
medida demostrada de liberación. La apertura BYD del09-09 partía de un agarre
imperfecto/apoyo parcial: su estado final libre no prueba esta geometría.

La propuesta de apertura cero se conservó únicamente como
`open_horizontal.rejected.yaml.txt`, con aviso de rechazo, ahora en el respaldo
de RELEASE5. Se retiró el
archivo `.candidate.yaml` anterior. `review.json`/preparador registran retención
bajo reborde, descenso requerido `null` y bloqueo. **No instalar ni ejecutar
esa apertura.** Los objetivos de altura absoluta siguen sin resolver; no se
activa ni se mueve el robot. El original continúa disponible por el mismo
`optimistic_scenario1.sh`, con sus fuentes intactas; esta observación no es
una orden ni una validación para repetir su depósito a la altura incorrecta.

Respaldo de los11archivos locales anteriores a esta corrección:
`../Humanoide-vla-evidence/20260930T171326Z_TABLE74_PIN_REVIEW/before/`, con
`before-sha256.json`; versión corregida/resultado en `after/`,
`after-sha256.json` y `verification.json`. Reversión local selectiva preservando
ediciones posteriores; si se restaura el borrador anterior, conservar este
rechazo documentado: restaurar bytes no demuestra desenganche. No hay archivos
remotos que revertir. Punto de continuación: determinar geometría pin/reborde,
movimiento relativo de desenganche y referencia de altura; después preparar
una variante separada y seleccionar explícitamente original/adaptada.

**BOX-01-TABLE74-DRAFT-01 — VERIFICADO offline; altura absoluta de manos,
instalación, integración y ensayo físico PENDIENTES.** El requisito vigente
del operador es una mesa horizontal de **0,74 m**. El título y el diagnóstico
del 16-09 que siguen son históricos. El operador confirma que el depósito
actual también llega a una altura incorrecta, y pide un descenso de manos
de como máximo5cm al depositar; después pide3cm para desenganchar. No aportó una referencia simultánea
medida de manos y base de caja; no se ha supuesto que el depósito actual
equivalga a74cm ni que un resultado exitoso pruebe esa altura.

Se guarda una variante de revisión en
[`config/box_handling/scenario1_table74/`](../../config/box_handling/scenario1_table74/):

| Magnitud | Original WRC | Candidato guardado |
| --- | --- | --- |
| Altura de superficie / inclinación | No son parámetros directos del YAML | 0,74m / 0°, en `profile.json` |
| Descenso relativo final de ambas manos,10→12s | −0,20m | **−0,05m** |
| Descenso relativo simultáneo del torso | −0,20m | −0,05m |
| Descenso durante liberación | −0,05m durante apertura/giro,2s | Propuesta−0,03m/2s, seguida de apertura/2s conΔZ0 |
| Giro relativo durante liberación | Aproximadamente±75° | Identidad propuesta, sin liberación verificada |
| Separación lateral de apertura | ±0,10m | ±0,10m |
| Tamaño de caja usado en ambos YAML | 0,60×0,40×0,28m | 0,603×0,397×0,22m, dimensiones del perfil actual |

El límite de5cm se refiere al **tramo relativo final de descenso**. No demuestra
que la aproximación absoluta previa desde cualquier postura descienda sólo5cm.
El objetivo inicial del torso permanece enZ1,20m; al reducir su descenso final,
su último objetivo nominal pasa de1,00a1,15m. Alcance, holgura e interpolación
siguen sin validar. Quitar el giro de apertura evita programar un barrido por
esa rotación, pero no certifica que las abrazaderas reales no puedan rozar.
X/Y de aproximación, tiempos, límites y controles originales se conservan;
la ventana de detección de contacto sigue siendo10–12s y no cubre contactos
anteriores a10s. No se modifican protecciones.

### Cálculo guardado y dato que falta

Con caja horizontal nominal de22cm, apoyada en esa mesa: base=0,74m,
centro=0,85m y borde superior=0,96m, todos respecto al suelo. **Ninguno de esos
tres números determina por sí solo la Z de las manos en Motion.**

Para cada mano, a partir de una misma referencia medida con la caja sujeta
horizontalmente y las orientaciones conservadas:

```text
Z_contacto = 0,74 + Z_mano_Motion_referencia − altura_base_caja_referencia
Z_aproximación = Z_contacto + 0,05
Z_tras_descenso = Z_aproximación − 0,05 = Z_contacto
Z_tras_desenganche_propuesto = Z_contacto − 0,03
Z_tras_apertura_lateral = Z_contacto − 0,03
```

La modalidad alternativa del perfil actual necesita demostrar que la posición
final WRC original se alcanzó realmente con la caja aún sujeta, sin contacto
prematuro. Entonces:

```text
Z_contacto = 0,45 + (0,74 − altura_base_caja_en_extremo_original_medido)
Z_aproximación = Z_contacto + 0,05
```

Las referencias de `profile.json` permanecen `null`, con verificaciones falsas.
El URDF y `clip_to_upper_edge_offset=0,05` no establecen por sí solos el punto
de agarre real: este último es un parámetro de comprobación de anomalías.
Por ello `put_table74.yaml.in` mantiene `${LEFT_HAND_APPROACH_Z_M}` y
`${RIGHT_HAND_APPROACH_Z_M}` sin rellenar; **no es un YAML ejecutable**.
`release_under_rim.candidate.yaml` contiene la propuesta de bajar3cm después
del apoyo y después separar lateralmente. No se genera XML de tarea, no se
instala y `optimistic_scenario1.sh` sigue usando la tarea original.
`review.json` registra explícitamente `can_install=false`, `installed=false`
e `integrated_in_optimistic=false`.

### Reproducción, pruebas y reversión

Fuente reproducible:
[`prepare_scenario1_table74.py`](../../scripts/box_handling/prepare_scenario1_table74.py).
Comprueba SHA de XML/depósito/apertura originales antes de producir copias,
usa el contrato geométrico existente y rechaza otras alturas o pendientes.
Exige un directorio de salida nuevo, para conservar cualquier revisión anterior.
Incluso una referencia completa sólo genera candidatos de revisión; no instala
ni certifica trayectorias. No cambiar las referencias/flags para aparentar una
medición que no existe.

```bash
python3 -B scripts/box_handling/prepare_scenario1_table74.py --output /ruta/nueva/table74
python3 -B -m unittest scripts.box_handling.test_prepare_scenario1_table74 \
  scripts.box_handling.test_scenario1_deposit
```

**28 pruebas pasan**: referencias ausentes no generan alturas numéricas ni XML,
cálculo con referencias sintéticas asimétricas, descenso final5cm, liberación
con descenso3cm y posterior apertura sin otra bajada/giro, conservación de
controles y rechazo de fuentes
alteradas. No se conectó al robot ni se envió movimiento. El instalador histórico
de depósito tiene una incompatibilidad de versión2frente al builder3; no se usa
para estos candidatos. Su actualización e integración corresponden a una
intervención posterior con geometría suficiente.

Respaldo previo de17archivos locales, incluidos los XML/YAML originales,
configuración, scripts y documentos:
`../Humanoide-vla-evidence/20260930T170222Z_DEPOSIT_TABLE74/before/`,
con `before-sha256.json`. Es una copia de las fuentes locales, no una lectura
nueva de archivos vivos del robot. `candidate-v1/` conserva el primer borrador
antes de la aclaración del límite5cm; `after/` y `after-sha256.json` identifican
la versión final, y `verification.json` recoge el resultado.

Rollback: retirar sólo los cuatro archivos de `config/box_handling/scenario1_table74/`
y el preparador/prueba nuevos si conservan los hashes de esta intervención;
restaurar selectivamente las entradas documentales desde `before/`, preservando
ediciones posteriores. Los archivos WRC originales, el SDK, el perfil operativo,
el ejecutor y el robot no cambian. No hay servicio que reiniciar ni estado
transitorio que restaurar. Punto de continuación: obtener una referencia real
para resolver las dos Z, revisar trayectoria completa y preparar la integración.

## Historial: diagnóstico de la estantería de 100 cm

2026-09-16, Europe/Madrid. Diagnóstico de lectura; sin movimientos, instalación,
recarga ni modificación de mapa/XML/YAML del robot por el agente.

## Resultado verificado

La tarea `wrc_cruzr/put_cruzr_wrc_low` llama a `wrc/put_cruzr_wrc_low`
y después a `wrc/open_arm_cruzr`: la apertura está incluida. La ampliación del
ejecutor enlazó esta tarea original; no adaptó sus alturas a la estantería local.

Fuentes archivadas del proveedor:
- [XML](../../vendor/ubtech/cruzr_s2/snapshot_20260916/motion/tasks/wrc_cruzr/put_cruzr_wrc_low.xml).
- [YAML](../../vendor/ubtech/cruzr_s2/snapshot_20260916/motion/meta_clamp/wrc/put_cruzr_wrc_low.yaml).

El YAML leído en Motion conserva estos objetivos. Ruta instalada:
`/opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config/meta_clamp/wrc/put_cruzr_wrc_low.yaml`.

| Instante | X de ambas manos | Z de ambas manos | Z del torso |
|---|---:|---:|---:|
| Inicio del plan observado | ≈0,30 m | ≈1,10 m | ≈1,23 m |
| 6 s | 0,75 m | 0,65 m | 1,20 m |
| 10 s | 0,95 m | 0,65 m | 1,20 m |
| 12 s | 0,95 m | 0,45 m | 1,00 m |

Son coordenadas de referencias del planificador, **no alturas medidas de la base
de la caja ni prueba de que se alcanzara el último punto**. El registro Motion
con hora interna 18:52:19.854 confirma la composición ABSOLUTE/RELATIVE del YAML:
Z izquierda `1.10007 0.65 0.65 0.45`, derecha `1.10028 0.65 0.65 0.45`.
El `1.2` del YAML es el objetivo Z del torso, no la altura de la estantería.
El descenso programado explica el intento demasiado bajo comunicado por el usuario.
Acercar la estantería o modificar put1 no cambia estos objetivos verticales.
El perfil además configura `box_size: [0.6, 0.4, 0.28]`, distinto de la caja
real comunicada `0.603 × 0.397 × 0.217 m`; su efecto concreto debe revisarse al adaptar.

## Referencias del documento

Fuente: `Cruzr S2 搬箱子操作流程.docx`, texto y figuras originales; copia
[saneada/texto chino](../vendor/ubtech/box_handling/texto_zh.md).

- Escenario 1, get1: 59 cm desde el centro de la rueda derecha hasta el frente
  de la caja; lateral de 16 cm entre los lados derechos indicados.
- Escenario 1, put1: 90 cm desde el centro de la rueda derecha hasta la parte
  inferior de la estantería (`架子最下面`); lateral de 20 cm respecto al centro
  del pie derecho. Es distancia horizontal, no altura. El texto no define con
  precisión suficiente su equivalencia con el borde del tablero de otro mueble.
- El texto describe un extremo inferior a 85 cm ajustable ±10 cm, el otro a
  99 cm ajustable; nivel superior a 129 cm e inclinación de 10°.
- La fotografía del conjunto muestra un nivel inferior cercano al suelo:
  discrepancia visual con esas alturas, sin convertir píxeles en medidas.
- Escenario 2: niveles inferiores de 70 y 90 cm, superiores de 125 cm;
  put1 a 33,5 cm desde el centro frontal del parachoques. Es otro escenario y
  otra referencia; no sustituir directamente los 90 cm del escenario 1.
- No se encontró una altura de 120 cm en el texto del documento.

Los 59 y 90 cm no son intercambiables: cambian el objeto de referencia y la
trayectoria de manipulación. Tampoco quedan validados 90 cm para la estantería
local por aparecer en la receta del proveedor.

## Estado y reanudación

OBSERVADO: el usuario comunica agarre exitoso tras acercar las cajas e intento
de depósito demasiado bajo. Luego indica reinicio y que llevará el robot a HOME;
no se atribuye ese movimiento al agente ni se da HOME por medido tras el reinicio.
Se toma como requisito vigente la superficie de depósito indicada ahora: 100 cm.

PENDIENTE: variante de depósito adaptada a esa superficie, dimensiones reales,
transformación referencia de mano→base de caja, inclinación, profundidad de
inserción y holgura antes de bajar. No basta cambiar Z a 1,00 m: mano y base de
caja son puntos distintos. No repetir el depósito original para probar distancia.
No se ha producido ni instalado una trayectoria corregida en esta revisión.

Evidencia externa: `../Humanoide-vla-evidence/20260916T105936Z_DEPOSIT_HEIGHT/`,
`yaml.json` y `log.json`. Consultas de lectura; no requieren reversión del robot.
Respaldos de los documentos previos en `before-docs/` de esa misma evidencia.
