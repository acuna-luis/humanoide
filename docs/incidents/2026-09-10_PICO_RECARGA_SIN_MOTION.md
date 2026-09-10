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
La ausencia de objeto en las abrazaderas aún requiere confirmación explícita.
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

## Punto de reanudación

open_v2 está instalado, pero su ejecución física sigue **pendiente**.
Motion no está operativo y los brazos siguen en PICO por declaración del usuario.
No repetir instalación/recarga, llamar StartMotion, cambiar de modo ni reiniciar
para probar. El HOME interno puede recorrer una trayectoria distinta de open_v2
y ya existe antecedente de contacto al cerrar brazos desde PICO.

Preparar primero la recuperación física y el apagado controlado según la guía
de esta unidad. Apagar no garantiza que los brazos desciendan de forma controlada;
no forzarlos ni liberar frenos de forma improvisada. Antes de cualquier arranque,
debe estar resuelta su postura y la zona de descenso por personal presente.
La pregunta pendiente aclara si están vacías las abrazaderas; no autoriza por sí
sola un apagado, rearme ni trayectoria. Ningún movimiento o rearme enviado.

Evidencia de consultas y pruebas:
`../Humanoide-vla-evidence/20260910T072711Z_PICO-RELOAD-NO-ACTION/`.
Reloj robot UTC+8 y desfase de unos 29 s frente al PC: la secuencia se compara
dentro de la misma fuente y por instancias, no mezclando tiempos sin corregir.
