# Transferencia de una caja entre dos mesas con AprilTag

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

**2026-09-09 — CONFIRMACIÓN PRESENCIAL del depósito de las 10:52 UTC:**
el usuario confirmó caja apoyada estable y ambas abrazaderas libres de contacto.
El depósito queda confirmado físicamente; HOME sigue pendiente. Esta confirmación
no valida la navegación ni el ciclo completo de transferencia.

**2026-09-09 10:52 UTC — VERIFICADO por Motion, depósito aislado en mesa 2; confirmación física final PENDIENTE:**
el usuario confirmó caja justo encima de la mesa, con toda su base dentro de
los márgenes, registró de nuevo la referencia fresca y pidió depositarla.
Se ejecutó `cruzr_blue_workbin_cycle.sh --deposit-held --yes` tras --verify-grasp,
lectura de postura, paros/cargador/baterías y comprobación nativa de writers=0.
Sólo tarea `cruzr/blue_workbin_auto_deposit`, goal
`cc47207e-6274-4121-b686-c860eae8a117`, SUCCEED/state1101001/status4, exit0.
Plantillas ya presentes: no instalación nueva ni cambios de primitivas.
Postlectura: 20 articulaciones válidas, velocidad0, delta consigna máximo
0,001751 rad; twist de base0; MEASURED_HOME=0. Brazos abiertos, sin ordenar
navegación, retirada ni HOME. Baterías antes del depósito 74,1/75,6 %.
Nueva referencia registrada a 10:49:56 UTC: X=-0,327576313007 m,
Y=1,06406329955 m, yaw=1,68192970908 rad; capture_method=volatile-stamped-v2.
El depósito aislado no valida aún el ciclo completo ni resuelve el error
auxiliar VSLAM de la navegación anterior. Próximo paso: confirmar caja apoyada
estable y abrazaderas libres antes de preparar la recuperación HOME.
Evidencia: `../Humanoide-vla-evidence/20260909T105221Z_MESA2-DEPOSIT-ONLY/`.

**2026-09-09 — VERIFICADO offline, variante de transferencia sin AprilTags; enseñanza/prueba física PENDIENTES:**
se añade `scripts/cruzr_blue_workbin_table_transfer_no_tag.sh`, wrapper del
orquestador con --without-apriltag. Conserva detector workbin para recoger,
perfil de percepción de carga, depósito por contacto y recuperación HOME.
No requiere ni invoca el alineador, servicio o tópico AprilTag. Todos los modos
--check/--stage-held/--run/reanudaciones mantienen su separación de etapas.
--stage-held termina en la premesa enseñada, sin aproximar ni depositar.

--teach-mesa2 --approach-distance METROS lee tres poses estables y registra
la pose actual de base como depósito, más una distancia elegida de 0,10–1,20 m.
No mueve ni posiciona al robot. Calcula premesa detrás según yaw; perfil JSON
local ligado a nombre/tipo de mapa y huella de umap.json/user/task.json.
No sobrescribe perfiles. El ejemplo contiene null en referencias no conocidas
y no permite ejecutar. Cada ejecución valida y copia el perfil antes de conectar;
no inventa coordenadas ni convierte la enseñanza en aprobación geométrica.

El flujo navega a premesa y verifica X/Y/yaw, comprueba posición antes de avanzar,
parte la aproximación en tramos iguales de hasta 0,60 m y vuelve a comprobar mapa
tras cada tramo. Fuera de tolerancia, avance fallido o mapa cambiado bloquean
el depósito; no hay reintentos ni correcciones automáticas. Valores iniciales
0,05 m y 0,05 rad, pendientes de confirmar dentro del margen físico de la mesa.
El perfil usa --fast; --fluid queda reservado a la variante AprilTag.
Se mantiene mapa preparado sin carga/relocalización automática. Los nuevos
modos de map_route leen referencia, comprueban pose o navegan una pose numérica;
validan números/ángulos antes de conectar y propagan fallos de lecturas incluso
dentro de sustituciones Bash. La huella no detecta mesas movidas ni certifica SLAM.

Validación: 91 tests offline, sintaxis Bash, self-test del recuperador y diff check.
Incluye ausencia total de dependencias AprilTag, enseñanza sin movimiento, perfil
incompleto/mapa distinto, segmentación/orientación, estabilidad de pose, rechazo
tras avance y fallo de navegación con restauración. Sin SSH/ROS/movimiento real,
instalación remota, cambios de velocidades vendor, commits ni push.
Próximo paso: enseñar pose adecuada con montaje/postura de caja repetibles y
mesas fijas; después --check y prueba supervisada --stage-held/--resume-held.
[Guía sin AprilTags](TRANSFERENCIA_CAJA_ENTRE_MESAS_SIN_APRILTAG.md).
Rollback: retirar selectivamente wrapper/opción/módulo y modos nuevos comparando
con before/; conservar cambios anteriores del usuario. Evidencia:
`Humanoide-vla-evidence/20260909T090753Z_TABLE-TRANSFER-NO-APRILTAG/`.

**2026-09-09 — VERIFICADO offline, revisión del flujo de transferencia; prueba física PENDIENTE:**
se corrigen fallo oculto de restauración de percepción, reintento que añadía
retroceso y cambiaba destino, aproximación no anunciada en --stage-held,
mensajes incorrectos de caja tras interrupción y repetición posible de HOME.
Se retira caché fluida entre ejecuciones; --check/transferencia no cargan ni
relocalizan mapa. --fast conserva salud fresca antes de acciones/verificación
de agarre. Preflight usa gate estricto 20D y cuatro lecturas de seguridad en
paralelo. Historial de agarre acotado al arranque del contenedor, árbol terminado
y sin tareas/fallos posteriores. Perfil de percepción anterior exige restaurar.
Se guardan logs por etapa y códigos de fallo; no se reintenta navegación.

68 tests sin robot, self-test HOME, sintaxis Bash y diff check pasaron. Tres
regresiones fallan con la copia anterior y pasan tras la corrección. Flujo
normal del padre: 18→12 invocaciones al retirar cuatro verificaciones de agarre
y dos mediciones de tag duplicadas; ahorro real de tiempo sin medir.
No hubo conexión, movimiento, cambio remoto, velocidad/tolerancia nueva ni
commit. Próximo paso: mapa previamente preparado, --check conectado y prueba
supervisada --stage-held/--resume-held, con calibración de mesa/tag comprobada.
Detalles, límites, pruebas y rollback en
[revisión offline](../reviews/2026-09-09_WORKBIN_TABLE_TRANSFER_OFFLINE.md).
Evidencia: `Humanoide-vla-evidence/20260909T083451Z_TABLE-TRANSFER-OFFLINE-REVIEW/`.

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

**2026-09-09 — VERIFICADO, petición de recuperar anillo blanco: dos avisos activos:**
consulta 07:15–07:16 UTC de `fault_current` y catálogo instalado confirma
`02029001` (fallo al guardar mapa durante cartografía, MESAS3) y `00001001`
(aviso de batería baja, ocurrido 06:54:54 UTC). SOC actuales 27,0/27,6 %,
ambas descargando. `get_map_name` confirma MESAS2 y `check_state` devuelve
FSM_WAITNAVIGATE. El cambio anterior de mínimo a 20 % es local a los scripts;
no modifica el aviso de batería de Control Center. No atribuir todo el rojo
al fallo histórico de mapa ni prometer blanco eliminando sólo ese aviso.
El binario contiene `fault_solve`, descrito como «Simulate a fault solving»;
no se ejecutó porque simular resolución no demuestra recuperación real.
No se alteraron fault.db, expresión facial, umbrales, firmware ni estados;
no hubo reinicios, navegación o movimiento. El catálogo indica procedimiento
pendiente de confirmar para ambos códigos; no se identificó un procedimiento
normal de reconocimiento del aviso de guardado en lo inspeccionado.
PENDIENTE cargar físicamente las baterías y verificar resolución del aviso
00001001, además de recuperar/retirar por procedimiento válido el aviso de
mapa. Umbral exacto de desactivación e histéresis no verificados. Anillo blanco
NO conseguido ni afirmado; ambos avisos permanecen activos al cierre.
Evidencia: `Humanoide-vla-evidence/20260909T071558Z_RED-RING-ACTIVE-FAULTS/`.

**2026-09-09 — VERIFICADO en software y percepción, corrección de ventana lejana MESAS2:**
por petición «corrige ese bloqueo», `validate_approach_samples` en
`cruzr_blue_workbin_cycle.sh` admite y mínimo 0,00 m solamente si z>1,15 m.
Para z≤1,15 m conserva y mínimo 0,10 m; se mantienen y máximo 1,10 m,
z 0,65–1,80 m, centrado, coherencia entre muestras y orientación. Rechaza
además cualquier coordenada/cuaternión no finito. Es una ampliación acotada
del filtro perceptivo lejano motivada por la imagen y pose de MESAS2;
no constituye validación geométrica ni autorización de agarre a esa distancia.
El agarre conserva y=0,20–0,75 m, z=0,65–1,15 m y centrado ±0,035 m;
el planificador también conserva su control previo a extender brazos.
En `cruzr_blue_workbin_carry_back.sh`, los reintentos dicen «pose visual
admisible» y remiten al motivo concreto, sin atribuir todo rechazo a ruido.
Verificación: sintaxis Bash, diff sin errores de espacios y 8 tests offline
(`scripts/test_workbin_approach_window.py`): muestra observada, fronteras
lejanas/cercanas, no finitos, dispersión, cuaternión y separación entre
aproximación y agarre. Consulta real `--measure-box` finalizó código 0:
`BOX_POSE_CAMERA=0.167983 0.044992 1.741459 -4.614227` (m y grados).
Preflight: baterías 28,0/28,4 %, paros 0/0, cargador desconectado, acciones ready.
No se ordenó movimiento, ni cambio de firmware, configuración remota o mapa.
Scripts no estaban ejecutándose al editar. Cambios previos del usuario conservados.
Reversión selectiva: restaurar y mínimo fijo 0,10 m en el filtro de
aproximación; no revertir el archivo completo porque contiene otros cambios.
PENDIENTE prueba física completa: despejar persona/cables/equipo vistos en
la cámara y verificar de nuevo la zona y postura antes de ejecutar `--run`.
Evidencia: `Humanoide-vla-evidence/20260909T071047Z_APPROACH-WINDOW-FIX/`.

**2026-09-09 — VERIFICADO/OBSERVADO, cámara y detector consultados por Wi-Fi:**
ruta a Vision 192.168.11.3 vía 192.168.42.2, interfaz wlx80afcad40bd6.
Captura por suscripción a `/sensor/camera/stereo_left/image/raw` (Image6m,
yuv422, 1920×1536); consulta exclusivamente perceptiva a
`/cv/task/transport_action`, cámara head, box_size 0,60×0,40×0,22 m.
Resultado `ok=True`, status 4, workbin, marco
`stereo_left_rectified_optical_frame`: x=0,164391, y=0,050471,
z=1,730504 m. Imagen `/cv/pose_6d_info/segment` muestra el volumen detectado
sobre la caja azul visible en la mesa; dimensiones dibujadas son las del modelo
solicitado, no una medición independiente. El topic segment tiene stamp=0:
se conserva hora de adquisición y coincidencia de coordenadas con esta consulta,
sin atribuirle sincronización exacta con la captura de cámara anterior.
Se confirma que la caja visible es detectada; el rechazo previo corresponde
al mínimo y=0,10 m del script de aproximación, no a ausencia de detección ni
a distancia z fuera de rango. La imagen también muestra una persona junto
a la caja y cables/equipo en el suelo delante de la mesa: la zona debe despejarse
y verificarse de nuevo antes de movimiento. No inferir distancias libres de esta foto.
No se ordenó movimiento ni se modificaron límites/configuración; suscripciones
finalizadas y acción de percepción terminada. Pendiente revisar la ventana de
aproximación frente a esta disposición sin dar por validado el ciclo completo.
Evidencia: `Humanoide-vla-evidence/20260909T070402Z_BOX-CAMERA/`
(`head_camera.png`, `detector_segment.png`, respuestas originales).

**2026-09-09 — OBSERVADO, intento físico completo MESAS2/uslam interrumpido antes del agarre:**
con autorización explícita y confirmación de caja apoyada en mesa 1 y referencia
AprilTag/altura de mesa 2 conservadas, se ejecutó transferencia `--run --yes`.
Preflight completo OK; baterías 30,0/29,4 %, ambos paros 0 y cargador desconectado.
Motion confirmó `move_head_lower` SUCCEED. Primera medición de aproximación
rechazada tres veces: (y,z) = (0,051;1,734), (0,045;1,746), (0,049;1,737) m.
El rechazo concreto es **y < 0,10 m en el marco de cámara**; z sí cumple
0,65–1,80 m. El mensaje final «detección no estable» es genérico: no demuestra
inestabilidad entre pares porque la validación falla antes de compararlos.
No se ordenaron agarre, avance de aproximación, transporte ni depósito.
El script terminó código 1, etapa `agarre-mesa1`, 112 s; no se reintentó ni
se ordenó HOME. Lectura posterior 07:00:44 UTC: 22 actuadores con velocidad 0,
sin error_code, odometría con twist 0 y 0 escritores de RobotCommand.
Caja no agarrada por este intento; cabeza queda bajada según la acción realizada.
Perfil de carga estaba desactivado y no se alcanzó su activación.
PENDIENTE comprobar identificación/encuadre de la caja y geometría de la escena
antes de repetir desde el inicio; no usar `--resume-held` ni ampliar límites
basándose sólo en estas lecturas. Ciclo completo todavía NO validado.
Sin modificaciones remotas de configuración ni cambios de umbral en este intento.
Evidencia: `Humanoide-vla-evidence/20260909T070044Z_MESAS2-FULL-ATTEMPT/` (`transfer.log`,
actuadores, odometría y grafo de comandos posteriores). La cabeza bajada no
constituye HOME completo; comprobar postura antes de otra ejecución.

## Objetivo y alcance

**Actualización 09-09-2026 — batería mínima 20 % por petición del propietario:**
las comprobaciones del ciclo workbin y de navegación exigen al menos 20 %
en **cada batería**, también en retorno/reanudación. Sustituye los mínimos
anteriores 30 % al inicio y 25 % en retorno citados en el histórico inferior.
Se aplica a los scripts que reutilizan ese ciclo, incluida recuperación HOME.
No cambia protecciones del firmware/BMS ni garantiza carga para completar
una misión; rechaza valores inferiores a 20 % en los puntos de comprobación.
Verificado localmente sin ejecutar movimiento.

**Recuperación 09-09-2026 — MESAS2 mediante localización LiDAR (`uslam`):**
Verificación final: `--check` código 0, `TABLE_TRANSFER_CHECK_OK`; todos los
archivos de MESAS2 conservan sus hashes. Baterías finales 31,2/30,4 %.
se verificaron `NAVIGATION_READY`, `FSM_WAITNAVIGATE` y publicación de pose.
El detector workbin y AprilTag son independientes del mapa visual VSLAM.
Para conservar la selección en los scripts:

```bash
export CRUZR_MAP_NAME=MESAS2
export CRUZR_MAP_TYPE=uslam
./scripts/cruzr_blue_workbin_table_transfer.sh --check
```

`CRUZR_MAP_TYPE` admite `auto` (predeterminado), `uslam` y `fusion`; carga y
relocalización reciben el modo explícito. Cachés de preparación incluyen el
modo. Se utilizó el modo instalado del fabricante, sin cambiar LiDAR,
costmaps, bumpers, paros ni límites. Reiniciados únicamente VSLAM y gestor de
navegación, después restaurado MESAS2/uslam. No hubo ruta ni manipulación.
El aviso `02029001` del guardado visual fallido sigue retenido en Control
Center: no representa una reparación del mapa visual ni se borró del registro.
La primera comprobación completa pasó. Repetición final con archivos estables
tras un error local por editar la ayuda durante un check en curso. No editar
scripts hasta que termine cualquier proceso Bash que los ejecute.
Última batería 31,5/30,4 %, próxima al mínimo 30 %: conservar el gate y cargar
antes de una misión con margen insuficiente. Comprobar físicamente la pose
dibujada antes de navegar; el éxito de relocalización global no certifica por
sí solo la correspondencia física. Disposición nueva y transferencia física
siguen pendientes de validar. Evidencia externa:
`Humanoide-vla-evidence/20260909T063738Z_MAPPING-REPAIR/`.

**VERIFICADO 09-09-2026, guardado MESAS3:** 2D guardó, pero VSLAM abortó
`SAVE_MAP_FAILED` con cero poses (`rigs size: 0`); CC añadió `02029001`, fallo
de guardado de mapa. El mapa visual no se produjo. Después se cargó MESAS2
(`LOAD_MAP_FINISHED`), sin evidencia de resolución de los avisos ni de
localización recuperada. Pendiente corregir captura visual antes de otro
recorrido; no usar MESAS3 como mapa fusion validado. Evidencia externa:
`Humanoide-vla-evidence/20260909T063514Z_MAP-RETURN/`. Sin cambios remotos.

**Revisión 09-09-2026, diagnóstico de grabación:** el mapa 2D acumula 11 poses.
El árbol instalado guarda primero 2D y después ejecuta VSLAM `save_map`;
la configuración contiene `enable_mapping_callback=false`. No concluir fallo
de captura sólo por visualización vacía durante grabación. ROS2/ROSA discrepan
sobre publicadores de pose; no está demostrada su ausencia. Siguiente prueba:
guardar el tramo bajo nombre nuevo desde UI y verificar el resultado visual
antes de repetir un recorrido completo. Sin cambios remotos. Evidencia externa
`Humanoide-vla-evidence/20260909T062910Z_MAPPING-DIAG/`.

**OBSERVADO 09-09-2026, 06:27 UTC:** durante el primer tramo VIO muestra unos
0,45 m de variación entre poses, pero persiste `cannot get rig from map`.
No se ha demostrado crecimiento del mapa visual pese a `MAPPING_RUNNING`.
Pausar el recorrido largo y diagnosticar inserción antes de dar la captura por
válida. Evidencia externa `Humanoide-vla-evidence/20260909T062710Z_MAPPING-PROGRESS/`.

**OBSERVADO 09-09-2026, nueva captura:** `MAPPING_RUNNING` visual y
`MAPPING_NORMAL` 2D confirmados; llegada de imágenes y cálculo VIO activos.
El visualizador todavía reporta `cannot get rig from map` en la muestra
inicial. Pendiente demostrar incorporación de poses al mapa durante el
recorrido; no confundir estado de grabación con calidad del mapa guardado.
Evidencia externa: `Humanoide-vla-evidence/20260909T062503Z_MAPPING-LIVE/`.

**OBSERVADO 09-09-2026, 06:16–06:17 UTC:** el operador repitió localización
forzada; navegador registró éxito en modo fusion, pero VSLAM siguió LOST con
cero puntos del mapa emparejados. Hay extracción activa de características.
El mapa fuente visual MESAS2 contiene sólo 13 puntos PCD y una fila de poses;
cobertura visual insuficiente es una INFERENCIA a revisar, no un fallo de
cámara demostrado. Preparar nueva captura visual conservando el mapa actual;
ningún mapa se borró o modificó durante este diagnóstico. Evidencia externa:
`Humanoide-vla-evidence/20260909T061650Z_LOCALIZATION-AFTER-FORCED/`.

**OBSERVADO 09-09-2026, 06:10–06:11 UTC:** después de las comprobaciones de
MESAS2, diagnóstico del anillo rojo confirma `02039001` y VSLAM
`LOCATION_LOST`; CC registra el cambio `logo -> warning-red`. El catálogo
instalado identifica un fallo de relocalización visual basada en características.
LiDAR sigue en `LocateRunning` y ambos paros están a `0`. La validación de
waypoints y una carga de mapa exitosa no demuestran localización visual actual.
Pendiente recuperar y comprobar localización antes del transporte autónomo.
Sólo lecturas; no se enviaron navegación, relocalización ni reinicios.
Evidencia externa: `Humanoide-vla-evidence/20260909T061055Z_RED-FACE/`.

Actualización 09-09-2026: el mapa se selecciona mediante `CRUZR_MAP_NAME`;
si no se define se conserva `test_route_01`. Se hereda en todos los subprocesos
de transferencia y ruta corta. Para mantener la selección entre comandos:

```bash
export CRUZR_MAP_NAME=mesas_20260909
./scripts/cruzr_blue_workbin_table_transfer.sh --check
```

El nombre admite 1–128 letras ASCII, números, guiones y guiones bajos,
empezando por letra o número. Un valor vacío o inválido se rechaza. El mapa
debe existir: esta opción no crea ni copia mapas. El preflight de transferencia
exige únicamente `MESA2_PRE` en `umap.json`, con posición y orientación finitas.
Admite `mode="logo_nav"` o el formato observado en MESAS2:
`type="mapping_marker"` con `mode=""`. En este último caso la navegación directa
utiliza las coordenadas guardadas mediante `free_nav`; no cambia el mapa ni
interpreta ese ID como un `logo_nav`. `task.json` puede tener `target_points: []`. La navegación
directa comprueba el waypoint solicitado. Sólo el recorrido histórico mantiene
la secuencia `START`, `PASO1`, `PASO2`, `PASO 3`, `PASO4`, `FINISH` en
`task.json`. Las referencias AprilTag
y la distancia de aproximación siguen siendo las de la disposición anterior.
El modo `--check` puede activar el mapa y relocalizar, aunque no ordena
desplazamientos. La caché fluida no se reutiliza al cambiar de mapa.

Esta guía define la preparación y la secuencia prevista para recoger el
contenedor azul en la mesa 1, transportarlo hasta la mesa 2, depositarlo y
terminar con el robot en `home`.

La extensión para recoger a baja altura, volcar contenido y depositar la caja
vacía a otra altura, con varios tamaños y poses, se planifica en
[`../plan_de_trabajo.md`](../plan_de_trabajo.md). Esa extensión todavía no es
una capacidad física validada.

La arquitectura recomendada es:

```text
detector workbin -> agarre -> MESA2_PRE -> alineación AprilTag 113
                 -> depósito -> retirada -> home
```

El detector especializado `workbin` reconoce y localiza la caja. El AprilTag
no reconoce la caja: proporciona una referencia geométrica para la alineación
fina frente a la mesa 2. GR00T/VLA no interviene en esta operación.

> **Estado actual:** la detección AprilTag está instalada, pero los scripts de
> transporte todavía no consumen su pose para corregir el chasis. No debe
> intentarse la misión autónoma completa hasta implementar y validar ese
> alineador.

## 1. Etiquetas y puntos de navegación

| Estación | AprilTag | Lado negro medido | Necesidad | Función |
| --- | ---: | ---: | --- | --- |
| Mesa 1 | 112 | 75 mm | Opcional | Referencia de origen y recuperación futura |
| Mesa 2 | 113 | 73,5 mm | Recomendada | Alineación fina para el depósito |

La unidad revisada usa la familia `tag36h11`. En la configuración de
validación BYD aparecen los IDs 112–115 con un tamaño de `0,10 m`, aunque la
validación integrada está desactivada mediante `use_apriltag_val: false`. Los
tags finalmente instalados deben detectarse con sus medidas reales: `0.075`
para el ID 112 y `0.0735` para el ID 113. Para esta guía se utiliza el detector
AprilTag independiente.

También debe crearse en el mapa `test_route_01` un waypoint llamado
`MESA2_PRE`. Este punto realizará únicamente la aproximación global; el
AprilTag se utilizará después para la corrección local.

## 2. Generar los AprilTags en Ubuntu

Los diseños ya generados se obtienen del repositorio oficial
[AprilRobotics/apriltag-imgs](https://github.com/AprilRobotics/apriltag-imgs/tree/master/tag36h11).
No es necesario generar una familia personalizada.

Los siguientes comandos se ejecutan en el PC Ubuntu:

```bash
sudo apt install -y git python3-pil inkscape

cd /home/lacuna/proyectos/Robots/Humanoide
mkdir -p assets/apriltags

apriltag_source="$(mktemp -d)"

git clone --depth 1 \
  https://github.com/AprilRobotics/apriltag-imgs.git \
  "$apriltag_source/apriltag-imgs"

python3 "$apriltag_source/apriltag-imgs/tag_to_svg.py" \
  "$apriltag_source/apriltag-imgs/tag36h11/tag36_11_00112.png" \
  assets/apriltags/mesa1_tag112.svg \
  --size=125mm

python3 "$apriltag_source/apriltag-imgs/tag_to_svg.py" \
  "$apriltag_source/apriltag-imgs/tag36h11/tag36_11_00113.png" \
  assets/apriltags/mesa2_tag113.svg \
  --size=125mm
```

El conversor utilizado es el
[`tag_to_svg.py` oficial](https://github.com/AprilRobotics/apriltag-imgs/blob/master/tag_to_svg.py).

Generar los PDF:

```bash
inkscape assets/apriltags/mesa1_tag112.svg \
  --export-filename=assets/apriltags/mesa1_tag112.pdf

inkscape assets/apriltags/mesa2_tag113.svg \
  --export-filename=assets/apriltags/mesa2_tag113.pdf
```

## 3. Imprimir y medir

Imprimir cada PDF por separado con estas opciones:

- papel A4 blanco y mate;
- escala `100 %` o `Tamaño real`;
- desactivar `Ajustar a página`;
- no plastificar con acabado brillante;
- conservar completo el margen blanco;
- pegarlo sobre una superficie plana y rígida.

El SVG completo mide 125 mm, pero el cuadrado exterior negro detectable debe
medir 100 mm. La biblioteca define `tag_size` como la distancia entre las
esquinas de detección, no como el tamaño exterior incluido el margen blanco.
La definición oficial puede consultarse en
[Pose Estimation](https://github.com/AprilRobotics/apriltag#pose-estimation).

Después de imprimir, medir el lado negro con una regla. Si, por ejemplo, mide
99,2 mm, debe utilizarse `tag_size: 0.0992` en lugar de `0.10`.

## 4. Montaje físico en las mesas

Para la mesa 2:

1. Fijar el ID 113 en un panel vertical rígido unido a la mesa.
2. Colocarlo detrás de la mesa y aproximadamente centrado.
3. Dejarlo visible por encima de la caja transportada.
4. Mantener su plano paralelo al borde frontal de la mesa.
5. Evitar que el panel pueda desplazarse respecto a la mesa.
6. Registrar la altura de su centro y sus desplazamientos lateral y
   longitudinal respecto al centro de depósito.

No conviene colocarlo en el frontal bajo de la mesa porque la caja agarrada
podría ocultarlo. El ID 112 puede montarse de igual forma en la mesa 1, pero no
es necesario para la recogida actual: el detector `workbin` ya centra el robot
respecto a la caja.

Para la primera prueba, la mesa 2 debe ser estable, soportar la carga y tener
la misma altura verificada que la mesa 1. Una altura distinta exige adaptar y
validar por separado la trayectoria vertical de depósito.

## 5. Crear `MESA2_PRE` en el mapa

En `http://192.168.11.3/map/navigation`, sobre `test_route_01`:

1. Crear un waypoint llamado `MESA2_PRE`.
2. Situarlo aproximadamente entre 0,8 y 1,0 m delante de la mesa 2.
3. Orientarlo hacia el AprilTag 113 y perpendicular al borde de la mesa.
4. Dejar espacio para los giros considerando la anchura total de la caja.
5. No situarlo pegado a la mesa: la aproximación fina se hará con el tag.
6. Guardar el mapa y probar la navegación hasta el punto sin caja y con los
   brazos en `home`.

Los scripts calculan una huella de `umap.json`, `task.json` y de las instancias
del navegador. Si el mapa cambió o se reinició el runtime, lo recargan y
relocalizan una sola vez antes de navegar. Para sincronizar y navegar sin
entrar manualmente al Docker:

```bash
./scripts/cruzr_blue_workbin_map_route.sh \
  --navigate-waypoint MESA2_PRE --yes --fast
```

Puede añadirse `MESA1_PRE` como referencia de origen, aunque la aproximación
visual actual puede seguir utilizándose en la mesa 1.

## 6. Comprobar el detector AprilTag

Conectarse desde el PC mediante la Wi-Fi del robot:

```bash
ssh walker@192.168.42.2
docker exec -it walker-ros.ros2-1 bash
source /opt/ros/humble/setup.bash
```

Activar la detección del ID 113 usando el tamaño físico medido:

```bash
ros2 service call /apriltag/start_detecting \
  sensor_task_msgs/srv/AprilTagStartDetecting \
  "{start_detecting: true, img_topic_name: '/sensor/camera/stereo/color/raw', tag_id: 113, tag_size: 0.0735, tag_frame: 'mesa2_tag113'}"
```

Observar los resultados en otro terminal ROS 2:

```bash
timeout 20 ros2 topic echo \
  /sensor/camera/stereo/april_tag/results
```

Comprobar:

- ID 113 correcto;
- familia `tag36h11`;
- ausencia de correcciones Hamming inesperadas;
- `pose.header.frame_id` conocido;
- distancia y orientación físicamente razonables;
- poca variación de pose con el robot inmóvil.

Detener la detección:

```bash
ros2 service call /apriltag/start_detecting \
  sensor_task_msgs/srv/AprilTagStartDetecting \
  "{start_detecting: false, img_topic_name: '/sensor/camera/stereo/color/raw', tag_id: 113, tag_size: 0.0735, tag_frame: 'mesa2_tag113'}"
```

El contrato general del detector también está recogido en
[CATALOGO_FUNCIONALIDADES_CRUZR_S2.md](CATALOGO_FUNCIONALIDADES_CRUZR_S2.md#7-detector-apriltag).

## 7. Calibrar la pose de depósito

La calibración debe hacerse inicialmente sin transportar la caja:

1. Dejar la mesa 2 vacía, fija y estable.
2. Navegar hasta `MESA2_PRE` con los brazos en `home`.
3. Colocar la cabeza siempre en la misma postura reproducible.
4. Aproximar lentamente el robot hasta una pose válida para depositar.
5. Registrar al menos 20 poses consecutivas del AprilTag 113.
6. Guardar la mediana de posición y orientación como
   `MESA2_DROP_TARGET`.
7. Alejar el robot y repetir la aproximación al menos tres veces.

El alineador deberá comparar la pose observada con `MESA2_DROP_TARGET` y
corregir X, Y y giro mediante movimientos pequeños y limitados. Como criterio
inicial de desarrollo puede utilizarse un error máximo de 20 mm y 2 grados,
pero estos límites no son valores certificados y deben validarse físicamente.

La calibración realizada el 14 de agosto de 2026 utilizó tres aproximaciones
independientes de 20 muestras. La diferencia máxima entre ejecuciones fue de
18,30 mm y 1,62 grados. La referencia consolidada es:

```text
MESA2_DROP_TARGET
POSITION_M=-0.027403734 0.021092044 1.138346576
QUATERNION_XYZW=-0.976405603 0.011121442 -0.014522428 0.215168563
RPY_DEG=-155.126 -1.351 -1.603
TAG_ID=113
TAG_SIZE_M=0.0735
FRAME=stereo_left_rectified_optical_frame
```

Una medición independiente realizada después de integrar el alineador dio un
error planar de 0,43 mm, un error angular de 0,38 grados y `PLAN=READY`.

Al sujetar la caja, la postura de transporte cambia la transformación entre
cámara y tag. Por ello se calibró una segunda referencia específica en la misma
pose física de depósito:

```text
MESA2_DROP_TARGET_HELD
POSITION_M=-0.022617825 -0.122600795 0.803420107
QUATERNION_XYZW=-0.975321264 0.009621669 -0.004721560 0.220530186
TAG_ID=113
TAG_SIZE_M=0.0735
FRAME=stereo_left_rectified_optical_frame
```

La referencia con carga procede de 20 muestras con desviaciones posicionales
de 0,017, 0,058 y 0,223 mm. Una lectura independiente previa al depósito dio
un error planar de 0,10 mm, 0,088 grados de error angular y `PLAN=READY`.

La cabeza debe adoptar exactamente la misma postura durante la calibración y
la ejecución. Si la caja oculta el tag, habrá que elevar o desplazar su soporte
antes de continuar.

## 8. Integración disponible

El orquestador `scripts/cruzr_blue_workbin_table_transfer.sh` implementa:

1. comprobación de paros, cargador, batería, mapa y detector;
2. centrado y agarre en la mesa 1;
3. retirada de 0,50 m;
4. navegación hasta `MESA2_PRE`;
5. detección estable del ID 113;
6. alineación local con `MESA2_DROP_TARGET`;
7. verificación de que la caja continúa sujeta;
8. aproximación final y depósito;
9. retirada de la mesa 2 y recuperación a `home`.

Comprobar la infraestructura con el mapa ya activo y localizado, sin cargar mapas ni mover:

```bash
./scripts/cruzr_blue_workbin_table_transfer.sh --check --fast
```

La primera prueba con caja debe detenerse en `MESA2_PRE`:

```bash
./scripts/cruzr_blue_workbin_table_transfer.sh --stage-held --fast
```

Este modo coge la caja, se separa de mesa 1 y navega a **1,08 m detrás de
`MESA2_PRE`**. Allí verifica el agarre y mide el tag 113. No aproxima, alinea
ni deposita. Después de confirmar que
la caja sigue estable, que el tag permanece visible y que mesa 2 está libre:

```bash
./scripts/cruzr_blue_workbin_table_transfer.sh --resume-held --fast
```

Cuando ambos modos hayan sido validados repetidamente puede ejecutarse el
ciclo completo con una sola confirmación:

```bash
./scripts/cruzr_blue_workbin_table_transfer.sh --run --fast
```

### Perfil fluido para demostraciones

El perfil `--fluid` mantiene el perfil conservador anterior sin cambios y
aplica estas optimizaciones solamente cuando se solicita expresamente:

- tolerancia planar y por eje de 50 mm para aceptar pronto una caja que ya
  está suficientemente centrada sobre una mesa con margen;
- tolerancia de oscilación del tag de 3,5 grados, manteniendo un rechazo duro
  por encima de 5 grados;
- tres muestras AprilTag, correcciones longitudinales de hasta 0,18 m y un
  máximo de cuatro iteraciones;
- una muestra del detector workbin durante las correcciones intermedias y dos
  muestras obligatorias inmediatamente antes del agarre;
- aproximación limitada a 0,12 m/s, con tramos de hasta 0,42 m. El retroceso
  utiliza siempre un único tramo odométrico de 0,50 m y, en modo fluido, queda
  limitado a 0,08 m/s;
- eliminación de verificaciones duplicadas del orquestador, conservando
  comprobaciones frescas de salud, agarre y localización;
- medición del tiempo empleado por cada etapa y del total.

Cada ejecución realiza el preflight completo; ya no reutiliza una caché de
180 segundos. El mapa y la localización deben estar preparados previamente.
Las cuatro lecturas independientes de paros/batería/cargador se realizan en
paralelo. El tiempo real se medirá con esta versión conectada; `TIMING_*` y
`TRANSFER_LOG_DIR` permiten localizar el coste y los fallos por etapa.

```bash
./scripts/cruzr_blue_workbin_table_transfer.sh --check --fluid
./scripts/cruzr_blue_workbin_table_transfer.sh --run --fluid
```

No existe un requisito de iniciar el segundo comando dentro de tres minutos:
ambos comprueban el estado actual. `--fluid` no omite el control completo antes
del depósito, ni autoriza un retroceso adicional por un obstáculo de navegación.
Si se interrumpe una etapa, revisar el resultado antes de elegir el modo de
reanudación. Un depósito o HOME interrumpido no debe repetirse automáticamente.

El alineador también puede comprobarse de forma independiente:

```bash
# Infraestructura y referencia; no mueve.
./scripts/cruzr_apriltag_mesa2_align.sh --check

# Pose actual y error respecto al objetivo; no mueve.
./scripts/cruzr_apriltag_mesa2_align.sh --measure

# Correcciones del chasis sin caja.
./scripts/cruzr_apriltag_mesa2_align.sh --align-empty

# Correcciones del chasis exigiendo un agarre vigente.
./scripts/cruzr_apriltag_mesa2_align.sh --align-held
```

Los componentes de bajo nivel que reutiliza el orquestador son:

```bash
# Centrar, sujetar y elevar la caja.
./scripts/cruzr_blue_workbin_carry_back.sh \
  --grasp-only --yes --fast

# Separarse 0,50 m de la mesa 1.
./scripts/cruzr_blue_workbin_carry_back.sh \
  --retreat-only --yes --fast

# Navegar de forma autónoma hasta la premesa de destino.
./scripts/cruzr_blue_workbin_map_route.sh \
  --navigate-waypoint MESA2_PRE --yes --fast

# Depositar cuando la alineación con la mesa 2 ya esté validada.
./scripts/cruzr_blue_workbin_cycle.sh \
  --deposit-held --yes

# Separarse y terminar en home.
./scripts/cruzr_recover_to_home.sh \
  --run --yes --fast
```

La recuperación anterior presupone que el depósito terminó, que las
abrazaderas están vacías y que el estado pertenece al ciclo de caja. El modo
histórico para una postura PICO no reconocida con caja prescindible era:

```bash
./scripts/cruzr_recover_to_home.sh --run --force-held-home
```

**RETIRADO EL 28-08:** `open_arm_before_home` produjo sobreesfuerzo y faults al
usarse desde una postura PICO cruzada. El script rechaza ahora esa opción; una
caja prescindible permite aceptar su caída, pero no autoriza una trayectoria
incompatible con la postura. Si PICO no terminó en home medido, conservar el
estado, aplicar la guía de recuperación tras contacto y no cambiar a
`auto_task` para volver a intentar la misma primitiva.

El intento de recuperación del 27-08 confirmó además que un servidor de acción
activo no demuestra que todos los ejes estén habilitados. Después del contacto
contra la mesa, el hombro izquierdo yaw `4003` conservó
`error_code=0x1001`/`status=0x0238` incluso después del reinicio; su habilitación
terminó en timeout. El preflight de `cruzr_blue_workbin_cycle.sh` lee ahora
`/mc/actuator_state` y rechaza cualquier articulación con error, bit FAULT o
sin `Operation Enabled`, mostrando `ACTUATOR_FAULT=...`. Este gate no tiene
override: una caja prescindible permite aceptar su caída, pero no permite
mover una cadena cinemática con un servo en fallo. Debe mantenerse el robot
estable y solicitar a UBTECH el significado y procedimiento oficial de
recuperación antes de resetear el eje o enviar `home`.

Una prueba excepcional posterior intentó separar únicamente el brazo derecho
50 mm en 6 s para soltar una caja prescindible. El servidor aceptó el objetivo,
pero lo terminó como `MoveToGoalFailed`/`status=6`; las posiciones y el fault
no cambiaron. El intento dejó, no obstante, consignas derechas latentes de
hasta 0,1043 rad. Por ello tampoco es seguro rearmar 4003 en caliente: al
recuperarse el eje podrían aplicarse esas consignas. El gate comprueba ahora
también `abs(cmd_pos-position) <= 0.01` rad. El XML temporal se retiró tanto del
robot como del repositorio. El siguiente paso seguro es descartar el estado de
mando mediante un apagado completo aprobado, volver a descubrir todo el stack
y no rearmar hasta demostrar posiciones/consignas coincidentes.

En la ejecución real, el operador retiró la caja durante el apagado y usó
`KEY1`; los brazos descendieron sin trayectoria. No se considera un método de
recuperación aprobado. El siguiente arranque, con el paro inicialmente
accionado, descartó tanto el fault de 4003 como las consignas latentes. Al
liberar el paro se verificaron todos los actuadores sin error,
`status=0x1237`, velocidades cero y posiciones/consignas dentro de ±0,003 rad
de cero. El robot ya estaba en `home` articular, por lo que no se envió otra
trayectoria. El boot guard sí terminó en `failed` por
`unexpected_control_state_unknown`; Control Center debe revalidarse por
separado antes de otra misión o teleoperación.

Si la alineación falla antes del depósito, el orquestador no abre los cogedores.
Debe conservarse la zona despejada y diagnosticarse el estado antes de
reanudar. No se debe lanzar de nuevo el ciclo completo con una caja ya sujeta.

## 9. Validación progresiva

La puesta en servicio debe realizarse en este orden:

1. Detectar el tag con el robot inmóvil: completado.
2. Navegar sin caja hasta `MESA2_PRE`: completado.
3. Calibrar y repetir tres veces la pose final: completado.
4. Validar el cálculo `PLAN=READY` en la pose objetivo: completado.
5. Probar `--align-empty` desde un desplazamiento inicial pequeño y controlado:
   pendiente de completar como ensayo independiente.
6. Ejecutar `--stage-held` y confirmar que el tag sigue visible con la caja:
   completado.
7. Calibrar `MESA2_DROP_TARGET_HELD` en la pose física de depósito: completado.
8. Ejecutar `--resume-held` con la caja vacía: completado; el depósito, el
   retroceso de 0,484 m y `cruzr/home` terminaron correctamente.
9. Ejecutar y repetir el ciclo completo `--run` únicamente después de obtener
   resultados
   consistentes.

Durante todas las pruebas de movimiento deben permanecer desconectados el
cargador y Ethernet, debe haber espacio libre para robot y caja, y una segunda
persona debe mantener preparado el paro físico. El detector, ROS 2 y estos
scripts no sustituyen una función de seguridad certificada.
