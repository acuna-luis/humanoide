# HOME tras retorno desde ENTRY

2026-09-08. VERIFICADO: READY→HOME solicitado por propietario, con confirmación
física renovada del recorrido HOME. XML/YAML exactos cotejados, READY 20D
comprobado, actuadores sanos, ambos paros 0, cargador 0, baterías 61,6 %/80,9 %,
servidor ArmTask único, VLA exited/restart=no y RobotCommand writers 0.

Acción única `s2_bio_vla/s2_vla_e6_0_exact_recovery`, goal
`9c4933e1-c1b9-482f-a254-3992de03ff55`: SUCCEED/status=4, state=1101001, rc=0.
HOME final 20D máximo 0,002780 rad, brazos 0,000959 rad, velocidad cero,
veinte actuadores habilitados/sin fallos y delta consigna máximo 0,002780 rad.
Confirmación visual posterior PENDIENTE. Último estado medido HOME sustituye READY.
Sin cambios remotos de configuración/protecciones, reintentos, captura continua
ni monitor persistente. ENTRY sigue pendiente de revisión por inclinación.

Consulta de script: `scripts/vla/cruzr_vla_ready_pose.sh` aún reserva/bloquea
--run-recover. `scripts/cruzr_recover_to_home.sh` corresponde a recuperación
HOME/ciclo de caja y puede mover chasis; no es sustituto directo de esta tarea
READY→HOME. No se habilitó ningún wrapper con esta ejecución. Se observó que
el contenido actual del lock compartido está comentado; no fue editado por
esta intervención y no se utilizó como prueba de seguridad.

Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260908T073158Z_OWNER-READY-HOME-SECOND/`.
