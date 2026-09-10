# Cruzr S2 — recuperación tras contacto, paro y fault durante teleoperación

**2026-09-10 — HOME interno sustituido por apertura relativa; 20 s instalados.**
Usuario confirma brazos abajo/vacíos/libres y solicita corregir `cruzr/home`.
Se reemplazó su XML por home_open_v3_20s: abrir ambos hombros −0,4 rad relativos
conservando los otros ángulos; bajar abiertos a roll−0,6; cuerpo HOME; cerrar
sólo con brazos abajo. Evita que copiar PICO abra elevando brazos desde abajo.
No cambia task_list, primitivas, límites ni el ejecutor PICO. Principal1/servo0/
cargador0 y hash de MetaMove comprobados antes/después de instalación y recarga.
XML nuevo SHA05174d2b…8cbe; original50d819d6…ed88 respaldado en
/etc/walker/trajectory-overlays/20260910T100528.529307Z_home_open_v3/.
Sólo manipulación reiniciada (StartedAt10:06:09Z); CC/hw no reiniciados, cero
objetivos enviados. Manipulación espera ListControllers bajo paro: no afirmar
validación física ni ejecución del árbol. Se conservó E-stop pulsado.
Barrido4referencias×4etapas×501muestras: mínimo69,79mm fuera de uniones locales,
cota condicional7,929mm. No cubre escena/seguimiento/parada ni posturas arbitrarias.
7 pruebas nuevas y20 previas correctas. Seis segundos: borrador local, sin
instalar; aceleración quintic estimada11,11× frente a20s. Tiempo instalado20s,
primera prueba física pendiente. No repetir reload/cambiar modo para probar.
Evidencia: ../Humanoide-vla-evidence/20260910T095255Z_HOME-ROUTE-REVIEW/ y
20260910T100548.301769Z / 20260910T100621.887349Z_INTERNAL-HOME-CHANGE.
[Detalle, limitaciones y reversión](../teleoperation/CRUZR_HOME_INTERNO_APERTURA.md).

**2026-09-10 — Incidente tras instalar 4×: HOME interno por cambio a auto (VERIFICADO).**
El perfil 4× quedó instalado con XML/hash exacto, pero la recarga dejó acciones0
sin estados articulares. Liberar el paro no recuperó por sí solo Motion.
A09:38:19Z CC recibió `workMode:auto_task` desde TeleopMode y ejecutó StartMotion;
a09:38:33Z Motion inició `cruzr/home`, ordenando todos los ejes de ambos brazos
a cero en6s. Operador pulsó E-stop a09:38:37Z al ver acercamiento al cuerpo.
Los intentos del script 4× se detuvieron en preflight; no enviaron esa ruta.
La nueva trayectoria no sustituye el HOME interno del fabricante. No usar
cambio a auto/StartMotion/reinicio para recuperar desde brazos elevados.
Nuevo encendido: principal1 y CC WaitEStopRelease comprobados. Voz autónoma
completó su chequeo y TTS Success/status4 a09:45:27Z, primera ejecución en
encendido completo registrada; no confirma por sí misma postura ni audición.
Pendientes respuesta física (brazos abajo/elevados, carga, contacto), liberación
supervisada y ensayo 4×. Mantener E-stop mientras se verifica la postura.
Sólo lectura remota y documentación local; cero reinicios/objetivos/cambios
remotos del agente. Evidencia: ../Humanoide-vla-evidence/20260910T094443Z_RELEASE-AFTER-RELOAD/.
[Secuencia y diagnóstico](../incidents/2026-09-10_HOME_INTERNO_TRAS_RELOAD_4X.md).

**2026-09-10 — PICO→HOME: 4× por defecto; perfiles rápidos verificados sólo en PC.**
**OBSERVADO por el operador:** open_v2 original funciona bien, pero es lenta.
**VERIFICADO local:** el ejecutor acepta `--speed 1|3|4` en todos sus modos;
por petición expresa, omitirlo selecciona 4×. Tiempos de movimiento nominales:
80 / 26,666 / 20 s, más preflight y verificación. Se conservan objetivos,
apertura de hombros, orden de las cuatro etapas y protecciones. Cada velocidad
exige su XML/hash y tarea independientes; si falta, no envía acción ni cambia
a otro perfil. El XML original mantiene hash6b8309f3…6999; 3×f66e53b2…8da y
4×6dd482a7…7dc. Veinte pruebas y bash -n correctos; ShellCheck no está instalado. Sin argumentos
sigue siendo --check local, sin movimiento. Timeout120s y TimeRatio1 intactos.
**PENDIENTE:** instalar/cargar y ensayar 3×/4× en robot; no hubo conexión,
escritura remota ni movimiento en esta modificación. El éxito comunicado de
1× no certifica seguimiento/parada a 4× ni acredita el estado físico actual.
Preparar instalación con brazos abajo/vacíos y E-stop conforme a la guía;
no reiniciar desde PICO para forzar la carga. Reversión: `--speed 1`, sin
restaurar la tarea directa retirada. Evidencia/backup antes y después:
`../Humanoide-vla-evidence/20260910T091420Z_PICO-HOME-SPEED/`.
[Perfiles, carga y límites de la verificación](../teleoperation/CRUZR_PICO_HOME_OPEN_V2.md).

**2026-09-10 — Actualización de recuperación: apagado completo y brazos abajo.**
Con E-stop pulsado y brazos asegurados confirmados, lectura principal1 y
solicitud única /emb/pm_shutdown aceptada. Usuario confirmó pantalla/luces
apagadas y brazos estables. Después de KEY1/chasis, confirmó apagado y brazos
abajo. Se indica nuevo encendido manteniendo el paro; confirmación y readiness
pendientes antes de liberar o seleccionar PICO.
Sin HOME ni rearme. [Detalle](../incidents/2026-09-10_PICO_RECARGA_SIN_MOTION.md).

**2026-09-10 — Estado vigente tras paro para instalar open_v2:**
Operador confirma brazos en PICO, estables/sin contacto. La tarea nueva está
instalada pero no se ejecutó: hw espera arranque, manipulación espera
ListControllers y no hay muestra de actuadores ni servidor de acciones.
No aplicar HOME, reiniciar ni cambiar de modo para probar: el HOME interno
no sigue necesariamente la ruta nueva. Preparación física/apagado pendientes;
abrazaderas vacías confirmadas después por el operador. Se corrigieron localmente mensajes
de recarga y propagación del preflight; sin movimientos/rearmes del agente.
[Evidencia y recuperación pendiente](../incidents/2026-09-10_PICO_RECARGA_SIN_MOTION.md).

**2026-09-09 — Corrección local PICO→HOME open_v2 (VERIFICADO offline; NO instalada/ejecutada):**
Se retira del wrapper la tarea directa `cruzr/pico_to_home_owner` tras contacto
comunicado por el operador. Nueva tarea independiente `cruzr/pico_to_home_open_v2`:
abrir hombros roll a −0,60 rad (10 s), bajar otros ejes de brazo manteniendo
apertura (40 s), llevar cuerpo a cero manteniendo brazos abiertos (15 s), cerrar
hombros de brazos ya bajados (15 s). XML/hash nuevos; si sólo existe el antiguo,
--run no envía acción. Instalación/recarga pendientes bajo condiciones existentes.
Doce pruebas y sintaxis correctas; mapeo MetaMove verificado, espera aumentada
120 s para 80 s nominales, nueva lectura articular después de confirmación,
conservación de stdout/stderr y código remoto incluso cuando falla una acción.
Barrido de envolventes, dos variantes/501 muestras por etapa: mínimo fuera de
uniones locales 69,79 mm; menor cota entre muestras 7,95 mm condicionada a la
interpolación común monótona. Todos los pares locales siguen informados, sin
nuevas exenciones. No certifica registro físico, desviaciones, frenado ni escena;
no sustituye ensayo real. Límites de postura/velocidad y protecciones intactos.
Cambios sólo en PC; cero consultas o escrituras al robot durante esta revisión.
Detalle: docs/teleoperation/CRUZR_PICO_HOME_OPEN_V2.md.
Evidencia/backup previo: /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260909T124028Z_PICO-HOME-OPEN-REVISION.
No restaurar la versión retirada para ejecutar; rollback operativo = suspender
ruta y retirar únicamente la nueva tarea bajo E-stop, conservando otros cambios.
Punto siguiente: instalación, recarga y ensayo supervisado pendientes después
de resolver contacto/apagado. No asumir postura actual ni apagado completado.


**2026-09-09 — CONTACTO REAL durante PICO→HOME body-zero (OBSERVADO por operador):**
El usuario informa contacto al ejecutar owner --run tras aprobar pico_body_zero
(error inicial 0,002684466 rad); resultado ACTION_FAILED_NO_RETRY. Esta evidencia
invalida reutilizar el recorrido como libre de contacto: reconocimiento de postura
y pruebas nominales NO demostraban seguridad del barrido. Se suspende su uso,
incluida cualquier repetición desde la postura posterior al contacto. No enviar
HOME, rearmar ni cambiar de modo para recuperar. Usuario solicita instrucciones
para apagado con E-stop presionado; estado de caja/apoyo de brazos aún pendiente.
Mantener paro; apagado lógico antes de KEY1 y chasis conforme informe de esta
unidad. Apagado no garantiza relajación controlada ni liberación de frenos.
Ningún movimiento, rearme o apagado enviado por el agente en este diagnóstico.
Evidencia: ../Humanoide-vla-evidence/20260909T142542_PICO-HOME-OWNER-RUN/.


**2026-09-09 — Nuevo bloqueo con caja durante PICO (OBSERVADO, recuperación pendiente):**
Usuario informa caja sujeta y brazos asimétricos; considera segura la suelta.
Consulta pasiva: Motion registra protección de fuerza izquierda 20:20:34.504
(hora del log) y derecha 20:20:38.404, separadas 3,900 s. Cancelación de tarea
PICO a 20:23:17 y nuevo inicio de tarea observado a 20:23:53; no asumir control
inactivo persistente. En muestra inicial ambos paros 0, writers RobotCommand 0;
gate de actuadores rechaza consigna latente, delta máximo 0,010203 rad.
La secuencia de disparos puede explicar la asimetría, no demuestra por sí sola
la causa mecánica del esfuerzo. No ejecutar HOME ni apertura workbin desde esta
postura: apertura existente limitada al agarre frontal workbin. No se enviaron
servicios, movimientos, cancelaciones ni rearme. Pendiente estado físico de
apoyo de caja y cese confirmado de otros mandos antes de preparar liberación.
Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260909T122324Z_TELEOP-BOX-BLOCK`. Sustituye como estado operativo al preflight PICO
body-zero previo; no reutilizar aquella postura ni su aprobación de extremos.


**2026-09-09 — Corregido PICO→HOME con cuerpo a cero (VERIFICADO local y preflight vivo):**
El gate reconoce dos referencias completas y discretas: `pico_body_flexed`
(original) y `pico_body_zero` (los mismos 14 ejes de brazos; cabeza, elevador y
cintura a cero). Selecciona la referencia más próxima y exige que TODOS los
ejes cumplan 0,02 rad y velocidad máxima 0,01 rad/s. No mezcla referencias ni
acepta posturas intermedias; HOME sigue exigiendo veinte ceros. El informe
incluye referencia, valores esperados/medidos y cada articulación discrepante.
XML/hash, tiempos 19,617+6,254 s, protecciones y confirmación local intactos;
no requiere instalar ni recargar. Ocho tests pasan, incluidos rechazos en cada
uno de los veinte ejes de ambas variantes, mezcla, datos inválidos y secuencia
XML. `--preflight` vivo finalizó 0: `matched_reference=pico_body_zero`, error
máximo 0,00278034 rad, velocidad cero, sano/control exclusivo, `MOVEMENT_COMMANDS=0`.
Revisión geométrica archivada, 101 muestras por segmento y variante: menor
separación OBB fuera de uniones locales 3,473 mm frente a lifter_pitch_2_link
(antes 25,056 mm). Las 15 consultas de superficies STL cerca de ese mínimo,
con hipótesis axial 0/20/40 mm, dieron mínimo 19.303 mm. Son distancias
nominales muestreadas, no cota global ni certificación física; las uniones locales
siguen en el informe y no se crean exenciones. Interpolador, errores dinámicos,
parada y escena conservan las limitaciones ya declaradas al operador.
Cambios persistentes sólo locales: gate, tests, ayuda y etiqueta del wrapper.
Backup/rollback: restaurar esos tres archivos desde `before/` de la evidencia
con el ejecutor detenido, preservando otros cambios. Sin reinicios ni movimiento.
Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260909T121801Z_PICO-HOME-BODY-ZERO`. Próximo paso: `--run` por operador presente,
con confirmación literal existente; ejecución física de esta variante pendiente.


**2026-09-09 — VERIFICADO: recuperación tras depósito completada y HOME medido:**
`cruzr_recover_to_home.sh --run --yes` terminó exit0. Retirada única de
0,492031 m, lateral -0,002139 m y giro 0,471 grados; después tarea vendor
`cruzr/open_arm_before_home`, goal `2f4b2a37-b6ff-469e-ba85-907b81d32573`,
SUCCEED/state1101001/status4. Lock de tareas libre, sin reset ni reinicios.
Verificación final: 20D presentes, MEASURED_HOME=1, posición absoluta máxima
0,002780 rad (brazos 0,000863), velocidad0, delta consigna máximo0,002780 rad.
Baterías 73,1/74,7 %, paros0/0, cargador desconectado, actuadores habilitados.
El robot queda en HOME, separado de mesa 2; caja depositada y previamente
confirmada estable por el usuario. La autorización del corredor trasero de
esta disposición se conserva como se describe debajo. No repetir retirada.
No se cambiaron scripts durante la ejecución ni se instalaron archivos remotos.
La transferencia automática completa sin tags y el error auxiliar VSLAM siguen
pendientes; este éxito corresponde a depósito aislado seguido de recuperación.
Evidencia: `../Humanoide-vla-evidence/20260909T105640Z_POST-DEPOSIT-HOME/`.

**2026-09-09 — CONFIRMADO por el propietario: espacio de recuperación libre en la disposición actual de mesa 2:**
tras confirmar el depósito, el usuario confirmó 1,50 m libres detrás del robot,
recorrido de brazos despejado, ningún mando activo y persona junto al paro.
Pidió conservar la comprobación del espacio para no volver a preguntarla.
Se registra para el corredor de esta disposición de mesa 2 y la retirada única
prevista de 0,50 m. Reutilizar la confirmación mientras no haya cambios que
invaliden ese corredor; no pedirla otra vez sólo por iniciar otro turno.
No equivale a declarar libre cualquier posición del mapa ni a repetir una
retirada interrumpida. Si cambia la disposición o aparecen obstáculos/personas,
se vuelve a comprobar el tramo afectado. Mantener comprobaciones técnicas
frescas de postura, paros, cargador, batería y clientes de control.
Preflight --check terminó con RECOVERY_CHECK_OK, estado deposited_open_near_table,
20D inmóviles y sin eventos inseguros. Autorizado --run --yes para retirada+HOME;
resultado pendiente del registro de ejecución.

**2026-09-09 — VERIFICADO, reconocimiento de apertura aislada en recuperación HOME; movimiento PENDIENTE:**
el --check del operador clasificaba box_may_be_held pese a la apertura aislada
exitosa. Se corrige `scripts/cruzr_recover_to_home.sh`: nuevo estado
`opened_workbin_near_table`, distinto de depósito. Exige última tarea
blue_workbin_open_only, precedente clamp_only, una sola primitiva
byd/open_arm_cruzr, resultado MetaClamp SUCCESS y BTree tick succeeded posterior,
sin fallo/cancelación/evento inseguro durante o después. Tareas posteriores,
incluso desconocidas, invalidan esa clasificación. Una apertura incompleta o
fallida produce open_result_unverified. El HOME interno admite el nuevo estado
bajo el mismo gate central; se conservan preflight, batería mínima 20 %, 20D,
retroceso 0,50 m y revalidación antes del HOME vendor. No se valida el agarre
fallido para transporte ni se modifica ninguna primitiva/protección remota.

Se aclara la confirmación: caja estable sobre mesa o retirada, abrazaderas
vacías y libres, mesa/caja/personas fuera del recorrido completo, 1,50 m libre
detrás, sin cargador/Ethernet/otros mandos y persona junto al paro. El retroceso
ya está incluido; no ejecutarlo antes por separado ni repetir automáticamente
una recuperación interrumpida después de mover la base.

Verificación: 8 pruebas nuevas del clasificador/ruta, self-test del recuperador,
16 de apertura aislada, 6 de agarre, sintaxis Bash. Registro real leído por SSH
reproduce nuevo estado, apertura línea 2098 y sin evento inseguro posterior.
--check conectado posterior terminó código 31 por BATTERY_LOW=19.899999618530273,
antes de clasificar/retroceder. **No se movió el robot y no se completó el
preflight de recuperación.** Reanudar tras cargar y desconectar cargador con
--check; sólo después --run con comprobación física actual de todo el recorrido.
Rollback: retirar selectivamente esta clasificación y su estado admitido del
ciclo interno, conservando cambios ajenos. Evidencia:
`Humanoide-vla-evidence/20260909T075754Z_OPEN-TO-HOME-INTEGRATION/`.

**2026-09-09 — VERIFICADO, ejecutor manual reutilizable de apertura aislada:**
a petición del propietario se añade `scripts/cruzr_blue_workbin_open_only.sh`,
con --check predeterminado y --run interactivo. Delega en modos específicos
--check-open-only/--open-only del ciclo canónico, conservando el bloqueo local
compartido, preflight completo y validación estricta 20D antes/después.
[Guía de liberación](CRUZR_WORKBIN_LIBERAR_CAJA.md).
Ejecuta sólo el XML/primitiva ya contrastados: cada útil ±5 cm lateral en ~2 s,
sin descenso previo, transporte o HOME. Puede dejar caer/bascular la caja.
No requiere un agarre exitoso porque sirve para liberar el agarre imperfecto;
no relaja la verificación de --resume-held ni --deposit-held.

Exige última tarea workbin_clamp_only en registros de la instancia actual,
sin eventos de fuerza/autocolisión ni publicadores RobotCommand; PICO/HOME/
otras tareas o estado no demostrable bloquean. Una apertura ya intentada produce
OPEN_ONLY_NO_ACTION y no se repite automáticamente, aunque hubiese fallado.
Esto no certifica postura/entorno ni reemplaza la comprobación presencial.
--run pide escribir ABRIR ABRAZADERAS, rechaza --yes/--fast y entrada sin TTY;
tras la confirmación renueva preflight, 20D y contexto. Instala el XML sólo si
falta y bloquea conflictos de hash. Sin reset/reinicio ni reintento ante fallo.

Verificación: 16 pruebas nuevas del ejecutor/gate (incluyendo despacho simulado
único, fallo sin reintento, salud cambiada, cancelación y repetición bloqueada),
6 de agarre y 8 de aproximación, sintaxis Bash y diff check. Primer --check
conectado detectó incompatibilidad Python 3.8 con timestamp Docker nanosegundos;
corregida truncando a microsegundos y cubierta por regresión. Segunda ejecución
--check exit 0: 21,9/23,6 % batería, paros 0/0, cargador desconectado, 20D
inmóvil y delta 0,001885 rad; detectó apertura anterior y emitió NO_ACTION.
El nuevo wrapper no ejecutó movimiento físico; la primitiva subyacente sí
había sido ejecutada y confirmada antes. Ningún cambio remoto adicional durante
estas comprobaciones. Preparación futura: usar guía, con persona junto al paro.
Rollback local: retirar wrapper/gate y modos añadidos de forma selectiva;
no revertir archivos completos porque contienen otros cambios del usuario.
Evidencia: `Humanoide-vla-evidence/20260909T074532Z_OPEN-ONLY-SCRIPT/`.

**2026-09-09 — VERIFICADO, apertura aislada completada y confirmada físicamente:**
propietario pidió abrir aceptando caída/basculación de caja vacía y confirmó
recorridos laterales de 5 cm despejados, zona de caída libre y persona junto
al paro. Preflight final: 23,6/25,0 % batería, paros 0/0, cargador desconectado,
actuadores habilitados, servidor ready, RobotCommand escritores 0 y hash del
XML correcto. Goal único `cruzr/blue_workbin_open_only`,
`b550b1e2-32b2-499f-a17f-abd142715df0`: SUCCEED, status 4, estado 1101001.
Se ejecutó únicamente la primitiva instalada `byd/open_arm_cruzr`; no se
ordenó descenso previo, navegación, HOME, reintento, rearme ni reinicio.
Muestra posterior: 22 actuadores, velocidades cero, error_code cero, cuerpo
Operation Enabled y delta máximo de consigna 0,001789 rad; odometría twist cero.
Operador confirma caja estable sobre la mesa y ambas abrazaderas libres de
contacto. **Recuperación de la caja/liberación completada; brazos abiertos,
HOME no solicitado ni alcanzado por esta acción.** No convierte el agarre
anterior ClampBoxImperfect en válido ni valida la transferencia completa.
La tarea nueva conserva hash
`90cd1be8ac7421ed36882175735429b9c6d2bd88831b3f2995501b4e7e37b119`;
ubicación/rollback en preparación inferior. Sin cambios de protecciones,
primitivas vendor o umbrales; avisos del anillo no tratados en esta maniobra.
Evidencia: `Humanoide-vla-evidence/20260909T072838Z_OWNER-OPEN-ONLY/`
(`open_action.json`, preflight final, actuadores y odometría posteriores).
Siguiente movimiento requiere decidir recorrido desde brazos abiertos y
comprobar caja/mesa fuera de su envolvente; no repetir el ciclo desde aquí.

**2026-09-09 — apertura aislada preparada por petición expresa del propietario:**
usuario solicita abrir y acepta caída de caja vacía parcialmente apoyada.
Se contrastó primitiva instalada `byd/open_arm_cruzr`: desplazamientos relativos
izquierda +0,05 m en Y y derecha −0,05 m en Y, duración 2 s, sin objetivo de
descenso y objetivo relativo de torso cero. La trayectoria efectiva del cuerpo
no queda certificada sólo por esos objetivos. XML versionado
`test_blue_workbin_factory_open_only.xml` contiene únicamente esa acción.
Preflight canónico --check pasó: 24,4/25,7 % de batería, paros 0/0, cargador
desconectado, actuadores habilitados y acciones ready. Muestra previa inmóvil,
sin errores y máximo delta corporal 0,006763 rad; RobotCommand escritores 0.
Se instaló como archivo nuevo `config/cruzr/blue_workbin_open_only.xml` en
manipulation_task_manager, hash
`90cd1be8ac7421ed36882175735429b9c6d2bd88831b3f2995501b4e7e37b119`.
No se sobrescribió ningún XML ni se reinició/recargó Motion; no se modificó
la primitiva vendor, el verificador de agarre ni protecciones.
**PENDIENTE: confirmación actual de 5 cm laterales libres en ambos brazos,
zona de caída/basculación libre y persona junto al paro. Ningún goal enviado.**
Preparación no equivale a liberación, depósito ni HOME. Rollback del archivo
nuevo: retirarlo sólo con Motion inactivo respecto a esta tarea y conservando
la evidencia; no se necesita reiniciar para restaurar el archivo.
Evidencia: `Humanoide-vla-evidence/20260909T072838Z_OWNER-OPEN-ONLY/`.

**2026-09-09 — recuperación preparada, apertura pendiente con caja parcialmente apoyada:**
operador confirma inmovilidad y todos los scripts/mando/PICO inactivos.
Después estima 85 % de la base sobre el tablero y esquina elevada unos 8 cm;
su apreciación «se puede soltar sin problema» no demuestra ausencia de basculación
ni descarga de abrazaderas. No se ordenó apertura, descenso, HOME ni reinicio.
Muestra fresca 07:20 UTC: 22 actuadores inmóviles, sin error_code, máximo delta
corporal de consigna 0,007051 rad. FT leídos en marcos de sensores; no se
interpretan directamente como pesos ni distribución de apoyos.
Depósito instalado secuencia `put_collision_cruzr` → `byd/open_arm_cruzr`:
el primer contacto no demuestra apoyo completo en esta situación. XML alternativo
`test_blue_workbin_release_only.xml` baja 6 cm y abre; no se ejecutó ni se
considera recuperación validada desde esquina elevada 8 cm y apoyo parcial.

**Corrección local necesaria:** se reprodujo offline que `verify_clamp_log`
aceptaba el log real con ClampBoxImperfect (separación 0,580 m, Fy 21,5 N).
Ahora rechaza fallo explícito de Motion y exige finalización MetaClamp SUCCESS,
además de las comprobaciones previas de fuerza/distancia y ausencia de liberación.
Esto afecta --verify-grasp, --deposit-held y reanudaciones con carga; no convierte
ese depósito en una recuperación desde agarre fallido. Espera también el marcador
End MetaClamp al recoger el registro. Reproducción real ahora rechazada; seis
regresiones nuevas y ocho de aproximación pasan, más sintaxis y diff check.
El caso SUCCESS del test es sintético; no se afirma nuevo agarre físico válido.
No había scripts workbin activos al editar. Cambios anteriores preservados.
Reversión selectiva de este parche de verificación sólo para depuración offline:
la versión anterior puede autorizar una reanudación tras fallo y no debe usarse
para mover. PENDIENTE estabilizar/apoyar completamente la caja mediante
intervención presencial adecuada, sin acceso bajo carga ni manipular brazos;
después determinar una liberación compatible con postura, contacto y entorno.
Evidencia: `Humanoide-vla-evidence/20260909T072023Z_PARTIAL-BOX-RECOVERY-CHECK/`.

**2026-09-09 — OBSERVADO, agarre imperfecto y caja parcialmente apoyada:**
tras aportar un check histórico satisfactorio y foto, el operador declara
«caja apoyada en el lado más lejano y derecho del robot». Se registra apoyo
parcial, no depósito completo ni abrazaderas descargadas. Falta confirmar
si algún script/mando permanece activo y estado de soporte del resto de caja.
Lectura 07:18 UTC: 22 actuadores con velocidad cero y sin error_code;
RobotCommand con 0 escritores (no demuestra por sí solo todos los clientes
inactivos). Baterías actuales 26,5/27,4 %, distintas del 31,0/30,1 % del check
aportado. Avisos activos siguen 00001001 y 02029001; no se ha recuperado blanco.
Motion registra a las 07:16:09–10 UTC (15:16 +08) intento de clamp:
`distance_on_float_base.y: 0.581279 > box size.outside_len: 0.578`,
`ClampBoxImperfect`, MetaClamp FAILURE y árbol detenido. Diferencia 3,279 mm
entre distancia modelada de útiles y límite configurado; NO es una medición
independiente del ancho real ni prueba de que el error sea despreciable.
El registro sugiere contacto en borde superior/otra sección más ancha, sin
confirmarlo como causa única. No se ha demostrado agarre válido para transporte.
No usar --resume-held, repetir --run, abrir, HOME o reiniciar desde este apoyo
parcial sin recuperación específica y comprobación física actuales.
Intervención del agente exclusivamente de lectura y documentación: ninguna
orden física, modificación de umbrales, reset o reinicio. PENDIENTE resolver
apoyo/descarga de caja, postura y control exclusivo antes de recuperar.
Evidencia: `Humanoide-vla-evidence/20260909T071802Z_RING-AFTER-USER-CHECK/`.

## 2026-09-08 — ejecutor PICO→HOME autorizado por el propietario

Se añadió `scripts/teleoperation/cruzr_pico_to_home_owner.sh` y la tarea
`scripts/teleoperation/tasks/cruzr_pico_to_home_owner.xml`. La ruta concreta
es: ambos brazos a cero en 19,617 s manteniendo la postura corporal medida;
después cabeza, los tres ejes del elevador y cintura a cero en 6,254 s.

El ejecutor no parte de una postura PICO genérica. Compara los veinte ejes con
la muestra PICO revisada y bloquea si el error máximo supera 0,02 rad o la
velocidad supera 0,01 rad/s. Además aplica el gate de actuadores (fault, estado,
velocidad y consigna latente), el preflight canónico, ausencia de publicadores
concurrentes, hash del XML y orden de carga del task manager. `--run` sólo
funciona en TTY y exige transcribir una declaración que asigna al operador la
decisión de iniciar bajo observación directa y con mano en E-stop. Tras éxito
de la acción exige HOME20D medido; un fallo termina sin reintento.

Secuencia operativa prevista:

1. Con E-stop accionado: `--install`.
2. Manteniendo el E-stop: `--reload`.
3. Liberación supervisada mediante el procedimiento de arranque aplicable.
4. Con zona nuevamente comprobada: `--preflight`.
5. Sólo por decisión del operador presente: `--run`.

Limitación aceptada por el propietario: Motion puede no reproducir la ley
quintic revisada y no existe una cota de parada verificada. No se desactivan
protecciones para compensarlo. Estado al documentar: pruebas locales correctas;
ninguna instalación remota, reinicio o orden de movimiento enviada.

**2026-09-08 — refinamiento condicional HOME y comparación de órdenes:**
Con parada hipotética (+0,68755°), error articular 5° y origen axial 0–40 mm,
la comprobación continua local abrazadera–muñeca conserva reservas de 0,304 mm
izquierda y 0,018 mm derecha después de márgenes 2+2 mm. Cierra ese cálculo
local, no la validación física. Los tres órdenes nominales comparados conservan
el mismo mínimo muestreado de 25,056 mm frente al elevador. Parada real,
incertidumbre global y equivalencia de ejecución siguen sin demostrarse.
Sin movimiento. [Detalle y evidencia](../measurements/2026-09-08_CIERRE_REVISION_PICO_HOME.md).

**2026-09-08 — tolerancias UBTECH comunicadas y presupuesto insuficiente:**
usuario informa sin procedimiento aplicable, error articular «5ª» interpretado
como 5° y espacial 2 mm. Si este último es seguimiento adicional, supera reserva
previa derecha 0,856 mm. Desplazamiento angular debe acotarse por pieza; parada
sin cota. Falsos positivos de dos pares aceptados como criterio técnico comunicado,
sin desactivar checks. Propuesta sigue NO aprobada, sin colisión física afirmada
ni movimiento enviado. Ver informe de cierre y error-budget-ubtech-reported.json.

**2026-09-08 — revisión ampliada PICO→HOME, NO aprobación física:**
[resultado](../measurements/2026-09-08_CIERRE_REVISION_PICO_HOME.md). Nueva lectura inmóvil;
376 pares/202 estados, 33 refinamientos STL y 40 muestras adicionales de
brazos–torso. Dos intersecciones nominales ya iniciales en uniones requieren
interpretación, no prueban contacto real. Plantillas de ejecución leídas sin
llamarlas; equivalencia con curva revisada y cotas de seguimiento/parada no
demostradas. Decisión documentada NOT_APPROVED; ninguna ejecución ni reinicio.

**2026-09-08 — VERIFICADO, origen en modelo instalado y chequeo PICO→HOME:**
[resultado y alcance](../measurements/2026-09-08_REVISION_ORIGEN_Y_PICO_HOME.md). URDF instalado distinto
del SDK archivado: sí contiene L/R_hand_link. Sensor z[-26,5;0] mm; origen mano
[±94,0,11,5] mm. Error 2 mm y contención declarados registrados. Propuesta
25,870372 s dentro de límites; barrido condicionado y refinamiento de malla dejan
cotas propias de muñeca hasta 0,86 mm, sin margen angular/dinámico ni calificación
física del detalle. NO aprobación de movimiento; cero comandos. Origen en modelo
cerrado, correspondencia física/robot–robot/escena/controlador aún pendientes.

**2026-09-08 — P alineado con cara externa y sin desnivel, por declaración:**
referencia externa F diferenciada de S y origen ROS. F→P derecha [95,0,0] e
izquierda [-95,0,0] mm en direcciones del sensor. Si O está en tramo axial
F→muñeca de 0–40 mm, O→P tiene Z en [0,+40] mm; hipótesis, no registro probado.
Ficha y dibujo actualizados; precisión/modelo pendientes, contrato físico sin cambios.

**2026-09-08 — foto anotada de intervalo axial 40 mm:** referencia externa
interpretada desde cara del cilindro junto al soporte negro hacia cara junto
a muñeca. No identifica automáticamente S ni origen ROS; asociación de lado
y medición axial bilateral pendientes. HTML y registro actualizados, sin movimiento.

**2026-09-08 — declaraciones bilaterales y S oculto:** 95 mm P–eje confirmados
por usuario en ambos brazos. Proyección de S comunicada entre 0 y 40 mm; referencia
y sentido pendientes. Centro 20 ±20 mm sólo representa intervalo, no coordenada
ROS validada. Conservadurismo requiere cubrir intervalo completo, no elegir un
extremo. Registrado en HTML/nota de ejes; sin movimiento ni contrato alterado.

**2026-09-08 — OBSERVADO por declaración, distancia P–eje 95 mm:** usuario
identifica distancia mínima del centro exterior de almohadilla al eje de
fijación (punto–recta). No es P–S ni una componente ROS determinada. Lado de la
medición, reparto perpendicular, posición longitudinal e incertidumbre pendientes.
Registrado en ficha HTML y nota de ejes; sin modificar contrato ni mover robot.

**2026-09-08 — CORRECCIÓN del dibujo 3D de abrazaderas:** usuario señala que
el eje de fijación es paralelo al plano de almohadillas. El renderer principal
aún dibujaba orientación identidad; ahora aplica Ry(+90°) derecha/Ry(-90°)
izquierda a placa y patitas, coherente con direcciones contrastadas. Patitas
hacia +Y, eje del sensor dibujado; P en centro de cara girada y S en fijación.
Traslación de pantalla arbitraria y explícitamente ilustrativa: no medida ni
exportada como registro. Cotas 70/100 pasan a lado corto/largo; retiradas flechas
A/B/C/T del marco antiguo hasta registrar referencias. Visualización Chrome y
sintaxis comprobadas; contrato físico y robot sin cambios.

**2026-09-08 — referencias S/P visibles en HTML:** marcadores con llamadas
naranja/verde en fijación y cara de almohadilla; vista inicial de posición y
botón desde la ficha. Corregida definición antigua de P como punto del soporte.
Posiciones del esquema ilustrativas, no medidas ni registro ROS. Sintaxis y
visualización Chrome comprobadas. Sin comandos al robot.

**2026-09-08 — HTML rellenado con datos disponibles:** orientación aproximada
por lado con confirmación técnica comunicada, cotas declaradas, deducciones
descriptivas y evidencia. Traslación, incertidumbre y límites en nuevo marco
permanecen explícitamente pendientes. Ejemplos ficticios separados en desplegables;
exportación conserva estado de precarga y ediciones. Sin registro de colisión
ni comandos al robot.

**2026-09-08 — OBSERVADO por confirmación técnica comunicada, orientación bilateral:**
usuario confirma también ejes izquierdos. Candidatas cualitativas derecha
Ry(+90°), izquierda Ry(-90°), marco útil +Y hacia patitas/+Z hacia contacto.
Siguiente medición: tres componentes S→P, cara de fijación a centro de almohadilla,
en mm; registrar S respecto al origen URDF antes de obtener traslación ROS.
[Detalle y pendientes](../measurements/2026-09-08_EJES_SENSOR_DERECHO.md). Sin movimiento ni contrato de colisión alterado.

**2026-09-08 — confirmación técnica comunicada del lado derecho e inferencia izquierda:**
usuario confirma resultado derecho por técnico. Nueva muestra 11:26:59 UTC y
URDF archivado sitúan +X izquierdo hacia fuera, +Y arriba y +Z delante; R útil
candidata Ry(-90°), con +Z hacia almohadilla y +Y hacia patitas. Contraste físico
izquierdo y precisión pendientes. [Registro](../measurements/2026-09-08_EJES_SENSOR_DERECHO.md).
Sin movimiento ni cambio del contrato de geometría.

**2026-09-08 — INFERENCIA, ejes derechos calculados sin movimiento:**
[resultado](../measurements/2026-09-08_EJES_SENSOR_DERECHO.md). Muestra actual inmóvil y URDF
archivado sitúan aproximadamente +X sensor al centro, +Y arriba y +Z delante.
Con descripción del usuario y marco útil explícito, R candidata ≈Ry(+90°).
No registro validado: runtime/modelo físico, marco dimensional e incertidumbre
siguen pendientes; contrato geométrico no alterado, cero comandos de movimiento.

**2026-09-08 — ejemplos de R ampliados a X/Y/Z:** comparador didáctico con
identidad y tres giros independientes de +90 grados respecto al sensor fijo.
Incluye matrices, sentido de giro y dirección de almohadilla, borde y patitas.
Ejemplos ficticios, sin modificar geometría real ni validación de trayectorias.

**2026-09-08 — VERIFICADO, comparación didáctica de R:** [dos vistas 3D](../measurements/orientacion_R_ejemplos.html), integradas en la ficha. Sensor y traslación
idénticos; identidad frente a giro de +90 grados sobre Z. Matrices aplicadas a
la geometría del útil, cámara sincronizada y ejemplo de coordenadas. Sintaxis
JavaScript y visualización Chrome comprobadas. Son ejemplos ficticios; registro
real sigue PENDIENTE. Sin movimiento ni cambios al modelo físico.

**2026-09-08 — orientación explicada para el operador:** la ficha HTML describe
cómo queda girada la abrazadera respecto al sensor de muñeca, mediante cara de
almohadilla, borde superior y patitas. Matriz de ejemplo en desplegable técnico;
la descripción fotográfica no sustituye el registro numérico, aún PENDIENTE.
Sin cambios geométricos ni acciones sobre el robot.

**2026-09-08 — ejemplos numéricos en la ficha:** fotos históricas 1/2.jpeg
revisadas; no aportan registro métrico al sensor. Borrador de límites descriptivos
[-35,47], [-55,45], [-35,95] mm derivado de cotas declaradas, no medido ni
registrado en ROS. Traslación cero, identidad y errores 2/3 mm y 5 grados son
ejemplos ficticios de formato, separados de datos y etiquetados no utilizables
para movimiento. Geometría y validación física siguen PENDIENTES.

**2026-09-08 — ficha geométrica mínima y unidades:** cinco apartados por lado
(posición, orientación, envolvente, incertidumbre y evidencia); medidas en mm,
ángulos en grados con convención, matriz sin unidades. Doce fichas detalladas
quedan opcionales. Datos existentes reutilizados desde el contrato local;
registro y geometría siguen PENDIENTES. JSON v3 no ejecutable. No constituye
aprobación de todas las trayectorias: cada recorrido e interpolador requieren
validación específica con estado, entorno y márgenes. Sin acciones en el robot.

**2026-09-08 — ayuda por campo de medición:** HTML ampliado con definición,
extremos/dirección de cada distancia, ejemplos sin valor medido y situación de
partida por campo. Distingue ocho cotas declaradas de referencias por identificar,
geometría por medir y evidencia por documentar. Registro físico sigue PENDIENTE;
sin cambios de geometría ni acciones sobre el robot.

**2026-09-08 — cotas declaradas visibles en la ficha HTML:** ocho longitudes
precargadas por lado, con estado pendiente de confirmar; referencias y medidas
ausentes diferenciadas. Exportación v2 conserva valores declarados y estado por
campo, incluso en paneles no visitados. No acredita medición ni modifica el robot.

**2026-09-08 — VERIFICADO, aclaración de la guía de medición:** leyenda de
O/X/Y/Z y cotas A/B/C/T añadida al HTML; marcas fotográficas renombradas
P1/P2/P3 para evitar confundir puntos con longitudes. Sin cambios geométricos
ni comandos al robot; registro físico de referencias sigue PENDIENTE.

**2026-09-08 — VERIFICADO, guía visual de medición disponible:**
[Modelo 3D interactivo](../measurements/abrazadera_mediciones_3d.html) y
[instrucciones](../measurements/README.md). Doce fichas por lado, vistas giratorias
y descarga JSON; comprobación local en Chrome de los doce paneles, separación
izquierda/derecha y vistas completada. Esquema ilustrativo: únicamente la placa
usa cotas nominales declaradas; montaje, sensor y holguras no están medidos.
**PENDIENTE:** fotos con escala coplanar, mediciones del técnico, transformación
al marco del robot e incertidumbre. La cinta aporta escala local, no certifica
geometría ni trayectoria PICO→HOME. Sólo archivos locales, sin comandos al robot.
Punto de reanudación: completar ambas fichas y registrar las zonas no accesibles.

**08-09, unión fija de abrazadera precisada:** [auditoría](../incidents/2026-09-08_UNION_FIJA_ABRAZADERA.md).
Modelo distingue sensor+wrist_roll rígidos de wrist_pitch móvil. Los dos
solapamientos históricos afectan wrist_pitch: no son exenciones de montaje.
Añadida topología explícita, sin recortar envolvente ni ocultar colisiones;
cinco tests pasan. PICO→HOME sigue sin validación geométrica. Cero movimiento.

**08-09, propuesta PICO→HOME offline preparada:** [alcance](../incidents/2026-09-08_PROPUESTA_PICO_HOME_OFFLINE.md).
Captura20D sana/inmóvil; propuesta matemática de25,870372s y rangos URDF pasan.
No búsqueda de camino ni validación de contacto; JSON no ejecutable, cero
movimientos. Tres tests pasan. Script físico sigue pendiente de ruta revisada.

**08-09, recuperación operativa y HOME verificados:** [resultado](../incidents/2026-09-08_HOME_TRAS_RECUPERAR_CONTROL_CENTER.md).
Tras reinicio único de CC y liberación supervisada, self-check/StartMotion
correctos y JoystickMode. HOME20D máximo0,003068 rad, velocidad0, actuadores
sanos; servidor1, VLA detenido/writers0. Confirmación visual posterior pendiente.
Sustituye Fault como estado vigente; causa watchdog6002/SIGSEGV sigue abierta,
sin otro restart de hw ni HOME publicado por agente. Sin monitor persistente.

**08-09, reinicio de Control Center autorizado y completado:** propietario pidió
reiniciar lo necesario y confirmó E-stop principal presionado. Lectura desde
Vision verifica data1 antes de una única llamada docker restart --time5 a
walker-system.control_center-1. rc0; nueva instancia y log muestran
waitBootReady→Recover→WaitEStopRelease, principal pressed/servo released.
No se reinició hw de nuevo: ya estaba reiniciado automáticamente y esperando
/mc/rosa_control/start. No se llamó start, servo enable, reset ni HOME.
Cambio volátil de proceso; sin archivos/configuración modificados en robot,
sin rollback automático porque reanudar puede mover. Mantener paro hasta nueva
comprobación y liberación supervisada. Esto restaura espera de arranque, NO
prueba resuelto el watchdog6002 ni HOME. Relojes hosts/PC con desfase; comparar
instancia/PID y secuencia, no ordenar timestamps de hosts distintos a ciegas.
Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260908T083040Z_SERVICE-RECOVERY/`. Sin monitor persistente.

**08-09, EtherCAT diagnosticado:** [secuencia y límites](../incidents/2026-09-08_DIAGNOSTICO_ECAT_6002.md).
6002 identificado como FT derecho; enumerado antes del watchdog0x1b durante
SAFEOP→OP. Master falla y hw sufre SIGSEGV; Docker lo reinicia una vez,
sin restaurar Motion. OOMfalse. Causa física/software primaria aún no aislada;
no demuestra sobrecarga ni sensor averiado. Sólo lectura; no reparaciones ni
reintentos. Pendiente revisión técnica de bus/sensor y fallo software.

**08-09, resultado tras liberación supervisada: FALLO StartMotion.** Self-check
passed=true/error0, pero StartMotion fail reason19 y Control Center Fault.
Log hw: sensor FT KunWeiTech EtherCAT 6002 queda SAFEOP ERROR (0x14),
Sync manager watchdog (0x1b); no alcanza OP, master error0x98110024. Después
fallo del proceso hw y timeout de /mc/servo/enable. Manipulación espera
ListControllers; servidor de acciones0, actuadores sin muestra (timeout7s).
Paros0/0 y cargador0 en consulta. No asignar lado físico a6002 sin cotejar mapa;
no interpretar watchdog como prueba de daño o repetir reinicio a ciegas.
Readiness previo x86/cámaras sí pasó; no garantizaba inicialización EtherCAT.
HOME/estado físico de servos no verificables. Sólo diagnóstico desde agente:
ningún HOME, rearme, restart o cambio de protecciones. Sin monitor persistente.
Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260908T082533Z_BOOT-AFTER-RELEASE/`.

**08-09, siguiente arranque preparado para liberación supervisada:** operador
confirma brazos abajo, abrazaderas vacías, estabilidad/sin contacto, recorrido
libre, ruedas bloqueadas y persona junto al paro. Primera consulta Motion
agotada; posterior descubrimiento observa contenedores recién iniciados.
Guard instalado leído y ejecutado sólo --check: rc0, v0.2.0, WaitEStopRelease,
x86 funcional 3/3, seis cámaras 2/2, seguridad 1/0/0 (principal/servo/cargador).
No reinicio ni movimiento desde agente. Condiciones técnicas previas satisfechas
para liberar el principal bajo supervisión confirmada; puede iniciar HOME
interno. Pendientes self-check/StartMotion y medición 20D posteriores; no se
considera HOME ni recuperación final completada. No monitor persistente.
Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260908T082050Z_BOOT-BEFORE-RELEASE/guard-check.log`.

**08-09, reinicio del operador con E-stop ya liberado:** reporta brazos abajo.
Lectura nueva confirma ambos paros 0 y cargador 0; no permite inferir HOME.
Control Center pasó WaitEStopRelease→SelfChecking→Fault: self-check false,
error 4; servicios x86 no disponibles durante el chequeo, errores de consulta
IP/reloj/red y sensores. Contenedores Motion running desde hace ~2 min y Vision
~4 min; compatible con arranque desfasado, no causa única demostrada.
Servidor manipulación 0, actuadores sin muestra (timeout 7 s). Estado físico
articular y servo NO VERIFICABLE; VLA exited/restart=no. No se llamó StartMotion,
reset, cambio de modo, HOME ni se liberó paro mediante agente. Evitar nuevas
órdenes mientras se diagnostica el arranque fallido. Sin monitor persistente.
Evidencia externa: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260908T081454Z_REBOOT-ESTOP-RELEASED/`.

**08-09, petición de script PICO→HOME:** añadida herramienta exclusivamente
de diagnóstico `scripts/teleoperation/check_pico_home_recovery.py --check`.
Descubre contenedores, captura actuadores/joints/status y distingue HOME,
READY completo u OTHER sin inferir posición del historial. No contiene --run,
publicación, cancelación ni rearme; no satisface todavía la recuperación física
solicitada. Primera prueba corrigió selección ambigua ros2/ros2-export antes de
consultar ROS. Prueba conectada posterior completa: OTHER, cero movimientos,
exit 3 y evidencia 20260908T080600.790170Z_PICO-HOME-CHECK fuera de Git.
Pendiente trayectoria revisada desde postura PICO actual y montaje real.
No retirar bloqueo por ser dueño ni interpretar esto como falta de autorización:
la autorización existe y falta resolver el recorrido físico.

**08-09, error del script de recuperación revisado:** usuario aporta --run --yes
abortado al leer historial, después de actuadores sanos y lock de tareas libre.
No movimiento en ese intento según la rama ejecutada. Lectura repetida funciona:
HISTORICAL_STATE=teleoperated_pose; fallo original no reproducido ni causa probada.
Se mejora scripts/cruzr_recover_to_home.sh: conserva código de error/salida,
sustituye head por sed para evitar cierre anticipado bajo pipefail y reconoce
`force protection triggered!` como evento de fuerza. No relaja rutas de HOME.
Sintaxis y self-test pasan; tres regresiones de logs FT pasan. Lectura remota
reconoce disparo en línea 3523 y nueva tarea PICO en 4306: evento anterior a esa
tarea no se declara evento nuevo, ni se considera resuelto mecánicamente.
Sin cambios remotos ni movimiento. Postura actual requiere medición y una ruta
aplicable; ACTIONS=ready sólo indica disponibilidad de acciones, no postura READY.

**08-09, recuperación post-FT evaluada:** [resultado y bloqueo técnico](../incidents/2026-09-08_EVALUACION_RECUPERACION_POST_FT.md).
Postura sana/inmóvil pero a 0,783135 rad de READY; HOME genérico simultáneo y
OMPL sin plan previo comprobable no proporcionan recuperación demostrada.
No nuevo movimiento/rearme/reinicio. Pendiente retirada presencial cualificada
o procedimiento aplicable; autorización del propietario ya recibida.

**08-09, recuperación solicitada tras disparo FT:** el operador confirma caja
retirada, abrazaderas vacías, estabilidad/sin contacto, zona libre y otros mandos
detenidos. El --check de recuperación rechaza ACTION_BUSY (rc27). Se canceló
únicamente la tarea PICO `ac314729-ec21-4ea5-9439-4d4d8f179824` por CancelGoal;
respuesta aceptada y status final 5 (CANCELED). ROSA falló en conversión local
del UUID antes de llamar; la llamada ROS2 estándar sí fue aceptada.
Muestra posterior sana e inmóvil, delta máximo 0,001900 rad, NO HOME.
No se envió trayectoria ni rearme. Recuperación HOME pendiente: postura PICO
tras fuerza no cubierta por READY→HOME ni por el ciclo de caja del wrapper.
No hubo cambio persistente de configuración ni reinicio; sin monitor activo.

**08-09, nueva detención PICO con caja vacía:** [diagnóstico](../incidents/2026-09-08_PARADA_PICO_CAJA_VACIA.md).
Protección de fuerza izquierda y derecha activadas con 0,200 s de separación.
Operador dice caja soltada y ningún paro; lecturas paros 0/0, actuadores sanos
inmóviles, delta 0,001900 rad. Postura teleoperada NO HOME sustituye estado
anterior. Causa mecánica/estado físico y recuperación específica pendientes.
Sólo lectura; no rearme, HOME, reinicio ni modificación de protecciones.

**08-09, HOME tras finalizar el ensayo ENTRY:** [registro](../incidents/2026-09-08_HOME_TRAS_ENTRY.md).
READY→HOME SUCCEED/status=4; HOME 20D máximo 0,002780 rad, velocidad cero,
actuadores sanos. Último estado medido HOME sustituye READY; confirmación visual
posterior pendiente. Revisión de ENTRY por inclinación y shadow 0/5 pendientes.

**08-09, retorno ENTRY→READY completado:** [registro](../incidents/2026-09-08_RETORNO_ENTRY_READY.md).
Último estado medido READY: SUCCEED/status=4, error brazos 0,001633 rad,
cuerpo en READY, velocidad cero y actuadores sanos. Operador confirma estabilidad, ausencia de contacto y postura adecuada del torso. ENTRY sigue pendiente de revisión por inclinación; shadow 0/5.
Esta actualización sustituye ENTRY como último estado medido.

**08-09, observación posterior del propietario:** señala inclinación del torso
muy pronunciada y aporta fotografía. OBSERVADO: postura visual inclinada;
no confirma aceptación física de ENTRY ni estabilidad/ausencia de contacto.
La ejecución y el gate articular siguen verificados, pero la idoneidad de esta
postura queda PENDIENTE de revisión antes de avanzar con fixture/shadow.
El XML solicita lifter_pitch_1 = −0,834773 rad (−47,83°) y lifter_pitch_3 =
0,291265 rad (16,69°): son ángulos articulares, no medición del torso respecto
al suelo. La fotografía no demuestra el estado físico actual ni las holguras.
No se ha enviado movimiento ni modificado el objetivo por esta observación.

**08-09, HOME→READY→ENTRY ejecutado:** [evidencia y estado](../incidents/2026-09-08_READY_ENTRY_AUTORIZADO.md).
Ambas acciones SUCCEED/status=4; ENTRY 20D error 0,003835 rad, velocidad 0,
actuadores sanos. Captura completa de la transición: pico reportado 0,107861 rad/s.
Último estado ENTRY, VLA detenido/writers 0. Confirmación visual posterior
pendiente; retorno ENTRY→READY y cinco shadow (0/5) pendientes.
Esta actualización prevalece sobre los estados históricos HOME/ENTRY pendiente.

**08-09, plan reanudado en E6.1:** [gates y preparación](../incidents/2026-09-08_REANUDACION_PLAN_E6_1.md).
HOME↔READY deja de ser bloqueante pendiente de ensayo. ENTRY XML/aceptación
cotejados; error proyectado al frame 40 de 0,001055 rad. Auditor nuevo identifica
relaciones rígidas y calcula barrido condicionado de útiles (4.096 celdas);
no validación física completa de ENTRY. Perfil P14 faltante añadido a ambos
hosts; validador Motion/inferencia Vision actualizados con backup y sin arrancar
contenedores. --check ahora verifica hashes de código y pasa. Seis tests nuevos,
shadow local correcto; HOME medido, VLA exited/restart=no. No nuevo movimiento.
Siguen pendientes ENTRY físico, fixture actual y cinco shadow (0/5).

**08-09, vuelta READY→HOME completada y confirmada:** [cierre del ciclo](../incidents/2026-09-08_HOME_DESDE_READY_AUTORIZADO.md).
Goal único SUCCEED/status=4; HOME 20D máximo 0,002684 rad, velocidad 0,
actuadores sanos; operador confirma «todo bien». Ida y vuelta quedan PASS físico
en este ensayo con montaje actual. Captura parcial del retorno: 2.251 estados,
pico reportado 2,049366 rad/s. VLA detenido/writers 0; sin monitor persistente.
No cambios remotos de configuración/protecciones; geometría continua pendiente.
Este HOME sustituye READY como último estado físico documentado.

**08-09, READY ejecutado por autorización actual del propietario:** [resultado](../incidents/2026-09-08_READY_AUTORIZADO_PROPIETARIO.md).
Propietario revocó bloqueo anterior y confirmó condiciones físicas tras aviso
de riesgo. Goal único SUCCEED/status=4; READY medido, error brazos 0,001938 rad,
velocidad 0, actuadores sanos, VLA detenido y writers 0. Sin cambios de
configuración/protecciones ni vuelta HOME. Operador confirma recorrido sin
problemas y READY estable/libre de contacto: PASS físico de esta ida con montaje
actual. Retorno y validación geométrica general pendientes; sin monitor continuo.

**08-09, barrido condicionado de ida y vuelta:** [abrazaderas incluidas](../incidents/2026-09-08_BARRIDO_ABRAZADERAS.md).
Envolventes de orientación libre y reservas explícitas calculadas en 36.864
celdas; separación condicionada de cuerpo central/brazo contrario/otra
abrazadera. Muñeca y antebrazo propios siguen inconclusos. No se aprueba
movimiento ni se cambia READY; errores de montaje e interpolación sin verificar.

**08-09, contraste de ida y recuperación:** [informe de rutas](../incidents/2026-09-08_CONTRASTE_RUTAS_HOME_READY.md).
XML/YAML instalados coinciden por hash; retorno conserva puntos inversos,
pero TimeRatio registrado difiere (0.5/1.0). No acredita barrido de abrazaderas
sin transformación al sensor ni curva continua del controlador. Sin acciones
o cambios remotos; diez tests locales OK. READY final conservado.

**08-09, confirmación visual posterior recibida:** operador reporta HOME sin
incidencias y estable. FT y joints puntuales disponibles, sin tara/compensación
verificadas. READY no enviado, ruta sin validar; detalles en HOME_INTERNO_TRAS_LIBERACION.

**08-09, estado posterior:** [liberación del operador y HOME interno](../incidents/2026-09-08_HOME_INTERNO_TRAS_LIBERACION.md).
StartMotion/home terminaron; muestra posterior próxima a cero, errores cero y
velocidades cero. Sólo diagnóstico retrospectivo; ausencia de roce no demostrada,
confirmación visual pendiente. No se envió READY ni se validó recorrido.

**08-09, lectura bajo paro:** [disponibilidad](../incidents/2026-09-08_DIAGNOSTICO_BAJO_ESTOP.md).
Principal 1/chasis 0 corroborados; CC espera liberación, actuadores sin writer,
manipulación sin servidor. Sin posición/fuerza actuales verificables. No llamar
start ni liberar paro para completar diagnóstico. Guard disabled, VLA detenido.
Lecturas sin movimientos/reinicios/despliegues; no monitor activo.

**08-09, ilustración CAD disponible:** MODELO_CUELLO muestra ubicación del cruce
modelado y triángulos ampliados. No reproduce el robot actual ni exige moverlo
para obtener esa vista. Referencia física equivalente sigue pendiente.

**08-09, auditoría del cuello:** [resultado](../incidents/2026-09-08_MODELO_CUELLO.md).
Copia/escala/FK revisados; cruce modelado persiste con READY medido histórico.
No se alteran referencias/mallas para eliminarlo. No prueba contacto físico,
no aprueba rutas ni exige mover para fotografiar. Tres tests, sólo offline.

**08-09:** [reanudación offline](../incidents/2026-09-08_REANUDACION_REFERENCIAS.md).
P1/P2/P3 contrastados: dos correspondencias 2D siguen empatadas, sin registro
3D ni nueva autorización. Cabeza yaw;pitch ya observada en E6.1C-READY histórico.
No se consultó ni movió robot; estado físico de hoy desconocido, sin monitor.

**Relevo 07-09:** ver [punto de reanudación](../incidents/2026-09-07_RELEVO_HOME_READY.md).
Último reporte físico energizado/paros liberados/estable sin contacto; no se
confirmó aislamiento o apagado. No tratar guardado de conversación como parada.
P1/P2/P3 reconocidos visualmente; montaje CAD aún pendiente. No monitor activo.

**07-09, modelo offline corregido:** PGC/dedos históricos retirados, muñecas y
sensores conservados. Abrazaderas nominales incluidas como datos descriptivos
sin montaje inferido; aún no colisionadores mundiales. Barrido sólo robot
561 pares/34 avisos, no aprobación. VALIDACION_HOME_READY_HOME documenta detalle.

**07-09, premisa declarada:** operador pide asumir READY sin choques reales.
Se distingue de validación medida; no valida HOME↔READY. Mallas en HOME numérico
ilustradas sin movimiento; no representan abrazaderas exactas ni escena.
Ver VALIDACION_HOME_READY_HOME. No se cambian tareas ni exclusiones de colisión.

**07-09, READY preservado:** auditor de destino detecta intersección modelada
cabeza–torso en READY, verificada mediante cálculo independiente. No inferir
choque físico ni resolverlo con rodeo: el extremo no cambia. Cabeza fija queda
descartada para petición vigente; sin tareas modificadas ni órdenes. Ver
VALIDACION_HOME_READY_HOME y ready_endpoint_locked. Cuatro tests offline pasan.

**07-09, refinamiento HOME↔READY:** intersecciones modeladas cabeza–torso al
girar; variante offline conserva cabeza fija, no equivale a READY completo ni
ordena llevarla a cero. Seis uniones de brazos ya intersectan en cero sintético;
no se declaran contacto permitido ni se resuelven con rodeos. Informe
VALIDACION_HOME_READY_HOME y full_home_ready_mesh_witnesses_v2; sin movimiento.

**07-09, retorno completo hipotético revisado:** auditor HOME↔READY incluye A,
staging y cabeza, no sólo hombros. 1.836 estados/828 pares; 48 avisos AABB no
resueltos. Reversión de puntos del recovery verificada, no reversión física ni
cancelación de órdenes. Ver VALIDACION_HOME_READY_HOME y evidencia
full_home_ready_screen_v2. Útiles reales, escena y barrido continuo pendientes.

**07-09, HOME↔READY priorizado:** cierre local recovery 0,6 rad en1,5 s exige
>=0,40 rad/s bajo duración literal; no compatible con provisional0,15. No usar
la temporización quíntica offline como si estuviera instalada. Ver
VALIDACION_HOME_READY_HOME. Sin movimiento ni modificación de tiempos operativos.

**07-09, STOP software no es parada mecánica:** trazado backend ROS VLA destruye
publisher y vacía cola, sin orden adicional hold/torque-off. No usar como
evidencia de distancia de parada ni los límites de aceleración provisional
como frenado garantizado. Refinamiento interno deja seis ceros en uniones
adyacentes, no descartados. SALIDA_MUNECA_FIJA documenta alcance. Sin movimiento.

**07-09, pares internos:** diagnóstico con shoulder_pitch visual provisional,
56 pares, 24 solapamientos AABB sin retirar adyacencias. No contacto permitido
inferido. 42 relaciones rígidas y 14 variables en salida de hombro; pendiente
contraste físico/geométrico. Ver SALIDA_MUNECA_FIJA. Sin comandos al robot.

**07-09, bloque cruzado parcial:** 459 pares con cota AABB positiva y tres
refinados STL positivos, sólo bajo hipótesis del modelo. No cubre herramienta,
propios brazos, escena ni parada. No autoriza recuperación física. Detalle
en SALIDA_MUNECA_FIJA; no convertir recuento de pares en porcentaje de seguridad.

**07-09, cota inter-muestras parcial:** tres pares hombro–torso tienen cotas
positivas bajo modelo rígido/distancia numérica. No interpretar como validación
continua del conjunto ni margen físico/parada. Ver SALIDA_MUNECA_FIJA.

**07-09, extensión del refinamiento STL:** 61 posturas en cada uno de tres
pares hombro–torso, mínimos positivos iniciales; vuelta ideal equivalente en
posturas, no ejecución física verificada. No aprobar recuperación con este
filtro parcial. Evidencia y límites en SALIDA_MUNECA_FIJA.

**07-09, cálculo STL corregido:** rutina de distancia entre triángulos omitía
algunos cruces arista–cara. Históricos dependientes no utilizables como prueba
de separación sin regenerar. Nuevos tres testigos iniciales hombro–torso
separados en superficies STL, sin recorrido completo ni tolerancias físicas.
Detalle y tests en SALIDA_MUNECA_FIJA; ninguna autorización de movimiento.

**07-09, ampliación de candidato:** filtro AABB de salida/vuelta encuentra
tres pares hombro–torso inconclusos, no contacto físico demostrado. Geometría
shoulder_pitch incompleta y entorno/frenado sin evaluar. No usar como autorización
de movimiento. Informe SALIDA_MUNECA_FIJA, tres tests nuevos correctos.

**07-09, candidato de muñeca fija:** invariancia relativa sensor/muñeca
comprobada numéricamente en salida sintética de hombro, no holgura inicial
ni seguridad física. Diagonales L174/R178 mm no son separación mínima.
Ver `docs/incidents/2026-09-07_SALIDA_MUNECA_FIJA.md` antes de continuar.

**07-09, precisión del bloqueo geométrico:** no está limitado a staging↔A;
los 30 tramos revisados tienen testigos de solapamiento conservador bilateral
con propio brazo. No interpretar las separaciones negativas como penetración
real. Aumentar radios o serializar no habilita la ruta. Ver auditoría por tramo
en BARRIDO_PESIMISTA_RECORRIDO; sin movimiento ni cambios de protecciones.

**07-09, desarrollo offline:** salida histórica temporizada y límites de posición
evaluados, no autorización de salida/retorno. El solapamiento útil–wrist_pitch
permanece inconcluso. Emparejador temporal implementado sin recolector vivo;
no usarlo como monitor de seguridad. Diez tests locales pasan entre ambos módulos.

**07-09 ~12:54 Madrid:** imagen estéreo disponible por suscripción pasiva,
pero par concurrente imagen/joints separado 1,288 s; no sincronización validada
ni protección de movimiento. Véase TELEMETRIA_ESTACIONARIA en incidents.

**07-09 ~12:49 Madrid:** lectura puntual de joints y FT disponible; brazos
próximos a cero, velocidades reportadas cero. No demuestra ausencia de contacto,
tara FT ni vigilancia preventiva. No se enviaron movimientos ni cambios de modo.
Alcance y pendientes: `docs/incidents/2026-09-07_TELEMETRIA_ESTACIONARIA.md`.

**07-09 ~12:33 Madrid:** operador reporta HOME sin problemas tras rearme.
Log muestra éxito pero 184 avisos de cabeza fuera de rango; sin alarmas FT
explícitas en ventana consultada retrospectivamente. No fue ensayo monitorizado
antes del contacto ni aprobación de recuperación general. No ampliar límites.
Evidencia y alcance en `docs/incidents/2026-09-07_HOME_OBSERVADO_1233.md`.

**07-09, peor caso geométrico:** la esfera nominal 119,411 mm ya invade la malla
de muñeca en el testigo conservado (centro hipotético a 40,639 mm). No demuestra
contacto real; sí impide aprobar mediante esa envolvente. Reservas mayores no
lo resuelven. No excluir la muñeca ni elegir giro favorable para obtener PASS.

**07-09, referencia de útil pendiente:** revisión de fotos y cotas no permite
reducir el registro a otra longitud. Hace falta identificar físicamente origen,
ejes y cara de fijación del sensor sixforce_link (croquis de referencia o
registro cualificado). No exigir repetir A–F/T ni más fotos genéricas; no
desmontar/mover para resolverlo. No hay nueva aprobación de recuperación.

**07-09, alcance adicional offline:** candidato histórico pasa límites de
posición URDF para 14 ejes; continuidad monotónica garantiza que no sale del
intervalo de sus extremos. No equivale a límites activos ni comprobación de
colisiones. Generador exige --urdf y conserva JSON no ejecutable. V2 externa;
geometría de útil/muñeca y HOME interno siguen pendientes.

**07-09, candidato temporal local:** generador build_home_offline_candidate.py
calcula tiempos para retorno histórico P14, no una recuperación autorizada.
35,389 s totales con curva quíntica y límites provisionales; no trasladar sus
duraciones a MetaMove suponiendo la misma interpolación. No valida colisiones,
postura actual, estado de otros ejes ni arranque. JSON no ejecutable, sin ROS.

**07-09, interfaz de planificación examinada:** ArmTask no expone un plan
articular previo; GetMnpActionList sólo catálogo. PickPlanner/WalkPlanner son
interfaces de punto/pose, no retorno articular. No usar MetaMove/ArmTask como
consulta sin ejecución ni confiar en un yaml_args dry-run no documentado.
Planificación desacoplada aún no demostrada; informe RUTA_HOME_ALTERNATIVAS.

**07-09, alternativa HOME estudiada sin ejecutar:** existe tarea instalada
move_dual_arms_home_ompl con planificación solicitada para 14 ejes. No es un
reemplazo aprobado: no demostrados plan-only, geometría activa, recorrido ni
intercepción del HOME interno. No reutilizar variantes genéricas cintura/base
con dimensiones distintas. No llamar MetaMove para obtener un plan de prueba.
Hallazgos, hashes y dependencias en
`docs/incidents/2026-09-07_RUTA_HOME_ALTERNATIVAS.md`. Sin cambios en robot.

**07-09 ~09:44 UTC, autoarranque del guard contenido:** con autorización expresa,
Vision guard pasa a disabled sin --now/stop/restart. Archivos y marcas de última
ejecución intactos; copias antes/después y manifiesto verificados. Se retiró sólo
el enlace de arranque, reversible bajo nueva revisión. No cubre HOME interno
ni ejecución manual del guard, no habilita movimiento o rearme. Ver diagnóstico
de arranque; no confundir con las consultas previas que no cambiaron el robot.

**07-09 09:38 UTC, lectura conectada:** guard Vision enabled/active-exited y copia
instalada sin bloqueo del repositorio, ahora contrastado con archivos remotos.
No ejecutado ni cambiado. Deshabilitar sólo autoarranque queda propuesto pendiente
de aprobación; no resuelve HOME interno ni habilita rearme. VLA control/inference
detenidos según inventario; no implica estado físico seguro. Evidencia y alcance
en diagnóstico de arranque sólo lectura. Cero ROS/movimiento/recargas.

**07-09, muñeca refinada con STL:** en dos testigos, distancia centro supuesto
a superficie ~40,6 mm frente a radio mínimo 139,4 mm: la esfera sigue alcanzando
muñeca. No es evidencia de contacto de la herramienta real ni motivo para
excluir el par. No se aprueba retorno/HOME con esa aproximación. Hace falta
acotar montaje y comportamiento, no incrementar márgenes. Ver cierre de bloqueos
de aprobación; sin conexión al robot, desbloqueo ni comandos.

**07-09, recorrido sintético histórico muestreado:** cuatro envolventes y tres
órdenes de brazos; 6.030 muestras en resolución mayor. Separación condicional
respecto a cuerpo/brazo contrario/otra abrazadera, pero solapamiento con propio
brazo; no se elimina ese par para producir PASS. No reproduce HOME interno ni
su postura inicial/tiempos/ley Motion. Falta geometría propia shoulder_pitch y
resto de coberturas descritas en el informe de barrido pesimista. Suite v5 pasa;
sin modificación ni autorización de movimiento o rearme.

**07-09, cotas pesimistas sólo en sensibilidad offline:** para postura URDF
cero, cuatro radios hipotéticos 139,411–204,411 mm quedan separados de 26 AABB
de cuerpo. Mínimo del caso mayor: 15,550 mm, no distancia física observada.
No incluye brazos/entorno/recorrido ni demuestra tolerancias reales. No usar
este resultado para rearmar o enviar HOME; no cambió el robot. Informe externo
`20260907_clamp_pessimistic_screen.json`, tres tests nuevos correctos.

**07-09, cota sin resolver el giro (sólo estudio):** radio nominal 119,411 mm
alrededor del origen descriptivo cubre la caja para toda rotación si las
referencias son ortonormales y la contención reportada es válida. Centro en
sensor y errores siguen sin registrar; no es un radio de seguridad. Una esfera
que intersecta torso es inconclusa, no evidencia de colisión del útil. Tres
tests nuevos/suite v4 pasan, sin cálculos sobre trayectorias ni cambios físicos.

**07-09, envolvente nominal recibida:** operador indica T=130 mm, sin salientes
fuera de otros márgenes. Modelo propio nominal 82×100×130 mm, profundidad
−35/+95 respecto al eje descriptivo. No volver a pedir T o un CAD inexistente.
Ocho tests del generador pasan; no incluye incertidumbre validada ni montaje
registrado, y no protege el HOME interno. No libera paros ni habilita movimiento.

**07-09, integridad del auditor y siguiente dato:** límites calculados sólo
se incluyen para lados con evidencia validada; rechazo de overflow y prueba
contra uso del modelo parcial como contrato. Suite v3 local ampliada, sin
modificar protección instalada. Ficha de cotas del soporte en
`docs/incidents/2026-09-07_COTAS_PENDIENTES_SOPORTE.md`: T desde almohadillas,
contención y salientes; aún pendientes. No medir con acceso inseguro ni
rearmar/mover para identificar geometría. HOME interno sigue sin interceptar.

**07-09, alternativa al plano de fabricante:** un modelo propio de volúmenes
envolventes puede sustituir al CAD inexistente de la abrazadera, siempre que
contención, montaje e incertidumbre estén verificados. El generador local
`build_clamp_simplified_model.py` sólo representa la placa y una reserva lateral
condicionada para las patitas; soporte completo y R/t siguen pendientes.
Cuatro tests pasan, sin aprobación física. No pedir nuevas fotos genéricas ni
liberar el E-stop para resolver el registro. El HOME interno continúa sin
interceptar; este modelo no modifica esa situación.

**07-09, cierre de la vía de tornillos sin referencia adicional:** los diez
centros CAD usados son invariantes bajo reflexión lateral; las dos hipótesis
2D restantes no son dos configuraciones físicas demostradas. No resolver el
empate mediante movimiento ni otra repetición de foto. Falta referencia de
cara/normal/plano físico y soporte completo, no más tests de esos mismos
puntos. Seis tests pasan, informe exterior v2; sin desbloquear ni mover.

**07-09, correspondencias exteriores candidatas:** cuatro fijaciones exteriores
de las fotos permiten destacar dos de las seis hipótesis del patrón central,
sin calificar ninguna como transformación física. Análisis sólo 2D: alturas
de cabezas, identidad y perspectiva no resueltas. No cambia bloqueo de HOME,
rearme ni movimiento; cero órdenes/despliegues. Evidencia en contraste de fotos.

**07-09, fotos suficientes para documentar, no para cualificar:** se retira
la solicitud genérica de otra vista/conector no identificado. La auditoría
`audit_clamp_sensor_asymmetry.py` demuestra asimetría de la malla completa,
no correspondencia con la herramienta real. Tres tests correctos. Falta
registro geométrico y protección de recorridos/arranque; conservar E-stop,
sin ensayo HOME ni rearme. Ver contraste fotográfico para evidencia y límites.

**07-09, rutas heredadas:** instalación E6.0N, recarga E6.0O y apply/restore
de READY E6.0P bloqueadas localmente antes de conexión. Suite v2: 18 variantes
rechazadas, sin cambios en tareas instaladas ni protección del HOME interno.
No usar un restore-vendor o un reinicio como ensayo de recuperación.

**07-09, entradas estrictas y suite local:** gate HOME exige posición,
velocidad, cmd_pos, status y error, sin valores por defecto. Clasificar HOME
no demuestra frescura, geometría ni salud más allá de los campos inspeccionados.
E6.1C instalación/recarga bloqueadas antes de conexión. La suite
`scripts/run_contact_requalification_offline.py` terminó
`OFFLINE_REGRESSIONS_OK_PHYSICAL_BLOCKED`; 14 variantes de lanzamiento rechazadas.
No se modificaron las tareas instaladas ni el HOME interno.

**07-09, desfases HOME verificados en logs:** órdenes de grupos escalonadas
~0,2 s; dispersión total ~0,805–0,806 s en ambos arranques del 04-09.
Primer HOME: consignas avisadas fuera de rango en ambos brazos y cabeza
antes de FT. No ampliar límites ni asumir que una interpolación sincronizada
reproduce Motion. Véase [temporización](../incidents/2026-09-07_HOME_TEMPORIZACION.md).
Esto no prueba la causa única, trayectoria física ni ausencia de contacto.

**07-09, E6.1C offline retirado como vía de aprobación:** wrapper --check/--run
y analizador directo devuelven bloqueo/salida 78. No regeneran PASS basados
en el proxy antiguo. Informes previos preservados, no rehabilitados. Este
cierre documental no protege HOME interno de arranque ni modifica el robot.

**07-09, contraste numérico de fotos:** ajuste 2D reproducible confirma varias
correspondencias indistinguibles del patrón central (RMS L~0,852 px y R~1,022 px).
No demuestra orientación absoluta, plano, distancias de colisión ni protección
de HOME. Se conserva bloqueo; falta referencia no simétrica física/CAD, no
repetir las dimensiones de placa ni las mismas fotografías.

**07-09, referencia de fijación pendiente:** el STL del sensor se auditó
offline; z=0 es candidato, no plano real confirmado. Vistas inferiores
recibidas (primera L, segunda R), originales `Imágenes/1.jpeg` y `2.jpeg`
inspeccionados y hashes registrados; pendientes de correspondencia contra CAD. El patrón
de seis contornos de ~4,2 mm es simétrico cada 120°; no identifica por sí solo
el montaje ni demuestra equivalencia con los seis tornillos visibles.
No sustituir esa correspondencia por
offset PGC ni reutilizar los PASS históricos para HOME.

**07-09, geometría parcial actualizada:** F=36 mm en ambos clamps confirmado;
volumen de placa calculado offline, cinco tests aprobados. No incluye aún
soporte completo ni transformación al sensor: no autoriza HOME/rearme.

**07-09, patillas hacia interior:** confirmado por operador en postura actual;
ancho de placa 70 mm centrado, extremo de patillas a 47 mm del centro lateral.
No equivale a holgura respecto al torso ni a orientación fija del frame ROS.
Contorno frontal implementado offline; sin desbloqueo de trayectorias.

**07-09, cotas recibidas:** A=95 mm, B/C=45/55 mm reportados bilateralmente;
altura remedida=100 mm; patillas=12 mm. B/C aclaradas desde unión real,
centro daría 50/50; [detalle y cotas restantes](../incidents/2026-09-07_CONTRASTE_FOTOS_CLAMPS.md).
No modifican la cuarentena ni validan HOME; sólo completan entradas manuales.

**Actualización 07-09:** [seis fotos corregidas contrastadas con URDF](../incidents/2026-09-07_CONTRASTE_FOTOS_CLAMPS.md).
Se conocen las referencias externas del soporte; faltan sus cotas respecto
al sensor, no otra confirmación de la inspección ni las mismas fotografías.
No usar el offset de la pinza PGC como offset de estas placas.

> **07-09 — contención local implementada:** [estado de recalificación](../incidents/2026-09-07_REQUALIFICACION_CLAMPS.md).
> Doce variantes de lanzamiento rechazadas en tests sin conexión; no cubre
> HOME interno del arranque, UI/PICO ni el guard instalado en Vision.
> E-stop mantenido; no liberar ni reiniciar para probar. Inspección reportada:
> daño sólo en carcasa; clamps restauradas. Geometría bilateral y barrido
> pendientes; E6.0K retirado para nuevos PASS. No hubo despliegue ni movimiento.

**Última actualización:** 7 de septiembre de 2026
**Unidad observada:** Cruzr S2 `WAE001UBT60000669`  
**Baseline:** robot v0.2.0, abrazaderas, `HW_TYPE=cruzr_s2_v1`, PC controller 4.7.0  
**Ámbito:** contacto contra mobiliario, objeto posiblemente sujeto, postura no
`home`, paro de emergencia, fault de servo y consignas latentes.

Este documento describe incidentes reales y el procedimiento conservador que
permitió recuperar el robot en los casos cerrados. No convierte un apagado abrupto ni un reset de
servo en procedimientos aprobados por UBTECH. El estado físico y lógico debe
comprobarse de nuevo en cada incidente.

## 1. Resultado ejecutivo del incidente

**Restricción vigente:** la [auditoría del 07-09](../incidents/2026-09-07_AUDITORIA_CONTACTOS_HOME.md)
demuestra que el arranque v0.2.0 envía internamente `cruzr/home`. Un ciclo de
apagado/arranque **no es una retirada segura universal** desde contacto,
READY o postura asimétrica. Los casos históricos siguientes no autorizan
repetirlo: primero inspección de daño, geometría real y trayectoria cualificada.
El wrapper PC no intercepta ese HOME interno. No hay bloqueo técnico central
desplegado por esta auditoría; no confundir restricción documental con protección.

Durante teleoperación PICO el robot ejerció fuerza contra una mesa. Se accionó
el paro y el robot quedó estable, flexionado y con una caja de cartón
prescindible posiblemente sujeta. La mesa se retiró.

La recuperación automática se bloqueó correctamente varias veces:

- el registro más nuevo no permitía demostrar la fase de manipulación;
- `/mc/manipulation/action` quedó temporalmente sin servidor;
- el hombro izquierdo yaw, servo `4003`, permaneció en FAULT;
- una tarea excepcional sólo para el brazo derecho fue abortada sin mover;
- ese aborto dejó consignas derechas distintas de las posiciones reales;
- el preflight impidió rearmar `4003` con esas consignas latentes.

El operador realizó después un apagado completo, retiró la caja y usó `KEY1`.
Los brazos descendieron sin una trayectoria controlada. En el siguiente
arranque el robot se encendió inicialmente con el paro accionado. Después de
liberarlo, Motion inicializó todos los ejes sin fault, inmóviles, con
posición/consigna coincidentes y dentro de ±0,003 rad de cero. El robot ya
estaba en `home` articular, por lo que **no se envió otra trayectoria `home` ni
se llamó al servicio de rearmado**.

`KEY1` no queda validado como método de recuperación. En esta unidad ya se
había asociado su uso aislado a un corte abrupto y corrupción de registros
Docker. Consulte
[`../support/UBTECH_SHUTDOWN_PROCEDURE_MISMATCH_V020.md`](../support/UBTECH_SHUTDOWN_PROCEDURE_MISMATCH_V020.md).

## 2. Evidencia verificable

### 2.1 Fault del hombro 4003

Tras el contacto se observaron:

```text
L_shoulder_yaw_motor
id=4003
error_code=0x1001
status=0x0238
velocity=0
```

Las lecturas SDO confirmaron:

```text
0x603F -> 0x1001   # error code
0x6041 -> 0x0238   # status word con FAULT
```

Los registros añadieron esta secuencia:

```text
servo 4003 error code:0x1001
Operation disabled unexpected
servo 4003 error code:0x2007
EnableServoSrv timeout
```

Los demás ejes mostraban `0x0237`, compatible con `Operation Enabled`. No se
dispone de la tabla oficial UBTECH que traduzca `0x1001` y `0x2007`; su nombre
y causa exacta siguen pendientes del proveedor.

### 2.2 Arranque parcial de manipulación

Después de seleccionar `auto_task`, `manipulation_robot_app` reinició porque
esperaba controladores que no estaban cargados. Se restauraron de forma
volátil mediante el `controller_manager` oficial:

```text
force_torque_sensor_controller: running
imu_sensor_controller: running
```

Después `/mc/manipulation/action` volvió a publicar un servidor. Esto resolvió
el arranque de la aplicación, pero no el fault 4003. En el arranque completo
posterior ambos controladores aparecieron `running` sin intervención manual.

### 2.3 Objetivo aceptado no equivale a movimiento ni éxito

Se preparó una tarea temporal con una única acción:

```xml
<Action ID="MetaMove" type="arm" location="right"
        delta_translation="0;-0.05;0" duration="6" />
```

El objetivo fue aceptado, pero terminó:

```text
desc=MoveToGoalFailed
state=7104050
status=6
```

Las siete posiciones derechas permanecieron iguales y todas las velocidades
fueron cero. En esta plataforma, el éxito observado de una acción es
`status=4` y `SUCCEED`; `status=6` es un resultado terminal abortado, no éxito.

### 2.4 Un aborto puede dejar consignas latentes

Aunque la tarea anterior no movió el brazo, `/mc/actuator_state` mostró después
estas diferencias `cmd_pos-position` en la cadena derecha:

```text
mínimo absoluto: 0,0166 rad
máximo absoluto: 0,1043 rad
```

Rearmar el eje fallido en ese estado podía permitir que las consignas se
aplicaran de forma brusca. La llamada dirigida a `/ecat/servo/op_enable` fue
bloqueada por el preflight **antes de ejecutarse**.

### 2.5 Estado final recuperado

Después del apagado y nuevo arranque:

```text
todos los ejes no rueda: error_code=0
status=0x1237
velocity=0
abs(cmd_pos-position)<0,003 rad
abs(position)<0,003 rad
/mc/manipulation/action: server count 1
manipulation_controller: running
force_torque_sensor_controller: running
imu_sensor_controller: running
charger: conn_status=2, current=0
baterías: 65,6 % y 74,6 %
estops: 0,0
```

El comando de sólo lectura terminó:

```text
./scripts/cruzr_blue_workbin_cycle.sh --check
ACTUATORS_OPERATION_ENABLED=1
ESTOPS=0,0
CHARGER=disconnected
ACTIONS=ready
CHECK_OK
```

### 2.6 Segundo incidente: trip FT y recuperación completa

El 27-08 una sesión arms-only bimanual tomó una caja y el robot dejó de
responder mientras PICO/PC seguían publicando a 90 Hz. Motion midió en el FT
izquierdo `Force-X=-305,6…-307,0 N` frente al umbral de 120 N, registró
`Excessive force` y detuvo la tarea. Después aparecieron faults del servo 5003,
saltos de consigna en ambos hombros y todos los esclavos EtherCAT pasaron a
`SAFEOP ERROR`. Los reinicios automáticos de contenedores no restauraron
`ListControllers` ni `/mc/manipulation/action`.

Con caja retirada, brazos/robot estables y zona despejada se completó el flujo
lógico `/emb/pm_shutdown` hasta `Shutdown→Term`; sólo después de confirmar
pantalla, luces y red apagadas se pulsó `KEY1` y finalmente se apagó el chasis.
En el arranque siguiente se mantuvo inicialmente el paro accionado. Al
liberarlo, sin movimiento inesperado, Control Center completó self-check y
`StartMotion`; EtherCAT, controladores y servidor de manipulación reaparecieron.
El check versionado verificó todos los actuadores `Operation Enabled`, sin
fault, inmóviles y con consignas dentro del límite, paros `0,0` y cargador
desconectado. No se envió `home`: el nuevo log no permitía clasificar la
postura, aunque el hardware estaba sano.

Este segundo incidente confirma que el grip PICO no determina fuerza
proporcional: es un clutch booleano. La carga FT provino de la interacción
física o de un transitorio/bias del sensor, no de cuánto se apretó el botón.
También confirma que un reinicio automático de contenedores no equivale a
recuperación cuando EtherCAT cae; debe exigirse el preflight completo.

### 2.7 Tercer incidente: home vendor incompatible con postura cruzada

El 28-08, después de una sesión PICO, el script clasificó
`teleoperated_pose` y ejecutó por primera vez físicamente la tarea vendor
`cruzr/open_arm_before_home`, goal `54f7beb2-ffd2-45bd-86e6-07559fae709b`.
El XML no calcula una retirada condicionada por la postura: en su primera fase
manda en paralelo el brazo derecho a
`[0,-0.332024,0,0,0,0,0]`, el izquierdo a
`[0,-0.348983,0,0,0,0,0]`, y cintura/elevador a cero.

El final de PICO ya había registrado autocolisión entre torso y codo/muñeca
izquierdos, con distancias de aproximadamente 17–25 mm, rechazando comandos.
Durante el recovery, 1,76 s después del inicio del goal, la protección midió:

```text
Excessive force detected ... left ft sensor: -370.944 [Force-X]
```

El brazo derecho y la cintura informaron éxito; el brazo izquierdo no alcanzó
el objetivo —incluido un error de codo de `-1,30408 rad`— y el elevador quedó
abortado. El resultado global fue `MoveToGoalFailed`, state `7104050`,
`status=6`. Inmediatamente después, los servos izquierdos 4004 (codo roll),
4003 (hombro yaw) y 4002 (hombro roll) registraron `error_code=0x1003` y
`Operation disabled unexpected:0x123f`.

El operador accionó el paro. `hw` y `manipulation_robot_app` reiniciaron una
vez; el nuevo rosa_control quedó esperando `/mc/rosa_control/start`,
`/mc/actuator_state` sin publicador y `/mc/manipulation/action` sin servidor.
Los checks versionados terminaron con código 25. El diagnóstico mantuvo el
paro y no rearmó, reinició, cambió modo ni envió otra trayectoria.

**DESCARTADO:** considerar `open_arm_before_home` una retirada segura universal
desde cualquier postura PICO. Hasta diseñar y validar una recuperación por
regiones de postura, el script no debe ejecutarse de nuevo después de PICO.

### 2.8 Cuarto incidente: rearmado `StartMotion` desde READY con clamp contra torso

El 04-09 el goal E6.1C READY→ENTRY no llegó a enviarse: el preflight abortó
porque Motion seguía en `WaitStartMotion`. Tras un ciclo completo, el operador
liberó el E-stop desde la postura READY. El self-check terminó
`passed=true`, pero la acción interna `StartMotion` falló trece segundos
después con `reason:19 Limb motion failed`. La clamp izquierda quedó
visiblemente contra el torso. A continuación 4003/4004 registraron `0x1003`,
4004 pasó a `0x2006` y EtherCAT cayó globalmente a `SAFEOP ERROR`.

No se había arrancado el checkpoint, el publicador ni ENTRY. Se accionó el
E-stop y se hizo un segundo apagado completo; al retirar potencia el contacto
se alivió y los brazos descendieron. El segundo arranque, ya sin contacto,
terminó en `JoystickMode`. El preflight canónico aprobó y una muestra fresca
midió HOME en los 20 ejes, con brazos ≤`0,000479 rad`, velocidad cero y deltas
posición–consigna ≤`0,002397 rad`; no se envió otra trayectoria HOME desde el PC.
**Corrección 07-09:** los logs originales demuestran `cruzr/home` interno en
ambos arranques (19:58:01 y 20:20:14 +08); el primero registró FT −317,787 y
abortó. El segundo ejecutó HOME y terminó. No fue sólo reenergización.

El propietario confirmó posteriormente que las abrazaderas estaban montadas
deliberadamente en orientación invertida para mejorar la manipulación de
cajas. Ese cambio amplió o desplazó la envolvente física hacia el torso, pero
no se representó en el URDF, en una malla de colisión ni en un perfil distinto
de herramienta; tampoco existe un parámetro de orientación en el contrato VLA
inspeccionado. Por ello los checks articulares podían aprobar sin detectar las
patillas salientes. La coincidencia geométrica y temporal hace de esta
envolvente no modelada una hipótesis contribuyente fuerte, no una causa única
demostrada de cada daño. La distribución exacta de fuerzas y el alcance material
requieren inspección. No repetir HOME→READY hasta registrar orientación de fábrica y
holgura física bilateral, y sustituir la transición rápida por una validación
escalonada.

Las fotografías posteriores muestran rayado y una marca/orificio aparente en
la cubierta. No se ha demostrado todavía si el daño es sólo cosmético o si
afecta una pieza estructural, cableado o sensor. Debe conservarse evidencia
fotográfica y realizarse una inspección técnica antes de calificarlo.

## 3. Posibles causas

Mantener separadas las observaciones de las explicaciones evita convertir una
hipótesis en procedimiento.

| Estado | Posible causa | Evidencia y límite |
|---|---|---|
| **OBSERVADO** | contacto sostenido contra la mesa | el operador vio fuerza elevada y accionó el paro; el fault apareció en el mismo intervalo |
| **INFERENCIA** | sobrecarga o protección del hombro izquierdo yaw | `4003` fue el único eje en FAULT y no terminó de habilitar; falta la tabla de códigos UBTECH |
| **OBSERVADO** | transición EtherCAT anormal alrededor del incidente/reinicio | se registraron `WKC act/set=29/69`, `SAFEOP ERROR` y errores de sincronización; no está demostrado si fueron causa o consecuencia |
| **VERIFICADO** | arranque incompleto del stack de manipulación | faltaban los controladores FT e IMU y el servidor de acción era 0; cargarlos restauró la aplicación, no el servo |
| **VERIFICADO** | una acción abortada puede modificar consignas sin mover | `status=6`, posiciones iguales y deltas de consigna posteriores de hasta 0,1043 rad |
| **OBSERVADO** | `KEY1` puede desenergizar la parte superior de forma abrupta | los brazos descendieron sin trayectoria; un uso anterior coincidió con registros Docker corruptos |
| **DESCARTADO** | el boot guard debía tratar como error un arranque detenido en `WaitEStopRelease` | el reinicio supervisado del 03-09 demostró que éste es el estado correcto mientras el paro físico sigue accionado; el guard ahora lo reconoce y sale sin reiniciar ni mover |
| **VERIFICADO** | la primera fase de `open_arm_before_home` puede aumentar el contacto desde una postura PICO cruzada | el XML mueve ambos brazos, cintura y elevador en paralelo; produjo `Force-X=-370,944 N`, fallo del brazo izquierdo y faults 4002/4003/4004 |

No está demostrado que el fault implique daño mecánico permanente: desapareció
en el arranque final. Tampoco está demostrado que repetir un power cycle sea
siempre suficiente o seguro.

## 4. Árbol de decisión

```text
contacto, fuerza anormal o movimiento inesperado
                 |
                 v
        STOP / paro físico
                 |
                 v
 ¿objeto, mesa o persona en trayectoria?
       | sí                     | no
       v                        v
 no enviar home          preflight de sólo lectura
 retirar contacto sólo          |
 con estado físico seguro       v
                       ¿fault, movimiento o
                       abs(cmd-pos)>0,01?
                         | sí          | no
                         v             v
                  no home/rearmado   ¿ya está en home?
                  no tarea parcial    | sí       | no
                         |             v          v
                         v          terminar   recuperación oficial
                  apagado aprobado              con preflight fresco
                  y nuevo descubrimiento
```

## 5. Procedimiento de recuperación

### Fase A — detener y clasificar

1. Ante contacto o fuerza inesperada, detener teleoperación y usar el paro
   físico si el movimiento continúa o existe riesgo inmediato.
2. Mantener personas, pies y manos fuera de brazos, cabeza, elevador, cintura,
   caja y posibles zonas de caída.
3. Clasificar el objeto como **sujeto**, **apoyado** o **retirado**. No deducirlo
   del log.
4. No enviar `home` mientras una mesa, caja o persona pueda interceptar la
   trayectoria.
5. No combinar PICO, UI, mando y scripts como clientes simultáneos.

### Fase B — diagnóstico sin movimiento

Desde el PC:

```bash
./scripts/cruzr_recover_to_home.sh --check
./scripts/cruzr_blue_workbin_cycle.sh --check
```

El segundo script comprueba ahora, para cada articulación no rueda:

- `error_code == 0`;
- bit FAULT ausente;
- bits de `Operation Enabled` presentes;
- `abs(cmd_pos-position) <= 0.01` rad;
- servidor de manipulación, objetivos, batería, cargador y paros.

Interpretación:

```text
ACTUATOR_FAULT=...          -> no mover, no rearmar
ACTION_BUSY=...             -> no iniciar otro objetivo
ACTUATORS_OPERATION_ENABLED=1
CHECK_OK                    -> infraestructura apta; aún falta estado físico
```

Un topic anunciado no garantiza una muestra fresca. Después de reinicios hay
que redescubrir nombres de contenedor y no depender del daemon ROS 2 obsoleto.

### Fase C — condiciones que prohíben `home`

No ejecutar `home` si se cumple cualquiera:

- fault o error de cualquier articulación;
- una articulación no está `Operation Enabled`;
- `abs(cmd_pos-position)>0,01` rad con el robot inmóvil;
- acción activa o estado interno desconocido;
- objeto posiblemente sujeto sin zona de caída libre;
- cargador conectado, batería insuficiente o paros sin comprobar;
- robot, brazo o caja apoyados contra mobiliario;
- postura PICO cruzada o con codo/muñeca dentro del margen de autocolisión: la
  tarea `open_arm_before_home` no es una retirada segura demostrada;
- falta una persona con acceso inmediato al paro.

`--force-held-home` queda **RETIRADO**. El incidente demostró que aceptar la
caída de una caja no vuelve geométricamente segura la trayectoria: desde la
postura PICO real aumentó el contacto contra el torso antes de abortar.

### Fase D — fault o consignas latentes

1. No repetir una tarea parcial: este incidente demostró que puede abortar y
   dejar consignas latentes.
2. No escribir SDO, no publicar posiciones crudas y no reiniciar controladores
   individualmente para “probar”.
3. No rearmar un servo mientras otro eje conserve `cmd_pos` alejado de su
   posición real.
4. Si no existe un reset de tareas documentado y las consignas no se limpian,
   detenerse y usar únicamente el procedimiento de apagado completo aprobado.
5. `KEY1` aislado no es ese procedimiento. La discrepancia de apagado v0.2.0
   sigue pendiente de UBTECH.
6. Retirar un objeto con el robot apagado sólo corresponde a personal presente
   que pueda demostrar estabilidad mecánica; nadie debe quedar debajo de un
   brazo que pueda descender.

### Fase E — siguiente arranque

La secuencia usada en este incidente fue arrancar con el paro principal
accionado y la zona despejada. Es una observación, no un SOP universal aprobado.

1. Esperar el arranque completo de Motion y Vision.
2. Descubrir contenedores con `docker ps`; no reutilizar nombres históricos.
3. Leer el boot guard. Con el paro accionado debe reconocer
   `WaitEStopRelease` y salir con
   `NO_ACTION=waiting_for_physical_estop_release`; no reiniciarlo
   automáticamente si una recuperación pudiera mover cabeza o brazos.
4. Antes de liberar el paro: abrazaderas vacías, brazos sin contacto, zona
   completa despejada y una persona preparada para volver a accionarlo.
5. Después de liberarlo, no seleccionar PICO, UI ni `auto_task` hasta obtener
   una muestra de `/mc/actuator_state`.
6. Exigir error cero, `Operation Enabled`, velocidad cero y consignas
   coincidentes para todos los ejes.

### Fase F — decidir si hace falta mover

Si todos los ejes ya están cerca de cero, no enviar una trayectoria redundante:

```text
abs(position)<0,02 rad para brazos, cabeza, cintura y elevador
velocity=0
abs(cmd_pos-position)<0,01 rad
```

Si están sanos pero no en `home`, repetir primero:

```bash
./scripts/cruzr_recover_to_home.sh --check
```

El script canónico aplica ahora esta decisión de forma automática:

- muestra 20D sana y `abs(position)<0,02`: declara `home_measured` y envía
  **cero objetivos**;
- último estado demostrado de depósito/apertura del ciclo de caja: permite
  retirada del chasis y la tarea vendor, con un segundo gate antes y una
  medición 20D después;
- postura PICO, estado desconocido, caja posiblemente sujeta, intento de home
  no confirmado o evento posterior de fuerza/autocolisión/fault: bloquea antes
  de publicar un goal.

En la imagen v0.2.0 observada, `/mc/actuator_state` identifica elevador y
cintura como `11004/11003/11002/11001`. El gate acepta esos IDs como aliases
de los históricos `2001/2002/2003/3001`, exige una única muestra por eje lógico
y sigue requiriendo los 14 IDs de brazos. No relaja límites ni permite omitir
un eje.

`--fast` se conserva sólo por compatibilidad con los flujos exteriores, pero
ya no omite ninguna auditoría de seguridad de return-to-home. Sin argumentos,
el script equivale a `--check`; el movimiento requiere `--run` explícito.

## 6. Checklist breve para la persona junto al robot

Antes de cualquier transición que pueda habilitar par:

- [ ] objeto retirado o caída aceptada y zona inferior despejada;
- [ ] brazos sin apoyar contra robot, suelo, mesa o pared;
- [ ] abrazaderas vacías;
- [ ] robot estable y cargador desconectado;
- [ ] ambas personas fuera de la envolvente;
- [ ] una persona toca o alcanza inmediatamente el paro;
- [ ] terminal visible y un único cliente de control;
- [ ] criterio acordado para volver a accionar el paro.

Después:

- [ ] no hubo tirón, ruido, olor ni calentamiento;
- [ ] velocidades cero;
- [ ] error cero y `Operation Enabled` en todos los ejes;
- [ ] consignas coinciden con posiciones;
- [ ] resultado de acción, si existió, fue `status=4`/`SUCCEED`;
- [ ] estado físico final confirmado visualmente.

## 7. Cambios preventivos implementados

`scripts/cruzr_blue_workbin_cycle.sh` bloquea ahora antes de enviar objetivos
si detecta:

```text
error_code != 0
status con bit FAULT
estado distinto de Operation Enabled
abs(cmd_pos-position) > 0.01 rad
abs(velocity) > 0.02 rad/s
```

Además, `cruzr_recover_to_home.sh`:

- exige una muestra fresca de los 20 ejes de cuerpo y no confunde el inicio de
  una tarea con un home completado;
- busca eventos posteriores de exceso de fuerza, autocolisión,
  `MoveToGoalFailed`, fault de servo y EtherCAT `SAFEOP`;
- prohíbe `open_arm_before_home` desde `teleoperated_pose`, `unknown` o un
  intento anterior no confirmado;
- restringe la primitiva vendor a estados conocidos del ciclo de caja;
- revalida después del retroceso/reset y confirma el home final por posición,
  velocidad y consigna, no sólo por `status=4`;
- centraliza también `cruzr_blue_workbin_cycle.sh --home`, que ya no puede
  invocar directamente la trayectoria;
- retira `--force-held-home` y hace que `--fast` no salte gates.

Las regresiones locales se ejecutan con:

```bash
./scripts/cruzr_recover_to_home.sh --self-test
```

El 28-08 pasaron los casos home, non-home, consigna latente, eje en movimiento,
fault 4003, eje ausente, PICO bloqueado, intento de home fallido, fuerza
bloqueada y estado conocido de workbin. Esta validación fue exclusivamente
local con el robot completamente apagado; la nueva ruta de caja aún requiere
una prueba física controlada posterior y no autoriza el arranque actual.

El XML temporal de liberación sólo con el brazo derecho se retiró del robot y
del repositorio. No debe recrearse como workaround automático.

## 8. Pendientes para UBTECH

1. Tabla oficial de errores de servo `0x1001` y `0x2007`.
2. Procedimiento aprobado para inspeccionar y rearmar únicamente el servo 4003.
3. Significado y tratamiento de `MoveToGoalFailed`, state `7104050`.
4. Método oficial para limpiar consignas después de una acción abortada.
5. SOP de apagado y arranque aplicable a esta revisión física, incluida la
   función exacta de `KEY1` y la posición de los paros.
6. Confirmación de si un contacto/overload exige inspección mecánica antes de
   volver a teleoperar.

## 9. Punto de reanudación

Al cerrar el incidente:

- caja retirada y abrazaderas vacías por confirmación del operador;
- postura articular `home` demostrada sin una acción adicional;
- todos los actuadores sin error, `0x1237`, inmóviles y sincronizados;
- paros `0,0`, cargador desconectado, baterías suficientes;
- `/mc/manipulation/action` con un servidor y controladores requeridos running;
- boot guard `failed` por `unexpected_control_state_unknown` y Control Center
  pendiente de revalidación;
- ninguna nueva teleoperación autorizada por este documento.

Antes de otro movimiento: comprobar Control Center, repetir ambos `--check`,
inspeccionar visualmente hombro izquierdo/abrazaderas y hacer una prueba vacía
de amplitud mínima con persona en el paro.

### Punto de reanudación vigente tras el incidente del 28-08

El punto anterior queda histórico. El estado vigente es:

- apagado lógico aceptado por `/emb/pm_shutdown` con `success=True`;
- Motion y Vision sin respuesta; pantalla y luces confirmadas apagadas;
- `KEY1` pulsado únicamente después de esa confirmación;
- chasis apagado e indicador verde apagado;
- postura no `home`, con brazo izquierdo apoyado contra el torso sin presión
  apreciable antes del apagado; robot y brazos estables al final;
- abrazaderas vacías, cargador desconectado y zona de descenso despejada por
  confirmación del operador;
- FT izquierdo disparado a `-370,944 N` durante la apertura previa;
- faults 4002/4003/4004 observados antes del reinicio automático;
- no se rearmó ningún servo ni se envió otra trayectoria.

No encender para “probar”. El siguiente arranque debe comenzar con paro
accionado, abrazaderas vacías, cargador fuera, zona completa despejada y una
persona junto al paro. Después hay que descubrir contenedores desde cero y,
antes de liberar el paro o seleccionar modo, demostrar EtherCAT/controladores,
errores, status, velocidad y deltas posición–consigna. No ejecutar `home` ni
teleoperación hasta resolver una retirada segura específica para esta región
de postura.

### Punto de reanudación vigente tras el arranque del 03-09

El punto del 28-08 queda histórico. Se completó un shutdown lógico y un ciclo
de alimentación supervisado con el E-stop principal accionado. Control Center
pasó `WaitEStopRelease→SelfChecking→JoystickMode`; al liberar el paro, el
operador confirmó estabilidad y ausencia de movimiento inesperado. Self-check
y `StartMotion` terminaron con éxito.

La comprobación viva final, sin objetivos, registró:

```text
ACTUATORS_OPERATION_ENABLED=1
ESTOPS=0,0
CHARGER=disconnected
ACTIONS=ready
ACTUATOR_BODY_COUNT=20
ACTUATOR_ARM_COUNT=14
BODY_MAX_ABS_POSITION=0.002684
ARMS_MAX_ABS_POSITION=0.000959
BODY_MAX_ABS_VELOCITY=0.000000
BODY_MAX_ABS_COMMAND_DELTA=0.002684
MEASURED_HOME=1
RECOVERY_ROUTE=already-home,no-motion
```

El guard de arranque se corrigió e instaló en Vision con hash
`6c3cbe48…9287b`; backup
`/home/walker/cruzr-v020-boot-guard-backups/20260903T113735`. Su `--check`
confirmó x86 3/3, cámaras 2/2, `JoystickMode`, seguridad `0 0 0` y
`movement=none restart=none`. Antes de cualquier movimiento debe repetirse el
preflight físico; esta evidencia no valida una trayectoria de recuperación
desde una postura distinta de home.
