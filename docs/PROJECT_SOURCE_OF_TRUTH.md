# Cruzr S2 — fuente de verdad global del proyecto

**2026-09-10 — Limpieza del índice y credenciales locales (VERIFICADO offline).**
Por petición del propietario se prepara un commit de los cambios pendientes.
Se retiran del índice los dos paquetes 3D originales del proveedor: 130 archivos,
unos 107 MB, conservados en disco y con todos sus SHA256 sin cambios.
`.gitignore` añade esos directorios, secretos locales, entornos/cachés Python,
salidas de ROS/colcon y grabaciones. Se comprueban 12 rutas excluidas y seis
rutas de fuentes/ejemplos que siguen admitidas. Los modelos y las evidencias
externas deben respaldarse aparte para reproducir los análisis desde otro PC.
Tres scripts modificados dejan de incluir contraseña literal y usan un helper
ASKPASS con entorno o archivo privado ignorado; se conserva el acceso local
mediante `.secrets/cruzr_ssh_password`, permisos 600 en directorio 700.
No se cambian credenciales del robot ni se reescribe el historial de Git.
[Registro y restauración: OPS-01/PC-03](SYSTEM_CUSTOMIZATIONS.md).
Validación: 91 pruebas Python offline, pruebas JavaScript del visor y sintaxis
Bash/Python/XML/JavaScript correctas. No se conectó ni se ordenó nada al robot
para esta limpieza. La validación física pendiente de trayectorias no cambia.
Índice previo, fuentes anteriores, manifiesto y resultados de pruebas:
`../Humanoide-vla-evidence/20260910T122441Z_COMMIT-CLEANUP/`.

**2026-09-10 — Apertura adaptativa implementada en planificador; activación física PENDIENTE.**
Propietario solicita aplicar optimizaciones y no abrir de más. Nuevo
`plan_clamp_home_adaptive.py`: abre cada hombro sólo hasta `min(actual,−0,50rad)`,
conserva el lado más abierto y los demás ángulos, baja antes de cerrar, omite
etapas exactamente inmóviles y corrige pequeños errores corporales. Clasifica
sólo formas PICO/brazos abajo y dos familias corporales; rechaza otras posturas.
Siete casos auditados501muestras: límites y cotas nominales no locales positivos;
PICO cuerpo cero15,417s, flexionado18,544s, ya abierto13,876s. Hipótesis quintic.
Con error5° siguen25–35pares sin separación demostrada y la parada no está
acotada. **No se exportó/instaló una ruta ni se sustituyó HOME interno; reducir
apertura/tiempos en el robot sigue pendiente.** Los perfiles Motion conservan20s.
**Sí aplicado al ejecutor PC:** si actuadores sanos y JointState nuevos demuestran
HOME20D≤0,005rad e inmovilidad≤0,002rad/s, termina `ALREADY_HOME_MEASURED` sin
enviar trayectoria. Errores de lectura abortan; fuera de HOME conserva gate PICO.
Ocho pruebas nuevas del planificador y22del ejecutor pasan. Lectura realJointState
vacía/ROSA sin tipo fue rechazada; preflight posterior abortó por paro accionado.
Lecturas independientes confirman principal1/servo0. No se acredita una postura
actual ni ensayo del camino nuevo. Sólo lectura remota y cambios PC; cero
movimientos, instalaciones o reinicios. [Detalle y reanudación](teleoperation/CRUZR_HOME_ADAPTATIVO.md).
Backup/planes/consultas: `../Humanoide-vla-evidence/20260910T120838Z_ADAPTIVE-HOME/`.

**2026-09-10 — Corregida incompatibilidad del preflight con HOME abierto (VERIFICADO local y en vivo, sólo lectura).**
El ejecutor PICO 4× rechazaba `home.xml` SHA05174d2b…8cbe, aunque era exactamente
el overlay MOT-01 instalado. El preflight canónico de `cruzr_blue_workbin_cycle.sh`
conservaba únicamente el hash del HOME directo anterior. Ahora reconoce ambos
archivos exactos; para open-v3-20s exige además el hash de `libmeta_move.so`
comprobado por el instalador. No admite hashes arbitrarios ni cambia trayectorias.
El auditor E6.0G diferencia `PREFLIGHT_FAILURE=config-hash` y deja de diagnosticar
WaitStartMotion/recomendar el ciclo de encendido por cualquier fallo canónico.
Seis regresiones nuevas y cinco controles previos pasan; sintaxis Bash correcta.
`cruzr_pico_to_home_owner.sh --preflight` completo termina con
`PICO_HOME_PREFLIGHT_OK` y `MOVEMENT_COMMANDS=0`: perfil4× exacto, acciones1,
PICO body_zero, velocidad0, error máximo0,002972rad, baterías59,3/65%,
paros0/0 y cargador0. No hubo instalación, recarga, cambio de modo ni movimiento.
Cambios persistentes sólo en PC. Reanudación: el mismo `--run` con su comprobación
presencial; no hace falta `install`/`reload`. Esto no cierra el ensayo físico4×.
Backup, log y fuentes: `../Humanoide-vla-evidence/20260910T114627Z_HOME-PREFLIGHT-CONTRACT/`.
[Contrato y reversión](teleoperation/CRUZR_HOME_INTERNO_APERTURA.md#compatibilidad-del-preflight-canónico).

**2026-09-10 — Comparación de trayectorias con abrazaderas terminada (VERIFICADO offline; candidatos sin activar).**
Nuevo comparador FK/envolventes/tiempos y ocho pruebas, sin cambios a XML,
generadores ni ejecutor. Conserva geometría completa/2mm/intervalo0–40mm y todos
los pares locales registrados. Concordancia `splint`–runtime en744estados:
orígenes de abrazaderas <0,027mm y orientación<0,0023°; cabeza difiere4,6mm.
PICO cuerpo a cero: omitir etapa exactamente inmóvil permitiría20→16,25s,
sin variar recorrido nominal ni máximos quintic individuales. Requiere verificar
asentamiento real antes de activarlo. Apertura−0,45rad permite14,946s pero pierde
unos35mm nominales respecto al torso; no se prioriza. Cuerpo y brazos en paralelo
mantienen máximos individuales pero requieren comprobar cargas/sincronización.
La cota conservadora con5° por articulación no demuestra separación para todos
los pares; frenado sin cota. No se afirma validación física ni despliegue.
Se revisó además el alcance de READY/ENTRY/MetaClamp/transferencia: el URDF solo
no describe primitivas nombradas, contacto, carga y escena de todo el flujo.
[Informe completo y reproducción](reports/2026-09-10_OPTIMIZACION_TRAYECTORIAS_ABRAZADERAS.md).
Fuentes/evidencia: `../Humanoide-vla-evidence/20260910T113554Z_CLAMP-TRAJECTORY-OPTIMIZATION/`.
Reanudación: para optimizar en operación, contrastar la variante sin etapa
inmóvil antes de reducir apertura o escalar todos los tiempos. Perfil vigente20s.

**2026-09-10 — Revisión de carpetas de descripción 3D (VERIFICADO local).**
La variante base describe pinzas PGC con dos dedos; `splint` las sustituye por
abrazaderas rígidas. Sólo cambia el URDF entre archivos comunes y se añaden
dos STL. Sus mallas de abrazadera coinciden byte a byte con la captura runtime
del 08-09: no son una geometría nueva para resolver los solapamientos.
El URDF completo difiere del runtime; los auditores actuales siguen usando su
snapshot explícito. Parseo/árbol/mallas correctos, sin lanzar ROS ni modificar
modelos o robot. Mismo nombre interno en ambos paquetes y dependencia GUI
omitida en manifiesto. [Informe y hashes](reports/2026-09-10_MODELOS_CRUZR_S2_DESCRIPTION.md).
Evidencia: `../Humanoide-vla-evidence/20260910T112000Z_DESCRIPTION-REVIEW/`.
Reanudación: si se pide integrarlos, contrastar cinemática/montaje y preparar
visualización o análisis aislado. Sólo documentación añadida, sin commit/push.

**2026-09-10 — Política global de registro y recuperación tras actualización (VERIFICADO local).**
Por petición del propietario, `AGENTS.md` obliga a registrar en la misma
intervención todo cambio de robot, PC y PICO, incluidas acciones temporales,
archivos, servicios, contenedores, red, paquetes, mapas y calibraciones.
Nuevo [registro de adaptaciones](SYSTEM_CUSTOMIZATIONS.md), con IDs, estado
vigente, fuentes, destinos, dependencias, respaldo, aplicación, activación,
verificación y reversión; separa cambios retirados/borradores y pruebas pendientes.
Nueva [guía de respaldo y reaplicación](guides/CRUZR_REAPLICAR_CAMBIOS_TRAS_ACTUALIZACION.md)
con copia externa de ambos hosts y trabajo sin commit, comparación de versiones
y receta de espera/voz/pantalla. No restaurar indiscriminadamente compose,
HOME antiguo, guard retirado o estados transitorios de control.
Se amplió `preupgrade_backup_remote.sh`: boot/systemd/overlays y configuraciones
de manipulación, navegación y visor dentro de contenedores; inventario/diff,
permisos privados iniciales, checksums transportables y errores parciales
explícitos. Cuatro pruebas offline correctas, sintaxis Bash y enlaces revisados.
Consolidación basada en evidencia documental; no es inventario nuevo en vivo.
PENDIENTE: primera captura con el respaldo ampliado en ambos hosts; permanecen
las pruebas físicas y de próximo arranque ya pendientes. No hubo conexiones,
movimientos, despliegues ni reinicios del robot en esta intervención.
Backup/fuentes/hashes: `../Humanoide-vla-evidence/20260910T110924Z_SYSTEM-CHANGE-POLICY/`.
Punto de reanudación: usar la ficha OPS-01 y la guía antes de una actualización;
mantener el registro con cada intervención futura. Sin commit/push.

**2026-09-10 — Aviso visual de arranque añadido a la voz (VERIFICADO en pantalla).**
Por petición del usuario, el aviso inglés se acompaña de `巡检`/`inspection.mp4`
(anillo azul con barrido) durante la primera espera de liberar E-stop. El añadido
sólo se superpone a `breath`; otras expresiones del proveedor tienen prioridad.
Permiso de visualización renovable y caducidad12s independiente en navegador:
lecturas Motion/cámaras crecientes/paros/cargador/identidadCC; al perderlas deja
la pantalla nativa. Cero llamadas de expresión ni comandos de movimiento.
Instalados módulo/JS de pantalla y servicio de voz actualizado en Vision; enabled,
Type=simple y voz única por boot conservada. Pruebas23Python+Node+Chromium
correctas, captura real del visor muestra巡检. Se recargó exclusivamente la
sesión gráfica LightDM para aplicar; CC y contenedores conservan identidad.
Primera versión refrescaba en18s; consultas paralelizadas y lectura de proceso directa para conservar TTL12s.
Renovación final observada8,54–8,75s; preview activo hasta liberación/pérdida
de comprobación o30min. PENDIENTE: próximo encendido con voz y vídeo combinados. El indicador
no valida el ensayo físico del HOME nuevo ni sustituye la preparación presencial.
Backup: /etc/walker/boot/backups/20260910T102219Z_BOOT-VISUAL/.
Evidencia: ../Humanoide-vla-evidence/20260910T102219Z_BOOT-VISUAL/.
[Uso y reversión](guides/CRUZR_AVISO_VOZ_ARRANQUE.md).

**2026-09-10 — Chequeo previo a primera liberación del HOME nuevo (VERIFICADO técnico).**
`cruzr_boot_ready.sh --check` terminó con RELEASE_TECHNICAL_CHECK=passed:
CC en primera espera de liberación, tres respuestas Motion y seis cámaras con
marcas de tiempo avanzando. Principal pulsado, servo liberado, cargador
desconectado y HOME open-v3-20s/hash de MetaMove esperados. Baterías 70,8/68,3 %.
Consulta VLA de sólo lectura: inferencia/control detenidos y publicadores del
SDK cero. No se envió movimiento ni se reinició ningún servicio.
**PENDIENTE:** confirmación actual del espacio de apertura lateral, sujeciones
retiradas y supervisión junto al paro, seguida de ensayo físico del HOME nuevo.
La comprobación técnica no constituye validación física de la trayectoria.
Evidencia: ../Humanoide-vla-evidence/20260910T101530Z_INTERNAL-HOME-FIRST-RELEASE/.

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
[Detalle, limitaciones y reversión](teleoperation/CRUZR_HOME_INTERNO_APERTURA.md).

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
[Secuencia y diagnóstico](incidents/2026-09-10_HOME_INTERNO_TRAS_RELOAD_4X.md).

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
[Perfiles, carga y límites de la verificación](teleoperation/CRUZR_PICO_HOME_OPEN_V2.md).

**2026-09-10 — Aviso de voz de arranque instalado; comprobación técnica verificada:**
A petición del propietario, Vision tiene `cruzr-boot-voice.service` habilitado
para decir «Ready to release the emergency stop.» una vez por encendido.
No necesita PC ni Codex. El servicio nuevo sólo consulta y usa la acción TTS;
no inicia Motion ni reinicia contenedores. Espera al CC actual en su primera
WaitEStopRelease, tres respuestas Motion, seis cámaras en dos rondas con
marcas temporales crecientes y paros/cargador1/0/0. Recomprueba antes de hablar.
El wrapper previo de CC ahora incluye esas cámaras antes del arranque vendor.
Guard antiguo disabled/inactive; compose, ID y StartedAt de CC conservados.
Alternativa desde PC: `./scripts/cruzr_boot_ready.sh --check`, que ya ha pasado
en vivo y mostrado LISTO PARA LIBERAR EL E-STOP. Preparación física de brazos
abajo/vacíos y zona libre sigue a cargo del operador; el aviso es técnico.
Pruebas locales16 correctas; systemd-analyze verify rc0. Dos reproducciones:
la segunda devolvió status4, desc Success, SpeechState1001000 y el operador
confirmó «Sí, se entiende bien». Corregido el análisis del resultado TTS
(esperaba SUCCEED en vez del Success real); comprobado contra la respuesta
capturada, sin repetir voz de nuevo. Instalación y audición verificadas;
pendiente observar el aviso durante el siguiente encendido completo.
[Uso, instalación, evidencia y rollback](guides/CRUZR_AVISO_VOZ_ARRANQUE.md).
Evidencia: ../Humanoide-vla-evidence/20260910T081749Z_BOOT-VOICE/.

**2026-09-10 — Nuevo arranque en frío: espera de Motion verificada; paro aún pulsado:**
Tras apagado completo y brazos abajo confirmados, el usuario inicia el encendido
y pregunta por un sonido. Ambos hosts responden. Contenedor CC inició07:53:53Z;
hw, manipulación y self-check Motion07:55:29Z, sin reinicios automáticos.
La espera instalada registró cuatro respuestas fallidas0/3, después1/3,2/3,3/3,
y sólo inició CC a07:56:02Z. Nueva instancia cc_main.20260910_155603.184.log
alcanza WaitEStopRelease; no reutilizar el log Term del apagado anterior.
Principal1/servo0/cargador0. Guard antiguo disabled/inactive y ambos hashes
sin cambios. XML open_v2 y task_list sobreviven al apagado con hashes exactos.
Prevención de la carrera observada comprobada en este encendido; no equivale
a Motion operativo antes de self-check/StartMotion tras liberar.
Comprobación ampliada sólo --check terminada rc0: x86 tres respuestas, seis
cámaras en dos rondas, v0.2.0, WaitEStopRelease y seguridad1/0/0.
Se indica liberar el principal con brazos abajo/vacíos/libres de las sujeciones
del apagado, recorrido despejado y persona junto al paro. Puede iniciar HOME interno.
Pendientes confirmación de liberación, autodiagnóstico, StartMotion, HOME y anillo.
Sin reinicios ni objetivos enviados por el agente en este arranque.
Evidencia: restart-20260910T075519Z dentro de
../Humanoide-vla-evidence/20260910T072711Z_PICO-RELOAD-NO-ACTION/.

**2026-09-10 — Apagado completo confirmado; brazos abajo, nuevo arranque pendiente:**
Usuario confirmó E-stop pulsado y brazos asegurados, además de abrazaderas
vacías y postura PICO estable/sin contacto. Lectura nueva: principal1, servo0,
cargador0; servicio /emb/pm_shutdown redescubierto con tipo ShutDown.
Se envió una única solicitud deadline_sec15/confirm-to-shutdown a las07:45:08Z
(PC); success=True. No se reinició ni rearmó Motion ni se envió HOME.
Después ambos hosts dejaron de responder; el operador confirmó pantalla y
luces superiores apagadas y brazos asegurados/estables. Sólo entonces se indicó
KEY1 y después botón metálico del chasis, conservando paro y aseguramiento.
Después de KEY1 y chasis, usuario confirma «apagado y brazos abajo» en respuesta
a indicador verde apagado/estabilidad. Apagado completo cerrado. Se indica
nuevo arranque habitual chasis→KEY1→encendido manteniendo E-stop pulsado y
brazos vacíos/libres, antes de comprobar servicios y permitir liberar el paro.
PENDIENTE: confirmación de encendido con paro, readiness y recuperación Motion.
La nueva ruta open_v2 sigue sin ensayo; no activar PICO hasta recuperar el arranque.
Evidencia: subdirectorio shutdown-* de
../Humanoide-vla-evidence/20260910T072711Z_PICO-RELOAD-NO-ACTION/.
Detalle: docs/incidents/2026-09-10_PICO_RECARGA_SIN_MOTION.md.

**2026-09-10 — PICO→HOME instalado, pero Motion detenido tras E-stop (VERIFICADO):**
El operador instaló/recargó open_v2; XML remoto hash6b8309f3…6999 exacto,
una entrada y proceso posterior al task_list. Después de entrar/salir de PICO,
principal pulsado15:18:50 UTC+8 coincide con reinicio hw (RestartCount1), que
espera /mc/rosa_control/start; manipulación recargada07:20:47Z espera ListControllers.
Liberar a15:24:16 no produjo nuevo StartMotion. Acción0 y actuadores sin muestra
(timeout7s); fault_current vacío no demuestra disponibilidad. CC conserva la
prevención de arranque y última transición AutoTaskMode, no WaitStartMotion.
Usuario confirma «en PICO, estable sin contacto» y después abrazaderas vacías.
No reutilizar HOME medido anterior ni reiniciar para probar: HOME interno no es open_v2.
Corregido wrapper LOCAL: propaga fallos dentro de sustituciones Bash, conserva
diagnóstico, distingue orden temporal/servidor disponible y retira indicación
de liberar paro inmediatamente tras recarga. Preparación exige brazos abajo/vacíos.
Preparación de apagado: servicio /emb/pm_shutdown y contrato ShutDown verificados
sólo por lectura; principal sigue0. Se indica pulsarlo y se espera confirmar paro
y aseguramiento presencial de los brazos contra caída/golpe antes de apagar.
No se ha enviado apagado: ausencia de caja no demuestra descenso controlado.
17 pruebas locales pasan; --preflight vivo corregido falla1 con PREFLIGHT_FAILED
antes de consultar runtime, sin objetivos. Ninguna escritura/reinicio en robot
desde el agente durante este diagnóstico. Recuperación física y ensayo pendientes.
Detalle, backup y reanudación: docs/incidents/2026-09-10_PICO_RECARGA_SIN_MOTION.md.
Evidencia: ../Humanoide-vla-evidence/20260910T072711Z_PICO-RELOAD-NO-ACTION/.

**2026-09-10 — Arranque recuperado tras liberar E-stop (VERIFICADO):**
El usuario comunica que parece terminado; nuevas consultas confirman principal0,
servo0, cargador0 y fault_current vacío. CC registró selfcheck passed=true/error0,
StartMotion succ y transición a AutoTaskMode a las 15:08:17 del reloj robot
(UTC+8). Muestra fresca20D válida: MEASURED_HOME=1, máximo absoluto0,002972 rad,
brazos0,000959 rad, velocidad0 y delta consigna0,002972 rad; actuadores habilitados
y sin error. Servidor de manipulación1, writers RobotCommand0, ambos contenedores
VLA exited/restart=no. Baterías97,1%/72,8%. Sólo consultas de lectura tras liberar;
sin objetivos de movimiento adicionales. Prevención de arranque instalada y
recuperación software verificadas. Pendientes confirmación visual del anillo
y repetición posterior de un arranque completo en frío. La trayectoria open_v2
no se instaló ni ejecutó. Sustituye la espera de liberación indicada abajo.
Evidencia: ../Humanoide-vla-evidence/20260910T064413Z_BOOT-READONLY/after-release/.
Detalle y reversión: docs/incidents/2026-09-10_ARRANQUE_CONTROL_CENTER_MOTION.md.

**2026-09-10 — VERIFICADO: carrera de arranque corregida en Vision; liberación pendiente:**
CC empezó self-check unos 51 s antes de arrancar el servicio x86 de Motion.
Fallaron archivos/sistema por servicio ausente y reloj/latencia por IP no
disponible; energía, cámaras y sobrecorriente pasaron. No es el fallo EtherCAT
del 08-09. Operador confirmó E-stop principal pulsado, brazos abajo, vacíos y
estables/sin contacto. Reinicio único de CC recuperó WaitEStopRelease.
Prevención instalada: /etc/walker/boot/cruzr_cc_start_when_ready.py espera tres
respuestas reales de Motion antes de ejecutar el comando original de CC.
Se cambió sólo el comando de system.control_center en compose y se recreó sólo
ese contenedor bajo nueva lectura principal1. Imagen, entorno, entrypoint y
montajes conservados; otros contenedores sin cambios. Registro nuevo confirma
3/3 respuestas, arranque vendor y WaitEStopRelease. Guard antiguo disabled/inactive.
Ocho pruebas locales y --check dentro del robot correctos. Nueva comprobación
previa rc0: tres respuestas x86, seis cámaras en dos rondas, v0.2.0,
WaitEStopRelease, paros/cargador1/0/0. Se indica liberar el principal bajo la
supervisión ya confirmada y se espera confirmación del operador. No se enviaron
objetivos de brazos/chasis; liberar el paro puede iniciar HOME interno vendor.
Backup: /home/walker/.config/udoke/walker/compose.yml.before-cc-ready-20260910T065831Z.
Reversión, hashes y alcance: docs/incidents/2026-09-10_ARRANQUE_CONTROL_CENTER_MOTION.md.
Evidencia: ../Humanoide-vla-evidence/20260910T064413Z_BOOT-READONLY/.
PENDIENTE: liberación supervisada, self-check y
StartMotion, HOME medido/anillo y repetición de arranque completo en frío.
La trayectoria PICO→HOME open_v2 continúa sin instalar/ejecutar en esta intervención.

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


**2026-09-09 — Apagado postcontacto pendiente de confirmación visual:**
Usuario confirma caja retirada y entorno despejado; después comunica pulsación
Power durante cinco segundos. No se envió /emb/pm_shutdown: PC había perdido
Wi-Fi robot, Motion/Vision SSH timeout. SSID Cruzr S2-0669 visible; intento
acotado de reactivar perfil guardado `Cruzr S2-0669 1` en wlx80afcad40bd6
(never-default, ruta .11/24 vía .42.2) agotó 15 s. Sin modificación persistente
de perfil ni de DSA CORPORATE. No inferir apagado por falta de conectividad.
Mantener E-stop, no repetir Power ni pulsar KEY1 hasta pantalla/luces apagadas.
Después KEY1 y finalmente chasis; comprobar indicador verde apagado y estabilidad.
Pendiente confirmar estado visual; no se declaró apagado completado.
Evidencia diagnóstico de red: /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260909T123421Z_POST-CONTACT-SHUTDOWN.


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


**2026-09-09 — Diagnóstico de rechazo del ejecutor PICO→HOME (VERIFICADO en captura):**
El intento del operador `20260909T141428_PICO-HOME-OWNER-RUN` no envió
movimiento: el gate exige una única referencia PICO20D con elevador
[0,299989118; −0,500269484; 0,199609250] rad. La captura guardada muestra
[−0,000191748; −0,000191748; −0,000383495] rad, prácticamente HOME corporal.
Los 14 ejes de brazos sí coinciden con PICO (error máximo 0,002013350 rad).
Por tanto `postura_no_coincide_con_pico` no significa que el usuario no esté
en modo PICO: significa que no coincide la postura corporal específica del
recorrido revisado. Error máximo elevador 2 = 0,500077737 rad (28,65°),
tolerancia 0,02 rad. Inferencia: variante de brazos PICO con cuerpo a cero,
compatible con el overlay de control sólo de brazos; no demuestra modo vivo.
No se alteraron referencias, tolerancias, tareas ni robot durante el diagnóstico.
Pendiente adaptar y revisar explícitamente esa variante antes de ejecutarla;
no ensanchar la tolerancia ni llevar el torso a la referencia antigua para pasar.
Evidencia: `../Humanoide-vla-evidence/20260909T141428_PICO-HOME-OWNER-RUN/before-joints.yaml`
y `scripts/teleoperation/cruzr_pico_to_home_owner_gate.py`.


**2026-09-09 — Reanudación y HOME cerrados (VERIFICADO):**
La ejecución `SRG3DFN4` terminó con código 0 en 443 s. Depósito Motion
SUCCEED, retirada odométrica 0,492029 m y HOME vendor
`43d16648-273d-4395-854b-d0f94e679652`, SUCCEED/status4. Medición final:
`MEASURED_HOME=1`, 20D máximo absoluto 0,002780 rad, brazos 0,000863 rad,
velocidad máxima 0. No se reiniciaron contenedores ni se alteraron límites.
Punto de reanudación: robot en HOME detrás de mesa 2; caja liberada por la
acción de depósito. Confirmación visual final del operador no recogida aún.
Evidencia persistida en
`../Humanoide-vla-evidence/20260909T112523Z_USLAM-AUX-RESUME/completed-transfer/`.
Las entradas «en curso» de abajo describen fases anteriores ya terminadas.


**2026-09-09 — Depósito reanudado con éxito (VERIFICADO Motion y mapa):**
`--resume-held-approach --yes --fast` avanzó 0,474785 m y luego 0,503024 m,
recalculando tras una llegada intermedia con error 0,029 m. Pose final fresca
−0,323384265933/1,06489210132/1,66272749992: error de posición 0,0043 m y
orientación −1,10° respecto al depósito enseñado. No se ampliaron tolerancias.
`cruzr/blue_workbin_auto_deposit`, goal
`165d4649-88a7-4ab1-b47d-9b61e2c36dbd`, SUCCEED/status4; registro posterior
`deposited_open_near_table`, sin eventos inseguros y articulaciones quietas.
Log `/tmp/cruzr-table-transfer.SRG3DFN4` y copia en evidencia
`20260909T112523Z_USLAM-AUX-RESUME`. Recuperación de HOME aún en curso.
Pendiente una repetición completa desde mesa 1 para verificar físicamente el
tratamiento del resultado auxiliar de navegación; esta reanudación no navegó.


**2026-09-09 — Reanudación medida dentro de la aproximación (VERIFICADO offline; ejecución en curso):**
Los 5,1 cm eran error de localización respecto a la **premesa virtual**, situada
1,0 m antes de la pose de depósito enseñada; no distancia caja–mesa. El intento
`gl8OhUFM` bloqueó antes de avanzar al superar 5 cm. Una corrección local
0,049032 m adelante/−0,047125 m lateral se interrumpió por objetivo fuera del
arco frontal (−75,2°); hubo avance parcial, no se repitió. Nueva pose fresca
−0,241386/0,120383/1,657037: unos 5,3 cm dentro del tramo, 1,9 cm lateral.
Cambio LOCAL: `--resume-held-approach` sólo sin tags calcula el resto desde
pose fresca, dentro del corredor y orientación enseñados, y rechaza una
proyección recta fuera del margen. Cada tramo recalcula la distancia desde la
llegada medida; también el flujo normal deja de acumular distancias nominales.
Se conservan tolerancias de mapa, agarre, paros, LiDAR y límites de primitivas.
97 pruebas workbin pasan (incluyen corredor, distancias, ausencia de repetición
de agarre/retirada y bloqueo antes de movimiento). No se cambia perfil ni XML.
Rollback: con robot detenido, retirar el modo nuevo y revisar sólo las funciones
modificadas, preservando cambios anteriores. Nunca repetir una distancia fija
desde un tramo parcialmente recorrido. Copia del código probado en evidencia/changed.
Ejecución `--resume-held-approach --yes --fast`, log
`/tmp/cruzr_remaining_resume_run.log`; resultado físico pendiente.


**2026-09-09 — Corrección del aviso VSLAM auxiliar y reanudación desde premesa (en curso):**
nuevo intento `/tmp/cruzr-table-transfer.yk6hsjdq`, 328 s, se detuvo por el
rechazo explícito de VSLAM_MAP_DIR_ERROR pese a llegada real a premesa.
Planificador: FINISH, goal interno5e585d95-e06f-44ed-9904-8e80aa273c86;
pose objetivo -0,216672/0,070232/1,681930, lectura fresca posterior
-0,261118/0,049621/1,685730, error<0,05 m. Agarre vigente0,566 m,
Fy28,7 N/Fz-10,1 N, 20D inmóviles y writer de RobotCommand0.
Cambio LOCAL map_route: caso excepcional sólo para navigate-map-pose en uslam,
respuesta status4 + dmsg navigation_start SUCCEEDED + desc exactamente
VSLAM_MAP_DIR_ERROR. Esa combinación exige todavía tres lecturas frescas
estables y llegada dentro de las tolerancias configuradas; si no, bloquea.
Fuera de ese caso conserva rechazo estricto (fusion/auto, otros errores,
lectura fallida, desviación, aborto). El aviso se informa; no se finge resuelto
el guardado visual ni se cambia el árbol vendor. LiDAR y controles intactos.
94 tests workbin/sintaxis/diff correctos. Usuario autorizó corregir y continuar
con la misma disposición; se inició --resume-held --yes --fast, sin repetir
agarre, retirada inicial ni navegación a premesa. Resultado físico pendiente.
Evidencia: `../Humanoide-vla-evidence/20260909T112523Z_USLAM-AUX-RESUME/`.

**2026-09-09 11:11 UTC — VERIFICADO: anillo blanco y recuperación operativa tras liberar E-stop:**
el propietario confirmó paro liberado y anillo blanco. Lectura nueva: principal0,
fault_current vacío; instancia nueva de CC muestra selfcheck passed=true/error0,
StartMotion succ y transición SelfChecking→JoystickMode. Postura fresca: 20D
válidos, MEASURED_HOME=1, máximo absoluto0,002780 rad (brazos0,000959),
velocidad0 y delta consigna0,002780 rad. Sin nuevos movimientos enviados por
el agente en esta verificación. El fallo histórico 02029001 permanece archivado
con resolve3/Restart (id55); no se forzó el color ni se modificó la base.
Caso de anillo rojo CERRADO. Esto no valida el flujo completo sin AprilTag ni
elimina la deuda separada del error auxiliar VSLAM durante navegación.
Evidencia: `../Humanoide-vla-evidence/20260909T110505Z_CC-RESTART-RED-RING/`.

**2026-09-09 11:09 UTC — VERIFICADO: preparación para liberar E-stop tras retirar aviso rojo:**
`/usr/local/sbin/cruzr-v020-boot-guard --check` terminó rc0 en la instancia nueva.
Tres pruebas funcionales x86, dos rondas de las seis cámaras, versión v0.2.0,
CONTROL_STATE=WaitEStopRelease y SAFETY_STATE=1 0 0 (principal/servo/cargador).
Fue sólo --check, sin otro reinicio ni órdenes de movimiento. Se indica al
operador liberar el paro bajo la supervisión ya confirmada; puede iniciar
HOME interno. Pendientes self-check/StartMotion, ausencia de fallos después de
liberar y confirmación visual del anillo. No declarar recuperación operativa
completa por el mero vaciado de fault_current.

**2026-09-09 11:05 UTC — VERIFICADO: aviso histórico 02029001 archivado tras reinicio único de Control Center:**
operador confirmó E-stop principal pulsado; lectura VOLATILE dio principal1,
servo0. Se ejecutó una sola vez `docker restart --time 5 walker-system.control_center-1`,
rc0. StartedAt cambió de 05:20:04Z a 11:05:01Z (reloj robot, desfasado del PC).
La nueva instancia registró `Found unresolved fault code=02029001, will mark
as resolved with Restart`; fault_current quedó vacío y fault_history incorporó
id55/code2029001/resolve3. No se editó la base, no se simuló resolución ni se
forzó expresión facial. Archivo de mapa MESAS3 fallido no se recuperó; se archivó
su aviso histórico. La causa auxiliar VSLAM de navegación es un asunto separado.
Secuencia nueva: WaitBootReady succ → Recover succ → WaitEStopRelease.
E-stop continúa1. Preparación de arranque en comprobación antes de liberar.
Sin reiniciar Motion/hw, sin comandos de brazos/chasis; el propio Control Center
puede iniciar self-check/StartMotion y HOME interno tras liberar el paro.
Resultado visual blanco y recuperación operativa posterior aún PENDIENTES.
Evidencia: `../Humanoide-vla-evidence/20260909T110505Z_CC-RESTART-RED-RING/`.

**2026-09-09 11:01–11:03 UTC — OBSERVADO, anillo rojo después de HOME:**
lectura SQLite readonly de Control Center muestra únicamente 02029001,
iniciado en 1788935580688 ms: fallo de guardado de mapa durante cartografía.
Los avisos de batería 00001001 ya constan resueltos (resolve1); no son la causa
actual. Catálogo instalado asigna 02029001 a guardado de mapa, solución pendiente.
No hay otros códigos activos en esa consulta. Servicios y contenedores
redescubiertos por Wi-Fi. No se modificó la expresión, la base de fallos ni
se ejecutó fault_solve (el binario lo describe como simulación).
El binario contiene processUnresolvedFaults y el mensaje de archivado de fallos
pendientes como Restart al inicializar; el historial tiene resoluciones tipo3.
INFERENCIA: reiniciar sólo Control Center puede retirar este aviso histórico;
se debe verificar después, sin afirmar recuperado el blanco antes de observarlo.
Intervención preparada: único reinicio de walker-system.control_center-1,
con E-stop principal físicamente presionado por el operador y verificado por
lectura antes de reiniciar; después comprobar nueva instancia y estado de
arranque antes de liberar. Razón: CC puede disparar HOME/StartMotion interno,
como consta en CRUZR_V020_BOOT_GUARD.md. No se ha reiniciado ningún servicio.
La confirmación de corredor libre sigue vigente para esa disposición; esta
petición del paro no vuelve a preguntar por el espacio.
Evidencia: `../Humanoide-vla-evidence/20260909T110137Z_RED-RING/`.

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

**2026-09-09 10:42–10:46 UTC — VERIFICADO: parada en premesa sin tags por pose retenida; referencia de depósito NO VÁLIDA:**
intento `--run --fast`, log `/tmp/cruzr-table-transfer.VsaES4gk`, 342 s.
Agarró correctamente (separación 0,567 m; Fy 24,6 N), retrocedió 0,492 m y
el planificador llegó a premesa con FINISH. No ejecutó aproximación final,
depósito ni HOME. Restauró el perfil de percepción original. Foto del usuario:
caja elevada. La situación física posterior requiere confirmación presencial.

`ros2 topic echo --once /nav/robot_pose` recibió una muestra TRANSIENT_LOCAL
con stamp 1788933620.562976, X/Y/yaw -0,278215821/0,886028107/1,678875678,
de más de cuatro horas antes. Es exactamente la usada al enseñar el depósito.
La suscripción VOLATILE y ROSA nativo recibieron pose actual aproximada
-0,211166/-0,089866/1,6827, a 0,0447 m de la premesa solicitada.
El supuesto error de distancia de 1 m procedía de comparar la muestra retenida.
`VSLAM_MAP_DIR_ERROR` se produjo en save_auto_update_map después de FINISH;
el árbol vendor ignora ese fallo auxiliar y responde status=4/dmsg SUCCEEDED.
No demuestra fallo de llegada a premesa ni permite validar el depósito.

Correcciones locales: `scripts/lib/cruzr_map_pose_gate.py` suscribe VOLATILE,
exige dos sellos crecientes, edad <=3 s usando el reloj del host robot, marco
map, geometría finita y cuaternión planar válido. map_route usa este lector y
rechaza resultados de navegación con errores internos aunque status=4.
Los perfiles sin capture_method=volatile-stamped-v2 se rechazan: deben volver
a enseñarse físicamente; no añadir la marca manualmente. Perfil actual y backup
preservados, sin modificar coordenadas. No se enviaron movimientos, reinicios,
servicios ni cambios remotos durante este diagnóstico. Lector nuevo verificado
en vivo mediante suscripción; 92 tests workbin offline y sintaxis Bash correctos.
Evidencia y copias previas: `../Humanoide-vla-evidence/20260909T104241Z_NO-TAG-NAV-FAILURE/`.
Pendiente: asegurar/descargar caja con procedimiento presencial, enseñar depósito
con lectura fresca y resolver resultado auxiliar de navegación antes del siguiente
ciclo. No reanudar el metro restante con la referencia antigua ni repetir --run.


**2026-09-09 — Sobrescritura explícita de referencia sin tags (offline):**
se añade `--teach-mesa2 --overwrite-mesa2` al orquestador y wrapper sin tags.
Captura y valida antes de sustituir; conserva copia exacta `.bak.*` junto al
perfil y usa sustitución atómica. Fallo de captura conserva el original;
sin opción explícita mantiene el rechazo previo. No envía movimiento.
Evidencia reproducible: tests de `scripts/test_workbin_without_apriltag.py`
para copia exacta, fallo de captura y rechazo de enlaces/modos incompatibles.
Cambios sólo locales en scripts y documentación; captura física PENDIENTE.
Rollback y comando en la guía
`docs/guides/TRANSFERENCIA_CAJA_ENTRE_MESAS_SIN_APRILTAG.md`.

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
No sobrescribe perfiles por defecto (opción explícita documentada arriba). El ejemplo contiene null en referencias no conocidas
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
[Guía sin AprilTags](guides/TRANSFERENCIA_CAJA_ENTRE_MESAS_SIN_APRILTAG.md).
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
[revisión offline](reviews/2026-09-09_WORKBIN_TABLE_TRANSFER_OFFLINE.md).
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
[Guía de liberación](guides/CRUZR_WORKBIN_LIBERAR_CAJA.md).
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

**2026-09-09 — mínimo de batería 20 % solicitado por el propietario:**
`cruzr_blue_workbin_cycle.sh` y el inicio de `cruzr_blue_workbin_map_route.sh`
pasan de 30 a 20 %. Retorno/reanudación de mapa pasa de 25 a 20 % para no
rechazar una continuación con más batería que la exigida al inicio. Ambos
SOC deben ser al menos 20 % en las comprobaciones existentes. El ciclo es
compartido por transferencia, agarre, alineación y recuperación HOME; el
alcance incluye esos consumidores. Cambio local, sin movimiento ni cambios
en firmware/BMS. Verificación local de sintaxis y frontera 19,9/20/20,1 %;
no demuestra autonomía restante ni constituye prueba física del ciclo.
Reversión: restaurar 30 % en ciclo/inicio de mapa y 25 % en retorno de mapa.

**2026-09-09 — recuperación operativa MESAS2 en modo LiDAR del fabricante:**
**Verificación final:** `--check` terminó con código 0 y
`TABLE_TRANSFER_CHECK_OK`, baterías 31,2/30,4 %. Hashes de todos los archivos
MESAS2 idénticos antes/después. Log final `check_final.log` en la evidencia.
por autorización «haz todo lo necesario», se seleccionó explícitamente
`map_type=uslam` en `map_set` y `relocation_start`. Árboles instalados admiten
ese modo; configuración de relocalización leída con `non_rotate=true` y
`global_using_rotation=false`. Resultado `NAVIGATION_READY`/`FSM_WAITNAVIGATE`
y poses publicadas. Se reiniciaron sólo `walker-nav.vslam-1` y
`walker-nav.nav_taskmanager-1`; posteriormente se restauró MESAS2/uslam.
VSLAM quedó `READY`. Motion y Control Center no se reiniciaron. No se ordenó
navegación a destinos ni manipulación; no se modificaron umbrales/protecciones.
El código `02039001` ya no estaba activo al consultar `fault_current`;
`02029001` (guardado MESAS3 fallido) sigue retenido, también tras los reinicios.
No se manipuló esa base de datos ni se dio el mapa visual por reparado.

Scripts locales ahora aceptan `CRUZR_MAP_TYPE=auto|uslam|fusion`, con `auto`
predeterminado; el tipo explícito viaja en carga/relocalización y separa las
cachés de preparación. Se preservan MESAS2 y sus waypoints. Primera comprobación
completa de transferencia satisfactoria; otra alcanzó todos los checks pero
salió 127 al editarse la ayuda del script mientras Bash aún lo ejecutaba
(`irm_once`). No repetir ediciones de scripts en ejecución; verificación final
repetida con archivos estables. Pruebas locales: sintaxis, 9 tests de puntos y
10 comprobaciones de payload/modo sin conexión. Baterías últimas 31,5/30,4 %;
gate de inicio 30 % conservado. Antes de navegación física comprobar que la
pose dibujada coincide con posición/orientación reales: relocalizaciones
globales anteriores dieron poses distintas. Transferencia física pendiente.

Evidencia externa `Humanoide-vla-evidence/20260909T063738Z_MAPPING-REPAIR/`:
configuraciones leídas, hashes previos del mapa, acciones y reinicios. No hubo
edición de configuración del robot; cambio persistente local en scripts y
cachés remotas de mapa. Reversión local: quitar `CRUZR_MAP_TYPE`; para cambiar
el modo runtime se requiere carga explícita del modo elegido. `fusion` puede
activar giro de cabeza durante relocalización y exige preparación física.
La fuente del fallo visual permanece pendiente; el mapa 2D MESAS2 tenía 69
nodos, mientras el tramo de MESAS3 produjo sólo uno. No confundir las 11 poses
del trazado 2D con nodos clave ni dar la captura visual por reparada.

**2026-09-09 — VERIFICADO, guardado visual MESAS3 fallido:** lectura 06:35 UTC
confirma intento de guardado a las 06:33 UTC: 2D `MAPPING_SUCCESS`, VSLAM
`rigs size: 0`, `NO date to save!`, `SAVE_MAP_FAILED`. CC añade `02029001`
(catálogo: fallo de guardado de mapa); no aparece resolución de ese aviso ni
del anterior `02039001` en la muestra. MESAS3 carece de los archivos visuales
de mapa esperados. El operador volvió a MESAS2; registro confirma carga y
estado visual `LOAD_MAP_FINISHED`, que no demuestra localización recuperada.
MESAS2 conserva su mapa visual anterior (13 puntos/una pose). Se confirma
captura visual vacía en MESAS3, aunque el origen del fallo sigue pendiente.
No repetir recorridos hasta diagnosticar inserción de datos visuales. Evidencia
externa `Humanoide-vla-evidence/20260909T063514Z_MAP-RETURN/`. Sólo lecturas.

**2026-09-09 — revisión del diagnóstico durante grabación:** recorrido 2D
creció a 11 poses; cámaras/VIO activos. `use_lidar_mapping=true` y
`enable_mapping_callback=false` en configuración instalada. ROS2 reporta cero
publicadores de `/nav/robot_pose`, pero ROSA reporta dos; las suscripciones
acotadas no recibieron muestra estando parado. NO demuestra conexión ausente.
El árbol vendor guarda primero mapa 2D y después VSLAM `save_map`; por tanto,
`cannot get rig from map` durante grabación no basta para declarar fallida la
captura ni justificar cambiar configuración. Pendiente finalizar el tramo de
prueba desde UI bajo nombre nuevo, revisar resultado guardado y relocalizar.
Evidencia externa `Humanoide-vla-evidence/20260909T062910Z_MAPPING-DIAG/`.
Sólo lectura; ningún reinicio, edición remota ni comando de movimiento.

**2026-09-09 — OBSERVADO, primera comprobación tras tramo manual:** a las
06:27 UTC sigue `MAPPING_RUNNING`, pero continúa `cannot get rig from map`.
Entre las poses VIO inicial/final de la ventana de registro hay aproximadamente
0,45 m de variación; el seguimiento detecta desplazamiento, sin incorporación
de poses al mapa demostrada. Ya no basta explicar el aviso por inmovilidad.
Evidencia externa `Humanoide-vla-evidence/20260909T062710Z_MAPPING-PROGRESS/`.
Sin comandos físicos; pendiente diagnosticar inserción de referencias visuales.

**2026-09-09 — OBSERVADO, nueva cartografía iniciada:** tras aviso del operador,
VSLAM confirma `MAPPING_RUNNING` y mapping2d `MAPPING_NORMAL`. Imágenes de
cuatro cámaras llegan y VIO calcula poses, pero durante la muestra inicial
persiste `cannot get rig from map`/`draw map failed`; incorporación de poses
al mapa visual aún PENDIENTE. No atribuirlo a avería sin distinguir inicio
inmóvil de recorrido efectivo. Sólo lectura; evidencia externa
`Humanoide-vla-evidence/20260909T062503Z_MAPPING-LIVE/`.

**2026-09-09 — OBSERVADO, relocalización forzada no recupera VSLAM:**
lecturas 06:16–06:17 UTC confirman dos `FSM_Relocating SUCCEEDED` con
`map_type: fusion`, pero persiste `LOCATION_LOST`; VSLAM recibe imágenes y
extrae características, con intentos repetidos `matched map point num is 0`.
MESAS2 contiene un `vslam/source_map/points.pcd` de sólo 13 puntos y
`mapping_pose.csv` con una fila; `localization_map/map.pb` ocupa 1372 bytes.
INFERENCIA: cobertura visual guardada muy escasa, probable impedimento para
relocalización; no se ha demostrado el motivo de su generación ni el contenido
completo del protobuf. No basta el éxito del navegador para cerrar este aviso.
Evidencia externa `Humanoide-vla-evidence/20260909T061650Z_LOCALIZATION-AFTER-FORCED/`.
Sin cambios remotos ni movimiento. Reanudación: revisar captura del mapa visual
y preparar nueva cartografía conservando MESAS2 y sus puntos.

**2026-09-09 — OBSERVADO, anillo rojo por fallo de relocalización visual:**
lecturas nuevas a las 06:10–06:11 UTC: CC registra `02039001` seguido de
`logo -> warning-red`, sin resolución posterior en el registro actual;
`/vnav/vslam/state=LOCATION_LOST`. Catálogo instalado: fallo de relocalización
basada en características. Ambos paros `0`; LiDAR publica `LocateRunning`,
lo que no demuestra recuperación de VSLAM. No es el aviso histórico `02039005`.
La causa de la pérdida visual sigue PENDIENTE; no atribuirla al nuevo mapa
sin más evidencia. Diagnóstico de lectura, sin movimientos ni cambios remotos.
Evidencia: `../Humanoide-vla-evidence/20260909T061055Z_RED-FACE/` (respecto a
la raíz del repositorio). Reanudación: comprobar recuperación de localización
antes del transporte autónomo; no se relocalizó ni reinició ningún servicio.

**2026-09-09 — puntos MESAS2 guardados como mapping_marker:** lectura directa
de `umap.json` a las 06:05 UTC confirma MESA1_PRE/MESA2_PRE con `mode=""`,
`type="mapping_marker"` y coordenadas/orientación. El mapa histórico utiliza
`logo_nav`/`precise_marker`. El preflight directo y la consulta de waypoint
admiten ahora ese formato concreto de la UI; navegación a esos puntos utiliza
sus coordenadas mediante `free_nav` en lugar de enviar su ID como `logo_nav`.
Otros modos vacíos/desconocidos siguen rechazados. Validación de puntos ejecutada
en lectura sobre MESAS2; pruebas locales de validación y despacho simulado.
No se modificó el mapa ni se envió navegación. Prueba física pendiente.

**2026-09-09 — corrección del preflight de transferencia en mapas nuevos:**
el operador observó carga y localización satisfactorias de `MESAS2`, seguidas
de rechazo por `task.json` sin ruta. La transferencia ahora exige únicamente
`MESA2_PRE` en `umap.json`; navegación directa valida el destino solicitado.
Se admiten rutas programadas vacías en esos modos, conservando comprobaciones
de existencia, unicidad, modo y coordenadas/orientación finitas. El recorrido
histórico conserva su secuencia obligatoria. Pruebas locales sin conexiones;
pendiente repetir `--check` en MESAS2. No se modificó el mapa ni se movió el robot.

**2026-09-09 — VERIFICADO localmente, mapa parametrizado:** navegación acepta
`CRUZR_MAP_NAME` (predeterminado `test_route_01`), heredado por transferencia y
ruta corta. Nombre validado antes de conectar; caché de preparación fluida
asociada al mapa. No crea mapas ni modifica waypoints/calibraciones; sigue
exigiendo la secuencia histórica en el preflight de mapa. Sin acciones remotas.


**2026-09-08 — ejecutor PICO→HOME creado por autorización expresa del propietario:**
`scripts/teleoperation/cruzr_pico_to_home_owner.sh` implementa `--check`,
`--install`, `--reload`, `--preflight` y `--run`. La tarea mueve primero los
dos brazos a cero en 19,617 s conservando los seis ejes corporales y después
cabeza/elevador/cintura a cero en 6,254 s. Instalación y recarga exigen E-stop;
ejecución exige tarea exacta cargada, preflight canónico, cero publicadores,
actuadores sanos, postura PICO medida dentro de 0,02 rad, velocidad máxima
0,01 rad/s, confirmación humana literal y verificación HOME posterior. No hay
reintento automático ni se desactiva ninguna protección. El operador acepta
explícitamente que interpolador y parada no están certificados. XML, gate y
tres tests locales pasan; **no se instaló, recargó ni ejecutó en el robot**.
Punto de continuación: `--install` con E-stop activo.

**2026-09-08 — refinamiento condicional HOME y comparación de órdenes:**
Con parada hipotética (+0,68755°), error articular 5° y origen axial 0–40 mm,
la comprobación continua local abrazadera–muñeca conserva reservas de 0,304 mm
izquierda y 0,018 mm derecha después de márgenes 2+2 mm. Cierra ese cálculo
local, no la validación física. Los tres órdenes nominales comparados conservan
el mismo mínimo muestreado de 25,056 mm frente al elevador. Parada real,
incertidumbre global y equivalencia de ejecución siguen sin demostrarse.
Sin movimiento. [Detalle y evidencia](measurements/2026-09-08_CIERRE_REVISION_PICO_HOME.md).

**2026-09-08 — tolerancias UBTECH comunicadas y presupuesto insuficiente:**
usuario informa sin procedimiento aplicable, error articular «5ª» interpretado
como 5° y espacial 2 mm. Si este último es seguimiento adicional, supera reserva
previa derecha 0,856 mm. Desplazamiento angular debe acotarse por pieza; parada
sin cota. Falsos positivos de dos pares aceptados como criterio técnico comunicado,
sin desactivar checks. Propuesta sigue NO aprobada, sin colisión física afirmada
ni movimiento enviado. Ver informe de cierre y error-budget-ubtech-reported.json.

**2026-09-08 — revisión ampliada PICO→HOME, NO aprobación física:**
[resultado](measurements/2026-09-08_CIERRE_REVISION_PICO_HOME.md). Nueva lectura inmóvil;
376 pares/202 estados, 33 refinamientos STL y 40 muestras adicionales de
brazos–torso. Dos intersecciones nominales ya iniciales en uniones requieren
interpretación, no prueban contacto real. Plantillas de ejecución leídas sin
llamarlas; equivalencia con curva revisada y cotas de seguimiento/parada no
demostradas. Decisión documentada NOT_APPROVED; ninguna ejecución ni reinicio.

**2026-09-08 — VERIFICADO, origen en modelo instalado y chequeo PICO→HOME:**
[resultado y alcance](measurements/2026-09-08_REVISION_ORIGEN_Y_PICO_HOME.md). URDF instalado distinto
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
[Detalle y pendientes](measurements/2026-09-08_EJES_SENSOR_DERECHO.md). Sin movimiento ni contrato de colisión alterado.

**2026-09-08 — confirmación técnica comunicada del lado derecho e inferencia izquierda:**
usuario confirma resultado derecho por técnico. Nueva muestra 11:26:59 UTC y
URDF archivado sitúan +X izquierdo hacia fuera, +Y arriba y +Z delante; R útil
candidata Ry(-90°), con +Z hacia almohadilla y +Y hacia patitas. Contraste físico
izquierdo y precisión pendientes. [Registro](measurements/2026-09-08_EJES_SENSOR_DERECHO.md).
Sin movimiento ni cambio del contrato de geometría.

**2026-09-08 — INFERENCIA, ejes derechos calculados sin movimiento:**
[resultado](measurements/2026-09-08_EJES_SENSOR_DERECHO.md). Muestra actual inmóvil y URDF
archivado sitúan aproximadamente +X sensor al centro, +Y arriba y +Z delante.
Con descripción del usuario y marco útil explícito, R candidata ≈Ry(+90°).
No registro validado: runtime/modelo físico, marco dimensional e incertidumbre
siguen pendientes; contrato geométrico no alterado, cero comandos de movimiento.

**2026-09-08 — ejemplos de R ampliados a X/Y/Z:** comparador didáctico con
identidad y tres giros independientes de +90 grados respecto al sensor fijo.
Incluye matrices, sentido de giro y dirección de almohadilla, borde y patitas.
Ejemplos ficticios, sin modificar geometría real ni validación de trayectorias.

**2026-09-08 — VERIFICADO, comparación didáctica de R:** [dos vistas 3D](measurements/orientacion_R_ejemplos.html), integradas en la ficha. Sensor y traslación
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
[Modelo 3D interactivo](measurements/abrazadera_mediciones_3d.html) y
[instrucciones](measurements/README.md). Doce fichas por lado, vistas giratorias
y descarga JSON; comprobación local en Chrome de los doce paneles, separación
izquierda/derecha y vistas completada. Esquema ilustrativo: únicamente la placa
usa cotas nominales declaradas; montaje, sensor y holguras no están medidos.
**PENDIENTE:** fotos con escala coplanar, mediciones del técnico, transformación
al marco del robot e incertidumbre. La cinta aporta escala local, no certifica
geometría ni trayectoria PICO→HOME. Sólo archivos locales, sin comandos al robot.
Punto de reanudación: completar ambas fichas y registrar las zonas no accesibles.

**08-09, unión fija de abrazadera precisada:** [auditoría](incidents/2026-09-08_UNION_FIJA_ABRAZADERA.md).
Modelo distingue sensor+wrist_roll rígidos de wrist_pitch móvil. Los dos
solapamientos históricos afectan wrist_pitch: no son exenciones de montaje.
Añadida topología explícita, sin recortar envolvente ni ocultar colisiones;
cinco tests pasan. PICO→HOME sigue sin validación geométrica. Cero movimiento.

**08-09, propuesta PICO→HOME offline preparada:** [alcance](incidents/2026-09-08_PROPUESTA_PICO_HOME_OFFLINE.md).
Captura20D sana/inmóvil; propuesta matemática de25,870372s y rangos URDF pasan.
No búsqueda de camino ni validación de contacto; JSON no ejecutable, cero
movimientos. Tres tests pasan. Script físico sigue pendiente de ruta revisada.

**08-09, diagnóstico adicional localización02039005:** get_map_name de consulta
termina SUCCESS/status4 y devuelve mapanuevo (no asumir test_route_01 histórico).
Locate3d informa LocateRunning y publica pose, con avisos repetidos de estado
estimado anterior al último tiempo. VSLAM sigue extrayendo características,
pero advierte TF L_arm_base_link inexistente al calcular máscara de brazo.
No demuestra que ese TF ni los avisos temporales causen02039005; tampoco que
el mapa corresponda a escena actual. Preguntado al operador sobre mapanuevo.
Sin navegación, cambio de mapa, pose inicial, reinicios ni cambio de umbrales.
Resolución pendiente: confirmar mapa/escena, visibilidad y calibración/TF antes
de relocalizar o remapear; no ocultar el aviso. Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260908T091128Z_LOCALIZATION-WARNING/`.

**08-09, anillo rojo explicado por localización:** log CC correlaciona
occur02039005 con logo→warning-red; varias resoluciones temporales y nueva
aparición persistente en última transición. Catálogo instalado define02039005
como cantidad baja de características coincidentes durante localización,
sistema navegación/localización; solución vendor pendiente. No atribuir al
vr_status0 ni al watchdog FT anterior. Consulta actual CC JoystickMode,
paros0/0, actuadores sin errores y velocidad0, hw sin nuevo reinicio. Posibles
causas visuales/mapa aún no investigadas. Sin movimientos/cambios de modo,
sin ocultar aviso ni reiniciar. Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260908T090540Z_RED-FACE/`.

**08-09, vr_status0 durante sesión PICO:** lectura pasiva PC muestra transición
1→0 a10:52:58, seguida de Pico publisher stop y operation_type1. Tracking vuelve
1 a10:52:59 y0 a10:54:15. Dos TCP establecidos desde PICO42.211 a PC42.215:63901;
ADB sin dispositivos. Esto no demuestra pérdida Wi-Fi ni sensor averiado.
Lanzador --teleoperate todavía presente (PID distinto entre consultas); no
inferir sesión finalizada sólo por STOP del publisher. Antes de reactivar
Working cerrar lanzador con Ctrl+C para evitar reanudación al volver tracking.
No se abrió WebSocket, reconectó ADB, reinició app/servicio ni envió movimiento.
Pendiente comprobar dentro del visor Head+Controllers/Send data/Working y
repetir --check con lanzador detenido. Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260908T085738Z_VR-STATUS-ZERO/`.

**08-09, recuperación operativa y HOME verificados:** [resultado](incidents/2026-09-08_HOME_TRAS_RECUPERAR_CONTROL_CENTER.md).
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

**08-09, EtherCAT diagnosticado:** [secuencia y límites](incidents/2026-09-08_DIAGNOSTICO_ECAT_6002.md).
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

**08-09, recuperación post-FT evaluada:** [resultado y bloqueo técnico](incidents/2026-09-08_EVALUACION_RECUPERACION_POST_FT.md).
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

**08-09, nueva detención PICO con caja vacía:** [diagnóstico](incidents/2026-09-08_PARADA_PICO_CAJA_VACIA.md).
Protección de fuerza izquierda y derecha activadas con 0,200 s de separación.
Operador dice caja soltada y ningún paro; lecturas paros 0/0, actuadores sanos
inmóviles, delta 0,001900 rad. Postura teleoperada NO HOME sustituye estado
anterior. Causa mecánica/estado físico y recuperación específica pendientes.
Sólo lectura; no rearme, HOME, reinicio ni modificación de protecciones.

**08-09, HOME tras finalizar el ensayo ENTRY:** [registro](incidents/2026-09-08_HOME_TRAS_ENTRY.md).
READY→HOME SUCCEED/status=4; HOME 20D máximo 0,002780 rad, velocidad cero,
actuadores sanos. Último estado medido HOME sustituye READY; confirmación visual
posterior pendiente. Revisión de ENTRY por inclinación y shadow 0/5 pendientes.

**08-09, retorno ENTRY→READY completado:** [registro](incidents/2026-09-08_RETORNO_ENTRY_READY.md).
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

**08-09, HOME→READY→ENTRY ejecutado:** [evidencia y estado](incidents/2026-09-08_READY_ENTRY_AUTORIZADO.md).
Ambas acciones SUCCEED/status=4; ENTRY 20D error 0,003835 rad, velocidad 0,
actuadores sanos. Captura completa de la transición: pico reportado 0,107861 rad/s.
Último estado ENTRY, VLA detenido/writers 0. Confirmación visual posterior
pendiente; retorno ENTRY→READY y cinco shadow (0/5) pendientes.
Esta actualización prevalece sobre los estados históricos HOME/ENTRY pendiente.

**08-09, plan reanudado en E6.1:** [gates y preparación](incidents/2026-09-08_REANUDACION_PLAN_E6_1.md).
HOME↔READY deja de ser bloqueante pendiente de ensayo. ENTRY XML/aceptación
cotejados; error proyectado al frame 40 de 0,001055 rad. Auditor nuevo identifica
relaciones rígidas y calcula barrido condicionado de útiles (4.096 celdas);
no validación física completa de ENTRY. Perfil P14 faltante añadido a ambos
hosts; validador Motion/inferencia Vision actualizados con backup y sin arrancar
contenedores. --check ahora verifica hashes de código y pasa. Seis tests nuevos,
shadow local correcto; HOME medido, VLA exited/restart=no. No nuevo movimiento.
Siguen pendientes ENTRY físico, fixture actual y cinco shadow (0/5).

**08-09, vuelta READY→HOME completada y confirmada:** [cierre del ciclo](incidents/2026-09-08_HOME_DESDE_READY_AUTORIZADO.md).
Goal único SUCCEED/status=4; HOME 20D máximo 0,002684 rad, velocidad 0,
actuadores sanos; operador confirma «todo bien». Ida y vuelta quedan PASS físico
en este ensayo con montaje actual. Captura parcial del retorno: 2.251 estados,
pico reportado 2,049366 rad/s. VLA detenido/writers 0; sin monitor persistente.
No cambios remotos de configuración/protecciones; geometría continua pendiente.
Este HOME sustituye READY como último estado físico documentado.

**08-09, READY ejecutado por autorización actual del propietario:** [resultado](incidents/2026-09-08_READY_AUTORIZADO_PROPIETARIO.md).
Propietario revocó bloqueo anterior y confirmó condiciones físicas tras aviso
de riesgo. Goal único SUCCEED/status=4; READY medido, error brazos 0,001938 rad,
velocidad 0, actuadores sanos, VLA detenido y writers 0. Sin cambios de
configuración/protecciones ni vuelta HOME. Operador confirma recorrido sin
problemas y READY estable/libre de contacto: PASS físico de esta ida con montaje
actual. Retorno y validación geométrica general pendientes; sin monitor continuo.

**08-09, barrido con abrazaderas incluidas:** [resultado condicionado](incidents/2026-09-08_BARRIDO_ABRAZADERAS.md).
36.864 celdas con cota intermedia continua para curvas especificadas; esferas
contienen soporte/patitas en cualquier orientación bajo errores supuestos.
Cuerpo central, brazo contrario y otras abrazaderas separados en esos casos;
propia muñeca/antebrazo inconclusos. No es registro geométrico físico ni
aprobación de interpolación vendor. Cero movimiento/conexiones, diez tests OK.

**08-09, rutas contrastadas en lectura:** [HOME↔READY](incidents/2026-09-08_CONTRASTE_RUTAS_HOME_READY.md).
Cuatro hashes instalados coinciden con referencias; retorno invierte puntos de
brazos. Task-list: TimeRatio ida 0.5/vuelta 1.0, no equivalencia temporal
demostrada. Éxitos históricos conservados; montaje registrado y barrido continuo
siguen pendientes. Diez tests locales OK; cero movimiento/cambios remotos.

**08-09, operador confirma HOME estable sin incidencias:** nueva lectura puntual
recibe FT bilateral y joints inmóviles; ver HOME_INTERNO_TRAS_LIBERACION.
FT no tarado/compensación no verificada, no prueba de ausencia de contacto.
READY solicitado pero no enviado: recorrido no validado. Sin monitor continuo.

**08-09, paro liberado por operador:** [HOME interno observado](incidents/2026-09-08_HOME_INTERNO_TRAS_LIBERACION.md).
CC ejecutó StartMotion y cruzr/home, terminó JoystickMode. Lectura posterior:
20 ejes no rueda error=0/status=0x1237, |q| y delta ≤0,003068 rad, velocidad 0;
paros 0/0, action server 1, robot_command writers 0, VLA detenido. No se envió
movimiento desde PC ni se monitorizó preventivamente. Confirmación visual pendiente;
no valida HOME↔READY. Sin monitor continuo.

**08-09, diagnóstico vivo bajo E-stop:** [informe](incidents/2026-09-08_DIAGNOSTICO_BAJO_ESTOP.md).
Principal 1/chasis 0, CC en WaitEStopRelease según log actual; hardware espera
start, actuator writers 0 y action server 0. Sin joints completos/FT disponibles.
Wi-Fi operativo, guard Vision disabled/inactive, VLA exited/restart=no.
Carga input 0, baterías discharging 67,0/98,4 %. Netdata Vision unhealthy y posible
desfase PC–robot ~25 s, sin corregir. Sólo lecturas, cero movimiento/rearme;
no preflight PASS ni monitor continuo. READY/rutas siguen pendientes.

**08-09, testigo del cuello ilustrado:** MODELO_CUELLO incluye PNG 3D determinista
de las mallas completas y ampliación de los dos triángulos que se cruzan en READY
histórico. Hashes y vértices contrastados, imagen inspeccionada. Marcador superpuesto,
no visibilidad física demostrada ni instrucción para inclinar cabeza. Sin movimiento.

**08-09, cuello revisado offline:** [auditoría de referencias](incidents/2026-09-08_MODELO_CUELLO.md).
URDF idéntico al ZIP; visual/colisión iguales y sin escala extra para cabeza/torso.
FK independiente coincide; con READY histórico medido persiste cruce modelado
cerca de la unión del cuello. No explica contacto real ni autoriza corregir
mallas por conveniencia. Tres tests pasan, READY intacto, cero conexión/movimiento.

**08-09, reanudación offline:** [contraste P1/P2/P3 cerrado](incidents/2026-09-08_REANUDACION_REFERENCIAS.md).
Son puntos 0/1/4 ya ajustados; sobreviven las dos correspondencias 2D y no se
obtiene montaje 3D. No repetir fotos/cotas. El run E6.1C-READY del 04-09 ya
documenta cabeza yaw;pitch; los dos órdenes del barrido posterior son sensibilidad,
no incertidumbre histórica nueva. Sin conexión, movimiento ni estado físico
actual comprobado. READY intacto; trayectos sin aprobación.

**RELEVO 07-09 → 08-09:** operador pide guardar para mañana. Punto exacto en
[`docs/incidents/2026-09-07_RELEVO_HOME_READY.md`](incidents/2026-09-07_RELEVO_HOME_READY.md).
Reconocidos P1/P2/P3 en foto izquierda; contraste CAD aún no ejecutado, patrón
simétrico previamente ambiguo. Figura generada sólo orientativa, original para
cálculos. Último estado reportado: energizado, ambos paros liberados, estable
sin contacto; NO consta apagado/aislamiento ni estado seguro de fin de jornada.
Sin órdenes ni monitor nocturno. READY intacto y aceptado como premisa, rutas no
validadas. Reanudar offline sin repetir cotas/fotos genéricas.

**07-09, perfil de trabajo sin PGC:** retiradas seis geometrías históricas
sólo offline. Abrazaderas nominales 82×100×130 registradas descriptivamente,
sin transformación inventada; cobertura mundial del útil sigue incompleta.
Barrido por defecto corregido: 1.836 estados/561 pares de robot/34 avisos AABB;
menos pares NO implica mayor seguridad. Render separado y seis tests pasan.
Ver VALIDACION_HOME_READY_HOME, home_ready_clamps_profile y
home_clamps_unregistered_visual. READY y robot sin modificar.

**07-09, READY válido como premisa del operador:** se acepta expresamente para
análisis que READY no presenta choques reales; no es verificación independiente
ni aprobación de tránsito. Aviso cabeza–torso pasa a discrepancia de modelo bajo
esa premisa, sin modificar mallas/pares/READY. Render HOME sintético con colores
de procedencia y esferas hipotéticas: home_mesh_visual. Ver VALIDACION_HOME_READY_HOME.

**07-09, READY final inalterable por operador:** descartada variante cabeza fija
para solicitud vigente. Nuevo auditor offline preserva objetivos y evalúa READY
completo: cabeza–torso intersecta en ambas hipótesis de orden, confirmado con
dos cruces independientes arista–cara por hipótesis. No prueba contacto real;
un rodeo no elimina intersección en destino del modelo. Cuatro tests pasan,
evidencia ready_endpoint_locked; ver VALIDACION_HOME_READY_HOME. Sin modificación
de READY, robot o despliegue. Correspondencia física de mallas sigue pendiente.

**07-09, testigos STL y variante offline:** 48 testigos refinados: 36 separados
en ese punto y 12 ceros (seis PGC histórico, seis uniones de brazos en cero).
Barrido cabeza–torso: 26/27 intersecciones por hipótesis pitch/yaw, cero separa
sólo 0,200 mm modelados. No contacto físico demostrado. Variante brazos READY
con cabeza fija generada en informe, NO READY completo, no ejecutable/aprobada.
Tres tests nuevos; sin robot/despliegue. Ver VALIDACION_HOME_READY_HOME y
evidencia full_home_ready_mesh_witnesses_v2.

**07-09, geometría HOME↔READY ampliada (offline):** 1.836 estados hipotéticos,
828 pares, 48 solapamientos AABB inconclusos (incluida cabeza–torso); no choques
demostrados ni aprobación. Tres calendarios de brazos y dos órdenes hipotéticos
de cabeza; cintura/resto cero sintético. URDF PGC no representa abrazaderas reales.
Evidencia full_home_ready_screen_v2; detalle VALIDACION_HOME_READY_HOME. Tres tests
pasan; sin robot. Velocidad sigue siendo requisito independiente pendiente.

**07-09, prioridad HOME↔READY sin VLA:** XML locales de apertura/cierre piden
0,6 rad/1,5 s: pico necesario >=0,40 rad/s, incompatible con provisional0,15
si duration es tiempo real. No equivalencia con candidato lento ni reescalado
vendor demostrados. Ayuda obsoleta corregida, sin cambio de tareas/despliegue.
Auditor y evidencia ready_home_timing_audit; detalle VALIDACION_HOME_READY_HOME.

**07-09, 24 avisos internos refinados:** 264 cálculos STL, 18 mínimos positivos
y seis ceros en uniones adyacentes (no choques físicos demostrados ni contacto
permitido). STOP VLA trazado hasta backend: vacía cola/destruye publisher, no
demuestra parada mecánica ni cancela necesariamente consigna aceptada. 0,414 s
histórico FT→halt no es tiempo de frenado. Evidencia arm_internal_geometry_mesh,
detalle SALIDA_MUNECA_FIJA. Gates físicos no cerrables con esos datos; sin robot.

**07-09, cobertura interna ampliada:** mallas visuales shoulder_pitch halladas
en SDK (1462 triángulos/lado), sólo sustituto provisional offline, no collision
vendor validada. 56 pares internos: 42 rígidos comunes y 14 con relación variable;
24 solapamientos AABB sin excluir adyacencias. Detalle SALIDA_MUNECA_FIJA,
evidencia 20260907_arm_internal_geometry.json. No robot ni aprobación física.

**07-09, pares cruzados acotados:** 459/462 pares brazo–cuerpo/otro brazo con
cota positiva entre muestras; tres restantes coinciden con refinamientos STL
positivos previos. Bloque parcial condicional, no porcentaje de seguridad global.
Siguen útil, propios brazos, geometría faltante, escena, seguimiento y parada.
Seis tests base pasan; evidencia 20260907_fixed_wrist_cross_pair_bounds.json.
Sin robot; SALIDA_MUNECA_FIJA lista cobertura y pendientes.

**07-09, intervalo entre muestras acotado condicionalmente:** tres pares
STL hombro–torso con fórmula min(d)-R*h/2, cotas 10,621/10,620/18,501 mm.
Sólo superficies rígidas, giro único, distancias numéricas asumidas correctas;
no error físico/contención/escena/frenado ni validación global. Tres tests,
evidencia 20260907_shoulder_between_samples.json. SALIDA_MUNECA_FIJA detalla
hipótesis. Sin robot o autorización física.

**07-09, barrido STL extendido:** tres pares hombro–torso, 61 posturas/par,
183 cálculos con kernel corregido. Mínimos iniciales 11,215/11,213/20,196 mm;
ninguna muestra a cero. Vuelta ideal usa mismas muestras invertidas, no runtime.
Sin continuidad/contención/escena/frenado ni aprobación física. Evidencia externa
20260907_fixed_wrist_shoulder_path_61.json y SALIDA_MUNECA_FIJA. Sin robot.

**07-09, corrección crítica del cálculo entre triángulos:** se omitían cruces
arista–interior de cara; contraejemplo daba distancia 1 cuando era 0. Corregido
en analyze_vla_clearance_guards_e6_0d.py, cinco casos y 300 referencias pasan.
Históricos que dependen de esa distancia requieren regeneración antes de uso;
no se revalidan automáticamente. Tres testigos STL iniciales nuevos hombro–torso
dan 11,215/11,213/20,196 mm entre superficies, no recorrido/contención/margen real.
Ver SALIDA_MUNECA_FIJA. Cero robot o aprobación física.

**07-09, salida fija ampliada offline:** 231 pares brazo–cuerpo/otro brazo por
lado, 242 muestras salida/vuelta. AABB inconclusa en tres pares hombro–torso,
testigo inicial cero sintético; otros pares separados en muestras. Falta geometría
propia shoulder_pitch, abrazaderas/entorno/barrido/frenado no cubiertos. Tres tests
pasan. No aprobación ni robot. Detalle SALIDA_MUNECA_FIJA, evidencia externa
20260907_fixed_wrist_arm_body.json.

**07-09, salida muñeca fija offline:** registradas diagonales reportadas L174/R178 mm,
no holgura mínima. En tramo sintético de hombro, 121 muestras/lado, relación
wrist_pitch→sensor constante a precisión numérica; distancia origen sensor–AABB
cuerpo aumenta 228→518 mm L, 220→518 mm R. No comparable directamente con
patita física, no barrido completo ni aprobación. Evidencia y pendientes en
`docs/incidents/2026-09-07_SALIDA_MUNECA_FIJA.md`. Sin conexión/movimiento.

**07-09, auditoría de peor caso por tramo:** los 30 segmentos existentes
del barrido de 201 muestras tienen algún solapamiento esfera–propio brazo
bilateral incluso con radio mínimo ampliado. No sólo staging→A. Serializar
brazos o aumentar margen no lo elimina; no prueba contacto físico. Cotas de
error siguen sin verificación física. Alternativa de conservar geometría
relativa de muñeca identificada sólo como hipótesis analítica, no ruta aprobada.
Detalle en BARRIDO_PESIMISTA_RECORRIDO. Sólo archivos locales, sin robot.

**07-09, avance offline salida/medición:** generador admite salida histórica
cero→staging→A→READY, total 35,389 s y posición URDF aprobada; siete tests.
No ruta nueva de observación ni colisiones aprobadas: temporizar no elimina
solapamiento propio brazo. Emparejador temporal nuevo, tres tests, rechaza
desfase 1,288 s, sellos cero y falta de referencia de reloj. Recolector continuo
pendiente. Sin red/movimiento/despliegue. Véanse BARRIDO_PESIMISTA_RECORRIDO
y TELEMETRIA_ESTACIONARIA en docs/incidents.

**07-09 ~12:54 Madrid, cámara pasiva localizada:** stereo/color/info retenido
960×576 con sello cero; stereo/color/raw entrega Image2m bgr8 con sello real.
Dos consultas concurrentes imagen/joints difieren 1,288 s: no sincronizadas.
Sin arranque de cámara, modos ni movimiento; píxeles no guardados/inspeccionados.
Pendiente buffer por sello y referencia de reloj. Detalle en TELEMETRIA_ESTACIONARIA.

**07-09 ~12:49 Madrid, diagnóstico estacionario:** muestras actuales joints
con brazos |q| <= 0,000958738 rad y velocidades reportadas cero; FT de ambas
muñecas disponible con sello, sin tara/compensación/umbrales verificados.
Última transición CC observada JoystickMode; PC backend activo, UI inactiva,
cero clientes WebSocket no demuestra STOP. Cámara sincronizada pendiente.
Sólo lectura, sin comandos. Detalle `docs/incidents/2026-09-07_TELEMETRIA_ESTACIONARIA.md`.

**07-09 ~12:33 Madrid, HOME realizado por rearme del operador:** reporte
«se fue a home sin problemas». Log Motion registra cruzr/home 18:33:35–42
(host +08:00), éxito de cinco grupos/BTree y sin alarmas FT explícitas en
ventana revisada; 184 avisos de consigna de cabeza fuera de rango. Lectura
retrospectiva iniciada después del movimiento, no vigilancia preventiva.
Sin órdenes del agente. No aprueba otras rutas ni demuestra ausencia de daño.
Detalle `docs/incidents/2026-09-07_HOME_OBSERVADO_1233.md`.

**07-09, peor caso solicitado sin soporte:** contraste de evidencias existentes:
radio nominal independiente de orientación 119,411 mm frente a distancia de
muñeca izquierda 40,639 mm en testigo histórico; solapamiento incluso sin
reservas, no contacto físico demostrado. Ampliar cotas no permite aprobar.
Debe restringirse incertidumbre de montaje con evidencia, no escoger hipótesis
favorable. Análisis en RUTA_HOME_ALTERNATIVAS; sin robot ni aprobación física.

**07-09, referencias físicas revisadas:** fotos/cotas existentes no justifican
una única cota nueva que cierre el registro. Falta asociar origen/ejes y cara
del sixforce_link a referencias físicas; no repetir medidas generales o fotos.
Se precisa croquis de referencia del sensor o registro cualificado, no CAD
completo del útil. Alcance en RUTA_HOME_ALTERNATIVAS. Contrato sin modificar,
ningún nuevo permiso físico ni conexión al robot.

**07-09, candidato offline contrastado con URDF:** límites de posición válidos
para los 14 ejes y extremos de las tres etapas; monotonicidad de smoothstep
extiende ese resultado al segmento continuo (sólo posición, no colisiones).
Generador exige --urdf, rechaza límites ausentes/inválidos y devuelve 3 ante
rechazo. Seis tests pasan. Evidencia 20260907_home_offline_candidate_v2.json,
hash URDF incluido. No son límites activos Motion verificados. Sigue sin
aprobación física ni resolución del útil frente a la muñeca.

**07-09, temporización offline implementada:** build_home_offline_candidate.py
genera retorno histórico P14 READY→A→staging→cero de brazos con smoothstep
quíntico, reposo en cada etapa. Límites provisionales 0,15 rad/s y 0,5 rad/s²
acotados analíticamente para esa curva; duraciones 4,645/23,245/7,500 s,
total 35,389 s. Cinco tests pasan. No búsqueda de ruta ni validación de
colisiones; resto de ejes no especificado (no cero implícito), no estado real,
no exportación ejecutable, no equivalencia con Motion. Evidencia externa
20260907_home_offline_timing_candidate.json. Sin conexión al robot en este paso.

**07-09, plan-only no demostrado:** inspección de ArmTask, GetMnpActionList,
PickPlanner/WalkPlanner y headers SDK no encuentra exportación previa de
trayectoria articular HOME. ArmTask ofrece ejecución/estado, no usarlo como
dry-run ni lanzar/cancelar para probar. Búsqueda ampliada de interfaces bajo
/opt/walker; alcance y hashes en informe RUTA_HOME_ALTERNATIVAS. Sin llamadas
ROS, SDK ejecutado ni cambios remotos. Ruta física sigue pendiente.

**07-09, investigación de ruta HOME:** releídos HOME y open_arm, hashes sin
cambio respecto a auditoría. Localizada alternativa instalada
move_dual_arms_home_ompl (14 objetivos, OMPL solicitado), no ejecutada.
Variantes genéricas cintura/base no reutilizables sin adaptación dimensional.
No demostrada API plan-only, geometría activa ni integración previa al HOME
interno. Ruta NO aprobada; sin modificaciones remotas ni ROS. Detalle y hashes:
`docs/incidents/2026-09-07_RUTA_HOME_ALTERNATIVAS.md`.

**07-09, continuación Control Center sólo lectura:** comando de arranque y
lectura completa de config/cc.conf (725 bytes) y base.conf (1892 bytes)
verificados; no contienen opción para omitir HOME/StartMotion. No demuestra
ausencia de otra interfaz vendor. No se modificó CC ni se ejecutó ROS/rearme.
Guard nuevamente disabled, active/exited. HOME interno y validación geométrica
siguen pendientes; no hay aprobación física. Hashes, alcance y resultado
negativo de búsqueda en log en
`docs/incidents/2026-09-07_DIAGNOSTICO_ARRANQUE_SOLO_LECTURA.md`.

**07-09 ~09:44 UTC, cambio remoto autorizado:** deshabilitado únicamente
autoarranque de `cruzr-v020-boot-guard.service` en Vision mediante systemctl
disable (sin --now). Verificado UnitFileState=disabled; active/exited y marcas
de ejecución sin cambio. Sólo retirado enlace multi-user.target.wants; script
y unidad intactos, hashes coincidentes. Copia previa 093815Z y posterior
094421Z_BOOT-READONLY, manifiesto verificado. No stop/restart/mask, Control Center,
ROS, paros ni movimiento. Reversible por reenable con revisión/autorización;
NO bloquea HOME interno ni arranque manual del guard. Detalle en diagnóstico
de arranque y guía especializada. Este cambio sucede después de la captura
anterior y sustituye el estado «propuesto/pendiente autorización» de abajo.

**07-09 09:38 UTC, diagnóstico conectado sólo lectura:** Motion/Vision accesibles
por Wi-Fi; inventario de contenedores y copia del guard de Vision preservados en
`20260907T093815Z_BOOT-READONLY/`. Guard enabled, active/exited, último código 0;
copia instalada `6c3cbe48…` carece del bloqueo --run del repositorio (única diferencia).
VLA control/inference Exited; no arrancados. Cero llamadas ROS, docker exec,
restart, configuración remota o movimiento. Postura/paros/cargador no verificados.
Se propone deshabilitar sólo autoarranque del guard, pendiente autorización
específica; NO contiene HOME interno. Detalle en
`docs/incidents/2026-09-07_DIAGNOSTICO_ARRANQUE_SOLO_LECTURA.md`.

**07-09, refinamiento STL no elimina bloqueo propio brazo:** dos testigos L/R
del barrido de 201 muestras/segmento, staging→A fracción 0,685. Distancias del
centro supuesto a malla wrist_pitch: 40,639/40,652 mm; ambas dentro de esfera
mínima 139,411 mm. No demuestra colisión real de abrazadera; muestra que la
aproximación esférica no permite aprobar esta zona, incluso refinando el brazo.
Kernel: 4 casos + 300 referencias aleatorias correctos; fuente/hash/triángulo
en `20260907_clamp_wrist_mesh_witness.json`. No reescaneo completo STL ni nueva
aprobación. Cierre y dependencias en
`docs/incidents/2026-09-07_CIERRE_BLOQUEOS_APROBACION.md`. Sin cambios físicos.

**07-09, recorrido ampliado offline:** candidato histórico brazos cero sintético
→ staging → A → READY B y vuelta, resto de joints a cero explícito. Tres órdenes
(sincronizado, L antes R, R antes L), 3.030 y 6.030 muestras. Cuatro radios:
sin solapamiento muestreado esfera–cuerpo/brazo contrario/otra esfera; sí con
propio brazo (wrist_pitch), resultado global inconcluso. Radio 204,411 mm:
cuerpo mínimo R 15,550 mm, L 23,757; entre esferas 250,166 mm. No trayectoria
real, no barrido continuo ni protección de HOME. Shoulder_pitch sin geometría
propia en URDF, cobertura pendiente explícita. Cuatro tests nuevos y suite v5
correctos; detalle `docs/incidents/2026-09-07_BARRIDO_PESIMISTA_RECORRIDO.md`.
Sin red ni modificación de robot, límites, paros o perfil operativo.

**07-09, sensibilidad con cotas ampliadas solicitada por operador:** análisis
local nuevo `audit_clamp_pessimistic_screen.py` usa postura URDF cero explícita
(NO estado medido ni HOME validado), esfera nominal 119,411 mm y errores de
centro hipotéticos 10/25/50/75 mm más reserva geométrica hipotética 10 mm.
Cuatro radios 139,411–204,411 mm no se solapan con las AABB de los 26 links
de cuerpo evaluados; peor separación para el mayor radio: R 15,550 mm y
L 23,757 mm, frente a `lifter_pitch_2_link`. No se ensayaron brazos entre sí,
útil-brazo, entorno ni recorridos. Hipótesis no verificadas, perfil operativo
no seleccionado, autorización física falsa. Tres tests nuevos pasan, evidencia
externa `20260907_clamp_pessimistic_screen.json`. Sin conexiones/despliegues.

**07-09, alternativa condicional independiente del giro:** sobre la envolvente
nominal T=130 se calcula radio respecto al origen descriptivo de 119,411 mm
(`hypot(47,55,95)`). La invariancia de norma evita seleccionar orientación
para esta cota esférica, pero NO identifica el centro físico en sixforce_link
ni valida ortogonalidad/referencias, incertidumbre o recorrido. Intersección
de esfera no prueba contacto real. Script `audit_clamp_orientation_bound.py`,
tres tests nuevos y suite v4 correcta (`20260907_requalification_regressions_v4.json`).
Informe externo `20260907_clamp_orientation_bound.json`, centros y radio seguro
nulos, sin trayectoria evaluada, red ni movimiento. No se reemplaza el contrato
de montaje por esta cota ni se habilita HOME.

**07-09, T=130 mm y contención recibidos (OBSERVADO, declaración del operador):**
«T=130, no sobresale nada fuera de los otros márgenes». Incorporado al contrato
como cotas reportadas, sin completar R/t ni margen. Envolvente nominal propia
82×100×130 mm: u −35/+47, v −55/+45, profundidad −35/+95 mm. Alcance bilateral
basado en igualdad previamente declarada, no metrología independiente L/R.
Generador actualizado, ocho tests correctos; JSON y SVG/PNG inspeccionado en
`20260907_clamp_nominal_T130/` (raíz externa de evidencias). Estado
`NOMINAL_TOOL_ENVELOPE_UNREGISTERED`. Ya no falta T ni contención nominal del
soporte; siguen incertidumbre, registro al sensor y recorridos/arranque.
Sin cambios remotos ni autorización física.

**07-09, continuación offline del soporte:** auditor de montaje no expone
límites de un lado si falla su evidencia y rechaza desbordamientos no finitos.
Test explícito impide interpretar el modelo parcial como contrato de montaje.
Suite ampliada con modelo/asimetría, informe externo
`20260907_requalification_regressions_v3.json`. Nueva ficha
`docs/incidents/2026-09-07_COTAS_PENDIENTES_SOPORTE.md`: profundidad total T
desde almohadillas al extremo trasero, más comprobaciones de contención respecto
a bordes ya medidos. No exige CAD ni otra ronda de fotos genéricas; T y
contención aún no recibidos. Sin cambios en robot, contrato, paros o despliegues.

**07-09, modelo propio sin exigir CAD inexistente:** se corrige el requisito:
no es obligatorio disponer del CAD de fabricante de la abrazadera. Se generó
un modelo descriptivo parcial reproducible con las cotas del operador mediante
`scripts/build_clamp_simplified_model.py`: placa 70×100×36 mm, reserva lateral
de 12 mm, profundidad 59–95 mm. Soporte/riostras/tornillería quedan explícitamente
sin límites medidos; no se inventa su envolvente ni R/t. Cuatro tests correctos,
SVG/PNG inspeccionado y JSON en la raíz externa de evidencias,
`20260907_clamp_simplified_model/`. Estado `PARTIAL_MODEL_NOT_REGISTERED`.
Últimas seis vistas L recibidas sólo en chat documentan el conjunto; no se les
atribuye hash local. No se requieren más fotos genéricas. Pendientes: límites
del soporte, contención de patitas en altura/profundidad, incertidumbre y registro
al sensor; después recorridos/arranque. Sin red, robot, desbloqueo ni despliegue.

**07-09, límite del registro fotográfico identificado:** los conjuntos CAD
central, exterior y combinado conservan exactamente sus centros al reflejar
Y (residuo 0 mm en ambos lados). Esto explica el empate de correspondencias
2D, no demuestra dos montajes físicos. Informe exterior v2 y seis tests
correctos. No repetir esta fotografía ni elegir por RMS. Sigue pendiente
identificar cara/normal/plano físico con referencia independiente y acotar el
soporte completo; HOME/rearme continúan bloqueados. No hubo red ni movimiento.

**07-09, contraste exterior con fotos existentes:** render ortográfico de ambas
caras del STL y extracción de cuatro contornos exteriores CAD z=4 mm,
centros (±28,±17,5) mm. Extrapolación 2D desde seis puntos centrales a cuatro
cabezas exteriores: dos hipótesis destacan entre las seis de buen ajuste
central (L ~10,2 px frente a ~142; R ~21,2 frente a ~156). No hay umbral de
aceptación ni montaje 3D validado; identidad/planos/oclusiones siguen pendientes.
Evidencias externas `20260907_sensor_cad_views/` y
`20260907_clamp_outer_correspondence.json`; cinco tests de proyección pasan.
Cero robot/red/movimiento. No se piden nuevas fotos; ver contraste fotográfico.

**07-09, corrección de solicitud fotográfica y asimetría CAD:** no pedir más
vistas inferiores ni buscar un conector cuya visibilidad no está demostrada.
Las fotos recibidas documentan el montaje; el pendiente es técnico. Auditoría
local nueva demuestra que la malla completa del sensor y sus triángulos z=0
no tienen la simetría de 120° del patrón central. No identifica todavía una
característica física ni calcula R/t. Tres tests correctos, evidencia externa
`20260907_clamp_sensor_asymmetry.json`. Detalle y punto de reanudación en
`docs/incidents/2026-09-07_CONTRASTE_FOTOS_CLAMPS.md`. Sin red, movimiento,
despliegue ni desbloqueo; mantener restricción de HOME/rearme.

**07-09, ampliación autónoma y límite de evidencia:** E6.0N instalación,
E6.0O recarga y E6.0P apply/restore con bloqueo local directo; suite v2 correcta
(18 variantes bloqueadas, siete syntax checks). Evidencia externa
`20260907_requalification_regressions_v2.json`. Manual SDK revisado: figura
de ejes corresponde a manos articuladas; offsets de sensores no son del clamp.
Pendiente técnico: identificar una correspondencia no simétrica del sensor
respecto a muñeca/soporte; no solicitar otra foto sin localizar antes esa
referencia en el CAD y justificar su visibilidad. No repetir A–F.
Detalles y límites en contraste de fotos/recalificación. Cero cambios remotos.

**07-09, suite offline y entradas incompletas:** HOME ya no sustituye datos
ausentes por ceros ni cmd_pos por posición; endpoint20D rechaza tipos/límites
inválidos y nombres duplicados. E6.1C instalación/recarga con bloqueo directo
antes de conexión (14 variantes verificadas). Suite
`scripts/run_contact_requalification_offline.py`: 19 unittest, 36 casos de
endpoint, cuatro syntax checks y self-test de recovery correctos; evidencia
externa `20260907_requalification_regressions.json`. Estado
`OFFLINE_REGRESSIONS_OK_PHYSICAL_BLOCKED`, no validación de movimiento.
Sin despliegues, recargas ni comandos al robot. Pendientes físicos/geométricos
en el informe de recalificación y matriz prioritaria del plan.

**07-09, HOME reconstruido a nivel de órdenes:** ambos arranques del 04-09
escalonan `Now move` elevador/L/R/cintura/cabeza, con dispersión 0,805274 y
0,806148 s, aunque todas las duraciones son 6 s y objetivos cero. Primer
HOME muestra avisos de rango L:2, R:2 y head:2 antes de FT; no son posiciones
medidas. No se reconstruyó la trayectoria cartesiana ni tiempo de parada.
Herramienta offline `scripts/audit_home_group_timing.py`; evidencia externa
`20260907_home_group_timing.json`; detalle
`docs/incidents/2026-09-07_HOME_TEMPORIZACION.md`. Sin red ni movimiento.

**07-09, cierre de aprobación documental obsoleta:** E6.1C podía regenerar
un PASS de geometría con el proxy E6.0J sin montaje real registrado. Se retiran
las entradas públicas del wrapper offline (--check/--run) y analizador directo:
`BLOCKED_RETIRED_UNREGISTERED_CLAMP_GEOMETRY`, salida 78; ningún helper/fuente
de trayectoria ejecutado. Informes históricos preservados, salida nueva sin
sobrescritura. Siete tests de recalificación y tres de fotografía correctos.
Sin cambio remoto ni movimiento; HOME interno sigue sin interceptar.
Detalle: `docs/incidents/2026-09-07_REQUALIFICACION_CLAMPS.md`.

**07-09, ajuste fotográfico offline:** doce correspondencias por lado evaluadas
en originales 1/2; seis dan RMS prácticamente idénticos (L~0,852 px,
R~1,022 px). Compatible con patrón CAD, pero sin orientación absoluta ni R/t
demostrados. No son tolerancias de seguridad. Script
`scripts/audit_clamp_photo_correspondence.py`, puntos manuales en
`config/clamp_photo_landmarks.json`, evidencia externa
`20260907_clamp_photo_correspondence.json`. Sin red/movimiento ni cambios de
bloqueo; detalle en `docs/incidents/2026-09-07_CONTRASTE_FOTOS_CLAMPS.md`.

**07-09, referencia CAD de sensor:** inspección offline reproducible añade
`scripts/audit_clamp_sensor_reference.py`. Superficie z=0 candidata en ambos
STL, sin correspondencia física de fijación demostrada. Vistas inferiores
recibidas en chat: primera L, segunda R; originales `/home/lacuna/Imágenes/1.jpeg`
y `2.jpeg` inspeccionados y SHA-256 registrados en el contrato y contraste.
Se confirman visualmente patitas del lado del torso en estas vistas, no ejes ROS.
Seis contornos CAD de ~4,2 mm presentan simetría de
120°: su número no identifica por sí solo el montaje ni los tornillos visibles.
No repetir cotas de placa. Evidencia: `20260907_clamp_sensor_bolt_pattern.json`
en la raíz externa de evidencias; detalle en el contraste de fotos.
Resultado `CAD_REFERENCE_CANDIDATE_ONLY`; cero red y movimiento.

**07-09, espesor bilateral confirmado:** F=36 mm (34+2); placa+almohadillas
70×100×36 mm, profundidad descriptiva desde eje 59…95 mm. Prisma con patillas
82×100×36 mm sigue candidato sujeto a inclusión en profundidad. Cinco tests
offline pasan; soporte, transformación y barrido pendientes, sin movimiento.

**07-09, contorno frontal actualizado:** placa 70 mm centrada; con patillas
82 mm. Operador confirma ambas patillas hacia interior en postura actual.
Envolvente frontal local −35/+47 mm y −55/+45 mm, no ejes ROS ni volumen
completo. Cuatro tests offline aprobados; montaje/recorridos siguen bloqueados.

**07-09, medidas manuales actualizadas:** ambos clamps A=95, B=45, C=55 mm
reportados; altura total remedida directamente=100 mm; dos patillas por
clamp, proyección lateral=12 mm. Registro separado de la transformación
geométrica en `config/clamp_mount_requalification.json`: referencia B/C
aclarada por operador (unión real, centro daría 50/50). No repetir A/B/C;
faltan ancho/posición lateral y correspondencia al frame; sin PASS de barrido.

**07-09, contraste fotográfico offline:** seis fotos del montaje corregido
recibidas y hash-identificadas. URDF: unión muñeca→sensor de 77,12 mm y
sensor→PGC de traslación cero; ninguna es una transformación demostrada del
clamp pasivo. [Referencias y cotas pendientes](incidents/2026-09-07_CONTRASTE_FOTOS_CLAMPS.md).
Sin movimiento, conexión al robot ni modificación del bloqueo.

> **07-09 — contención local implementada:** [estado de recalificación](incidents/2026-09-07_REQUALIFICACION_CLAMPS.md).
> Doce variantes de lanzamiento rechazadas en tests sin conexión; no cubre
> HOME interno del arranque, UI/PICO ni el guard instalado en Vision.
> E-stop mantenido; no liberar ni reiniciar para probar. Inspección reportada:
> daño sólo en carcasa; clamps restauradas. Geometría bilateral y barrido
> pendientes; E6.0K retirado para nuevos PASS. No hubo despliegue ni movimiento.

**Última actualización:** 8 de septiembre de 2026
**Unidad:** Cruzr S2, SN `WAE001UBT60000669`  
**Propósito:** relevo técnico y operativo entre sesiones, personas y agentes

Este documento es el índice vivo del proyecto completo. Conserva el estado
conocido del robot, las modificaciones persistentes, lo que ya funciona, los
bloqueos y el punto de reanudación. No sustituye las guías especializadas ni
certifica el estado físico actual.

`AGENTS.md` obliga a Codex a leer esta fuente al iniciar una sesión desde el
repositorio. Si se modifica aquí una condición material, debe actualizarse
también la fuente especializada enlazada.

## 1. Cómo interpretar el documento

- **VERIFICADO:** demostrado en esta unidad mediante estado, archivos, hashes,
  logs, topics, servicios o una prueba controlada.
- **OBSERVADO:** visto durante una prueba, pero sin causa interna totalmente
  demostrada.
- **INFERENCIA:** explicación compatible con la evidencia que requiere otra
  prueba o confirmación del proveedor.
- **PENDIENTE:** no probado, no resuelto o no contestado por DSA/UBTECH.
- **DESCARTADO:** hipótesis o workaround contradicho por la evidencia.

Una observación histórica no autoriza movimiento. Al retomar, comprobar de
nuevo el estado físico y lógico.

## 2. Relevo vigente

### Alerta prioritaria 07-09: auditoría de daños, movimientos suspendidos

Prevalece la [auditoría de contactos y HOME](incidents/2026-09-07_AUDITORIA_CONTACTOS_HOME.md)
sobre las conclusiones preliminares del 04-09. **VERIFICADO:** StartMotion
ejecutó internamente `cruzr/home` a las 19:58:01 y 20:20:14 (+08) del 04-09.
El primer HOME registró FT izquierdo hasta −317,787 y abortó; el segundo
terminó. «Sin goals del PC» no significó «sin trayectoria HOME». El montaje
invertido está reportado, pero no demuestra por sí solo la causa de cada daño.

**PENDIENTE/CRÍTICO:** inspección material, montaje bilateral/transformación real,
trayectorias y cobertura de arranque/rearme. E6.0K asumía la posición de la
envolvente dentro del proxy; sus resultados y los gates derivados no cualifican
el montaje real. No reanudar movimiento usando esos PASS históricos.
La restricción es operativa/documental: **no existe aún un bloqueo técnico
central desplegado** que cubra Control Center y todos los runners.

Auditoría: 129 logs preservados, 137 artefactos hash-verificados, cronología
offline de 2.995 entradas. Sólo lecturas SSH/configuración; ningún ROS, goal,
rearme, reinicio o cambio remoto. El HOME/preflight de la tabla siguiente es
**histórico**, no estado actual: los logs muestran otro apagado el 04-09 a
20:53 (+08). Punto de reanudación: acciones A1–A5 del informe, sin ensayo físico.

### 2.1 Último estado conocido

| Elemento | Último estado documentado | Confianza |
|---|---|---|
| Postura | 08-09: HOME tras READY→HOME autorizado; máximo 20D 0,002684 rad, brazos 0,000959 rad, velocidad cero. Operador confirma recorrido correcto y estado estable/libre de contacto | **HOME MEDIDO Y VISUALMENTE CONFIRMADO; ESTADO VOLÁTIL** |
| Modo robot | 08-09: última transición CC observada JoystickMode; servidor de manipulación 1, preflight aprobado y tareas READY/recuperación SUCCEED/status=4 | **VERIFICADO EN ESTA EJECUCIÓN; RECOMPROBAR ANTES DE OTRA** |
| Efector | abrazaderas, `HW_TYPE=cruzr_s2_v1` confirmado por el check fresco | **VERIFICADO POR SOFTWARE; VACÍO DEBE RECONFIRMARSE ANTES DE MOVIMIENTO** |
| Actuadores | 08-09 posterior a HOME: 20 ejes sin error/habilitados, velocidad 0, delta posición–consigna máximo 0,002684 rad | **VERIFICADO; ESTADO VOLÁTIL** |
| Teleoperación PC | combinación oficial robot v0.2.0 + controller 4.7.0 + UI 4.1.0, overlay `clamp,0,0` y control bimanual. La sesión 10:25 terminó por protección FT, no por VR. Tras el reinicio el robot quedó en `AutoTaskMode`; no se ha recargado ni reanudado PICO | **BLOQUEADA HASTA NUEVO PREFLIGHT Y CAMBIO DE MODO AUTORIZADO** |
| Servicio PC/PICO | el STOP oficial tras `Ctrl+C` quedó confirmado; PC permaneció encendido durante el power cycle del robot | **STOP VERIFICADO; SIN CLIENTE FÍSICO** |
| VLA | 08-09 posterior a HOME: contenedores exited/exited, writers RobotCommand=0. HOME→READY→HOME se ejecutó como tareas deterministas, sin checkpoint ni ENTRY | **SIN HABILITACIÓN FÍSICA VLA NUEVA** |
| Cargador | 08-09 previo al retorno HOME: software CHARGER=0 y desconexión confirmada por operador | **DESCONECTADO EN PREFLIGHT; ESTADO VOLÁTIL** |
| Paros, ruedas y zona | 08-09: paros 0/0 medidos; ruedas bloqueadas, escena sin caja/mesa, ningún otro cliente de control y persona junto al paro confirmados. Final estable/libre de contacto confirmado | **OBSERVADO/VERIFICADO SEGÚN FUENTE; REVALIDAR ANTES DE OTRA ACCIÓN** |
| Mapa/localización | `test_route_01` se conservó; activación y localización son volátiles | **RECOMPROBAR** |

La rama `main` estaba limpia y sincronizada con `origin/main` en el commit
`4536f8a` antes de crear esta fuente global. El estado Git actual prevalece
sobre esa referencia.

El 28-08 se endureció localmente return-to-home. El script no mueve ya sin
`--run`, mide los 20 ejes,
trata todo inicio de home como no confirmado hasta observar las posiciones,
bloquea PICO/unknown/fuerza/autocolisión/fault y restringe la tarea vendor a
estados del ciclo de caja. `--force-held-home` quedó retirado y `--fast` ya no
omite gates. El 03-09 se corrigió el mapping para aceptar los IDs reales
v0.2.0 `11004…11001`; las regresiones de ambos mappings pasaron y un `--check`
vivo demostró `home` sin ordenar movimiento. La recuperación general desde
una postura arbitraria no-home sigue sin validación física; la ruta específica
VLA READY→HOME sí quedó validada por E6.0Q.


### 2.2 Primeros pasos de la siguiente sesión

Sin mover el robot:

```bash
git status --short --branch

# Elegir sólo los diagnósticos relacionados con la tarea.
./scripts/cruzr_blue_workbin_cycle.sh --check
./scripts/cruzr_blue_workbin_table_transfer.sh --check --fast
./scripts/teleoperation/cruzr_pico_teleop_pc.sh --check
./scripts/vla/run_ubtech_vla_shadow.sh --status
```

El diagnóstico de teleoperación exige que estén presentes los enlaces que
pretende comprobar; no debe interpretarse un fallo por PICO desconectado como
un defecto nuevo del robot. Consulte siempre `--help` antes de usar modos de
movimiento o recuperación.

## 3. Inventario técnico consolidado

### 3.1 Robot y red

| Componente | Valor conocido | Estado |
|---|---|---|
| Modelo | Cruzr S2 | **VERIFICADO** |
| Número de serie | `WAE001UBT60000669` | **VERIFICADO** |
| Software | genérico `v0.2.0` en Motion y Vision | **VERIFICADO** |
| Motion | Ubuntu 22.04, `192.168.11.2` | **VERIFICADO** |
| Vision/web | `192.168.11.3` | **VERIFICADO** |
| PC Ethernet | `eno1`, perfil `cruzr-s2`, `192.168.11.250/24`, autonegociación, 1000 Mb/s full, never-default; Motion/Vision directos | **VERIFICADO; PREFERIDO PC→ROBOT** |
| PC Wi-Fi Internet | `wlo1`, `DSA CORPORATE`, `192.168.40.120/24` | **VERIFICADO; CONSERVAR** |
| PC Wi-Fi robot/PICO y fallback | `wlx80afcad40bd6`, `Cruzr S2-0669`, `192.168.42.215/24`; `.42.0/24` directa y fallback `.11.0/24` vía `.42.2`, never-default, sin DNS y `powersave=disable` | **VERIFICADO; VIGILAR RESET USB REALTEK** |
| PICO Wi-Fi local | `Cruzr S2-0669`, `.211` el 25-08 y `.212` el 26-08 | **VERIFICADO; DHCP, REDESCUBRIR** |
| Efector actual | abrazaderas | **VERIFICADO** |
| `HW_TYPE` | `cruzr_s2_v1` | **VERIFICADO** |
| `TELE_DEVICE` | `pico` | **VERIFICADO** |
| `transmit` | `local` | **VERIFICADO** |
| `MC_SCENE` | vacío en contenedores inspeccionados | **VERIFICADO; DIFERENCIA CON SOP** |

Las credenciales del robot no se versionan. Las rutas Wi-Fi pueden diferir de
las rutas Ethernet; deben descubrirse en cada sesión.

### 3.2 Efectores

- Las abrazaderas son el efector operativo actual. La configuración coherente
  es `HW_TYPE=cruzr_s2_v1`.
- Las manos v4 se instalaron físicamente, se detectaron mediante
  `/mc/left_hand/joint_states` y `/mc/right_hand/joint_states`, y se probaron
  tareas de fábrica. Después se retiraron y se restauraron las abrazaderas.
- Con manos v4 se observó `HW_TYPE=cruzr_s2_v1_sps`. No reutilizar ese valor
  con abrazaderas.
- Las demostraciones de manos son trayectorias fijas, no manipulación autónoma.
  La coreografía de corazón requirió iteración y llegó a dejar un dedo en
  contacto con el torso; no debe ejecutarse desde una postura desconocida.

Guía: [`../scripts/hands/README.md`](../scripts/hands/README.md).

### 3.3 Mapa, estaciones y referencias

- Mapa: `test_route_01`.
- Waypoints conocidos: `START`, `PASO1`, `PASO2`, `PASO 3`, `PASO4`,
  `FINISH`, `MESA2_PRE`.
- La misión mesa 1 → mesa 2 no necesita pasar por `PASO1`; el destino global
  es `MESA2_PRE`, seguido de alineación local.
- AprilTag mesa 1: ID 112, familia `tag36h11`, lado negro medido 75 mm,
  `tag_size=0.075`; uso opcional.
- AprilTag mesa 2: ID 113, familia `tag36h11`, lado negro medido 73,5 mm,
  `tag_size=0.0735`; referencia del depósito.
- El tag 113 se detectó con márgenes de decisión altos y medidas estables. Hay
  referencias separadas para robot vacío y con caja sujeta porque la postura
  de transporte cambia la transformación cámara-tag.
- Activar el mapa no equivale a estar bien localizado. Después de un arranque,
  actualización o movimiento manual hay que validar la pose contra el entorno
  LiDAR antes de navegar.

Guía y valores completos:
[`guides/TRANSFERENCIA_CAJA_ENTRE_MESAS_CON_APRILTAG.md`](guides/TRANSFERENCIA_CAJA_ENTRE_MESAS_CON_APRILTAG.md).

### 3.4 Caja de ensayo y carga

- Contenedor azul de plástico, aproximadamente `600 × 400 × 220–230 mm`.
- Las pruebas descritas se hicieron con la caja vacía o ligera.
- DSA/UBTECH indicó por chat una carga útil máxima bimanual de 20 kg y un rango
  recomendado de 10–15 kg. Es una afirmación del proveedor, no una curva de
  payload validada para cualquier alcance, centro de gravedad o aceleración.
- No extrapolar las pruebas de caja vacía a carga industrial sin commissioning
  mecánico y límites documentados.

## 4. Cambios persistentes realizados en el robot

### 4.1 Actualización v0.2.0

**VERIFICADO:** se aplicó el paquete offline genérico v0.2.0 en Motion y
Vision. Antes se respaldaron configuraciones y mapas. El flujo estándar
`udoke replace` no recibió `upload-confirm` en tres intentos, por lo que se
aplicó el fallback manual incluido en el SOP: preinstalación, sustitución de
configuración, despliegue uDoke y postinstalación.

Se preservaron:

- mapa `test_route_01` y su checksum;
- configuración de abrazaderas `HW_TYPE=cruzr_s2_v1`;
- acceso web, navegación, manipulación y visión.

Detalles y reporte al proveedor: [`../upgrade.txt`](../upgrade.txt) y
[`../upgrade_summary.txt`](../upgrade_summary.txt).

### 4.2 Servicios estabilizados tras la actualización

- `main.x86` y `main.orin`: plantillas sin comando que reiniciaban en bucle;
  se dejó su reinicio automático deshabilitado.
- Cliente MQTT cloud: se bloqueaba con `segmentation fault` en el callback de
  batería; se dejó detenido y sin reinicio automático. El MQTT local/upilot
  permaneció estable.
- Netdata Vision: contenedor activo pero health check local de `19999` no
  saludable; pendiente de corrección oficial.
- Frecuencia GPU Vision: el script oficial informó 1,224 GHz frente a objetivo
  1,122 GHz; pendiente de confirmación del proveedor.

Estos cambios son workarounds locales y deben revisarse después de cualquier
actualización oficial.

### 4.3 Guard de arranque v0.2.0

**Nota de vigencia 2026-09-10:** el mecanismo descrito a continuación es
histórico. Su unidad permanece deshabilitada/inactiva; fue sustituido por la
espera preventiva dentro del comando de CC, con voz y pantalla separadas.
Para reinstalar usar las fichas BOOT-01/02/03 del
[registro vigente](SYSTEM_CUSTOMIZATIONS.md), no activar el guard antiguo.

**VERIFICADO:** Vision arrancaba Control Center antes de que Motion ofreciera
servicios x86 funcionales. El self-check fallaba, la cara quedaba roja y la
cabeza baja. Se instaló en Vision un guard reversible que:

- espera versión exacta v0.2.0 y servicios Motion funcionales;
- exige respuestas reales de self-check y muestras de las seis cámaras;
- sólo recupera el patrón `Fault` conocido con paros/cargador seguros;
- reconoce `WaitEStopRelease` como espera física segura y sale sin reiniciar ni
  mover;
- reinicia Control Center una vez, exige `StartMotion` y `JoystickMode`;
- devuelve la cabeza a la tarea oficial de home.

Archivos instalados en Vision:

```text
/usr/local/sbin/cruzr-v020-boot-guard
/etc/systemd/system/cruzr-v020-boot-guard.service
/usr/local/share/doc/cruzr-v020-boot-guard.md
```

Guía, comprobación y rollback:
[`guides/CRUZR_V020_BOOT_GUARD.md`](guides/CRUZR_V020_BOOT_GUARD.md).

### 4.4 VLA suministrado

**VERIFICADO:** se instalaron las imágenes, workspaces y
`checkpoint-40000` suministrados. Los dos contenedores se mantienen detenidos
con `restart=no`.

Se añadió un overlay local para:

- usar el perfil S2 correcto de 20 ejes;
- leer `/mc/whole_joint_states` como fuente read-only, porque
  `/mc/sdk/robot_state` no entregaba muestras;
- montar la variante GR00T suministrada y los metadatos de inferencia;
- validar chunks sin importar ni publicar `RobotCommand`.

La inferencia shadow produjo chunks finitos de forma esperada y confirmó cero
publicadores en `/mc/sdk/robot_command`. Desde `home`, los chunks se rechazaron
por diferencias de hasta aproximadamente 1,35 rad en ocho articulaciones. No
se habilitó movimiento VLA.

El 2026-08-28 se ejecutó task 0 otra vez desde una postura/escena viva no
documentada, por lo que el run se clasifica `OOD_RUNTIME_SMOKE`, no prueba
nominal. Generó dos chunks y el validador rechazó ambos por siete saltos del
primer punto; el máximo fue `R_shoulder_yaw_joint=1,339886 rad` frente a
`0,35 rad`. El goal solicitado por 8 s concluyó en `10,063076 s`, al terminar
el ciclo de inferencia en curso. STOP dejó ambos contenedores `exited` y cero
publicadores. Los logs se recuperaron de los contenedores detenidos en
`Humanoide-vla-evidence/20260828T080202_E2.0_recovered/`. Estado:
`PASS_SHADOW_SAFETY_ONLY`; E1.0/E1.3 y la validación de task siguen pendientes.

El 2026-08-28 se implementó y ejecutó E2.2 para PLACE sin utilizar el robot.
`run_vla_offline_place_e2_2.sh` creó un contenedor NVIDIA transitorio en Vision
con red desactivada, sin ROS ni `RobotCommand`, y cargó el checkpoint una sola
vez. El run válido `20260828T112730_E2.2` reprodujo task 1/episodio 465 y task
3/episodio 265 desde frame 0: salidas 10×20 finitas, MAE `0,007283609` y
`0,011394879`, sin violaciones de rango ni de primer salto. El split es el
último 15 % estratificado definido por el proyecto; el dataset sólo declara
`train`, por lo que no prueba generalización ni exclusión del entrenamiento.
`meta/info.json` anuncia `frame_index`, pero los parquets inspeccionados lo
omiten; se usó índice de fila únicamente tras validar task, episodio y la línea
temporal exacta a 120 Hz. Los dos intentos previos fallaron antes de inferencia
y quedaron documentados. La limpieza de JSON root-owned se corrigió y el
residuo temporal se retiró. Hashes de evidencia válidos; estado final
`exited/exited/publishers:0`, sin leer estado ni ordenar movimiento físico.

E3.0 amplió esa ruta a tasks 0–3, cinco episodios/fases por task y cinco
ejecuciones totales del seed 0: run `20260828T114346_E3.0`, 20 muestras y 36
inferencias. Las MAE medias fueron task 0 `0,004908891`, task 1 `0,006516288`,
task 2 `0,009686776` y task 3 `0,008983554`; las repeticiones seed 0 fueron
idénticas (`max_abs_diff=0`). Dos de 20 baselines excedieron el rango del
perfil: task 2/episodio 270/frame 0 predijo `lifter_pitch_1_joint=0,051654458`
en el primer punto, y task 3/episodio 287/frame 0 llegó a `0,060465574` y
excedió el máximo `0,000336618` en 7/10 puntos. No hubo violaciones del salto
inicial. El split local fue 424/76 episodios con solapamiento cero, pero el
proveedor sólo declara `train` y no se conoce la membresía del entrenamiento
de C0; no se permite afirmar generalización. Los hashes completos del
checkpoint coincidieron antes/después. Resultado
`PASS_OFFLINE_CAMPAIGN_WITH_CONSERVATIVE_VIOLATIONS`; sólo libera E3.1 offline,
no publicación física. Cierre `exited/exited/publishers:0`, sin estado ni
movimiento del robot.

E3.1 se ejecutó offline sobre dos frames fijos de tasks 0/2. El dataset carece
de RGB-D, calibración, máscara/pose 6D de la caja y geometría métrica de repisa;
por tanto la parrilla solicitada en metros/yaw real queda explícitamente
`BLOCKED_MISSING_RGBD_CALIBRATION_MASK_AND_SCENE_GEOMETRY`. El run válido
`20260828T120228_E3.1` aplicó una sola transformación global de imagen por vez:
desplazamiento horizontal ±5/±10 %, zoom 0,9/1,1 y perspectiva trapezoidal
±5/±15 grados-proxy. Las 26 variantes fueron `ACCEPT_STRUCTURAL`, las tres
entradas nominales por task produjeron exactamente lo mismo y no hubo
violaciones conservadoras. Los máximos cambios del chunk para task 0 fueron
`0,027470/0,040258/0,030194 rad`; para task 2,
`0,036843/0,053590/0,014256 rad`, respectivamente. Esto es sensibilidad a
imagen, no OOD métrico, éxito de agarre ni generalización. Checkpoint intacto;
cierre `exited/exited/publishers:0`, sin leer ni mover el robot. Sólo libera
E3.2 en sink offline.

E3.2 implementó un sink Python local sin ROS, red, mensajes de mando ni API de
publisher/action. El run `20260828T121832_E3.2` aceptó dos chunks válidos
consecutivos y rechazó 32/32 fallos de identidad, esquema, finitud, frescura,
timeline, límites, secuencia, control y cliente. Cancel/STOP son idempotentes,
el deadman expira con STOP enclavado y los chunks inválidos no consumen el ID.
Los ocho perfiles `P14_A…P20_AHLW` tienen cobertura unitaria de máscara/hold no
nulo, pero la campaña completa se ejecutó sólo para `P20_AHLW/low`. La pose
low es un midpoint sintético del perfil, no `VLA_READY_LOW`. Antes/después:
`exited/exited/publishers:0`; no se leyó estado ni se mandó movimiento. Falta
un límite certificado de aceleración, por lo que VLA-5 y todo ejecutor físico
siguen bloqueados. Sólo queda liberado E3.3 offline.

E3.3 se ejecutó como simulación temporal Python local y auditoría estática del
runtime suministrado, run `20260828T124011_E3.3`. Pasaron 22/22 casos: diez
puntos exactos a 80 ms, no repetición durante huecos, timeout inter-chunk,
solapamiento/dispatch tardío fail-closed, IDs, cancel antes/durante/entre
chunks, STOP, pérdida de imagen/estado, timeout de sesión y política candidata
de cinco flags. Cancel/STOP/fault purgan la cola en el mismo evento lógico. El
módulo no importa ROS/red, no contiene API de publisher/action ni topic físico;
antes/después quedó `exited/exited/publishers:0`, sin leer estado ni mover.

La auditoría UBTECH no permite cerrar VLA-3: Vision declara `0,2 Hz`, chunks
10×20 a `0,08 s` (horizonte `0,72 s`) y termina con un único
`flag_pred > 0,1`, mientras el YAML declara `continuous_end_chunk_num=5` sin
que el Python lo consulte. Además, el ejecutor bajo `src/` interpola a 900
puntos/9 s y la copia bajo `install/` a 600 puntos/6 s. El contrato local de
cinco flags y timeout de hueco a 0,5 s es una propuesta fail-closed, no la
semántica física del proveedor. Resultado
`PASS_LOCAL_TEMPORAL_FAIL_CLOSED_VENDOR_SEMANTICS_UNRESOLVED`; sólo se libera
E4.0 de resolución de artefactos en lectura, nunca movimiento.

E4.0 se ejecutó en lectura local/remota, run final corregido
`20260901T075728_E4.0`. Motion sí
contiene `clamp_s2_joints_trajectory` (hash `7722b734…7f6`, 2×14,
`1,5 + 1,0 s`) y `clamp_s2_joints_trajectory_back` (hash
`ee39039c…389`, 2×14, `2,0 + 3,0 s`). El back termina en el primer waypoint
forward, pero no invierte la secuencia completa ni restaura cabeza, cintura y
elevador. El task esperado por el loader suministrado,
`s2_bio_vla/s2_vla_pick_large_teleop_ready`, no está instalado ni registrado.
Los candidatos presentes tienen distinta semántica y el task tampoco aparece
en el upgrade v0.2.0 suministrado. La revisión v2 corrigió hombro/codo, pero
asumió erróneamente que también debía intercambiar `wrist_pitch/wrist_roll`.
E6.0A rechazó después ese intercambio al compararlo con task 0/frame 0 del
dataset: el orden directo da error máximo `0,002112805 rad` y el intercambio
`0,614627484 rad`. El URDF sólo contiene `waist_yaw_joint`, el ejecutor
genérico usa `[pitch,yaw]` y el S2 conserva el índice 19, de modo que el
segundo cero resuelve `waist_yaw=0`. Los lifter quedan heredados; el ejecutor
los descarta y 500 episodios muestran múltiples configuraciones, no un ready
único. Faltan límites runtime, swept volume y recuperación completa. Resultado
`PARTIAL_RESOLUTION_BLOCKED_NOT_READY_FOR_E4_1_OR_PHYSICAL_USE`; sólo queda
autorizado E4.2 offline, no E4.1 ni movimiento. Antes/después:
`exited/exited/publishers:0`, sin leer estado ni ordenar movimiento.

E4.2 se ejecutó sin red al robot en `20260901T081210_E4.2`. El analizador
versionado cruzó los 500 episodios, perfiles no-S2 55/70/85/100/115 y FK del
URDF S2. Rechazó una altura única: tasks 0/1 tienen coincidencias 55/70/85 y
tasks 2/3 100/115 a `0,05 rad`, pero 84/95/49/58 episodios no coinciden con
ningún perfil nombrado. Los pares task 0/2 episodios 450/206 y task 1/3
443/171 comparten configuración de elevador a sólo
`0,000124356/0,000206182 rad`, de modo que lifter/FK no determina nivel ni
`platform_in_base`. Tasks 2/3 episodios 90/91 correlacionan con el perfil 100
y la plataforma SDK de 1 m, pero el XML es no-S2 y falta calibración métrica.
Estado `PARTIAL_HEIGHT_FAMILIES_RESOLVED_SINGLE_HEIGHT_MAPPING_REJECTED`; diez
frames representativos y todos los hashes validan. Inferencia, publicadores,
estado y movimiento del robot fueron cero. Sólo se permite aclaración de
semántica o calibración métrica offline; E4.0 y lo físico siguen bloqueados.

E4.1 métrico se ejecutó después, por autorización del propietario, en
`20260901T084855_E4.1`. El VLA permaneció `exited/exited/publishers:0`; no hubo
movimiento. CameraInfo vivo confirmó `960×576`, frame rectificado y
`fx=fy=383,1236026`; 20 posiciones del tag 113 validaron escala/TF. La rama
angular planar (`5,484°`) se declaró ambigua y se excluyó de la solución. Dos
rayos del borde posterior de B0, píxeles `(307,293)…(713,293)`, reconstruyeron
`0,603128627 m`, residual `+0,128627 mm`. Con origen en el centro del borde
frontal de la mesa, +X ancho/+Y fondo/+Z arriba, la candidata es
`platform_in_base=(0,261844987,-0,027738106,0,870000000,0,0,-1,545870035)`.
`D_BUMPER_PLATFORM=-0,092859226 m` revela solape de proyecciones; la
incertidumbre es ±16,84/13,30/10,00 mm y ±0,868°. Estado
`METRIC_FIXTURE_CANDIDATE_RESOLVED_PHYSICAL_GATES_OPEN`: E4.0, swept volume,
colisiones y recovery aún impiden colocar la mesa allí o mover el robot.

La continuación E4.1C se repitió completamente local en
`20260903T093408_E4.1C` después de corregir el orden de muñecas demostrado por
E6.0A. Sobre 121 muestras de
`preposition→forward_1→forward_2→back_1→back_2`, el URDF vendor y sus 46
geometrías de colisión produjeron 60 candidatos AABB contra el tablero E4.1;
32 cruces fueron confirmados a nivel de triángulos en doce links de
muñeca/sensor/efector. B0 tuvo cero candidatos y no se colocó. Resultado
`SOLID_TABLETOP_CANDIDATE_REJECTED_BY_VENDOR_URDF_SWEEP`: la mesa sólida no
debe acercarse a esa pose. El run anterior `20260901T090235_E4.1C` queda
`DESCARTADO` porque usó el mapping de muñecas incorrecto.

E4.1D se repitió después en `20260903T093440_E4.1D`. El SDK identifica los
meshes como pinza Dahuan
PGC-140-50 y exige `HW_TYPE=cruzr_s2_v1_gripper`; no son el mecanismo
instalado `cruzr_s2_v1`, compuesto por abrazaderas laterales pasivas. Sin CAD
o cotas de las abrazaderas, la equivalencia de envolventes queda
`NOT_DEMONSTRATED`. Sin embargo, la partición de los 32 cruces deja 10 en
`pgc/finger` y **22 en muñecas/sensores de fuerza**. Por ello el rechazo del
tablero sólido se mantiene aun excluyendo todo el modelo PGC. Sólo queda
autorizado diseñar offline otra pose o una plataforma rígida con huecos; la
entrada a preposición y el recovery completo continúan sin resolver. E4.1C y
E4.1D no conectaron con el robot ni iniciaron inferencia, publicadores o
movimiento, y B0 no se colocó. El intento `20260903T093412_E4.1D` quedó
incompleto y `DESCARTADO`: el wrapper aún exigía los conteos obsoletos; ahora
valida dinámicamente la partición y su suma.

E4.1E continuó ese camino offline en `20260903T093443_E4.1E`. Sobre 401
estados y tres planos verticales (`-10/0/+10 mm`) calculó un margen XY total de
55 mm para muñecas/sensores. Manteniendo B0 y su apoyo fijos, la búsqueda
alineada de mesa sólida en ±5° produjo 128.386 colocaciones con apoyo válido y
cero libres de colisión. La única referencia sólida global refinada exige
`+76,5°` y desplazar el origen `0,856 m`, fuera de la escena calibrada. Se
derivaron dos muescas frontales candidatas: izquierda
`x=-0,720…-0,470, y=0…0,200 m`; derecha
`x=0,400…0,650, y=0…0,170 m`. No solapan el apoyo B0+50 mm, pero no incluyen
la envolvente real de las abrazaderas, patas/espesor, entrada ni recovery. No
se autorizó acercar/modificar la mesa, colocar B0, inferencia, publicador o
movimiento. E4.1F sustituyó la medición manual por una auditoría exclusiva de
fuentes oficiales.

E4.1F se ejecutó localmente en `20260903T085912_E4.1F`. Verificó por hash el
manual SDK, manual de producto, USD/URDF, XML ready y metadatos VLA
suministrados. Las fuentes fijan B0 `0,60×0,40×0,22 m`, plataforma `1,00 m`,
carga máxima global bimanual `15 kg` y PGC-140-50
`0,1385×0,075×0,075 m`/carrera `0,05 m`. Esta última corresponde a
`cruzr_s2_v1_gripper` y queda excluida. El manual enumera la familia
`clamp hands`, pero ningún artefacto publica envolvente, TCP, masa, CoG o CAD
de las placas pasivas `cruzr_s2_v1`; USD/URDF sólo contienen PGC. No se
inventaron cotas ni se usaron mediciones/fotografías. El fixture físico sigue
bloqueado, pero el punto de reanudación pasa a E5.0 offline.

E5.0 se ejecutó localmente en `20260903T090355_E5.0`. La matriz completa de
ocho perfiles `P14_A…P20_AHLW` por fixtures sintéticos `low/middle` aprobó
16/16 celdas: 544 casos, 32 válidos aceptados, 512 inválidos rechazados y
16/16 probes de máscara. Los ejes habilitados copiaron el chunk y los
bloqueados conservaron el hold sintético del fixture. Se corrigió el fault
`axis_profile_mismatch` para que `P14_A` use realmente otro perfil. El sink y
la campaña no usan ROS, red, publicadores ni estado del robot; no hubo
movimiento. E5.0 completa VLA-5 sólo en alcance offline y libera únicamente
E5.1 shadow. No valida poses reales, aceleración ni un ejecutor físico.

E5.1 se completó como shadow-replay local en `20260903T091319_E5.1`. Dado que
los perfiles son máscaras posteriores y no inputs del checkpoint, las 20
inferencias C0 congeladas de E3.0 —4 tasks × seeds 0–4— se reutilizaron bajo
los ocho perfiles, generando 160 bundles comparables. Resultado: 148
`ACCEPT_STRUCTURAL`, 12 `REJECT_SAFE` y 160/160 contratos de máscara. Todos
los rechazos requieren `L`: task 1/seed 2 excede velocidad de
`lifter_pitch_3_joint`; task 2/seed 0 y task 3/seed 0 exceden rango de
`lifter_pitch_1_joint`. Los perfiles sin elevador aceptan 80/80. Los hashes de
E3.0 y del checkpoint antes/después se verificaron. No hubo red, ROS, estado
vivo, publicador o movimiento. Sólo se libera E5.2 offline; faltan fixture
vivo, GPU/VRAM, frecuencia, `flag_pred` y toda validación física.

E5.2 ejecutó la selección preliminar local en `20260903T091901_E5.2`. Exigió
5/5 aceptaciones y eligió el perfil de menor dimensión dentro de
`max(0,0001 rad, 1 %)` del mejor MAE por task. El resultado fue `P14_A` para
tasks 0–3. H no produjo mejora material (`-5,0×10⁻⁹…+1,20×10⁻⁶ rad` frente a
P14), W empeoró `+6,88×10⁻⁶…+1,16×10⁻⁵ rad` y L empeoró
`+7,83×10⁻⁴…+3,48×10⁻³ rad`, además de 12/80 rechazos en todos los perfiles
con elevador. La banda es un criterio de selección offline, no límite
mecánico. No hubo red, ROS, estado vivo, publicador o movimiento. E6.0 sigue
bloqueado.

El precheck reproducible `E6.0-CHECK` se ejecutó de nuevo localmente en
`20260903T123041_E6.0-CHECK`. Corrige el alcance del gate de fixture: E4.4 y
la geometría clamp/mesa **no aplican** al canary `NO_BOX_READY`, porque exige
retirar plataforma y B0; sí siguen siendo obligatorios para E7+. El precheck
cerró correctamente sin red, ROS, estado del robot, publicador ni movimiento,
y dejó tres bloqueos explícitos: recovery sin validar, transporte físico/STOP
ausente y límite de aceleración no certificado. La semántica del canary de un
punto ya quedó cerrada por contrato de proyecto E6.0L: consume únicamente el
índice 0 de un chunk, una vez, sin replay y sin usar el `end_flag` ambiguo del
proveedor. El gate geométrico del canary sin caja se acepta sólo bajo el proxy
documental conservador E6.0J ordenado por el propietario; no constituye CAD ni
certificación del clamp real. El
registro runtime y el preflight articular fresco ya están demostrados. El ready P14 ya no exige tres valores numéricos
de lifter: E6.0A demuestra que sus 14 ejes comandados coinciden con el frame 0
grabado y que H/L/W deben capturarse frescos y mantenerse bloqueados. El
frontend `run_cruzr_vla_canary.sh` sólo implementa `--check`; todos los modos
activos fallan antes de acceder al robot.

E6.0A autoritativo es `20260903T093145_E6.0A`. Derivó un recovery de brazos
exactamente inverso `B→A→preposición`, con segmentos dentro de la envolvente
de velocidad analítica, y confirmó que el `back` vendor no es esa inversa. No
lo instaló ni validó contra colisiones o hardware. El run anterior
`20260903T092935_E6.0A` queda `DESCARTADO`: heredó el intercambio de muñecas
equivocado de E4.0 y produjo un falso fuera de soporte. Se conserva como
evidencia, pero no debe usarse para decisiones.

E6.0B se ejecutó localmente en `20260903T094547_E6.0B`. Reconstruyó por FK
401 estados del recorrido exacto de brazos
`preposición→A→B→A→preposición` y aplicó SAT de OBB a 46 geometrías de
colisión vendor. No encontró violaciones de límites URDF ni solapes OBB entre
links alejados (distancia cinemática >3), incluso antes de excluir PGC/dedos.
Esto sólo cierra el broad phase upstream: 58 pares cercanos/estructurales no
pueden clasificarse sin SRDF/matriz de colisiones permitidas, y el URDF no
incluye la geometría de las abrazaderas pasivas instaladas. Tampoco certifica
holgura, flexión, fuerza o aceleración. Por tanto el gate de autocolisión y el
canary físico permanecen bloqueados. Cero red, ROS, estado vivo, publicador o
movimiento.

E6.0C continuó el narrow phase local en `20260903T095600_E6.0C`. Clasificó
los 58 pares cercanos de E6.0B en 40 uniones directas estructurales, 12 pares
estáticos fuera de P14, 2 pares PGC no instalados y 4 pares móviles upstream.
Estos cuatro —codo/muñeca y hombro/torso de cada lado— se comprobaron en los
401 estados mediante BVH de los STL: las AABB de triángulos descartaron todos
los candidatos y hubo cero intersecciones exactas; cuatro casos sintéticos
validaron además la rama SAT coplanar/3D. Es evidencia favorable para el modelo vendor, pero no
resuelve las abrazaderas reales, holgura mínima/tolerancias, revisión de la
política runtime ni validación física. El gate sigue cerrado; cero red, ROS,
estado vivo, publicador o movimiento.

E6.0D cuantificó la distancia exacta muestreada en
`20260903T101730_E6.0D`. Recorrió 401 estados (201 únicos y retorno simétrico)
con BVH best-first y distancia exacta triángulo-triángulo. Los mínimos fueron
`34,877144 mm` y `34,884472 mm` para codo/muñeca, y `16,378588 mm` y
`16,377700 mm` para hombro/torso; el mínimo global fue `16,377700 mm` en la
muestra 100. El kernel superó 4 casos dirigidos y 300 comparaciones aleatorias
contra una implementación escalar. Es sólo holgura de malla vendor en puntos
muestreados: no prueba continuidad, clamp pasivo, calibración, flexión ni
tolerancia física. También derivó un contrato offline fail-closed de un punto:
el delta efectivo es `min(delta_perfil, velocidad_perfil × 0,08 s)`, pero
aceleración, fuerza/corriente y margen físico permanecen `null`; no contiene
topic/publicador y `physical_execution_enabled=false`.

E6.0E implementó y probó ese guard en
`20260903T102652_E6.0E`: 35 casos de mensajes y 7 manipulaciones del contrato,
42/42 expectativas correctas, 2 previews válidos, cero autorizaciones físicas
y cero publicadores. Rechaza ejecución solicitada, segundo punto, identidad u
orden incorrectos, estados no-ready, datos no finitos/obsoletos/futuros,
rangos/deltas excedidos y cambios de H/L/W. El run `20260903T102636_E6.0E`
queda `DESCARTADO`: sólo falló el empaquetado autocontenido de evidencia por
copiar el módulo un nivel incorrecto; no llegó a ejecutar la campaña ni
accedió al robot.

E6.0F cerró el inventario exclusivamente local en
`20260903T102931_E6.0F`. Congeló el XML ready, la entrada exacta de
`task_list`, los destinos previstos y un rollback sin aplicarlos. Detectó que
el loader vendor es interactivo y puede usar `rm -rf`, `sed -i` y reemplazo de
`task_list`, por lo que queda prohibido ejecutarlo desatendido. Los seis
componentes offline están agotados con las fuentes actuales; lo pendiente
cruza necesariamente a robot vivo o entrada física/certificada. El primer
escenario será `NO_BOX_READY_EMPTY_CELL`: sin caja, mesa/plataforma ni
AprilTag, radio libre mínimo 1,5 m, clamps vacíos, ruedas bloqueadas, cargador
fuera, dos personas y un solo cliente. E6.0F no autoriza ese movimiento.

E6.0G ejecutó el primer preflight vivo de sólo lectura en
`20260903T104309_E6.0G`. Confirmó `HW_TYPE=cruzr_s2_v1`, E-stop principal
accionado (`1`) y servo E-stop liberado (`0`), cargador fuera, baterías
79,8/82,1 %, ambos contenedores VLA detenidos y cero publicadores. El task/XML
ready estaban ausentes. Con el paro activo no había servidor de acción ni
`/mc/whole_joint_states`; `/mc/actuator_state` se anunciaba pero no entregó
muestra, por lo que la inmovilidad no quedó instrumentada. No hubo instalación,
recarga, reinicio ni movimiento.

Tras liberar físicamente el E-stop principal sin movimiento inesperado, E6.0G
se repitió inicialmente en `20260903T105539_E6.0G`: ambos paros `0`, cargador
`0`, ready presente sólo en disco y VLA detenido/cero publicadores, pero
Control Center permaneció en `WaitStartMotion` sin servidor de acción ni
muestra articular. Una pulsación exterior se registró sólo como `Power click`.
Se aplicó entonces el ciclo completo prescrito por la sección 5.3.3: shutdown
lógico aceptado, apagado físico confirmado y arranque supervisado con E-stop.
Control Center pasó por `WaitEStopRelease`; al liberarlo completó self-check,
`StartMotion` y `JoystickMode`, sin movimiento inesperado.

El run E6.0G vigente `20260903T113216_E6.0G` usa ahora `rosa action info` —el
CLI `ros2 action info` había dado un falso cero bajo ROSA/DDS— y demostró un
servidor de manipulación, proceso Motion posterior al `task_list`, ready
cargado en runtime, preflight canónico aprobado, articulaciones inmóviles,
paros `0/0`, cargador fuera y VLA `exited/exited` con cero publicadores. No
envió movimiento y no autoriza el canary.

E6.0H instaló únicamente en disco el XML vendor y una entrada exacta en
`task_list.yaml` en `20260903T104552_E6.0H`, con el E-stop principal activo.
Verificó el hash XML `f4025124…d8323`, creó el backup fresco
`/home/walker/cruzr-vla/backups/20260903T104552_E6.0H`, cambió el hash del
task list de `c03ea6a…21a44` a `e4ac5e43…4def7` y volvió a comprobar VLA
detenido/cero publicadores. No recargó ni reinició el task manager; el registro
runtime y todo movimiento continúan bloqueados. El diagnóstico shadow se
corrigió para tratar un topic de mando inexistente como cero publicadores, sin
ocultar otros errores de transporte. El wrapper E6.0H quedó idempotente:
`--check` reconoce el hash postinstalación y no vuelve a escribir. El proceso
`robot_app` es anterior al cambio del task list; ni sus strings ni sus logs
demostraron recarga dinámica, y los logs repiten `ListControllers: service not
available` bajo el paro. Se exige una recarga supervisada separada.

E6.0I cerró el segmento geométrico omitido después del reinicio, sin ordenar
movimiento. El primer run `20260903T114811_E6.0I` detectó conservadoramente un
nuevo solape OBB `R_shoulder_yaw_link↔torso_link` y terminó fail-safe; queda
reemplazado por `20260903T115129_E6.0I`, que sometió también ese par a BVH,
SAT de triángulos y distancia exacta. Usó un snapshot fresco de 20 ejes en
home, 101 estados `home↔preposición` y la evidencia anterior para cubrir 601
estados compuestos. No hubo violaciones URDF, pares cercanos nuevos ni
intersecciones exactas; el mínimo vendor muestreado fue `0,011169662 m` en
hombro derecho/torso desde home. El resultado no incorpora las abrazaderas
pasivas, tolerancias, continuidad ni dinámica, y no autoriza movimiento.

E6.0J `20260903T120626_E6.0J` aplicó la decisión del propietario de continuar
sin medición manual usando especificaciones y artefactos oficiales. Sustituyó
cada clamp por la unión completa `pgc_base+finger1+finger2` del URDF vendor,
dilatada 25 mm en cada cara a partir de la carrera documentada de 50 mm. La
envolvente resultante por extremo es aproximadamente
`0,145×0,142×0,330 m`. Tras declarar únicamente la cadena de montaje propia
`sixforce/wrist_roll/wrist_pitch` como contacto permitido, auditó 1.201
estados `home→staging→A→B→A→staging→home`, con paso máximo
`0,0092978 rad`, cero pares OBB externos y cero intersecciones exactas. Es una
**suposición de ingeniería aceptada para el canary sin caja**, no demuestra la
geometría, masa, CoG, fuerza o flexión de las abrazaderas instaladas y no
autoriza movimiento por sí sola. Los runs `120340` y `120453` son intentos
fail-safe de implementación/formato y contacto proximal antes de fijar esta
política.

E6.0K `20260903T121338_E6.0K` registró las cuatro fotografías con cinta del
clamp instalado como observación manual aproximada: `120×52×105 mm` en ejes
montaje-transversal/espesor/distal y un espesor local de 33 mm. Se añadió
10 mm por cada cara, obteniendo `140×72×125 mm`. El analizador demostró por
inclusión que este paralelepípedo cabe en el proxy E6.0J para ambos lados bajo
la hipótesis de hardware igual o reflejado. Por ello el barrido de 1.201
estados del proxy mayor domina la envolvente observada; no hubo acceso al
robot, ROS, publicador ni movimiento. Las fotos no están versionadas y la
lectura conserva incertidumbre de perspectiva; no se convierte en CAD ni en
certificación de carga/fuerza.

E6.0L `20260903T122501_E6.0L` añadió el núcleo local del canary de un punto y
pasó 30 casos de estado/fallo más 6 manipulaciones del contrato. Sólo acepta
el punto fuente 0 de un único chunk ya validado por E6.0E, crea como máximo un
intent en memoria, queda enclavado en `COMPLETED` y no repite. Cancel, STOP y
fault purgan el preview antes de cualquier intent posterior. El módulo no
contiene ROS, red, action, topic ni publicador; por diseño tampoco contiene el
transporte físico o STOP físico. Resuelve la semántica temporal propia de
E6.0, no el gate del adaptador físico.

E6.0M `20260903T122502_E6.0M` empaquetó y auditó localmente la secuencia
determinista `home→staging→A→B→A→staging→home`. El tramo nombrado de retorno
usa los goals `B→A→staging` con duraciones invertidas `1,0/1,5 s`, y el tramo
final lleva brazos, cabeza y cintura a cero numérico. El frontend
`cruzr_vla_ready_pose.sh` permite sólo `--check`/`--dry-plan`; instalación,
ready, recovery y STOP fallan antes de acceder al robot. El bundle no está
instalado ni validado físicamente y no autoriza movimiento.

Al preparar la validación física de E6.0, la primera confirmación textual de
E-stop no coincidió con dos lecturas `ESTOPS=0,0`; ese intento se detuvo sin
instalar ni mover. El operador volvió a enclavar el E-stop principal y declaró
también el paro del chasis. El run fresco E6.0G
`20260903T123632_E6.0G` confirmó `ESTOP_KEY=1`, cargador fuera, VLA
`exited/exited`, `publishers:0` y ausencia esperada de estado articular/action
server con el paro activo. `SERVO_ESTOP_KEY=0` no permite afirmar por software
que el paro del chasis esté activo.

E6.0N `20260903T123940_E6.0N` instaló bajo ese E-stop los archivos previstos
para la recuperación exacta y una entrada única en `task_list.yaml`. Respaldó el
estado anterior en
`/home/walker/cruzr-vla/backups/20260903T123940_E6.0N`; el hash del task list
cambió de `e4ac5e43…4def7` a `0d24122c…64957`, XML
`45359d49…cd3c` y MetaMove `bd5f588a…e3b0`. E6.0Q demostró después que ese
check validaba una ruta incorrecta para el MetaMove: se había instalado bajo
`manipulation_task_manager/config/meta_move`, mientras el binario lo busca en
`manipulation_meta_tasks/config/meta_move`. El check posterior de E6.0N había
confirmado `installed-on-disk-not-reloaded` y las nueve evidencias pasaron
`evidence.sha256`. No se recargó/reinició Motion, no se inició VLA y no se
publicó movimiento. En ese punto la tarea todavía no existía en el runtime;
su carga se resolvió en E6.0O y la validación física supervisada sigue
pendiente.

E6.0O `20260903T124843_E6.0O` recargó exclusivamente el contenedor dedicado
`walker-motion.manipulation_robot_app-1` bajo la autorización física del
operador. El proceso pasó de `10:35:33Z` a `10:48:31Z`, posterior al mtime del
task list; persistieron el hash `0d24122c…64957`, una sola entrada y los hashes
exactos de XML/MetaMove. El E-stop principal se verificó antes y después,
`SERVO_ESTOP_KEY` siguió en `0`, el cargador permaneció fuera, VLA detenido y
`publishers:0`. No se invocó tarea ni se publicó movimiento. El arranque sólo
espera `ListControllers`, coherente con los controladores no disponibles bajo
E-stop; no registró fatal, crash o error YAML. Se corrigió después un defecto
de quoting que hacía que el recolector incluyera líneas anteriores en el log;
la lectura corregida confirmó el arranque limpio sin repetir la recarga.

Después, el operador liberó el E-stop principal y confirmó estabilidad. La
lectura aislada mostró `ESTOP_KEY=0`, `SERVO_ESTOP_KEY=0`, cargador `0` y
baterías 64,6/67,1 %, pero no `/mc/whole_joint_states` ni action server
(`count=0`). La inspección del log de Control Center descartó la inferencia
inicial de que el paro del chasis explicaba el bloqueo: no hay un evento
`onServoEstopState=1`; el E-stop principal había provocado
`JoystickMode/Ready→WaitStartMotion`, y su liberación sólo produjo
`onEstopState=0`, sin `ButtonStartMotion`. Por tanto, telemetría y log son
consistentes con ambos paros liberados y rearme pendiente. El preflight terminó
antes de cualquier goal. El auditor se corrigió para imprimir el bloqueo en
vez de salir silenciosamente. Las fotos posteriores confirman la revisión de
hardware ya documentada: blanco=`KEY1`, aro verde=Power/Start exterior,
metálico=alimentación del chasis y ningún START Motion independiente
identificable. Una pulsación verde ya produjo sólo `Power click`; no debe
repetirse. Desde `WaitStartMotion`, el único recovery comprobado es el ciclo
completo supervisado de la sección 5.3.3.

El ciclo completo posterior se completó y E6.0G
`20260903T132151_E6.0G` volvió a demostrar ambos paros `0/0`, actuadores
habilitados, un servidor de manipulación, acciones listas, cargador fuera,
task ready/recovery cargados, VLA `exited/exited` y cero publicadores. Desde
home medido se invocó por primera vez únicamente
`s2_bio_vla/s2_vla_pick_large_teleop_ready`. La acción fue aceptada, pero
terminó `MoveToGoalFailed/status=6`. El log demuestra la causa: el primer
`MetaMove` de cintura terminó `FAILURE` antes de emitir `MoveTo`; el XML vendor
entrega `joint_angles="-0.0; 0.0"`, mientras esta unidad expone una cintura
S2 de un eje. El `Parallel threshold=4` abortó después cabeza y ambos brazos,
dejando un avance parcial quieto de cuerpo `0,195870 rad` y brazos
`0,080246 rad`. No hubo fuerza excesiva, colisión ni fault. Con confirmación
física fresca se ejecutó una sola vuelta vendor `cruzr/home`, que devolvió
`SUCCEED/status=4`; la medida posterior confirmó `MEASURED_HOME=1` con cuerpo
`0,002589 rad`, brazos `0,000671 rad` y velocidad cero.

E6.0P `20260903T133300_E6.0P` creó una copia versionada del ready que cambia
exclusivamente la cintura a `joint_angles="0.0"`, validó por parseo/diff que
no cambia ningún otro atributo de acción y sustituyó atómicamente sólo el XML
vivo. Hash vendor `f4025124…d8323` → overlay S2
`c767f739…a9b2`; backup
`/home/walker/cruzr-vla/backups/20260903T133300_E6.0P`. No hubo reload,
inferencia, publicador ni movimiento durante el cambio, y home se mantuvo
medido. El auditor vivo distingue ahora explícitamente
`vendor-incompatible-waist-2d` de `s2-waist-1d-overlay`.

E6.0Q `20260903T135236_E6.0Q` cerró la validación física determinista sin
caja. El READY corregido terminó `SUCCEED/status=4` y quedó medido contra las
consignas nativas con error máximo `0,001842048 rad`, velocidad cero y sin
faults. El primer recovery no movió: el loader no encontró el MetaMove en su
ruta runtime y abortó fatalmente en `GetRequestFromYamlNode`, lo que reinició
una vez el contenedor (`OOMKilled=false`) y dejó las articulaciones exactamente
en READY. Se corrigieron dos defectos del bundle local: el YAML se instala
ahora en `manipulation_meta_tasks/config/meta_move` y la acción final de
cintura contiene un único valor. El XML nuevo es
`9e47b6ee37f83f75036c203b809e9a93284d459316764615496a872ca3b4fbcc`;
el backup remoto es
`/home/walker/cruzr-vla/backups/20260903T134947_E6.0Q`. Sin reload ni
movimiento durante el arreglo, el segundo recovery obtuvo el goal
`c183c3e0-240a-4bfe-8904-535f0b2b50eb`, `SUCCEED/status=4`. La muestra final
dio `MEASURED_HOME=1`, cuerpo `0,002589 rad`, brazos `0,000959 rad` y velocidad
cero. VLA quedó `exited/exited` con `publishers:0`. Esto cierra el gate de
ready/recovery, pero no autoriza el checkpoint: siguen pendientes el adaptador
de transporte/STOP físico y un límite de aceleración aprobado.

El E6.0-CHECK regenerado `20260903T140006_E6.0-CHECK` consume E6.0Q y reduce
el inventario vigente de bloqueos de tres a dos:
`physical_executor_implemented_and_reviewed` y
`certified_acceleration_limit`. Continúa con `E6.0_PHYSICAL_AUTHORIZED=0`.

El trabajo de cierre E6.0R/S/T avanzó esos dos gates sin mover el robot.
E6.0R `20260903T142823_E6.0R` implementó y probó offline el adaptador P14 de
un punto para `/mc/sdk/robot_command`: 43 casos funcionales y 8 tamper pasaron,
incluyendo STOP idempotente, purga, no replay y fallo de backend cerrado. El
backend ROS existe sólo como componente inyectable, sin `main`, autoarranque ni
launcher activo. E6.0T autoritativo `20260903T143529_E6.0T` verificó en vivo y
sólo lectura que el transporte correcto es `mc_task_msgs/msg/RobotCommand` en
`/mc/sdk/robot_command`, con dos suscriptores, y que
`/mc/sdk/robot_state` tiene dos publicadores; los topics alternativos directos
de brazos no existen. Ambos contenedores VLA estaban `exited` y había cero
publicadores de comando. Los runs T `142955`, `143123` y `143255` se descartan
por auditorías incompletas/corregidas y no accedieron a movimiento.

E6.0S `20260903T144344_E6.0S` validó localmente una envolvente de ingeniería
reemplazable para el canary sin caja: delta máximo `0,1 rad`, velocidad
`0,15 rad/s`, aceleración `0,5 rad/s²`, muestreo `0,01 s` y transición
minimum-jerk `0,5–2,0 s`. Pasaron 28 casos dirigidos y 2.000 aleatorios. No es
un límite certificado por el fabricante ni está todavía aceptado por el
propietario.

E6.0U `20260904T073609_E6.0U` implementó el monitor fail-closed sobre estado
medido: exige los 14 ejes de brazos y los seis ejes H/L/W bloqueados, estado y
velocidad frescos, READY inicial, `|v_arm|<=0,15 rad/s`,
`|a_arm|<=0,5 rad/s²`, deriva H/L/W `<=0,01 rad` y velocidad H/L/W
`<=0,01 rad/s`. Pasaron 152 casos y 8 tamper. E6.0V
`20260904T073852_E6.0V` seleccionó en vivo y sólo lectura
`/mc/whole_joint_states`: entregó 22 nombres/posiciones/velocidades con QoS
reliable; `/mc/sdk/robot_state` tenía dos publicadores pero no produjo payload
en 3 s. También confirmó que los dos consumidores de
`/mc/sdk/robot_command` usan BEST_EFFORT y que había cero publicadores.

E6.0W `20260904T074537_E6.0W` implementó el coordinador y proceso ROS acotado
de un punto. Pasaron 24 casos de runtime y 3 casos de activación. Sólo acepta
el punto 0 de un chunk 10x20 de task 0/P14, mantiene H/L/W con el estado fresco,
crea el publicador SDK de forma perezosa tras READY+chunk válidos y destruye el
publicador al completar, fallar o recibir STOP. La plantilla versionada exige
una escena vacía estática y conserva `owner_accepted=false`,
`active_launcher_enabled=false` y `physical_execution_authorized=false`.

E6.0X `20260904T075519_E6.0X` registra la aceptación explícita del propietario
de esa envolvente únicamente para `NO_BOX_READY`, task 0, P14 y un solo punto.
El registro referencia por SHA-256 los límites aceptados y deja expresamente
`acceptance_is_movement_authorization=false` y
`physical_execution_authorized=false`.

El consolidado histórico `20260904T075648_E6.0-CHECK` consume E6.0R–X. El gate
de ejecutor queda `PASS_CODE_OFFLINE_ACTIVATION_GATED`, la aceptación queda
`PASS` y hay cero bloqueos estáticos. El preflight anterior se clasifica
`RUN_SPECIFIC_REQUIRED` y no se reutiliza hoy. No se creó ningún publicador ni
se movió el robot. Su siguiente paso de celda vacía fue ejecutado y después
retirado por E6.0Z; no debe reutilizarse para generar otro grant. Sigue
`E6.0_PHYSICAL_AUTHORIZED=0`.

El preflight fresco de fase A `20260904T075947_E6.0G`, realizado sólo en
lectura con los paros declarados accionados, confirmó Motion/ROS en ejecución,
`HW_TYPE=cruzr_s2_v1`, cargador fuera, baterías `45,8/48,5 %`, READY S2
registrado con hash `c767f739…a9b2`, VLA `exited/exited` y cero publicadores.
Software leyó `ESTOP_KEY=1` pero `SERVO_ESTOP_KEY=0`: el principal sí quedó
corroborado; el paro físico de chasis no tiene corroboración positiva por esa
señal. Como es normal bajo E-stop, no había whole-state ni action server y no
se evaluó estacionariedad. No hubo movimiento ni autorización. Reanudación:
liberar físicamente ambos paros bajo supervisión y repetir inmediatamente el
preflight con `--expect-released`, sin pulsar Power/KEY1/Start.

Tras la confirmación física de liberación, dos lecturas mostraron
`ESTOP_KEY=0`, `SERVO_ESTOP_KEY=0` y cargador `0`, pero siguieron ausentes
`/mc/whole_joint_states` y el servidor `/mc/manipulation/action`. El preflight
canónico falló cerrado y no envió movimiento. Una primera invocación local de
`cruzr_v020_boot_guard.sh --check` desde el PC produjo
`containers_not_ready`; se descarta porque ese binario debe ejecutarse dentro
de Vision. La invocación correcta de la copia instalada en `192.168.11.3`
confirmó v0.2.0, 3/3 probes x86, 2/2 rondas de las seis cámaras y seguridad
`0 0 0`, pero `CONTROL_STATE=unknown`; fue sólo lectura. Esto confirma el
estado post-E-stop no rearmado. No pulsar Power/KEY1/Start aisladamente ni
invocar StartMotion por ROS: hace falta el ciclo completo supervisado de
apagado y arranque descrito para v0.2.0.

Ese ciclo completo se realizó el 04-09 con el E-stop principal accionado
durante el arranque. Tras liberarlo, el guard remoto de Vision mostró
`JoystickMode`, grafo/cámaras listos y seguridad `0 0 0`. El preflight
`20260904T084316_E6.0G` confirmó action server, estado 20D, actuadores
habilitados, acciones libres, cargador fuera, VLA `exited/exited` y cero
publicadores. Un gate articular posterior midió HOME con velocidad cero. La
auditoría general `cruzr_recover_to_home.sh --check` puede seguir fallando si
el log recién rotado no contiene una etiqueta histórica; para E6.0 se usa el
estado articular fresco y no esa inferencia de log.

E6.0Y añade el primer launcher activo pero cerrado por defecto. `--ready`,
`--one-point` y `--recover` son etapas separadas, cada una revalida estado y
exige una frase exacta. El grant del punto dura como máximo 180 s, queda ligado
por SHA-256 al preflight/READY/aceptación/límites y se comprueba antes de
importar ROS. El publicador se crea sólo después de READY y un chunk válido;
el ejecutor vendor no se arranca y los contenedores se detienen al terminar o
fallar. La prueba offline `20260904T085243_E6.0Y-OFFLINE` pasó; no hubo acceso
al robot ni movimiento. Un recorrido vivo sin confirmación llegó hasta HOME y
falló cerrado antes del goal.

La transición E6.0Y HOME→READY autorizada se ejecutó una sola vez en
`20260904T085921_E6.0Y-READY`: Motion devolvió `SUCCEED/status=4`. El gate
inicial produjo un falso negativo porque comparó signos de coordenadas crudas
de motor con coordenadas articulares del checkpoint. La captura independiente
nombrada `20260904T090051_E6.0V` demostró los 14 brazos a un máximo de
`0,001842 rad` del READY y velocidad cero; la comprobación cruda mantuvo salud
de actuadores y delta posición–consigna máximo `0,001842 rad`. Se corrigió
`cruzr_s2_vla_ready_state_gate.py` para consumir
`/mc/whole_joint_states` por nombre, conservando la muestra cruda como gate de
fallos/consigna. La regresión offline `20260904T090403_E6.0Y-OFFLINE` pasó.
No hubo reintento, inferencia ni publicador; el estado posterior confirmó VLA
`exited/exited` y `publishers:0`. Antes de `--one-point` falta la inspección
visual del operador de READY estable y libre de contacto.

El primer intento autorizado de `--one-point`,
`20260904T090909_E6.0Y`, no llegó al trigger. La inferencia quedó lista, los
dos preflights midieron READY y se copió un grant íntegro, pero el proceso de
Motion lo rechazó antes de importar ROS con `grant_not_current`: el PC estaba
22 s adelantado respecto a Motion, por lo que `issued_at` aún quedaba en el
futuro desde el reloj validador. El cleanup confirmó contenedores
`exited/exited` y `publishers:0`; no hubo publicador ni movimiento. El builder
y launcher toman ahora un epoch fresco de Motion, registran el desfase y
fallan si `abs(skew)>60 s`. La regresión offline
`20260904T091614_E6.0Y-OFFLINE` incluye el rechazo del desfase. Una captura
posterior volvió a dar `MEASURED_READY=1`, error máximo `0,001842 rad` y
velocidad cero. No se reintenta con la autorización ya consumida: hace falta
otra confirmación exacta de un punto.

El segundo intento autorizado `20260904T091928_E6.0Y` resolvió el reloj
usando Motion (`skew=23 s`) y llegó al checkpoint. La inferencia task 0
terminó correctamente y generó tres chunks, pero el primer punto recibido fue
rechazado por `transport:arm:target_delta:2`: el objetivo del eje 2 excedía el
límite aceptado de `0,1 rad`. `frames_published=0`, por lo que no se envió
movimiento. En esta versión del runtime el backend llegó a construir
brevemente el publicador antes de planificar, aunque lo destruyó en el rechazo;
el estado final fue `publishers:0`. Esto se endureció inmediatamente: la
trayectoria completa se valida ahora antes de construir el backend/publicador,
el error incluye delta y límite numéricos y los estados repetitivos ya no
inundan el log. E6.0R check y las regresiones E6.0W
`20260904T092245_E6.0W` y E6.0Y `20260904T092246_E6.0Y-OFFLINE` pasan. Una
muestra posterior volvió a confirmar READY a `0,001842 rad`, velocidad cero;
VLA quedó `exited/exited`, `publishers:0`. No procede relajar `0,1 rad`,
repetir el punto ni recuperar automáticamente: primero debe analizarse en
shadow la discontinuidad del checkpoint.

Con confirmación física independiente, el recovery E6.0 se ejecutó una sola
vez en `20260904T092716_E6.0Y-RECOVERY`. Revalidó READY, paros liberados,
cargador fuera, actuadores sanos y acciones libres; la tarea
`s2_bio_vla/s2_vla_e6_0_exact_recovery` terminó `SUCCEED/status=4`. La medida
final dio `MEASURED_HOME=1`, cuerpo máximo `0,002780 rad`, brazos
`0,000959 rad`, velocidad cero y delta posición–consigna `0,002780 rad`. VLA
permaneció `exited/exited` y `publishers:0`. La inspección visual posterior se
registró a continuación; no debe iniciarse otro canary desde HOME sin un nuevo
ciclo HOME→READY y nueva autorización.

La inspección post-recovery quedó confirmada por el operador: HOME visual
estable, brazos y cabeza sin contacto, clamps vacíos y sin movimiento
inesperado. E6.0 queda cerrado físicamente en HOME. El siguiente trabajo es
exclusivamente shadow/offline para conservar el punto normalizado y medir la
discontinuidad de `L_shoulder_pitch_joint`; no hay autorización vigente para
READY, checkpoint ni recovery adicionales.

E6.0Z cerró el diagnóstico offline en
`20260904T094803_E6.0Z`. La metadata del checkpoint marca los 20 grupos de
acción como `absolute=true`; la salida se desnormaliza y se copia como
posición articular, por lo que no es lícito reinterpretarla como delta. Los
500 frame 0 del dataset muestran que, para task 0 (150 episodios), el primer
target demostrado difiere del estado observado como máximo `0,003134013 rad`.
Los 14 brazos usados por E6.0Y sí estaban dentro de la familia task 0
(`0,000287628 rad` respecto del frame más próximo sólo en brazos), pero la
entrada completa 20D estaba a `0,834773183 rad` de su frame task 0 más cercano:
`lifter_pitch_1_joint=0` frente a `-0,834773183 rad`. Además se solicitó
“Pick up the large box from the lowest level of shelf” en `NO_BOX_READY`; seis
frames representativos de las familias de elevador muestran un contenedor
grande apoyado, no una celda vacía. Son dos incumplimientos confirmados de
entrada (escena y estado 20D); no puede aislarse cuánto aportó cada uno al
outlier neuronal porque el runtime antiguo no conservó los valores exactos del
chunk rechazado y sólo demostró `abs(delta)>0,1` en el eje 2.

El hueco de evidencia queda corregido para futuras ejecuciones: shadow y el
runtime guardan estado, primer punto, deltas con signo y máximo por eje antes
de crear un publicador. `check_vla_task_entry_state.py` compara tarea, escena y
los 20 ejes contra un mismo frame 0 del dataset; el contrato E6.0Z exige una
distancia Chebyshev de proyecto `<=0,01 rad` y cinco chunks shadow frescos,
todos con primer delta `<=0,1 rad`. Un PASS sólo califica shadow y nunca
autoriza movimiento. La evaluación histórica falla por
`task_scene_mismatch`, `state_outside_same_task_observed_bounds` y
`state_not_close_to_any_same_task_frame_zero`.

La ruta anterior queda retirada, no meramente advertida:
`run_vla_canary_physical_e6_0y.sh --ready` y `--one-point` abortan localmente
antes de acceder a la red, y el launcher ya no contiene trigger de inferencia,
grant ni proceso publicador. Sólo permanecen `--stop` y el recovery
READY→HOME para una postura histórica interrumpida. La regresión
`20260904T100258_E6.0Y-OFFLINE` confirma 10 checks estáticos, ruta activa
eliminada, READY retirado, recovery conservado y cero acceso al robot. No se
aumentará `0,1`, no se recortará/proyectará el target y no se reintentará
`NO_BOX/task 0`. Un
sucesor físico nuevo requerirá, en este orden, escena `SUPPORTED_LOW`, entrada
20D asociada a un frame task 0, transición y recovery deterministas validados,
cinco chunks shadow frescos aceptados y una autorización física nueva. Durante
este cierre el cargador quedó conectado; no se ordenó movimiento, los análisis
de parquet se ejecutaron en un contenedor efímero `--network none` y no se
arrancaron los contenedores VLA persistentes.

Como punto de partida exclusivamente offline se seleccionó
`episode_000040`, el frame task 0 más próximo a la entrada histórica E6.0Y.
Su H/L/W es `[-0,431336224, 0, -0,834773183, -0,000958738, 0,291264594,
0,024639565] rad` y su primer target se separa sólo `0,000326395 rad` de ese
estado. El frame RGB muestra un contenedor plástico gris grande, abierto y
vacío, apoyado sobre una superficie blanca; no demuestra equivalencia con una
caja de cartón arbitraria. Esta selección permite diseñar y auditar
HOME→ENTRY→HOME, pero no congela el fixture ni autoriza movimiento.

E6.1A cerró esa auditoría offline en el run autoritativo
`20260904T103516_E6.1A`. Congeló `episode_000040/frame 0/task 0` en un contrato
versionado y generó HOME→ENTRY→HOME con minimum jerk (`23,59 s` por sentido,
`10 ms`). El mayor recorrido es `1,887083978 rad` en
`L_shoulder_yaw_joint`; con los valores de diseño `0,15 rad/s` y
`0,5 rad/s²` obtuvo cero violaciones URDF en 401 muestras, cero intersecciones
exactas de mallas monitorizadas y cero intersecciones del proxy documental de
las abrazaderas. Esos límites no están certificados ni aceptados por el
propietario para movimiento E6.1, y el muestreo no certifica una trayectoria
continua.

Usando el RGB congelado, la cámara calibrada y la anchura vendor de caja
`0,60 m`, la reconstrucción infiere una superficie a `0,774597 m` del suelo,
con rango `0,768191–0,780828 m` para ±4 píxeles. Un soporte de referencia
`0,75 × 0,50 × 0,04 m` y la caja exterior `0,60 × 0,40 × 0,22 m` no produjeron
candidatos OBB en las 16 variantes. Esas dimensiones describen el volumen de
referencia reconstruido: no son máximos de compatibilidad para el VLA. La pose
sigue siendo una inferencia, no una medida del proveedor ni un fixture físico
congelado. `MESA_T1` de `1,80 × 0,80 × 1,00 m` no coincide con este frame por
altura (`+0,225403 m`) y su modelo hipotético produjo 159 candidatos OBB; eso
la deja sin calificar para HOME→ENTRY con este candidato, pero no demuestra
contacto físico ni la descarta para otros escenarios o shadow estacionario.

El wrapper `audit_vla_task_entry_path_e6_1a.sh` comprobó estáticamente ausencia
de ROS, red, contenedores, publicadores y comandos de movimiento; la ejecución
confirmó esos cinco ceros y el manifiesto SHA-256. El run previo
`20260904T103323_E6.1A` queda superado porque todavía incluía en el volumen
barrido la geometría PGC incorrecta además del proxy clamp; el run autoritativo
la excluye y conserva sólo el proxy documental, sin cambiar el PASS.

E6.1B quedó revalidado offline en `20260904T121621_E6.1B`: fijó los 20 ejes
de `episode_000040/frame 0`, previews ENTRY/recovery deliberadamente no
ejecutables, un gate que no acepta ejes ausentes/defaults ni estado obsoleto y
un orquestador para exactamente cinco sesiones task 0/P14 independientes. Cada
sesión futura vuelve a medir ENTRY y debe conservar el RGB y estado 20D exactos
entregados al checkpoint, aceptar al menos un chunk sin clipping y terminar
con ambos contenedores detenidos y cero publicadores. No mueve a ENTRY/recovery,
no instala artefactos y no puede autorizar movimiento.

La mesa disponible, medida por el propietario en
`0,838 × 0,84 m`, `0,77 m` de altura y `0,038 m` de espesor, fue declarada
inmovilizada. B0 se declaró rígida, vacía, abierta, centrada lateralmente, con
el lado largo paralelo y frente a `0,05 m` del borde. Las dos fotos originales
quedaron guardadas localmente y validadas por SHA-256; el fixture
`TABLE_77_B0_20260904` está congelado con incertidumbre manual conservadora de
`±0,005 m`. Muestran una caja azul. El gris observado en
el frame se conserva como referencia visual, no como propiedad exigida por la
instrucción “large box”; azul queda como variación que deberá evaluar shadow.
El robot sólo podría situarse en ENTRY mediante un procedimiento separado.
Con espesores hipotéticos de
`0,005` y `0,04 m`, el OBB simplificado produjo respectivamente 20 y 44
candidatos, todos contra proxies rectangulares conservadores de clamps y no
contra CAD/contacto físico medido. Es una alerta reproducible, no evidencia
determinista de colisión real ni razón para capar el VLA a una única mesa.
ENTRY/recovery con la mesa presente sigue sin calificar hasta una comprobación
geométrica más precisa y una prueba incremental autorizada por separado. El
AprilTag no forma parte de este checkpoint ni aparece en el frame congelado.
El barrido repetido con el espesor real `0,038 m` produjo 44 alertas OBB, cero
violaciones articulares y cero contactos exactos robot/proxy; no cambia esa
clasificación. Las alertas centrales aparecen sólo en las muestras `342–374`
de `400` (`20,17–22,06 s` de una transición de `23,59 s`); las muestras
`375–400`, incluida ENTRY, quedan libres en ese modelo. Esto sustenta como
hipótesis de prueba llegar a ENTRY con la celda vacía, inmovilizar el robot y
colocar después el fixture, retirándolo antes del recovery. No autoriza esa
secuencia ni demuestra clearance real. La pose reconstruida para el borde
frontal de la mesa es `base=(0,7192, 0,0025, 0,6446) m`, equivalente a unos
`0,365 m` desde el extremo frontal de la malla base; debe materializarse con
marcas y validarse antes de shadow.

E6.1C quedó reemitido offline en `20260904T130901_E6.1C` después del primer
HOME→READY físico. El READY vendor vivo está a `0,001055 rad` del frame
congelado en los 14 ejes de brazo;
por tanto el nuevo preview no vuelve a comandarlos. Sólo cabeza, elevador y
cintura recorren READY↔ENTRY durante 12 s. El barrido de 401 muestras produjo
cero límites, contactos exactos robot/proxy, solapamientos clamp–clamp y
candidatos OBB contra la mesa/caja reconstruidas. Máximos minimum-jerk:
`0,130433310 rad/s` y `0,033469203 rad/s²`. El gate de extremos exige una
muestra fresca de los 20 ejes, distancia `<=0,01 rad` y velocidad
`<=0,01 rad/s`. Los XML siguen sin instalación, no se demostró equivalencia
con el interpolador runtime de `MetaMove` y falta aceptación específica E6.1C.

El plan ponderado queda en `48,5 %`, las cuatro tareas físicas del checkpoint
siguen en `0/4` y E6.1 queda al `60 %`: E6.1A, E6.1B, el fixture y E6.1C
offline están cerrados; faltan aceptación/deploy, ENTRY fresca y cinco shadow.
E6.1B no accedió ni movió el robot. E6.1C sí completó un único HOME→READY
vendor en `20260904T130344_E6.1C-READY`; no ejecutó ENTRY, checkpoint ni
publicador. La medida inmediata corrigió la referencia y demostró que el orden
runtime del grupo head es `yaw;pitch`, no `pitch;yaw`.

La evidencia VLA ya no depende de variables exportadas por un bloque anterior.
`new_vla_evidence_run.sh` crea cada run de forma exclusiva y rechaza `/` y
rutas existentes. E1.1/E1.2, los smoke E2.0/E2.1 y las repeticiones E2.3 tienen
wrappers autocontenidos; E2.3 usa sesiones independientes y STOP entre runs.
E2.2, E3.0, E3.1, E3.2, E3.3, E4.0, E4.1, E4.1C, E4.1D, E4.1E,
E4.1F, E4.2, E5.0, E5.1, E5.2, E6.0A, E6.0B, E6.0C, E6.0D, E6.0E, E6.0F,
E6.0G, E6.0H, E6.0I, E6.0J, E6.0K, E6.0L, E6.0M, E6.0N, E6.0O, E6.0P,
E6.0Q, E6.0R, E6.0S, E6.0T, E6.0U, E6.0V, E6.0W, E6.0X, E6.0Y, E6.0Z,
E6.0-CHECK, E6.1A, E6.1B y E6.1C
disponen ahora de
evaluador/sink y wrappers autocontenidos. Los ejemplos aún no implementados de
VLA-T00…T08 inicializan su directorio
en el mismo bloque. Las herramientas de evidencia son cambios del
PC/repositorio; E2.2/E3.0/E3.1 sólo arrancaron contenedores offline transitorios
en Vision; E3.2/E3.3 fueron procesos Python locales y E3.3 sólo consultó el
estado remoto antes/después. No alteraron Motion ni los contenedores VLA
persistentes.

El paquete local sí contiene
`codes-S2/motion/s2_vla_scripts/s2_bio_vla/s2_vla_pick_large_teleop_ready.xml`,
hash `f4025124…d8323`. Preposiciona cintura, cabeza y brazos y llama a la
primitiva 14D ya localizada, pero el task S2 completo no está instalado, la
pose 20D sigue incompleta y los límites/recovery/swept volume no están
demostrados. El SDK 7.3 confirma B0 `60×40×22 cm` sobre plataforma de **1 m de
altura** y sólo pide mover el robot a una posición adecuada; no proporciona
distancia horizontal.

Se extrajeron de sólo lectura 12 frames —inicio/medio/final de los episodios 0,
1, 90 y 91— con VLC. La referencia visual es un tote rígido gris abierto de
paredes altas y borde gris, con tiras/marcas negras estrechas en algunos frames
y un pequeño elemento con lazo visible dentro, no una caja de cartón cerrada.
Por ello `B0_SAFE` vacía puede servir para canary, pero es OOD si no
reproduce esa apariencia/contenido.

El siguiente bloque de trabajo VLA está planificado al principio de
[`plan_de_trabajo.md`](plan_de_trabajo.md): auditoría offline, contrato temporal,
posturas `VLA-ready`, ejecutor sink, matriz shadow de 4 tasks × 8 perfiles
funcionales (`P14`…`P20`), canary progresivo y comparación del checkpoint
intacto frente a continuación o nuevo DataConfig. Se añadieron tarjetas
`VLA-T00…T10` con fixture, estado inicial, comandos/mensajes PC, PASS/FAIL,
evidencia y recovery: `B0_SAFE` `0,603 × 0,397 × 0,217 m`, plataforma inicial
a 1 m de altura confirmada por SDK y pose medible en `PLATFORM_FRAME`. E4.2
demostró que low/middle son familias, no alturas escalares. E4.1 resolvió una
pose métrica candidata para el episodio 90 y detectó solape firmado con el
bumper. La repetición corregida E4.1C rechazó esa candidata para un tablero
sólido al confirmar 32 cruces de mesh. E4.1D confirmó que 22 cruces pertenecen
a muñecas/sensores y
subsisten sin `pgc/finger`. E4.1E encontró cero poses sólidas libres dentro de
±5° y derivó dos huecos upstream que aún carecen de la envolvente real de las
abrazaderas; el plan no autoriza movimiento, modificar la mesa ni colocar B0.
Las tarjetas
físicas permanecen bloqueadas hasta demostrar `VLA_READY`, ejecutor canary y
primitiva de trayectoria. El manual operativo al inicio del plan ordena los
experimentos `E1.0…E8.2`: montaje medido, baseline, primera inferencia, OOD,
ready, perfiles 14–20, canary, cuatro tareas físicas y evolución C1/C2. Para
experimentos 1–3 mantiene plataforma/B0 fuera de la envolvente; el 1 m es
altura de plataforma, no separación.

Fuente: [`guides/CRUZR_S2_VLA_SAFE_ENABLEMENT.md`](guides/CRUZR_S2_VLA_SAFE_ENABLEMENT.md).

### 4.5 Teleoperación del robot

Se verificaron `TELE_DEVICE=pico`, `transmit=local`, `signal_server`,
`rtm_receiver` y la tarea
`teleoperation/cruzr_clamp_pico_teleoperation`. No se renombraron topics,
colas o servicios del robot.

`walker28` es exclusivamente el `channel_name` del backend PC. El nombre
`walker28_web` no se encontró en el frontend ni en el sistema inspeccionado.

### 4.6 Tareas auxiliares y scripts

El repositorio contiene XML auxiliares y scripts para brazos, voz, manos,
cajas, navegación, recovery, VLA y teleoperación. Algunos scripts pueden
instalar tareas versionadas en el árbol de manipulación del robot antes de
ejecutarlas; su presencia debe comprobarse mediante los modos `--check` y los
hashes incorporados. No asumir que una tarea local está instalada tras una
actualización.

Los scripts se migraron a los nombres de imágenes/tareas observados en v0.2.0.
La migración se validó sin instalar tareas nuevas ni mover el robot.

## 5. Cambios persistentes en el PC de teleoperación

### 5.1 Paquetes instalados

- XRoboToolkit PC Service `1.0.0.0` para Ubuntu 24.04.
- `ubt-controller` `4.7.0` entregado por UBTECH para el robot v0.2.0 e
  instalado el 26-08; binario oficial sin parches `e88b83b7…`.
- `ubt-remote-control` `4.1.0`.
- ADB y regla udev para PICO.
- Servicio systemd `/etc/systemd/system/ubt-controller.service`.

Instaladores grandes y SOP se mantienen fuera de Git; sus hashes están en la
fuente de teleoperación y en [`../utats/README.md`](../utats/README.md).

### 5.2 Configuración y workarounds PC

- Ruta preferida PC → Motion/Vision por Ethernet `eno1`/`.11.250`, 1 Gb/s;
  Wi-Fi Cruzr conserva PICO, `.42.0/24` y el fallback `.11.0/24` vía `.42.2`.
  Ambas son never-default; Internet continúa exclusivamente por DSA.
- Backend con `transmit=local`, señalización
  `ws://192.168.11.3:4000`, `channel_name=walker28`, dispositivo PICO y
  `enable_foot_switch=1` restaurado por 4.7.0, pendiente de aclaración.
- Los tres parches diagnósticos de 5.3.0 —`GRIPPER→CLAMP`, gatillo izquierdo
  como Y por flanco y timeout heartbeat 300 s— ya no están instalados. 4.7.0
  usa el binario exacto del DEB del proveedor y su watchdog por defecto.
- `arm=clamp` se conserva como variable systemd del PC; `LC_NUMERIC=C` evita
  diferencias locales de separador decimal sin modificar el ejecutable.
- 4.7.0 instala además el cliente oficial `/usr/local/bin/pico_control`
  (`46323392…`), cuya ayuda admite `--arm_type clamp`. No se ejecutó porque
  puede iniciar el flujo de control; el preflight sólo verifica hash y ayuda.
- La instalación 5.3.0 parcheada, configuración, units y backups quedó
  archivada en
  `/home/lacuna/Descargas/ubt-controller-5.3.0-patched-20260826.tar.gz`
  (SHA-256 `c085fc4b…`). El DEB original 5.3.0 se conserva fuera de Git.
- El preflight de teleoperación muestra ahora siete etapas con timestamp y
  timeouts de 5 s para ADB/systemd/journal/WebSocket. La variable
  `CRUZR_TELEOP_DEBUG=1` activa traza Bash con línea y comando; los fallos del
  gate informan el punto exacto antes de solicitar STOP.
- Se mejoró orden de arranque: servicio XR y PICO antes del backend; UI al
  final. Una desconexión/suspensión del visor puede exigir reinicio del
  servicio.
- El lanzador descubre ahora el mismo visor por `ro.serialno` tanto si ADB usa
  el serial USB como si usa un destino `IP:puerto`; `PICO_ADB_TARGET` permite
  fijar el transporte para diagnóstico. No se cambió ninguna ruta de mando.

El binario original permanece respaldado; los hashes original y activo están
en la fuente especializada.

### 5.3 Último estado PC

El 26-08 quedó activo `ubt-controller 4.7.0`, listener 8082 y XR Service 63901;
la UI está inactiva. PICO mantiene el flujo USB `192.168.51.220` →
`192.168.51.42:63901` y `vr_status=1`. El cliente oficial se ejecutó una vez
con timeout y `--arm_type clamp`: Y produjo `Left.b_button=true` y el callback
`tele_operation enable=1`; el grip derecho llegó al backend. Sin embargo, el
backend registró `Arm type is: gripper`. El propietario acepta temporalmente
esa diferencia sólo para cinemática de brazos y prohíbe inferir equivalencia
para mandar el efector. `pico_control` confirmó STOP/`operation_type=1`. El
rearme observado un segundo después no fue espontáneo: un segundo cliente
diagnóstico `wscat --wait 1` permaneció conectado después de enviar STOP y el
backend autoarrancó al detectar cliente + PICO online. El STOP canónico corto
lo dejó después en `operation_type=1`, cliente terminado y articulaciones
inmóviles. No mantener otro WebSocket abierto después de STOP.
La concesión Wi-Fi observada del PICO cambió a `.42.212`, como corresponde a
DHCP. Tras sustituir el cable, Ethernet negocia 1000 Mb/s full y Motion/Vision
responden directamente desde `.11.250` en 0,2–0,9 ms; Wi-Fi Cruzr queda activa
para PICO/fallback y `DSA CORPORATE` mantiene la ruta por defecto de Internet.

El estado 5.3.0 con `vr_status=1`, `enable_control=0` y el backend parcheado
`5083e9f0…` queda como evidencia histórica del 25-08, no como estado activo.

El 27-08 se verificó en Motion que la tarea
`teleoperation/cruzr_clamp_pico_teleoperation` carga `Hand type: clamp`, pero
el YAML vendor activa cuerpo completo con `waist_mode=1` y `leg_mode=2`.
Durante la sesión problemática ambos grips quedaron simultáneamente altos y
el solver registró fallos de alcance repetidos; el torso/elevador compensó en
CoreMode 7. Se instaló de forma reversible un overlay que cambia únicamente
esos dos modos a cero, SHA-256 `4e8d79a4…`, conservando clamp, brazos,
anticolisión y umbrales de fuerza. El backup vendor `5f08b30c…` y el overlay
persisten en Motion bajo `$HOME/.local/share/cruzr-pico-arms-only/`. El overlay
se recargó después y el último baseline conocido quedó
`ARMS_ONLY_LOADED=hand:clamp,waist:0,leg:0`.

El 28-08 se añadió `scripts/teleoperation/probar_pico_full.sh` como lanzador
separado, dejando `probar_pico.sh` sin cambios. Puede preparar el rollback
exacto al YAML vendor y sólo permite START full-body si demuestra hash
`5f08b30c…` más tarea viva `clamp,waist=1,leg=2`; exige Wi-Fi sin Ethernet
sujeto al robot, conserva los gates oficiales y añade STOP ante clicks de
protección, fallos IK, sobreesfuerzo, EtherCAT o pérdida del monitor Motion.
La preparación, recarga de TeleopMode y movimiento son pasos separados. El
cambio quedó validado localmente y con checks de sólo lectura: el full rechazó
correctamente el hash activo `4e8d79a4…` y el original confirmó
`ARMS_ONLY_LOADED=hand:clamp,waist:0,leg:0`. **No se restauró ni cargó el perfil
full, no hubo START ni movimiento**. El primer `--prepare-full` real del
28-08 a las 09:48 superó el preflight Motion, pero abortó antes del rollback:
el comprobador pasivo intentaba asignar temporalmente la constante shell
`readonly BACKEND_LOG`, por lo que Python no recibió la ruta. Se corrigió usando
el nombre de entorno independiente `BACKEND_LOG_PATH`. La reproducción de sólo
lectura devolvió `PASSIVE_OPERATION_TYPE=1` y el check posterior volvió a
demostrar `clamp,waist=0,leg=0`; por tanto no hubo cambio parcial.

Más tarde, tras una sesión PICO, `cruzr_recover_to_home.sh --run --yes`
clasificó correctamente `teleoperated_pose` y lanzó la tarea vendor verificada
`cruzr/open_arm_before_home`. Su primera fase no es una separación cartesiana
condicionada por postura: manda en paralelo ambos brazos a objetivos articulares
intermedios, y también cintura/elevador a cero. Desde la postura cruzada real,
Motion registró primero anticolisión torso–codo/muñeca izquierda durante el
final de teleoperación y, ya en recovery, `Force-X=-370,944 N` en el FT
izquierdo. El brazo derecho y cintura terminaron; el izquierdo falló con
errores articulares grandes y el elevador abortó. La acción acabó
`MoveToGoalFailed`, state `7104050`, `status=6`. Después 4004, 4003 y 4002
registraron `0x1003`/`Operation disabled unexpected:0x123f`; `hw` y
`manipulation_robot_app` reiniciaron. Con el paro accionado, rosa_control espera
`/mc/rosa_control/start`, `/mc/actuator_state` tiene cero publicadores y la
acción de manipulación cero servidores. **DESCARTADO** usar
`open_arm_before_home` como retorno universal desde cualquier postura PICO.
No se liberó el paro, rearmó, reinició, cambió modo ni envió otro movimiento
durante el diagnóstico; el siguiente paso requiere confirmación física fresca
y, si procede, apagado completo controlado, no otra trayectoria.

El operador confirmó después paro accionado, brazo izquierdo apoyado sin
presión apreciable, robot/brazos estables, abrazaderas vacías, cargador fuera,
zona de descenso despejada y persona junto al paro. La solicitud oficial
`/emb/pm_shutdown` con `confirm-to-shutdown` respondió `success=True`; Motion y
Vision pasaron de accesibles a no responder. Tras confirmar físicamente
pantalla y luces apagadas, el operador pulsó `KEY1` y luego apagó el chasis.
Estado final: indicador verde apagado, hosts sin respuesta, robot y brazos
estables. No se liberó el paro, rearmó ningún servo ni se envió otra
trayectoria. Los faults y consignas deben redescubrirse desde cero en el
próximo arranque controlado.

El drop-in de lifecycle de 15 s permanece instalado. Una parada anterior de
5.3.0 agotó el margen y recibió SIGKILL; durante la migración el servicio se
mantuvo enmascarado para impedir que el `postinst` del proveedor arrancara el
backend antes de completar la configuración.

Fuente completa:
[`teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md`](teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md).

## 6. Capacidades verificadas

### 6.1 Operación y diagnóstico

- Lectura de batería, cargador, paros, sensores y estado de potencia.
- Control web y cambio de modos de trabajo.
- Mando físico para elevador/chasis después de rearme correcto y desbloqueo de
  ruedas.
- TTS en inglés y ASR capaz de transcribir inglés; español funciona peor.
- Cámaras, LiDAR, RGB-D/estéreo y navegación con evitación de obstáculos.

### 6.2 Manipulación tradicional, sin VLA

- Detector especializado `workbin` de UBTECH/DSA para pose 6D de contenedores.
- Centrado visual, agarre bimanual BYD, elevación y depósito mediante tareas
  deterministas.
- Control de separación y fuerzas durante el agarre.
- Transferencia de la caja azul desde mesa 1 a mesa 2 mediante detector,
  navegación, waypoint y AprilTag; un ciclo `--resume-held` completó depósito,
  retroceso de aproximadamente 0,484 m y `home`.
- AprilTag 113 detectado y calibrado para pose vacía y pose con carga.

GR00T/VLA no intervino en esas pruebas. La adaptación procede de detección 6D,
transformaciones, realimentación de fuerza y secuencias programadas.

### 6.3 Manos

Con manos v4 instaladas se verificaron topics y tareas de fábrica para apertura,
cierre, pinzas de dedos, gestos y secuencias. Las manos ya no están instaladas.

### 6.4 VLA

- Checkpoint suministrado cargable en v0.2.0 mediante overlay.
- Inferencia y validación shadow sin publicar a control físico.
- Cuatro IDs documentados: recoger/depositar caja grande en nivel inferior y
  medio.
- No se ha demostrado una ejecución física segura del checkpoint.

Catálogo detallado:
[`guides/CATALOGO_FUNCIONALIDADES_CRUZR_S2.md`](guides/CATALOGO_FUNCIONALIDADES_CRUZR_S2.md).

## 7. Problemas conocidos y decisiones vigentes

### 7.1 PICO/teleoperación — bloqueo P0

La cadena PICO → PC → robot llegó a `Working`, señalización, DataChannel y
recepción de tele-data. El PC no recibe el heartbeat de aplicación esperado.
Con el timeout original esto deshabilitaba la sesión aproximadamente cada
11,1 s; el timeout diagnóstico de 300 s ya superó en runtime ese límite, pero
no corrige ni valida el heartbeat.

En el gate del 25 de agosto se verificó además el workaround de entrada:
gatillo izquierdo → `b_button=true` → `enable=1` → Motion `CoreMode 7`. El
Y del proveedor funciona como conmutador con repetición, no como *deadman*:
con el gatillo crudo estable en `1.0`, `enable` alternó aproximadamente cada
0,51 segundos. A las 12:27 una sola pulsación de 0,567 s volvió a alternar
`enable 0→1→0`; no fue un fallo de heartbeat. El backend activo publica ahora
sólo el flanco ascendente. Tras detectar que el primer gate reutilizaba
muestras antiguas, los scripts exigen ahora muestras Left/Right nuevas después
de START mientras `enable_control=0`, neutralidad antes de mostrar
`TOQUE AHORA` y liberación posterior del gatillo. Su test aislado pasó; el E2E
físico queda pendiente.
Los STOP automáticos dejaron el PC en `operation_type=1`, `enable_control=0`.
El operador confirmó cero movimiento físico en los intentos informados. El gate
local de 60 segundos se ejecutó el 25 de agosto: START fue a las 09:53:46.142,
el toque habilitó a las 09:53:49.845 y el watchdog cerró a las 09:53:56.718 por
`No heartbeat for 10 seconds`. No hubo movimiento físico y sí se oyó una voz
del robot. Esto confirma el bloqueo P0 de heartbeat.

En la ventana de las 10:38 con el timeout de 300 s, el DataChannel abrió antes
de habilitar y `enable_control=1` se sostuvo durante unos 46,1 s sin disparar
el watchdog anterior. Motion entró en `CoreMode 7`, habilitó la protección de
fuerza de ambos brazos y arrancó ambos chequeos de fuerza. El operador movió
los mandos, pero observó cero movimiento del robot. El log PC contiene 4.530
muestras por mando durante ese minuto y ninguna activación de
`squeeze`/grip (`false`, valor `0.0`). Según el SOP, mover el mando sólo hace
seguir al brazo mientras se mantiene el grip correspondiente; por ello este
resultado es el esperado para el gate sin maniobra y no valida ni refuta aún
el seguimiento físico. Tres pulsaciones nuevas al final produjeron
`enable=0→1→0` a intervalos de 0,5 s; el lanzador detectó la pérdida y envió
STOP. El robot quedó `CoreMode 0`/`NotTele` y el PC en
`operation_type=1`, `enable_control=0`. A las 10:43 el stream XR volvió a
`vr_status=0`, aunque TCP/ADB reverse seguían presentes.

A las 10:50–10:51 se restauró de nuevo el stream reiniciando sólo
XRoboToolkit y conservando ADB reverse. El propietario autorizó después una
prueba física real inmediata. `probar_pico.sh` sin argumentos ejecuta ahora
una micromaniobra del brazo derecho; `--move-left-arm` permite la segunda
prueba y `--gate-only` conserva el diagnóstico sin movimiento. Cada modo
físico exige un preflight fresco de paros, batería, cargador, efector, tarea
PICO y velocidad articular, mantiene 60 s sin grips, admite un solo grip y un
gesto de 2–3 cm durante un máximo de 5 s, y envía STOP al soltar o fallar. El
preflight sólo lectura pasó con baterías 77,2/77,8 %, ambos paros a cero,
cargador desconectado, robot inmóvil y tarea Cruzr/PICO correcta. No se envió
START durante la implementación ni la validación seca.

A las 11:53 el transporte XR se migró a la WLAN local `Cruzr S2-0669` sin
alterar `DSA CORPORATE`: PC `192.168.42.215`, PICO `192.168.42.211`. Tras
seleccionar `Head + Controllers` y `Send data`, XRoboToolkit abrió TCP directo
hacia el listener PC `63901`. Se borró el reverse, el flujo siguió establecido
y el preflight canónico terminó correctamente con el backend en STOP. ADB TCP
se usó sólo para administración inalámbrica; no transporta el stream XR
directo. No hubo movimiento físico.

La reinspección de los artefactos instalados descarta que el heartbeat deba
producirlo la UI PC: el source map de `ubt-remote-control 4.1.0` sólo envía
START/STOP. El bytecode de `Publisher.callback` en `ubt_controller 5.3.0`
declara que procesa mensajes inversos del robot por RTM y sólo ante
`type=heartbeat` actualiza `last_heartbeat_time`. **DESCARTADO** desactivar o
puentear este watchdog en el PC: eliminaría la detección de pérdida robot→PC.
El propietario autorizó después una excepción limitada: ampliar el timeout a
300 s para diagnóstico, conservando el STOP. Esto no resuelve ni valida el
heartbeat y una ventana local de 60 s ya no puede declararse gate de heartbeat.
Si el robot debe permanecer inmutable, UBTECH debe suministrar un backend PC
compatible con la v0.2.0 genérica o el componente oficial que complete ese
heartbeat, conservando la parada por pérdida de enlace.

La coordinación del flanco ya no debe realizarse por chat. El modo local
`cruzr_pico_teleop_pc.sh --gate-local` exige terminal interactivo, emite la
señal `TOQUE AHORA` sólo después de armar, monitoriza el gate y envía STOP al
terminar o ante cualquier fallo. `--run` es únicamente un alias compatible.
El lanzador humano `scripts/teleoperation/probar_pico.sh` presenta esas órdenes
en el terminal y delega el flujo al controlador canónico. Por defecto ejecuta
la prueba física mínima del brazo derecho; `--move-left-arm` selecciona el
izquierdo y `--gate-only` conserva el gate sin maniobra. Tras observar que
`Ctrl+C` durante un `read` enviaba STOP pero permitía continuar, el handler se
corrigió para terminar definitivamente con código 130 (143 para `TERM`)
después del STOP.

El SOP exige `utars-udoke-config-v0.2.0-dac-beta.2.tar.gz`, pero sólo está
demostrada la build genérica v0.2.0. Además, `MC_SCENE` está vacío y no se
encontró `pico_control`, aunque ambos aparecen en el SDK/SOP.

Decisiones:

- no eliminar el watchdog ni fabricar heartbeat; el timeout temporal autorizado
  es 300 s y debe tratarse como workaround diagnóstico;
- no declarar lista la teleoperación por ver sólo `Working`, `TeleopMode` o un
  topic existente;
- no ejecutar a la vez el cliente PC y un supuesto cliente PICO directo;
- exigir un gate monitorizado de 60 s antes de cualquier movimiento mínimo;
- pedir a DSA paquete DAC exacto, hashes, matriz de versiones, componente de
  heartbeat y procedimiento directo.

Fuente viva obligatoria:
[`teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md`](teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md).

### 7.2 Navegación transportando caja

La caja puede aparecer ante las cámaras RGB-D/estéreo como obstáculo propio y
bloquear el costmap dinámico. Se creó un perfil temporal de percepción de
carga que redirige únicamente tres entradas de nube de puntos; mantiene LiDAR,
odom, mapa, bumpers y paros. El último preflight registró
`CARGO_PERCEPTION_PROFILE=disabled`, es decir, restaurado.

Nunca desactivar toda la evitación ni dejar el perfil activo después del
transporte.

### 7.3 Depósito y AprilTag

- Una tolerancia demasiado estricta causaba múltiples correcciones aunque la
  caja ya estuviera razonablemente sobre la mesa.
- El perfil `--fluid` acepta hasta 50 mm en la estación validada, con límites
  duros y menos muestras/iteraciones.
- Una lectura vertical no se corrige con el chasis. La postura de cabeza y
  brazos debe coincidir con la calibración.
- La aproximación autónoma se interrumpe si la orientación o la detección es
  inestable; no debe abrir las abrazaderas al fallar.

### 7.4 Arranque y apagado

- La carrera de arranque v0.2.0 está mitigada mediante boot guard local.
- El manual oficial exige un `Servo Control Button` no identificable en esta
  revisión física.
- La máquina de estados v0.2.0 pide pulsar el paro rojo después de aceptar un
  apagado, aunque el manual no lo incluye como apagado normal.
- Usar `KEY1` aisladamente produjo un corte compatible con apagado abrupto y
  corrupción de logs Docker. No debe usarse como sustituto del apagado lógico.
- El procedimiento definitivo aplicable a este número de serie sigue
  pendiente de DSA.

Fuente:
[`support/UBTECH_SHUTDOWN_PROCEDURE_MISMATCH_V020.md`](support/UBTECH_SHUTDOWN_PROCEDURE_MISMATCH_V020.md).

### 7.5 Baterías/BMS

Históricamente se observó gran diferencia de SOC y truncamiento del segundo
número de serie. Tras la actualización se registraron SOC equilibrados y
números completos, pero la respuesta técnica del proveedor sobre el fallo
histórico sigue pendiente. La UI también llegó a mostrar “fault” sin error de
powerboard. No borrar alarmas ni asumir que son falsas sin comprobar BMS.

### 7.6 Voz

ASR transcribió frases inglesas cuando `run_record`/chatting estaban en el
estado adecuado. Los topics no siempre emitían; se llegó a recuperar texto del
log del motor ASR. El español se reconocía peor. No existe una lista completa
confirmada de órdenes industriales por voz.

### 7.7 Soporte documental y proveedor

Siguen abiertos, entre otros: build DAC exacta, heartbeat, apagado actualizado,
corrección oficial del boot race, cliente MQTT, Netdata, GPU, documentación de
payload, pipeline teleoperación → LeRobot, certificado de conformidad y reporte
de inspección de fábrica.

Seguimiento:
[`support/UBTECH_SUPPORT_TRACKER.md`](support/UBTECH_SUPPORT_TRACKER.md) y
[`support/UBTECH_OPEN_QUESTIONS.md`](support/UBTECH_OPEN_QUESTIONS.md).

## 8. Matriz de reanudación por tarea

### 8.1 Diagnóstico o recuperación de postura

1. Confirmar visualmente efector, carga y obstáculos.
2. Ejecutar `./scripts/cruzr_recover_to_home.sh --check`.
3. Leer `RECOVERY_ROUTE`: `already-home` no envía objetivos;
   `known-workbin` es la única ruta automática candidata.
4. No enviar `home` con una carga o contacto dentro de la trayectoria.
5. Tras PICO no usar `cruzr/home` ni `open_arm_before_home`: el script canónico
   bloquea toda postura no-home de PICO. Volver a home dentro de la propia
   sesión PICO antes de STOP o usar el procedimiento de recuperación por
   fault/apagado; no adivinar una trayectoria desde una postura cruzada.

### 8.2 Caja mesa 1 → mesa 2

1. Leer la guía AprilTag completa.
2. Ejecutar `--check --fast` o preparar `--check --fluid`.
3. Primera puesta en servicio: `--stage-held`; inspeccionar en `MESA2_PRE`.
4. Con caja ya sujeta, usar el modo de reanudación apropiado; no reiniciar el
   ciclo completo.
5. Confirmar visualmente tag, mesa y estabilidad antes del depósito.

Script canónico:
`scripts/cruzr_blue_workbin_table_transfer.sh`.

### 8.3 PICO

1. Leer la fuente PICO completa, incluida la checklist P0.
2. Comprobar que no hay otro cliente ni servicio reactivado.
3. Recuperar ADB/red/`Working`; verificar tracking y backend por separado.
4. Ejecutar `./scripts/teleoperation/probar_pico.sh --check` con el visor en
   Head + Controllers / Send data / Working; debe terminar 7/7 con
   `PICO_TRACKING_OK=vr_status:1`.
5. Ejecutar `./scripts/teleoperation/probar_pico.sh --check-arms-only`; debe
   demostrar el hash esperado y `hand:clamp,waist:0,leg:0`. Si informa
   `waist:1,leg:2`, no mover: salir de TeleopMode y volver a entrar sólo con
   preflight físico fresco para recargar la tarea.
6. Para brazos use únicamente `./scripts/teleoperation/probar_pico.sh
   --teleoperate`: integra `pico_control` oficial, cámara, preflight físico,
   muestras neutras, Y, gate arms-only, ventana de 300 s y STOP. Permite uno o
   ambos brazos; con ambos use recorridos pequeños y suelte ante resistencia,
   retraso o movimiento del torso. `PICO_ALLOW_BIMANUAL=0` restaura el rechazo
   de solapamiento. No autoriza chasis, elevador, joysticks, botones adicionales
   ni gatillos de efector.
7. No usar todavía `--gate-only`, `--move-*-arm` ni `--all-controls`: 4.7.0 no
   publica el campo `enable_control` usado por los gates de 5.3.0. Los scripts
   solicitan STOP y bloquean START en esos modos legados.
8. Repetir siempre el preflight físico fresco y verificar cámara PICO antes de
   cualquier movimiento. La captura de un episodio piloto
   sigue pendiente de exportación y auditoría.

### 8.4 VLA suministrado

1. Mantener contenedores detenidos salvo diagnóstico solicitado.
2. Usar `--status` y shadow, nunca un ejecutor físico implícito.
3. Registrar la postura oficial ready y repetir shadow desde ella.
4. Resolver task-ID, primitiva de trayectoria, límites y deadman antes de
   publicar a control.

### 8.5 Nuevo dataset/checkpoint

1. No iniciar una campaña grande hasta exportar y auditar un episodio piloto.
2. Capturar misión, fases, observaciones sincronizadas, acciones, estado,
   fuerza, cámaras, transformaciones, mapa/waypoints, AprilTags y resultado.
3. Separar navegación global, alineación local, pick, transporte y place.
4. Mantener variantes de caja/pose/iluminación y negativos/recovery en splits
   por escenario, no por frames.

Fuente:
[`vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md`](vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md).

### 8.6 Manos

Las manos no están instaladas. Para retomarlas: SOP físico, `HW_TYPE` correcto,
homing, `check_hands.sh`, ensayo `--check` y luego demostración vacía. No usar
scripts de manos con abrazaderas.

## 9. Qué no debe darse por hecho

- Que la postura o el modo descritos aquí siguen vigentes.
- Que mapa cargado significa localización correcta.
- Que `Working` del PICO significa teleoperación autorizada.
- Que un topic DDS anunciado está publicando muestras frescas.
- Que `status=6` con `RUNNING` es éxito; en acciones ROS 2, el éxito observado
  ha sido `status=4` con `SUCCEED`.
- Que una tarea de manos, caja o VLA sigue instalada después de actualizar.
- Que `KEY1` es el botón de apagado lógico.
- Que una caja ligera valida la carga nominal.
- Que un detector workbin generaliza a botellas u otras clases.
- Que una reproducción `.motion` es una política adaptativa.

## 10. Estructura y fuentes canónicas

| Tema | Fuente canónica |
|---|---|
| Contexto global | este documento |
| Teleoperación PICO/PC/robot | [`teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md`](teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md) |
| Handoff histórico PICO | [`teleoperation/CRUZR_S2_PICO_TELEOP_HANDOFF_2026-08-24.md`](teleoperation/CRUZR_S2_PICO_TELEOP_HANDOFF_2026-08-24.md) |
| Captura y entrenamiento VLA | [`vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md`](vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md) |
| VLA instalado y shadow | [`guides/CRUZR_S2_VLA_SAFE_ENABLEMENT.md`](guides/CRUZR_S2_VLA_SAFE_ENABLEMENT.md) |
| Cajas y AprilTags | [`guides/TRANSFERENCIA_CAJA_ENTRE_MESAS_CON_APRILTAG.md`](guides/TRANSFERENCIA_CAJA_ENTRE_MESAS_CON_APRILTAG.md) |
| Plan pick → transporte → volcado → depósito multialtura | [`plan_de_trabajo.md`](plan_de_trabajo.md) |
| Contacto/fault y recuperación post-teleop | [`guides/CRUZR_S2_RECUPERACION_TRAS_CONTACTO_TELEOP.md`](guides/CRUZR_S2_RECUPERACION_TRAS_CONTACTO_TELEOP.md) |
| Capacidades y ejemplos | [`guides/CATALOGO_FUNCIONALIDADES_CRUZR_S2.md`](guides/CATALOGO_FUNCIONALIDADES_CRUZR_S2.md) |
| Manos | [`../scripts/hands/README.md`](../scripts/hands/README.md) |
| Boot guard | [`guides/CRUZR_V020_BOOT_GUARD.md`](guides/CRUZR_V020_BOOT_GUARD.md) |
| Apagado | [`support/UBTECH_SHUTDOWN_PROCEDURE_MISMATCH_V020.md`](support/UBTECH_SHUTDOWN_PROCEDURE_MISMATCH_V020.md) |
| Soporte | [`support/UBTECH_SUPPORT_TRACKER.md`](support/UBTECH_SUPPORT_TRACKER.md) |
| SDK original | [`../Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/`](<../Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/>) |

## 11. Protocolo de actualización de esta fuente

Después de cada intervención material, añadir o corregir:

1. fecha y evidencia;
2. estado físico/lógico final **sin asumir que persistirá**;
3. cambio persistente en robot, PC o repositorio;
4. verificación realizada y resultado;
5. rollback disponible;
6. bloqueo o riesgo nuevo;
7. siguiente comando de sólo lectura y documento a consultar.

No copie logs completos aquí. Resuma y enlace la fuente detallada. Si la
evidencia contradice este documento, prevalece la evidencia actual y debe
actualizarse este archivo antes de cerrar la sesión.

## 12. Historial global

| Fecha | Hito | Resultado |
|---|---|---|
| 2026-09-04 | Contacto clamp–torso al rearmar desde READY y recuperación a HOME | ENTRY no se ejecutó. En el primer ciclo, tras liberar E-stop: self-check `passed=true`; `StartMotion` falló a las 19:58:04 con `reason:19 Limb motion failed`. La clamp izquierda quedó visiblemente contra el torso; 4003/4004 registraron `0x1003`, luego 4004 `0x2006`, y todos los esclavos pasaron a `SAFEOP ERROR`. Se accionó E-stop y se completó apagado lógico/físico; al quitar potencia el contacto se alivió y los brazos descendieron. Segundo arranque supervisado desde brazos libres: `JoystickMode`, action server `1`, whole-state presente y preflight PASS. `cruzr_recover_to_home.sh --check` midió HOME (`arms≤0,000479`, cuerpo/delta≤`0,002397`, velocidad `0`) sin enviar goals. Causa inmediata verificada: `StartMotion`/rearme desde READY, no checkpoint ni publicador. El propietario confirmó que las abrazaderas estaban invertidas deliberadamente para mejorar la manipulación de cajas; la envolvente modificada no estaba representada en URDF/CAD/mesh ni en un perfil de herramienta. Es el principal factor contribuyente al contacto, aunque el alcance del rayado y orificio/marca aparente requiere inspección. HOME→READY queda bloqueado y no se autoriza la orientación invertida para movimiento automático. |
| 2026-09-04 | E6.1C ENTRY bloqueada antes del goal | el propietario autorizó READY→ENTRY con READY medido, clamps vacíos, fixture fuera de trayectoria, cargador fuera, ruedas bloqueadas, ambos paros liberados y dos personas. El runner abortó fail-closed en el preflight canónico. Diagnóstico posterior de sólo lectura: `CONTROL_STATE=WaitStartMotion`, último evento `Ready --(ButtonStopMotion)-> WaitStartMotion`, servidor `/mc/manipulation/action=0` y `/mc/whole_joint_states=0`. No se envió goal, no se arrancó checkpoint/publicador y no hubo movimiento. Siguiente paso: ciclo completo supervisado de v0.2.0; después READY fresco y nueva autorización. |
| 2026-09-04 | Preflight vivo previo a E6.1C | run `20260904T125740_E6.0G`: Motion/ROS y action server listos, `ESTOP_KEY=0`, `SERVO_ESTOP_KEY=0`, cargador fuera, baterías `94,6/94,5 %`, READY S2 cargado, VLA `exited/exited`, `publishers:0` y preflight canónico aprobado. Fue sólo lectura, sin objetivo ni movimiento. No basta para mover con el fixture delante: el HOME→READY vendor mueve ambos brazos en `1,5 s` y E6.1C exige mesa/B0 ausentes durante ese tramo. |
| 2026-09-04 | E6.1C HOME→READY físico y corrección de head | run `20260904T130344_E6.1C-READY`: preflight fresco, HOME medido 20D, clamps vacíos/fixture fuera/ruedas bloqueadas/dos personas confirmados; goal único READY `SUCCEED/status=4`, sin reintento, checkpoint ni publicador. Estado inmediato inmóvil; los 14 brazos coinciden a ≤`0,000096 rad` con el READY previo. `head_pitch=-0,651079` ante XML vendor `-0.0;-0.65` prueba que MetaMove head serializa `yaw;pitch`; el gate histórico falló seguro antes de ENTRY. Preview/recovery corregidos y reauditoría offline `20260904T130901_E6.1C`: 0 límites/contactos/candidatos. Falta confirmación visual READY; no instalar ni enviar ENTRY. |
| 2026-09-04 | E6.1C aceptación y despliegue preparado | el operador confirmó READY visual estable, sin contactos y clamps vacíos. Run `20260904T131403_E6.1C-ACCEPTANCE`: propietario aceptó `0,15 rad/s` y `0,5 rad/s²` provisionales/no certificados sólo para READY↔ENTRY de cabeza/elevador/cintura; no autoriza una corrida ni publicador. Se implementaron instalador atómico con backup/rollback, recarga exclusiva bajo E-stop y runner con gates frescos 20D y cero reintentos. Sintaxis y auditorías offline PASS; nada instalado/recargado/ejecutado todavía. |
| 2026-09-04 | E6.1C instalado y recargado bajo E-stop | `20260904T132339_E6.1C-INSTALL`: task list `0d24122c…64957`→`224c6fca…fac1b`, dos XML hash-matched, backup `/home/walker/cruzr-vla/backups/20260904T132339_E6.1C-INSTALL`, sin recarga/movimiento. `20260904T132423_E6.1C-RELOAD`: reinició sólo `walker-motion.manipulation_robot_app-1` con `ESTOP_KEY=1`, cargador fuera, VLA `exited/exited`, `publishers:0`; proceso posterior al task list, ninguna tarea invocada y cero movimiento. Mantener E-stop hasta liberación supervisada; ENTRY aún no autorizada. |
| 2026-09-04 | E6.1C transición reducida READY↔ENTRY | run offline `20260904T124321_E6.1C`: el READY observado deja los 14 ejes de brazo a ≤`0,000959 rad` de `episode_000040/frame 0`; los previews de 12 s no comandan brazos y sólo ajustan cabeza/elevador/cintura. Máximos minimum-jerk `0,130433310 rad/s` y `0,033469203 rad/s²`; 401 muestras, 0 límites, 0 contactos exactos robot/proxy, 0 solapamientos clamp–clamp y 0 candidatos OBB contra fixture reconstruido. Gate 20D READY/ENTRY y 5/5 regresiones PASS. Sin robot/red/ROS/contenedor/publicador/movimiento. XML no instalado, ley runtime no demostrada, aceptación específica pendiente. E6.1=60 %, plan=48,5 % |
| 2026-09-04 | E6.1B fixture y campaña shadow fail-closed | run offline `20260904T121621_E6.1B`: fixture `TABLE_77_B0_20260904` congelado con mesa `0,838 × 0,84 × 0,77 m`, espesor `0,038 m`, B0 azul y dos fotos originales SHA-256 válidas; azul es variación registrada, no rechazo. Contrato exacto `episode_000040/frame 0/task 0`, previews ENTRY/recovery sin ejecutor, gate fresco 20D y cinco sesiones task 0/P14. El barrido real da 44 alertas OBB y cero contactos exactos: no descarta shadow, mantiene HOME→ENTRY bloqueado. Sin robot/red/ROS/contenedor/publicador/movimiento; E6.1=50 %, plan=47,6 %, faltan ENTRY viva y 5 shadow |
| 2026-09-04 | E6.1A transición task-matched offline y matriz de avance | run autoritativo `20260904T103516_E6.1A`: `episode_000040/frame 0/task 0`, primer delta `0,000326395 rad`; HOME→ENTRY→HOME minimum-jerk `23,59 s` por sentido. En 401 muestras: 0 límites URDF, 0 intersecciones exactas robot/proxy clamp y 0 candidatos OBB para soporte+caja en 16 variantes. Soporte inferido `0,774597 m`, no medido; referencia `0,75 × 0,50 m`. Mesa T1 no calificada para HOME→ENTRY de este frame (`+0,225403 m`, 159 alertas OBB), sin prueba de contacto real ni descarte general. Sin robot/red/ROS/contenedor/publicador/movimiento; físico no autorizado. E6.1=20 %, plan ponderado=44,6 %, tasks físicas=0/4. Sigue E6.1B |
| 2026-09-04 | E6.0Z cierre del outlier de entrada | run `20260904T094803_E6.0Z`: metadata demuestra acciones absolutas; 500 entradas/4 tasks auditadas offline. Task 0 tiene 150 episodios y delta máximo frame-0 acción−estado `0,003134013 rad`. La entrada histórica E6.0Y estaba a `0,834773183 rad` del frame task 0 más próximo por `lifter_pitch_1_joint`, además de usar `NO_BOX` para una instrucción de pick con caja/repisa. Gate de tarea/escena/20D rechazó por tres causas; 3/3 tests. El valor exacto del target histórico no es recuperable del log anterior, pero la instrumentación futura ya conserva posiciones y deltas completos. `--ready`/`--one-point` E6.0Y retirados antes de red y código activo eliminado; regresión `20260904T100258_E6.0Y-OFFLINE`, sólo STOP/recovery histórico. Cargador conectado, cero ROS/publicador/movimiento durante E6.0Z |
| 2026-09-04 | E6.0Y recovery READY→HOME | run `20260904T092716_E6.0Y-RECOVERY`: preflight/READY frescos; tarea exacta terminó `SUCCEED/status=4`. HOME medido en 20 ejes: cuerpo ≤`0,002780 rad`, brazos ≤`0,000959 rad`, velocidad 0 y delta ≤`0,002780 rad`. VLA `exited/exited`, `publishers:0`. Operador confirmó HOME visual estable, sin contactos, clamps vacíos y sin movimiento inesperado; ciclo físico cerrado |
| 2026-09-04 | E6.0Y checkpoint rechazado sin movimiento | run `20260904T091928_E6.0Y`: grant ligado a Motion válido (`skew=23 s`), inferencia task 0 `SUCCEEDED`, 3 chunks; primer punto rechazado por `target_delta` del eje 2 >`0,1 rad`. Cero frames y cero movimiento; un publicador se construyó transitoriamente y fue destruido, final `exited/exited`, `publishers:0`. Runtime corregido para planificar antes de crear publicador; E6.0W `20260904T092245` y E6.0Y offline `20260904T092246` pasan. READY posterior ≤`0,001842 rad`, velocidad 0. Bloqueado nuevo punto hasta análisis shadow |
| 2026-09-04 | E6.0Y primer intento de punto abortado antes de ROS | run `20260904T090909_E6.0Y`: inferencia lista y READY fresco, pero `grant_not_current` por PC 22 s adelantado a Motion. Rechazo anterior a import ROS, publicador y trigger: cero movimiento; cleanup `exited/exited`, `publishers:0`. Grant corregido para usar epoch Motion y rechazar `abs(skew)>60 s`; regresión `20260904T091614_E6.0Y-OFFLINE` aprobada. READY posterior sigue medido a ≤`0,001842 rad`, velocidad 0. Pendiente nueva autorización |
| 2026-09-04 | E6.0Y HOME→READY físico | run `20260904T085921_E6.0Y-READY`: goal único `SUCCEED/status=4`; falso negativo inicial por mezclar coordenadas crudas de motor con joints ROS. E6.0V `20260904T090051_E6.0V` midió READY por nombre con error máximo `0,001842 rad`, velocidad 0 y delta crudo ≤`0,001842 rad`. Gate corregido y regresión `20260904T090403_E6.0Y-OFFLINE` aprobada. Sin reintento, inferencia ni publicador; VLA `exited/exited`, `publishers:0`. Pendiente confirmación visual antes del punto físico |
| 2026-09-04 | E6.0Y launcher por etapas | `20260904T085243_E6.0Y-OFFLINE`: grant válido y rechazo por E-stop, gate READY nominal/rechazo por delta y 7 checks estáticos pasan; plantilla desactivada, sin robot/ROS/publicador/movimiento. Un preflight vivo posterior sin confirmación verificó HOME, `ESTOPS=0,0`, acciones listas y `publishers:0`, y terminó antes del goal. Próximo paso: autorización física específica de `--ready` |
| 2026-09-04 | Reinicio completo rearma Motion | ciclo supervisado con E-stop activo durante arranque; después de liberarlo, guard Vision en `JoystickMode`. E6.0G `20260904T084316_E6.0G`: actuadores habilitados, estado/action disponibles, cargador fuera, VLA detenido y cero publicadores. HOME fresco: cuerpo ≤0,002780 rad, brazos ≤0,000959 rad, velocidad cero |
| 2026-09-04 | Liberación de paros no rearma Motion | señales `0/0/0`, pero sin whole-state ni action server; preflight fail-closed, cero movimiento. Guard ejecutado correctamente en Vision: v0.2.0, x86 3/3, cámaras 2/2, `CONTROL_STATE=unknown`, `RECOVERY_ELIGIBLE=0`. El `containers_not_ready` previo se descarta por haberse ejecutado localmente en PC. Siguiente paso: ciclo completo supervisado; no Power/KEY1/Start aislados |
| 2026-09-04 | E6.0 preflight fresco fase A | run `20260904T075947_E6.0G`: principal corroborado activo (`1`), servo/chasis no corroborado (`0`), cargador fuera, baterías 45,8/48,5 %, READY S2 correcto, VLA detenido y cero publicadores. Sin estado/action server bajo E-stop, sin movimiento. Pendiente liberar ambos paros y repetir `--expect-released` |
| 2026-09-04 | E6.0U/V/W/X y consolidado | U `20260904T073609_E6.0U`: monitor medido, 160/160 casos. V `20260904T073852_E6.0V`: estado vivo `/mc/whole_joint_states`, 22/22/22, command QoS BEST_EFFORT y cero publicadores. W `20260904T074537_E6.0W`: runtime/proceso ROS de un punto, 27/27 casos, publicador perezoso y activación cerrada. X `20260904T075519_E6.0X`: propietario acepta `0,1 rad / 0,15 rad/s / 0,5 rad/s²` sólo para NO_BOX y no como autorización de movimiento. CHECK `20260904T075648_E6.0-CHECK`: cero gates estáticos; preflight/grant de corrida pendientes, sin movimiento ni autorización física |
| 2026-09-03 | Cierre E6.0R/S/T | R `20260903T142823_E6.0R`: adaptador SDK/STOP offline, 51/51 casos. T autoritativo `20260903T143529_E6.0T`: `/mc/sdk/robot_command` es el transporte vivo correcto, cero publicadores, VLA detenido; runs T previos descartados. S `20260903T144344_E6.0S`: 2.028/2.028 trayectorias dentro de 0,1 rad, 0,15 rad/s y 0,5 rad/s². Falta monitor medido, launcher cerrado y aceptación del propietario; sin autorización física |
| 2026-09-03 | E6.0-CHECK posterior a Q | run `20260903T140006_E6.0-CHECK`: consume la evidencia física de READY/recovery y marca ese gate PASS. Quedan 2 bloqueos: transporte/STOP físico y aceleración; `E6.0_PHYSICAL_AUTHORIZED=0` |
| 2026-09-03 | E6.0Q READY/recovery físico sin caja | run `20260903T135236_E6.0Q`: READY S2 y segundo recovery `s2_vla_e6_0_exact_recovery` terminaron `SUCCEED/status=4`; HOME final medido en 20 ejes, velocidad cero. El primer recovery no movió y reveló YAML en la raíz de paquete errónea; el fatal reinició una vez el task manager. Se corrigieron ruta MetaMove y cintura 1D, XML `9e47b6ee…4fbcc`, backup `20260903T134947_E6.0Q`. VLA `exited/exited`, `publishers:0`. El auditor canary queda con 2 gates: transporte/STOP físico y aceleración |
| 2026-09-03 | E6.0P primer ready físico, recovery y overlay cintura S2 | desde home medido, el ready vendor fue aceptado pero falló porque enviaba dos valores a la cintura S2 de un eje; el paralelo abortó cabeza/brazos y dejó sólo un avance parcial quieto. Sin fuerza/colisión/fault, una vuelta única `cruzr/home` terminó `SUCCEED/status=4` y home quedó medido. Se aplicó después sólo el overlay `joint_angles="0.0"`, hash `c767f739…a9b2`, con backup `20260903T133300_E6.0P`; sin reload, VLA, publicador ni movimiento. Reintento supervisado pendiente |
| 2026-09-03 | E6.0 preflight tras liberar E-stop | topics `0/0`, cargador fuera, pero estado articular/action server ausentes. Log: `JoystickMode/Ready→WaitStartMotion` al accionar el principal y luego `onEstopState=0`, sin `ButtonStartMotion`; no hay evento servo E-stop activo. Bloqueo atribuido a rearme pendiente, no al paro de chasis. Cero goals/movimiento; auditor corregido para reportar el fallo |
| 2026-09-03 | E6.0-CHECK consume N/O | run vigente `20260903T125333_E6.0-CHECK`: verifica recovery instalado, registrado y con proceso posterior a la configuración bajo E-stop. Mantiene 3 gates: validación física del recovery, transporte/STOP físico y aceleración aceptada; no autoriza movimiento |
| 2026-09-03 | E6.0O recarga mínima del task manager | run `20260903T124843_E6.0O`: reinició sólo `walker-motion.manipulation_robot_app-1` bajo E-stop principal, sin llamar tareas. Proceso posterior al task list; configuración/hashes exactos, E-stop antes/después, cargador fuera, VLA detenido y cero publicadores/movimiento. `SERVO_ESTOP_KEY=0`; registro action y trayectoria aún requieren validación supervisada |
| 2026-09-03 | E6.0N recovery exacto instalado sólo en disco | run `20260903T123940_E6.0N`: tras confirmar `ESTOP_KEY=1`, cargador fuera, VLA detenido y cero publicadores, respaldó en `/home/walker/cruzr-vla/backups/20260903T123940_E6.0N`, añadió una sola entrada y los XML/YAML hash-matched; task list `e4ac5e43…4def7`→`0d24122c…64957`. Check posterior `installed-on-disk-not-reloaded`; 9/9 artefactos verifican. Sin recarga, reinicio, VLA, publicador ni movimiento; runtime y validación supervisada pendientes |
| 2026-09-03 | E-stop principal reconciliado para E6.0N | run `20260903T123632_E6.0G`: `ESTOP_KEY=1`, `SERVO_ESTOP_KEY=0`, cargador fuera, VLA `exited/exited`, `publishers:0`; estado articular/action server ausentes por el paro activo. El segundo paro declarado no quedó corroborado por software |
| 2026-09-03 | E6.0K envolvente observada de clamp | run `20260903T121338_E6.0K`: cuatro fotos con cinta dan aproximadamente `120×52×105 mm`; con 10 mm por cara se usa `140×72×125 mm`. El volumen queda contenido en E6.0J para ambos lados bajo simetría, por lo que hereda su barrido mayor de 1.201 estados. Fotos no versionadas, sin CAD/carga/fuerza certificados; cero red/ROS/estado/publicador/movimiento |
| 2026-09-03 | E6.0L núcleo temporal de un punto | run `20260903T122501_E6.0L`: 30 casos de estado/fallo y 6 tamper pasan; consume sólo punto 0 una vez, sin replay ni `end_flag`. Cero ROS/red/publicador/movimiento; transporte físico y STOP físico ausentes por diseño |
| 2026-09-03 | E6.0M bundle ready/recovery local | run `20260903T122502_E6.0M`: valida `home→staging→A→B→A→staging→home` y la inversión exacta del segmento nombrado. Modos activos bloqueados antes del robot; no instalado ni validado físicamente |
| 2026-09-03 | Preparación física E6.0 bloqueada por discrepancia de E-stop | confirmación textual decía E-stop principal accionado; auditor vivo y preflight canónico leyeron `ESTOPS=0,0`, actuadores habilitados, acciones listas, cargador fuera y baterías 67,1/70,1 %. No se instaló, recargó ni movió |
| 2026-09-03 | E6.0-CHECK incorpora contrato temporal | run vigente `20260903T123041_E6.0-CHECK`: consume E6.0L/M; quedan 3 gates —recovery física, transporte/STOP físico y aceleración certificada— y no autoriza movimiento |
| 2026-09-03 | E6.0-CHECK incorpora medida observada | run histórico `20260903T121415_E6.0-CHECK`: consumió E6.0K además de E6.0J y mantuvo 4 gates antes del contrato temporal E6.0L; no autorizó movimiento |
| 2026-09-03 | E6.0J proxy documental conservador de clamps | run vigente `20260903T120626_E6.0J`: por decisión del propietario se usó la unión PGC completa del URDF vendor y se dilató 25 mm por cara según la carrera documentada de 50 mm; proxy por extremo `0,145×0,142×0,330 m`. En 1.201 estados del recorrido completo, paso máximo `0,0092978 rad`, no hubo pares OBB externos ni intersecciones exactas. Sólo se permiten contactos de la cadena propia `sixforce/wrist_roll/wrist_pitch`. Supuesto aceptado para canary sin caja, no CAD/certificación física; cero red/ROS/estado/publicador/movimiento |
| 2026-09-03 | E6.0-CHECK actualizado con supuesto geométrico | run histórico `20260903T120716_E6.0-CHECK`: consumió E6.0J y marcó autocolisión como `PASS_WITH_DOCUMENT_PROXY_ASSUMPTION`. Dejó 4 gates antes de E6.0L/M. Local, sin red/ROS/publicador; E6.0 físico no autorizado |
| 2026-09-03 | E6.0H instalación ready sólo en disco | run `20260903T104552_E6.0H`: con E-stop principal activo se respaldó `task_list.yaml`, se instaló atómicamente el XML vendor `f4025124…d8323` y una sola entrada; hash task list `c03ea6a…21a44`→`e4ac5e43…4def7`. Backup `/home/walker/cruzr-vla/backups/20260903T104552_E6.0H`. Sin recarga/reinicio, VLA detenido, cero publicadores y cero movimiento; registro runtime pendiente |
| 2026-09-03 | E6.0G preflight vivo de sólo lectura | runs iniciales `20260903T104309`/`105539`: E-stop 1/0 y luego `WaitStartMotion`. Tras el ciclo completo supervisado, run vigente `20260903T113216_E6.0G`: `rosa action info` demuestra un servidor, ready cargado porque Motion arrancó después del task list, preflight canónico aprobado, articulaciones inmóviles, paros 0/0, cargador fuera, VLA detenido y cero publicadores. Sin movimiento ni autorización física |
| 2026-09-03 | E6.0F cierre offline y escenario físico | run `20260903T102931_E6.0F`: 6/6 componentes locales inventariados; no queda acción exclusivamente local sin nueva entrada física/certificada. Preview no aplicado del XML/entrada ready y rollback; loader vendor marcado destructivo/interactivo. Primer escenario `NO_BOX_READY_EMPTY_CELL`, sin fixture y no autorizado. Cero red/ROS/estado/publicador/movimiento |
| 2026-09-03 | E6.0E guard de un punto | run autoritativo `20260903T102652_E6.0E`: 35 mensajes + 7 tamper de contrato, 42/42 expectativas, 2 previews válidos, cero autorizaciones y publicadores. Guard local/in-memory; rechaza toda solicitud física. Run `102636` descartado por estructura de copia de evidencia, sin campaña ni acceso externo |
| 2026-09-03 | E6.0D holgura vendor y contrato de guards | run `20260903T101730_E6.0D`: distancia exacta en 401 estados, mínimo global muestreado `0,016377700 m` hombro derecho/torso en muestra 100; 4 tests dirigidos y 300 aleatorios contra referencia escalar. Contrato de un punto sólo como especificación fail-closed, sin topic/publicador, con aceleración/fuerza/margen físico nulos. No certifica continuidad, clamp ni tolerancias. Cero red/ROS/estado/publicador/movimiento |
| 2026-09-03 | E6.0C narrow phase de pares cercanos P14 | run autoritativo `20260903T095600_E6.0C`: los 58 pares E6.0B se dividieron en 40 directos, 12 estáticos fuera de P14, 2 PGC no instalados y 4 móviles upstream. BVH de STL descartó todos los pares de triángulos por AABB sobre 401 estados (cero intersecciones); 4 self-tests validaron el SAT coplanar/3D. Faltan clamp real, holgura/tolerancias, política runtime revisada y validación física; gate cerrado. Cero red/ROS/estado/publicador/movimiento |
| 2026-09-03 | E6.0B broad phase de autocolisión P14 | run `20260903T094547_E6.0B`: 401 estados `preposición→A→B→A→preposición`, 46 links vendor, cero violaciones URDF y cero solapes OBB entre links con distancia cinemática >3. Los 58 pares cercanos quedan sin clasificar por ausencia de SRDF/ACM; PGC no representa las abrazaderas pasivas. Estado parcial, gate físico cerrado. Cero red/ROS/estado/publicador/movimiento |
| 2026-09-03 | E6.0A contrato ready/recovery P14 | run autoritativo `20260903T093145_E6.0A`: task0/frame0 demuestra orden directo de muñecas (`0,002112805 rad`) y rechaza el swap E4.0 (`0,614627484 rad`); ready B queda dentro del soporte. P14 usa 14 valores y hold fresco H/L/W. Recovery exacto de brazos `B→A→preposición` derivado pero no validado físicamente/colisiones; `back` vendor no es inverso. Run `092935` descartado por el mapping antiguo. Cero red/ROS/estado/publicador/movimiento |
| 2026-09-03 | E6.0I entrada/salida home del ready | run vigente `20260903T115129_E6.0I`: snapshot fresco 20D home, 101 muestras de `home↔preposición` y cobertura compuesta de 601 estados. Un nuevo OBB hombro derecho/torso se resolvió por malla exacta; cero intersecciones, mínimo vendor `0,011169662 m`. Sin publicador/movimiento; falta geometría clamp, tolerancias, dinámica y validación física. Run `114811` es fail-safe superado por no haber probado aún ese quinto par |
| 2026-09-03 | E6.0-CHECK auditoría inicial de preparación del canary | run `20260903T115457_E6.0-CHECK`, superado por `120716`: consumió E6.0G/H/I y dejó 5 gates antes de adoptar el proxy documental E6.0J. Local, sin red/ROS/publicador; no autorizó movimiento |
| 2026-09-03 | recuperación de E-stop y guard de arranque | shutdown lógico aceptado y apagado completo confirmado; el arranque con E-stop pasó `WaitEStopRelease→SelfChecking→JoystickMode`, self-check y `StartMotion` exitosos. Se corrigió el guard para aceptar `WaitEStopRelease` sin reiniciar/mover; instalado en Vision hash `6c3cbe48…9287b`, backup `/home/walker/cruzr-v020-boot-guard-backups/20260903T113735`. `--check`: versión v0.2.0, estado JoystickMode, x86 3/3, cámaras 2/2, seguridad 0/0/0, `movement=none restart=none` |
| 2026-09-03 | gate home compatible con IDs v0.2.0 | `/mc/actuator_state` usa elevador/cintura `11004/11003/11002/11001`, no los IDs históricos `2001/2002/2003/3001`. El parser acepta ambos esquemas y rechaza duplicados. Self-test completo pasó; `cruzr_recover_to_home.sh --check` vivo midió 20 ejes, cuerpo ≤0,002684 rad, brazos ≤0,000959 rad, velocidad 0 y delta ≤0,002684 rad; `MEASURED_HOME=1`, cero objetivos |
| 2026-09-03 | E5.2 selección preliminar de perfil | run `20260903T091901_E5.2`: regla de menor dimensión dentro de `max(0,0001 rad,1 %)` del mejor MAE elegible selecciona P14 para tasks 0–3. H sin mejora material, W empeora ~`6,88e-6…1,16e-5 rad`, L empeora ~`7,83e-4…3,48e-3 rad` y presenta 12/80 rechazos. Cero red/ROS/estado vivo/publicador/movimiento. No autoriza E6.0; el desglose vigente de gates está en E6.0-CHECK |
| 2026-09-03 | E5.1 matriz shadow-replay por perfil | run `20260903T091319_E5.1`: 20 inferencias C0 E3.0 verificadas se enmascararon bajo 8 perfiles para 160 bundles comparables. 148 ACCEPT, 12 REJECT_SAFE y 160/160 máscaras; los 12 rechazos sólo habilitan L (task1/seed2 velocidad lifter3; task2/seed0 y task3/seed0 rango lifter1). Perfiles sin L: 80/80 aceptados. Sin red/ROS/estado vivo/publicador/movimiento; sólo libera E5.2 offline |
| 2026-09-03 | E5.0 matriz completa del sink | run `20260903T090355_E5.0`: 8 perfiles × `low/middle`, 16/16 celdas PASS, 544 casos; 32 válidos aceptados, 512 inválidos rechazados y 16/16 probes de máscara/hold. Corregido el falso `axis_profile_mismatch` de P14. Todo local, sin ROS/red/estado/publicador/movimiento. VLA-5 queda completo sólo offline; libera E5.1 shadow, no ejecución física |
| 2026-09-03 | E4.1F auditoría de geometría oficial | run `20260903T085912_E4.1F`: manual SDK/producto, USD/URDF, XML ready y dataset validados por hash. Oficial: B0 `0,60×0,40×0,22 m`, plataforma 1 m, carga global bimanual 15 kg y PGC `0,1385×0,075×0,075 m`/50 mm; PGC corresponde a `cruzr_s2_v1_gripper` y se excluye. Para las placas pasivas `cruzr_s2_v1` sólo se enumera la familia clamp: no hay envolvente/TCP/masa/CoG/CAD oficial. Cero mediciones manuales, red al robot, inferencia, publicadores o movimiento. Fixture físico bloqueado; E5.0 offline autorizado |
| 2026-09-03 | E4.1E diseño offline de fixture corregido | run `20260903T093443_E4.1E`: 401 estados, tres planos y margen XY de 55 mm. Manteniendo B0+50 mm fijo, 128.386 colocaciones sólidas alineadas resultaron compatibles con apoyo y cero con colisión; la referencia global `+76,5°`/`0,856 m` fue rechazada. Se derivaron muescas upstream izquierda `[-0,720,-0,470]×[0,000,0,200] m` y derecha `[0,400,0,650]×[0,000,0,170] m`, sin solape con apoyo. Faltan abrazaderas reales, estructura, entrada y recovery; no autoriza fabricar ni mover. Cero red al robot, inferencia, publicadores o movimiento |
| 2026-09-03 | E4.1D identidad de efector y dependencia de colisión corregida | run `20260903T093440_E4.1D`: el SDK asigna PGC-140-50 a `HW_TYPE=cruzr_s2_v1_gripper`, distinto de las abrazaderas pasivas `cruzr_s2_v1` instaladas. Sin CAD/cotas no se validó equivalencia geométrica. Los 32 cruces E4.1C se separaron en 10 `pgc/finger` y 22 muñeca/sensor de fuerza; el tablero sólido sigue rechazado al excluir PGC. El intento `093412` se descarta por conteos hardcoded obsoletos; el wrapper ya valida la partición dinámica. Cero red al robot, inferencia, publicadores o movimiento |
| 2026-09-03 | E4.1C barrido offline corregido del fixture | run autoritativo `20260903T093408_E4.1C`: 121 estados, 46 geometrías URDF, 60 candidatos AABB y 32 intersecciones triángulo/plano contra el tablero en doce links. B0 tuvo cero candidatos y no se colocó. El run `20260901T090235_E4.1C` queda descartado por el mapping de muñecas anterior. Estado `SOLID_TABLETOP_CANDIDATE_REJECTED_BY_VENDOR_URDF_SWEEP`; todo local, cero red al robot, inferencia, publicadores o movimiento |
| 2026-09-01 | E4.1 calibración métrica del fixture | run válido `20260901T084855_E4.1`: CameraInfo/TF vivos, 20 posiciones tag 113 y borde posterior B0 del episodio 90. Reconstrucción `0,603128627 m` frente a `0,603 m`; `platform_in_base=(0,261844987,-0,027738106,0,870000000,0,0,-1,545870035)`, incertidumbre ±16,84/13,30/10,00 mm y ±0,868°. `D_BUMPER_PLATFORM=-0,092859226 m` revela solape de proyecciones; no se colocó la mesa ni hubo inferencia/publicador/movimiento. Estado `METRIC_FIXTURE_CANDIDATE_RESOLVED_PHYSICAL_GATES_OPEN`; siguiente: geometría de mesa, colisiones/swept volume y recovery E4.0, sólo offline/lectura |
| 2026-09-01 | E4.2 familias de altura low/middle offline | run `20260901T081210_E4.2`: 500 episodios + XML no-S2 55/70/85/100/115 + FK URDF S2. Tasks 0/1 correlacionan con 55/70/85 y tasks 2/3 con 100/115, pero quedan 84/95/49/58 episodios sin perfil a 0,05 rad. Pares task 0/2 y 1/3 comparten lifter a 0,000124356/0,000206182 rad: no existe altura escalar deducible ni `platform_in_base`. Episodios 90/91 sólo correlacionan tasks 2/3 con 1 m/perfil 100 no-S2. Estado `PARTIAL_HEIGHT_FAMILIES_RESOLVED_SINGLE_HEIGHT_MAPPING_REJECTED`; 10 frames y hashes válidos, sin red al robot, inferencia, publicadores o movimiento. Siguiente: aclaración UBTECH o calibración métrica offline |
| 2026-09-01 | E4.0 resolución read-only de VLA-ready | run final corregido `20260901T075728_E4.0`: forward `7722b734…7f6` 2×14/2,5 s y back `ee39039c…389` 2×14/5 s; back no invierte la secuencia. Se corrigió el orden MetaMove→checkpoint del candidato 20D y se resolvió cintura como `waist_yaw=0`. El task no está instalado/registrado ni en el upgrade v0.2.0; lifter queda heredado y 500 episodios demuestran múltiples configuraciones. Faltan límites runtime/swept volume/recovery. Resultado `PARTIAL_RESOLUTION_BLOCKED_NOT_READY_FOR_E4_1_OR_PHYSICAL_USE`; `exited/exited/publishers:0`, sin estado ni movimiento. Siguiente: E4.2 offline |
| 2026-08-28 | E3.3 contrato temporal offline | run `20260828T124011_E3.3`: 22/22 casos locales pasan y cancel/STOP/fault purgan sin replay ni publicador. Auditoría estática: chunk 10×20 a 80 ms/horizonte 0,72 s, inferencia 0,2 Hz; `continuous_end_chunk_num=5` sólo está en YAML, mientras Vision termina con un único `flag_pred>0,1`; ejecutores suministrados discrepan entre 900/9 s (`src`) y 600/6 s (`install`). `exited/exited/publishers:0`, sin estado ni movimiento. Estado `PASS_LOCAL_TEMPORAL_FAIL_CLOSED_VENDOR_SEMANTICS_UNRESOLVED`; VLA-3 y ejecución física siguen bloqueados, sólo E4.0 read-only queda autorizado |
| 2026-08-28 | E3.2 fault injection contra sink local | run `20260828T121832_E3.2`: 2/2 chunks de control aceptados y 32/32 inválidos rechazados; cubre identidad, esquema/orden/dimensión, NaN/Inf, frescura, timeline, rango/salto/velocidad, IDs, cancel/STOP/deadman y doble cliente. AST sin ROS/red/publicador/topic físico; `exited/exited/publishers:0` antes/después, sin estado ni movimiento. Ocho máscaras tienen tests unitarios, pero sólo P20/low ejecutó la suite completa; aceleración no tiene límite certificado. Estado `PASS_LOCAL_SINK_ALL_INVALID_REJECTED`; sólo libera E3.3 offline |
| 2026-08-28 | E3.1 OOD visual offline | run válido `20260828T120228_E3.1`: 26 proxies de imagen sobre tasks 0/2, 26 `ACCEPT_STRUCTURAL`, nominales exactos y máximos cambios de chunk 0,040258/0,053590 rad bajo zoom. Checkpoint sin cambios; `exited/exited/publishers:0`, sin ROS, estado o movimiento del robot. La parrilla métrica sigue bloqueada por falta de RGB-D, calibración, segmentación/pose y geometría de repisa; sólo queda liberado E3.2 con sink offline. El intento `20260828T115905_E3.1` falló seguro tras una muestra por consumo de stdin de `ssh`; wrapper corregido y regresión cubierta por ejecución completa |
| 2026-08-28 | E2.3 piloto reducido de repetibilidad P20 | se ejecutaron dos runs independientes task 0 y dos task 2, con STOP entre ellos. Task 0: 4 chunks, todos rechazados por 7 discontinuidades, duración 10,006055–10,039981 s y máximo `R_shoulder_yaw_joint` 1,361919–1,367893 rad. Task 2: 4 chunks, todos rechazados por 7 discontinuidades, duración 10,005578–10,006689 s y máximo 1,372170–1,379845 rad en el mismo eje. Ambos manifests validan; cada run y los finales quedaron `exited/exited`, `publishers:0`, sin movimiento. Estado `PASS_PILOT_2X2_SHADOW_ONLY`: rechazo/runtime reproducibles, no éxito de PICK |
| 2026-08-28 | E1.0/E1.3 reducidos y E2.1 task 2 completado en shadow | por decisión del propietario, E1.0 cerró con medidas `1,80 × 0,80 × 1,00 m`, cuatro esquinas a 1 m, rigidez/estabilidad y separación >1,5 m; fotos/marcas se difieren a E4. E1.3 reutiliza B0 `0,603 × 0,397 × 0,217 m` y difiere masa/colocación a E4/E6, sólo para liberar shadow. E2.1 `20260828T105547_E2.1` produjo dos chunks task 2 en 10,065 s; ambos fueron rechazados por siete saltos iniciales, máximo `R_shoulder_yaw_joint=1,376502 rad` frente a 0,35. Inferencia/control terminaron `exited`, publicadores `0`, hashes válidos y ningún movimiento. Estado `PASS_SHADOW_SAFETY_ONLY`, no PICK validado |
| 2026-08-28 | reanudación VLA en E1.0 con robot encendido | el propietario informó `home`; el diagnóstico fresco confirmó Motion/Vision accesibles, `HW_TYPE=cruzr_s2_v1`, baterías 70,0/77,7 %, paros 0/0, cargador fuera, acciones listas y máquina de tareas libre. El gate de home no certificó los 20 ejes porque faltaron `2001/2002/2003/3001`, por lo que no se autorizó movimiento. VLA permaneció `exited/exited` con `publishers:0`. Se abrió `Humanoide-vla-evidence/20260828T104622_E1.0/actual_result.yaml`; E1.0 queda pendiente de cuatro alturas, ancho/fondo, estabilidad y fotografías reales de `MESA_T1` a más de 1,5 m del robot |
| 2026-08-28 | return-to-home condicionado por muestra 20D y estado | `cruzr_recover_to_home.sh` pasa a `--check` por omisión, exige 20 ejes presentes, error cero, Operation Enabled, velocidad ≤0,02 rad/s, delta consigna ≤0,01 rad y usa `<0,02 rad` para declarar home sin enviar goals. Un inicio de tarea home ya no prueba éxito. Posturas PICO/unknown/caja posiblemente sujeta/intento no confirmado y eventos posteriores de fuerza, autocolisión, `MoveToGoalFailed`, fault o SAFEOP quedan bloqueados. La primitiva vendor sólo puede ejecutarse internamente desde estados reconocidos del ciclo de caja, con gates antes/después; `cycle.sh --home` delega al recovery, `--force-held-home` se retiró y `--fast` no omite auditorías. `--self-test`, `bash -n`, compilación Python y diff aprobaron localmente con el robot apagado; ruta física revisada pendiente de validación controlada |
| 2026-08-28 | `open_arm_before_home` falla desde postura PICO cruzada; apagado controlado completado | el goal `54f7beb2…` inició ambos brazos, cintura y elevador en paralelo. El FT izquierdo llegó a `Force-X=-370,944 N`; el brazo izquierdo no alcanzó el objetivo y el elevador abortó, terminando `MoveToGoalFailed`/`7104050`/`status=6`. El final previo de PICO ya mostraba autocolisión torso–codo/muñeca izquierda a 17–25 mm. Después 4004/4003/4002 registraron `0x1003` y `0x123f`; `hw`/manipulation reiniciaron y quedaron sin publisher de actuadores ni servidor de acción. Con confirmación física completa y paro mantenido, `/emb/pm_shutdown` respondió `success=True`; Motion/Vision cayeron, pantalla/luces se confirmaron apagadas, y sólo entonces se pulsó `KEY1` y apagó el chasis. Indicador verde apagado, robot/brazos estables. Se descarta esa tarea como home universal desde postura PICO; faults/consignas pendientes de redescubrir antes de cualquier movimiento |
| 2026-08-28 | corregido aborto de `--prepare-full` antes del rollback | el primer intento superó el preflight Motion, pero la asignación de entorno `BACKEND_LOG=…` chocó con la constante shell de sólo lectura y dejó a Python sin ruta. Se cambió únicamente el nombre exportado a `BACKEND_LOG_PATH`. `bash -n` y `git diff --check` aprobaron; el mismo parser pasivo obtuvo `operation_type=1` y `--check-arms-only` confirmó hash `4e8d79a4…`, `clamp/waist=0/leg=0`. El perfil full no fue restaurado, no se recargó modo, no hubo START ni movimiento |
| 2026-08-28 | lanzador PICO full-body separado, aún no activado | se creó `probar_pico_full.sh` sin modificar `probar_pico.sh`. El nuevo flujo exige el YAML vendor exacto y la tarea viva `clamp/waist=1/leg=2`, separa restauración, recarga y START, requiere Wi-Fi sin Ethernet sujeto y conserva preflight/Y/STOP. Añade monitor de log Motion y aborta ante IK, fuerza, EtherCAT, pérdida del monitor o click que conmute protección. El gestor de perfil comprueba STOP mediante log pasivo, sin abrir el WebSocket que podía autoarrancar 4.7.0. Sintaxis, ayudas, diff y bloqueos no-TTY aprobados; `shellcheck` no disponible. Checks reales: full rechazó el hash arms-only activo y el original confirmó `clamp/0/0`. No se cambió configuración robot/PC, no se recargó TeleopMode y no hubo movimiento; el baseline sigue arms-only |
| 2026-08-28 | disciplina de evidencia VLA endurecida para todos los ejercicios | se añadió un creador exclusivo de runs que rechaza raíz/rutas existentes, wrapper completo E1.1, protección de no sobrescritura y hashes relativos en E1.2, y wrapper E2.3 con sub-runs/STOP independientes. E2.0/E2.1 usan el mismo creador. Todos los bloques actuales/futuros del plan que escriben evidencia inicializan su ruta localmente; se eliminaron dependencias de `$VLA_RUN_ID`/`$VLA_EVIDENCE_ROOT` heredadas. Validación local solamente: no se inició inferencia, no se cambió el robot y no hubo movimiento |
| 2026-08-28 | E2.0 task 0 ejecutado fuera de secuencia y recuperado | el bloque manual sí ejecutó check, inferencia shadow y STOP, pero `$VLA_RUN_DIR` estaba vacío y todos los `tee` fallaron contra `/`. La evidencia persistente se recuperó en modo read-only desde los contenedores detenidos: dos chunks, ambos rechazados por `first_point_delta_violations:7`, máximo `R_shoulder_yaw_joint=1,339886 rad` frente a 0,35; duración real `10,063076 s` ante 8 s solicitados. Estado final verificado: inferencia/control `exited`, publicadores `0`, ningún movimiento. Se añadieron `--export-evidence` y `run_vla_shadow_smoke.sh` para evidencia autocontenida y STOP en fallo. Clasificación `PASS_SHADOW_SAFETY_ONLY`; escena/postura no documentadas y E1.0/E1.3 pendientes, por lo que E2.1 no está autorizado |
| 2026-08-27 | referencia visual del dataset VLA identificada | se validó en `/tmp`, sin alterar el dataset, el muestreo automatizado de 12 frames —inicio/medio/final de episodios 0/1/90/91— mediante VLC. Muestran un tote rígido gris abierto de paredes altas y borde gris, con tiras/marcas negras estrechas en algunos frames y un pequeño elemento con lazo visible dentro. El seek puede elegir frames adyacentes entre runs, por lo que sus hashes son de integridad por run, no canónicos. El plan distingue `B0_SAFE` vacía de la referencia: cartón u otro tote es OOD aunque mida 60×40×22 cm. No hubo inferencia ni movimiento |
| 2026-08-27 | mesa candidata disponible para fixture VLA | el propietario declara disponible `MESA_T1`, nominalmente `1,85 × 0,80 × 1,00 m` (ancho × fondo × altura). Se registró como `PENDIENTE`: E1.0 debe medir tablero/cuatro esquinas y comprobar nivelación, rigidez, estabilidad, patas y travesaños. No determina la separación horizontal ni autoriza acercarla al robot |
| 2026-08-27 | inventario mínimo de superficies VLA definido | para tasks 0–3 se reutilizará `MESA_T1` a 1 m y sólo se considerará una plataforma regulable rígida después de que E4.2 resuelva las alturas low/middle; no se requieren compartimientos ni dos repisas simultáneas. `RECEPTOR_VOLCADO` y `MESA_DESTINO_VACIA` corresponden a la misión ampliada y quedan pendientes de nueva primitiva/dataset, no del checkpoint actual. No se adquirió ni movió mobiliario |
| 2026-08-27 | primer intento E1.1 técnicamente correcto pero sin evidencia | `install --check/--verify` y `shadow --check/--status/--stop` observaron hosts correctos, paquete S2/checkpoint, instalación deshabilitada, contenedores `exited`, cero publishers y sesión detenida. `VLA_RUN_DIR` estaba vacío y los cinco `tee` intentaron escribir bajo `/`, fallando por permisos; no quedaron logs. El plan inicializa/valida ahora el directorio y exige cinco logs no vacíos más hashes. Estado `INCOMPLETE_EVIDENCE_EMPTY_VLA_RUN_DIR`; repetir E1.1, sin inferencia ni movimiento |
| 2026-08-27 | E1.1 baseline PC/VLA aprobado con evidencia | run `20260827T141244_E1.1`: cinco logs no vacíos validados contra `logs.sha256`; Vision/Motion y paquete `codes-S2`/`checkpoint-40000`/abrazaderas correctos; instalación deshabilitada; inferencia/control `exited`; `verify_installation` exige `restart=no`; publicadores de movimiento `0`; STOP confirmado. Se creó `actual_result.yaml` con `PASS`. Sólo queda habilitado E1.2 de lectura; no hubo inferencia ni movimiento |
| 2026-08-27 | primer intento manual E1.2 sin directorio de evidencia | `VLA_RUN_DIR` había sido definido dentro del subshell E1.1 y dejó de existir al volver al prompt. Las redirecciones intentaron escribir tres ficheros bajo `/` y fueron rechazadas por permisos; fuentes y robot no cambiaron. Se añadió `audit_vla_experiment_e1_2.sh`, wrapper local de sólo lectura que crea/valida su directorio, comprueba XML/tasks, extrae 12 frames y deja revisión visual pendiente |
| 2026-08-27 | E1.2 auditoría local de artefactos aprobada | run `20260827T141837_E1.2`: XML S2 hash `f4025124…d8323`, preposiciones y llamada pendiente `clamp_s2_joints_trajectory`; catálogo exacto tasks 0–3; doce frames y hoja de contacto inspeccionados. Referencia: tote gris abierto de paredes altas/borde gris, tiras negras estrechas en algunos frames y pequeño elemento con lazo dentro, no cartón. Alturas low/middle, task ready instalado, trayectoria interna y pose horizontal siguen `UNRESOLVED`. Estado `PASS`, sin conexión al robot, inferencia ni movimiento |
| 2026-08-27 | repetición E1.2 del operador aprobada | run `20260827T142214_E1.2`: todos los ficheros validan contra sus hashes. Varios PNG difieren bit a bit del run anterior porque el seek temporal de VLC seleccionó frames adyacentes; la hoja de contacto revisada mantiene el mismo tote/escenario/semántica. El extractor documenta ahora que los hashes PNG prueban integridad por run, no identidad canónica. Estado `PASS`, sin conexión al robot ni inferencia |
| 2026-08-27 | corregida la interpretación geométrica del demo VLA | la sección 7.3 del SDK dice que B0 `60×40×22 cm` debe estar sobre una plataforma de **1 m de altura**; no dice que exista 1 m horizontal robot–plataforma. El plan retiró esa separación inventada y dejó `D_BUMPER_PLATFORM/platform_in_base=UNRESOLVED`. También separó las alturas 55/70/85/100/115 del árbol alternativo no-S2. Se localizó el XML S2 ready, hash `f4025124…d8323`, que aún depende de `clamp_s2_joints_trajectory`. E4 debe derivar pose horizontal/alturas con XML, FK, cámara y frames antes de movimiento. Sólo hubo lectura y documentación |
| 2026-08-27 | manual secuencial E1.0→E8.2 añadido al plan VLA | el inicio de `docs/plan_de_trabajo.md` define plataforma S2 a 1 m de altura fuera de la envolvente, pose de B0, tolerancias, orden literal de comandos, salida esperada, PASS/FAIL/BLOCKED, artefactos y formulario `actual_result.yaml`. E2 es smoke shadow OOD; E4 calcula la pose horizontal y el mapeo low/middle antes de manipular. Los experimentos físicos E4/E6/E7 continúan bloqueados; no se inició inferencia ni movimiento |
| 2026-08-27 | escenarios y runbook PC completos para validación VLA | se definieron en `docs/plan_de_trabajo.md` B0, plataforma S2 de 1 m, estados `NO_BOX/SUPPORTED/HELD`, manifiesto de evidencia y tarjetas `VLA-T00…T10`. Cada tarjeta especifica escenario, comandos o mensajes PC, PASS/FAIL, evidencia y recovery; se separan scripts existentes de herramientas aún por implementar. La revisión de `cruzr_blue_workbin_cycle.sh --help` fijó el lado de 600 mm paralelo a hombros. Es planificación documental: no se inició inferencia ni hubo movimiento; los canaries físicos siguen bloqueados por falta de ready/fixture, ejecutor y primitiva demostrados |
| 2026-08-27 | campaña VLA 14→20 priorizada | se amplió el inicio de `docs/plan_de_trabajo.md` con una campaña por gates para caracterizar exhaustivamente por grupos los 20 outputs del checkpoint: A=14 brazos, H=2 cabeza, L=3 elevador y W=1 cintura. Cubre ocho perfiles funcionales —incluidas dos combinaciones distintas de 17D—, los cuatro task IDs, 32 celdas shadow, postura baja/media, contrato temporal, end flag, OOD, ejecutor sink, canary sin caja, tareas físicas con caja vacía y decisión C0/C1/C2. Es planificación documental; no se inició VLA, no se creó publicador y no hubo movimiento |
| 2026-08-27 | plan de trabajo multialtura y multitamaño | se documentó en `docs/plan_de_trabajo.md` una misión por estados para recoger una caja a baja altura, transportarla, volcar contenido ligero en un receptor, devolverla erguida y depositarla vacía a otra altura. Incluye una caja manipulada por ensayo, perfiles de cajas/estaciones, variación OFAT de posición/orientación/altura, comparación de detector/tag/RGB-D, control determinista, replay, PICO y VLA, gates de captura 20D y recuperación por fase. Es planificación documental: no se enviaron comandos ni se autorizó movimiento |
| 2026-08-27 | arranque controlado después del trip FT restaura Motion sin mover | se encendió chasis, `KEY1` y botón trasero con el paro accionado; Control Center esperó `WaitEStopRelease`. Tras confirmación física se liberó y no hubo movimiento inesperado. La primera consulta `docker info` activó `docker.service` mediante `docker.socket`; se registró explícitamente y no envió comandos al robot. Motion inició `hw`/`manipulation_robot_app`, readiness x86 3/3 y cámaras 2/2; self-check global `passed=true` y `StartMotion` exitoso. Control Center quedó en `AutoTaskMode`. `cruzr_blue_workbin_cycle.sh --check` aprobó: actuadores Operation Enabled, errores/deltas/velocidades dentro de gates, paros 0/0, cargador fuera, baterías 51,5/63,4 % y acciones listas. `cruzr_recover_to_home.sh --check` repitió la salud pero bloqueó correctamente `home` porque el nuevo log no clasifica la postura. El boot guard terminó `failed` por `CONTROL_STATE=unknown`, aunque no ejecutó recuperación (`RECOVERY_ELIGIBLE=0`) y registró seguridad `0 0 0`; no invalida el preflight de Motion, pero debe corregirse para reconocer `AutoTaskMode` |
| 2026-08-27 | teleoperación interrumpida al sujetar una caja; protección FT, caída de Motion y apagado completo | el stream PICO/PC continuó a 90 Hz, Y/enable permaneció activo y el script sólo terminó al `Ctrl+C` del operador. Motion registró en la muñeca izquierda `Force-X=-305,6…-307,0 N` frente al umbral de 120 N, declaró `Excessive force` y detuvo la tarea a las 16:25:59. La causa física exacta —compresión de la caja/contacto externo o transitorio/bias FT— queda pendiente, pero **no fue apretar fuerte el grip del PICO**, que es un clutch booleano. Después se observaron servo 5003 `0x1001/0x2007`, saltos de consigna en ambos hombros y EtherCAT SAFEOP ERROR; los checks terminaron `exit 25` sin servidor de manipulación. Con caja retirada y robot estable, el propietario autorizó apagado completo. `/emb/pm_shutdown` respondió `success=True`; Control Center transitó `TeleopMode→WaitShutdownReady→Shutdown→Term`. Motion y Vision dejaron de responder, el operador confirmó pantalla/luces apagadas, pulsó después `KEY1` y finalmente apagó el chasis; indicador verde apagado y robot estable. No se ha arrancado ni demostrado recuperación |
| 2026-08-27 | carrera de auto-START de WebSocket 4.7.0 eliminada del preflight | el intento 10:12 encontró `operation_type=2` antes de la confirmación. Los logs demuestran que las consultas locales breves de las 10:12:28.592 y 10:12:48.961 coincidieron con `Broadcasting publisher states`; 4.7.0 ejecutó `device detected online, starting remote operation` y arrancó el publisher sin un mensaje `collect operation_type=2`. El preflight detectó el segundo caso y su cleanup lo dejó en STOP a las 10:12:54.828. Se sustituyeron la espera, CHECK 7/7 y la verificación final por reconstrucción pasiva desde transiciones `Pico connect state` y eventos `Pico publisher start/stop`, limitada al arranque vigente del servicio. El WebSocket queda reservado para el cliente oficial después de la confirmación o un STOP de emergencia. `--check` real a las 10:17 abrió **0** clientes WebSocket y produjo **0** START; bloqueó únicamente por `vr_status=0`. Sintaxis, shellcheck y diff correctos; no hubo movimiento |
| 2026-08-27 | primer intento izquierdo tras habilitar bimanual: STOP por segundo Y | arms-only y preflight aprobaron; Y produjo `enable=1` a las 10:07:06.050. Al intentar mover el brazo izquierdo, el grip permanecía activo (`squeeze=1.0`) y XR publicó otro intervalo independiente `Left.b_button=true` desde 10:07:12.312; 5 ms después el backend vendor conmutó `enable=0`. El derecho siguió neutro, no hubo fallo IK y la velocidad articular final fue cero. El script identificó la deshabilitación y confirmó STOP. Es un segundo evento Y en la entrada XR, no una limitación bimanual ni un fallo del brazo. No se modificó software: en la siguiente prueba mantener ambos grips neutros hasta `ENABLE_OFICIAL_CONFIRMADO=1` y después mantener el pulgar izquierdo alejado de Y; no ocultar este STOP sin definir antes otra parada desde el visor |
| 2026-08-27 | control bimanual habilitado por el propietario | tras confirmar el operador que el torso permaneció quieto y verificar cero fallos IK en la sesión arms-only, `--teleoperate` permite por defecto ambos grips/brazos. El gate de `clamp,waist=0,leg=0`, enlaces, tracking, watchdog, STOP y demás seguridades permanece. Se registran `BIMANUAL_GRIPS_ACTIVE=1/0`; `PICO_ALLOW_BIMANUAL=0` ofrece rollback operativo inmediato al criterio de un brazo. Cambio de código sin START ni movimiento |
| 2026-08-27 | primer START con arms-only y STOP por solapamiento mínimo de grips | preflight aprobado y sesión oficial activa durante 29 s con Motion `clamp,waist=0,leg=0`. El guard local detectó ambos grips sólo entre 09:59:26.872 y .917 (~45 ms, cinco frames derechos) y solicitó STOP. En la ventana Motion hubo cero `CalcS2*…failed`; los dos mensajes `ik_restart_time_` eran estado, no fallo. Estado final: `operation_type=1`, UI/cámara paradas y velocidad articular cero. No se ha demostrado que el robot prohíba control bimanual; el bloqueo actual es intencionalmente conservador |
| 2026-08-27 | perfil arms-only recargado y demostrado sin movimiento | con preflight físico/lógico fresco se cambió Control Center `teleop→auto_task→teleop` usando el mismo RPC de la web. En el estado intermedio hubo cero acciones y velocidad articular máxima 0. El último arranque Motion y el gate canónico demuestran ahora hash `4e8d79a4…`, `hand=clamp,waist=0,leg=0`; preflight final: paros 0/0, baterías 58,0/69,0 %, cargador fuera, única acción PICO y joints inmóviles. PC quedó STOP, UI inactiva, sin `pico_control`; prueba física de un brazo pendiente |
| 2026-08-27 | causa de oscilación aislada y perfil PICO arms-only instalado | Motion confirmó que la tarea real era clamp, pero su configuración vendor activaba cintura y elevador (`waist_mode=1`, `leg_mode=2`) en CoreMode 7. Ambos grips estuvieron simultáneamente activos casi toda la sesión y los logs mostraron fallos IK repetidos de alcance, especialmente en el brazo derecho; ésa es la causa comprobada del movimiento compensatorio del torso. Se instaló sin reinicio ni movimiento un overlay reversible que cambia sólo ambos modos a cero (`4e8d79a4…`; vendor `5f08b30c…`). La tarea viva sigue con 1/2: `--check-arms-only` falla de forma esperada y `--teleoperate` no puede enviar START hasta recargar TeleopMode y demostrar `clamp,0,0`. También se añadió STOP si ambos grips quedan apretados |
| 2026-08-27 | movimiento pronunciado del torso con controller 4.7.0 | en una sesión oficial, `pico_control` solicitó `clamp`, el backend PC etiquetó `gripper`, ambos grips estuvieron activos casi continuamente y el operador observó oscilación grande del torso. STOP quedó confirmado (`operation_type=1`, `enable=0`). El diagnóstico posterior verificó Motion `clamp` con cintura/elevador 1/2 y fallos IK: véase la entrada arms-only precedente. En un hallazgo separado, ADB TCP 5555 cerró al retirar USB aunque XR/63901 siguió activo; el preflight bloqueó antes de START |
| 2026-08-27 | recuperación tras PICO, fault 4003 y consignas latentes | la recuperación normal bloqueó `unknown`; después apareció `L_shoulder_yaw_motor` 4003 en FAULT `0x1001/0x0238`. Una tarea temporal sólo para el brazo derecho fue aceptada pero terminó `MoveToGoalFailed/status=6`, sin cambiar posiciones; dejó consignas derechas latentes de hasta 0,1043 rad. El preflight impidió correctamente llamar al rearmado 4003. Se añadió un gate para error/status y `abs(cmd_pos-position)>0,01`. El operador hizo un apagado completo, retiró la caja y usó `KEY1`; los brazos descendieron sin trayectoria. En el arranque siguiente, el boot guard quedó `failed` por `CONTROL_STATE=unknown` mientras el paro estaba accionado, pero tras liberarlo Motion inicializó correctamente: todos los ejes quedaron sin fault, `0x1237`, inmóviles, con posición/consigna dentro de ±0,003 rad de cero. **Home articular alcanzado sin enviar una trayectoria adicional ni llamar al rearmado.** `KEY1` aislado sigue sin ser un procedimiento aprobado y no debe reutilizarse como recuperación |
| 2026-08-27 | auditoría local del contrato de datos 20D suministrado | **VERIFICADO** en metadatos/configuración: estado 32D = 20 posiciones + 12 fuerza/par, acción 20D y horizonte de 10 filas. **OBSERVADO** en episodios 000000/000088/000499: `action[t]` está casi alineada con las 20 posiciones simultáneas (MAE ≈`9e-5`–`1.1e-4` rad; un frame de desfase empeora ≈20x). Parquet y MP4 exportan una timeline de 120 Hz, H.264 `960x576`, con igual número de filas/frames en las muestras. **PENDIENTE UBTECH/DSA**: origen exacto de la acción previa al actuador, reloj maestro y cadencia física real. Se documentó una vía de recolector pasivo y piloto, sin declararla contrato oficial. Sólo lectura: no se cambió PC/robot ni hubo movimiento |
| 2026-08-26 | PICO migrado de USB a Wi-Fi Cruzr | con STOP confirmado se habilitó ADB TCP y se retiró USB. PICO quedó `192.168.42.212:5555`, PC robot-Wi-Fi `.215`; tras reiniciar sólo XRoboToolkit y reactivar Head + Controllers / Working, Unity conectó directamente a `.215:63901`, `vr_status=1` y `probar_pico.sh --check` pasó 7/7. Motion/Vision siguen por Ethernet y DSA conserva Internet. Un socket `.51` obsoleto siguió visible temporalmente en el kernel, pero el preflight seleccionó y demostró el flujo Wi-Fi `.212→.215` |
| 2026-08-26 | destino de cámara PICO corregido | la primera ejecución de `--teleoperate` abrió correctamente el stream Vision pero el relay esperaba el listener en la concesión histórica `.42.211`; el PICO actual era `.42.212`, por lo que no podía llegar el keyframe y no se envió START. Se eliminó la IP predeterminada fija: el lanzador y el script de cámara descubren ahora `wlan0` por el serial ADB y usan USB sólo como fallback. Validado `.42.212` por `wlx80afcad40bd6`; sin relay residual ni movimiento |
| 2026-08-26 | primer gate oficial 4.7.0 y nuevo `--teleoperate` | `pico_control --arm_type clamp` abrió P2P, Y izquierdo produjo `Left.b_button`/`enable=1` y el grip derecho llegó al backend. El cliente oficial confirmó STOP. Un rearme posterior fue causado por un segundo `wscat --wait 1`, no por el STOP oficial; ese patrón quedó prohibido. El propietario acepta temporalmente la selección interna `gripper` sólo para cinemática de brazos. Se añadió `probar_pico.sh --teleoperate`: preflight, cámara principal, neutralidad fresca, Y, ventana inicialmente de 120 s y elevada por el propietario a 300 s, monitor de enlaces/heartbeat y STOP. Sintaxis, diff y rechazo no-TTY/duración inválida verificados; la cancelación final quedó STOP y no movió. El resultado físico del primer grip sigue pendiente de confirmación del operador |
| 2026-08-26 | cable Ethernet sustituido y enlace directo restaurado | `eno1` pasó de 10 a 1000 Mb/s full con autonegociación; se activó el perfil persistente `cruzr-s2`/`192.168.11.250`, never-default, y Motion `.2`/Vision `.3` respondieron sin pérdida en 0,2–0,9 ms. La ruta a `.11.0/24` usa Ethernet, PICO/Wi-Fi Cruzr permanecen activos y la ruta por defecto/Internet sigue por `DSA CORPORATE`. `probar_pico.sh --check` reconoció Ethernet y llegó a CHECK 5/7; falló únicamente porque el PICO aún no transmite TCP 63901. Sin START ni movimiento |
| 2026-08-26 | migración solicitada por UBTECH a controller 4.7.0 para robot v0.2.0 | se respaldó 5.3.0 parcheado (`c085fc4b…`), verificó el DEB 4.7.0 (`4f2b728b…`), purgó 5.3.0 e instaló 4.7.0 conservando el servicio parado durante los scripts del proveedor. El binario instalado coincide con el DEB (`e88b83b7…`), UI 4.1.0 permanece inactiva y el backend está STOP (`operation_type=1`); 4.7.0 no expone `enable_control`, por lo que los scripts validan el baseline pero bloquean todo START hasta observar el Y/enable oficial. XRoboToolkit está abierto por ADB, aunque el visor aún no envía TCP 63901 (`vr_status=0`). No hubo movimiento. Ethernet `eno1` negoció 10 Mb/s pero no resolvió ARP hacia `.2/.3`; el perfil quedó inactivo y Wi-Fi Cruzr sigue llevando Motion/Vision, mientras DSA conserva Internet. En la reunión UBTECH afirmó que 4.7.0 sí recopila datos del robot, contradiciendo/precisando la etiqueta china `只支持遥操作`; formatos, modalidades y exportación continúan PENDIENTES |
| 2026-08-25 | cámara principal Cruzr integrada en XRoboToolkit | `cruzr_pico_camera.sh` abre mediante `/streaming/start` la estéreo izquierda de cabeza, mantiene el heartbeat exclusivo de vídeo, convierte SRS HTTP-FLV/AVCC a H.264 Annex-B con longitud TCP y lo envía al listener 12345 del PICO; las pruebas físicas esperan `PICO_CAMERA_LIVE_BEFORE_START=1`. Fuente real validada (64 frames/3 keyframes en muestra y 36 unidades contra PICO simulado), cierre sin streams ni heartbeat residuales. No hubo START ni movimiento; la visualización en el PICO real queda PENDIENTE porque `.42.211` está fuera de línea |
| 2026-08-25 | reset USB Wi-Fi durante gate PICO | a las 12:59:43 desapareció del kernel el Realtek `0bda:b812`/`wlx80afcad40bd6`; el trigger nunca llegó (758 muestras a cero), `vr_status` cayó y nunca hubo `enable=1`; STOP final, sin movimiento. USB autosuspend ya estaba desactivado, pero Wi-Fi powersave estaba activo y existían errores LPS/tx report. Se fijó `powersave=disable` sólo para `Cruzr S2-0669 1`, se reconectó con STOP, se verificó `Power save: off`, DSA intacta y `--check` 7/7. Los bucles armados abortan ahora inmediatamente ante pérdida de interfaz/carrier/IP/ruta o tracking |
| 2026-08-25 | falso positivo de neutralidad corregido | el intento de las 12:53 abortó antes de START al reutilizar las últimas muestras del log, que eran de las 12:31:26 con ambos grips altos. Ahora START queda aún con `enable=0`, se exigen estados nuevos de ambos mandos pertenecientes a esa ejecución, se valida neutralidad y sólo después aparece `TOQUE AHORA`; ausencia o entrada activa envía STOP. Sin movimiento; final STOP/UI inactiva |
| 2026-08-25 | fallo de gatillo de nivel y corrección a flanco | `--all-controls` habilitó con una sola pulsación, pero sus 0,567 s altos repitieron Y y causaron `enable 0→1→0`; STOP automático, sin trip de heartbeat. Backend cambiado a pulso sólo en flanco ascendente, con gates de mandos neutros/liberación; activo `5083e9f0…`, rollback de nivel/300 s `40b440f4…`. A las 12:44 `--check` recuperó PICO/stream y pasó 7/7; final `vr_status=1`, `operation_type=1`, `enable_control=0`, UI inactiva; E2E físico pendiente |
| 2026-08-25 | Wi-Fi Cruzr canónica para todos los dispositivos del robot; DSA sólo Internet | toda `.11.0/24` se enruta vía `.42.2` y `.42.0/24` es directa por `wlx80afcad40bd6`; perfil Cruzr `never-default`/sin DNS. Motion, Vision, PICO y servicios robot usan `Cruzr S2-0669`; sólo Internet usa `wlo1`. Scripts dejaron de exigir `eno1`; `--check-motion-ready` pasó sin START/movimiento |
| 2026-08-25 | `--all-controls` abortó antes de START por Ethernet caído | `eno1` quedó `NO-CARRIER`/sin `192.168.11.250`; Motion/Vision no eran accesibles y no se armó teleoperación. El preflight ahora recomprueba portadora, IP, ruta, ping y SSH justo antes de los gates físicos para fallar inmediatamente y con causa concreta; ambas Wi-Fi permanecieron conectadas |
| 2026-08-25 | ventana integral PICO autorizada, aún no ejecutada | `probar_pico.sh --all-controls` permite 120 s activos tras 60 s neutros (configurable 120–180 s), cubre controles documentados y siempre solicita STOP; resumen sólo acredita entradas, no efectos finales. Tras una caída WLAN quedaron dos sockets y `vr_status=0` pese a Working; reiniciar sólo XRoboToolkit y reseleccionar Head+Controllers/Send data recuperó el enlace. El `--check` final terminó 7/7 con `vr_status=1`, clamp/300 s y backend desarmado; no hubo START ni movimiento durante el cambio |
| 2026-08-25 | PICO por Wi-Fi local sin túnel XR | `DSA CORPORATE` se conservó en `wlo1`; adaptador secundario y PICO se asociaron a `Cruzr S2-0669` (`.215`/`.211`); XR abrió TCP directo 63901, reverse vacío, `--check` OK y backend STOP; ADB por Wi-Fi soportado por discovery de serial |
| 2026-08-25 | movimiento PICO y retorno a home | el brazo se movió; STOP desarmó el PC pero TeleopMode persistió hasta seleccionar `auto_task`; home directo terminó, aunque las abrazaderas bajas pasaron casi rozando. `--home` queda cambiado a la tarea oficial `cruzr/open_arm_before_home` (apertura previa); hash y preflight sin movimiento verificados, prueba física de la corrección pendiente |
| 2026-08-25 | modo físico real PICO autorizado | `probar_pico.sh` por defecto prueba sólo brazo derecho: preflight Motion+PC, estabilidad 60 s, grip exclusivo, gesto 2–3 cm/5 s máximo y STOP al soltar/fallar; XR restaurado a `vr_status=1`; en ese preflight aún no se había ejecutado START físico |
| 2026-08-25 | ventana PICO 300 s / gate sin maniobra | DataChannel abrió antes de enable; `CoreMode 7` y protección de fuerza activos ~46 s sin trip de 10 s; cero movimiento con ambos grips siempre libres; tres pulsaciones finales alternaron `0→1→0` y provocaron STOP seguro; a las 10:43 `vr_status=0` |
| 2026-08-25 | debug lanzador PICO | añadidos progreso 1/7, timestamps, timeouts de 5 s y traza opcional; flujo normal y fallo ADB simulado verificados; backend permaneció STOP |
| 2026-08-25 | reconexión XR | restaurado ADB reverse 63901 y reiniciada sólo la app; TCP y `vr_status=1`; backend activo pero STOP (`operation_type=1`, `enable_control=0`); `--check` completo OK |
| 2026-08-25 | timeout PICO 300 s | propietario autorizó 10→300 s; binario PC `40b440…` instalado con STOP conservado y backup `0f0d3414…`; backend/UI/XR quedaron detenidos; sin runtime ni movimiento |
| 2026-08-25 | gate PICO/conmutador | gatillo y `CoreMode 7` verificados; toque único correcto habilitó, pero el gate falló por heartbeat a los 10,576 s desde START; STOP dejó `operation_type=1`, `enable_control=0`; en el último intento no hubo movimiento y sí voz |
| 2026-08-10/11 | diagnóstico inicial BMS | se observó desequilibrio SOC y SN truncado; pendiente proveedor |
| 2026-08-14 | AprilTag mesa 2 | tag 113 y referencias empty/held calibrados |
| 2026-08-17 | manos v4 | detección y demos de fábrica; luego se restauraron abrazaderas |
| 2026-08-20/21 | upgrade v0.2.0 | sistema actualizado, mapa y `HW_TYPE` preservados |
| 2026-08-21 | boot guard | recuperación controlada del race Vision→Motion validada |
| 2026-08-21 | VLA shadow | inferencia funcional; chunks rechazados desde `home`; cero mando físico |
| 2026-08-21 | apagado | discrepancia manual/hardware/software documentada |
| 2026-08-24/25 | PICO | cadena hasta DataChannel validada; heartbeat sigue bloqueando sesión estable |
| 2026-08-25 | relevo global | `AGENTS.md` y esta fuente hacen el contexto descubrible automáticamente |
