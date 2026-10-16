# Arranque fallido tras retirar las manos v4

15-10-2026, Europe/Madrid. ID HANDS-REMOVED-BOOT-20261015.

## Estado observado

El operador informa brazos estables y muñecas sin manos ni abrazaderas para
embalar y trasladar el robot. Retirada con alimentación apagada no confirmada.
Ambos paros físicos pendientes de confirmación; una lectura nueva del principal
`/emb/estop_key_state` devuelve 0 (liberado). No se interpreta como autorización
para reiniciar, rearmar ni mover. HOME actual no medido.

## Hallazgo verificado por lectura

- Motion hw y Vision Control Center conservan `HW_TYPE=cruzr_s2_v1_sps`.
- Hardware registra `InitDeviceManager:hand cnt=0` y el bus llega a estado 8/OP.
- Selección persistente observada: `last_eni: "eni_cruzr_kw_noimu.xml"`.
  La selección automática difiere de la de manos instaladas; no fue cambiada por el agente.
- El controlador `dexterous_hand_controller` intenta obtener `/ecat/hand/get_version`,
  agota timeout y falla con `Unknown hand type` / `Dexterous Hand Controller Init Failed`.
- Control Center termina StartMotion con reason 19 y pasa a Fault.
- Manipulación reinicia automáticamente y espera `force_torque_sensor_controller`.
  Esta espera posterior no demuestra una avería del sensor de fuerza/par.

Conclusión: la ausencia física de manos y la carga del controlador de manos
son incompatibles en este arranque. El mensaje que sugiere exportar HAND_TYPE
no resuelve la ausencia de hardware. No afirmar un fallo físico de los sensores.
Marcas internas de logs en zona distinta a PC: no presentarlas como hora local.

## Continuación

Identificar un perfil y procedimiento del proveedor compatibles con la unidad
sin efectores antes de cambiar configuración. El perfil de abrazaderas no queda
validado automáticamente para muñecas vacías. Precisar si el traslado será
motorizado o manual; verificar también procedimiento de ruedas/frenos, postura,
paros y soportes. No forzar HOME/start ni liberar frenos sin contrato comprobado.
Una recarga puede iniciar HOME y requiere preparación física actual.

## Evidencia y cambios

`../Humanoide-vla-evidence/20261015_HANDS_REMOVED_BOOT/`: contenedores, logs
hw/app/CC, perfil efectivo y muestra del paro. Consultas SSH/docker/logs y una
suscripción acotada; sin publicación, movimiento, reinicio ni cambio remoto.
Cambio local exclusivamente documental. Respaldo de índices en before-docs;
reversión selectiva de esta entrada y enlaces, conservando otras ediciones.

## Cambio a perfil de abrazaderas solicitado

Usuario autoriza restaurar perfil anterior e iniciar sistema. INSTALADO, no
cargado: Motion compose devuelve HW_TYPE base mediante transformación revisada;
DB global ya era base, se conserva byte a byte (uDoke cambió solo su formato JSON
respecto al respaldo original). El instalador anterior rechazó correctamente
este estado mixto; se comprobó igualdad semántica completa antes de preparar la
receta `scripts/teleoperation/restore_clamp_environment.py`.
Vision compose y metafile de CC restaurados con el rollback revisado existente.
No se restauró un compose distinto ni se alteró HOME, ENI, límites o watchdogs.

Recetas:
- `python3 scripts/teleoperation/restore_clamp_environment.py --check --evidence NUEVO`
- `--install` aplica archivos Motion sin recarga.
- `python3 scripts/teleoperation/install_pico_v4_cc_env.py --rollback --evidence NUEVO`
- `scripts/teleoperation/activate_clamp_profile.py` separa inventario/respaldo,
  parada, recreación/restauración, carga y verificación. Recarga PENDIENTE.

Respaldos de configuración/inventario externos en
`../Humanoide-vla-evidence/20261015_RETURN_CLAMP/` (privado). Motion remoto conserva
compose/DB previos en `/home/walker/.local/share/cruzr-return-clamp-20261015/`;
Vision conserva el stage CC anterior. Configuración de controles base no incluye
`dexterous_hand_controller`, a diferencia de SPS; ver controller-profiles.json.
El estado físico para reactivar sigue pendiente de la respuesta del operador;
no iniciar ni pedir liberación de E-stop sin ella. Arranque con muñecas vacías
no validado físicamente todavía. Procesos actuales siguen SPS hasta recreación.
Reversión: restaurar exclusivamente los archivos previos verificados y recrear
con las mismas imágenes y archivos conservados, bajo preparación física actual.

### Recarga completada con paro principal pulsado

El operador confirma condiciones físicas, después «pulsado estop todo asegurado».
Lecturas previas: principal/servo 0/0, cargador0 y baterías33,8/39,8%; cada fase
vuelve a exigir principal1/cargador0. Con esos valores se detienen CC y nueve
servicios Motion; se recrean los mismos nueve con imágenes idénticas y único
cambio de entorno HW_TYPE base. Cmd/montajes iguales. Archivos modificados
restaurados y hashes de los nueve contenedores verificados antes de arrancar CC.
CC recreado también con mismaimagen, comando/guard, montajes y resto del entorno.

Carga observada: hw/app running, restart0, HW_TYPE=cruzr_s2_v1; hardware espera
start nativo, sin start ROS ni HOME adicional del agente. Guard CC llega a
Motion3/3 y MOTION_READY1; resto de readiness y liberación siguen pendientes en
este punto. No se requiere apagar/reencender todavía. No se declara HOME ni
robot listo para desplazamiento.

Preparación de respaldo excedió el timeout diagnóstico SSH18s; no se repitió a
ciegas. Lectura posterior verifica manifests/archives completos; se exporta
reload-backup.tar.gz a PC y se comprueba SHA de nueve archivos tar. Recetas de
fases posteriores usan timeout120s y recibos secuenciales; no alteran watchdogs.
Copia privada incluye grabación .motion suelta y archivos personalizados; no
se añade a Git. El debug detenido no se arranca. Conserva guard de voz/arranque.
Los avisos compose LD_LIBRARY_PATH/DISPLAY sin definir no cambian los entornos
comparados; ver recibos de igualdad efectiva antes de activar.

Readiness final bajo paro: Motion3/3, seis cámaras2/2 con timestamps avanzando;
CC nativo bootready, Recover succ y WaitEStopRelease. Principal1 y servo0.
Se solicita al operador liberación supervisada con recorrido libre y soportes
fuera de trayectoria; respuesta pendiente. No requiere reinicio físico.

### Resultado final VERIFICADO

Operador confirma liberación del paro. CC detecta principal0, SelfCheck succ,
LimbMotion succ, StartMotion succ y JoystickMode. La secuencia nativa ejecuta
HOME; no se envió un objetivo HOME adicional. Consulta ListControllers responde:
controladores de fuerza/par y manipulación activos, sin dexterous_hand_controller.

Muestra nueva whole_joint_states:20 ejes corporales, posición absoluta máxima
0,003068rad y velocidad0. Muestra nueva actuator_state con QoS best_effort pasa
el clasificador original: HOME20D=1, maxposición0,002972rad, brazos0,000863rad,
velocidad0, diferencia máxima consigna/medida0,002972rad; sin fallos ni actuadores
inhabilitados según dicho clasificador. Consulta reliable previa agotó timeout:
no se rebajaron límites ni se supuso ausencia de telemetría. Se conservan ambos
recibos. El resultado confirma arranque/HOME sin efectores; no valida una
trayectoria de transporte, navegación ni empuje manual.

No hace falta reinicio físico. Estado de continuación: perfil base de
abrazaderas, muñecas vacías, JoystickMode y HOME medido. Para volver a manos,
instalar hardware con alimentación apagada según SOP y restaurar perfil SPS
con preparación y comprobaciones nuevas. No usar PICO v4 con este perfil base.

Verificación de recetas: sintaxis de ambos scripts y código remoto, ayuda CLI,
igualdad de imágenes/Cmd/montajes y entorno salvo HW_TYPE, nueve archivos tar
comprobados fuera del robot y hashes de archivos restaurados. Incidente y
personalizaciones actualizados sin commit/push.
