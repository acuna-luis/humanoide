# Escenario 1 con supervisión continua

## Ciclo completo supervisado para mesa de 74 cm

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
barrera automática exige además el log nativo acotado de la **tarea exacta**,
su duración y resultado; rechaza `DectionForceCollision`, otros fallos o una
transacción incompleta aunque ROS devuelva SUCCEED. Ante fallo o evidencia
incierta detiene el ciclo, sin apertura siguiente, retry ni HOME de
recuperación. Un log nativo normal tampoco mide apoyo o pines libres.

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
