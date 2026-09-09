# Revisión offline de transferencia entre mesas — 09-09-2026

**VERIFICADO en software; PENDIENTE prueba física.** Trabajo realizado por petición
del propietario mientras el robot estaba desconectado. No se ejecutaron SSH,
ROS, consultas de red, instalación remota ni movimiento. Los tests ejecutan
copias del orquestador con todos sus hijos sustituidos por procesos simulados.

## Problemas corregidos

| Hallazgo | Resultado de la corrección |
| --- | --- |
| `restore_cargo_profile` podía devolver éxito tras un fallo porque se invocaba dentro de `||` y después borraba la marca de perfil activo. | Propaga el fallo, conserva la marca, bloquea aproximación/depósito y vuelve a intentar **sólo restauración** al salir. Un fallo de limpieza también produce salida no cero. |
| El reintento por `START_ONOBSTACLE` añadía 0,50 m de retroceso y cambiaba el destino desde el punto a 1,08 m detrás hasta el propio MESA2_PRE. | Un único intento al destino previsto; ante bloqueo se restaura percepción y se interrumpe. No se añade movimiento ni cambia destino. |
| `--stage-held` ejecutaba aproximación gruesa aunque anunciaba que sólo navegaba y medía el tag. | Termina a 1,08 m detrás del waypoint, verifica agarre y visibilidad; aproximación y depósito pertenecen a `--resume-held` o al tramo final de `--run`. |
| Cuatro verificaciones de agarre y dos lecturas de tag redundantes en el padre. | Se conservan las verificaciones dentro de los alineadores y del depósito. El flujo normal del padre baja de 18 a 12 invocaciones; no equivale a una reducción medida de tiempo del 33 %. |
| Caché fluida de 180 s no ligada al estado actual completo, y marcas de preflight heredables del entorno. | Se retira esa caché del orquestador y se eliminan las marcas heredadas. Cada invocación comprueba de nuevo; navegación con carga revalida mapa y salud. |
| `--check` y navegación podían cargar/relocalizar mapa, incluso con una caja sujeta; la relocalización puede mover la cabeza. | En contexto `table-transfer`, sólo se acepta mapa activo, localización lista y tipo/instancia verificados. No se carga, relocaliza ni escribe caché de preparación. Preparar mapa por separado. |
| `--fast` omitía salud antes de acciones de brazos y podía convertir un `--check --fast` en un chequeo incompleto. | Check, preparación de cabeza, agarre, verificación de agarre, depósito y HOME interno conservan el preflight canónico fresco. |
| Paros, batería y cargador se consultaban secuencialmente. | Cuatro lecturas independientes en paralelo; se espera a todas y cualquier fallo impide continuar. Mínimo de ambas baterías sigue siendo 20 %. Valores ausentes/no finitos/fuera de rango se rechazan. |
| Una lista vacía/incompleta de actuadores o ciertos NaN podían atravesar el verificador anterior. | Se reutiliza el validador estricto 20D de HOME, ejecutándolo en memoria remota; sin instalar archivos. Exige campos, IDs, habilitación, velocidades y consignas válidos. No exige postura HOME para sujetar una caja. |
| Un agarre anterior a un reinicio de contenedor, o seguido de una tarea no contemplada, podía seguir pareciendo válido. | Colector limitado a registros posteriores al arranque del contenedor, última tarea de agarre, MetaClamp SUCCESS y árbol completado; rechaza tareas posteriores, cancelación, fallos y medidas no finitas. Fallos terminales se reportan sin consumir los cinco intentos de espera. |
| Un depósito fallido se describía como caja todavía sujeta; un HOME fallido sugería repetir recuperación, pudiendo duplicar retroceso. | Se informa incertidumbre en agarre/depósito. Tras recuperación interrumpida se advierte que puede haber retrocedido ya; comprobar registro/estado antes de repetir. |
| Perfil de carga remanente de otra ejecución podía pasar preflight y seguir activo durante recogida. | Se exige perfil `disabled`; una transacción anterior se restaura explícitamente antes de reanudar. |
| Modos incompatibles se sobrescribían silenciosamente; faltaban salidas explícitas por señal. | Se rechaza combinar modos; INT/TERM/HUP finalizan con estado no cero y limpieza. |

## Registros y uso

Se conserva la interfaz principal:

```bash
export CRUZR_MAP_NAME=MESAS2
export CRUZR_MAP_TYPE=uslam
./scripts/cruzr_blue_workbin_table_transfer.sh --check
./scripts/cruzr_blue_workbin_table_transfer.sh --stage-held
# Después de comprobar caja estable, mesa 2 libre y toda la zona:
./scripts/cruzr_blue_workbin_table_transfer.sh --resume-held
```

Estos comandos son para el robot conectado y preparado; no se han ejecutado
durante esta revisión. Si el mapa no está listo, la transferencia se detiene.
La preparación de mapa existente pertenece a `cruzr_blue_workbin_map_route.sh`
fuera del contexto `table-transfer` o a la interfaz oficial, con robot sin carga,
postura adecuada y supervisión; esa preparación puede relocalizar/mover cabeza.

Cada invocación crea un directorio privado `/tmp/cruzr-table-transfer.XXXXXXXX`
(o bajo TMPDIR) e imprime `TRANSFER_LOG_DIR`. Conserva salida de cada etapa,
código de salida y duración `TIMING_*`. No contiene una orden automática de
reanudación. Copiar esos archivos antes de reiniciar el PC si se necesitan.
El timeout de navegación y el modo de alineación extendida se limitan a su etapa.

## Validación reproducible

68 tests pasaron, incluidos fallos inyectados en todas las etapas del ciclo,
restauración fallida, interrupción TERM en navegación simulada, todos los modos
de reanudación, etapas sin movimiento, mapa inactivo, lecturas de salud fallidas,
muestras 20D vacías/incompletas/duplicadas/no finitas y regresiones del agarre real
`ClampBoxImperfect`. Las tres regresiones de restauración, reintento y stage-held
**fallan al ejecutar la copia anterior** y pasan con la nueva versión.

```bash
python3 -m unittest \
  scripts.test_workbin_table_transfer \
  scripts.test_workbin_transfer_preflight \
  scripts.test_workbin_clamp_result \
  scripts.test_workbin_map_points \
  scripts.test_workbin_open_only \
  scripts.test_workbin_approach_window \
  scripts.test_recovery_open_history
./scripts/cruzr_recover_to_home.sh --self-test
bash -n scripts/cruzr_blue_workbin_table_transfer.sh \
  scripts/cruzr_blue_workbin_cycle.sh scripts/cruzr_blue_workbin_map_route.sh
```

Sintaxis Bash, self-test del recuperador y `git diff --check` pasaron.
ShellCheck no está instalado; no se instaló durante la revisión.
Evidencia: `Humanoide-vla-evidence/20260909T083451Z_TABLE-TRANSFER-OFFLINE-REVIEW/`.

## Límites y reanudación

No se alteraron trayectorias vendor, velocidades, tolerancias de agarre/depósito,
calibración AprilTag ni umbrales físicos de protección. El perfil fluido sigue
siendo opcional; no se activó por omisión. La distancia de espera 1,08 m y la
referencia AprilTag pertenecen a la disposición histórica: deben comprobarse
para las nuevas mesas. El fallo físico de agarre imperfecto requiere revisar
contacto/posición real; estos cambios no prueban que el próximo agarre funcione.

Ni el log de agarre prueba apoyo/estabilidad actual de la caja ni las pruebas
sin robot certifican latencia, parada física, conectividad o ausencia de
colisiones. Pérdida de energía, SIGKILL o Wi-Fi pueden impedir limpieza remota;
una señal al orquestador no sustituye el paro físico. El éxito completo de esta
versión requiere un nuevo --check conectado y una prueba supervisada por etapas,
con batería suficiente y la referencia mesa/tag comprobada.

Cambios persistentes: sólo repositorio y evidencia local; sin commits/push.
Rollback: comparar con `before/` de la evidencia y retirar selectivamente los
cambios de esta revisión. No revertir archivos completos: ya tenían cambios del
usuario y de las recuperaciones anteriores.
