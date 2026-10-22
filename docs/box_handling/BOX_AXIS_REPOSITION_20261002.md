# Corrección visual del chasis antes de recoger

## Port acotado a la rama de mesa74 — 22-10-2026

**BOX-01-VISUAL-ALIGN-PORT-20261022. IMPLEMENTADO en PC; pruebas del port
correctas, errores globales previos documentados; carga en el robot y prueba
física PENDIENTES.** Fecha/zona:22-10-2026,
Europe/Madrid. Petición: trasladar sólo la aproximación visual del chasis de
`feriabarcelona`, con contador configurable y sin cambiar el agarre nativo.
No se ha conectado ni movido el robot durante este port. No se infiere su
postura actual del ensayo previo ni de haber cambiado de rama.

### Procedencia y diferencia con el donante

Rama receptora `feat/scenario1-deposit-table-74cm`, base de esta intervención
`8107664669c187ecd31179c086cd29749d2b83b9`; donante
`feriabarcelona@0cbc32095be3e752de91db6a9ed91d165e02186a`.
Se adapta su planificación visual, supervisión de navegación, adquisición
persistente de odometría y conexión al ejecutor actual. No es un merge completo:
no se trae depósito90/69,5cm, cambios de brazos ni recuperación automática
`NO_PROGRESS` del donante. Una cancelación o desenlace incierto aborta; no se
resetean ni recrean workers para intentar de nuevo.

El rechazo previo de esta rama fue X=`0,7908843151889853 m`, exceso0,884315mm
sobre0,79m, después de preparar cabeza/brazos. Esto explica por qué comprobar
la caja antes del goal nativo puede evitar aquella preparación innecesaria;
no demuestra que la siguiente detección vaya a coincidir ni resuelve el
plegado/divergencia izquierda del22Oct. La prueba+2° en vacío sólo validó ese
recorrido pequeño. Véase el [ensayo de recogida](OPTIMISTIC_SCENARIO1.md#22-10-2026-recogida-detenida-en-preparación-destino-de-74-cm-pendiente).

### Contador y límites

`--box-alignment-attempts N` admite enteros **0..7**, por defecto **7 en
Optimistic**. Las otras entradas que comparten el CLI conservan0 por defecto;
pueden seleccionar N explícitamente.
N es el máximo de objetivos del **chasis antes de un único agarre**; no son
reintentos de brazos. Cero omite esta fase y conserva la entrada original del
agarre: esa entrada sí puede preparar cabeza/brazos antes de rechazar SPS.

| Condición | Valor mantenido |
| --- | --- |
| Gate SPS exterior en `base_link` | X[0,41;0,79], Y[−0,39;0,39], Z[0,01;1,49]m; reserva10mm frente al intervalo nativo |
| Margen de aproximación adicional | 20mm hacia dentro: X[0,43;0,77], Y[−0,37;0,37]m; Z no se corrige con elevador |
| Objetivo por corrección | Norma XY≤50mm; yaw final conservado |
| Suma solicitada / plazo de fase | ≤100mm / ≤120s, independientes deN; cada objetivo se reserva antes de despacharlo |
| Llegada antes de volver a observar | Éxito técnico, reposo y dos poses nuevas≤12mm/2° |
| Continuidad de caja | Pareja coherente≤20mm/3°; asociación geométrica entre posturas en odometría local≤20mm/3° |
| Progreso visual | Mejora≥2mm del exceso respecto al margen interior cuando siga fuera |
| Imagen / emparejamiento temporal | Segunda captura≤2s; TF del sello exacto; poses emparejadas≤0,5s y base estable≤5mm/1° |
| Vigilancia por acción | ≤30s, excursión≤80mm, recorrido≤120mm, sin progreso≤4s; mapas/odom, velocidades, salud y lease conservados |

100mm solicitados no acotan la trayectoria real, holgura ni frenado. Subir N
no amplía distancia/plazo ni permite corregir un objetivo mayor de50mm.
Los dos ajustes de llegada a get1 conservan su contrato independiente.

### Secuencia y preparación real de los brazos

1. Antes de mover, exigir abrazaderas declaradas vacías, brazos/torso HOME medidos,
   actuadores sanos/en reposo y condiciones presenciales actuales.
2. Verificar y ejecutar sólo `cruzr/move_head_lower`: cabeza0/−0,43rad,
   brazos/torso siguen en HOME. Su XML existente conserva SHA256
   `f3a73626f97b471d4a0a03c98c24de32243651116c497328e69b5ddc57ea46c1`.
3. Obtener dos detecciones nuevas, TF exacta, odometría anterior/posterior y
   poses de mapa contemporáneas. `enable_vision` es un `MetaLook` de transporte;
   no debe confundirse con esta bajada de cabeza ni con el goal de agarre.
4. Si falta margen interior, calcular objetivoXY de chasis desde la medida
   actual, conservar yaw, navegar con vigilancia y volver a medir tras éxito,
   reposo y llegada. Sólo entonces puede haber otro objetivo dentro deN.
5. Cuando cumple margen, guardar una referencia de comparación y enviar una
   sola vez `local_front_box/separate_right_cruzr`. **Ese goal nativo conserva
   sus3s iniciales de cabeza y ambos brazos**, seguidos por separación y
   `bodyback`. El port no altera esa preparación ni convierte la fase visual
   en una trayectoria exclusivamente de chasis de principio a fin.
6. El adaptador transitorio adquiere dos capturas nuevas en la petición SPS
   nativa, después de preparar brazos. Aplica coherencia, TF, frescura, XYZ
   originales y comparación con la referencia. Nunca entrega esa referencia
   antigua como pose, recorta coordenadas ni elige otra caja para pasar el gate.

Por ello un rechazo posterior todavía puede dejar postura preparatoria.
`--stop-after grasp` se detiene tras `verify_held` asumido sólo si la recogida
termina; confirmar físicamente la sujeción antes de transportar o liberar.
Un fallo no es una pausa exitosa ni autoriza reiniciar el ciclo o enviar HOME.

### Frescura y fuentes preservadas

La lectura de reposo usa el worker de salud persistente, con adquisición nueva
en cada petición. Evita lanzar otro proceso ROSA después de recibir la imagen:
el diagnóstico histórico del donante observó0,903s de coste y una imagen ya
mayor de2s. Se mantiene el límite2s; un procesamiento lento sigue abortando.
No se rejuvenecen sellos ni se reutilizan muestras antiguas como permiso.

Fuentes del port: `scenario1_box_alignment.py`, `scenario1_runtime.py`,
`scenario1_nav_correction.py`, `scenario1_health_worker.py` y
`scenario1_cli.py`, bajo `scripts/box_handling/`, con sus pruebas. Se transmiten
en memoria en la siguiente sesión mediante el lanzador existente; no requieren
instalar SPS ni reiniciar servicios. `TASKS`, `motion_stage`, SDK, fuerza,
XML/YAML y once fuentes protegidas se contrastan por hash con ambas ramas.
El builder conserva paquete **bf145fa17e1116fc** y los mismos XML/YAML generados;
las coincidencias de software no demuestran resuelta la causa física izquierda.

`box-alignment-policy.json` registra N/política de la sesión; el payload lo
transmite y las retomas impresas lo conservan. `events.jsonl` registra medidas,
frescura, asociación, objetivos/contador y motivo de límite. Los archivos de
intención/referencia de Motion son transitorios, no autorizaciones reutilizables.
No editar checkpoint, consumed ni valores de la política para recuperar permiso.
La consola muestra preparación de cabeza, intento/N, XYZ en centímetros,
llegada y margen listo; esas etiquetas no anuncian recogida completada.

La fixture versionada
`scripts/box_handling/fixtures/box_alignment_arm_invariants_20261022.json` y
`test_scenario1_box_alignment_arm_invariants.py` fijan por bytes las once
fuentes protegidas y el paquete generado. No convierten esa identidad de
software en cualificación del movimiento físico.

### Revisión local y uso condicional

```bash
# Plan local, sin conectar; muestra N y pausa tras recogida:
./scripts/optimistic_scenario1.sh --table-height-cm 74 \
  --box-alignment-attempts 3 --plan --stop-after grasp
# Comprobación técnica; no inicia detección, bajada de cabeza ni navegación:
./scripts/optimistic_scenario1.sh --table-height-cm 74 \
  --box-alignment-attempts 3 --check --stop-after grasp
```

Sólo en una sesión nueva, después de resolver la postura preparatoria anterior,
medir HOME y comprobar efector/caja libres, cargador, paros, ruedas en navegación,
recorrido completo, control exclusivo y persona junto al paro:

```bash
./scripts/optimistic_scenario1.sh --table-height-cm 74 \
  --box-alignment-attempts 3 --run --stop-after grasp
```

El comando no es una indicación de ejecutar ahora desde el fallo. La mesa74
sigue con depósito/apertura/HOME no ejecutables; este port no resuelve sus
alturas o desenganche ni habilita el ciclo completo.

### Verificación, evidencia y reversión

**Verificación local completada, sin suite global completamente verde.** La
ejecución de51 módulos realiza921 pruebas:904 pasan y17 producen errores,
todos en `test_scenario1_deposit_install`. Los17 se reproducen con los mismos
nombres en una copia aislada del HEAD previo`8107664`; no son regresiones
nuevas del port. El instalador y su configuración no se modifican en este
alcance. Las pruebas focales del cambio pasan. Después se añaden y ejecutan
correctamente otras2 pruebas de invariantes por bytes; no estaban incluidas
en las921. Las pruebas del donante no se presentan como pruebas de esta revisión.
No ha habido SSH,
captura nueva, navegación, recogida ni cambios del robot en esta intervención;
carga y comportamiento físico del port siguen PENDIENTES.

Recetas exactas y resultados en `scenario1-regression-final-receipt.json`,
`baseline-deposit-installer-complete-receipt.json` y recibos focales del directorio
de evidencia. Revisión focal reproducible, sin robot:

```bash
python3 -B -m unittest \
  scripts.box_handling.test_scenario1_box_alignment \
  scripts.box_handling.test_scenario1_box_alignment_runtime \
  scripts.box_handling.test_scenario1_box_alignment_cli \
  scripts.box_handling.test_scenario1_box_alignment_guard \
  scripts.box_handling.test_scenario1_box_alignment_console \
  scripts.box_handling.test_scenario1_health_base \
  scripts.box_handling.test_scenario1_box_alignment_arm_invariants
git diff --check
```

Evidencia privada:
`../Humanoide-vla-evidence/20261022T080944Z_BOX_ALIGNMENT_ONLY_PORT/`.
`context.json` fija ambos HEAD; `arm-invariants-before.json` conserva once
archivos/SHA y paquete generado; `before/` y `before-sha256.json` guardan el
estado previo. `before-alignment-docs/manifest.json` respalda esta guía como
ausente y la versión anterior de Optimistic. Las verificaciones locales y
fuentes finales se conservan allí antes de cerrar el cambio.

Reversión con todos los ejecutores detenidos: restaurar selectivamente los
archivos modificados del port desde sus backups y retirar sólo módulos/tests
nuevos sin referencias, preservando cambios de mesa74 y trabajo posterior.
Alternativa operativa `--box-alignment-attempts 0`: omite sólo esta fase,
manteniendo los gates y los movimientos originales. No restaura postura física,
checkpoints, sesiones, mapa ni un estado anterior del robot. Sin push.
