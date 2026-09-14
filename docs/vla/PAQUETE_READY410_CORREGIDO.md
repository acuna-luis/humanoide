# READY corregido y ENTRY410: paquete y ensayo por etapas

**Actualización vigente — 2026-09-14: READY→ENTRY410 probado físicamente,
5/5 etapas con éxito según el operador y sus cinco resultados Motion SUCCEED.**
HOME→READY nuevo y READY→ENTRY410 quedan completados para los ensayos comunicados.
Se conserva `force_entry.sh` del operador. Siguiente: lectura fresca y propuestas
VLA task 0 en shadow desde ENTRY; el agarre VLA aún no se ha probado.
[Registro del ensayo, Goal ID y evidencia](ENSAYO_READY_ENTRY410_20260914.md).


**Actualización vigente — 2026-09-14: HOME→READY nuevo probado físicamente,
5/5 etapas con éxito.** El propietario aporta los cinco resultados Motion
`SUCCEED` (state 1101001, status 4) y confirma el ensayo exitoso desde HOME.
Se cierra el pendiente de primera ejecución del acceso
`ready410_h63_access_01..05_forward` para este ensayo. Se registra lentitud:
122 s nominales; duración real no cronometrada. La ejecución fue mediante ROSA
directo con un `force_ready.sh` modificado por el operador; el agente conserva
ese archivo. ENTRY/VLA y el monitor Python no quedan probados por este ensayo.
Esta actualización prevalece sobre los estados históricos de READY pendiente.
[Resultados, cinco Goal ID, alcance y evidencia](ENSAYO_HOME_READY_NUEVO_20260914.md).


2026-09-14, Europe/Madrid. Ficha **VLA-01**. **VERIFICADO en PC y mediante
consultas al robot; INSTALADO EN DISCO. Carga y ensayo físico pendientes. Actualización al final.**

Este paquete conecta la postura medida con READY y después con ENTRY410.
Corrige sólo el objetivo de cabeza de READY a −0,63 rad; conserva el destino
ENTRY y las tareas existentes. No es un retorno desde cualquier postura ni
activa el VLA. La escena revisada es la mesa de 725 mm y la separación de
220 mm documentadas anteriormente; no se extrapola a otra disposición.

## Resultado de esta intervención

- Captura actual: 98 muestras por nombre articular, inmóvil. Cabeza bajada;
  no llamar a esa postura HOME completo de 20 articulaciones.
- Preflight de lectura: PASS, baterías 45,3/46,8 %, ambos paros liberados,
  cargador desconectado, actuadores habilitados. Contenedores VLA detenidos,
  sin publicadores de comandos SDK. Este resultado caduca; se repite antes
  de cualquier acción.
- Hashes actuales de configuración hardware, descripción de Motion y
  biblioteca de interpolación coinciden con los snapshots utilizados.
- Referencia de ida y recuperación, acceso y ENTRY: 1018 pares certificados,
  54 avisos internos conservados, cero UNRESOLVED y ningún timeout. Los
  avisos internos no se etiquetan como certificados ni desaparecen del informe.
- Duración nominal de avance: acceso 122 s + ENTRY 74 s = 196 s. No son
  tiempos físicos medidos y no incluyen comprobaciones ni pausas.
- 42 tests pasan: contratos, límites, alteraciones de archivos, pérdida de
  bindings, paquete incompleto, nombres duplicados, rollback de escritura,
  ausencia de habilitación y regresión del instalador anterior.
- Veinte XML listos: cinco etapas de acceso y cinco de ENTRY, cada una con
  dirección forward/reverse. Las variantes inversas sólo admiten el extremo
  exacto correspondiente; no recuperan una etapa interrumpida.

Evidencia privada (incluye fuentes reproducibles, backups, capturas y hashes):
`../Humanoide-vla-evidence/20260914_READY410_EXECUTOR/`.

## Fuentes y comportamiento

`prepare_ready410_trial.py` une ambas revisiones y exige una referencia común,
continuidad exacta de los 20 ejes, cabeza READY −0,63 rad, orden de grupos y
límites nominales hardware compatibles. Vincula referencias y fuentes por hash.

`install_ready410_trial.py` reutiliza la transacción del instalador ENTRY410.
Añade exclusivamente `s2_bio_vla/ready410_h63_{access|entry}_{01..05}_{forward|reverse}`.
No sobrescribe XML, claves existentes o enlaces simbólicos; conserva los bytes
del registro anterior, respalda y revierte una escritura fallida cuando no hay
cambios concurrentes. No recarga ni ejecuta. Se ha comprobado el **plan** vivo:

- Registro actual: `82ac1bc898451767c734bbb9c5b57c7e2c82a7e9fa6d1f4cc3f099854d2e434e`.
- Registro previsto: `9d40ede9537d53f655e99aec883fd75fcd94828883398268c21b6c652b5440fa`.

`run_ready410_trial.py` reutiliza el transporte monitorizado de una sola etapa.
Comprueba postura medida, estabilidad, salud, ambos paros, identidad de tarea y
proceso, límites del segmento y llegada inmóvil. Nunca encadena ni reintenta.
Exige una habilitación vinculada a evidencia; ni el paquete ni una confirmación
del operador crean esa habilitación. El plazo de comunicación del paro de 6 s
no es una distancia o un tiempo de parada física certificado.

Los ejecutores e instaladores originales conservan su CLI. Los planes y
habilitaciones anteriores pueden quedar obsoletos por el cambio de hashes:
hay que regenerarlos, no editar sus hashes para saltar la comprobación.

## Comandos reproducibles

Desde la raíz del repositorio, para inspeccionar el paquete preparado:

```bash
EVIDENCE=../Humanoide-vla-evidence/20260914_READY410_EXECUTOR
.venv/general-home/bin/python scripts/vla/run_ready410_trial.py \
  --check --review "$EVIDENCE/package/access.json" --step 1 --direction forward
```

La instalación siguiente **requiere E-stop principal pulsado y comprobado**, sin
cargador, sin otro cliente de control y brazos/abrazaderas estables y vacíos.
El estado observado en esta intervención tiene el paro liberado: este comando
se documenta pero **no se ha ejecutado**.

```bash
.venv/general-home/bin/python scripts/vla/install_ready410_trial.py \
  --install-on-disk --review "$EVIDENCE/package/bundle.json" \
  --plan-file "$EVIDENCE/install-plan.json" \
  --evidence-dir "$EVIDENCE/install"
```

Si cambió el registro o cualquier fuente, preparar un plan nuevo con `--plan`
y otro `--plan-file`; no sobrescribir el anterior. El instalador verifica de
nuevo las fuentes después del preflight y el registro durante la transacción.

Después de instalar, guardar fuera del robot el backup indicado en receipt.json.
La activación queda separada: aplicar el ciclo completo supervisado de
[arranque v0.2.0](../guides/CRUZR_V020_BOOT_GUARD.md), sin recarga aislada ni
StartMotion improvisado. La incidencia SIGABRT al pulsar el paro sigue abierta.
No se considera cargado por estar escrito en disco; verificar el nuevo
registro, XML y proceso después del arranque.

Cuando exista una habilitación revisada para **ese paquete y ese arranque**:

```bash
.venv/general-home/bin/python scripts/vla/run_ready410_trial.py \
  --preflight --review "$EVIDENCE/package/access.json" --step 1 --direction forward \
  --qualification /ruta/habilitacion-revisada.json --evidence-dir /ruta/preflight-nuevo
.venv/general-home/bin/python scripts/vla/run_ready410_trial.py \
  --run --review "$EVIDENCE/package/access.json" --step 1 --direction forward \
  --qualification /ruta/habilitacion-revisada.json --evidence-dir /ruta/ensayo-nuevo
```

Esos dos últimos comandos son la receta posterior a habilitación, **no una
instrucción de ejecución inmediata**. No hay bucle automático. El orden es
access 1→5, comprobando resultado y estado físico tras cada etapa, y después
entry 1→5 con su propia habilitación. Ante interrupción, diagnosticar desde el
estado medido; no enviar la inversa ni HOME automáticamente.

Para reconstruir tras una actualización: capturar por nombres con
`capture_named_entry_state.py`, generar referencia con
`prepare_ready_head_hardware_limit.py`, acceso con `prepare_home_ready_access.py`
y ENTRY con `prepare_entry410_stages.py`. Después:

```bash
.venv/general-home/bin/python scripts/vla/prepare_ready410_trial.py \
  --access-review /ruta/acceso/review.json --entry-review /ruta/entry/review.json \
  --reference /ruta/referencia-corregida.json --hardware-snapshot /ruta/hardware-configs.json \
  --output-dir /ruta/paquete-nuevo
.venv/general-home/bin/python scripts/vla/install_ready410_trial.py \
  --plan --review /ruta/paquete-nuevo/bundle.json --plan-file /ruta/plan-nuevo.json
```

## Pendiente y reanudación

Primero instalación en disco con paro comprobado; después activación supervisada
y evidencia de carga. Aún falta cerrar el protocolo de ensayo de brazos y
elevador, su despacho efectivo y seguimiento/parada. La prueba suave de cabeza
no demuestra esos puntos. No se ha emitido una habilitación ni conectado el VLA
a movimiento. No hace falta repetir todos los cálculos si fuentes y escena
siguen iguales; la postura inicial y el estado vivo sí se contrastan otra vez.

Cambios persistentes sólo en PC: preparador, contrato, wrappers, extensiones de
los módulos comunes, tests y documentación. Dependencias: entorno existente
`.venv/general-home` (numpy/FCL/PyYAML), SSH y scripts canónicos del proyecto.
Backup previo en `before/`; dos módulos inicialmente limpios se respaldaron
desde HEAD y los demás desde sus bytes de trabajo. Reversión selectiva de estos
cambios, preservando modificaciones ajenas. No hay rollback remoto que aplicar
porque sólo se consultó el robot. Si se instala posteriormente, documentar
receipt, copia externa y estado de carga/prueba en VLA-01 antes de cerrar.


## 2026-09-14T20:02:55.861758+02:00 — VLA-01: paquete READY410 instalado en disco

**VERIFICADO: INSTALADO EN DISCO; CARGA Y PRUEBA FÍSICA PENDIENTES.**
Operador confirma paro principal pulsado, brazos abajo, abrazaderas vacías y
estables. Preflight activo pasó; se ejecutó una sola instalación aditiva del
paquete ready410_head063. Veinte XML y registro final verificados por una lectura
independiente. No se ordenó recarga, reinicio, cambio de modo ni movimiento.

Destino Motion192.168.11.2, contenedor walker-motion.manipulation_robot_app-1,
/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/:
20 s2_bio_vla/ready410_h63_*.xml nuevos y adición a task_list.yaml.
Registro anterior 82ac1bc898451767c734bbb9c5b57c7e2c82a7e9fa6d1f4cc3f099854d2e434e;
registro instalado 9d40ede9537d53f655e99aec883fd75fcd94828883398268c21b6c652b5440fa.
Backup robot: /var/tmp/cruzr-entry410-backups/entry410-1789408853100542285.
Copia externa verificada de backup, paquete, receipt, XML y registro actual:
../Humanoide-vla-evidence/20260914_READY410_EXECUTOR/install/external-copy/.
Receipt, verificación independiente, preflight y hashes en el directorio install/.

Fuente reproducible y comandos: scripts/vla/install_ready410_trial.py con
package/bundle.json e install-plan.json de la misma evidencia. No repetir la
instalación: rechaza los nombres ya presentes. Fuentes completas y revisiones
conservadas fuera del robot en sources/, access/, entry/ y package/.
Reversión requiere paro comprobado y ausencia de cambios posteriores: restaurar
exactamente el registro respaldado y retirar sólo los20 archivos de receipt;
si el registro ya cambió, preparar una reversión selectiva revisada. No revertir
ni recargar automáticamente. Activar después mediante ciclo completo supervisado
de arranque v0.2.0; verificar nueva instancia y carga de tareas antes del ensayo.
Mantener el paro hasta completar la preparación del siguiente arranque.
La instalación no valida despacho/seguimiento/parada de brazos ni VLA físico.


## 2026-09-14 — VLA-01: HOME posterior al arranque comprobado

VERIFICADO por captura nueva de98 muestras: 20D inmóviles y salud válida,
máximo absoluto0,00306796rad; head_pitch−0,00306796rad. Servidor de acciones1.
No demuestra por sí solo despacho de las tareas nuevas. Cero órdenes enviadas.
Comparación con el acceso instalado: éste parte de head_pitch−0,43085685rad;
tras el HOME interno la diferencia es0,42778889rad, fuera de tolerancia0,02.
Sólo la cabeza difiere del inicio revisado. No ejecutar el acceso directamente
ni cambiar su tolerancia. El siguiente acceso previsto necesita primero la
bajada de cabeza al inicio revisado mediante la tarea existente, con su ensayo
verificado y comprobaciones actuales; no se ha ordenado esa bajada aquí.
READY es el siguiente objetivo; la habilitación específica del ensayo de brazos
sigue pendiente, separada de instalación y de la prueba anterior de cabeza.
Evidencia: ../Humanoide-vla-evidence/20260914_READY410_AFTER_HOME/.
No cambios remotos ni reinicios. Backups documentales en docs-before/.


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
