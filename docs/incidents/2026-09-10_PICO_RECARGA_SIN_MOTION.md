# Recarga de PICO→HOME con Motion sin iniciar — 10-09-2026

## Estado y secuencia observados

El operador instaló y recargó open_v2 y presentó un preflight fallido.
El XML remoto coincide con
`6b8309f3c29025baf4d7116888c4f64a4f3a86f0cd74e226642203c194dd6999`;
task_list contiene una entrada y su hash es
`33dad663f78a3c295d530eea01561d45194c85b9d8d4999e3694e83df96c8826`.
La fecha del proceso es posterior a la del task_list. Esto **no** demuestra
que el proceso haya terminado de inicializar ni ofrezca acciones.

Las consultas nuevas separan estos hechos:

- CC conserva el contenedor `4a7eab87bd4d…` y la espera de Motion instalada
  durante la reparación de arranque anterior. Arrancó correctamente y después
  hubo cambios `AutoTaskMode→TeleopMode→AutoTaskMode` a las 15:15 del reloj robot.
- E-stop principal pulsado a las 15:18:50. El log hw registra la parada de
  EtherCAT y retención de posición; el contenedor hw se reinició una vez a las
  07:18:50Z y pasó a esperar `/mc/rosa_control/start`.
- Manipulación se reinició a las 07:20:47Z, después de la instalación, y sigue
  esperando `ListControllers`. Servidor de acciones=0.
- E-stop liberado a las 15:24:16; no consta un nuevo StartMotion posterior.
  La última transición registrada de CC sigue siendo AutoTaskMode. **No** se
  ha demostrado WaitStartMotion: el texto del preflight lo citaba como ejemplo.
- Consulta nueva de `/mc/actuator_state` agotó siete segundos sin muestra.
  Un topic anunciado no permite conocer la postura, los errores ni las consignas.
- `fault_current=[]` en lectura SQLite readonly. Ausencia de fallos en esa tabla
  no equivale a Motion disponible. El estado hw inspeccionado no registra OOM.

**CONFIRMACIÓN FÍSICA:** el usuario dice «en PICO, estable sin contacto».
Después confirma explícitamente abrazaderas «vacías».
No reutilizar la medición HOME anterior al cambio a PICO y al paro.

La proximidad temporal demuestra que la pérdida de Motion ocurrió con el paro,
antes de la recarga de manipulación. No atribuirla a un XML defectuoso, a batería
baja ni a la carrera de arranque reparada. El detalle interno de terminación de
hw no queda completamente explicado por el extracto; no se ha demostrado daño
de hardware ni se han ensayado rearmes para inferirlo.

## Corrección local

En `scripts/teleoperation/cruzr_pico_to_home_owner.sh`:

1. `active_estop_preflight` y `released_preflight` propagan explícitamente un
   error del auditor y rechazan marcadores requeridos ausentes o incorrectos.
   Antes, Bash desactivaba errexit dentro de la sustitución de comandos y el
   `printf` final podía devolver cero pese a los fallos anteriores. En el intento
   comunicado no hubo movimiento: el chequeo posterior de servidor=0 detuvo
   la ejecución. No depender de ese segundo fallo para bloquear.
2. El despacho de preflight conserva la salida y el código del auditor y sale
   antes de consultar el runtime o enviar la trayectoria. En `--run` también
   finaliza la evidencia antes de salir por ese error.
3. Se separan `TASK_PROCESS_ORDER=after-task-list|reload-required` y
   `RUNTIME_STATE=action-server-ready|action-server-unavailable`. Se retira la
   afirmación engañosa `RUNTIME_STATE=loaded` basada sólo en fechas.
4. La recarga informa `PROCESS_RESTARTED`, y su no-op no equivale a una
   recuperación operativa. Se retira la instrucción de liberar E-stop y pasar
   directamente a preflight: el arranque debe recuperarse según su guía.
5. Ayuda y confirmaciones de instalación/recarga explicitan brazos abajo y
   abrazaderas vacías **antes** de preparar PICO. La instalación no constituye
   un método de recuperación desde unos brazos ya elevados.

No se modifica el XML, la trayectoria, los tiempos ni las protecciones.
No se instalaron archivos ni reiniciaron contenedores desde el agente durante
este diagnóstico. La instalación/recarga aquí observada fue realizada por el
operador. La adaptación de arranque de CC anterior se conserva.

## Validación y reversión

Diecisiete pruebas locales y sintaxis Bash correctas. Cinco pruebas nuevas
ejecutan las funciones Bash reales con auditor sustituido, dentro de las mismas
sustituciones de comandos: código no cero incluso con marcadores positivos,
marcadores ausentes/malformados, ambos paros admitidos, despacho detenido antes
del runtime con evidencia conservada y servidor ausente pese a fecha posterior.
El resto comprueba postura, XML y secuencia de la ruta open_v2.

Preflight vivo corregido: exit1, `PREFLIGHT_FAILED=1`, sin `INSTALL_STATE`
posterior, por lo que se detuvo antes de consultar el runtime remoto. Conservó
la salida del auditor (acciones0, joints ausentes, paros0/0, cargador0) y no
envió movimiento. Se confirma el bloqueo; no la recuperación de Motion.

Backup local de todos los archivos afectados antes de esta corrección:
`../Humanoide-vla-evidence/20260910T072711Z_PICO-RELOAD-NO-ACTION/before/`.
Revertir selectivamente con robot fuera de ejecución, preservando cambios
anteriores. No restaurar para uso operativo la indicación errónea de liberar el
paro ni la propagación defectuosa de errores.

## Preparación de recuperación después del diagnóstico

open_v2 está instalado, pero su ejecución física sigue **pendiente**.
Motion no está operativo y los brazos siguen en PICO por declaración del usuario.
No repetir instalación/recarga, llamar StartMotion, cambiar de modo ni reiniciar
para probar. El HOME interno puede recorrer una trayectoria distinta de open_v2
y ya existe antecedente de contacto al cerrar brazos desde PICO.

Preparar primero la recuperación física y el apagado controlado según la guía
de esta unidad. Apagar no garantiza que los brazos desciendan de forma controlada;
no forzarlos ni liberar frenos de forma improvisada. Antes de cualquier arranque,
debe estar resuelta su postura y la zona de descenso por personal presente.
El usuario confirmó después abrazaderas vacías. La consulta preparatoria nueva
redescubre `/emb/pm_shutdown` con tipo `emb_task_msgs/srv/ShutDown` y su contrato
(`deadline_sec`, `confirm_str`, respuesta `success/message`). Se conserva la
solicitud documentada de plazo15 y `confirm-to-shutdown` como preparación;
**no se invocó el servicio**. Lectura nueva del principal=0 y ningún StartMotion
posterior a la liberación en el extracto CC consultado.

Se indica pulsar y mantener el E-stop, sin Power/KEY1. Se espera confirmación
de paro pulsado y de que una persona cualificada haya asegurado los brazos
contra caída/golpe al quitar alimentación. Esta preparación se exige por el
estado elevado actual; no se deduce del hecho de que las abrazaderas estén
vacías. Sin apagado, movimiento, rearme ni cambio de configuración enviados.

## Apagado solicitado y punto de reanudación vigente

El usuario confirmó después «confirmo estop y brazos asegurados». Lecturas
nuevas dieron principal1, servo0 y cargador0; servicio y tipo ShutDown vigentes.
La consulta de writers nativa no produjo salida: no se afirmó writers0.
Ese diagnóstico no fue requisito para cortar alimentación con el paro físico
accionado y los brazos asegurados; no se estaba habilitando ni ordenando movimiento.

Se envió **una única solicitud** a `/emb/pm_shutdown` a las 07:45:08Z (PC),
`deadline_sec=15`, `confirm_str=confirm-to-shutdown`. Respuesta `success=True`,
sin mensaje de error. No se reintentó. No se enviaron HOME, StartMotion,
cambios de frenos ni reinicios. Motion y Vision dejaron de responder a SSH;
no pudo recuperarse el log de la transición final de Control Center.

El operador confirmó entonces pantalla y luces superiores apagadas y brazos
asegurados/estables. Esto aporta la confirmación visual que la pérdida de red
no demostraba. Se indicó entonces pulsar KEY1 y después apagar el chasis con
su botón metálico, manteniendo E-stop y aseguramiento.

El operador respondió finalmente **«apagado y brazos abajo»** a la comprobación
de indicador verde apagado, estabilidad y postura después de KEY1/chasis.
Apagado completo confirmado; ya no se registra PICO como postura física vigente.
El apagado no valida open_v2 ni demuestra por sí solo un descenso controlado:
se había confirmado aseguramiento presencial de brazos antes de quitar energía.

Se indica el nuevo arranque habitual chasis→KEY1→encendido con el principal
pulsado, brazos abajo/vacíos/libres y personas fuera del recorrido.
**PENDIENTE:** confirmar nuevo encendido con paro, redescubrir servicios y
comprobar readiness antes de indicar liberar el E-stop. No seleccionar PICO
hasta confirmar que Motion está recuperado. La ejecución de open_v2 permanece
pendiente y no se ha ordenado ningún movimiento adicional.

Evidencia de esta fase: subdirectorio `shutdown-*` del directorio del incidente,
con lecturas previas, marcador de intento único, solicitud/respuesta y consulta
posterior de conectividad. Cambio remoto: apagado lógico solicitado; no se
modificaron archivos. Reversión no automática: sólo un arranque posterior
supervisado con la postura preparada, nunca un reinicio desde PICO para probar.

## Nuevo encendido y verificación de la espera

El usuario pregunta si el sonido significa que ya está encendido. Las lecturas
confirman ambos hosts accesibles, principal1/servo0/cargador0. El sonido no se
utiliza como prueba de autodiagnóstico completo.

CC conserva el comando de espera; contenedor iniciado07:53:53Z. Motion (hw,
manipulación y self-check) inició07:55:29Z, RestartCount0. El wrapper registró
cuatro intentos0/3 antes de obtener1/3,2/3,3/3 y ejecutar el CC original a
07:56:02Z. El nuevo log `cc_main.20260910_155603.184.log` alcanza
WaitEStopRelease a15:56:06 UTC+8. Esto verifica la prevención en arranque en
frío, sin reiniciar CC para recuperarlo ni saltar el autodiagnóstico.

La primera consulta del enlace `.latest.log` todavía devolvía Term del apagado
anterior, mientras el wrapper esperaba. Se contrastó después con la nueva
instancia y la salida Docker limitada al StartedAt actual; no se tomó ese Term
histórico por un fallo nuevo. El log recuperado también demuestra que el apagado
anterior sí alcanzó WaitShutdownReady→Shutdown→Term.

Los archivos open_v2 y task_list conservan sus hashes y entrada única tras el
ciclo de alimentación. El guard antiguo sigue disabled/inactive y su hash no
cambia. Se ejecuta sólo su `--check` como comprobación ampliada de servicios y
seis cámaras. Terminó rc0: x86 tres respuestas, seis cámaras en dos rondas,
v0.2.0, WaitEStopRelease y seguridad1/0/0. No reinició ni envió objetivos.
Se indica liberar el principal con los brazos abajo, vacíos y libres de las
sujeciones usadas al apagar, recorrido libre y persona junto al paro; puede
iniciar HOME interno. Pendientes confirmación de liberación y comprobaciones
posteriores self-check/StartMotion/postura/anillo. No activar PICO todavía.

Evidencia de consultas y pruebas:
`../Humanoide-vla-evidence/20260910T072711Z_PICO-RELOAD-NO-ACTION/`.
Reloj robot UTC+8 y desfase de unos 29 s frente al PC: la secuencia se compara
dentro de la misma fuente y por instancias, no mezclando tiempos sin corregir.
