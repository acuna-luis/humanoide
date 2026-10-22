# Escenario 1 con supervisión continua

### Ensayo integrado74 interrumpido antes de recoger — 22-10-2026, 18:49 CEST

**BOX-UNIFIED74-ALIGNMENT-FAIL-20261022 — OBSERVADO; no valida depósito ni tiempo de ciclo.**
Ejecución `20261022T164937Z_OPTIMISTIC_SCENARIO1_1546460`, perfil
`scenario1_height_74_v1`, con `--height-deposit-trial`. Llegó a get1 en31,948 s
(incluye sincronización de mapa5,3 s), activó visión en1,794 s y falló durante
la etapa de preparación/recogida tras17,874 s hasta el evento de error. No se
envió el agarre nativo ni se alcanzaron retirada, put1, depósito o HOME.
Desde primer evento hasta ready:14,735 s; envolvente completa registrada en
Motion70,855 s. Son ventanas del registro, no duración total del comando PC:
no se resta el reloj Motion del PC ni se compara esta toma parcial con323,879 s
como si fuera un ciclo completo.

Causa inmediata VERIFICADA: el primer ajuste visual pedido fue15,413 mm en X.
El guard se armó y canceló4,003 s después por falta de mejora significativa;
el criterio existente exige2 mm de mejora dentro de4 s. Distancia al objetivo
según mapa15,415→14,464 mm: mejora neta0,951 mm. Hubo telemetría y movimiento:
excursión máxima mapa7,086 mm y odometría18,023 mm, sin violación de velocidad.
Son métricas de sus propios marcos; no prueban por sí solas deslizamiento.
Durante ese intervalo los feedbacks siguieron en LOCATE_RUNNING; el resultado
tras cancelar fueRELOCATE_CANCEL/status5. Hipótesis: el microajuste no llegó
a una localización/convergencia utilizable antes de vencer el guard; no se ha
probado la causa física de esa falta de convergencia. No afirmar que estuvo
inmóvil o que el depósito integrado falló.

Los errores de lease/health posteriores son cierre en cascada tras el error
inicial; no constituyen prueba de fallo de brazos. Parada física no confirmada
por el resultado de cancelación. No se ha enviado nueva orden, reintento ni
HOME, ni se ha relajado watchdog/localización para continuar. La siguiente
revisión debe estudiar la gestión del microajuste y la localización; el
presupuesto de7 intentos no sirve si el primer objetivo se cancela con estado
físico sin confirmar. La toma no proporciona un nuevo tiempo objetivo medido.

Observación local iniciada con proceso activo; el helper de sondeo llegó cuando
el PID ya había terminado y no inició captura continua. El desglose se recuperó
del journal original completo, conservando sus timestamps. Informe JSON/CSV y
backup documental: `../Humanoide-vla-evidence/20261022_UNIFIED_LIVE_TIMING_185108/`.
Fuentes originales intactas. Código/robot/servicios sin cambios en esta revisión.


**22-10-2026 — BOX-TABLE74-EMPTY-HOME-RECOVERY-20261022: HOME recuperado.**
Tras confirmar caja/pines libres, abrazaderas vacías y barrido libre con brazos
aún en agarre/torso inclinado, el usuario autoriza un único HOME. Lecturas nuevas
correctas, HOME instalado d9e946 sin cambios. Goal b559d0c5 termina SUCCEED4/
1101001; comando16,594 s. Dos muestras20D HOME=1, velocidad0, máximo0,002109 rad;
SOC55,8/56,1 %, paros/cargador0. Sin apertura, navegación, reset ni reintento.
Pin-relief original consumido antes de HOME mediante marcador nuevo; archivos
originales y cycle interrupted intactos. No reutilizar esa frontera. Programa
sin cambios; el nuevo ciclo b92d004 no se ha probado. Confirmación visual final
PENDIENTE. [Resultado y receta](../incidents/2026-10-22_APERTURA_BLOQUEADA_TELEMETRIA_CADUCADA.md#recuperación-home-autorizada-y-ejecutada--22-10-2026).

### Ciclo común por altura: optimización implementada — 22-10-2026

**BOX-SCENARIO1-UNIFIED-FAST-20261022 — código y pruebas offline; robot sin modificar ni mover.**
Esta entrada sustituye la propuesta anterior como estado del código. La toma
323,879 s sigue siendo la última medición física del flujo antiguo: no se ha
medido todavía el nuevo flujo. No se atribuye al nuevo código un éxito físico.

`optimistic_scenario1.sh --table-height-cm 74|90` selecciona ahora perfiles del
mismo motor `scenario1_runtime`, con una conexión, un monitor de salud y un
checkpoint para todo el ciclo. Se eliminan los cinco arranques separados del
depósito y la sesión HOME independiente. Se conserva el descubrimiento inicial,
la evaluación de salud fresca entre etapas, identidad de contenedores/archivos,
llegada y reposo, controles nativos y HOME medido. La tarea de recogida y sus
constructores no cambian. No se modifican límites de velocidad ni del chasis.
La interpolación74 sí cambia:19 cm entre las referencias t10 y t12; puede
aumentar la velocidad efectiva frente a los dos descensos partidos y exige ensayo.

| Perfil | Colocación nativa | Liberación | Estado |
| --- | --- | --- | --- |
| 74 cm | Aproximación Z nominal0,94; descenso relativo único19 cm en el tramo final de la misma tarea12 s; torso relativo final0 | Pines:4 cm verticales/2 s; después10 cm laterales por lado/2 s, sin rotación añadida | Nueva interpolación PENDIENTE de ensayo; mismos destinos nominales de la receta anterior, resultado físico sin comprobar |
| 90 cm | Geometría histórica: Z inicial1,10; manos y torso−20 cm al final de tarea12 s | Apertura original2 s, simultánea lateral/−5 cm y orientación vendor | Geometría conservada; nuevo empaquetado/sesión PENDIENTE de ensayo |

Los perfiles **no son sólo una resta de alturas**: registran por separado el
movimiento del torso y la liberación. Sólo74 y90 están admitidos. Añadir otra
altura exige revisar su geometría y ensayarla; no implica copiar otro motor.
La ventana de fuerzas y demás bytes de control del YAML original se conservan;
la nueva interpolación74 requiere comprobar contacto y holguras. Éxito nativo
no mide apoyo ni pines libres. En el modo sin preguntas siguen siendo supuestos
del montaje conocido; no se crean medidas ni certificados de validación.

**Ahorro buscado, aún no medido:** quitar arranques repetidos y consultas HOME
externas; colocación/liberación74 pasa de38 a16 s nominales. Como hipótesis
inicial, aproximadamente210–240 s por ciclo frente a323,879 s, con la misma
recogida y navegación. No es un compromiso: puede variar con localización,
ajustes y salud; no sumar los huecos SPS a los arranques que ya los incluyen.

Plan local, sin conexión, instalación ni movimiento:

```bash
./scripts/optimistic_scenario1.sh --table-height-cm 74 --box-alignment-attempts 7 --plan
./scripts/optimistic_scenario1.sh --table-height-cm 90 --plan
```

Preparación opcional fuera de la toma cronometrada, con directorio nuevo:

```bash
python3 -m scripts.box_handling.scenario1_height_deposit --height-cm 74 \
  --output ../Humanoide-vla-evidence/altura74-integrada-instalacion
python3 -B scripts/box_handling/scenario1_table74_trial_install.py \
  --bundle ../Humanoide-vla-evidence/altura74-integrada-instalacion/bundle.json --install
./scripts/optimistic_scenario1.sh --table-height-cm 74 --check
```

El instalador sólo añade archivos de tareas; no publica ROS, no cambia modos,
no reinicia servicios y no sobrescribe originales. Conserva recibos/rollback en
`/var/tmp/cruzr-table74-trial/<id>`. Antes de armar, el CLI verifica y copia ese
paquete al PC. Si falta instalación, `--check` informa y termina sin instalar;
un futuro `--run` autorizado prepara los archivos antes del preflight físico.
Ethernet directa requerida para este instalador. Cambiar altura cambia el
paquete inmutable, no el motor; los paquetes ya presentes se comprueban/reusan.

**Primer ensayo físico, sólo después de comprobar las condiciones actuales:**

```bash
./scripts/optimistic_scenario1.sh --table-height-cm 74 \
  --box-alignment-attempts 7 --height-deposit-trial --run
```

`--height-deposit-trial` declara la elección de ensayar el nuevo paquete; no
omite paros, fuerza, límites, cargador, salud ni localización, y no convierte el
perfil en probado. Actualmente es obligatorio para todo ciclo completo con
estos perfiles. No se autoriza el ensayo por el mero hecho de documentarlo.
No activar `--cycle` hasta revisar el primer resultado y sus tiempos.
Para probar sólo recogida/llegada, `--stop-after grasp|put1` conserva las pausas.
La reanudación de un checkpoint **nuevo** usa la misma altura/perfil y, si
alcanza depósito/HOME, también `--height-deposit-trial`; nunca repetir el agarre
con caja sujeta. Ctrl+C guarda la retoma conservando altura y modo de ensayo.

Compatibilidad: `--table-height-cm 74 --table74-supervised` mantiene el flujo
anterior por fases. Checkpoints antiguos del perfil74 de preparación siguen
por su coordinador antiguo; no se migran a la trayectoria integrada ni se
reutilizan checkpoints consumidos. `--continue-deposit` y `--finish-deposit`
conservan sus protocolos. Ante resultado desconocido no se repite depósito ni
se envía HOME automáticamente.

Fuentes: `scenario1_height_deposit.py` (perfiles/generador/validador puro),
`scenario1_cli.py`, `scenario1_runtime.py`, `scenario1_contract.py` y extensión
del instalador existente. Los hashes del modelo, HOME, bibliotecas y tareas
originales se comprueban de nuevo antes de las acciones. La validación aislada
reconstruye el paquete desde fuentes fijadas; recalcular un hash no permite
cambiar fuerza, trayectorias o tareas arbitrarias.

Verificación offline: regresión1133 pruebas correcta;17 pruebas focalizadas
del nuevo flujo (incluyen dos casos adicionales posteriores a esa regresión),
bootstrap aislado de Runtime/instalador, planes74/90 y sintaxis Bash correctos.
La suite antigua test_scenario1_deposit_install se excluyó por sus17 errores
de fixtures ya documentados; no se modificó. Ninguna prueba contacta al robot.

Reversión: volver al modo supervisado anterior o revertir sólo el commit de
esta intervención; para retirar un paquete instalado, usar el instalador con
el mismo `bundle.json` y `--rollback`, sin tarea activa. Sólo elimina archivos
aditivos propiedad del paquete con hashes intactos; no toca SDK/originales ni
registros de ejecución. No cambiar código/perfil con caja sujeta para empezar
un ciclo nuevo. Evidencia y respaldo local:
`../Humanoide-vla-evidence/20261022_UNIFIED_FAST_CYCLE_183415/`.


**22-10-2026 — BOX-TABLE74-OPEN-STALE-20261022: aborto antes de apertura.**
Toma162111Z1476072: alivio SUCCEED4/1101001, journal sin consumir; apertura
sin ready, acciones ni trial.json; HOME no iniciado. Health inicial falla en5,860 s
por `Collected safety samples became stale`. Inconsistencia VERIFICADA: adquisición
completa exige2 s para todos los recibos, monitor continuo admite5 s para paros
con cadencia histórica≈4,49 s. Puede fallar con valores invariantes; canal/edades
reales no archivados, causa temporal concreta PENDIENTE. Diagnóstico offline,
sin arreglo operativo ni movimiento; conservar frontera tras alivio y no repetir ciclo.
[Análisis y reproducción](../incidents/2026-10-22_APERTURA_BLOQUEADA_TELEMETRIA_CADUCADA.md).

## Ciclo completo supervisado para mesa de 74 cm

### Preparación de la próxima medición y candidatos para demo — 22-10-2026

**BOX-DEMO-TIMING-PREP-20261022 — VERIFICADO offline; ciclo nuevo PENDIENTE.**
El usuario pide preparar otra toma, **sin ejecutarla hasta su aviso**, y estudiar
operaciones sin valor en un montaje de demo repetible. No se cambia el control,
la receta, las distancias, las comprobaciones ni las trayectorias en esta preparación.

Se versionan dos herramientas locales independientes del ejecutor:
[observador](../../scripts/box_handling/scenario1_timing_observe.py) y
[analizador](../../scripts/box_handling/scenario1_timing_analyze.py).
El observador sólo lee `cycle.json` cada10 ms y escribe sus cambios en otro
archivo nuevo; no importa el runtime ni abre SSH/ROS, inicia ciclos o manda señales.
Ctrl+C sólo termina el observador. No queda proceso de observación iniciado.
El analizador incorpora la receta usada para la referencia323,879 s, antes
ubicada sólo en evidencia privada; genera `summary.json` y `pc-phases.csv`.

#### Captura preparada para cuando se autorice el ciclo

Elegir una carpeta NUEVA externa al repositorio para cada toma. En estos ejemplos
`/ruta/nueva-toma` es un marcador que debe sustituirse; no es evidencia existente.
Antes de lanzar por separado el ciclo autorizado, arrancar el observador:

```bash
python3 -B scripts/box_handling/scenario1_timing_observe.py \
  --evidence /ruta/nueva-toma/cycle \
  --output /ruta/nueva-toma/cycle-observer.jsonl
```

La carpeta padre de salida debe existir y el archivo debe ser nuevo. El observador
espera hasta30 minutos y sale al ver un estado terminal, también `paused`.
No reutilizar carpeta/journal anterior. Tras terminar observador y ciclo:

```bash
python3 -B scripts/box_handling/scenario1_timing_analyze.py \
  --evidence /ruta/nueva-toma/cycle \
  --observer /ruta/nueva-toma/cycle-observer.jsonl \
  --output /ruta/nueva-toma/timing-analysis
```

`timing-analysis` también debe ser nuevo. El resultado separa ventanas PC,
etapas de recogida, acciones SDK, eventos `timing`, arranque hasta ready y
consultas HOME ya registradas. No resta relojes PC/Motion ni suma intervalos
anidados/paralelos. Sin captura externa del comando, `wrapper` queda ausente:
el total es **journal**, no comando completo. Para repetir el total323,879 s,
medir además inicio/salida del comando con reloj monotónico PC cuando se lance;
se conservará recibo `command-result.json` compatible, sin convertir una espera
del observador o check independiente en tiempo del robot.

Limitaciones: sondeo no garantiza capturar toda transición; se indica si falta
final de fase. Las ventanas incluyen coordinación y no miden comienzo/fin físico.
El hueco atribuido a descubrimiento SPS sigue siendo INFERENCIA por orden de
código, sin cronómetro propio. HOME no tiene accepted/result individuales.
No inventar esos tiempos ni contar una toma interrumpida como ciclo completo.

#### Candidatos concretos, todavía sin aplicar

| Prioridad | Coste identificado | Cambio propuesto y condición |
| --- | --- | --- |
| 1 | Seis arranques hasta ready:83,885 s incluidos en la toma anterior | Mantener una sesión/clientes/monitor para todo el ciclo; eliminar arranques repetidos, conservar evaluación de salud fresca al pasar de etapa. El total no es ahorro íntegro garantizado |
| 2 | Descubrimiento SPS repetido al iniciar Runtime.run; huecos atribuidos45,986 s, incluidos en los arranques anteriores | Descubrir topología al inicio/contexto y vigilarla dentro de sesión; no arrancar descubrimiento de percepción en cada descenso sin uso de visión. Invalidar al cambiar boot/contenedor/topología. No sumar45,986 a83,885 |
| 3 | Aproximación+dos descensos:36 s nominales; cada descenso mantiene referencias cero hasta10 s | Integrar un descenso de apoyo y quitar tiempos heredados sin desplazamiento cuando su función haya sido revisada. Son referencias de trayectoria, no `sleep`; validar fuerzas, interpolación y nueva trayectoria antes de probar |
| 4 | Instalador/archivo de rollback por fase y liberación con staging separado | Generar e instalar por contenido/configuración antes del ciclo cronometrado; verificar identidad vigente y conservar respaldo único verificable. La procedencia de cada ejecución/consumo sigue separada |
| 5 | HOME42,514 s de bloque total, movimiento sin cronómetro individual | Compartir monitor y clientes; localizar adquisición/consultas repetidas. No atribuir todo el bloque a HOME físico ni prometer eliminarlo |
| 6 | Medidas manuales repetidas de montaje | Declarar una vez geometría calibrada de mesa/caja/efector y recorridos para la demo. Ya existe receta sin preguntas: verificar antes si el coste está realmente eliminado |

Las distancias nominales y holguras del montaje pueden registrarse como
**supuestos de receta**, con perfil/hash; no son mediciones nuevas de apoyo,
pines o posición real. La llegada del navegador, el reposo tras la acción y la
salud cambian durante un ciclo, aunque mesa y destino sean los mismos. Mantener
esas observaciones, paros, cargador, batería, límites, fuerza, localización,
identidad del resultado y HOME medido. El objetivo es eliminar adquisiciones y
preparación duplicadas, usando datos frescos del monitor, sin forzar éxito.

La siguiente toma debe conservar el flujo actual para comparar contra323,879 s,
registrar ajustes de alineación reales y distinguir preparación/SDK/cierre.
Después seleccionar cambios por ahorro **medido**, probando nueva geometría
aparte. No se fija aún un tiempo objetivo ni se afirma que toda la infraestructura
sea prescindible. Un montaje de demo no acredita que su estado real no cambie.

Verificación offline: replay de la toma anterior reproduce journal323,798353316 s,
ocho ventanas (incluida coordinación) y residual0; éxito/HOME registrados
conservados. Ensayos locales sintéticos: pausa terminal, journal intacto,
rechazo de salida existente/dentro del ciclo, timeout sin journal y duración de
acción usando sólo reloj interno Motion. `--help` de ambas herramientas correcto.
No consultas ni cambios en robot/servicios. Backup/validación:
`../Humanoide-vla-evidence/20261022_DEMO_TIMING_PREPARATION_163323Z/`.
Reversión: retirar únicamente estas herramientas y sus entradas documentales;
no tocar evidencia/journals ni revertir el control. Ensayo nuevo PENDIENTE.

### Comparación 90/74 cm y diseño de un único ciclo — 22-10-2026

**BOX-SCENARIO1-UNIFIED-HEIGHTS-REVIEW-20261022 — comparación offline; implementación pendiente.**
Se comparan `feat/scenario1-deposit-table-90cm@ad3e23a` y
`74-jacob@7da25ba`, sin checkout, merge, conexión ni movimiento del robot.

#### Comparación de tiempos y alcance

La última toma completa guardada del perfil90 es
`20261014T160430Z_OPTIMISTIC_SCENARIO1_1214265`:156,430 s entre primer y último
evento Motion. Las cinco últimas tomas completas de ese perfil oscilan entre
149,531 y182,212 s, mediana156,430 s. Todas completan diez etapas sin fallo.
La toma actual74 es `20261022T160455Z_TABLE74_CURRENT_BASELINE`:323,879 s de
comando PC, medida continua y confirmada por el operador.

| Bloque | Histórico90, s | Actual74, s |
| --- | ---: | ---: |
| Ir a get1 | 28,287 | 28,273 |
| Alineación/recogida | 43,512 | 56,777 |
| Ir a put1 | 23,662 | 17,982 |
| Aproximación, depósito y apertura | **14,626** | **153,026** |
| HOME y verificaciones de liberación/HOME | 19,737 | 42,514 |
| Total registrado, aproximadamente | **156,430** | **323,879** |

Los mapas/destinos, fecha y boot son distintos. El total90 usa una ventana de
eventos Motion; el total74, reloj monotónico del comando PC. Esto describe
registros históricos, no una prueba controlada de cambio de software.
El módulo `scenario1_table90.py` de las cinco tomas coincide por SHA con el
tip de la rama90, igual que la identidad de receta/bundle. CLI/runtime no
coinciden íntegramente con ese tip: no atribuir todo el tiempo histórico a
la compilaciónad3e23a. Los recibos y diferencias se conservan en la evidencia.

#### Diferencia funcional que explica la lentitud

**90 cm:** el runtime común ejecuta una etapa deposit, una acción SDK y
una tarea nativa XML: MetaClamp de colocación12 s, después open_arm2 s.
El primer bloque aproxima/avanza y contiene un descenso nominal20 cm al final;
las referencias de manos y torso bajan20 cm. La apertura desplaza cada mano
10 cm hacia fuera y5 cm hacia abajo simultáneamente. El total nominal es14 s.

**74 cm:** el ciclo de pruebas supervisadas se convirtió en coordinador del
ciclo automático. Conserva cinco ejecuciones independientes:
aproximación12 s, precontact14 cm/12 s, support5 cm/12 s, alivio4 cm/2 s
y apertura lateral10 cm/2 s. Total nominal40 s; acciones SDK medidas41,350 s.
En precontact/support, las referencias son cero a6 y10 s; el desplazamiento
final se programa entre10 y12 s. Se repite esa estructura de12 s dos veces,
aunque ya no hay aproximación que realizar en ellas.

Cada tarea abre sesión, descubre acciones, adquiere salud, valida llegada,
prepara/instala y archiva antes de ejecutar. Sólo esos cinco arranques hasta
ready suman71,694 s en la última toma. Las cinco fases completas suman153,026 s;
la diferencia111,676 s respecto a acciones SDK contiene infraestructura,
comprobaciones y cierre, no tiempo íntegramente eliminable.

La altura **no exige por sí misma dos descensos de apoyo**. La división14+5 cm
procedía del ensayo de huecos/apoyo y sigue en producción. El alivio4 cm
posterior es otra operación: desenganchar pines con la caja ya apoyada.
Unificar no significa quitar esa función.

También hay una diferencia geométrica real: en los descensos74 se piden
deltas de torso cero, mientras90 pide descenso del torso. Referencia cero
no es un bloqueo mecánico. Además, apertura74 separa bajar4 cm de abrir10 cm;
90 combina bajar5 cm y abrir. No son recetas equivalentes salvo por altura.
Los generadores `front_box_integration.py` y `front_box_adapter.py` del agarre
sí son idénticos entre ambas ramas; el runtime/alineación/supervisión evolucionó.

#### Diseño propuesto para un único branch mantenible

1. **Un motor de ciclo y una sesión.** Navegación, visión, agarre, retirada,
   depósito y HOME comparten runtime/monitor/checkpoints. Recuperar el patrón
   integrado90 manteniendo las correcciones útiles actuales; no sustituir
   todo el código nuevo por la rama antigua ni importar cambios de agarre.
2. **Un generador de depósito parametrizado.** Altura y calibración de
   caja/efector/mesa alimentan la misma construcción XML/YAML. La altura no
   selecciona otro orquestador. Una tarea de producción aproxima y hace
   **un descenso de apoyo**, seguido del desenganche/apertura apropiados.
   Preservar correctamente referencias y ventanas de fuerza/contacto.
   Aprovechar el generador geométrico existente scenario1_deposit.py,
   completando su integración en el runtime común, en lugar de otro módulo
   de ejecución independiente por cada altura.
3. **Perfiles de geometría, no forks del programa.** Misma estructura para
   74 y90 cm: altura de superficie, referencia calibrada de caja/manos,
   holgura de aproximación, política de torso, descenso, alivio y apertura.
   El principio deltaZ=altura_objetivo−altura_referencia sólo se aplica a
   una referencia válida; Z de Motion no se equipara sin más a altura al suelo.
4. **Producción y puesta a punto diferenciadas.** El modo normal usa la tarea
   integrada. El modo de ensayo permite parar antes de apoyo/liberación y
   medir; las pausas/retomas históricas se conservan para diagnóstico, sin
   imponer sus cinco procesos al flujo normal.
5. **Instalación por contenido.** Generar/verificar una vez por perfil y
   contexto; hash de tarea/contexto vigente antes del despacho. Un paquete
   cambia con su geometría/configuración, no por el UUID del ensayo anterior.
   Mantener evidencia/consumo por ejecución separados de la receta reutilizable.
6. **Validación y consolidación.** Reproducir offline la receta90 conocida,
   mantener exacto el agarre, construir candidato74 integrado y comprobar
   modelo, alcance y liberación. Después ensayo supervisado por altura,
   cronometraje y regresión. Un solo branch mantenido; ramas anteriores como
   historia/rollback, sin borrarlas ni fusionarlas automáticamente.

Objetivo de comportamiento: cambiar la altura o el perfil sin cambiar el motor,
manteniendo explícita la validación de la nueva geometría. Aún no existe en la
rama actual un selector90 equivalente al74. No declarar validada una nueva
trayectoria74 integrada por haber funcionado su versión partida, ni reutilizar
la cualificación90 para otra altura.

La comparación justifica priorizar la consolidación del depósito sobre pequeños
ahorros de consola. No se fija todavía un tiempo final del nuevo ciclo:
el patrón90 ofrece una referencia real de integración, no una garantía para
otra geometría. Esta intervención **no implementa ni ejecuta la unificación**.

Evidencia privada:
`../Humanoide-vla-evidence/20261022T162518Z_TABLE90_74_COMPARISON/`:
comparison.json con las cinco tomas90, hashes y tabla; branch90/ con fuentes
de referencia; before/ y before.json con documentos/refs anteriores.


### Medición continua de la versión actual — 22-10-2026

**BOX-TABLE74-BASELINE-CONTINUOUS-20261022 — VERIFICADO/OBSERVADO.**
Nueva referencia de tiempo: **323,879012206 s — 5 min 23,9 s**, desde lanzar
el comando hasta su salida, reloj monotónico del PC. Un único ciclo completo,
sin reanudación ni interrupciones, en rama `74-jacob`, commit
`f18a2bfe9a43c71e6329bd4854297cdaa49ecc99`.
Se ejecutó el flujo actual, sin implementar las optimizaciones propuestas;
los **155 hashes de fuentes de control** del inventario inicial permanecen iguales.

Comando ejecutado una sola vez, después de confirmar las condiciones físicas
actuales y obtener CHECK_OK:

```bash
./scripts/optimistic_scenario1.sh --table-height-cm 74 \
  --box-alignment-attempts 7 --run \
  --evidence-dir /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20261022T160455Z_TABLE74_CURRENT_BASELINE/cycle
```

La captura externa sólo registra stdout y cambios del journal en el PC;
no añade consultas al robot ni modifica el código de control.
El preflight de lectura independiente duró14,031 s según su journal y queda
**fuera del total anterior**. El preflight interno del propio run sí está incluido.

#### Resultado y estado final registrado

- `cycle.json`: succeeded, measured_home, sin fase pendiente.
- HOME `2bf38328-f981-470c-a405-3a7ea8a04220`: SUCCEED/status4/state1101001.
- Dos muestras nuevas20D: MEASURED_HOME=1, velocidad0, máximo absoluto0,002493 rad.
- Operador confirma al terminar: depósito/HOME correctos, caja estable,
  abrazaderas libres y ninguna incidencia ni resistencia inesperada.
- Batería inicial62,4 %/62,3 %, final61,4 %/61,3 %; paros y cargador0 en
  las lecturas de inicio/final. Son estados registrados, no una garantía futura.
- Máximo permitido7 ajustes visuales; se ejecutó **uno**, de16,030 mm solicitados.
- Se mantuvieron la receta de mesa74, el agarre y todas las comprobaciones;
  ninguna optimización de la propuesta se aplicó para esta medición.

El resultado visual procede del operador. El script mantiene apoyo/pines
como supuestos de receta; no se transforman en mediciones sensoriales.

#### Tabla de referencia actual

| Operación | Total, s |
| --- | ---: |
| Ir a get1 | 28,273 |
| Activar visión | 1,537 |
| Alineación y recogida | 56,777 |
| Retirada con caja | 5,208 |
| Ir a put1 | 17,982 |
| Aproximación a mesa | 34,554 |
| Descenso previo14 cm | 34,055 |
| Apoyo5 cm | 34,124 |
| Desenganche4 cm | 25,533 |
| Apertura lateral | 24,761 |
| HOME y verificación final20D | 42,514 |
| Preparación, coordinación, confirmación asumida y cierres restantes | 18,561 |
| **Total del comando** | **323,879** |

Cada fase de depósito incluye instalación/preparación, consultas, ejecución,
registro y cierre. Las subetapas de recogida usan elapsed monotónico,
redondeado a milisegundos; los bloques posteriores usan ventanas PC entre
inicios de fase y final del journal. La fila restante es un saldo contable,
incluyendo la confirmación asumida de sujeción de0,009 s; no es una consulta
individual de18,561 s. No sumar otra vez los tiempos internos.

El journal del ciclo mide **323,798353316 s**. Las siete ventanas PC de fase,
más coordinación inicial, suman exactamente ese valor, residual0.
La diferencia respecto al comando completo corresponde al lanzamiento/cierre:
0,056924402 s antes del journal y0,023735151 s después, usando reloj PC de pared.
El total monotónico y el de pared del comando difieren menos de un microsegundo.
El observador capturó las siete entradas y sus siete terminaciones; se usan
los updated_ns del journal, no la hora posterior de observación.

Acciones SDK principales accepted→result, siempre con `detail.time_ns`
interno del mismo reloj Motion: get1 20,383 s; agarre30,770 s; retirada4,941 s;
put1 16,691 s; aproximación12,385 s; precontact12,389 s; apoyo11,799 s;
alivio2,397 s y apertura2,381 s. Son duraciones de acción, no una medida
independiente de inicio/fin físico. HOME sigue sin timestamps individuales de
aceptación/resultado; sólo su bloque total queda medido.

Las seis sesiones hasta ready suman83,885 s, ya incluidos en el total.
El intervalo atribuible por orden de código al descubrimiento SPS suma
45,986 s; es una atribución inferida, no cronómetro individual del descubrimiento.
Se conserva como dato para estudiar después, sin desactivar comprobaciones.
La consulta Docker siguió inconcluyente; no hubo rechazo del ciclo por ello.

Esta toma **sustituye la suma histórica329,415 s como referencia actual**.
Una repetición no mide variación estadística. Todavía no se atribuye ahorro a
la propuesta ni se cambia el objetivo: primero se conserva este resultado medido.

#### Evidencia, reproducción y efectos del run

Directorio: `../Humanoide-vla-evidence/20261022T160455Z_TABLE74_CURRENT_BASELINE/`.

- `before.json`: rama/commit, condiciones confirmadas y hashes de fuentes;
  `before/`: documentos anteriores a esta intervención.
- `preflight/`: consulta independiente CHECK_OK.
- `run_baseline.py`: invocación única del script actual, captura local y
  reloj monotónico; `command-result.json`, `console.log`,
  `console-timestamps.jsonl`, `cycle-observer.jsonl`.
- `cycle/`: evidencia original completa, journals y copias autenticadas
  de instalación/reversión antes del despacho.
- `operator-final-observation.json`: confirmación física final del operador.
- `analyze_baseline.py`, `export_operations.py`, `timing-analysis/`:
  análisis reproducible, summary.json, pc-phases.csv y operations.csv/JSON.
- `installation-index.json`: cinco bundles usados, rutas, recibos y backups.
  Aproximación ya instalada; se añadieron los otros cuatro bundles derivados.

Sólo para reproducir el análisis local, sin movimiento ni conexión:

```bash
python3 ../Humanoide-vla-evidence/20261022T160455Z_TABLE74_CURRENT_BASELINE/analyze_baseline.py \
  --evidence ../Humanoide-vla-evidence/20261022T160455Z_TABLE74_CURRENT_BASELINE/cycle \
  --observer ../Humanoide-vla-evidence/20261022T160455Z_TABLE74_CURRENT_BASELINE/cycle-observer.jsonl \
  --output ../Humanoide-vla-evidence/20261022T160455Z_TABLE74_CURRENT_BASELINE/timing-analysis
python3 ../Humanoide-vla-evidence/20261022T160455Z_TABLE74_CURRENT_BASELINE/export_operations.py
```

El run usó la aproximación existente acb7e54a…c4a9830 y añadió lowering
7a8638a5…72ff39 /0958506d…8b211b y liberación67533062…8b21cf /
a8fa9714…a88ee2. Destinos Motion: XML bajo config/local_table74_current,
local_table74_lower, local_table74_release en manipulation_task_manager y
YAML homólogos bajo config/meta_clamp en manipulation_meta_tasks. Los originales
WRC y librería se validaron por sus hashes, sin sustituirlos.
Las copias de reversión están en cada fase o carpeta *-staging y fuera del
robot antes de la acción; usar sus recibos con el instalador versionado si
procede retirar esa adaptación. No reutilizar journals consumidos ni restaurar
postura mediante archivos. El flujo sincronizó utars_nav_map y sus destinos
en el planificador, sin editar el mapa ni los puntos get1/put1. No se
reiniciaron servicios ni se cambió firmware, red, efectores, límites o velocidades.

**Referencia histórica anterior:** la sección siguiente explica la interrupción y
su reanudación. La referencia continua vigente es la medición anterior.


### Estudio del tiempo del último ciclo — 22-10-2026

**BOX-TABLE74-TIMING-20261022 — OBSERVADO/VERIFICADO offline.** Último ciclo
reconstruido a partir de dos sesiones reales:

- `20261022T150133Z_TABLE74_SUPERVISED_CYCLE_1280135`: recogida, traslado a put1
  y aproximación; interrumpida por diagnóstico después del SUCCEED nativo.
- `20261022T153114Z_TABLE74_CONTINUATION_1354458/continuation`: omite lo anterior
  y completa precontact, apoyo, desenganche, apertura y HOME, sin preguntas.

La segunda termina `status=succeeded`, `phase_boundary=measured_home`.
HOME goal `8ab357b5-3e0e-4f0d-aa57-70bd034c68a7`, SUCCEED/status4/1101001;
dos muestras nuevas 20D HOME, velocidad 0 y máximo 0,002493 rad. Es terminación
técnica observada en registros: apoyo/pines siguen siendo supuestos de receta,
sin una nueva inspección física del agente. El origen de aproximación está
**consumido**, manteniendo su journal original failed.

#### Tiempo total y alcance de la comparación

| Medida | Duración |
| --- | ---: |
| Sesión inicial | 169,570 s — 2 min49,6 s |
| Continuación hasta HOME | 159,844 s — 2 min39,8 s |
| **Suma de sesiones activas** | **329,415 s — 5 min29,4 s** |
| Parada de diagnóstico y preparación de continuación | 1611,541 s — 26 min51,5 s |
| Transcurrido desde el primer inicio hasta el final | 1940,955 s — 32 min21,0 s |

Horarios PC, Europe/Madrid: 17:01:33,580→17:04:23,150 y
17:31:14,691→17:33:54,535. «Activo» significa tiempo dentro de las sesiones,
incluyendo consultas y preparación; no movimiento continuo.
La parada incluye revisión, cambios y espera, ajenos al flujo normal.

**Limitación:** una sola toma partida, con una revisión del coordinador entre
sesiones. Los 5 min29,4 s no son un benchmark del ciclo actual sin interrupciones,
ni una media o medida de repetibilidad.

#### Tiempo por operación

SDK indica la **acción principal** aceptada→resultado: excluye otras acciones
auxiliares de esa fila y no mide exclusivamente movimiento físico.
Los tiempos internos ya están incluidos en el total; no sumarlos otra vez.
Los centímetros identifican el desplazamiento nominal de la tarea, sin una
medición independiente del recorrido físico en este análisis.

| Operación | Total, s | % activo | Acción SDK principal, s |
| --- | ---: | ---: | ---: |
| Ir a get1, incluida sincronización del planificador | 26,845 | 8,15 % | 18,682 |
| Activar visión | 1,628 | 0,49 % | — |
| Alineación y recogida | 59,319 | 18,01 % | 30,756 |
| Retirada con caja | 4,925 | 1,50 % | 4,631 |
| Ir a put1 | 16,951 | 5,15 % | 15,690 |
| Aproximación a mesa, incluidos preparación y cierre del fallo diagnóstico | 38,855 | 11,80 % | 12,367 |
| Descenso previo 14 cm | 32,897 | 9,99 % | 12,396 |
| Apoyo 5 cm | 34,610 | 10,51 % | 11,910 |
| Desenganche 4 cm | 24,418 | 7,41 % | 2,374 |
| Apertura lateral10 cm por lado | 24,784 | 7,52 % | 2,380 |
| HOME y comprobación final 20D | 43,102 | 13,08 % | Sin timestamps suficientes |
| Preparación, coordinación, confirmación asumida y cierres restantes | 21,081 | 6,40 % | — |
| **Total activo** | **329,415** | **100 %** | — |

Las cinco primeras filas usan `stage_complete.elapsed_s`, monotónico y
redondeado a milisegundos. Aproximación: primer→último evento Motion, sin
stage_complete por el fallo diagnóstico posterior. Las cinco últimas
operaciones físicas usan ventanas PC contiguas entre autorizaciones de receta
y fin de ciclo. La fila restante es **saldo contable**, no una consulta medida
de 21,081 s: incluye preflight inicial, coordinación/registro/transporte fuera
de las otras filas, cierre y confirmación de sujeción asumida de 0,010 s.
No acredita una verificación sensorial de caja. Las cifras mostradas pueden
diferir unas milésimas por redondeo.

#### Dónde se consume el tiempo

**Recogida:** de 59,319 s, unos 28,5 s preceden al envío del agarre y 30,756 s
corresponden a su acción SDK. Preparación previa:

| Bloque | Duración, s |
| --- | ---: |
| Salud y comprobación inicial de archivos | 5,002 |
| Bajar cabeza y primera medición estable | 8,450 |
| Una corrección de chasis y comprobar llegada | 6,552 |
| Salud posterior y segunda medición estable | 8,513 |

Hubo **un ajuste**, no siete: 20,403 mm solicitados; X observada de caja
0,776403→0,760238 m. El máximo configurado no indica correcciones ejecutadas.
Cabeza 2,302 s SDK y ajuste 5,988 s están incluidos arriba. Los recibos de
salud completa de esa preparación suman 10,080 s, también incluidos.

**Depósito:** precontact, apoyo, desenganche y apertura suman 116,709 s, con
29,059 s de acciones SDK. La diferencia 87,649 s incluye comprobaciones útiles,
conexiones, instalación/archivo, preparación y cierre: no es íntegramente
eliminable. Sólo desenganchar y abrir ocupan 49,202 s para 4,753 s de acciones.

Cada fase reconstruye una sesión. Primer evento→ready:
13,237 /14,572 /12,467 /12,660 s =**52,936 s**. Dentro aparece un intervalo
de 7,57–7,75 s por fase entre dependencias e inicio de salud,30,665 s acumulados.
Por orden del código corresponde al descubrimiento SPS: lista de acciones y
dos `action info` secuenciales. Es **INFERENCIA acotada**, no cronómetro
individual. El handshake inmediato sí reutilizó una entrada válida una vez
por fase; las comprobaciones rápidas de salud tardan milisegundos.

**HOME:** bloque completo 43,102 s. PC: 13,576 s de LIBRE a intent,
29,512 s de intent a finished y 0,015 s hasta fin del ciclo.
Las rondas Motion inmediata/posterior abarcan 12,680 /12,321 s. Cada una
incluye dos lecturas articulares secuenciales de unos 3 s; las seis consultas
de salud restantes corren en paralelo y no se suman como consecutivas.
Entre rondas hay 17,266 s con HOME y trabajo intermedio.
El stdout de `force_home.sh` no marca temporalmente aceptación/resultado:
**la duración exacta de la acción HOME no está disponible**.

**Navegación:** get1 suma 26,845 s, incluidos 5,557 s de sincronización del
planificador, con set_map 4,690 s; se realiza una vez en esta sesión.
Navegación principal 18,682 s. Put1 suma 16,951 s para 15,690 s de acción:
en este tramo ya predomina la navegación.

**Log Docker:** en la retoma tarda 0,065–0,071 s por consulta, diagnóstico
unavailable. Resultado→fin de etapa ≈0,075–0,093 s: no es el cuello de botella.
El rechazo anterior provocó la parada, pero no consumió por sí mismo
los 26 min51,5 s de intervención.

#### Prioridades propuestas, todavía sin implementar

1. **Compartir sesión durante el depósito.** Mantener clientes/monitor vivos
   y conservar entrada fresca, reposo, mapa/llegada, hashes, consumo durable
   y registro por fase. Los 52,936 s de arranques muestran el margen; no todos
   son prescindibles. Hipótesis inicial: **25–35 s de ahorro**, pendiente de
   implementación/medición. Sin cambiar agarre ni trayectorias 74.
2. **Agrupar adquisición HOME.** Un lector persistente puede proporcionar
   las mismas dos muestras nuevas 20D y seguridad actual sin otro proceso por
   lectura. Conservar preflight/postflight; ahorro sin medir.
3. **Evitar instalación duplicada de liberación.** `stage_release` comprueba,
   instala y archiva; `finish.main` vuelve a invocar install. Compartir recibo
   autenticado conservando identidad/hashes. Coste exacto no aislado.
4. **Mejorar repetibilidad de get1 y pila.** Entrar bien puede evitar ajuste
   y segunda adquisición; esos bloques suman ≈15,1 s en esta toma. Ahorro
   condicionado, conservando medición fresca inicial, no garantizado.
5. **Medir ciclos completos actuales comparables.** Separar primer arranque
   de siguientes; registrar duración por fase, consultas, instalación,
   descubrimiento y ajustes. Obtener media/mínimo/máximo de varias repeticiones.
   Marcar accepted/result de HOME antes de atribuirle duración física exacta.

Sesión compartida, descubrimiento e instalación se solapan: **no sumar sus
estimaciones**. La primera mejora debe reducir coordinación/arranque de
clientes. Cambiar duración, geometría o límites requiere otro estudio y
validación física. El antiguo preflight de aproximación repetido 25,989 s
pertenece a la revisión anterior; su coste no debe proyectarse sin medir al
ciclo actual, que ya usa quick_health y el handshake inmediato.

#### Reproducción y evidencia

Directorio privado externo al Git:
`../Humanoide-vla-evidence/20261022_TABLE74_TIMING_ANALYSIS/`.

- `analyze_cycle.py`: stdlib, sólo lectura local; verifica enlace entre
  sesiones, estados/objetivos/HOME, fuentes y conservación de tiempos.
- `summary.json`: totales, operaciones, porcentajes, límites y hashes.
- `operations.csv`: tabla importable en una hoja de cálculo.
- `pickup-approach.json`, `continuation-analysis.json`: detalle de intervalos,
  UUID/campos/líneas, rondas HOME y consultas sin doble conteo.
- `before/`, `before.json`: documentos anteriores y commit base.

Desde el repositorio, sin conexión al robot:

```bash
python3 ../Humanoide-vla-evidence/20261022_TABLE74_TIMING_ANALYSIS/analyze_cycle.py
```

No mtimes ni restas PC contra Motion: sus relojes absolutos difieren.
Cada duración usa un solo reloj; después se suman duraciones.
Verificado: enlace original→retoma, activo 329,414620375 s,
activo+pausa=extremo a extremo, filas=100 % y dos muestras HOME 20D válidas.
No se han modificado scripts de control, contenedores, parámetros o trayectorias,
ni conectado al robot durante el estudio.

### Continuación histórica de la toma1280135, ya completada

**Actualización posterior:** la retoma153114Z terminó hasta HOME y consumió
el origen. El comando siguiente se conserva como receta histórica: **no
repetirlo con ese origen**. Los pendientes inferiores describen el momento de
implementación, anterior al resultado analizado arriba.


**22-10-2026 — BOX-TABLE74-CONTINUE-LOG-FAILURE-20261022.** Entrada específica
para la aproximación que terminó correctamente y después quedó registrada
como fallida por `TABLE74_NATIVE_IDENTITY`. La caja sigue **SUJETA** según
el usuario. Esta continuación omite recogida, navegación y aproximación:
su primer movimiento es **precontact14 cm**, seguido de apoyo5 cm,
alivio4 cm, apertura10 cm por lado y HOME con medición20D. Usa la receta
guardada, sin nuevas preguntas.

`--recovery-confirmed` declara el estado **actual**: caja aún sujeta y estable,
con toda su base sobre la mesa74; misma postura y montaje desde la parada,
sin reinicio, movimiento manual u otro control; recorridos14+5 cm, alivio,
apertura y HOME despejados, cargador fuera, ambos paros libres, ruedas en
navegación, demás mandos detenidos y observador junto al paro. Si cambió
alguna condición, este origen no sirve para continuar. El flag no transforma
estos supuestos en una medida física ni omite comprobaciones técnicas.

Con esas condiciones comprobadas, el comando completo de continuación es:

```bash
./scripts/optimistic_scenario1.sh --continue-deposit --table-height-cm 74 \
  --after /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20261022T150133Z_TABLE74_SUPERVISED_CYCLE_1280135/approach/physical-run \
  --recovery-confirmed --run
```

Para inspección offline, sustituir `--recovery-confirmed --run` por `--plan`.
El plan es el modo predeterminado de esta entrada: requiere `--after`, pero
no lo lee, no conecta ni crea archivos. Para comprobar antes de mover,
sustituir sólo `--run` por `--check`, manteniendo `--recovery-confirmed`:
crea evidencia local y comprueba precontact sin instalar ni mover; puede
devolver55 si falta su tarea. No confundir ese resultado con permiso para
reiniciar el ciclo completo.

La entrada autentica los seis archivos originales, una única acción SDK
aceptada con terminal4/SUCCEED y el error diagnóstico **exacto posterior**,
además del cierre de sus workers inactivos. En un directorio nuevo añade un
recibo tipado `table74_log_only_recovery`, con hashes y
`current_physical_measurement=false`. El journal original **sigue failed**;
no se cambia a succeeded ni se borra ningún marcador consumido. Tras el
preflight actual correcto, el primer precontact consume el trial original
y su copia antes de armar: esa frontera no puede repetirse.

Se revalidan hashes, boot/contenedores, contexto, mapa/put1, salud, batería,
cargador y paros. Un reinicio o cambio de control/postura invalida la retoma;
no se reajustan límites para admitirlo. Fuentes:
[`entrada`](../../scripts/box_handling/scenario1_table74_continue.py) y
[`prueba de recuperación`](../../scripts/box_handling/scenario1_table74_log_recovery.py).
Preparación local, sin movimiento para crear esta entrada; **ensayo físico
PENDIENTE**. Backup/evidencia:
`../Humanoide-vla-evidence/20261022T152158Z_TABLE74_CONTINUE_AFTER_LOG_FAILURE/`.

**22-10-2026 — BOX-TABLE74-FERIA-COORDINATION-20261022: coordinación rápida
sin convertir los logs de Docker en un requisito de movimiento.** El intento
`20261022T150133Z_TABLE74_SUPERVISED_CYCLE_1280135` completó la aproximación:
goal `48339049-920e-4c9b-9762-7774f92c3621`, SUCCEED/status4/1101001,
12,367 s. Después se detuvo por `TABLE74_NATIVE_IDENTITY`. La consulta de
lectura identificó el problema del diagnóstico: Docker devolvía rc0 y sólo
77 bytes, `Error grabbing logs: invalid character '\x00' looking for beginning of value`,
sin la transacción nativa. No se repararon logs ni se reiniciaron servicios.

La auditoría de logs es ahora adicional: ausencia/formato no disponible
produce `verified=false` y diagnóstico `inconclusive`/`unavailable`, sin
inventar éxito. La continuación conserva el UUID y terminal SDK reales más
salud fresca. Un hallazgo positivo de fuerza/IK/fault, resultado fallido o
fin prematuro documentado **sigue bloqueando**, igual que una incompatibilidad
de configuración, contexto o pruebas históricas. La salida cruda acotada se
guarda antes de analizarla.

Las fases usan la salud fresca del monitor continuo (`quick_health`) como
`feriabarcelona`, evitando adquirir de nuevo toda la salud. Sólo se reutiliza
el handshake durante menos de2 s, con idéntico contexto, última acción y
monitor; la entrada de cada etapa se vuelve a comprobar. Se mantienen74 cm,
Z0,94,14+5 cm, alivio4 cm, apertura10 cm, recogida intacta y HOME20D; no se
copian las geometrías69,5/90 cm de otra rama. Sin nuevas preguntas ni retry.

**Estado comunicado: caja aún SUJETA.** No reiniciar el ciclo desde vacío ni
repetir la aproximación, enviar HOME, borrar `consumed` o reescribir journals
para retomar. Los comandos de inicio que siguen corresponden a un futuro
ciclo desde HOME; la continuación actual requiere su frontera específica.
Verificación: **383 pruebas correctas** de27 módulos de mesa74, runtime,
monitor de salud, reanudación, sesión y consola; plan offline y sintaxis correctos.
Esta corrección está comprobada localmente y sólo se han hecho consultas
remotas de lectura; **ensayo físico de la corrección PENDIENTE**.
Fuentes: [`recipe`](../../scripts/box_handling/scenario1_table74_recipe.py),
[`auditoría`](../../scripts/box_handling/scenario1_table74_native_completion.py)
y [`runner`](../../scripts/box_handling/scenario1_table74_trial_run.py).
Backup/evidencia: `../Humanoide-vla-evidence/20261022T150650Z_TABLE74_FERIA_COORDINATION/`.

**22-10-2026 — BOX-TABLE74-RECORDED-RECIPE-20261022: receta guardada y avance
sin preguntas al ejecutar el ciclo completo.** Por petición expresa del
usuario, `--table-height-cm 74 --run` utiliza ahora la receta de la toma
supervisada correcta `20261022T142922Z_TABLE74_SUPERVISED_CYCLE_1198976`.
La nueva automatización está implementada en PC y comprobada con pruebas
locales; **su ensayo físico sin preguntas sigue PENDIENTE**. La toma fuente
sí completó recogida, traslado, depósito, liberación y HOME medido.

Para inspeccionar la secuencia sin conectar ni crear una sesión:

```bash
./scripts/optimistic_scenario1.sh --table-height-cm 74 \
  --box-alignment-attempts 7 --plan
```

El comando que no incluye modo explícito sigue siendo **sólo check**, sin
movimiento ni instalación de tareas de depósito:

```bash
./scripts/optimistic_scenario1.sh --table-height-cm 74 \
  --box-alignment-attempts 7
```

Para ejecutar **un ciclo sin preguntas** desde HOME, comprobar antes las
condiciones actuales: mismas abrazaderas, caja de0,603×0,397×0,22 m y montaje
de mesa74 de la toma fuente; efectores vacíos, caja preparada, trayectorias
incluido HOME despejadas, cargador desconectado, paros liberados, ruedas en
navegación, otros mandos detenidos y persona observando junto al paro:

```bash
./scripts/optimistic_scenario1.sh --table-height-cm 74 \
  --box-alignment-attempts 7 --run
```

La receta conserva los movimientos probados: aproximación con Z nominal de
manos0,94 m, descenso14 cm, apoyo5 cm, alivio4 cm sin giro, apertura10 cm por
lado sin bajada y una única tarea HOME con comprobación posterior20D. **No
incluye settle** ni otra bajada automática. Los valores guardados son19 cm
después de aproximar,5 cm antes de apoyar,8 cm de holgura antes del alivio,
salida de pin necesaria2 cm y5 cm de holgura después del alivio.

Estos valores y los estados «apoyada», «pines libres» y «útiles vacíos» son
**supuestos de la receta para repetir el mismo montaje**, no observaciones
actuales ni medidas de sensores. La procedencia se registra como
`recorded_recipe_assumption`, con `current_physical_measurement=false`;
las referencias de liberación v3 mantienen falsas las confirmaciones del
operador actual. No se editan los journals fuente para convertirlos en
mediciones ni se reutiliza su checkpoint consumido. Cambiar caja, mesa,
efector, ubicación o geometría exige revisar el montaje y usar el modo
supervisado; la receta no detecta por sí sola todas esas diferencias.

Para recuperar las preguntas y las observaciones actuales por fase:

```bash
./scripts/optimistic_scenario1.sh --table-height-cm 74 \
  --box-alignment-attempts 7 --table74-supervised --run
```

Ese modo admite un único settle1 cm sólo si el operador comunica hueco1 cm
uniforme, sin ningún apoyo. Apoyo parcial o geometría diferente detienen el
avance; no se improvisa una nivelación ni se abre. El modo automático sigue
sin settle, reset, navegación de recuperación o reintentos de brazos.

Verificación de esta intervención: **1071 casos PASS** en la suite de escenario1
excluyendo el módulo histórico `test_scenario1_deposit_install` (23 casos;
17 errores de fixture reproducidos con archivos idénticos a HEAD anterior).
La nueva receta, la carga remota aislada, los errores sin avance y el modo
supervisado están incluidos en los casos correctos. La suite global no se
declara totalmente verde; no se ha cambiado ese instalador anterior.

### Qué se acelera y qué sigue comprobándose

Se eliminan cinco sesiones completas de `--check` que precedían a otro
`--run` con el mismo preflight; en la toma fuente sumaban **78,4 s**. Cada
runner conserva su preflight fresco al ejecutar. HOME mantiene una
comprobación inmediata completa antes del único goal y la medición posterior,
sin repetir además otra comprobación antes de una pregunta que ya no existe.
No se acortan duraciones de trayectorias ni se amplían tolerancias. El ahorro
total real de la nueva ruta, incluida su auditoría adicional, está pendiente
de medir;78,4 s es el coste medido de las sesiones retiradas.

Continúan las comprobaciones de contexto, dependencias, salud, reposo,
llegada/mapa/localización, cargador, batería, paros y supervisión continua de
los runners. Fuerza, límites y controles nativos quedan intactos. La nueva
auditoría adicional contrasta, cuando está disponible, el log nativo de la
**tarea exacta**, su duración y resultado. Rechaza `DectionForceCollision` y
otros fallos positivos aunque ROS devuelva SUCCEED. Un log ausente o de formato
inconcluyente se registra como tal y no sustituye el terminal real ni la salud
fresca; tampoco mide apoyo o pines libres. Un fallo de control, salud o prueba
auténtica detiene sin retry ni HOME de recuperación.

Esta entrada permite un solo ciclo y rechaza `--cycle` y `--wifi` antes de
conectar; las pausas parciales anteriores no cambian. Se usa Ethernet.
El perfil histórico de preparación mantiene
`deposit.compatibility=pending` para preservar checkpoints y sus hashes;
no despacha el depósito WRC original. Tampoco se reetiqueta la prueba
anterior con ajuste manual como validación de autonomía.
`--stop-after get1`, `grasp` o `put1` mantienen el comportamiento anterior;
`--finish-deposit` sigue permitiendo la liberación separada desde un origen
auténtico. No copiar referencias consumidas de las pruebas anteriores.

Se puede continuar desde un checkpoint limpio con caja sujeta de ESTA
selección74 (`verify_held`, retirada o llegada put1), sin repetir el agarre:
añadir `--resume /ruta/actual/checkpoint.json --box-state held --run` al
comando completo. No admite saltos de etapa ni recuperación de un estado
fallido/desconocido. El check de una retoma ya en put1 no exige HOME: consulta
la instalación de su aproximación y devuelve55 si falta, sin instalar ni
afirmar salud comprobada; `--run` instalará y hará el check real antes de mover.
Después de una fase de depósito, `cycle.json` es un resumen **no ejecutable**;
se conserva el journal de la última frontera para los runners específicos.
No pasarlo como si fuera un checkpoint de recogida.

### Toma supervisada fuente y verificación del cambio

**OBSERVADO/VERIFICADO:** el ciclo fuente1198976 terminó `status=succeeded`,
frontera `measured_home`, sin settle ni acción pendiente. Las respuestas
guardadas fueron HUECO19, HUECO5, APOYADA,8 cm/2 cm, PINES_LIBRES,5 cm,
LIBRE y HOME74. HOME goal `f3de6794-1497-496f-85d6-a06068f6a8bd` terminó
SUCCEED/status4/1101001 y `measured_home=true`. Son declaraciones físicas
del operador más evidencia técnica; no se elevan a medición de apoyo.
Fuente privada: `../Humanoide-vla-evidence/20261022T142922Z_TABLE74_SUPERVISED_CYCLE_1198976/`.

Receta reproducible v1:
[`scenario1_table74_recipe.py`](../../scripts/box_handling/scenario1_table74_recipe.py).
Incluye ID, hash del cycle fuente, valores y política sin retry/settle.
Backup, pruebas y evidencia de esta revisión:
`../Humanoide-vla-evidence/20261022T144742Z_TABLE74_RECORDED_RECIPE/`.
No se ha conectado ni movido el robot para habilitar esta nueva ruta.

**Registro histórico BOX-TABLE74-SUPERVISED-CYCLE-20261022:** antes de la toma
fuente se comprobaron407 casos locales y un check real de lectura, con
20D HOME inmóviles, batería72,7 %/72,5 %, cargador/paros0 y mapa correcto.
Su «ensayo integrado pendiente» queda superado por1198976, no por una
prueba física de la nueva automatización. Evidencia anterior:
`../Humanoide-vla-evidence/20261022T135743Z_TABLE74_SUPERVISED_CYCLE_INTEGRATION/`.
La utilidad HOME independiente conserva `--run` y confirmaciónTTY; sólo el
coordinador automático utiliza su política explícita de receta.

**Registro histórico22-10-2026 — BOX-TABLE74-FINISH-EXECUTED-20261022: liberación y HOME completados.**
Alivio4 cm y apertura10 cm por lado se ejecutaron una vez por fase con check
real correcto y SUCCEED/status4/1101001. Entre ambas, operador confirma
pines libres y holguras actuales; al finalizar confirma caja estable y
abrazaderas libres. Tras nueva confirmación específica del barrido de HOME,
una orden `force_home.sh` termina correcta; dos muestras20D muestran HOME=1,
velocidad0 y máximo absoluto0,002589 rad. Operador confirma HOME y caja estable.
No se repiten etapas ni se envía navegación. Fuentes anteriores de settle/
alivio consumidas; no retomar el open después de HOME. En aquella prueba hubo
ajuste manual previo y confirmaciones por fase: no acredita la automatización
posterior descrita arriba.
[Resultados, referencias y evidencia](DEPOSITO_WRC_ALTURA_100CM.md#cierre-real-del-depósito-y-home--22-10-2026).

## Continuar una liberación de mesa74 ya apoyada — 22-10-2026

**BOX-TABLE74-FINISH-20261022.** Nueva entrada exclusiva
`--finish-deposit --table-height-cm 74 --phase pin-relief|open --after DIR`.
Una fase por invocación: **alivio4 cm** (referencia v2, holgura mínima5 cm
antes de bajar) y después apertura lateral10 cm por lado,
con nueva declaración de pines libres. Plan offline; run instala aditivamente,
comprueba salud y exige `LIBERAR74`. No cambia la recogida ni activa el
depósito ordinario74 pendiente, navegación o HOME.

El cambio4 cm se ejecutó después en las tomas descritas arriba. Su preparación
local no afirmaba por sí sola una nueva holgura5 cm. El paquete v1 de3 cm queda para historia/rollback,
rechazado como nuevo despacho. La apertura mantiene su holgura actual≥4 cm,
Z0 y confirmación separada de pines libres.

Estado histórico anterior a la recarga y a las tomas completas: tras ajuste manual, operador declara apoyo plano y completo.
Alivio concreto **v1 de3 cm** instalado pero check bloqueado por batería17,6 %/18,6 %
frente al mínimo20 %; no se movió ni consumió el journal de settle.
Operador recargará y avisará. Revalidar postura/condiciones/contexto después,
sin reutilizar los4 cm de holgura tras un descenso ni derivar pines libres
del SUCCEED. [Comandos completos, evidencia y límites](DEPOSITO_WRC_ALTURA_100CM.md#finalización-por-fases-y-bloqueo-de-batería--22-10-2026).

## Historial anterior de depósito74

**22-10-2026 — BOX-TABLE74-PARTIAL-SUPPORT-20261022: detener antes de liberar.**
El operador aclara apoyo sólo en la esquina derecha alejada, con unos1cm de
hueco en las demás zonas. El log nativo demuestra `DectionForceCollision`:
variación vertical derecha10,5374N frente10N, tres superaciones; el árbol
lo devuelve como SUCCEED, sin acreditar apoyo completo ni completar el
centímetro. No se repitió la bajada solicitada después, ni se enviaron alivio,
apertura o HOME. Lectura posterior:20D habilitados/sin fault, velocidad0 y
delta consigna–posición máximo0,004203rad. No acredita seguridad mecánica.

La frontera sigue siendo `settle-run/trial.json`, sin consumir pero no apta
físicamente para liberar. Candidatos de alivio/apertura sólo en PC, sin
instalar; el perfil normal74 continúa pendiente. Antes de otra trayectoria
faltan geometría actual de contacto y una nivelación revisada/validada;
no deducir un pivote o corregir sólo un brazo a partir de un único contacto.
No cambiar umbrales ni referencias para forzar el descenso.
[Detalle, evidencia y reanudación](DEPOSITO_WRC_ALTURA_100CM.md).

## Settle1cm completado; apoyo y pines pendientes — 22-10-2026

**BOX-TABLE74-CURRENT-SETTLE-20261022.** Tras support, el operador comunica
1cm igual ambos lados, caja horizontal/estable y ninguna esquina apoyada.
Se ejecutó una sola fase adicional settle .01→0m: goal
`9565b30d-4753-4627-8238-aeb7a586de27`, SUCCEED/status4/state1101001,
etapa17,029s; check13,1mm/0,34°. Support trial consumido, nueva frontera
`settle-run/trial.json` todavía sin consumir, con support=false.
No repetir support, precontact, approach ni settle, ni reanudar el depósito
completo desde un checkpoint antiguo. La cadena histórica se limita a3
antecesores; no hay descenso nuevo desde settle.

Apoyo plano/completo y holguras/pines actuales aún requieren respuesta del
operador. Liberación sólo preparada en PC, sin instalar o ejecutar; no abrir
ni enviar HOME.24 pruebas focales settle PASS, total nuevo pendiente.
[Resultados y fuentes](DEPOSITO_WRC_ALTURA_100CM.md#descenso-residual-de-1-cm-después-del-support--22-10-2026).

## Descensos14cm y5cm completados; apoyo físico pendiente — 22-10-2026

**BOX-TABLE74-CURRENT-LOWERING-20261022.** El descenso precontact19→5cm
se ejecutó una sola vez: goal `3ea53b0c-d306-409d-8602-3f6fea005b16`,
SUCCEED/status4/state1101001, etapa18,060s; bundle6dc59fb3…d65cc.
El operador confirma después≈5cm en ambos lados, horizontal/estable y sin
contacto, con persona junto al paro. No equivale a apoyo; journal support=false.
El trial del approach queda consumido y la frontera actual es el trial limpio
de `precontact-run`, no el checkpoint862349 ni una nueva recogida.

Support5→0 es otro bundle aditivo9e662224…92746, instalado/cargado/probado:
check13,7mm/0,27°, una acción SUCCEED/status4/state1101001, goal
`a8b7e6b9-f578-4b37-b028-9e2b5e179819`, etapa17,626s. Precontact trial
queda consumido; support trial fue después consumido por settle, descrito
arriba. El runner usa `--after DIRECTORIO`
y valida la cadena histórica de dos fases, contexto y mediciones actuales;
consume el journal anterior al armar. No se reanuda el ciclo completo de
Optimistic ni se cambia el perfil74 pendiente. Conjunto125 pruebas PASS.

No repetir los comandos de approach/precontact ni el support ya ejecutado.
Journal `support-run/trial.json` mantiene `physical_support_confirmed=false`:
el operador aún debe confirmar apoyo plano/completo y holguras. Liberación
sólo en preparación, sin instalar; apertura y HOME no están incluidos.
[Recetas y evidencias](DEPOSITO_WRC_ALTURA_100CM.md#descenso-actual-de-14-cm-y-apoyo-separado--22-10-2026).

## Put1 alcanzado y aproximación separada a 74 cm — 22-10-2026

**BOX-TABLE74-CURRENT-APPROACH-20261022.** La retoma posterior al arreglo de
referencia ya fue ejecutada por el operador: diario/checkpoint
`20261022T105614Z_OPTIMISTIC_SCENARIO1_862349`, con `retreat` y
`navigate_put1` completos, held limpio y sin acción en curso. Las dos muestras
de llegada put1 son18,451/17,789mm y0,444/0,325°. No hubo depósito, apertura
o HOME. Los pendientes de retoma física en las secciones anteriores del
historial quedan superados por este resultado; no reutilizar807763 si ya se
consumió. La entrada de la siguiente fase es el nuevo origen862349.

El usuario pide adaptar asumiendo los mismos valores de feriabarcelona.
Se preparó y probó un candidato separado `approach_vendor_reference` de referencia
vendor45: Z nominal0,65+(0,74−0,45)=0,94m y sin el descenso final ni apertura.
Los20cm restantes eran hipótesis nominal. Instalación aditiva y check real
correctos; una única aproximación termina SUCCEED/status4/state1101001,
goal `80974a9d-f9b2-4322-a2d7-2db41f28766e`, etapa18,026s. El origen862349
queda byte intacto pero consumido. No repetir el comando de aproximación
ni la retoma anterior. No hubo descenso final, apoyo, apertura o HOME.

La lectura corregida del operador es **19cm**, iguales en ambos lados,
horizontal/estable, base entera sobre el tablero y sin contacto, paro u otro
mando. No equivale a apoyo: la caja sigue sujeta y el journal conserva
`physical_support_confirmed=false`. El siguiente tramo en preparación baja
nominalmente14cm para dejar5cm; instalación/check/ensayo PENDIENTES. Debe
continuar desde el journal exitoso de approach, no desde862349 consumido.
El apoyo5→0 sólo se considerará tras observar y medir ese nuevo resultado.

**No continuar con la reanudación completa de Optimistic desde put1:** el
perfil74 normal sigue pendiente y no se modifica para saltar el bloqueo.
La aproximación termina con caja aún sujeta; apoyo, desenganche, apertura y
HOME requieren decisiones posteriores según el resultado real. No se aplican
los1,10m/−31cm/5cm históricos sin nueva medición. No cambiar checkpoint,
evidencia de held o marcadores consumed para forzar la entrada.
[Diseño de la fase y estado vigente](DEPOSITO_WRC_ALTURA_100CM.md#aproximación-actual-a-74-cm-con-referencia-asumida--22-10-2026),
[ficha](../SYSTEM_CUSTOMIZATIONS.md#box-table74-current-approach-20261022).

## Referencia de retoma tras la alineación visual — 22-10-2026

**BOX-ALIGNED-PICKUP-RESUME-20261022. Corrección y check real de lectura
VERIFICADOS; retoma física PENDIENTE.** El origen 807763 terminó limpio tras
`grasp/verify_held`, con caja declarada held. La retoma 832193 se bloqueó al
comparar contra get1 nominal: 50,824 mm, aunque la pose medida estaba a ≈2,77 mm
de la referencia de mapa registrado al terminar la alineación previa al agarre.
No se amplía la tolerancia de 20 mm / 2°: se usa la referencia correspondiente a la
recogida que se pretende continuar. No se manda navegar hacia ese referencia ni
se modifica el punto get1 guardado.

El CLI deriva `resume-pickup-reference.json` del diario, checkpoint y contexto
del origen; el runtime vuelve a validarlo. Exige origen held limpio, alineación
coherente, UUID/request y terminales nativos correctos, perfil/contexto exactos
y ausencia de navegación posterior a la referencia o fallo antes del cierre
solicitado. Datos incompletos o contradictorios bloquean la retoma. Un origen
sin alineación visual conserva la comparación nominal. Las poses históricas
no sustituyen medidas nuevas de mapa/odom, salud, reposo y estado actuales;
`verify_held.source=assumed` permanece asumido.

Para esta secuencia se conserva el **origen 807763**, no el checkpoint fallido
832193. El comando de la sección siguiente mantiene `--stop-after put1`:
`retreat → navigate_put1`, sin repetir grasp, alineación, HOME o depósito.
Antes de mover, comprobar la caja realmente sujeta/estable y las condiciones
físicas actuales; inspeccionar con `--plan` y realizar `--check` antes de
`--run`. Si el origen está consumido o cambia contexto/estado, no editarlo
para forzar la entrada. Depósito de 74 cm sigue pendiente y bloqueado.

Validación: 98 pruebas focales PASS y `--check` real final con entrada a
2,2 mm / 0,26°, `RESUME_CHECK_OK`. Sólo consulta estado/mapa, no envía órdenes de movimiento ni altera el checkpoint
ni lo consume. El diario conserva los errores de lease de la terminación de
los workers después del cierre solicitado; no son un nuevo fallo de entrada.

Fuentes: helper puro `scripts/box_handling/resume_pickup_reference.py`, CLI y
runtime; backup/evidencia
`../Humanoide-vla-evidence/20261022T104831Z_ALIGNED_PICKUP_RESUME_FIX/`.
[Contrato de la referencia](BOX_AXIS_REPOSITION_20261002.md#referencia-de-retoma-held-después-de-alinear--22-10-2026),
[ficha de restauración](../SYSTEM_CUSTOMIZATIONS.md#box-aligned-pickup-resume-20261022).

## Retomar la recogida de 74 cm con caja sujeta — 22-10-2026

**BOX-01-TABLE74-HELD-RESUME-20261022. Plan local VERIFICADO; ejecución PENDIENTE.**
El checkpoint `20261022T103357Z_OPTIMISTIC_SCENARIO1_807763/checkpoint.json`
conserva `grasp/verify_held` completados y `box_state=held`, sin fallo ni acción
en curso. El operador informa recogida correcta y get1 anteriormente mal
situado respecto a las cajas; no se atribuye por ello la causa de cada fallo
anterior. No editar el checkpoint para convertir la evidencia asumida en medida.

Con caja aún sujeta, separada y estable, trayectorias libres, cargador fuera,
paros liberados, ruedas en navegación, otros mandos detenidos y persona junto
al paro, la retoma siguiente sólo retira y navega a put1:

```bash
./scripts/optimistic_scenario1.sh --table-height-cm 74 \
  --box-alignment-attempts 5 \
  --resume /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20261022T103357Z_OPTIMISTIC_SCENARIO1_807763/checkpoint.json \
  --box-state held --stop-after put1 --run
```

El plan comprobado usa entrada `retreat`, HOME no requerido y waypoint `get1`;
la referencia de entrada alineada se corrige como se indica arriba. No repite
agarre ni alineación. Para inspección local, sustituir `--run` por
`--plan`: no conecta ni consume el origen. La ejecución real vuelve a comprobar
contexto/boot, dependencias, estado y postura. No se ha ejecutado desde el agente.
No usar `--from-stage grasp` para volver sobre una recogida ya completada.
No hace falta `--recovery-confirmed` para este origen limpio.

El límite `--stop-after put1` es necesario: por defecto se solicita el ciclo
completo y el selector74 bloquea el depósito aún pendiente. Al llegar a put1
se conservará la caja sujeta; apoyo/desenganche/apertura74 requieren su propia
preparación. Rutas históricas sólo son utilizables mientras no estén consumidas
y el estado/contexto siga siendo válido.

**22-10-2026 — BOX-01-ALIGN-HEALTH-RETURN-20261022: corregido el `NoneType`
de la primera ejecución con alineación.** Se omitió retornar el informe de
`Runtime.health()` al trasladar el consumidor del donante. Se añade sólo
`return report` después de todas las validaciones. La prueba real se detuvo
tras activar visión, antes de bajar cabeza, corregir el chasis o enviar el
agarre; su checkpoint fallido/`unknown` se conserva. Las seis regresiones con
el método real y las 127 pruebas focales pasan. No se ha movido el robot para
esta corrección; ensayo físico del arreglo pendiente. Sintaxis e intentos
siguen iguales. [Causa, evidencia y uso](BOX_AXIS_REPOSITION_20261002.md#corrección-del-retorno-de-salud-tras-la-primera-prueba-real).

## 22-10-2026: aproximación visual configurable antes del único agarre

**BOX-01-VISUAL-ALIGN-PORT-20261022 — Implementado en PC; pruebas del cambio
correctas y errores globales previos separados; carga/ensayo físico PENDIENTES.** Port selectivo desde
`feriabarcelona@0cbc320` a esta rama; no importa sus depósitos ni su recuperación
automática tras falta de progreso. `--box-alignment-attempts N` acepta0..7,
por defecto7 en Optimistic; las otras entradas compartidas conservan0 salvo
selección explícita. **N son objetivos del chasis antes de un único agarre**, no
reintentos de brazos. Cero conserva la entrada original sin esta aproximación.

La fase exige brazos/torso HOME y abrazaderas vacías, baja sólo la cabeza con
la tarea vendor verificada y adquiere dos medidas frescas. CorrigeXY hacia el
margen interior20mm sin alterar gateSPS X[0,41;0,79],Y[−0,39;0,39],Z[0,01;1,49]m.
Conserva paso≤50mm, suma solicitada≤100mm, plazo120s y vigilancia4s sin progreso;
otro ajuste exige resultado válido, reposo, llegada≤12mm/2°, nueva visión,
asociación y mejora≥2mm si sigue fuera. Cancelación, resultado incierto o fallo
detienen; no se reinician workers ni se reintenta el agarre nativo.

La preparación nativa **posterior** sigue moviendo cabeza y ambos brazos antes
de pedir SPS. El adaptador compara sus capturas actuales con la referencia,
sin convertirla en pose autorizada: un rechazo posterior puede dejar otra vez
postura preparatoria. No usar medidas del ensayo fallido ni asumir HOME.
El antecedente de plegado/divergencia izquierda sigue sin causa resuelta;
preservar XML/YAML/fuerzas/SDK no demuestra corregido ese fallo.

```bash
# Local; sin conectar ni mover:
./scripts/optimistic_scenario1.sh --table-height-cm 74 \
  --box-alignment-attempts 3 --plan --stop-after grasp
# Consulta técnica; no prepara cabeza ni inicia detección/alineación:
./scripts/optimistic_scenario1.sh --table-height-cm 74 \
  --box-alignment-attempts 3 --check --stop-after grasp
```

Una futura ejecución usa los mismos argumentos sustituyendo `--plan` por
`--run`, únicamente después de recuperación específica, HOME medido y
condiciones físicas actuales. No ejecutar ahora desde el checkpoint fallido.
`box-alignment-policy.json` registra N/política; payload y retomas impresas
conservan el contador. No hay depósito74 activado ni ciclo completo permitido.
La consola muestra cabeza, intento/N, XYZ en cm, llegada y margen listo;
un margen listo no equivale a un agarre completado.
[Secuencia, procedencia, límites, fuentes y reversión](BOX_AXIS_REPOSITION_20261002.md).
Evidencia/backups: `../Humanoide-vla-evidence/20261022T080944Z_BOX_ALIGNMENT_ONLY_PORT/`;
suite global51 módulos/921 pruebas:904 pasan y17 errores previos del instalador
de depósito, reproducidos idénticos en copia aislada de`8107664`. Pruebas focales
del port correctas; otras2 pruebas nuevas de invariantes por bytes pasan después,
fuera de ese recuento. No se modifican instalador/configuración ni se presenta
la suite como completamente verde. Recibos `scenario1-regression-final-receipt.json`
y `baseline-deposit-installer-complete-receipt.json`; fixture de once fuentes y
test de invariantes versionados. Sin SSH ni movimiento en este port.

## 22-10-2026: recogida detenida en preparación; destino de 74 cm pendiente

**BOX-01-TABLE74-PICKUP-REJECT-20261022 — OBSERVADO/VERIFICADO, Europe/Madrid.**
En la rama `feat/scenario1-deposit-table-74cm`, base `c5e8de1`, el operador
confirma mesa de destino de **74 cm** y autoriza probar primero sólo la recogida.
El `--check --stop-after grasp` pasa. Un único `--run --stop-after grasp`
(09:47:24–09:48:09 CEST) termina con código **78**: después de preparar los
brazos, el guard de percepción rechaza la caja elegida en `base_link`:

- X **0,790884315 m**, máximo permitido **0,79 m**: exceso **0,884315 mm**.
- Y −0,036360267 m; Z 0,902236291 m. **Ese Z no es altura sobre el suelo.**
- Goal de recogida `1a7d9db7-8c6a-4913-bdff-16f9d9ae8a1f`, status6,
  `NoneException`; sólo `navigate_get1` y `enable_vision` constan completadas.

No comenzó la separación nativa ni su `bodyback`. Tampoco se ejecutaron
retirada, depósito o HOME. La preparación sí movió brazos y cabeza: la postura
final **no es HOME**. El operador confirma después caja totalmente apoyada,
abrazaderas vacías y sin contacto, y robot inmóvil. El checkpoint conserva
`box_state=unknown` y el fallo; esa confirmación no lo transforma en recogida
completada ni autoriza a repetir el ciclo desde esa postura.

La llegada a get1 registró `VSLAM_LOCATION_LOST`, aunque la acción terminó y
la llegada medida fue 7,4 mm / 0,45°. Se conserva ese aviso para diagnóstico.
Los errores de lease del cierre son posteriores; no sustituyen al rechazo de
posición como motivo de esta interrupción. No se amplió el límite de 79 cm.
La prueba tampoco repite la fase de separación del incidente del codo izquierdo
del 22-10; su causa sigue pendiente y el ensayo vacío de 2° no valida el agarre.

Evidencia privada completa, capturas pasivas de posición/consigna y respaldo:
`../Humanoide-vla-evidence/20261022T074315Z_TABLE74_PICKUP_TRIAL/`.
El preflight y la ejecución utilizaron los scripts versionados; durante la
ejecución se recargaron mapa/puntos en el planner, sin editar sus valores.
Los suscriptores de diagnóstico terminaron, sin instalar archivos en Motion.
La captura contiene 7.602 mensajes (4.596 estados articulares y 3.006 de
actuadores), sin valores no finitos ni errores de esquema; se conserva aparte
la línea INFO de arranque. Las últimas muestras muestran velocidades cero en
los 20 ejes, códigos de error cero y diferencia máxima posición/consigna de
0,002330 rad. Durante preparación la mayor diferencia capturada fue 0,021500
rad (yaw derecho), y 0,020482 rad en yaw izquierdo. Son muestras de esta
preparación, no una validación de la separación ni del fallo anterior.
Resumen y procedencia: `analysis/trace-summary.json`; confirmación del operador
separada en `analysis/operator-confirmation.json`. Los relojes PC/robot no están
sincronizados; el análisis conserva tiempos fuente y no los fusiona como uno.

La altura de la mesa no cambia este rechazo de **recogida**. El ejecutor de
esta revisión continúa utilizando el depósito WRC original. Los ensayos de
74 cm descritos abajo son **históricos**, con mediciones y journals de
septiembre; no acreditan el depósito desde esta recogida.

Referencia actual pendiente, preparación reproducible y punto de reanudación:
[Depósito de 74 cm: revisión del 22-10](DEPOSITO_WRC_ALTURA_100CM.md#revisión-del-22-10-2026-destino-de-74-cm-y-referencia-actual-pendiente).

### Selección explícita de 74 cm: preparación local

**BOX-01-TABLE74-PREPARATION-20261022 — Implementado en PC; sin activación
del depósito ni prueba física del selector.** Para revisar sin conectar:

```bash
./scripts/optimistic_scenario1.sh --table-height-cm 74 --plan
./scripts/optimistic_scenario1.sh --table-height-cm 74 --plan --stop-after grasp
```

El primer comando declara el depósito no ejecutable y las fases pendientes.
El segundo muestra únicamente `navigate_get1 → enable_vision → grasp → verify_held`.
Este selector no altera los movimientos de recogida. Una ejecución o check
limitados explícitamente a `get1`, `grasp` o `put1` pueden utilizar el perfil
operativo nuevo; incluir depósito/ciclo completo queda bloqueado localmente,
antes de SSH. El valor aceptado actualmente es sólo 74; `--profile` y
`--table-height-cm` no pueden combinarse. Sin selector se conserva el perfil
original: el nombre de la rama no selecciona mesa.

El perfil operativo `scripts/box_handling/scenario1_table74_preparation.json`
tiene ID propio y `deposit.compatibility=pending`. La intención queda ligada al
hash del perfil en el checkpoint. Una retoma debe conservar el selector y la
identidad originales; no se puede convertir un checkpoint anterior o fallido
en una recogida de este perfil. Las órdenes de retoma impresas conservan la
selección. El checkpoint fallido de hoy se deja intacto.

El **perfil de calibración** de `config/box_handling/scenario1_table74/` es
distinto del operativo del CLI: lo utiliza el preparador offline, no `--profile`
del ciclo. Las referencias de alturas siguen pendientes. No hay una tarea
nueva de depósito instalada, ni apertura o HOME de 74 cm validados. El siguiente
ensayo físico requiere resolver primero la postura y aproximación de recogida;
los comandos anteriores son sólo planes locales.

Verificación offline: **91 pruebas afines pasan**, incluidas 13 nuevas sobre
selección, bloqueo antes de SSH, despacho simulado hasta recogida y continuidad
de retomas. Los tres planes locales (74 completo, 74 hasta recogida y original)
terminan con código 0 y contenidos esperados. Sintaxis y `git diff --check`
correctos. Recibos en `table74-preparation-verification/` y `*-plan-receipt.json`
de la evidencia de esta intervención. Los archivos finales sin commit también
quedan respaldados en `final-worktree/`, con su manifiesto SHA256.

**30-09-2026 — BOX-01-TABLE74-PAUSE-01: apagado confirmado por el operador.**
«Ya apagado y todo asegurado y estable»: caja, brazos y cuerpo asegurados;
sin verificación física independiente del agente. Última prueba support_only
SUCCEED, pero caja inclinada: toda la base sobre mesa, contacto en una punta y
esquina alta a 2,8 cm. No apertura, desenganche de 3 cm ni HOME ejecutados.
El agente sólo consultó: observó reinicios recientes de hw/manipulación y
posterior timeout SSH en ambos hosts; no ordenó movimiento, paro ni apagado.
Relevo/consultas/backups: ../Humanoide-vla-evidence/20260930T183000Z_TABLE74_SHUTDOWN_PREP/.
Última ejecución: 20260930T182221Z_TABLE74_SUPPORT_TRIAL_2072686; journal de
aproximación consumido, soporte exitoso sin apoyo físico completo acreditado.
Mañana arrancar con paro pulsado y mantenerlo durante revisión física/técnica;
no liberar para HOME automático con caja encajada o apoyos externos. No repetir
ensayos ni borrar consumed; redescubrir contexto tras el reinicio.
[Estado, evidencia y punto de reanudación](DEPOSITO_WRC_ALTURA_100CM.md#pausa-para-apagado-caja-inclinada-y-desenganche-pendiente).

**30-09-2026 — BOX-01-TABLE74-SUPPORT-TRIAL-01: descenso de apoyo instalado.**
Tarea separada de 5 cm desde la aproximación exitosa y el hueco confirmado por
el operador; sin apertura, desenganche de 3 cm, HOME ni navegación. Dos archivos
aditivos Motion con controles WRC conservados; originales y aproximación intactos.
Referencia/bundle en config/box_handling/scenario1_table74/support_trial/.
--check real 182123Z pasa, put1=6,4 mm / 0,04°, journal previo sin consumir;
avisos de lease al cierre registrados. Carga/prueba física de apoyo PENDIENTES.
70 pruebas pasan. Runner --after verifica journal+eventos+contexto anterior, consume trial.json
antes de armar y registra support.json; no permite repetir ni produce checkpoint
ordinario. Backup remoto /var/tmp/cruzr-table74-trial/649c5325…e6655d1 y copia
externa ../Humanoide-vla-evidence/20260930T181234Z_TABLE74_SUPPORT_TRIAL/.
[Fuentes, ejecución, límites y rollback](DEPOSITO_WRC_ALTURA_100CM.md#continuación-separada-descenso-de-apoyo-de-5-cm).

**30-09-2026 — BOX-01-TABLE74-APPROACH-TRIAL-02: aproximación física completada.**
Operador ejecutó tarea independiente: única acción SUCCEED/status4/1101001,
12,407 s; etapa 17,347 s. Dos muestras posteriores inmóviles. Confirma hueco
actual aproximado de 5 cm sobre mesa74cm; la estimación por foto de 7–8 cm se descarta.
Caja aún sujeta, sin apoyo/liberación/HOME. Origen put1 consumido; contexto no
reutilizable, sin checkpoint ordinario. No repetir aproximación ni ciclo completo.
Evidencia 20260930T180539Z_TABLE74_APPROACH_TRIAL_2028660 y backup documental
review-before; originales/rollback conservados. Próximo tramo: apoyo nominal de 5 cm,
por tarea separada; después comprobar apoyo antes del desenganche de 3 cm.
[Resultado y evidencia](DEPOSITO_WRC_ALTURA_100CM.md#resultado-físico-de-la-aproximación-del-30-09-2026).

**30-09-2026 — BOX-01-TABLE74-APPROACH-TRIAL-01: aproximación instalada.**
Tarea independiente hasta base nominal a 79 cm (mesa 74 + margen 5), mediante
Z relativo −31 cm desde la medición aproximada de 1,10 m. Conserva movimientos
XY/torso y controles WRC; sin descenso final, apertura, liberación ni HOME.
Dos archivos nuevos inmutables en Motion; originales intactos. Instalación y
hashes verificados, carga/prueba física PENDIENTES. No integrada en ciclo normal.
Generador, instalador y runner específicos con 44 pruebas; exige checkpoint
limpio tras put1 y confirmación actual, consume origen antes de armar, sin retry
ni checkpoint ordinario reutilizable. Backup remoto /var/tmp/cruzr-table74-trial/
y copia externa en ../Humanoide-vla-evidence/20260930T175607Z_TABLE74_APPROACH_TRIAL/.
[Receta, dependencias, límites y rollback](DEPOSITO_WRC_ALTURA_100CM.md#ensayo-separado-de-aproximación-a-mesa-de-74-cm).

**30-09-2026 — BOX-01-STOP-PUT1-01: límite de ensayo implementado en PC.**
Se añade `--stop-after put1` al contrato y CLI. Desde el checkpoint limpio de
recogida173316Z planifica únicamente `retreat → navigate_put1`, deja
`box_state=held` y termina con `PUT1_ALCANZADO; caja sujeta; depósito no ejecutado`.
No se despachan depósito, HOME ni adaptadores de agarre en esa retoma. Se rechaza
combinarlo con `--cycle`. Los perfiles, TASKS y Runtime conservan la tarea WRC
original. **Una retoma genérica posterior sin límite ejecutaría ese original;
no es una entrada al depósito relativo de74cm.**

Receta de revisión sin movimiento ni consumo de checkpoint:

```bash
checkpoint_recogida=../Humanoide-vla-evidence/20260930T173316Z_OPTIMISTIC_SCENARIO1_1944108/checkpoint.json
./scripts/optimistic_scenario1.sh --plan --resume "$checkpoint_recogida" --stop-after put1
```

Para una prueba física de transporte, una vez comprobada de nuevo la carga
estable y los recorridos/destino/modo/paros/persona junto al paro, sustituir
`--plan` por `--run`; eso mueve hasta put1 y continúa sosteniendo la caja.
**No se ejecutó ese transporte en esta intervención.** Su finalidad es una
frontera determinista antes del depósito, sin depender de acertar Ctrl+C.

Fuentes PC: `scenario1_cli.py` y `scenario1_contract.py`, pruebas en
`test_scenario1_{navigation_only,resume,cycle_cli,contract}.py`.
VERIFICADO:73pruebas afines pasan (7,258s); plan con checkpoint real rc0,
etapas exactas retreat/navigate_put1, cero reintentos, SHA del origen intacto,
sin marcador consumed. `git diff --check` pasa. Carga en robot/ensayo físico
de esta nueva frontera PENDIENTES. No conexión ni cambio de configuración remota.

Respaldo previo (incluye trabajo sin commit) y versión final/SHA:
`../Humanoide-vla-evidence/20260930T174618Z_TABLE74_MEASURED_REFERENCE/`. Rollback: con ejecutor detenido,
comparar cada archivo con after-sha256.json y restaurar selectivamente desde
before/ si no hubo cambios posteriores. No borrar/rebajar checkpoints para
restablecer etapas ya consumidas; un checkpoint futuro detenido en put1 debe
conservarse aunque se retire la nueva opción. El original de depósito no cambia.

**30-09-2026 19:33 CEST — prueba de recogida con pausa completada.**
`--run --stop-after grasp` terminó con éxito técnico y checkpoint held/asumido;
no se ejecutó depósito. La variante74cm sigue sin activar; la referencia
geométrica y confirmación física final están pendientes. Evidencia:
`20260930T173316Z_OPTIMISTIC_SCENARIO1_1944108`. No retomar un ciclo desde vacío
con la caja sujeta; conservar el checkpoint de esta pausa.

**30-09-2026 — depósito mesa74cm: candidato local, todavía no activo.**
Existe una plantilla de revisión con descenso relativo final5cm y, después
del apoyo, otros3cm propuestos para desenganchar antes de separar lateralmente.
La apertura sin bajada se descartó tras confirmar pines bajo reborde;
liberación física pendiente. Faltan dos alturas absolutas derivadas de referencia
mano/caja; no se instalaron ni integraron archivos. Este ejecutor sigue
llamando a `wrc_cruzr/put_cruzr_wrc_low` con sus valores originales.
[Archivos guardados, cálculos y respaldo](DEPOSITO_WRC_ALTURA_100CM.md#mesa-horizontal-de-74-cm--candidato-local-del-30-09-2026).

## Un reintento de HOME tras aborto confirmado — 30-09-2026

**BOX-01-HOME-RETRY-01 — IMPLEMENTADO en PC; VERIFICADO offline, prueba física
PENDIENTE.** A petición del operador, el perfil `optimistic_v1`/`assume` permite
un segundo `cruzr/home` si el primero termina exactamente en
`MoveToGoalFailed`, código7104050 y status6. Son dos intentos como máximo por
ciclo; no se reintentan agarre, depósito o navegación por esta adaptación.
El estado de caja debe ser `released`, asumido tras el depósito en este perfil.

El cliente conserva el resultado fallido y exige una traza coherente con un
único UUID despachado, aceptado y terminado. Sólo en este caso retira ese goal
terminal y mantiene vivo el ejecutor. No convierte el aborto en éxito ni
reinicia un worker fallido. Antes del segundo envío vuelve a comprobar
contenedores, hashes, salud completa, acción ociosa y dos muestras inmóviles
posteriores al resultado. Mantiene paros, cargador, batería, actuadores,
heartbeat y lease vigentes. Un timeout, cancelación, resultado desconocido,
fallo de comunicación o comprobación fallida termina el flujo sin reintento.

El permiso se consume **antes de enviar** el segundo HOME y queda registrado
como `home_retry` en el checkpoint, con UUID del fallo y tiempos. Se conserva
en retomas y retrocesos de etapas. Si el PC cae antes de recibir esa reserva,
una retoma cuyo origen indique HOME en curso o fallido sin ese registro añade
`home_retry_blocked: true`: admite la recuperación HOME solicitada expresamente,
pero no otro reintento automático. Este bloqueo también se propaga en retomas
sucesivas. Una pausa limpia antes de iniciar HOME conserva su permiso; sólo un
nuevo ciclo completo comienza con presupuesto nuevo.

El segundo HOME usa la misma tarea v8 **completa**, incluidos sus desplazamientos
relativos iniciales; XML, tiempos, tolerancias y MetaMove no cambian. La salud
y el reposo medidos no certifican holgura geométrica desde cualquier postura.
No resuelve la causa interna del fallo del elevador descrito abajo. Si ese
segundo intento falla, el flujo se interrumpe y conserva estado indeterminado.
Si termina bien, sigue exigiendo `verify_home` medido antes de avanzar o pausar.
Ctrl+C mantiene su significado de terminar la etapa: durante HOME incluye su
posible reintento y la verificación final. La pérdida de conexión o una parada
del supervisor impiden iniciar el reintento. El primer HOME exitoso no añade
comprobaciones ni movimientos por este cambio.

Fuentes reproducibles: `scripts/optimistic_scenario1.sh` y
`scripts/box_handling/scenario1_{runtime,action_client,session,contract,resume,cli,console}.py`.
Destino: fuentes del PC; payload temporal en la siguiente ejecución del script.
No requiere instalar XML ni reiniciar servicios del robot. Compatible con el
protocolo actual v0.2.0 y HOMEv8 verificado en el diagnóstico; otros errores no
se admiten por semejanza de texto. La consola anuncia comprobación/reintento y
distingue un aborto recuperable de la salida definitiva del ejecutor.

Pruebas reproducibles, sin conexión ni movimiento:

```bash
python3 -B -m unittest scripts.box_handling.test_scenario1_home_retry_protocol \
  scripts.box_handling.test_scenario1_home_retry_runtime \
  scripts.box_handling.test_scenario1_home_retry_checkpoint \
  scripts.box_handling.test_scenario1_console \
  scripts.box_handling.test_scenario1_console_shutdown
```

Se reproduce offline la traza real del fallo `af60c1f3…`: ambos validadores
aceptan exclusivamente su aborto conocido para considerar el reintento.
Regresiones cubren UUID/resultados incoherentes, pérdida de lease, cancelación,
comprobaciones fallidas, segundo fallo, Ctrl+C, persistencia y retomas.
**732 pruebas pasan**, sin fallos ni errores, en23,136s. Resultados completos
en `tests-final.json` y `scenario1-tests-final.txt` de
`../Humanoide-vla-evidence/20260930T161503Z_OPTIMISTIC_HOME_RETRY/`.
El módulo `test_scenario1_deposit_install` se excluye por sus17errores previos
reproducidos también en HEAD durante la intervención de ciclos; no se altera.
Plan, sintaxis y payload (13 módulos/5 workers) se verifican localmente;
el plan muestra un permiso para ciclo nuevo y cero para HOME de retoma ambiguo.
Ejercicio final de presentación CLI registrado aparte en la evidencia.
Ejecución física PENDIENTE;
no se reanuda automáticamente el intento fallido que motivó esta adaptación.

**Respaldo y reversión:** `before/` y `before-sha256.json` de esa evidencia
guardan los archivos previos, incluidas ediciones sin commit. `after/` y
`after-sha256.json` identifican esta versión reproducible. Con el ejecutor
terminado, restaurar selectivamente esos ocho archivos de producción y sus
pruebas/documentación, preservando cambios posteriores; retirar las tres
pruebas nuevas `test_scenario1_home_retry_*.py` si se revierte todo el cambio.
No se revierte ningún archivo o estado del robot. Conservar checkpoints y
evidencias: el código anterior puede rechazar los nuevos campos; no borrarlos
para recuperar un permiso de reintento ni presentar el ciclo como completado.

## HOME abortado en el elevador — 30-09-2026

**BOX-01-HOME-FAIL-20260930 — VERIFICADO; diagnóstico de lectura, sin cambios
de control ni trayectoria.** Intento
`20260930T155848Z_OPTIMISTIC_SCENARIO1_1699304`: depósito y registro de liberación
completados; falla `home` (etapa9), antes de entrar en `verify_home` (etapa10).
No es el aviso de cierre de lectores descrito al final de este documento.

Una única acción `cruzr/home`, UUID
`af60c1f3-0a11-48b9-8982-dedf2fb1ed32`, devuelve
`MoveToGoalFailed/7104050`, status6, a16:00:36.038 UTC /18:00:36 CEST.
El reloj textual de Motion muestra01-10 00:00:36 (+08); distinguirlo del PC.
Los cuatro avisos de feedback no son cuatro reintentos.

Motion concreta el primer fallo: `lifter` recibió destino `[0,0,0]` para3,75s
a16:00:31.943 UTC; `component.cpp:288:IsReached` lo rechaza a16:00:35.707 UTC
con errores `[-0.242465,-0.000479369,0.302098]` rad, aproximadamente
−13,89°, −0,027° y17,31°. Cabeza/cintura y los ajustes iniciales de brazos
terminan; las fases finales de bajada/cierre de brazos no se ejecutan.
No fue timeout del cliente de60s: falló la comprobación nativa del tramo.

Los errores `Lease missing…` de navegación/planificador llegan16,8/58,2ms
después del resultado fallido. El runtime revoca la sesión tras el aborto y
los lectores ociosos salen; no explican el fallo del elevador. Se conserva
el checkpoint bloqueado (`failure.stage=home`, caja `unknown`) y no se inicia
otra vuelta. La consola conserva esta cascada en fallos reales; el filtro
anterior sólo reduce ruido en cierres limpios.

**Estado posterior medido**, 16:03:05–16:03:40 UTC: JointState fresco en dos
lecturas, elevador aproximadamente `[-0,239972,-0,000288,0,299510]` rad;
brazos aún abiertos/elevados, máximo articular1,753915rad. Los20actuadores están
habilitados (`0x1237`), error0, velocidad0, diferencia máxima consigna–posición
0,001980rad. Clasificación `MEASURED_HOME=0`. Paros0/0 y último objetivo HOME
en status6. Operador confirma inmóvil, caja apoyada/liberada, abrazaderas vacías
y sin contacto; no se infiere holgura de una nueva trayectoria.
La primera consulta de actuadores con QoS por defecto agotó7s; se descubrió un
writer BestEffort y la lectura con ese QoS funcionó. No fue pérdida demostrada
del publicador ni se cambió su configuración.

HOME sigue en v8, SHA `d9e9462792b41300d352604b53ea2a4890a9382e942321990708f6ded2e26ccb`;
MetaMove SHA `bfeab1c7a295b58cd96fddd20916fc3f7fe16bd8c8ad1e77720f48aad34ccc69`,
ambos releídos. Tres éxitos previos de hoy empleaban los mismos hashes de HOME,
depósito, apertura, retirada y SPS; HOME tardó15,335–15,389s. Sus eventos guardan
sólo máximos articulares antes de HOME, no el vector completo del elevador.
**PENDIENTE:** distinguir trayectoria/seguimiento/tiempo de llegada u otra causa
interna. El error final no demuestra por sí solo atasco, contacto, fault de
servo ni que aumentar el tiempo baste. La adaptación de voz no modifica esos
archivos ni emite movimientos.

Punto de continuación del diagnóstico, anterior a la petición de reintento
documentada arriba: revisar el primer tramo del elevador y su seguimiento
desde la postura medida antes de preparar recuperación. Omitir `verify_home`
no resolvería este aborto. No repetir el ciclo entero ni HOME automáticamente:
v8 contiene deltas relativos que ya se aplicaron parcialmente. Una futura
retoma requiere revisión de postura y recuperación explícita según la guía;
`verify_home` sin movimiento sólo corresponde si una nueva medida ya confirma
HOME, condición que aquí **no se cumple**. No modificar el checkpoint para
presentar este intento como completado.

Evidencia externa y copia del intento:
`../Humanoide-vla-evidence/20260930T160259Z_OPTIMISTIC_HOME_FAILED/`.
Archivos principales: `robot-app-logs.json`, `failed-attempt/events.jsonl`,
`current-posture-summary.json`, `home-current-hashes.json` y muestras originales.
Las consultas exactas quedan en sus campos `command`; el clasificador reproducible
es `scripts/lib/cruzr_home_posture_gate.py`. Quince pruebas existentes de consola,
cierre y sesiones, más simulación local de HOME fallido, confirman un solo envío
y bloqueo de retoma automática. No se cambiaron scripts ni se enviaron acciones,
cancelaciones, servicios de control, rearme o reinicios. Rollback sólo documental:
restaurar selectivamente `before/` preservando ediciones posteriores; ningún
archivo/estado del robot que revertir.

## Ciclos continuos y pausa entre etapas — 30-09-2026

**BOX-01-EXEC-OPTIMISTIC-CYCLE — IMPLEMENTADO en PC; comprobación offline,
ensayo físico PENDIENTE.** `--cycle` ejecuta ciclos completos en una sola sesión:
después de depósito y HOME medido, prepara un checkpoint nuevo y vuelve a get1.
No repite el preflight inicial, descubrimiento SPS, adquisición inicial de salud
ni recarga del planificador. Con el mapa sincronizado conserva los destinos
guardados en esa sesión y evita repetir `prepare_map` y la descarga HTTP del mapa.
El primer recorrido mantiene preparación y sincronización completas.

```bash
# Revisar sin conexión:
./scripts/optimistic_scenario1.sh --cycle --plan
# Ejecutar continuamente, con las condiciones físicas del flujo comprobadas:
./scripts/optimistic_scenario1.sh --cycle
# Continuar desde el checkpoint indicado al pausar:
./scripts/optimistic_scenario1.sh --cycle --resume /ruta/checkpoint.json
# Comprobar una retoma sin mover ni consumir su origen:
./scripts/optimistic_scenario1.sh --cycle --resume /ruta/checkpoint.json --check
```

`--cycle` implica ejecución; admite `--run` explícito. `--plan` y `--check`
siguen siendo de lectura. Sólo está disponible en la entrada optimista y no
se combina con `--stop-after get1/grasp`. Sin argumentos sigue siendo `--check`.
La próxima caja y el destino deben estar preparados para cada ciclo; este
perfil mantiene la suposición de sujeción/liberación tras éxito técnico.

Se conservan salud continua, paros, heartbeat, supervisión de acciones,
comprobaciones de postura/reposo, hashes, límites SPS y resultados del proveedor.
Antes de navegar se exige pose reciente, y después se comprueban mapa/estado
de navegación y llegada medida. HOME final continúa medido. Un mapa o sus
puntos editados requiere terminar la sesión y volver a iniciar: no se recargan
entre vueltas. Una reanudación en otro proceso realiza las comprobaciones de
contexto, estado y entrada correspondientes; un reinicio del robot o cambios
de mapa/dependencias siguen bloqueando un checkpoint antiguo.

**Ctrl+C solicita una pausa al terminar la etapa actual**, también en un
`--run` optimista de una sola vuelta. Mantiene conexión y heartbeat mientras
espera su resultado; repetir Ctrl+C no fuerza una cancelación. La etapa puede
contener varios movimientos internos de una tarea del proveedor. Ctrl+C no es
una parada de emergencia. Si la etapa falla, conserva el fallo y el estado
indeterminado; no lo convierte en una pausa limpia. La única excepción de
reintento es el aborto HOME confirmado y acotado descrito arriba.

| Etapa en curso al pulsar Ctrl+C | Siguiente etapa de la retoma limpia |
| --- | --- |
| Navegación a get1 | Activar visión |
| Activar visión | Agarre |
| Agarre / registro de sujeción | Retroceso |
| Retroceso | Navegación a put1 |
| Navegación a put1 | Depósito |
| Depósito / registro de liberación | HOME |
| HOME / comprobación HOME | get1 de la siguiente vuelta, con `--cycle` |

Después de agarre y depósito se cierran también `verify_held` y
`verify_released`, sin otro movimiento; después de HOME se completa
`verify_home`. Así la retoma no queda a mitad del registro de caja ni repite
la acción anterior. Si Ctrl+C llega entre etapas físicas no inicia la siguiente.
Durante el preflight termina las lecturas y sale sin armar; si era una retoma,
deja el origen sin consumir y conserva sus opciones explícitas de recuperación.

El programa imprime la orden de retoma y la ruta de `checkpoint.json`. Éste
siempre representa la posición vigente en la secuencia. `cycle-000001.json`,
etc., son históricos envueltos y no se aceptan como checkpoints de ejecución.
El cambio de vuelta desde un segmento reanudado elimina sus requisitos de
entrada anteriores, conservando el contexto y el planificador de la sesión.

La autorización de sesión de 15 minutos se renueva **sólo tras un ciclo completo
con HOME comprobado**, sin revivir una autorización vencida o un fallo. Los
adaptadores SPS leen esa renovación mediante un envoltorio temporal en memoria;
los archivos instalados y sus hashes no cambian. Se mantienen los límites de
tiempo de captura, acciones, heartbeat y lease de control. Los identificadores
de solicitudes secuenciales rechazan repeticiones sin guardar un historial
creciente ni cortar tras 256/4096 solicitudes. Al completar una vuelta se
retiran clientes de acciones que acumulan al menos 128 solicitudes para acotar
su historial nativo de UUID; se recrean al próximo uso, conservando salud,
adaptadores, mapa y puntos. No hay reconexión automática tras fallo.
La ejecución prolongada en el robot está pendiente de medir: el servidor SPS
del SDK conserva resultados históricos internamente. Esta adaptación no afirma
memoria constante de todo el SDK ni duración indefinida verificada.

Fuentes reproducibles: [CLI](../../scripts/box_handling/scenario1_cli.py),
[supervisor](../../scripts/box_handling/scenario1_runtime.py),
[adaptación de sesión SPS](../../scripts/box_handling/scenario1_cycle_lease.py),
[identidad de solicitudes](../../scripts/box_handling/scenario1_request_ids.py),
[cliente de acciones](../../scripts/box_handling/scenario1_action_client.py),
[lector de salud](../../scripts/box_handling/scenario1_health_worker.py) y wrapper.
Activación: próxima ejecución desde el PC; el código se transmite en memoria,
sin instalación persistente, reinicio o cambio del HOME automático del robot.

Pruebas: `test_scenario1_cycle_cli`, `test_scenario1_cycle_boundaries`,
`test_scenario1_cycle_runtime`, `test_scenario1_cycle_lease`,
`test_scenario1_cycle_signal` y `test_scenario1_continuous_sessions`, dentro de
`scripts.box_handling`. Incluyen Ctrl+C real enviado al grupo de procesos de
un simulador local: el transporte aislado conserva el heartbeat y termina la
etapa antes del cierre. No se conectó ni movió el robot durante este cambio.
Resultados completos en `tests.json` y `scenario1-tests.txt` de la evidencia.

Resultado final: **680 pruebas correctas**, sin errores, en 23,117 s; compilación
del payload y envoltorio SPS, `bash -n`, `--cycle --plan`, `--help` y
`git diff --check` correctos. Bundle calculado `bf145fa17e1116fc`, sin cambios.
La primera pasada amplia ejecutó 701 pruebas: 684 correctas y **17 errores
preexistentes** en `test_scenario1_deposit_install`. Se reprodujeron los mismos
17 en una copia aislada de `HEAD=fba2f75a1b7b66bf575528b8f108da8b5062ca96`:
el fixture mezcla referencias medidas con `calibration_mode=vendor_final_reference`.
No se modificó ese instalador ni sus fixtures; la pasada final excluye ese
módulo de 23 casos e incorpora dos regresiones nuevas de pausa/consola.
Evidencia de la pasada inicial en `all-initial-tests.json` /
`all-initial-scenario1-tests.txt` y comparación HEAD en `deposit-preexisting-audit/`.

Regresiones de esta intervención, sin robot:

```bash
python3 -B -m unittest scripts.box_handling.test_scenario1_cycle_cli \
  scripts.box_handling.test_scenario1_cycle_boundaries \
  scripts.box_handling.test_scenario1_cycle_runtime \
  scripts.box_handling.test_scenario1_cycle_lease \
  scripts.box_handling.test_scenario1_cycle_signal \
  scripts.box_handling.test_scenario1_continuous_sessions \
  scripts.box_handling.test_scenario1_console_shutdown
```

Backup, fuentes finales y SHA256:
`../Humanoide-vla-evidence/20260930T145400Z_OPTIMISTIC_CYCLE/`.
Rollback: con el ejecutor terminado, restaurar selectivamente desde `before/`
los archivos PC indicados, preservando cualquier edición posterior; retirar
los módulos nuevos de ciclo/solicitudes sólo después de retirar sus referencias.
No usar un reset del repositorio ni restaurar checkpoints o estado transitorio
del robot. Sin `--cycle` se mantiene una sola vuelta, pero eso no revierte la
nueva semántica Ctrl+C ni la presentación de cierre descrita al final.

**Actualización 29-09-2026:** la consola muestra XYZ, rango y margen/exceso tanto
de cajas válidas como rechazadas durante la recogida. Las válidas usan la segunda
captura; las rechazadas, la pose real que comprobó el gate, sin alterar su fallo.
No añade capturas/esperas de sensores ni modifica el paquete SPS o sus límites.
[Formato, verificación y reversión](FORCE_IMPROVED_SCENARIO1.md#medidas-de-caja-en-consola--29-09-2026).

**28-09-2026, Europe/Madrid — BOX-01-EXEC-OPTIMISTIC. Implementado en el PC;
VERIFICADO offline y en lectura. Ensayo físico PENDIENTE.**
Entrada: [`optimistic_scenario1.sh`](../../scripts/optimistic_scenario1.sh).
Usa `policy=assume` y `execution_profile=optimistic_v1`, conserva la geometría
y las tareas de [improved](FORCE_IMPROVED_SCENARIO1.md). No mide si la caja quedó
sujeta o liberada: registra esa condición como **asumida** tras éxito técnico.
Un resultado terminal sin error no demuestra presencia, apoyo ni liberación.

## Qué cambia

El lector nativo mantiene muestras en `live-health.json`; cada transición valida
esos datos sin iniciar otra adquisición completa de todas las señales. No guarda
un permiso reutilizable de «todo correcto». Un dato inválido, caducado, un fallo
o la desaparición de una fuente impiden continuar; un fallo detectado queda
retenido durante la sesión aunque después llegue una muestra correcta.

| Punto del flujo | Comprobación vigente |
| --- | --- |
| Inicio, entrada de reanudación y HOME final | Adquisición completa, igual que el perfil normal; HOME medido cuando corresponde |
| Entre etapas físicas | Descubrimiento de contenedores y hashes, instantánea continua válida, acción libre y reposo articular |
| Después de una acción | Dos muestras articulares con sellos crecientes, fuente y recepción posteriores a su resultado |
| Durante la acción | Salud continua, heartbeat, lease y supervisión del cliente; el movimiento articular esperado no se confunde con reposo |
| `verify_held` / `verify_released` | Registro de suposición, sin ventanas FT ni confirmación presencial |

Se conservan paros, estado de servo, cargador, carga de ambas baterías ≥20 %,
actuadores habilitados y sin fault, cobertura corporal 20D y estado del
controlador. La recepción de paro/servo puede tener edad ≤5 s, acorde con la
cadencia observada de sus canales; cargador, batería, controlador y actuadores
mantienen ≤2 s. También se comprueba la edad de la fuente articular. El archivo
debe haberse actualizado hace ≤1 s, usando reloj de pared y monotónico.
`receipt_ages` conserva edades reales y límites aplicados; no rejuvenece señales.
El estado de acción conserva su
QoS retenido: no se presenta como un mensaje periódico nuevo cada dos segundos.
Entre etapas debe indicar acción libre. Se exige una fuente por canal de salud
y un servicio de controlador; una fuente duplicada o perdida provoca fallo.

La escritura de la instantánea es atómica, con intervalo objetivo de 0,05 s
(hasta 20 Hz, sujeto a planificación); se consulta
el controlador aproximadamente cada segundo. Los duplicados articulares idénticos
no renuevan su edad; conflictos y regresiones fallan. El watchdog comprueba salud
y renueva el lease; un fallo revoca su renovación y activa el cierre existente.
La cancelación solicita sólo el UUID propio y no demuestra parada física.

La frontera puede esperar **hasta 0,5 s** para reunir las dos muestras posteriores
al resultado y confirmar reposo/consigna. Si no lo consigue, falla sin enviar
la etapa siguiente. Un fault o dato caducado no usa esa espera para quedar
dispensado. El descubrimiento y los hashes siguen ejecutándose; su coste previo
era del orden de 0,2 s, no un tiempo garantizado. No hay ahorro total medido de
este perfil ni un objetivo garantizado de cinco segundos entre etapas.

Navegación, llegada 2 cm/2° en get1 y 5 cm/3° en put1, correcciones supervisadas,
percepción SPS y estabilidad de sus dos capturas no cambian. Tampoco cambian
el [selector y límite XYZ](FRONT_BOX_DEPTH_GATE_20260928.md) del paquete instalado
`bf145fa17e1116fc`: una selección fuera de límites falla sin escoger otra caja.
Los bloqueos, plazos, resultado de aplicación, checkpoints y HOME medido siguen
vigentes. Este perfil reduce esperas de adquisición entre etapas; no elimina
las verificaciones bloqueantes ni convierte FT sin cualificar en evidencia.

## Uso y reanudación

```bash
# Plan local, sin conectar:
./scripts/optimistic_scenario1.sh --plan
# Sin argumentos equivale a --check; consulta, sin movimiento:
./scripts/optimistic_scenario1.sh --check
# Ejecución sin preguntas, tras comprobar las condiciones físicas actuales:
./scripts/optimistic_scenario1.sh --run
# Pausa tras el agarre, con sujeción asumida:
./scripts/optimistic_scenario1.sh --run --stop-after grasp
# Revisar una continuación sin mover ni consumir el origen:
./scripts/optimistic_scenario1.sh --resume /ruta/checkpoint.json --check
# Continuar ese checkpoint con el mismo perfil:
./scripts/optimistic_scenario1.sh --resume /ruta/checkpoint.json
```

`--resume` sin `--check`/`--plan` autoriza ejecución; por sí solo no es diagnóstico.
Tras fallo, interrupción o salto se mantienen `--from-stage`, `--box-state` y
`--recovery-confirmed`, además de las condiciones de entrada documentadas en
[reanudación por etapa](FORCE_IMPROVED_SCENARIO1.md#reanudación-por-etapa--28-09-2026).
Se debe usar siempre esta misma entrada para checkpoints optimistas.

Los checkpoints incluyen `execution_profile=optimistic_v1`; el contexto remoto
lo fija también. Los antiguos sin campo significan `standard_v1`. No se permite
pasar de uno a otro, ni siquiera con `--recovery-confirmed`; el contrato rechaza
el cruce antes de SSH. No editar el campo, el origen ni su marcador de consumo.
`policy=assume` y perfil de ejecución son identidades distintas: compartir una
política no hace intercambiables las reanudaciones. `--verbose` conserva la
consola técnica; `events.jsonl` siempre mantiene el detalle completo.

## Fuentes, verificación y reversión

Fuentes: [CLI](../../scripts/box_handling/scenario1_cli.py),
[supervisor](../../scripts/box_handling/scenario1_runtime.py),
[lector nativo](../../scripts/box_handling/scenario1_health_worker.py),
[validador continuo](../../scripts/box_handling/scenario1_live_health.py),
[contrato](../../scripts/box_handling/scenario1_contract.py) y
[reanudación](../../scripts/box_handling/scenario1_resume.py).
La fuente PC se transmite en memoria al iniciar; sólo crea procesos y evidencia
temporales de sesión. No instala archivos persistentes en el robot, modifica
autoarranque, reinicia servicios ni sustituye el paquete SPS instalado.

Pruebas reproducibles sin robot:

```bash
python3 -B -m unittest scripts.box_handling.test_scenario1_execution_profile \
  scripts.box_handling.test_scenario1_live_health \
  scripts.box_handling.test_scenario1_optimistic
bash -n scripts/optimistic_scenario1.sh
./scripts/optimistic_scenario1.sh --plan
```

Suite final: **583 pruebas correctas**, sin fallos ni errores, en 7,176 s
(`tests.json`), incluidas las regresiones de permisos y caducidad por canal.
El contrato y la reanudación incluyen 14 pruebas nuevas de identidad.

Medición pasiva de **16,09 s**, sin acciones (`cadence-result.json`): paro y servo,
4 mensajes cada uno, intervalos 4,4889–4,4920 s; cargador y batería, 64 mensajes
cada uno, media ≈0,253 s; actuadores, 801 mensajes, media ≈0,020 s; estado de
acción, un mensaje retenido. Justifica el límite de 5 s sólo para paro/servo;
no modifica el paro físico ni ignora una activación/fault cuando se recibe.
Inicio, reanudación y HOME final conservan la adquisición completa de datos nuevos.

Los dos primeros `--check` terminaron con código 78, sin solicitar movimiento:
`robot-check/` y `check-console.log` conservan el fallo de acceso al archivo
creado por root con 0600; se corrigió a 0644 dentro de la sesión privada 0700.
`robot-check-benchmark/` y `check-benchmark-console.log` conservan el rechazo
por edad de paro >2 s, previo a medir y ajustar su cadencia. No se presentan
como comprobaciones satisfactorias.

Tercera comprobación, `--check --benchmark-checks 1`: **código 0, CHECK_OK**,
HOME 20D medido al inicio y en la ronda adicional. No se armó ni ejecutó ninguna
etapa; las consultas de navegación fueron `get_map` / `check_state`, de lectura.
Evidencia: `robot-check-final/events.jsonl`, `check-final-console.log` y
`check-final-result.json`. Tiempos medidos con el robot en reposo:

| Consulta | Tiempo |
| --- | ---: |
| Salud completa inicial | 4,414627 s |
| Salud completa en la ronda adicional | 2,491728 s |
| Validación de salud continua en esa ronda | 0,003216 s |
| Descubrimiento de contenedores, conservado | 0,080831 s |
| Comprobación de hashes, conservada | 0,145992 s |

La comparación mide lecturas en reposo, no una transición posterior a movimiento
ni el ahorro de un ciclo completo. En el cierre, después de `ready`, la revocación
deliberada de leases produjo mensajes de lease vencido/stop y salidas 2/78 de los
trabajadores; el supervisor terminó con 0. Queda pendiente mejorar esos mensajes
de cierre: no se describe la ejecución como libre de diagnósticos de error.

Evidencia, pruebas y backup:
`../Humanoide-vla-evidence/20260928T155443Z_OPTIMISTIC_SCENARIO1/`.
Para revertir, retirar la entrada nueva y restaurar selectivamente CLI, runtime,
lector de salud, contrato y reanudación desde `before/`; retirar después el
validador nuevo y sus pruebas si ya no tienen referencias. Preservar cambios
posteriores, evidencia y checkpoints; no restaurar estados de control ni deshacer
SPS `bf145fa17e1116fc`. Actualizar esta ficha y el índice global al revertir.

## HOME completado y mensajes de cierre — 30-09-2026

**BOX-01-CLOSE-CONSOLE — VERIFICADO offline, 30-09-2026 CEST.** El operador
informa de errores al finalizar pese a llegar físicamente a HOME. En los
**22 ciclos completos del 30-09 conservados en el PC**, `verify_home` terminó
correctamente; no se ha localizado un rechazo de esa etapa en esos registros.
Después aparecen errores de lease de los ejecutores sin petición activa.
Eso permite explicar esos mensajes concretos; no demuestra que cualquier
error de HOME de otra sesión sea un falso rechazo.

Ejemplo: `../Humanoide-vla-evidence/20260930T093725Z_OPTIMISTIC_SCENARIO1_661061/`.
Sus dos muestras finales tienen `MEASURED_HOME=1`, máximo absoluto 20D
`0,002972 rad`, máximo de brazos `0,000959 rad` y velocidad cero. `verify_home`
queda completado en el checkpoint, sin fallo, a `1790761139408995474 ns`.
A continuación, los clientes de navegación, planificación y Motion emiten
`Lease missing, invalid or expired` con `request_id=null` y `goal_id=null`,
y el lector de salud emite `Health worker lease expired or stop requested`.
La causa del orden es el cierre del supervisor: revoca deliberadamente el lease
antes de esperar la salida de los procesos. La consola anterior presentaba esas
salidas esperadas como `ERROR`. Las verificaciones HOME completas de ese día
duraron entre `0,506` y `4,638 s`.

La corrección **sólo cambia la presentación en el PC**. Tras recibir el evento
explícito `session_finishing` con motivo `requested`, la consola indica cierre
solicitado. Reclasifica únicamente esos motivos exactos de clientes inactivos
y su correspondiente código de salida esperado (`2`, o `78` para salud).
Un error previo al cierre, una petición/UUID activa, otro motivo, una cancelación
o un estado final desconocido sigue visible. `events.jsonl` y `--verbose`
conservan todos los eventos originales. No se omite ni se da por superada la
medición de HOME, y no cambian los límites de postura ni el freno.

Fuentes: [consola](../../scripts/box_handling/scenario1_console.py),
[supervisor](../../scripts/box_handling/scenario1_runtime.py) y
[pruebas de cierre](../../scripts/box_handling/test_scenario1_console_shutdown.py).
Activación: próxima ejecución con las fuentes PC actualizadas; no requiere
instalar ni reiniciar servicios del robot. **45 pruebas de consola pasan**,
incluidas nueve nuevas de cierre; no se conectó al robot ni se repitió el ciclo.
La comprobación de esta presentación en una nueva ejecución real queda
**PENDIENTE**.

Evidencia: `../Humanoide-vla-evidence/20260930T145400Z_OPTIMISTIC_CYCLE/`,
archivos `home-shutdown-audit.json` (sesiones, hashes y medidas originales) y
`console-shutdown-tests.txt`. Respaldo previo de consola en
`before/scripts/box_handling/scenario1_console.py` del mismo directorio;
copia adicional previa, con SHA256, en
`../Humanoide-vla-evidence/20260930T145803Z_SCENARIO1_CLOSE_PRESENTATION/`.
Rollback de esta presentación: restaurar selectivamente ese archivo previo
o retirar únicamente el reconocimiento `session_finishing` y
`expected_idle_close`, preservando el resto de cambios posteriores. Los logs
originales y los checkpoints no se modifican ni se restauran al revertir.
