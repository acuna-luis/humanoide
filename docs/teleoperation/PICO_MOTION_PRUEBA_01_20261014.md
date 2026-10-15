# Primera reproducción de movimiento PICO — 14-10-2026

ID PICO-MOTION-REPLAY-20261014; zona Europe/Madrid. Operador autoriza reproducción y confirma abrazaderas vacías, trayectoria de brazos/cabeza despejada, cargador fuera, persona junto al paro y PICO/web/otros mandos detenidos. Nueva autorización para continuar tras interrupción.

Original PC: /home/lacuna/grabaciones_cruzr/prueba_pico_01_20261014_192800.motion; SHA2560191fb331c6f2ebc5be0cfb5f8d6c9a2369600e6a07b77dc14d3d990c0003af9. Motion contenedor walker-motion.manipulation_robot_app-1, original /tmp/pico_grabaciones/ con el mismo nombre/hash. Copia nueva /tmp/pico_grabaciones/prueba_pico_01_lenta_20261014.motion; SHA2561e8d7ac8250708907e4c962c66a5c7a06fb34b6f7389059cc52f09ff561d65cb. Editor native scale factor2: posiciones idénticas, tiempos exactamente dobles,33,68s. Conservado original; borrar exclusivamente copia lenta para revertir creación de archivo. /tmp es temporal: guardar fuera antes de reiniciar si se desea conservar.

Receta del editor, en contenedor Motion tras source /opt/walker/setup.bash (no repetir si destino existe):

```bash
rosa run manipulation_outline_sdk editor -- scale --input /tmp/pico_grabaciones/prueba_pico_01_20261014_192800.motion --output /tmp/pico_grabaciones/prueba_pico_01_lenta_20261014.motion --factor 2.0
```

Preflight pasivo contrastado: SDK joint_order/utars_joints.yaml y /mc/joint_states coinciden con inicio (máxdiferencia0,002876rad); velocidades0, sin error_code, actuadores habilitados, paros0/0, cargador0, baterías28,6/36,8%, sin acción activa (status5cancelada anterior), controladores force_torque y manipulation running. La comparación inicial con rawactuator generó diferencias de signos: se corrigió usando articulaciones SDK por nombre, no modificando trayectoria ni signando manualmente comandos. Modo últimoobservadojoystick, sin cambio de modo. SDKplayer documentado para reproducción tras teleoperación; ninguna orden adicional de HOME/enable. Cabeza también se mueve, brazoizquierdo constante y derecho variable.

Comando físico previsto, una sola reproducción (NO diagnóstico):

```bash
source /opt/walker/setup.bash
export ROS2CLI_DISABLE_DAEMON=1
rosa run manipulation_outline_sdk player -- --robot utars --input /tmp/pico_grabaciones/prueba_pico_01_lenta_20261014.motion
```

No ejecutar esta receta sin volver a comprobar postura y condiciones físicas/exclusividad. No hay retornoHOME automático. No cambiar a ciegas q, velocidades ni controles de fuerza. Evidencia privada fueraGit: ../Humanoide-vla-evidence/20261014_PICO_REPLAY_PRECHECK/, consultas, hashes, validaciones y resultados. Resultado: reproducción intentada una vez, FALLIDA por std::bad_any_cast del player antes de recorrer trayectoria. No commit/push.


## Resultado del único intento

Inicio11:52:51Z, fin11:52:52Z. El proceso informa `terminate called after throwing an instance of std::bad_any_cast; what(): bad any_cast`; el wrapper rosa/SSH devuelve rc0 a pesar del error. Por tanto rc0 NO se acepta como éxito. No se completó trayectoria, no hay repetición ni HOME enviados. Consulta posterior pasiva: velocidades0 y cambio máximo de posiciones (sin ruedas)0,000095874rad respecto al preflight; no demuestra estado continuo durante el segundo del intento. Logs Motion acotados al intento vacíos; causa raíz del fallo de tipos SDK PENDIENTE. No se atribuye al usuario, postura, mapa, formato o copia ralentizada sin diagnóstico adicional. No se cambia modo ni SDK vendor. El timeout envolvente65s no llegó a actuar.

Despliegue persistente: ninguno de configuración; sólo copia lenta en /tmp y documentación PC. Copia original permanece intacta por hash verificado. Pendiente verificar compatibilidad real recorder/player/SDK y contrato antes de un nuevo intento, con autorización/estado físico vigentes.


## Corrección PICO-PLAYER-LOOP-20261014 — VERIFICADO parser, reproducción pendiente

El error del intento anterior fue provocado por `--loop 1`, añadido por el agente para pedir una sola pasada. El binario vendor registra default1 como int pero deja el valor explícito como string; la extracción int produce std::bad_any_cast ANTES de rosa::init, creación del cliente y carga del archivo. No es un diagnóstico de fallo de grabación ni de firmware; no se modifica el SDK original. La receta física de arriba queda corregida eliminando --loop; el valor predeterminado de esta build es1. La llamada histórica fallida se conserva íntegra en play-start.json de la evidencia previa.

Build player SHA2568744a30ecce20c414dcf67b60d9aa7ac486bab752d5eee3de08a7336d65ddf0d, BuildID309bda94efa296773a856865350828008c2d0cc4. Inspección estática del main muestra default int1 y extracción de --loop antes de rosa::init. Dos pruebas en el binario real con entrada deliberadamente inexistente y bloqueo obligatorio de la función rosa::init: explícito --loop1 devuelve señal6 y bad_any_cast; sin opción alcanza bloqueo con marcador PICO_PLAYER_PARSE_OK_ROSA_INIT_BLOCKED y rc86. No se crea cliente ni se inicia reproducción. Compilación/interposer sólo en carpeta temporal propia, eliminada al terminar; no se desactiva ninguna seguridad del control en ejecución. Fuente reproducible [pico_player_parser_probe.cpp](../../scripts/teleoperation/pico_player_parser_probe.cpp).

Receta de diagnóstico exclusiva para esta build, en contenedor con g++ y setup cargado: verificar primero SHA256 del player anterior; compilar la fuente como biblioteca compartida en una carpeta temporal (`g++ -shared -fPIC probe.cpp -o probe.so`); invocar directamente el ELF player con LD_PRELOAD apuntando a probe.so, --robot utars --input /__PARSER_ONLY_NEVER_PLAY__/absent.motion, primero con --loop1 y luego sin opción. El marcador/rc86 identifica parada ANTES de init. Nunca usar este LD_PRELOAD para una reproducción real. Mantener RLIMIT_CORE0 y eliminar carpeta temporal. Comandos/respuestas completos reproducibles del diagnóstico en evidencia.

No se repitió movimiento al arreglar el comando. Nueva reproducción requiere postura/estado físicos vigentes. El parser corregido no certifica que la ejecución de trayectoria termine con éxito: pendiente prueba física. No grabación, versión de librerías ni archivos motion alterados. Evidencia ../Humanoide-vla-evidence/20261014_PICO_PLAYER_BAD_ANY_DIAG/ con ELF original privado, hashes, símbolos, disassembly y resultados; no binarios enGit. Reversión documental selectiva desde before; no rollback del vendor. No commit/push.


## Reproducción corregida posterior — éxito confirmado

El operador vuelve a autorizar reproducción y confirma condiciones físicas actuales. Preflight y hashes correctos. Una llamada player SIN --loop, original SDK intacto: inicio2026-10-14T12:03:40.613313Z, fin12:04:15.917469Z, rc0/stderr vacío e `Action finished with is_finished=true, bag has been played successfully`. Operador confirma que funcionó perfectamente. No se mandó HOME ni otro movimiento. El turno fue interrumpido antes de obtener medición final prevista: no se declara un postflight medido que no existe. La lectura anterior de postura corresponde al preflight. Archivo/evidencia ../Humanoide-vla-evidence/20261014_PICO_REPLAY_CORRECTED/.

Para futuras tomas seguir [procedimiento reutilizable](PICO_GRABAR_REPRODUCIR_PROCEDIMIENTO.md): no reinvestigar parser o signos si software no cambia; inspector offline e inicial por nombre, preflight único y reproducir sin --loop. Confirmaciones físicas y salud actual se conservan.
