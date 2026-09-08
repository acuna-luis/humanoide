# Retorno ENTRY→READY por inclinación observada

2026-09-08. VERIFICADO: acción única SUCCEED/status=4, state=1101001.
Task `s2_bio_vla/s2_vla_e6_1c_entry_to_ready`, goal
`32ba33a5-0c2c-48aa-91ca-6530b659bce5`. Usuario pidió READY o HOME;
se eligió READY para revertir los seis ejes de la transición, con XML de 12 s.
Confirmó de nuevo recorrido libre y condiciones físicas después de advertir
mesa/caja/persona próximas en la fotografía. Sin retorno adicional a HOME.

Preflight: ENTRY medido inmóvil, actuadores sanos; XML remoto idéntico al local,
contenedores descubiertos, ambos paros 0, cargador 0, baterías 61,6 %/82 %,
servidor ArmTask único, writers RobotCommand 0, VLA exited/restart=no.
El auditor E6.0G --check fue inaplicable porque exige un paro accionado para su
escenario diagnóstico; se conservó el fallo y se consultaron directamente los
estados vigentes. No se modificó el auditor ni se puenteó protección alguna.

Resultado: READY brazos error máximo 0,001633 rad, seis ejes de cuerpo dentro
de 0,01 rad de READY, velocidad 20D cero, veinte actuadores habilitados/sin
fallos y delta máximo consigna 0,001633 rad. No captura continua del retorno:
no se valida dinámica por el éxito del endpoint. Sin cambios remotos de
configuración, reintentos, checkpoint físico ni monitor persistente.

VERIFICADO por confirmación posterior del operador: retorno estable, libre de
contacto y torso en postura adecuada (respuesta «sí»). La postura ENTRY anterior
sigue pendiente de revisión por inclinación del torso señalada por el usuario;
no se interpreta la llegada a los objetivos como aceptación de su idoneidad.
Shadow 0/5, fixture pendiente. Último estado medido READY sustituye ENTRY.

Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260908T072711Z_OWNER-ENTRY-READY/`.
