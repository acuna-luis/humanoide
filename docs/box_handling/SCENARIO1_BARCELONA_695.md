# Escenario 1 en Barcelona: depósito a 69,5 cm

**21-10-2026, Europe/Madrid — BOX-01-BARCELONA-695.**
**Seguimiento actual: cuarto ensayo FINAL rc78; ninguno de los cuatro alcanza el depósito.**
El cuarto completa `get1` (≈10,6 mm / 0,44°), visión y bajada de cabeza.
La corrección solicitada de 23,1 mm termina a ≈4,9 mm / 0,42°; X de caja
pasa de 77,910 a 76,500 cm. El gate nativo acepta
XYZ≈76,31 / −3,41 / 79,25 cm. Durante el agarre nativo, tras unos 19,4 s,
el watchdog informa `PERSISTENT_WORKER_LOST`; el lector de salud termina con
`ValueError: estop not confirmed clear`. Cancelación aceptada (ack0/status5)
no demuestra parada física ni éxito de agarre. No se alcanzan `verify_held`,
retirada, `put1`, depósito o HOME del ciclo.

`fourth-interruption-read.json` conserva los últimos valores de paro/servo0
anteriores al fallo; no permite descartar una activación posterior. La app nativa
presenta un reinicio (count1) y cero servidores ROS en la consulta posterior.
`Clamp box succeed` y `HQP solve failed` no prueban éxito físico ni la causa del
reinicio. Los relojes PC/robot difieren aproximadamente un minuto; no ordenar
eventos de ambos hosts por su hora absoluta sin corregir esa diferencia.
**Estado físico actual pendiente:** confirmar presencialmente caja sujeta,
apoyada o retirada e inmovilidad antes de decidir una recuperación específica.
No repetir el ciclo ni enviar HOME automáticamente. Depósito695 y retorno
siguen sin prueba física; `PHYSICAL_QUALIFICATION=None`.

**Historia de los tres primeros ensayos.**
Archivos695 instalados y SPS repuesto. El primero se interrumpe durante el
agarre por el recuento de servidores del servicio de controlador; el segundo,
antes del agarre nativo, por `LIVE_HEALTH_STALE: estop receipt`. El tercero
completa `get1`, visión y bajada de cabeza; la observación X de caja pasa de
79,803 a 77,672 cm tras una primera corrección solicitada de 28,0 mm.
La segunda corrección, de 20,7 mm, se cancela por
`Correction made no significant progress`, con avisos `LOCATION_LOST`.
**No se inicia el agarre nativo en el tercero ni se completan recogida,
navegación a `put1`, depósito o HOME del ciclo en ninguno de los tres.**

Los lectores de los dos paros solicitan ahora RELIABLE/VOLATILE, conservando
frescura, valores y latch. El preflight de cinco rondas adicionales pasa y en
la tercera sesión no reaparece `estop receipt stale`; este alcance no demuestra
una solución exhaustiva. El cuarto ensayo falla por paro no confirmado libre,
según el seguimiento actual anterior. El estado físico y la localización deben
comprobarse de nuevo.
La descripción siguiente conserva la preparación local inicial y sus recetas.
[Cronología, recibos y resultados de los cuatro ensayos](../incidents/2026-10-21_BARCELONA_TABLE695_ENSAYO.md).

Estado inicial al terminar la preparación local: **instalación, carga y prueba física PENDIENTES**.
Se conserva el depósito de 90 cm como opción predeterminada de
`scripts/optimistic_scenario1.sh`. La altura de Barcelona se selecciona
expresamente con `--table-height-cm 69.5`.

La preparación inicial creó archivos y una vía de ensayo acotado sin conectar
al robot, instalar el paquete remoto, recargar servicios ni enviar movimiento.
La intervención posterior autorizada sí instaló los archivos y llegó al agarre,
según el seguimiento anterior. El ensayo de 90 cm del 01-10 es un precedente de trabajo por etapas;
su cualificación no se transfiere a 69,5 cm. El ciclo completo a la nueva altura
permanece bloqueado hasta disponer de evidencia física específica, incluida la
liberación y el retorno a HOME medido.

## Qué cambia y qué debe comprobarse

La receta parte de la superficie original de 45 cm, cuya compatibilidad funcional
fue confirmada por el operador en la adaptación anterior. Esa referencia no es
una nueva medición del montaje de Barcelona.

| Dato de la receta | Valor |
|---|---:|
| Superficie original de referencia | 0,450 m |
| Superficie de destino solicitada | 0,695 m |
| Incremento de altura | +0,245 m |
| Z absoluta inicial de cada mano | 0,650 → 0,895 m |
| Descenso relativo original | 0,200 m |
| Z final resultante de la receta | 0,695 m |

Las Z de manos son **coordenadas de tarea**, no una medición independiente desde
el suelo ni de la base de la caja. Sólo se trasladan las dos Z absolutas
iniciales. Se conservan X/Y, orientaciones, torso, tamaño de caja, tiempos,
descenso relativo, apertura y controles originales de fuerza/colisión. Motion
calcula las articulaciones; el paquete no contiene una trayectoria articular
nueva cualificada.

La adaptación presupone la misma caja original de **0,603 × 0,397 × 0,220 m**,
abrazaderas, agarre y disposición horizontal de la referencia. La mesa de
Barcelona es provisional: antes del ensayo hay que medir y registrar su altura
suelo–superficie, estabilidad, márgenes de apoyo y posición respecto al robot.
Una diferencia de montaje no queda resuelta cambiando sólo el número de altura.
Los estudios y la prueba de 90 cm tampoco certifican alcance, colisiones o
seguimiento a 69,5 cm.

En la feria deben prepararse y comprobarse **el mapa real y sus puntos `get1` y
`put1`**. No usar las coordenadas del montaje anterior como puntos del nuevo
recinto, ni considerar válida una llegada por conservar el nombre del mapa.
El perfil software y el efector físico deben corresponder a abrazaderas
(`HW_TYPE=cruzr_s2_v1`); cambiar físicamente las manos no selecciona ese perfil.

## Selección de altura

Desde la raíz del repositorio, los siguientes planes son locales y no mueven:

```bash
./scripts/optimistic_scenario1.sh --plan --table-height-cm 69.5
./scripts/optimistic_scenario1.sh --plan --table-height-cm 45
./scripts/optimistic_scenario1.sh --plan --table-height-cm 90
```

Sin selector explícito, optimistic conserva 90 cm. El argumento admite únicamente
`45`, `69.5` y `90`; se escribe punto decimal en la terminal. `--table-height-cm`
y `--profile` son excluyentes. Cada variante conserva su identidad y sus
checkpoints: no cruzar los de 45, 69,5 y 90 cm.

El perfil nuevo es
[`scenario1_table695_geometry.json`](../../config/box_handling/scenario1_table695_geometry.json).
La receta está en
[`scenario1_table695.py`](../../scripts/box_handling/scenario1_table695.py), con
`PHYSICAL_QUALIFICATION=None`. La tarea aditiva identificada por su contenido es:

```text
local_scenario1_deposit/da20110015415128cfc8d89ba7ce4f1dfa8e23498d72381d528316687545d128
```

## Preparar y comprobar el paquete

Generar en una carpeta local nueva; el generador rechaza un destino existente:

```bash
python3 -B scripts/box_handling/prepare_scenario1_table695.py \
  --output /ruta/nueva/table695
```

El resultado contiene XML, YAML, `bundle.json` y `review.json`. El generador
contrasta las fuentes originales y conserva pendientes la validación cinemática
y física. También existe una copia preparada en
[`config/box_handling/table695_candidate/`](../../config/box_handling/table695_candidate/).

Validar ese bundle **sólo en el PC**, sin conexión remota:

```bash
python3 -B scripts/box_handling/scenario1_table695_install.py \
  --bundle /ruta/nueva/table695/bundle.json
```

La siguiente **receta se conserva de la preparación local inicial**; la
instalación posterior ya está registrada en la cronología enlazada arriba.
`--install` sí conecta y cambia archivos de Motion; requiere
inventario y respaldo del estado real, así como una carpeta de evidencia nueva:

```bash
python3 -B scripts/box_handling/scenario1_table695_install.py \
  --bundle /ruta/nueva/table695/bundle.json \
  --install --evidence-dir /ruta/privada/nueva/instalacion695
```

La escritura es aditiva: XML bajo
`/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/`
y YAML bajo
`/opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config/meta_clamp/`,
con el nombre de tarea anterior. No sobrescribe las tareas originales, recarga
servicios ni mueve el robot. El recibo de archivos instalados no demuestra carga
nativa o éxito físico. Las dependencias de modelo, HOME y primitivas se contrastan
por hash; una actualización exige revisar compatibilidad.

Después de instalar y preparar el montaje real, la comprobación del escenario
consulta el robot sin ordenar movimiento:

```bash
./scripts/optimistic_scenario1.sh --check --table-height-cm 69.5
```

Un check correcto no certifica la geometría de la mesa ni autoriza por sí solo
un movimiento. No ejecutar recetas remotas para resolver una dependencia que
todavía no se haya identificado.

## Ensayo nuevo: terminar después del depósito

Antes de cualquier movimiento, comprobar de nuevo las condiciones físicas de
AGENTS.md: abrazaderas y objeto, postura/HOME, ambas baterías, cargador, ambos
paros, ruedas y modo, recorrido de brazos/chasis/caja, control exclusivo y persona
junto al paro. No inferirlas de los ensayos de 90 cm ni de una fotografía.

La vía explícita para **un ensayo supervisado a 69,5 cm** es:

```bash
./scripts/optimistic_scenario1.sh --run --table-height-cm 69.5 \
  --stop-after deposit --deposit-trial
```

Este comando puede navegar, recoger, transportar, depositar y abrir las
abrazaderas. Conserva los controles técnicos y nativos y termina inmediatamente
después de depósito/apertura, **antes de asumir liberación y antes de HOME**.
`--deposit-trial` sólo admite este perfil con `--stop-after deposit` y ejecución
explícita; no se usa para el plan o el check. No acredita previamente la nueva
altura ni habilita el ciclo completo. No añade reintentos tras un fallo.

Conservar el checkpoint y los resultados de ese segmento. La política optimistic
puede registrar sujeción asumida; el éxito de la tarea y su apertura no sustituyen
la comprobación de que la caja está apoyada estable y ambas abrazaderas libres.
Si hay apoyo parcial, contacto, fallo o estado incierto, conservar la postura y
aplicar la recuperación específica: no repetir el ciclo ni enviar HOME para probar.

## Retorno separado tras confirmar liberación

Sólo después de confirmar físicamente **caja apoyada estable, abrazaderas vacías
y libres, y recorrido completo de HOME despejado**, usar el checkpoint real del
segmento de depósito. Primero comprobar la reanudación sin mover:

```bash
./scripts/optimistic_scenario1.sh \
  --resume /ruta/privada/ensayo695/checkpoint.json \
  --table-height-cm 69.5 --box-state released --recovery-confirmed --check
```

Si la comprobación y las condiciones físicas actuales permiten el retorno,
la ejecución separada es:

```bash
./scripts/optimistic_scenario1.sh \
  --resume /ruta/privada/ensayo695/checkpoint.json \
  --table-height-cm 69.5 --box-state released --recovery-confirmed
```

Esta segunda orden puede mover el robot y ejecutar HOME. **No lleva
`--deposit-trial`**: es la recuperación desde liberación confirmada, no otro
depósito. El check no consume el origen; una reanudación física sí lo consume.
No reutilizar un checkpoint ya consumido ni sustituirlo por el de otra altura.
La salud y la postura se renuevan antes de actuar, y HOME debe quedar medido.

Hasta cerrar y registrar el ensayo específico, una ejecución completa nueva a
69,5 cm sin la pausa de prueba sigue bloqueada. No editar el campo de
cualificación para fabricar evidencia ni heredar el ensayo de 90 cm.

## Estado de la preparación local inicial, evidencia y reversión

- **Preparado localmente:** selector de altura, contrato/perfil 69,5 cm, generador,
  bundle e instalador aditivo; vía de ensayo acotado y retorno separado.
- **PENDIENTE:** medición del montaje de Barcelona, mapa/puntos reales, contraste
  del robot, instalación, carga nativa, revisión cinemática/escena y prueba física
  con liberación y HOME medido.
- **VERIFICADO localmente:** 686 pruebas de escenario correctas en 8,196 s,
  incluidas 20 nuevas de 69,5 cm; planes 45/69.5/90 y predeterminado90,
  generación reproducible, exportación/validación local del instalador, AST Python,
  JSON, Bash y `git diff --check` correctos. Los archivos/perfiles/artefactos90
  y el perfil original45 conservan sus hashes. La suite legacy
  `test_scenario1_deposit_install` no se incluyó por los errores de fixtures
  preexistentes documentados en la adaptación90; el instalador695 se ejercita
  mediante FakeDocker, incluidos conflictos y orden YAML antes de XML.
  `scenario-regressions.log/.json` y `local-validation.json` conservan resultados
  y comandos. Durante esa preparación inicial no hubo comprobación remota ni
  ensayo cinemático/físico nuevo; el seguimiento superior registra lo posterior.

Evidencia privada de la preparación local inicial:
`../Humanoide-vla-evidence/20261021T113037Z_BARCELONA_TABLE695/`.
El estado anterior está en `before/`; conservar fuentes pendientes de commit,
recibos, resultados y hashes. No se instalaron paquetes ni se hizo commit o push.

Reversión PC: retirar selectivamente las fuentes nuevas de 69,5 cm y restaurar
los fragmentos modificados desde `before/`, preservando cambios ajenos. El
depósito predeterminado de 90 cm se conserva durante esta adaptación. Si después
se instala el bundle remoto, su reversión debe retirar únicamente los archivos
aditivos cuyos hashes coincidan con el recibo, sin sustituir originales, recargar
ni mover como parte de la retirada. Una reversión de archivos no recupera la
postura ni el estado físico de la caja.

Precedente y límites: [ensayo de mesa90](SCENARIO1_TABLE90_CANDIDATE.md).
Supervisión: [ejecutor optimistic](OPTIMISTIC_SCENARIO1.md).
