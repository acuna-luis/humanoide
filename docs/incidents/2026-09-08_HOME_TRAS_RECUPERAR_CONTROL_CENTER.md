# Recuperación de arranque y HOME tras reinicio de Control Center

2026-09-08. VERIFICADO tras liberación física del E-stop por operador:
self-check passed=true/error0; StartMotion succ; SelfChecking→JoystickMode.
Servidor ArmTask1. Muestra20D: errores0, OperationEnabled, velocidades0,
max posición0,003068 rad (brazos0,000959), max delta consigna0,003068 rad;
MEASURED_HOME=1. Ambos paros0, cargador0. VLA exited/restart=no, RobotCommand
writers0/readers2. Confirmación visual de estabilidad/sin tirón/contacto PENDIENTE.

Intervención anterior: único restart autorizado de Control Center con principal
presionado; se verificó WaitEStopRelease y servicio x86 antes de esta liberación.
No se reinició hardware desde agente: su StartedAt08:24:06.390Z y RestartCount1
permanecen iguales. No HOME ni enable/StartMotion publicados por agente;
la secuencia normal del Control Center realizó el arranque. Recuperación
operativa observada, no reparación demostrada del watchdog FT6002/SIGSEGV.

Último estado vigente HOME medido sustituye Fault. No repetir esta recuperación
como bucle automático; conservar diagnóstico del sensor derecho y escalar si
recurre. No valida nuevo agarre ni resuelve geometría ENTRY/PICO→HOME general.
Sin cambios de archivos/protecciones remotos ni monitor persistente.

Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260908T083349Z_AFTER-CC-RECOVERY-RELEASE/`.
