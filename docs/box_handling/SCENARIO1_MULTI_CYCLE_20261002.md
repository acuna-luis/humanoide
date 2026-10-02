# Tandas del escenario1 en una sesión

**BOX-01-MULTI-CYCLE — 02-10-2026, Europe/Madrid.**
IMPLEMENTADO/instalado PC; verificación offline registrada abajo. Carga remota,
ensayo físico con varias cajas y ahorro real de tiempo PENDIENTES. El agente
no se ha conectado ni ha enviado movimiento. El operador confirma que retirará
cada caja entre depósitos; conserva el punto/altura de depósito existente.


**Actualización OBSERVADA — intento105632 del operador:** --cycle2 completó la
primera caja, HOME y una transición en la misma sesión; la segunda pasó llegada
tras ajuste y se detuvo antes del agarre por orientación estimada5,482°>3°,
con traslación6,657mm≤20mm. Carga/transición demostradas; dos depósitos y ahorro
comparado PENDIENTES. No confundir con una tanda completa ni atribuir el fallo a
recalcular el mapa. [Diagnóstico y evidencia](BOX_ASSOCIATION_ROTATION_20261002.md).

## Uso y preparación

```bash
./scripts/optimistic_scenario1.sh --plan --cycle 4
./scripts/optimistic_scenario1.sh --check --cycle 4
./scripts/optimistic_scenario1.sh --run --cycle 4
```

Sin --run sigue siendo --check. Sin --cycle, o con --cycle1, se conserva una
sola ejecución y sus opciones habituales. N debe ser un entero positivo; N>1
sólo permite el perfil optimistic_v1/assume y las diez etapas completas, sin
--resume ni --stop-after get1/grasp/deposit. Los wrappers standard no añaden
esta opción. --check --cycle4 verifica una sola sesión sin ejecutar la tanda;
--plan describe cantidad, etapas por caja y condiciones sin conectar.

Antes de --run hay que verificar presencialmente abrazaderas instaladas/vacías,
HOME, caja/origen y recorridos despejados, batería/cargador, paros, ruedas, modo,
exclusividad de mando y persona junto al paro. La retirada de cada caja debe
completarse sin entrar en una trayectoria de brazos/chasis activa y antes del
siguiente depósito. La tanda no cambia coordenadas ni apila cajas por sí sola.
No hay detector nuevo de destino ocupado; sigue vigente la preparación física
del perfil optimista. Sujeción/liberación son asumidas tras éxito técnico,
no una medición de presencia/apoyo ni autorización para contacto.

## Qué se ahorra y qué se comprueba de nuevo

Una conexión SSH, un supervisor, preparación inicial/dependencias, arranque del
lector de salud, clientes persistentes de navegación/manipulación y adaptadores
SPS para toda la tanda. Bundle y helpers se calculan/transmiten una vez.
El mapa no se carga/relocaliza en cada arranque nuevo: las navegaciones conservan
prepare_map(), que ya retorna con una consulta si utars está listo. Por tanto
los mensajes de navegación observados no prueban por sí solos recálculo de mapa;
la tarea nativa puede emitir LOCATE_RUNNING durante cada navegación real.

Se mantienen descubrimiento/hashes por etapa física, salud continua/watchdog,
reposo, límites y cancelación, puntos de mapa sin cambios, poses frescas de
llegada, doble percepción/TF, ajuste X/Y presupuestado por caja, gateXYZ, tarea
nativa de agarre/depósito y HOME final medido para cada caja. No se reutiliza una
pose de caja ni un permiso antiguo de llegada. La detección de ausencia o una
caja rechazada aborta; no se cuenta como caja completada ni se salta a otra.

Tras las diez etapas, contrato puro exige checkpoint completo sin fallo ni
in_flight, released, perfil intacto y verify_home completado. El comando
next_cycle sólo se acepta con índice consecutivo≤N. Antes de vaciar el progreso
se comprueban conexión/watchdog, contenedores/hashes, reposo con dos muestras
posteriores al resultado y HOME20D mediante live-health fresco, mapa utars en
FSM_WAITNAVIGATE y puntos idénticos. Esta frontera es de lectura, sin carga de
mapa/relocalización/HOME/movimiento. Un dato inválido o cambio aborta.

El nuevo checkpoint comienza empty sin etapas/confirmaciones heredadas; la
asociación perceptiva anterior se borra. Se mantienen sesión, workers, sensores,
lease y plazo; no se llama a otro arranque de SPS o supervisor. Las etapas llevan
cycle_index para rechazar mensajes de otra caja. finish no puede dar éxito si
faltan cajas o si la última no terminó en HOME medido.

**Límite global vigente900s (15min), desde la creación de la sesión:** no se
amplía ni renueva entre cajas. Una tanda larga puede agotar ese plazo y detenerse
antes de N; no se garantiza que toda cantidad positiva quepa en una sesión.
Conserva heartbeat12s, control-lease4s y los restantes tiempos de acción/gates.
No se calculó ni midió velocidad de una tanda física en esta intervención.

## Evidencia y recuperación

PC, una carpeta de evidencia con events.jsonl/ssh.log/profile/context/hashes:

```text
batch.json                       cantidad, caja actual, completadas, estado/fallo
checkpoint.json                  checkpoint activo; al final, última caja
cycles/0001/checkpoint.json       historial independiente de la primera caja
cycles/0001/context.json          contexto compatible con resume de una caja
cycles/0002/checkpoint.json       intención/progreso/fallo de la segunda caja
cycles/0002/context.json          mismo contexto validado para esa caja
...
```

Antes de cada acción se guarda intención local en el checkpoint activo y en su
carpeta de caja; el supervisor también guarda intención/resultado por caja.
Creación de directorios y archivos se sincroniza a disco. El contexto inmutable
se copia una vez por caja. Batch tiene estados preparing/running/box_complete/
transition_pending/completed/interrupted; --check usa checked/check_failed y
completed_cycles=0. completed_cycles cuenta ciclos técnicos completos con HOME,
no presencia física de N cajas en destino. El remoto conserva también batch y
checkpoints por caja dentro de su sesión temporal.

Un fallo/cancelación, pérdida de enlace/worker, datos caducados o agotamiento de
sesión interrumpe toda la tanda. Se conservan las cajas completadas y el fallo
actual; no se envía la siguiente caja ni HOME de recuperación automático.
El checkpoint de la caja afectada y su contexto admiten el resume de una caja
existente (por defecto cycle1), con recuperación presencial explícita cuando
corresponda. No se reanuda automáticamente el resto de la tanda ni se repiten
cajas completadas. El operador debe comprobar caja sujeta/apoyada/retirada,
parada y postura actual; un diario no las determina. El marcador consumed del
resume se aplica al archivo de origen elegido como en el flujo existente.

## Archivos, activación y reversión

Destino persistente: PC, archivos versionados siguientes. CLI transmite las
fuentes en memoria a Motion/cliente nativo redescubierto en la próxima sesión
autorizada; no instala XML/YAML, cambia mapa/SDK, reinicia contenedores ni publica
nuevos topics. No hay cambio de tolerancias físicas ni ampliación de watchdogs.

- [optimistic_scenario1.sh](../../scripts/optimistic_scenario1.sh), SHA256 `97f96e57e35770ffddc480e994627e6a9b6a45cc1e8c5ad163b3fb767bfcd62e`.
- [scenario1_cli.py](../../scripts/box_handling/scenario1_cli.py), SHA256 `1df7da775dab2ce78532d58a4d35fc6e005d5fa8903d40282bd406f5d974d104`.
- [scenario1_contract.py](../../scripts/box_handling/scenario1_contract.py), SHA256 `f98f0609a5bb5fb96854ed841cbd60b74ce7c3fff9fe868bac22724774d94438`.
- [scenario1_runtime.py](../../scripts/box_handling/scenario1_runtime.py), SHA256 `863d4988cade88f83f234408d2017cacd107c237d203baf897e5ebfcbb3dabf1`.
- [test_scenario1_cycles.py](../../scripts/box_handling/test_scenario1_cycles.py), SHA256 `cd42d33ce71b3521980587225b4f5257383c873800e7f5dff3887b3b51625fc0`.

Dependencias: contratos v2 y optimistic_v1 existentes, clasificador20D original,
monitor continuo con dos muestras posteriores al resultado, workers persistentes,
profile90/SPS/native HOME y sus hashes vigentes. Se preservan sus gates.
Aplicación: conservar estas fuentes, verificar localmente y usar primero --check;
--run transmite el helper sin instalación remota. Carga/ensayo físico PENDIENTES.

Backup exacto del árbol anterior y posterior, estado Git/commit base, manifiestos,
resultados y plan de cuatro cajas:
`../Humanoide-vla-evidence/20261002_SCENARIO1_MULTI_CYCLE/`.
Reversión selectiva desde before/ de wrapper/CLI/contrato/runtime/notas y retirada
del nuevo test/documento, preservando cambios posteriores. No restaurar estados
remotos, checkpoint, mapa o paquetes vendor. El rollback de software no revierte
ninguna postura física. No se hizo commit ni push; los dos locks previos del
usuario se conservaron.

## Verificación reproducible

```bash
python3 -m unittest scripts.box_handling.test_scenario1_cycles
bash -n scripts/optimistic_scenario1.sh
./scripts/optimistic_scenario1.sh --plan --cycle 4
git diff --check
```

Pruebas offline: simulación de40 etapas/4HOME con una inicialización de SPS y
lector; transición sin movimiento ni adquisición completa; HOME/salud/mapa/
dependencias inválidos bloquean reset; índices antiguos/duplicados, conteos
inválidos, pausas/resume incompatibles y finish prematuro bloqueados; archivos
independientes con intención antes de la acción; fallo en segundo agarre conserva
primera caja e impide tercera/HOME automático; acuse de caja incorrecta no mueve;
--check4 sin armar; default1 y restantes flujos en suite de regresión.
Resultados exactos y exclusión legacy se registran en tests.json. No demuestra
ahorro real, disposición de cajas ni calificación física de tandas.

**VERIFICADO:**743 pruebas pertinentes correctas,16 del módulo nuevo. Tras
colocar la última comprobación HOME después de las consultas de mapa, se repasan
las7 pruebas de frontera/dispatch y pasan. Sintaxis/AST/help/plan4/diff-check
correctos. Suite excluye sólo test_scenario1_deposit_install legacy con errores
previos ya registrados. Inicialmente una fixture de dispatch carecía de mode=run;
se corrigió el test, sin modificar gates de producción. Instalado PC; carga,
ensayo de varias cajas y ahorro físico PENDIENTES.
